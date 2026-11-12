import json
import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.auth.tenant import assert_org_resource, resolve_organization_id
from app.database import get_db
from app.models.entities import User
from app.models.control_plane_entities import (
    ActionApproval,
    ActionDefinition,
    ActionExecution,
    ActionExecutionStep,
    ActionPreflightResult,
    ActionRequest,
    ConnectorCapability,
    ControlPlaneAuditEvent,
    ControlPlaneConnector,
    ResourceExecutionLock,
)
from app.realtime.event_bus import OutboxService, raise_if_version_conflict
from app.services.control_plane_service import (
    SUPPORTED_PROVIDERS,
    VALID_ACTION_TRANSITIONS,
    execute_read_only_action,
    record_cp_audit,
    run_preflight_and_dry_run,
    seed_action_definitions,
    validate_credential_ref,
)
from app.utils.datetime_utils import utc_now

router = APIRouter()


class ConnectorRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    provider: str = Field(..., min_length=2, max_length=64)
    version: str = "1.0.0"
    credential_ref: str = Field(..., min_length=4, max_length=256)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CapabilityRegisterRequest(BaseModel):
    action_key: str = Field(..., min_length=2, max_length=64)
    is_supported: bool = True
    dry_run_mode: str = "AEGISSTOR_PREFLIGHT"  # NATIVE_PROVIDER | AEGISSTOR_PREFLIGHT | UNSUPPORTED
    constraints: Dict[str, Any] = Field(default_factory=dict)


class ActionPolicyUpdateRequest(BaseModel):
    requires_approval: Optional[bool] = None
    risk_level: Optional[str] = None
    is_active: Optional[bool] = None


class ActionCreateRequest(BaseModel):
    connector_id: str
    operation: str
    resource_type: str = "DEVICE"
    resource_id: str
    resource_version: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    idempotency_key: Optional[str] = None


class ActionDecisionRequest(BaseModel):
    comment: str = ""
    expected_version: Optional[int] = None


class ActionCancelRequest(BaseModel):
    reason: str = "Cancelled by requester"
    expected_version: Optional[int] = None


def _serialize_connector(db: Session, c: ControlPlaneConnector) -> Dict[str, Any]:
    caps = (
        db.query(ConnectorCapability)
        .filter(ConnectorCapability.connector_id == c.id)
        .order_by(ConnectorCapability.action_key.asc())
        .all()
    )
    return {
        "id": c.id,
        "organization_id": c.organization_id,
        "name": c.name,
        "provider": c.provider,
        "version": c.version,
        "connection_status": c.connection_status,
        "last_health_check_at": c.last_health_check_at.isoformat() if c.last_health_check_at else None,
        "last_error": c.last_error,
        "credential_ref": c.credential_ref,
        "metadata": json.loads(c.metadata_json or "{}"),
        "entity_version": c.entity_version,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "capabilities": [
            {
                "id": cap.id,
                "action_key": cap.action_key,
                "is_supported": cap.is_supported,
                "dry_run_mode": cap.dry_run_mode,
                "constraints": json.loads(cap.constraints_json or "{}"),
            }
            for cap in caps
        ],
    }


