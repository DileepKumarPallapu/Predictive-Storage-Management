import numpy as np
from typing import List, Dict, Any

class ModelCalibrator:
    """
    Evaluates prediction interval calibration, coverage, width, and pinball loss.
    Implements conformal confidence calibration checks.
    """

    @staticmethod
    def calculate_pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, alpha: float) -> float:
        """
        Quantile check loss (Pinball loss):
        L_alpha(y, y_hat) = max(alpha * (y - y_hat), (alpha - 1) * (y - y_hat))
        """
        err = y_true - y_pred
        return float(np.mean(np.maximum(alpha * err, (alpha - 1.0) * err)))

    @staticmethod
    def evaluate_interval_coverage(
        y_true: List[float],
        q10: List[float],
        q90: List[float]
    ) -> Dict[str, float]:
        y_arr = np.array(y_true)
        lo_arr = np.array(q10)
        hi_arr = np.array(q90)

        inside = (y_arr >= lo_arr) & (y_arr <= hi_arr)
        empirical_coverage = float(np.mean(inside)) if len(y_arr) > 0 else 0.80
        mean_width = float(np.mean(hi_arr - lo_arr)) if len(y_arr) > 0 else 0.0

        return {
            "empirical_coverage": round(empirical_coverage, 4),
            "mean_interval_width": round(mean_width, 2),
            "nominal_target": 0.80
        }

    @staticmethod
    def conformal_adjustment_factor(
        residuals: List[float],
        nominal_alpha: float = 0.20
    ) -> float:
        """
        Calculates conformal expansion factor from calibration residuals.
        """
        if not residuals or len(residuals) < 10:
            return 1.0
        abs_res = np.abs(residuals)
        # 1 - alpha quantile of absolute residuals
        q_val = float(np.quantile(abs_res, 1.0 - nominal_alpha))
        median_res = float(np.median(abs_res)) + 1e-6
        factor = max(0.9, min(2.0, q_val / median_res))
        return round(factor, 3)
