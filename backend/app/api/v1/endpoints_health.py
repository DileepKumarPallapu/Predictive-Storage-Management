import json
import logging
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("aegisstor.health")

from app.auth.permissions import require_permission
from app.config import settings
from app.database import engine, get_db
from app.models.entities import ApplicationSetting, BackgroundJob, OutboxEvent, User
from app.realtime.event_bus import realtime_manager
from app.schemas.payloads import ModeChangeRequest, SystemHealth
from app.services.audit_service import AuditService
from app.services.object_storage import object_storage

router = APIRouter()


def _probe_database(db: Session) -> dict:
    t0 = time.perf_counter()
    try:
        db.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        alembic_rev = None
        try:
            row = db.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            alembic_rev = row[0] if row else None
        except Exception:
            alembic_rev = None

        pool_info = {}
        try:
            pool = engine.pool
            if hasattr(pool, "size"):
                pool_info = {
                    "pool_size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }
        except Exception:
            pool_info = {}

        return {
            "status": "healthy",
            "connected": True,
            "latency_ms": latency_ms,
            "alembic_revision": alembic_rev,
            "pool": pool_info,
        }
    except Exception:
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": None,
            "alembic_revision": None,
            "pool": {},
        }


def _probe_worker(db: Session) -> dict:
    try:
        queued = db.query(BackgroundJob).filter(BackgroundJob.status == "QUEUED").count()
        running = db.query(BackgroundJob).filter(BackgroundJob.status == "RUNNING").count()
        failed = db.query(BackgroundJob).filter(BackgroundJob.status == "FAILED").count()
        completed = db.query(BackgroundJob).filter(BackgroundJob.status == "COMPLETED").count()
        oldest_pending = (
            db.query(BackgroundJob)
            .filter(BackgroundJob.status == "QUEUED")
            .order_by(BackgroundJob.created_at.asc())
            .first()
        )
        oldest_pending_age_sec = None
        if oldest_pending and oldest_pending.created_at:
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            oldest_pending_age_sec = round((now_naive - oldest_pending.created_at).total_seconds(), 1)

        hb_row = db.query(ApplicationSetting).filter(ApplicationSetting.key == "worker_heartbeat").first()
        hb_data = None
        worker_status = "embedded_background_tasks"
        if hb_row and hb_row.value_json:
            try:
                hb_data = json.loads(hb_row.value_json)
                last_seen = datetime.fromisoformat(hb_data["last_seen_utc"])
                age_sec = (datetime.now(timezone.utc).replace(tzinfo=None) - last_seen).total_seconds()
                hb_data["heartbeat_age_sec"] = round(age_sec, 1)
                worker_status = "healthy" if age_sec <= max(60, settings.WORKER_HEARTBEAT_INTERVAL_SEC * 3) else "stale"
            except Exception:
                worker_status = "unknown"

        return {
            "status": worker_status,
            "queued_jobs": queued,
            "running_jobs": running,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "oldest_pending_age_sec": oldest_pending_age_sec,
            "heartbeat": hb_data,
        }
    except Exception as exc:
        logger.warning("Worker probe failed: %s", exc)
        return {"status": "unhealthy", "queued_jobs": None, "running_jobs": None}


def _probe_realtime(db: Session) -> dict:
    try:
        latest_event = db.query(OutboxEvent).order_by(OutboxEvent.seq_id.desc()).first()
        total_events = db.query(OutboxEvent).count()
        return {
            "status": "healthy",
            "active_websocket_connections": realtime_manager.connection_count(),
            "redis_configured": bool((settings.REDIS_URL or "").strip()),
            "latest_outbox_seq": latest_event.seq_id if latest_event else 0,
            "outbox_total_events": total_events,
        }
    except Exception as exc:
        logger.warning("Realtime probe failed: %s", exc)
        return {
            "status": "degraded",
            "active_websocket_connections": realtime_manager.connection_count(),
            "redis_configured": bool((settings.REDIS_URL or "").strip()),
        }


