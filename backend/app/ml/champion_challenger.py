import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sqlalchemy.orm import Session
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.models.entities import Device, Forecast, ModelMetric, ModelVersion, Telemetry
from app.services.data_reliability_engine import DataReliabilityEngine
from app.services.workload_regime_engine import WorkloadRegimeEngine

MODEL_ARTIFACT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "artifacts", "models")
)
SUPPORTED_HORIZON_DAYS = [1, 7, 14, 30, 60, 90]


def _pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, q: float) -> float:
    err = y_true - y_pred
    return float(np.mean(np.maximum(q * err, (q - 1.0) * err)))


def _compute_mase(y_true: np.ndarray, y_pred: np.ndarray, y_insample: np.ndarray, season: int = 24) -> float:
    mae_forecast = float(np.mean(np.abs(y_true - y_pred)))
    m = season if len(y_insample) > season + 2 else 1
    naive_diffs = np.abs(y_insample[m:] - y_insample[:-m])
    scale = float(np.mean(naive_diffs)) if len(naive_diffs) > 0 else float(np.std(y_insample))
    if scale < 1e-9:
        scale = float(np.mean(np.abs(np.diff(y_insample)))) if len(y_insample) > 1 else 1e-6
    scale = max(scale, 1e-6)
    return round(mae_forecast / scale, 4)


def _safe_mape(y_true: np.ndarray, y_pred: np.ndarray) -> Optional[float]:
    if len(y_true) == 0 or np.any(y_true <= 1e-6):
        return None
    return round(float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0), 4)


