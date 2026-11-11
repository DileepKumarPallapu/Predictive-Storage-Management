import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import Device, Telemetry, OracleWorkload, OracleWorkloadTelemetry

class CapacityForensicsService:
    """
    AEGISSTOR ORACLE — Capacity Growth Forensics.
    Decomposes historical capacity consumption, quantifies growth velocity & acceleration,
    identifies step changepoints and compaction events, and reconciles observed vs residual trends.
    """

    @classmethod
    def analyze_capacity_growth(cls, db: Session, device_id: str, window_hours: int = 168) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # 1. Fetch aggregate telemetry points for device
        telemetry_rows = (
            db.query(Telemetry)
            .filter(
                Telemetry.device_id == device_id,
                Telemetry.timestamp >= cutoff
            )
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        if not telemetry_rows or len(telemetry_rows) < 2:
            # Fallback to most recent available telemetry if time drift or gap
            telemetry_rows = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == device_id)
                .order_by(Telemetry.timestamp.desc())
                .limit(window_hours)
                .all()
            )
            telemetry_rows.reverse()

        if not telemetry_rows or len(telemetry_rows) < 2:
            total_cap_gb = (device.total_capacity_bytes / (1024 ** 3)) if device else 1000.0
            crit_pct = device.critical_threshold_pct if device else 90.0
            return {
                "device_id": device_id,
                "status": "INSUFFICIENT_TELEMETRY",
                "message": "Fewer than 2 telemetry points recorded in selected window.",
                "window_hours": window_hours,
                "initial_used_gb": 0.0,
                "final_used_gb": 0.0,
                "net_growth_gb": 0.0,
                "growth_rate_gb_per_day": 0.0,
                "acceleration_gb_per_day2": 0.0,
                "growth_pattern": "STEADY",
                "changepoints_detected": [],
                "workload_contributions": [],
                "unattributed_residual_growth_gb": 0.0,
                "unattributed_share_pct": 0.0,
                "period_comparison": {},
                "reserve_runway_projection": {
                    "remaining_headroom_gb": 0.0,
                    "projected_days_to_breach": None,
                    "critical_threshold_pct": crit_pct
                },
                "data": None
            }

        first_point = telemetry_rows[0]
        last_point = telemetry_rows[-1]

        first_gb = first_point.used_bytes / (1024 ** 3)
        last_gb = last_point.used_bytes / (1024 ** 3)
        total_delta_gb = last_gb - first_gb

        elapsed_hours = max(1.0, (last_point.timestamp - first_point.timestamp).total_seconds() / 3600.0)
        growth_rate_gb_day = (total_delta_gb / elapsed_hours) * 24.0

        # 2. Acceleration calculation: compare 1st half vs 2nd half velocity
        half_idx = len(telemetry_rows) // 2
        mid_point = telemetry_rows[half_idx]
        mid_gb = mid_point.used_bytes / (1024 ** 3)

        first_half_hours = max(1.0, (mid_point.timestamp - first_point.timestamp).total_seconds() / 3600.0)
        second_half_hours = max(1.0, (last_point.timestamp - mid_point.timestamp).total_seconds() / 3600.0)

        v1_gb_day = ((mid_gb - first_gb) / first_half_hours) * 24.0
        v2_gb_day = ((last_gb - mid_gb) / second_half_hours) * 24.0
        acceleration_gb_day2 = v2_gb_day - v1_gb_day

        growth_pattern = "STEADY"
        if acceleration_gb_day2 > 5.0:
            growth_pattern = "ACCELERATING"
        elif acceleration_gb_day2 < -5.0:
            growth_pattern = "DECELERATING"

        # 3. Detect changepoints (sudden bursts >= 30GB in 1 hour, or negative drops >= 15GB)
        changepoints = []
        for i in range(1, len(telemetry_rows)):
            p_prev = telemetry_rows[i - 1]
            p_curr = telemetry_rows[i]
            step_delta_gb = (p_curr.used_bytes - p_prev.used_bytes) / (1024 ** 3)

            if step_delta_gb >= 30.0:
                changepoints.append({
                    "timestamp": p_curr.timestamp.isoformat(),
                    "type": "BURST_ALLOCATION",
                    "magnitude_gb": round(step_delta_gb, 2),
                    "note": f"Abrupt capacity surge (+{step_delta_gb:.1f} GB)"
                })
            elif step_delta_gb <= -15.0:
                changepoints.append({
                    "timestamp": p_curr.timestamp.isoformat(),
                    "type": "COMPACTION_DELETION",
                    "magnitude_gb": round(step_delta_gb, 2),
                    "note": f"Compaction/Deletion reclamation ({step_delta_gb:.1f} GB)"
                })

        # 4. Workload-specific growth contribution breakdown
        workloads = db.query(OracleWorkload).filter(OracleWorkload.target_device_id == device_id).all()
        workload_contributions = []
        sum_workload_growth_gb = 0.0

        for w in workloads:
            w_first = (
                db.query(OracleWorkloadTelemetry)
                .filter(OracleWorkloadTelemetry.workload_id == w.id, OracleWorkloadTelemetry.timestamp >= cutoff)
                .order_by(OracleWorkloadTelemetry.timestamp.asc())
                .first()
            )
            w_last = (
                db.query(OracleWorkloadTelemetry)
                .filter(OracleWorkloadTelemetry.workload_id == w.id, OracleWorkloadTelemetry.timestamp >= cutoff)
                .order_by(OracleWorkloadTelemetry.timestamp.desc())
                .first()
            )
            if not w_first:
                w_first = (
                    db.query(OracleWorkloadTelemetry)
                    .filter(OracleWorkloadTelemetry.workload_id == w.id)
                    .order_by(OracleWorkloadTelemetry.timestamp.asc())
                    .first()
                )
            if not w_last:
                w_last = (
                    db.query(OracleWorkloadTelemetry)
                    .filter(OracleWorkloadTelemetry.workload_id == w.id)
                    .order_by(OracleWorkloadTelemetry.timestamp.desc())
                    .first()
                )
            if w_first and w_last:
                w_delta_gb = (w_last.allocated_bytes - w_first.allocated_bytes) / (1024 ** 3)
                if w.attribution_available:
                    sum_workload_growth_gb += max(0.0, w_delta_gb)
                    workload_contributions.append({
                        "workload_id": w.id,
                        "workload_name": w.name,
                        "workload_type": w.workload_type,
                        "growth_delta_gb": round(w_delta_gb, 2),
                        "growth_share_pct": 0.0  # Normalized below
                    })

        unattributed_growth_gb = max(0.0, total_delta_gb - sum_workload_growth_gb)
        if total_delta_gb > 0:
            for wc in workload_contributions:
                wc["growth_share_pct"] = round((wc["growth_delta_gb"] / total_delta_gb) * 100.0, 1)

        # 5. Period comparison: Current window vs Previous equivalent window
        prev_cutoff = cutoff - timedelta(hours=window_hours)
        prev_first = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id, Telemetry.timestamp >= prev_cutoff)
            .order_by(Telemetry.timestamp.asc())
            .first()
        )
        prev_delta_gb = (first_gb - (prev_first.used_bytes / (1024 ** 3))) if prev_first else None

        # 6. Reserve runway estimate from growth rate
        total_capacity_gb = device.total_capacity_bytes / (1024 ** 3)
        critical_cap_gb = total_capacity_gb * (device.critical_threshold_pct / 100.0)
        remaining_headroom_gb = max(0.0, critical_cap_gb - last_gb)
        time_to_breach_days = (
            round(remaining_headroom_gb / growth_rate_gb_day, 1)
            if growth_rate_gb_day > 0.05 else None
        )

        return {
            "device_id": device_id,
            "device_name": device.name,
            "window_hours": window_hours,
            "initial_used_gb": round(first_gb, 2),
            "final_used_gb": round(last_gb, 2),
            "net_growth_gb": round(total_delta_gb, 2),
            "growth_rate_gb_per_day": round(growth_rate_gb_day, 2),
            "acceleration_gb_per_day2": round(acceleration_gb_day2, 2),
            "growth_pattern": growth_pattern,
            "changepoints_detected": changepoints,
            "workload_contributions": workload_contributions,
            "unattributed_residual_growth_gb": round(unattributed_growth_gb, 2),
            "unattributed_share_pct": round((unattributed_growth_gb / total_delta_gb) * 100.0, 1) if total_delta_gb > 0 else 0.0,
            "period_comparison": {
                "current_period_growth_gb": round(total_delta_gb, 2),
                "previous_period_growth_gb": round(prev_delta_gb, 2) if prev_delta_gb is not None else "N/A",
                "delta_pct_vs_previous": round(((total_delta_gb - prev_delta_gb) / prev_delta_gb) * 100.0, 1) if prev_delta_gb and prev_delta_gb > 0 else None
            },
            "reserve_runway_projection": {
                "remaining_headroom_gb": round(remaining_headroom_gb, 2),
                "projected_days_to_breach": time_to_breach_days,
                "critical_threshold_pct": device.critical_threshold_pct
            }
        }
