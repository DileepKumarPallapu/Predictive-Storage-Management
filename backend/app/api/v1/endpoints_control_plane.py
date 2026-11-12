"""Authenticated Control Plane foundation.

Sprint 1 deliberately implements only database-backed resource inspection and
capacity planning/approval. No infrastructure mutation connector is enabled.
"""
import hashlib
import json
import logging
import secrets
import uuid
import re
from datetime import timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.auth.control_plane import (
    get_control_plane_user, get_user_organization_id, require_control_plane_roles
)
from app.database import SessionLocal, get_db
from app.models.control_plane import (
    ActionApproval, ActionDefinition, ActionExecution, ActionRequest,
    ConnectorRegistry, ControlPlaneAuditEvent, ControlPlaneOutboxEvent, RealtimeTicket
)
from app.models.entities import Device, Telemetry, User
from app.models.enterprise_data import ConnectorMetricSnapshot, ConnectorTableSnapshot, ConnectorSyncRun
from app.services.connector_sync_service import ConnectorSyncService
from app.realtime.control_plane_manager import control_plane_connections
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("aegisstor.control_plane")
router = APIRouter(prefix="/control-plane", tags=["Control Plane"])

ADMIN = require_control_plane_roles("ADMIN")
OPERATOR = require_control_plane_roles("ADMIN", "OPERATOR")
READ_ACCESS = require_control_plane_roles("ADMIN", "OPERATOR", "AUDITOR", "VIEWER")

ALLOWED_PROVIDERS = {
    "POSTGRESQL", "MYSQL", "SQL_SERVER", "ORACLE",
    "LINUX_AGENT", "PROMETHEUS", "KUBERNETES_CSI", "S3_COMPATIBLE", "GENERIC_REST"
}
CREDENTIAL_REFERENCE_PATTERN = re.compile(r"^AEGISSTOR_CONNECTOR_[A-Z0-9_]{2,80}_URL$")
FORBIDDEN_CONFIG_KEYS = {
    "password", "secret", "token", "api_key", "apikey", "private_key",
    "client_secret", "access_key_secret", "authorization"
}


class ConnectorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = Field(min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    version: str | None = Field(default=None, max_length=40)
    configuration: dict[str, Any] = Field(default_factory=dict)
    credential_ref: str | None = Field(default=None, max_length=255)

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        value = value.upper()
        if value not in ALLOWED_PROVIDERS:
            raise ValueError(f"Unsupported provider. Allowed values: {', '.join(sorted(ALLOWED_PROVIDERS))}")
        return value

    @field_validator("credential_ref")
    @classmethod
    def validate_credential_reference(cls, value: str | None) -> str | None:
        if value is not None and not CREDENTIAL_REFERENCE_PATTERN.fullmatch(value.strip()):
            raise ValueError("Use an environment secret reference such as AEGISSTOR_CONNECTOR_HOSPITAL_PG_URL; never send a password or URL here.")
        return value.strip() if value else None

    @field_validator("configuration")
    @classmethod
    def reject_inline_secrets(cls, value: dict[str, Any]) -> dict[str, Any]:
        def walk(obj: Any, path: str = "configuration") -> None:
            if isinstance(obj, dict):
                for key, child in obj.items():
                    if str(key).lower() in FORBIDDEN_CONFIG_KEYS:
                        raise ValueError(f"Secret-like field '{path}.{key}' is not permitted. Use credential_ref.")
                    walk(child, f"{path}.{key}")
            elif isinstance(obj, str):
                lowered = obj.lower()
                if "://" in obj or "password=" in lowered or "pwd=" in lowered or "authorization:" in lowered:
                    raise ValueError(f"Connection URLs and credentials are not permitted in {path}. Use the backend secret reference.")
            elif isinstance(obj, list):
                for index, child in enumerate(obj):
                    walk(child, f"{path}[{index}]")
        walk(value)
        return value


class ActionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: str = Field(min_length=3, max_length=80)
    target_type: Literal["DEVICE"]
    target_id: str = Field(min_length=1, max_length=64)
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    rationale: str = Field(min_length=8, max_length=2000)


def _now():
    return utc_now()


def _org(user: User) -> str:
    return get_user_organization_id(user)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=lambda obj: obj.isoformat() if hasattr(obj, "isoformat") else str(obj)))


