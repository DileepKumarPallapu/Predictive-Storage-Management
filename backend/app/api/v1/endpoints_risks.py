from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry
from app.schemas.payloads import RiskResponse
from app.services.risk_engine import RiskEngine
from app.ml.models import run_forecast

router = APIRouter()

@router.get("/devices/{device_id}/risks", response_model=RiskResponse)
def get_device_risk_assessment(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    if not records:
        raise HTTPException(status_code=400, detail="No telemetry available to compute risk profile")

    latest = records[-1]
    telemetry_dicts = [
        {
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "used_bytes": r.used_bytes,
            "free_bytes": r.free_bytes,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "throughput_mb_s": r.throughput_mb_s,
            "latency_p95_ms": r.latency_p95_ms,
            "queue_depth": r.queue_depth,
            "is_synthetic": r.is_synthetic
        }
        for r in records
    ]

    forecast_out = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    device_meta = {
        "id": device.id,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms
    }

    risk_eval = RiskEngine.assess_device_risk(
        device_id=device_id,
        device_meta=device_meta,
        forecast_result=forecast_out
    )

    return RiskResponse(
        device_id=risk_eval["device_id"],
        computed_at=risk_eval["computed_at"],
        current_capacity_pct=risk_eval["current_capacity_pct"],
        runway_hours_estimate=risk_eval["runway_hours_estimate"],
        runway_hours_lower_bound=risk_eval["runway_hours_lower_bound"],
        runway_hours_upper_bound=risk_eval["runway_hours_upper_bound"],
        risk_level=risk_eval["risk_level"],
        breach_status=risk_eval.get("breach_status", "NOMINAL_HEADROOM"),
        is_runway_reliable=risk_eval.get("is_runway_reliable", True),
        unreliability_reason=risk_eval.get("unreliability_reason"),
        capacity_breach_prob_24h=risk_eval["capacity_breach_prob_24h"],
        capacity_breach_prob_72h=risk_eval["capacity_breach_prob_72h"],
        latency_breach_prob_24h=risk_eval["latency_breach_prob_24h"],
        risk_contributors=risk_eval["risk_contributors"]
    )
