"""complete rbac sessions password reset assignments

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-11 23:15:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
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

    _add_column_if_missing("users", "failed_login_attempts", sa.Integer(), "0")
    _add_column_if_missing("users", "locked_until", sa.DateTime(), None)
    _add_column_if_missing("users", "last_login_at", sa.DateTime(), None)
    _add_column_if_missing("users", "password_changed_at", sa.DateTime(), None)
    _add_column_if_missing("users", "created_at", sa.DateTime(), None)

    _add_column_if_missing("audit_logs", "user_id", sa.String(64), None)
    _add_column_if_missing("audit_logs", "user_role", sa.String(32), None)
    _add_column_if_missing("audit_logs", "outcome", sa.String(32), "SUCCESS")

    if "roles" not in existing:
        op.create_table(
            "roles",
            sa.Column("name", sa.String(32), primary_key=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_system", sa.Boolean(), default=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "permissions" not in existing:
        op.create_table(
            "permissions",
            sa.Column("key", sa.String(64), primary_key=True),
            sa.Column("module", sa.String(48), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
        )
    if "role_permissions" not in existing:
        op.create_table(
            "role_permissions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("role_name", sa.String(32), sa.ForeignKey("roles.name"), nullable=False),
            sa.Column("permission_key", sa.String(64), sa.ForeignKey("permissions.key"), nullable=False),
            sa.Column("is_allowed", sa.Boolean(), default=True),
        )
    if "user_sessions" not in existing:
        op.create_table(
            "user_sessions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("session_token_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("csrf_token_hash", sa.String(128), nullable=True),
            sa.Column("role_at_issue", sa.String(32), nullable=False),
            sa.Column("client_ip", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(256), nullable=True),
            sa.Column("is_revoked", sa.Boolean(), default=False),
            sa.Column("revoked_reason", sa.String(128), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "password_reset_tokens" not in existing:
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("token_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
    if "login_attempts" not in existing:
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("identifier", sa.String(128), nullable=False),
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("success", sa.Boolean(), default=False),
            sa.Column("failure_reason", sa.String(128), nullable=True),
            sa.Column("client_ip", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(256), nullable=True),
            sa.Column("attempted_at", sa.DateTime(), nullable=True),
        )
    if "operational_assignments" not in existing:
        op.create_table(
            "operational_assignments",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("target_type", sa.String(32), nullable=False),
            sa.Column("target_id", sa.String(64), nullable=False),
            sa.Column("assigned_to_user_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("assigned_by", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), default="ASSIGNED"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    pass