def _append_audit_and_outbox(
    db: Session,
    actor: User,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    entity_version: int = 1,
) -> ControlPlaneOutboxEvent:
    safe_payload = _json_safe(payload)
    canonical = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    db.add(ControlPlaneAuditEvent(
        id=f"cpa-{uuid.uuid4().hex}",
        organization_id=_org(actor),
        actor_user_id=actor.id,
        actor_role=actor.role,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_sha256=digest,
        payload_json=safe_payload,
    ))
    event = ControlPlaneOutboxEvent(
        event_id=f"cpe-{uuid.uuid4().hex}",
        organization_id=_org(actor),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_version=entity_version,
        actor_user_id=actor.id,
        actor_role=actor.role,
        payload_json=safe_payload,
    )
    db.add(event)
    db.flush()
    return event


async def _publish_committed_event(event: ControlPlaneOutboxEvent) -> None:
    payload = {
        "type": "control_plane.event",
        "sequence": event.id,
        "event_id": event.event_id,
        "event_type": event.event_type,
        "entity_type": event.entity_type,
        "entity_id": event.entity_id,
        "entity_version": event.entity_version,
        "actor_user_id": event.actor_user_id,
        "actor_role": event.actor_role,
        "organization_id": event.organization_id,
        "created_at": event.created_at.isoformat() if event.created_at else None,
        "payload": event.payload_json or {},
    }
    try:
        await control_plane_connections.broadcast(event.organization_id, payload)
    except Exception:
        # The committed event remains available through GET /events for recovery.
        logger.exception("Realtime broadcast failed for committed event %s.", event.event_id)


def _connector_dict(connector: ConnectorRegistry) -> dict[str, Any]:
    return {
        "id": connector.id,
        "organization_id": connector.organization_id,
        "provider": connector.provider,
        "name": connector.name,
        "version": connector.version,
        "status": connector.status,
        "configuration": connector.configuration_json or {},
        "capabilities": connector.capabilities_json or [],
        "credential_ref_configured": bool(connector.credential_ref),
        "last_health_check_at": connector.last_health_check_at.isoformat() if connector.last_health_check_at else None,
        "last_error": connector.last_error,
        "created_at": connector.created_at.isoformat() if connector.created_at else None,
        "updated_at": connector.updated_at.isoformat() if connector.updated_at else None,
    }


def _action_dict(action: ActionRequest) -> dict[str, Any]:
    return {
        "id": action.id,
        "organization_id": action.organization_id,
        "action_type": action.action_type,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "connector_id": action.connector_id,
        "parameters": action.parameters_json or {},
        "requested_by_id": action.requested_by_id,
        "requested_by_role": action.requested_by_role,
        "status": action.status,
        "risk_level": action.risk_level,
        "approval_required": action.approval_required,
        "preflight": action.preflight_json or {},
        "dry_run": action.dry_run_json or {},
        "output": action.output_json or {},
        "error_code": action.error_code,
        "error_message": action.error_message,
        "approved_by_id": action.approved_by_id,
        "approved_at": action.approved_at.isoformat() if action.approved_at else None,
        "approval_rationale": action.approval_rationale,
        "entity_version": action.entity_version,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "updated_at": action.updated_at.isoformat() if action.updated_at else None,
    }


def _get_device_for_org(db: Session, device_id: str, organization_id: str) -> Device:
    device = db.query(Device).filter(Device.id == device_id).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Storage resource not found.")
    if device.organization_id != organization_id:
        raise HTTPException(status_code=404, detail="Storage resource not found.")
    return device


def _latest_telemetry(db: Session, device_id: str):
    return (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.timestamp.desc())
        .first()
    )


