import math
import json
import random
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import JurassicScenario, Device
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("aegisstor.jurassic.scenario")

PRESET_SCENARIOS = [
    {
        "id": "scenario-jurassic-cap-burst-01",
        "name": "Sudden Write Burst & Rapid Growth Shock",
        "scenario_family": "CAPACITY_DISTURBANCE",
        "description": "Injects three consecutive 250 GB database table-dump bursts and quadruples organic daily growth rate from 45 GB to 180 GB/day.",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 101,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 72.0,
        "capacity_growth_gb_day": 180.0,
        "burst_events_json": json.dumps([
            {"hour": 36, "size_gb": 250.0, "reason": "Unplanned database bulk snapshot"},
            {"hour": 42, "size_gb": 250.0, "reason": "ETL table repartition dump"},
            {"hour": 48, "size_gb": 280.0, "reason": "Kafka consumer replay backlog"},
        ]),
        "read_iops_base": 14000.0,
        "write_iops_base": 18000.0,
        "latency_noise_ms": 1.2,
        "telemetry_drop_rate": 0.0,
        "telemetry_delay_s": 0,
        "chaos_faults_json": json.dumps([]),
        "is_preset": True,
    },
    {
        "id": "scenario-jurassic-perf-gc-storm-02",
        "name": "Flash Controller TRIM/GC Saturation Storm",
        "scenario_family": "PERFORMANCE_DISTURBANCE",
        "description": "Simulates flash controller write amplification, erase-block exhaustion, and concurrent RAID scrub driving P95 tail latency above 30ms.",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 202,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 82.5,
        "capacity_growth_gb_day": 50.0,
        "burst_events_json": json.dumps([
            {"hour": 24, "size_gb": 120.0, "reason": "Bulk delete triggering heavy asynchronous TRIM"},
        ]),
        "read_iops_base": 18000.0,
        "write_iops_base": 24000.0,
        "latency_noise_ms": 5.5,
        "telemetry_drop_rate": 0.0,
        "telemetry_delay_s": 0,
        "chaos_faults_json": json.dumps([
            {
                "hour": 30,
                "duration_hours": 18,
                "fault_type": "RESOURCE_SATURATION_SPIKE",
                "target_module": "RESILIENCE_TWIN",
                "expected_symptom": "P95 tail latency exceeds 25.0ms SLA",
                "recovery_condition": "TRIM queue flushes after 18h",
            }
        ]),
        "is_preset": True,
    },
    {
        "id": "scenario-jurassic-temporal-phase-03",
        "name": "Diurnal Phase Inversion & Unseen Batch Shift",
        "scenario_family": "TEMPORAL_DISTURBANCE",
        "description": "Shifts high-throughput analytical batch jobs from 02:00 AM off-peak into 13:00 peak transactional hours, challenging seasonal model assumptions.",
        "target_device_id": "vol-sas-tier2-analytics",
        "seed": 303,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 68.0,
        "capacity_growth_gb_day": 85.0,
        "burst_events_json": json.dumps([
            {"hour": 60, "size_gb": 400.0, "reason": "Midday corporate data refresh"},
        ]),
        "read_iops_base": 8500.0,
        "write_iops_base": 7000.0,
        "latency_noise_ms": 2.0,
        "telemetry_drop_rate": 0.0,
        "telemetry_delay_s": 0,
        "chaos_faults_json": json.dumps([]),
        "is_preset": True,
    },
    {
        "id": "scenario-jurassic-telemetry-blackout-04",
        "name": "Agent Network Partition & Heartbeat Blackout",
        "scenario_family": "TELEMETRY_DISTURBANCE",
        "description": "Simulates complete telemetry agent loss for 20 hours (hours 40-60) followed by delayed out-of-order burst delivery.",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 404,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 74.0,
        "capacity_growth_gb_day": 60.0,
        "burst_events_json": json.dumps([]),
        "read_iops_base": 12000.0,
        "write_iops_base": 9000.0,
        "latency_noise_ms": 0.8,
        "telemetry_drop_rate": 0.45,
        "telemetry_delay_s": 3600,
        "chaos_faults_json": json.dumps([
            {
                "hour": 40,
                "duration_hours": 20,
                "fault_type": "TELEMETRY_PAUSE",
                "target_module": "INGESTION_COLLECTOR",
                "expected_symptom": "No incoming heartbeats; telemetry is stale",
                "recovery_condition": "Ingestion recovers at hour 60 with backlog flush",
            }
        ]),
        "is_preset": True,
    },
    {
        "id": "scenario-jurassic-compound-disaster-05",
        "name": "Compound Disaster: Capacity Shock + Latency Surge + Telemetry Loss",
        "scenario_family": "COMPOUND_DISTURBANCE",
        "description": "Simultaneous triple failure: rapid write growth, flash GC tail latency spikes to 42ms, and 30% telemetry packet loss. Tests state degradation.",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 505,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 78.0,
        "capacity_growth_gb_day": 160.0,
        "burst_events_json": json.dumps([
            {"hour": 24, "size_gb": 350.0, "reason": "Compound spike A"},
            {"hour": 72, "size_gb": 400.0, "reason": "Compound spike B"},
        ]),
        "read_iops_base": 15000.0,
        "write_iops_base": 22000.0,
        "latency_noise_ms": 6.0,
        "telemetry_drop_rate": 0.30,
        "telemetry_delay_s": 1200,
        "chaos_faults_json": json.dumps([
            {
                "hour": 24,
                "duration_hours": 24,
                "fault_type": "TELEMETRY_PAUSE",
                "target_module": "INGESTION_COLLECTOR",
                "expected_symptom": "Partial agent outage during growth surge",
                "recovery_condition": "Restored at hour 48",
            },
            {
                "hour": 48,
                "duration_hours": 36,
                "fault_type": "RESOURCE_SATURATION_SPIKE",
                "target_module": "RESILIENCE_TWIN",
                "expected_symptom": "Controller latency exceeds 35ms",
                "recovery_condition": "Restored at hour 84",
            }
        ]),
        "is_preset": True,
    },
    {
        "id": "scenario-jurassic-infeasible-rebalance-06",
        "name": "Destination Saturation & Infeasible Action Stress Test",
        "scenario_family": "COMPOUND_DISTURBANCE",
        "description": "Source volume approaches critical 90% threshold while candidate destination pool is also constrained. Tests planner rejection of unsafe actions.",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 606,
        "simulation_duration_hours": 168,
        "initial_capacity_pct": 86.0,
        "capacity_growth_gb_day": 120.0,
        "burst_events_json": json.dumps([
            {"hour": 18, "size_gb": 300.0, "reason": "Database partition expansion"},
        ]),
        "read_iops_base": 13000.0,
        "write_iops_base": 14000.0,
        "latency_noise_ms": 1.5,
        "telemetry_drop_rate": 0.0,
        "telemetry_delay_s": 0,
        "chaos_faults_json": json.dumps([
            {
                "hour": 36,
                "duration_hours": 48,
                "fault_type": "INFEASIBLE_ACTION_ATTEMPT",
                "target_module": "ACTION_PLANNER",
                "expected_symptom": "Rebalancing violates destination capacity ceiling",
                "recovery_condition": "Operator manual volume expansion required",
            }
        ]),
        "is_preset": True,
    },
]

