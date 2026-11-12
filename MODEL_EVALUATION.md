# AEGISSTOR — Model Evaluation & Champion-Challenger Selection (`MODEL_EVALUATION.md`)

## 1. Chronological Evaluation Metrics
Both LightGBM (`LGBMRegressor`) and `SARIMAX` are evaluated on identical chronological held-out validation windows (`y_true`) using:
- **MAE** (`mean_absolute_error`): Mean absolute error in GB (and Bytes in `CapacityMLEngine`).
- **RMSE** (`sqrt(mean_squared_error)`): Root mean square error penalizing large capacity deviations.
- **R²** (`r2_score`): Computed only when held-out variance $> 10^{-12}$.
- **MASE** (`_compute_mase`): Mean Absolute Scaled Error relative to in-sample seasonal-naive differences (`m = 24` when history permits).
- **MAPE** (`_safe_mape`): Computed strictly when all observed targets $> 10^{-6}$; returns `None` otherwise to prevent divide-by-zero distortion.
- **Pinball Loss** (`_pinball_loss`): Mean asymmetric quantile loss across $q = 0.10$ and $q = 0.90$.
- **Prediction Interval Coverage & Mean Width**: Empirical fraction of validation targets falling inside `[q10, q90]` alongside average interval width.

## 2. Baseline Comparison Rule (`vs_baseline_status`)
Each candidate ML model RMSE is compared directly against `SeasonalNaiveBenchmark` RMSE on the identical validation slice:
- `BEATS_BASELINE`: `model_rmse < baseline_rmse * 0.98`
- `TIES_BASELINE`: `model_rmse <= baseline_rmse * 1.03`
- `WORSE_THAN_BASELINE`: `model_rmse > baseline_rmse * 1.03`

## 3. Champion Selection & Unreliable-Forecast Guard
1. Models are scored with a calibration-aware composite objective balancing RMSE, Pinball Loss, and coverage proximity to target nominal coverage (`0.80`).
2. The superior model is promoted (`is_active = True`, `is_selected = True`) while recording the runner-up challenger metrics side-by-side in `model_metrics`.
3. Previous active models remain safely preserved if candidate fitting fails due to insufficient records or numerical non-convergence.
4. When telemetry quality (`DataReliabilityProfile`) is `LOW` or stale, high-confidence forecast recommendations are automatically flagged/gated rather than reported as certain.
