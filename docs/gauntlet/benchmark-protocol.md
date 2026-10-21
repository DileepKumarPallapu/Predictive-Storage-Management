# AEGISSTOR GAUNTLET — Benchmark Protocol & Evaluation Standards
**Module:** GAUNTLET Benchmark Catalog (Prompt 18.0 Parts 3, 4, 5, 6, 7)  
**Target Environment:** Python 3.13.14, SQLite WAL, Enterprise Block Storage Telemetry  

---

## 1. Fair Benchmark Execution Guarantees

To ensure scientific fairness and prevent benchmark distortion:
1. **Identical Temporal Splits:** All competing models (Persistence, Seasonal-Naive, Gradient Boosting, Evidence-Gated Planner) are evaluated over identical time windows. The standard temporal split is:
   * **Training Partition:** Earliest 70% of chronological observations.
   * **Validation Partition:** Next 15% (for conformal non-conformity tuning).
   * **Test Partition (Holdout):** Final 15% strictly reserved for out-of-sample evaluation.
2. **Zero Temporal Leakage:** Feature extraction utilizes only historical observations $y(t' \le t)$. Future window statistics are strictly excluded.
3. **No Deliberate Baseline Weakening:** Competing baselines (Persistence and Seasonal-Naive) are given full access to recent innovation volatility and diurnal drift parameters.

---

## 2. Canonical Benchmark Suites

### Suite A: Capacity Forecasting (`suite-capacity-forecast-v1`)
* **Objective:** Measures multi-horizon capacity projection error and prediction interval calibration.
* **Target Metric:** `used_bytes` aggregated in 60-minute windows.
* **Evaluated Horizons:** 12h, 24h, 48h, 72h.
* **Metrics:**
  * Mean Absolute Error (MAE in GB): $\frac{1}{H}\sum_{h=1}^H |y_h - \hat{y}_h|$
  * Root Mean Square Error (RMSE in GB): $\sqrt{\frac{1}{H}\sum_{h=1}^H (y_h - \hat{y}_h)^2}$
  * Prediction Interval Coverage (PICP): Percentage of actuals within $[q_{10}, q_{90}]$
  * Mean Prediction Interval Width (MPIW in GB): $\frac{1}{H}\sum_{h=1}^H (q_{90,h} - q_{10,h})$
  * Quantile Pinball Loss ($L_\tau$): $\frac{1}{H}\sum_{h=1}^H \max(\tau(y_h - q_{\tau,h}), (\tau - 1)(y_h - q_{\tau,h}))$
* **Acceptance Criteria:**
  * Quantile ML MAE must be lower than Persistence MAE.
  * Interval coverage must fall within $[75\%, 95\%]$ at nominal $\alpha = 0.80$.

### Suite B: Performance & Latency (`suite-perf-iops-v1`)
* **Objective:** Evaluates accuracy of IOPS, throughput, and p95 tail latency projections under bursty transactional workloads.
* **Target Metrics:** Total IOPS (read + write), p95 latency (ms), queue depth.
* **Metrics:** IOPS MAE, p95 Latency RMSE, Contention Warning Lead Time ($h_{\text{cont}}$).
* **Acceptance Criteria:** p95 latency RMSE $\le 1.5\,\text{ms}$ on Tier-1 NVMe SSD.

### Suite C: Storage Decision Quality (`suite-decision-quality-v1`)
* **Objective:** Assesses the end-to-end decision quality of automated intervention planning compared to static alerting.
* **Competing Methods:**
  * Baseline A: Fixed Watermark Thresholds (Alert at $\ge 80\%$, critical at $\ge 90\%$).
  * Baseline E: Ungated Digital Twin Planner (Acts on raw simulation without evidence gating).
  * Baseline F: Proposed Evidence-Gated Multi-Resource Planner.
* **Metrics:**
  * Warning Lead Time ($h^*$): Duration in hours from alert until critical threshold breach.
  * False Alarm Rate (FAR): Proportion of alerts where breach never occurred within horizon.
  * Missed Breach Rate (MBR): Proportion of breaches occurring without prior alert.
  * Infeasible Action Rate: Percentage of recommended actions violating physical lead-time or bus limits.
  * Residual Operational Risk: Composite risk score $[0.0, 1.0]$.
* **Acceptance Criteria:** Infeasible Action Rate = $0.0\%$, FAR $\le 5.0\%$, Residual Risk $\le 0.10$.

### Suite D: System Robustness & Chaos (`suite-robustness-jurassic-v1`)
* **Objective:** Evaluates stability under injected sensor failure, packet drops, and sudden demand spikes.
* **Scenarios:** 45% telemetry dropouts, out-of-band +2TB data step surges, and Kolmogorov-Smirnov drift ($W > 0.40$).
* **Acceptance Criteria:** 100% suppression of autonomous action during active sensor failure, deterministically falling back to `FALLBACK_TO_MANUAL_REVIEW`.