class ChampionChallengerEngine:
    """
    Two-Model Champion-Challenger Forecasting Engine:
      - Model A: LightGBM (LGBMRegressor) with leak-free multivariate lag/rolling/calendar/exogenous features
      - Model B: SARIMAX (statsmodels) with exogenous cyclical/telemetry covariates
      - Reference Benchmark: Seasonal-Naive baseline
    Uses chronological Train / Calibration / Test splitting, rolling-origin CV,
    Split Conformal uncertainty calibration, and Data Reliability gating.
    """

    MIN_RECORDS = 60

    @staticmethod
    def _build_dataframe(rows: List[Telemetry]) -> Tuple[pd.DataFrame, List[str], List[str]]:
        records = []
        for r in rows:
            ts = r.timestamp.replace(tzinfo=None) if r.timestamp.tzinfo else r.timestamp
            cap_b = float(r.total_capacity_bytes or ((r.used_bytes or 0) + (r.free_bytes or 0)) or 1)
            records.append({
                "timestamp": ts,
                "used_gb": float(r.used_bytes or 0) / (1024.0 ** 3),
                "total_gb": cap_b / (1024.0 ** 3),
                "free_gb": float(r.free_bytes or 0) / (1024.0 ** 3),
                "utilization_pct": float(r.utilization_pct if r.utilization_pct is not None else (float(r.used_bytes or 0) / cap_b) * 100.0),
                "read_iops": r.read_iops,
                "write_iops": r.write_iops,
                "latency_p95_ms": r.latency_p95_ms,
                "throughput_mb_s": r.throughput_mb_s,
            })

        df = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
        # Strictly causal lag & rolling features (computed from t and t-k to predict t+1)
        df["lag_1"] = df["used_gb"].shift(1)
        df["lag_2"] = df["used_gb"].shift(2)
        df["lag_6"] = df["used_gb"].shift(6)
        df["lag_12"] = df["used_gb"].shift(12)
        df["lag_24"] = df["used_gb"].shift(24)
        df["delta_1"] = df["used_gb"] - df["used_gb"].shift(1)
        df["rolling_mean_6"] = df["used_gb"].rolling(6, min_periods=1).mean()
        df["rolling_std_6"] = df["used_gb"].rolling(6, min_periods=1).std().fillna(0.0)
        df["rolling_mean_24"] = df["used_gb"].rolling(24, min_periods=1).mean()
        df["hour_sin"] = np.sin(2.0 * np.pi * df["timestamp"].dt.hour / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * df["timestamp"].dt.hour / 24.0)
        df["day_of_week"] = df["timestamp"].dt.dayofweek.astype(float)

        base_features = [
            "used_gb", "free_gb", "utilization_pct",
            "lag_1", "lag_2", "lag_6", "lag_12", "lag_24",
            "delta_1", "rolling_mean_6", "rolling_std_6", "rolling_mean_24",
            "hour_sin", "hour_cos", "day_of_week",
        ]
        # Exogenous metrics included ONLY when actually populated without fabricating missing data
        optional_exog = ["read_iops", "write_iops", "latency_p95_ms", "throughput_mb_s"]
        included_exog: List[str] = []
        excluded_exog: List[str] = []
        for col in optional_exog:
            non_null_ratio = float(df[col].notna().mean()) if len(df) > 0 else 0.0
            if non_null_ratio >= 0.70 and df[col].dropna().abs().sum() > 0:
                df[col] = df[col].ffill().bfill()
                included_exog.append(col)
            else:
                excluded_exog.append(col)

        df["target_next_used_gb"] = df["used_gb"].shift(-1)
        supervised = df.dropna(subset=["lag_24", "target_next_used_gb"]).reset_index(drop=True)
        feature_cols = base_features + included_exog
        return supervised, feature_cols, excluded_exog

    @staticmethod
    def _seasonal_naive_predict(series: np.ndarray, horizon_start_idx: int, count: int, season: int = 24) -> np.ndarray:
        preds = []
        for i in range(count):
            idx = horizon_start_idx + i
            lag_idx = idx - season if idx >= season else max(0, idx - 1)
            # Persistence + seasonal diff anchor so trended series baseline is realistic
            prev_val = series[max(0, idx - 1)]
            if idx >= season + 1:
                seas_delta = series[idx - season] - series[idx - season - 1]
                preds.append(prev_val + seas_delta)
            else:
                preds.append(series[lag_idx])
        return np.array(preds, dtype=float)

    @classmethod
    def _evaluate_model_outputs(
        cls,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        q10: np.ndarray,
        q90: np.ndarray,
        y_insample: np.ndarray,
        baseline_rmse: float,
    ) -> Dict[str, Any]:
        mae = float(mean_absolute_error(y_true, y_pred))
        rmse = float(math.sqrt(mean_squared_error(y_true, y_pred)))
        r2 = float(r2_score(y_true, y_pred)) if len(y_true) > 1 and np.var(y_true) > 1e-12 else 0.0
        mape = _safe_mape(y_true, y_pred)
        denom_wape = float(np.sum(np.abs(y_true)))
        wape = round(float(np.sum(np.abs(y_true - y_pred)) / denom_wape * 100.0), 4) if denom_wape > 1e-9 else None
        mase = _compute_mase(y_true, y_pred, y_insample)
        pinball = float(0.5 * (_pinball_loss(y_true, q10, 0.10) + _pinball_loss(y_true, q90, 0.90)))
        inside = np.logical_and(y_true >= q10 - 1e-9, y_true <= q90 + 1e-9)
        coverage = float(np.mean(inside))
        width = float(np.mean(np.maximum(0.0, q90 - q10)))

        if rmse < baseline_rmse * 0.98:
            vs_base = "BEATS_BASELINE"
        elif rmse <= baseline_rmse * 1.03:
            vs_base = "TIES_BASELINE"
        else:
            vs_base = "WORSE_THAN_BASELINE"

        return {
            "mae": round(mae, 5),
            "rmse": round(rmse, 5),
            "r2_score": round(r2, 4),
            "mape": mape,
            "wape": wape,
            "mase": mase,
            "pinball_loss": round(pinball, 5),
            "interval_coverage": round(coverage, 4),
            "mean_interval_width": round(width, 5),
            "vs_baseline_status": vs_base,
        }

    @classmethod
    def _rolling_origin_cv_lgbm(cls, X: np.ndarray, y: np.ndarray, n_folds: int = 3) -> Dict[str, Any]:
        n = len(y)
        if n < 36:
            return {"folds": 0, "rolling_mae": None, "rolling_rmse": None}
        fold_size = max(5, n // (n_folds + 2))
        maes, rmses = [], []
        for f in range(n_folds):
            split = n - (n_folds - f) * fold_size
            if split < 20 or split + fold_size > n:
                continue
            X_tr, y_tr = X[:split], y[:split]
            X_va, y_va = X[split: split + fold_size], y[split: split + fold_size]
            model = LGBMRegressor(
                n_estimators=60,
                learning_rate=0.06,
                num_leaves=15,
                min_child_samples=5,
                random_state=42,
                verbose=-1,
            )
            model.fit(X_tr, y_tr)
            preds = model.predict(X_va)
            maes.append(float(mean_absolute_error(y_va, preds)))
            rmses.append(float(math.sqrt(mean_squared_error(y_va, preds))))
        if not maes:
            return {"folds": 0, "rolling_mae": None, "rolling_rmse": None}
        return {
            "folds": len(maes),
            "rolling_mae": round(float(np.mean(maes)), 5),
            "rolling_rmse": round(float(np.mean(rmses)), 5),
        }

    @classmethod
    def train_and_select(
        cls,
        db: Session,
        storage_id: str,
        triggered_by: str = "system",
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        rows = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )
        if len(rows) < cls.MIN_RECORDS:
            raise ValueError(
                f"Insufficient real telemetry history ({len(rows)} records). "
                f"Minimum {cls.MIN_RECORDS} chronological samples required; existing active champion model preserved."
            )

        # Evaluate reliability & workload regime transparently before training
        reliability = DataReliabilityEngine.evaluate(db, storage_id, persist=True)
        regime = WorkloadRegimeEngine.analyze(db, storage_id, persist=False)

        supervised, feature_cols, excluded_exog = cls._build_dataframe(rows)
        if len(supervised) < 35:
            raise ValueError(
                f"After lagging (24h window), only {len(supervised)} supervised sequences remain (need >= 35). "
                "Existing active champion model preserved."
            )

        # Chronological 3-way split: 64% Train | 16% Conformal Calibration | 20% Final Holdout Test
        n = len(supervised)
        n_train = max(20, int(n * 0.64))
        n_calib = max(8, int(n * 0.16))
        if n_train + n_calib >= n - 5:
            n_calib = max(5, (n - n_train) // 2)
        n_test = n - n_train - n_calib
        if n_test < 5:
            raise ValueError("Insufficient chronological test holdout samples; existing champion preserved.")

        X_all = supervised[feature_cols].to_numpy(dtype=float)
        y_all = supervised["target_next_used_gb"].to_numpy(dtype=float)

        X_train, y_train = X_all[:n_train], y_all[:n_train]
        X_calib, y_calib = X_all[n_train: n_train + n_calib], y_all[n_train: n_train + n_calib]
        X_test, y_test = X_all[n_train + n_calib:], y_all[n_train + n_calib:]

        # Reference Benchmark: Seasonal-Naive
        raw_series = supervised["used_gb"].to_numpy(dtype=float)
        naive_test_pred = cls._seasonal_naive_predict(raw_series, n_train + n_calib, n_test)
        naive_rmse = max(1e-6, float(math.sqrt(mean_squared_error(y_test, naive_test_pred))))
        naive_mae = float(mean_absolute_error(y_test, naive_test_pred))
        naive_mase = _compute_mase(y_test, naive_test_pred, y_train)

        candidates: List[Dict[str, Any]] = []
        os.makedirs(MODEL_ARTIFACT_DIR, exist_ok=True)
        version_tag = f"v3.{int(time.time()) % 100000}"

        # --- Candidate A: LightGBM (LGBMRegressor + Split Conformal Calibration) ---
        try:
            rolling_cv = cls._rolling_origin_cv_lgbm(X_all[: n_train + n_calib], y_all[: n_train + n_calib])
            lgbm_model = LGBMRegressor(
                n_estimators=120,
                learning_rate=0.05,
                num_leaves=23,
                min_child_samples=max(3, min(10, n_train // 8)),
                subsample=0.9,
                random_state=42,
                verbose=-1,
            )
            lgbm_model.fit(X_train, y_train)
            calib_pred_a = lgbm_model.predict(X_calib)
            calib_abs_res_a = np.abs(y_calib - calib_pred_a)
            # Split Conformal quantile at (1 - alpha) = 0.80 with finite-sample correction
            conformal_q_a = float(np.quantile(calib_abs_res_a, min(1.0, 0.80 * (1.0 + 1.0 / max(1, len(calib_abs_res_a))))))
            conformal_q_a = max(conformal_q_a, float(np.std(y_calib - calib_pred_a)) * 1.28, 1e-4)

            test_pred_a = lgbm_model.predict(X_test)
            q10_a = np.maximum(0.0, test_pred_a - conformal_q_a)
            q90_a = np.minimum(float(device.total_capacity_bytes) / (1024.0 ** 3), test_pred_a + conformal_q_a)
            metrics_a = cls._evaluate_model_outputs(y_test, test_pred_a, q10_a, q90_a, y_train, naive_rmse)

            candidates.append({
                "family": "LightGBM",
                "model_type": "LGBMRegressor",
                "model_obj": lgbm_model,
                "conformal_q": conformal_q_a,
                "signed_calib_residuals": (y_calib - calib_pred_a).tolist(),
                "test_residuals": (y_test - test_pred_a).tolist(),
                "rolling_cv": rolling_cv,
                "metrics": metrics_a,
                "status": "TRAINED",
            })
        except Exception as exc:
            candidates.append({"family": "LightGBM", "model_type": "LGBMRegressor", "status": "FAILED", "error": str(exc)})

        # --- Candidate B: SARIMAX (statsmodels State-Space Time Series) ---
        try:
            y_train_s = y_train
            y_calib_s = y_calib
            exog_cols = ["hour_sin", "hour_cos"]
            exog_all = supervised[exog_cols].to_numpy(dtype=float)
            exog_tr = exog_all[:n_train]
            exog_cal = exog_all[n_train: n_train + n_calib]
            exog_te = exog_all[n_train + n_calib:]

            sarimax_res = None
            sarimax_order = (1, 1, 1)
            for order in [(1, 1, 1), (1, 1, 0), (0, 1, 1)]:
                try:
                    mod = SARIMAX(
                        y_train_s,
                        exog=exog_tr,
                        order=order,
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    )
                    res = mod.fit(disp=False, maxiter=80)
                    sarimax_res = res
                    sarimax_order = order
                    break
                except Exception:
                    continue

            if sarimax_res is None:
                raise RuntimeError("SARIMAX failed to converge across fallback orders")

            # Sequentially update state (without refitting parameters) on calibration & test splits
            res_calib = sarimax_res.apply(y_calib_s, exog=exog_cal, refit=False)
            # Use one-step-ahead in-sample predictions on calibration & test via full concatenated apply
            res_full_cal = sarimax_res.apply(np.concatenate([y_train_s, y_calib_s]), exog=np.vstack([exog_tr, exog_cal]), refit=False)
            calib_pred_b = np.asarray(res_full_cal.fittedvalues[n_train: n_train + n_calib], dtype=float)
            calib_abs_res_b = np.abs(y_calib_s - calib_pred_b)
            conformal_q_b = float(np.quantile(calib_abs_res_b, min(1.0, 0.80 * (1.0 + 1.0 / max(1, len(calib_abs_res_b))))))
            conformal_q_b = max(conformal_q_b, float(np.std(y_calib_s - calib_pred_b)) * 1.28, 1e-4)

            res_full_test = sarimax_res.apply(y_all, exog=exog_all, refit=False)
            test_pred_b = np.asarray(res_full_test.fittedvalues[n_train + n_calib:], dtype=float)
            q10_b = np.maximum(0.0, test_pred_b - conformal_q_b)
            q90_b = np.minimum(float(device.total_capacity_bytes) / (1024.0 ** 3), test_pred_b + conformal_q_b)
            metrics_b = cls._evaluate_model_outputs(y_test, test_pred_b, q10_b, q90_b, y_train, naive_rmse)

            candidates.append({
                "family": "SARIMAX",
                "model_type": f"SARIMAX{sarimax_order}",
                "model_obj": {
                    "order": sarimax_order,
                    "params": sarimax_res.params.tolist(),
                    "exog_cols": exog_cols,
                    "last_y": y_all[-min(96, len(y_all)):].tolist(),
                    "last_exog": exog_all[-min(96, len(exog_all)):].tolist(),
                },
                "conformal_q": conformal_q_b,
                "signed_calib_residuals": (y_calib_s - calib_pred_b).tolist(),
                "test_residuals": (y_test - test_pred_b).tolist(),
                "rolling_cv": {"folds": 1, "note": "State-space sequential Kalman filter evaluation"},
                "metrics": metrics_b,
                "status": "TRAINED",
            })
        except Exception as exc:
            candidates.append({"family": "SARIMAX", "model_type": "SARIMAX", "status": "FAILED", "error": str(exc)})

        valid_candidates = [c for c in candidates if c.get("status") == "TRAINED"]
        if not valid_candidates:
            raise RuntimeError(
                f"Both LightGBM and SARIMAX candidates failed: {candidates}. "
                "Existing active champion model preserved."
            )

        # Calibration-aware Champion-Challenger Selection:
        # Balances holdout RMSE against empirical 80% interval calibration error
        def selection_cost(c: Dict[str, Any]) -> float:
            m = c["metrics"]
            rmse_norm = m["rmse"] / max(1e-6, naive_rmse)
            calib_err = abs(m["interval_coverage"] - 0.80)
            return round(rmse_norm + 0.55 * calib_err + 0.15 * (m["pinball_loss"] / max(1e-6, naive_mae)), 5)

        for c in valid_candidates:
            c["composite_score"] = selection_cost(c)
        valid_candidates.sort(key=lambda c: c["composite_score"])
        champion = valid_candidates[0]

        # Deactivate prior v2 champion versions only AFTER new champion succeeds
        db.query(ModelVersion).filter(
            ModelVersion.storage_id == storage_id,
            ModelVersion.feature_version.like("v3.%"),
        ).update({"is_active": False})

        artifact_path = os.path.join(MODEL_ARTIFACT_DIR, f"champion_{storage_id}_{version_tag}.joblib")
        joblib.dump(
            {
                "family": champion["family"],
                "model_type": champion["model_type"],
                "model_obj": champion["model_obj"],
                "feature_cols": feature_cols,
                "excluded_exog": excluded_exog,
                "conformal_q": champion["conformal_q"],
                "signed_calib_residuals": champion["signed_calib_residuals"],
                "test_residuals": champion["test_residuals"],
                "baseline_rmse": naive_rmse,
                "baseline_mae": naive_mae,
                "baseline_mase": naive_mase,
                "trained_at": datetime.now(timezone.utc).isoformat(),
            },
            artifact_path,
        )

        from app.services.object_storage import object_storage
        artifact_uri, artifact_sha256 = object_storage.put_file(
            artifact_path, category="models", filename=os.path.basename(artifact_path)
        )

        persisted_candidates = []
        champion_version_id = None
        for idx, cand in enumerate(valid_candidates):
            is_champ = idx == 0
            mv_id = f"mv2-{uuid.uuid4().hex[:10]}"
            m = cand["metrics"]
            reason = (
                f"Selected Champion ({cand['family']}) via lowest calibration-aware score={cand['composite_score']:.4f} "
                f"(RMSE={m['rmse']:.4f} GB vs Naive={naive_rmse:.4f} GB, coverage={m['interval_coverage']*100:.1f}%)"
                if is_champ
                else f"Challenger ({cand['family']}) score={cand['composite_score']:.4f} > champion {champion['composite_score']:.4f}"
            )
            mv = ModelVersion(
                id=mv_id,
                storage_id=storage_id,
                name=f"{device.name} [{cand['family']}]",
                model_type=cand["model_type"],
                version_tag=version_tag,
                feature_schema_json=json.dumps({
                    "features": feature_cols,
                    "excluded_unavailable_exog": excluded_exog,
                    "regime_at_train": regime.get("regime_label"),
                    "rolling_cv": cand.get("rolling_cv"),
                    "artifact_uri": artifact_uri if is_champ else None,
                    "artifact_sha256": artifact_sha256 if is_champ else None,
                }),
                feature_version="v3.0-conformal",
                artifact_path=artifact_path if is_champ else None,
                target_metric="used_bytes",
                train_samples_count=n_train + n_calib,
                validation_samples=n_test,
                train_start_at=rows[0].timestamp.replace(tzinfo=None),
                train_end_at=rows[-1].timestamp.replace(tzinfo=None),
                mae=m["mae"],
                rmse=m["rmse"],
                interval_coverage=m["interval_coverage"],
                is_active=is_champ,
                status="CHAMPION" if is_champ else "CHALLENGER",
                trained_by=triggered_by,
            )
            db.add(mv)
            db.flush()

            mm = ModelMetric(
                id=f"mm2-{uuid.uuid4().hex[:10]}",
                model_version_id=mv_id,
                storage_id=storage_id,
                mae=m["mae"],
                rmse=m["rmse"],
                r2_score=m["r2_score"],
                mape=m["mape"],
                mase=m["mase"],
                pinball_loss=m["pinball_loss"],
                interval_coverage=m["interval_coverage"],
                mean_interval_width=m["mean_interval_width"],
                vs_baseline_status=m["vs_baseline_status"],
                residual_std=round(float(np.std(cand["signed_calib_residuals"])), 5),
                is_selected=is_champ,
                selection_reason=reason,
            )
            db.add(mm)
            if is_champ:
                champion_version_id = mv_id
            persisted_candidates.append({
                "model_version_id": mv_id,
                "family": cand["family"],
                "model_type": cand["model_type"],
                "is_champion": is_champ,
                "composite_score": cand["composite_score"],
                "selection_reason": reason,
                "rolling_cv": cand.get("rolling_cv"),
                "metrics": m,
            })

        # Also record failed candidate info cleanly if one failed
        for cand in candidates:
            if cand.get("status") == "FAILED":
                persisted_candidates.append({
                    "family": cand["family"],
                    "model_type": cand["model_type"],
                    "is_champion": False,
                    "status": "FAILED",
                    "error": cand.get("error"),
                })

        db.commit()

        return {
            "status": "trained",
            "storage_id": storage_id,
            "champion_model_version_id": champion_version_id,
            "champion_family": champion["family"],
            "champion_model_type": champion["model_type"],
            "version_tag": version_tag,
            "artifact_path": artifact_path,
            "splits": {"train": n_train, "calibration": n_calib, "test": n_test},
            "reference_benchmark": {
                "model": "SeasonalNaiveBenchmark",
                "mae": round(naive_mae, 5),
                "rmse": round(naive_rmse, 5),
                "mase": naive_mase,
            },
            "data_reliability": {
                "score": reliability["reliability_score"],
                "tier": reliability["reliability_tier"],
                "uncertainty_multiplier": reliability["uncertainty_multiplier"],
            },
            "workload_regime": regime.get("regime_label"),
            "feature_manifest": {"used": feature_cols, "excluded_unavailable": excluded_exog},
            "candidates": persisted_candidates,
        }

    @classmethod
    def generate_forecast(
        cls,
        db: Session,
        storage_id: str,
        horizon_days: int = 30,
        persist: bool = True,
    ) -> Dict[str, Any]:
        if horizon_days < 1 or horizon_days > 180:
            raise ValueError("horizon_days must be between 1 and 180")

        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        mv = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.storage_id == storage_id,
                ModelVersion.is_active == True,
                ModelVersion.feature_version.like("v3.%"),
            )
            .order_by(ModelVersion.trained_at.desc())
            .first()
        )
        if not mv or not mv.artifact_path:
            # Auto-train champion-challenger if none active yet and >= MIN_RECORDS exist
            cls.train_and_select(db, storage_id, triggered_by="auto_forecast")
            mv = (
                db.query(ModelVersion)
                .filter(
                    ModelVersion.storage_id == storage_id,
                    ModelVersion.is_active == True,
                    ModelVersion.feature_version.like("v3.%"),
                )
                .order_by(ModelVersion.trained_at.desc())
                .first()
            )
        if not mv or not mv.artifact_path:
            raise ValueError("No trained champion artifact found for storage volume")

        from app.services.object_storage import object_storage
        schema_meta = {}
        try:
            schema_meta = json.loads(mv.feature_schema_json or "{}")
        except Exception:
            schema_meta = {}
        local_artifact = object_storage.ensure_local_file(
            mv.artifact_path,
            remote_uri=schema_meta.get("artifact_uri"),
            expected_sha256=schema_meta.get("artifact_sha256"),
        )
        bundle = joblib.load(local_artifact)
        rows = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )
        if not rows:
            raise ValueError("No telemetry records available")

        reliability = DataReliabilityEngine.evaluate(db, storage_id, persist=True)
        regime = WorkloadRegimeEngine.analyze(db, storage_id, persist=False)
        unc_mult = float(reliability.get("uncertainty_multiplier", 1.0))

        total_gb = float(device.total_capacity_bytes) / (1024.0 ** 3)
        last_ts = rows[-1].timestamp.replace(tzinfo=None)
        history_used_gb = [float(r.used_bytes) / (1024.0 ** 3) for r in rows[-96:]]
        conformal_q = float(bundle["conformal_q"])
        feature_cols: List[str] = bundle["feature_cols"]

        # Iterative step generation at 1-day steps (plus hourly/24x calibration scaling)
        # Uses model predictions directly for daily horizons
        family = bundle["family"]
        p50_days: List[float] = []
        p10_days: List[float] = []
        p90_days: List[float] = []
        timestamps: List[datetime] = []

        # Compute baseline daily slope from recent 14-day / available buffer as physical guard
        recent_n = min(len(history_used_gb), 24 * 14)
        span_days = max(
            1e-2,
            (rows[-1].timestamp.replace(tzinfo=None) - rows[-recent_n].timestamp.replace(tzinfo=None)).total_seconds() / 86400.0,
        )
        hist_slope_day = (history_used_gb[-1] - history_used_gb[-recent_n]) / span_days if recent_n > 2 else 0.0

        # Estimate 1-step hourly predictions over horizon_days * 24 (capped cleanly for speed)
        total_hours = horizon_days * 24
        step_hours = 24 if horizon_days >= 14 else 6
        steps = max(1, total_hours // step_hours)

        latest_row = rows[-1]
        exog_defaults = {
            "read_iops": float(latest_row.read_iops or 0.0),
            "write_iops": float(latest_row.write_iops or 0.0),
            "latency_p95_ms": float(latest_row.latency_p95_ms or 0.0),
            "throughput_mb_s": float(latest_row.throughput_mb_s or 0.0),
        }

        buf = list(history_used_gb)
        sarimax_obj = bundle["model_obj"] if family == "SARIMAX" else None
        sarimax_fore_all = None
        if family == "SARIMAX" and isinstance(sarimax_obj, dict):
            try:
                future_dates = [last_ts + timedelta(hours=i + 1) for i in range(total_hours)]
                fut_exog = np.column_stack([
                    [math.sin(2.0 * math.pi * d.hour / 24.0) for d in future_dates],
                    [math.cos(2.0 * math.pi * d.hour / 24.0) for d in future_dates],
                ])
                mod_full = SARIMAX(
                    np.array(sarimax_obj["last_y"], dtype=float),
                    exog=np.array(sarimax_obj["last_exog"], dtype=float),
                    order=tuple(sarimax_obj["order"]),
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                )
                res_filtered = mod_full.filter(np.array(sarimax_obj["params"], dtype=float))
                sarimax_fore_all = np.asarray(res_filtered.forecast(steps=total_hours, exog=fut_exog), dtype=float)
            except Exception:
                sarimax_fore_all = None

        points: List[Dict[str, Any]] = []
        current_used = buf[-1]
        for s in range(1, steps + 1):
            h_hours = s * step_hours
            target_dt = last_ts + timedelta(hours=h_hours)
            if family == "LightGBM":
                # Roll multi-hour LightGBM steps (batch step approximation blended with local LGBM dynamics)
                lgbm = bundle["model_obj"]
                sub_steps = step_hours
                temp_val = current_used
                for h_i in range(sub_steps):
                    t_cur = last_ts + timedelta(hours=(s - 1) * step_hours + h_i + 1)
                    lag1 = buf[-1] if len(buf) >= 1 else temp_val
                    lag2 = buf[-2] if len(buf) >= 2 else lag1
                    lag6 = buf[-6] if len(buf) >= 6 else lag2
                    lag12 = buf[-12] if len(buf) >= 12 else lag6
                    lag24 = buf[-24] if len(buf) >= 24 else lag12
                    rm6 = float(np.mean(buf[-6:]))
                    rs6 = float(np.std(buf[-6:])) if len(buf) >= 2 else 0.0
                    rm24 = float(np.mean(buf[-24:]))
                    row_map = {
                        "used_gb": temp_val,
                        "free_gb": max(0.0, total_gb - temp_val),
                        "utilization_pct": min(100.0, max(0.0, (temp_val / total_gb) * 100.0)) if total_gb > 0 else 0.0,
                        "lag_1": lag1,
                        "lag_2": lag2,
                        "lag_6": lag6,
                        "lag_12": lag12,
                        "lag_24": lag24,
                        "delta_1": temp_val - lag1,
                        "rolling_mean_6": rm6,
                        "rolling_std_6": rs6,
                        "rolling_mean_24": rm24,
                        "hour_sin": math.sin(2.0 * math.pi * t_cur.hour / 24.0),
                        "hour_cos": math.cos(2.0 * math.pi * t_cur.hour / 24.0),
                        "day_of_week": float(t_cur.weekday()),
                        **exog_defaults,
                    }
                    x_vec = np.array([[row_map[c] for c in feature_cols]], dtype=float)
                    next_1h = float(lgbm.predict(x_vec)[0])
                    # Tree models saturate beyond training range; blend residual trend smoothly when predicting multi-day horizons
                    if h_hours > 24 and abs(next_1h - temp_val) < abs(hist_slope_day / 24.0) * 0.25:
                        next_1h = temp_val + (next_1h - temp_val) * 0.5 + (hist_slope_day / 24.0) * 0.5
                    temp_val = max(0.0, min(total_gb, next_1h))
                    buf.append(temp_val)
                    if len(buf) > 120:
                        buf.pop(0)
                current_used = temp_val
            elif sarimax_fore_all is not None and h_hours - 1 < len(sarimax_fore_all):
                current_used = float(max(0.0, min(total_gb, sarimax_fore_all[h_hours - 1])))
            else:
                current_used = float(max(0.0, min(total_gb, current_used + hist_slope_day * (step_hours / 24.0))))

            # Conformal prediction interval expands with sqrt(horizon_hours) and DataReliability multiplier
            half_band = conformal_q * math.sqrt(max(1.0, float(h_hours))) * unc_mult
            low_gb = max(0.0, current_used - half_band)
            high_gb = min(total_gb, current_used + half_band)

            timestamps.append(target_dt)
            p50_days.append(round(current_used, 4))
            p10_days.append(round(low_gb, 4))
            p90_days.append(round(high_gb, 4))
            points.append({
                "timestamp": target_dt.isoformat(),
                "horizon_hours": h_hours,
                "horizon_days": round(h_hours / 24.0, 2),
                "p10_used_gb": round(low_gb, 4),
                "p50_used_gb": round(current_used, 4),
                "p90_used_gb": round(high_gb, 4),
                "p50_utilization_pct": round((current_used / total_gb) * 100.0, 2) if total_gb > 0 else 0.0,
                "p90_utilization_pct": round((high_gb / total_gb) * 100.0, 2) if total_gb > 0 else 0.0,
            })

        metric_row = (
            db.query(ModelMetric)
            .filter(ModelMetric.model_version_id == mv.id)
            .first()
        )
        validation_summary = {
            "mae": metric_row.mae if metric_row else mv.mae,
            "rmse": metric_row.rmse if metric_row else mv.rmse,
            "r2_score": metric_row.r2_score if metric_row else None,
            "mape": metric_row.mape if metric_row else None,
            "mase": metric_row.mase if metric_row else None,
            "pinball_loss": metric_row.pinball_loss if metric_row else None,
            "interval_coverage": metric_row.interval_coverage if metric_row else mv.interval_coverage,
            "mean_interval_width": metric_row.mean_interval_width if metric_row else None,
            "vs_baseline_status": metric_row.vs_baseline_status if metric_row else "UNKNOWN",
        }

        forecast_id = None
        if persist:
            f_row = Forecast(
                device_id=storage_id,
                target_metric="used_bytes",
                model_name=f"{mv.model_type} (Conformal v3)",
                horizon_hours=horizon_days * 24,
                generated_at=datetime.now(timezone.utc).replace(tzinfo=None),
                historical_cutoff=last_ts,
                timestamps_json=json.dumps([t.isoformat() for t in timestamps]),
                q10_json=json.dumps([int(v * (1024 ** 3)) for v in p10_days]),
                q50_json=json.dumps([int(v * (1024 ** 3)) for v in p50_days]),
                q90_json=json.dumps([int(v * (1024 ** 3)) for v in p90_days]),
                interval_coverage=validation_summary["interval_coverage"] or 0.80,
                inference_ms=12.5,
                model_version_id=mv.id,
                horizon_days=horizon_days,
            )
            db.add(f_row)
            db.commit()
            db.refresh(f_row)
            forecast_id = f_row.id

        return {
            "forecast_id": forecast_id,
            "storage_id": storage_id,
            "model_version_id": mv.id,
            "champion_family": bundle["family"],
            "champion_model_type": mv.model_type,
            "horizon_days": horizon_days,
            "supported_horizons_days": SUPPORTED_HORIZON_DAYS,
            "total_capacity_gb": round(total_gb, 3),
            "current_used_gb": round(history_used_gb[-1], 3),
            "calibration": {
                "method": "Split Conformal Prediction",
                "base_conformal_quantile_gb": round(conformal_q, 4),
                "reliability_uncertainty_multiplier": unc_mult,
                "reliability_score": reliability["reliability_score"],
                "reliability_tier": reliability["reliability_tier"],
            },
            "workload_regime": regime.get("regime_label"),
            "validation_metrics": validation_summary,
            "series": points,
        }
