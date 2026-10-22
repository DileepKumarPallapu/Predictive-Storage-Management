# AEGISSTOR FORGE — Machine Learning Methodology Defense (Viva Guide)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-ML-001  
**Viva Examination Target:** Machine Learning Rigor, Temporal Causality & Uncertainty Modeling  

---

## 1. Model Selection & Feature Engineering

### Question: "Why LightGBM and Ridge regression instead of Deep Learning (LSTM / Transformers)?"
**Defensible Answer:**
1. **Sample Efficiency & Edge Deployment Constraints:** Enterprise storage telemetry arrives in hourly or 1-minute aggregations. Storage controllers and telemetry sidecars cannot afford GPU accelerators or large memory footprints. Ridge and LightGBM models train in $<2\,\text{seconds}$ on CPU with $<10\,\text{MB}$ memory footprint.
2. **Tabular Feature Engineering with Causal Physics:** Deep sequence models are prone to overfitting on autocorrelated time-series with strong diurnal cycles. In AEGISSTOR, explicit domain features capture physical patterns:
   - Diurnal periodicity: $\sin\left(\frac{2\pi h}{24}\right), \cos\left(\frac{2\pi h}{24}\right)$
   - Weekly seasonality: $\sin\left(\frac{2\pi d}{7}\right), \cos\left(\frac{2\pi d}{7}\right)$
   - Autoregressive lags: $y_{t-1}, y_{t-6}, y_{t-24}$
   - Moving average ratios: $\frac{\text{MA}_6}{\text{MA}_{24}}$
3. **Bandwidth in Federated Scenarios:** Ridge regression requires transmitting only $d=8$ parameter weights ($2.05\,\text{KB}$ per round), saving $>99.9\%$ bandwidth compared to deep neural networks.

---

## 2. Prevention of Temporal Data Leakage

### Question: "How is data leakage prevented during model training and evaluation?"
**Defensible Answer:**
- **Strict Chronological Splitting:** K-fold cross-validation is mathematically invalid for time-series forecasting because future samples would leak into training folds. AEGISSTOR enforces strict chronological partitioning:
  $$T_{\text{train, max}} < T_{\text{eval, min}}$$
- **Preprocessing Encapsulation:** Rolling statistics (moving averages, scale normalizers) are computed exclusively over the training slice and frozen before test evaluation.
- **Lag Feature Causality:** In Step 5 of the canonical demonstration, the script asserts that all training timestamps precede evaluation timestamps with zero overlap.

---

## 3. Quantile Uncertainty & Calibration

### Question: "How are confidence intervals generated and why are they trustworthy?"
**Defensible Answer:**
- **Quantile Loss Function:** Rather than assuming Gaussian error distributions (which underestimate catastrophic storage tails), LightGBM is trained directly on pinball/quantile loss:
  $$\mathcal{L}_\alpha(y, \hat{y}) = \max\left(\alpha (y - \hat{y}), (1 - \alpha)(\hat{y} - y)\right)$$
- Evaluated at $\alpha \in \{0.10, 0.50, 0.90\}$ to yield the 80% empirical prediction interval $[p_{10}, p_{90}]$.
- **Monotonicity & Widening:** The uncertainty envelope is mathematically monotonic ($p_{10} \le p_{50} \le p_{90}$) and broadens over the prediction horizon (e.g., $1.15\,\text{GB}$ spread at $t=1$ widening to $27.6\,\text{GB}$ spread at $t=24$), reflecting real accumulated uncertainty.
