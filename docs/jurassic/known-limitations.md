# AEGISSTOR JURASSIC — Known Limitations & Non-Claim Boundaries
**Milestone**: AEGISSTOR JURASSIC (Prompt 7.0)  

---

## 1. Scope & Non-Claims

This document defines the strict scientific and operational limits of the AEGISSTOR Jurassic Failure Discovery Lab:

1. **No Hardware Diagnosis**: The system is designed for capacity exhaustion, tail latency amplification, and operational planning resilience. It is not an electrical or silicon-level hardware defect analyzer.
2. **Synthetic Boundary**: Scenarios are simulated using physics-informed mathematical models. While validated against flash garbage collection and M/M/1 queuing dynamics, they do not replace testing on physical enterprise storage hardware before live production rollout.
3. **Shadow Mode Invariant**: Physical host storage drives are never modified by the chaos framework.

---

## 2. Technical Limitations

### 2.1 Micro-Burst Resolution
- Telemetry simulation operates at 1-hour step granularity. Sub-minute microsecond I/O bursts (e.g. 50ms PCIe link dropouts) are aggregated into hourly P95 tail latency and queue depth statistics.
- Higher resolution sub-second traces require high-frequency ring buffers that increase storage ingestion overhead.

### 2.2 Drift Detector Convergence Window
- The Page-Hinkley cumulative sum test requires at least 20 historical observations to establish an empirical mean and variance baseline. During the first 19 timesteps of a brand-new storage volume, drift status is conservatively reported as `INSUFFICIENT_DATA`.

### 2.3 Destination Pool Bottleneck Modeling
- When modeling cross-device data migrations (e.g. from NVMe Tier 1 to SAS Tier 2), shared bus concurrency is modeled as a unified throughput pool. Complex protocol handshakes (e.g. Fibre Channel BB-credits or TCP window stalls on RoCE v2) are represented as latency amplification penalties rather than packet-level simulations.
