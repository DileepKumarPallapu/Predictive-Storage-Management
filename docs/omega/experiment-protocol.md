# AEGISSTOR OMEGA — Reproducible Experiment Protocol & Benchmarks
**Milestone**: AEGISSTOR OMEGA (Prompt 6.0)  

---

## 1. Overview & Execution Commands

All empirical experiments in AEGISSTOR Omega are fully automated, deterministic, and verifiable through standard command-line tools.

### Running the Full Test Suite
```powershell
# From the backend directory
cd C:\Users\dilee\.gemini\antigravity\scratch\aegisstor\backend
python -m pytest -q
```
*Expected Result*: 57 passed tests in ~11-13 seconds.

### Running the Omega Research Intelligence Tests
```powershell
python -m pytest tests/test_omega_intelligence.py -v
```

### Running the Performance Benchmark
```powershell
python tests/run_performance_benchmark.py
```

### Building the Frontend Application
```powershell
cd C:\Users\dilee\.gemini\antigravity\scratch\aegisstor\frontend
npm run build
```
*Expected Result*: Production bundle compiles cleanly via `tsc -b && vite build` in ~500ms.

---

## 2. Hypothesis H1 Benchmark: Decision Loss vs Symmetric MAE

### Objective
Demonstrate that minimizing symmetric MAE (L1 loss) does not minimize operational failure costs in enterprise storage systems.

### Protocol
1. **Target**: `vol-nvme-tier1-db` (10 TB NVMe OLTP tier).
2. **Horizon**: 72 hours.
3. **Evaluation Window**: 144 chronological steps.
4. **Cost Matrix**:
   - $C_{\text{missed\_breach}} = \$3,500$ (outage / emergency remediation).
   - $C_{\text{false\_alarm}} = \$320$ (unnecessary tier migration overhead).
   - $C_{\text{lead\_shortfall}} = \$85/\text{hr}$ (penalty when lead-time $< 24\text{ hours}$).
5. **Evaluated Models**:
   - `naive_rolling_linear`: Constant window rolling average.
   - `holt_winters_seasonal`: Triple exponential smoothing with diurnal periodicity.
   - `standard_mae_lightgbm`: Point-prediction LightGBM trained with L1 symmetric objective.
   - `aegisstor_omega_decision_aware`: Conformal quantile regressor with asymmetric upper-quantile loss ($q_{0.90}$).

### Verification Assertion
```python
assert lgbm["mae_pct"] < omega["mae_pct"]
assert omega["total_operational_decision_loss_usd"] < lgbm["total_operational_decision_loss_usd"]
assert omega["missed_breaches_count"] == 0
```

---

## 3. Hypothesis H2 Benchmark: Adaptive Attention & Value of Information

### Objective
Quantify telemetry network/disk overhead, warning lead time, and anomaly capture rate across 30 days of fleet operations.

### Policies Tested
- **Policy A (Fixed High-Frequency)**: Uniform 60s sampling interval across all volumes.
- **Policy B (Threshold-Triggered)**: 3600s nominal interval, accelerating to 60s only after utilization exceeds 80%.
- **Policy C (AEGISSTOR Omega Attention)**: Dynamically scales interval $\Delta t \in [30\text{s}, 1800\text{s}]$ based on:
  $$\text{AttentionScore} = 0.45 \cdot P(\text{breach}_{72h}) + 0.35 \cdot \text{ConformalWidth} + 0.20 \cdot \text{ContentionCoupling}$$

### Metric Formula
$$\text{VoI Score} = \frac{\text{Warning Margin (hours)} \times \text{Anomaly Capture Rate (\%)}}{\text{Network Bandwidth (MB / day)}}$$

---

## 4. Hypothesis H3 Benchmark: Dual-Sided Hard Safety Envelope

### Objective
Verify that candidate cross-volume data migrations enforce safety constraints on both the source volume, the destination volume, and shared array interconnects.

### Test Cases
1. **Safe Rebalance**:
   - Source: `vol-nvme-tier1-db` (75% used)
   - Destination: `vol-sas-tier2-analytics` (65% used)
   - Size: 800 GB, Bandwidth: 200 MB/s
   - *Expected Verdict*: `FEASIBLE_SAFE` or `FEASIBLE_WITH_THROTTLING` with $+426\text{h}$ runway gained.
2. **Unsafe Destination Breach**:
   - Source: `vol-nvme-tier1-db`
   - Destination: `vol-sas-tier2-analytics`
   - Size: 45,000 GB, Bandwidth: 350 MB/s
   - *Expected Verdict*: `REJECTED_UNSAFE_SECONDARY_BREACH` due to destination capacity ceiling breach ($> 90\%$).

---

## 5. Hypothesis H4 Benchmark: Governed Model Promotion

### Objective
Verify that candidate forecasting models are evaluated by a strict decision-loss safety gate before deployment.

### Test Cases
1. **Model with lower MAE but higher Decision Loss**:
   - Candidate: MAE 1.85% (vs baseline 2.64%), Decision Loss $1,420 (vs baseline $320).
   - *Expected Verdict*: `REJECTED`, `hard_safety_check_passed: false`.
2. **Model improving Decision Loss**:
   - Candidate: MAE 2.50%, Decision Loss $290, ECE 0.022.
   - *Expected Verdict*: `PROMOTED`, `hard_safety_check_passed: true`.
