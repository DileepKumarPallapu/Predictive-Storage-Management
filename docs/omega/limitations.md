# AEGISSTOR OMEGA — System Limitations & Boundary Conditions
**Milestone**: AEGISSTOR OMEGA (Prompt 6.0)  

---

## 1. Overview & Non-Claim Boundaries

In accordance with rigorous academic and engineering standards, this document explicitly records the design assumptions, modeling simplifications, and known operational boundaries of AEGISSTOR Omega. 

**AEGISSTOR Omega does not claim**:
- General artificial intelligence for storage hardware diagnosis.
- Universal optimality across unmodeled proprietary SAN microcode fabrics.
- Zero-error forecasting on non-stationary, regime-shifting external cyberattacks (e.g. ransomware encryption bursts with zero prior historical telemetry).

---

## 2. Identified System Boundaries

### 2.1 Physics-Informed Queueing Approximations
- **M/M/1 and M/G/1 Modeling**:
  The performance risk engine models queue contention and tail latency inflation using an M/M/1 queuing approximation under high arrival rates. In physical hardware, multi-core NVMe controllers use 64K submission/completion queue pairs (SQ/CQ) with hardware interrupt steering (MSI-X). 
- **Tail Latency Physics**:
  While the simulator models non-linear latency inflation above 80% utilization due to flash controller garbage collection (GC/TRIM) and erase-block reclamation, it does not simulate NAND flash bit error rates (RBER) or read disturb voltage shifts at the physical cell level.

### 2.2 Storage Interconnect Topology & Discovery
- **Bus Bandwidth Aggregation**:
  Interconnect bus contention on shared SAN arrays (e.g. `sys-hybrid-matrix` FC-32G dual controller) is modeled as a unified throughput pool (6,400 MB/s). It simplifies Fibre Channel fabric credit starvation (buffer-to-buffer credits), PCIe lane bifurcation, and TCP window scaling dynamics on iSCSI/RoCE interfaces.
- **Inferred Relationship Confidence**:
  Inferred edges derived from cross-volume IOPS correlation ($r > 0.70$) have an assigned confidence score between 0.70 and 0.85. While effective for detecting co-located background jobs, correlation does not prove physical hardware causation without Out-of-Band (OOB) BMC or switch telemetry.

### 2.3 Synthetic Telemetry vs Physical Production Telemetry
- **Default Telemetry Baseline**:
  In local development and demonstration environments, the system generates deterministic synthetic enterprise telemetry with diurnal seasonality and injected write bursts.
- **Production Integration Requirement**:
  Deploying AEGISSTOR Omega to production requires connecting the Prometheus collector endpoint (`/api/v1/metrics`) to live host agents (`node_exporter`, `smartctl_exporter`, or vendor SMI-S / NVMe-MI APIs).

### 2.4 Shadow Mode Invariant
- **No Physical Mutations**:
  The system strictly enforces `SHADOW_MODE_ENABLED: true`. Recommended rebalancing interventions and capacity purges are executed within the **Resilience Digital Twin Simulator** and logged to the counterfactual audit ledger. Physical execution requires an authenticated human administrator to uncheck shadow mode via RBAC-protected endpoints.
