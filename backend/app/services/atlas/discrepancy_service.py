"""
AEGISSTOR ATLAS — Sim-to-Real Discrepancy Detection & Analysis Service
Quantifies gaps between simulated predictions and actual storage observations across workload regimes.
"""
from typing import Dict, Any, List, Optional
import math
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.entities import AtlasDiscrepancyRecord, AtlasCalibrationRun, Device


class DiscrepancyAnalysisService:
    """
    Computes residual profiles, regime breakdowns, and systematic bias across held-out evaluations.
    """

    @classmethod
    def analyze_run_discrepancy(cls, db: Session, run_id: str) -> Dict[str, Any]:
        run = db.query(AtlasCalibrationRun).filter(AtlasCalibrationRun.id == run_id).first()
        if not run:
            raise ValueError(f"Calibration run {run_id} not found.")

        records = (
            db.query(AtlasDiscrepancyRecord)
            .filter(AtlasDiscrepancyRecord.run_id == run_id)
            .order_by(AtlasDiscrepancyRecord.evaluation_timestamp.asc())
            .all()
        )

        if not records:
            return {
                "run_id": run_id,
                "discrepancy_count": 0,
                "timeline": [],
                "regime_breakdown": {},
                "systematic_bias": 0.0,
                "time_dependent_drift": "INSUFFICIENT_DATA"
            }

        residuals = [r.residual for r in records]
        obs_vals = [r.observed_value for r in records]
        sim_vals = [r.simulated_value for r in records]
        timestamps = [r.evaluation_timestamp.isoformat() for r in records]

        # 1. Systematic Bias Analysis
        mean_bias = sum(residuals) / len(residuals)
        bias_direction = (
            "UNDER_PREDICTING" if mean_bias > 0.5
            else "OVER_PREDICTING" if mean_bias < -0.5
            else "UNBIASED_NOMINAL"
        )

        # 2. Workload Regime Breakdown
        by_regime: Dict[str, List[AtlasDiscrepancyRecord]] = {}
        for r in records:
            by_regime.setdefault(r.workload_regime, []).append(r)

        regime_breakdown = {}
        for reg, recs in by_regime.items():
            reg_residuals = [x.residual for x in recs]
            reg_mae = sum(abs(x) for x in reg_residuals) / len(reg_residuals)
            reg_rmse = math.sqrt(sum(x * x for x in reg_residuals) / len(reg_residuals))
            regime_breakdown[reg] = {
                "sample_count": len(recs),
                "mae": round(reg_mae, 3),
                "rmse": round(reg_rmse, 3),
                "mean_bias": round(sum(reg_residuals) / len(reg_residuals), 3),
                "outlier_count": sum(1 for x in recs if x.is_outlier)
            }

        # 3. Time-Dependent Horizon Drift (early horizon vs late horizon error)
        n = len(records)
        early_records = records[: n // 3] if n >= 6 else records
        late_records = records[- (n // 3):] if n >= 6 else records

        early_mae = sum(abs(r.residual) for r in early_records) / max(len(early_records), 1)
        late_mae = sum(abs(r.residual) for r in late_records) / max(len(late_records), 1)

        drift_ratio = late_mae / (early_mae + 1e-4)
        if drift_ratio > 1.5:
            drift_status = "SIGNIFICANT_HORIZON_EXPANSION"
        elif drift_ratio > 1.15:
            drift_status = "MODERATE_HORIZON_DRIFT"
        else:
            drift_status = "STABLE_ACROSS_HORIZON"

        # 4. Synchronized Timeline Payload for Obsidian UI Charts
        timeline = []
        for r in records:
            timeline.append({
                "timestamp": r.evaluation_timestamp.isoformat(),
                "observed": r.observed_value,
                "simulated": r.simulated_value,
                "residual": r.residual,
                "relative_error": r.relative_error,
                "workload_regime": r.workload_regime,
                "is_outlier": r.is_outlier
            })

        return {
            "run_id": run_id,
            "metric_name": records[0].metric_name,
            "discrepancy_count": len(records),
            "systematic_bias": round(mean_bias, 3),
            "bias_direction": bias_direction,
            "overall_mae": round(sum(abs(x) for x in residuals) / len(residuals), 3),
            "overall_rmse": round(math.sqrt(sum(x * x for x in residuals) / len(residuals)), 3),
            "time_dependent_drift": drift_status,
            "drift_expansion_ratio": round(drift_ratio, 2),
            "regime_breakdown": regime_breakdown,
            "timeline": timeline
        }
