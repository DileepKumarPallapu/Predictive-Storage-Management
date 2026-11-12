import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import JurassicScenario, JurassicExperiment, JurassicResilienceReport, Device
from app.services.jurassic.scenario_engine import ScenarioEngine, PRESET_SCENARIOS
from app.services.jurassic.experiment_runner import ExperimentRunner
from app.services.jurassic.fallback_engine import FALLBACK_STATES
from app.utils.datetime_utils import utc_now
from app.auth.permissions import require_method_permission

logger = logging.getLogger("aegisstor.api.jurassic")

router = APIRouter(
    prefix="/jurassic",
    tags=["AEGISSTOR Jurassic Resilience Lab"],
    dependencies=[Depends(require_method_permission("digital_twin.read", "digital_twin.execute"))],
)

# --- Request / Response Pydantic Schemas ---

class CreateScenarioRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    scenario_family: str = Field(default="CAPACITY_DISTURBANCE")
    description: Optional[str] = ""
    target_device_id: str = Field(default="vol-nvme-tier1-db")
    seed: int = Field(default=42)
    simulation_duration_hours: int = Field(default=168, ge=24, le=720)
    initial_capacity_pct: float = Field(default=70.0, ge=10.0, le=95.0)
    capacity_growth_gb_day: float = Field(default=45.0, ge=-500.0, le=2000.0)
    burst_events: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    read_iops_base: float = Field(default=10000.0, ge=100.0)
    write_iops_base: float = Field(default=8000.0, ge=100.0)
    latency_noise_ms: float = Field(default=0.5, ge=0.0, le=50.0)
    telemetry_drop_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    telemetry_delay_s: int = Field(default=0, ge=0, le=86400)
    chaos_faults: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class RunExperimentRequest(BaseModel):
    scenario_id: str
    target_device_id: Optional[str] = None


# --- Endpoints ---

