"""
AEGISSTOR PHOENIX — Incident Orchestration & Safe Recovery API Endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json

from app.database import get_db
from app.models.entities import (
    PhoenixIncident, PhoenixRunbook, PhoenixPolicy,
    PhoenixActionProposal, PhoenixExecutionRecord, PhoenixRecoveryVerification, Device
)
from app.services.phoenix import (
    IncidentLifecycleManager, IncidentCorrelationEngine,
    PolicyGateway, RunbookEngine, ActionGateway, ActionGatewayError,
    RecoveryVerifier, EvidenceGraphEngine
)
from app.utils.datetime_utils import utc_now
from app.auth.permissions import require_method_permission

router = APIRouter(
    prefix="/phoenix",
    dependencies=[Depends(require_method_permission("alerts.read", "alerts.acknowledge"))],
)


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------
class TransitionRequest(BaseModel):
    target_state: str = Field(..., description="Target lifecycle state")
    reason: Optional[str] = Field(None, description="Reason or operational justification")


class ProposalCreateRequest(BaseModel):
    runbook_id: Optional[str] = None
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    simulated_outcome: Optional[Dict[str, Any]] = None


class ApproveProposalRequest(BaseModel):
    reviewer_id: str = "operator@aegisstor.internal"
    rationale: str = "Approved after reviewing simulated capacity runway and policy invariants."


class ExecuteProposalRequest(BaseModel):
    idempotency_token: str
    execution_mode: str = "MODE_A_SIMULATE"


class VerifyIncidentRequest(BaseModel):
    execution_id: Optional[str] = None
    force_mock_outcome: Optional[str] = None  # RECOVERY_SATISFIED, PARTIALLY_VERIFIED, INCONCLUSIVE, UNSUCCESSFUL
    observation_window_hours: float = 24.0


# ---------------------------------------------------------
# Incidents Endpoints
# ---------------------------------------------------------
@router.get("/incidents")
def list_incidents(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    device_id: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    query = db.query(PhoenixIncident)
    if severity:
        query = query.filter(PhoenixIncident.severity == severity)
    if status:
        query = query.filter(PhoenixIncident.status == status)
    if category:
        query = query.filter(PhoenixIncident.category == category)
    if device_id:
        query = query.filter(PhoenixIncident.target_device_id == device_id)
    
    incidents = query.order_by(PhoenixIncident.detection_timestamp.desc()).limit(limit).all()
    
    results = []
    for inc in incidents:
        results.append({
            "id": inc.id,
            "title": inc.title,
            "category": inc.category,
            "severity": inc.severity,
            "status": inc.status,
            "target_device_id": inc.target_device_id,
            "affected_devices": json.loads(inc.affected_devices_json) if inc.affected_devices_json else [],
            "pool_id": inc.pool_id,
            "evidence_type": inc.evidence_type,
            "detection_timestamp": inc.detection_timestamp.isoformat() if inc.detection_timestamp else None,
            "time_to_breach_hours": inc.time_to_breach_hours,
            "confidence_score": inc.confidence_score,
            "model_version": inc.model_version,
            "active_proposal_id": inc.active_proposal_id,
            "assigned_engineer": inc.assigned_engineer,
            "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
            "allowed_next_states": IncidentLifecycleManager.get_allowed_next_states(inc.status)
        })
    return results


@router.post("/incidents/scan")
def trigger_incident_scan(db: Session = Depends(get_db)):
    """
    Runs fleet-wide telemetry, forecast, and risk correlation to create or update incidents.
    """
    results = IncidentCorrelationEngine.scan_and_create_incidents(db)
    return {
        "status": "COMPLETED",
        "scanned_devices_count": db.query(Device).count(),
        "active_incidents_count": len(results),
        "timestamp": utc_now().isoformat()
    }


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")

    return {
        "id": inc.id,
        "title": inc.title,
        "category": inc.category,
        "severity": inc.severity,
        "status": inc.status,
        "target_device_id": inc.target_device_id,
        "affected_devices": json.loads(inc.affected_devices_json) if inc.affected_devices_json else [],
        "pool_id": inc.pool_id,
        "evidence_type": inc.evidence_type,
        "detection_timestamp": inc.detection_timestamp.isoformat() if inc.detection_timestamp else None,
        "projected_breach_timestamp": inc.projected_breach_timestamp.isoformat() if inc.projected_breach_timestamp else None,
        "time_to_breach_hours": inc.time_to_breach_hours,
        "confidence_score": inc.confidence_score,
        "model_version": inc.model_version,
        "symptoms": json.loads(inc.symptoms_json) if inc.symptoms_json else [],
        "hypotheses": json.loads(inc.hypotheses_json) if inc.hypotheses_json else [],
        "evidence_payload": json.loads(inc.evidence_payload_json) if inc.evidence_payload_json else {},
        "active_proposal_id": inc.active_proposal_id,
        "assigned_engineer": inc.assigned_engineer,
        "escalation_reason": inc.escalation_reason,
        "resolution_summary": inc.resolution_summary,
        "resolved_at": inc.resolved_at.isoformat() if inc.resolved_at else None,
        "allowed_next_states": IncidentLifecycleManager.get_allowed_next_states(inc.status)
    }


@router.post("/incidents/{incident_id}/transition")
def transition_incident(
    incident_id: str,
    req: TransitionRequest,
    db: Session = Depends(get_db)
):
    inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")

    valid, reason = IncidentLifecycleManager.validate_transition(inc.status, req.target_state)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    old_state = inc.status
    inc.status = req.target_state
    if req.target_state == "RESOLVED":
        inc.resolved_at = utc_now()
        if req.reason:
            inc.resolution_summary = req.reason
    elif req.target_state == "ESCALATED":
        inc.escalation_reason = req.reason or "Escalated for human engineering review"

    inc.updated_at = utc_now()
    db.commit()
    db.refresh(inc)

    return {
        "incident_id": inc.id,
        "previous_state": old_state,
        "current_state": inc.status,
        "allowed_next_states": IncidentLifecycleManager.get_allowed_next_states(inc.status),
        "updated_at": inc.updated_at.isoformat()
    }


# ---------------------------------------------------------
# Runbooks & Policies Endpoints
# ---------------------------------------------------------
@router.get("/runbooks")
def list_runbooks(category: Optional[str] = None, db: Session = Depends(get_db)):
    RunbookEngine.seed_standard_runbooks(db)
    query = db.query(PhoenixRunbook).filter(PhoenixRunbook.is_active == True)
    if category:
        query = query.filter(PhoenixRunbook.category == category)
    runbooks = query.all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "version": r.version,
            "category": r.category,
            "description": r.description,
            "preconditions": json.loads(r.preconditions_json) if r.preconditions_json else [],
            "steps": json.loads(r.steps_json) if r.steps_json else [],
            "rollback_steps": json.loads(r.rollback_steps_json) if r.rollback_steps_json else [],
            "safety_constraints": json.loads(r.safety_constraints_json) if r.safety_constraints_json else {},
            "verification_criteria": json.loads(r.verification_criteria_json) if r.verification_criteria_json else {},
            "estimated_duration_minutes": r.estimated_duration_minutes,
            "is_automated": r.is_automated
        }
        for r in runbooks
    ]


@router.get("/policies")
def get_policies(db: Session = Depends(get_db)):
    policy = PolicyGateway.get_active_policy(db)
    return {
        "id": policy.id,
        "name": policy.name,
        "version": policy.version,
        "min_free_reserve_pct": policy.min_free_reserve_pct,
        "max_latency_ms": policy.max_latency_ms,
        "max_bandwidth_mb_s": policy.max_bandwidth_mb_s,
        "max_telemetry_age_seconds": policy.max_telemetry_age_seconds,
        "allowed_action_types": json.loads(policy.allowed_action_types_json) if policy.allowed_action_types_json else [],
        "require_human_approval": policy.require_human_approval,
        "allow_shadow_mode_only": policy.allow_shadow_mode_only,
        "is_active": policy.is_active
    }


# ---------------------------------------------------------
# Proposals, Approvals & Execution Endpoints
# ---------------------------------------------------------
@router.post("/incidents/{incident_id}/proposals")
def generate_proposal_for_incident(
    incident_id: str,
    req: ProposalCreateRequest,
    db: Session = Depends(get_db)
):
    inc = db.query(PhoenixIncident).filter(PhoenixIncident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found.")

    target_res = inc.target_device_id or "dev-nvme-db-01"
    runbook_id = req.runbook_id
    if not runbook_id:
        rb = RunbookEngine.select_runbook_for_incident(db, inc)
        runbook_id = rb.id if rb else None

    sim_outcome = req.simulated_outcome or {
        "projected_utilization_pct": 74.0,
        "projected_latency_ms": 11.2,
        "projected_bandwidth_mb_s": 2400.0,
        "expected_headroom_gain_gb": 45.0
    }

    verdict, violations = PolicyGateway.evaluate_proposal(
        db=db,
        action_type=req.action_type,
        target_resource_id=target_res,
        parameters=req.parameters,
        simulated_outcome=sim_outcome,
        recommendation_score=0.88
    )

    proposal = ActionGateway.create_proposal(
        db=db,
        incident_id=inc.id,
        runbook_id=runbook_id,
        action_type=req.action_type,
        target_resource_id=target_res,
        parameters=req.parameters,
        simulation_outcome=sim_outcome,
        policy_verdict=verdict,
        policy_violations=violations,
        recommendation_score=0.88
    )

    return {
        "proposal_id": proposal.id,
        "incident_id": proposal.incident_id,
        "runbook_id": proposal.runbook_id,
        "action_type": proposal.action_type,
        "target_resource_id": proposal.target_resource_id,
        "parameters": json.loads(proposal.parameters_json),
        "policy_verdict": proposal.policy_verdict,
        "policy_violations": json.loads(proposal.policy_violations_json),
        "approval_status": proposal.approval_status,
        "proposal_hash": proposal.proposal_hash
    }


@router.post("/proposals/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    req: ApproveProposalRequest,
    db: Session = Depends(get_db)
):
    try:
        proposal = ActionGateway.approve_proposal(
            db=db,
            proposal_id=proposal_id,
            reviewer_id=req.reviewer_id,
            rationale=req.rationale
        )
        return {
            "proposal_id": proposal.id,
            "approval_status": proposal.approval_status,
            "approved_by": proposal.approved_by,
            "approved_at": proposal.approved_at.isoformat() if proposal.approved_at else None,
            "approval_rationale": proposal.approval_rationale
        }
    except ActionGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/proposals/{proposal_id}/execute")
def execute_proposal(
    proposal_id: str,
    req: ExecuteProposalRequest,
    db: Session = Depends(get_db)
):
    try:
        record = ActionGateway.execute_proposal(
            db=db,
            proposal_id=proposal_id,
            idempotency_token=req.idempotency_token,
            execution_mode=req.execution_mode
        )
        return {
            "execution_id": record.id,
            "proposal_id": record.proposal_id,
            "incident_id": record.incident_id,
            "status": record.status,
            "execution_mode": record.execution_mode,
            "idempotency_token": record.idempotency_token,
            "total_steps": record.total_steps,
            "step_logs": json.loads(record.step_logs_json) if record.step_logs_json else [],
            "execution_result": json.loads(record.execution_result_json) if record.execution_result_json else {},
            "started_at": record.started_at.isoformat() if record.started_at else None,
            "completed_at": record.completed_at.isoformat() if record.completed_at else None
        }
    except ActionGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------
# Recovery Verification & Evidence Graph
# ---------------------------------------------------------
@router.post("/incidents/{incident_id}/verify")
def verify_recovery(
    incident_id: str,
    req: VerifyIncidentRequest,
    db: Session = Depends(get_db)
):
    try:
        verif = RecoveryVerifier.verify_incident_recovery(
            db=db,
            incident_id=incident_id,
            execution_id=req.execution_id,
            force_mock_outcome=req.force_mock_outcome,
            observation_window_hours=req.observation_window_hours
        )
        return {
            "verification_id": verif.id,
            "incident_id": verif.incident_id,
            "status": verif.status,
            "observation_window_hours": verif.observation_window_hours,
            "threshold_checks": json.loads(verif.threshold_checks_json) if verif.threshold_checks_json else [],
            "secondary_degradation_detected": verif.secondary_degradation_detected,
            "residual_risk_score": verif.residual_risk_score,
            "verification_notes": verif.verification_notes,
            "verified_at": verif.verified_at.isoformat() if verif.verified_at else None
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/incidents/{incident_id}/evidence-graph")
def get_incident_evidence_graph(incident_id: str, db: Session = Depends(get_db)):
    graph = EvidenceGraphEngine.build_graph_for_incident(db, incident_id)
    return graph


@router.get("/analytics/repeated-patterns")
def get_repeated_patterns(db: Session = Depends(get_db)):
    return EvidenceGraphEngine.analyze_repeated_patterns(db)


@router.get("/executions")
def list_executions(limit: int = 50, db: Session = Depends(get_db)):
    execs = db.query(PhoenixExecutionRecord).order_by(PhoenixExecutionRecord.started_at.desc()).limit(limit).all()
    return [
        {
            "id": ex.id,
            "proposal_id": ex.proposal_id,
            "incident_id": ex.incident_id,
            "idempotency_token": ex.idempotency_token,
            "execution_mode": ex.execution_mode,
            "status": ex.status,
            "current_step_index": ex.current_step_index,
            "total_steps": ex.total_steps,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None
        }
        for ex in execs
    ]
