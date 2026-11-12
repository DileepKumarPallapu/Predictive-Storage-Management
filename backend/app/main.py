import logging
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

    # Register Control Plane action definitions on every fresh deployment.
    # This is idempotent reference data only; it does not seed users/connectors/telemetry.
    from app.services.control_plane_bootstrap import ensure_control_plane_action_definitions
    cp_db = SessionLocal()
    try:
        ensure_control_plane_action_definitions(cp_db)
    finally:
        cp_db.close()

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
                if "organization_id" not in user_cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN organization_id VARCHAR(64) DEFAULT 'org-primary-enterprise'"))
            if "audit_logs" in inspector.get_table_names():
                audit_cols = [c["name"] for c in inspector.get_columns("audit_logs")]
                if "organization_id" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN organization_id VARCHAR(64) DEFAULT 'org-primary-enterprise'"))
                if "client_ip" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN client_ip VARCHAR(64) DEFAULT '127.0.0.1'"))
                if "prev_hash" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN prev_hash VARCHAR(64)"))
                if "entry_hash" not in audit_cols:
                    conn.execute(text("ALTER TABLE audit_logs ADD COLUMN entry_hash VARCHAR(64)"))
            if "recommendations" in inspector.get_table_names():
                rec_cols = [c["name"] for c in inspector.get_columns("recommendations")]
                if "details_json" not in rec_cols:
                    conn.execute(text("ALTER TABLE recommendations ADD COLUMN details_json TEXT DEFAULT '{}'"))
            conn.commit()


    except Exception as e:
        logger.warning(f"Column migration check note: {e}")

    db = SessionLocal()
    try:
        # 0. Ensure default administrative and operator accounts exist
        default_admin = db.query(User).filter(User.username == "admin").first()
        if not default_admin:
            admin_user = User(
                id="usr-system-admin",
                username="admin",
                email="admin@aegisstor.internal",
                hashed_password=hash_password("admin123"),
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            db.flush()

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
    initialize_database_and_seed_demo()
    yield

app = FastAPI(
    title="AEGISSTOR — Storage Resilience Intelligence Platform",
    description="Predictive Storage Capacity and Performance Management Using Machine Learning",
    version=settings.PROJECT_VERSION,
    lifespan=lifespan
)

# Dynamic CORS Configuration with support for local, Vercel deployments and custom origins
cors_env = settings.model_dump().get("CORS_ALLOWED_ORIGINS", "*") if hasattr(settings, "CORS_ALLOWED_ORIGINS") else "*"
configured_origins = [o.strip() for o in cors_env.split(",") if o.strip()] if cors_env != "*" else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins if configured_origins else ["*"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|.*\.vercel\.app|.*\.onrender\.com)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse

@app.middleware("http")
async def request_tracing_and_security_middleware(request: Request, call_next):
    """
    Injects request tracing headers (X-Request-ID, X-Process-Time-Ms),
    enforces enterprise HTTP security headers, and provides structured timing logs.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    
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
    
    # Enterprise Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' http: ws:;"

    
    if request.url.path not in ["/metrics", "/api/v1/health"]:
        logger.info(
            f"[{request_id[:8]}] {request.method} {request.url.path} -> {response.status_code} ({process_time:.1f}ms)"
        )
    return response

app.include_router(api_router, prefix=settings.API_V1_STR)

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
        "mode": settings.OPERATING_MODE,
        "timestamp": time.time()
    }
