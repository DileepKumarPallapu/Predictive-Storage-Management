# AEGISSTOR — Prior-Art Research Report & Feature Comparison Matrix (Research Tasks 1 & 2)

> **Preparation Notice**: This document is preliminary technical and prior-art research preparation for the university project *AEGISSTOR — Predictive Storage Capacity and Performance Management Based on Machine Learning*. It does **not** constitute legal advice, a formal Freedom-to-Operate (FTO) clearance, or a patentability opinion, and must be reviewed by a registered Indian patent agent or IP counsel.

---

## 1. Search Scope & Methodology

Searches were executed across patent disclosures indexed in **Google Patents**, **WIPO PATENTSCOPE**, **European Patent Office (Espacenet)**, **Indian Patent Office (IPO / InPASS query templates)**, and **academic peer-reviewed / preprint repositories (arXiv, NeurIPS, JMLR)**. Search terms combined:
- `"predictive storage capacity forecasting" + "machine learning" + "threshold crossing"`
- `"storage telemetry data quality" + "gating" + "time series" + "model selection"`
- `"digital twin" + "storage capacity optimization" + "workload regime"`
- `"conformal prediction" + "time series" + "change points" + "cloud workload"`

---

## 2. Verified Prior-Art Catalog

References are grouped explicitly into **Granted Patents**, **Pending / Published Patent Applications**, and **Academic / Technical Publications**.

### A. Granted Patents

| Reference No. | Document Type & Jurisdiction | Title | Publication / Issue Date | Earliest Priority / Filing Date | Assignee / Applicant | Technical Problem & Claimed Mechanism | Overlap with AEGISSTOR | Potential Distinction / Gap Analysis |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **US10949116B2** | Granted Patent (USPTO) | *Storage resource capacity prediction utilizing a plurality of time series forecasting models* | 2021-03-16 | 2019-07-30 | EMC IP Holding Company LLC | Single capacity forecasting model underperforms across diverse storage trends; extracts historical storage utilization, runs multiple time-series forecasting models concurrently, evaluates/filters predictions, and aggregates/selects subsets to tune provisioning. | Concurrent multi-model time-series forecasting (`ChampionChallengerEngine`), error-based selection across models, storage provisioning threshold linkage. | **Potential distinction:** US10949116B2 does not teach coupling a 9-factor deterministic `DataReliabilityEngine` score (`0..1`) both to widen **Split Conformal Prediction** uncertainty intervals and to gate high-confidence automated interventions when telemetry is `LOW`/`STALE`, nor does it combine empirical residual-CDF Brier validation with constrained Digital Twin counterfactual rejection. *(Note: Multi-model selection itself IS clearly disclosed here.)* |
| **US11750468B2** | Granted Patent (USPTO) | *Proactive asset failure remediation utilizing conformal asset state prediction* | 2023-09-05 | 2021-06-14 (App. 17/346,398) | Dell Products L.P. | Reactive IT asset alerts miss failure lead time or misprioritize support tickets; applies a **conformal prediction framework** to historical state transitions & time-series operational telemetry to predict future asset states with bounded confidence and adjust remediation priority. | Uses conformal prediction over IT infrastructure time-series telemetry for proactive threshold/state prediction and bounded confidence. | **Close overlapping art.** AEGISSTOR differs by applying Split Conformal intervals specifically to **capacity exhaustion / safety-threshold probability** scaled dynamically by a 9-factor `uncertainty_multiplier` paired with **LightGBM vs SARIMAX** champion-challenger selection and multi-constraint (`budget`, `max_latency`, `max_transfer_gb`) counterfactual planning. A patent agent must examine US11750468B2's independent claims closely. |
| **US12153647B2** | Granted Patent (USPTO) | *Scalable capacity forecasting in storage systems using a machine learning model* | 2024-11-26 | *(Verify family continuation chain in USPTO PAIR)* | Commvault Systems, Inc. | Scaling capacity forecasts across heterogeneous enterprise storage nodes via ensemble/tree ML models over historical capacity telemetry. | Machine-learning-based storage capacity forecasting across arrays and capacity tiers. | Does not emphasize Split Conformal calibration under data-reliability gating (`LOW`/`STALE` recommendation suppression) or LightGBM-vs-SARIMAX regime-aware champion selection. |
| **US7783510B1** | Granted Patent (USPTO) | *Computer storage capacity forecasting system using cluster-based seasonality analysis* | 2010-08-24 | 2006-06-23 | Quest Software, Inc. | Storage capacity forecasts fail when seasonal cycles and level shifts distort linear trend projections; decomposes time series into trend & seasonal parts, detects level shifts/outliers via cluster-based seasonality & Fourier analysis. | Storage capacity forecasting with explicit seasonality/periodicity detection and level-shift decomposition. | Pre-dates LightGBM gradient boosting, Split Conformal finite-sample calibration, and constrained Digital Twin optimization. Confirms seasonality decomposition and shift detection in storage forecasting are well-established prior art. |
| **US11228645B2** | Granted Patent (USPTO) | *Digital twin of IT infrastructure* | 2022-01-18 | 2020-03-27 | Microsoft Technology Licensing, LLC | Difficulty simulating IT infrastructure configuration & capacity changes safely offline; crawls topology & telemetry, constructs a cloud/virtual **Digital Twin** replica for testing and simulation. | Non-destructive Digital Twin simulation grounded in real collected storage topology and telemetry (`PageStorageDigitalTwin` + `get_real_storage_topology`). | Focuses on infrastructure discovery/provisioning blueprints rather than coupling conformal threshold-crossing probability CDFs and 9-factor reliability multipliers into hard constraint optimization (`DecisionOptimizer`). |
| **US11960348B2** | Granted Patent (USPTO) | *Cloud-based monitoring of hardware components in a fleet of storage systems* | 2024-04-16 | 2016-09-07 | Pure Storage, Inc. | Fleet-wide distributed storage array telemetry aggregation, wear tracking, and proactive maintenance alerts. | Read-only fleet storage telemetry collection (`ConnectorRegistry`), staleness tracking, proactive capacity/health alerts. | Covers fleet monitoring & lifecycle alerting rather than coupled LightGBM/SARIMAX champion-challenger selection + reliability-scaled conformal prediction + non-execution human-in-the-loop shadow planning. |
| **US11500829B2 / US11609885B2** | Granted Patents (USPTO) | *Adapting time series database schema / plurality of TSDB schemas* | 2022-11-15 / 2023-03-21 | 2019-07-19 | VMware, Inc. | Adapting TSDB storage schemas to incoming metric workload patterns and ingestion rates. | Workload-pattern identification over infrastructure time-series telemetry. | Targets database schema storage layout rather than capacity exhaustion conformal forecasting or constrained intervention ranking. |

