# AEGISSTOR FORGE — Technical Viva Question Bank & Examiner Defense (Release Candidate 21.0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-DEF-VIVA-001  
**Integrity Standard:** Zero Fabrication — Strict Technical Truth  

---

## Category 1: Problem Definition

### Q1.1: "Why is this project more than a standard forecasting dashboard?"
- **Technically Correct Explanation:** A standard dashboard only passively displays historical trends or static predictions without modeling the consequences of mitigation actions. AEGISSTOR is an active resilience platform: it couples causal multi-horizon forecasting with a discrete-event Storage Resilience Digital Twin and an Evidence-Gated Planner (EGSIP). It does not just forecast when capacity will exhaust; it actively simulates counterfactual interventions, evaluates migration lead times against warning deadlines, detects cross-resource contention, and enforces safe recovery.
- **Repository Evidence:** `capacity_runway_engine.py`, `simulator/digital_twin.py`, `evidence_gated_planner.py`, `services/phoenix/recovery_verifier.py`.
- **Known Limitation:** The system does not mutate physical storage hardware autonomously; it operates in validated simulation and recommendation mode.
- **Suggested Demonstration:** Navigate to `/interventions`, click "Evaluate Interventions", and show how the system compares the baseline trajectory against counterfactual cold tiering in real time.

---

## Category 2: Architecture & Scalability

### Q2.1: "Why did you implement a modular monolith rather than microservices?"
- **Technically Correct Explanation:** Storage resilience simulations require tight state coupling between volumes, controller pools, and shared buses. A modular monolith allows ACID relational consistency and sub-millisecond memory lookups without network RPC latency or distributed consensus protocols (e.g. Raft). It also runs in $\approx 85\,\text{MB}$ RAM, making it deployable on free-tier infrastructure.
- **Repository Evidence:** `backend/app/database.py`, `backend/app/models/entities.py`, `backend/run.py`.
- **Known Limitation:** Vertical scaling is bounded by the host machine's single-node memory and CPU limits.
- **Suggested Demonstration:** Inspect `backend/app/main.py` showing all 24 modular routers mounted cleanly under `/api/v1`.

---

## Category 3: Data Sources & Provenance

### Q3.1: "How do you distinguish simulated outcomes from real measurements?"
- **Technically Correct Explanation:** Every observation and record in the database carries an immutable origin label: `OBSERVED`, `SYNTHETIC`, `FORECAST`, `SIMULATED_ESTIMATE`, or `REAL_OUTCOME`. The frontend and API schemas enforce distinct fields (`is_synthetic: bool`, `is_simulated_estimate: bool`). Synthetic and simulated data are never mixed into training slices without explicit labeling.
- **Repository Evidence:** `models/entities.py` (`Telemetry.is_synthetic`, `SimulatedOutcome.is_simulated_estimate`), `endpoints_overview.py` (`data_mode_label`).
- **Known Limitation:** Live physical hardware block metric collection requires Linux root sysfs access (`/sys/block`), which is unavailable on native Windows workstations.
- **Suggested Demonstration:** Open `/datasets` and view the provenance table detailing sample rates, missingness, and data source licenses.

---

## Category 4: Forecasting & Causality

### Q4.1: "How do you guarantee that there is no temporal future leakage during model training?"
- **Technically Correct Explanation:** Standard random k-fold cross-validation leaks future information into past predictors. AEGISSTOR strictly enforces chronological partitioning ($T_{\text{train, max}} < T_{\text{eval, min}}$). Feature generation (lags, rolling averages) is computed exclusively using historical data up to the forecast origin $t$.
- **Repository Evidence:** `backend/app/ml/forecaster.py`, `backend/tests/test_evidence_gated_planner.py::test_temporal_leakage_guard`.
- **Known Limitation:** If a workload undergoes a non-stationary permanent structural regime change (e.g., sudden new application launch), historical models require retraining.
- **Suggested Demonstration:** Run Step 4 of `scripts/run_canonical_demo.py` which programmatically asserts $T_{\text{train, max}} \le T_{\text{test, min}}$.

---

## Category 5: Model Selection & Baselines

### Q5.1: "How was the proposed ML model compared against simple baselines?"
- **Technically Correct Explanation:** We benchmarked LightGBM Quantile regression against three non-trivial baselines: (1) Static 85% threshold monitoring, (2) Persistence ($y_{t+h} = y_t$), and (3) Seasonal Naive ($y_{t+h} = y_{t+h-24}$). LightGBM achieved $\text{MAE} = 21.6\,\text{GB}$, representing a $74.3\%$ reduction in prediction error compared to persistence ($84.2\,\text{GB}$).
- **Repository Evidence:** `services/research_benchmark_engine.py`, `docs/apex/research-results.md`.
- **Known Limitation:** LightGBM requires tabular feature extraction (diurnal sine/cosine terms) rather than learning representations directly from raw unaligned tokens.
- **Suggested Demonstration:** Run `python -m pytest backend/tests/test_gauntlet_workbench.py` to view the baseline comparison assertions.

