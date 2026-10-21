"""
AEGISSTOR ATLAS — Value-of-Experiment (VOE) Planner
Ranks potential follow-up experiments by expected reduction of epistemic uncertainty and operational risk.
"""
from typing import Dict, Any, List, Optional
import json
import uuid
from sqlalchemy.orm import Session

from app.models.entities import AtlasEvidenceGap, AtlasCalibrationRun, Device
from app.utils.datetime_utils import utc_now


STANDARD_EVIDENCE_GAPS = [
    {
        "metric_name": "latency_p95_ms",
        "workload_regime": "WRITE_HEAVY",
        "gap_description": "Flash controller TRIM/GC tail latency inflation under sustained >70% write traffic lacks empirical calibration.",
        "impact_level": "HIGH",
        "uncertainty_score": 0.78,
        "candidate_experiment": {
            "title": "FIO Sustained 4KB Random Write Burst Calibration",
            "research_question": "Does queue depth inflation exceed the M/M/1 assumption when flash controller garbage collection activates?",
            "proposed_measurement": "Controlled 60-minute 4KB random write benchmark on dedicated test volume with blktrace logging.",
            "learning_objective": "Calibrate non-linear latency penalty curve in DigitalTwinSimulator for queue depths > 4.0.",
            "resource_requirements": "1x Isolated NVMe namespace, 30 GB scratch space, 60 minutes run duration.",
            "safety_constraints": "Zero production host I/O; rate-limited to 50,000 IOPS max to prevent controller thermal throttling.",
            "limitations": "Synthetic benchmark patterns may have lower entropy than real production OLTP databases."
        }
    },
    {
        "metric_name": "utilization_pct",
        "workload_regime": "HIGH_CAPACITY_STRESS",
        "gap_description": "Data movement throughput degradation during cross-pool evacuation near 90% capacity boundary is supported only by simulation estimates.",
        "impact_level": "HIGH",
        "uncertainty_score": 0.72,
        "candidate_experiment": {
            "title": "Controlled Cold Tier Migration Bandwidth Benchmark",
            "research_question": "What is the measured bus contention penalty on foreground OLTP reads during a 500GB background tiering pass?",
            "proposed_measurement": "Schedule controlled 500GB synthetic data transfer from Tier 1 to Tier 2 while measuring foreground P95 latency.",
            "learning_objective": "Derive empirical side-effect coefficients for TIER_COLD_DATA and WORKLOAD_REBALANCING models.",
            "resource_requirements": "Tier 1 NVMe volume and Tier 2 SAS pool staging buffer, 90 minutes run duration.",
            "safety_constraints": "Halt transfer automatically if foreground latency exceeds 18.0 ms.",
            "limitations": "Fabric interconnect is assumed dedicated; shared top-of-rack switch contention is unmodeled."
        }
    },
    {
        "metric_name": "action_duration_minutes",
        "workload_regime": "BALANCED_OLTP",
        "gap_description": "Capacity expansion provisioning lead time (EXPAND_CAPACITY) is estimated at 15 minutes without empirical SAN API measurement.",
        "impact_level": "MEDIUM",
        "uncertainty_score": 0.54,
        "candidate_experiment": {
            "title": "Virtual Storage Volume Online Resize Latency Profile",
            "research_question": "Does online LUN capacity expansion introduce temporary filesystem metadata lock delays?",
            "proposed_measurement": "Trigger 500GB virtual capacity resize on isolated test target under synthetic 1000 IOPS load.",
            "learning_objective": "Verify provisioning_lead_hours and verify whether filesystem lock pauses exceed 500ms.",
            "resource_requirements": "Test LUN on SAN / virtual disk backend, 15 minutes run duration.",
            "safety_constraints": "Strictly isolated test volume; no production volumes affected.",
            "limitations": "Cloud-specific EBS / Ceph orchestration latency may differ from on-premise hardware arrays."
        }
    }
]


class ValueOfExperimentPlanner:
    """
    Ranks evidence gaps by operational consequence and expected information gain.
    """

    @classmethod
    def seed_initial_gaps_if_missing(cls, db: Session, target_device_id: str = "vol-nvme-tier1-db"):
        existing = db.query(AtlasEvidenceGap).filter(AtlasEvidenceGap.device_id == target_device_id).count()
        if existing > 0:
            return

        for idx, gap_spec in enumerate(STANDARD_EVIDENCE_GAPS, 1):
            gap = AtlasEvidenceGap(
                id=f"gap-{target_device_id[:12]}-{idx}",
                device_id=target_device_id,
                metric_name=gap_spec["metric_name"],
                workload_regime=gap_spec["workload_regime"],
                gap_description=gap_spec["gap_description"],
                impact_level=gap_spec["impact_level"],
                uncertainty_score=gap_spec["uncertainty_score"],
                candidate_experiment_json=json.dumps(gap_spec["candidate_experiment"]),
                voe_rank=idx,
                created_at=utc_now()
            )
            db.add(gap)
        db.commit()

    @classmethod
    def rank_evidence_gaps(cls, db: Session, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        dev_id = device_id or "vol-nvme-tier1-db"
        cls.seed_initial_gaps_if_missing(db, dev_id)

        query = db.query(AtlasEvidenceGap)
        if device_id:
            query = query.filter(AtlasEvidenceGap.device_id == device_id)
        gaps = query.order_by(AtlasEvidenceGap.voe_rank.asc()).all()

        results = []
        for g in gaps:
            results.append({
                "id": g.id,
                "device_id": g.device_id,
                "metric_name": g.metric_name,
                "workload_regime": g.workload_regime,
                "gap_description": g.gap_description,
                "impact_level": g.impact_level,
                "uncertainty_score": g.uncertainty_score,
                "voe_rank": g.voe_rank,
                "candidate_experiment": json.loads(g.candidate_experiment_json) if g.candidate_experiment_json else {},
                "created_at": g.created_at.isoformat() if g.created_at else None
            })
        return results
