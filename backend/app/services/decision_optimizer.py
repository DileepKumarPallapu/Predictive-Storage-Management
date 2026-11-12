from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.ml.champion_challenger import ChampionChallengerEngine
from app.models.entities import Device, Telemetry
from app.services.data_reliability_engine import DataReliabilityEngine


class DecisionOptimizer:
    """
    Constrained Storage Intervention Optimizer.
    Evaluates candidate actions against explicit operational constraints:
      - budget_usd (checked only when unit costs are provided!)
      - max_utilization_pct
      - min_free_space_pct
      - max_latency_ms
      - max_transfer_gb
      - decision_horizon_days
    Never invents dollar prices when unit cost parameters are absent.
    """

    @classmethod
    def optimize(
        cls,
        db: Session,
        storage_id: str,
        budget_usd: Optional[float] = None,
        max_utilization_pct: float = 85.0,
        min_free_space_pct: float = 15.0,
        max_latency_ms: float = 25.0,
        max_transfer_gb: Optional[float] = None,
        decision_horizon_days: int = 30,
        unit_costs: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage volume '{storage_id}' not found")

        latest = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if not latest:
            raise ValueError("No telemetry records available for optimization")

        reliability = DataReliabilityEngine.evaluate(db, storage_id, persist=False)
        total_gb = float(device.total_capacity_bytes) / (1024.0 ** 3)
        current_used_gb = float(latest.used_bytes) / (1024.0 ** 3)
        base_latency = float(latest.latency_p95_ms) if latest.latency_p95_ms is not None else None

        # Project baseline utilization at decision_horizon_days using Champion-Challenger if available, else linear telemetry slope
        projected_used_gb = current_used_gb
        projected_p90_gb = current_used_gb
        try:
            fc = ChampionChallengerEngine.generate_forecast(
                db, storage_id, horizon_days=decision_horizon_days, persist=False
            )
            if fc["series"]:
                projected_used_gb = float(fc["series"][-1]["p50_used_gb"])
                projected_p90_gb = float(fc["series"][-1]["p90_used_gb"])
        except Exception:
            rows = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == storage_id)
                .order_by(Telemetry.timestamp.asc())
                .all()
            )
            if len(rows) >= 2:
                span_d = max(0.05, (rows[-1].timestamp.replace(tzinfo=None) - rows[0].timestamp.replace(tzinfo=None)).total_seconds() / 86400.0)
                slope = ((rows[-1].used_bytes - rows[0].used_bytes) / (1024.0 ** 3)) / span_d
                projected_used_gb = max(0.0, min(total_gb, current_used_gb + slope * decision_horizon_days))
                projected_p90_gb = min(total_gb, projected_used_gb * 1.05)

        uc = unit_costs or {}

        candidates_spec: List[Dict[str, Any]] = [
            {
                "action_type": "NO_ACTION",
                "title": "Observe Without Intervention (Baseline)",
                "delta_total_gb": 0.0,
                "delta_used_gb": 0.0,
                "transfer_gb": 0.0,
                "latency_delta_ms": 0.0,
                "cost_formula": lambda: 0.0 if uc else None,
            },
            {
                "action_type": "COMPRESS_DEDUP",
                "title": "Enable Inline Compression & Deduplication (15% Footprint Reduction)",
                "delta_total_gb": 0.0,
                "delta_used_gb": -round(projected_used_gb * 0.15, 3),
                "transfer_gb": 0.0,
                "latency_delta_ms": 1.2,  # Slight CPU decode overhead
                "cost_formula": lambda: round(float(uc["dedup_compute_usd"]), 2) if "dedup_compute_usd" in uc else None,
            },
            {
                "action_type": "ARCHIVE_COLD",
                "title": "Archive Cold Objects (>90d) — 20% Capacity Reclaim",
                "delta_total_gb": 0.0,
                "delta_used_gb": -round(projected_used_gb * 0.20, 3),
                "transfer_gb": round(projected_used_gb * 0.20, 3),
                "latency_delta_ms": 2.5,  # Temporary scan overhead
                "cost_formula": lambda: (
                    round(projected_used_gb * 0.20 * float(uc["archive_usd_per_gb"]), 2)
                    if "archive_usd_per_gb" in uc
                    else None
                ),
            },
            {
                "action_type": "EXPAND_VOLUME",
                "title": "Expand Volume Pool by +25% Provisioned Capacity",
                "delta_total_gb": round(total_gb * 0.25, 3),
                "delta_used_gb": 0.0,
                "transfer_gb": 0.0,
                "latency_delta_ms": -0.3,
                "cost_formula": lambda: (
                    round(total_gb * 0.25 * float(uc["expand_usd_per_gb"]), 2)
                    if "expand_usd_per_gb" in uc
                    else None
                ),
            },
            {
                "action_type": "MIGRATE_WORKLOAD",
                "title": "Migrate Heavy Tenant Slice (25% Used) to Secondary Pool",
                "delta_total_gb": 0.0,
                "delta_used_gb": -round(projected_used_gb * 0.25, 3),
                "transfer_gb": round(projected_used_gb * 0.25, 3),
                "latency_delta_ms": 4.0,  # Temporary replication/cutover latency
                "cost_formula": lambda: (
                    round(projected_used_gb * 0.25 * float(uc["migration_usd_per_gb"]), 2)
                    if "migration_usd_per_gb" in uc
                    else None
                ),
            },
        ]

        feasible: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []

        for spec in candidates_spec:
            post_total_gb = max(1e-6, total_gb + spec["delta_total_gb"])
            post_used_gb = max(0.0, projected_used_gb + spec["delta_used_gb"])
            post_p90_gb = max(0.0, projected_p90_gb + spec["delta_used_gb"])
            post_util_pct = round((post_used_gb / post_total_gb) * 100.0, 2)
            post_p90_util_pct = round((post_p90_gb / post_total_gb) * 100.0, 2)
            post_free_pct = round(max(0.0, 100.0 - post_util_pct), 2)

            est_latency_ms = round(max(0.1, base_latency + spec["latency_delta_ms"]), 2) if base_latency is not None else None
            cost_val = spec["cost_formula"]()
            cost_status = "PROVIDED" if cost_val is not None else "Cost not provided"

            violations: List[str] = []
            binding: List[str] = []

            if post_util_pct > max_utilization_pct:
                violations.append(f"max_utilization_pct exceeded ({post_util_pct}% > {max_utilization_pct}%)")
            elif post_util_pct >= max_utilization_pct - 5.0:
                binding.append("max_utilization_pct (near ceiling)")

            if post_free_pct < min_free_space_pct:
                violations.append(f"min_free_space_pct violated ({post_free_pct}% < {min_free_space_pct}%)")
            elif post_free_pct <= min_free_space_pct + 5.0:
                binding.append("min_free_space_pct (near floor)")

            if est_latency_ms is not None:
                if est_latency_ms > max_latency_ms:
                    violations.append(f"max_latency_ms exceeded ({est_latency_ms}ms > {max_latency_ms}ms)")
                elif est_latency_ms >= max_latency_ms * 0.85:
                    binding.append("max_latency_ms")

            if max_transfer_gb is not None and spec["transfer_gb"] > max_transfer_gb:
                violations.append(f"max_transfer_gb exceeded ({spec['transfer_gb']} GB > {max_transfer_gb} GB)")

            if budget_usd is not None and cost_val is not None and cost_val > budget_usd:
                violations.append(f"budget_usd exceeded (${cost_val:.2f} > ${budget_usd:.2f})")

            # Deterministic preference score: lower post_util & lower P90 risk & lower cost (if known)
            rank_score = round(
                post_util_pct * 0.65
                + post_p90_util_pct * 0.35
                + ((cost_val or 0.0) * 0.01),
                3,
            )

            entry = {
                "action_type": spec["action_type"],
                "title": spec["title"],
                "feasible": len(violations) == 0,
                "rank_score": rank_score,
                "projected_post_action": {
                    "total_capacity_gb": round(post_total_gb, 3),
                    "used_gb": round(post_used_gb, 3),
                    "utilization_pct": post_util_pct,
                    "adverse_p90_utilization_pct": post_p90_util_pct,
                    "free_space_pct": post_free_pct,
                    "transfer_gb": spec["transfer_gb"],
                    "estimated_latency_ms": est_latency_ms if est_latency_ms is not None else "No latency baseline available",
                },
                "estimated_cost_usd": cost_val,
                "cost_status": cost_status,
                "binding_constraints": binding,
                "violation_reasons": violations,
            }

            if entry["feasible"]:
                feasible.append(entry)
            else:
                rejected.append(entry)

        feasible.sort(key=lambda x: x["rank_score"])
        recommended = feasible[0] if feasible else None

        return {
            "storage_id": storage_id,
            "decision_horizon_days": decision_horizon_days,
            "data_reliability_tier": reliability["reliability_tier"],
            "allow_high_confidence_recommendations": reliability["allow_high_confidence_recommendations"],
            "constraints": {
                "budget_usd": budget_usd,
                "max_utilization_pct": max_utilization_pct,
                "min_free_space_pct": min_free_space_pct,
                "max_latency_ms": max_latency_ms,
                "max_transfer_gb": max_transfer_gb,
                "unit_costs_supplied": bool(uc),
            },
            "recommended_option": recommended,
            "feasible_candidates": feasible,
            "rejected_candidates": rejected,
            "non_execution_notice": "Advisory optimization only; no physical storage operations or billing charges executed.",
        }
