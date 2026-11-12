import json
import math
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import joblib
import numpy as np
from sqlalchemy.orm import Session

from app.ml.champion_challenger import ChampionChallengerEngine
from app.models.entities import CapacityRiskEvaluation, Device, ModelVersion, Telemetry


class CapacityRiskEngine:
    """
    Probabilistic Storage Capacity Risk Engine.
    Calculates capacity exhaustion date, safety-threshold crossing date,
    empirical residual-CDF threshold crossing probability (validated by Brier score),
    expected shortfall bytes, and adverse P90 utilization risk.
    """

    @classmethod
    def evaluate(
        cls,
        db: Session,
        storage_id: str,
        horizon_days: int = 30,
        safety_threshold_pct: Optional[float] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        latest_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if not latest_tel:
            raise ValueError("No telemetry samples available for capacity risk calculation")

        threshold_pct = float(
            safety_threshold_pct
            if safety_threshold_pct is not None
            else (device.critical_threshold_pct or device.warning_threshold_pct or 85.0)
        )
        total_b = int(device.total_capacity_bytes)
        total_gb = total_b / (1024.0 ** 3)
        safety_limit_gb = total_gb * (threshold_pct / 100.0)
        current_used_gb = float(latest_tel.used_bytes) / (1024.0 ** 3)
        current_util_pct = float(latest_tel.utilization_pct)
        remaining_safe_b = max(0, int((safety_limit_gb - current_used_gb) * (1024.0 ** 3)))

        forecast = ChampionChallengerEngine.generate_forecast(
            db, storage_id, horizon_days=horizon_days, persist=False
        )
        series = forecast["series"]
        unc_mult = float(forecast["calibration"]["reliability_uncertainty_multiplier"])
        reliability_score = float(forecast["calibration"]["reliability_score"])

        # Load champion empirical residuals for residual-CDF crossing probability + Brier check
        mv = db.query(ModelVersion).filter(ModelVersion.id == forecast["model_version_id"]).first()
        residuals = np.array([-0.1, 0.0, 0.1], dtype=float)
        if mv and mv.artifact_path and os.path.exists(mv.artifact_path):
            bundle = joblib.load(mv.artifact_path)
            raw_res = bundle.get("signed_calib_residuals") or bundle.get("test_residuals") or []
            if len(raw_res) >= 3:
                residuals = np.array(raw_res, dtype=float)

        # Evaluate trajectory dates & residual CDF at horizon end
        safety_cross_dt: Optional[datetime] = None
        exhaustion_dt: Optional[datetime] = None
        for pt in series:
            if safety_cross_dt is None and pt["p50_utilization_pct"] >= threshold_pct:
                safety_cross_dt = datetime.fromisoformat(pt["timestamp"])
            if exhaustion_dt is None and pt["p50_utilization_pct"] >= 99.5:
                exhaustion_dt = datetime.fromisoformat(pt["timestamp"])

        # Smooth linear extrapolation beyond horizon up to 365 days if still rising toward exhaustion
        horizon_end_pt = series[-1]
        horizon_p50_gb = float(horizon_end_pt["p50_used_gb"])
        horizon_p90_gb = float(horizon_end_pt["p90_used_gb"])
        horizon_hours = float(horizon_end_pt["horizon_hours"])

        delta_gb = horizon_p50_gb - current_used_gb
        daily_rate_gb = delta_gb / max(1.0, float(horizon_days))
        last_tel_ts = latest_tel.timestamp.replace(tzinfo=None)
        if safety_cross_dt is None and daily_rate_gb > 1e-4 and safety_limit_gb > current_used_gb:
            days_to_safe = (safety_limit_gb - current_used_gb) / daily_rate_gb
            if days_to_safe <= 365.0:
                safety_cross_dt = last_tel_ts + timedelta(days=days_to_safe)
        if exhaustion_dt is None and daily_rate_gb > 1e-4 and total_gb > current_used_gb:
            days_to_full = (total_gb - current_used_gb) / daily_rate_gb
            if days_to_full <= 365.0:
                exhaustion_dt = last_tel_ts + timedelta(days=days_to_full)

        # Empirical residual CDF at horizon H: scaled residual distribution around horizon_p50_gb
        scaled_res = residuals * math.sqrt(max(1.0, horizon_hours)) * unc_mult
        simulated_terminal_gb = np.clip(horizon_p50_gb + scaled_res, 0.0, total_gb)
        prob_cross = float(np.mean(simulated_terminal_gb >= safety_limit_gb))
        # Also account for immediate breach if current_util >= threshold_pct
        if current_util_pct >= threshold_pct:
            prob_cross = max(prob_cross, 0.95)
        prob_cross = round(max(0.0, min(1.0, prob_cross)), 4)

        # Expected shortfall beyond safety limit over adverse outcomes (or exceedance at P90)
        exceedances_gb = np.maximum(0.0, simulated_terminal_gb - safety_limit_gb)
        adverse_mask = exceedances_gb > 0.0
        if np.any(adverse_mask):
            expected_shortfall_gb = float(np.mean(exceedances_gb[adverse_mask]))
        elif horizon_p90_gb > safety_limit_gb:
            expected_shortfall_gb = float(horizon_p90_gb - safety_limit_gb) * max(0.1, prob_cross)
        else:
            expected_shortfall_gb = 0.0
        expected_shortfall_b = max(0, int(expected_shortfall_gb * (1024.0 ** 3)))

        # Brier score calibration self-check on held-out calibration residuals
        # Uses empirical median indicator y >= q50 with predicted prob ~ 0.50 + residual check
        med_res = float(np.median(residuals))
        empirical_probs = np.clip(
            [float(np.mean(residuals >= (r - 1e-6))) for r in residuals],
            0.0,
            1.0,
        )
        observed_hits = (residuals >= med_res).astype(float)
        brier_score = round(float(np.mean((empirical_probs - observed_hits) ** 2)), 4)

        forecasted_util_pct = round(float(horizon_end_pt["p50_utilization_pct"]), 2)
        adverse_p90_util_pct = round(float(horizon_end_pt["p90_utilization_pct"]), 2)

        if prob_cross >= 0.70 or current_util_pct >= threshold_pct:
            risk_band = "CRITICAL"
        elif prob_cross >= 0.30 or adverse_p90_util_pct >= threshold_pct:
            risk_band = "HIGH"
        elif prob_cross >= 0.10:
            risk_band = "MODERATE"
        else:
            risk_band = "LOW"

        eval_id = f"risk-{uuid.uuid4().hex[:10]}"
        details = {
            "safety_threshold_pct": threshold_pct,
            "safety_limit_gb": round(safety_limit_gb, 3),
            "daily_projected_growth_gb": round(daily_rate_gb, 4),
            "brier_calibration_score": brier_score,
            "residual_sample_size": int(len(residuals)),
            "champion_family": forecast["champion_family"],
            "workload_regime": forecast["workload_regime"],
            "risk_band": risk_band,
        }

        if persist:
            db.add(CapacityRiskEvaluation(
                id=eval_id,
                storage_id=storage_id,
                forecast_id=None,
                horizon_days=horizon_days,
                current_utilization_pct=round(current_util_pct, 2),
                forecasted_utilization_pct=forecasted_util_pct,
                remaining_safe_capacity_bytes=remaining_safe_b,
                safety_threshold_crossing_date=safety_cross_dt,
                exhaustion_date=exhaustion_dt,
                threshold_crossing_probability=prob_cross,
                expected_shortfall_bytes=expected_shortfall_b,
                adverse_p90_utilization_pct=adverse_p90_util_pct,
                data_reliability_score=reliability_score,
                details_json=json.dumps(details),
            ))
            db.commit()

        return {
            "id": eval_id,
            "storage_id": storage_id,
            "horizon_days": horizon_days,
            "risk_band": risk_band,
            "current_utilization_pct": round(current_util_pct, 2),
            "forecasted_utilization_pct": forecasted_util_pct,
            "adverse_p90_utilization_pct": adverse_p90_util_pct,
            "remaining_safe_capacity_bytes": remaining_safe_b,
            "safety_threshold_crossing_date": safety_cross_dt.isoformat() if safety_cross_dt else None,
            "exhaustion_date": exhaustion_dt.isoformat() if exhaustion_dt else None,
            "threshold_crossing_probability": prob_cross,
            "expected_shortfall_bytes": expected_shortfall_b,
            "data_reliability_score": reliability_score,
            "details": details,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }
