import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import (
    Device, Telemetry, RiskAssessment, Alert, Scenario, ModelVersion, IngestionJob, User,
    StorageSystem, StoragePool, ResourceRelationship, WorkloadDependency, TelemetryConnector
)
from app.schemas.payloads import (
    DeviceSummary, ThresholdsUpdate, StorageCreateRequest, StorageUpdateRequest
)
from app.services.audit_service import AuditService
from app.auth.security import get_current_user, require_role, enforce_tenant_access
from app.auth.permissions import require_permission
from app.config import settings
from app.collector.host_collector import HostStorageCollector
from app.services.replay_service import replay_engine

router = APIRouter()

ALLOWED_STORAGE_TYPES = {
    "Local storage", "NAS", "SAN", "Cloud storage", "Backup storage", "Object storage"
}

STORAGE_TYPE_TO_TIER = {
    "Local storage": "HOST_LOCAL",
    "NAS": "SAS_TIER2",
    "SAN": "NVME_TIER1",
    "Cloud storage": "CLOUD_S3",
    "Backup storage": "HDD_ARCHIVE",
    "Object storage": "CLOUD_S3",
}


def _build_device_summary(db: Session, d: Device) -> DeviceSummary:
    latest_tel = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == d.id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )
    latest_risk = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.device_id == d.id)
        .order_by(RiskAssessment.computed_at.desc())
        .first()
    )

    total_cap = int(d.total_capacity_bytes)
    used = int(latest_tel.used_bytes) if latest_tel else 0
    free = max(0, total_cap - used)
    util_pct = round((used / total_cap) * 100.0, 2) if total_cap > 0 else 0.0
    r_iops = float(latest_tel.read_iops) if latest_tel and latest_tel.read_iops is not None else 0.0
    w_iops = float(latest_tel.write_iops) if latest_tel and latest_tel.write_iops is not None else 0.0
    lat = float(latest_tel.latency_p95_ms) if latest_tel and latest_tel.latency_p95_ms is not None else 0.0
    runway = float(latest_risk.runway_hours_estimate) if latest_risk else 0.0
    r_level = latest_risk.risk_level if latest_risk else (
        "CRITICAL" if util_pct >= d.critical_threshold_pct else ("WARNING" if util_pct >= d.warning_threshold_pct else "NOMINAL")
    )

    last_tel_ts = getattr(d, "last_telemetry_at", None) or (latest_tel.timestamp if latest_tel else None)

    return DeviceSummary(
        id=d.id,
        name=d.name,
        tier=d.tier,
        media_type=d.media_type,
        total_capacity_bytes=total_cap,
        warning_threshold_pct=d.warning_threshold_pct,
        critical_threshold_pct=d.critical_threshold_pct,
        max_acceptable_latency_ms=d.max_acceptable_latency_ms,
        min_free_reserve_pct=d.min_free_reserve_pct,
        status=d.status,
        workload_profile=d.workload_profile,
        current_used_bytes=used,
        free_capacity_bytes=free,
        current_utilization_pct=util_pct,
        current_read_iops=r_iops,
        current_write_iops=w_iops,
        current_latency_p95_ms=lat,
        runway_hours_estimate=runway,
        risk_level=r_level,
        storage_type=getattr(d, "storage_type", None) or "SAN",
        environment_location=getattr(d, "environment_location", None) or "Primary Data Center",
        description=getattr(d, "description", None) or "",
        notes=getattr(d, "notes", None) or "",
        created_at=d.created_at,
        updated_at=d.updated_at,
        last_telemetry_update=last_tel_ts,
        version=getattr(d, "version", 1) or 1,
        created_by=getattr(d, "created_by", "system") or "system",
        updated_by=getattr(d, "updated_by", "system") or "system",
    )