### B. Published Patent Applications (Pending / Pre-Grant Disclosures)

| Reference No. | Document Type & Jurisdiction | Title | Publication Date | Earliest Priority / Filing Date | Applicant / Assignee | Technical Problem & Disclosed Mechanism | Overlap with AEGISSTOR | Potential Distinction |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **US20210034278A1** | Published App. (USPTO — parent pub of US10949116B2) | *Storage resource capacity prediction utilizing a plurality of time series forecasting models* | 2021-02-04 | 2019-07-30 | EMC IP Holding Company LLC | Concurrent execution & error-based filtering of multiple time-series capacity models. | Direct overlap with multi-model candidate selection. | See US10949116B2 analysis above. |
| **WO2019195039A1** | Published PCT App. (WIPO) | *Anomaly detection and processing for seasonal data* | 2019-10-03 | 2018-03-29 | *(PCT applicant record — verify exact assignee via WIPO)* | Seasonal compute telemetry produces false alarms on periodic spikes; decomposes trend & seasonal components to reduce false-positive alerts. | Separates periodic workload seasonality (`PERIODIC_SEASONAL`) from abnormal bursts (`SUDDEN_BURST`). | Focuses on anomaly filtering rather than driving Split Conformal prediction band widths and constrained capacity optimization. |
| **US20230396511A1** | Published App. (USPTO) | *Capacity Aware Cloud Environment Node Recovery System* | *(Published 2023; verify exact date)* | 2022-06-06 (App. 17/833,238) | Microsoft Technology Licensing, LLC | Combines multi-dimensional capacity health telemetry prediction with node recoverability status before scheduling node recovery. | Evaluates predicted capacity health + operational feasibility constraints prior to scheduling interventions. | Focuses on cloud compute node recovery rather than storage capacity Digital Twin optimization under missing-cost honesty and reliability-gated conformal bounds. |
| **US20220342401A1** | Published App. (USPTO) | *Systems and methods for production-line optimization* | 2022-10-27 | 2020-01-02 | Georgia-Pacific LLC | Evaluates positive fill gradients toward breach thresholds using operational telemetry & optimization rules. | Threshold-crossing monitoring over fill-level gradients. | Manufacturing domain; distinct technical architecture from enterprise storage ML forecasting & conformal risk. |