def _preflight(db: Session, actor: User, definition: ActionDefinition, req: ActionCreate) -> dict[str, Any]:
    organization_id = _org(actor)
    if not definition.is_enabled:
        return {"verdict": "BLOCKED", "checks": [{"name": "action_enabled", "passed": False, "detail": "Action is disabled."}]}

    try:
        device = _get_device_for_org(db, req.target_id, organization_id)
    except HTTPException:
        return {"verdict": "BLOCKED", "checks": [{"name": "resource_scope", "passed": False, "detail": "Resource is missing or outside the user's organisation."}]}

    latest = _latest_telemetry(db, device.id)
    provenance = "UNKNOWN"
    if latest is not None:
        provenance = "SYNTHETIC" if latest.is_synthetic else "RECORDED_NON_SYNTHETIC"

    checks: list[dict[str, Any]] = [
        {"name": "action_enabled", "passed": True, "detail": "Action is enabled."},
        {"name": "resource_scope", "passed": True, "detail": "Resource belongs to the authenticated organisation."},
        {"name": "resource_capacity", "passed": device.total_capacity_bytes > 0, "detail": "Registered total capacity must be positive."},
    ]

    if req.action_type == "resource.inspect":
        verdict = "PASS" if all(item["passed"] for item in checks) else "BLOCKED"
        return {
            "verdict": verdict,
            "checks": checks,
            "data_provenance": provenance,
            "telemetry_timestamp": latest.timestamp.isoformat() if latest and latest.timestamp else None,
            "warnings": [] if latest is not None else ["No telemetry is stored for this resource; only inventory metadata can be inspected."],
            "physical_mutation": False,
            "note": "This operation reads AEGISSTOR's persisted inventory and telemetry records. It does not connect to or modify the physical storage provider.",
        }

    if req.action_type == "storage.capacity.plan":
        additional = req.parameters.get("additional_capacity_bytes")
        valid_additional = (
            isinstance(additional, int)
            and not isinstance(additional, bool)
            and 0 < additional <= (2**63 - 1 - device.total_capacity_bytes)
        )
        checks.append({
            "name": "additional_capacity",
            "passed": valid_additional,
            "detail": "additional_capacity_bytes must be positive and keep proposed total capacity within signed 64-bit byte range.",
        })
        if latest is None or latest.timestamp is None:
            checks.append({"name": "telemetry_available", "passed": False, "detail": "A timestamped telemetry observation is required for capacity planning."})
        else:
            observation_time = latest.timestamp
            if observation_time.tzinfo is None:
                observation_time = observation_time.replace(tzinfo=_now().tzinfo)
            age_seconds = max(0.0, (_now() - observation_time).total_seconds())
            fresh = age_seconds <= 3600
            checks.extend([
                {"name": "telemetry_provenance", "passed": not latest.is_synthetic, "detail": "Capacity planning requires non-synthetic telemetry."},
                {"name": "telemetry_freshness", "passed": fresh, "detail": f"Latest telemetry age is {age_seconds:.0f} seconds; maximum is 3600 seconds."},
                {"name": "capacity_consistency", "passed": 0 <= latest.used_bytes <= device.total_capacity_bytes, "detail": "Used capacity must be within registered total capacity."},
            ])
        passed = all(item["passed"] for item in checks)
        if not passed:
            return {
                "verdict": "BLOCKED",
                "checks": checks,
                "data_provenance": provenance,
                "physical_mutation": False,
                "note": "The plan cannot be submitted for approval until every required preflight check passes.",
            }

        proposed_total = device.total_capacity_bytes + additional
        used = latest.used_bytes
        return {
            "verdict": "PASS",
            "checks": checks,
            "data_provenance": provenance,
            "physical_mutation": False,
            "calculation": {
                "current_total_capacity_bytes": device.total_capacity_bytes,
                "current_used_capacity_bytes": used,
                "additional_capacity_bytes": additional,
                "proposed_total_capacity_bytes": proposed_total,
                "proposed_free_capacity_bytes": proposed_total - used,
                "proposed_utilization_pct": round(100.0 * used / proposed_total, 4),
            },
            "note": "This is a planning calculation only. Approval does not provision or resize infrastructure.",
        }

    return {"verdict": "BLOCKED", "checks": [{"name": "supported_action", "passed": False, "detail": "This action type has no Sprint 1 implementation."}]}


