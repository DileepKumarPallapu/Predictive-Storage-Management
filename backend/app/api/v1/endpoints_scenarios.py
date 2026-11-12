import csv
import io
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, Scenario, SimulatedOutcome, User
from app.schemas.payloads import ScenarioCreate, ScenarioSimulationResponse
from app.simulator.digital_twin import DigitalTwinSimulator
from app.services.decision_optimizer import DecisionOptimizer
from app.ml.models import run_forecast
from app.services.audit_service import AuditService
from app.auth.security import require_role
from app.auth.permissions import require_permission

router = APIRouter()

def _run_digital_twin(db: Session, device_id: str, action_type: str, parameters: dict, name: str, seed: int = 42):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target device not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )
    if not records:
        raise HTTPException(status_code=400, detail="No telemetry available to run simulation")

    latest = records[-1]
    telemetry_dicts = [
        {
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "used_bytes": r.used_bytes,
            "free_bytes": r.free_bytes,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "throughput_mb_s": r.throughput_mb_s,
            "latency_p95_ms": r.latency_p95_ms,
            "queue_depth": r.queue_depth,
            "is_synthetic": r.is_synthetic
        }
        for r in records
    ]

    base_forecast = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    device_meta = {
        "id": device.id,
        "tier": device.tier,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms,
        "current_throughput_mb_s": latest.throughput_mb_s
    }

    try:
        sim_result = DigitalTwinSimulator.simulate_scenario(
            device_id=device_id,
            device_metadata=device_meta,
            base_forecast=base_forecast,
            action_type=action_type,
            parameters=parameters,
            seed=seed
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Persist in DB
    scenario_id = sim_result["scenario_id"]
    scenario = Scenario(
        id=scenario_id,
        device_id=device_id,
        name=name,
        action_type=action_type,
        parameters_json=json.dumps(parameters),
        created_at=datetime.now(timezone.utc),
        created_by="system_operator"
    )
    db.add(scenario)

    outcome = SimulatedOutcome(
        id=f"out-{scenario_id}",
        scenario_id=scenario_id,
        duration_minutes=sim_result["duration_minutes"],
        estimated_cost_usd=sim_result["estimated_cost_usd"],
        overhead_io_penalty_pct=sim_result["overhead_io_penalty_pct"],
        safety_envelope_passed=sim_result["safety_envelope_passed"],
        violation_reasons_json=json.dumps(sim_result["violation_reasons"]),
        residual_risk_score=sim_result["residual_risk_score"],
        trajectory_json=json.dumps(sim_result["counterfactual_q50"]),
        assumptions_json=json.dumps(sim_result["assumptions"])
    )
    db.add(outcome)
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="scenario.created",
        resource_type="scenario",
        resource_id=scenario_id,
        actor_username="system_operator",
        actor_role="OPERATOR",
        entity_version=1,
        payload={
            "scenario_id": scenario_id,
            "device_id": device_id,
            "name": name,
            "action_type": action_type,
            "safety_envelope_passed": sim_result["safety_envelope_passed"],
        },
        required_permission="digital_twin.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="CREATE_SCENARIO",
        target_type="SCENARIO",
        target_id=scenario_id,
        details={"name": name, "action_type": action_type, "safety_passed": sim_result["safety_envelope_passed"]}
    )

    return sim_result

@router.post("/scenarios", response_model=ScenarioSimulationResponse)
def create_and_run_scenario(
    payload: ScenarioCreate,
    current_user: User = Depends(require_permission("digital_twin.execute")),
    db: Session = Depends(get_db),
):
    """Creates a new scenario definition and executes the Digital Twin simulation."""
    sim_result = _run_digital_twin(
        db=db,
        device_id=payload.device_id,
        action_type=payload.action_type,
        parameters=payload.parameters,
        name=payload.name
    )

    return ScenarioSimulationResponse(
        scenario_id=sim_result["scenario_id"],
        device_id=payload.device_id,
        name=payload.name,
        action_type=payload.action_type,
        parameters=payload.parameters,
        duration_minutes=sim_result["duration_minutes"],
        estimated_cost_usd=sim_result["estimated_cost_usd"],
        overhead_io_penalty_pct=sim_result["overhead_io_penalty_pct"],
        safety_envelope_passed=sim_result["safety_envelope_passed"],
        violation_reasons=sim_result["violation_reasons"],
        residual_risk_score=sim_result["residual_risk_score"],
        assumptions=sim_result["assumptions"],
        timeline_timestamps=sim_result["timeline_timestamps"],
        baseline_q50=sim_result["baseline_q50"],
        counterfactual_q50=sim_result["counterfactual_q50"],
        hard_limit=sim_result["hard_capacity_limit_bytes"],
        is_simulated_estimate=True
    )

