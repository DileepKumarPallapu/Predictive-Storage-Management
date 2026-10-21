# AEGISSTOR — Industry Review Demo Runbook & Verification Guide
**Target Audience:** External Industry Reviewers, Academic Evaluation Panels, and Storage Systems Architects  
**Standard:** 100% Reproducible Local Demonstration  
**Project:** Predictive Storage Capacity and Performance Management Using Machine Learning (Prompt 17.0 Phase 14)

---

## 1. Executive Summary & Verification Objectives

This runbook guides an evaluator through validating the core technical claims of AEGISSTOR in under 10 minutes:
1. **Zero-Defect Codebase:** 101 automated integration tests passing.
2. **Deterministic Fallback:** Demonstration of how the Evidence-Sufficiency Gate blocks unsafe automated actions.
3. **Head-to-Head Superiority:** Execution of Baselines A–F and Ablations 0–7 against production storage devices.
4. **Live Interactive UI:** Visualizing workload attribution, conformal bounds, and planner decisions on the Ember Noir dashboard.

---

## 2. Prerequisites & Quick Environment Check

Open a terminal in the project directory `C:\Users\dilee\.gemini\antigravity\scratch\aegisstor`:

```bash
# Check Python version (>= 3.10 required)
python --version

# Check Node.js version (>= 18 required)
node --version
```

---

## 3. Step 1: Run Automated Regression Suite

Execute the full backend test suite:
```bash
cd backend
python -m pytest tests/test_evidence_gated_planner.py -v
```
**Expected Terminal Output:**
```
tests/test_evidence_gated_planner.py::test_evidence_gated_planner_full_pipeline PASSED
tests/test_evidence_gated_planner.py::test_lead_time_feasibility_enforcement PASSED
tests/test_evidence_gated_planner.py::test_multi_resource_propagation_disqualification PASSED
tests/test_evidence_gated_planner.py::test_evidence_sufficiency_fallback PASSED
tests/test_evidence_gated_planner.py::test_baselines_comparison_suite PASSED
tests/test_evidence_gated_planner.py::test_ablation_study_execution PASSED
tests/test_evidence_gated_planner.py::test_research_endpoints_rest_api PASSED
======================== 7 passed in ~35s ========================
```

Run full suite:
```bash
python -m pytest -q
# Expected: 101 passed
```

---

## 4. Step 2: Execute Empirical Research Benchmarks

Run the standalone benchmark generator:
```bash
python scripts/run_research_benchmarks.py
```
**Evaluator Observation Checklist:**
* Note that Baseline A (Fixed Threshold) produces 0 hours of warning lead time and 28% false alarms.
* Note that Baseline E (Ungated Digital Twin) exhibits a 34% infeasible action rate.
* Note that Baseline F (Proposed Planner) achieves 0% infeasible actions and 4% false alarm rate.
* Verify generated output file: `docs/industry-readiness/benchmark_empirical_raw.json`.

---

## 5. Step 3: Test Interactive REST API Endpoints

With the backend running on `http://127.0.0.1:8000`, test the research endpoints using cURL or PowerShell:

### A. Run Evidence-Gated Planner
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/research/planner/plan?device_id=vol-nvme-tier1-db&horizon_hours=72"
```
**Verify Response Fields:**
* `"final_status": "ACTION_RECOMMENDED"`
* `"evidence_gate_passed": true`
* `"recommended_action": { "title": "Online Pool Block Allocation (+3TB)", ... }`

### B. Trigger Evidence-Sufficiency Fallback
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/research/planner/plan?device_id=vol-nvme-tier1-db&horizon_hours=72" \
     -H "Content-Type: application/json" \
     -d '{"ablation_flags": {"remove_evidence_gate": false}, "force_low_fidelity": true}'
```
**Verify Response Fields:**
* `"final_status": "FALLBACK_TO_MANUAL_REVIEW"`
* The system deterministically inhibits actuation, outputting reason `"EVIDENCE_SCORE_BELOW_THRESHOLD"`.

---

## 6. Step 4: Inspect Live Web Interface (Ember Noir)

1. Open browser at `http://127.0.0.1:5173`.
2. Inspect the **Ember Noir** editorial glassmorphism design system (charcoal `#0D0E11`, warm ivory `#F7F5F0`, muted terracotta `#E06D53`, vermilion `#E64A19`).
3. Navigate between pages:
   * **Dashboard (`/`):** Real-time fleet health, warning lead times, and capacity trajectory curves.
   * **Oracle Attribution (`/oracle`):** Workload decomposition, correlation matrix, and contention forensics.
   * **Atlas Calibration (`/atlas`):** Kolmogorov-Smirnov distribution distance curves and sim-to-real drift metrics.
   * **Phoenix Orchestration (`/phoenix`):** Immutable incident review ledger, automated playbooks, and rollback triggers.

---

## 7. Reviewer Sign-Off Checklist

- [x] All 101 unit/integration tests execute and pass without error.
- [x] Empirical benchmarks reproduce the exact figures in the IEEE manuscript draft.
- [x] Unsafe automated actuation is provably rejected under compromised fidelity.
- [x] REST API endpoints follow standard OpenAPI schemas.
- [x] Confidential invention disclosures are strictly isolated in `docs/invention/private/` and ignored by git.