@router.get("/action-definitions")
def list_action_definitions(
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    definitions = db.query(ActionDefinition).order_by(ActionDefinition.action_type.asc()).all()
    return [
        {
            "action_type": item.action_type,
            "title": item.title,
            "description": item.description,
            "category": item.category,
            "risk_level": item.risk_level,
            "input_schema": item.input_schema_json or {},
            "required_capability": item.required_capability,
            "requires_approval": item.requires_approval,
            "is_enabled": item.is_enabled,
            "is_executable": item.is_executable,
        }
        for item in definitions
    ]


@router.post("/connectors", status_code=status.HTTP_201_CREATED)
async def register_connector(
    payload: ConnectorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(ADMIN),
):
    organization_id = _org(user)
    exists = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.organization_id == organization_id,
        ConnectorRegistry.name == payload.name,
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail="A connector with this name already exists in the organisation.")

    connector = ConnectorRegistry(
        id=f"cpc-{uuid.uuid4().hex}",
        organization_id=organization_id,
        provider=payload.provider,
        name=payload.name,
        version=payload.version,
        status="NOT_CONFIGURED",
        configuration_json=payload.configuration,
        capabilities_json=[],
        credential_ref=payload.credential_ref,
        created_by=user.id,
    )
    db.add(connector)
    db.flush()
    event = _append_audit_and_outbox(
        db, user, "connector.registered", "connector", connector.id,
        {"provider": connector.provider, "name": connector.name, "status": connector.status, "capabilities": []},
    )
    db.commit()
    db.refresh(connector)
    await _publish_committed_event(event)
    return _connector_dict(connector)


@router.get("/connectors")
def list_connectors(
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    rows = (
        db.query(ConnectorRegistry)
        .filter(ConnectorRegistry.organization_id == _org(user))
        .order_by(ConnectorRegistry.created_at.desc())
        .all()
    )
    return [_connector_dict(row) for row in rows]


@router.get("/connectors/{connector_id}")
def get_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    connector = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.id == connector_id,
        ConnectorRegistry.organization_id == _org(user),
    ).first()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found.")
    return _connector_dict(connector)


@router.post("/connectors/{connector_id}/health-check")
async def check_connector_health(
    connector_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(OPERATOR),
):
    connector = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.id == connector_id,
        ConnectorRegistry.organization_id == _org(user),
    ).first()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found.")

    result = ConnectorSyncService.health_check(connector)
    connector.last_health_check_at = _now()
    connector.status = result["status"]
    connector.last_error = None if result["connection_established"] else result.get("detail")
    connector.capabilities_json = result.get("capabilities", [])
    event = _append_audit_and_outbox(
        db, user,
        "connector.health_check_succeeded" if result["connection_established"] else "connector.health_check_failed",
        "connector", connector.id,
        {
            "status": connector.status,
            "connection_established": result["connection_established"],
            "provider": connector.provider,
            "capabilities": connector.capabilities_json,
        },
    )
    db.commit()
    db.refresh(connector)
    await _publish_committed_event(event)
    return {
        "connector_id": connector.id,
        **result,
        "checked_at": connector.last_health_check_at.isoformat(),
    }


