import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import hash_token, require_role
from app.auth.permissions import require_permission, get_effective_permissions
from app.collector.connector_registry import ConnectorRegistry
from app.database import get_db
from app.models.entities import (
    ApiKey,
    DataQualityResult,
    Device,
    IngestionJob,
    ReportHistory,
    Telemetry,
    TelemetryConnector,
    User,
)
from app.services.audit_service import AuditService
from app.api.v1.endpoints_settings import _load_persisted_settings
from app.config import settings
import math

router = APIRouter()


class ConnectorCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    connector_type: str = Field(..., description="LINUX_HOST, PROMETHEUS, CSV_HISTORICAL, HTTP_API, POSTGRESQL, MYSQL, MARIADB, MSSQL, or ORACLE")
    endpoint_url: Optional[str] = None
    target_storage_id: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class ConnectorCollectRequest(BaseModel):
    persist_to_storage_id: Optional[str] = None
    mountpoint_filter: Optional[str] = None


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    role: str = Field(default="OPERATOR", pattern="^(ADMIN|OPERATOR|AUDITOR|VIEWER)$")


class RetentionRunRequest(BaseModel):
    retention_days: Optional[int] = Field(default=None, ge=1, le=3650)
    dry_run: bool = False


@router.get("/connectors/types")
def list_connector_types(current_user: User = Depends(require_permission("integrations.read"))):
    return {
        "status": "ok",
        "permission_mode": "READ_ONLY",
        "supported_types": ConnectorRegistry.list_supported_types(),
    }


class ConnectorUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=128)
    endpoint_url: Optional[str] = None
    target_storage_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None


class SyntheticDemoRequest(BaseModel):
    storage_id: str
    hours: int = Field(default=96, ge=24, le=720)
    regime: str = Field(default="STABLE_GROWTH", description="STABLE_GROWTH, ACCELERATING_GROWTH, PERIODIC_SEASONAL, SUDDEN_BURST, DECLINING_CONSUMPTION")