@router.get("/scenarios")
def list_scenarios(
    device_id: Optional[str] = None,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    """Retrieves all saved counterfactual scenarios and their historical run parameters."""
    query = db.query(Scenario)
    if device_id:
        query = query.filter(Scenario.device_id == device_id)
    scenarios = query.order_by(Scenario.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": s.id,
            "device_id": s.device_id,
            "name": s.name,
            "action_type": s.action_type,
            "parameters": json.loads(s.parameters_json),
            "created_at": s.created_at,
            "created_by": s.created_by
        }
        for s in scenarios
    ]

@router.get("/scenarios/{scenario_id}")
def get_scenario_definition(
    scenario_id: str,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    """Retrieves a specific scenario definition by ID."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return {
        "id": scenario.id,
        "device_id": scenario.device_id,
        "name": scenario.name,
        "action_type": scenario.action_type,
        "parameters": json.loads(scenario.parameters_json),
        "created_at": scenario.created_at,
        "created_by": scenario.created_by
    }

@router.post("/scenarios/{scenario_id}/run", response_model=ScenarioSimulationResponse)
def rerun_scenario(
    scenario_id: str,
    seed: int = 42,
    current_user: User = Depends(require_permission("digital_twin.execute")),
    db: Session = Depends(get_db),
):
    """Re-executes an existing scenario deterministically with a configurable seed."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    sim_result = _run_digital_twin(
        db=db,
        device_id=scenario.device_id,
        action_type=scenario.action_type,
        parameters=json.loads(scenario.parameters_json),
        name=f"Replay: {scenario.name}",
        seed=seed
    )

    return ScenarioSimulationResponse(
        scenario_id=sim_result["scenario_id"],
        device_id=scenario.device_id,
        name=scenario.name,
        action_type=scenario.action_type,
        parameters=json.loads(scenario.parameters_json),
        duration_minutes=sim_result["duration_minutes"],
        estimated_cost_usd=sim_result["estimated_cost_usd"],
        overhead_io_penalty_pct=sim_result["overhead_io_penalty_pct"],
        safety_envelope_passed=sim_result["safety_envelope_passed"],
        violation_reasons=sim_result["violation_reasons"],
        residual_risk_score=sim_result["residual_risk_score"],
        assumptions=sim_result["assumptions"],
        timeline_timestamps=sim_result["timeline_timestamps"],
        baseline_q50=sim_result["baseline_q50"],
        counterfactual_q50=sim_result["counterfactual_q50"],
        hard_limit=sim_result["hard_capacity_limit_bytes"],
        is_simulated_estimate=True
    )