def _serialize_action(a: ActionRequest) -> Dict[str, Any]:
    return {
        "id": a.id,
        "organization_id": a.organization_id,
        "connector_id": a.connector_id,
        "action_definition_id": a.action_definition_id,
        "resource_type": a.resource_type,
        "resource_id": a.resource_id,
        "resource_version": a.resource_version,
        "requester_user_id": a.requester_user_id,
        "requester_username": a.requester_username,
        "requesting_role": a.requesting_role,
        "operation": a.operation,
        "parameters": json.loads(a.parameters_json or "{}"),
        "risk_level": a.risk_level,
        "status": a.status,
        "approval_required": a.approval_required,
        "execution_result": json.loads(a.execution_result_json) if a.execution_result_json else None,
        "idempotency_key": a.idempotency_key,
        "entity_version": a.entity_version,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _admin_user_ids(db: Session, org_id: str) -> list:
    admins = db.query(User).filter(User.role == "ADMIN", User.is_active == True).all()
    return [u.id for u in admins]


@router.get("/control-plane/connectors")
def list_cp_connectors(
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    rows = (
        db.query(ControlPlaneConnector)
        .filter(ControlPlaneConnector.organization_id == org_id)
        .order_by(ControlPlaneConnector.created_at.desc())
        .all()
    )
    return {"organization_id": org_id, "connectors": [_serialize_connector(db, c) for c in rows]}


@router.post("/control-plane/connectors", status_code=status.HTTP_201_CREATED)
def register_cp_connector(
    payload: ConnectorRegisterRequest,
    current_user: User = Depends(require_permission("control_plane.connectors.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    provider = payload.provider.strip().upper()
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported provider '{provider}'. Supported: {sorted(SUPPORTED_PROVIDERS)}",
        )
    try:
        cred_ref = validate_credential_ref(payload.credential_ref)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    conn = ControlPlaneConnector(
        id=f"cpc-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        name=payload.name.strip(),
        provider=provider,
        version=payload.version.strip(),
        connection_status="CONFIGURED",
        credential_ref=cred_ref,
        metadata_json=json.dumps(payload.metadata),
    )
    db.add(conn)
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="connector.registered",
        actor=current_user,
        connector_id=conn.id,
        details={"name": conn.name, "provider": conn.provider, "credential_ref": cred_ref},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="connector.updated",
        resource_type="ControlPlaneConnector",
        resource_id=conn.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=conn.entity_version,
        payload={"id": conn.id, "name": conn.name, "provider": conn.provider, "status": conn.connection_status},
        required_permission="control_plane.read",
    )
    return _serialize_connector(db, conn)


@router.get("/control-plane/connectors/{connector_id}")
def get_cp_connector(
    connector_id: str,
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    conn = assert_org_resource(
        db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == connector_id).first(),
        org_id,
        "ControlPlaneConnector",
    )
    return _serialize_connector(db, conn)


@router.post("/control-plane/connectors/{connector_id}/capabilities", status_code=status.HTTP_201_CREATED)
def register_connector_capability(
    connector_id: str,
    payload: CapabilityRegisterRequest,
    current_user: User = Depends(require_permission("control_plane.connectors.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    conn = assert_org_resource(
        db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == connector_id).first(),
        org_id,
        "ControlPlaneConnector",
    )
    action_key = payload.action_key.strip().upper()
    defn = db.query(ActionDefinition).filter(ActionDefinition.id == action_key, ActionDefinition.is_active == True).first()
    if not defn:
        raise HTTPException(
            status_code=422,
            detail=f"Action '{action_key}' is not a registered Sprint 1 capability.",
        )
    if payload.dry_run_mode.upper() not in ("NATIVE_PROVIDER", "AEGISSTOR_PREFLIGHT", "UNSUPPORTED"):
        raise HTTPException(status_code=422, detail="Invalid dry_run_mode.")

    existing = (
        db.query(ConnectorCapability)
        .filter(ConnectorCapability.connector_id == conn.id, ConnectorCapability.action_key == action_key)
        .first()
    )
    if existing:
        existing.is_supported = payload.is_supported
        existing.dry_run_mode = payload.dry_run_mode.upper()
        existing.constraints_json = json.dumps(payload.constraints)
        cap = existing
    else:
        cap = ConnectorCapability(
            id=f"cap-{uuid.uuid4().hex[:10]}",
            connector_id=conn.id,
            organization_id=org_id,
            action_key=action_key,
            is_supported=payload.is_supported,
            dry_run_mode=payload.dry_run_mode.upper(),
            constraints_json=json.dumps(payload.constraints),
        )
        db.add(cap)

    conn.entity_version += 1
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="connector.capability_registered",
        actor=current_user,
        connector_id=conn.id,
        details={"action_key": action_key, "dry_run_mode": cap.dry_run_mode},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="connector.updated",
        resource_type="ControlPlaneConnector",
        resource_id=conn.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=conn.entity_version,
        payload={"id": conn.id, "capability": action_key},
        required_permission="control_plane.read",
    )
    return _serialize_connector(db, conn)


@router.post("/control-plane/connectors/{connector_id}/health-check")
def check_connector_health(
    connector_id: str,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    conn = assert_org_resource(
        db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == connector_id).first(),
        org_id,
        "ControlPlaneConnector",
    )
    conn.last_health_check_at = utc_now()
    if conn.credential_ref and conn.provider in SUPPORTED_PROVIDERS:
        conn.connection_status = "CONNECTED"
        conn.last_error = None
    else:
        conn.connection_status = "ERROR"
        conn.last_error = "Missing valid credential_ref or unsupported provider."
    conn.entity_version += 1
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="connector.health_checked",
        actor=current_user,
        connector_id=conn.id,
        details={"status": conn.connection_status},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="connector.updated",
        resource_type="ControlPlaneConnector",
        resource_id=conn.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=conn.entity_version,
        payload={"id": conn.id, "connection_status": conn.connection_status},
        required_permission="control_plane.read",
    )
    return _serialize_connector(db, conn)


@router.get("/control-plane/action-definitions")
def list_action_definitions(
    current_user: User = Depends(require_permission("control_plane.read")),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    defs = db.query(ActionDefinition).order_by(ActionDefinition.id.asc()).all()
    return {
        "definitions": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "risk_level": d.risk_level,
                "requires_approval": d.requires_approval,
                "is_read_only": d.is_read_only,
                "dry_run_supported": d.dry_run_supported,
                "input_schema": json.loads(d.input_schema_json or "{}"),
                "description": d.description,
                "is_active": d.is_active,
            }
            for d in defs
        ]
    }


@router.patch("/control-plane/action-definitions/{action_id}")
def update_action_definition_policy(
    action_id: str,
    payload: ActionPolicyUpdateRequest,
    current_user: User = Depends(require_permission("control_plane.connectors.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    defn = db.query(ActionDefinition).filter(ActionDefinition.id == action_id).first()
    if not defn:
        raise HTTPException(status_code=404, detail="ActionDefinition not found.")
    if payload.requires_approval is not None:
        defn.requires_approval = payload.requires_approval
    if payload.risk_level is not None:
        defn.risk_level = payload.risk_level.upper()
    if payload.is_active is not None:
        defn.is_active = payload.is_active
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action_policy.updated",
        actor=current_user,
        details={"action_id": defn.id, "requires_approval": defn.requires_approval, "risk_level": defn.risk_level},
    )
    db.commit()
    return {"id": defn.id, "requires_approval": defn.requires_approval, "risk_level": defn.risk_level, "is_active": defn.is_active}


@router.get("/control-plane/actions")
def list_action_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    q = db.query(ActionRequest).filter(ActionRequest.organization_id == org_id)
    if status_filter:
        q = q.filter(ActionRequest.status == status_filter.upper())
    rows = q.order_by(ActionRequest.created_at.desc()).limit(100).all()
    return {"organization_id": org_id, "actions": [_serialize_action(a) for a in rows]}


@router.post("/control-plane/actions", status_code=status.HTTP_201_CREATED)
def create_action_request(
    payload: ActionCreateRequest,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    seed_action_definitions(db)
    idem_key = (payload.idempotency_key or "").strip() or f"idem-{uuid.uuid4().hex[:12]}"
    existing = db.query(ActionRequest).filter(ActionRequest.idempotency_key == idem_key).first()
    if existing:
        if existing.organization_id != org_id:
            raise HTTPException(status_code=409, detail="Idempotency key conflict.")
        return {**_serialize_action(existing), "idempotent_replay": True}

    conn = assert_org_resource(
        db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == payload.connector_id).first(),
        org_id,
        "ControlPlaneConnector",
    )
    op = payload.operation.strip().upper()
    defn = db.query(ActionDefinition).filter(ActionDefinition.id == op, ActionDefinition.is_active == True).first()
    if not defn:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported or inactive operation '{op}'.",
        )
    if not defn.is_read_only:
        raise HTTPException(status_code=403, detail="Sprint 1 permits read-only operations only.")

    cap = (
        db.query(ConnectorCapability)
        .filter(
            ConnectorCapability.connector_id == conn.id,
            ConnectorCapability.action_key == op,
            ConnectorCapability.is_supported == True,
        )
        .first()
    )
    if not cap:
        raise HTTPException(
            status_code=422,
            detail=f"Connector '{conn.name}' does not support capability '{op}'.",
        )

    action = ActionRequest(
        id=f"act-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        connector_id=conn.id,
        action_definition_id=defn.id,
        resource_type=payload.resource_type.strip().upper(),
        resource_id=payload.resource_id.strip(),
        resource_version=payload.resource_version,
        requester_user_id=current_user.id,
        requester_username=current_user.username,
        requesting_role=current_user.role,
        operation=op,
        parameters_json=json.dumps(payload.parameters),
        risk_level=defn.risk_level,
        status="DRAFT",
        approval_required=defn.requires_approval,
        idempotency_key=idem_key,
        entity_version=1,
    )
    db.add(action)
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.created",
        actor=current_user,
        action_request_id=action.id,
        connector_id=conn.id,
        from_status=None,
        to_status="DRAFT",
        details={"operation": op, "resource_id": action.resource_id},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.created",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload=_serialize_action(action),
        required_permission="control_plane.read",
    )
    return _serialize_action(action)


@router.get("/control-plane/actions/{action_id}")
def get_action_detail(
    action_id: str,
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    preflights = (
        db.query(ActionPreflightResult)
        .filter(ActionPreflightResult.action_request_id == action.id)
        .order_by(ActionPreflightResult.evaluated_at.desc())
        .all()
    )
    approvals = (
        db.query(ActionApproval)
        .filter(ActionApproval.action_request_id == action.id)
        .order_by(ActionApproval.decided_at.desc())
        .all()
    )
    executions = (
        db.query(ActionExecution)
        .filter(ActionExecution.action_request_id == action.id)
        .order_by(ActionExecution.started_at.desc())
        .all()
    )
    exec_payload = []
    for ex in executions:
        steps = (
            db.query(ActionExecutionStep)
            .filter(ActionExecutionStep.execution_id == ex.id)
            .order_by(ActionExecutionStep.step_order.asc())
            .all()
        )
        exec_payload.append({
            "id": ex.id,
            "status": ex.status,
            "result_summary": json.loads(ex.result_summary_json or "{}"),
            "error_message": ex.error_message,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
            "steps": [
                {
                    "id": s.id,
                    "step_order": s.step_order,
                    "step_name": s.step_name,
                    "status": s.status,
                    "output": json.loads(s.output_json or "{}"),
                }
                for s in steps
            ],
        })
    audits = (
        db.query(ControlPlaneAuditEvent)
        .filter(ControlPlaneAuditEvent.action_request_id == action.id)
        .order_by(ControlPlaneAuditEvent.created_at.asc())
        .all()
    )
    return {
        "action": _serialize_action(action),
        "preflights": [
            {
                "id": p.id,
                "overall_status": p.overall_status,
                "checks": json.loads(p.checks_json or "[]"),
                "dry_run_mode": p.dry_run_mode,
                "dry_run_summary": json.loads(p.dry_run_summary_json or "{}"),
                "evaluated_by": p.evaluated_by,
                "evaluated_at": p.evaluated_at.isoformat() if p.evaluated_at else None,
            }
            for p in preflights
        ],
        "approvals": [
            {
                "id": ap.id,
                "decision": ap.decision,
                "approver_username": ap.approver_username,
                "approver_role": ap.approver_role,
                "comment": ap.comment,
                "decided_at": ap.decided_at.isoformat() if ap.decided_at else None,
            }
            for ap in approvals
        ],
        "executions": exec_payload,
        "audit_events": [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "actor_username": ev.actor_username,
                "actor_role": ev.actor_role,
                "from_status": ev.from_status,
                "to_status": ev.to_status,
                "details": json.loads(ev.details_json or "{}"),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in audits
        ],
    }


@router.post("/control-plane/actions/{action_id}/preflight")
def run_action_preflight(
    action_id: str,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    if action.status not in ("DRAFT", "VALIDATING", "DRY_RUN"):
        raise HTTPException(
            status_code=422,
            detail=f"Preflight cannot run from status '{action.status}'.",
        )
    old_status = action.status
    action.status = "VALIDATING"
    pf = run_preflight_and_dry_run(db, action=action, actor=current_user, org_id=org_id)
    action.status = "DRY_RUN" if pf.overall_status != "BLOCKED" else "FAILED"
    action.entity_version += 1

    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.preflight_completed",
        actor=current_user,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status=old_status,
        to_status=action.status,
        details={"overall_status": pf.overall_status, "dry_run_mode": pf.dry_run_mode},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.preflight_completed",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload={
            "id": action.id,
            "status": action.status,
            "overall_status": pf.overall_status,
            "dry_run_mode": pf.dry_run_mode,
        },
        required_permission="control_plane.read",
    )
    return {
        "action": _serialize_action(action),
        "preflight": {
            "id": pf.id,
            "overall_status": pf.overall_status,
            "checks": json.loads(pf.checks_json),
            "dry_run_mode": pf.dry_run_mode,
            "dry_run_summary": json.loads(pf.dry_run_summary_json),
        },
    }


@router.post("/control-plane/actions/{action_id}/submit-approval")
def submit_action_for_approval(
    action_id: str,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    if "PENDING_APPROVAL" not in VALID_ACTION_TRANSITIONS.get(action.status, set()):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot submit for approval from status '{action.status}'. Run preflight first.",
        )
    latest_pf = (
        db.query(ActionPreflightResult)
        .filter(ActionPreflightResult.action_request_id == action.id)
        .order_by(ActionPreflightResult.evaluated_at.desc())
        .first()
    )
    if not latest_pf or latest_pf.overall_status == "BLOCKED":
        raise HTTPException(
            status_code=422,
            detail="Cannot submit a BLOCKED action for approval.",
        )

    old_status = action.status
    action.status = "PENDING_APPROVAL"
    action.entity_version += 1
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.approval_requested",
        actor=current_user,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status=old_status,
        to_status="PENDING_APPROVAL",
        details={"operation": action.operation, "risk_level": action.risk_level},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.approval_requested",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload=_serialize_action(action),
        required_permission="control_plane.read",
        notify_user_ids=_admin_user_ids(db, org_id),
    )
    return _serialize_action(action)


