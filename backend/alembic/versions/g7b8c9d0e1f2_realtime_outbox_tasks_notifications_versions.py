"""realtime outbox tasks notifications versions

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-11-12 14:25:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "g7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _add_column_if_missing(table_name: str, col_name: str, col_type: sa.types.TypeEngine, default=None):
    bind = op.get_bind()
    insp = inspect(bind)
    if table_name not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns(table_name)}
    if col_name not in cols:
        op.add_column(table_name, sa.Column(col_name, col_type, nullable=True, server_default=default))


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing = set(insp.get_table_names())

    _add_column_if_missing("devices", "version", sa.Integer(), "1")
    _add_column_if_missing("devices", "created_by", sa.String(64), "system")
    _add_column_if_missing("devices", "updated_by", sa.String(64), "system")

    _add_column_if_missing("scenarios", "version", sa.Integer(), "1")
    _add_column_if_missing("scenarios", "updated_at", sa.DateTime(), None)
    _add_column_if_missing("scenarios", "updated_by", sa.String(64), "system_operator")

    _add_column_if_missing("application_settings", "version", sa.Integer(), "1")

    _add_column_if_missing("background_jobs", "stage", sa.String(32), "QUEUED")
    _add_column_if_missing("background_jobs", "progress_pct", sa.Integer(), "0")
    _add_column_if_missing("background_jobs", "updated_at", sa.DateTime(), None)

    if "outbox_events" not in existing:
        op.create_table(
            "outbox_events",
            sa.Column("seq_id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("id", sa.String(64), nullable=False, unique=True),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("event_version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("organization_id", sa.String(64), nullable=False, server_default="org-primary-enterprise"),
            sa.Column("actor_user_id", sa.String(64), nullable=True),
            sa.Column("actor_username", sa.String(64), nullable=True),
            sa.Column("actor_role", sa.String(32), nullable=True),
            sa.Column("resource_type", sa.String(48), nullable=False),
            sa.Column("resource_id", sa.String(64), nullable=False),
            sa.Column("entity_version", sa.Integer(), nullable=True),
            sa.Column("changed_fields_json", sa.Text(), server_default="[]"),
            sa.Column("payload_json", sa.Text(), server_default="{}"),
            sa.Column("required_permission", sa.String(64), nullable=True),
            sa.Column("target_user_id", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("published_at", sa.DateTime(), nullable=True),
            sa.Column("delivery_error", sa.Text(), nullable=True),
        )

    if "user_notifications" not in existing:
        op.create_table(
            "user_notifications",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("event_id", sa.String(64), nullable=True),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("resource_type", sa.String(48), nullable=False),
            sa.Column("resource_id", sa.String(64), nullable=False),
            sa.Column("severity", sa.String(24), server_default="INFO"),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "operational_tasks" not in existing:
        op.create_table(
            "operational_tasks",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("organization_id", sa.String(64), nullable=False, server_default="org-primary-enterprise"),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("priority", sa.String(24), server_default="MEDIUM"),
            sa.Column("status", sa.String(32), server_default="ASSIGNED"),
            sa.Column("assigned_to_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_by_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("linked_device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=True),
            sa.Column("linked_alert_id", sa.String(64), nullable=True),
            sa.Column("due_date", sa.DateTime(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_by", sa.String(64), server_default="system"),
            sa.Column("updated_by", sa.String(64), server_default="system"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    if "task_comments" not in existing:
        op.create_table(
            "task_comments",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("task_id", sa.String(64), sa.ForeignKey("operational_tasks.id"), nullable=False),
            sa.Column("author_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("author_username", sa.String(64), nullable=False),
            sa.Column("author_role", sa.String(32), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "user_presence" not in existing:
        op.create_table(
            "user_presence",
            sa.Column("session_id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("username", sa.String(64), nullable=False),
            sa.Column("role", sa.String(32), nullable=False),
            sa.Column("current_route", sa.String(128), server_default="/"),
            sa.Column("is_online", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("connected_at", sa.DateTime(), nullable=True),
            sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
            sa.Column("disconnected_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("user_presence")
    op.drop_table("task_comments")
    op.drop_table("operational_tasks")
    op.drop_table("user_notifications")
    op.drop_table("outbox_events")
