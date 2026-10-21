import logging
from typing import Dict, Any

logger = logging.getLogger("aegisstor.jurassic.scorecard")

SCORECARD_WEIGHTS = {
    "capacity_forecasting_reliability": 0.15,
    "performance_forecasting_reliability": 0.10,
    "prediction_interval_coverage": 0.15,
    "breach_detection_quality": 0.15,
    "false_alarm_resistance": 0.10,
    "degraded_evidence_detection": 0.10,
    "safe_fallback_correctness": 0.10,
    "infeasible_action_rejection": 0.05,
    "scenario_reproducibility": 0.05,
    "resource_overhead_efficiency": 0.05,
}

class ScorecardEngine:
    """
    Transparent Multi-Dimensional Resilience Scorecard for AEGISSTOR Jurassic Lab.
    Computes separate, auditable metrics across ten dimensions with normalized weights.
    """

    @classmethod
    def calculate_resilience_scorecard(
        cls,
        capacity_mae_pct: float,
        latency_mae_ms: float,
        empirical_coverage: float,
        missed_breaches: int,
        false_alarms: int,
        degraded_evidence_caught: bool,
        fallback_state_correct: bool,
        infeasible_action_rejected: bool,
        reproducibility_verified: bool,
        cpu_overhead_pct: float
    ) -> Dict[str, Any]:
        """Calculates multi-dimensional scores (0-100) and composite index."""
        # 1. Capacity forecasting (100 if MAE <= 2%, 0 if MAE >= 12%)
        s_cap = max(0.0, min(100.0, 100.0 - (capacity_mae_pct - 2.0) * 10.0))

        # 2. Performance forecasting (100 if MAE <= 1ms, 0 if MAE >= 15ms)
        s_perf = max(0.0, min(100.0, 100.0 - (latency_mae_ms - 1.0) * 7.14))

        # 3. Interval coverage (target 0.80)
        cov_diff = abs(empirical_coverage - 0.80)
        s_cov = max(0.0, min(100.0, 100.0 - cov_diff * 200.0))

        # 4. Breach detection (100 if 0 missed, -35 per missed breach)
        s_breach = max(0.0, 100.0 - (missed_breaches * 35.0))

        # 5. False alarm resistance (100 if 0 false alarms, -15 per false alarm)
        s_fa = max(0.0, 100.0 - (false_alarms * 15.0))

        # 6. Degraded evidence detection
        s_deg = 100.0 if degraded_evidence_caught else 0.0

        # 7. Safe fallback correctness
        s_fb = 100.0 if fallback_state_correct else 20.0

        # 8. Infeasible action rejection
        s_rej = 100.0 if infeasible_action_rejected else 0.0

        # 9. Scenario reproducibility
        s_rep = 100.0 if reproducibility_verified else 0.0

        # 10. Resource overhead (100 if CPU <= 2%, 0 if CPU >= 20%)
        s_cpu = max(0.0, min(100.0, 100.0 - (cpu_overhead_pct - 2.0) * 5.5))

        dimensions = {
            "capacity_forecasting_reliability": round(s_cap, 1),
            "performance_forecasting_reliability": round(s_perf, 1),
            "prediction_interval_coverage": round(s_cov, 1),
            "breach_detection_quality": round(s_breach, 1),
            "false_alarm_resistance": round(s_fa, 1),
            "degraded_evidence_detection": round(s_deg, 1),
            "safe_fallback_correctness": round(s_fb, 1),
            "infeasible_action_rejection": round(s_rej, 1),
            "scenario_reproducibility": round(s_rep, 1),
            "resource_overhead_efficiency": round(s_cpu, 1),
        }

        # Weighted composite
        composite_score = sum(dimensions[k] * SCORECARD_WEIGHTS[k] for k in SCORECARD_WEIGHTS)
        composite_score = round(composite_score, 1)

        # Rating tier
        if composite_score >= 88.0:
            rating_tier = "EXEMPLARY_RESILIENCE"
        elif composite_score >= 72.0:
            rating_tier = "PRODUCTION_DEPENDABLE"
        elif composite_score >= 55.0:
            rating_tier = "ELEVATED_VULNERABILITY"
        else:
            rating_tier = "CRITICAL_RESILIENCE_DEFICIT"

        return {
            "composite_resilience_score": composite_score,
            "rating_tier": rating_tier,
            "dimensions": dimensions,
            "weights": SCORECARD_WEIGHTS,
            "interpretation_notice": (
                "The Composite Resilience Score evaluates software robustness across 10 empirical dimensions. "
                "It is a benchmark index, not a physical hardware probability of failure."
            ),
        }
