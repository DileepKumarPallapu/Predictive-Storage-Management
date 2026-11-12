from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, RiskAssessment, User
from app.schemas.payloads import DeviceSummary, ThresholdsUpdate
from app.services.audit_service import AuditService
from app.auth.security import get_current_user, require_role, enforce_tenant_access
from app.config import settings
from app.collector.host_collector import HostStorageCollector
from app.services.replay_service import replay_engine


router = APIRouter()

@router.get("/devices", response_model=List[DeviceSummary])
def list_devices(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
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
            if tier and tier != "HOST_LOCAL":
                continue
            current_status = (
                "CRITICAL" if p["utilization_pct"] >= 90.0
                else "WARNING" if p["utilization_pct"] >= 80.0
                else "HEALTHY"
            )
            if status and current_status != status:
                continue
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
                status=current_status,
                workload_profile="Host Filesystem Capacity",
                current_used_bytes=p["used_bytes"],
                current_utilization_pct=p["utilization_pct"],
                current_read_iops=None,
                current_write_iops=None,
                current_latency_p95_ms=None,
                runway_hours_estimate=None,
                risk_level="CRITICAL" if current_status == "CRITICAL" else "ELEVATED" if current_status == "WARNING" else "INSUFFICIENT_EVIDENCE"
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

    # 3. DEMO MODE: synthetic fleet fixtures
    query = db.query(Device).filter(Device.tier != "HOST_LOCAL")
    if tier:
        query = query.filter(Device.tier == tier)
    if status:
        query = query.filter(Device.status == status)
    if search:
        query = query.filter(Device.name.ilike(f"%{search}%") | Device.id.ilike(f"%{search}%"))

    devices = query.all()

    for d in devices:
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

        used = latest_tel.used_bytes if latest_tel else int(d.total_capacity_bytes * 0.70)
        util_pct = latest_tel.utilization_pct if latest_tel else 70.0
        r_iops = latest_tel.read_iops if latest_tel else 5000.0
        w_iops = latest_tel.write_iops if latest_tel else 4000.0
        lat = latest_tel.latency_p95_ms if latest_tel else 2.5
        runway = latest_risk.runway_hours_estimate if latest_risk else 120.0
        r_level = latest_risk.risk_level if latest_risk else "NOMINAL"

        results.append(DeviceSummary(
            id=d.id,
            name=d.name,
            tier=d.tier,
            media_type=d.media_type,
            total_capacity_bytes=d.total_capacity_bytes,
            warning_threshold_pct=d.warning_threshold_pct,
            critical_threshold_pct=d.critical_threshold_pct,
            max_acceptable_latency_ms=d.max_acceptable_latency_ms,
            min_free_reserve_pct=d.min_free_reserve_pct,
            status=d.status,
            workload_profile=d.workload_profile,
            current_used_bytes=used,
            current_utilization_pct=util_pct,
            current_read_iops=r_iops,
            current_write_iops=w_iops,
            current_latency_p95_ms=lat,
            runway_hours_estimate=runway,
            risk_level=r_level
        ))

    return results

@router.get("/devices/{device_id}", response_model=DeviceSummary)
def get_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
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
        HostStorageCollector.sync_live_partitions_to_db(db)
        partitions = HostStorageCollector.get_available_partitions()
        for p in partitions:
            if p["id"] == device_id:
                current_status = (
                    "CRITICAL" if p["utilization_pct"] >= 90.0
                    else "WARNING" if p["utilization_pct"] >= 80.0
                    else "HEALTHY"
                )
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
                    status=current_status,
                    workload_profile="Host Filesystem Capacity",
                    current_used_bytes=p["used_bytes"],
                    current_utilization_pct=p["utilization_pct"],
                    current_read_iops=None,
                    current_write_iops=None,
                    current_latency_p95_ms=None,
                    runway_hours_estimate=None,
                    risk_level="CRITICAL" if current_status == "CRITICAL" else "ELEVATED" if current_status == "WARNING" else "INSUFFICIENT_EVIDENCE"
                )
        raise HTTPException(status_code=404, detail=f"Host storage volume '{device_id}' not found")

    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Storage device not found")

    # Enforce multi-tenant boundary isolation against IDOR
    enforce_tenant_access(current_user, getattr(d, "organization_id", None))

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

    used = latest_tel.used_bytes if latest_tel else None
    util_pct = latest_tel.utilization_pct if latest_tel else None
    r_iops = latest_tel.read_iops if latest_tel else None
    w_iops = latest_tel.write_iops if latest_tel else None
    lat = latest_tel.latency_p95_ms if latest_tel else None
    runway = latest_risk.runway_hours_estimate if latest_risk else None
    r_level = latest_risk.risk_level if latest_risk else "INSUFFICIENT_EVIDENCE"

    return DeviceSummary(
        id=d.id,
        name=d.name,
        tier=d.tier,
        media_type=d.media_type,
        total_capacity_bytes=d.total_capacity_bytes,
        warning_threshold_pct=d.warning_threshold_pct,
        critical_threshold_pct=d.critical_threshold_pct,
        max_acceptable_latency_ms=d.max_acceptable_latency_ms,
        min_free_reserve_pct=d.min_free_reserve_pct,
        status=d.status,
        workload_profile=d.workload_profile,
        current_used_bytes=used,
        current_utilization_pct=util_pct,
        current_read_iops=r_iops,
        current_write_iops=w_iops,
        current_latency_p95_ms=lat,
        runway_hours_estimate=runway,
        risk_level=r_level
    )

@router.patch("/devices/{device_id}/thresholds")
def update_thresholds(
    device_id: str,
    payload: ThresholdsUpdate,
    admin_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

    # Enforce multi-tenant boundary isolation against IDOR
    enforce_tenant_access(admin_user, getattr(d, "organization_id", None))

    changes = {}
    if payload.warning_threshold_pct is not None:
        changes["warning_threshold_pct"] = {"old": d.warning_threshold_pct, "new": payload.warning_threshold_pct}
        d.warning_threshold_pct = payload.warning_threshold_pct
    if payload.critical_threshold_pct is not None:
        changes["critical_threshold_pct"] = {"old": d.critical_threshold_pct, "new": payload.critical_threshold_pct}
        d.critical_threshold_pct = payload.critical_threshold_pct
    if payload.max_acceptable_latency_ms is not None:
        changes["max_acceptable_latency_ms"] = {"old": d.max_acceptable_latency_ms, "new": payload.max_acceptable_latency_ms}
        d.max_acceptable_latency_ms = payload.max_acceptable_latency_ms
    if payload.min_free_reserve_pct is not None:
        changes["min_free_reserve_pct"] = {"old": d.min_free_reserve_pct, "new": payload.min_free_reserve_pct}
        d.min_free_reserve_pct = payload.min_free_reserve_pct

    db.commit()

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
