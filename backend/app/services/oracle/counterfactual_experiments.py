import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    Device, Telemetry, OracleWorkload, OracleWorkloadTelemetry,
    OracleCounterfactualExperiment
)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class CounterfactualExperimentService:
    """
    AEGISSTOR ORACLE — Controlled Counterfactual Workload Simulator.
    Simulates what-if workload parameter shifts in the pure software Digital Twin.
    Strictly isolated: zero host mutations, zero unearned causal claims.
    """

    SIMULATOR_VERSION = "DigitalTwin-Oracle-v5.0"

    @classmethod
    def run_counterfactual_simulation(
        cls,
        db: Session,
        target_device_id: str,
        workload_id: str,
        intervention_type: str,
        parameters: Dict[str, Any],
        horizon_hours: int = 72
    ) -> Dict[str, Any]:
        """
        Executes a controlled what-if counterfactual scenario against the Digital Twin.
        Supported intervention types:
          - THROTTLE_INTENSITY: reduces arrival IOPS by intensity_reduction_pct (e.g. 30.0%)
          - RESCHEDULE_WINDOW: shifts batch execution window off-peak by shift_hours
          - REBALANCE_READ_WRITE: optimizes write batching, shifting read_ratio
          - EXPAND_SHARED_LIMIT: relaxes controller queue cap
        """
        device = db.query(Device).filter(Device.id == target_device_id).first()
        if not device:
            raise ValueError(f"Device {target_device_id} not found")

        workload = db.query(OracleWorkload).filter(OracleWorkload.id == workload_id).first()
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")

        # 1. Baseline Telemetry State
        latest_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == target_device_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        base_cap_bytes = latest_tel.used_bytes if (latest_tel and latest_tel.used_bytes) else int(device.total_capacity_bytes * 0.70)
        base_cap_gb = base_cap_bytes / (1024 ** 3)
        base_lat_ms = latest_tel.latency_p95_ms if (latest_tel and latest_tel.latency_p95_ms) else 8.5
        base_sla_ms = device.max_acceptable_latency_ms or 15.0

        # 2. Simulate Action Dynamics over Horizon
        simulated_latencies = []
        simulated_capacities = []
        timestamps = []

        now = utc_now().replace(minute=0, second=0, microsecond=0)

        # Parameter extraction
        intensity_reduction = float(parameters.get("intensity_reduction_pct", 25.0)) / 100.0
        shift_hours = int(parameters.get("shift_hours", 4))

        sim_current_gb = base_cap_gb
        daily_growth_gb = getattr(device, "daily_growth_gb", 45.0)
        growth_step_gb = (daily_growth_gb / 24.0)

        for h in range(horizon_hours):
            t = now + timedelta(hours=h)
            timestamps.append(t.isoformat())
            hour_of_day = t.hour

            # Baseline diurnal multiplier
            diurnal = 0.55 + 0.45 * math.sin((hour_of_day - 6) / 24.0 * 2.0 * math.pi)
            diurnal = max(0.2, min(1.2, diurnal))

            # Batch workload burst
            is_burst_hour = 1 <= hour_of_day <= 4
            if intervention_type == "RESCHEDULE_WINDOW":
                # Shifted window (e.g. 05:00 - 08:00)
                is_burst_hour = (1 + shift_hours) % 24 <= hour_of_day <= (4 + shift_hours) % 24

            batch_mult = 2.2 if is_burst_hour else 1.0

            # Apply throttling intervention
            if intervention_type == "THROTTLE_INTENSITY" and is_burst_hour:
                batch_mult = max(1.0, batch_mult * (1.0 - intensity_reduction))

            # Capacity trajectory
            sim_current_gb += growth_step_gb * (0.8 + 0.3 * diurnal)
            simulated_capacities.append(round(sim_current_gb, 2))

            # Latency physics simulation: non-linear queue delay
            sim_queue = max(0.4, (batch_mult * diurnal) * 2.2)
            if intervention_type == "EXPAND_SHARED_LIMIT":
                sim_queue *= 0.65  # Controller expansion absorbs queue depth

            sim_lat = base_lat_ms * (0.8 + (sim_queue ** 1.3) * 0.4)
            simulated_latencies.append(round(sim_lat, 2))

        # 3. Aggregate Comparative Metrics
        max_sim_lat = max(simulated_latencies)
        avg_sim_lat = sum(simulated_latencies) / len(simulated_latencies)
        latency_reduction_pct = max(0.0, ((base_lat_ms - avg_sim_lat) / base_lat_ms) * 100.0)

        sla_breach_prevented = (base_lat_ms >= base_sla_ms) and (max_sim_lat < base_sla_ms)

        exp_id = f"exp-oracle-{uuid.uuid4().hex[:8]}"
        title = f"Counterfactual {intervention_type} on {workload.name}"

        baseline_summary = {
            "device_id": target_device_id,
            "starting_used_gb": round(base_cap_gb, 2),
            "baseline_p95_latency_ms": round(base_lat_ms, 2),
            "sla_latency_ceiling_ms": round(base_sla_ms, 2)
        }

        simulated_summary = {
            "max_simulated_latency_ms": round(max_sim_lat, 2),
            "avg_simulated_latency_ms": round(avg_sim_lat, 2),
            "latency_reduction_pct": round(latency_reduction_pct, 1),
            "sla_breach_prevented": sla_breach_prevented,
            "final_projected_capacity_gb": simulated_capacities[-1],
            "timestamps_sample": timestamps[:6],
            "simulated_latencies_sample": simulated_latencies[:6],
            "simulated_capacities_sample": simulated_capacities[:6]
        }

        # 4. Save simulation audit record
        exp_record = OracleCounterfactualExperiment(
            id=exp_id,
            title=title,
            target_device_id=target_device_id,
            workload_id=workload_id,
            intervention_type=intervention_type,
            parameter_changes_json=json.dumps(parameters),
            baseline_metrics_json=json.dumps(baseline_summary),
            simulated_metrics_json=json.dumps(simulated_summary),
            is_causally_proven=False,
            causality_disclaimer="Simulated counterfactual outcome in Digital Twin sandbox. Observational attribution does not establish physical causation without real controlled measurement.",
            simulator_version=cls.SIMULATOR_VERSION,
            created_at=utc_now()
        )
        db.add(exp_record)
        db.commit()
        db.refresh(exp_record)

        return {
            "experiment_id": exp_record.id,
            "title": title,
            "target_device_id": target_device_id,
            "workload_id": workload_id,
            "intervention_type": intervention_type,
            "horizon_hours": horizon_hours,
            "baseline": baseline_summary,
            "simulated_outcome": simulated_summary,
            "sla_breach_prevented": sla_breach_prevented,
            "is_causally_proven": False,
            "causality_disclaimer": exp_record.causality_disclaimer,
            "simulator_version": cls.SIMULATOR_VERSION,
            "created_at": exp_record.created_at.isoformat()
        }

    @classmethod
    def list_experiments(cls, db: Session, target_device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(OracleCounterfactualExperiment)
        if target_device_id:
            query = query.filter(OracleCounterfactualExperiment.target_device_id == target_device_id)
        runs = query.order_by(OracleCounterfactualExperiment.created_at.desc()).all()

        results = []
        for r in runs:
            results.append({
                "id": r.id,
                "title": r.title,
                "target_device_id": r.target_device_id,
                "workload_id": r.workload_id,
                "intervention_type": r.intervention_type,
                "parameters": json.loads(r.parameter_changes_json or "{}"),
                "baseline": json.loads(r.baseline_metrics_json or "{}"),
                "simulated_outcome": json.loads(r.simulated_metrics_json or "{}"),
                "is_causally_proven": r.is_causally_proven,
                "causality_disclaimer": r.causality_disclaimer,
                "simulator_version": r.simulator_version,
                "created_at": r.created_at.isoformat()
            })
        return results
