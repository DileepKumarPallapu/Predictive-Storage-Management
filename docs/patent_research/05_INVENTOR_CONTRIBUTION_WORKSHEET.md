# AEGISSTOR — Inventor Contribution & Verification Worksheet (Research Task 5)

> **Legal Rule on Inventorship**: Under the Indian Patents Act, 1970 (Sections 2(1)(y), 6, and 28), inventorship is determined strictly by **who conceived of or contributed intellectually to the claimed technical features** — *not* merely project membership, supervisory roles, documentation formatting, or routine boilerplate coding. Incorrect inventorship can jeopardize enforceability or lead to revocation under Section 64. Final inventorship must be verified jointly by the team, academic supervisors, University Technology Transfer Office (TTO), and a registered Indian patent agent **after** potential claim topics are finalized.

---

## 1. Candidate Claimable Technical Modules (To Map Against Individuals)

| Technical Module Code | Subsystem in Repository | Core Technical Mechanism Requiring Conception Attribution |
| :--- | :--- | :--- |
| **TM-1** | `backend/app/services/data_reliability_engine.py` | 9-factor deterministic reliability scoring ($R \in [0,1]$) computing continuous `uncertainty_multiplier` $\gamma$ and gating automated recommendations at `LOW`/`STALE`. |
| **TM-2** | `backend/app/services/workload_regime_engine.py` | Combined detrended lag-periodicity autocorrelation + slope convexity + Z-score burst + KS/PSI drift state classifier preventing tiny oscillations from misclassifying trended ramps. |
| **TM-3** | `backend/app/ml/champion_challenger.py` | Chronological 3-way Split Conformal calibration across LightGBM (with missing-feature zero-fabrication filter) vs SARIMAX vs SeasonalNaiveBenchmark using coverage-penalized champion cost. |
| **TM-4** | `backend/app/services/capacity_risk_engine.py` | Residual-CDF threshold-crossing probability + expected shortfall propagation scaled by $\sqrt{h}\cdot \gamma$ and audited via Brier self-check. |
| **TM-5** | `backend/app/services/decision_optimizer.py` & `backend/app/simulator/digital_twin.py` | Constrained counterfactual intervention optimizer separating feasible vs constraint-violating actions while gating/omitting financial metrics when unit rates are absent. |
| **TM-6** | `backend/app/collector/connector_registry.py` & `endpoints_recommendations.py` | Idempotent read-only collector normalization + strict non-execution 5-state shadow governance and outcome discrepancy feedback loop. |

---

## 2. Contributor Attribution Table (To Be Completed & Signed Off by Team & Institution)

| Full Legal Name | Institutional Affiliation / Role | Email / ID | Exact Technical Conception Contributed *(cite specific algorithms, formulas, or architectural integrations; leave blank if non-inventive)* | Repository Files / Commits Authored *(Evidence Link)* | Contributor Type *(Pre-Review Draft: Candidate Inventor / Implementer Under Direction / Advisor / Administrative)* | Verification Sign-Off (Team + Faculty + TTO Initials & Date) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dileep Kumar Pallapu** *(Team Member — verify exact scope)* | Developer / Student Researcher *(Verify university details)* | `[Verify Institutional Email]` | `[Specify exact technical contributions conceptualized vs implemented]` | `[Link git commits / PRs]` | *To be evaluated by Patent Agent* | `[Pending]` |
| `[Additional Co-Developer / Member 2]` | `[Student / Researcher / Faculty]` | `[Email]` | `[Describe conception of TM-1..TM-6 or state "No inventive conception — implementation/UI only"]` | `[Commits]` | *Pending review* | `[Pending]` |
| `[Faculty Guide / Supervisor]` | `[Department / University]` | `[Email]` | `[Under Indian patent law, general supervision or funding without conception of a specific claim element is NOT inventorship — record accurately]` | `[Supervision notes]` | *Supervisor (Verify whether inventive contribution occurred)* | `[Pending]` |

---

## 3. Institutional Ownership & University IP Policy Checklist

- [ ] Verify whether university IP policy claims ownership (or co-ownership / revenue sharing) over student/funded capstone research outputs.
- [ ] Identify whether any open-source dependencies (`lightgbm` MIT, `statsmodels` BSD-3-Clause, `scikit-learn` BSD-3-Clause, `React` MIT, `FastAPI` MIT) impose disclosure or attribution obligations on commercial filings (open-source usage does not bar patenting novel system combinations implemented using those libraries, provided third-party libraries themselves are not claimed as novel).
- [ ] Confirm no public thesis upload, GitHub public repository release, conference poster, or live URL disclosure triggers non-grace-period loss of novelty (**Critical Note on Section 29–34 of Indian Patents Act**: avoid public disclosure before filing a Provisional/Complete Application, or verify statutory 12-month display exceptions strictly with a patent agent!).
- [ ] Collect signed No-Objection / Assignment declarations (Form 1 endorsement / proof of right under Section 7(2) within **6 months** of filing if applicant differs from inventors).
