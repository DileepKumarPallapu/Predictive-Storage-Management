# AEGISSTOR ORACLE — Attribution Methodology
**Document**: Attribution Engine & Mathematical Formulation  
**Module**: ORACLE Workload Forensics  
**Status**: Validated  

---

## 1. Overview of the Three-Method Triangulation

Storage attribution is inherently ambiguous because modern operating systems, filesystems, and storage controllers multiplex I/O requests across shared hardware queues, internal wear-leveling algorithms, and dynamic buffer caches.

ORACLE employs a **three-method triangulation framework**:

```
+-------------------------------------------------------------------+
| Method A: Direct Measurement (Deterministic Workload Instrumentation) |
|   - Host-level agent traces (cgroups, eBPF block traces, mount IOPS) |
+-------------------------------------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
| Method B: Aggregate Reconciliation (Mass-Conservation Constraint)   |
|   - Reconciles sum(Attributed) against Total Physical Used        |
|   - Isolates Unmeasured Residual: Delta = Total - sum(Attributed) |
+-------------------------------------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
| Method C: Statistical Attribution Proxy (Feature Decomposition)    |
|   - Relative capacity growth share & IOPS contention scoring      |
|   - Non-causal mathematical association proxy                     |
+-------------------------------------------------------------------+
```

---

## 2. Mathematical Formulations

### 2.1 Method A: Direct Workload Measurement
For each instrumented workload $w \in W_{dev}$ attached to target device $dev$:
$$C_w(t) = \text{Allocated Capacity in Bytes at time } t$$
$$IOPS_w(t) = \text{Read IOPS}_w(t) + \text{Write IOPS}_w(t)$$
$$\Delta C_w(t_0, t_1) = \max(0, C_w(t_1) - C_w(t_0))$$

Direct measurements are assigned high confidence ($0.90 \le \gamma \le 0.98$) based on kernel agent probe status.

### 2.2 Method B: Aggregate Reconciliation & Residual Delta
Let $C_{\text{device}}(t)$ be the aggregate storage consumption reported by the physical device telemetry. The attributed sum is:
$$C_{\text{attributed}}(t) = \sum_{w \in W_{dev}} C_w(t)$$

The unmeasured residual is computed as:
$$R(t) = \max\left(0, C_{\text{device}}(t) - C_{\text{attributed}}(t)\right)$$

The attribution coverage ratio is:
$$\text{Coverage}(t) = \min\left(1.0, \frac{C_{\text{attributed}}(t)}{C_{\text{device}}(t)}\right) \times 100\%$$

Reconciliation categorization:
- **`BALANCED`**: $\text{Coverage} \ge 90.0\%$
- **`PARTIAL_COVERAGE`**: $60.0\% \le \text{Coverage} < 90.0\%$
- **`POOR_COVERAGE`**: $\text{Coverage} < 60.0\%$

The residual $R(t)$ is explicitly attributed to `wl-unattributed-residual` (`workload_type = RESIDUAL`), accounting for filesystem journals, inode structures, block allocation bitmaps, and untagged tenant writes.

### 2.3 Method C: Statistical Attribution Proxy (Feature Decomposition)
To estimate relative demand pressure across workloads without making unearned causal assertions:
$$\text{Capacity Share}_w = \frac{\Delta C_w}{\sum_{k} \Delta C_k}$$
$$\text{IOPS Share}_w = \frac{IOPS_w}{\sum_{k} IOPS_k}$$
$$\text{Composite Attribution Score}_w = 0.6 \cdot (\text{Capacity Share}_w) + 0.4 \cdot (\text{IOPS Share}_w)$$

> [!WARNING]
> **Scientific Invariant**: The Composite Attribution Score represents observational correlation with aggregate resource consumption. It **does not** imply that workload $w$ caused a downstream latency spike, queue saturation, or pool depletion without controlled ablation.

---

## 3. Capacity Dynamics: Velocity, Acceleration & Changepoints

### 3.1 Growth Velocity (First Derivative)
Computed via finite difference over the active evaluation window ($H$ hours):
$$v = \frac{\Delta C_{\text{window}}}{H / 24.0} \quad [\text{GB/day}]$$

### 3.2 Growth Acceleration (Second Derivative)
Computed by comparing velocity in the first half of the window ($v_1$) to the second half ($v_2$):
$$a = \frac{v_2 - v_1}{(H / 2.0) / 24.0} \quad [\text{GB/day}^2]$$

Growth trajectory pattern classifications:
- **`EXPONENTIAL_ACCELERATION`**: $a > 5.0 \text{ GB/day}^2$
- **`ACCELERATING`**: $a > 1.0 \text{ GB/day}^2$
- **`DECELERATING`**: $a < -1.0 \text{ GB/day}^2$
- **`STEADY_LINEAR`**: $-1.0 \le a \le 1.0 \text{ GB/day}^2$

### 3.3 Changepoint Burst Detection
Step-changes in capacity time-series are isolated using a threshold filter:
- **`RAPID_SURGE`**: Discrete single-step jump $> +30 \text{ GB}$
- **`COMPACTION_OR_DELETION`**: Discrete step drop $< -15 \text{ GB}$

Each changepoint is cross-referenced with concurrent workload delta jumps to identify the candidate workload associated with the step.
