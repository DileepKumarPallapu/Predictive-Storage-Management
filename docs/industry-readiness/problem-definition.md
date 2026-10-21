# AEGISSTOR — Formal Technical Problem Definition
**Document**: Mathematical & Systems Problem Formulation  
**Phase**: Phase 1 (Problem Formalization)  
**Status**: Formalized  

---

## 1. Monitored Storage Environment

Let $\mathcal{S} = (\mathcal{D}, \mathcal{P}, \mathcal{C}, \mathcal{W}, \mathcal{E})$ represent an enterprise multi-tier storage platform, where:
- $\mathcal{D} = \{d_1, d_2, \dots, d_N\}$ is the set of physical storage volumes/devices across distinct tiers (NVMe flash, SAS magnetic array, cold archival, high-throughput edge cache).
- $\mathcal{P} = \{p_1, \dots, p_M\}$ is the set of shared storage pools grouping volumes.
- $\mathcal{C} = \{c_1, \dots, c_K\}$ is the set of storage controllers, HBAs, and PCIe switches multiplexing I/O.
- $\mathcal{W} = \{w_1, \dots, w_J\}$ is the set of concurrent workloads (transactional OLTP, analytics batch ETL, streaming ingestion, backup snapshot sync).
- $\mathcal{E}$ is the directed dependency graph representing physical and logical resource mappings:
  $$\mathcal{E} \subseteq (\mathcal{W} \times \mathcal{D}) \cup (\mathcal{D} \times \mathcal{P}) \cup (\mathcal{P} \times \mathcal{C})$$

---

## 2. Formal State Space & Measurement Vector

At each discrete time step $t \in \mathbb{N}$ (hourly sampling $\Delta t = 1\text{ hour}$), the system observes a telemetry vector for each device $d \in \mathcal{D}$:
$$\mathbf{y}_d(t) = \begin{bmatrix}
C_d(t) & \text{Used capacity [Bytes]} \\
\rho_d(t) & \text{Capacity utilization [\%]} \\
IOPS_d^{\text{read}}(t) & \text{Read arrival rate [IOPS]} \\
IOPS_d^{\text{write}}(t) & \text{Write arrival rate [IOPS]} \\
T_d(t) & \text{Bus throughput [MB/s]} \\
L_d^{(95)}(t) & \text{P95 tail latency [ms]} \\
Q_d(t) & \text{Average queue depth}
\end{bmatrix}$$

---

## 3. Operational Constraints & Failure Thresholds

Each device $d \in \mathcal{D}$ is governed by hard operational constraints defined by SLAs and physical limits:
1. **Capacity Reserve Constraint**:
   $$C_d(t) \le C_d^{\max} \cdot (1 - \phi_d^{\text{reserve}})$$
   Where $C_d^{\max}$ is total capacity and $\phi_d^{\text{reserve}}$ is the mandatory free space reserve (e.g., $15\%$ to preserve flash controller over-provisioning and garbage collection performance).
2. **P95 Tail Latency SLA Constraint**:
   $$L_d^{(95)}(t) \le L_d^{\text{SLA}}$$
   Where $L_d^{\text{SLA}}$ is the maximum allowable P95 response time (e.g., $15.0\text{ ms}$ on NVMe Tier-1).

An **Incident** occurs at time $t$ if either constraint is violated:
$$\mathcal{I}_d(t) = \mathbb{I}\left(C_d(t) > C_d^{\max}(1 - \phi_d^{\text{reserve}})\right) \lor \mathbb{I}\left(L_d^{(95)}(t) > L_d^{\text{SLA}}\right)$$

---

## 4. Multi-Horizon Predictive Target

Given historical observations up to time $t_0$, $\mathcal{H}(t_0) = \{\mathbf{y}_d(t) \mid t \le t_0, d \in \mathcal{D}\}$, the forecasting task is to estimate the future quantile distribution of capacity and tail latency over horizon $H \in \{24, 72, 168\}$ hours:
$$\hat{C}_d^{(\tau)}(t_0 + h) \quad \text{and} \quad \hat{L}_d^{(95, \tau)}(t_0 + h), \quad h \in [1, H], \; \tau \in \{0.10, 0.50, 0.90\}$$

### Reserve Runway Problem
Determine the earliest time step $h^*$ at which the probability of constraint breach exceeds safety threshold $\alpha = 0.05$:
$$h^* = \min \left\{ h \in [1, H] \;\middle|\; \mathbb{P}\left(C_d(t_0 + h) \ge C_d^{\text{crit}} \;\middle|\; \mathcal{H}(t_0)\right) \ge \alpha \right\}$$

---

## 5. Decision Space & Candidate Actions

The set of permissible management actions $\mathcal{A}$ on device $d$ includes:
- **`THROTTLE_INTENSITY`**: Scale arrival IOPS of batch workload $w$ by reduction percentage $\delta \in [0.10, 0.70]$.
- **`RESCHEDULE_WINDOW`**: Shift execution window of batch workload $w$ by $\Delta h \in [1, 12]$ hours off-peak.
- **`TIERED_MIGRATION`**: Migrate data blocks $B$ from device $d$ (Tier-1) to destination device $d'$ (Tier-2).
- **`INLINE_COMPRESSION`**: Enable background block compaction/deduplication on eligible data volumes.
- **`EXPAND_CONTROLLER_QUEUE`**: Relax controller concurrency threshold to absorb transient queue depth spikes.

Each action $a \in \mathcal{A}$ requires execution lead time $\Delta t_{\text{exec}}(a)$ and incurs operational cost $\text{Cost}(a)$ (I/O bus penalty, CPU overhead, or SLA degradation of deprioritized workloads).

---

## 6. The Core Technical Optimization Problem

Given an impending predicted incident on device $d$ with warning lead time $h^*$, select an optimal action $a^* \in \mathcal{A}$ that satisfies:
1. **Feasibility**: Can the action complete before breach occurs?
   $$\Delta t_{\text{exec}}(a) \le h^*$$
2. **Safety Envelope Compliance**: Does the action eliminate the constraint breach without pushing shared controllers into queue saturation?
   $$\hat{C}_d(t_0 + h \mid a) \le C_d^{\text{crit}} \quad \text{and} \quad \hat{L}_{d'}^{(95)}(t_0 + h \mid a) \le L_{d'}^{\text{SLA}} \quad \forall d' \in \mathcal{D}$$
3. **Evidence Gating**: Is the recommendation supported by measured calibration and empirical coverage bounds?
   $$\text{Discrepancy}(\text{Twin}, \text{Observed}) \le \epsilon_{\max} \quad \text{and} \quad \text{Coverage}(\hat{C}) \ge 1 - \alpha$$

If no action $a \in \mathcal{A}$ satisfies all three conditions, the system must trigger the guaranteed fallback:
$$\text{Output} = \textbf{INSUFFICIENT EVIDENCE OR NO FEASIBLE ACTION — MANUAL REVIEW REQUIRED}$$
