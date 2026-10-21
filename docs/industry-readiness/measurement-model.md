# AEGISSTOR — Storage Measurement & Epistemological Model
**Document**: Telemetry Acquisition, Measurement Boundaries & Calibration Model  
**Phase**: Phase 1 (Measurement Modeling)  
**Status**: Formalized  

---

## 1. Physical vs Inferred Metrics Taxonomy

To satisfy industry review standards, AEGISSTOR explicitly segregates what is physically observed from what is modeled or inferred:

| Metric Category | Observable Signal | Measurement Instrument | Epistemological Class |
| :--- | :--- | :--- | :--- |
| **Physical Block Allocation** | `used_bytes`, `free_bytes` | OS Filesystem superblock query / block bitmap count | **Empirical Fact** (Ground Truth) |
| **I/O Arrival Rates** | `read_iops`, `write_iops` | OS kernel block I/O trace daemon / `/proc/diskstats` | **Empirical Fact** (Ground Truth) |
| **Bus Throughput** | `throughput_mb_s` | Byte transfer summation per sampling window | **Empirical Fact** (Ground Truth) |
| **Tail Latency** | `latency_p95_ms` | Flash controller submission-to-completion time histogram | **Empirical Fact** (Ground Truth) |
| **Queue Saturation** | `queue_depth` | Snapshot of outstanding requests at device queue | **Empirical Fact** (Ground Truth) |
| **Quantile Trajectories** | $q_{10}(t), q_{50}(t), q_{90}(t)$ | Parametric quantile regression model | **Probabilistic Estimate** |
| **Reserve Runway** | $h^*$ (Hours to breach) | Continuous extrapolation of quantile growth curves | **Probabilistic Estimate** |
| **What-If Dynamics** | $\hat{L}(t \mid \text{throttle})$ | Storage Resilience Digital Twin pure-software simulator | **Simulated Counterfactual** |
| **Attribution Share** | $\text{Composite Attribution}$ | Statistical feature decomposition (Method C) | **Statistical Association** |
| **Unexplained Residual** | $R(t)$ | Mass conservation reconciliation ($C_{\text{device}} - \sum C_w$) | **Empirical Accounting Residual** |

---

## 2. Measurement Errors & Confounders

1. **Telemetry Missingness ($m_d(t)$)**:
   - When an agent heartbeat is dropped or the storage node undergoes reboot, metrics are absent.
   - **Rule**: Missing intervals are recorded as explicit gap intervals $[t_{\text{start}}, t_{\text{end}}]$. Missing intervals are **never** filled with zeros or interpolated blindly.

2. **Temporal Windowing**:
   - Telemetry observations are aggregated over non-overlapping 1-hour epochs.
   - Microsecond bursts within an hourly epoch are reflected in the P95 tail latency histogram rather than the mean latency.

3. **Multi-Tenant Residuals**:
   - Kernel background processes (kworker, xfsaild, zfs-txg), journaling overhead, and untagged tenant writes cannot be isolated to a single application container without kernel eBPF probes.
   - Unassigned capacity is accounted for under `wl-unattributed-residual`.