@router.post("/control-plane/actions/{action_id}/approve")
def approve_action_request(
    action_id: str,
    payload: ActionDecisionRequest,
    current_user: User = Depends(require_permission("control_plane.actions.approve")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    raise_if_version_conflict(payload.expected_version, action.entity_version, "ActionRequest", action.id, _serialize_action(action))
    if action.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=422, detail=f"Cannot approve action in status '{action.status}'.")

    approval = ActionApproval(
        id=f"appr-{uuid.uuid4().hex[:10]}",
        action_request_id=action.id,
        organization_id=org_id,
        decision="APPROVED",
        approver_user_id=current_user.id,
        approver_username=current_user.username,
        approver_role=current_user.role,
        comment=payload.comment,
    )
    db.add(approval)
    action.status = "APPROVED"
    action.entity_version += 1

    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.approved",
        actor=current_user,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status="PENDING_APPROVAL",
        to_status="APPROVED",
        details={"comment": payload.comment},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.approved",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload={**_serialize_action(action), "approver": current_user.username, "comment": payload.comment},
        required_permission="control_plane.read",
        notify_user_ids=[action.requester_user_id],
    )
    return _serialize_action(action)


@router.post("/control-plane/actions/{action_id}/reject")
def reject_action_request(
    action_id: str,
    payload: ActionDecisionRequest,
    current_user: User = Depends(require_permission("control_plane.actions.approve")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    raise_if_version_conflict(payload.expected_version, action.entity_version, "ActionRequest", action.id, _serialize_action(action))
    if action.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=422, detail=f"Cannot reject action in status '{action.status}'.")

    approval = ActionApproval(
        id=f"appr-{uuid.uuid4().hex[:10]}",
        action_request_id=action.id,
        organization_id=org_id,
        decision="REJECTED",
        approver_user_id=current_user.id,
        approver_username=current_user.username,
        approver_role=current_user.role,
        comment=payload.comment,
    )
    db.add(approval)
    action.status = "REJECTED"
    action.entity_version += 1

    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.rejected",
        actor=current_user,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status="PENDING_APPROVAL",
        to_status="REJECTED",
        details={"comment": payload.comment},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.rejected",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload={**_serialize_action(action), "approver": current_user.username, "comment": payload.comment},
        required_permission="control_plane.read",
        notify_user_ids=[action.requester_user_id],
    )
    return _serialize_action(action)


