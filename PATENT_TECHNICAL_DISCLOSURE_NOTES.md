# AEGISSTOR — Preliminary Patent Technical Disclosure Notes (`PATENT_TECHNICAL_DISCLOSURE_NOTES.md`)

> **Disclaimer:** Prepared solely as technical architecture notes for review by a registered Indian patent agent. Makes no representation of legal patentability; contains zero fabricated prior-art claims or invented experimental results.

For the full multi-document research package (`01_PRIOR_ART_AND_FEATURE_MATRIX.md` through `06_INDIA_PATENT_SECTION3K_AND_CHECKLIST.md` and `experimental_results_observed.json`), see [`docs/patent_research/`](docs/patent_research/).

## Summary of Candidate Integrated Technical Mechanism (Verified in Codebase)
The potentially distinguishable system coupling implemented in AEGISSTOR spans 7 linked software engines rather than isolated threshold monitors:
1. **9-Factor Telemetry Reliability Scoring (`app/services/data_reliability_engine.py`)**: Quantifies completeness, freshness, continuity, duplicate rate, invariant violations, and source availability into composite score $R \in [0, 1]$, staleness boolean, uncertainty multiplier $\gamma \ge 1.0$, and automated recommendation gate.
2. **Statistical Workload Regime & Drift Analysis (`app/services/workload_regime_engine.py`)**: Combines rolling growth slopes, lag-24 autocorrelation, burst Z-scores, change-point detection, KS-test, and PSI drift metrics.
3. **Calibration-Aware Champion-Challenger Selection (`app/ml/champion_challenger.py`)**: Trains multivariate causal `LGBMRegressor` and `SARIMAX` (using observed exogenous metrics only when $\ge 70\%$ populated), compares against `SeasonalNaive`, and selects using point accuracy + quantile interval quality.
4. **Reliability-Scaled Split Conformal Intervals**: Calibrates conformal bounds on chronological held-out validation splits and scales horizon uncertainty by $\sqrt{h} \cdot \gamma$.
5. **Empirical Residual-CDF Threshold Risk (`app/services/capacity_risk_engine.py`)**: Computes threshold-crossing probability, runway bounds, and expected shortfall directly from calibrated prediction distributions.
6. **Constraint-Bounded Non-Destructive Digital Twin (`app/simulator/digital_twin.py`, `app/services/decision_optimizer.py`)**: Evaluates expansion, tiering, and workload redistribution under capacity headroom and latency SLA envelopes prior to human shadow approval.
7. **Closed-Loop Outcome Verification (`app/api/v1/endpoints_recommendations.py`, `outcome_ledger.py`)**: Compares post-action measured telemetry against simulated counterfactual expectations and records discrepancies in a hash-chained `AuditLog`.
