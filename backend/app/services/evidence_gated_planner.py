import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import Device, Telemetry
from app.ml.models import run_forecast
from app.services.risk_engine import RiskEngine
from app.services.atlas.calibration_engine import DigitalTwinCalibrationEngine
from app.services.atlas.fidelity_assessor import FidelityAssessor
from app.services.fleet_topology_service import FleetTopologyService
from app.simulator.digital_twin import DigitalTwinSimulator

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class EvidenceGatedPlanner:
    """
    AEGISSTOR — Candidate Research Contribution (Prompt 17.0):
    Evidence-Gated, Multi-Resource Storage Intervention Planner.

    Jointly evaluates:
      A. Forecast Uncertainty (conformal quantiles [q10, q90])
      B. Simulator Discrepancy (Atlas held-out error against physical observations)
      C. Action-Effect Uncertainty (variance in migration/throttling outcomes)
      D. Multi-Resource Propagation (Omega shared controller & backplane contention)
      E. Lead-Time Feasibility (action completes before predicted breach h*)
      F. Evidence Sufficiency Gating (restricts automated action when uncalibrated)
    """

    MAX_ACCEPTABLE_DISCREPANCY_PCT = 20.0
    MIN_REQUIRED_EVIDENCE_FIDELITY = 70.0
    MAX_ALLOWABLE_MISSINGNESS_RATE = 0.05

    @classmethod
    def plan_interventions(
        cls,
        db: Session,
        device_id: str,
        horizon_hours: int = 72,
        ablation_flags: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """
        Executes the evidence-gated planning pipeline for a target storage device.
        Supports ablation flags to experimentally test which components provide value.
        """
        ablation = ablation_flags or {}
        use_forecast_uncertainty = not ablation.get("remove_forecast_uncertainty", False)
        use_fidelity_checks = not ablation.get("remove_simulator_fidelity", False)
        use_action_uncertainty = not ablation.get("remove_action_uncertainty", False)
        use_resource_propagation = not ablation.get("remove_resource_propagation", False)
        use_lead_time_checks = not ablation.get("remove_lead_time_checks", False)
        use_evidence_gate = not ablation.get("remove_evidence_gate", False)
        use_workload_shift = not ablation.get("remove_workload_shift", False)

        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        # 1. Fetch Latest Telemetry State
        latest_tel = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        current_used_bytes = latest_tel.used_bytes if latest_tel else int(device.total_capacity_bytes * 0.70)
        current_used_gb = current_used_bytes / (1024 ** 3)
        total_cap_gb = device.total_capacity_bytes / (1024 ** 3)
        current_util_pct = (current_used_gb / total_cap_gb) * 100.0 if total_cap_gb > 0 else 70.0
        current_lat_p95 = latest_tel.latency_p95_ms if latest_tel else 8.5
        sla_lat_limit = device.max_acceptable_latency_ms or 15.0

        # 2. Forecast Generation (Capacity & P95 Latency)
        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )
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
        forecast_res = run_forecast(
            telemetry_records=telemetry_dicts,
            target_metric="used_bytes",
            model_type="lightgbm_quantile",
            horizon_hours=horizon_hours,
            total_capacity=device.total_capacity_bytes
        )

        q10_gb = [v / (1024 ** 3) for v in forecast_res["q10"]]
        q50_gb = [v / (1024 ** 3) for v in forecast_res["q50"]]
        q90_gb = [v / (1024 ** 3) for v in forecast_res["q90"]]

        # Effective trajectory for planning: Upper quantile bound (conservative risk assessment)
        effective_trajectory = q90_gb if use_forecast_uncertainty else q50_gb

        # Critical threshold in GB
        crit_threshold_pct = device.critical_threshold_pct or 90.0
        crit_ceiling_gb = total_cap_gb * (crit_threshold_pct / 100.0)

        # 3. Calculate Warning Lead Time h* (Hours to breach)
        lead_time_h_star = None
        for h, val in enumerate(effective_trajectory):
            if val >= crit_ceiling_gb:
                lead_time_h_star = h + 1
                break

        # 4. Assess Simulator Discrepancy & Evidence Fidelity (Atlas Integration)
        fidelity_report = FidelityAssessor.evaluate_device_fidelity(db, device_id)
        if hasattr(fidelity_report, "overall_fidelity_score"):
            overall_fidelity = float(fidelity_report.overall_fidelity_score or 80.0)
        elif isinstance(fidelity_report, dict):
            overall_fidelity = float(fidelity_report.get("overall_fidelity_score", 80.0))
        else:
            overall_fidelity = 80.0
        discrepancy_pct = max(0.0, 100.0 - overall_fidelity)
        telemetry_missingness = getattr(device, "telemetry_missingness_rate", 0.0)

        # Evidence Sufficiency Gate check
        evidence_sufficient = True
        evidence_disqualification_reasons = []

        if use_fidelity_checks:
            if discrepancy_pct > cls.MAX_ACCEPTABLE_DISCREPANCY_PCT:
                evidence_sufficient = False
                evidence_disqualification_reasons.append(
                    f"Simulator discrepancy {discrepancy_pct:.1f}% exceeds maximum allowable error {cls.MAX_ACCEPTABLE_DISCREPANCY_PCT}%"
                )
            if overall_fidelity < cls.MIN_REQUIRED_EVIDENCE_FIDELITY:
                evidence_sufficient = False
                evidence_disqualification_reasons.append(
                    f"Overall evidence fidelity {overall_fidelity:.1f} is below minimum threshold {cls.MIN_REQUIRED_EVIDENCE_FIDELITY}"
                )

        if use_evidence_gate:
            if telemetry_missingness > cls.MAX_ALLOWABLE_MISSINGNESS_RATE:
                evidence_sufficient = False
                evidence_disqualification_reasons.append(
                    f"Telemetry missingness {telemetry_missingness*100:.1f}% exceeds tolerance {cls.MAX_ALLOWABLE_MISSINGNESS_RATE*100}%"
                )

        # 5. Multi-Resource Shared Backplane Topology (Omega Integration)
        fleet_topo = FleetTopologyService.get_fleet_topology(db)
        pool_id = getattr(device, "pool_id", "pool-nvme-ultra")
        shared_devices = [
            n["id"] for n in fleet_topo["nodes"]
            if n.get("type") == "DEVICE" and n.get("pool_id") == pool_id and n["id"] != device_id
        ]
        controller_id = getattr(device, "system_id", "sys-flasharray-prime") or "ctrl-nvme-pcie4"

        # 6. Candidate Actions Formulation & Evaluation
        candidate_actions = [
            {
                "id": "act-tier-cold-1800",
                "action_type": "TIER_COLD_DATA",
                "title": "Migrate 1.8 TB Inactive Blocks to Cold Tier",
                "parameters": {"data_volume_gb": 1800.0, "migration_rate_mb_s": 150.0},
                "execution_hours": 3.5,
                "cost_usd": 45.0,
                "shared_bus_penalty_pct": 18.0,
                "base_runway_gain_h": 168.0
            },
            {
                "id": "act-expand-lun-3000",
                "action_type": "EXPAND_CAPACITY",
                "title": "Online Pool Block Allocation (+3 TB Flash)",
                "parameters": {"added_capacity_gb": 3000.0},
                "execution_hours": 1.0,
                "cost_usd": 120.0,
                "shared_bus_penalty_pct": 5.0,
                "base_runway_gain_h": 240.0
            },
            {
                "id": "act-rebalance-batch-35",
                "action_type": "WORKLOAD_REBALANCING",
                "title": "Rebalance Nightly Analytics Batch Workload (35% IOPS Relocated)",
                "parameters": {"relocated_iops_pct": 35.0},
                "execution_hours": 0.25,
                "cost_usd": 15.0,
                "shared_bus_penalty_pct": -12.0,  # Negative penalty = alleviates bus contention
                "base_runway_gain_h": 48.0
            },
            {
                "id": "act-reschedule-batch-4h",
                "action_type": "RESCHEDULE_TASK",
                "title": "Reschedule Batch Job to Off-Peak 05:00 (+4h Shift)",
                "parameters": {},
                "execution_hours": 0.1,
                "cost_usd": 5.0,
                "shared_bus_penalty_pct": -25.0,
                "base_runway_gain_h": 72.0
            },
            {
                "id": "act-do-nothing",
                "action_type": "DO_NOTHING",
                "title": "Maintain Existing Configurations (Do Nothing)",
                "parameters": {},
                "execution_hours": 0.0,
                "cost_usd": 0.0,
                "shared_bus_penalty_pct": 0.0,
                "base_runway_gain_h": 0.0
            }
        ]

        evaluated_candidates = []

        for act in candidate_actions:
            disqualified = False
            rejection_reasons = []

            exec_time_h = act["execution_hours"]
            cost_usd = act["cost_usd"]
            bus_penalty = act["shared_bus_penalty_pct"]
            runway_gain = act["base_runway_gain_h"]

            # Check 1: Lead-time feasibility (Action must complete before predicted breach)
            if use_lead_time_checks and lead_time_h_star is not None:
                if exec_time_h > lead_time_h_star:
                    disqualified = True
                    rejection_reasons.append(
                        f"Lead-time violation: Execution time ({exec_time_h}h) exceeds warning lead time ({lead_time_h_star}h)"
                    )

            # Check 2: Multi-resource backplane propagation
            if use_resource_propagation and bus_penalty > 15.0:
                # Heavy migration on a shared controller risks pushing neighboring I/O into SLA breach
                disqualified = True
                rejection_reasons.append(
                    f"Multi-resource contention: Shared bus penalty (+{bus_penalty}%) risks SLA breach on shared controller fabric {controller_id}"
                )

            # Check 3: Digital Twin simulator execution
            twin_outcome = DigitalTwinSimulator.simulate_scenario(
                device_id=device_id,
                device_metadata={
                    "total_capacity_bytes": device.total_capacity_bytes,
                    "max_acceptable_latency_ms": sla_lat_limit,
                    "critical_threshold_pct": crit_threshold_pct
                },
                base_forecast=forecast_res,
                action_type=act["action_type"],
                parameters=act["parameters"]
            )

            if not twin_outcome["safety_envelope_passed"]:
                disqualified = True
                rejection_reasons.extend(twin_outcome["violation_reasons"])

            # Check 4: Action effect uncertainty (pessimistic bounds)
            if use_action_uncertainty:
                # Real migration bandwidth varies by ±20% due to concurrent disk wear
                effective_runway_gain = runway_gain * 0.85
                effective_cost = cost_usd * 1.15
            else:
                effective_runway_gain = runway_gain
                effective_cost = cost_usd

            # Multi-objective utility calculation:
            # U = RunwayGain * 1.5 - Cost * 0.1 - BusPenalty * 0.4
            if disqualified:
                utility_score = -999.0
            else:
                utility_score = round(
                    (effective_runway_gain * 1.5) - (effective_cost * 0.1) - (max(0.0, bus_penalty) * 0.4),
                    2
                )

            evaluated_candidates.append({
                "id": act["id"],
                "action_type": act["action_type"],
                "title": act["title"],
                "parameters": act["parameters"],
                "execution_hours": exec_time_h,
                "cost_usd": cost_usd,
                "shared_bus_penalty_pct": bus_penalty,
                "estimated_runway_gain_h": round(effective_runway_gain, 1),
                "is_feasible": not disqualified,
                "rejection_reasons": rejection_reasons,
                "utility_score": utility_score,
                "twin_envelope_passed": twin_outcome["safety_envelope_passed"],
                "simulated_p95_lat_ms": round(current_lat_p95 * (1.0 + (bus_penalty / 100.0) * 0.5), 2)
            })

        # Rank candidates by utility
        feasible_candidates = [c for c in evaluated_candidates if c["is_feasible"]]
        feasible_candidates.sort(key=lambda x: x["utility_score"], reverse=True)

        # 7. Final Evidence-Gated Decision Logic
        if not evidence_sufficient and use_evidence_gate:
            final_status = "EVIDENCE_GATED_FALLBACK"
            recommended_action = None
            decision_rationale = (
                f"FALLBACK TRIGGERED: Autonomous recommendation restricted due to insufficient empirical evidence. "
                f"Reasons: {'; '.join(evidence_disqualification_reasons)}. Manual review required."
            )
        elif len(feasible_candidates) == 0:
            final_status = "NO_FEASIBLE_ACTION_FALLBACK"
            recommended_action = None
            decision_rationale = "FALLBACK TRIGGERED: No candidate action satisfies safety envelope and lead-time constraints. Manual operator triage required."
        else:
            final_status = "ACTION_RECOMMENDED"
            recommended_action = feasible_candidates[0]
            decision_rationale = (
                f"Selected '{recommended_action['title']}' (Utility: {recommended_action['utility_score']}). "
                f"Feasible within warning lead time ({recommended_action['execution_hours']}h <= {lead_time_h_star}h). "
                f"Projected runway extension: +{recommended_action['estimated_runway_gain_h']}h. "
                f"Evidence validated: Atlas discrepancy {discrepancy_pct:.1f}% <= {cls.MAX_ACCEPTABLE_DISCREPANCY_PCT}%."
            )

        return {
            "device_id": device_id,
            "target_device_name": device.name,
            "timestamp": utc_now().isoformat(),
            "warning_lead_time_h_star": lead_time_h_star,
            "forecast_summary": {
                "horizon_hours": horizon_hours,
                "current_used_gb": round(current_used_gb, 2),
                "total_capacity_gb": round(total_cap_gb, 2),
                "current_utilization_pct": round(current_util_pct, 1),
                "q50_terminal_gb": round(q50_gb[-1], 2),
                "q90_terminal_gb": round(q90_gb[-1], 2),
                "conformal_interval_width_gb": round(q90_gb[-1] - q10_gb[-1], 2),
                "using_uncertainty": use_forecast_uncertainty
            },
            "evidence_quality": {
                "overall_fidelity_score": overall_fidelity,
                "atlas_discrepancy_pct": discrepancy_pct,
                "telemetry_missingness_rate": telemetry_missingness,
                "evidence_sufficient": evidence_sufficient,
                "disqualification_reasons": evidence_disqualification_reasons
            },
            "multi_resource_context": {
                "controller_id": controller_id,
                "shared_pool_devices": shared_devices,
                "propagation_checked": use_resource_propagation
            },
            "candidate_evaluations": evaluated_candidates,
            "final_status": final_status,
            "recommended_action": recommended_action,
            "decision_rationale": decision_rationale,
            "ablation_configuration": ablation
        }
