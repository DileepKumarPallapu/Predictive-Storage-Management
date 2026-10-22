from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry
from app.schemas.payloads import ForecastResponse
from app.config import settings
from app.services.replay_service import replay_engine
from app.collector.host_collector import HostStorageCollector
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
    mode = settings.OPERATING_MODE.lower()

    if mode == "replay":
        # Build telemetry from replay engine frames up to current cursor
        trace_devs = {d["id"]: d for d in replay_engine.get_current_devices()}
        if device_id not in trace_devs:
            raise HTTPException(status_code=404, detail=f"Replay device '{device_id}' not found in active trace")

        tot_cap = float(trace_devs[device_id]["total_capacity_bytes"])
        crit_pct = float(trace_devs[device_id]["critical_threshold_pct"])
        max_lat = float(trace_devs[device_id]["max_acceptable_latency_ms"])

        cur_idx = replay_engine.current_frame_index
        if cur_idx < 12:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient trace history at current replay frame ({cur_idx + 1} frames). Advance replay timeline to at least frame 12 to run forecasts."
            )

        telemetry_dicts = []
        for i in range(cur_idx + 1):
            f = replay_engine.frames[i]
            v = f.get("volumes", {}).get(device_id)
            if v:
                telemetry_dicts.append({
                    "timestamp": datetime.fromisoformat(f["timestamp"].replace("Z", "+00:00")),
                    "device_id": device_id,
                    "used_bytes": v["used_bytes"],
                    "free_bytes": v["free_bytes"],
                    "read_iops": v["read_iops"],
                    "write_iops": v["write_iops"],
                    "throughput_mb_s": v["throughput_mb_s"],
                    "latency_p95_ms": v["latency_p95_ms"],
                    "queue_depth": v["queue_depth"],
                    "is_synthetic": False
                })

        forecast_out = run_forecast(
            telemetry_records=telemetry_dicts,
            target_metric=target_metric,
            model_type=model_type,
            horizon_hours=horizon_hours,
            total_capacity=tot_cap
        )

        hard_limit = (crit_pct / 100.0) * tot_cap if target_metric == "used_bytes" else max_lat

        return ForecastResponse(
            device_id=device_id,
            target_metric=target_metric,
            model_name=forecast_out["model_name"],
            forecast_horizon_hours=horizon_hours,
            generated_at=datetime.now(timezone.utc),
            historical_cutoff=telemetry_dicts[-1]["timestamp"],
            timestamps=forecast_out["timestamps"],
            q10=forecast_out["q10"],
            q50=forecast_out["q50"],
            q90=forecast_out["q90"],
            units=METRIC_UNITS.get(target_metric, "Value"),
            hard_constraint_value=hard_limit,
            interval_coverage=forecast_out.get("interval_coverage", 0.85),
            inference_latency_ms=forecast_out.get("inference_latency_ms", 12.0)
        )

    if device_id.startswith("host-vol"):
        HostStorageCollector.sync_live_partitions_to_db(db)

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
