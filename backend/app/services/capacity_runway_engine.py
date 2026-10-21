import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import numpy as np

from app.schemas.intelligence_contract import (
    CapacityRunwayResult,
    ReliabilityStatus
)

class CapacityRunwayEngine:
    """
    Dedicated Capacity Reserve Runway and Breach Horizon Service.
    Integrates historical growth with calibrated forecast trajectories.
    """

    @classmethod
    def evaluate_runway(
        cls,
        device_id: str,
        total_capacity_bytes: int,
        telemetry_history: List[Dict[str, Any]],
        forecast_contract: Optional[Dict[str, Any]] = None,
        critical_threshold_pct: float = 90.0,
        warning_threshold_pct: float = 80.0,
        evaluation_time: Optional[datetime] = None
    ) -> CapacityRunwayResult:
        if evaluation_time is None:
            evaluation_time = datetime.now(timezone.utc)

        assumptions = [
            "Usable capacity bounds assume persistent storage pool volume allocation.",
            "Threshold crossing assumes continuity of workload patterns observed in historical training window."
        ]
        limitations = []

        # 1. Inspect History & Data Quality
        if not telemetry_history:
            return cls._fallback_insufficient_data(
                device_id, total_capacity_bytes, critical_threshold_pct, warning_threshold_pct, evaluation_time,
                "No historical telemetry records provided."
            )

        # Sort telemetry chronologically
        history_sorted = sorted(telemetry_history, key=lambda x: x["timestamp"])
        latest_record = history_sorted[-1]
        latest_ts = latest_record["timestamp"]
        if latest_ts.tzinfo is None:
            latest_ts = latest_ts.replace(tzinfo=timezone.utc)

        # Check data freshness (stale if > 3.0 hours without observation)
        time_since_last = (evaluation_time - latest_ts).total_seconds() / 3600.0
        is_stale = time_since_last > 3.0
        if is_stale:
            limitations.append(f"Telemetry is stale: latest observation is {round(time_since_last, 1)} hours old.")

        current_used = int(latest_record["used_bytes"])
        current_free = int(max(0, total_capacity_bytes - current_used))
        current_util_pct = round((current_used / float(total_capacity_bytes)) * 100.0, 2)
        crit_bytes = (critical_threshold_pct / 100.0) * total_capacity_bytes
        warn_bytes = (warning_threshold_pct / 100.0) * total_capacity_bytes

        # 2. Compute Historical Growth Rates
        used_series = [r["used_bytes"] for r in history_sorted]
        growth_1h = float(used_series[-1] - used_series[-2]) if len(used_series) >= 2 else 0.0
        growth_24h = float(used_series[-1] - used_series[-25]) if len(used_series) >= 25 else (growth_1h * 24.0)
        daily_growth_gb = round(growth_24h / (1024.0 ** 3), 2)

        # Coefficient of variation on hourly diffs
        if len(used_series) >= 24:
            hourly_diffs = np.diff(used_series[-72:])
            mean_diff = np.mean(hourly_diffs)
            std_diff = np.std(hourly_diffs)
            cv_diff = (std_diff / (abs(mean_diff) + 1e-5)) if mean_diff != 0 else 0.0
            is_unstable = cv_diff > 2.5
        else:
            is_unstable = False

        if is_unstable:
            limitations.append("High volatility detected in hourly write increments; linear projections may have wide error margins.")

        # 3. Check Immediate Threshold Violations
        if current_util_pct >= critical_threshold_pct:
            return CapacityRunwayResult(
                device_id=device_id,
                evaluated_at=evaluation_time,
                total_capacity_bytes=total_capacity_bytes,
                current_used_bytes=current_used,
                current_free_bytes=current_free,
                current_utilization_pct=current_util_pct,
                configured_critical_threshold_pct=critical_threshold_pct,
                configured_warning_threshold_pct=warning_threshold_pct,
                growth_rate_1h_bytes=growth_1h,
                growth_rate_24h_bytes=growth_24h,
                growth_rate_daily_gb=daily_growth_gb,
                estimated_runway_hours=0.0,
                runway_lower_bound_hours=0.0,
                runway_upper_bound_hours=0.0,
                earliest_breach_timestamp=latest_ts,
                breach_status="ALREADY_BREACHED",
                sensitivity_optimistic_hours=0.0,
                sensitivity_expected_hours=0.0,
                sensitivity_pessimistic_hours=0.0,
                reliability_status=ReliabilityStatus.ALREADY_BREACHED,
                is_runway_reliable=True,
                unreliability_reason="Storage volume has already exceeded configured critical reserve capacity.",
                assumptions=assumptions,
                limitations=limitations
            )

        # 4. Trajectory-Driven Breach Estimation
        estimated_runway = 999.0
        runway_lower = 999.0
        runway_upper = 999.0
        breach_ts = None
        used_trajectory = False

        if forecast_contract and "q50" in forecast_contract and len(forecast_contract["q50"]) > 0:
            used_trajectory = True
            q50 = forecast_contract["q50"]
            q90 = forecast_contract.get("q90", q50)
            q10 = forecast_contract.get("q10", q50)
            f_timestamps = forecast_contract.get("timestamps", [])

            # Check expected trajectory (q50)
            for idx, val in enumerate(q50):
                if val >= crit_bytes:
                    estimated_runway = float(idx + 1)
                    if idx < len(f_timestamps):
                        breach_ts = f_timestamps[idx]
                    break

            # Check pessimistic trajectory (q90)
            for idx, val in enumerate(q90):
                if val >= crit_bytes:
                    runway_lower = float(idx + 1)
                    break

            # Check optimistic trajectory (q10)
            for idx, val in enumerate(q10):
                if val >= crit_bytes:
                    runway_upper = float(idx + 1)
                    break

        # 5. Extrapolation Beyond Forecast Window or Baseline Extrapolation
        if estimated_runway == 999.0:
            # Calculate average growth rate
            if len(used_series) >= 24:
                window_hours = min(len(used_series) - 1, 168)
                hourly_rate = float(used_series[-1] - used_series[-1 - window_hours]) / float(window_hours)
            else:
                hourly_rate = growth_1h

            if is_stale:
                rel_status = ReliabilityStatus.STALE_DATA
                is_reliable = False
                unrel_reason = limitations[0] if limitations else "Telemetry is stale."
                if hourly_rate <= 0:
                    breach_status = "ZERO_OR_NEGATIVE_GROWTH"
                    estimated_runway = 9999.0
                    runway_lower = 9999.0
                    runway_upper = 9999.0
                    sens_opt, sens_exp, sens_pess = 9999.0, 9999.0, 9999.0
                else:
                    headroom_bytes = crit_bytes - current_used
                    estimated_runway = round(headroom_bytes / max(1.0, hourly_rate), 1)
                    runway_lower = round(max(1.0, estimated_runway * 0.72), 1)
                    runway_upper = round(estimated_runway * 1.35, 1)
                    sens_opt = round(headroom_bytes / max(1.0, hourly_rate * 0.80), 1)
                    sens_exp = estimated_runway
                    sens_pess = round(headroom_bytes / max(1.0, hourly_rate * 1.30), 1)
                    breach_status = "ACTIVE_GROWTH_BREACH_ESTIMATE"
            elif hourly_rate <= 0:
                breach_status = "ZERO_OR_NEGATIVE_GROWTH"
                estimated_runway = 9999.0
                runway_lower = 9999.0
                runway_upper = 9999.0
                sens_opt = 9999.0
                sens_exp = 9999.0
                sens_pess = 9999.0
                rel_status = ReliabilityStatus.ZERO_OR_NEGATIVE_GROWTH
                is_reliable = False
                unrel_reason = "Net capacity growth is non-positive; runway is indefinitely safe under current operational conditions."
            else:
                headroom_bytes = crit_bytes - current_used
                extrapolated_hours = headroom_bytes / max(1.0, hourly_rate)
                base_hours = len(forecast_contract["q50"]) if used_trajectory else 0.0
                estimated_runway = round(base_hours + extrapolated_hours, 1)
                runway_lower = round(max(1.0, estimated_runway * 0.72), 1)
                runway_upper = round(estimated_runway * 1.35, 1)
                breach_status = "ACTIVE_GROWTH_BREACH_ESTIMATE"
                
                # Sensitivity analysis
                sens_opt = round(headroom_bytes / max(1.0, hourly_rate * 0.80), 1)
                sens_exp = estimated_runway
                sens_pess = round(headroom_bytes / max(1.0, hourly_rate * 1.30), 1)
                
                rel_status = ReliabilityStatus.STALE_DATA if is_stale else (
                    ReliabilityStatus.HIGH_VARIANCE_UNSTABLE if is_unstable else ReliabilityStatus.RELIABLE
                )
                is_reliable = not is_stale and not is_unstable
                unrel_reason = limitations[0] if limitations else None
        else:
            # Trajectory found breach inside prediction window
            breach_status = "FORECAST_HORIZON_BREACH"
            headroom_bytes = crit_bytes - current_used
            sens_opt = round(runway_upper if runway_upper != 999.0 else estimated_runway * 1.25, 1)
            sens_exp = estimated_runway
            sens_pess = round(runway_lower if runway_lower != 999.0 else estimated_runway * 0.80, 1)
            rel_status = ReliabilityStatus.STALE_DATA if is_stale else ReliabilityStatus.RELIABLE
            is_reliable = not is_stale
            unrel_reason = limitations[0] if limitations else None

        return CapacityRunwayResult(
            device_id=device_id,
            evaluated_at=evaluation_time,
            total_capacity_bytes=total_capacity_bytes,
            current_used_bytes=current_used,
            current_free_bytes=current_free,
            current_utilization_pct=current_util_pct,
            configured_critical_threshold_pct=critical_threshold_pct,
            configured_warning_threshold_pct=warning_threshold_pct,
            growth_rate_1h_bytes=growth_1h,
            growth_rate_24h_bytes=growth_24h,
            growth_rate_daily_gb=daily_growth_gb,
            estimated_runway_hours=estimated_runway,
            runway_lower_bound_hours=runway_lower,
            runway_upper_bound_hours=runway_upper,
            earliest_breach_timestamp=breach_ts,
            breach_status=breach_status,
            sensitivity_optimistic_hours=sens_opt,
            sensitivity_expected_hours=sens_exp,
            sensitivity_pessimistic_hours=sens_pess,
            reliability_status=rel_status,
            is_runway_reliable=is_reliable,
            unreliability_reason=unrel_reason,
            assumptions=assumptions,
            limitations=limitations
        )

    @classmethod
    def _fallback_insufficient_data(
        cls,
        device_id: str,
        total_capacity_bytes: int,
        critical_threshold_pct: float,
        warning_threshold_pct: float,
        evaluation_time: datetime,
        reason: str
    ) -> CapacityRunwayResult:
        return CapacityRunwayResult(
            device_id=device_id,
            evaluated_at=evaluation_time,
            total_capacity_bytes=total_capacity_bytes,
            current_used_bytes=0,
            current_free_bytes=total_capacity_bytes,
            current_utilization_pct=0.0,
            configured_critical_threshold_pct=critical_threshold_pct,
            configured_warning_threshold_pct=warning_threshold_pct,
            growth_rate_1h_bytes=0.0,
            growth_rate_24h_bytes=0.0,
            growth_rate_daily_gb=0.0,
            estimated_runway_hours=720.0,
            runway_lower_bound_hours=500.0,
            runway_upper_bound_hours=1000.0,
            earliest_breach_timestamp=None,
            breach_status="INSUFFICIENT_HISTORY",
            sensitivity_optimistic_hours=1000.0,
            sensitivity_expected_hours=720.0,
            sensitivity_pessimistic_hours=500.0,
            reliability_status=ReliabilityStatus.INSUFFICIENT_HISTORY,
            is_runway_reliable=False,
            unreliability_reason=reason,
            assumptions=["Insufficient observations to evaluate empirical trajectory."],
            limitations=[reason]
        )
