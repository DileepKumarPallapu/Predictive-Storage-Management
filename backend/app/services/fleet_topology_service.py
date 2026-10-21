import json
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    Device, StorageSystem, StoragePool, ResourceRelationship, WorkloadDependency
)
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("aegisstor.fleet_topology")

# Seed configuration constants
DEFAULT_SYSTEMS = [
    {
        "id": "sys-flasharray-prime",
        "name": "Apex Titan AFA-800",
        "system_type": "ALL_FLASH_ARRAY",
        "vendor_family": "Enterprise All-Flash Array",
        "interconnect_type": "NVMe-oF / PCIe Gen4",
        "total_bus_bandwidth_mb_s": 12800.0,
        "max_iops_capacity": 1500000.0,
        "status": "HEALTHY",
    },
    {
        "id": "sys-hybrid-matrix",
        "name": "Matrix SAN Hybrid-400",
        "system_type": "HYBRID_SAN",
        "vendor_family": "Tiered SAN Array",
        "interconnect_type": "FC-32G dual-port",
        "total_bus_bandwidth_mb_s": 6400.0,
        "max_iops_capacity": 450000.0,
        "status": "HEALTHY",
    },
    {
        "id": "sys-archive-cluster",
        "name": "VaultStore Object & Cold Cluster",
        "system_type": "OBJECT_STORAGE_CLUSTER",
        "vendor_family": "Distributed Ceph / S3",
        "interconnect_type": "100GbE RoCE / S3 API",
        "total_bus_bandwidth_mb_s": 10000.0,
        "max_iops_capacity": 100000.0,
        "status": "HEALTHY",
    },
]

DEFAULT_POOLS = [
    {
        "id": "pool-nvme-ultra",
        "system_id": "sys-flasharray-prime",
        "name": "Pool 01 - Ultra NVMe Production",
        "tier": "NVME_TIER1",
        "redundancy_policy": "RAID10 (Dual Parity)",
        "total_raw_bytes": 16 * 1024 * 1024 * 1024 * 1024,
        "usable_capacity_bytes": 12 * 1024 * 1024 * 1024 * 1024,
        "allocated_bytes": 7 * 1024 * 1024 * 1024 * 1024,
        "overcommit_ratio": 1.15,
        "status": "HEALTHY",
    },
    {
        "id": "pool-sas-fast",
        "system_id": "sys-hybrid-matrix",
        "name": "Pool 02 - SAS Fast Analytics",
        "tier": "SAS_TIER2",
        "redundancy_policy": "RAID6 (8+2)",
        "total_raw_bytes": 80 * 1024 * 1024 * 1024 * 1024,
        "usable_capacity_bytes": 60 * 1024 * 1024 * 1024 * 1024,
        "allocated_bytes": 35 * 1024 * 1024 * 1024 * 1024,
        "overcommit_ratio": 1.05,
        "status": "HEALTHY",
    },
    {
        "id": "pool-backup-secondary",
        "system_id": "sys-hybrid-matrix",
        "name": "Pool 03 - Tier2 Backup Retention",
        "tier": "SAS_TIER2",
        "redundancy_policy": "RAID6 (8+2)",
        "total_raw_bytes": 150 * 1024 * 1024 * 1024 * 1024,
        "usable_capacity_bytes": 120 * 1024 * 1024 * 1024 * 1024,
        "allocated_bytes": 60 * 1024 * 1024 * 1024 * 1024,
        "overcommit_ratio": 1.0,
        "status": "HEALTHY",
    },
    {
        "id": "pool-hdd-cold",
        "system_id": "sys-archive-cluster",
        "name": "Pool 04 - High-Density Cold Archive",
        "tier": "HDD_ARCHIVE",
        "redundancy_policy": "Erasure Coding 8+4",
        "total_raw_bytes": 300 * 1024 * 1024 * 1024 * 1024,
        "usable_capacity_bytes": 220 * 1024 * 1024 * 1024 * 1024,
        "allocated_bytes": 170 * 1024 * 1024 * 1024 * 1024,
        "overcommit_ratio": 1.0,
        "status": "WARNING",
    },
]