@router.get("/command-center", summary="Resilience Command Center Overview")
def get_command_center(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns experiment counters, recent outcomes, and resilience findings."""
    try:
        return ExperimentRunner.get_command_center_metrics(db)
    except Exception as e:
        logger.error(f"Error fetching command center metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios", summary="List Available Resilience Scenarios")
def list_scenarios(
    family: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Returns preset and user-configured stress-test scenarios."""
    ScenarioEngine.seed_presets_if_missing(db)
    query = db.query(JurassicScenario)
    if family:
        query = query.filter(JurassicScenario.scenario_family == family)
    scenarios = query.order_by(JurassicScenario.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "scenario_family": s.scenario_family,
            "description": s.description,
            "target_device_id": s.target_device_id,
            "seed": s.seed,
            "simulation_duration_hours": s.simulation_duration_hours,
            "initial_capacity_pct": s.initial_capacity_pct,
            "capacity_growth_gb_day": s.capacity_growth_gb_day,
            "burst_events": json.loads(s.burst_events_json) if s.burst_events_json else [],
            "chaos_faults": json.loads(s.chaos_faults_json) if s.chaos_faults_json else [],
            "telemetry_drop_rate": s.telemetry_drop_rate,
            "is_preset": s.is_preset,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_id}", summary="Get Scenario Details")
def get_scenario(scenario_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns single scenario configuration by ID."""
    ScenarioEngine.seed_presets_if_missing(db)
    s = db.query(JurassicScenario).filter(JurassicScenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return {
        "id": s.id,
        "name": s.name,
        "scenario_family": s.scenario_family,
        "description": s.description,
        "target_device_id": s.target_device_id,
        "seed": s.seed,
        "simulation_duration_hours": s.simulation_duration_hours,
        "initial_capacity_pct": s.initial_capacity_pct,
        "capacity_growth_gb_day": s.capacity_growth_gb_day,
        "burst_events": json.loads(s.burst_events_json) if s.burst_events_json else [],
        "chaos_faults": json.loads(s.chaos_faults_json) if s.chaos_faults_json else [],
        "telemetry_drop_rate": s.telemetry_drop_rate,
        "is_preset": s.is_preset,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.post("/scenarios", summary="Create Custom Scenario")
def create_scenario(req: CreateScenarioRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Saves a new user-configured stress-test scenario."""
    import uuid
    sc_id = f"scenario-custom-{uuid.uuid4().hex[:8]}"
    scenario = JurassicScenario(
        id=sc_id,
        name=req.name,
        scenario_family=req.scenario_family,
        description=req.description or "",
        target_device_id=req.target_device_id,
        seed=req.seed,
        simulation_duration_hours=req.simulation_duration_hours,
        initial_capacity_pct=req.initial_capacity_pct,
        capacity_growth_gb_day=req.capacity_growth_gb_day,
        burst_events_json=json.dumps(req.burst_events or []),
        read_iops_base=req.read_iops_base,
        write_iops_base=req.write_iops_base,
        latency_noise_ms=req.latency_noise_ms,
        telemetry_drop_rate=req.telemetry_drop_rate,
        telemetry_delay_s=req.telemetry_delay_s,
        chaos_faults_json=json.dumps(req.chaos_faults or []),
        is_preset=False,
        created_at=utc_now()
    )
    db.add(scenario)
    db.commit()

    return {"id": sc_id, "name": req.name, "status": "CREATED"}


@router.post("/experiments/run", summary="Launch Resilience Experiment")
def run_experiment(req: RunExperimentRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Executes a full resilience experiment run against a scenario."""
    try:
        return ExperimentRunner.execute_resilience_experiment(
            db=db,
            scenario_id=req.scenario_id,
            target_device_id=req.target_device_id
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error running resilience experiment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/experiments", summary="List Completed Resilience Experiments")
def list_experiments(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists past resilience experiments with scores and fallback states."""
    ExperimentRunner.seed_initial_experiments_if_missing(db)
    experiments = (
        db.query(JurassicExperiment)
        .order_by(JurassicExperiment.created_at.desc())
        .limit(limit)
        .all()
    )

    results = []
    for e in experiments:
        sc = db.query(JurassicScenario).filter(JurassicScenario.id == e.scenario_id).first()
        results.append({
            "id": e.id,
            "scenario_id": e.scenario_id,
            "scenario_name": sc.name if sc else e.scenario_id,
            "status": e.status,
            "target_device_id": e.target_device_id,
            "final_fallback_state": e.final_fallback_state,
            "drift_detected": e.drift_detected,
            "resilience_score": e.resilience_score,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return results


@router.get("/experiments/{experiment_id}", summary="Get Experiment Forensic Details")
def get_experiment_details(experiment_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns complete experiment forensic timeline, scorecard, and telemetry."""
    ExperimentRunner.seed_initial_experiments_if_missing(db)
    exp = db.query(JurassicExperiment).filter(JurassicExperiment.id == experiment_id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    sc = db.query(JurassicScenario).filter(JurassicScenario.id == exp.scenario_id).first()

    return {
        "id": exp.id,
        "scenario_id": exp.scenario_id,
        "scenario_name": sc.name if sc else exp.scenario_id,
        "scenario_family": sc.scenario_family if sc else "UNKNOWN",
        "status": exp.status,
        "target_device_id": exp.target_device_id,
        "model_version": exp.model_version,
        "started_at": exp.started_at.isoformat() if exp.started_at else None,
        "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
        "final_fallback_state": exp.final_fallback_state,
        "fallback_transitions": json.loads(exp.fallback_transitions_json) if exp.fallback_transitions_json else [],
        "fault_events": json.loads(exp.fault_events_json) if exp.fault_events_json else [],
        "telemetry_samples": json.loads(exp.telemetry_history_json) if exp.telemetry_history_json else [],
        "forecast_evaluations": json.loads(exp.forecast_evaluations_json) if exp.forecast_evaluations_json else {},
        "drift_detected": exp.drift_detected,
        "drift_details": json.loads(exp.drift_details_json) if exp.drift_details_json else {},
        "resilience_score": exp.resilience_score,
        "resilience_breakdown": json.loads(exp.resilience_breakdown_json) if exp.resilience_breakdown_json else {},
        "forensics": json.loads(exp.forensics_json) if exp.forensics_json else {},
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }


@router.get("/experiments/{experiment_id}/report", summary="Download Resilience Report")
def get_experiment_report(
    experiment_id: str,
    format: str = Query("markdown", pattern="^(markdown|csv)$"),
    db: Session = Depends(get_db)
):
    """Downloads experiment report in Markdown or CSV format."""
    rep = db.query(JurassicResilienceReport).filter(JurassicResilienceReport.experiment_id == experiment_id).first()
    if not rep:
        # Fallback to generating a report if not explicitly stored
        exp = db.query(JurassicExperiment).filter(JurassicExperiment.id == experiment_id).first()
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")
        sc = db.query(JurassicScenario).filter(JurassicScenario.id == exp.scenario_id).first()
        md_text = f"# Resilience Report for Experiment {exp.id}\nScenario: {sc.name if sc else 'Unknown'}\nResilience Score: {exp.resilience_score}"
        csv_text = "step,timestamp,utilization_pct\n0,2026-10-21T00:00:00Z,70.0"
    else:
        md_text = rep.summary_markdown
        csv_text = rep.csv_metrics_data

    if format == "csv":
        return Response(content=csv_text, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=jurassic_report_{experiment_id}.csv"})
    else:
        return Response(content=md_text, media_type="text/markdown", headers={"Content-Disposition": f"attachment; filename=jurassic_report_{experiment_id}.md"})


@router.get("/fallback-states", summary="List Formal Fallback Safe States")
def get_fallback_states() -> Dict[str, Any]:
    """Returns definitions, entry conditions, and prohibited operations for the 5 safe states."""
    return FALLBACK_STATES
