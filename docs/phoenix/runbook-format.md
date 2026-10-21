# AEGISSTOR PHOENIX — Typed Runbook Specification & Execution Format

## 1. Runbook Architecture
Every remediation runbook in AEGISSTOR PHOENIX is typed, declarative, and bounded by safety invariants. Runbooks cannot execute arbitrary shell scripts or destructive disk commands.

### Schema Structure
```json
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
  "is_automated": false
}
```

---

## 2. Allowlisted Action Types

| Action Type | Operational Behavior | Safe Simulation Effect | Permitted Modes |
|:---|:---|:---|:---|
| `COMPACT_SHADOW_SNAPSHOTS` | Evicts non-pinned shadow volume metadata and expired snapshots | Simulates 5–15% capacity reclaim without modifying physical blocks | `MODE_A_SIMULATE`, `MODE_B` |
| `WORKLOAD_RATE_LIMIT` | Throttles incoming tenant I/O ingest rate | Models reduction in queue depth and write throughput | `MODE_A_SIMULATE`, `MODE_B` |
| `POOL_WEIGHT_REBALANCE` | Shifts allocation weight to under-utilized pools | Simulates cross-pool data redistribution | `MODE_A_SIMULATE`, `MODE_B` |
| `READ_CACHE_PREFETCH_REBALANCE` | Adjusts prefetch cache buffer sizes | Simulates reduction in P95 read tail latency | `MODE_A_SIMULATE`, `MODE_B` |
| `TIER_THROTTLE_ADJUSTMENT` | Throttles back background scrubbing/tiering traffic | Reduces bus contention and restores OLTP priority | `MODE_A_SIMULATE`, `MODE_B` |
| `SIMULATED_DRAIN_REPLICA` | Drains replica placement from failing device | Validates pool capacity headroom before replica migration | `MODE_A_SIMULATE`, `MODE_B` |
| `NOOP_DIAGNOSTIC_SAMPLE` | High-frequency sampling of queue and controller counters | Read-only metric capture; zero state alteration | All Modes |
