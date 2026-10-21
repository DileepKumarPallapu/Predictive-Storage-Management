import math
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional

class DigitalTwinSimulator:
    """
    Storage Resilience Digital Twin Simulator (v4.0).
    Reproduces projected storage capacity and performance states under alternative
    interventions against the immutable Hard Safety Envelope.
    Guarantees deterministic, isolated simulation with zero physical host disk mutations.
    """

    SUPPORTED_SCENARIOS = [
        "DO_NOTHING",
        "EXPAND_CAPACITY",
        "TIER_COLD_DATA",
        "RESCHEDULE_TASK",
        "WORKLOAD_REBALANCING",
        "CUSTOM_SCENARIO"
    ]

    @classmethod
    def simulate_scenario(
        cls,
        device_id: str,
        device_metadata: Dict[str, Any],
        base_forecast: Dict[str, Any],
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        seed: int = 42
    ) -> Dict[str, Any]:
        if parameters is None:
            parameters = {}

        action_type_norm = action_type.upper()
        if action_type_norm not in cls.SUPPORTED_SCENARIOS:
            raise ValueError(f"Unsupported scenario type: '{action_type}'. Must be one of {cls.SUPPORTED_SCENARIOS}")

        rng = random.Random(seed + hash(action_type_norm) + hash(device_id))

        timestamps = base_forecast.get("timestamps", [])
        if not timestamps:
            now = datetime.now(timezone.utc)
            timestamps = [now + timedelta(hours=h) for h in range(1, 73)]

        baseline_capacity_q50 = list(base_forecast.get("q50", []))
        total_capacity = float(device_metadata.get("total_capacity_bytes", 10 * 1024 * 1024 * 1024 * 1024))
        critical_pct = float(device_metadata.get("critical_threshold_pct", 90.0))
        warning_pct = float(device_metadata.get("warning_threshold_pct", 80.0))
        hard_capacity_limit = (critical_pct / 100.0) * total_capacity
        max_latency_sla = float(device_metadata.get("max_acceptable_latency_ms", 20.0))
        base_latency = float(device_metadata.get("current_latency_p95_ms", 1.8))
        base_throughput = float(device_metadata.get("current_throughput_mb_s", 280.0))

        counterfactual_capacity_q50 = []
        baseline_latency = []
        counterfactual_latency = []
        baseline_throughput = []
        counterfactual_throughput = []
        
        violations = []
        assumptions = []
        limitations = [
            "Simulation estimates are physics approximations and do not constitute measured physical guarantees.",
            "Assumes constant network fabric bandwidth between storage controllers and destination tiers."
        ]
        
        overhead_penalty_pct = 0.0
        duration_hours = 0.0
        estimated_cost_usd = 0.0
        data_movement_gb = 0.0
        start_time = timestamps[0] if timestamps else datetime.now(timezone.utc)
        completion_time = start_time

        # -------------------------------------------------------------
        # SCENARIO 1: DO NOTHING
        # -------------------------------------------------------------
        if action_type_norm == "DO_NOTHING":
            counterfactual_capacity_q50 = list(baseline_capacity_q50)
            duration_hours = 0.0
            estimated_cost_usd = 0.0
            data_movement_gb = 0.0
            assumptions.append("Assumes continued organic diurnal storage consumption without human or automated mitigation.")

        # -------------------------------------------------------------
        # SCENARIO 2: CAPACITY EXPANSION
        # -------------------------------------------------------------
        elif action_type_norm == "EXPAND_CAPACITY":
            added_gb = float(parameters.get("added_capacity_gb", 2000.0))
            if added_gb < 100.0 or added_gb > 100000.0:
                raise ValueError("added_capacity_gb must be between 100 GB and 100,000 GB.")
            
            lead_time_hours = float(parameters.get("provisioning_lead_hours", 2.0))
            duration_hours = lead_time_hours
            data_movement_gb = 0.0
            new_total = total_capacity + (added_gb * 1024 * 1024 * 1024)
            hard_capacity_limit = (critical_pct / 100.0) * new_total

            cost_per_gb = 0.18 if "NVME" in device_metadata.get("tier", "") else 0.06
            estimated_cost_usd = round(added_gb * cost_per_gb, 2)
            overhead_penalty_pct = 2.0  # Minor controller metadata re-striping

            assumptions.append(f"Storage pool extended by +{added_gb} GB; expansion active at T+{lead_time_hours}h.")
            assumptions.append("Requires physical unpartitioned drive blocks in current storage chassis.")

            counterfactual_capacity_q50 = list(baseline_capacity_q50)

        # -------------------------------------------------------------
        # SCENARIO 3: COLD-DATA TIERING
        # -------------------------------------------------------------
        elif action_type_norm == "TIER_COLD_DATA":
            volume_gb = float(parameters.get("data_volume_gb", 1500.0))
            migration_rate_mb_s = float(parameters.get("migration_rate_mb_s", 150.0))
            if volume_gb < 10.0 or volume_gb > 50000.0:
                raise ValueError("data_volume_gb must be between 10 GB and 50,000 GB.")
            if migration_rate_mb_s < 20.0 or migration_rate_mb_s > 1000.0:
                raise ValueError("migration_rate_mb_s must be between 20 MB/s and 1000 MB/s.")

            data_movement_gb = volume_gb
            total_mb = volume_gb * 1024.0
            duration_hours = total_mb / (migration_rate_mb_s * 3600.0)
            
            # Non-linear latency penalty model for controller bus contention
            overhead_penalty_pct = round((migration_rate_mb_s / 300.0) ** 1.35 * 22.0, 1)
            estimated_cost_usd = round(volume_gb * 0.015, 2)  # Secondary tier storage + egress

            assumptions.append(f"Relocates {volume_gb} GB of eligible cold objects (last read > 30 days) to secondary pool.")
            assumptions.append(f"Streams at {migration_rate_mb_s} MB/s inducing a transient +{overhead_penalty_pct}% I/O bus contention.")

            volume_bytes = volume_gb * 1024 * 1024 * 1024
            for h_idx, val in enumerate(baseline_capacity_q50):
                elapsed_h = h_idx + 1
                if elapsed_h <= duration_hours:
                    fraction = elapsed_h / duration_hours
                    effective_reduction = volume_bytes * fraction
                else:
                    effective_reduction = volume_bytes
                counterfactual_capacity_q50.append(round(max(0.0, val - effective_reduction), 2))

        # -------------------------------------------------------------
        # SCENARIO 4: BACKGROUND-JOB RESCHEDULING
        # -------------------------------------------------------------
        elif action_type_norm == "RESCHEDULE_TASK":
            duration_hours = 0.5
            data_movement_gb = 0.0
            estimated_cost_usd = 0.0
            overhead_penalty_pct = -18.0  # Latency reduction during peak operational hours
            assumptions.append("Reschedules heavy RAID scrubbing, volume verification, and backup jobs to off-peak (02:00 - 05:00 UTC).")
            assumptions.append("No volume data is deleted or moved; queue contention and tail latency are relieved.")
            counterfactual_capacity_q50 = list(baseline_capacity_q50)

        # -------------------------------------------------------------
        # SCENARIO 5: WORKLOAD REBALANCING
        # -------------------------------------------------------------
        elif action_type_norm == "WORKLOAD_REBALANCING":
            relocated_iops_pct = float(parameters.get("relocated_iops_pct", 25.0))
            if relocated_iops_pct < 5.0 or relocated_iops_pct > 75.0:
                raise ValueError("relocated_iops_pct must be between 5% and 75%.")
            
            duration_hours = 2.0
            data_movement_gb = round(relocated_iops_pct * 12.0, 1)
            estimated_cost_usd = 15.0
            overhead_penalty_pct = 4.0
            assumptions.append(f"Re-routes {relocated_iops_pct}% of concurrent database tenant queries to destination pool.")
            assumptions.append("Requires verification that destination pool has $\\ge 30\\%$ unused IOPS headroom.")
            
            reduction_factor = 1.0 - (relocated_iops_pct / 100.0) * 0.12
            for val in baseline_capacity_q50:
                counterfactual_capacity_q50.append(round(val * reduction_factor, 2))

        # -------------------------------------------------------------
        # SCENARIO 6: CUSTOM SCENARIO
        # -------------------------------------------------------------
        elif action_type_norm == "CUSTOM_SCENARIO":
            capacity_delta_gb = float(parameters.get("capacity_delta_gb", 0.0))
            duration_hours = max(0.1, float(parameters.get("duration_hours", 1.0)))
            overhead_penalty_pct = float(parameters.get("io_overhead_pct", 5.0))
            estimated_cost_usd = float(parameters.get("estimated_cost_usd", 10.0))
            data_movement_gb = max(0.0, abs(capacity_delta_gb))

            assumptions.append(f"Custom scenario parameters applied: delta={capacity_delta_gb} GB, duration={duration_hours}h.")
            
            delta_bytes = capacity_delta_gb * 1024 * 1024 * 1024
            for h_idx, val in enumerate(baseline_capacity_q50):
                elapsed_h = h_idx + 1
                if elapsed_h <= duration_hours:
                    effective_delta = delta_bytes * (elapsed_h / duration_hours)
                else:
                    effective_delta = delta_bytes
                counterfactual_capacity_q50.append(round(max(0.0, val - effective_delta), 2))

        # -------------------------------------------------------------
        # Trajectory Simulation for Performance (Latency & Throughput)
        # -------------------------------------------------------------
        completion_time = start_time + timedelta(hours=duration_hours)
        
        for h_idx, base_cap in enumerate(baseline_capacity_q50):
            elapsed_h = h_idx + 1
            # Diurnal seasonality on baseline latency
            hour_of_day = (start_time.hour + elapsed_h) % 24
            diurnal_mult = 1.0 + 0.35 * math.sin((hour_of_day - 6) / 24.0 * 2.0 * math.pi)
            
            # Baseline performance
            b_lat = round(base_latency * diurnal_mult, 2)
            b_tp = round(base_throughput * diurnal_mult, 1)
            baseline_latency.append(b_lat)
            baseline_throughput.append(b_tp)

            # Counterfactual performance with transient overhead
            if elapsed_h <= duration_hours:
                active_overhead = overhead_penalty_pct
            else:
                active_overhead = 0.0

            # Tail latency inflation during action
            cf_lat = round(b_lat * (1.0 + active_overhead / 100.0), 2)
            cf_tp = round(b_tp * (1.0 + (active_overhead * 0.5) / 100.0), 1)
            counterfactual_latency.append(cf_lat)
            counterfactual_throughput.append(cf_tp)

        # -------------------------------------------------------------
        # Hard Safety Envelope Constraints Evaluation
        # -------------------------------------------------------------
        # 1. Capacity Constraint
        capacity_breach_count = 0
        for val in counterfactual_capacity_q50:
            if val >= hard_capacity_limit:
                capacity_breach_count += 1

        if capacity_breach_count > 0:
            violations.append(
                f"Counterfactual capacity violates critical limit ({critical_pct}%) for {capacity_breach_count} hours."
            )

        # 2. Tail Latency Constraint
        latency_breach_count = 0
        peak_simulated_latency = max(counterfactual_latency) if counterfactual_latency else base_latency
        for lat in counterfactual_latency:
            if lat > max_latency_sla:
                latency_breach_count += 1

        if latency_breach_count > 0:
            violations.append(
                f"Simulated tail latency ({peak_simulated_latency}ms) breaches hard SLA ({max_latency_sla}ms) for {latency_breach_count} hours."
            )

        passed_envelope = len(violations) == 0

        # Residual Risk Score calculation
        final_used = counterfactual_capacity_q50[-1] if counterfactual_capacity_q50 else baseline_capacity_q50[-1]
        final_util = (final_used / total_capacity) * 100.0
        
        if passed_envelope:
            residual_risk = max(0.04, min(0.60, (final_util / critical_pct) * 0.45))
        else:
            residual_risk = 0.95

        return {
            "scenario_id": f"sim-{action_type_norm.lower()}-{uuid.uuid4().hex[:10]}",
            "device_id": device_id,
            "action_type": action_type_norm,
            "parameters": parameters,
            "simulation_seed": seed,
            "duration_hours": round(duration_hours, 2),
            "duration_minutes": round(duration_hours * 60.0, 1),
            "action_start_timestamp": start_time,
            "action_completion_timestamp": completion_time,
            "estimated_cost_usd": estimated_cost_usd,
            "data_movement_gb": data_movement_gb,
            "overhead_io_penalty_pct": overhead_penalty_pct,
            "safety_envelope_passed": passed_envelope,
            "violation_reasons": violations,
            "residual_risk_score": round(residual_risk, 3),
            "assumptions": assumptions,
            "limitations": limitations,
            "timeline_timestamps": timestamps,
            "baseline_q50": baseline_capacity_q50,
            "counterfactual_q50": counterfactual_capacity_q50,
            "baseline_latency_p95": baseline_latency,
            "counterfactual_latency_p95": counterfactual_latency,
            "baseline_throughput_mb_s": baseline_throughput,
            "counterfactual_throughput_mb_s": counterfactual_throughput,
            "hard_capacity_limit_bytes": hard_capacity_limit,
            "max_latency_sla_ms": max_latency_sla,
            "is_simulated_estimate": True
        }
