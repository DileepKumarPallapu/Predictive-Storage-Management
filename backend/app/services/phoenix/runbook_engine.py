"""
AEGISSTOR PHOENIX — Typed Runbook Generation Engine
Provides structured runbooks with pre-conditions, allowlisted steps, rollback procedures, and verification targets.
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import json
import uuid

from app.models.entities import PhoenixRunbook, PhoenixIncident
from app.utils.datetime_utils import utc_now


STANDARD_RUNBOOKS = [
    {
        "id": "rbk-capacity-throttle-rebalance",
        "name": "Predictive Capacity Quota & Snapshot Eviction Runbook",
        "version": "1.2.0",
        "category": "CAPACITY_EXHAUSTION",
        "description": "Progressively evicts expired shadow snapshots, adjusts tier ingest rate, and triggers cross-pool weight rebalancing.",
        "preconditions": [
            "Device status in ['WARNING', 'CRITICAL']",
            "Shadow mode verified enabled",
            "Device replication status in sync"
        ],
        "steps": [
            {
                "step_number": 1,
                "name": "Audit and Compact Shadow Snapshots",
                "action_type": "COMPACT_SHADOW_SNAPSHOTS",
                "timeout_seconds": 300,
                "parameters": {"target_reclaim_pct": 8.0, "preserve_retention_days": 7},
                "rollback_action": "NOOP_DIAGNOSTIC_SAMPLE"
            },
            {
                "step_number": 2,
                "name": "Adjust Workload Ingest Throttle",
                "action_type": "WORKLOAD_RATE_LIMIT",
                "timeout_seconds": 120,
                "parameters": {"throttle_factor": 0.85, "duration_minutes": 60},
                "rollback_action": "WORKLOAD_RATE_LIMIT"
            },
            {
                "step_number": 3,
                "name": "Rebalance Storage Pool Allocation Weights",
                "action_type": "POOL_WEIGHT_REBALANCE",
                "timeout_seconds": 600,
                "parameters": {"rebalance_ratio": 0.15, "destination_tier": "SAS_TIER2"},
                "rollback_action": "POOL_WEIGHT_REBALANCE"
            }
        ],
        "rollback_steps": [
            {
                "step_number": 1,
                "name": "Restore Ingest Throttle to Nominal",
                "action_type": "WORKLOAD_RATE_LIMIT",
                "parameters": {"throttle_factor": 1.0}
            }
        ],
        "safety_constraints": {
            "min_free_reserve_pct": 10.0,
            "max_latency_ms": 20.0
        },
        "verification_criteria": {
            "target_metric": "utilization_pct",
            "expected_reduction_pct": 5.0,
            "observation_window_hours": 24.0
        },
        "estimated_duration_minutes": 20,
        "is_automated": False
    },
    {
        "id": "rbk-latency-cache-prefetch",
        "name": "Read Cache Rebalance & Queue Depth Stabilization",
        "version": "1.1.0",
        "category": "LATENCY_SATURATION",
        "description": "Adjusts device read prefetch caching and optimizes queue depth thresholds to mitigate P95 latency spikes.",
        "preconditions": [
            "Device media_type in ['NVMe SSD', 'Enterprise SAS']",
            "P95 latency exceeding acceptable threshold"
        ],
        "steps": [
            {
                "step_number": 1,
                "name": "Sample Controller Queue Metrics",
                "action_type": "NOOP_DIAGNOSTIC_SAMPLE",
                "timeout_seconds": 60,
                "parameters": {"sample_interval_ms": 500, "sample_count": 10},
                "rollback_action": "NOOP_DIAGNOSTIC_SAMPLE"
            },
            {
                "step_number": 2,
                "name": "Reallocate Prefetch Read Cache",
                "action_type": "READ_CACHE_PREFETCH_REBALANCE",
                "timeout_seconds": 180,
                "parameters": {"cache_allocation_boost_pct": 25.0},
                "rollback_action": "READ_CACHE_PREFETCH_REBALANCE"
            },
            {
                "step_number": 3,
                "name": "Apply Dynamic Ingest Throttle",
                "action_type": "TIER_THROTTLE_ADJUSTMENT",
                "timeout_seconds": 120,
                "parameters": {"throttle_reduction_pct": 10.0},
                "rollback_action": "TIER_THROTTLE_ADJUSTMENT"
            }
        ],
        "rollback_steps": [
            {
                "step_number": 1,
                "name": "Reset Prefetch Cache Allocation",
                "action_type": "READ_CACHE_PREFETCH_REBALANCE",
                "parameters": {"cache_allocation_boost_pct": 0.0}
            }
        ],
        "safety_constraints": {
            "max_latency_ms": 20.0,
            "max_bandwidth_mb_s": 6400.0
        },
        "verification_criteria": {
            "target_metric": "latency_p95_ms",
            "expected_reduction_pct": 20.0,
            "observation_window_hours": 12.0
        },
        "estimated_duration_minutes": 15,
        "is_automated": False
    }
]


class RunbookEngine:
    """
    Manages runbook registry and synthesizes incident-specific action proposals.
    """

    @classmethod
    def seed_standard_runbooks(cls, db: Session) -> List[PhoenixRunbook]:
        runbooks = []
        for r_spec in STANDARD_RUNBOOKS:
            existing = db.query(PhoenixRunbook).filter(PhoenixRunbook.id == r_spec["id"]).first()
            if not existing:
                rb = PhoenixRunbook(
                    id=r_spec["id"],
                    name=r_spec["name"],
                    version=r_spec["version"],
                    category=r_spec["category"],
                    description=r_spec["description"],
                    preconditions_json=json.dumps(r_spec["preconditions"]),
                    steps_json=json.dumps(r_spec["steps"]),
                    rollback_steps_json=json.dumps(r_spec["rollback_steps"]),
                    safety_constraints_json=json.dumps(r_spec["safety_constraints"]),
                    verification_criteria_json=json.dumps(r_spec["verification_criteria"]),
                    estimated_duration_minutes=r_spec["estimated_duration_minutes"],
                    is_automated=r_spec["is_automated"],
                    is_active=True
                )
                db.add(rb)
                db.flush()
                runbooks.append(rb)
            else:
                runbooks.append(existing)
        db.commit()
        return runbooks

    @classmethod
    def select_runbook_for_incident(cls, db: Session, incident: PhoenixIncident) -> Optional[PhoenixRunbook]:
        cls.seed_standard_runbooks(db)
        # Find matching category
        rb = (
            db.query(PhoenixRunbook)
            .filter(
                PhoenixRunbook.category == incident.category,
                PhoenixRunbook.is_active == True
            )
            .first()
        )
        if not rb:
            rb = db.query(PhoenixRunbook).filter(PhoenixRunbook.is_active == True).first()
        return rb
