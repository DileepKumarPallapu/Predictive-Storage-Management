"""enterprise_modules_v2

Revision ID: d4e5f6a7b8c9
Revises: c00e12269790
Create Date: 2026-11-11 21:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c00e12269790'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_col(inspector, table_name: str, col_name: str) -> bool:
    if not _has_table(inspector, table_name):
        return False
    return col_name in [c["name"] for c in inspector.get_columns(table_name)]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    # 1. Extend devices table
    if _has_table(inspector, "devices"):
        for col, col_type in [
            ("storage_type", sa.String(length=64)),
            ("environment_location", sa.String(length=128)),
            ("description", sa.Text()),
            ("notes", sa.Text()),
            ("last_telemetry_at", sa.DateTime()),
        ]:
            if not _has_col(inspector, "devices", col):
                op.add_column("devices", sa.Column(col, col_type, nullable=True))

    # 2. Extend telemetry table
    if _has_table(inspector, "telemetry"):
        for col, col_type in [
            ("total_capacity_bytes", sa.BigInteger()),
            ("read_latency_ms", sa.Float()),
            ("write_latency_ms", sa.Float()),
        ]:
            if not _has_col(inspector, "telemetry", col):
                op.add_column("telemetry", sa.Column(col, col_type, nullable=True))

    # 3. Extend forecasts table
    if _has_table(inspector, "forecasts"):
        for col, col_type in [
            ("model_version_id", sa.String(length=64)),
            ("horizon_days", sa.Integer()),
            ("daily_predictions_json", sa.Text()),
            ("projected_capacity_breach", sa.Boolean()),
            ("breach_timestamp", sa.DateTime()),
        ]:
            if not _has_col(inspector, "forecasts", col):
                op.add_column("forecasts", sa.Column(col, col_type, nullable=True))

    # 4. Extend alerts table
    if _has_table(inspector, "alerts"):
        for col, col_type in [
            ("acknowledged_by", sa.String(length=64)),
            ("acknowledged_at", sa.DateTime()),
            ("resolution_details", sa.Text()),
            ("supporting_evidence_json", sa.Text()),
        ]:
            if not _has_col(inspector, "alerts", col):
                op.add_column("alerts", sa.Column(col, col_type, nullable=True))

    # 5. Extend model_versions table
    if _has_table(inspector, "model_versions"):
        for col, col_type in [
            ("storage_id", sa.String(length=64)),
            ("feature_version", sa.String(length=32)),
            ("artifact_path", sa.String(length=512)),
            ("validation_samples", sa.Integer()),
            ("train_start_at", sa.DateTime()),
            ("train_end_at", sa.DateTime()),
            ("status", sa.String(length=32)),
            ("error_message", sa.Text()),
            ("trained_by", sa.String(length=64)),
        ]:
            if not _has_col(inspector, "model_versions", col):
                op.add_column("model_versions", sa.Column(col, col_type, nullable=True))

    # 6. Create new tables idempotently
    if not _has_table(inspector, "revoked_tokens"):
        op.create_table(
            "revoked_tokens",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("token_hash", sa.String(length=128), nullable=False, unique=True),
            sa.Column("user_id", sa.String(length=64), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "ingestion_jobs"):
        op.create_table(
            "ingestion_jobs",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("storage_id", sa.String(length=64), nullable=True),
            sa.Column("source_type", sa.String(length=32), nullable=False),
            sa.Column("filename", sa.String(length=255), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=True),
            sa.Column("total_rows", sa.Integer(), nullable=True),
            sa.Column("accepted_rows", sa.Integer(), nullable=True),
            sa.Column("rejected_rows", sa.Integer(), nullable=True),
            sa.Column("duplicate_rows", sa.Integer(), nullable=True),
            sa.Column("errors_json", sa.Text(), nullable=True),
            sa.Column("uploaded_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "data_quality_results"):
        op.create_table(
            "data_quality_results",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("storage_id", sa.String(length=64), nullable=False),
            sa.Column("ingestion_job_id", sa.String(length=64), nullable=True),
            sa.Column("total_records_received", sa.Integer(), nullable=True),
            sa.Column("valid_records", sa.Integer(), nullable=True),
            sa.Column("rejected_records", sa.Integer(), nullable=True),
            sa.Column("duplicate_records", sa.Integer(), nullable=True),
            sa.Column("missing_field_stats_json", sa.Text(), nullable=True),
            sa.Column("outlier_count", sa.Integer(), nullable=True),
            sa.Column("data_completeness_pct", sa.Float(), nullable=True),
            sa.Column("latest_telemetry_timestamp", sa.DateTime(), nullable=True),
            sa.Column("preprocessing_decisions_json", sa.Text(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "model_metrics"):
        op.create_table(
            "model_metrics",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("model_version_id", sa.String(length=64), nullable=False),
            sa.Column("storage_id", sa.String(length=64), nullable=False),
            sa.Column("mae", sa.Float(), nullable=False),
            sa.Column("rmse", sa.Float(), nullable=False),
            sa.Column("r2_score", sa.Float(), nullable=True),
            sa.Column("mape", sa.Float(), nullable=True),
            sa.Column("residual_std", sa.Float(), nullable=True),
            sa.Column("is_selected", sa.Boolean(), nullable=True),
            sa.Column("selection_reason", sa.Text(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "report_history"):
        op.create_table(
            "report_history",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("report_type", sa.String(length=64), nullable=False),
            sa.Column("format", sa.String(length=16), nullable=False),
            sa.Column("storage_id", sa.String(length=64), nullable=True),
            sa.Column("filters_json", sa.Text(), nullable=True),
            sa.Column("generated_by", sa.String(length=64), nullable=True),
            sa.Column("row_count", sa.Integer(), nullable=True),
            sa.Column("summary_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(inspector, "application_settings"):
        op.create_table(
            "application_settings",
            sa.Column("key", sa.String(length=64), primary_key=True),
            sa.Column("value_json", sa.Text(), nullable=False),
            sa.Column("category", sa.String(length=32), nullable=True),
            sa.Column("updated_by", sa.String(length=64), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    pass
