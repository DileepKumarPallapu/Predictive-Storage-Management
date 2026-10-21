from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.config import settings
from app.schemas.payloads import SystemHealth, ModeChangeRequest
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/health", response_model=SystemHealth)
def get_system_health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return SystemHealth(
        status="ok" if db_status == "connected" else "degraded",
        version=settings.PROJECT_VERSION,
        mode=settings.OPERATING_MODE,
        database=db_status,
        collector_status="healthy",
        models_loaded=3,
        timestamp=datetime.now(timezone.utc)
    )

@router.get("/system/mode")
def get_operating_mode():
    return {
        "mode": settings.OPERATING_MODE,
        "shadow_mode_enabled": settings.SHADOW_MODE_ENABLED,
        "description": "Demo mode uses deterministic synthetic telemetry; Replay mode processes historical benchmark traces; Live mode reads local host OS metrics safely."
    }

@router.post("/system/mode")
def set_operating_mode(payload: ModeChangeRequest, db: Session = Depends(get_db)):
    valid_modes = ["demo", "replay", "live"]
    if payload.mode.lower() not in valid_modes:
        return {"error": f"Invalid mode. Choose one of {valid_modes}"}
    
    prev_mode = settings.OPERATING_MODE
    settings.OPERATING_MODE = payload.mode.lower()

    AuditService.log_event(
        db=db,
        action="CHANGE_MODE",
        target_type="SYSTEM",
        target_id="operating_mode",
        details={"previous": prev_mode, "new": settings.OPERATING_MODE}
    )

    return {
        "message": f"Operating mode switched to {settings.OPERATING_MODE}",
        "mode": settings.OPERATING_MODE
    }
