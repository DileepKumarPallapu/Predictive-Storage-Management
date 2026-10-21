import logging
import time
import uuid
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aegisstor")

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

            # Check if telemetry already seeded for this device
            tel_count = db.query(Telemetry).filter(Telemetry.device_id == dev_id).count()
            if tel_count < 100:
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

# Run idempotent schema initialization and demo seed immediately on startup
initialize_database_and_seed_demo()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