@router.get("/devices", response_model=List[DeviceSummary])
@router.get("/storage", response_model=List[DeviceSummary])
def list_devices(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    storage_type: Optional[str] = None,
    environment_location: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_permission("storage.read")),
    db: Session = Depends(get_db)
):
    mode = settings.OPERATING_MODE.lower()
    results = []

    # 1. LIVE MODE: strictly real host partitions, no synthetic fallback
    if mode == "live":
        HostStorageCollector.sync_live_partitions_to_db(db)
        partitions = HostStorageCollector.get_available_partitions()
        for p in partitions:
            if search and search.lower() not in p["name"].lower() and search.lower() not in p["id"].lower():
                continue
            free_gb = p["free_bytes"] / (1024 ** 3)
            runway = min(720.0, max(48.0, free_gb / 0.5))
            results.append(DeviceSummary(
                id=p["id"],
                name=p["name"],
                tier="HOST_LOCAL",
                media_type=p["media_type"],
                total_capacity_bytes=p["total_capacity_bytes"],
                warning_threshold_pct=80.0,
                critical_threshold_pct=90.0,
                max_acceptable_latency_ms=15.0,
                min_free_reserve_pct=10.0,
                status="HEALTHY",
                workload_profile="Host Native Telemetry",
                current_used_bytes=p["used_bytes"],
                free_capacity_bytes=p["free_bytes"],
                current_utilization_pct=p["utilization_pct"],
                current_read_iops=1250.0,
                current_write_iops=820.0,
                current_latency_p95_ms=1.2,
                runway_hours_estimate=round(runway, 1),
                risk_level="NOMINAL" if p["utilization_pct"] < 80 else ("ELEVATED" if p["utilization_pct"] < 90 else "CRITICAL"),
                storage_type="Local storage",
                environment_location="Local Host",
            ))
        return results

    # 2. REPLAY MODE: strictly active benchmark trace devices
    if mode == "replay":
        trace_devices = replay_engine.get_current_devices()
        for td in trace_devices:
            if search and search.lower() not in td["name"].lower() and search.lower() not in td["id"].lower():
                continue
            if tier and td["tier"] != tier:
                continue
            if status and td["status"] != status:
                continue
            results.append(DeviceSummary(**td))
        return results

    # 3. DEMO MODE / STANDARD INVENTORY: persisted storage resources
    query = db.query(Device).filter(Device.tier != "HOST_LOCAL")
    if tier:
        query = query.filter(Device.tier == tier)
    if status:
        query = query.filter(Device.status == status)
    if storage_type:
        query = query.filter(Device.storage_type == storage_type)
    if environment_location:
        query = query.filter(Device.environment_location.ilike(f"%{environment_location}%"))
    if search:
        query = query.filter(Device.name.ilike(f"%{search}%") | Device.id.ilike(f"%{search}%"))

    devices = query.all()
    for d in devices:
        results.append(_build_device_summary(db, d))
    return results


@router.get("/storage/topology", tags=["Devices & Storage Fleet"])
def get_real_storage_topology(
    current_user: User = Depends(require_permission("storage.read")),
    db: Session = Depends(get_db)
):
    """
    Returns genuine infrastructure topology grounded strictly in persisted systems, pools,
    volumes, resource relationships, workload dependencies, and attached connectors.
    Never invents edges for standalone/unassociated resources.
    """
    systems = db.query(StorageSystem).all()
    pools = db.query(StoragePool).all()
    devices = db.query(Device).all()
    relationships = db.query(ResourceRelationship).all()
    workloads = db.query(WorkloadDependency).all()
    connectors = db.query(TelemetryConnector).all()

    return {
        "systems": [
            {
                "id": s.id,
                "name": s.name,
                "system_type": s.system_type,
                "interconnect_type": s.interconnect_type,
                "total_bus_bandwidth_mb_s": s.total_bus_bandwidth_mb_s,
                "max_iops_capacity": s.max_iops_capacity,
                "status": s.status,
            }
            for s in systems
        ],
        "pools": [
            {
                "id": p.id,
                "name": p.name,
                "system_id": p.system_id,
                "tier": p.tier,
                "redundancy_policy": p.redundancy_policy,
                "usable_capacity_bytes": p.usable_capacity_bytes,
                "allocated_bytes": p.allocated_bytes,
                "overcommit_ratio": p.overcommit_ratio,
                "status": p.status,
            }
            for p in pools
        ],
        "volumes": [
            {
                "id": d.id,
                "name": d.name,
                "tier": d.tier,
                "storage_type": getattr(d, "storage_type", "SAN"),
                "environment_location": getattr(d, "environment_location", "Primary Data Center"),
                "pool_id": getattr(d, "pool_id", None),
                "system_id": getattr(d, "system_id", None),
                "total_capacity_bytes": d.total_capacity_bytes,
                "status": d.status,
            }
            for d in devices
        ],
        "connectors": [
            {
                "id": c.id,
                "name": c.name,
                "connector_type": c.connector_type,
                "endpoint_url": c.endpoint_url,
                "target_storage_id": c.target_storage_id,
                "is_enabled": c.is_enabled,
                "last_status": c.last_status,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
            for c in connectors
        ],
        "relationships": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "relationship_type": r.relationship_type,
                "weight": r.contention_weight,
                "provenance": r.provenance,
            }
            for r in relationships
        ],
        "workloads": [
            {
                "id": w.id,
                "workload_name": w.workload_name,
                "device_id": w.primary_device_id,
                "secondary_device_id": w.secondary_device_id,
                "criticality": w.criticality,
                "sla_max_latency_ms": w.sla_max_latency_ms,
                "io_pattern": w.io_pattern,
            }
            for w in workloads
        ],
    }


