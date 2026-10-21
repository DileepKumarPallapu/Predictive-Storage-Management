# AEGISSTOR OMEGA — Data Provenance, Labeling & Integrity Specification
**Milestone**: AEGISSTOR OMEGA (Prompt 6.0)  

---

## 1. Data Provenance & Category Taxonomy

AEGISSTOR Omega mandates strict semantic typing and visual labeling across all API contracts, database entities, and user interface components.

```
       ┌─────────────────────────────────────────────────────────────┐
       │              TELEMETRY & INTELLIGENCE DATA                  │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         │                            │                            │
         ▼                            ▼                            ▼
┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│    OBSERVED     │          │    PREDICTED    │          │    SIMULATED    │
│  (Real/Synthetic│          │   (Calibrated   │          │ (Counterfactual │
│   Sensor Data)  │          │   ML Forecast)  │          │  Digital Twin)  │
└─────────────────┘          └─────────────────┘          └─────────────────┘
```

### Explicit Contract Categories

1. **`OBSERVED_MEASUREMENT`**:
   - Direct physical or synthetic generator metrics (timestamp, used bytes, free bytes, IOPS, P95 latency, queue depth).
   - Tagged with `is_synthetic: true/false` and source identifier.
2. **`MODEL_PREDICTION`**:
   - Output of statistical or ML quantile regression models ($q_{10}, q_{50}, q_{90}$).
   - Includes inference latency, model version tag, and nominal vs empirical coverage.
3. **`SIMULATED_OUTCOME`**:
   - Deterministic counterfactual trajectory projected by the Digital Twin under hypothetical interventions.
   - Tagged with `is_simulated_estimate: true` and simulation seed $S=42$.
4. **`UNVERIFIED_ASSUMPTION`**:
   - Explicit domain heuristics (e.g. constant background write rate, linear LBA mapping, fixed controller interconnect caps).

---

## 2. Resource Relationship Provenance Attribution

In multi-pool storage clusters, graph edges between systems, pools, volumes, and workloads carry an explicit **Provenance Tag**:

| Provenance Tag | Source / Discovery Mechanism | Default Confidence Score |
| :--- | :--- | :---: |
| **`DISCOVERED`** | Automatically queried from storage array management APIs, host sysfs (`/sys/block`), NVMe-oF namespace mappings, or SCSI inquiry pages. | **1.0 (100%)** |
| **`USER_DEFINED`** | Explicitly configured by storage administrators via runbooks, backup schedules (e.g. Veeam nightly window), or SLA policies. | **0.95 - 1.0 (95-100%)** |
| **`INFERRED`** | Statistically deduced by AEGISSTOR Omega correlation engines (e.g. cross-volume IOPS cross-correlation $r > 0.70$ indicating unmapped shared PCIe switch or network switch contention). | **0.70 - 0.85 (70-85%)** |

---

## 3. Synthetic Benchmark Generator Integrity

### Physics-Informed Dynamics
The synthetic benchmark generator (`SyntheticGenerator`) generates realistic traces:
- **Diurnal Business Cyclicity**: Cosine curves modeling 09:00 to 19:00 enterprise OLTP transaction spikes.
- **Micro-Burst Injection**: Stochastic write bursts simulating snapshot consolidation and database checkpoint flushes.
- **Flash Controller Coupling**: Garbage collection (GC/TRIM) write amplification kicks in at utilization $> 80\%$, inflating P95 tail latency by up to +6.5ms.
- **Queueing Physics**: Approximates M/M/1 queueing delay under high concurrent arrival rates.

### Reproducibility Guarantee
- The generator runs with deterministic pseudorandom seeds (`seed=42 + hash(device_id)`).
- Re-running the application or backtests produces identical values across all test suites and experiments.

---

## 4. Shadow Mode Safety Guarantee

Physical host safety is strictly guaranteed:
- **`SHADOW_MODE_ENABLED: true`**: No storage LUNs, volumes, namespaces, or filesystems are mutated, unmounted, formatted, or deleted.
- All intervention actions and tier rebalancing routines run entirely within the memory space of the **Resilience Digital Twin Simulator**.
- User interfaces prominently display the `SHADOW MODE (ACTIVE)` badge to maintain transparent operational context.