> **Indian Patent Office (InPASS) Note**: Public keyword search strategies for `IN202*` series filings (`("predictive storage" OR "storage capacity management") AND ("digital twin" OR "telemetry")`) are documented below; **direct live scraping against InPASS CAPTCHA/portal was not bypassed**, so a registered Indian patent agent must execute a formal InPASS full-text clearance query prior to filing in India.

### C. Academic & Technical Literature

| Citation | Year | Authors / Venue | Core Mechanism | Overlap & Impact on Novelty |
| :--- | :--- | :--- | :--- | :--- |
| **Adaptive Conformal Inference Under Distribution Shift** | 2021 / 2024 | Isaac Gibbs & Emmanuel J. Candès (*NeurIPS 2021*; *JMLR 2024*) | Updates conformal quantile target $\alpha_t$ dynamically online across non-exchangeable, distribution-shifted time series. | Establishes mathematical foundation for conformal prediction intervals under distribution shift; AEGISSTOR cannot claim novelty in Split or Adaptive Conformal Prediction *alone*. |
| **Conformal Prediction for Time-series Forecasting with Change Points (CPTC)** (`arXiv:2509.02844`) | 2025 | Sophia Huiwen Sun & Rose Yu (*arXiv:2509.02844*) | Integrates change-point detection directly with time-series conformal prediction to recalibrate intervals rapidly across regime shifts. | Directly overlaps with coupling `WorkloadRegimeEngine` changepoint detection + Split Conformal calibration; narrows standalone novelty of regime-aware conformal bands. |
| **Right-sizing Recommendations (RSR): Cloud Workload Conformal Prediction for VMs in Data Center Operations** (`arXiv:2607.24773`) | 2025 / 2026 | Mehryar Majd, Feng Cheng, Ali Pahlevan (*arXiv:2607.24773*) | Applies time-series conformal prediction bounds to generate risk-bounded cloud capacity right-sizing recommendations. | Demonstrates close convergence in cloud operations (using conformal intervals directly for resource sizing decisions). Distinguish AEGISSTOR's 9-factor `DataReliabilityEngine` uncertainty multiplier, LOW/STALE blocking gate, and dual LightGBM/SARIMAX selection. |

### Source URL Verification List
- EMC `US10949116B2` / `US20210034278A1`: Justia / Google Patents (`https://patents.google.com/patent/US10949116B2/en`)
- Dell `US11750468B2`: Google Patents (`https://patents.google.com/patent/US11750468B2/en`)
- Commvault `US12153647B2`: Google Patents (`https://patents.google.com/patent/US12153647B2/en`)
- Quest `US7783510B1`: Google Patents (`https://patents.google.com/patent/US7783510B1/en`)
- Microsoft `US11228645B2`: Google Patents (`https://patents.google.com/patent/US11228645B2/en`)
- Pure Storage `US11960348B2`: Google Patents (`https://patents.google.com/patent/US11960348B2/en`)
- VMware `US11500829B2` / `US11609885B2`: Google Patents (`https://patents.google.com/patent/US11500829B2/en`)
- Microsoft `US20230396511A1`: Google Patents (`https://patents.google.com/patent/US20230396511A1/en`)
- WIPO `WO2019195039A1`: Google Patents (`https://patents.google.com/patent/WO2019195039A1/en`)
- Gibbs & Candès (2024, JMLR): `https://jmlr.org`
- Sun & Yu (2025): `https://arxiv.org/abs/2509.02844`
- Majd et al. (2025/2026): `https://arxiv.org/abs/2607.24773`

*(Every HTTP source retrieved via search grounding in this session; exact full-text claims of US/WO patents must be inspected by a patent attorney before drafting claims.)*

---

## 3. Seven-Feature Prior-Art Comparison Matrix (Research Task 2)

