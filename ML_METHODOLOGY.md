# AEGISSTOR — Machine Learning Methodology (`ML_METHODOLOGY.md`)

**Primary Module:** `backend/app/ml/champion_challenger.py` (`ChampionChallengerEngine`) & `backend/app/ml/sklearn_engine.py` (`CapacityMLEngine`)

---

## 1. Eligibility & Data Quality Gate
Before training runs on any storage resource:
1. Telemetry rows are sorted strictly ascending by timestamp (`Telemetry.timestamp.asc()`).
2. Minimum chronological history check: **`MIN_RECORDS = 60`** valid points (`48` for `CapacityMLEngine`). If history is shorter, training aborts safely, explains the shortage, and **never overwrites previously active models**.
3. `DataReliabilityEngine.evaluate(db, storage_id)` computes the 9-factor composite reliability score $R \in [0, 1]$, staleness status, and uncertainty multiplier $\gamma \ge 1.0$. Low or stale profiles propagate wider uncertainty bounds and gate high-confidence recommendations.

## 2. Leak-Free Feature Engineering (`_build_dataframe`)
For each step $t$ predicting $y = \text{used\_gb}_{t+1}$:
- **Endogenous Causal Lags & Deltas**: `used_gb`, `free_gb`, `utilization_pct`, `lag_1`, `lag_2`, `lag_6`, `lag_12`, `lag_24`, `delta_1`.
- **Causal Rolling Windows**: `rolling_mean_6`, `rolling_std_6`, `rolling_mean_24` (computed exclusively over past/present points).
- **Cyclical Calendar Features**: `hour_sin`, `hour_cos`, `day_of_week`.
- **Filtered Exogenous Features**: `read_iops`, `write_iops`, `latency_p95_ms`, `throughput_mb_s` are included **only** if empirical non-null completeness $\ge 70\%$ and non-zero variation exists; unavailable sensors are explicitly excluded (`excluded_exog`) rather than synthesized.
- Zero future target information or unknown future IOPS/latency enters the feature vector.

## 3. Primary Models & Evaluation Baseline
1. **Model A — LightGBM (`LGBMRegressor`)**: Non-linear gradient boosted regression trees trained on the full causal feature matrix (`base_features + included_exog`), supplemented by chronological rolling-origin cross-validation (`_rolling_origin_cv_lgbm`).
2. **Model B — SARIMAX (`statsmodels`)**: Linear state-space time-series model capturing autoregressive trend/seasonality on `used_gb` alongside cyclical/telemetry exogenous covariates.
3. **Evaluation Benchmark — Seasonal-Naive**: Anchored seasonal difference persistence (`_seasonal_naive_predict`), used strictly as a reference benchmark rather than a primary candidate model.

## 4. Chronological Splits & Split Conformal Uncertainty Calibration
- Data is partitioned strictly in time order (zero random shuffling): **64% Train / 16% Calibration / 20% Test** (`validation`).
- Non-conformity residuals on the held-out Calibration window yield empirical conformal radius $q_{\text{conf}}$.
- Multi-horizon uncertainty bands `[P10, P50, P90]` expand monotonically with horizon $\sqrt{h}$ and data-reliability inflation multiplier $\gamma$ (`_evaluate_model_outputs`), clamped strictly within physical capacity bounds `[0, total_capacity]`.

## 5. Supported Forecast Horizons & Traceability
- Supported forecast horizons: **1, 7, 14, 30, 60, and 90 days** (`SUPPORTED_HORIZON_DAYS`).
- Every trained model stores `.joblib` binary weights on disk plus `model_versions` & `model_metrics` database records linking directly to persisted `forecasts` rows.
