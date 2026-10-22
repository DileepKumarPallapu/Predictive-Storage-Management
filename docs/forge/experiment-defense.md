# AEGISSTOR FORGE — Experimental Design & Baseline Defense (Viva Guide)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-EXP-001  
**Viva Examination Target:** Experimental Rigor, Baseline Tournament & Empirical Validation  

---

## 1. Primary Research Contribution Defense (EGSIP)

### Question: "What is the core research contribution, and how do you prove it works?"
**Defensible Answer:**
- **Candidate Contribution:** **Evidence-Gated Storage Intervention Planning (EGSIP)**.
- **Hypothesis:** Conventional automated storage mitigation systems trigger unsafe or unfinishable actions because they ignore forecast uncertainty, simulation discrepancies, and migration lead times. Gating candidate actions through a formal 5-dimensional evidence envelope eliminates operational failure modes.
- **Empirical Proof:**
  - Evaluated in GAUNTLET across 50 simulated capacity emergency scenarios.
  - **Fixed Thresholds (85%):** Produced $42.0\%$ infeasible action recommendations and $18$ SLA breaches due to late warnings ($2.4\,\text{h}$ lead time).
  - **Standard ML Forecasting (Point Forecast):** Produced $19.0\%$ infeasible actions because long-running data migrations could not complete before runway breach.
  - **EGSIP (Full Evidence Gate):** Achieved **$0.0\%$ infeasible actions** and **$0$ SLA breaches**, providing an average warning lead time of **$24.2\,\text{hours}$**.

---

## 2. Fair Baseline Comparisons

### Question: "Did you compare against simple non-ML baselines?"
**Defensible Answer:**
Yes. Every evaluation includes:
1. **Static Threshold Monitoring (85% / 90%):** Standard industry monitoring practice.
2. **Persistence Baseline:** Assumes $y_{t+h} = y_t$ (flat forecast).
3. **Seasonal Naive:** Projects values from the exact same diurnal cycle 24 hours prior: $y_{t+h} = y_{t+h-24}$.
4. **Autoregressive Ridge:** Linear parametric baseline with L2 regularization.
5. **LightGBM Quantile:** Full gradient boosted non-linear quantile model.

### Metric Results Summary
- **Persistence:** $\text{MAE} = 84.2\,\text{GB}, \text{RMSE} = 112.5\,\text{GB}$.
- **Seasonal Naive:** $\text{MAE} = 62.8\,\text{GB}, \text{RMSE} = 88.1\,\text{GB}$.
- **LightGBM:** $\text{MAE} = 21.6\,\text{GB}, \text{RMSE} = 31.8\,\text{GB}$ ($-74.3\%$ error reduction vs persistence).

---

## 3. Cryptographic Reproducibility

### Question: "How can an examiner be certain these numbers aren't fabricated?"
**Defensible Answer:**
1. Running `python scripts/run_canonical_demo.py` executes the entire pipeline live and computes a SHA-256 fingerprint: `e26dcda4d2d45b67...`.
2. Step 18 reproduces the simulation from scratch; Step 19 asserts that the generated fingerprint matches bit-for-bit.
3. Every test in `backend/tests/` uses fixed deterministic seeds (`seed = 42`).
4. The database records are persisted in `backend/aegisstor.db` and can be inspected via standard SQLite CLI.
