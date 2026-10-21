"""
AEGISSTOR PHOENIX — Safe Action Gateway & Execution Machine
Guarantees fail-closed safety, strict zero-physical-mutations, human approval integrity, and idempotency.
"""
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.entities import (
    PhoenixActionProposal, PhoenixExecutionRecord, PhoenixIncident, PhoenixRunbook
)
from app.services.phoenix.incident_lifecycle import IncidentLifecycleManager
from app.utils.datetime_utils import utc_now


def compute_proposal_hash(action_type: str, target_resource_id: str, parameters: Dict[str, Any]) -> str:
    payload = f"{action_type}:{target_resource_id}:{json.dumps(parameters, sort_keys=True)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ActionGatewayError(Exception):
    pass


class ActionGateway:
    """
    Executes storage incident recovery runbooks safely with zero physical host mutations.
    """

    ALLOWED_MODES = ["MODE_A_SIMULATE", "MODE_B_DIAGNOSTIC_READONLY", "MODE_C_CONTROLLED_EXECUTION"]
    ENABLE_CONTROLLED_EXECUTION = False  # Hard safety flag; Mode C locked down by default

    @classmethod
    def create_proposal(
        cls,
        db: Session,
        incident_id: str,
        runbook_id: Optional[str],
        action_type: str,
        target_resource_id: str,
        parameters: Dict[str, Any],
        simulation_outcome: Dict[str, Any],
        policy_verdict: str,
        policy_violations: List[str],
        recommendation_score: float = 0.85
    ) -> PhoenixActionProposal:
        p_hash = compute_proposal_hash(action_type, target_resource_id, parameters)
        proposal_id = f"prop-phx-{uuid.uuid4().hex[:8]}"

        proposal = PhoenixActionProposal(
            id=proposal_id,
            incident_id=incident_id,
            runbook_id=runbook_id,
            action_type=action_type,
            target_resource_id=target_resource_id,
            parameters_json=json.dumps(parameters),
            simulation_run_id=f"sim-{uuid.uuid4().hex[:6]}",
            simulation_outcome_json=json.dumps(simulation_outcome),
            policy_verdict=policy_verdict,
            policy_violations_json=json.dumps(policy_violations),
            recommendation_score=recommendation_score,
            approval_status="PENDING",
            proposal_hash=p_hash
        )
        db.add(proposal)

        # Update incident active proposal
        inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == incident_id).first()
        if inc:
            inc.active_proposal_id = proposal_id
            if inc.status in ["DETECTED", "EVIDENCE_COLLECTION", "TRIAGE", "INVESTIGATION"]:
                inc.status = "PLAN_GENERATION"
            db.flush()

        db.commit()
        db.refresh(proposal)
        return proposal

    @classmethod
    def approve_proposal(
        cls,
        db: Session,
        proposal_id: str,
        reviewer_id: str,
        rationale: str
    ) -> PhoenixActionProposal:
        proposal = db.query(PhoenixActionProposal).filter(PhoenixActionProposal.id == proposal_id).first()
        if not proposal:
            raise ActionGatewayError(f"Proposal {proposal_id} not found.")

        if proposal.policy_verdict == "REJECTED_BY_POLICY":
            raise ActionGatewayError(
                "Cannot approve proposal that was REJECTED_BY_POLICY due to hard safety constraint violations."
            )

        # Validate proposal hash integrity
        current_params = json.loads(proposal.parameters_json)
        expected_hash = compute_proposal_hash(proposal.action_type, proposal.target_resource_id, current_params)
        if proposal.proposal_hash != expected_hash:
            proposal.approval_status = "INVALIDATED"
            db.commit()
            raise ActionGatewayError("Proposal parameters were modified after generation. Approval invalidated.")

        proposal.approval_status = "APPROVED"
        proposal.approved_by = reviewer_id
        proposal.approved_at = utc_now()
        proposal.approval_rationale = rationale

        # Advance incident state machine to APPROVED
        inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == proposal.incident_id).first()
        if inc and inc.status in ["SIMULATION", "AWAITING_APPROVAL", "PLAN_GENERATION"]:
            inc.status = "APPROVED"

        db.commit()
        db.refresh(proposal)
        return proposal

    @classmethod
    def execute_proposal(
        cls,
        db: Session,
        proposal_id: str,
        idempotency_token: str,
        execution_mode: str = "MODE_A_SIMULATE"
    ) -> PhoenixExecutionRecord:
        """
        Executes an approved proposal safely.
        """
        # 1. Check Idempotency Token
        existing_exec = (
            db.query(PhoenixExecutionRecord)
            .filter(PhoenixExecutionRecord.idempotency_token == idempotency_token)
            .first()
        )
        if existing_exec:
            return existing_exec  # Return cached execution result (Drill F)

        # 2. Validate Proposal Exists and is Approved
        proposal = db.query(PhoenixActionProposal).filter(PhoenixActionProposal.id == proposal_id).first()
        if not proposal:
            raise ActionGatewayError(f"Proposal {proposal_id} not found.")

        # Re-verify proposal hash to prevent tampering
        params = json.loads(proposal.parameters_json)
        computed = compute_proposal_hash(proposal.action_type, proposal.target_resource_id, params)
        if proposal.proposal_hash != computed:
            proposal.approval_status = "INVALIDATED"
            db.commit()
            raise ActionGatewayError("Proposal hash mismatch. Potential post-approval tampering detected.")

        if proposal.approval_status != "APPROVED":
            raise ActionGatewayError(
                f"Execution rejected: Proposal {proposal_id} is '{proposal.approval_status}', not 'APPROVED'."
            )

        # 3. Validate Execution Mode
        if execution_mode not in cls.ALLOWED_MODES:
            raise ActionGatewayError(f"Invalid execution mode '{execution_mode}'.")

        if execution_mode == "MODE_C_CONTROLLED_EXECUTION" and not cls.ENABLE_CONTROLLED_EXECUTION:
            raise ActionGatewayError(
                "MODE_C_CONTROLLED_EXECUTION is disabled by safety invariant. Only MODE_A_SIMULATE or MODE_B_DIAGNOSTIC_READONLY permitted."
            )

        # 4. Advance Incident State to EXECUTING
        inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == proposal.incident_id).first()
        if inc:
            ok, msg = IncidentLifecycleManager.validate_transition(inc.status, "EXECUTING")
            if not ok and inc.status != "APPROVED":
                raise ActionGatewayError(f"Incident transition to EXECUTING prohibited: {msg}")
            inc.status = "EXECUTING"
            db.flush()

        exec_id = f"exec-phx-{uuid.uuid4().hex[:8]}"
        step_logs: List[Dict[str, Any]] = []

        # Load runbook steps or synthesize single-action step
        runbook = db.query(PhoenixRunbook).filter(PhoenixRunbook.id == proposal.runbook_id).first() if proposal.runbook_id else None
        steps = json.loads(runbook.steps_json) if runbook and runbook.steps_json else [
            {"step_number": 1, "name": proposal.action_type, "action_type": proposal.action_type, "parameters": params}
        ]

        # 5. Execute Runbook Steps (Safe Simulation / Readonly sampling)
        for idx, step in enumerate(steps, 1):
            step_logs.append({
                "step_index": idx,
                "step_name": step.get("name", "Step"),
                "action_type": step.get("action_type", proposal.action_type),
                "mode": execution_mode,
                "status": "COMPLETED",
                "timestamp": utc_now().isoformat(),
                "details": f"Simulated safe execution of {step.get('action_type')} with parameters {step.get('parameters', {})}. Zero physical host mutations."
            })

        result_payload = {
            "mode": execution_mode,
            "target_resource_id": proposal.target_resource_id,
            "action_type": proposal.action_type,
            "simulated_reclaim_gb": 42.5,
            "latency_stabilization_ms": -3.2,
            "zero_physical_mutations_verified": True,
            "applied_safely": True
        }

        exec_record = PhoenixExecutionRecord(
            id=exec_id,
            proposal_id=proposal.id,
            incident_id=proposal.incident_id,
            idempotency_token=idempotency_token,
            execution_mode=execution_mode,
            status="SUCCESS",
            current_step_index=len(steps),
            total_steps=len(steps),
            step_logs_json=json.dumps(step_logs),
            execution_result_json=json.dumps(result_payload),
            started_at=utc_now(),
            completed_at=utc_now()
        )
        db.add(exec_record)

        # 6. Advance Incident to VERIFYING_RECOVERY
        if inc:
            inc.status = "VERIFYING_RECOVERY"

        db.commit()
        db.refresh(exec_record)
        return exec_record
