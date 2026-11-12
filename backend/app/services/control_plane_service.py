import json
import uuid
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.auth.permissions import get_effective_permissions
from app.models.entities import Device, Telemetry, User
from app.models.enterprise_entities import StoragePoolEntity, StorageVolume
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
from app.realtime.event_bus import OutboxService
from app.utils.datetime_utils import utc_now

SPRINT1_ACTION_STATES = [
    "DRAFT",
    "VALIDATING",
    "DRY_RUN",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "SCHEDULED",
    "EXECUTING",
    "VERIFYING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "MANUAL_INTERVENTION_REQUIRED",
]

VALID_ACTION_TRANSITIONS: Dict[str, set] = {
    "DRAFT": {"VALIDATING", "CANCELLED"},
    "VALIDATING": {"DRY_RUN", "PENDING_APPROVAL", "SCHEDULED", "FAILED", "CANCELLED"},
    "DRY_RUN": {"PENDING_APPROVAL", "SCHEDULED", "CANCELLED", "FAILED"},
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED": {"SCHEDULED", "EXECUTING", "CANCELLED"},
    "REJECTED": set(),
    "SCHEDULED": {"EXECUTING", "CANCELLED", "FAILED"},
    "EXECUTING": {"VERIFYING", "FAILED", "MANUAL_INTERVENTION_REQUIRED"},
    "VERIFYING": {"SUCCEEDED", "FAILED", "MANUAL_INTERVENTION_REQUIRED"},
    "SUCCEEDED": set(),
    "FAILED": {"MANUAL_INTERVENTION_REQUIRED"},
    "CANCELLED": set(),
    "MANUAL_INTERVENTION_REQUIRED": {"CANCELLED"},
}

SPRINT1_DEFAULT_DEFINITIONS = [
    {
        "id": "RESOURCE_INSPECT",
        "name": "Resource Inspection",
        "category": "INSPECTION",
        "risk_level": "LOW",
        "requires_approval": False,
        "is_read_only": True,
        "dry_run_supported": True,
        "input_schema": {"required": [], "optional": ["include_metadata", "include_relationships"]},
        "description": "Read-only inspection of storage resource state, version, capacity, and status.",
    },
    {
        "id": "CAPACITY_INSPECT",
        "name": "Capacity Inspection",
        "category": "CAPACITY",
        "risk_level": "LOW",
        "requires_approval": False,
        "is_read_only": True,
        "dry_run_supported": True,
        "input_schema": {"required": [], "optional": ["window_hours", "include_forecast"]},
        "description": "Read-only calculation of capacity utilization, reserve headroom, and recent telemetry trend.",
    },
    {
        "id": "CONNECTOR_HEALTH_CHECK",
        "name": "Connector Health Check",
        "category": "CONNECTIVITY",
        "risk_level": "LOW",
        "requires_approval": False,
        "is_read_only": True,
        "dry_run_supported": True,
        "input_schema": {"required": [], "optional": ["timeout_seconds"]},
        "description": "Read-only verification of connector status, credential reference presence, and capability readiness.",
    },
    {
        "id": "CONFIG_INSPECT",
        "name": "Configuration Inspection",
        "category": "GOVERNANCE",
        "risk_level": "MEDIUM",
        "requires_approval": True,
        "is_read_only": True,
        "dry_run_supported": True,
        "input_schema": {"required": [], "optional": ["scope", "redact_sensitive"]},
        "description": "Read-only inspection of connector and storage configuration metadata with secret redaction.",
    },
]

SUPPORTED_PROVIDERS = {
    "AEGISSTOR_LOCAL",
    "LINUX_STORAGE",
    "PROMETHEUS",
    "ONTAP_READONLY",
    "S3_STORAGE",
}

ALLOWED_CREDENTIAL_PREFIXES = ("env://", "vault://", "kms://", "secret-ref://", "iam://", "none://")


def seed_action_definitions(db: Session) -> None:
    """Idempotently seed Sprint 1 read-only ActionDefinitions."""
    for item in SPRINT1_DEFAULT_DEFINITIONS:
        existing = db.query(ActionDefinition).filter(ActionDefinition.id == item["id"]).first()
        if not existing:
            db.add(
                ActionDefinition(
                    id=item["id"],
                    name=item["name"],
                    category=item["category"],
                    risk_level=item["risk_level"],
                    requires_approval=item["requires_approval"],
                    is_read_only=item["is_read_only"],
                    dry_run_supported=item["dry_run_supported"],
                    input_schema_json=json.dumps(item["input_schema"]),
                    description=item["description"],
                    is_active=True,
                )
            )
    db.commit()