| Reference | 1. Telemetry Quality-Aware Model / Action Gating | 2. Workload Regime-Aware Prediction | 3. Adaptive Model Selection (ML + Statistical) | 4. Leakage-Safe Forecast Uncertainty Calibration | 5. Probability of Threshold Crossing | 6. Multi-Resource Constraint Simulation (Digital Twin) | 7. Feedback-Based Recalibration / Verification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **US10949116B2** (EMC) | Partial (error filter) | No | **Yes** (multi-model subset selection) | Partial (prediction variance) | **Yes** (capacity threshold alerts) | Partial (provisioning tuning) | Partial |
| **US11750468B2** (Dell) | Partial (support/telemetry filter) | No | No explicit LightGBM/SARIMAX duel | **Yes** (conformal prediction bounds) | **Yes** (future asset state breach) | No explicit multi-constraint Digital Twin | **Yes** (remediation priority updates) |
| **US7783510B1** (Quest) | Partial (outlier filter) | **Yes** (cluster seasonality & shifts) | No (Fourier/decomposition) | Classical residual intervals | **Yes** | No | No |
| **US11228645B2** (Microsoft) | No explicit 9-factor score | Partial | No | No | Partial | **Yes** (IT Infrastructure Digital Twin) | Partial |
| **US11960348B2** (Pure Storage) | Partial (telemetry health) | No | No | No | **Yes** (fleet capacity/wear alerts) | No | Partial |
| **US20230396511A1** (Microsoft) | Partial | No | Unspecified prediction engine | No explicit conformal bounds | **Yes** (capacity health bounds) | Partial (node recoverability check) | No |
| **Sun & Yu (2025, CPTC)** | No | **Yes** (changepoint-coupled CP) | Single backbone | **Yes** (online conformal calibration) | No storage focus | No | **Yes** (online coverage updates) |
| **Majd et al. (2025/26, RSR)** | No | Implicit rolling | Single/ensemble | **Yes** (conformal right-sizing) | **Yes** (SLA capacity headroom) | Partial (cost right-sizing) | No Digital Twin constraint rejection |
| **AEGISSTOR (Implemented)** | **Yes** (9-factor score + `uncertainty_multiplier` + LOW/STALE block) | **Yes** (7 statistical regimes + KS/PSI drift) | **Yes** (`LGBMRegressor` vs `SARIMAX` vs `SeasonalNaiveBenchmark` w/ coverage penalty) | **Yes** (Chronological 3-way Split Conformal $\times \sqrt{h} \times \text{reliability}$) | **Yes** (empirical residual-CDF + Brier validation + shortfall) | **Yes** (Constrained Optimizer + Digital Twin non-executing shadow bounds) | **Yes** (`RecommendationVerification` discrepancy check + rolling retraining) |

### Key Combination Overlap Assessment
1. **Already Disclosed Combinations**:
   - Multi-model storage capacity selection + threshold prediction is squarely disclosed by **US10949116B2** (`EMC`).
   - Conformal prediction over IT operational telemetry for proactive remediation is squarely disclosed by **US11750468B2** (`Dell`) and academically by **Majd et al. (`arXiv:2607.24773`)**.
   - Changepoint/regime-aware conformal calibration is disclosed academically by **Sun & Yu (`arXiv:2509.02844`)**.
   - IT infrastructure Digital Twin simulation from crawled telemetry is disclosed by **US11228645B2** (`Microsoft`).
2. **Candidate Combined Technical Mechanism Requiring Deep Attorney Review**:
   - No single retrieved document explicitly teaches the **tightly coupled closed-loop pipeline** in which a quantitative **9-factor data-reliability score** simultaneously scales a **Split Conformal prediction half-width** ($\times \text{uncertainty\_multiplier}$), penalizes calibration error inside a **LightGBM-vs-SARIMAX champion-challenger selector**, feeds empirical residual-CDF **threshold-crossing risk & shortfall**, constrains a **Digital Twin / Decision Optimizer**, and **explicitly blocks high-confidence automated interventions when telemetry quality falls below threshold or becomes stale**.
   - *Caution*: Combining known building blocks is frequently rejected on **inventive step / obviousness** grounds unless backed by quantitative experimental proof of a **non-obvious technical synergy or system-level improvement** (e.g., maintaining target $\ge 80\%$ empirical coverage under corrupted/stale/bursty telemetry without triggering unsafe or infeasible storage interventions).
