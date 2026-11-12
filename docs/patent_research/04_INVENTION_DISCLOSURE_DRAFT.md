# AEGISSTOR — Preliminary Invention Disclosure Draft (Research Task 5)

> **CONFIDENTIAL — PRELIMINARY TECHNICAL DISCLOSURE FOR REGISTERED PATENT AGENT REVIEW**  
> This draft organizes the implemented software/systems architecture of AEGISSTOR into a standard 20-section invention disclosure structure. It makes **no representation of patentability** and requires substantive prior-art claim scoping and Section 3(k) drafting by a registered Indian patent agent.

---

### 1. Title
**Telemetry-Reliability-Gated, Regime-Adaptive Multi-Model Storage Capacity Forecasting, Conformal Risk Calibration, and Constraint-Bounded Digital Twin Decision System**

### 2. Field of Invention
Enterprise computer storage systems, infrastructure telemetry observability, machine learning time-series forecasting, conformal uncertainty calibration, and non-destructive digital twin capacity optimization.

### 3. Background
Enterprise block, file, NAS, SAN, and cloud storage pools must maintain free headroom below critical safety thresholds (e.g., 85%–90% capacity) while honoring read/write latency Service Level Agreements (SLAs). Existing monitoring platforms rely either on static percentage alerts or uncalibrated point forecasts that ignore sensor staleness and workload regime shifts.

### 4. Existing Technical Problem
1. Corrupted or delayed storage telemetry induces false over-confident capacity predictions and erroneous automated scaling recommendations.
2. Non-stationary workload transitions (diurnal batch cycles vs. abrupt bursts vs. storage reclamation) defeat single-model predictors (`US10949116B2` addresses multi-model subsetting without reliability-scaled conformal intervals or constraint-bounded execution blocking).
3. Horizon uncertainty grows non-linearly over multi-week horizons; ignoring calibration residuals under-predicts tail capacity exhaustion (`P90`).

### 5. Summary of Proposed Mechanism (As Implemented)
AEGISSTOR implements a staged read-only intelligence loop that: (a) ingests storage telemetry idempotently across heterogeneous collectors; (b) computes a 9-factor composite `DataReliabilityProfile` score $R \in [0, 1]$, staleness flag, uncertainty multiplier $\gamma \ge 1.0$, and automated recommendation permission gate; (c) classifies statistical workload regimes and KS/PSI drift; (d) selects a calibration-penalized champion between multivariate `LGBMRegressor` and state-space `SARIMAX` benchmarked against `SeasonalNaiveBenchmark`; (e) calibrates prediction bands via chronological Split Conformal quantiles scaled by $\sqrt{h} \cdot \gamma$; (f) derives threshold-crossing probability and expected shortfall from the empirical residual CDF; and (g) ranks candidate interventions through a constrained Digital Twin optimizer prior to non-executing shadow approval.

### 6. Detailed System Architecture & Flow Diagrams

```mermaid
flowchart LR
  C["Read-Only Collectors (Linux Host / Prometheus / CSV / HTTP API)"] -->|X-API-Key + Idempotency-Key| I["Telemetry Validation & Quality Store"]
  I --> R["DataReliabilityEngine (9 Factors -> Score R, Multiplier gamma, LOW/STALE Gate)"]
  I --> W["WorkloadRegimeEngine (OLS Slopes, Lag-24 AC, Burst Z-Score, KS/PSI)"]
  R -->|gamma & features| CC["ChampionChallengerEngine (LightGBM vs SARIMAX vs SeasonalNaive)"]
  W -->|regime context| CC
  CC -->|3-Way Split Conformal + sqrt(h)*gamma| F["Multi-Horizon Forecasts (P10/P50/P90)"]
  F --> K["CapacityRiskEngine (Empirical Residual CDF Crossing Prob, Shortfall, Brier)"]
  R -->|Gate Block if LOW/STALE| K
  K --> O["DecisionOptimizer & Digital Twin (Hard Constraints, Feasible vs Rejected)"]
  O --> G["5-State Non-Executing Shadow Approval + Outcome Verification Feedback"]
```

