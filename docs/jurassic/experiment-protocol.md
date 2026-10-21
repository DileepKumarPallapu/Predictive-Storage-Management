# AEGISSTOR JURASSIC — Experimental Research Protocol & Research Questions
**Milestone**: AEGISSTOR JURASSIC (Prompt 7.0)  

---

## 1. Research Protocol Overview

This document specifies the scientific questions, experimental setups, and quantitative metrics used to evaluate whether the AEGISSTOR Jurassic Resilience Lab improves failure discovery and operational reliability.

---

## 2. Formal Research Questions

### RQ1: Forecast Error Under Workload Distribution Shift
- **Question**: How does capacity and latency forecast error (MAE/RMSE) degrade when enterprise workloads transition from nominal diurnal patterns to accelerated multi-burst regimes?
- **Protocol**: Compare model error on 168-hour timeline across:
  * Baseline nominal operation (`scenario-jurassic-cap-burst-01` hours 0-35).
  * Shifted multi-burst regime (`scenario-jurassic-cap-burst-01` hours 36-72).
- **Target Metric**: $\Delta \text{MAE}_{\text{shift}} = \text{MAE}_{\text{shifted}} - \text{MAE}_{\text{nominal}}$.

### RQ2: Prediction Interval Robustness Under Unusual Workloads
- **Question**: How effectively do conformal prediction intervals ($q_{10}-q_{90}$) communicate deteriorating reliability during compound disturbances?
- **Protocol**: Assess empirical coverage against the 80.0% nominal target across all 6 scenarios.
- **Hypothesis**: Conventional fixed-width intervals experience empirical coverage collapse ($<50\%$), whereas conformal adaptive intervals maintain calibration or transparently declare `WORKLOAD_DISTRIBUTION_SHIFT`.

### RQ3: Degraded Evidence Detection and Unsafe Action Rejection
- **Question**: Can the system reliably detect degraded telemetry and reject unsafe interventions during interacting failure conditions?
- **Protocol**: Execute Scenario 04 (heartbeat dropout) and Scenario 06 (destination saturation).
- **Success Criteria**:
  * In Scenario 04: automated actions are 100% blocked during telemetry blackout.
  * In Scenario 06: cross-pool rebalancing is 100% rejected (`REJECTED_UNSAFE_SECONDARY_BREACH`).

### RQ4: Safe Fallback State Transitions and Recovery Latency
- **Question**: What is the detection latency and recovery latency when transitioning between the 5 formal safe states?
- **Protocol**: Measure timestep intervals between fault injection, state transition, and heartbeat resumption.
- **Target Metric**: Mean detection latency $\le 1$ hour; recovery latency $\le 2$ hours after telemetry returns.

### RQ5: Computational and Resource Overhead
- **Question**: What additional CPU, memory, and database overhead is introduced by real-time Page-Hinkley drift monitoring and dual-sided safety checks?
- **Protocol**: Run full 66-test pytest suite and 72-hour simulation benchmark while profiling execution duration.
- **Target Metric**: Added host CPU overhead $< 2.5\%$; execution time $\le 12.5$ seconds for full 168-hour simulation.

---

## 3. CLI Execution Commands

To execute and verify the research protocol:

```powershell
# 1. Run complete automated test suite
cd C:\Users\dilee\.gemini\antigravity\scratch\aegisstor\backend
python -m pytest tests/test_jurassic_resilience.py -v

# 2. Run complete platform test suite
python -m pytest -q

# 3. Build frontend bundle
cd C:\Users\dilee\.gemini\antigravity\scratch\aegisstor\frontend
npm run build
```