@router.post("/control-plane/actions/{action_id}/cancel")
def cancel_action_request(
    action_id: str,
    payload: ActionCancelRequest,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    raise_if_version_conflict(payload.expected_version, action.entity_version, "ActionRequest", action.id, _serialize_action(action))
    if "CANCELLED" not in VALID_ACTION_TRANSITIONS.get(action.status, set()):
        raise HTTPException(status_code=422, detail=f"Cannot cancel action in status '{action.status}'.")

    old_status = action.status
    action.status = "CANCELLED"
    action.entity_version += 1
    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.cancelled",
        actor=current_user,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status=old_status,
        to_status="CANCELLED",
        details={"reason": payload.reason},
    )
    OutboxService.emit_and_commit(
        db=db,
        event_type="action.cancelled",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload={**_serialize_action(action), "reason": payload.reason},
        required_permission="control_plane.read",
    )
    return _serialize_action(action)


@router.post("/control-plane/actions/{action_id}/execute")
def execute_control_plane_action(
    action_id: str,
    current_user: User = Depends(require_permission("control_plane.actions.create")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    action = assert_org_resource(
        db.query(ActionRequest).filter(ActionRequest.id == action_id).first(),
        org_id,
        "ActionRequest",
    )
    if action.approval_required and action.status != "APPROVED":
        raise HTTPException(
            status_code=422,
            detail=f"Action requires Administrator approval before execution (current status: {action.status}).",
        )
    if not action.approval_required and action.status not in ("DRY_RUN", "APPROVED", "SCHEDULED"):
        raise HTTPException(
            status_code=422,
            detail=f"Action must pass preflight/dry-run before execution (current status: {action.status}).",
        )
    try:
        exec_rec = execute_read_only_action(db, action=action, actor=current_user, org_id=org_id)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    OutboxService.emit_and_commit(
        db=db,
        event_type="action.executed",
        resource_type="ActionRequest",
        resource_id=action.id,
        actor_user=current_user,
        organization_id=org_id,
        entity_version=action.entity_version,
        payload={**_serialize_action(action), "execution_id": exec_rec.id},
        required_permission="control_plane.read",
    )
    return {
        "action": _serialize_action(action),
        "execution_id": exec_rec.id,
        "result": json.loads(exec_rec.result_summary_json or "{}"),
    }


@router.get("/control-plane/locks")
def list_execution_locks(
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ResourceExecutionLock)
        .filter(ResourceExecutionLock.organization_id == org_id)
        .order_by(ResourceExecutionLock.acquired_at.desc())
        .limit(50)
        .all()
    )
    return {
        "locks": [
            {
                "id": l.id,
                "resource_type": l.resource_type,
                "resource_id": l.resource_id,
                "locked_by_action_id": l.locked_by_action_id,
                "lock_reason": l.lock_reason,
                "is_active": l.is_active,
                "acquired_at": l.acquired_at.isoformat() if l.acquired_at else None,
                "released_at": l.released_at.isoformat() if l.released_at else None,
            }
            for l in rows
        ]
    }


@router.get("/control-plane/audit")
def list_cp_audit_events(
    current_user: User = Depends(require_permission("control_plane.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ControlPlaneAuditEvent)
        .filter(ControlPlaneAuditEvent.organization_id == org_id)
        .order_by(ControlPlaneAuditEvent.created_at.desc())
        .limit(100)
        .all()
    )
    return {
        "events": [
            {
                "id": ev.id,
                "action_request_id": ev.action_request_id,
                "connector_id": ev.connector_id,
                "event_type": ev.event_type,
                "actor_username": ev.actor_username,
                "actor_role": ev.actor_role,
                "from_status": ev.from_status,
                "to_status": ev.to_status,
                "details": json.loads(ev.details_json or "{}"),
                "created_at": ev.created_at.isoformat() if ev.created_at else None,
            }
            for ev in rows
        ]
    }
