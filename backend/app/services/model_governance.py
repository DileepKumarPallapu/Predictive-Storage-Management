import logging
import uuid
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.entities import GovernancePromotionGate, ModelVersion
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("aegisstor.model_governance")

DEFAULT_GATES = [
    {
        "id": "gate-eval-20261019-01",
        "candidate_model_name": "LightGBM-Asymmetric-Quantile-v2.1",
        "baseline_model_name": "LightGBM-Conformal-Quantile-v1.8",
        "candidate_version": "2.1.0",
        "candidate_mae": 2.58,
        "baseline_mae": 2.64,
        "candidate_decision_loss": 310.0,
        "baseline_decision_loss": 320.0,
        "candidate_calibration_error": 0.024,
        "baseline_calibration_error": 0.028,
        "hard_safety_check_passed": True,
        "gate_verdict": "PROMOTED",
        "verdict_rationale": "Candidate achieved 0.06% lower MAE and reduced operational decision loss by $10.0 with 0.024 ECE. Passed all safety tests.",
        "evaluated_at": utc_now(),
        "evaluated_by": "aegisstor_automated_governor",
    },
    {
        "id": "gate-eval-20261014-02",
        "candidate_model_name": "DeepAR-PointEstimator-v3.0",
        "baseline_model_name": "LightGBM-Conformal-Quantile-v1.8",
        "candidate_version": "3.0.0-rc1",
        "candidate_mae": 2.12,  # Substantially lower MAE!
        "baseline_mae": 2.64,
        "candidate_decision_loss": 1850.0,  # Catastrophic decision loss due to underpredicting 2 tail bursts!
        "baseline_decision_loss": 320.0,
        "candidate_calibration_error": 0.089,
        "hard_safety_check_passed": False,
        "gate_verdict": "REJECTED",
        "verdict_rationale": (
            "REJECTED by AEGISSTOR Omega Governance Gate. While candidate boasts 19.7% lower MAE (2.12% vs 2.64%), "
            "it underpredicts sudden write bursts, increasing decision loss by +$1,530 and failing the Hard Safety Envelope."
        ),
        "evaluated_at": utc_now(),
        "evaluated_by": "aegisstor_automated_governor",
    },
]

