from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry
from app.schemas.payloads import ForecastResponse
from app.ml.models import run_forecast

router = APIRouter()

METRIC_UNITS = {
    "used_bytes": "Bytes",
    "latency_p95_ms": "ms",
    "read_iops": "IOPS",
    "write_iops": "IOPS",
    "throughput_mb_s": "MB/s"
}

@router.get("/devices/{device_id}/forecasts", response_model=ForecastResponse)
def get_device_forecast(
    device_id: str,
    target_metric: str = Query("used_bytes", description="Target metric for forecasting"),
    model_type: str = Query("lightgbm_quantile", description="lightgbm_quantile, seasonal_naive, persistence"),
    horizon_hours: int = Query(72, description="Forecast horizon in hours (24, 72, 168)"),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Fetch last 30 days of telemetry for model training
    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    if len(records) < 24:
        raise HTTPException(status_code=400, detail="Insufficient telemetry history to train forecasting model (minimum 24 points required)")

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
        target_metric=target_metric,
        model_type=model_type,
        horizon_hours=horizon_hours,
        total_capacity=float(device.total_capacity_bytes)
    )

    # Compute hard constraint threshold for the metric
    hard_limit = None
    if target_metric == "used_bytes":
        hard_limit = (device.critical_threshold_pct / 100.0) * device.total_capacity_bytes
    elif target_metric == "latency_p95_ms":
        hard_limit = device.max_acceptable_latency_ms

    return ForecastResponse(
        device_id=device_id,
        target_metric=target_metric,
        model_name=forecast_out["model_name"],
        forecast_horizon_hours=horizon_hours,
        generated_at=datetime.now(timezone.utc),
        historical_cutoff=records[-1].timestamp,
        timestamps=forecast_out["timestamps"],
        q10=forecast_out["q10"],
        q50=forecast_out["q50"],
        q90=forecast_out["q90"],
        units=METRIC_UNITS.get(target_metric, "Value"),
        hard_constraint_value=hard_limit,
        interval_coverage=forecast_out.get("interval_coverage", 0.85),
        inference_latency_ms=forecast_out.get("inference_latency_ms", 12.0)
    )
