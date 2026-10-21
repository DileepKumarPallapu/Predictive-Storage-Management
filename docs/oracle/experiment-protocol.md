# AEGISSTOR ORACLE — Controlled Counterfactual Experiment Protocol
**Document**: Pure-Software Digital Twin Workload Simulation Protocol  
**Module**: ORACLE What-If Engine  
**Status**: Validated  

---

## 1. Protocol Objective

The objective of the ORACLE Counterfactual Protocol is to evaluate how storage capacity and tail latency dynamics respond to synthetic changes in workload parameters **without performing physical mutations on production hardware**.

---

## 2. Supported Counterfactual Interventions

| Intervention Type | Simulation Logic | Key Parameters |
| :--- | :--- | :--- |
| `THROTTLE_INTENSITY` | Scales arrival IOPS during peak contention hours | `intensity_reduction_pct` (e.g., 25% – 50% reduction) |
| `RESCHEDULE_WINDOW` | Shifts batch execution time-windows to off-peak hours | `shift_hours` (e.g., +4h to shift 01:00 burst to 05:00) |
| `EXPAND_SHARED_LIMIT` | Simulates relaxing controller queue saturation threshold | `queue_depth_multiplier` (absorbs tail queueing) |
| `REBALANCE_READ_WRITE` | Optimizes write batching and flash write-amplification | `write_coalesce_pct` |

---

## 3. Simulation Physics Model

The counterfactual service models:
1. **Diurnal Cycle Function**:
   $$D(t) = 0.55 + 0.45 \cdot \sin\left(\frac{hour(t) - 6}{24} \cdot 2\pi\right)$$
2. **Queue Saturation & Tail Latency Growth**:
   $$Q_{\text{sim}}(t) = \max\left(0.4, (\beta \cdot D(t)) \cdot 2.2\right)$$
   $$L_{\text{sim}}(t) = L_{\text{baseline}} \cdot \left(0.8 + Q_{\text{sim}}^{1.3}(t) \cdot 0.4\right)$$
   Where $\beta$ is the batch burst multiplier modulated by intervention parameters.
3. **Cumulative Capacity Trajectory**:
   $$C_{\text{sim}}(t+1) = C_{\text{sim}}(t) + \frac{v_{\text{daily}}}{24} \cdot (0.8 + 0.3 \cdot D(t))$$

---

## 4. Execution Workflow & Safety Envelopes

1. **Pre-Flight Validation**:
   - Target device exists in storage catalog.
   - Workload exists and is mapped to target device or shared controller.
   - Verified zero physical mounts or cgroups will be mutated.

2. **Simulation Run**:
   - Executes $H$-hour forward trajectory in pure memory.
   - Samples 72 time steps with corresponding P95 latency and allocated capacity.
   - Evaluates whether maximum simulated latency falls below the device SLA ceiling:
     $$\text{SLA Breach Prevented} = (L_{\text{base}} \ge L_{\text{SLA}}) \land (\max(L_{\text{sim}}) < L_{\text{SLA}})$$

3. **Audit Ledger Logging**:
   - Persists execution record to `oracle_counterfactual_experiments`.
   - Records simulator version (`DigitalTwin-Oracle-v5.0`), baseline metrics, simulated outcome, and mandatory causality disclaimer.

---

## 5. Causality Disclaimer Standard
Every counterfactual experiment report must contain the following verbatim notice:
> *"Simulated counterfactual outcome generated within Digital Twin sandbox. Observational attribution does not establish physical causation without real controlled measurement."*
