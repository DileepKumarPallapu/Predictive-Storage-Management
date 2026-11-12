import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import numpy as np

from app.schemas.intelligence_contract import PerformanceRiskResult

class PerformanceRiskEngine:
    """
    Dedicated Storage Performance Risk Engine.
    Evaluates tail latency, queue depth contention, and capacity-latency coupling.
    """

    @classmethod
    def evaluate_performance_risk(
        cls,
        device_id: str,
        device_metadata: Dict[str, Any],
        telemetry_history: List[Dict[str, Any]],
        calibrated_latency_forecast: Optional[Dict[str, Any]] = None,
        evaluation_time: Optional[datetime] = None
    ) -> PerformanceRiskResult:
        if evaluation_time is None:
            evaluation_time = datetime.now(timezone.utc)

        reasons_for_inaccuracy = []

        # 1. Configured Storage Limits
        max_latency_ms = float(device_metadata.get("max_acceptable_latency_ms", 20.0))
        max_queue_depth = float(device_metadata.get("max_acceptable_queue_depth", 8.0))
        tier = device_metadata.get("tier", "NVME_TIER1")
        
        # Physical device bus limits
        if "NVME" in tier:
            max_iops = 150000.0
            max_throughput_mb_s = 3500.0
        elif "SAS" in tier:
            max_iops = 35000.0
            max_throughput_mb_s = 1200.0
        else:
            max_iops = 8000.0
            max_throughput_mb_s = 350.0

        if not telemetry_history:
            return cls._fallback_empty(
                device_id, max_latency_ms, max_queue_depth, max_iops, max_throughput_mb_s, evaluation_time
            )

        latest = telemetry_history[-1]
        current_lat_p95 = float(latest.get("latency_p95_ms") or 0.0)
        current_read_iops = float(latest.get("read_iops") or 0.0)
        current_write_iops = float(latest.get("write_iops") or 0.0)
        current_total_iops = current_read_iops + current_write_iops
        current_throughput = float(latest.get("throughput_mb_s") or 0.0)
        current_queue = float(latest.get("queue_depth") or 1.0)
        current_util = float(latest.get("utilization_pct") or 70.0)

        # Check for missing latency readings
        if current_lat_p95 <= 0.0:
            reasons_for_inaccuracy.append("P95 latency telemetry returned zero or unmeasured; fallback to empirical queue proxy.")
            current_lat_p95 = max(1.0, current_queue * 1.8)

        # 2. Capacity-Latency Coupling Physics:
        # Flash SSD / SAS arrays experience controller garbage collection (GC) and wear-leveling
        # stalls when free reserve drops below 20%, amplifying tail latency by up to 2.5x.
        coupling_penalty_ms = 0.0
        coupling_explanation = "Nominal storage reserve; flash controller garbage collection is unconstrained."
        if current_util > 80.0:
            excess_util = (current_util - 80.0) / 20.0  # 0.0 to 1.0
            coupling_penalty_ms = round(excess_util * 6.5, 2)
            coupling_explanation = (
                f"Elevated capacity utilization ({current_util}%) triggers controller TRIM/GC background overhead, "
                f"injecting an estimated +{coupling_penalty_ms}ms of tail latency inflation."
            )

        effective_p95_lat = current_lat_p95 + coupling_penalty_ms

        # 3. Queue Saturation Risk
        if current_queue >= max_queue_depth:
            queue_risk = "CRITICAL_SATURATION"
        elif current_queue >= max_queue_depth * 0.70:
            queue_risk = "ELEVATED_CONGESTION"
        else:
            queue_risk = "NOMINAL_QUEUING"

        # 4. Throughput Headroom
        throughput_headroom = max(0.0, 100.0 - (current_throughput / max_throughput_mb_s) * 100.0)

        # 5. Latency Breach Probability & Severity Assessment
        is_calibrated = False
        calib_method = "Empirical Queuing Delay Model"
        p_breach_24 = 0.0
        p_breach_72 = 0.0

        if calibrated_latency_forecast and "q50" in calibrated_latency_forecast:
            # Calibrated forecast exists
            is_calibrated = True
            calib_method = "LightGBM Conformal Quantile Extrapolation"
            q50 = calibrated_latency_forecast["q50"]
            q90 = calibrated_latency_forecast.get("q90", q50)
            
            # Check 24h
            idx_24 = min(23, len(q90) - 1)
            if q90[idx_24] >= max_latency_ms:
                p_breach_24 = 0.45 if q50[idx_24] < max_latency_ms else 0.85
            else:
                p_breach_24 = 0.08

            # Check 72h
            idx_72 = min(71, len(q90) - 1)
            if q90[idx_72] >= max_latency_ms:
                p_breach_72 = 0.60 if q50[idx_72] < max_latency_ms else 0.92
            else:
                p_breach_72 = 0.12
        else:
            # Empirical uncalibrated severity score
            is_calibrated = False
            ratio = effective_p95_lat / max_latency_ms
            p_breach_24 = round(min(0.95, max(0.02, ratio ** 2.2 * 0.35)), 3)
            p_breach_72 = round(min(0.98, max(0.05, ratio ** 1.8 * 0.50)), 3)
            reasons_for_inaccuracy.append(
                "Probabilities are derived from empirical queue heuristics, NOT calibrated forecast residuals."
            )

        # 6. Overall Latency Risk Level
        if effective_p95_lat >= max_latency_ms or queue_risk == "CRITICAL_SATURATION" or p_breach_24 >= 0.70:
            lat_risk_level = "CRITICAL"
        elif effective_p95_lat >= max_latency_ms * 0.75 or queue_risk == "ELEVATED_CONGESTION" or p_breach_72 >= 0.50:
            lat_risk_level = "ELEVATED"
        elif effective_p95_lat >= max_latency_ms * 0.50:
            lat_risk_level = "WARNING"
        else:
            lat_risk_level = "NOMINAL"

        return PerformanceRiskResult(
            device_id=device_id,
            evaluated_at=evaluation_time,
            current_latency_p95_ms=round(current_lat_p95, 2),
            max_acceptable_latency_ms=max_latency_ms,
            current_queue_depth=round(current_queue, 2),
            max_acceptable_queue_depth=max_queue_depth,
            current_total_iops=round(current_total_iops, 1),
            max_supported_iops=max_iops,
            current_throughput_mb_s=round(current_throughput, 2),
            max_bus_throughput_mb_s=max_throughput_mb_s,
            latency_risk_level=lat_risk_level,
            queue_saturation_risk=queue_risk,
            throughput_headroom_pct=round(throughput_headroom, 1),
            is_calibrated_probability=is_calibrated,
            estimated_violation_probability_24h=p_breach_24,
            estimated_violation_probability_72h=p_breach_72,
            calibration_method=calib_method,
            capacity_latency_coupling_penalty_ms=coupling_penalty_ms,
            coupling_explanation=coupling_explanation,
            reasons_for_potential_inaccuracy=reasons_for_inaccuracy
        )

    @classmethod
    def _fallback_empty(
        cls,
        device_id: str,
        max_lat: float,
        max_q: float,
        max_iops: float,
        max_tp: float,
        eval_time: datetime
    ) -> PerformanceRiskResult:
        return PerformanceRiskResult(
            device_id=device_id,
            evaluated_at=eval_time,
            current_latency_p95_ms=1.5,
            max_acceptable_latency_ms=max_lat,
            current_queue_depth=1.0,
            max_acceptable_queue_depth=max_q,
            current_total_iops=1000.0,
            max_supported_iops=max_iops,
            current_throughput_mb_s=50.0,
            max_bus_throughput_mb_s=max_tp,
            latency_risk_level="NOMINAL",
            queue_saturation_risk="NOMINAL_QUEUING",
            throughput_headroom_pct=95.0,
            is_calibrated_probability=False,
            estimated_violation_probability_24h=0.01,
            estimated_violation_probability_72h=0.05,
            calibration_method="Heuristic Default",
            capacity_latency_coupling_penalty_ms=0.0,
            coupling_explanation="No telemetry available to assess performance coupling.",
            reasons_for_potential_inaccuracy=["Telemetry history is absent; default nominal ratings applied."]
        )
