import logging
from typing import Dict, Any, List

logger = logging.getLogger("aegisstor.jurassic.fallback")

FALLBACK_STATES = {
    "STATE_1_HEALTHY_EVIDENCE": {
        "name": "State 1: Healthy Evidence & Nominal Intelligence",
        "description": "Continuous fresh telemetry, validated model forecasts, and verified safety envelopes.",
        "user_visible_status": "OPERATIONAL_NOMINAL",
        "permitted_operations": [
            "AUTOMATED_FORECASTING",
            "RESERVE_RUNWAY_ESTIMATION",
            "INTERVENTION_RECOMMENDATIONS",
            "AUTONOMOUS_POLICY_ALLOCATION",
        ],
        "prohibited_actions": [
            "BYPASS_SAFETY_ENVELOPE",
        ],
        "recovery_conditions": "Always active when telemetry freshness < 120s and model ECE <= 0.05.",
    },
    "STATE_2_DEGRADED_EVIDENCE": {
        "name": "State 2: Degraded Evidence & Telemetry Impairment",
        "description": "Telemetry is stale (>300s), dropout rate > 15%, or clock skew detected.",
        "user_visible_status": "DEGRADED_TELEMETRY",
        "permitted_operations": [
            "CONSERVATIVE_HEURISTIC_BOUNDS",
            "MANUAL_AUDIT_LOGGING",
            "PASSIVE_OBSERVATION",
        ],
        "prohibited_actions": [
            "AUTOMATED_REBALANCING_DISPATCH",
            "AGGRESSIVE_CAPACITY_SHRINK",
            "SILENT_OLD_VALUE_REUSE",
        ],
        "recovery_conditions": "Consecutive 5 successful fresh telemetry heartbeats received without dropout.",
    },
    "STATE_3_MODEL_UNRELIABLE": {
        "name": "State 3: Model Unreliable & Distribution Shift",
        "description": "Confirmed workload distribution shift, residual variance explosion, or conformal coverage < 70%.",
        "user_visible_status": "MODEL_DRIFT_UNRELIABLE",
        "permitted_operations": [
            "HISTORICAL_MOVING_AVERAGE_BOUNDS",
            "OPERATOR_MANUAL_REVIEW_REQUEST",
            "DRIFT_AUDIT_RECORDING",
        ],
        "prohibited_actions": [
            "AUTOMATED_TIER_MIGRATION",
            "CONFIDENCE_DEPENDENT_HEADROOM_SHAVING",
        ],
        "recovery_conditions": "Model recalibration completed with empirical coverage >= 80% on recent window.",
    },
    "STATE_4_PLANNING_UNSAFE": {
        "name": "State 4: Planning Unsafe & Hard Constraint Deadlock",
        "description": "All candidate interventions fail the dual-sided safety envelope (destination capacity saturated or interconnect bottleneck).",
        "user_visible_status": "PLANNING_SAFETY_DEADLOCK",
        "permitted_operations": [
            "CRITICAL_OPERATOR_ALARM",
            "CAPACITY_QUOTA_CLAMP_RECOMMENDATION",
            "READ_ONLY_HOLDING_PATTERN",
        ],
        "prohibited_actions": [
            "CROSS_POOL_DATA_TRANSFER",
            "FORCED_SECONDARY_BURST_INDUCTION",
        ],
        "recovery_conditions": "Manual physical capacity expansion or secondary pool load relief detected.",
    },
    "STATE_5_SERVICE_UNAVAILABLE": {
        "name": "State 5: Intelligence Service Unavailable",
        "description": "Inference engine timeout, database connection pool exhaustion, or collector process failure.",
        "user_visible_status": "INTELLIGENCE_OFFLINE",
        "permitted_operations": [
            "FAIL_SAFE_PASSIVE_MONITORING",
            "LAST_KNOWN_SAFETY_CLAMP",
        ],
        "prohibited_actions": [
            "ANY_MUTATING_ACTION",
            "FABRICATED_FORECAST_GENERATION",
        ],
        "recovery_conditions": "Successful health check ping to all core services with HTTP 200.",
    },
}

class FallbackEngine:
    """
    Formal Safe Fallback State Manager for AEGISSTOR Jurassic Lab.
    Enforces deterministic state transitions and prevents unsafe actions
    during degraded evidence, model drift, or planning deadlocks.
    """

    @classmethod
    def evaluate_state_transition(
        cls,
        telemetry_fresh: bool,
        telemetry_drop_rate: float,
        model_drift_detected: bool,
        interval_coverage: float,
        planning_feasible: bool,
        service_online: bool
    ) -> Dict[str, Any]:
        """
        Determines the appropriate safe state according to priority:
          State 5 (Service Offline) > State 4 (Planning Unsafe) >
          State 3 (Model Unreliable) > State 2 (Degraded Evidence) > State 1 (Healthy)
        """
        if not service_online:
            new_state = "STATE_5_SERVICE_UNAVAILABLE"
            reason = "Core inference or database service returned unrecoverable connection failure."
        elif not planning_feasible:
            new_state = "STATE_4_PLANNING_UNSAFE"
            reason = "No candidate intervention satisfies the dual-sided hard safety envelope."
        elif model_drift_detected or interval_coverage < 0.70:
            new_state = "STATE_3_MODEL_UNRELIABLE"
            reason = f"Conformal interval coverage collapsed to {round(interval_coverage * 100, 1)}% or distribution shift confirmed."
        elif not telemetry_fresh or telemetry_drop_rate > 0.15:
            new_state = "STATE_2_DEGRADED_EVIDENCE"
            reason = f"Telemetry dropout rate is {round(telemetry_drop_rate * 100, 1)}% or heartbeat is stale."
        else:
            new_state = "STATE_1_HEALTHY_EVIDENCE"
            reason = "Continuous fresh telemetry and validated calibrated forecasts available."

        state_meta = FALLBACK_STATES[new_state]
        return {
            "current_state": new_state,
            "status_label": state_meta["user_visible_status"],
            "state_name": state_meta["name"],
            "reason": reason,
            "permitted_operations": state_meta["permitted_operations"],
            "prohibited_actions": state_meta["prohibited_actions"],
            "recovery_conditions": state_meta["recovery_conditions"],
            "automated_actions_disabled": new_state != "STATE_1_HEALTHY_EVIDENCE",
        }
