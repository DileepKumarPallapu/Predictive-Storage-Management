# AEGISSTOR JURASSIC — Scenario Catalog & Disturbance Taxonomy
**Milestone**: AEGISSTOR JURASSIC (Prompt 7.0)  

---

## 1. Catalog Overview

The Jurassic Resilience Lab includes six standard preconfigured scenarios covering the primary failure modes of enterprise storage tiers. Each scenario is deterministic, reproducible, and verifiable.

---

## 2. Preconfigured Scenarios

### Scenario 01: Sudden Write Burst & Rapid Growth Shock
- **Scenario ID**: `scenario-jurassic-cap-burst-01`
- **Family**: `CAPACITY_DISTURBANCE`
- **Target Volume**: `vol-nvme-tier1-db` (Production NVMe OLTP)
- **Starting Capacity**: 72.0%
- **Growth Rate**: Surges from 45.0 GB/day to 180.0 GB/day
- **Disturbance Details**:
  * Injects three consecutive 250 GB database table-dump bursts at hours 36, 42, and 48.
  * Organic daily growth quadruples, challenging the quantile regression engine.
- **Expected System Response**:
  * Forecast engine detects accelerated trajectory.
  * Transitions to `STATE_3_MODEL_UNRELIABLE` at hour 42 as conformal interval bounds are breached.
  * Proactive tier migration is recommended before critical 90% threshold trip.

---

### Scenario 02: Flash Controller TRIM/GC Saturation Storm
- **Scenario ID**: `scenario-jurassic-perf-gc-storm-02`
- **Family**: `PERFORMANCE_DISTURBANCE`
- **Target Volume**: `vol-nvme-tier1-db`
- **Starting Capacity**: 82.5% (High capacity zone where flash GC kicks in)
- **Disturbance Details**:
  * Bulk delete at hour 24 triggers massive asynchronous flash block erasure.
  * Injects `RESOURCE_SATURATION_SPIKE` fault at hour 30 for 18 hours.
  * Write IOPS jumps to 24,000, inflating P95 tail latency above 30.0ms.
- **Expected System Response**:
  * Performance risk engine detects SLA violation ($T_{\text{lat}} > 15.0\text{ms}$).
  * QoS rate limiting is recommended; rebalancing bandwidth is throttled to prevent compounding controller queue depth.

---

### Scenario 03: Diurnal Phase Inversion & Unseen Batch Shift
- **Scenario ID**: `scenario-jurassic-temporal-phase-03`
- **Family**: `TEMPORAL_DISTURBANCE`
- **Target Volume**: `vol-sas-tier2-analytics` (Data Warehouse SAS)
- **Starting Capacity**: 68.0%
- **Disturbance Details**:
  * High-throughput Trino batch queries move from off-peak 02:00 AM into midday business peak (13:00).
  * Diurnal curve phase shifts by 180 degrees.
- **Expected System Response**:
  * Page-Hinkley test detects temporal distribution shift.
  * Forecasting expands conformal prediction bounds to accommodate midday variance without generating false alarm breach warnings.

---

### Scenario 04: Agent Network Partition & Heartbeat Blackout
- **Scenario ID**: `scenario-jurassic-telemetry-blackout-04`
- **Family**: `TELEMETRY_DISTURBANCE`
- **Target Volume**: `vol-nvme-tier1-db`
- **Starting Capacity**: 74.0%
- **Disturbance Details**:
  * Complete telemetry ingestion blackout for 20 hours (hours 40-60).
  * Followed by backlog catch-up with out-of-order packets.
- **Expected System Response**:
  * Immediate transition to `STATE_2_DEGRADED_EVIDENCE` upon missed heartbeats.
  * Automated migration dispatch is blocked; operator manual review requested.
  * Safe recovery at hour 60 without physical operation replay.

---

### Scenario 05: Compound Disaster (Growth + Latency Surge + Telemetry Loss)
- **Scenario ID**: `scenario-jurassic-compound-disaster-05`
- **Family**: `COMPOUND_DISTURBANCE`
- **Target Volume**: `vol-nvme-tier1-db`
- **Starting Capacity**: 78.0%
- **Disturbance Details**:
  * Combines 350 GB write spike + flash controller queue saturation + 30% telemetry packet loss.
- **Expected System Response**:
  * Multi-failure containment test.
  * Fallback manager transitions sequentially through `STATE_2_DEGRADED_EVIDENCE` and `STATE_3_MODEL_UNRELIABLE`.
  * Preserves host safety envelope throughout the disturbance.

---

### Scenario 06: Destination Saturation & Infeasible Action Stress Test
- **Scenario ID**: `scenario-jurassic-infeasible-rebalance-06`
- **Family**: `COMPOUND_DISTURBANCE`
- **Target Volume**: `vol-nvme-tier1-db`
- **Starting Capacity**: 86.0% (Approaching critical breach)
- **Disturbance Details**:
  * Candidate destination pool (`pool-sas-fast`) is pre-filled to 88% capacity.
  * Injects `INFEASIBLE_ACTION_ATTEMPT` fault at hour 36.
- **Expected System Response**:
  * Dual-sided safety envelope detects that migrating data to destination will breach destination ceiling ($>90\%$).
  * Planner transitions to `STATE_4_PLANNING_UNSAFE` with `REJECTED_UNSAFE_SECONDARY_BREACH`.
  * Emits critical administrator alarm for physical tier expansion instead of causing secondary outage.
