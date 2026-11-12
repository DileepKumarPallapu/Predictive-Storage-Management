import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.fleet_topology_service import FleetTopologyService
from app.services.fleet_risk_engine import FleetRiskEngine
from app.services.decision_evaluator import DecisionEvaluator
from app.services.adaptive_monitor import AdaptiveMonitorService
from app.services.fleet_planner import FleetPlannerService
from app.services.outcome_ledger import OutcomeLedgerService
from app.services.model_governance import ModelGovernanceService
from app.auth.permissions import require_method_permission

logger = logging.getLogger("aegisstor.api.omega")

router = APIRouter(
    prefix="/omega",
    tags=["AEGISSTOR Omega Intelligence"],
    dependencies=[Depends(require_method_permission("risk.read", "optimisation.execute"))],
)

# --- Request / Response Pydantic Schemas ---

class FleetRebalanceRequest(BaseModel):
    source_device_id: str = Field(default="vol-nvme-tier1-db")
    destination_device_id: str = Field(default="vol-sas-tier2-analytics")
    migration_size_gb: float = Field(default=1200.0, ge=1.0, le=50000.0)
    bandwidth_cap_mb_s: float = Field(default=350.0, ge=10.0, le=5000.0)

class CandidatePromotionRequest(BaseModel):
    candidate_model_name: str
    candidate_version: str
    candidate_mae: float = Field(..., ge=0.0)
    candidate_decision_loss: float = Field(..., ge=0.0)
    candidate_calibration_error: float = Field(..., ge=0.0, le=1.0)
    baseline_model_name: Optional[str] = "LightGBM-Conformal-Quantile-v1.8"
    baseline_mae: Optional[float] = 2.64
    baseline_decision_loss: Optional[float] = 320.0
    baseline_calibration_error: Optional[float] = 0.028


# --- Endpoints ---

@router.get("/topology", summary="Retrieve Fleet Resource Topology Graph")
def get_fleet_topology(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns storage systems, storage pools, devices, provenance edges, and workload dependencies."""
    try:
        return FleetTopologyService.get_fleet_topology(db)
    except Exception as e:
        logger.error(f"Error fetching fleet topology: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fleet-risk", summary="Fleet-Wide Risk Aggregator & Correlated Bottlenecks")
def get_fleet_risk(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Calculates multi-pool risk posture, shared interconnect bottlenecks, and fleet risk budget."""
    try:
        return FleetRiskEngine.evaluate_fleet_risk(db)
    except Exception as e:
        logger.error(f"Error evaluating fleet risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decision-evaluation", summary="Hypothesis H1: Decision-Aware Forecasting Benchmark")
def get_decision_evaluation(
    device_id: str = Query("vol-nvme-tier1-db", description="Target storage volume ID"),
    horizon_hours: int = Query(72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Evaluates whether prediction errors change operational decisions vs pure symmetric MAE."""
    try:
        return DecisionEvaluator.evaluate_decision_loss_benchmark(
            db, device_id=device_id, horizon_hours=horizon_hours
        )
    except Exception as e:
        logger.error(f"Error evaluating decision loss benchmark: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/adaptive-monitoring", summary="Hypothesis H2: Adaptive Monitoring Policy Simulation")
def get_adaptive_monitoring(
    simulation_days: int = Query(30, description="Simulation window in days"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Simulates Policy A (Fixed), Policy B (Threshold-Triggered), and Policy C (VoI Adaptive Attention)."""
    try:
        sim = AdaptiveMonitorService.evaluate_monitoring_policies(db, simulation_days=simulation_days)
        live_allocations = AdaptiveMonitorService.get_live_device_attention_allocations(db)
        return {
            **sim,
            "live_device_attention_allocations": live_allocations
        }
    except Exception as e:
        logger.error(f"Error evaluating adaptive monitoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fleet-plan", summary="Hypothesis H3: Global Fleet Intervention & Safety Envelope Simulation")
def simulate_fleet_rebalance(
    req: FleetRebalanceRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Evaluates cross-device rebalancing, enforcing Dual-Sided Hard Safety Envelopes on source & destination."""
    try:
        return FleetPlannerService.evaluate_fleet_rebalance(
            db=db,
            source_device_id=req.source_device_id,
            destination_device_id=req.destination_device_id,
            migration_size_gb=req.migration_size_gb,
            bandwidth_cap_mb_s=req.bandwidth_cap_mb_s
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error simulating fleet rebalance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/outcome-ledger", summary="Hypothesis H4: Closed-Loop Counterfactual Outcome Ledger")
def get_outcome_ledger(
    limit: int = Query(50, description="Maximum ledger records to return"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves immutable records of predicted vs simulated vs observed outcomes and precision metrics."""
    try:
        return OutcomeLedgerService.get_ledger_records(db, limit=limit)
    except Exception as e:
        logger.error(f"Error fetching outcome ledger: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/governance", summary="Hypothesis H4: Model Governance Promotion Gate History")
def get_model_governance(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns candidate model evaluations and safety gate decisions."""
    try:
        return ModelGovernanceService.get_promotion_history(db)
    except Exception as e:
        logger.error(f"Error fetching model governance history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/governance/evaluate", summary="Hypothesis H4: Evaluate Candidate Model Promotion")
def evaluate_candidate_model(
    req: CandidatePromotionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Gated safety check comparing candidate model vs baseline on MAE, decision loss, and calibration error."""
    try:
        return ModelGovernanceService.evaluate_candidate_promotion(
            db=db,
            candidate_model_name=req.candidate_model_name,
            candidate_version=req.candidate_version,
            candidate_mae=req.candidate_mae,
            candidate_decision_loss=req.candidate_decision_loss,
            candidate_calibration_error=req.candidate_calibration_error,
            baseline_model_name=req.baseline_model_name or "LightGBM-Conformal-Quantile-v1.8",
            baseline_mae=req.baseline_mae or 2.64,
            baseline_decision_loss=req.baseline_decision_loss or 320.0,
            baseline_calibration_error=req.baseline_calibration_error or 0.028
        )
    except Exception as e:
        logger.error(f"Error evaluating candidate model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