@router.get("/connectors")
def list_connectors(
    current_user: User = Depends(require_permission("integrations.read")),
    db: Session = Depends(get_db),
):
    rows = db.query(TelemetryConnector).order_by(TelemetryConnector.created_at.desc()).all()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    items = []
    for c in rows:
        cfg = json.loads(c.config_json or "{}")
        # Never expose raw auth credentials in list responses
        redacted_cfg = {
            k: (
                "***REDACTED***"
                if any(s in k.lower() for s in ("password", "token", "secret", "dsn", "connection_string", "api_key"))
                else v
            )
            for k, v in cfg.items()
        }
        jobs = (
            db.query(IngestionJob)
            .filter(IngestionJob.filename == c.name)
            .order_by(IngestionJob.created_at.desc())
            .limit(20)
            .all()
        )
        metrics_received = sum(j.accepted_rows for j in jobs)
        failed_jobs = [j for j in jobs if j.status == "FAILED"]
        data_delay_seconds = (
            round(max(0.0, (now_naive - c.last_sync_at.replace(tzinfo=None)).total_seconds()), 1)
            if c.last_sync_at
            else None
        )
        freq_sec = int(cfg.get("collection_frequency_seconds", 300))
        items.append({
            "id": c.id,
            "name": c.name,
            "connector_type": c.connector_type,
            "endpoint_url": c.endpoint_url,
            "target_storage_id": c.target_storage_id,
            "config": redacted_cfg,
            "is_enabled": c.is_enabled,
            "last_status": c.last_status,
            "last_error": c.last_error,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "last_failure_at": failed_jobs[0].created_at.isoformat() if failed_jobs and failed_jobs[0].created_at else None,
            "data_delay_seconds": data_delay_seconds,
            "collection_frequency_seconds": freq_sec,
            "metrics_received": metrics_received,
            "error_logs": [{"job_id": j.id, "errors": json.loads(j.errors_json or "[]"), "created_at": j.created_at.isoformat() if j.created_at else None} for j in failed_jobs[:5]],
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"connectors": items, "count": len(items)}


@router.post("/connectors")
def register_connector(
    payload: ConnectorCreateRequest,
    current_user: User = Depends(require_permission("integrations.configure")),
    db: Session = Depends(get_db),
):
    ctype = payload.connector_type.upper()
    try:
        ConnectorRegistry.get_adapter(ctype)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if payload.target_storage_id:
        dev = db.query(Device).filter(Device.id == payload.target_storage_id).first()
        if not dev:
            raise HTTPException(status_code=404, detail=f"Target storage '{payload.target_storage_id}' not found")

    cfg = dict(payload.config)
    if payload.endpoint_url:
        cfg["endpoint_url"] = payload.endpoint_url
    if payload.target_storage_id:
        cfg["target_storage_id"] = payload.target_storage_id

    conn = TelemetryConnector(
        id=f"conn-{uuid.uuid4().hex[:10]}",
        name=payload.name,
        connector_type=ctype,
        endpoint_url=payload.endpoint_url,
        config_json=json.dumps(cfg),
        target_storage_id=payload.target_storage_id,
        is_enabled=payload.is_enabled,
        last_status="CONFIGURED",
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    AuditService.log_event(
        db=db,
        action="CONNECTOR_REGISTERED",
        target_type="CONNECTOR",
        target_id=conn.id,
        user=current_user.username,
        details={"connector_type": ctype, "name": payload.name},
    )

    return {
        "status": "created",
        "connector": {
            "id": conn.id,
            "name": conn.name,
            "connector_type": conn.connector_type,
            "endpoint_url": conn.endpoint_url,
            "target_storage_id": conn.target_storage_id,
            "is_enabled": conn.is_enabled,
            "last_status": conn.last_status,
        },
    }


@router.post("/connectors/{connector_id}/test")
def test_connector(
    connector_id: str,
    current_user: User = Depends(require_permission("telemetry.collect")),
    db: Session = Depends(get_db),
):
    conn = db.query(TelemetryConnector).filter(TelemetryConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")

    adapter = ConnectorRegistry.get_adapter(conn.connector_type)
    cfg = json.loads(conn.config_json or "{}")
    if conn.endpoint_url and "endpoint_url" not in cfg:
        cfg["endpoint_url"] = conn.endpoint_url

    result = adapter.test_connection(cfg)
    raw_status = result.get("status")
    if raw_status in {"CONNECTED", "READY"}:
        conn.last_status = "CONNECTED"
    elif raw_status in {"NOT_CONFIGURED", "DRIVER_MISSING"}:
        conn.last_status = raw_status
    else:
        conn.last_status = "ERROR"
    conn.last_error = result.get("error")
    db.commit()

    return {"connector_id": conn.id, "connector_type": conn.connector_type, "last_status": conn.last_status, "result": result}


@router.post("/connectors/{connector_id}/collect")
def collect_from_connector(
    connector_id: str,
    payload: ConnectorCollectRequest = ConnectorCollectRequest(),
    current_user: User = Depends(require_permission("telemetry.collect")),
    db: Session = Depends(get_db),
):
    conn = db.query(TelemetryConnector).filter(TelemetryConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")
    if not conn.is_enabled:
        raise HTTPException(status_code=400, detail="Connector is disabled")

    adapter = ConnectorRegistry.get_adapter(conn.connector_type)
    cfg = json.loads(conn.config_json or "{}")
    if conn.endpoint_url and "endpoint_url" not in cfg:
        cfg["endpoint_url"] = conn.endpoint_url

    result = adapter.collect(cfg)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    conn.last_sync_at = now_utc
    if result.get("status") == "CONNECTION_FAILED":
        conn.last_status = "ERROR"
        conn.last_error = result.get("error")
        db.commit()
        return {"connector_id": conn.id, "persisted_count": 0, "result": result}

    conn.last_status = "CONNECTED"
    conn.last_error = None

    target_storage_id = payload.persist_to_storage_id or conn.target_storage_id
    persisted_count = 0
    if target_storage_id and result.get("volumes"):
        device = db.query(Device).filter(Device.id == target_storage_id).first()
        if not device:
            raise HTTPException(status_code=404, detail=f"Target storage '{target_storage_id}' not found")

        volumes = result["volumes"]
        if payload.mountpoint_filter:
            matched = [v for v in volumes if v.get("mountpoint") == payload.mountpoint_filter]
            volumes = matched or volumes[:1]
        else:
            volumes = volumes[:1]

        existing_ts = {
            (r[0].replace(tzinfo=None) if r[0].tzinfo else r[0]).replace(microsecond=0)
            for r in db.query(Telemetry.timestamp).filter(Telemetry.device_id == target_storage_id).all()
            if r[0] is not None
        }
        for vol in volumes:
            ts_raw = datetime.fromisoformat(vol["timestamp"].replace("Z", "+00:00"))
            ts_naive = ts_raw.astimezone(timezone.utc).replace(tzinfo=None, microsecond=0)
            if ts_naive in existing_ts:
                continue
            total_b = int(vol["total_capacity_bytes"])
            used_b = int(vol["used_bytes"])
            free_b = int(vol["free_bytes"])
            util_pct = round((used_b / total_b) * 100.0, 2) if total_b > 0 else 0.0
            db.add(Telemetry(
                device_id=target_storage_id,
                timestamp=ts_naive,
                total_capacity_bytes=total_b,
                used_bytes=used_b,
                free_bytes=free_b,
                utilization_pct=util_pct,
                read_iops=vol.get("read_iops"),
                write_iops=vol.get("write_iops"),
                throughput_mb_s=vol.get("throughput_mbps"),
                latency_p95_ms=vol.get("read_latency_ms"),
                queue_depth=None,
                is_synthetic=False,
                source_label=vol.get("source_label") or conn.connector_type.lower(),
            ))
            existing_ts.add(ts_naive)
            device.last_telemetry_at = ts_naive
            persisted_count += 1

        if persisted_count > 0:
            job_id = f"job-{uuid.uuid4().hex[:10]}"
            db.add(IngestionJob(
                id=job_id,
                storage_id=target_storage_id,
                source_type=conn.connector_type,
                filename=conn.name,
                status="COMPLETED",
                total_rows=len(volumes),
                accepted_rows=persisted_count,
                rejected_rows=0,
                duplicate_rows=len(volumes) - persisted_count,
                uploaded_by=current_user.username,
            ))
            db.add(DataQualityResult(
                id=f"dq-{uuid.uuid4().hex[:10]}",
                storage_id=target_storage_id,
                ingestion_job_id=job_id,
                total_records_received=len(volumes),
                valid_records=persisted_count,
                rejected_records=0,
                duplicate_records=len(volumes) - persisted_count,
                data_completeness_pct=100.0,
                latest_telemetry_timestamp=now_utc,
                preprocessing_decisions_json=json.dumps(["REAL_CONNECTOR_READ_ONLY_INGESTION"]),
            ))

    db.commit()
    return {
        "connector_id": conn.id,
        "connector_type": conn.connector_type,
        "persisted_to_storage_id": target_storage_id,
        "persisted_count": persisted_count,
        "result": result,
    }


@router.get("/admin/api-keys")
def list_api_keys(
    current_user: User = Depends(require_permission("integrations.manage_secrets")),
    db: Session = Depends(get_db),
):
    keys = db.query(ApiKey).order_by(ApiKey.created_at.desc()).all()
    return {
        "api_keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "role": k.role,
                "organization_id": k.organization_id,
                "is_active": k.is_active,
                "created_by": k.created_by,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ]
    }


@router.post("/admin/api-keys")
def create_api_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(require_permission("integrations.manage_secrets")),
    db: Session = Depends(get_db),
):
    raw_key = f"aegis_{secrets.token_hex(20)}"
    key_prefix = raw_key[:14]
    rec = ApiKey(
        id=f"key-{uuid.uuid4().hex[:10]}",
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=hash_token(raw_key),
        role=payload.role,
        organization_id=current_user.organization_id,
        created_by=current_user.username,
        is_active=True,
    )
    db.add(rec)
    db.commit()

    AuditService.log_event(
        db=db,
        action="API_KEY_CREATED",
        target_type="API_KEY",
        target_id=rec.id,
        user=current_user.username,
        details={"name": payload.name, "role": payload.role, "prefix": key_prefix},
    )

    return {
        "id": rec.id,
        "name": rec.name,
        "key_prefix": key_prefix,
        "role": rec.role,
        "api_key": raw_key,
        "notice": "Store this API key securely now. It will not be shown again.",
    }


@router.delete("/admin/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_permission("integrations.manage_secrets")),
    db: Session = Depends(get_db),
):
    rec = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="API key not found")
    rec.is_active = False
    db.commit()

    AuditService.log_event(
        db=db,
        action="API_KEY_REVOKED",
        target_type="API_KEY",
        target_id=rec.id,
        user=current_user.username,
        details={"name": rec.name},
    )
    return {"status": "revoked", "id": key_id}


@router.post("/admin/retention/run")
def run_data_retention(
    payload: RetentionRunRequest = RetentionRunRequest(),
    current_user: User = Depends(require_permission("settings.update")),
    db: Session = Depends(get_db),
):
    persisted = _load_persisted_settings(db)
    retention_days = payload.retention_days or int(persisted.get("data_retention_settings", {}).get("retention_days", 365))
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=retention_days)

    # Preserve at least the latest telemetry row per device even if older than retention_days
    latest_ids = []
    for dev in db.query(Device.id).all():
        newest = (
            db.query(Telemetry.id)
            .filter(Telemetry.device_id == dev[0])
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if newest:
            latest_ids.append(newest[0])

    tel_q = db.query(Telemetry).filter(Telemetry.timestamp < cutoff)
    if latest_ids:
        tel_q = tel_q.filter(~Telemetry.id.in_(latest_ids))
    jobs_q = db.query(IngestionJob).filter(IngestionJob.created_at < cutoff)
    reports_q = db.query(ReportHistory).filter(ReportHistory.created_at < cutoff)

    expired_telemetry = tel_q.count()
    expired_jobs = jobs_q.count()
    expired_reports = reports_q.count()

    if not payload.dry_run:
        if expired_telemetry > 0:
            tel_q.delete(synchronize_session=False)
        if expired_jobs > 0:
            jobs_q.delete(synchronize_session=False)
        if expired_reports > 0:
            reports_q.delete(synchronize_session=False)
        db.commit()

        AuditService.log_event(
            db=db,
            action="RETENTION_CLEANUP_EXECUTED",
            target_type="SYSTEM",
            target_id="retention-policy",
            user=current_user.username,
            details={
                "retention_days": retention_days,
                "deleted_telemetry": expired_telemetry,
                "deleted_ingestion_jobs": expired_jobs,
                "deleted_reports": expired_reports,
            },
        )

    return {
        "status": "dry_run" if payload.dry_run else "completed",
        "retention_days": retention_days,
        "cutoff_utc": cutoff.isoformat(),
        "audit_logs_preserved": True,
        "deleted_telemetry_rows": 0 if payload.dry_run else expired_telemetry,
        "would_delete_telemetry_rows": expired_telemetry,
        "expired_ingestion_jobs": expired_jobs,
        "expired_reports": expired_reports,
    }


@router.put("/connectors/{connector_id}")
def update_connector(
    connector_id: str,
    payload: ConnectorUpdateRequest,
    current_user: User = Depends(require_permission("telemetry.configure")),
    db: Session = Depends(get_db),
):
    conn = db.query(TelemetryConnector).filter(TelemetryConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")
    if payload.config is not None:
        secret_keys = [
            k for k, v in payload.config.items()
            if v != "***REDACTED***"
            and any(tok in k.lower() for tok in ("password", "token", "secret", "api_key", "credential"))
        ]
        if secret_keys and "integrations.manage_secrets" not in get_effective_permissions(db, current_user.role):
            raise HTTPException(
                status_code=403,
                detail="Modifying connector secrets or credentials requires integrations.manage_secrets permission.",
            )
    if payload.name is not None:
        conn.name = payload.name
    if payload.endpoint_url is not None:
        conn.endpoint_url = payload.endpoint_url
    if payload.target_storage_id is not None:
        if payload.target_storage_id:
            dev = db.query(Device).filter(Device.id == payload.target_storage_id).first()
            if not dev:
                raise HTTPException(status_code=404, detail=f"Target storage '{payload.target_storage_id}' not found")
        conn.target_storage_id = payload.target_storage_id or None
    if payload.config is not None:
        existing_cfg = json.loads(conn.config_json or "{}")
        for k, v in payload.config.items():
            if v != "***REDACTED***":
                existing_cfg[k] = v
        conn.config_json = json.dumps(existing_cfg)
    if payload.is_enabled is not None:
        conn.is_enabled = payload.is_enabled
    db.commit()

    AuditService.log_event(
        db=db,
        action="CONNECTOR_UPDATED",
        target_type="CONNECTOR",
        target_id=conn.id,
        user=current_user.username,
        details={"is_enabled": conn.is_enabled, "target_storage_id": conn.target_storage_id},
    )
    return {"status": "updated", "connector_id": conn.id, "is_enabled": conn.is_enabled}


@router.delete("/connectors/{connector_id}")
def delete_connector(
    connector_id: str,
    current_user: User = Depends(require_permission("integrations.configure")),
    db: Session = Depends(get_db),
):
    conn = db.query(TelemetryConnector).filter(TelemetryConnector.id == connector_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connector not found")
    db.delete(conn)
    db.commit()
    AuditService.log_event(
        db=db,
        action="CONNECTOR_DELETED",
        target_type="CONNECTOR",
        target_id=connector_id,
        user=current_user.username,
        details={"name": conn.name},
    )
    return {"status": "deleted", "connector_id": connector_id}


@router.post("/telemetry/synthetic/generate")
def generate_synthetic_demo_telemetry(
    payload: SyntheticDemoRequest,
    current_user: User = Depends(require_permission("telemetry.ingest")),
    db: Session = Depends(get_db),
):
    """
    Explicitly labeled Synthetic Demonstration Telemetry Generator.
    Restricted exclusively to DEMO operating mode; never mixed into LIVE or REPLAY monitoring.
    All generated records carry is_synthetic=True and source_label='synthetic_demo_generator'.
    """
    if settings.OPERATING_MODE.lower() != "demo":
        raise HTTPException(
            status_code=403,
            detail="Synthetic telemetry generator is disabled outside 'demo' mode to preserve live/replay provenance.",
        )
    device = db.query(Device).filter(Device.id == payload.storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target storage resource not found")

    total_b = int(device.total_capacity_bytes)
    latest = db.query(Telemetry).filter(Telemetry.device_id == device.id).order_by(Telemetry.timestamp.desc()).first()
    base_pct = float(latest.utilization_pct) if latest else 45.0
    now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    existing_ts = {
        r[0].replace(tzinfo=None, microsecond=0)
        for r in db.query(Telemetry.timestamp).filter(Telemetry.device_id == device.id).all()
        if r[0] is not None
    }

    rows = []
    start = now - timedelta(hours=payload.hours - 1)
    for i in range(payload.hours):
        ts = start + timedelta(hours=i)
        if ts in existing_ts:
            continue
        frac = i / max(1, payload.hours - 1)
        if payload.regime == "ACCELERATING_GROWTH":
            pct = base_pct + 22.0 * (frac ** 2)
        elif payload.regime == "PERIODIC_SEASONAL":
            pct = base_pct + 4.5 * math.sin(2.0 * math.pi * i / 24.0)
        elif payload.regime == "SUDDEN_BURST":
            pct = base_pct + (2.0 * frac) + (12.0 if i >= payload.hours - 4 else 0.0)
        elif payload.regime == "DECLINING_CONSUMPTION":
            pct = max(10.0, base_pct - 15.0 * frac)
        else:
            pct = base_pct + 12.0 * frac
        pct = round(max(1.0, min(98.5, pct)), 2)
        used_b = int(total_b * (pct / 100.0))
        free_b = max(0, total_b - used_b)
        rows.append(Telemetry(
            device_id=device.id,
            timestamp=ts,
            total_capacity_bytes=total_b,
            used_bytes=used_b,
            free_bytes=free_b,
            utilization_pct=pct,
            read_iops=round(1400.0 + 350.0 * math.sin(i / 4.0), 1),
            write_iops=round(620.0 + 180.0 * math.cos(i / 5.0), 1),
            throughput_mb_s=round(240.0 + 60.0 * math.sin(i / 3.0), 1),
            latency_p95_ms=round(4.5 + (pct / 25.0), 2),
            queue_depth=4.0,
            is_synthetic=True,
            source_label="synthetic_demo_generator",
        ))
    if rows:
        db.bulk_save_objects(rows)
        device.last_telemetry_at = max(r.timestamp for r in rows)
    job_id = f"job-{uuid.uuid4().hex[:10]}"
    db.add(IngestionJob(
        id=job_id,
        storage_id=device.id,
        source_type="SYNTHETIC_DEMO",
        filename=f"synthetic_{payload.regime.lower()}",
        status="COMPLETED",
        total_rows=payload.hours,
        accepted_rows=len(rows),
        rejected_rows=0,
        duplicate_rows=payload.hours - len(rows),
        uploaded_by=current_user.username,
    ))
    db.commit()
    return {
        "status": "generated",
        "is_synthetic": True,
        "notice": "Clearly labeled synthetic demo telemetry generated for demonstration only.",
        "job_id": job_id,
        "storage_id": device.id,
        "regime": payload.regime,
        "inserted_records": len(rows),
    }
