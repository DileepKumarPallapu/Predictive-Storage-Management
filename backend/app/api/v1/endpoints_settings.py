import json
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import AuditLog
from app.schemas.payloads import AuditItem
from app.config import settings

router = APIRouter()

@router.get("/settings")
def get_system_settings():
    return {
        "project_name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "operating_mode": settings.OPERATING_MODE,
        "shadow_mode_enabled": settings.SHADOW_MODE_ENABLED,
        "hard_safety_envelope": {
            "enforce_critical_capacity_ceiling": True,
            "max_migration_latency_overhead_pct": 35.0,
            "max_migration_duration_hours": 6.0,
            "prohibit_destructive_host_ops": True
        },
        "default_forecast_horizon_hours": settings.DEFAULT_FORECAST_HORIZON_HOURS,
        "nominal_interval_coverage": settings.NOMINAL_COVERAGE
    }

@router.get("/audit", response_model=List[AuditItem])
def get_audit_trail(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    results = []
    for l in logs:
        details = json.loads(l.details_json) if l.details_json else {}
        results.append(AuditItem(
            id=l.id,
            timestamp=l.timestamp,
            user=l.user,
            action=l.action,
            target_type=l.target_type,
            target_id=l.target_id,
            details=details
        ))
    return results