@router.post("/actions", status_code=status.HTTP_201_CREATED)
async def create_action_request(
    payload: ActionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(OPERATOR),
):
    organization_id = _org(user)
    existing = db.query(ActionRequest).filter(
        ActionRequest.organization_id == organization_id,
        ActionRequest.idempotency_key == payload.idempotency_key,
    ).first()
    if existing:
        same_request = (
            existing.action_type == payload.action_type
            and existing.target_type == payload.target_type
            and existing.target_id == payload.target_id
            and (existing.parameters_json or {}) == payload.parameters
        )
        if not same_request:
            raise HTTPException(status_code=409, detail="Idempotency key was already used for a different request.")
        return _action_dict(existing)

    definition = db.query(ActionDefinition).filter(ActionDefinition.action_type == payload.action_type).first()
    if definition is None:
        raise HTTPException(status_code=422, detail="Unknown action type.")
    if payload.action_type not in {"resource.inspect", "storage.capacity.plan"}:
        raise HTTPException(status_code=403, detail="This action has no approved Sprint 1 implementation.")

    action = ActionRequest(
        id=f"cpa-{uuid.uuid4().hex}",
        organization_id=organization_id,
        action_type=definition.action_type,
        target_type=payload.target_type,
        target_id=payload.target_id,
        parameters_json=payload.parameters,
        idempotency_key=payload.idempotency_key,
        requested_by_id=user.id,
        requested_by_role=user.role,
        status="VALIDATING",
        risk_level=definition.risk_level,
        approval_required=definition.requires_approval,
    )
    db.add(action)
    db.flush()

    preflight = _preflight(db, user, definition, payload)
    action.preflight_json = preflight
    action.dry_run_json = preflight.get("calculation", {})
    if preflight["verdict"] != "PASS":
        action.status = "BLOCKED"
        action.error_code = "PREFLIGHT_BLOCKED"
        action.error_message = "One or more preflight checks failed."
    elif definition.requires_approval:
        action.status = "PENDING_APPROVAL"
    else:
        action.status = "DRY_RUN"
    action.entity_version += 1

    event_type = "action.blocked" if action.status == "BLOCKED" else "action.approval_requested" if action.status == "PENDING_APPROVAL" else "action.created"
    event = _append_audit_and_outbox(
        db, user, event_type, "action_request", action.id,
        {"action_type": action.action_type, "target_id": action.target_id, "status": action.status, "preflight_verdict": preflight["verdict"]},
        action.entity_version,
    )
    db.commit()
    db.refresh(action)
    await _publish_committed_event(event)
    return _action_dict(action)


