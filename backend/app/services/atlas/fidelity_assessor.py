"""
AEGISSTOR ATLAS — Digital Twin Fidelity Envelope Engine
Evaluates multi-dimensional simulator fidelity, tracks condition coverage, and identifies out-of-scope boundaries.
"""
from typing import Dict, Any, List, Optional
import math
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.entities import (
    Device, Telemetry, AtlasCalibrationRun, AtlasCalibrationConfig,
    AtlasFidelityAssessment, AtlasActionEffectEvidence
)
from app.utils.datetime_utils import utc_now


class FidelityAssessor:
    """
    Computes transparent, multi-indicator fidelity assessments without opaque black-box scoring.
    """

    @classmethod
    def evaluate_device_fidelity(cls, db: Session, device_id: str) -> AtlasFidelityAssessment:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found.")

        # 1. Fetch latest completed calibration run
        latest_run = (
            db.query(AtlasCalibrationRun)
            .join(AtlasCalibrationConfig, AtlasCalibrationRun.config_id == AtlasCalibrationConfig.id)
            .filter(AtlasCalibrationConfig.device_id == device_id)
            .order_by(AtlasCalibrationRun.started_at.desc())
            .first()
        )

        # 2. Fetch latest telemetry reading to check current operating conditions
        latest_telemetry = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )

        warnings: List[str] = []
        assessed_status = "UNKNOWN"

        if not latest_run or latest_run.calibration_status == "INSUFFICIENT_EVIDENCE":
            # Insufficient evidence
            assessment = AtlasFidelityAssessment(
                id=f"fid-{device_id[:12]}-{uuid.uuid4().hex[:6]}",
                device_id=device_id,
                simulator_version="DigitalTwin-v4.0",
                assessment_status="UNKNOWN",
                prediction_fidelity_score=0.0,
                workload_coverage_score=0.0,
                data_quality_score=50.0,
                calibration_recency_score=0.0,
                action_effect_evidence_score=0.0,
                overall_fidelity_score=0.0,
                evaluated_conditions_json=json.dumps({"error": "No calibration run completed for target device"}),
                out_of_scope_warnings_json=json.dumps(["Simulator has not been calibrated against real storage telemetry."]),
                evaluated_at=utc_now()
            )
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            return assessment

        # Indicator A: Prediction Fidelity (based on held-out RMSE)
        # RMSE <= 1.0% -> 98, RMSE == 3.0% -> 85, RMSE == 8.0% -> 50, RMSE >= 15.0% -> 20
        rmse = latest_run.evaluation_rmse
        pred_fidelity = max(10.0, min(99.0, 100.0 - (rmse * 4.5)))

        # Indicator B: Data Quality
        data_quality = 92.0 if latest_telemetry and not latest_telemetry.is_synthetic else 84.0

        # Indicator C: Calibration Recency (exponential decay over 30 days)
        now = utc_now()
        run_time = latest_run.completed_at or latest_run.started_at or now
        if run_time.tzinfo is None:
            run_time = run_time.replace(tzinfo=timezone.utc)
        days_ago = max(0.0, (now - run_time).total_seconds() / 86400.0)
        recency = max(30.0, 100.0 * math.exp(-0.03 * days_ago))

        # Indicator D: Action-Effect Empirical Evidence
        evidence_records = (
            db.query(AtlasActionEffectEvidence)
            .filter(AtlasActionEffectEvidence.target_device_id == device_id)
            .all()
        )
        if evidence_records:
            verified_count = sum(1 for e in evidence_records if e.is_causally_verified)
            action_evidence = max(40.0, min(95.0, (verified_count / len(evidence_records)) * 100.0))
        else:
            action_evidence = 60.0

        # Indicator E: Workload Coverage & Scope Validation
        workload_coverage = 82.0
        scope_data = json.loads(latest_run.condition_scope_json) if latest_run.condition_scope_json else {}
        util_range = scope_data.get("validated_capacity_utilization_range", [30.0, 90.0])
        max_qd_scope = scope_data.get("validated_queue_depth_max", 8.0)

        curr_util = latest_telemetry.utilization_pct if latest_telemetry else 75.0
        curr_qd = latest_telemetry.queue_depth if latest_telemetry else 1.5

        if curr_util > util_range[1]:
            warnings.append(
                f"Current utilization ({curr_util:.1f}%) exceeds calibrated envelope ceiling ({util_range[1]}%). Simulator predictions may underestimate controller garbage collection overhead."
            )
            workload_coverage -= 18.0

        if curr_qd > max_qd_scope:
            warnings.append(
                f"Current queue depth ({curr_qd:.1f}) exceeds calibrated envelope max ({max_qd_scope:.1f}). Queueing delays may be non-linear."
            )
            workload_coverage -= 15.0

        # Composite score
        overall = (
            (pred_fidelity * 0.35) +
            (workload_coverage * 0.25) +
            (data_quality * 0.15) +
            (recency * 0.15) +
            (action_evidence * 0.10)
        )

        # Categorical Assignment
        if warnings:
            assessed_status = "LIMITED_SCOPE"
        elif overall >= 85.0:
            assessed_status = "HIGH_FIDELITY"
        elif overall >= 70.0:
            assessed_status = "MODERATE_FIDELITY"
        else:
            assessed_status = "DEGRADED"

        evaluated_conditions = {
            "device_id": device_id,
            "tier": device.tier,
            "current_utilization_pct": curr_util,
            "current_queue_depth": curr_qd,
            "held_out_rmse": round(rmse, 3),
            "held_out_mae": round(latest_run.evaluation_mae, 3),
            "calibration_status": latest_run.calibration_status,
            "calibration_age_days": round(days_ago, 1)
        }

        assessment = AtlasFidelityAssessment(
            id=f"fid-{device_id[:12]}-{uuid.uuid4().hex[:6]}",
            device_id=device_id,
            simulator_version=latest_run.simulator_version,
            assessment_status=assessed_status,
            prediction_fidelity_score=round(pred_fidelity, 1),
            workload_coverage_score=round(workload_coverage, 1),
            data_quality_score=round(data_quality, 1),
            calibration_recency_score=round(recency, 1),
            action_effect_evidence_score=round(action_evidence, 1),
            overall_fidelity_score=round(overall, 1),
            evaluated_conditions_json=json.dumps(evaluated_conditions),
            out_of_scope_warnings_json=json.dumps(warnings),
            evaluated_at=utc_now()
        )
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        return assessment
