import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import OracleWorkload, OracleWorkloadTelemetry, Device

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class WorkloadCatalogService:
    """
    Manages known enterprise workloads, their resource associations,
    and deterministic workload-level telemetry generation.
    """

    DEFAULT_WORKLOADS = [
        {
            "id": "wl-postgres-oltp",
            "name": "PostgreSQL Primary OLTP Engine",
            "target_device_id": "vol-nvme-tier1-db",
            "tier": "NVME_TIER1",
            "workload_type": "TRANSACTIONAL",
            "priority": "P0_CRITICAL",
            "sla_max_latency_ms": 15.0,
            "sla_min_throughput_mb_s": 120.0,
            "owner_team": "database-reliability@aegisstor.internal",
            "attribution_available": True,
            "description": "Primary transactional e-commerce core database. Highly sensitive to P95 tail latency contention.",
            "base_allocated_gb": 4200.0,
            "daily_growth_gb": 18.5,
            "read_ratio": 0.35,
            "base_iops": 9500.0,
        },
        {
            "id": "wl-analytics-batch",
            "name": "Corporate OLAP & Daily ETL Batch",
            "target_device_id": "vol-nvme-tier1-db",
            "tier": "NVME_TIER1",
            "workload_type": "BATCH_ETL",
            "priority": "P2_NORMAL",
            "sla_max_latency_ms": 45.0,
            "sla_min_throughput_mb_s": 250.0,
            "owner_team": "data-platform@aegisstor.internal",
            "attribution_available": True,
            "description": "Large-block nightly analytical transformations reading from Tier-1 and writing to Tier-2 SAS.",
            "base_allocated_gb": 1850.0,
            "daily_growth_gb": 14.2,
            "read_ratio": 0.65,
            "base_iops": 3200.0,
        },
        {
            "id": "wl-backup-snapshot",
            "name": "Snapshot DR & Archive Synchronizer",
            "target_device_id": "vol-cold-tier3-backup",
            "tier": "COLD_TIER3",
            "workload_type": "BACKUP",
            "priority": "P3_BACKGROUND",
            "sla_max_latency_ms": 120.0,
            "sla_min_throughput_mb_s": 80.0,
            "owner_team": "infrastructure-sre@aegisstor.internal",
            "attribution_available": True,
            "description": "Continuous and hourly deduplicated snapshot sync to remote disaster recovery cold storage.",
            "base_allocated_gb": 22000.0,
            "daily_growth_gb": 48.0,
            "read_ratio": 0.10,
            "base_iops": 1100.0,
        },
        {
            "id": "wl-edge-telemetry-sink",
            "name": "Edge Ingestion Buffer Stream",
            "target_device_id": "vol-edge-cache-01",
            "tier": "NVME_TIER1",
            "workload_type": "STREAMING",
            "priority": "P1_HIGH",
            "sla_max_latency_ms": 10.0,
            "sla_min_throughput_mb_s": 180.0,
            "owner_team": "iot-fleet@aegisstor.internal",
            "attribution_available": True,
            "description": "High-velocity streaming time-series ingest with circular write buffering.",
            "base_allocated_gb": 850.0,
            "daily_growth_gb": 6.5,
            "read_ratio": 0.20,
            "base_iops": 6800.0,
        },
        {
            "id": "wl-log-aggregator",
            "name": "Distributed Log Indexer & Audit",
            "target_device_id": "vol-sas-tier2-analytics",
            "tier": "SAS_TIER2",
            "workload_type": "BATCH_ETL",
            "priority": "P2_NORMAL",
            "sla_max_latency_ms": 30.0,
            "sla_min_throughput_mb_s": 90.0,
            "owner_team": "security-ops@aegisstor.internal",
            "attribution_available": True,
            "description": "Elastic index rotation and log compression pipeline on Tier-2 SAS.",
            "base_allocated_gb": 5800.0,
            "daily_growth_gb": 22.0,
            "read_ratio": 0.40,
            "base_iops": 2800.0,
        },
        {
            "id": "wl-unattributed-residual",
            "name": "Filesystem Overhead & Unattributed Storage",
            "target_device_id": "vol-nvme-tier1-db",
            "tier": "NVME_TIER1",
            "workload_type": "RESIDUAL",
            "priority": "P3_BACKGROUND",
            "sla_max_latency_ms": 100.0,
            "sla_min_throughput_mb_s": 0.0,
            "owner_team": "storage-sre@aegisstor.internal",
            "attribution_available": False,  # Explicitly flagged as unmeasured residual
            "description": "Filesystem journaling, superblock allocations, space reclamation residuals, and untagged tenant writes.",
            "base_allocated_gb": 350.0,
            "daily_growth_gb": 4.5,
            "read_ratio": 0.50,
            "base_iops": 450.0,
        }
    ]

    @classmethod
    def seed_workloads_if_missing(cls, db: Session) -> int:
        """
        Seeds workload catalog and historical attribution telemetry idempotently.
        """
        seeded = 0
        for w_def in cls.DEFAULT_WORKLOADS:
            existing = db.query(OracleWorkload).filter(OracleWorkload.id == w_def["id"]).first()
            if not existing:
                workload = OracleWorkload(
                    id=w_def["id"],
                    name=w_def["name"],
                    target_device_id=w_def["target_device_id"],
                    tier=w_def["tier"],
                    workload_type=w_def["workload_type"],
                    priority=w_def["priority"],
                    sla_max_latency_ms=w_def["sla_max_latency_ms"],
                    sla_min_throughput_mb_s=w_def["sla_min_throughput_mb_s"],
                    owner_team=w_def["owner_team"],
                    is_active=True,
                    attribution_available=w_def["attribution_available"],
                    description=w_def["description"]
                )
                db.add(workload)
                seeded += 1

        db.commit()

        # Seed telemetry traces if empty
        cls.seed_workload_telemetry_if_missing(db)
        return seeded

    @classmethod
    def seed_workload_telemetry_if_missing(cls, db: Session, hours: int = 168):
        """
        Generates 168 hours (7 days) of hourly deterministic workload telemetry.
        """
        count = db.query(OracleWorkloadTelemetry).count()
        if count > 0:
            return

        now = utc_now().replace(minute=0, second=0, microsecond=0)
        start_time = now - timedelta(hours=hours)

        telemetry_rows = []
        for w_def in cls.DEFAULT_WORKLOADS:
            w_id = w_def["id"]
            dev_id = w_def["target_device_id"]
            base_gb = w_def["base_allocated_gb"]
            growth_step_gb = w_def["daily_growth_gb"] / 24.0
            base_iops = w_def["base_iops"]
            read_ratio = w_def["read_ratio"]
            sla_lat = w_def["sla_max_latency_ms"]

            current_gb = base_gb
            for h in range(hours):
                step_time = start_time + timedelta(hours=h)
                hour_of_day = step_time.hour
                day_of_week = step_time.weekday()

                # Diurnal curve (peak 10:00 - 18:00)
                diurnal = 0.55 + 0.45 * math.sin((hour_of_day - 6) / 24.0 * 2.0 * math.pi)
                diurnal = max(0.2, min(1.2, diurnal))

                # Batch spikes (ETL runs between 01:00 and 04:00)
                if w_def["workload_type"] == "BATCH_ETL" and 1 <= hour_of_day <= 4:
                    diurnal *= 2.4

                # Snapshot backup runs Sunday morning
                if w_def["workload_type"] == "BACKUP" and day_of_week == 6 and 2 <= hour_of_day <= 6:
                    diurnal *= 2.8

                # Capacity growth increment with realistic noise
                current_gb += growth_step_gb * (0.8 + 0.4 * diurnal)
                allocated_bytes = current_gb * (1024 ** 3)

                # IOPS and throughput
                total_iops = base_iops * diurnal
                read_iops = total_iops * read_ratio
                write_iops = total_iops * (1.0 - read_ratio)

                avg_kb = 32.0 if w_def["tier"] == "NVME_TIER1" else 64.0
                read_bytes_sec = read_iops * avg_kb * 1024.0
                write_bytes_sec = write_iops * avg_kb * 1024.0

                # Queue depth approximation
                queue_depth = max(0.2, (total_iops / 10000.0) * 1.8)

                # Tail latency inflation under high queue depth
                lat_mult = 1.0 + (queue_depth ** 1.5) * 0.4
                latency_p95 = min(sla_lat * 2.5, (sla_lat * 0.25) * lat_mult)

                row = OracleWorkloadTelemetry(
                    workload_id=w_id,
                    device_id=dev_id,
                    timestamp=step_time,
                    allocated_bytes=allocated_bytes,
                    read_bytes_sec=read_bytes_sec,
                    write_bytes_sec=write_bytes_sec,
                    read_iops=read_iops,
                    write_iops=write_iops,
                    latency_p95_ms=round(latency_p95, 2),
                    avg_io_size_kb=avg_kb,
                    queue_depth=round(queue_depth, 2),
                    is_synthetic=True
                )
                telemetry_rows.append(row)

        db.bulk_save_objects(telemetry_rows)
        db.commit()

    @classmethod
    def list_workloads(cls, db: Session, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(OracleWorkload)
        if device_id:
            query = query.filter(OracleWorkload.target_device_id == device_id)
        workloads = query.all()

        results = []
        for w in workloads:
            # Query latest telemetry record
            latest_tel = (
                db.query(OracleWorkloadTelemetry)
                .filter(OracleWorkloadTelemetry.workload_id == w.id)
                .order_by(OracleWorkloadTelemetry.timestamp.desc())
                .first()
            )

            latest_metrics = {
                "allocated_gb": round(latest_tel.allocated_bytes / (1024 ** 3), 2) if latest_tel else 0.0,
                "read_iops": round(latest_tel.read_iops, 1) if latest_tel else 0.0,
                "write_iops": round(latest_tel.write_iops, 1) if latest_tel else 0.0,
                "throughput_mb_s": round((latest_tel.read_bytes_sec + latest_tel.write_bytes_sec) / (1024 ** 2), 2) if latest_tel else 0.0,
                "latency_p95_ms": latest_tel.latency_p95_ms if latest_tel else 0.0,
                "queue_depth": latest_tel.queue_depth if latest_tel else 0.0,
                "data_freshness_timestamp": latest_tel.timestamp.isoformat() if latest_tel else None
            }

            results.append({
                "id": w.id,
                "name": w.name,
                "target_device_id": w.target_device_id,
                "tier": w.tier,
                "workload_type": w.workload_type,
                "priority": w.priority,
                "sla_max_latency_ms": w.sla_max_latency_ms,
                "sla_min_throughput_mb_s": w.sla_min_throughput_mb_s,
                "owner_team": w.owner_team,
                "is_active": w.is_active,
                "attribution_available": w.attribution_available,
                "description": w.description,
                "latest_telemetry": latest_metrics
            })
        return results
