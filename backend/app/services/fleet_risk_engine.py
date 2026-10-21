import math
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.entities import Device, Telemetry, StoragePool, StorageSystem, ResourceRelationship, WorkloadDependency
from app.services.capacity_runway_engine import CapacityRunwayEngine
from app.services.performance_risk_engine import PerformanceRiskEngine

logger = logging.getLogger("aegisstor.fleet_risk")

class FleetRiskEngine:
    """
    Fleet-Wide Risk Aggregator for AEGISSTOR Omega.
    Evaluates:
      1. Aggregated fleet capacity & latency headroom.
      2. Correlated resource bottlenecks (shared bus contention, cross-pool saturation).
      3. Fleet Risk Budget & burn rate.
    """

    CRITICALITY_WEIGHTS = {
        "MISSION_CRITICAL": 3.0,
        "PRODUCTION": 2.0,
        "BATCH_ANALYTICS": 1.2,
        "COLD_ARCHIVE": 1.0,
    }

    @classmethod
    def evaluate_fleet_risk(cls, db: Session) -> Dict[str, Any]:
        """Calculates multi-device fleet risk posture, correlated bottlenecks, and fleet risk budget."""
        devices = db.query(Device).all()
        workloads = db.query(WorkloadDependency).all()
        workload_map = {w.primary_device_id: w for w in workloads}

        total_capacity_bytes = sum(d.total_capacity_bytes for d in devices)
        total_used_bytes = 0
        device_risk_summaries = []

        # Risk budget baseline
        FLEET_RISK_BUDGET_CAP = 100.0
        consumed_risk_points = 0.0

        for d in devices:
            latest_tel = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == d.id)
                .order_by(Telemetry.timestamp.desc())
                .first()
            )
            used_b = latest_tel.used_bytes if latest_tel else int(d.total_capacity_bytes * 0.7)
            util_pct = latest_tel.utilization_pct if latest_tel else 70.0
            total_used_bytes += used_b

            # Run capacity runway assessment and performance risk
            records = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == d.id)
                .order_by(Telemetry.timestamp.desc())
                .limit(168)
                .all()
            )
            records = list(reversed(records))
            telemetry_dicts = [
                {
                    "timestamp": r.timestamp,
                    "device_id": r.device_id,
                    "used_bytes": r.used_bytes,
                    "free_bytes": r.free_bytes,
                    "read_iops": r.read_iops,
                    "write_iops": r.write_iops,
                    "throughput_mb_s": r.throughput_mb_s,
                    "latency_p95_ms": r.latency_p95_ms,
                    "queue_depth": r.queue_depth,
                    "is_synthetic": r.is_synthetic
                }
                for r in records
            ]

            runway = CapacityRunwayEngine.evaluate_runway(
                device_id=d.id,
                total_capacity_bytes=d.total_capacity_bytes,
                telemetry_history=telemetry_dicts,
                critical_threshold_pct=d.critical_threshold_pct,
                warning_threshold_pct=d.warning_threshold_pct
            )

            perf = PerformanceRiskEngine.evaluate_performance_risk(
                device_id=d.id,
                device_metadata={
                    "max_acceptable_latency_ms": d.max_acceptable_latency_ms,
                    "tier": d.tier
                },
                telemetry_history=telemetry_dicts
            )

            runway_hours = runway.estimated_runway_hours
            breach_prob_72h = 1.0 if runway_hours < 72.0 else (0.85 if runway_hours < 168.0 else (0.25 if runway_hours < 336.0 else 0.05))
            p95_lat = perf.current_latency_p95_ms
            latency_breach_prob_24h = perf.estimated_violation_probability_24h

            # Determine risk level
            is_cap_breach = breach_prob_72h > 0.40 or runway_hours < 72.0
            is_perf_breach = latency_breach_prob_24h > 0.35
            
            if is_cap_breach and is_perf_breach:
                risk_level = "CRITICAL"
                raw_risk_score = 40.0
            elif is_cap_breach:
                risk_level = "ELEVATED"
                raw_risk_score = 25.0
            elif is_perf_breach:
                risk_level = "WARNING"
                raw_risk_score = 18.0
            else:
                risk_level = "NOMINAL"
                raw_risk_score = 5.0

            # Workload weighting
            wl = workload_map.get(d.id)
            crit = wl.criticality if wl else "PRODUCTION"
            crit_weight = cls.CRITICALITY_WEIGHTS.get(crit, 1.5)
            weighted_risk = raw_risk_score * crit_weight
            consumed_risk_points += weighted_risk

            device_risk_summaries.append({
                "device_id": d.id,
                "device_name": d.name,
                "tier": d.tier,
                "utilization_pct": round(util_pct, 2),
                "runway_hours": round(runway_hours, 1),
                "breach_prob_72h": round(breach_prob_72h, 3),
                "p95_latency_ms": round(p95_lat, 2),
                "latency_breach_prob_24h": round(latency_breach_prob_24h, 3),
                "risk_level": risk_level,
                "workload_criticality": crit,
                "weighted_risk_contribution": round(weighted_risk, 2),
            })

        fleet_util_pct = (total_used_bytes / total_capacity_bytes * 100.0) if total_capacity_bytes > 0 else 0.0

        # Correlated bottleneck detection
        correlated_bottlenecks = cls._detect_correlated_bottlenecks(db)

        # Correlated risk multiplier
        correlation_penalty = len(correlated_bottlenecks) * 8.5
        total_risk_score = round(min(100.0, (consumed_risk_points / 2.5) + correlation_penalty), 1)

        # Budget status
        if total_risk_score >= 80.0:
            budget_status = "BUDGET_EXCEEDED"
        elif total_risk_score >= 50.0:
            budget_status = "PRESSURE_ELEVATED"
        else:
            budget_status = "BALANCED"

        return {
            "fleet_metrics": {
                "total_devices": len(devices),
                "total_capacity_tb": round(total_capacity_bytes / (1024**4), 2),
                "total_used_tb": round(total_used_bytes / (1024**4), 2),
                "fleet_utilization_pct": round(fleet_util_pct, 2),
                "nominal_count": sum(1 for d in device_risk_summaries if d["risk_level"] == "NOMINAL"),
                "warning_count": sum(1 for d in device_risk_summaries if d["risk_level"] == "WARNING"),
                "elevated_count": sum(1 for d in device_risk_summaries if d["risk_level"] == "ELEVATED"),
                "critical_count": sum(1 for d in device_risk_summaries if d["risk_level"] == "CRITICAL"),
            },
            "fleet_risk_budget": {
                "max_budget_points": FLEET_RISK_BUDGET_CAP,
                "consumed_risk_points": round(total_risk_score, 1),
                "remaining_budget_points": round(max(0.0, FLEET_RISK_BUDGET_CAP - total_risk_score), 1),
                "budget_status": budget_status,
                "budget_burn_rate_points_per_day": 4.2,
                "recommended_action": "REBALANCE_CROSS_POOL" if total_risk_score > 60.0 else "CONTINUE_MONITORING"
            },
            "device_risks": device_risk_summaries,
            "correlated_bottlenecks": correlated_bottlenecks,
        }

    @classmethod
    def _detect_correlated_bottlenecks(cls, db: Session) -> List[Dict[str, Any]]:
        """Identifies active shared buses, co-located storage pools, and cross-volume lock contention."""
        relationships = (
            db.query(ResourceRelationship)
            .filter(ResourceRelationship.relationship_type.in_([
                "SHARED_BUS_CONCURRENCY", "REPLICATION_TARGET", "BACKUP_DEPENDENCY"
            ]))
            .all()
        )

        bottlenecks = []
        for r in relationships:
            if r.relationship_type == "SHARED_BUS_CONCURRENCY" and r.contention_weight >= 0.5:
                bottlenecks.append({
                    "id": f"bottleneck-{r.id}",
                    "type": "SHARED_CONTROLLER_BUS_CONTENTION",
                    "severity": "HIGH" if r.contention_weight > 0.6 else "MEDIUM",
                    "resource_a": r.source_id,
                    "resource_b": r.target_id,
                    "contention_coupling": r.contention_weight,
                    "impact_summary": (
                        f"Simultaneous peak I/O on {r.source_id} and {r.target_id} induces up to "
                        f"{int(r.contention_weight * 50)}% tail latency amplification on shared interconnect."
                    ),
                    "provenance": r.provenance,
                    "remedy": "Stagger backup execution window or enforce QoS IOPS rate-limit."
                })
            elif r.relationship_type == "REPLICATION_TARGET":
                bottlenecks.append({
                    "id": f"bottleneck-{r.id}",
                    "type": "SYNCHRONOUS_REPLICATION_LOCKING",
                    "severity": "MEDIUM",
                    "resource_a": r.source_id,
                    "resource_b": r.target_id,
                    "contention_coupling": r.contention_weight,
                    "impact_summary": (
                        f"Snapshot replication lock from {r.source_id} to {r.target_id} causes "
                        f"transient write queue depth elevation."
                    ),
                    "provenance": r.provenance,
                    "remedy": "Shift to asynchronous incremental snapshots with write-ahead delta logging."
                })

        return bottlenecks
