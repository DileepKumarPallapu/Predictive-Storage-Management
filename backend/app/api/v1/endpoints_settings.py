import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import AuditLog, ApplicationSetting, User
from app.schemas.payloads import AuditItem
from app.config import settings
from app.auth.security import require_role
from app.auth.permissions import require_permission, get_effective_permissions
from app.services.audit_service import AuditService

router = APIRouter()

DEFAULT_SETTINGS_MAP: Dict[str, Dict[str, Any]] = {
    "capacity_thresholds": {
        "default_warning_pct": 80.0,
        "default_critical_pct": 90.0,
    },
    "risk_thresholds": {
        "runway_warning_days": 30.0,
        "runway_critical_days": 14.0,
        "max_acceptable_latency_ms": 20.0,
    },
    "forecast_settings": {
        "default_horizon_days": 30,
        "min_training_records": 48,
    },
    "data_retention_settings": {
        "retention_days": 365,
        "stale_telemetry_hours": 24.0,
    },
    "approval_policy": {
        "operator_can_self_approve": False,
    },
}


def _load_persisted_settings(db: Session) -> Dict[str, Dict[str, Any]]:
    stored = {row.key: json.loads(row.value_json) for row in db.query(ApplicationSetting).all()}
    merged = {}
    for k, default_val in DEFAULT_SETTINGS_MAP.items():
        merged[k] = {**default_val, **stored.get(k, {})}
    return merged


class SettingsUpdateRequest(BaseModel):
    capacity_thresholds: Optional[Dict[str, Any]] = None
    risk_thresholds: Optional[Dict[str, Any]] = None
    forecast_settings: Optional[Dict[str, Any]] = None
    data_retention_settings: Optional[Dict[str, Any]] = None
    approval_policy: Optional[Dict[str, Any]] = None


@router.get("/settings")
def get_system_settings(
    current_user: User = Depends(require_permission("settings.read")),
    db: Session = Depends(get_db),
):
    persisted = _load_persisted_settings(db)
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
        "nominal_interval_coverage": settings.NOMINAL_COVERAGE,
        **persisted,
    }


@router.put("/settings")
def update_system_settings(
    payload: SettingsUpdateRequest,
    admin_user: User = Depends(require_permission("settings.update")),
    db: Session = Depends(get_db)
):
    """Updates and persists global capacity, risk, forecast, approval policy, and data retention settings (Admin only)."""
    if payload.capacity_thresholds:
        w = float(payload.capacity_thresholds.get("default_warning_pct", 80.0))
        c = float(payload.capacity_thresholds.get("default_critical_pct", 90.0))
        if w <= 0 or c > 100 or w >= c:
            raise HTTPException(status_code=400, detail="default_warning_pct must be > 0 and < default_critical_pct <= 100")

    if payload.data_retention_settings:
        ret = int(payload.data_retention_settings.get("retention_days", 365))
        if ret < 7:
            raise HTTPException(status_code=400, detail="retention_days must be at least 7 days")

    current = _load_persisted_settings(db)
    updated_keys = []
    for section in ("capacity_thresholds", "risk_thresholds", "forecast_settings", "data_retention_settings", "approval_policy"):
        patch_data = getattr(payload, section)
        if patch_data is not None:
            merged_val = {**current[section], **patch_data}
            row = db.query(ApplicationSetting).filter(ApplicationSetting.key == section).first()
            if not row:
                row = ApplicationSetting(
                    key=section,
                    value_json=json.dumps(merged_val),
                    category=section,
                    updated_by=admin_user.username,
                )
                db.add(row)
            else:
                row.value_json = json.dumps(merged_val)
                row.version = (getattr(row, "version", 1) or 1) + 1
                row.updated_by = admin_user.username
                row.updated_at = datetime.now(timezone.utc)
            updated_keys.append(section)

    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="settings.updated",
        resource_type="settings",
        resource_id="global_application_settings",
        actor_user=admin_user,
        changed_fields=updated_keys,
        payload={"updated_sections": updated_keys},
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    AuditService.log_event(
        db=db,
        action="UPDATE_SETTINGS",
        target_type="SETTINGS",
        target_id="global_application_settings",
        user=admin_user.username,
        details={"updated_sections": updated_keys}
    )
    return get_system_settings(current_user=admin_user, db=db)


@router.get("/audit", response_model=List[AuditItem])
def get_audit_trail(
    current_user: User = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
):
    perms = get_effective_permissions(db, current_user.role)
    can_export_all = "audit.export" in perms or current_user.role in {"ADMIN", "AUDITOR"}
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if not can_export_all:
        operational_targets = {
            "DEVICE", "INGESTION", "MODEL", "FORECAST", "ALERT",
            "SCENARIO", "RECOMMENDATION", "REPORT", "CONNECTOR", "TELEMETRY",
        }
        query = query.filter(
            (AuditLog.user == current_user.username)
            | (AuditLog.target_type.in_(operational_targets))
        )
    logs = query.limit(100).all()
    results = []
    for l in logs:
        raw_details = json.loads(l.details_json) if l.details_json else {}
        details = raw_details if isinstance(raw_details, dict) else {"message": str(raw_details)}
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


@router.delete("/audit")
@router.delete("/audit/{log_id}")
def block_audit_deletion(
    log_id: Optional[int] = None,
    current_user: User = Depends(require_permission("audit.read")),
    db: Session = Depends(get_db),
):
    AuditService.log_event(
        db=db,
        action="AUDIT_TAMPER_ATTEMPT_BLOCKED",
        target_type="AUDIT_LOG",
        target_id=str(log_id or "all"),
        user=current_user.username,
        outcome="DENIED",
        details={"reason": "Audit records are immutable and append-only"},
    )
    raise HTTPException(status_code=403, detail="Audit logs are immutable and cannot be deleted or disabled.")