### 7. Component Descriptions (Verified Codebase Mapping)
- **Collector & Security Layer**: [`connector_registry.py`](../../backend/app/collector/connector_registry.py), [`endpoints_connectors.py`](../../backend/app/api/v1/endpoints_connectors.py), [`endpoints_telemetry.py`](../../backend/app/api/v1/endpoints_telemetry.py) (`Idempotency-Key`, hashed `X-API-Key`, read-only OS/PromQL probes).
- **Data Reliability Engine**: [`data_reliability_engine.py`](../../backend/app/services/data_reliability_engine.py).
- **Workload Regime & Drift Engine**: [`workload_regime_engine.py`](../../backend/app/services/workload_regime_engine.py).
- **Champion-Challenger ML Engine**: [`champion_challenger.py`](../../backend/app/ml/champion_challenger.py).
- **Probabilistic Capacity Risk Engine**: [`capacity_risk_engine.py`](../../backend/app/services/capacity_risk_engine.py).
- **Digital Twin & Decision Optimizer**: [`digital_twin.py`](../../backend/app/simulator/digital_twin.py), [`decision_optimizer.py`](../../backend/app/services/decision_optimizer.py).
- **Governance & Outcome Verification**: [`endpoints_recommendations.py`](../../backend/app/api/v1/endpoints_recommendations.py), [`entities.py`](../../backend/app/models/entities.py).

### 8. Data-Flow Explanation
Raw counters `(timestamp, total_capacity_bytes, used_bytes, free_bytes, optional IOPS/latency/throughput)` are persisted unmodified (`Telemetry`, `IngestionJob`) without fabricating missing sensors. All analytics modules read persisted `Telemetry` slices strictly in chronological order and write immutable trace/artifact pointers (`DataReliabilityProfile`, `WorkloadRegimeEvent`, `ModelVersion`, `ModelMetric`, `Forecast`, `CapacityRiskEvaluation`, `AuditLog`).

### 9. Processing Sequence
1. Validate & deduplicate incoming batch (`Idempotency-Key` + timestamp uniqueness);
2. Evaluate 9-factor reliability profile `(R, tier, is_stale, gamma)`;
3. Evaluate statistical regime `(regime_label, confidence, ks_pvalue, psi_drift)`;
4. If records $\ge 60$, build leak-free lag/rolling features, filter unavailable exogenous features, split chronologically `64% / 16% / 20%`, train `LGBMRegressor` and `SARIMAX` + evaluate `SeasonalNaiveBenchmark`;
5. Calibrate $q_{\text{conf}}$ on the 16% calibration split and pick champion via calibration-aware score;
6. Generate multi-step `P10/P50/P90` bands scaled by $\sqrt{h_{\text{hours}}} \cdot \gamma$;
7. Compute residual-CDF breach probability & expected shortfall;
8. Run constrained counterfactual scenarios; suppress automated high-confidence actions if reliability is `LOW` or `is_stale = True`.

### 10. Algorithm Descriptions & 11. Mathematical Calculations
1. **9-Factor Data Reliability Score**:
   $$R = \sum_{k=1}^{9} w_k f_k, \quad \sum_{k=1}^{9} w_k = 1$$
   where $f_k \in [0, 1]$ measures completeness, freshness, timestamp continuity, non-duplicate rate, non-invalid rate, capacity accounting consistency ($|\text{used} + \text{free} - \text{total}|/\text{total} \le 0.015$), optional-metric presence, connector availability, and depth/jump stability.
   - Uncertainty Multiplier $\gamma$:
     $$\gamma = \begin{cases} 1.0, & R \ge 0.80 \land \neg\text{is\_stale} \\ 1.0 + 1.5 \cdot \max(0.05, 0.80 - R), & 0.55 \le R < 0.80 \lor (R \ge 0.80 \land \text{is\_stale}) \\ 1.0 + 2.0 \cdot \max(0.25, 0.80 - R), & R < 0.55 \end{cases}$$
2. **Split Conformal Interval & Champion Cost**:
   - Calibration quantile: $q_{\text{conf}} = \text{Quantile}_{0.80(1 + 1/n_{\text{cal}})}\{|y_i - \hat{y}_i|\}_{i \in \text{Calib}}$.
   - Champion composite cost:
     $$C_m = \frac{\text{RMSE}_m}{\text{RMSE}_{\text{naive}}} + 0.55 |\text{Coverage}_m - 0.80| + 0.15 \frac{\text{Pinball}_m}{\text{MAE}_{\text{naive}}}$$
   - Multi-horizon bounds at horizon $h$ hours:
     $$[\hat{y}_{t+h} - q_{\text{conf}}\sqrt{h}\cdot \gamma,\; \hat{y}_{t+h} + q_{\text{conf}}\sqrt{h}\cdot \gamma] \cap [0, C_{\text{total}}]$$