class ModelGovernanceService:
    """
    Model Governance & Promotion Gate Service for AEGISSTOR Omega (Hypothesis H4).
    Enforces decision-loss and safety gating before any candidate forecasting model
    can be promoted to active production serving.
    """

    @classmethod
    def seed_governance_if_missing(cls, db: Session):
        """Idempotently seeds historical promotion gate decisions."""
        for g in DEFAULT_GATES:
            if not db.query(GovernancePromotionGate).filter(GovernancePromotionGate.id == g["id"]).first():
                db.add(GovernancePromotionGate(**g))
        db.commit()

    @classmethod
    def get_promotion_history(cls, db: Session) -> Dict[str, Any]:
        """Returns historical model promotion evaluations and safety gate decisions."""
        cls.seed_governance_if_missing(db)

        gates = (
            db.query(GovernancePromotionGate)
            .order_by(GovernancePromotionGate.evaluated_at.desc())
            .all()
        )

        results = []
        for g in gates:
            results.append({
                "id": g.id,
                "candidate_model_name": g.candidate_model_name,
                "baseline_model_name": g.baseline_model_name,
                "candidate_version": g.candidate_version,
                "candidate_mae": g.candidate_mae,
                "baseline_mae": g.baseline_mae,
                "candidate_decision_loss": g.candidate_decision_loss,
                "baseline_decision_loss": g.baseline_decision_loss,
                "candidate_calibration_error": g.candidate_calibration_error,
                "baseline_calibration_error": g.baseline_calibration_error,
                "hard_safety_check_passed": g.hard_safety_check_passed,
                "gate_verdict": g.gate_verdict,
                "verdict_rationale": g.verdict_rationale,
                "evaluated_at": g.evaluated_at.isoformat() if g.evaluated_at else None,
                "evaluated_by": g.evaluated_by,
            })

        return {
            "summary": {
                "total_evaluations": len(gates),
                "promoted_count": sum(1 for g in gates if g.gate_verdict == "PROMOTED"),
                "rejected_count": sum(1 for g in gates if g.gate_verdict == "REJECTED"),
                "canary_count": sum(1 for g in gates if g.gate_verdict == "CANARY_TRIAL"),
            },
            "evaluations": results,
        }

    @classmethod
    def evaluate_candidate_promotion(
        cls,
        db: Session,
        candidate_model_name: str,
        candidate_version: str,
        candidate_mae: float,
        candidate_decision_loss: float,
        candidate_calibration_error: float,
        baseline_model_name: str = "LightGBM-Conformal-Quantile-v1.8",
        baseline_mae: float = 2.64,
        baseline_decision_loss: float = 320.0,
        baseline_calibration_error: float = 0.028,
        evaluated_by: str = "operator@aegisstor.internal"
    ) -> Dict[str, Any]:
        """
        Evaluates candidate model promotion request and registers gate decision in database.
        """
        # Hard Safety Envelope Rules:
        # 1. Candidate Decision Loss must not exceed baseline by more than 5%
        # 2. Calibration error (ECE) must be <= 0.05
        hard_safety_passed = True
        violations = []

        if candidate_decision_loss > baseline_decision_loss * 1.05:
            hard_safety_passed = False
            violations.append(
                f"DECISION LOSS REGRESSION: Candidate loss ${candidate_decision_loss} exceeds baseline ${baseline_decision_loss}."
            )

        if candidate_calibration_error > 0.05:
            hard_safety_passed = False
            violations.append(
                f"CALIBRATION UNCERTAINTY EXCEEDED: ECE {candidate_calibration_error} exceeds 0.05 threshold."
            )

        if hard_safety_passed and candidate_decision_loss <= baseline_decision_loss:
            verdict = "PROMOTED"
            rationale = (
                f"Candidate successfully satisfies all criteria. Decision loss is ${candidate_decision_loss} "
                f"(vs baseline ${baseline_decision_loss}) with calibration error {candidate_calibration_error}."
            )
        elif hard_safety_passed:
            verdict = "CANARY_TRIAL"
            rationale = "Candidate passed safety envelope but marginal decision loss requires 7-day canary validation."
        else:
            verdict = "REJECTED"
            rationale = f"Promotion REJECTED: {'; '.join(violations)}"

        gate_record = GovernancePromotionGate(
            id=f"gate-eval-{uuid.uuid4().hex[:8]}",
            candidate_model_name=candidate_model_name,
            baseline_model_name=baseline_model_name,
            candidate_version=candidate_version,
            candidate_mae=candidate_mae,
            baseline_mae=baseline_mae,
            candidate_decision_loss=candidate_decision_loss,
            baseline_decision_loss=baseline_decision_loss,
            candidate_calibration_error=candidate_calibration_error,
            baseline_calibration_error=baseline_calibration_error,
            hard_safety_check_passed=hard_safety_passed,
            gate_verdict=verdict,
            verdict_rationale=rationale,
            evaluated_at=utc_now(),
            evaluated_by=evaluated_by
        )
        db.add(gate_record)
        db.commit()

        return {
            "id": gate_record.id,
            "gate_verdict": verdict,
            "hard_safety_check_passed": hard_safety_passed,
            "verdict_rationale": rationale,
            "comparison": {
                "candidate_mae": candidate_mae,
                "baseline_mae": baseline_mae,
                "candidate_decision_loss": candidate_decision_loss,
                "baseline_decision_loss": baseline_decision_loss,
                "candidate_calibration_error": candidate_calibration_error,
                "baseline_calibration_error": baseline_calibration_error,
            }
        }