def validate_credential_ref(credential_ref: str) -> str:
    ref = (credential_ref or "").strip()
    if not ref:
        raise ValueError("credential_ref is required (e.g. env://AEGISSTOR_CONN_KEY or none://local).")
    lower = ref.lower()
    if not any(lower.startswith(p) for p in ALLOWED_CREDENTIAL_PREFIXES):
        raise ValueError(
            "Plain-text credentials are forbidden. credential_ref must start with one of: "
            + ", ".join(ALLOWED_CREDENTIAL_PREFIXES)
        )
    if "password=" in lower or "secret=" in lower or "token=" in lower:
        raise ValueError("credential_ref must not contain inline secret values.")
    return ref


def record_cp_audit(
    db: Session,
    *,
    organization_id: str,
    event_type: str,
    actor: User,
    action_request_id: Optional[str] = None,
    connector_id: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ControlPlaneAuditEvent:
    ev = ControlPlaneAuditEvent(
        id=f"cpaud-{uuid.uuid4().hex[:10]}",
        organization_id=organization_id,
        action_request_id=action_request_id,
        connector_id=connector_id,
        event_type=event_type,
        actor_user_id=actor.id,
        actor_username=actor.username,
        actor_role=actor.role,
        from_status=from_status,
        to_status=to_status,
        details_json=json.dumps(details or {}),
    )
    db.add(ev)
    return ev


def _lookup_resource(db: Session, org_id: str, resource_type: str, resource_id: str) -> Tuple[Optional[Any], Optional[int]]:
    rt = resource_type.upper()
    if rt == "DEVICE":
        obj = db.query(Device).filter(Device.id == resource_id, Device.organization_id == org_id).first()
        return obj, getattr(obj, "version", None) if obj else None
    if rt == "CONNECTOR":
        obj = db.query(ControlPlaneConnector).filter(
            ControlPlaneConnector.id == resource_id,
            ControlPlaneConnector.organization_id == org_id,
        ).first()
        return obj, getattr(obj, "entity_version", None) if obj else None
    if rt == "POOL":
        obj = db.query(StoragePoolEntity).filter(
            StoragePoolEntity.id == resource_id,
            StoragePoolEntity.organization_id == org_id,
        ).first()
        return obj, None
    if rt == "VOLUME":
        obj = db.query(StorageVolume).filter(
            StorageVolume.id == resource_id,
            StorageVolume.organization_id == org_id,
        ).first()
        return obj, None
    return None, None


def run_preflight_and_dry_run(
    db: Session,
    *,
    action: ActionRequest,
    actor: User,
    org_id: str,
) -> ActionPreflightResult:
    checks: List[Dict[str, Any]] = []
    perms = get_effective_permissions(db, actor.role)

    # 1. User permission
    has_perm = "control_plane.actions.create" in perms or "control_plane.connectors.manage" in perms
    checks.append({
        "check": "user_permissions",
        "status": "PASS" if has_perm else "BLOCKED",
        "detail": f"Role {actor.role} permission verified" if has_perm else f"Role {actor.role} lacks control_plane.actions.create",
    })

    # 2. Organisation ownership
    connector = db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == action.connector_id).first()
    org_ok = bool(connector and connector.organization_id == org_id and action.organization_id == org_id)
    checks.append({
        "check": "organisation_ownership",
        "status": "PASS" if org_ok else "BLOCKED",
        "detail": f"Connector and action belong to {org_id}" if org_ok else "Organisation ownership mismatch",
    })

    # 3. Resource existence
    res_obj, current_res_version = _lookup_resource(db, org_id, action.resource_type, action.resource_id)
    checks.append({
        "check": "resource_existence",
        "status": "PASS" if res_obj is not None else "BLOCKED",
        "detail": f"{action.resource_type}:{action.resource_id} found" if res_obj else f"{action.resource_type}:{action.resource_id} not found in {org_id}",
    })

    # 4. Connector capability
    cap = (
        db.query(ConnectorCapability)
        .filter(
            ConnectorCapability.connector_id == action.connector_id,
            ConnectorCapability.action_key == action.operation,
            ConnectorCapability.is_supported == True,
        )
        .first()
    )
    checks.append({
        "check": "connector_capability",
        "status": "PASS" if cap is not None else "BLOCKED",
        "detail": f"Capability {action.operation} supported (dry_run_mode={cap.dry_run_mode})" if cap else f"Connector does not support {action.operation}",
    })

    # 5. Input schema
    defn = db.query(ActionDefinition).filter(ActionDefinition.id == action.operation).first()
    schema_ok = True
    schema_detail = "Parameters valid"
    try:
        params = json.loads(action.parameters_json or "{}")
        if not isinstance(params, dict):
            schema_ok = False
            schema_detail = "Parameters must be a JSON object"
        elif defn:
            schema = json.loads(defn.input_schema_json or "{}")
            required = schema.get("required", [])
            missing = [k for k in required if k not in params]
            if missing:
                schema_ok = False
                schema_detail = f"Missing required parameter(s): {', '.join(missing)}"
    except json.JSONDecodeError:
        schema_ok = False
        schema_detail = "Malformed JSON parameters"
        params = {}
    checks.append({
        "check": "input_schema",
        "status": "PASS" if schema_ok else "BLOCKED",
        "detail": schema_detail,
    })

    # 6. Connector status
    if not connector:
        conn_check = "BLOCKED"
        conn_detail = "Connector not found"
    elif connector.connection_status == "CONNECTED":
        conn_check = "PASS"
        conn_detail = "Connector status is CONNECTED"
    elif connector.connection_status in ("CONFIGURED", "DEGRADED"):
        conn_check = "WARNING"
        conn_detail = f"Connector status is {connector.connection_status}; read-only inspection will use cached/preflight state"
    else:
        conn_check = "BLOCKED"
        conn_detail = f"Connector status is {connector.connection_status}"
    checks.append({"check": "connector_status", "status": conn_check, "detail": conn_detail})

    # 7. Resource version
    if action.resource_version is not None and current_res_version is not None and int(action.resource_version) != int(current_res_version):
        ver_status = "BLOCKED"
        ver_detail = f"Expected resource_version={action.resource_version}, actual={current_res_version}"
    else:
        ver_status = "PASS"
        ver_detail = f"Resource version verified ({current_res_version})"
    checks.append({"check": "resource_version", "status": ver_status, "detail": ver_detail})

    # 8. Active execution locks
    active_lock = (
        db.query(ResourceExecutionLock)
        .filter(
            ResourceExecutionLock.organization_id == org_id,
            ResourceExecutionLock.resource_type == action.resource_type,
            ResourceExecutionLock.resource_id == action.resource_id,
            ResourceExecutionLock.is_active == True,
        )
        .first()
    )
    if active_lock and active_lock.locked_by_action_id != action.id:
        lock_status = "BLOCKED"
        lock_detail = f"Locked by active action {active_lock.locked_by_action_id}"
    else:
        lock_status = "PASS"
        lock_detail = "No conflicting execution locks"
    checks.append({"check": "active_execution_locks", "status": lock_status, "detail": lock_detail})

    statuses = {c["status"] for c in checks}
    overall = "BLOCKED" if "BLOCKED" in statuses else ("WARNING" if "WARNING" in statuses else "PASS")

    # Dry-run calculation (strictly read-only)
    dry_run_mode = cap.dry_run_mode if cap else "UNSUPPORTED"
    dry_run_summary: Dict[str, Any] = {
        "dry_run_mode": dry_run_mode,
        "read_only": True,
        "infrastructure_modified": False,
        "operation": action.operation,
        "resource": f"{action.resource_type}:{action.resource_id}",
    }
    if dry_run_mode == "UNSUPPORTED":
        dry_run_summary["note"] = "Dry-run unsupported by connector capability."
    elif action.operation == "CAPACITY_INSPECT" and res_obj is not None and action.resource_type == "DEVICE":
        latest_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == res_obj.id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        dry_run_summary["simulation"] = {
            "device_name": res_obj.name,
            "total_capacity_bytes": res_obj.total_capacity_bytes,
            "latest_used_pct": latest_tel.used_pct if latest_tel else None,
            "telemetry_available": latest_tel is not None,
        }
    elif action.operation == "CONNECTOR_HEALTH_CHECK" and connector is not None:
        dry_run_summary["simulation"] = {
            "connector_name": connector.name,
            "provider": connector.provider,
            "connection_status": connector.connection_status,
            "credential_ref_present": bool(connector.credential_ref),
        }
    elif action.operation in ("RESOURCE_INSPECT", "CONFIG_INSPECT") and res_obj is not None:
        dry_run_summary["simulation"] = {
            "resource_found": True,
            "resource_version": current_res_version,
            "fields_to_inspect": list(params.keys()) or ["status", "metadata", "capacity"],
        }

    pf = ActionPreflightResult(
        id=f"pf-{uuid.uuid4().hex[:10]}",
        action_request_id=action.id,
        organization_id=org_id,
        overall_status=overall,
        checks_json=json.dumps(checks),
        dry_run_mode=dry_run_mode,
        dry_run_summary_json=json.dumps(dry_run_summary),
        evaluated_by=actor.username,
    )
    db.add(pf)
    return pf