DEFAULT_RELATIONSHIPS = [
    {
        "id": "rel-dev-nvme-to-pool",
        "source_id": "vol-nvme-tier1-db",
        "source_type": "DEVICE",
        "target_id": "pool-nvme-ultra",
        "target_type": "POOL",
        "relationship_type": "POOL_MEMBER",
        "provenance": "DISCOVERED",
        "confidence_score": 1.0,
        "contention_weight": 0.20,
        "metadata_json": json.dumps({"lba_mapping": "direct_nvme_ns1", "multipath": "active-active"}),
    },
    {
        "id": "rel-dev-sas-to-pool",
        "source_id": "vol-sas-tier2-analytics",
        "source_type": "DEVICE",
        "target_id": "pool-sas-fast",
        "target_type": "POOL",
        "relationship_type": "POOL_MEMBER",
        "provenance": "DISCOVERED",
        "confidence_score": 1.0,
        "contention_weight": 0.35,
        "metadata_json": json.dumps({"lba_mapping": "sas_lun_12", "stripe_size_kb": 256}),
    },
    {
        "id": "rel-dev-backup-to-pool",
        "source_id": "vol-backup-target",
        "source_type": "DEVICE",
        "target_id": "pool-backup-secondary",
        "target_type": "POOL",
        "relationship_type": "POOL_MEMBER",
        "provenance": "DISCOVERED",
        "confidence_score": 1.0,
        "contention_weight": 0.40,
        "metadata_json": json.dumps({"lba_mapping": "sas_lun_15", "compress_enabled": True}),
    },
    {
        "id": "rel-dev-hdd-to-pool",
        "source_id": "vol-hdd-archive",
        "source_type": "DEVICE",
        "target_id": "pool-hdd-cold",
        "target_type": "POOL",
        "relationship_type": "POOL_MEMBER",
        "provenance": "DISCOVERED",
        "confidence_score": 1.0,
        "contention_weight": 0.50,
        "metadata_json": json.dumps({"ceph_crush_rule": "replicated_hdd_rule"}),
    },
    {
        "id": "rel-shared-bus-sas-matrix",
        "source_id": "pool-sas-fast",
        "source_type": "POOL",
        "target_id": "pool-backup-secondary",
        "target_type": "POOL",
        "relationship_type": "SHARED_BUS_CONCURRENCY",
        "provenance": "DISCOVERED",
        "confidence_score": 1.0,
        "contention_weight": 0.65,
        "metadata_json": json.dumps({
            "shared_resource": "Matrix SAN Dual-Controller FC-32G Bus",
            "bus_bandwidth_mb_s": 6400.0,
            "contention_trigger": "concurrent_backup_and_etl_burst"
        }),
    },
    {
        "id": "rel-replication-nvme-backup",
        "source_id": "vol-nvme-tier1-db",
        "source_type": "DEVICE",
        "target_id": "vol-backup-target",
        "target_type": "DEVICE",
        "relationship_type": "REPLICATION_TARGET",
        "provenance": "USER_DEFINED",
        "confidence_score": 1.0,
        "contention_weight": 0.30,
        "metadata_json": json.dumps({
            "schedule": "01:00 UTC Daily Incremental Snapshot",
            "sync_mode": "asynchronous_delta"
        }),
    },
    {
        "id": "rel-tiering-sas-to-cold",
        "source_id": "vol-sas-tier2-analytics",
        "source_type": "DEVICE",
        "target_id": "vol-hdd-archive",
        "target_type": "DEVICE",
        "relationship_type": "TIERING_PARTNER",
        "provenance": "USER_DEFINED",
        "confidence_score": 0.95,
        "contention_weight": 0.25,
        "metadata_json": json.dumps({
            "policy": "Migrate data unread > 60 days to Cold Archive",
            "batch_window": "03:00 - 05:00 UTC"
        }),
    },
    {
        "id": "rel-inferred-pcie-concurrency",
        "source_id": "vol-nvme-tier1-db",
        "source_type": "DEVICE",
        "target_id": "vol-sas-tier2-analytics",
        "target_type": "DEVICE",
        "relationship_type": "SHARED_BUS_CONCURRENCY",
        "provenance": "INFERRED",
        "confidence_score": 0.78,
        "contention_weight": 0.35,
        "metadata_json": json.dumps({
            "inference_basis": "Cross-device IOPS cross-correlation r=0.72 during end-of-quarter batch runs",
            "shared_path": "PCIe Fabric Switch 02"
        }),
    },
]

DEFAULT_WORKLOADS = [
    {
        "id": "workload-ecommerce-checkout",
        "workload_name": "E-Commerce Checkout & Inventory Engine",
        "primary_device_id": "vol-nvme-tier1-db",
        "secondary_device_id": "vol-backup-target",
        "criticality": "MISSION_CRITICAL",
        "sla_max_latency_ms": 15.0,
        "sla_min_throughput_mb_s": 250.0,
        "io_pattern": "RANDOM_WRITE_DOMINANT",
        "cross_volume_lock": True,
    },
    {
        "id": "workload-corporate-bi",
        "workload_name": "Corporate BI / Trino Analytic Queries",
        "primary_device_id": "vol-sas-tier2-analytics",
        "secondary_device_id": "vol-hdd-archive",
        "criticality": "PRODUCTION",
        "sla_max_latency_ms": 30.0,
        "sla_min_throughput_mb_s": 350.0,
        "io_pattern": "READ_HEAVY",
        "cross_volume_lock": False,
    },
    {
        "id": "workload-dr-nightly-backup",
        "workload_name": "Nightly Cumulative DR Backup Stream",
        "primary_device_id": "vol-backup-target",
        "secondary_device_id": "vol-nvme-tier1-db",
        "criticality": "BATCH_ANALYTICS",
        "sla_max_latency_ms": 45.0,
        "sla_min_throughput_mb_s": 500.0,
        "io_pattern": "SEQUENTIAL_BURST",
        "cross_volume_lock": True,
    },
    {
        "id": "workload-media-archive",
        "workload_name": "Cold Media & Compliance Retention",
        "primary_device_id": "vol-hdd-archive",
        "secondary_device_id": None,
        "criticality": "COLD_ARCHIVE",
        "sla_max_latency_ms": 60.0,
        "sla_min_throughput_mb_s": 80.0,
        "io_pattern": "READ_HEAVY",
        "cross_volume_lock": False,
    },
]


