# AEGISSTOR — Technical Contribution Analysis & Novelty Hypothesis (Research Task 3)

> **Preliminary Technical Analysis Disclaimer**: Nothing in this document declares AEGISSTOR patentable or patent-ready. All novelty hypotheses below must be validated empirically via large-scale real storage traces and legally assessed by a qualified patent practitioner.

---

## 1. Precise Technical Problem

Enterprise storage capacity & SLA management platforms fail under real-world operational telemetry because four interacting failure modes occur concurrently in production arrays:
1. **Corrupted, Delayed, or Heterogeneous Telemetry**: Polling collectors (`LINUX_HOST`, `PROMETHEUS`, CSV imports) experience silent staleness, sampling gaps, missing optional IOPS/latency channels, duplicate retries, and out-of-range counters. Standard ML forecasters ingest degraded streams blindly and emit over-confident point projections (`LOW` reliability misread as `HIGH` certainty).
2. **Non-Stationary Regime Transitions**: Storage consumption alternates between periodic/diurnal workloads (`PERIODIC_SEASONAL`), steady growth (`STABLE_GROWTH`), sudden bursts (`SUDDEN_BURST`), reclamation drops (`DECLINING_CONSUMPTION`), and distribution drift (`UNUSUAL_CONSUMPTION_CHANGE`). Neither pure tree models (`LightGBM`, which plateaus outside training bounds and excels with multivariate covariates) nor pure linear state-space models (`SARIMAX`, which extrapolates smooth trends & seasonality cleanly) dominates all regimes.
3. **Uncalibrated Uncertainty & Data Leakage**: Conventional prediction bands assume Gaussian homoscedastic errors or leak future scaler statistics across train/test splits, causing underestimated multi-horizon `P90` upper bounds.
4. **Unsafe Unconstrained Recommendations**: Translating a raw capacity threshold crossing directly into a storage resize/migration action without checking IOPS latency SLAs, transfer caps, provisioning duration, or data reliability risks triggering thrashing or acting on stale telemetry.

---

## 2. Candidate Technical Invention Hypothesis

> **Hypothesis (Unproven Pending Full Multi-Trace Experimental Validation)**:  
> A **telemetry-reliability-coupled, regime-aware champion-challenger storage resilience controller** achieves safer target empirical coverage ($\ge 80\%$) and avoids infeasible/unsafe storage intervention triggers across degraded and non-stationary storage telemetry streams by:
> 1. Computing a deterministic multi-factor **Data Reliability Profile** ($R \in [0, 1]$) producing an explicit **uncertainty inflation factor** ($\gamma \ge 1.0$) and an **action-execution gate** (`allow_high_confidence_recommendations = False` when $R < 0.55$ or `is_stale = True`);
> 2. Classifying the storage volume's active **Workload Regime** via detrended periodicity autocorrelation, OLS trend convexity, Z-score changepoints, KS/PSI tests, and gap auditing;
> 3. Selecting a runtime champion between a leak-free multivariate gradient-boosted tree (`LGBMRegressor`) and a state-space `SARIMAX` model evaluated against a `SeasonalNaiveBenchmark` using a **calibration-aware composite cost** that penalizes both holdout RMSE and departure from nominal $80\%$ Split Conformal coverage;
> 4. Propagating Split Conformal holdout quantiles scaled jointly by $\sqrt{h_{\text{hours}}} \cdot \gamma$ into an **empirical residual-CDF threshold-crossing probability** and expected shortfall; and
> 5. Filtering candidate remediation actions through a hard-constraint **Digital Twin & Decision Optimizer** prior to human shadow sign-off and post-action verification (`RecommendationVerification`).

---

## 3. Implemented System vs. Proposed Future Improvements

Maintaining strict engineering honesty between what **exists in executable code today** versus **proposed future extensions**:

### A. Actually Implemented in Current Codebase (Verified in `backend/app/`)
1. **Read-Only Telemetry & Collector Layer** (`backend/app/collector/connector_registry.py`, `endpoints_connectors.py`, `endpoints_telemetry.py`):
   - `LinuxStorageConnector`, `PrometheusConnector`, `CsvHistoricalConnector`, `HttpIngestionConnector`.
   - `X-API-Key` hashed auth (`ApiKey`) and `Idempotency-Key` replay deduplication.
   - Missing optional performance metrics preserved strictly as `None` / `UNAVAILABLE` / `UNSUPPORTED_BY_CONNECTOR`.