@router.get("/scenarios/{scenario_id}/results")
def get_scenario_results(
    scenario_id: str,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    """Retrieves the latest simulation outcome recorded for a scenario."""
    outcome = db.query(SimulatedOutcome).filter(SimulatedOutcome.scenario_id == scenario_id).first()
    if not outcome:
        raise HTTPException(status_code=404, detail="No simulation outcome found for this scenario")
    
    return {
        "scenario_id": outcome.scenario_id,
        "duration_minutes": outcome.duration_minutes,
        "estimated_cost_usd": outcome.estimated_cost_usd,
        "overhead_io_penalty_pct": outcome.overhead_io_penalty_pct,
        "safety_envelope_passed": outcome.safety_envelope_passed,
        "violation_reasons": json.loads(outcome.violation_reasons_json),
        "residual_risk_score": outcome.residual_risk_score,
        "trajectory": json.loads(outcome.trajectory_json),
        "assumptions": json.loads(outcome.assumptions_json)
    }


# ------------------------------------------------------------------------------
# MODULE 9 — DIGITAL TWIN SCENARIO LIFECYCLE (/digital-twin)
# ------------------------------------------------------------------------------

class ScenarioUpdateRequest(BaseModel):
    name: Optional[str] = None
    action_type: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ScenarioCompareRequest(BaseModel):
    scenario_ids: List[str]


@router.post("/digital-twin/scenarios", tags=["Digital Twin & Simulator"], status_code=201)
def create_digital_twin_scenario(
    payload: ScenarioCreate,
    current_user: User = Depends(require_permission("digital_twin.create")),
    db: Session = Depends(get_db)
):
    """Simulates and saves a Digital Twin scenario with baseline vs counterfactual state & runway analysis."""
    sim_result = _run_digital_twin(
        db=db,
        device_id=payload.device_id,
        action_type=payload.action_type,
        parameters=payload.parameters,
        name=payload.name,
    )
    return {
        "scenario_id": sim_result["scenario_id"],
        "device_id": payload.device_id,
        "name": payload.name,
        "action_type": sim_result["action_type"],
        "parameters": payload.parameters,
        "baseline_state": sim_result["baseline_state"],
        "predicted_outcome": sim_result["predicted_outcome"],
        "safety_envelope_passed": sim_result["safety_envelope_passed"],
        "violation_reasons": sim_result["violation_reasons"],
        "residual_risk_score": sim_result["residual_risk_score"],
        "estimated_cost_usd": sim_result["estimated_cost_usd"],
        "overhead_io_penalty_pct": sim_result["overhead_io_penalty_pct"],
        "duration_hours": sim_result["duration_hours"],
        "assumptions": sim_result["assumptions"],
        "calculation_methodology": sim_result["calculation_methodology"],
        "simulation_notice": sim_result["simulation_notice"],
        "is_simulated_estimate": True,
    }


@router.get("/digital-twin/scenarios", tags=["Digital Twin & Simulator"])
def list_digital_twin_scenarios(
    device_id: Optional[str] = None,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    return list_scenarios(device_id=device_id, current_user=current_user, db=db)


@router.get("/digital-twin/scenarios/{scenario_id}", tags=["Digital Twin & Simulator"])
def get_digital_twin_scenario(
    scenario_id: str,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    s = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    outcome = db.query(SimulatedOutcome).filter(SimulatedOutcome.scenario_id == scenario_id).first()
    return {
        "id": s.id,
        "device_id": s.device_id,
        "name": s.name,
        "action_type": s.action_type,
        "parameters": json.loads(s.parameters_json),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "created_by": s.created_by,
        "simulation_notice": "Simulation only: no real storage systems were modified.",
        "outcome": {
            "duration_minutes": outcome.duration_minutes,
            "estimated_cost_usd": outcome.estimated_cost_usd,
            "overhead_io_penalty_pct": outcome.overhead_io_penalty_pct,
            "safety_envelope_passed": outcome.safety_envelope_passed,
            "violation_reasons": json.loads(outcome.violation_reasons_json),
            "residual_risk_score": outcome.residual_risk_score,
            "assumptions": json.loads(outcome.assumptions_json),
            "trajectory": json.loads(outcome.trajectory_json),
        } if outcome else None,
    }


@router.put("/digital-twin/scenarios/{scenario_id}", tags=["Digital Twin & Simulator"])
def update_and_rerun_digital_twin_scenario(
    scenario_id: str,
    payload: ScenarioUpdateRequest,
    current_user: User = Depends(require_permission("digital_twin.update")),
    db: Session = Depends(get_db)
):
    """Edits scenario assumptions/parameters, re-executes the Digital Twin simulation, and updates persisted results."""
    s = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")

    new_name = payload.name or s.name
    new_action = payload.action_type or s.action_type
    new_params = payload.parameters if payload.parameters is not None else json.loads(s.parameters_json)

    device = db.query(Device).filter(Device.id == s.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target device not found")

    records = db.query(Telemetry).filter(Telemetry.device_id == s.device_id).order_by(Telemetry.timestamp.asc()).all()
    if not records:
        raise HTTPException(status_code=400, detail="No telemetry available to run simulation")
    latest = records[-1]
    telemetry_dicts = [
        {
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "used_bytes": r.used_bytes,
            "free_bytes": r.free_bytes,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "throughput_mb_s": r.throughput_mb_s,
            "latency_p95_ms": r.latency_p95_ms,
            "queue_depth": r.queue_depth,
            "is_synthetic": r.is_synthetic
        }
        for r in records
    ]
    base_forecast = run_forecast(telemetry_dicts, "used_bytes", "lightgbm_quantile", 72, float(device.total_capacity_bytes))
    device_meta = {
        "id": device.id,
        "tier": device.tier,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms,
        "current_throughput_mb_s": latest.throughput_mb_s
    }

    try:
        sim_result = DigitalTwinSimulator.simulate_scenario(
            device_id=s.device_id,
            device_metadata=device_meta,
            base_forecast=base_forecast,
            action_type=new_action,
            parameters=new_params,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    s.name = new_name
    s.action_type = sim_result["action_type"]
    s.parameters_json = json.dumps(new_params)

    outcome = db.query(SimulatedOutcome).filter(SimulatedOutcome.scenario_id == scenario_id).first()
    if not outcome:
        outcome = SimulatedOutcome(id=f"out-{scenario_id}", scenario_id=scenario_id)
        db.add(outcome)
    outcome.duration_minutes = sim_result["duration_minutes"]
    outcome.estimated_cost_usd = sim_result["estimated_cost_usd"]
    outcome.overhead_io_penalty_pct = sim_result["overhead_io_penalty_pct"]
    outcome.safety_envelope_passed = sim_result["safety_envelope_passed"]
    outcome.violation_reasons_json = json.dumps(sim_result["violation_reasons"])
    outcome.residual_risk_score = sim_result["residual_risk_score"]
    outcome.trajectory_json = json.dumps(sim_result["counterfactual_q50"])
    outcome.assumptions_json = json.dumps(sim_result["assumptions"])
    s.version = (getattr(s, "version", 1) or 1) + 1
    s.updated_by = current_user.username
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="scenario.updated",
        resource_type="scenario",
        resource_id=scenario_id,
        actor_user=current_user,
        entity_version=s.version,
        changed_fields=["name", "action_type", "parameters"],
        payload={
            "scenario_id": scenario_id,
            "device_id": s.device_id,
            "name": new_name,
            "action_type": sim_result["action_type"],
            "safety_envelope_passed": sim_result["safety_envelope_passed"],
        },
        required_permission="digital_twin.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="UPDATE_SCENARIO",
        target_type="SCENARIO",
        target_id=scenario_id,
        user=current_user.username,
        details={"name": new_name, "action_type": new_action}
    )

    return {
        "scenario_id": scenario_id,
        "device_id": s.device_id,
        "name": new_name,
        "action_type": sim_result["action_type"],
        "parameters": new_params,
        "baseline_state": sim_result["baseline_state"],
        "predicted_outcome": sim_result["predicted_outcome"],
        "safety_envelope_passed": sim_result["safety_envelope_passed"],
        "violation_reasons": sim_result["violation_reasons"],
        "residual_risk_score": sim_result["residual_risk_score"],
        "assumptions": sim_result["assumptions"],
        "calculation_methodology": sim_result["calculation_methodology"],
        "simulation_notice": sim_result["simulation_notice"],
    }


@router.delete("/digital-twin/scenarios/{scenario_id}", tags=["Digital Twin & Simulator"])
@router.delete("/scenarios/{scenario_id}", tags=["Digital Twin & Simulator"])
def delete_digital_twin_scenario(
    scenario_id: str,
    current_user: User = Depends(require_permission("digital_twin.delete")),
    db: Session = Depends(get_db)
):
    """Deletes a saved Digital Twin scenario."""
    s = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Scenario not found")
    name = s.name
    db.delete(s)
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="scenario.deleted",
        resource_type="scenario",
        resource_id=scenario_id,
        actor_user=current_user,
        payload={"deleted_id": scenario_id, "deleted_name": name},
        required_permission="digital_twin.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)
    AuditService.log_event(
        db=db,
        action="DELETE_SCENARIO",
        target_type="SCENARIO",
        target_id=scenario_id,
        user=current_user.username,
        details={"deleted_name": name}
    )
    return {"status": "ok", "deleted_id": scenario_id}


@router.post("/digital-twin/compare", tags=["Digital Twin & Simulator"])
def compare_digital_twin_scenarios(
    payload: ScenarioCompareRequest,
    current_user: User = Depends(require_permission("digital_twin.read")),
    db: Session = Depends(get_db),
):
    """Side-by-side comparison of two or more saved Digital Twin scenarios."""
    if len(payload.scenario_ids) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 scenario_ids to compare")

    items = []
    for sid in payload.scenario_ids:
        s = db.query(Scenario).filter(Scenario.id == sid).first()
        if not s:
            raise HTTPException(status_code=404, detail=f"Scenario '{sid}' not found")
        out = db.query(SimulatedOutcome).filter(SimulatedOutcome.scenario_id == sid).first()
        traj = json.loads(out.trajectory_json) if out and out.trajectory_json else []
        items.append({
            "scenario_id": s.id,
            "name": s.name,
            "device_id": s.device_id,
            "action_type": s.action_type,
            "parameters": json.loads(s.parameters_json),
            "safety_envelope_passed": out.safety_envelope_passed if out else None,
            "residual_risk_score": out.residual_risk_score if out else None,
            "estimated_cost_usd": out.estimated_cost_usd if out else None,
            "overhead_io_penalty_pct": out.overhead_io_penalty_pct if out else None,
            "duration_minutes": out.duration_minutes if out else None,
            "end_used_bytes": traj[-1] if traj else None,
            "violation_reasons": json.loads(out.violation_reasons_json) if out else [],
        })

    valid_items = [i for i in items if i["safety_envelope_passed"] and i["residual_risk_score"] is not None]
    best = min(valid_items, key=lambda x: (x["residual_risk_score"], x["estimated_cost_usd"] or 0.0)) if valid_items else None
    return {
        "compared_count": len(items),
        "recommended_scenario_id": best["scenario_id"] if best else None,
        "simulation_notice": "Simulation only: no real storage systems were modified.",
        "scenarios": items,
    }


@router.get("/digital-twin/scenarios/{scenario_id}/export", tags=["Digital Twin & Simulator"])
def export_digital_twin_scenario(
    scenario_id: str,
    format: str = Query("csv", description="csv or json"),
    current_user: User = Depends(require_permission("digital_twin.export")),
    db: Session = Depends(get_db)
):
    """Exports scenario configuration and counterfactual trajectory in CSV or JSON format."""
    data = get_digital_twin_scenario(scenario_id, current_user=current_user, db=db)
    if format.lower() == "json":
        return data

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["scenario_id", "name", "device_id", "action_type", "step_hour", "predicted_used_bytes", "safety_passed", "residual_risk_score", "estimated_cost_usd"])
    outcome = data.get("outcome") or {}
    traj = outcome.get("trajectory") or []
    for idx, val in enumerate(traj, start=1):
        writer.writerow([
            data["id"],
            data["name"],
            data["device_id"],
            data["action_type"],
            idx,
            val,
            outcome.get("safety_envelope_passed"),
            outcome.get("residual_risk_score"),
            outcome.get("estimated_cost_usd"),
        ])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=scenario_{scenario_id}.csv"}
    )


class OptimizeConstraintsRequest(BaseModel):
    budget_usd: Optional[float] = None
    max_utilization_pct: float = 85.0
    min_free_space_pct: float = 15.0
    max_latency_ms: float = 25.0
    max_transfer_gb: Optional[float] = None
    decision_horizon_days: int = 30
    unit_costs: Optional[Dict[str, float]] = None


@router.post("/digital-twin/optimize/{storage_id}", tags=["Digital Twin & Simulator"])
def optimize_interventions(
    storage_id: str,
    payload: OptimizeConstraintsRequest = OptimizeConstraintsRequest(),
    current_user: User = Depends(require_permission("optimisation.execute")),
    db: Session = Depends(get_db),
):
    """Constrained multi-objective intervention optimizer ranking feasible vs rejected actions."""
    try:
        return DecisionOptimizer.optimize(
            db=db,
            storage_id=storage_id,
            budget_usd=payload.budget_usd,
            max_utilization_pct=payload.max_utilization_pct,
            min_free_space_pct=payload.min_free_space_pct,
            max_latency_ms=payload.max_latency_ms,
            max_transfer_gb=payload.max_transfer_gb,
            decision_horizon_days=payload.decision_horizon_days,
            unit_costs=payload.unit_costs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