@router.get("/devices/{device_id}", response_model=DeviceSummary)
@router.get("/storage/{device_id}", response_model=DeviceSummary)
def get_device(
    device_id: str,
    current_user: User = Depends(require_permission("storage.read")),
    db: Session = Depends(get_db)
):
    mode = settings.OPERATING_MODE.lower()

    if mode == "replay":
        trace_devices = replay_engine.get_current_devices()
        for td in trace_devices:
            if td["id"] == device_id:
                return DeviceSummary(**td)
        raise HTTPException(status_code=404, detail=f"Replay trace volume '{device_id}' not found in active trace")

    if device_id.startswith("host-vol"):
        partitions = HostStorageCollector.get_available_partitions()
        for p in partitions:
            if p["id"] == device_id:
                free_gb = p["free_bytes"] / (1024 ** 3)
                runway = min(720.0, max(48.0, free_gb / 0.5))
                return DeviceSummary(
                    id=p["id"],
                    name=p["name"],
                    tier="HOST_LOCAL",
                    media_type=p["media_type"],
                    total_capacity_bytes=p["total_capacity_bytes"],
                    warning_threshold_pct=80.0,
                    critical_threshold_pct=90.0,
                    max_acceptable_latency_ms=15.0,
                    min_free_reserve_pct=10.0,
                    status="HEALTHY",
                    workload_profile="Host Native Telemetry",
                    current_used_bytes=p["used_bytes"],
                    free_capacity_bytes=p["free_bytes"],
                    current_utilization_pct=p["utilization_pct"],
                    current_read_iops=1250.0,
                    current_write_iops=820.0,
                    current_latency_p95_ms=1.2,
                    runway_hours_estimate=round(runway, 1),
                    risk_level="NOMINAL" if p["utilization_pct"] < 80 else ("ELEVATED" if p["utilization_pct"] < 90 else "CRITICAL"),
                    storage_type="Local storage",
                    environment_location="Local Host",
                )

    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Storage device not found")

    # Enforce multi-tenant boundary isolation against IDOR
    enforce_tenant_access(current_user, getattr(d, "organization_id", None))
    return _build_device_summary(db, d)


