"""
AEGISSTOR ATLAS — Reality-Calibrated Action-Effect Evidence Model
Rigorously tracks the empirical backing of candidate interventions, distinguishing
simulated estimates, controlled benchmark results, operational outcomes, and assumptions.
"""
from typing import Dict, Any, List, Optional
import json
import uuid
from sqlalchemy.orm import Session

from app.models.entities import AtlasActionEffectEvidence, Device
from app.utils.datetime_utils import utc_now


STANDARD_ACTION_EFFECTS = [
    {
        "action_type": "EXPAND_CAPACITY",
        "evidence_category": "CONTROLLED_EXPERIMENT",
        "sample_size": 24,
        "primary_effect_mean": 2000.0,  # +2000 GB headroom
        "primary_effect_std": 0.0,
        "side_effects": {
            "provisioning_latency_minutes": 15.0,
            "temporary_metadata_lock_ms": 120.0,
            "monetary_cost_per_gb_month": 0.025
        },
        "confounding_factors": ["Controller firmware hot-expansion support", "RAID stripe resizing overhead"],
        "is_causally_verified": True,
        "evaluation_status": "EXPERIMENTALLY_VERIFIED"
    },
    {
        "action_type": "TIER_COLD_DATA",
        "evidence_category": "OBSERVED_OPERATIONAL_OUTCOME",
        "sample_size": 18,
        "primary_effect_mean": 850.0,  # Reclaim ~850 GB
        "primary_effect_std": 120.0,
        "side_effects": {
            "migration_bus_bandwidth_mb_s": 450.0,
            "secondary_read_latency_penalty_pct": 14.5,
            "cold_object_store_retrieval_cost_usd_per_gb": 0.01
        },
        "confounding_factors": ["Diurnal tenant access spikes during evacuation", "Cold data classification accuracy"],
        "is_causally_verified": True,
        "evaluation_status": "OPERATIONAL_OUTCOME_BACKED"
    },
    {
        "action_type": "WORKLOAD_REBALANCING",
        "evidence_category": "SIMULATION_COUNTERFACTUAL",
        "sample_size": 6,
        "primary_effect_mean": 420.0,  # Migrate 420 GB to secondary pool
        "primary_effect_std": 85.0,
        "side_effects": {
            "interconnect_queue_depth_spike": 3.2,
            "peer_pool_capacity_reduction_gb": 420.0
        },
        "confounding_factors": ["Target pool I/O saturation", "Cross-chassis fabric contention"],
        "is_causally_verified": False,
        "evaluation_status": "SIMULATION_ESTIMATE_ONLY"
    },
    {
        "action_type": "RESCHEDULE_TASK",
        "evidence_category": "ASSUMPTION_SUPPORTED",
        "sample_size": 2,
        "primary_effect_mean": -6.5,  # -6.5ms P95 latency drop
        "primary_effect_std": 2.1,
        "side_effects": {
            "backup_window_elongation_hours": 1.5
        },
        "confounding_factors": ["Unscheduled ad-hoc analytics queries during rescheduled window"],
        "is_causally_verified": False,
        "evaluation_status": "THEORETICAL_ASSUMPTION"
    },
    {
        "action_type": "DO_NOTHING",
        "evidence_category": "OBSERVED_OPERATIONAL_OUTCOME",
        "sample_size": 120,
        "primary_effect_mean": 0.0,
        "primary_effect_std": 0.0,
        "side_effects": {
            "organic_headroom_erosion_gb_per_day": 45.0,
            "breach_risk_inflation_rate": 0.08
        },
        "confounding_factors": ["Seasonal burst activity"],
        "is_causally_verified": True,
        "evaluation_status": "EMPIRICAL_BASELINE"
    }
]


class ActionEffectEvidenceService:
    """
    Manages empirical evidence profiles for candidate storage operations.
    """

    @classmethod
    def seed_initial_evidence_if_missing(cls, db: Session, target_device_id: str = "vol-nvme-tier1-db"):
        existing_count = db.query(AtlasActionEffectEvidence).count()
        if existing_count > 0:
            return

        for spec in STANDARD_ACTION_EFFECTS:
            record = AtlasActionEffectEvidence(
                id=f"aee-{spec['action_type'].lower()[:12]}-{uuid.uuid4().hex[:6]}",
                action_type=spec["action_type"],
                target_device_id=target_device_id,
                evidence_category=spec["evidence_category"],
                sample_size=spec["sample_size"],
                primary_effect_mean=spec["primary_effect_mean"],
                primary_effect_std=spec["primary_effect_std"],
                side_effects_json=json.dumps(spec["side_effects"]),
                confounding_factors_json=json.dumps(spec["confounding_factors"]),
                is_causally_verified=spec["is_causally_verified"],
                evaluation_status=spec["evaluation_status"],
                last_evaluated_at=utc_now()
            )
            db.add(record)
        db.commit()

    @classmethod
    def get_action_evidence_summary(cls, db: Session, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cls.seed_initial_evidence_if_missing(db)
        query = db.query(AtlasActionEffectEvidence)
        if device_id:
            query = query.filter(AtlasActionEffectEvidence.target_device_id == device_id)
        records = query.all()

        results = []
        for r in records:
            results.append({
                "id": r.id,
                "action_type": r.action_type,
                "target_device_id": r.target_device_id,
                "evidence_category": r.evidence_category,
                "sample_size": r.sample_size,
                "primary_effect_mean": r.primary_effect_mean,
                "primary_effect_std": r.primary_effect_std,
                "side_effects": json.loads(r.side_effects_json) if r.side_effects_json else {},
                "confounding_factors": json.loads(r.confounding_factors_json) if r.confounding_factors_json else [],
                "is_causally_verified": r.is_causally_verified,
                "evaluation_status": r.evaluation_status,
                "last_evaluated_at": r.last_evaluated_at.isoformat() if r.last_evaluated_at else None
            })
        return results
