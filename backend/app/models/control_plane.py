"""Persistent models for the AEGISSTOR Control Plane foundation.

This module contains operational records only. It deliberately does not seed
resources, credentials, telemetry, or executable infrastructure adapters.
"""
from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String,
    Text, UniqueConstraint
)
from app.database import Base
from app.utils.datetime_utils import utc_now


class ConnectorRegistry(Base):
    __tablename__ = "control_plane_connectors"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_cp_connector_org_name"),
        Index("ix_cp_connector_org_status", "organization_id", "status"),
    )

    id = Column(String(64), primary_key=True)
    organization_id = Column(String(64), nullable=False, index=True)
    provider = Column(String(40), nullable=False)
    name = Column(String(120), nullable=False)
    version = Column(String(40), nullable=True)
    status = Column(String(32), nullable=False, default="NOT_CONFIGURED")
    configuration_json = Column(JSON, nullable=False, default=dict)
    capabilities_json = Column(JSON, nullable=False, default=list)
    credential_ref = Column(String(255), nullable=True)
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_by = Column(String(64), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ActionDefinition(Base):
    __tablename__ = "control_plane_action_definitions"

    action_type = Column(String(80), primary_key=True)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    category = Column(String(40), nullable=False)
    risk_level = Column(String(24), nullable=False)
    input_schema_json = Column(JSON, nullable=False, default=dict)
    required_capability = Column(String(100), nullable=True)
    requires_approval = Column(Boolean, nullable=False, default=False)
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_executable = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ActionRequest(Base):
    __tablename__ = "control_plane_action_requests"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_cp_action_org_idempotency"),
        Index("ix_cp_action_org_status", "organization_id", "status"),
        Index("ix_cp_action_target", "target_type", "target_id"),
    )

    id = Column(String(64), primary_key=True)
    organization_id = Column(String(64), nullable=False, index=True)
    action_type = Column(String(80), ForeignKey("control_plane_action_definitions.action_type"), nullable=False)
    target_type = Column(String(32), nullable=False)
    target_id = Column(String(64), nullable=False)
    connector_id = Column(String(64), ForeignKey("control_plane_connectors.id"), nullable=True)
    parameters_json = Column(JSON, nullable=False, default=dict)
    idempotency_key = Column(String(128), nullable=False)
    requested_by_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    requested_by_role = Column(String(32), nullable=False)
    status = Column(String(40), nullable=False, default="DRAFT")
    risk_level = Column(String(24), nullable=False)
    approval_required = Column(Boolean, nullable=False, default=False)
    preflight_json = Column(JSON, nullable=False, default=dict)
    dry_run_json = Column(JSON, nullable=False, default=dict)
    output_json = Column(JSON, nullable=False, default=dict)
    error_code = Column(String(80), nullable=True)
    error_message = Column(Text, nullable=True)
    approved_by_id = Column(String(64), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approval_rationale = Column(Text, nullable=True)
    entity_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class ActionApproval(Base):
    __tablename__ = "control_plane_action_approvals"
    __table_args__ = (
        Index("ix_cp_approval_action_created", "action_request_id", "created_at"),
    )

    id = Column(String(64), primary_key=True)
    action_request_id = Column(String(64), ForeignKey("control_plane_action_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    decision = Column(String(16), nullable=False)
    rationale = Column(Text, nullable=False)
    action_version = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ActionExecution(Base):
    __tablename__ = "control_plane_action_executions"

    id = Column(String(64), primary_key=True)
    action_request_id = Column(String(64), ForeignKey("control_plane_action_requests.id"), nullable=False, index=True)
    execution_mode = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False)
    result_json = Column(JSON, nullable=False, default=dict)
    verification_json = Column(JSON, nullable=False, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ResourceExecutionLock(Base):
    __tablename__ = "control_plane_resource_locks"
    __table_args__ = (
        UniqueConstraint("organization_id", "resource_type", "resource_id", name="uq_cp_resource_lock"),
    )

    id = Column(String(64), primary_key=True)
    organization_id = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(32), nullable=False)
    resource_id = Column(String(64), nullable=False)
    action_request_id = Column(String(64), ForeignKey("control_plane_action_requests.id"), nullable=False)
    acquired_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)


class ControlPlaneAuditEvent(Base):
    __tablename__ = "control_plane_audit_events"
    __table_args__ = (
        Index("ix_cp_audit_org_created", "organization_id", "created_at"),
    )

    id = Column(String(64), primary_key=True)
    organization_id = Column(String(64), nullable=False, index=True)
    actor_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(32), nullable=False)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(48), nullable=False)
    entity_id = Column(String(64), nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class ControlPlaneOutboxEvent(Base):
    __tablename__ = "control_plane_outbox_events"
    __table_args__ = (
        Index("ix_cp_outbox_org_id", "organization_id", "id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), nullable=False, unique=True)
    organization_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(48), nullable=False)
    entity_id = Column(String(64), nullable=False)
    entity_version = Column(Integer, nullable=False, default=1)
    actor_user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    actor_role = Column(String(32), nullable=False)
    payload_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)


class RealtimeTicket(Base):
    __tablename__ = "control_plane_realtime_tickets"

    ticket_hash = Column(String(64), primary_key=True)
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String(64), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
