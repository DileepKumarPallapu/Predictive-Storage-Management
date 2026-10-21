from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.evidence_gated_planner import EvidenceGatedPlanner
from app.services.research_benchmark_engine import ResearchBenchmarkEngine

router = APIRouter(prefix="/research", tags=["Research Contribution & Benchmarks (Prompt 17.0)"])

@router.post("/planner/plan")
def execute_evidence_gated_planner(
    device_id: str = Query("vol-nvme-tier1-db", description="Target storage volume"),
    horizon_hours: int = Query(72, description="Forward forecast horizon in hours"),
    ablation_flags: Optional[Dict[str, bool]] = Body(default=None),
    db: Session = Depends(get_db)
):
    """
    Executes the Evidence-Gated, Multi-Resource Storage Intervention Planner.
    Jointly evaluates forecast uncertainty, simulator discrepancy, multi-resource propagation,
    and lead-time feasibility before producing an action recommendation or graceful fallback.
    """
    try:
        return EvidenceGatedPlanner.plan_interventions(
            db, device_id=device_id, horizon_hours=horizon_hours, ablation_flags=ablation_flags
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Planning execution error: {str(e)}")

@router.get("/benchmarks/baselines")
def get_baseline_comparison(
    device_id: str = Query("vol-nvme-tier1-db", description="Target storage volume"),
    horizon_hours: int = Query(72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """
    Executes a head-to-head comparison across Baselines A through F:
    A: Fixed threshold monitoring
    B: Persistence model
    C: ML point forecast (q50) + threshold
    D: Quantile forecasting with conformal bounds (q90)
    E: Ungated Digital Twin planner
    F: Proposed Evidence-Gated Multi-Resource Planner
    """
    try:
        return ResearchBenchmarkEngine.run_all_baselines(db, device_id=device_id, horizon_hours=horizon_hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/benchmarks/ablations")
def get_ablation_study_results(
    device_id: str = Query("vol-nvme-tier1-db", description="Target storage volume"),
    horizon_hours: int = Query(72, description="Forecast horizon in hours"),
    db: Session = Depends(get_db)
):
    """
    Evaluates which architectural components of the proposed mechanism contribute value:
    Ablations 1 to 7 removing forecast uncertainty, simulator fidelity, action uncertainty,
    resource propagation, lead-time checks, evidence gate, and workload shifts.
    """
    try:
        return ResearchBenchmarkEngine.run_ablation_study(db, device_id=device_id, horizon_hours=horizon_hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
