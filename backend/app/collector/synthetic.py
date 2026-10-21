import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

class SyntheticGenerator:
    """
    Deterministic enterprise storage telemetry generator.
    Produces physics-informed multi-tier storage traces with diurnal seasonality,
    burst I/O spikes, scrubbing jobs, queue contention, and realistic noise.
    
    Simulator Physics & Modeling Assumptions:
      1. Capacity Dynamics: Daily organic growth rate modified by diurnal activity multiplier
         and optional burst steps simulating large snapshot or ETL dumps.
      2. I/O Dynamics: Read/write IOPS follow diurnal business curves (09:00-19:00 peak)
         with stochastic variance.
      3. Throughput Physics: Proportional to IOPS * transfer size (32KB NVMe, 64KB SAS),
         saturating at physical bus bandwidth caps.
      4. Queue Depth: Approximates M/M/1 queueing delay under high concurrent arrival rates.
      5. P95 Tail Latency: Non-linear inflation when queue depth > 4.0 or utilization > 80%
         due to flash controller garbage collection (GC/TRIM) or disk head contention.
      6. Missing Telemetry: Intermittent dropouts simulating agent heartbeat loss.
    """

    SCENARIO_TYPES = [
        "NORMAL_OPERATION",
        "GRADUAL_GROWTH",
        "SUDDEN_BURST",
        "PERFORMANCE_DEGRADATION",
        "MIXED_RISK",
        "MISSING_TELEMETRY",
        "WORKLOAD_SHIFT"
    ]

    DEVICES_CONFIG = [
        {
            "id": "vol-nvme-tier1-db",
            "name": "Production E-Commerce OLTP NVMe",
            "tier": "NVME_TIER1",
            "media_type": "NVMe SSD (PCIe 4.0)",
            "total_capacity_bytes": 10 * 1024 * 1024 * 1024 * 1024,  # 10 TB
            "initial_used_pct": 0.70,
            "daily_growth_gb": 45.0,
            "burst_step_hours": [360, 520, 680],  # Injected write bursts
            "burst_gb": 120.0,
            "warning_threshold_pct": 80.0,
            "critical_threshold_pct": 90.0,
            "max_acceptable_latency_ms": 15.0,
            "min_free_reserve_pct": 10.0,
            "base_read_iops": 12000.0,
            "base_write_iops": 9000.0,
            "base_latency_ms": 1.4,
            "workload_profile": "OLTP E-Commerce Database",
            "default_scenario": "GRADUAL_GROWTH"
        },
        {
            "id": "vol-sas-tier2-analytics",
            "name": "Corporate Data Warehouse & ETL SAS",
            "tier": "SAS_TIER2",
            "media_type": "Enterprise SAS 15K",
            "total_capacity_bytes": 50 * 1024 * 1024 * 1024 * 1024,  # 50 TB
            "initial_used_pct": 0.65,
            "daily_growth_gb": 80.0,
            "burst_step_hours": [240, 480],
            "burst_gb": 350.0,
            "warning_threshold_pct": 80.0,
            "critical_threshold_pct": 90.0,
            "max_acceptable_latency_ms": 25.0,
            "min_free_reserve_pct": 10.0,
            "base_read_iops": 5000.0,
            "base_write_iops": 4000.0,
            "base_latency_ms": 6.5,
            "workload_profile": "Analytics Spark / Trino Batch",
            "default_scenario": "SUDDEN_BURST"
        },
        {
            "id": "vol-hdd-archive",
            "name": "Object & Media Archive Cold Pool",
            "tier": "HDD_ARCHIVE",
            "media_type": "High-Density SATA 7200 RPM",
            "total_capacity_bytes": 200 * 1024 * 1024 * 1024 * 1024,  # 200 TB
            "initial_used_pct": 0.84,
            "daily_growth_gb": 110.0,
            "burst_step_hours": [600],
            "burst_gb": 800.0,
            "warning_threshold_pct": 85.0,
            "critical_threshold_pct": 92.0,
            "max_acceptable_latency_ms": 40.0,
            "min_free_reserve_pct": 8.0,
            "base_read_iops": 1500.0,
            "base_write_iops": 1200.0,
            "base_latency_ms": 16.0,
            "workload_profile": "Cold Archival & Video Assets",
            "default_scenario": "MIXED_RISK"
        },
        {
            "id": "vol-backup-target",
            "name": "Secondary Veeam / SnapMirror Target",
            "tier": "SAS_TIER2",
            "media_type": "Hybrid Flash/SAS",
            "total_capacity_bytes": 100 * 1024 * 1024 * 1024 * 1024,  # 100 TB
            "initial_used_pct": 0.58,
            "daily_growth_gb": 130.0,
            "burst_step_hours": [],
            "burst_gb": 0.0,
            "warning_threshold_pct": 80.0,
            "critical_threshold_pct": 90.0,
            "max_acceptable_latency_ms": 30.0,
            "min_free_reserve_pct": 10.0,
            "base_read_iops": 2200.0,
            "base_write_iops": 6500.0,
            "base_latency_ms": 8.0,
            "workload_profile": "Nightly Cumulative Backup Target",
            "default_scenario": "NORMAL_OPERATION"
        }
    ]

    def __init__(self, seed: int = 42):
        self.seed = seed

    def generate_device_telemetry(
        self,
        device_cfg: Dict[str, Any],
        hours_history: int = 720,
        end_time: Optional[datetime] = None,
        scenario_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        rng = random.Random(self.seed + hash(device_cfg["id"]))
        if end_time is None:
            end_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        start_time = end_time - timedelta(hours=hours_history)

        active_scenario = scenario_type or device_cfg.get("default_scenario", "NORMAL_OPERATION")
        total_bytes = device_cfg["total_capacity_bytes"]
        used_bytes = int(total_bytes * device_cfg["initial_used_pct"])
        daily_growth_bytes = int(device_cfg["daily_growth_gb"] * 1024 * 1024 * 1024)
        hourly_growth_base = daily_growth_bytes / 24.0

        records = []
        for step in range(hours_history + 1):
            curr_time = start_time + timedelta(hours=step)
            hour_of_day = curr_time.hour
            day_of_week = curr_time.weekday()

            # Scenario: MISSING_TELEMETRY (simulate dropout gaps between step 400-406 and 610-614)
            if active_scenario == "MISSING_TELEMETRY" and (400 <= step <= 405 or 610 <= step <= 613):
                continue

            # Diurnal workload intensity curve
            diurnal_cycle = math.sin((hour_of_day - 6) / 24.0 * 2.0 * math.pi)
            activity_multiplier = 1.0 + 0.45 * diurnal_cycle
            if day_of_week >= 5:
                activity_multiplier *= 0.70 if "backup" not in device_cfg["id"] else 1.35

            # Workload intensity metric (0.5 to 2.5)
            workload_intensity = round(max(0.3, activity_multiplier * rng.uniform(0.9, 1.1)), 2)

            # Scenario: WORKLOAD_SHIFT (shifts from read-heavy to intensive write-heavy after step 450)
            if active_scenario == "WORKLOAD_SHIFT" and step > 450:
                activity_multiplier *= 1.4
                workload_intensity = round(workload_intensity * 1.5, 2)

            # Scenario: PERFORMANCE_DEGRADATION (injected queue contention after step 500)
            is_degraded = active_scenario in ["PERFORMANCE_DEGRADATION", "MIXED_RISK"] and step > 500

            # Growth dynamics
            growth_noise = rng.uniform(0.7, 1.3)
            current_hourly_growth = hourly_growth_base * activity_multiplier * growth_noise

            # Check burst steps or SUDDEN_BURST scenario
            if step in device_cfg.get("burst_step_hours", []) or (active_scenario == "SUDDEN_BURST" and step in [350, 500]):
                burst_bytes = int(device_cfg.get("burst_gb", 200.0) * 1024 * 1024 * 1024)
                current_hourly_growth += burst_bytes

            used_bytes = min(total_bytes, max(0, int(used_bytes + current_hourly_growth)))
            free_bytes = total_bytes - used_bytes
            utilization_pct = round((used_bytes / total_bytes) * 100.0, 2)

            # Performance dynamics
            read_mult = 0.4 if (active_scenario == "WORKLOAD_SHIFT" and step > 450) else 1.0
            write_mult = 2.2 if (active_scenario == "WORKLOAD_SHIFT" and step > 450) else 1.0

            read_iops = device_cfg["base_read_iops"] * activity_multiplier * read_mult * rng.uniform(0.88, 1.12)
            write_iops = device_cfg["base_write_iops"] * activity_multiplier * write_mult * rng.uniform(0.88, 1.12)
            total_iops = read_iops + write_iops

            avg_io_size_kb = 32.0 if "nvme" in device_cfg["id"] else 64.0
            throughput_mb_s = round((total_iops * avg_io_size_kb) / 1024.0, 2)

            # Queue depth physics
            queue_mult = 2.8 if is_degraded else 1.0
            queue_depth = max(1.0, round((total_iops / 4000.0) * queue_mult * rng.uniform(0.9, 1.2), 2))

            # Non-linear latency modeling
            capacity_pressure = max(1.0, (utilization_pct / 80.0) ** 2) if utilization_pct > 80.0 else 1.0
            latency_base = device_cfg["base_latency_ms"]
            latency_spike = (queue_depth * 0.4) if is_degraded else (queue_depth * 0.15)
            latency_p95 = round(latency_base * (1.0 + latency_spike) * capacity_pressure * rng.uniform(0.92, 1.12), 2)

            # Scrubbing events for SAS / HDD
            if hour_of_day in [2, 3] and ("sas" in device_cfg["id"] or "hdd" in device_cfg["id"]):
                latency_p95 = round(latency_p95 * rng.uniform(1.5, 2.2), 2)
                queue_depth = round(queue_depth * 1.6, 2)

            record = {
                "device_id": device_cfg["id"],
                "timestamp": curr_time,
                "used_bytes": used_bytes,
                "free_bytes": free_bytes,
                "utilization_pct": utilization_pct,
                "read_iops": round(read_iops, 1),
                "write_iops": round(write_iops, 1),
                "throughput_mb_s": throughput_mb_s,
                "latency_p95_ms": latency_p95,
                "queue_depth": queue_depth,
                "workload_intensity": workload_intensity,
                "telemetry_quality": "NOMINAL",
                "scenario_type": active_scenario,
                "is_synthetic": True,
                "source_label": "synthetic_generator_v1"
            }
            records.append(record)

        return records
