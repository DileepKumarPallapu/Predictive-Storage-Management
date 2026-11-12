from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from app.database import Base
from app.utils.datetime_utils import utc_now


class ControlPlaneConnector(Base):
    __tablename__ = "connectors"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    provider = Column(String(64), nullable=False)  # LINUX_STORAGE, PROMETHEUS, ONTAP_READONLY, S3_STORAGE, AEGISSTOR_LOCAL
    version = Column(String(32), default="1.0.0", nullable=False)
    connection_status = Column(String(32), default="CONFIGURED", nullable=False)  # CONFIGURED, CONNECTED, DEGRADED, DISCONNECTED, ERROR
    last_health_check_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    credential_ref = Column(String(256), default="", nullable=False)  # Reference only (env://, vault://), never plain-text secret
    metadata_json = Column(Text, default="{}")
    entity_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ConnectorCapability(Base):
    __tablename__ = "connector_capabilities"

    id = Column(String(64), primary_key=True, index=True)
    connector_id = Column(String(64), ForeignKey("connectors.id"), nullable=False, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    action_key = Column(String(64), nullable=False, index=True)
    is_supported = Column(Boolean, default=True, nullable=False)
    dry_run_mode = Column(String(32), default="AEGISSTOR_PREFLIGHT", nullable=False)  # NATIVE_PROVIDER | AEGISSTOR_PREFLIGHT | UNSUPPORTED
    constraints_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)

    __table_args__ = (
        UniqueConstraint("connector_id", "action_key", name="uq_connector_capability"),
    )


class ActionDefinition(Base):
    __tablename__ = "action_definitions"

    id = Column(String(64), primary_key=True, index=True)  # e.g., RESOURCE_INSPECT, CAPACITY_INSPECT, CONNECTOR_HEALTH_CHECK, CONFIG_INSPECT
    name = Column(String(128), nullable=False)
    category = Column(String(48), nullable=False)
    risk_level = Column(String(24), default="LOW", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval = Column(Boolean, default=False, nullable=False)
    is_read_only = Column(Boolean, default=True, nullable=False)
    dry_run_supported = Column(Boolean, default=True, nullable=False)
    input_schema_json = Column(Text, default="{}")
    description = Column(Text, default="")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ActionRequest(Base):
    __tablename__ = "action_requests"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    connector_id = Column(String(64), ForeignKey("connectors.id"), nullable=False, index=True)
    action_definition_id = Column(String(64), ForeignKey("action_definitions.id"), nullable=False, index=True)
    resource_type = Column(String(48), nullable=False)
    resource_id = Column(String(64), nullable=False, index=True)
    resource_version = Column(Integer, nullable=True)
    requester_user_id = Column(String(64), ForeignKey("users.id"), nullable=False, index=True)
    requester_username = Column(String(64), nullable=False)
    requesting_role = Column(String(32), nullable=False)
    operation = Column(String(64), nullable=False, index=True)
    parameters_json = Column(Text, default="{}")
    risk_level = Column(String(24), default="LOW", nullable=False)
    status = Column(String(40), default="DRAFT", nullable=False, index=True)
    approval_required = Column(Boolean, default=False, nullable=False)
    execution_result_json = Column(Text, nullable=True)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    entity_version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class ActionApproval(Base):
    __tablename__ = "action_approvals"

    id = Column(String(64), primary_key=True, index=True)
    action_request_id = Column(String(64), ForeignKey("action_requests.id"), nullable=False, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    decision = Column(String(24), nullable=False)  # APPROVED | REJECTED
    approver_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    approver_username = Column(String(64), nullable=False)
    approver_role = Column(String(32), nullable=False)
    comment = Column(Text, default="")
    decided_at = Column(DateTime, default=utc_now, index=True)


class ActionPreflightResult(Base):
    __tablename__ = "action_preflight_results"

    id = Column(String(64), primary_key=True, index=True)
    action_request_id = Column(String(64), ForeignKey("action_requests.id"), nullable=False, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    overall_status = Column(String(24), nullable=False)  # PASS | WARNING | BLOCKED
    checks_json = Column(Text, nullable=False, default="[]")
    dry_run_mode = Column(String(32), default="AEGISSTOR_PREFLIGHT", nullable=False)
    dry_run_summary_json = Column(Text, default="{}")
    evaluated_by = Column(String(64), nullable=False)
    evaluated_at = Column(DateTime, default=utc_now, index=True)


class ActionExecution(Base):
    __tablename__ = "action_executions"

    id = Column(String(64), primary_key=True, index=True)
    action_request_id = Column(String(64), ForeignKey("action_requests.id"), nullable=False, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    connector_id = Column(String(64), ForeignKey("connectors.id"), nullable=False, index=True)
    status = Column(String(24), default="RUNNING", nullable=False)  # RUNNING | SUCCEEDED | FAILED
    idempotency_key = Column(String(128), unique=True, nullable=False)
    result_summary_json = Column(Text, default="{}")
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)


class ActionExecutionStep(Base):
    __tablename__ = "action_execution_steps"

    id = Column(String(64), primary_key=True, index=True)
    execution_id = Column(String(64), ForeignKey("action_executions.id"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String(128), nullable=False)
    status = Column(String(24), nullable=False)  # PENDING | RUNNING | SUCCEEDED | FAILED
    output_json = Column(Text, default="{}")
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)


class ResourceExecutionLock(Base):
    __tablename__ = "resource_execution_locks"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    resource_type = Column(String(48), nullable=False)
    resource_id = Column(String(64), nullable=False, index=True)
    locked_by_action_id = Column(String(64), ForeignKey("action_requests.id"), nullable=False, index=True)
    lock_reason = Column(String(256), default="Active action execution")
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    acquired_at = Column(DateTime, default=utc_now)
    released_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class ControlPlaneAuditEvent(Base):
    __tablename__ = "control_plane_audit_events"

    id = Column(String(64), primary_key=True, index=True)
    organization_id = Column(String(64), ForeignKey("organisations.id"), nullable=False, index=True)
    action_request_id = Column(String(64), ForeignKey("action_requests.id"), nullable=True, index=True)
    connector_id = Column(String(64), ForeignKey("connectors.id"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(String(64), nullable=False)
    actor_username = Column(String(64), nullable=False)
    actor_role = Column(String(32), nullable=False)
    from_status = Column(String(40), nullable=True)
    to_status = Column(String(40), nullable=True)
    details_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now, index=True)
