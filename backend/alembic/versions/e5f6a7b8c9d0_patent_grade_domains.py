"""patent_grade_domains

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-11 22:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(insp, tbl: str) -> bool:
    return tbl in insp.get_table_names()


def _has_col(insp, tbl: str, col: str) -> bool:
    return _has_table(insp, tbl) and col in [c["name"] for c in insp.get_columns(tbl)]


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if _has_table(insp, "ingestion_jobs") and not _has_col(insp, "ingestion_jobs", "idempotency_key"):
        op.add_column("ingestion_jobs", sa.Column("idempotency_key", sa.String(length=128), nullable=True))

    if _has_table(insp, "model_metrics"):
        for col, ctype in [
            ("mase", sa.Float()),
            ("pinball_loss", sa.Float()),
            ("interval_coverage", sa.Float()),
            ("mean_interval_width", sa.Float()),
            ("vs_baseline_status", sa.String(length=32)),
        ]:
            if not _has_col(insp, "model_metrics", col):
                op.add_column("model_metrics", sa.Column(col, ctype, nullable=True))

    if not _has_table(insp, "api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("key_prefix", sa.String(length=16), nullable=False),
            sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
            sa.Column("role", sa.String(length=32), nullable=True),
            sa.Column("organization_id", sa.String(length=64), nullable=True),
            sa.Column("created_by", sa.String(length=64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(insp, "telemetry_connectors"):
        op.create_table(
            "telemetry_connectors",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("connector_type", sa.String(length=32), nullable=False),
            sa.Column("endpoint_url", sa.String(length=512), nullable=True),
            sa.Column("config_json", sa.Text(), nullable=True),
            sa.Column("target_storage_id", sa.String(length=64), nullable=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=True),
            sa.Column("last_status", sa.String(length=32), nullable=True),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("last_sync_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(insp, "data_reliability_profiles"):
        op.create_table(
            "data_reliability_profiles",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("storage_id", sa.String(length=64), nullable=False),
            sa.Column("reliability_score", sa.Float(), nullable=False),
            sa.Column("reliability_tier", sa.String(length=16), nullable=False),
            sa.Column("is_stale", sa.Boolean(), nullable=True),
            sa.Column("last_successful_timestamp", sa.DateTime(), nullable=True),
            sa.Column("completeness_score", sa.Float(), nullable=True),
            sa.Column("freshness_score", sa.Float(), nullable=True),
            sa.Column("continuity_score", sa.Float(), nullable=True),
            sa.Column("duplicate_rate_score", sa.Float(), nullable=True),
            sa.Column("invalid_rate_score", sa.Float(), nullable=True),
            sa.Column("capacity_consistency_score", sa.Float(), nullable=True),
            sa.Column("missing_metric_score", sa.Float(), nullable=True),
            sa.Column("source_availability_score", sa.Float(), nullable=True),
            sa.Column("historical_stability_score", sa.Float(), nullable=True),
            sa.Column("weights_json", sa.Text(), nullable=True),
            sa.Column("explanation_json", sa.Text(), nullable=True),
            sa.Column("uncertainty_multiplier", sa.Float(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(insp, "workload_regime_events"):
        op.create_table(
            "workload_regime_events",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("storage_id", sa.String(length=64), nullable=False),
            sa.Column("regime_label", sa.String(length=48), nullable=False),
            sa.Column("event_type", sa.String(length=48), nullable=False),
            sa.Column("severity", sa.String(length=16), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("supporting_metrics_json", sa.Text(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("detected_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(insp, "background_jobs"):
        op.create_table(
            "background_jobs",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("job_type", sa.String(length=48), nullable=False),
            sa.Column("storage_id", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=True),
            sa.Column("result_json", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("triggered_by", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    if not _has_table(insp, "capacity_risk_evaluations"):
        op.create_table(
            "capacity_risk_evaluations",
            sa.Column("id", sa.String(length=64), primary_key=True),
            sa.Column("storage_id", sa.String(length=64), nullable=False),
            sa.Column("forecast_id", sa.Integer(), nullable=True),
            sa.Column("horizon_days", sa.Integer(), nullable=True),
            sa.Column("current_utilization_pct", sa.Float(), nullable=False),
            sa.Column("forecasted_utilization_pct", sa.Float(), nullable=False),
            sa.Column("remaining_safe_capacity_bytes", sa.BigInteger(), nullable=False),
            sa.Column("safety_threshold_crossing_date", sa.DateTime(), nullable=True),
            sa.Column("exhaustion_date", sa.DateTime(), nullable=True),
            sa.Column("threshold_crossing_probability", sa.Float(), nullable=False),
            sa.Column("expected_shortfall_bytes", sa.BigInteger(), nullable=True),
            sa.Column("adverse_p90_utilization_pct", sa.Float(), nullable=False),
            sa.Column("data_reliability_score", sa.Float(), nullable=True),
            sa.Column("details_json", sa.Text(), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    pass
