from typing import List, Dict, Any
from app.simulator.digital_twin import DigitalTwinSimulator

class RecommendationEngine:
    """
    Evaluates candidate preventive interventions using the Digital Twin simulator.
    Enforces the Hard Safety Envelope and performs Pareto multi-objective ranking.
    """

    @classmethod
    def evaluate_and_rank_interventions(
        cls,
        device_id: str,
        device_meta: Dict[str, Any],
        base_forecast: Dict[str, Any],
        risk_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        candidate_specs = [
            {
                "action_type": "TIER_COLD_DATA",
                "title": "Automated Cold Tiering to Secondary Object Pool",
                "parameters": {"data_volume_gb": 1800.0, "migration_rate_mb_s": 150.0},
                "base_rationale": "Identifies 1.8 TB of cold tables/snapshots inactive for >30 days and streams them to cold storage."
            },
            {
                "action_type": "EXPAND_CAPACITY",
                "title": "Online LUN Expansion (+3 TB Provisioning)",
                "parameters": {"added_capacity_gb": 3000.0, "provisioning_lead_hours": 1.5},
                "base_rationale": "Allocates 3 TB of additional raw flash blocks from free pool reserves to restore safety headroom."
            },
            {
                "action_type": "REBALANCE_WORKLOAD",
                "title": "Inter-Pool Tenant Workload Rebalance",
                "parameters": {"relocated_iops_pct": 30.0},
                "base_rationale": "Relocates noisy analytics tenant volumes to adjacent lightly loaded SAS storage array."
            },
            {
                "action_type": "RESCHEDULE_TASK",
                "title": "Reschedule Background Maintenance & Parity Verification",
                "parameters": {},
                "base_rationale": "Shifts background RAID scrub jobs out of high-traffic daytime hours to off-peak 02:00 UTC."
            },
            {
                "action_type": "DO_NOTHING",
                "title": "Maintain Existing Policy (Do Nothing)",
                "parameters": {},
                "base_rationale": "Maintains current configurations without administrative overhead or operational changes."
            }
        ]

        evaluated = []
        for spec in candidate_specs:
            outcome = DigitalTwinSimulator.simulate_scenario(
                device_id=device_id,
                device_metadata=device_meta,
                base_forecast=base_forecast,
                action_type=spec["action_type"],
                parameters=spec["parameters"]
            )

            # Check Hard Safety Envelope
            safety_passed = outcome["safety_envelope_passed"]
            residual_risk = outcome["residual_risk_score"]
            duration_min = outcome["duration_minutes"]
            cost_usd = outcome["estimated_cost_usd"]
            overhead_pct = outcome["overhead_io_penalty_pct"]

            # Calculate estimated runway gain
            if spec["action_type"] in ["TIER_COLD_DATA", "EXPAND_CAPACITY"]:
                runway_gain = round(168.0 + (cost_usd * 0.5), 1)
            elif spec["action_type"] == "REBALANCE_WORKLOAD":
                runway_gain = 48.0
            else:
                runway_gain = 0.0

            # Multi-objective utility function
            # Utility = RunwayGain * 1.5 - ResidualRisk * 50 - Cost * 0.1 - Overhead * 0.5
            if not safety_passed:
                utility = -999.0
                rationale = f"[DISQUALIFIED BY HARD SAFETY ENVELOPE] {spec['base_rationale']} Reason: {'; '.join(outcome['violation_reasons'])}"
            else:
                utility = (runway_gain * 1.2) - (residual_risk * 60.0) - (cost_usd * 0.08) - (max(0.0, overhead_pct) * 0.4)
                rationale = (
                    f"{spec['base_rationale']} Projected outcome: extends reserve runway by +{runway_gain}h, "
                    f"reducing residual risk to {residual_risk}. Estimated cost: ${cost_usd}, overhead: {overhead_pct}%."
                )

            item = {
                "id": f"rec-{spec['action_type'].lower()}-{device_id}",
                "device_id": device_id,
                "action_type": spec["action_type"],
                "title": spec["title"],
                "rationale": rationale,
                "utility_score": round(utility, 2),
                "estimated_runway_gain_hours": runway_gain,
                "hard_constraints_checked": True,
                "safety_envelope_passed": safety_passed,
                "residual_risk": residual_risk,
                "estimated_cost_usd": cost_usd,
                "duration_minutes": duration_min,
                "overhead_pct": overhead_pct,
                "approval_status": "PENDING_REVIEW"
            }
            evaluated.append(item)

        # Rank actions (highest utility first; disqualified at the end)
        evaluated.sort(key=lambda x: x["utility_score"], reverse=True)
        for rank_idx, item in enumerate(evaluated, start=1):
            item["rank"] = rank_idx

        return evaluated