class ScenarioEngine:
    """
    Deterministic Scenario Generation Engine for AEGISSTOR Jurassic Lab.
    Generates physics-informed, reproducible synthetic stress-test telemetry
    for capacity, performance, temporal, telemetry, and compound disturbance regimes.
    """

    @classmethod
    def seed_presets_if_missing(cls, db: Session):
        """Idempotently seeds standard preset scenarios."""
        for p in PRESET_SCENARIOS:
            existing = db.query(JurassicScenario).filter(JurassicScenario.id == p["id"]).first()
            if not existing:
                db.add(JurassicScenario(**p))
        db.commit()

    @classmethod
    def generate_scenario_telemetry(
        cls,
        scenario: JurassicScenario,
        device: Device,
        start_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Deterministically produces chronological hourly telemetry for the scenario.
        Guarantees:
          - Deterministic repeatability: same seed + scenario.id produces exact same output.
          - Invariant: used_bytes >= 0 and free_bytes >= 0.
          - Physical flash controller coupling: latency inflates non-linearly when utilization > 80%.
        """
        rng = random.Random(scenario.seed + hash(scenario.id))
        if start_time is None:
            start_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(hours=scenario.simulation_duration_hours)

        total_bytes = device.total_capacity_bytes
        current_used_bytes = int(total_bytes * (scenario.initial_capacity_pct / 100.0))
        hourly_growth_bytes = int((scenario.capacity_growth_gb_day * (1024**3)) / 24.0)

        burst_map = {}
        if scenario.burst_events_json:
            try:
                bursts = json.loads(scenario.burst_events_json)
                for b in bursts:
                    burst_map[int(b["hour"])] = int(b["size_gb"] * (1024**3))
            except Exception as e:
                logger.warning(f"Error parsing burst_events_json: {e}")

        # Chaos faults mapping
        fault_map = {}
        if scenario.chaos_faults_json:
            try:
                faults = json.loads(scenario.chaos_faults_json)
                for f in faults:
                    h_start = int(f.get("hour", 0))
                    h_dur = int(f.get("duration_hours", 1))
                    f_type = f.get("fault_type", "")
                    for step in range(h_start, h_start + h_dur):
                        fault_map[step] = f_type
            except Exception as e:
                logger.warning(f"Error parsing chaos_faults_json: {e}")

        records = []
        for step in range(scenario.simulation_duration_hours):
            ts = start_time + timedelta(hours=step)
            hour_of_day = ts.hour

            # 1. Capacity dynamics
            active_fault = fault_map.get(step)
            burst_addition = burst_map.get(step, 0)
            
            # Growth modified by business diurnal curve (peak 10:00 to 18:00)
            diurnal_factor = 1.0 + 0.4 * math.sin((hour_of_day - 8) * math.pi / 12.0)
            step_growth = int(hourly_growth_bytes * max(0.2, diurnal_factor))

            current_used_bytes = min(total_bytes, current_used_bytes + step_growth + burst_addition)
            free_bytes = max(0, total_bytes - current_used_bytes)
            util_pct = round((current_used_bytes / total_bytes) * 100.0, 2)

            # 2. IOPS & Throughput dynamics
            iops_noise = rng.uniform(0.85, 1.15)
            read_iops = scenario.read_iops_base * max(0.3, diurnal_factor) * iops_noise
            write_iops = scenario.write_iops_base * max(0.3, diurnal_factor) * iops_noise

            if burst_addition > 0:
                write_iops *= 2.8

            throughput_mb_s = round(((read_iops * 32.0 + write_iops * 48.0) / 1024.0), 2)

            # 3. Queue Depth & P95 Tail Latency
            queue_depth = max(1.0, round((read_iops + write_iops) / 6000.0, 2))
            base_latency = 1.4 if "NVME" in device.tier else (6.5 if "SAS" in device.tier else 18.0)
            
            # Non-linear flash controller garbage collection penalty above 80% capacity
            gc_penalty = 0.0
            if util_pct > 80.0:
                gc_penalty = math.exp((util_pct - 80.0) / 4.5) * 1.5

            # Fault amplification
            fault_penalty = 0.0
            if active_fault == "RESOURCE_SATURATION_SPIKE":
                fault_penalty = 22.5
            elif active_fault == "INFEASIBLE_ACTION_ATTEMPT":
                fault_penalty = 8.0

            p95_latency = round(
                base_latency + (queue_depth * 0.4) + gc_penalty + fault_penalty + rng.uniform(-scenario.latency_noise_ms, scenario.latency_noise_ms),
                2
            )
            p95_latency = max(0.5, p95_latency)

            # 4. Telemetry availability / dropouts
            is_dropped = False
            drop_rate = scenario.telemetry_drop_rate if scenario.telemetry_drop_rate is not None else 0.0
            if active_fault == "TELEMETRY_PAUSE":
                is_dropped = True
            elif drop_rate > 0.0 and rng.random() < drop_rate:
                is_dropped = True

            records.append({
                "timestamp": ts,
                "step_hour": step,
                "device_id": device.id,
                "used_bytes": current_used_bytes,
                "free_bytes": free_bytes,
                "utilization_pct": util_pct,
                "read_iops": round(read_iops, 1),
                "write_iops": round(write_iops, 1),
                "throughput_mb_s": throughput_mb_s,
                "latency_p95_ms": p95_latency,
                "queue_depth": queue_depth,
                "is_synthetic": True,
                "is_telemetry_dropped": is_dropped,
                "active_fault": active_fault,
                "burst_addition_gb": round(burst_addition / (1024**3), 2),
            })

        return records