3. **Empirical Residual-CDF Risk & Shortfall**:
   - Using calibration residuals $\{r_j\}$, terminal samples $S_j = \text{clip}(\hat{y}_{t+H} + r_j\sqrt{H}\cdot \gamma, 0, C_{\text{total}})$, threshold crossing probability $\hat{P} = \frac{1}{M}\sum_j \mathbb{I}(S_j \ge L_{\text{safe}})$, and expected shortfall $\mathbb{E}[S_j - L_{\text{safe}} \mid S_j > L_{\text{safe}}]$.

### 12. Example Implementation
Executable in `backend/app/` and surfaced across 20 frontend modules in `frontend/src/pages/` connected via FastAPI REST endpoints (`/api/v1/v2/...`, `/api/v1/reliability/...`, `/api/v1/risk/capacity/...`, `/api/v1/digital-twin/optimize/...`).

### 13. Drawing List (Proposed Patent Drawings)
- **FIG. 1**: High-level closed-loop architecture (`Telemetry -> Reliability/Regime -> Champion-Challenger -> Risk -> Constrained Twin -> Shadow Governance`).
- **FIG. 2**: Flowchart of 9-factor Data Reliability gating and dynamic conformal uncertainty multiplier $\gamma$ branching.
- **FIG. 3**: Chronological 3-way split & coverage-penalized Champion-Challenger tournament (`LightGBM` vs `SARIMAX` vs `SeasonalNaiveBenchmark`).
- **FIG. 4**: Empirical residual-CDF crossing probability calculation and Brier calibration feedback graph.
- **FIG. 5**: Constrained Digital Twin optimization state filtering (`Feasible Ranked` vs `Hard-Constraint Rejected`).

### 14. Experimental Plan & 15. Actual Results
See [`03_EXPERIMENTAL_VALIDATION_PLAN_AND_TEMPLATE.md`](03_EXPERIMENTAL_VALIDATION_PLAN_AND_TEMPLATE.md) and measured script outputs in [`experimental_results_observed.json`](experimental_results_observed.json) *(controlled benchmark runs only; field traces pending)*.

### 16. Advantages Supported by Implemented Logic
- Explicit suppression of automated high-confidence interventions under stale or low-reliability telemetry.
- Zero fabrication of missing IOPS/latency/cost fields during both training and optimization.
- Chronological split + Split Conformal finite-sample calibration preventing optimistic interval collapse across multi-day horizons.

### 17. Known Limitations
- Requires $\ge 60$ points for ML champion-challenger training and $\ge 24$ points for regime classification.
- Controlled benchmarks do not yet prove external validity across 90-day heterogeneous production array logs.

### 18. Prior-Art Comparison
See full matrix in [`01_PRIOR_ART_AND_FEATURE_MATRIX.md`](01_PRIOR_ART_AND_FEATURE_MATRIX.md) analyzing `US10949116B2`, `US11750468B2`, `US12153647B2`, `US7783510B1`, `US11228645B2`, `US11960348B2`, `US20230396511A1`, and `arXiv:2509.02844` / `arXiv:2607.24773`.

### 19. Unresolved Novelty Questions (For Patent Agent)
1. Does scaling Split Conformal quantile widths by a 9-factor storage reliability score $\gamma$ AND hard-blocking storage interventions establish inventive step over **US11750468B2** (Dell conformal asset state prediction) + **US10949116B2** (EMC multi-model selection) + **arXiv:2509.02844** (changepoint conformal)?
2. Are independent hardware/system ties required in claim drafting to overcome **Section 3(k)** exclusions under Indian CRI Guidelines 2025?

### 20. Potential Claim Topics for Patent Agent Review
*(Strictly preliminary technical claim concepts, not legal claim language)*:
1. A non-destructive storage telemetry resilience controller coupling multi-factor telemetry reliability scoring directly to both conformal prediction interval expansion ($\sqrt{h}\cdot \gamma$) and automated intervention suppression gates.
2. Calibration-penalized runtime champion-challenger selection across heterogeneous statistical (`SARIMAX`) and gradient-boosted (`LightGBM`) storage capacity predictors filtered against uncollected exogenous channels.
3. Constraint-bounded counterfactual storage intervention evaluation preserving missing unit-cost neutrality while jointly enforcing capacity margin, tail-latency SLA, and transfer volume bounds.
