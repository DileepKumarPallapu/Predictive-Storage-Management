import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import OutcomeLedgerRecord, Device
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("aegisstor.outcome_ledger")

DEFAULT_LEDGER_ENTRIES = [
    {
        "id": "ledger-rec-20261015-01",
        "timestamp": utc_now() - timedelta(days=6),
        "device_id": "vol-nvme-tier1-db",
        "evaluation_window_hours": 24,
        "forecasted_used_pct": 91.2,
        "simulated_used_pct": 82.5,
        "observed_used_pct": 81.9,
        "forecast_error_mae": 0.6,
        "action_taken": "TIER_MIGRATION_OFFLOAD",
        "counterfactual_outcome_class": "CORRECT_PREVENTIVE_SUCCESS",
        "runway_hours_gained": 72.0,
        "decision_cost_usd": 120.0,
        "net_decision_loss": 0.0,
        "metadata_json": json.dumps({"migrated_gb": 1200, "target": "vol-sas-tier2-analytics", "operator": "auto_governor"}),
    },
    {
        "id": "ledger-rec-20261016-02",
        "timestamp": utc_now() - timedelta(days=5),
        "device_id": "vol-sas-tier2-analytics",
        "evaluation_window_hours": 24,
        "forecasted_used_pct": 86.4,
        "simulated_used_pct": 74.0,
        "observed_used_pct": 72.8,
        "forecast_error_mae": 1.2,
        "action_taken": "COMPACTION_PURGE",
        "counterfactual_outcome_class": "CORRECT_PREVENTIVE_SUCCESS",
        "runway_hours_gained": 120.0,
        "decision_cost_usd": 45.0,
        "net_decision_loss": 0.0,
        "metadata_json": json.dumps({"purged_snapshots": 8, "bytes_reclaimed_gb": 420}),
    },
    {
        "id": "ledger-rec-20261017-03",
        "timestamp": utc_now() - timedelta(days=4),
        "device_id": "vol-hdd-archive",
        "evaluation_window_hours": 48,
        "forecasted_used_pct": 93.5,
        "simulated_used_pct": 88.0,
        "observed_used_pct": 85.1,
        "forecast_error_mae": 2.9,
        "action_taken": "COLD_TIER_EXPANSION",
        "counterfactual_outcome_class": "UNNECESSARY_INTERVENTION",
        "runway_hours_gained": 240.0,
        "decision_cost_usd": 320.0,
        "net_decision_loss": 320.0,
        "metadata_json": json.dumps({"counterfactual_check": "End-of-month batch was cancelled by tenant; capacity would have stayed at 85.1%"}),
    },
    {
        "id": "ledger-rec-20261018-04",
        "timestamp": utc_now() - timedelta(days=3),
        "device_id": "vol-backup-target",
        "evaluation_window_hours": 24,
        "forecasted_used_pct": 68.0,
        "simulated_used_pct": 68.0,
        "observed_used_pct": 67.5,
        "forecast_error_mae": 0.5,
        "action_taken": "NO_ACTION",
        "counterfactual_outcome_class": "CORRECT_PREVENTIVE_SUCCESS",
        "runway_hours_gained": 0.0,
        "decision_cost_usd": 0.0,
        "net_decision_loss": 0.0,
        "metadata_json": json.dumps({"decision": "Monitoring maintained; capacity safely nominal"}),
    },
    {
        "id": "ledger-rec-20261019-05",
        "timestamp": utc_now() - timedelta(days=2),
        "device_id": "vol-nvme-tier1-db",
        "evaluation_window_hours": 24,
        "forecasted_used_pct": 89.8,
        "simulated_used_pct": 81.0,
        "observed_used_pct": 80.4,
        "forecast_error_mae": 0.6,
        "action_taken": "DYNAMIC_QOS_THROTTLE",
        "counterfactual_outcome_class": "CORRECT_PREVENTIVE_SUCCESS",
        "runway_hours_gained": 48.0,
        "decision_cost_usd": 15.0,
        "net_decision_loss": 0.0,
        "metadata_json": json.dumps({"rate_limited_tenant": "analytics_bulk_export"}),
    },
    {
        "id": "ledger-rec-20261020-06",
        "timestamp": utc_now() - timedelta(days=1),
        "device_id": "vol-sas-tier2-analytics",
        "evaluation_window_hours": 24,
        "forecasted_used_pct": 78.5,
        "simulated_used_pct": 78.5,
        "observed_used_pct": 79.1,
        "forecast_error_mae": 0.6,
        "action_taken": "NO_ACTION",
        "counterfactual_outcome_class": "CORRECT_PREVENTIVE_SUCCESS",
        "runway_hours_gained": 0.0,
        "decision_cost_usd": 0.0,
        "net_decision_loss": 0.0,
        "metadata_json": json.dumps({"status": "Stable within runway envelope"}),
    },
]

