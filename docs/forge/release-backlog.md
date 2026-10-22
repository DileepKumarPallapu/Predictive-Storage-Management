# AEGISSTOR FORGE — Release Backlog & Traceability Matrix (Release Candidate 21.0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Product:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** FORGE-BACKLOG-001  

---

## 1. Prioritized Defect & Task Backlog

| Priority | Category | Item Description | Current Status | Resolution Plan / Verification |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | **Safety & Startup** | Single-source database connectivity & root `pytest.ini` | `RESOLVED` | `pytest.ini` & `database.py` hardened. All 120 tests pass. |
| **P0** | **Safety & Startup** | Physical disk mutation fail-closed invariant | `RESOLVED` | `PHYSICAL_MUTATION_DISABLED = True` asserted by release gate. |
| **P1** | **Core Workflow** | Canonical 20-step demonstration workflow execution | `IMPLEMENTED & VERIFIED` | Verified by `scripts/verify_apex_release_gate.py` with bitwise cryptographic reproduction. |
| **P1** | **Core Workflow** | Full UI Ember Noir integration across 19 views | `RESOLVED` | `tsc -b && vite build` builds in 1.60s with 0 errors. |
| **P2** | **Research Rigor** | EGSIP Evidence-gating against baselines (Persistence, LightGBM) | `RESOLVED` | Benchmarked in GAUNTLET with 0 infeasible actions. |
| **P2** | **Research Rigor** | Claim-to-Evidence Matrix linking metrics to experiment IDs | `RESOLVED` | Implemented in `services/gauntlet_service.py` & `PageGauntletWorkbench.tsx`. |
| **P3** | **Viva Preparation** | Technical defense questions, architecture explanations, viva bank | `RESOLVED` | Authored in `docs/forge/viva-question-bank.md` & defense docs. |
| **P4** | **Packaging** | Submission directory staging & artifact cleanup | `RESOLVED` | Documented in `submission/` specification without secret leakage. |

---

## 2. Requirements Traceability Matrix

| Academic Project Objective | Functional Module | API Routes | Relational Tables | Test References | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Storage Telemetry Monitoring** | Collector | `/api/v1/devices`, `/api/v1/telemetry` | `devices`, `telemetry` | `test_core_engine.py` | `PageTelemetryExplorer.tsx` |
| **2. ML Capacity & Performance Forecasting** | Forecaster | `/api/v1/devices/{id}/forecasts` | `forecasts`, `model_versions` | `test_upgrades_v3.py` | `PageMLPredictionLab.tsx` |
| **3. Uncertainty Quantification** | Quantile Engine | `/api/v1/forecasts/uncertainty` | `forecasts` ($q_{10}, q_{50}, q_{90}$) | `test_advanced_intelligence_engine.py` | `ScientificForecastChart.tsx` |
| **4. Multi-Tier Runway Risk Analysis** | Risk Engine | `/api/v1/devices/{id}/risks` | `risk_assessments` | `test_advanced_intelligence_engine.py` | `PageExecutiveOverview.tsx` |
| **5. Storage Resilience Digital Twin** | Digital Twin | `/api/v1/scenarios` | `scenarios`, `simulated_outcomes` | `test_jurassic_resilience.py` | `PageStorageDigitalTwin.tsx` |
| **6. Evidence-Gated Planning (EGSIP)** | EGSIP Planner | `/api/v1/interventions/evaluate` | Audit records | `test_evidence_gated_planner.py` | `PageInterventionStudio.tsx` |
| **7. Safe Incident Recovery** | Phoenix | `/api/v1/phoenix/incidents` | `phoenix_incidents`, `phoenix_runs` | `test_phoenix_orchestration.py` | `PagePhoenixOrchestrator.tsx` |
| **8. Sim-to-Real Calibration** | Atlas | `/api/v1/atlas/discrepancies` | `atlas_discrepancy_records` | `test_atlas_reality_calibration.py` | `PageAtlasRealityLab.tsx` |
| **9. Workload Attribution Forensics** | Oracle | `/api/v1/oracle/workloads` | `oracle_workloads`, `oracle_cases` | `test_oracle.py` | `PageOracleIntelligence.tsx` |
| **10. Privacy-Conscious Federation** | Sovereign | `/api/v1/sovereign/tournament` | `sovereign_sites`, `sovereign_rounds` | `test_sovereign_federated.py` | `PageSovereignFederation.tsx` |
| **11. Reproducible Research Benchmarking**| Gauntlet | `/api/v1/gauntlet/claims` | `gauntlet_suites`, `gauntlet_claims` | `test_gauntlet_workbench.py` | `PageGauntletWorkbench.tsx` |
