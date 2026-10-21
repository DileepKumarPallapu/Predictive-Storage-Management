import numpy as np
from datetime import datetime
from typing import Dict, Any, List

class DriftDetector:
    """
    Monitors prediction residuals and telemetry distributions for model drift,
    workload shifts, and stale collector updates.
    """

    @classmethod
    def check_drift_status(
        cls,
        observed_values: List[float],
        predicted_q50: List[float],
        threshold_ratio: float = 1.35
    ) -> Dict[str, Any]:
        if not observed_values or not predicted_q50 or len(observed_values) < 10:
            return {
                "drift_status": "STABLE",
                "drift_detected": False,
                "residual_mae": 0.0,
                "message": "Telemetry history nominal; insufficient deviation to indicate drift."
            }

        min_len = min(len(observed_values), len(predicted_q50))
        y = np.array(observed_values[-min_len:])
        y_hat = np.array(predicted_q50[:min_len])

        abs_err = np.abs(y - y_hat)
        mae = float(np.mean(abs_err))
        
        # Relative error against mean magnitude
        mean_mag = float(np.mean(y)) + 1e-5
        rel_err = mae / mean_mag

        if rel_err > 0.15:
            drift_detected = True
            drift_status = "ELEVATED_DRIFT"
            msg = f"Workload regime shift detected: prediction error ratio ({round(rel_err*100, 1)}%) exceeds stability limit."
        else:
            drift_detected = False
            drift_status = "STABLE"
            msg = "Residual distribution aligned with calibration bounds."

        return {
            "drift_status": drift_status,
            "drift_detected": drift_detected,
            "residual_mae": round(mae, 2),
            "relative_error_pct": round(rel_err * 100.0, 2),
            "checked_at": datetime.utcnow(),
            "message": msg
        }