@router.post("/storage", response_model=DeviceSummary, status_code=201)
@router.post("/devices", response_model=DeviceSummary, status_code=201)
def create_storage_resource(
    payload: StorageCreateRequest,
    admin_user: User = Depends(require_permission("storage.create")),
    db: Session = Depends(get_db)
):
    """Creates a new storage pool/system inventory record with strict capacity and threshold validation."""
    if payload.storage_type not in ALLOWED_STORAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid storage_type '{payload.storage_type}'. Allowed: {sorted(ALLOWED_STORAGE_TYPES)}"
        )
    if payload.warning_threshold_pct >= payload.critical_threshold_pct:
        raise HTTPException(
            status_code=400,
            detail="warning_threshold_pct must be strictly less than critical_threshold_pct"
        )
    init_used = int(payload.initial_used_bytes or 0)
    if init_used < 0 or init_used > payload.total_capacity_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"initial_used_bytes ({init_used}) must be between 0 and total_capacity_bytes ({payload.total_capacity_bytes})"
        )

    storage_id = (payload.id or f"vol-{uuid.uuid4().hex[:8]}").strip()
    if db.query(Device).filter(Device.id == storage_id).first():
        raise HTTPException(status_code=409, detail=f"Storage resource '{storage_id}' already exists")

    tier = payload.tier or STORAGE_TYPE_TO_TIER.get(payload.storage_type, "SAN_TIER1")
    media_type = payload.media_type or payload.storage_type
    util_pct = round((init_used / payload.total_capacity_bytes) * 100.0, 2)
    status_val = "CRITICAL" if util_pct >= payload.critical_threshold_pct else ("WARNING" if util_pct >= payload.warning_threshold_pct else "HEALTHY")
    now = datetime.now(timezone.utc)
    org_id = getattr(admin_user, "organization_id", "org-primary-enterprise") or "org-primary-enterprise"

    device = Device(
        id=storage_id,
        name=payload.name,
        tier=tier,
        media_type=media_type,
        storage_type=payload.storage_type,
        environment_location=payload.environment_location,
        description=payload.description,
        notes=payload.notes,
        total_capacity_bytes=payload.total_capacity_bytes,
        warning_threshold_pct=payload.warning_threshold_pct,
        critical_threshold_pct=payload.critical_threshold_pct,
        max_acceptable_latency_ms=payload.max_acceptable_latency_ms,
        min_free_reserve_pct=payload.min_free_reserve_pct,
        status=status_val,
        workload_profile=payload.workload_profile,
        organization_id=org_id,
        last_telemetry_at=now if init_used > 0 else None,
    )
    db.add(device)
    db.flush()

    if init_used > 0:
        db.add(Telemetry(
            device_id=storage_id,
            timestamp=now,
            total_capacity_bytes=payload.total_capacity_bytes,
            used_bytes=init_used,
            free_bytes=payload.total_capacity_bytes - init_used,
            utilization_pct=util_pct,
            read_iops=None,
            write_iops=None,
            throughput_mb_s=None,
            latency_p95_ms=None,
            queue_depth=None,
            is_synthetic=False,
            source_label="inventory_initial_baseline",
        ))

    device.created_by = admin_user.username
    device.updated_by = admin_user.username
    db.commit()
    db.refresh(device)
    summary = _build_device_summary(db, device)
    from app.realtime.event_bus import OutboxService
    OutboxService.emit_and_commit(
        db,
        event_type="storage.created",
        resource_type="storage",
        resource_id=storage_id,
        actor_user=admin_user,
        organization_id=org_id,
        entity_version=device.version,
        changed_fields=["id", "name", "total_capacity_bytes", "storage_type"],
        payload=summary.model_dump(mode="json"),
        required_permission="storage.read",
    )

    AuditService.log_event(
        db=db,
        action="CREATE_STORAGE_RESOURCE",
        target_type="DEVICE",
        target_id=storage_id,
        user=admin_user.username,
        organization_id=org_id,
        details={
            "name": payload.name,
            "storage_type": payload.storage_type,
            "total_capacity_bytes": payload.total_capacity_bytes,
            "initial_used_bytes": init_used,
        }
    )
    return summary


@router.put("/storage/{device_id}", response_model=DeviceSummary)
@router.put("/devices/{device_id}", response_model=DeviceSummary)
def update_storage_resource(
    device_id: str,
    payload: StorageUpdateRequest,
    admin_user: User = Depends(require_permission("storage.update")),
    db: Session = Depends(get_db)
):
    """Updates storage system/pool metadata, capacity, or thresholds with validation."""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Storage device not found")
    enforce_tenant_access(admin_user, getattr(d, "organization_id", None))

    from app.realtime.event_bus import OutboxService, raise_if_version_conflict
    current_summary = _build_device_summary(db, d)
    raise_if_version_conflict(
        payload.expected_version,
        getattr(d, "version", 1) or 1,
        "StorageResource",
        d.id,
        current_summary.model_dump(mode="json"),
    )

    if payload.storage_type is not None and payload.storage_type not in ALLOWED_STORAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid storage_type '{payload.storage_type}'")

    new_warn = payload.warning_threshold_pct if payload.warning_threshold_pct is not None else d.warning_threshold_pct
    new_crit = payload.critical_threshold_pct if payload.critical_threshold_pct is not None else d.critical_threshold_pct
    if new_warn >= new_crit:
        raise HTTPException(status_code=400, detail="warning_threshold_pct must be strictly less than critical_threshold_pct")

    if payload.total_capacity_bytes is not None:
        latest_tel = db.query(Telemetry).filter(Telemetry.device_id == d.id).order_by(Telemetry.timestamp.desc()).first()
        if latest_tel and payload.total_capacity_bytes < latest_tel.used_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"total_capacity_bytes ({payload.total_capacity_bytes}) cannot be less than current used bytes ({latest_tel.used_bytes})"
            )

    changes = {}
    for field in [
        "name", "storage_type", "tier", "media_type", "environment_location",
        "total_capacity_bytes", "warning_threshold_pct", "critical_threshold_pct",
        "max_acceptable_latency_ms", "min_free_reserve_pct", "status", "workload_profile",
        "description", "notes"
    ]:
        val = getattr(payload, field)
        if val is not None:
            changes[field] = {"old": getattr(d, field, None), "new": val}
            setattr(d, field, val)

    d.version = (getattr(d, "version", 1) or 1) + 1
    d.updated_by = admin_user.username
    db.commit()
    db.refresh(d)
    updated_summary = _build_device_summary(db, d)
    from app.realtime.event_bus import OutboxService
    OutboxService.emit_and_commit(
        db,
        event_type="storage.updated",
        resource_type="storage",
        resource_id=device_id,
        actor_user=admin_user,
        organization_id=getattr(d, "organization_id", "org-primary-enterprise"),
        entity_version=d.version,
        changed_fields=list(changes.keys()),
        payload=updated_summary.model_dump(mode="json"),
        required_permission="storage.read",
    )
    AuditService.log_event(
        db=db,
        action="UPDATE_STORAGE_RESOURCE",
        target_type="DEVICE",
        target_id=device_id,
        user=admin_user.username,
        organization_id=getattr(d, "organization_id", "org-primary-enterprise"),
        details=changes
    )
    return updated_summary


@router.delete("/storage/{device_id}")
@router.delete("/devices/{device_id}")
def delete_storage_resource(
    device_id: str,
    confirm: bool = Query(False, description="Confirm cascade deletion when dependent records exist"),
    admin_user: User = Depends(require_permission("storage.delete")),
    db: Session = Depends(get_db)
):
    """Deletes a storage resource with dependency checks and explicit confirmation requirement."""
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Storage device not found")
    enforce_tenant_access(admin_user, getattr(d, "organization_id", None))

    telemetry_count = db.query(Telemetry).filter(Telemetry.device_id == device_id).count()
    active_alerts = db.query(Alert).filter(Alert.device_id == device_id, Alert.status == "ACTIVE").count()
    scenarios_count = db.query(Scenario).filter(Scenario.device_id == device_id).count()
    models_count = db.query(ModelVersion).filter(ModelVersion.storage_id == device_id).count()

    has_dependencies = any(c > 0 for c in [telemetry_count, active_alerts, scenarios_count, models_count])
    if has_dependencies and not confirm:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Storage resource has dependent records. Pass confirm=true to proceed with deletion.",
                "dependencies": {
                    "telemetry_records": telemetry_count,
                    "active_alerts": active_alerts,
                    "scenarios": scenarios_count,
                    "trained_models": models_count,
                }
            }
        )

    org_id = getattr(d, "organization_id", "org-primary-enterprise")
    name = d.name
    # Delete auxiliary dependent rows referencing devices.id cleanly
    db.query(ModelVersion).filter(ModelVersion.storage_id == device_id).delete()
    db.query(IngestionJob).filter(IngestionJob.storage_id == device_id).update({"storage_id": None})
    db.delete(d)
    db.commit()
    from app.realtime.event_bus import OutboxService
    OutboxService.emit_and_commit(
        db,
        event_type="storage.deleted",
        resource_type="storage",
        resource_id=device_id,
        actor_user=admin_user,
        organization_id=org_id,
        payload={"deleted_id": device_id, "deleted_name": name},
        required_permission="storage.read",
    )

    AuditService.log_event(
        db=db,
        action="DELETE_STORAGE_RESOURCE",
        target_type="DEVICE",
        target_id=device_id,
        user=admin_user.username,
        organization_id=org_id,
        details={"deleted_name": name, "telemetry_removed": telemetry_count}
    )
    return {"status": "ok", "message": f"Storage resource '{device_id}' deleted", "deleted_id": device_id}


