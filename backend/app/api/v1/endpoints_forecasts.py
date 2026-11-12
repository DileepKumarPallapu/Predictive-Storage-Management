import json
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, ModelVersion, ModelMetric, Forecast, User
from app.schemas.payloads import ForecastResponse
from app.config import settings
from app.services.replay_service import replay_engine
from app.collector.host_collector import HostStorageCollector
from app.ml.models import run_forecast
from app.ml.sklearn_engine import CapacityMLEngine
from app.auth.security import require_role
from app.auth.permissions import require_permission
from app.services.audit_service import AuditService

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
    current_user: User = Depends(require_permission("forecasts.read")),
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


# ------------------------------------------------------------------------------
# MODULE 5 & 6 — DUAL-MODEL ML TRAINING, SAVED FORECASTS & CAPACITY RUNWAY
# ------------------------------------------------------------------------------

@router.post("/models/train/{storage_id}", tags=["ML Training Engine"])
def train_storage_ml_models(
    storage_id: str,
    admin_user: User = Depends(require_permission("models.train")),
    db: Session = Depends(get_db)
):
    """
    Trains Model A (RandomForestRegressor) and Model B (HistGradientBoostingRegressor)
    using chronological train/validation split, persists joblib artifacts, compares MAE/RMSE/R2/MAPE,
    and activates the superior model without overwriting working models on failure.
    """
    try:
        res = CapacityMLEngine.train_and_evaluate(db, storage_id=storage_id, trained_by=admin_user.username)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if res.get("status") == "TRAINED":
        AuditService.log_event(
            db=db,
            action="TRAIN_ML_MODEL",
            target_type="MODEL",
            target_id=storage_id,
            user=admin_user.username,
            details={
                "selected_algorithm": res["selected_model"]["algorithm"],
                "version": res["selected_model"]["version"],
                "rmse_bytes": res["selected_model"]["rmse_bytes"],
                "mae_bytes": res["selected_model"]["mae_bytes"],
            }
        )
    return res