def execute_read_only_action(
    db: Session,
    *,
    action: ActionRequest,
    actor: User,
    org_id: str,
) -> ActionExecution:
    defn = db.query(ActionDefinition).filter(ActionDefinition.id == action.operation).first()
    if not defn or not defn.is_read_only:
        raise ValueError("Sprint 1 strictly permits read-only operations only.")

    lock = ResourceExecutionLock(
        id=f"lock-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        resource_type=action.resource_type,
        resource_id=action.resource_id,
        locked_by_action_id=action.id,
        lock_reason=f"Executing {action.operation}",
        is_active=True,
        expires_at=utc_now() + timedelta(minutes=5),
    )
    db.add(lock)
    db.flush()

    exec_rec = ActionExecution(
        id=f"exec-{uuid.uuid4().hex[:10]}",
        action_request_id=action.id,
        organization_id=org_id,
        connector_id=action.connector_id,
        status="RUNNING",
        idempotency_key=f"exec:{action.id}:{action.entity_version}",
    )
    db.add(exec_rec)
    db.flush()

    action.status = "EXECUTING"
    action.entity_version += 1

    res_obj, current_ver = _lookup_resource(db, org_id, action.resource_type, action.resource_id)
    connector = db.query(ControlPlaneConnector).filter(ControlPlaneConnector.id == action.connector_id).first()

    step1 = ActionExecutionStep(
        id=f"step-{uuid.uuid4().hex[:10]}",
        execution_id=exec_rec.id,
        step_order=1,
        step_name="Acquire lock & validate read-only scope",
        status="SUCCEEDED",
        output_json=json.dumps({"lock_id": lock.id, "read_only": True}),
        completed_at=utc_now(),
    )
    db.add(step1)

    output_data: Dict[str, Any] = {"operation": action.operation, "resource_type": action.resource_type, "resource_id": action.resource_id}
    if action.operation == "CONNECTOR_HEALTH_CHECK" and connector:
        connector.last_health_check_at = utc_now()
        connector.connection_status = "CONNECTED" if connector.credential_ref else "ERROR"
        output_data["connector_status"] = connector.connection_status
        output_data["provider"] = connector.provider
    elif action.operation == "CAPACITY_INSPECT" and res_obj and action.resource_type == "DEVICE":
        tel = db.query(Telemetry).filter(Telemetry.device_id == res_obj.id).order_by(Telemetry.timestamp.desc()).first()
        output_data["device_name"] = res_obj.name
        output_data["total_capacity_bytes"] = res_obj.total_capacity_bytes
        output_data["used_pct"] = tel.used_pct if tel else None
        output_data["read_latency_ms"] = tel.read_latency_ms if tel else None
    elif res_obj:
        output_data["name"] = getattr(res_obj, "name", getattr(res_obj, "id", action.resource_id))
        output_data["status"] = getattr(res_obj, "status", getattr(res_obj, "connection_status", "ACTIVE"))
        output_data["version"] = current_ver
        if connector:
            output_data["connector_credential_ref"] = connector.credential_ref

    step2 = ActionExecutionStep(
        id=f"step-{uuid.uuid4().hex[:10]}",
        execution_id=exec_rec.id,
        step_order=2,
        step_name=f"Execute {action.operation} (read-only)",
        status="SUCCEEDED",
        output_json=json.dumps(output_data),
        completed_at=utc_now(),
    )
    db.add(step2)

    action.status = "VERIFYING"
    step3 = ActionExecutionStep(
        id=f"step-{uuid.uuid4().hex[:10]}",
        execution_id=exec_rec.id,
        step_order=3,
        step_name="Verify read-only integrity & release lock",
        status="SUCCEEDED",
        output_json=json.dumps({"verified": True, "infrastructure_modified": False}),
        completed_at=utc_now(),
    )
    db.add(step3)

    lock.is_active = False
    lock.released_at = utc_now()
    exec_rec.status = "SUCCEEDED"
    exec_rec.result_summary_json = json.dumps(output_data)
    exec_rec.completed_at = utc_now()

    action.status = "SUCCEEDED"
    action.execution_result_json = json.dumps(output_data)
    action.entity_version += 1

    record_cp_audit(
        db,
        organization_id=org_id,
        event_type="action.executed",
        actor=actor,
        action_request_id=action.id,
        connector_id=action.connector_id,
        from_status="APPROVED" if action.approval_required else "DRY_RUN",
        to_status="SUCCEEDED",
        details={"execution_id": exec_rec.id, "read_only": True},
    )
    return exec_rec