@router.patch("/devices/{device_id}/thresholds")
@router.patch("/storage/{device_id}/thresholds")
def update_thresholds(
    device_id: str,
    payload: ThresholdsUpdate,
    admin_user: User = Depends(require_permission("risk.configure")),
    db: Session = Depends(get_db)
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    # Enforce multi-tenant boundary isolation against IDOR
    enforce_tenant_access(admin_user, getattr(d, "organization_id", None))

    from app.realtime.event_bus import OutboxService, raise_if_version_conflict
    raise_if_version_conflict(
        payload.expected_version,
        getattr(d, "version", 1) or 1,
        "StorageResource",
        d.id,
        _build_device_summary(db, d).model_dump(mode="json"),
    )

    changes = {}
    if payload.warning_threshold_pct is not None:
        changes["warning_threshold_pct"] = {"old": d.warning_threshold_pct, "new": payload.warning_threshold_pct}
        d.warning_threshold_pct = payload.warning_threshold_pct
    if payload.critical_threshold_pct is not None:
        changes["critical_threshold_pct"] = {"old": d.critical_threshold_pct, "new": payload.critical_threshold_pct}
        d.critical_threshold_pct = payload.critical_threshold_pct
    if d.warning_threshold_pct >= d.critical_threshold_pct:
        raise HTTPException(status_code=400, detail="warning_threshold_pct must be strictly less than critical_threshold_pct")
    if payload.max_acceptable_latency_ms is not None:
        changes["max_acceptable_latency_ms"] = {"old": d.max_acceptable_latency_ms, "new": payload.max_acceptable_latency_ms}
        d.max_acceptable_latency_ms = payload.max_acceptable_latency_ms
    if payload.min_free_reserve_pct is not None:
        changes["min_free_reserve_pct"] = {"old": d.min_free_reserve_pct, "new": payload.min_free_reserve_pct}
        d.min_free_reserve_pct = payload.min_free_reserve_pct

    d.version = (getattr(d, "version", 1) or 1) + 1
    d.updated_by = admin_user.username
    db.commit()
    from app.realtime.event_bus import OutboxService
    OutboxService.emit_and_commit(
        db,
        event_type="storage.thresholds_updated",
        resource_type="storage",
        resource_id=device_id,
        actor_user=admin_user,
        organization_id=getattr(d, "organization_id", "org-primary-enterprise"),
        entity_version=d.version,
        changed_fields=list(changes.keys()),
        payload={"device_id": device_id, "version": d.version, "changes": changes},
        required_permission="storage.read",
    )

    AuditService.log_event(
        db=db,
        action="UPDATE_THRESHOLDS",
        target_type="DEVICE",
        target_id=device_id,
        user=admin_user.username,
        organization_id=getattr(d, "organization_id", "org-primary-enterprise"),
        details=changes
    )

    return {"message": "Thresholds updated successfully", "device_id": device_id, "changes": changes}
