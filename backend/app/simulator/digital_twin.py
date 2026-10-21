import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

class DigitalTwinSimulator:
    """
    Storage Resilience Digital Twin Simulator.
    Clones current storage geometry, capacity, and performance state to simulate
    counterfactual interventions against an immutable Hard Safety Envelope.
    Clearly marks all outputs as simulator estimates.
    """

    @classmethod
    def simulate_scenario(
        cls,
        device_id: str,
        device_metadata: Dict[str, Any],
        base_forecast: Dict[str, Any],
        action_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        timestamps = base_forecast["timestamps"]
        baseline_q50 = base_forecast["q50"]
        total_capacity = float(device_metadata["total_capacity_bytes"])
        critical_pct = float(device_metadata.get("critical_threshold_pct", 90.0))
        hard_limit = (critical_pct / 100.0) * total_capacity
        max_latency_sla = float(device_metadata.get("max_acceptable_latency_ms", 20.0))

        counterfactual_q50 = []
        violations = []
        assumptions = []
        overhead_penalty_pct = 0.0
        duration_minutes = 0.0
        estimated_cost_usd = 0.0

        if action_type == "DO_NOTHING":
            counterfactual_q50 = list(baseline_q50)
            duration_minutes = 0.0
            estimated_cost_usd = 0.0
            assumptions.append("Assumes persistence of current diurnal workload and organic growth without administrative intervention.")
            # Check if baseline breaches limit
            for val in baseline_q50:
                if val >= hard_limit:
                    violations.append(f"Baseline capacity breaches hard critical safety threshold ({round(val / 1e12, 2)} TB >= {round(hard_limit / 1e12, 2)} TB).")
                    break

        elif action_type == "EXPAND_CAPACITY":
            added_gb = float(parameters.get("added_capacity_gb", 2000.0))
            added_bytes = added_gb * 1024 * 1024 * 1024
            lead_time_hours = float(parameters.get("provisioning_lead_hours", 2.0))
            new_total = total_capacity + added_bytes
            new_hard_limit = (critical_pct / 100.0) * new_total

            duration_minutes = lead_time_hours * 60.0
            # Tier 1 NVMe: ~$0.15/GB/mo, SAS: ~$0.05/GB/mo
            cost_per_gb = 0.18 if "nvme" in device_id else 0.06
            estimated_cost_usd = round(added_gb * cost_per_gb, 2)
            assumptions.append(f"Capacity expansion (+{added_gb} GB) takes effect after a {lead_time_hours}h online volume grow operation.")
            assumptions.append("Requires available unallocated physical blocks in underlying storage pool.")

            for i, val in enumerate(baseline_q50):
                # Until lead time, usage is unchanged against old capacity; afterwards headroom increases
                counterfactual_q50.append(val)
            hard_limit = new_hard_limit

        elif action_type == "TIER_COLD_DATA":
            volume_gb = float(parameters.get("data_volume_gb", 1500.0))
            migration_rate_mb_s = float(parameters.get("migration_rate_mb_s", 150.0))
            volume_bytes = volume_gb * 1024 * 1024 * 1024
            
            # Migration physics
            total_mb = volume_gb * 1024.0
            duration_sec = total_mb / max(10.0, migration_rate_mb_s)
            duration_minutes = round(duration_sec / 60.0, 1)
            duration_hours = duration_sec / 3600.0

            overhead_penalty_pct = round(min(35.0, (migration_rate_mb_s / 300.0) * 25.0), 1)
            estimated_cost_usd = round(volume_gb * 0.015, 2)  # Secondary tier / egress fee

            assumptions.append(f"Data tiering moves {volume_gb} GB of cold objects to secondary storage.")
            assumptions.append(f"Transient I/O latency elevation of +{overhead_penalty_pct}% during migration window ({duration_minutes} min).")
            assumptions.append("Cold data identification based on access timestamp > 30 days.")

            # Calculate capacity progression
            hours_elapsed = 0.0
            for i, val in enumerate(baseline_q50):
                hours_elapsed += 1.0
                if hours_elapsed <= duration_hours:
                    # Partial migration completed
                    fraction = hours_elapsed / duration_hours
                    effective_reduction = volume_bytes * fraction
                else:
                    effective_reduction = volume_bytes
                
                c_val = max(0.0, val - effective_reduction)
                counterfactual_q50.append(round(c_val, 2))

            # Safety check: does migration latency penalty breach SLA?
            base_lat = float(device_metadata.get("current_latency_p95_ms", 1.8))
            projected_peak_latency = base_lat * (1.0 + overhead_penalty_pct / 100.0)
            if projected_peak_latency > max_latency_sla:
                violations.append(f"Migration I/O overhead elevates tail latency to {round(projected_peak_latency, 2)}ms, exceeding hard SLA limit ({max_latency_sla}ms).")

        elif action_type == "RESCHEDULE_TASK":
            duration_minutes = 15.0
            estimated_cost_usd = 0.0
            overhead_penalty_pct = -18.0  # Reduces latency during business hours
            assumptions.append("Reschedules heavy RAID scrub / backup windows to 02:00 - 05:00 UTC off-peak hours.")
            assumptions.append("Does not alter stored data volume, but significantly reduces peak queue contention.")

            counterfactual_q50 = list(baseline_q50)

        elif action_type == "REBALANCE_WORKLOAD":
            relocated_iops = float(parameters.get("relocated_iops_pct", 25.0))
            duration_minutes = 120.0
            estimated_cost_usd = 15.0
            overhead_penalty_pct = 5.0
            assumptions.append(f"Migrates noisy database tenant partitions ({relocated_iops}% I/O load) to adjacent pool.")
            assumptions.append("Requires 2 hours non-disruptive LUN remapping.")

            # Modest capacity adjustment
            reduction_factor = 1.0 - (relocated_iops / 100.0) * 0.15
            for val in baseline_q50:
                counterfactual_q50.append(round(val * reduction_factor, 2))

        else:
            raise ValueError(f"Unknown action type: {action_type}")

        # Final Hard Safety Envelope Verification
        final_used = counterfactual_q50[-1] if counterfactual_q50 else baseline_q50[-1]
        utilization_after = (final_used / total_capacity) * 100.0
        
        if utilization_after >= critical_pct:
            violations.append(f"End-of-horizon utilization ({round(utilization_after, 1)}%) exceeds hard critical limit ({critical_pct}%).")

        passed = len(violations) == 0

        # Residual risk calculation (0.0 = safe, 1.0 = critical danger)
        if passed:
            residual_risk = max(0.05, min(0.65, (utilization_after / critical_pct) * 0.5))
        else:
            residual_risk = 0.95

        return {
            "scenario_id": f"sim-{action_type.lower()}-{int(datetime.now(timezone.utc).timestamp())}",
            "device_id": device_id,
            "action_type": action_type,
            "parameters": parameters,
            "duration_minutes": duration_minutes,
            "estimated_cost_usd": estimated_cost_usd,
            "overhead_io_penalty_pct": overhead_penalty_pct,
            "safety_envelope_passed": passed,
            "violation_reasons": violations,
            "residual_risk_score": round(residual_risk, 3),
            "assumptions": assumptions,
            "timeline_timestamps": timestamps,
            "baseline_q50": baseline_q50,
            "counterfactual_q50": counterfactual_q50,
            "hard_limit": hard_limit,
            "is_simulated_estimate": True
        }
