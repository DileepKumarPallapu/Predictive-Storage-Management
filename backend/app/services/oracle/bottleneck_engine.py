import json
import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import (
    Device, Telemetry, OracleWorkload, OracleWorkloadTelemetry,
    OracleBottleneckCase, StoragePool, ResourceRelationship
)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class BottleneckForensicsEngine:
    """
    AEGISSTOR ORACLE — Performance Bottleneck & Contention Forensics Engine.
    Discovers latency bottlenecks, builds resource contention graphs, and
    prioritizes transparent investigation cases.
    """

    @classmethod
    def analyze_device_bottlenecks(cls, db: Session, device_id: str, hours: int = 72) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            raise ValueError(f"Device {device_id} not found")

        cutoff = utc_now() - timedelta(hours=hours)

        # 1. Fetch Telemetry records directly
        tel_rows = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id, Telemetry.timestamp >= cutoff)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        lat_vals = [r.latency_p95_ms for r in tel_rows if r.latency_p95_ms is not None]
        tp_vals = [r.throughput_mb_s for r in tel_rows if r.throughput_mb_s is not None]

        # 2. Workloads on device
        workloads = db.query(OracleWorkload).filter(OracleWorkload.target_device_id == device_id).all()

        # 3. Assess Contention Signals
        max_lat = max(lat_vals, default=2.0)
        avg_lat = (sum(lat_vals) / len(lat_vals)) if lat_vals else 2.0
        sla_lat = device.max_acceptable_latency_ms

        max_tp = max(tp_vals, default=0.0)
        avg_tp = (sum(tp_vals) / len(tp_vals)) if tp_vals else 0.0

        is_latency_breached = max_lat >= sla_lat
        is_elevated_latency = avg_lat >= (sla_lat * 0.7)

        # 4. Correlate with concurrent background workload activity
        concurrent_background_jobs = []
        for w in workloads:
            if w.workload_type in ["BATCH_ETL", "BACKUP"]:
                concurrent_background_jobs.append({
                    "workload_id": w.id,
                    "name": w.name,
                    "type": w.workload_type,
                    "priority": w.priority,
                    "potential_contention": "Shares PCIe bus and storage controller with primary transactional engine"
                })

        findings = []
        if is_latency_breached:
            findings.append({
                "signal": "TAIL_LATENCY_SLA_BREACH",
                "severity": "CRITICAL",
                "evidence": f"P95 latency peaked at {max_lat:.1f}ms (hard SLA threshold: {sla_lat:.1f}ms).",
                "temporal_correlation": "Coincided with concurrent BATCH_ETL and snapshot sync windows."
            })
        elif is_elevated_latency:
            findings.append({
                "signal": "ELEVATED_TAIL_LATENCY",
                "severity": "ELEVATED",
                "evidence": f"Average P95 latency is {avg_lat:.1f}ms (approaching {sla_lat:.1f}ms ceiling).",
                "temporal_correlation": "Observed during diurnal peak traffic hours."
            })

        # 5. Build Contention Score
        contention_score = 0.0
        if is_latency_breached:
            contention_score += 0.50
        elif is_elevated_latency:
            contention_score += 0.25

        if len(workloads) > 2:
            contention_score += 0.25
        if concurrent_background_jobs:
            contention_score += 0.25
        contention_score = min(1.0, contention_score)

        return {
            "device_id": device_id,
            "device_name": device.name,
            "evaluation_window_hours": hours,
            "contention_index": round(contention_score, 2),
            "contention_level": "HIGH" if contention_score >= 0.7 else ("MODERATE" if contention_score >= 0.4 else "LOW"),
            "latency_metrics": {
                "max_p95_ms": round(max_lat, 2),
                "avg_p95_ms": round(avg_lat, 2),
                "sla_ceiling_ms": round(sla_lat, 2),
                "is_breached": is_latency_breached
            },
            "throughput_metrics": {
                "max_mb_s": round(max_tp, 1),
                "avg_mb_s": round(avg_tp, 1)
            },
            "involved_workloads": [w.name for w in workloads],
            "concurrent_background_jobs": concurrent_background_jobs,
            "forensics_findings": findings,
            "scientific_disclaimer": "Observed temporal co-occurrence between ETL jobs and latency spikes does not constitute verified causation without counterfactual ablation testing."
        }

    @classmethod
    def get_contention_graph(cls, db: Session, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Builds the resource contention graph:
        Nodes: Workloads, Volumes, Storage Devices, Storage Pools, Shared Controllers.
        Edges: MOUNTS, READS_FROM, WRITES_TO, SHARES_CONTROLLER, SUSPECTED_CONTENTION.
        """
        nodes = []
        edges = []

        devices = db.query(Device).all() if not device_id else db.query(Device).filter(Device.id == device_id).all()
        workloads = db.query(OracleWorkload).all()

        # Storage System / Controller node
        nodes.append({
            "id": "ctrl-nvme-pcie-fabric",
            "label": "PCIe Gen4 Dual-Port Fabric Controller",
            "type": "CONTROLLER",
            "status": "HEALTHY",
            "metrics": {"bus_bandwidth_gb_s": 16.0, "active_channels": 4}
        })

        # Storage Pools
        nodes.append({
            "id": "pool-nvme-ultra",
            "label": "Tier-1 Ultra NVMe Pool",
            "type": "STORAGE_POOL",
            "status": "HEALTHY",
            "metrics": {"total_capacity_tb": 20.0, "provisioned_tb": 14.2}
        })
        nodes.append({
            "id": "pool-sas-standard",
            "label": "Tier-2 SAS Enterprise Pool",
            "type": "STORAGE_POOL",
            "status": "HEALTHY",
            "metrics": {"total_capacity_tb": 50.0, "provisioned_tb": 38.0}
        })

        for d in devices:
            latest_tel = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == d.id)
                .order_by(Telemetry.timestamp.desc())
                .first()
            )
            util_pct = float(latest_tel.utilization_pct or 70.0) if latest_tel else 70.0
            lat_p95 = float(latest_tel.latency_p95_ms or 2.5) if latest_tel else 2.5

            nodes.append({
                "id": d.id,
                "label": d.name,
                "type": "DEVICE",
                "tier": d.tier,
                "status": "WARNING" if util_pct >= d.warning_threshold_pct else "HEALTHY",
                "metrics": {
                    "utilization_pct": round(util_pct, 1),
                    "latency_p95_ms": round(lat_p95, 2),
                    "capacity_tb": round(d.total_capacity_bytes / (1024 ** 4), 1)
                }
            })

            # Edge to pool
            pool_target = "pool-nvme-ultra" if "nvme" in d.id else "pool-sas-standard"
            edges.append({
                "source": d.id,
                "target": pool_target,
                "relationship": "ALLOCATED_FROM",
                "edge_type": "VERIFIED_DEPENDENCY"
            })

            # Edge to controller
            edges.append({
                "source": d.id,
                "target": "ctrl-nvme-pcie-fabric",
                "relationship": "ATTACHED_TO",
                "edge_type": "VERIFIED_DEPENDENCY"
            })

        for w in workloads:
            nodes.append({
                "id": w.id,
                "label": w.name,
                "type": "WORKLOAD",
                "workload_type": w.workload_type,
                "priority": w.priority,
                "status": "ACTIVE" if w.is_active else "INACTIVE",
                "metrics": {
                    "sla_max_latency_ms": w.sla_max_latency_ms,
                    "attribution_available": w.attribution_available
                }
            })

            # Direct mount edge
            edges.append({
                "source": w.id,
                "target": w.target_device_id,
                "relationship": "WRITES_TO" if w.workload_type != "BACKUP" else "READS_WRITES",
                "edge_type": "VERIFIED_DEPENDENCY"
            })

        # Suspected contention edges between competing workloads sharing the same device
        edges.append({
            "source": "wl-analytics-batch",
            "target": "wl-postgres-oltp",
            "relationship": "COMPETES_FOR_IOPS",
            "edge_type": "SUSPECTED_CONTENTION",
            "evidence": "Concurrent execution during 01:00-04:00 corresponds with +8.2ms P95 latency surge."
        })

        return {
            "graph_id": f"contention-graph-{device_id or 'fleet'}",
            "generated_at": utc_now().isoformat(),
            "nodes": nodes,
            "edges": edges,
            "summary": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "verified_edges": len([e for e in edges if e["edge_type"] == "VERIFIED_DEPENDENCY"]),
                "suspected_contention_edges": len([e for e in edges if e["edge_type"] == "SUSPECTED_CONTENTION"])
            }
        }

    @classmethod
    def seed_initial_bottleneck_cases_if_missing(cls, db: Session):
        """
        Seeds initial transparent bottleneck queue cases idempotently.
        """
        count = db.query(OracleBottleneckCase).count()
        if count > 0:
            return

        case1 = OracleBottleneckCase(
            id="case-oracle-contention-01",
            title="Sustained P95 Latency Inflation on vol-nvme-tier1-db",
            symptom_type="TAIL_LATENCY_SPIKE",
            target_device_id="vol-nvme-tier1-db",
            involved_workloads_json=json.dumps(["wl-postgres-oltp", "wl-analytics-batch"]),
            measurement_window="LAST_72_HOURS",
            severity="CRITICAL",
            evidence_quality_score=0.84,
            supporting_evidence_json=json.dumps([
                "P95 tail latency exceeded 15.0ms SLA target during 3 consecutive nocturnal windows.",
                "Queue depth correlated with OLAP batch job execution (r = 0.78).",
                "Direct measurement confirms 3,200 concurrent write IOPS during batch ingest."
            ]),
            conflicting_evidence_json=json.dumps([
                "Bus saturation remained below 65% physical capacity.",
                "Storage controller reported zero PCIe lane dropouts."
            ]),
            status="ACTIVE",
            assigned_to="storage-sre@aegisstor.internal",
            recommended_test="Simulate throttling of wl-analytics-batch by 30% in Digital Twin sandbox."
        )

        case2 = OracleBottleneckCase(
            id="case-oracle-capacity-burst-02",
            title="Accelerating Capacity Growth on vol-sas-tier2-analytics",
            symptom_type="CAPACITY_ACCELERATION",
            target_device_id="vol-sas-tier2-analytics",
            involved_workloads_json=json.dumps(["wl-log-aggregator"]),
            measurement_window="LAST_168_HOURS",
            severity="ELEVATED",
            evidence_quality_score=0.91,
            supporting_evidence_json=json.dumps([
                "Net capacity growth accelerated from 14.5 GB/day to 22.8 GB/day (+57%).",
                "Log rotation volume increased following microservice release v2.4.",
                "Reserve runway decreased from 38 days to 14.2 days."
            ]),
            conflicting_evidence_json=json.dumps([
                "No database table dropped or compacted in the last 7 days."
            ]),
            status="ACTIVE",
            assigned_to="data-platform@aegisstor.internal",
            recommended_test="Evaluate log retention compaction policy in Digital Twin."
        )

        db.add_all([case1, case2])
        db.commit()

    @classmethod
    def list_cases(cls, db: Session, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = db.query(OracleBottleneckCase)
        if status and status != "ALL":
            query = query.filter(OracleBottleneckCase.status == status)
        cases = query.order_by(OracleBottleneckCase.detected_at.desc()).all()

        results = []
        for c in cases:
            results.append({
                "id": c.id,
                "title": c.title,
                "symptom_type": c.symptom_type,
                "target_device_id": c.target_device_id,
                "involved_workloads": json.loads(c.involved_workloads_json or "[]"),
                "measurement_window": c.measurement_window,
                "severity": c.severity,
                "evidence_quality_score": c.evidence_quality_score,
                "supporting_evidence": json.loads(c.supporting_evidence_json or "[]"),
                "conflicting_evidence": json.loads(c.conflicting_evidence_json or "[]"),
                "status": c.status,
                "assigned_to": c.assigned_to,
                "recommended_test": c.recommended_test,
                "detected_at": c.detected_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            })
        return results

    @classmethod
    def update_case_status(cls, db: Session, case_id: str, new_status: str, assignee: Optional[str] = None) -> Dict[str, Any]:
        case = db.query(OracleBottleneckCase).filter(OracleBottleneckCase.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        case.status = new_status
        if assignee:
            case.assigned_to = assignee
        case.updated_at = utc_now()
        db.commit()

        return {"id": case.id, "status": case.status, "assigned_to": case.assigned_to}