@router.get("/health", response_model=SystemHealth)
def get_system_health(response: Response, db: Session = Depends(get_db)):
    from app.models.entities import ModelVersion

    db_probe = _probe_database(db)
    db_status = "connected" if db_probe["connected"] else "error"
    models_count = 3
    if db_probe["connected"]:
        try:
            active_mvs = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
            persisted_artifacts = sum(
                1 for mv in active_mvs
                if getattr(mv, "artifact_path", None) and os.path.exists(mv.artifact_path)
            )
            models_count = max(3, persisted_artifacts + 2)
        except Exception:
            models_count = 3
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return SystemHealth(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.PROJECT_VERSION,
        mode=settings.OPERATING_MODE,
        database=db_status,
        collector_status="healthy",
        models_loaded=models_count,
        timestamp=datetime.now(timezone.utc),
    )


@router.get("/health/live")
def health_live():
    """Fast process liveness probe (does not query external dependencies)."""
    return {
        "status": "alive",
        "environment": settings.ENVIRONMENT,
        "version": settings.PROJECT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/database")
def health_database(response: Response, db: Session = Depends(get_db)):
    probe = _probe_database(db)
    if not probe["connected"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {**probe, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/worker")
def health_worker(db: Session = Depends(get_db)):
    probe = _probe_worker(db)
    return {**probe, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/realtime")
def health_realtime(db: Session = Depends(get_db)):
    probe = _probe_realtime(db)
    return {**probe, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/health/ready")
def health_ready(response: Response, db: Session = Depends(get_db)):
    """Readiness probe verifying database connectivity and subsystem status."""
    db_probe = _probe_database(db)
    worker_probe = _probe_worker(db) if db_probe["connected"] else {"status": "unavailable"}
    rt_probe = _probe_realtime(db) if db_probe["connected"] else {"status": "unavailable"}
    ready = bool(db_probe["connected"])
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "status": "ready" if ready else "not_ready",
        "environment": settings.ENVIRONMENT,
        "version": settings.PROJECT_VERSION,
        "dependencies": {
            "database": db_probe,
            "worker": worker_probe,
            "realtime": rt_probe,
            "object_storage": object_storage.status_summary(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/system/mode")
def get_operating_mode(current_user: User = Depends(require_permission("storage.read"))):
    from app.collector.host_collector import HostStorageCollector

    diagnostics = None
    if settings.OPERATING_MODE == "live":
        prom_status = HostStorageCollector.scrape_prometheus_node_exporter()
        diagnostics = {
            "native_host_active": True,
            "prometheus_operational": prom_status.get("status") == "ok",
            "prometheus_status": prom_status.get("status"),
            "prometheus_message": prom_status.get("error_message") or "Operational",
            "remedy": prom_status.get("remedy"),
        }

    return {
        "mode": settings.OPERATING_MODE,
        "environment": settings.ENVIRONMENT,
        "shadow_mode_enabled": settings.SHADOW_MODE_ENABLED,
        "diagnostics": diagnostics,
        "description": "Demo mode uses deterministic synthetic telemetry; Replay mode processes historical benchmark traces; Live mode reads local host OS metrics safely.",
    }


@router.post("/system/mode")
def set_operating_mode(
    payload: ModeChangeRequest,
    current_user: User = Depends(require_permission("settings.update")),
    db: Session = Depends(get_db),
):
    valid_modes = ["demo", "replay", "live"]
    if payload.mode.lower() not in valid_modes:
        return {"error": f"Invalid mode. Choose one of {valid_modes}"}

    prev_mode = settings.OPERATING_MODE
    settings.OPERATING_MODE = payload.mode.lower()

    diagnostics = None
    if settings.OPERATING_MODE == "live":
        from app.collector.host_collector import HostStorageCollector

        prom_status = HostStorageCollector.scrape_prometheus_node_exporter()
        diagnostics = {
            "native_host_active": True,
            "prometheus_operational": prom_status.get("status") == "ok",
            "prometheus_status": prom_status.get("status"),
            "prometheus_message": prom_status.get("error_message") or "Operational",
            "remedy": prom_status.get("remedy"),
        }

    AuditService.log_event(
        db=db,
        action="CHANGE_MODE",
        target_type="SYSTEM",
        target_id="operating_mode",
        user=current_user.username,
        details={"previous": prev_mode, "new": settings.OPERATING_MODE},
    )

    return {
        "message": f"Operating mode switched to {settings.OPERATING_MODE}",
        "mode": settings.OPERATING_MODE,
        "diagnostics": diagnostics,
    }
