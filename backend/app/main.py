import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.v1.router import api_router
from app.models.entities import Device, Telemetry, DatasetSource, Alert, Experiment, User
from app.collector.synthetic import SyntheticGenerator
from app.ml.models import run_forecast
from app.ml.calibration import ModelCalibrator
from app.auth.security import hash_password
from app.auth.permissions import seed_roles_and_permissions
from app.services.fleet_topology_service import FleetTopologyService
from app.services.outcome_ledger import OutcomeLedgerService
from app.services.model_governance import ModelGovernanceService
from app.services.jurassic.experiment_runner import ExperimentRunner
from app.services.phoenix import PolicyGateway, RunbookEngine, IncidentCorrelationEngine
from app.services.atlas import (
    DigitalTwinCalibrationEngine, ActionEffectEvidenceService,
    ValueOfExperimentPlanner, FidelityAssessor
)
from app.services.oracle import (
    WorkloadCatalogService, BottleneckForensicsEngine, HypothesisManager
)
from app.services.gauntlet_service import GauntletService
from app.services.sovereign_service import SovereignService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegisstor")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def initialize_database_and_seed_demo():
    """
    Initializes database schema and populates with realistic deterministic synthetic
    storage telemetry, initial alert states, and experiment backtests.
    Strictly idempotent: re-running does not produce duplicate devices or duplicate telemetry.
    """
    logger.info("Initializing AEGISSTOR database tables...")
    Base.metadata.create_all(bind=engine)

    from sqlalchemy import inspect as sa_inspect, text
    try:
        with engine.connect() as conn:
            inspector = sa_inspect(engine)
            if "devices" in inspector.get_table_names():
                columns = [c["name"] for c in inspector.get_columns("devices")]
                if "pool_id" not in columns:
                    conn.execute(text("ALTER TABLE devices ADD COLUMN pool_id VARCHAR(64)"))
                if "system_id" not in columns:
                    conn.execute(text("ALTER TABLE devices ADD COLUMN system_id VARCHAR(64)"))
                if "organization_id" not in columns:
                    conn.execute(text("ALTER TABLE devices ADD COLUMN organization_id VARCHAR(64) DEFAULT 'org-primary-enterprise'"))
            if "users" in inspector.get_table_names():
                user_cols = [c["name"] for c in inspector.get_columns("users")]
                user_migrations = [
                    ("organization_id", "VARCHAR(64) DEFAULT 'org-primary-enterprise'"),
                    ("failed_login_attempts", "INTEGER DEFAULT 0"),
                    ("locked_until", "DATETIME"),
                    ("last_login_at", "DATETIME"),
                    ("password_changed_at", "DATETIME"),
                    ("created_at", "DATETIME"),
                ]
                for c_name, c_def in user_migrations:
                    if c_name not in user_cols:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {c_name} {c_def}"))
            if "audit_logs" in inspector.get_table_names():
                audit_cols = [c["name"] for c in inspector.get_columns("audit_logs")]
                audit_migrations = [
                    ("organization_id", "VARCHAR(64) DEFAULT 'org-primary-enterprise'"),
                    ("client_ip", "VARCHAR(64) DEFAULT '127.0.0.1'"),
                    ("prev_hash", "VARCHAR(64)"),
                    ("entry_hash", "VARCHAR(64)"),
                    ("user_id", "VARCHAR(64)"),
                    ("user_role", "VARCHAR(32)"),
                    ("outcome", "VARCHAR(32) DEFAULT 'SUCCESS'"),
                ]
                for c_name, c_def in audit_migrations:
                    if c_name not in audit_cols:
                        conn.execute(text(f"ALTER TABLE audit_logs ADD COLUMN {c_name} {c_def}"))
            if "recommendations" in inspector.get_table_names():
                rec_cols = [c["name"] for c in inspector.get_columns("recommendations")]
                if "details_json" not in rec_cols:
                    conn.execute(text("ALTER TABLE recommendations ADD COLUMN details_json TEXT DEFAULT '{}'"))
            # Ensure v2 enterprise columns exist idempotently
            col_migrations = {
                "devices": [
                    ("storage_type", "VARCHAR(64) DEFAULT 'SAN'"),
                    ("environment_location", "VARCHAR(128) DEFAULT 'Primary Data Center'"),
                    ("description", "TEXT DEFAULT ''"),
                    ("notes", "TEXT DEFAULT ''"),
                    ("last_telemetry_at", "DATETIME"),
                    ("version", "INTEGER DEFAULT 1"),
                    ("created_by", "VARCHAR(64) DEFAULT 'system'"),
                    ("updated_by", "VARCHAR(64) DEFAULT 'system'"),
                ],
                "scenarios": [
                    ("version", "INTEGER DEFAULT 1"),
                    ("updated_at", "DATETIME"),
                    ("updated_by", "VARCHAR(64) DEFAULT 'system_operator'"),
                ],
                "application_settings": [
                    ("version", "INTEGER DEFAULT 1"),
                ],
                "background_jobs": [
                    ("stage", "VARCHAR(32) DEFAULT 'QUEUED'"),
                    ("progress_pct", "INTEGER DEFAULT 0"),
                    ("updated_at", "DATETIME"),
                ],
                "telemetry": [
                    ("total_capacity_bytes", "BIGINT"),
                    ("read_latency_ms", "FLOAT"),
                    ("write_latency_ms", "FLOAT"),
                ],
                "forecasts": [
                    ("model_version_id", "VARCHAR(64)"),
                    ("horizon_days", "INTEGER"),
                    ("daily_predictions_json", "TEXT"),
                    ("projected_capacity_breach", "BOOLEAN DEFAULT 0"),
                    ("breach_timestamp", "DATETIME"),
                ],
                "alerts": [
                    ("acknowledged_by", "VARCHAR(64)"),
                    ("acknowledged_at", "DATETIME"),
                    ("resolution_details", "TEXT"),
                    ("supporting_evidence_json", "TEXT DEFAULT '{}'"),
                ],
            }
            for tbl, cols in col_migrations.items():
                if tbl in inspector.get_table_names():
                    existing_c = [c["name"] for c in inspector.get_columns(tbl)]
                    for c_name, c_def in cols:
                        if c_name not in existing_c:
                            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {c_name} {c_def}"))
            conn.commit()


    except Exception as e:
        logger.warning(f"Column migration check note: {e}")

    db = SessionLocal()
    try:
        # 0. Seed Role & Permission catalog idempotently
        seed_roles_and_permissions(db)

        # 0b. Secure first-admin bootstrap from explicit environment variables only when no admin exists
        admin_exists = db.query(User).filter(User.role == "ADMIN", User.is_active == True).count() > 0
        bootstrap_user = os.getenv("AEGISSTOR_BOOTSTRAP_ADMIN_USERNAME", "").strip()
        bootstrap_pass = os.getenv("AEGISSTOR_BOOTSTRAP_ADMIN_PASSWORD", "")
        bootstrap_email = os.getenv("AEGISSTOR_BOOTSTRAP_ADMIN_EMAIL", "admin@aegisstor.internal").strip()
        if not admin_exists and bootstrap_user and len(bootstrap_pass) >= 8:
            if not db.query(User).filter((User.username == bootstrap_user) | (User.email == bootstrap_email)).first():
                db.add(User(
                    id=f"usr-bootstrap-{uuid.uuid4().hex[:8]}",
                    username=bootstrap_user,
                    email=bootstrap_email,
                    hashed_password=hash_password(bootstrap_pass),
                    role="ADMIN",
                    is_active=True,
                ))
                db.commit()
                logger.info(f"Bootstrapped initial administrator '{bootstrap_user}' from environment.")

        # 0c. Local development synthetic user seeding (NEVER active by default)
        if os.getenv("AEGISSTOR_ALLOW_DEV_SEED", "false").lower() == "true":
            dev_accounts = [
                (
                    "usr-dev-admin",
                    os.getenv("AEGISSTOR_DEV_ADMIN_USER", "admin"),
                    os.getenv("AEGISSTOR_DEV_ADMIN_EMAIL", "admin@aegisstor.internal"),
                    os.getenv("AEGISSTOR_DEV_ADMIN_PASS", "AegisAdmin!2026"),
                    "ADMIN",
                ),
                (
                    "usr-dev-operator",
                    os.getenv("AEGISSTOR_DEV_OPERATOR_USER", "operator"),
                    os.getenv("AEGISSTOR_DEV_OPERATOR_EMAIL", "operator@aegisstor.internal"),
                    os.getenv("AEGISSTOR_DEV_OPERATOR_PASS", "AegisOperator!2026"),
                    "OPERATOR",
                ),
                (
                    "usr-dev-viewer",
                    os.getenv("AEGISSTOR_DEV_VIEWER_USER", "viewer"),
                    os.getenv("AEGISSTOR_DEV_VIEWER_EMAIL", "viewer@aegisstor.internal"),
                    os.getenv("AEGISSTOR_DEV_VIEWER_PASS", "AegisViewer!2026"),
                    "VIEWER",
                ),
            ]
            for uid, uname, uemail, upass, urole in dev_accounts:
                if not db.query(User).filter(User.username == uname).first():
                    db.add(User(
                        id=uid,
                        username=uname,
                        email=uemail,
                        hashed_password=hash_password(upass),
                        role=urole,
                        is_active=True,
                    ))
                    db.flush()
            db.commit()

        # Idempotently seed default enterprise organisation and link all existing users
        from app.models.enterprise_entities import Organisation, OrganisationMember
        default_org_id = "org-primary-enterprise"
        if not db.query(Organisation).filter(Organisation.id == default_org_id).first():
            db.add(Organisation(
                id=default_org_id,
                name="Primary Enterprise Infrastructure",
                slug="primary-enterprise",
                plan="ENTERPRISE",
                default_currency="USD",
                status="ACTIVE",
            ))
            db.flush()
        for existing_user in db.query(User).all():
            if not existing_user.organization_id:
                existing_user.organization_id = default_org_id
            member = db.query(OrganisationMember).filter(
                OrganisationMember.organization_id == (existing_user.organization_id or default_org_id),
                OrganisationMember.user_id == existing_user.id,
            ).first()
            if not member:
                db.add(OrganisationMember(
                    id=f"mem-{existing_user.id}-primary",
                    organization_id=existing_user.organization_id or default_org_id,
                    user_id=existing_user.id,
                    role=existing_user.role or "OPERATOR",
                    status="ACTIVE",
                ))
        db.commit()

        from app.services.control_plane_service import seed_action_definitions
        seed_action_definitions(db)

        # Never populate synthetic storage/telemetry/alerts into a live runtime database unless explicitly requested
        allow_synthetic_seed = (
            os.getenv("AEGISSTOR_SEED_SYNTHETIC_DEMO", "false").lower() == "true"
            or bool(os.getenv("PYTEST_CURRENT_TEST"))
        )
        if not allow_synthetic_seed:
            db.commit()
            logger.info("Schema, RBAC catalog, and live bootstrap verified (zero synthetic records seeded).")
            return

        gen = SyntheticGenerator(seed=42)
        
        # 1. Register dataset source metadata idempotently
        ds_id = "ds-synthetic-enterprise-v1"
        existing_ds = db.query(DatasetSource).filter(DatasetSource.id == ds_id).first()
        if not existing_ds:
            ds = DatasetSource(
                id=ds_id,
                name="Synthetic Multi-Tier Enterprise Storage Benchmark",
                dataset_type="SYNTHETIC",
                records_count=721 * len(SyntheticGenerator.DEVICES_CONFIG),
                missing_rate=0.002,
                sampling_interval_s=3600,
                license="CC-BY-4.0 / Academic Evaluation",
                description="Deterministic synthetic time-series modeling diurnal enterprise OLTP, analytics, and cold tier workloads."
            )
            db.add(ds)
            db.flush()

        # 2. Insert or update devices and generated telemetry idempotently
        for dev_cfg in SyntheticGenerator.DEVICES_CONFIG:
            dev_id = dev_cfg["id"]
            existing_dev = db.query(Device).filter(Device.id == dev_id).first()
            if not existing_dev:
                device = Device(
                    id=dev_id,
                    name=dev_cfg["name"],
                    tier=dev_cfg["tier"],
                    media_type=dev_cfg["media_type"],
                    total_capacity_bytes=dev_cfg["total_capacity_bytes"],
                    warning_threshold_pct=dev_cfg["warning_threshold_pct"],
                    critical_threshold_pct=dev_cfg["critical_threshold_pct"],
                    max_acceptable_latency_ms=dev_cfg["max_acceptable_latency_ms"],
                    min_free_reserve_pct=dev_cfg["min_free_reserve_pct"],
                    status="WARNING" if "nvme" in dev_id or "archive" in dev_id else "HEALTHY",
                    workload_profile=dev_cfg["workload_profile"]
                )
                db.add(device)
                db.flush()
            else:
                device = existing_dev

            # Check if telemetry already seeded for this device and is fresh
            tel_count = db.query(Telemetry).filter(Telemetry.device_id == dev_id).count()
            latest_tel = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == dev_id)
                .order_by(Telemetry.timestamp.desc())
                .first()
            )
            is_stale = False
            if latest_tel and latest_tel.timestamp:
                t_val = latest_tel.timestamp
                if t_val.tzinfo is None:
                    t_val = t_val.replace(tzinfo=timezone.utc)
                age_h = (utc_now() - t_val).total_seconds() / 3600.0
                if age_h > 24.0:
                    is_stale = True

            if tel_count < 100 or is_stale:
                if is_stale:
                    db.query(Telemetry).filter(Telemetry.device_id == dev_id).delete()
                    db.flush()
                telemetry_data = gen.generate_device_telemetry(dev_cfg, hours_history=720)
                telemetry_objects = [
                    Telemetry(
                        device_id=t["device_id"],
                        timestamp=t["timestamp"],
                        used_bytes=t["used_bytes"],
                        free_bytes=t["free_bytes"],
                        utilization_pct=t["utilization_pct"],
                        read_iops=t["read_iops"],
                        write_iops=t["write_iops"],
                        throughput_mb_s=t["throughput_mb_s"],
                        latency_p95_ms=t["latency_p95_ms"],
                        queue_depth=t["queue_depth"],
                        is_synthetic=t["is_synthetic"],
                        source_label=t["source_label"]
                    )
                    for t in telemetry_data
                ]
                db.bulk_save_objects(telemetry_objects)

        # 3. Seed realistic initial alerts idempotently
        initial_alerts = [
            {
                "id": "alert-cap-nvme-01",
                "device_id": "vol-nvme-tier1-db",
                "category": "CAPACITY_RISK",
                "severity": "WARNING",
                "title": "Reserve Runway < 48 Hours on Production NVMe",
                "message": "Projected growth trajectory indicates critical threshold (90%) will be breached within 46.5 hours under predicted diurnal load."
            },
            {
                "id": "alert-perf-hdd-02",
                "device_id": "vol-hdd-archive",
                "category": "PERFORMANCE_RISK",
                "severity": "WARNING",
                "title": "P95 Latency Spikes During Parity Scrubbing",
                "message": "RAID parity verification cycles between 02:00-04:00 cause tail latency to exceed 35ms."
            },
            {
                "id": "alert-model-drift-01",
                "device_id": "vol-nvme-tier1-db",
                "category": "MODEL_DRIFT",
                "severity": "INFO",
                "title": "Transient Workload Variance Observed",
                "message": "Recent ETL write spike increased short-term residual variance; conformal interval width expanded by 4.2%."
            }
        ]

        for a_dict in initial_alerts:
            if not db.query(Alert).filter(Alert.id == a_dict["id"]).first():
                db.add(Alert(
                    id=a_dict["id"],
                    device_id=a_dict["device_id"],
                    category=a_dict["category"],
                    severity=a_dict["severity"],
                    title=a_dict["title"],
                    message=a_dict["message"],
                    status="ACTIVE"
                ))

        # 4. Seed initial backtest experiment idempotently
        exp_id = "exp-baseline-comparison-01"
        if not db.query(Experiment).filter(Experiment.id == exp_id).first():
            exp1 = Experiment(
                id=exp_id,
                name="Multi-Horizon Quantile Backtest vs Baselines (72h)",
                dataset_name="Synthetic Multi-Tier Enterprise Storage Benchmark",
                model_type="LightGBM Quantile Regressor",
                horizon_hours=72,
                train_samples=576,
                test_samples=144,
                mae=28.4,
                rmse=36.2,
                pinball_loss=11.9,
                interval_coverage=0.885,
                mean_interval_width=74.5,
                manifest_json='{"backtest_type": "chronological_rolling", "quantiles": [0.10, 0.50, 0.90]}'
            )
            db.add(exp1)

        # 5. Seed AEGISSTOR Omega fleet topology, outcome ledger, and governance
        FleetTopologyService.seed_fleet_topology_if_missing(db)
        OutcomeLedgerService.seed_ledger_if_missing(db)
        ModelGovernanceService.seed_governance_if_missing(db)

        # 6. Seed AEGISSTOR Jurassic Resilience Lab initial presets & experiment runs
        ExperimentRunner.seed_initial_experiments_if_missing(db)

        # 7. Seed AEGISSTOR Phoenix safety policies, standard runbooks, and correlate incidents
        PolicyGateway.get_active_policy(db)
        RunbookEngine.seed_standard_runbooks(db)
        IncidentCorrelationEngine.scan_and_create_incidents(db)

        # 8. Seed AEGISSTOR Atlas reality calibration configs, action evidence & VOE gaps
        cfg = DigitalTwinCalibrationEngine.get_or_create_default_config(db, "vol-nvme-tier1-db")
        DigitalTwinCalibrationEngine.run_calibration(db, cfg.id)
        ActionEffectEvidenceService.seed_initial_evidence_if_missing(db, "vol-nvme-tier1-db")
        ValueOfExperimentPlanner.seed_initial_gaps_if_missing(db, "vol-nvme-tier1-db")
        FidelityAssessor.evaluate_device_fidelity(db, "vol-nvme-tier1-db")

        # 9. Seed AEGISSTOR Oracle workload catalog, bottleneck cases, and initial hypotheses
        WorkloadCatalogService.seed_workloads_if_missing(db)
        BottleneckForensicsEngine.seed_initial_bottleneck_cases_if_missing(db)
        HypothesisManager.seed_initial_hypotheses_if_missing(db)

        # 10. Seed AEGISSTOR Gauntlet Validation & Examiner Workbench (Prompt 18.0)
        GauntletService.seed_initial_catalog(db)

        # 11. Seed AEGISSTOR Sovereign Federated Intelligence (Prompt 19.0)
        SovereignService.seed_initial_sites(db)

        # Ensure reviewer/examiner account exists
        examiner_user = db.query(User).filter(User.username == "examiner").first()
        if not examiner_user:
            ex_user = User(
                id="usr-system-examiner",
                username="examiner",
                email="examiner@review.internal",
                hashed_password=hash_password("examiner123"),
                role="REVIEWER",
                is_active=True
            )
            db.add(ex_user)
            db.flush()

        db.commit()
        logger.info("Demo database verified/seeded idempotently.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_safety()
    initialize_database_and_seed_demo()
    yield
    try:
        from app.realtime.event_bus import realtime_manager
        await realtime_manager.shutdown()
    except Exception as exc:
        logger.warning("Realtime shutdown warning: %s", exc)
    try:
        engine.dispose()
    except Exception as exc:
        logger.warning("Database engine dispose warning: %s", exc)

app = FastAPI(
    title="AEGISSTOR — Storage Resilience Intelligence Platform",
    description="Predictive Storage Capacity and Performance Management Using Machine Learning",
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

# Dynamic CORS Configuration with strict production enforcement
cors_env = settings.CORS_ALLOWED_ORIGINS if hasattr(settings, "CORS_ALLOWED_ORIGINS") else "*"
configured_origins = [o.strip() for o in cors_env.split(",") if o.strip()] if cors_env != "*" else []
is_prod = settings.ENVIRONMENT == "production"

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins if configured_origins else ([] if is_prod else ["*"]),
    allow_origin_regex=None if (is_prod and configured_origins) else r"^https?://(localhost|127\.0\.0\.1|.*\.vercel\.app|.*\.onrender\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from collections import defaultdict, deque
import os
from fastapi.responses import JSONResponse

_RATE_LIMIT_BUCKETS = defaultdict(deque)
app.state.rate_limit_max = int(os.getenv("AEGISSTOR_RATE_LIMIT_PER_MIN", "600"))
app.state.rate_limit_buckets = _RATE_LIMIT_BUCKETS


@app.middleware("http")
async def request_tracing_and_security_middleware(request: Request, call_next):
    """
    Injects request tracing headers (X-Request-ID, X-Process-Time-Ms),
    enforces configurable sliding-window API rate limits (X-RateLimit-Remaining),
    enterprise HTTP security headers, and structured timing logs.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()

    # Enforce maximum request payload size
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(
                    status_code=413,
                    headers={"X-Request-ID": request_id},
                    content={
                        "detail": f"Request payload exceeds limit of {settings.MAX_REQUEST_BODY_BYTES} bytes."
                    },
                )
        except ValueError:
            pass

    # Sliding-window 60s rate limit check (skipped only for root/health liveness probes)
    client_key = request.headers.get("X-API-Key") or (request.client.host if request.client else "unknown")
    limit_max = int(getattr(app.state, "rate_limit_max", 600))
    now_ts = time.time()
    remaining = limit_max
    if limit_max > 0 and request.url.path not in {"/health", "/health/live", "/api/v1/health", "/api/v1/health/live"}:
        bucket = _RATE_LIMIT_BUCKETS[client_key]
        cutoff_ts = now_ts - 60.0
        while bucket and bucket[0] < cutoff_ts:
            bucket.popleft()
        if len(bucket) >= limit_max:
            return JSONResponse(
                status_code=429,
                headers={
                    "X-Request-ID": request_id,
                    "X-RateLimit-Limit": str(limit_max),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
                content={"detail": "Rate limit exceeded. Retry after 60 seconds."},
            )
        bucket.append(now_ts)
        remaining = max(0, limit_max - len(bucket))

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"[{request_id[:8]}] Unhandled application error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            headers={
                "X-Request-ID": request_id,
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY"
            },
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal error occurred. Please contact storage resilience support with reference ID.",
                    "request_id": request_id,
                    "timestamp": time.time()
                }
            }
        )
    
    process_time = (time.perf_counter() - start_time) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    response.headers["X-RateLimit-Limit"] = str(limit_max)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    # Enterprise Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https: wss: http: ws:;"
    if settings.ENVIRONMENT in ("staging", "production") or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

    
    if request.url.path not in ["/metrics", "/api/v1/health"]:
        logger.info(
            f"[{request_id[:8]}] {request.method} {request.url.path} -> {response.status_code} ({process_time:.1f}ms)"
        )
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(api_router, prefix="/api", include_in_schema=False)

@app.get("/")
def root():
    return {
        "platform": settings.PROJECT_NAME,
        "academic_title": "Predictive Storage Capacity and Performance Management Using Machine Learning",
        "version": settings.PROJECT_VERSION,
        "mode": settings.OPERATING_MODE,
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR
    }

@app.get("/health")
def root_health():
    return {
        "status": "ok",
        "platform": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "environment": settings.ENVIRONMENT,
        "mode": settings.OPERATING_MODE,
        "timestamp": time.time()
    }


from app.api.v1 import endpoints_health as _health_ep
app.add_api_route("/health/live", _health_ep.health_live, methods=["GET"], include_in_schema=False)
app.add_api_route("/health/ready", _health_ep.health_ready, methods=["GET"], include_in_schema=False)
app.add_api_route("/health/database", _health_ep.health_database, methods=["GET"], include_in_schema=False)
app.add_api_route("/health/worker", _health_ep.health_worker, methods=["GET"], include_in_schema=False)
app.add_api_route("/health/realtime", _health_ep.health_realtime, methods=["GET"], include_in_schema=False)