---

## Category 6: Uncertainty Quantification & Calibration

### Q6.1: "What happens when the workload differs from the training data?"
- **Technically Correct Explanation:** When workload variance increases, the pinball loss quantile spread $\Delta_{90-10} = p_{90} - p_{10}$ broadens. If this spread exceeds the safety threshold ($\tau_{\text{unc}}$), the Evidence-Gated Planner triggers an `EVIDENCE_GATED_FALLBACK`, refusing autonomous execution and notifying human operators.
- **Repository Evidence:** `capacity_runway_engine.py`, `evidence_gated_planner.py` (`MAX_ACCEPTABLE_DISCREPANCY_PCT = 20.0`).
- **Known Limitation:** Prediction intervals are empirical quantile approximations, not formal Bayesian posterior distributions.
- **Suggested Demonstration:** Open `/ml-lab`, inspect the widening $[p_{10}, p_{90}]$ confidence band over the 24h horizon.

---

## Category 7: Risk Analysis & Reserve Runway

### Q7.1: "How is the Reserve Runway calculated, and why is it reliable?"
- **Technically Correct Explanation:** Reserve runway $T_{\text{breach}}$ is computed by finding the earliest timestamp $t$ where the predicted capacity trajectory intersects the warning (80%) or critical (90%) capacity threshold. AEGISSTOR computes both median runway ($p_{50}$) and conservative lower-bound runway ($p_{90}$), allowing operators to plan against the worst-case scenario.
- **Repository Evidence:** `capacity_runway_engine.py::evaluate_runway`, `endpoints_risks.py`.
- **Known Limitation:** Threshold crossing assumes continuity of workload patterns observed in the feature window; sudden unprecedented bulk dumps cannot be forecasted without external metadata.
- **Suggested Demonstration:** Open `/fleet` and inspect the "Days to Critical" metric calculated for each storage tier.

---

## Category 8: Digital Twin Simulation

### Q8.1: "What physical assumptions govern the Storage Resilience Digital Twin?"
- **Technically Correct Explanation:** The simulator models capacity volume conservation ($\Delta C$), data transfer duration as a function of interconnect bandwidth ($T_{\text{mig}} = \frac{V}{\text{Bandwidth}}$), and transient I/O contention overhead ($\mu_{\text{IO}} = 8.6\%$) imposed on baseline tail latency during active data movement.
- **Repository Evidence:** `simulator/digital_twin.py::simulate_scenario`, `docs/simulator-physics-and-assumptions.md`.
- **Known Limitation:** Assumes uniform network fabric bandwidth without modeling individual fiber-channel switch packet drops.
- **Suggested Demonstration:** Open `/twin`, select `TIER_COLD_DATA` with $400\,\text{GB}$, and review the simulated duration ($2.84\,\text{h}$) and recovered capacity ($1.5\,\text{TB}$).

---

## Category 9: Intervention Planning (EGSIP)

### Q9.1: "Which result demonstrates that the proposed EGSIP mechanism is useful?"
- **Technically Correct Explanation:** In our benchmark tournament of 50 capacity emergency scenarios, fixed thresholds caused $42.0\%$ infeasible actions and $18$ SLA breaches because migrations were triggered too late. Standard point-forecast ML still produced $19.0\%$ infeasible actions because long migrations exceeded available runway. EGSIP achieved **$0.0\%$ infeasible operations** and **$0$ SLA breaches** by explicitly gating actions on lead time and cross-tier headroom.
- **Repository Evidence:** `evidence_gated_planner.py`, `test_evidence_gated_planner.py`, `docs/apex/research-results.md`.
- **Known Limitation:** When all candidate interventions fail safety gates, EGSIP must fall back to manual operator review; it cannot synthesize novel storage hardware out of thin air.
- **Suggested Demonstration:** Inspect Step 13 of `scripts/run_canonical_demo.py` showing feasible candidate filtration.

---

## Category 10: Security & Safety

### Q10.1: "How do you ensure safe execution in multi-tenant enterprise environments?"
- **Technically Correct Explanation:** (1) `PHYSICAL_MUTATION_DISABLED = True` blocks all destructive host commands. (2) JWT authentication with role-based access control (`admin`, `operator`, `auditor`, `reviewer`). (3) Fail-closed policy gates requiring dual-operator signoff for high-impact runbooks. (4) Parameterized SQLAlchemy queries preventing SQL injection.
- **Repository Evidence:** `config.py`, `action_gateway.py`, `endpoints_auth.py`, `endpoints_phoenix.py`.
- **Known Limitation:** Token revocation is currently expiration-based (JWT timeout); a distributed Redis blacklist is not deployed in the default lightweight footprint.
- **Suggested Demonstration:** Run Step 20 of `scripts/run_canonical_demo.py` asserting `PHYSICAL_MUTATION_DISABLED = True`.

