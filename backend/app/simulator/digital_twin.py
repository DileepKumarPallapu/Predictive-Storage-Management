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
        "CAPACITY_EXPANSION",
        "TIER_COLD_DATA",
        "DATA_TIERING_ARCHIVAL",
        "RESCHEDULE_TASK",
        "WORKLOAD_REBALANCING",
        "WORKLOAD_DISTRIBUTION",
        "REBALANCE_WORKLOAD",
        "CAPACITY_GROWTH_CHANGE",
        "MAINTENANCE_PLANNING",
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
        total_capacity = float(device_metadata.get("total_capacity_bytes") or (10 * 1024 * 1024 * 1024 * 1024))
        effective_total_capacity = total_capacity
        current_used_bytes = float(device_metadata.get("current_used_bytes") if device_metadata.get("current_used_bytes") is not None else (baseline_capacity_q50[0] if baseline_capacity_q50 else 0.0))
        critical_pct = float(device_metadata.get("critical_threshold_pct") or 90.0)
        warning_pct = float(device_metadata.get("warning_threshold_pct") or 80.0)
        hard_capacity_limit = (critical_pct / 100.0) * total_capacity
        max_latency_sla = float(device_metadata.get("max_acceptable_latency_ms") or 20.0)
        base_latency = float(device_metadata.get("current_latency_p95_ms") or 1.8)
        base_throughput = float(device_metadata.get("current_throughput_mb_s") or 280.0)
        calculation_methodology = "Baseline time-series trajectory without intervention."

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
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except Exception:
                start_time = datetime.now(timezone.utc)
        completion_time = start_time

        # -------------------------------------------------------------
        # SCENARIO 1: DO NOTHING
        # -------------------------------------------------------------
        if action_type_norm == "DO_NOTHING":
            counterfactual_capacity_q50 = list(baseline_capacity_q50)
            duration_hours = 0.0
            estimated_cost_usd = 0.0
            data_movement_gb = 0.0
            calculation_methodology = "Direct baseline continuation: New Capacity = Existing Capacity; New Used = Forecasted Baseline Used."
            assumptions.append("Assumes continued organic diurnal storage consumption without human or automated mitigation.")

        # -------------------------------------------------------------
        # SCENARIO 2: CAPACITY EXPANSION
        # -------------------------------------------------------------
        elif action_type_norm in ("EXPAND_CAPACITY", "CAPACITY_EXPANSION"):
            added_gb = float(parameters.get("added_capacity_gb", parameters.get("additional_capacity_gb", 2000.0)))
            if added_gb <= 0.0 or added_gb > 1000000.0:
                raise ValueError("added_capacity_gb must be positive and <= 1,000,000 GB.")
            
            lead_time_hours = float(parameters.get("provisioning_lead_hours", 2.0))
            if lead_time_hours < 0:
                raise ValueError("provisioning_lead_hours cannot be negative.")
            duration_hours = lead_time_hours
            data_movement_gb = 0.0
            effective_total_capacity = total_capacity + (added_gb * 1024 * 1024 * 1024)
            hard_capacity_limit = (critical_pct / 100.0) * effective_total_capacity

            cost_per_gb = 0.18 if "NVME" in device_metadata.get("tier", "") else 0.06
            estimated_cost_usd = round(added_gb * cost_per_gb, 2)
            overhead_penalty_pct = 2.0  # Minor controller metadata re-striping
            calculation_methodology = (
                f"New Total Capacity = Existing Total Capacity ({total_capacity/(1024**3):.2f} GB) + "
                f"Additional Capacity ({added_gb:.2f} GB) = {effective_total_capacity/(1024**3):.2f} GB."
            )

            assumptions.append(f"Storage pool extended by +{added_gb} GB; expansion active at T+{lead_time_hours}h.")
            assumptions.append("Requires physical unpartitioned drive blocks in current storage chassis.")

            counterfactual_capacity_q50 = list(baseline_capacity_q50)

        # -------------------------------------------------------------
        # SCENARIO 3: DATA TIERING OR ARCHIVAL
        # -------------------------------------------------------------
        elif action_type_norm in ("TIER_COLD_DATA", "DATA_TIERING_ARCHIVAL"):
            volume_gb = float(parameters.get("data_volume_gb", parameters.get("archived_capacity_gb", 1500.0)))
            migration_rate_mb_s = float(parameters.get("migration_rate_mb_s", 150.0))
            if volume_gb <= 0.0 or volume_gb > 500000.0:
                raise ValueError("archived capacity (data_volume_gb) must be positive and <= 500,000 GB.")
            volume_bytes = volume_gb * 1024 * 1024 * 1024
            if volume_bytes > current_used_bytes:
                raise ValueError(
                    f"Impossible scenario: cannot archive {volume_gb:.2f} GB when current used capacity is only "
                    f"{current_used_bytes/(1024**3):.2f} GB."
                )
            if migration_rate_mb_s < 10.0 or migration_rate_mb_s > 2000.0:
                raise ValueError("migration_rate_mb_s must be between 10 MB/s and 2000 MB/s.")

            data_movement_gb = volume_gb
            total_mb = volume_gb * 1024.0
            duration_hours = total_mb / (migration_rate_mb_s * 3600.0)
            
            # Non-linear latency penalty model for controller bus contention
            overhead_penalty_pct = round((migration_rate_mb_s / 300.0) ** 1.35 * 22.0, 1)
            estimated_cost_usd = round(volume_gb * 0.015, 2)
            calculation_methodology = (
                f"New Used Capacity = Baseline Used Capacity - User-Defined Archived Capacity ({volume_gb:.2f} GB), "
                f"streamed linearly at {migration_rate_mb_s} MB/s over {duration_hours:.2f}h."
            )

            assumptions.append(f"Relocates {volume_gb} GB of eligible cold objects to secondary archival tier.")
            assumptions.append(f"Streams at {migration_rate_mb_s} MB/s inducing a transient +{overhead_penalty_pct}% I/O bus contention.")

            for h_idx, val in enumerate(baseline_capacity_q50):
                elapsed_h = h_idx + 1
                if duration_hours > 0 and elapsed_h <= duration_hours:
                    fraction = elapsed_h / duration_hours
                    effective_reduction = volume_bytes * fraction
                else:
                    effective_reduction = volume_bytes
                counterfactual_capacity_q50.append(round(max(0.0, val - effective_reduction), 2))

        # -------------------------------------------------------------
        # SCENARIO 4: BACKGROUND-JOB RESCHEDULING / MAINTENANCE PLANNING
        # -------------------------------------------------------------
        elif action_type_norm in ("RESCHEDULE_TASK", "MAINTENANCE_PLANNING"):
            duration_hours = float(parameters.get("maintenance_window_hours", parameters.get("duration_hours", 2.0)))
            if duration_hours < 0.1 or duration_hours > 48.0:
                raise ValueError("maintenance_window_hours must be between 0.1 and 48.0 hours.")
            overhead_penalty_pct = float(parameters.get("expected_io_overhead_pct", -18.0 if action_type_norm == "RESCHEDULE_TASK" else 12.0))
            if overhead_penalty_pct < -80.0 or overhead_penalty_pct > 200.0:
                raise ValueError("expected_io_overhead_pct must be between -80% and 200%.")
            data_movement_gb = 0.0
            estimated_cost_usd = round(duration_hours * 10.0, 2) if action_type_norm == "MAINTENANCE_PLANNING" else 0.0
            calculation_methodology = (
                f"Applies configurable maintenance window ({duration_hours}h) with {overhead_penalty_pct:+.1f}% "
                "transient I/O overhead; zero capacity mutation."
            )
            assumptions.append(f"Scheduled maintenance window of {duration_hours} hours with {overhead_penalty_pct:+.1f}% controller I/O impact.")
            counterfactual_capacity_q50 = list(baseline_capacity_q50)

        # -------------------------------------------------------------
        # SCENARIO 5: WORKLOAD DISTRIBUTION / REBALANCING
        # -------------------------------------------------------------
        elif action_type_norm in ("WORKLOAD_REBALANCING", "WORKLOAD_DISTRIBUTION", "REBALANCE_WORKLOAD"):
            relocated_iops_pct = float(parameters.get("relocated_iops_pct", parameters.get("distribution_share_pct", 25.0)))
            if relocated_iops_pct < 5.0 or relocated_iops_pct > 75.0:
                raise ValueError("relocated_iops_pct must be between 5% and 75%.")
            
            duration_hours = 2.0
            data_movement_gb = round(relocated_iops_pct * 12.0, 1)
            estimated_cost_usd = 15.0
            overhead_penalty_pct = 4.0
            calculation_methodology = (
                f"Workload distribution shifts {relocated_iops_pct}% IOPS & growth allocation to peer storage tier, "
                "reducing capacity demand proportionally."
            )
            assumptions.append(f"Re-routes {relocated_iops_pct}% of concurrent tenant workloads to destination pool.")
            assumptions.append("Requires verification that destination pool has >= 30% unused IOPS headroom.")
            
            reduction_factor = 1.0 - (relocated_iops_pct / 100.0) * 0.12
            for val in baseline_capacity_q50:
                counterfactual_capacity_q50.append(round(val * reduction_factor, 2))

        # -------------------------------------------------------------
        # SCENARIO 6: CAPACITY GROWTH CHANGE
        # -------------------------------------------------------------
        elif action_type_norm == "CAPACITY_GROWTH_CHANGE":
            growth_multiplier = float(parameters.get("growth_multiplier", 0.5))
            if growth_multiplier < -1.0 or growth_multiplier > 10.0:
                raise ValueError("growth_multiplier must be between -1.0 and 10.0.")
            duration_hours = 0.0
            data_movement_gb = 0.0
            estimated_cost_usd = 0.0
            overhead_penalty_pct = 0.0
            calculation_methodology = (
                f"Scales projected incremental capacity growth deltas by growth_multiplier={growth_multiplier}x "
                "starting from current observed used capacity."
            )
            assumptions.append(f"Evaluates sensitivity under {growth_multiplier}x capacity consumption growth rate.")
            for val in baseline_capacity_q50:
                delta = val - current_used_bytes
                scaled = current_used_bytes + (delta * growth_multiplier)
                counterfactual_capacity_q50.append(round(max(0.0, min(effective_total_capacity, scaled)), 2))

        # -------------------------------------------------------------
        # SCENARIO 7: CUSTOM SCENARIO
        # -------------------------------------------------------------
        elif action_type_norm == "CUSTOM_SCENARIO":
            capacity_delta_gb = float(parameters.get("capacity_delta_gb", 0.0))
            duration_hours = max(0.1, float(parameters.get("duration_hours", 1.0)))
            overhead_penalty_pct = float(parameters.get("io_overhead_pct", 5.0))
            estimated_cost_usd = float(parameters.get("estimated_cost_usd", 10.0))
            data_movement_gb = max(0.0, abs(capacity_delta_gb))
            calculation_methodology = f"Custom delta adjustment of {capacity_delta_gb} GB over {duration_hours}h."

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

        # Residual Risk Score & Baseline vs Counterfactual Outcome comparison
        final_used = counterfactual_capacity_q50[-1] if counterfactual_capacity_q50 else baseline_capacity_q50[-1]
        final_util = round((final_used / effective_total_capacity) * 100.0, 2) if effective_total_capacity > 0 else 0.0
        baseline_final_used = baseline_capacity_q50[-1] if baseline_capacity_q50 else current_used_bytes
        baseline_util = round((current_used_bytes / total_capacity) * 100.0, 2) if total_capacity > 0 else 0.0

        def _risk_cat(u: float) -> str:
            if u >= critical_pct:
                return "CRITICAL"
            if u >= warning_pct:
                return "WARNING"
            return "NORMAL"

        risk_before = _risk_cat(baseline_util)
        risk_after = _risk_cat(final_util)

        horizon_days = max(1.0, len(counterfactual_capacity_q50) / 24.0)
        cf_daily_growth = (final_used - counterfactual_capacity_q50[0]) / horizon_days if len(counterfactual_capacity_q50) >= 2 else 0.0
        safe_rem = hard_capacity_limit - final_used
        if safe_rem <= 0:
            est_runway_days = 0.0
        elif cf_daily_growth <= 1.0:
            est_runway_days = None
        else:
            est_runway_days = round(safe_rem / cf_daily_growth, 1)

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
            "action_start_timestamp": start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time),
            "action_completion_timestamp": completion_time.isoformat() if hasattr(completion_time, "isoformat") else str(completion_time),
            "estimated_cost_usd": estimated_cost_usd,
            "data_movement_gb": data_movement_gb,
            "overhead_io_penalty_pct": overhead_penalty_pct,
            "safety_envelope_passed": passed_envelope,
            "violation_reasons": violations,
            "residual_risk_score": round(residual_risk, 3),
            "baseline_state": {
                "total_capacity_bytes": int(total_capacity),
                "current_used_bytes": int(current_used_bytes),
                "current_free_bytes": int(max(0.0, total_capacity - current_used_bytes)),
                "current_utilization_pct": baseline_util,
                "projected_end_used_bytes": int(baseline_final_used),
                "risk_category": risk_before,
            },
            "predicted_outcome": {
                "new_total_capacity_bytes": int(effective_total_capacity),
                "new_used_bytes": int(final_used),
                "new_free_bytes": int(max(0.0, effective_total_capacity - final_used)),
                "new_utilization_pct": final_util,
                "new_estimated_runway_days": est_runway_days,
                "risk_category_before": risk_before,
                "risk_category_after": risk_after,
                "risk_category_changed": risk_before != risk_after,
            },
            "calculation_methodology": calculation_methodology,
            "simulation_notice": "Simulation only: no real storage systems were modified. Simulated results are not actual infrastructure changes.",
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