class FleetTopologyService:
    """
    Fleet Topology & Multi-Pool Dependency Service for AEGISSTOR Omega.
    Maintains graph of storage systems, pools, devices, relationships, and workloads.
    """

    @classmethod
    def seed_fleet_topology_if_missing(cls, db: Session):
        """Idempotently seeds fleet storage systems, pools, relationships and workloads."""
        # 1. Storage systems
        for s in DEFAULT_SYSTEMS:
            if not db.query(StorageSystem).filter(StorageSystem.id == s["id"]).first():
                db.add(StorageSystem(**s))

        # 2. Storage pools
        for p in DEFAULT_POOLS:
            if not db.query(StoragePool).filter(StoragePool.id == p["id"]).first():
                db.add(StoragePool(**p))

        # 3. Associate devices with pools and systems
        device_pool_map = {
            "vol-nvme-tier1-db": ("pool-nvme-ultra", "sys-flasharray-prime"),
            "vol-sas-tier2-analytics": ("pool-sas-fast", "sys-hybrid-matrix"),
            "vol-backup-target": ("pool-backup-secondary", "sys-hybrid-matrix"),
            "vol-hdd-archive": ("pool-hdd-cold", "sys-archive-cluster"),
        }
        for dev_id, (p_id, sys_id) in device_pool_map.items():
            dev = db.query(Device).filter(Device.id == dev_id).first()
            if dev:
                dev.pool_id = p_id
                dev.system_id = sys_id

        # 4. Resource relationships
        for r in DEFAULT_RELATIONSHIPS:
            if not db.query(ResourceRelationship).filter(ResourceRelationship.id == r["id"]).first():
                db.add(ResourceRelationship(**r))

        # 5. Workload dependencies
        for w in DEFAULT_WORKLOADS:
            if not db.query(WorkloadDependency).filter(WorkloadDependency.id == w["id"]).first():
                db.add(WorkloadDependency(**w))

        db.commit()

    @classmethod
    def get_fleet_topology(cls, db: Session) -> Dict[str, Any]:
        """Returns full fleet graph representation including systems, pools, devices, edges, and dependencies."""
        cls.seed_fleet_topology_if_missing(db)

        systems = db.query(StorageSystem).all()
        pools = db.query(StoragePool).all()
        devices = db.query(Device).all()
        relationships = db.query(ResourceRelationship).all()
        workloads = db.query(WorkloadDependency).all()

        nodes = []
        for s in systems:
            nodes.append({
                "id": s.id,
                "label": s.name,
                "type": "SYSTEM",
                "tier": "INFRASTRUCTURE",
                "system_type": s.system_type,
                "interconnect": s.interconnect_type,
                "bandwidth_mb_s": s.total_bus_bandwidth_mb_s,
                "max_iops": s.max_iops_capacity,
                "status": s.status,
            })
        for p in pools:
            nodes.append({
                "id": p.id,
                "label": p.name,
                "type": "POOL",
                "tier": p.tier,
                "system_id": p.system_id,
                "redundancy": p.redundancy_policy,
                "usable_capacity_bytes": p.usable_capacity_bytes,
                "allocated_bytes": p.allocated_bytes,
                "overcommit_ratio": p.overcommit_ratio,
                "status": p.status,
            })
        for d in devices:
            nodes.append({
                "id": d.id,
                "label": d.name,
                "type": "DEVICE",
                "tier": d.tier,
                "media_type": d.media_type,
                "pool_id": d.pool_id,
                "system_id": d.system_id,
                "total_capacity_bytes": d.total_capacity_bytes,
                "status": d.status,
                "workload_profile": d.workload_profile,
            })

        edges = []
        for r in relationships:
            edges.append({
                "id": r.id,
                "source": r.source_id,
                "source_type": r.source_type,
                "target": r.target_id,
                "target_type": r.target_type,
                "relationship_type": r.relationship_type,
                "provenance": r.provenance,
                "confidence_score": r.confidence_score,
                "contention_weight": r.contention_weight,
                "metadata": json.loads(r.metadata_json) if r.metadata_json else {},
            })

        workload_list = []
        for w in workloads:
            workload_list.append({
                "id": w.id,
                "workload_name": w.workload_name,
                "primary_device_id": w.primary_device_id,
                "secondary_device_id": w.secondary_device_id,
                "criticality": w.criticality,
                "sla_max_latency_ms": w.sla_max_latency_ms,
                "sla_min_throughput_mb_s": w.sla_min_throughput_mb_s,
                "io_pattern": w.io_pattern,
                "cross_volume_lock": w.cross_volume_lock,
            })

        return {
            "summary": {
                "total_systems": len(systems),
                "total_pools": len(pools),
                "total_devices": len(devices),
                "total_relationships": len(relationships),
                "total_workloads": len(workloads),
            },
            "nodes": nodes,
            "edges": edges,
            "workloads": workload_list,
        }
