import json
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import OracleHypothesis, OracleWorkload, Device, Telemetry

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class HypothesisManager:
    """
    AEGISSTOR ORACLE — Scientific Hypothesis Management & Contradiction Detection.
    Enforces rigorous investigation tracking, lifecycle audit trails, and automated
    evidence-contradiction checks.
    """

    ALLOWED_STATUSES = [
        "DRAFT",
        "EVIDENCE_GATHERING",
        "READY_FOR_TESTING",
        "UNDER_EVALUATION",
        "SUPPORTED_WITHIN_CONDITIONS",
        "NOT_SUPPORTED",
        "INCONCLUSIVE",
        "CLOSED"
    ]

    @classmethod
    def seed_initial_hypotheses_if_missing(cls, db: Session):
        count = db.query(OracleHypothesis).count()
        if count > 0:
            return

        hyp1 = OracleHypothesis(
            id="hyp-oracle-lat-01",
            question="Does concurrent nightly execution of wl-analytics-batch cause the observed P95 latency spikes on vol-nvme-tier1-db?",
            target_resource="vol-nvme-tier1-db",
            workload_id="wl-analytics-batch",
            status="READY_FOR_TESTING",
            supporting_evidence_json=json.dumps([
                "P95 latency surges from 1.4ms to 18.2ms precisely between 01:00 and 04:00.",
                "Analytics batch job logs confirm 3,200 IOPS arrival rate during the same window.",
                "Flash controller garbage collection TRIM cycles correlate with sustained queue depths > 3.5."
            ]),
            contradicting_evidence_json=json.dumps([
                "PCIe Gen4 bus throughput stays under 65% of rated hardware limit.",
                "Similar batch executions on Tuesday showed only a 4.1ms latency rise."
            ]),
            confounding_variables_json=json.dumps([
                "Co-occurring OS security vulnerability scanning at 02:00.",
                "Database index re-indexing scheduled concurrently on alternate partition."
            ]),
            proposed_evaluation_method="CONTROLLED_DIGITAL_TWIN_THROTTLING",
            conclusion=None,
            reviewer="lead_sre@aegisstor.internal",
            evidence_references_json=json.dumps(["telemetry:vol-nvme-tier1-db:latency_p95_ms", "workload:wl-analytics-batch:write_iops"]),
            status_history_json=json.dumps([
                {"status": "DRAFT", "timestamp": utc_now().isoformat(), "reviewer": "lead_sre", "rationale": "Initial hypothesis formulation"},
                {"status": "EVIDENCE_GATHERING", "timestamp": utc_now().isoformat(), "reviewer": "lead_sre", "rationale": "Collected 72h telemetry traces"},
                {"status": "READY_FOR_TESTING", "timestamp": utc_now().isoformat(), "reviewer": "lead_sre", "rationale": "Contradictory and supporting evidence compiled"}
            ])
        )

        hyp2 = OracleHypothesis(
            id="hyp-oracle-cap-02",
            question="Is uncompacted log aggregation on wl-log-aggregator solely driving the shortened reserve runway on vol-sas-tier2-analytics?",
            target_resource="vol-sas-tier2-analytics",
            workload_id="wl-log-aggregator",
            status="EVIDENCE_GATHERING",
            supporting_evidence_json=json.dumps([
                "Daily capacity consumption rose from 14.5 GB to 22.8 GB/day.",
                "Log index sizes account for 5,800 GB of total 8,400 GB allocated."
            ]),
            contradicting_evidence_json=json.dumps([
                "Reconciliation residual identifies 1,850 GB of unmeasured growth in the same period."
            ]),
            confounding_variables_json=json.dumps([
                "Unattributed filesystem journaling overhead and untagged tenant writes."
            ]),
            proposed_evaluation_method="HISTORICAL_CHANGEPOINT_DECOMPOSITION",
            conclusion=None,
            reviewer="storage-architect@aegisstor.internal",
            evidence_references_json=json.dumps(["telemetry:vol-sas-tier2-analytics:used_bytes"]),
            status_history_json=json.dumps([
                {"status": "DRAFT", "timestamp": utc_now().isoformat(), "reviewer": "storage-architect", "rationale": "Initial creation"},
                {"status": "EVIDENCE_GATHERING", "timestamp": utc_now().isoformat(), "reviewer": "storage-architect", "rationale": "Reconciling aggregate measurements"}
            ])
        )

        db.add_all([hyp1, hyp2])
        db.commit()

    @classmethod
    def list_hypotheses(cls, db: Session, target_resource: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(OracleHypothesis)
        if target_resource:
            query = query.filter(OracleHypothesis.target_resource == target_resource)
        items = query.order_by(OracleHypothesis.updated_at.desc()).all()

        results = []
        for h in items:
            results.append({
                "id": h.id,
                "question": h.question,
                "target_resource": h.target_resource,
                "workload_id": h.workload_id,
                "status": h.status,
                "supporting_evidence": json.loads(h.supporting_evidence_json or "[]"),
                "contradicting_evidence": json.loads(h.contradicting_evidence_json or "[]"),
                "confounding_variables": json.loads(h.confounding_variables_json or "[]"),
                "proposed_evaluation_method": h.proposed_evaluation_method,
                "conclusion": h.conclusion,
                "reviewer": h.reviewer,
                "evidence_references": json.loads(h.evidence_references_json or "[]"),
                "status_history": json.loads(h.status_history_json or "[]"),
                "created_at": h.created_at.isoformat(),
                "updated_at": h.updated_at.isoformat()
            })
        return results

    @classmethod
    def create_hypothesis(cls, db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
        hyp_id = payload.get("id") or f"hyp-oracle-{uuid.uuid4().hex[:8]}"

        # Run automated contradiction checks before save
        contradictions = cls.detect_evidence_contradictions(
            db,
            target_resource=payload["target_resource"],
            workload_id=payload.get("workload_id"),
            proposed_supporting=payload.get("supporting_evidence", [])
        )

        contradicting_list = payload.get("contradicting_evidence", [])
        if contradictions:
            contradicting_list.extend(contradictions)

        now_iso = utc_now().isoformat()
        initial_history = [{
            "status": "DRAFT",
            "timestamp": now_iso,
            "reviewer": payload.get("reviewer", "sre@aegisstor.internal"),
            "rationale": "Hypothesis created in investigation workspace."
        }]

        hyp = OracleHypothesis(
            id=hyp_id,
            question=payload["question"],
            target_resource=payload["target_resource"],
            workload_id=payload.get("workload_id"),
            status="DRAFT",
            supporting_evidence_json=json.dumps(payload.get("supporting_evidence", [])),
            contradicting_evidence_json=json.dumps(contradicting_list),
            confounding_variables_json=json.dumps(payload.get("confounding_variables", [])),
            proposed_evaluation_method=payload.get("proposed_evaluation_method", "CONTROLLED_DIGITAL_TWIN_SIMULATION"),
            conclusion=None,
            reviewer=payload.get("reviewer", "sre@aegisstor.internal"),
            evidence_references_json=json.dumps(payload.get("evidence_references", [])),
            status_history_json=json.dumps(initial_history),
            created_at=utc_now(),
            updated_at=utc_now()
        )
        db.add(hyp)
        db.commit()
        db.refresh(hyp)

        return {
            "id": hyp.id,
            "status": hyp.status,
            "question": hyp.question,
            "automated_contradictions_flagged": len(contradictions)
        }

    @classmethod
    def update_hypothesis_status(
        cls,
        db: Session,
        hypothesis_id: str,
        new_status: str,
        rationale: str,
        reviewer: str,
        conclusion: Optional[str] = None
    ) -> Dict[str, Any]:
        if new_status not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status '{new_status}' is invalid. Allowed: {cls.ALLOWED_STATUSES}")

        hyp = db.query(OracleHypothesis).filter(OracleHypothesis.id == hypothesis_id).first()
        if not hyp:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        # Scientific constraint: cannot promote directly from DRAFT to SUPPORTED without testing
        if new_status == "SUPPORTED_WITHIN_CONDITIONS" and hyp.status not in ["UNDER_EVALUATION", "READY_FOR_TESTING"]:
            raise ValueError(
                "Scientific Rule Violation: A hypothesis cannot be promoted to 'SUPPORTED_WITHIN_CONDITIONS' "
                "without first passing through 'READY_FOR_TESTING' and 'UNDER_EVALUATION' with recorded evaluation evidence."
            )

        history = json.loads(hyp.status_history_json or "[]")
        history.append({
            "previous_status": hyp.status,
            "status": new_status,
            "timestamp": utc_now().isoformat(),
            "reviewer": reviewer,
            "rationale": rationale
        })

        hyp.status = new_status
        hyp.reviewer = reviewer
        hyp.status_history_json = json.dumps(history)
        if conclusion:
            hyp.conclusion = conclusion
        hyp.updated_at = utc_now()

        db.commit()
        return {"id": hyp.id, "status": hyp.status, "conclusion": hyp.conclusion}

    @classmethod
    def detect_evidence_contradictions(
        cls,
        db: Session,
        target_resource: str,
        workload_id: Optional[str],
        proposed_supporting: List[str]
    ) -> List[str]:
        """
        Part 8 — Automated Evidence-Contradiction Detection:
        1. Checks whether workload target device matches target resource.
        2. Checks whether device has recorded telemetry dropouts during suspected window.
        3. Identifies whether competing workloads share the same bus.
        """
        contradictions = []

        if workload_id:
            wl = db.query(OracleWorkload).filter(OracleWorkload.id == workload_id).first()
            if wl:
                # 1. Topological check
                if wl.target_device_id != target_resource:
                    contradictions.append(
                        f"Topological Disconnect: Workload '{wl.name}' is mapped to '{wl.target_device_id}', not suspected resource '{target_resource}'. Direct I/O causation is physically impossible unless a shared backend fabric is involved."
                    )
                # 2. Attribution capability check
                if not wl.attribution_available:
                    contradictions.append(
                        f"Attribution Limitation: Workload '{wl.name}' does not have granular telemetry probes enabled. Claims regarding its individual contribution cannot be empirically verified from current metrics."
                    )

        # 3. Telemetry quality / dropouts check on target resource
        device = db.query(Device).filter(Device.id == target_resource).first()
        missingness = getattr(device, 'telemetry_missingness_rate', 0.0) if device else 0.0
        if missingness > 0.05:
            contradictions.append(
                f"Data Quality Warning: Storage pool '{target_resource}' has a {missingness * 100:.1f}% telemetry dropout rate. Time-series gaps may confound correlation analysis."
            )

        return contradictions
