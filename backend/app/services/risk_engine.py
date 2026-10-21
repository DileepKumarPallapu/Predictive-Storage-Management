import math
from datetime import datetime, timezone
from typing import Dict, Any, List

class RiskEngine:
    """
    Computes capacity and latency breach probabilities, Reserve Runway,
    and granular risk factor attribution.
    """

    @classmethod
    def assess_device_risk(
        cls,
        device_id: str,
        device_meta: Dict[str, Any],
        forecast_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        total_capacity = float(device_meta["total_capacity_bytes"])
        crit_pct = float(device_meta.get("critical_threshold_pct", 90.0))
        warn_pct = float(device_meta.get("warning_threshold_pct", 80.0))
        crit_bytes = (crit_pct / 100.0) * total_capacity
        warn_bytes = (warn_pct / 100.0) * total_capacity

        timestamps = forecast_result["timestamps"]
        q10 = forecast_result["q10"]
        q50 = forecast_result["q50"]
        q90 = forecast_result["q90"]

        current_val = q50[0] if q50 else float(device_meta.get("current_used_bytes", total_capacity * 0.75))
        current_pct = round((current_val / total_capacity) * 100.0, 2)

        # 1. Compute Reserve Runway & Edge Case Status
        breach_status = "NOMINAL_HEADROOM"
        is_runway_reliable = True
        unreliability_reason = None

        if current_pct >= crit_pct:
            breach_status = "ALREADY_BREACHED"
            runway_estimate = 0.0
            runway_lower = 0.0
            runway_upper = 0.0
            risk_level = "CRITICAL"
        else:
            runway_estimate = 999.0
            runway_lower = 999.0
            runway_upper = 999.0

            for h, val in enumerate(q50, start=1):
                if val >= crit_bytes:
                    runway_estimate = float(h)
                    breach_status = "ACTIVE_GROWTH_BREACH_ESTIMATE"
                    break

            for h, val in enumerate(q90, start=1):
                if val >= crit_bytes:
                    runway_lower = float(h)
                    break

            for h, val in enumerate(q10, start=1):
                if val >= crit_bytes:
                    runway_upper = float(h)
                    break

            # If not breached in horizon window, inspect growth rate
            if runway_estimate == 999.0:
                if len(q50) > 1:
                    hourly_growth = (q50[-1] - q50[0]) / float(len(q50))
                    if hourly_growth <= 0:
                        breach_status = "ZERO_OR_NEGATIVE_GROWTH"
                        runway_estimate = 9999.0
                        runway_lower = 9999.0
                        runway_upper = 9999.0
                        is_runway_reliable = False
                        unreliability_reason = "Growth is zero or negative; runway is indefinitely safe under current workload."
                    else:
                        remaining_bytes = crit_bytes - q50[-1]
                        extra_hours = remaining_bytes / hourly_growth
                        runway_estimate = round(float(len(q50)) + extra_hours, 1)
                        runway_lower = round(max(1.0, runway_estimate * 0.75), 1)
                        runway_upper = round(runway_estimate * 1.35, 1)
                        breach_status = "ACTIVE_GROWTH_BREACH_ESTIMATE" if runway_estimate < 720.0 else "NOMINAL_HEADROOM"
                else:
                    breach_status = "INSUFFICIENT_HISTORY"
                    runway_estimate = 720.0
                    runway_lower = 500.0
                    runway_upper = 1000.0
                    is_runway_reliable = False
                    unreliability_reason = "Fewer than 2 observation points available to compute empirical trajectory."

        # 2. Breach probabilities
        # At 24h
        p_breach_24 = 0.0
        if len(q90) >= 24:
            if q10[23] >= crit_bytes:
                p_breach_24 = 0.99
            elif q50[23] >= crit_bytes:
                p_breach_24 = 0.65
            elif q90[23] >= crit_bytes:
                p_breach_24 = 0.22
            elif q90[23] >= warn_bytes:
                p_breach_24 = 0.08

        # At 72h
        p_breach_72 = 0.0
        idx_72 = min(71, len(q90) - 1)
        if q10[idx_72] >= crit_bytes:
            p_breach_72 = 0.98
        elif q50[idx_72] >= crit_bytes:
            p_breach_72 = 0.82
        elif q90[idx_72] >= crit_bytes:
            p_breach_72 = 0.45
        elif q90[idx_72] >= warn_bytes:
            p_breach_72 = 0.18

        # Latency breach probability
        current_lat = float(device_meta.get("current_latency_p95_ms", 2.0))
        max_lat = float(device_meta.get("max_acceptable_latency_ms", 20.0))
        p_lat_breach = round(min(0.95, max(0.01, (current_lat / max_lat) ** 2 * 0.25)), 3)

        # 3. Overall Risk Level
        if current_pct >= crit_pct or runway_lower <= 24.0 or p_breach_24 >= 0.50:
            risk_level = "CRITICAL"
        elif current_pct >= warn_pct or runway_estimate <= 72.0 or p_breach_72 >= 0.40:
            risk_level = "ELEVATED"
        elif runway_estimate <= 168.0:
            risk_level = "WARNING"
        else:
            risk_level = "NOMINAL"

        # 4. Risk Contributors Attribution
        contributors = []
        if current_pct >= warn_pct:
            contributors.append({
                "factor": f"High Base Capacity Utilization ({current_pct}%)",
                "impact_score": 0.55
            })
        if "nvme" in device_id:
            contributors.append({
                "factor": "Diurnal E-Commerce Transaction Write Bursts",
                "impact_score": 0.35
            })
        elif "sas" in device_id:
            contributors.append({
                "factor": "Analytical Batch Ingestion Growth",
                "impact_score": 0.30
            })
        elif "archive" in device_id:
            contributors.append({
                "factor": "Periodic RAID Parity Scrubbing Latency Injections",
                "impact_score": 0.40
            })
        else:
            contributors.append({
                "factor": "Nightly Cumulative Snapshot Retention",
                "impact_score": 0.25
            })

        return {
            "device_id": device_id,
            "computed_at": datetime.now(timezone.utc),
            "current_capacity_pct": current_pct,
            "runway_hours_estimate": round(runway_estimate, 1),
            "runway_hours_lower_bound": round(runway_lower, 1),
            "runway_hours_upper_bound": round(runway_upper, 1),
            "risk_level": risk_level,
            "breach_status": breach_status,
            "is_runway_reliable": is_runway_reliable,
            "unreliability_reason": unreliability_reason,
            "capacity_breach_prob_24h": round(p_breach_24, 3),
            "capacity_breach_prob_72h": round(p_breach_72, 3),
            "latency_breach_prob_24h": p_lat_breach,
            "risk_contributors": contributors
        }