2. **9-Factor Data Reliability Engine** (`backend/app/services/data_reliability_engine.py`):
   - Computes weighted score over completeness, freshness, continuity, duplicate rate, invalid rate, capacity consistency, missing metric ratio, source availability, and historical stability.
   - Sets `uncertainty_multiplier` ($1.0$ for HIGH; $1.0 + (0.80 - R)\times 1.5$ for MEDIUM; $1.0 + (0.80 - R)\times 2.0$ for LOW) and blocks high-confidence capacity recommendations when `LOW` or stale (`endpoints_recommendations.py`).
3. **Workload Regime & Drift Engine** (`backend/app/services/workload_regime_engine.py`):
   - Computes OLS slopes (overall/early/recent), detrended lag-12/lag-24 periodicity autocorrelation, Z-score bursts, KS 2-sample p-values, PSI drift, and sampling interruptions.
4. **Two-Model Champion-Challenger + Split Conformal Engine** (`backend/app/ml/champion_challenger.py`):
   - Chronological 3-way split (64% train / 16% conformal calibration / 20% holdout test) + 3-fold rolling-origin CV.
   - Evaluates `LGBMRegressor` vs `SARIMAX` vs `SeasonalNaiveBenchmark` across MAE, RMSE, $R^2$, MASE, MAPE ($y>0$ only), Pinball Loss, Empirical Coverage, Mean Interval Width.
   - Calibration-aware champion selection + Split Conformal half-band scaled by $\sqrt{h_{\text{hours}}} \cdot \gamma$, persisted via `joblib`, executed synchronously or asynchronously via `BackgroundTasks` (`/jobs/{job_id}`).
5. **Probabilistic Capacity Risk Engine** (`backend/app/services/capacity_risk_engine.py`):
   - Residual-CDF safety-threshold crossing probability, self-check Brier score on calibration residuals, expected shortfall bytes, projected threshold-crossing & exhaustion dates.
6. **Digital Twin & Constrained Decision Optimizer** (`backend/app/simulator/digital_twin.py`, `backend/app/services/decision_optimizer.py`):
   - Deterministic sandbox counterfactuals + constrained ranking over `max_utilization_pct`, `min_free_space_pct`, `max_latency_ms`, `max_transfer_gb`, `budget_usd` (only when `unit_costs` provided).
7. **Non-Execution Governance & Feedback Ledger** (`endpoints_recommendations.py`):
   - 5-state workflow (`PENDING_REVIEW`, `APPROVED_SHADOW`, `REJECTED`, `COMPLETED`, `FAILED`) + post-action `verify-outcome` discrepancy calculation (`RecommendationVerification`).

### B. Not Yet Implemented / Proposed Future Improvements (Requires Explicit Labeling)
- **Automated Closed-Loop Retrigger on Online Drift/Brier Degradation**: Currently retraining is user/API-triggered (`/v2/models/train`), whereas an autonomous OS/controller closed-loop scheduler automatically re-fitting conformal residuals (`Adaptive Conformal Inference`, Gibbs & Candès) on every new observation is a *proposed enhancement*, not yet an autonomous daemon.
- **Direct Storage Array Execution Hooks (CSI / SAN SMI-S / NVMe-oF)**: Currently intentionally disabled under zero-mutation shadow mode; hardware write/resize actuation is NOT implemented.
- **Hardware-In-The-Loop Multi-Month Real Production Validation**: Multi-array long-horizon field validation against real Dell/NetApp/Ceph 90-day block traces has NOT been executed yet (current tests use host OS disk reads, mocked Prometheus series, and deterministic benchmark series).
- **Online Brier Score Feedback Loop Adjusting Ensemble Weights Dynamically**: Current `verify-outcome` logs discrepancy audits in `RecommendationVerification`; feedback adjustments back into `ModelVersion` weighting remain partially decoupled (`sentinel` recalibration vs `v2` champion-challenger).

---

## 4. Expected Technical Effect & Limitations

- **Expected Technical Effect**: Measurably bounds under-coverage when collector telemetry degrades (widening `P10–P90` bands via $\gamma$ rather than silently failing) and prevents downstream operational actions from executing on unverified or infeasible state trajectories — reducing storage SLA breaches and false intervention scheduling.
- **Known Technical Limitations**:
  - Minimum 60 chronological points required for `ChampionChallengerEngine` training (volume below 60 samples cannot produce ML predictions).
  - SARIMAX convergence may fall back across `(1,1,1) -> (1,1,0) -> (0,1,1)` or fail gracefully if series variance is near zero.
  - Digital Twin throughput/latency physics penalties use deterministic heuristic models calibrated to device metadata rather than full discrete-event kernel block-queue simulation.
