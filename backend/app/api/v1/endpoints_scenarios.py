import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, Scenario, SimulatedOutcome
from app.schemas.payloads import ScenarioCreate, ScenarioSimulationResponse
from app.simulator.digital_twin import DigitalTwinSimulator
from app.ml.models import run_forecast
from app.services.audit_service import AuditService

router = APIRouter()

@router.post("/scenarios", response_model=ScenarioSimulationResponse)
def create_and_run_scenario(payload: ScenarioCreate, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target device not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == payload.device_id)
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
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms
    }

    sim_result = DigitalTwinSimulator.simulate_scenario(
        device_id=payload.device_id,
        device_metadata=device_meta,
        base_forecast=base_forecast,
        action_type=payload.action_type,
        parameters=payload.parameters
    )

    # Save to database
    scenario_id = sim_result["scenario_id"]
    scenario = Scenario(
        id=scenario_id,
        device_id=payload.device_id,
        name=payload.name,
        action_type=payload.action_type,
        parameters_json=json.dumps(payload.parameters),
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
    db.commit()

    AuditService.log_event(
        db=db,
        action="CREATE_SCENARIO",
        target_type="SCENARIO",
        target_id=scenario_id,
        details={"name": payload.name, "action_type": payload.action_type, "safety_passed": sim_result["safety_envelope_passed"]}
    )

    return ScenarioSimulationResponse(
        scenario_id=scenario_id,
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
        hard_limit=sim_result["hard_limit"],
        is_simulated_estimate=True
    )