@router.get("/models", tags=["ML Training Engine"])
def list_all_trained_models(
    storage_id: Optional[str] = None,
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    """Lists persisted ML model versions, validation metrics, and selection status."""
    q = db.query(ModelVersion)
    if storage_id:
        q = q.filter(ModelVersion.storage_id == storage_id)
    versions = q.order_by(ModelVersion.trained_at.desc()).limit(100).all()

    results = []
    for mv in versions:
        mm = db.query(ModelMetric).filter(ModelMetric.model_version_id == mv.id).first()
        results.append({
            "id": mv.id,
            "storage_id": mv.storage_id,
            "name": mv.name,
            "algorithm": mv.model_type,
            "version": mv.version_tag,
            "feature_version": getattr(mv, "feature_version", "v2.0"),
            "training_samples": mv.train_samples_count,
            "validation_samples": getattr(mv, "validation_samples", 0),
            "train_start_at": mv.train_start_at.isoformat() if getattr(mv, "train_start_at", None) else None,
            "train_end_at": mv.train_end_at.isoformat() if getattr(mv, "train_end_at", None) else None,
            "mae_bytes": mm.mae if mm else mv.mae,
            "rmse_bytes": mm.rmse if mm else mv.rmse,
            "r2_score": mm.r2_score if mm else None,
            "mape_pct": mm.mape if mm else None,
            "is_active": mv.is_active,
            "is_selected": mm.is_selected if mm else mv.is_active,
            "selection_reason": mm.selection_reason if mm else "",
            "status": getattr(mv, "status", "TRAINED"),
            "artifact_available": bool(getattr(mv, "artifact_path", None) and os.path.exists(mv.artifact_path)),
            "trained_at": mv.trained_at.isoformat() if mv.trained_at else None,
        })
    return results


@router.get("/models/{storage_id}", tags=["ML Training Engine"])
def get_storage_models(
    storage_id: str,
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    """Returns trained models, algorithm comparison metrics, and active model status for a storage resource."""
    device = db.query(Device).filter(Device.id == storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Storage resource '{storage_id}' not found")
    models = list_all_trained_models(storage_id=storage_id, current_user=current_user, db=db)
    active = next((m for m in models if m["is_active"]), None)
    return {
        "storage_id": storage_id,
        "active_model": active,
        "models_count": len(models),
        "models": models,
    }


@router.post("/forecasts/generate/{storage_id}", tags=["Forecasting Engine"])
def generate_capacity_forecast(
    storage_id: str,
    horizon_days: int = Query(30, description="Forecast horizon in days (7, 30, or 90)"),
    auto_train_if_missing: bool = Query(True, description="Train RandomForest & HistGradientBoosting if no model exists yet"),
    current_user: User = Depends(require_permission("forecasts.generate")),
    db: Session = Depends(get_db)
):
    """
    Generates daily capacity predictions (7/30/90 days) using the persisted winning ML artifact,
    stores predictions in the database, computes threshold runway, and logs audit history.
    """
    try:
        res = CapacityMLEngine.predict_capacity(
            db=db,
            storage_id=storage_id,
            horizon_days=horizon_days,
            auto_train_if_missing=auto_train_if_missing,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if res.get("status") == "OK":
        AuditService.log_event(
            db=db,
            action="GENERATE_FORECAST",
            target_type="FORECAST",
            target_id=str(res["forecast_id"]),
            user=current_user.username,
            details={
                "storage_id": storage_id,
                "horizon_days": horizon_days,
                "model_used": res["model_used"],
                "projected_breach": res["projected_capacity_breach"],
            }
        )
    elif res.get("status") in ("INSUFFICIENT_HISTORY", "MODEL_NOT_TRAINED"):
        raise HTTPException(status_code=400, detail=res)
    return res


@router.get("/forecasts/{storage_id}", tags=["Forecasting Engine"])
def get_saved_forecasts(
    storage_id: str,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(require_permission("forecasts.read")),
    db: Session = Depends(get_db)
):
    """Retrieves saved ML capacity forecasts from the persistent forecasts table."""
    device = db.query(Device).filter(Device.id == storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Storage resource '{storage_id}' not found")

    rows = (
        db.query(Forecast)
        .filter(Forecast.device_id == storage_id)
        .order_by(Forecast.generated_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for f in rows:
        results.append({
            "id": f.id,
            "storage_id": f.device_id,
            "model_name": f.model_name,
            "model_version_id": getattr(f, "model_version_id", None),
            "target_metric": f.target_metric,
            "horizon_hours": f.horizon_hours,
            "horizon_days": getattr(f, "horizon_days", None) or max(1, f.horizon_hours // 24),
            "generated_at": f.generated_at.isoformat() if f.generated_at else None,
            "historical_cutoff": f.historical_cutoff.isoformat() if f.historical_cutoff else None,
            "projected_capacity_breach": bool(getattr(f, "projected_capacity_breach", False)),
            "breach_timestamp": f.breach_timestamp.isoformat() if getattr(f, "breach_timestamp", None) else None,
            "daily_predictions": json.loads(f.daily_predictions_json) if getattr(f, "daily_predictions_json", None) else [],
            "inference_ms": f.inference_ms,
        })
    return results


@router.get("/forecasts/{storage_id}/runway", tags=["Risk & Reserve Runway"])
def get_capacity_runway(
    storage_id: str,
    safety_threshold_pct: Optional[float] = Query(None, gt=0.0, le=100.0),
    current_user: User = Depends(require_permission("risk.read")),
    db: Session = Depends(get_db)
):
    """Calculates remaining safe capacity and estimated runway days until threshold breach."""
    device = db.query(Device).filter(Device.id == storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Storage resource '{storage_id}' not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == storage_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )
    latest_used = int(records[-1].used_bytes) if records else 0

    latest_forecast = (
        db.query(Forecast)
        .filter(Forecast.device_id == storage_id, Forecast.daily_predictions_json.isnot(None))
        .order_by(Forecast.generated_at.desc())
        .first()
    )
    daily_preds = json.loads(latest_forecast.daily_predictions_json) if latest_forecast and latest_forecast.daily_predictions_json else None

    runway = CapacityMLEngine.calculate_capacity_runway(
        device=device,
        current_used_bytes=latest_used,
        daily_predictions=daily_preds,
        records=records,
        safety_threshold_pct=safety_threshold_pct,
    )
    return {
        "storage_id": storage_id,
        "device_name": device.name,
        "total_capacity_bytes": int(device.total_capacity_bytes),
        "current_used_bytes": latest_used,
        "current_free_bytes": int(max(0, device.total_capacity_bytes - latest_used)),
        "current_utilization_pct": round((latest_used / device.total_capacity_bytes) * 100.0, 2) if device.total_capacity_bytes > 0 else 0.0,
        "latest_forecast_id": latest_forecast.id if latest_forecast else None,
        "latest_forecast_model": latest_forecast.model_name if latest_forecast else None,
        "runway": runway,
    }
