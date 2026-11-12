# AEGISSTOR — ML & Forecasting Methodology

## 1. Two-Model Champion-Challenger Architecture (`backend/app/ml/champion_challenger.py`)
1. **Model A — LightGBM (`LGBMRegressor`)**
   - Uses strictly causal lag features (`lag_1`, `lag_2`, `lag_6`, `lag_12`, `lag_24`), `delta_1`, rolling statistics (`rolling_mean_6`, `rolling_std_6`, `rolling_mean_24`), cyclical calendar features (`hour_sin`, `hour_cos`, `day_of_week`), and available exogenous telemetry.
2. **Model B — SARIMAX (`statsmodels.tsa.statespace.sarimax.SARIMAX`)**
   - State-space time-series model with exogenous cyclical covariates and fallback orders `[(1,1,1), (1,1,0), (0,1,1)]`.
3. **Reference Benchmark — Seasonal-Naive**
   - Used to verify whether trained ML models genuinely outperform simple seasonal persistence (`BEATS_BASELINE`, `TIES_BASELINE`, `WORSE_THAN_BASELINE`).

## 2. Chronological Validation & Uncertainty Calibration
- **Minimum Data Guard**: Requires `MIN_RECORDS = 60` chronological telemetry samples (and `>= 35` supervised sequences after 24h lagging). If insufficient, training refuses cleanly and preserves any existing champion model.
- **3-Way Chronological Split**: `64% Train | 16% Conformal Calibration | 20% Final Holdout Test` (no random shuffling, preventing temporal leakage), supplemented by 3-fold rolling-origin cross-validation (`_rolling_origin_cv_lgbm`).
- **Split Conformal Prediction (`Q10 / Q50 / Q90`)**: Finite-sample conformal quantile computed on held-out calibration residuals to produce calibrated 80% prediction intervals bounded by `[0, total_capacity]`.
- **Recorded Metrics**: `MAE`, `RMSE`, `R2`, `MAPE`, `WAPE`, `MASE`, `Pinball Loss`, `Interval Coverage`, and `Mean Interval Width`.