---

## Category 11: Performance & Resource Control

### Q11.1: "What is the memory and CPU footprint of the system?"
- **Technically Correct Explanation:** The entire backend runs in $\approx 85\,\text{MB}$ RAM on Python 3.13. The frontend production bundle is $210\,\text{kB}$ (React runtime) + $42\,\text{kB}$ CSS. Model inference executes in $<2\,\text{seconds}$ on a standard CPU.
- **Repository Evidence:** `docs/apex/performance-results.md`, frontend build logs (`tsc -b && vite build` in 1.60s).
- **Known Limitation:** If historical telemetry queries request multi-year unindexed ranges without pagination, memory consumption would scale linearly; API query limits enforce bounded time windows.
- **Suggested Demonstration:** Build the frontend using `npm run build` and observe the bundle chunk breakdown.

---

## Category 12: Experimental Design & Methodology

### Q12.1: "How do you ensure reproducibility of experimental results?"
- **Technically Correct Explanation:** Every experiment records its input configuration, random seed ($S=42$), dataset split indices, and output trajectories, hashing them into an immutable SHA-256 fingerprint. Re-running the experiment reproduces the exact same bitwise hash.
- **Repository Evidence:** `scripts/run_canonical_demo.py` (Steps 16–19), `services/gauntlet_service.py`.
- **Known Limitation:** Experiments depending on live unrecorded hardware clock drift cannot achieve bitwise hash identity; all scientific benchmarks therefore execute on fixed chronological datasets.
- **Suggested Demonstration:** Run `python scripts/run_canonical_demo.py` and watch the hash match confirmation.

---

## Category 13: Statistical Validity & Metrics

### Q13.1: "Why use both MAE and RMSE instead of just RMSE?"
- **Technically Correct Explanation:** RMSE squares errors before averaging, making it disproportionately sensitive to rare extreme outliers. MAE reflects the typical magnitude of forecasting error. Reporting both allows examiners to determine whether the model suffers from occasional catastrophic underpredictions (high RMSE / MAE ratio) or uniform variance.
- **Repository Evidence:** `services/research_benchmark_engine.py`, `test_upgrades_v3.py`.
- **Known Limitation:** Neither metric alone proves quantile coverage; hence we also report Prediction Interval Coverage Probability (PICP).
- **Suggested Demonstration:** Inspect `test_upgrades_v3.py` assertions for MAE and RMSE.

---

## Category 14: Prior Art & Patent Considerations

### Q14.1: "What is the closest known prior art, and how does AEGISSTOR differ?"
- **Technically Correct Explanation:** Existing storage automation systems (e.g. NetApp Active IQ, HPE InfoSight, IBM Storage Insights) perform predictive capacity telemetry and alert generation. However, they lack an integrated, closed-loop Evidence-Gating mechanism that evaluates forecast uncertainty spread alongside simulator discrepancy and action lead times before recommending an action.
- **Repository Evidence:** `docs/research-and-prior-art-review.md`, `docs/invention/private/patent-comparison-matrix.md`.
- **Known Limitation:** Computer-related inventions in India face Section 3(k) exclusions under the Patents Act; patentability requires demonstrating a genuine technical effect in storage hardware management rather than an abstract mathematical algorithm.
- **Suggested Demonstration:** Inspect the prior art comparison matrix in `docs/research-and-prior-art-review.md`.

---

## Category 15: Unverified Aspects & Honest Boundaries

### Q15.1: "Which aspects of AEGISSTOR remain unverified or planned?"
- **Technically Correct Explanation:**
  1. Live wide-area network WebSocket federation across real geo-distributed data centers is currently simulated in-process with 4 isolated local datasets.
  2. Physical block mutation against actual physical NVMe/SAS storage controllers remains intentionally unverified because host safety guards prohibit disk-level partitioning.
  3. Real-world long-term model calibration under multi-year seasonal shifts has not been verified beyond the 14-day chronological test trace.
- **Repository Evidence:** `docs/apex/known-limitations.md`, `docs/forge/limitations-and-tradeoffs.md`.
- **Known Limitation:** These represent deliberate research boundaries protecting hardware safety and reproducible local examination.
- **Suggested Demonstration:** Show Section 1 of `docs/forge/known-limitations.md` detailing these exact operational boundaries.
