# AEGISSTOR ATLAS — Digital Twin Calibration Methodology

## 1. Mathematical Formulation
Let $\{y_t\}_{t=1}^{T}$ denote the observed storage telemetry series for a given metric (e.g., capacity utilization \% or P95 tail latency ms) and let $\{\hat{y}_t(\theta)\}_{t=1}^{T}$ denote the counterfactual trajectory produced by `DigitalTwinSimulator` under parameter configuration $\theta$.

### Residual Error
$$e_t = y_t - \hat{y}_t(\theta)$$

### Evaluation Metrics
1. **Mean Absolute Error (MAE)**:
   $$\text{MAE} = \frac{1}{N} \sum_{t=1}^{N} |e_t|$$
2. **Root Mean Squared Error (RMSE)**:
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{t=1}^{N} e_t^2}$$
3. **Systematic Bias (Mean Error)**:
   $$\text{Bias} = \frac{1}{N} \sum_{t=1}^{N} e_t$$
   - $\text{Bias} > +0.5$: Simulator systematically **under-predicts** actual utilization.
   - $\text{Bias} < -0.5$: Simulator systematically **over-predicts** actual utilization.
   - $|\text{Bias}| \le 0.5$: Unbiased nominal operation.
4. **Epsilon-Guarded Relative Error**:
   $$\text{RelError} = \frac{1}{N} \sum_{t=1}^{N} \frac{|e_t|}{|y_t| + \epsilon}, \quad \epsilon = 10^{-4}$$
   $\epsilon$ prevents division-by-zero singularities during idle storage periods.

---

## 2. Chronological Separation & Leakage Prevention
Tuning a simulator on the same time window where its accuracy is reported is invalid scientific methodology.

ATLAS implements strict chronological splitting:
- **Calibration Window**: First $65\%$ of observations (default 14 days) used for model parameter alignment.
- **Held-Out Evaluation Window**: Trailing $35\%$ of observations (default 7 days) strictly reserved for out-of-sample discrepancy verification.
- **Invariant**: The simulator parameter configuration is never fitted or tuned against the held-out evaluation window.

---

## 3. Calibration State Machine

| State | Definition | Operational Consequence |
|:---|:---|:---|
| `NOT_CALIBRATED` | No calibration run executed for this target resource. | Simulator outputs flagged as unverified estimates. |
| `CALIBRATION_IN_PROGRESS` | Background calibration run actively calculating residuals. | Previous calibration remains active; no concurrent promotion. |
| `CALIBRATED_FOR_SPECIFIED_CONDITIONS` | Held-out RMSE within acceptable error bounds ($\le 5.0\%$). | Counterfactual simulations permitted within validated envelope. |
| `CALIBRATION_DEGRADATION_DETECTED` | Held-out RMSE exceeds $1.8\times$ training RMSE. | Alerts raised; simulator recalibration recommended. |
| `INSUFFICIENT_EVIDENCE` | Fewer than 48 hourly observations available. | Gating marks recommendations as `REQUIRES_ADDITIONAL_EVIDENCE`. |