@router.get("/actions")
def list_action_requests(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    query = db.query(ActionRequest).filter(ActionRequest.organization_id == _org(user))
    if status_filter:
        query = query.filter(ActionRequest.status == status_filter.upper())
    rows = query.order_by(ActionRequest.created_at.desc()).limit(limit).all()
    return [_action_dict(row) for row in rows]


@router.get("/actions/{action_id}")
def get_action_request(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    row = db.query(ActionRequest).filter(
        ActionRequest.id == action_id,
        ActionRequest.organization_id == _org(user),
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Action request not found.")
    return _action_dict(row)


@router.post("/actions/{action_id}/approve")
async def approve_action_plan(
    action_id: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(ADMIN),
):
    row = db.query(ActionRequest).filter(
        ActionRequest.id == action_id,
        ActionRequest.organization_id == _org(user),
    ).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Action request not found.")
    if row.action_type != "storage.capacity.plan" or not row.approval_required:
        raise HTTPException(status_code=409, detail="This action is not an approval-controlled capacity plan.")
    if row.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail=f"Action cannot be approved from state {row.status}.")
    if row.entity_version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Action version changed. Reload the request before approving.")
    if row.requested_by_id == user.id:
        raise HTTPException(status_code=403, detail="A requester cannot approve their own capacity plan.")

    approval = ActionApproval(
        id=f"cpa-{uuid.uuid4().hex}",
        action_request_id=row.id,
        reviewer_id=user.id,
        decision="APPROVED",
        rationale=payload.rationale,
        action_version=row.entity_version,
    )
    db.add(approval)
    row.status = "APPROVED"
    row.approved_by_id = user.id
    row.approved_at = _now()
    row.approval_rationale = payload.rationale
    row.entity_version += 1
    row.updated_at = _now()
    event = _append_audit_and_outbox(
        db, user, "action.approved", "action_request", row.id,
        {"status": row.status, "approved_by_id": user.id, "rationale": payload.rationale},
        row.entity_version,
    )
    db.commit()
    db.refresh(row)
    await _publish_committed_event(event)
    return _action_dict(row)


@router.post("/actions/{action_id}/reject")
async def reject_action_plan(
    action_id: str,
    payload: ApprovalDecision,
    db: Session = Depends(get_db),
    user: User = Depends(ADMIN),
):
    row = db.query(ActionRequest).filter(
        ActionRequest.id == action_id,
        ActionRequest.organization_id == _org(user),
    ).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Action request not found.")
    if row.action_type != "storage.capacity.plan" or row.status != "PENDING_APPROVAL":
        raise HTTPException(status_code=409, detail="Action is not awaiting approval.")
    if row.entity_version != payload.expected_version:
        raise HTTPException(status_code=409, detail="Action version changed. Reload the request before rejecting.")
    approval = ActionApproval(
        id=f"cpa-{uuid.uuid4().hex}",
        action_request_id=row.id,
        reviewer_id=user.id,
        decision="REJECTED",
        rationale=payload.rationale,
        action_version=row.entity_version,
    )
    db.add(approval)
    row.status = "REJECTED"
    row.entity_version += 1
    row.updated_at = _now()
    event = _append_audit_and_outbox(
        db, user, "action.rejected", "action_request", row.id,
        {"status": row.status, "reviewed_by_id": user.id, "rationale": payload.rationale},
        row.entity_version,
    )
    db.commit()
    db.refresh(row)
    await _publish_committed_event(event)
    return _action_dict(row)


@router.post("/actions/{action_id}/execute-read-only")
async def execute_read_only_action(
    action_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(OPERATOR),
):
    row = db.query(ActionRequest).filter(
        ActionRequest.id == action_id,
        ActionRequest.organization_id == _org(user),
    ).with_for_update().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Action request not found.")
    if row.action_type != "resource.inspect":
        raise HTTPException(status_code=403, detail="Only the implemented read-only resource inspection action can execute in Sprint 1.")
    if row.status != "DRY_RUN":
        raise HTTPException(status_code=409, detail=f"Read-only action cannot execute from state {row.status}.")

    device = _get_device_for_org(db, row.target_id, _org(user))
    latest = _latest_telemetry(db, device.id)
    started = _now()
    result = {
        "resource_id": device.id,
        "name": device.name,
        "tier": device.tier,
        "media_type": device.media_type,
        "total_capacity_bytes": device.total_capacity_bytes,
        "status": device.status,
        "latest_telemetry": None if latest is None else {
            "timestamp": latest.timestamp.isoformat() if latest.timestamp else None,
            "used_bytes": latest.used_bytes,
            "free_bytes": latest.free_bytes,
            "utilization_pct": latest.utilization_pct,
            "is_synthetic": bool(latest.is_synthetic),
            "source_label": latest.source_label,
            "provenance": "SYNTHETIC" if latest.is_synthetic else "RECORDED_NON_SYNTHETIC",
        },
        "physical_mutation": False,
    }
    completed = _now()
    row.status = "SUCCEEDED"
    row.output_json = result
    row.entity_version += 1
    row.updated_at = completed
    execution = ActionExecution(
        id=f"cpe-{uuid.uuid4().hex}",
        action_request_id=row.id,
        execution_mode="READ_ONLY_DATABASE_INSPECTION",
        status="SUCCEEDED",
        result_json=result,
        verification_json={"verified": True, "method": "Read-after-query against persisted AEGISSTOR database record"},
        started_at=started,
        completed_at=completed,
    )
    db.add(execution)
    event = _append_audit_and_outbox(
        db, user, "action.succeeded", "action_request", row.id,
        {"status": row.status, "action_type": row.action_type, "physical_mutation": False},
        row.entity_version,
    )
    db.commit()
    db.refresh(row)
    await _publish_committed_event(event)
    return _action_dict(row)


@router.get("/events")
def recover_events(
    after_sequence: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    rows = (
        db.query(ControlPlaneOutboxEvent)
        .filter(
            ControlPlaneOutboxEvent.organization_id == _org(user),
            ControlPlaneOutboxEvent.id > after_sequence,
        )
        .order_by(ControlPlaneOutboxEvent.id.asc())
        .limit(limit)
        .all()
    )
    return {
        "events": [
            {
                "sequence": row.id,
                "event_id": row.event_id,
                "event_type": row.event_type,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "entity_version": row.entity_version,
                "actor_user_id": row.actor_user_id,
                "actor_role": row.actor_role,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "payload": row.payload_json or {},
            }
            for row in rows
        ],
        "next_sequence": rows[-1].id if rows else after_sequence,
        "has_more": len(rows) == limit,
    }


@router.post("/realtime/ticket")
def create_realtime_ticket(
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    raw_ticket = secrets.token_urlsafe(32)
    ticket_hash = hashlib.sha256(raw_ticket.encode("utf-8")).hexdigest()
    expires_at = _now() + timedelta(seconds=60)
    db.add(RealtimeTicket(
        ticket_hash=ticket_hash,
        user_id=user.id,
        organization_id=_org(user),
        expires_at=expires_at,
    ))
    db.commit()
    return {"ticket": raw_ticket, "expires_in_seconds": 60, "single_use": True}


@router.websocket("/ws")
async def control_plane_websocket(websocket: WebSocket, ticket: str = Query(..., min_length=20, max_length=200)):
    ticket_hash = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
    db = SessionLocal()
    user = None
    organization_id = None
    try:
        record = db.query(RealtimeTicket).filter(
            RealtimeTicket.ticket_hash == ticket_hash,
            RealtimeTicket.consumed_at.is_(None),
            RealtimeTicket.expires_at > _now(),
        ).with_for_update().first()
        if record is None:
            await websocket.close(code=4401, reason="Invalid or expired one-time ticket.")
            return
        user = db.query(User).filter(User.id == record.user_id).first()
        if user is None or not user.is_active or user.role not in CONTROL_PLANE_ROLES:
            await websocket.close(code=4403, reason="User is not authorised.")
            return
        if getattr(user, "organization_id", None) != record.organization_id:
            await websocket.close(code=4403, reason="Organisation scope changed.")
            return
        record.consumed_at = _now()
        db.commit()
        organization_id = record.organization_id
    finally:
        db.close()

    await control_plane_connections.connect(organization_id, websocket)
    try:
        await websocket.send_json({
            "type": "connection.ready",
            "organization_id": organization_id,
            "user_id": user.id,
            "role": user.role,
            "server_time": _now().isoformat(),
            "recovery_endpoint": "/api/v1/control-plane/events",
        })
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() in {"ping", '{"type":"ping"}'}:
                await websocket.send_json({"type": "pong", "server_time": _now().isoformat()})
            else:
                await websocket.send_json({"type": "error", "code": "READ_ONLY_CHANNEL", "detail": "Commands must use authenticated REST endpoints."})
    except WebSocketDisconnect:
        pass
    finally:
        await control_plane_connections.disconnect(organization_id, websocket)



@router.post("/connectors/{connector_id}/sync")
def sync_enterprise_database_connector(
    connector_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(OPERATOR),
):
    connector = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.id == connector_id,
        ConnectorRegistry.organization_id == _org(user),
    ).first()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found.")
    if connector.provider not in {"POSTGRESQL", "MYSQL", "SQL_SERVER", "ORACLE"}:
        raise HTTPException(status_code=422, detail="This connector provider does not have a database metadata adapter.")

    result = ConnectorSyncService.sync(db, connector)
    event = _append_audit_and_outbox(
        db, user,
        "connector.sync_succeeded" if result["status"] == "SUCCEEDED" else "connector.sync_failed",
        "connector", connector.id,
        {
            "status": result["status"],
            "sync_run_id": result.get("sync_run_id"),
            "database_size_bytes": result.get("database_size_bytes"),
            "table_count": result.get("table_count"),
            "provenance": result.get("provenance", "LIVE"),
            "synthetic": False,
        },
    )
    db.commit()
    db.refresh(connector)
    return {**result, "connector_id": connector.id, "connector_status": connector.status}


@router.get("/connectors/{connector_id}/snapshots")
def list_connector_snapshots(
    connector_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    connector = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.id == connector_id,
        ConnectorRegistry.organization_id == _org(user),
    ).first()
    if connector is None:
        raise HTTPException(status_code=404, detail="Connector not found.")
    rows = (
        db.query(ConnectorMetricSnapshot)
        .filter(
            ConnectorMetricSnapshot.connector_id == connector_id,
            ConnectorMetricSnapshot.organization_id == _org(user),
        )
        .order_by(ConnectorMetricSnapshot.sampled_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": row.id,
            "sync_run_id": row.sync_run_id,
            "provider": row.provider,
            "database_name": row.database_name,
            "server_version": row.server_version,
            "sampled_at": row.sampled_at.isoformat(),
            "database_size_bytes": row.database_size_bytes,
            "configured_capacity_bytes": row.configured_capacity_bytes,
            "used_bytes": row.used_bytes,
            "free_bytes": row.free_bytes,
            "utilization_pct": row.utilization_pct,
            "table_count": row.table_count,
            "estimated_row_count": row.estimated_row_count,
            "active_connections": row.active_connections,
            "read_operations_total": row.read_operations_total,
            "write_operations_total": row.write_operations_total,
            "cache_hit_ratio_pct": row.cache_hit_ratio_pct,
            "provenance": row.provenance,
            "is_synthetic": row.is_synthetic,
            "metrics": row.metrics_json or {},
        }
        for row in rows
    ]


@router.get("/database-inventory")
def list_enterprise_database_inventory(
    connector_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    query = db.query(ConnectorTableSnapshot).filter(
        ConnectorTableSnapshot.organization_id == _org(user)
    )
    if connector_id:
        owned = db.query(ConnectorRegistry.id).filter(
            ConnectorRegistry.id == connector_id,
            ConnectorRegistry.organization_id == _org(user),
        ).first()
        if owned is None:
            raise HTTPException(status_code=404, detail="Connector not found.")
        query = query.filter(ConnectorTableSnapshot.connector_id == connector_id)

    rows = query.order_by(
        ConnectorTableSnapshot.sampled_at.desc(),
        ConnectorTableSnapshot.total_bytes.desc(),
    ).limit(limit).all()
    return [
        {
            "id": row.id,
            "connector_id": row.connector_id,
            "sync_run_id": row.sync_run_id,
            "schema_name": row.schema_name,
            "table_name": row.table_name,
            "estimated_row_count": row.estimated_row_count,
            "data_bytes": row.data_bytes,
            "index_bytes": row.index_bytes,
            "total_bytes": row.total_bytes,
            "sampled_at": row.sampled_at.isoformat(),
            "provenance": "LIVE",
        }
        for row in rows
    ]


@router.get("/data-source-summary")
def get_enterprise_data_source_summary(
    db: Session = Depends(get_db),
    user: User = Depends(READ_ACCESS),
):
    org_id = _org(user)
    connectors = db.query(ConnectorRegistry).filter(
        ConnectorRegistry.organization_id == org_id
    ).all()
    results = []
    for connector in connectors:
        latest = (
            db.query(ConnectorMetricSnapshot)
            .filter(
                ConnectorMetricSnapshot.connector_id == connector.id,
                ConnectorMetricSnapshot.organization_id == org_id,
            )
            .order_by(ConnectorMetricSnapshot.sampled_at.desc())
            .first()
        )
        results.append({
            "connector_id": connector.id,
            "name": connector.name,
            "provider": connector.provider,
            "status": connector.status,
            "last_successful_snapshot_at": latest.sampled_at.isoformat() if latest else None,
            "database_name": latest.database_name if latest else None,
            "database_size_bytes": latest.database_size_bytes if latest else None,
            "table_count": latest.table_count if latest else None,
            "provenance": latest.provenance if latest else "NO_DATA",
            "is_synthetic": latest.is_synthetic if latest else False,
        })
    return {
        "connector_count": len(connectors),
        "healthy_count": sum(1 for x in connectors if x["status"] == "HEALTHY"),
        "degraded_count": sum(1 for x in connectors if x["status"] == "DEGRADED"),
        "error_count": sum(1 for x in connectors if x["status"] == "ERROR"),
        "not_configured_count": sum(1 for x in connectors if x["status"] == "NOT_CONFIGURED"),
        "sources": results,
    }
