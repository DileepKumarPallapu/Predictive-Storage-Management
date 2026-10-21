# AEGISSTOR — Operational Assumptions & Environmental Boundaries
**Document**: Operating Boundaries, Safety Invariants & Domain Assumptions  
**Phase**: Phase 1 (Operational Assumptions)  
**Status**: Formalized  

---

## 1. Domain Assumptions

1. **Storage Hierarchy Coherence**:
   - The storage environment contains distinct tiers with known media characteristics:
     - **Tier 1 (NVMe Flash)**: Low latency ($< 15.0\text{ ms}$), high IOPS, sensitive to queue saturation ($Q > 2.0$).
     - **Tier 2 (SAS Magnetic / Hybrid)**: Moderate latency ($< 30.0\text{ ms}$), high sequential bandwidth, lower IOPS cap.
     - **Tier 3 (Cold DR Storage)**: High capacity, high latency tolerance ($< 120.0\text{ ms}$), low throughput budget.
     - **Edge Cache (High Velocity NVMe)**: Streaming time-series buffer with circular FIFO eviction policies.

2. **Workload Predictability & Diurnal Cycles**:
   - Production business workloads exhibit diurnal periodicity corresponding to human operating hours ($09:00 - 18:00\text{ peak}$) and scheduled nightly batch/backup windows ($01:00 - 04:00$).
   - Capacity consumption follows a superposition of secular continuous growth and discrete step-changepoints (batch data ingestion, database compaction).

3. **Digital Twin Fidelity Assumptions**:
   - Pure-software Digital Twin simulates queue delay using power-law equation:
     $$L_{\text{sim}} \propto L_{\text{base}} \cdot (0.8 + Q^{1.3} \cdot 0.4)$$
   - The simulator assumes that throttling a workload's arrival rate linearly decreases its contributed queue depth component.
   - Out-of-distribution operating regimes (e.g., $Q > 16.0$ or severe NAND thermal throttling) require empirical calibration gating via Atlas.

---

## 2. Hard Safety Invariants

1. **Shadow Mode / Zero Host Mutations**:
   - By default, `SHADOW_MODE_ENABLED = True`.
   - Recommendations produced by the system are advisory proposals. Automated destructive modifications to real hardware partitions or block devices are disabled.

2. **Explicit Fallback Requirement**:
   - If predictive models detect distributional drift, or if simulator discrepancy exceeds allowable tolerance, or if no intervention can complete before breach, the system must **fail safe** by issuing:
     `INSUFFICIENT EVIDENCE OR NO FEASIBLE ACTION — MANUAL REVIEW REQUIRED`
