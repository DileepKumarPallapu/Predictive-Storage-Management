"""
AEGISSTOR ATLAS — Evidence-Gated Recommendation Pipeline
Enforces empirical grounding and fidelity checks before ranking or recommending storage interventions.
"""
from typing import Dict, Any, List, Optional
import json
from sqlalchemy.orm import Session

from app.models.entities import Device, AtlasActionEffectEvidence, AtlasFidelityAssessment
from app.services.atlas.fidelity_assessor import FidelityAssessor
from app.services.atlas.action_effect_model import ActionEffectEvidenceService


class EvidenceGatedPlanner:
    """
    Rigorously gates candidate interventions against data quality, simulator fidelity,
    and empirical action-effect evidence.
    """

    @classmethod
    def evaluate_interventions(
        cls,
        db: Session,
        device_id: str,
        candidates: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found.")

        # 1. Fetch or compute fidelity assessment
        assessment = FidelityAssessor.evaluate_device_fidelity(db, device_id)
        fidelity_status = assessment.assessment_status
        out_of_scope_warnings = json.loads(assessment.out_of_scope_warnings_json) if assessment.out_of_scope_warnings_json else []

        # 2. Fetch action-effect evidence
        evidence_list = ActionEffectEvidenceService.get_action_evidence_summary(db, device_id)
        evidence_by_action = {e["action_type"]: e for e in evidence_list}

        if not candidates:
            candidates = [
                {"action_type": "EXPAND_CAPACITY", "parameters": {"added_capacity_gb": 2000.0}},
                {"action_type": "TIER_COLD_DATA", "parameters": {"target_reclaim_pct": 10.0}},
                {"action_type": "WORKLOAD_REBALANCING", "parameters": {"migration_size_gb": 400.0}},
                {"action_type": "RESCHEDULE_TASK", "parameters": {"shift_hours": 4}},
                {"action_type": "DO_NOTHING", "parameters": {}}
            ]

        results = []

        for c in candidates:
            act_type = c["action_type"]
            params = c.get("parameters", {})
            evidence = evidence_by_action.get(act_type, {})

            category = evidence.get("evidence_category", "ASSUMPTION_SUPPORTED")
            is_causal = evidence.get("is_causally_verified", False)
            sample_size = evidence.get("sample_size", 0)

            gating_verdict = "REQUIRES_ADDITIONAL_EVIDENCE"
            gating_rationale = []

            # Stage A: Check Hard Constraints
            # E.g. Do Nothing when utilization > critical threshold violates reserve
            if act_type == "DO_NOTHING" and (device.status in ["CRITICAL", "WARNING"]):
                gating_verdict = "REJECTED_BY_HARD_CONSTRAINT"
                gating_rationale.append("Operating without mitigation projects capacity reserve breach under diurnal load.")

            # Stage B: Check Simulator Fidelity & Evidence Category
            elif fidelity_status in ["DEGRADED", "UNKNOWN"]:
                gating_verdict = "REQUIRES_ADDITIONAL_EVIDENCE"
                gating_rationale.append(f"Simulator fidelity is '{fidelity_status}'. Digital Twin counterfactuals uncalibrated for target device.")

            elif out_of_scope_warnings and not is_causal:
                gating_verdict = "REQUIRES_HUMAN_REVIEW"
                gating_rationale.append("Operating conditions exceed validated calibration scope; action relies on simulation estimates.")

            elif is_causal and category in ["CONTROLLED_EXPERIMENT", "OBSERVED_OPERATIONAL_OUTCOME"]:
                gating_verdict = "SUPPORTED_RECOMMENDATION"
                gating_rationale.append(f"Supported by {sample_size} empirical trials with verified causal outcome.")

            elif category == "SIMULATION_COUNTERFACTUAL" and fidelity_status == "HIGH_FIDELITY":
                gating_verdict = "SAFE_TO_SIMULATE"
                gating_rationale.append("Validated in high-fidelity simulator; recommend controlled trial before physical change.")

            else:
                gating_verdict = "REQUIRES_ADDITIONAL_EVIDENCE"
                gating_rationale.append(f"Backed primarily by {category.lower().replace('_', ' ')}; requires experimental benchmarking.")

            results.append({
                "action_type": act_type,
                "parameters": params,
                "gating_verdict": gating_verdict,
                "gating_rationale": "; ".join(gating_rationale),
                "evidence_category": category,
                "is_causally_verified": is_causal,
                "sample_size": sample_size,
                "fidelity_status": fidelity_status,
                "overall_fidelity_score": assessment.overall_fidelity_score,
                "has_scope_warnings": len(out_of_scope_warnings) > 0,
                "scope_warnings": out_of_scope_warnings
            })

        # Rank: Supported recommendations first, followed by safe to simulate, requires review, requires evidence, rejected
        priority_map = {
            "SUPPORTED_RECOMMENDATION": 1,
            "SAFE_TO_SIMULATE": 2,
            "REQUIRES_HUMAN_REVIEW": 3,
            "REQUIRES_ADDITIONAL_EVIDENCE": 4,
            "REJECTED_BY_HARD_CONSTRAINT": 5
        }
        results.sort(key=lambda x: priority_map.get(x["gating_verdict"], 99))
        return results