class OutcomeLedgerService:
    """
    Closed-Loop Counterfactual Outcome Ledger Service for AEGISSTOR Omega.
    Maintains immutable records of predicted vs simulated vs observed outcomes.
    """

    @classmethod
    def seed_ledger_if_missing(cls, db: Session):
        """Idempotently populates initial realistic outcome ledger records."""
        for rec in DEFAULT_LEDGER_ENTRIES:
            if not db.query(OutcomeLedgerRecord).filter(OutcomeLedgerRecord.id == rec["id"]).first():
                db.add(OutcomeLedgerRecord(**rec))
        db.commit()

    @classmethod
    def get_ledger_records(cls, db: Session, limit: int = 50) -> Dict[str, Any]:
        """Fetches ledger records and calculates closed-loop audit statistics."""
        cls.seed_ledger_if_missing(db)

        records = (
            db.query(OutcomeLedgerRecord)
            .order_by(OutcomeLedgerRecord.timestamp.desc())
            .limit(limit)
            .all()
        )

        total_count = len(records)
        class_counts = {
            "CORRECT_PREVENTIVE_SUCCESS": 0,
            "UNNECESSARY_INTERVENTION": 0,
            "MISSED_BREACH": 0,
            "INEFFECTIVE_INTERVENTION": 0,
        }
        total_decision_loss = 0.0
        total_runway_gained = 0.0

        items = []
        for r in records:
            cat = r.counterfactual_outcome_class
            class_counts[cat] = class_counts.get(cat, 0) + 1
            total_decision_loss += (r.net_decision_loss or 0.0)
            total_runway_gained += (r.runway_hours_gained or 0.0)

            items.append({
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "device_id": r.device_id,
                "evaluation_window_hours": r.evaluation_window_hours,
                "forecasted_used_pct": r.forecasted_used_pct,
                "simulated_used_pct": r.simulated_used_pct,
                "observed_used_pct": r.observed_used_pct,
                "forecast_error_mae": r.forecast_error_mae,
                "action_taken": r.action_taken,
                "counterfactual_outcome_class": r.counterfactual_outcome_class,
                "runway_hours_gained": r.runway_hours_gained,
                "decision_cost_usd": r.decision_cost_usd,
                "net_decision_loss": r.net_decision_loss,
                "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
            })

        # Precision & Reliability
        success_count = class_counts["CORRECT_PREVENTIVE_SUCCESS"]
        unnecessary_count = class_counts["UNNECESSARY_INTERVENTION"]
        missed_count = class_counts["MISSED_BREACH"]

        precision = round((success_count / max(1, success_count + unnecessary_count)) * 100.0, 1)
        action_reliability_rate = round(
            (success_count / max(1, success_count + unnecessary_count + missed_count)) * 100.0, 1
        )

        return {
            "statistics": {
                "total_ledger_events": total_count,
                "correct_preventive_success": success_count,
                "unnecessary_interventions": unnecessary_count,
                "missed_breaches": missed_count,
                "ineffective_interventions": class_counts["INEFFECTIVE_INTERVENTION"],
                "intervention_precision_pct": precision,
                "action_reliability_rate_pct": action_reliability_rate,
                "total_runway_hours_protected": round(total_runway_gained, 1),
                "total_net_decision_loss_usd": round(total_decision_loss, 2),
            },
            "records": items,
        }
