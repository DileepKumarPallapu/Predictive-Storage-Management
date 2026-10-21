from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, RiskAssessment
from app.schemas.payloads import DeviceSummary, ThresholdsUpdate
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/devices", response_model=List[DeviceSummary])
def list_devices(
    tier: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Device)
    if tier:
        query = query.filter(Device.tier == tier)
    if status:
        query = query.filter(Device.status == status)
    if search:
        query = query.filter(Device.name.ilike(f"%{search}%") | Device.id.ilike(f"%{search}%"))

    devices = query.all()
    results = []

    for d in devices:
        # Get latest telemetry
        latest_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == d.id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        
        # Get latest risk assessment
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
def get_device(device_id: str, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Storage device not found")

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
def update_thresholds(device_id: str, payload: ThresholdsUpdate, db: Session = Depends(get_db)):
    d = db.query(Device).filter(Device.id == device_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Device not found")

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
        details=changes
    )

    return {"message": "Thresholds updated successfully", "device_id": device_id, "changes": changes}
