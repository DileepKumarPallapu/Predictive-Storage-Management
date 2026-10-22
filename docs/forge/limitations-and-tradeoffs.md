# AEGISSTOR FORGE — Limitations, Non-Goals & Engineering Trade-offs (Viva Guide)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-LIMIT-001  
**Integrity Standard:** Academic Transparency & Boundary Acknowledgment  

---

## 1. Transparent Technical Limitations

### 1. Simulated vs Physical Storage Mutation
- **Limitation:** In the default deployment, AEGISSTOR operates exclusively in simulation and recommendation mode.
- **Why this was chosen:** Running destructive disk operations against physical storage during academic evaluation or student workstations creates unacceptable risk of host data loss. All interventions are evaluated through verified physics sandboxes.

### 2. Environmental OS Disparity
- **Limitation:** The Linux block device collector (`/sys/block/*`) cannot run on native Windows development workstations.
- **Mitigation:** The system provides transparent runtime mode badges (`SYNTHETIC DEMO DATA`, `RECORDED REPLAY DATA`, `LIVE TELEMETRY`) and falls back cleanly without crashing.

### 3. Model Complexity vs Latency Trade-off
- **Limitation:** AEGISSTOR does not use deep sequence Transformers (e.g., PatchTST, TimesFM).
- **Justification:** Deep Transformer models require gigabytes of weights, multi-second inference latencies, and GPU accelerators. In storage resilience, fast edge execution ($<2\,\text{s}$) and lightweight federated updates ($2.05\,\text{KB}$) were prioritized.

### 4. Correlation vs Causation in Forensics
- **Limitation:** The Oracle workload attribution engine calculates statistical correlations between workload IOPS and device queue depths.
- **Honest Boundary:** Statistical attribution does not guarantee physical causation. Controlled counterfactual experiments provide directional hypotheses rather than absolute causal certainty.

---

## 2. Non-Goals

1. **Not a General Hardware Replacement:** AEGISSTOR is not a custom Linux block driver or filesystem; it is an intelligence and resilience platform operating above existing storage controllers.
2. **Not Unconditional Autopilot:** The system explicitly refrains from fully autonomous mitigations when uncertainty is elevated; it enforces a fail-closed human review fallback (`NO FEASIBLE AUTOMATED ACTION — MANUAL REVIEW REQUIRED`).
