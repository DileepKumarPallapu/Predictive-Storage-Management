"""Add the AEGISSTOR Control Plane Sprint 1 foundation.

Revision ID: 20261112_cp01
Revises: c00e12269790
"""
from alembic import op
import sqlalchemy as sa

revision = "20261112_cp01"
down_revision = "c00e12269790"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "control_plane_connectors",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("credential_ref", sa.String(length=255), nullable=True),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_cp_connector_org_name"),
    )
    op.create_index("ix_control_plane_connectors_organization_id", "control_plane_connectors", ["organization_id"])
    op.create_index("ix_cp_connector_org_status", "control_plane_connectors", ["organization_id", "status"])

    op.create_table(
        "control_plane_action_definitions",
        sa.Column("action_type", sa.String(length=80), primary_key=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("risk_level", sa.String(length=24), nullable=False),
        sa.Column("input_schema_json", sa.JSON(), nullable=False),
        sa.Column("required_capability", sa.String(length=100), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_executable", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    action_definitions = sa.table(
        "control_plane_action_definitions",
        sa.column("action_type", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("risk_level", sa.String),
        sa.column("input_schema_json", sa.JSON),
        sa.column("required_capability", sa.String),
        sa.column("requires_approval", sa.Boolean),
        sa.column("is_enabled", sa.Boolean),
        sa.column("is_executable", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    from datetime import datetime, timezone
    op.bulk_insert(action_definitions, [
        {
            "action_type": "resource.inspect",
            "title": "Inspect registered resource",
            "description": "Read the AEGISSTOR inventory record and its latest persisted telemetry. Does not connect to or change physical infrastructure.",
            "category": "READ_ONLY",
            "risk_level": "READ_ONLY",
            "input_schema_json": {"target_id": "string"},
            "required_capability": None,
            "requires_approval": False,
            "is_enabled": True,
            "is_executable": True,
            "created_at": datetime.now(timezone.utc),
        },
        {
            "action_type": "storage.capacity.plan",
            "title": "Prepare capacity expansion plan",
            "description": "Calculate a proposed capacity plan from fresh, non-synthetic persisted telemetry. Approval records acceptance of the plan only; no volume is provisioned or resized.",
            "category": "PLANNING",
            "risk_level": "HIGH",
            "input_schema_json": {"additional_capacity_bytes": "positive integer"},
            "required_capability": None,
            "requires_approval": True,
            "is_enabled": True,
            "is_executable": False,
            "created_at": datetime.now(timezone.utc),
        },
        {
            "action_type": "storage.volume.resize",
            "title": "Resize storage volume",
            "description": "Reserved action definition. Disabled until a provider-specific resize adapter, capability verification, safety tests and production policy are implemented.",
            "category": "MUTATION",
            "risk_level": "CRITICAL",
            "input_schema_json": {"new_capacity_bytes": "positive integer"},
            "required_capability": "volume.resize",
            "requires_approval": True,
            "is_enabled": False,
            "is_executable": False,
            "created_at": datetime.now(timezone.utc),
        },
    ])

    op.create_table(
        "control_plane_action_requests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("action_type", sa.String(length=80), sa.ForeignKey("control_plane_action_definitions.action_type"), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("connector_id", sa.String(length=64), sa.ForeignKey("control_plane_connectors.id"), nullable=True),
        sa.Column("parameters_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("requested_by_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requested_by_role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("risk_level", sa.String(length=24), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("preflight_json", sa.JSON(), nullable=False),
        sa.Column("dry_run_json", sa.JSON(), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("approved_by_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_rationale", sa.Text(), nullable=True),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_cp_action_org_idempotency"),
    )
    op.create_index("ix_control_plane_action_requests_organization_id", "control_plane_action_requests", ["organization_id"])
    op.create_index("ix_cp_action_org_status", "control_plane_action_requests", ["organization_id", "status"])
    op.create_index("ix_cp_action_target", "control_plane_action_requests", ["target_type", "target_id"])

    op.create_table(
        "control_plane_action_approvals",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("action_request_id", sa.String(length=64), sa.ForeignKey("control_plane_action_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("action_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cp_approval_action_created", "control_plane_action_approvals", ["action_request_id", "created_at"])

    op.create_table(
        "control_plane_action_executions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("action_request_id", sa.String(length=64), sa.ForeignKey("control_plane_action_requests.id"), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=False),
        sa.Column("verification_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_control_plane_action_executions_action_request_id", "control_plane_action_executions", ["action_request_id"])

    op.create_table(
        "control_plane_resource_locks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("action_request_id", sa.String(length=64), sa.ForeignKey("control_plane_action_requests.id"), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "resource_type", "resource_id", name="uq_cp_resource_lock"),
    )
    op.create_index("ix_control_plane_resource_locks_organization_id", "control_plane_resource_locks", ["organization_id"])

    op.create_table(
        "control_plane_audit_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=48), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_control_plane_audit_events_organization_id", "control_plane_audit_events", ["organization_id"])
    op.create_index("ix_cp_audit_org_created", "control_plane_audit_events", ["organization_id", "created_at"])

    op.create_table(
        "control_plane_outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=48), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("entity_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("actor_user_id", sa.String(length=64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_role", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_control_plane_outbox_events_organization_id", "control_plane_outbox_events", ["organization_id"])
    op.create_index("ix_cp_outbox_org_id", "control_plane_outbox_events", ["organization_id", "id"])

    op.create_table(
        "control_plane_realtime_tickets",
        sa.Column("ticket_hash", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_control_plane_realtime_tickets_user_id", "control_plane_realtime_tickets", ["user_id"])
    op.create_index("ix_control_plane_realtime_tickets_organization_id", "control_plane_realtime_tickets", ["organization_id"])
    op.create_index("ix_control_plane_realtime_tickets_expires_at", "control_plane_realtime_tickets", ["expires_at"])


def downgrade() -> None:
    op.drop_table("control_plane_realtime_tickets")
    op.drop_table("control_plane_outbox_events")
    op.drop_table("control_plane_audit_events")
    op.drop_table("control_plane_resource_locks")
    op.drop_table("control_plane_action_executions")
    op.drop_table("control_plane_action_approvals")
    op.drop_table("control_plane_action_requests")
    op.drop_table("control_plane_action_definitions")
    op.drop_table("control_plane_connectors")
