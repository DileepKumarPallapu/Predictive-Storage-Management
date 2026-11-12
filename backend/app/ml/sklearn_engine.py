import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score
from sqlalchemy.orm import Session

from app.models.entities import Device, Telemetry, ModelVersion, ModelMetric, Forecast
from app.utils.datetime_utils import utc_now

ARTIFACTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "model_artifacts")
FEATURE_VERSION = "v2.0-leakfree"
MIN_TRAINING_RECORDS = 48


def _ensure_artifacts_dir():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


class LeakFreeFeatureBuilder:
    """
    Constructs strictly leak-free chronological features for storage capacity prediction.
    Every feature at index t uses strictly observations from timestamps <= t-1.
    """

    BASE_FEATURES = [
        "hour_sin", "hour_cos", "day_sin", "day_cos", "is_weekend",
        "used_lag_1", "utilization_lag_1",
        "delta_lag_1", "delta_lag_6", "delta_lag_24",
        "roll_mean_delta_6", "roll_mean_delta_24", "roll_std_delta_24",
    ]
    PERF_FEATURES = ["read_iops_lag_1", "write_iops_lag_1", "latency_lag_1"]

    @classmethod
    def build_training_dataset(
        cls,
        records: List[Telemetry],
        total_capacity_bytes: int
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series, List[str]]:
        """
        Returns (X, y_delta, y_actual_used_bytes, feature_names).
        Target y_delta is (used_bytes[t] - used_bytes[t-1]), paired with y_actual_used_bytes[t]
        and base level used_lag_1[t] so validation computes exact byte-level MAE/RMSE/R2/MAPE.
        """
        rows = []
        for r in records:
            ts = r.timestamp.replace(tzinfo=None) if r.timestamp and r.timestamp.tzinfo else r.timestamp
            rows.append({
                "timestamp": ts,
                "used_bytes": float(r.used_bytes),
                "total_capacity_bytes": float(r.total_capacity_bytes or total_capacity_bytes),
                "read_iops": float(r.read_iops) if r.read_iops is not None else np.nan,
                "write_iops": float(r.write_iops) if r.write_iops is not None else np.nan,
                "latency_p95_ms": float(r.latency_p95_ms) if r.latency_p95_ms is not None else np.nan,
            })

        df = pd.DataFrame(rows).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

        hours = df["timestamp"].dt.hour
        days = df["timestamp"].dt.dayofweek
        df["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
        df["day_sin"] = np.sin(2.0 * np.pi * days / 7.0)
        df["day_cos"] = np.cos(2.0 * np.pi * days / 7.0)
        df["is_weekend"] = (days >= 5).astype(float)

        df["used_lag_1"] = df["used_bytes"].shift(1)
        df["utilization_lag_1"] = (df["used_lag_1"] / df["total_capacity_bytes"].replace(0, np.nan)) * 100.0

        delta_series = df["used_bytes"].diff()
        df["y_delta"] = delta_series
        df["delta_lag_1"] = delta_series.shift(1)
        df["delta_lag_6"] = delta_series.shift(6)
        df["delta_lag_24"] = delta_series.shift(24)
        df["roll_mean_delta_6"] = delta_series.shift(1).rolling(6).mean()
        df["roll_mean_delta_24"] = delta_series.shift(1).rolling(24).mean()
        df["roll_std_delta_24"] = delta_series.shift(1).rolling(24).std().fillna(0.0)

        feat_cols = list(cls.BASE_FEATURES)
        # Include performance features only when historical non-null density >= 80%
        if df["read_iops"].notna().mean() >= 0.8 and df["write_iops"].notna().mean() >= 0.8:
            df["read_iops_lag_1"] = df["read_iops"].shift(1).ffill()
            df["write_iops_lag_1"] = df["write_iops"].shift(1).ffill()
            df["latency_lag_1"] = df["latency_p95_ms"].shift(1).ffill()
            if df[cls.PERF_FEATURES].notna().all(axis=1).mean() >= 0.8:
                feat_cols.extend(cls.PERF_FEATURES)

        valid_mask = df[feat_cols].notna().all(axis=1) & df["y_delta"].notna() & df["used_bytes"].notna()
        valid_df = df.loc[valid_mask].reset_index(drop=True)

        return (
            valid_df[feat_cols],
            valid_df["y_delta"],
            valid_df["used_bytes"],
            feat_cols,
        )


class CapacityMLEngine:
    """
    AEGISSTOR Module 5 & 6 — Dual-Algorithm Scikit-Learn Capacity ML Engine.
    Strictly implements two algorithms:
      - Model A: RandomForestRegressor
      - Model B: HistGradientBoostingRegressor
    Persists artifacts via joblib, compares chronological validation metrics,
    selects the best performing model, and forecasts 7/30/90-day capacity + runway.
    """

    ALGORITHMS = ("RandomForestRegressor", "HistGradientBoostingRegressor")

    @classmethod
    def _build_estimator(cls, algorithm: str):
        if algorithm == "RandomForestRegressor":
            return RandomForestRegressor(
                n_estimators=80,
                max_depth=10,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
        if algorithm == "HistGradientBoostingRegressor":
            return HistGradientBoostingRegressor(
                max_iter=100,
                learning_rate=0.08,
                max_leaf_nodes=15,
                min_samples_leaf=5,
                random_state=42,
            )
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    @classmethod
    def train_and_evaluate(
        cls,
        db: Session,
        storage_id: str,
        trained_by: str = "system"
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage resource '{storage_id}' not found")

        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        if len(records) < MIN_TRAINING_RECORDS:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "storage_id": storage_id,
                "records_found": len(records),
                "records_required": MIN_TRAINING_RECORDS,
                "missing_records": MIN_TRAINING_RECORDS - len(records),
                "message": (
                    f"Insufficient historical telemetry for '{storage_id}': found {len(records)} observations, "
                    f"minimum {MIN_TRAINING_RECORDS} chronological hourly records required before training. "
                    "Existing active models (if any) were preserved."
                ),
                "models": [],
                "selected_model": None,
            }

        X, y_delta, y_actual, feat_cols = LeakFreeFeatureBuilder.build_training_dataset(
            records, device.total_capacity_bytes
        )

        if len(X) < 20:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "storage_id": storage_id,
                "records_found": len(records),
                "post_lag_rows": len(X),
                "records_required": MIN_TRAINING_RECORDS,
                "message": "Insufficient valid non-null chronological feature rows after 24h lag extraction.",
                "models": [],
                "selected_model": None,
            }

        # Chronological train/validation split (80% train, 20% future holdout — NEVER shuffled)
        split_idx = max(12, int(len(X) * 0.8))
        if split_idx >= len(X) - 2:
            split_idx = len(X) - 3

        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_delta_train = y_delta.iloc[:split_idx]
        y_actual_val = y_actual.iloc[split_idx:].values
        base_val = X_val["used_lag_1"].values

        _ensure_artifacts_dir()
        ts_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        train_start = records[0].timestamp
        train_end = records[-1].timestamp

        candidates = []
        try:
            for algo in cls.ALGORITHMS:
                est = cls._build_estimator(algo)
                est.fit(X_train, y_delta_train)

                pred_delta_val = est.predict(X_val)
                pred_bytes_val = np.clip(base_val + pred_delta_val, 0.0, float(device.total_capacity_bytes))

                mae = float(mean_absolute_error(y_actual_val, pred_bytes_val))
                rmse = float(root_mean_squared_error(y_actual_val, pred_bytes_val))
                r2 = float(r2_score(y_actual_val, pred_bytes_val)) if len(y_actual_val) >= 2 and np.std(y_actual_val) > 0 else None
                mape = (
                    float(np.mean(np.abs((y_actual_val - pred_bytes_val) / y_actual_val)) * 100.0)
                    if np.all(y_actual_val > 0)
                    else None
                )
                residual_std = float(np.std(y_actual_val - pred_bytes_val))

                version_tag = f"v{ts_tag}"
                model_id = f"mv-{storage_id[:16]}-{algo[:6].lower()}-{uuid.uuid4().hex[:6]}"
                artifact_file = os.path.join(ARTIFACTS_DIR, f"{model_id}.joblib")

                bundle = {
                    "estimator": est,
                    "algorithm": algo,
                    "storage_id": storage_id,
                    "version": version_tag,
                    "feature_version": FEATURE_VERSION,
                    "feature_columns": feat_cols,
                    "residual_std": residual_std,
                    "trained_at": utc_now().isoformat(),
                }
                joblib.dump(bundle, artifact_file)
                from app.services.object_storage import object_storage
                artifact_uri, artifact_sha256 = object_storage.put_file(
                    artifact_file, category="models", filename=os.path.basename(artifact_file)
                )

                candidates.append({
                    "model_id": model_id,
                    "algorithm": algo,
                    "version": version_tag,
                    "artifact_path": artifact_file,
                    "artifact_uri": artifact_uri,
                    "artifact_sha256": artifact_sha256,
                    "mae": round(mae, 2),
                    "rmse": round(rmse, 2),
                    "r2_score": round(r2, 4) if r2 is not None else None,
                    "mape": round(mape, 4) if mape is not None else None,
                    "residual_std": round(residual_std, 2),
                })
        except Exception as exc:
            # Atomic protection: do NOT alter active working models if training fails
            failed_mv = ModelVersion(
                id=f"mv-err-{uuid.uuid4().hex[:8]}",
                storage_id=storage_id,
                name=f"Failed Training ({storage_id})",
                model_type="TrainingFailure",
                version_tag=f"v{ts_tag}",
                feature_version=FEATURE_VERSION,
                train_samples_count=len(X_train),
                validation_samples=len(X_val),
                is_active=False,
                status="FAILED",
                error_message=str(exc),
                trained_by=trained_by,
            )
            db.add(failed_mv)
            db.commit()
            return {
                "status": "TRAINING_FAILED",
                "storage_id": storage_id,
                "error": str(exc),
                "message": "Model training failed; existing working model was preserved.",
            }

        # Compare validation RMSE (lowest wins)
        best = min(candidates, key=lambda c: (c["rmse"], c["mae"]))

        # Deactivate previous active models for this storage resource only after new models succeed
        db.query(ModelVersion).filter(ModelVersion.storage_id == storage_id, ModelVersion.is_active == True).update({"is_active": False})

        persisted_summaries = []
        for cand in candidates:
            is_winner = cand["model_id"] == best["model_id"]
            mv = ModelVersion(
                id=cand["model_id"],
                storage_id=storage_id,
                name=f"{cand['algorithm']} ({storage_id})",
                model_type=cand["algorithm"],
                version_tag=cand["version"],
                feature_schema_json=json.dumps({
                    "features": feat_cols,
                    "artifact_uri": cand.get("artifact_uri"),
                    "artifact_sha256": cand.get("artifact_sha256"),
                }),
                feature_version=FEATURE_VERSION,
                artifact_path=cand["artifact_path"],
                target_metric="used_bytes",
                train_samples_count=len(X_train),
                validation_samples=len(X_val),
                train_start_at=train_start,
                train_end_at=train_end,
                mae=cand["mae"],
                rmse=cand["rmse"],
                interval_coverage=0.80,
                is_active=is_winner,
                status="TRAINED",
                trained_by=trained_by,
            )
            db.add(mv)
            db.flush()

            mm = ModelMetric(
                id=f"mm-{uuid.uuid4().hex[:10]}",
                model_version_id=mv.id,
                storage_id=storage_id,
                mae=cand["mae"],
                rmse=cand["rmse"],
                r2_score=cand["r2_score"],
                mape=cand["mape"],
                residual_std=cand["residual_std"],
                is_selected=is_winner,
                selection_reason=(
                    f"Lowest chronological validation RMSE ({cand['rmse']:,.2f} bytes)"
                    if is_winner
                    else f"Higher validation RMSE ({cand['rmse']:,.2f} vs {best['rmse']:,.2f} bytes)"
                ),
            )
            db.add(mm)
            persisted_summaries.append({
                "model_version_id": mv.id,
                "algorithm": cand["algorithm"],
                "version": cand["version"],
                "feature_version": FEATURE_VERSION,
                "training_samples": len(X_train),
                "validation_samples": len(X_val),
                "mae_bytes": cand["mae"],
                "rmse_bytes": cand["rmse"],
                "r2_score": cand["r2_score"],
                "mape_pct": cand["mape"],
                "is_selected": is_winner,
                "selection_reason": mm.selection_reason,
                "artifact_saved": os.path.exists(cand["artifact_path"]),
            })

        db.commit()

        return {
            "status": "TRAINED",
            "storage_id": storage_id,
            "train_range": {
                "start": train_start.isoformat() if train_start else None,
                "end": train_end.isoformat() if train_end else None,
                "training_samples": len(X_train),
                "validation_samples": len(X_val),
            },
            "feature_version": FEATURE_VERSION,
            "selected_model": next(p for p in persisted_summaries if p["is_selected"]),
            "models": persisted_summaries,
        }

    @classmethod
    def get_active_model(cls, db: Session, storage_id: str) -> Optional[ModelVersion]:
        return (
            db.query(ModelVersion)
            .filter(
                ModelVersion.storage_id == storage_id,
                ModelVersion.is_active == True,
                ModelVersion.status == "TRAINED",
            )
            .order_by(ModelVersion.trained_at.desc())
            .first()
        )

    @classmethod
    def predict_capacity(
        cls,
        db: Session,
        storage_id: str,
        horizon_days: int = 30,
        auto_train_if_missing: bool = False
    ) -> Dict[str, Any]:
        if horizon_days not in (7, 30, 90) and (horizon_days < 1 or horizon_days > 365):
            raise ValueError("horizon_days must be between 1 and 365 (standard horizons: 7, 30, 90)")

        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage resource '{storage_id}' not found")

        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        if len(records) < MIN_TRAINING_RECORDS:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "storage_id": storage_id,
                "records_found": len(records),
                "records_required": MIN_TRAINING_RECORDS,
                "message": f"Cannot generate ML forecast: need {MIN_TRAINING_RECORDS} records, found {len(records)}.",
            }

        mv = cls.get_active_model(db, storage_id)
        if not mv or not mv.artifact_path or not os.path.exists(mv.artifact_path):
            if auto_train_if_missing:
                train_res = cls.train_and_evaluate(db, storage_id)
                if train_res.get("status") != "TRAINED":
                    return train_res
                mv = cls.get_active_model(db, storage_id)
            else:
                return {
                    "status": "MODEL_NOT_TRAINED",
                    "storage_id": storage_id,
                    "message": f"No trained model artifact found for '{storage_id}'. Run model training first.",
                }

        t0 = time.perf_counter()
        from app.services.object_storage import object_storage
        schema_meta = {}
        try:
            parsed = json.loads(mv.feature_schema_json or "{}")
            if isinstance(parsed, dict):
                schema_meta = parsed
        except Exception:
            schema_meta = {}
        local_artifact = object_storage.ensure_local_file(
            mv.artifact_path,
            remote_uri=schema_meta.get("artifact_uri"),
            expected_sha256=schema_meta.get("artifact_sha256"),
        )
        bundle = joblib.load(local_artifact)
        estimator = bundle["estimator"]
        feat_cols = bundle["feature_columns"]
        residual_std = float(bundle.get("residual_std", 0.0))

        # Prepare current rolling state from latest telemetry
        X_hist, y_delta_hist, y_actual_hist, _ = LeakFreeFeatureBuilder.build_training_dataset(
            records, device.total_capacity_bytes
        )
        if X_hist.empty:
            return {
                "status": "INSUFFICIENT_HISTORY",
                "storage_id": storage_id,
                "message": "Not enough post-lag observations to construct forecast input state.",
            }

        latest_rec = records[-1]
        latest_ts = latest_rec.timestamp.replace(tzinfo=None) if latest_rec.timestamp.tzinfo else latest_rec.timestamp
        total_cap = float(device.total_capacity_bytes)
        current_used = float(latest_rec.used_bytes)

        # Recent delta deque for autoregressive step prediction
        delta_buf = list(y_delta_hist.iloc[-25:].values)
        last_perf = {
            "read_iops_lag_1": float(latest_rec.read_iops or 0.0),
            "write_iops_lag_1": float(latest_rec.write_iops or 0.0),
            "latency_lag_1": float(latest_rec.latency_p95_ms or 0.0),
        }

        total_hours = horizon_days * 24
        acc_unconstrained = current_used
        daily_predictions: List[Dict[str, Any]] = []
        breach_detected = False
        breach_ts: Optional[datetime] = None

        hourly_ts_list = []
        hourly_q10 = []
        hourly_q50 = []
        hourly_q90 = []

        for h in range(1, total_hours + 1):
            t_next = latest_ts + timedelta(hours=h)
            row_dict = {
                "hour_sin": math.sin(2.0 * math.pi * t_next.hour / 24.0),
                "hour_cos": math.cos(2.0 * math.pi * t_next.hour / 24.0),
                "day_sin": math.sin(2.0 * math.pi * t_next.weekday() / 7.0),
                "day_cos": math.cos(2.0 * math.pi * t_next.weekday() / 7.0),
                "is_weekend": 1.0 if t_next.weekday() >= 5 else 0.0,
                "used_lag_1": min(total_cap, max(0.0, acc_unconstrained)),
                "utilization_lag_1": (min(total_cap, max(0.0, acc_unconstrained)) / total_cap) * 100.0 if total_cap > 0 else 0.0,
                "delta_lag_1": float(delta_buf[-1]) if len(delta_buf) >= 1 else 0.0,
                "delta_lag_6": float(delta_buf[-6]) if len(delta_buf) >= 6 else float(delta_buf[-1]),
                "delta_lag_24": float(delta_buf[-24]) if len(delta_buf) >= 24 else float(delta_buf[0]),
                "roll_mean_delta_6": float(np.mean(delta_buf[-6:])),
                "roll_mean_delta_24": float(np.mean(delta_buf[-24:])),
                "roll_std_delta_24": float(np.std(delta_buf[-24:])) if len(delta_buf) >= 2 else 0.0,
                **last_perf,
            }
            feat_df = pd.DataFrame([{c: row_dict[c] for c in feat_cols}])
            step_delta = float(estimator.predict(feat_df)[0])
            acc_unconstrained = max(0.0, acc_unconstrained + step_delta)
            delta_buf.append(step_delta)
            if len(delta_buf) > 48:
                delta_buf.pop(0)

            if acc_unconstrained >= total_cap and not breach_detected:
                breach_detected = True
                breach_ts = t_next

            # Constrained physical output [0, total_capacity_bytes]
            constrained = max(0.0, min(total_cap, acc_unconstrained))
            spread = 1.645 * max(residual_std, 1.0) * math.sqrt(h / 24.0 + 1.0)
            q10_val = max(0.0, constrained - spread)
            q90_val = min(total_cap, constrained + spread)

            hourly_ts_list.append(t_next.isoformat())
            hourly_q10.append(round(q10_val, 2))
            hourly_q50.append(round(constrained, 2))
            hourly_q90.append(round(q90_val, 2))

            if h % 24 == 0:
                day_num = h // 24
                util_pct = round((constrained / total_cap) * 100.0, 2) if total_cap > 0 else 0.0
                daily_predictions.append({
                    "day": day_num,
                    "timestamp": t_next.isoformat(),
                    "predicted_used_bytes": int(round(constrained)),
                    "predicted_free_bytes": int(round(max(0.0, total_cap - constrained))),
                    "predicted_utilization_pct": util_pct,
                    "lower_bound_bytes": int(round(q10_val)),
                    "upper_bound_bytes": int(round(q90_val)),
                    "unconstrained_exceeds_capacity": acc_unconstrained > total_cap,
                })

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        gen_time = utc_now()

        # Fetch validation metric for this model
        mm = db.query(ModelMetric).filter(ModelMetric.model_version_id == mv.id).first()
        val_metrics = {
            "mae_bytes": mm.mae if mm else mv.mae,
            "rmse_bytes": mm.rmse if mm else mv.rmse,
            "r2_score": mm.r2_score if mm else None,
            "mape_pct": mm.mape if mm else None,
        }

        # Persist forecast in database
        forecast_row = Forecast(
            device_id=storage_id,
            model_name=f"{mv.model_type} ({mv.version_tag})",
            model_version_id=mv.id,
            target_metric="used_bytes",
            horizon_hours=total_hours,
            horizon_days=horizon_days,
            generated_at=gen_time,
            historical_cutoff=latest_ts,
            timestamps_json=json.dumps(hourly_ts_list),
            q10_json=json.dumps(hourly_q10),
            q50_json=json.dumps(hourly_q50),
            q90_json=json.dumps(hourly_q90),
            daily_predictions_json=json.dumps(daily_predictions),
            projected_capacity_breach=breach_detected,
            breach_timestamp=breach_ts,
            interval_coverage=0.80,
            inference_ms=elapsed_ms,
        )
        db.add(forecast_row)
        db.commit()
        db.refresh(forecast_row)

        runway = cls.calculate_capacity_runway(
            device=device,
            current_used_bytes=int(current_used),
            daily_predictions=daily_predictions,
            records=records,
            safety_threshold_pct=device.critical_threshold_pct,
        )

        return {
            "status": "OK",
            "forecast_id": forecast_row.id,
            "storage_id": storage_id,
            "model_used": mv.model_type,
            "model_version": mv.version_tag,
            "model_version_id": mv.id,
            "horizon_days": horizon_days,
            "generated_at": gen_time.isoformat(),
            "historical_cutoff": latest_ts.isoformat(),
            "current_used_bytes": int(current_used),
            "current_free_bytes": int(max(0, total_cap - current_used)),
            "current_utilization_pct": round((current_used / total_cap) * 100.0, 2) if total_cap > 0 else 0.0,
            "total_capacity_bytes": int(total_cap),
            "validation_metrics": val_metrics,
            "projected_capacity_breach": breach_detected,
            "breach_timestamp": breach_ts.isoformat() if breach_ts else None,
            "daily_predictions": daily_predictions,
            "runway_analysis": runway,
            "inference_ms": elapsed_ms,
            "is_estimate": True,
            "disclaimer": "Predictions are statistical ML estimates based on persisted historical consumption and are not operational guarantees.",
        }

    @classmethod
    def calculate_capacity_runway(
        cls,
        device: Device,
        current_used_bytes: int,
        daily_predictions: Optional[List[Dict[str, Any]]] = None,
        records: Optional[List[Telemetry]] = None,
        safety_threshold_pct: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates safe capacity runway using documented rules:
          Remaining Safe Capacity = (Total Capacity * Safety Threshold) - Current Used Capacity
          Estimated Runway = Remaining Safe Capacity / Estimated Daily Consumption Growth
        Handles zero or negative growth cleanly without returning negative or infinite days.
        """
        total_cap = float(device.total_capacity_bytes)
        threshold_pct = float(safety_threshold_pct if safety_threshold_pct is not None else device.critical_threshold_pct)
        safe_ceiling_bytes = total_cap * (threshold_pct / 100.0)
        remaining_safe_bytes = safe_ceiling_bytes - float(current_used_bytes)
        current_util = round((current_used_bytes / total_cap) * 100.0, 2) if total_cap > 0 else 0.0

        # Estimate daily growth in bytes/day
        daily_growth_bytes = 0.0
        growth_source = "observed_trend"
        if daily_predictions and len(daily_predictions) >= 1:
            horizon_n = len(daily_predictions)
            end_used = float(daily_predictions[-1]["predicted_used_bytes"])
            daily_growth_bytes = (end_used - float(current_used_bytes)) / float(horizon_n)
            growth_source = "ml_forecast"
        elif records and len(records) >= 2:
            window = records[-min(len(records), 168):]
            span_days = max(1.0 / 24.0, (window[-1].timestamp - window[0].timestamp).total_seconds() / 86400.0)
            daily_growth_bytes = float(window[-1].used_bytes - window[0].used_bytes) / span_days

        # Determine risk category
        if current_util >= device.critical_threshold_pct or remaining_safe_bytes <= 0:
            risk_category = "CRITICAL"
        elif current_util >= device.warning_threshold_pct:
            risk_category = "WARNING"
        else:
            risk_category = "NORMAL"

        now = utc_now()
        if remaining_safe_bytes <= 0:
            return {
                "safety_threshold_pct": threshold_pct,
                "safe_capacity_ceiling_bytes": int(safe_ceiling_bytes),
                "remaining_safe_capacity_bytes": int(remaining_safe_bytes),
                "estimated_daily_growth_bytes": round(daily_growth_bytes, 2),
                "estimated_daily_growth_gb": round(daily_growth_bytes / (1024 ** 3), 4),
                "growth_source": growth_source,
                "runway_status": "THRESHOLD_BREACHED",
                "estimated_days_until_threshold": 0.0,
                "estimated_threshold_date": now.isoformat(),
                "risk_category": "CRITICAL",
                "is_estimate": True,
                "note": "Current used capacity already meets or exceeds the configured safety threshold.",
            }

        if daily_growth_bytes <= 1.0:  # Zero or negative growth
            return {
                "safety_threshold_pct": threshold_pct,
                "safe_capacity_ceiling_bytes": int(safe_ceiling_bytes),
                "remaining_safe_capacity_bytes": int(remaining_safe_bytes),
                "estimated_daily_growth_bytes": round(daily_growth_bytes, 2),
                "estimated_daily_growth_gb": round(daily_growth_bytes / (1024 ** 3), 4),
                "growth_source": growth_source,
                "runway_status": "STABLE_OR_SHRINKING",
                "estimated_days_until_threshold": None,
                "estimated_threshold_date": None,
                "risk_category": risk_category,
                "is_estimate": True,
                "note": "Zero or negative net daily capacity growth detected; threshold breach is not projected.",
            }

        est_days = round(remaining_safe_bytes / daily_growth_bytes, 1)
        # Escalate risk if runway < 14 days (CRITICAL) or < 30 days (WARNING)
        if est_days <= 14.0:
            risk_category = "CRITICAL"
        elif est_days <= 30.0 and risk_category == "NORMAL":
            risk_category = "WARNING"

        est_date = now + timedelta(days=min(est_days, 3650.0))
        return {
            "safety_threshold_pct": threshold_pct,
            "safe_capacity_ceiling_bytes": int(safe_ceiling_bytes),
            "remaining_safe_capacity_bytes": int(remaining_safe_bytes),
            "estimated_daily_growth_bytes": round(daily_growth_bytes, 2),
            "estimated_daily_growth_gb": round(daily_growth_bytes / (1024 ** 3), 4),
            "growth_source": growth_source,
            "runway_status": "PROJECTED_GROWTH",
            "estimated_days_until_threshold": est_days,
            "estimated_threshold_date": est_date.isoformat(),
            "risk_category": risk_category,
            "is_estimate": True,
            "note": f"Estimated from {growth_source}; subject to workload variance.",
        }
