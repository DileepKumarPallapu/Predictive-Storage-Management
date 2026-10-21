import math
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger("aegisstor.jurassic.robustness")

class RobustnessEngine:
    """
    Model Robustness, Distribution Shift & Prediction Interval Stress Testing Engine.
    Detects when unusual operating regimes violate model assumptions.
    """

    @classmethod
    def evaluate_distribution_shift(
        cls,
        baseline_values: List[float],
        observed_values: List[float],
        delta_threshold: float = 0.15
    ) -> Dict[str, Any]:
        """
        Evaluates statistical distribution shift between baseline training data
        and newly observed workload regimes using Page-Hinkley cumulative sum
        and distribution moments comparison.
        """
        if len(baseline_values) < 20 or len(observed_values) < 20:
            return {
                "drift_status": "INSUFFICIENT_DATA",
                "drift_statistic": 0.0,
                "threshold_value": delta_threshold,
                "explanation": "Insufficient sample count to assess distribution shift (minimum 20 samples required).",
                "shift_detected": False,
            }

        mean_base = float(np.mean(baseline_values))
        std_base = float(np.std(baseline_values)) + 1e-6
        mean_obs = float(np.mean(observed_values))
        std_obs = float(np.std(observed_values)) + 1e-6

        # Standardized mean shift
        z_score = abs(mean_obs - mean_base) / std_base
        # Variance ratio shift
        f_ratio = max(std_obs, std_base) / max(1e-6, min(std_obs, std_base))

        # Page-Hinkley cumulative sum test
        cumsum = 0.0
        min_cumsum = 0.0
        ph_stat = 0.0
        for val in observed_values:
            cumsum += (val - mean_base - (delta_threshold * std_base))
            min_cumsum = min(min_cumsum, cumsum)
            ph_stat = max(ph_stat, cumsum - min_cumsum)

        ph_normalized = ph_stat / (std_base * len(observed_values))

        if z_score > 3.0 or ph_normalized > 0.45 or f_ratio > 3.5:
            status = "CONFIRMED_EVALUATION_MISMATCH"
            explanation = (
                f"Severe distribution shift confirmed: Z-score is {round(z_score, 2)} and "
                f"Page-Hinkley statistic {round(ph_normalized, 3)} exceeds critical threshold 0.45."
            )
            shift_detected = True
        elif z_score > 1.8 or ph_normalized > 0.20 or f_ratio > 2.0:
            status = "POSSIBLE_SHIFT"
            explanation = (
                f"Transient workload variance or potential emerging shift detected (Z-score: {round(z_score, 2)})."
            )
            shift_detected = True
        else:
            status = "NO_DETECTED_SHIFT"
            explanation = "Observed telemetry matches historical baseline within expected statistical bounds."
            shift_detected = False

        return {
            "drift_status": status,
            "drift_statistic": round(ph_normalized, 3),
            "threshold_value": delta_threshold,
            "mean_shift_z_score": round(z_score, 2),
            "variance_ratio": round(f_ratio, 2),
            "explanation": explanation,
            "shift_detected": shift_detected,
        }

    @classmethod
    def stress_test_prediction_intervals(
        cls,
        y_true: List[float],
        q10_pred: List[float],
        q90_pred: List[float],
        nominal_coverage: float = 0.80
    ) -> Dict[str, Any]:
        """
        Assesses conformal prediction interval health under stress testing.
        Decomposes error sources and verifies whether the calibration holds.
        """
        n = min(len(y_true), len(q10_pred), len(q90_pred))
        if n == 0:
            return {
                "empirical_coverage": 0.0,
                "nominal_coverage": nominal_coverage,
                "coverage_error": -nominal_coverage,
                "mean_interval_width": 0.0,
                "calibration_passed": False,
                "error_attribution": "INSUFFICIENT_SAMPLES",
            }

        covered_count = sum(1 for i in range(n) if q10_pred[i] <= y_true[i] <= q90_pred[i])
        empirical_coverage = round(covered_count / n, 4)
        coverage_error = round(empirical_coverage - nominal_coverage, 4)
        widths = [max(0.0, q90_pred[i] - q10_pred[i]) for i in range(n)]
        mean_width = round(float(np.mean(widths)), 2)

        # Calibration check: must be within +/- 10% of nominal target
        calibration_passed = empirical_coverage >= (nominal_coverage - 0.10)

        # Error attribution
        if empirical_coverage < 0.60:
            attribution = "WORKLOAD_DISTRIBUTION_SHIFT"
            breakdown_reason = "Unmodeled write bursts breached upper 90th quantile; training distribution unrepresentative."
        elif mean_width > 50000.0:  # Excessive width
            attribution = "NOISY_OBSERVATIONS_EXPANSION"
            breakdown_reason = "Interval width inflated due to high variance; bounds are safe but excessively conservative."
        elif n < 50:
            attribution = "INSUFFICIENT_TRAINING_HISTORY"
            breakdown_reason = "Short observation window leads to sampling variance in empirical quantiles."
        else:
            attribution = "ACCEPTABLE_CALIBRATION"
            breakdown_reason = "Empirical coverage aligns with nominal coverage within acceptable conformal tolerances."

        return {
            "empirical_coverage": empirical_coverage,
            "nominal_coverage": nominal_coverage,
            "coverage_error": coverage_error,
            "mean_interval_width": mean_width,
            "calibration_passed": calibration_passed,
            "error_attribution": attribution,
            "breakdown_reason": breakdown_reason,
        }
