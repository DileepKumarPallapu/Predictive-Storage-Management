# AEGISSTOR — India Patent Act Section 3(k) Analysis, CRI Guidelines & Agent Review Checklist (Research Task 6)

> **Non-Legal-Opinion Notice**: This analysis prepares technical framing notes under **The Patents Act, 1970 (as amended)** and the **Indian Patent Office (IPO) Guidelines for Examination of Computer Related Inventions (CRIs — 2017 & July 2025)**. It is **NOT a legal opinion** and does **NOT** determine patentability. Every question below must be evaluated by a **registered Indian Patent Agent**.

---

## 1. Statutory Context: Section 3(k) of the Indian Patents Act, 1970

Section 3(k) excludes from patentability:
> *"a mathematical or business method or a computer programme per se or algorithms."*

Key statutory & judicial principles confirmed from Indian jurisprudence and the **IPO CRI Guidelines (2017 & 2025 update)**:
1. **The "Per Se" Qualifier**: Courts (*Ferid Allani v. Union of India*, W.P.(C) 7/2014; *Microsoft Technology Licensing v. Assistant Controller*; *OpenTV*) held that software inventions producing a **further technical effect** or **technical contribution** solving a technical problem beyond executing code on a generic computer are *not* automatically barred as a "computer programme per se."
2. **Algorithms / Mathematical Methods**: Abstract formulas (OLS regression, Split Conformal quantiles, KS/PSI statistics) are **not patentable in isolation**. Under CRI Guidelines 2025 (including dedicated AI/ML provisions), patentability hinges on whether those techniques are tied concretely to technical infrastructure control, memory/storage resource integrity, latency SLA compliance, or telemetry pipeline adaptation—yielding measurable hardware/system-level technical improvements rather than purely administrative dashboards or financial/business rules.
3. **Novel Hardware Not Mandatory (Post-*Ferid Allani* / CRI 2025)**: Physical novelty in storage controller silicon is not strictly required if the system architecture yields a measurable technical effect across existing computing/storage hardware; however, examiners aggressively scrutinize whether claims merely recite "business/dashboard rules on general-purpose computers."

---

## 2. Section 3(k) Risk vs. Technical Effect Framing in AEGISSTOR

| Aspect in AEGISSTOR | Section 3(k) Vulnerability Risk | Candidate "Technical Effect" Framing for Patent Agent Assessment |
| :--- | :--- | :--- |
| **9-Factor Data Reliability Scoring + Conformal Uncertainty Scaling** | **Medium-High Risk** if drafted as an abstract scoring formula or UI gauge (`"calculating a weighted average score"`). | Frame as **preventing corrupted/stale storage controller telemetry from triggering physical over-allocation, premature block migration, or missed exhaustion states**, measurably improving empirical coverage reliability ($\ge 80\%$) under sensor dropouts. |
| **Champion-Challenger LightGBM vs SARIMAX Selection** | **High Risk** if drafted as `"running two standard ML algorithms and picking lower RMSE"` (also overlaps US10949116B2). | Anchor strictly to **exogenous missing-sensor zero-fabrication gating + calibration-penalized selection across non-stationary storage I/O & capacity streams**, tied to storage controller headroom guarantees. |
| **Digital Twin & Decision Optimizer (`budget_usd`, `unit_costs`)** | **Very High Business-Method Risk** under Section 3(k) if claims mention **USD budgets, procurement cost minimization, or dashboard approval workflows!** *(Business methods face an absolute bar in India.)* | **CRITICAL DRAFTING WARNING**: Any Indian patent claims MUST strip financial `budget_usd` / pricing terminology and restrict technical constraint claims strictly to **physical/computational invariants** (storage pool free margin, I/O tail latency SLA in ms, interconnect transfer bandwidth/volume GB, and read-only safety invariants). |
| **Read-Only Telemetry Adapters (`LinuxStorageConnector`, `/proc/diskstats`)** | Low technical effect alone (standard OS monitoring, cf. Pure Storage US11960348B2). | Use only as structural context anchoring claims to **real filesystem/block device telemetry pipelines**, not as standalone novelty. |

---

## 3. Official Indian Filing Materials, Deadlines & Fee Structure (Educational Institution / Small Entity Route)

Verify exact current statutory fees with the IPO Gazette at time of filing:
- **Required Initial Forms**:
  - **Form 1**: Application for Grant of Patent (with Proof of Right / assignment endorsement if applicant $\ne$ inventors within 6 months).
  - **Form 2**: Provisional Specification (secures priority date while completing multi-array field benchmarks — **Complete Specification MUST be filed within 12 months**!) OR Complete Specification (with Background, Technical Drawings, Detailed Description, Claims, Abstract).
  - **Form 3**: Statement and Undertaking under Section 8 (foreign filing status; within **6 months** of filing).
  - **Form 5**: Declaration as to Inventorship (with Complete Specification).
  - **Form 18** (or **Form 18A** Expedited Examination for eligible Educational Institutions/Startups): Request for Examination — statutory deadline **31 months** from earliest priority/filing date (under amended Patent Rules).
  - **Form 26**: Power of Attorney if filed through a Registered Patent Agent.
  - **Form 28**: Required if claiming **Educational Institution / Startup / Small Entity** fee reduction (~80% reduction: e.g., Form 1 e-filing ~₹1,600 vs ₹8,000 for large entities; Form 18 ~₹4,000 vs ₹20,000; zero extra fee for $\le 30$ specification pages & $\le 10$ claims).

---

## 4. Questions & Action Checklist for the Registered Indian Patent Agent

- [ ] **Prior-Art Deep Claim Charting**: Compare exact independent claims of **US11750468B2** (Dell Conformal Prediction), **US10949116B2** (EMC Multi-Model Capacity), **US12153647B2** (Commvault ML Capacity), **US11228645B2** (Microsoft Digital Twin), plus arXiv preprints (`arXiv:2509.02844`, `arXiv:2607.24773`) against AEGISSTOR's coupled mechanism.
- [ ] **InPASS Full-Text Search Execution**: Run Indian Patent Office (InPASS) searches for `IN202*` applications matching storage forecasting / digital twins / conformal reliability gating.
- [ ] **Public Disclosure & GitHub / Vercel Risk Assessment (CRITICAL!)**: The team previously discussed pushing to GitHub (`Predictive-Storage-Management`) and Vercel deployments; verify **immediately** with the Patent Agent whether public code commits, live URLs, or thesis submissions have already triggered prior-art self-disclosure destroying absolute novelty in India/EPO (except narrow Section 29–34 / 12-month US provisional rules — *do NOT assume grace applies!*).
- [ ] **Section 3(k) Technical-Effect Claim Architecture**: Remove all "business/financial/cost budget" phrasing from candidate Indian claims; anchor claims to storage array IOPS latency SLAs, block pool exhaustion prevention, and sensor-reliability conformal bounds.
- [ ] **Experimental Evidence Gate**: Decide whether to file a **Provisional Specification (Form 2)** first while collecting 90-day real storage array traces per `03_EXPERIMENTAL_VALIDATION_PLAN_AND_TEMPLATE.md`.
- [ ] **Inventorship & University TTO Clearance**: Audit `05_INVENTOR_CONTRIBUTION_WORKSHEET.md` and secure institutional NOC / ownership agreement.
