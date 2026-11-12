from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models.entities import Device, Telemetry, User
from app.schemas.payloads import RiskResponse
from app.schemas.intelligence_contract import CapacityRunwayResult, PerformanceRiskResult
from app.services.risk_engine import RiskEngine
from app.services.capacity_runway_engine import CapacityRunwayEngine
from app.services.performance_risk_engine import PerformanceRiskEngine
from app.ml.models import run_forecast
from app.auth.permissions import require_permission

router = APIRouter()

def _fetch_device_and_telemetry(db: Session, device_id: str):
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
    return device, telemetry_dicts

@router.get("/devices/{device_id}/reserve-runway", response_model=CapacityRunwayResult)
def get_device_reserve_runway(
    device_id: str,
    current_user: User = Depends(require_permission("risk.read")),
    db: Session = Depends(get_db),
):
    """
    Dedicated Capacity Reserve Runway Endpoint.
    Integrates historical growth with calibrated forecast trajectories to estimate
    exact time to critical threshold breach under expected and sensitive growth rates.
    """
    device, telemetry_dicts = _fetch_device_and_telemetry(db, device_id)

    forecast_out = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    runway_res = CapacityRunwayEngine.evaluate_runway(
        device_id=device_id,
        total_capacity_bytes=device.total_capacity_bytes,
        telemetry_history=telemetry_dicts,
        forecast_contract=forecast_out,
        critical_threshold_pct=device.critical_threshold_pct,
        warning_threshold_pct=device.warning_threshold_pct
    )
    return runway_res

@router.get("/devices/{device_id}/risk-assessment")
def get_comprehensive_risk_assessment(
    device_id: str,
    current_user: User = Depends(require_permission("risk.read")),
    db: Session = Depends(get_db),
):
    """
    Comprehensive Storage Resilience Risk Assessment.
    Returns synchronized capacity runway, performance risk, and coupling analysis.
    """
    device, telemetry_dicts = _fetch_device_and_telemetry(db, device_id)

    device_meta = {
        "id": device.id,
        "tier": device.tier,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": telemetry_dicts[-1]["used_bytes"],
        "current_latency_p95_ms": telemetry_dicts[-1]["latency_p95_ms"],
        "current_throughput_mb_s": telemetry_dicts[-1]["throughput_mb_s"],
        "utilization_pct": round((telemetry_dicts[-1]["used_bytes"] / float(device.total_capacity_bytes)) * 100.0, 2)
    }

    # 1. Capacity forecast and runway
    cap_forecast = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    runway_res = CapacityRunwayEngine.evaluate_runway(
        device_id=device_id,
        total_capacity_bytes=device.total_capacity_bytes,
        telemetry_history=telemetry_dicts,
        forecast_contract=cap_forecast,
        critical_threshold_pct=device.critical_threshold_pct,
        warning_threshold_pct=device.warning_threshold_pct
    )

    # 2. Performance risk evaluation
    perf_res = PerformanceRiskEngine.evaluate_performance_risk(
        device_id=device_id,
        device_metadata=device_meta,
        telemetry_history=telemetry_dicts
    )

    return {
        "device_id": device_id,
        "evaluated_at": datetime.now(timezone.utc),
        "capacity_runway": runway_res.model_dump(),
        "performance_risk": perf_res.model_dump(),
        "overall_resilience_status": "CRITICAL" if (runway_res.estimated_runway_hours <= 24.0 or perf_res.latency_risk_level == "CRITICAL") else (
            "ELEVATED" if (runway_res.estimated_runway_hours <= 72.0 or perf_res.latency_risk_level == "ELEVATED") else "NOMINAL"
        )
    }

@router.get("/devices/{device_id}/risks", response_model=RiskResponse)
def get_device_risk_assessment_legacy(
    device_id: str,
    current_user: User = Depends(require_permission("risk.read")),
    db: Session = Depends(get_db),
):
    """Legacy compatibility endpoint for existing dashboard widgets."""
    device, telemetry_dicts = _fetch_device_and_telemetry(db, device_id)
    latest = telemetry_dicts[-1]

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
        "current_used_bytes": latest["used_bytes"],
        "current_latency_p95_ms": latest["latency_p95_ms"]
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
