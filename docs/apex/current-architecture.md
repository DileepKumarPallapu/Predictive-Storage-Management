# AEGISSTOR APEX — Current Architecture & Data Flow (Phase 0)

**Project Title:** Predictive Storage Capacity and Performance Management Using Machine Learning  
**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Document Code:** APEX-ARCH-001  
**Architecture Classification:** Modular Monolithic Engine with Strict Service Domain Boundaries  

---

## 1. Architectural Philosophy

AEGISSTOR avoids premature distributed microservice overhead by implementing a strictly bounded, high-cohesion, low-coupling **Modular Monolithic Architecture**. All data mutations flow through transactional service contracts, deterministic mathematical physics, and auditable governance gates.

```mermaid
graph TD
    subgraph Client ["Frontend Presentation Layer (React 19 + TypeScript + Vite)"]
        UI_Nav["Sidebar & App Shell<br/>(Ember Noir Theme)"]
        UI_Dash["Executive Dashboard & Fleet"]
        UI_Lab["ML Lab & Uncertainty"]
        UI_Twin["Digital Twin & Interventions"]
        UI_Pnx["Phoenix Incident Command"]
        UI_Gnt["Gauntlet Research Workbench"]
        UI_Sov["Sovereign Federation"]
    end

    subgraph API ["REST API Layer (FastAPI v1)"]
        R_Core["/devices, /telemetry, /forecasts"]
        R_Twin["/scenarios, /recommendations, /risks"]
        R_Atlas["/atlas (Reality Calibration)"]
        R_Pnx["/phoenix (Incident Orchestrator)"]
        R_Gnt["/gauntlet (Examiner Benchmark)"]
        R_Sov["/sovereign (Federated Storage)"]
        R_Oracle["/oracle (Workload Attribution)"]
    end

    subgraph CoreServices ["Business Logic & Intelligence Engines"]
        S_ML["ML Forecaster<br/>(Ridge, LightGBM, Quantiles)"]
        S_Twin["Digital Twin Sandbox<br/>(Action Physics & Queue Models)"]
        S_Risk["Multi-Tier Risk Engine<br/>(Runway, Contention, Latency)"]
        S_EGSIP["Evidence-Gated Planner<br/>(Uncertainty & Feasibility Gates)"]
        S_Pnx["Phoenix Orchestrator<br/>(Triage, Policy, Recovery Verifier)"]
        S_Sov["Sovereign Engine<br/>(FedAvg, DP-FedAvg, Shield)"]
        S_Oracle["Oracle Attribution<br/>(I/O Forensics & Contention)"]
    end

    subgraph DataStorage ["Data & Storage Layer"]
        DB[(SQLite / PostgreSQL Relational DB<br/>52 Entity Schemas)]
        SeedData["Synthetic Workload Replay Files"]
        ModelArtifacts["Serialized Models & Weight Artifacts"]
    end

    Client -->|HTTP/REST JSON| API
    API --> CoreServices
    CoreServices --> DataStorage
    CoreServices -.->|No Physical IOCTL| HardwareGate["Physical Hardware Safe Barrier<br/>(MUTATION_DISABLED=True)"]
```

---

## 2. Core Domain Boundaries & Responsibilities

| Subsystem | Service Module | Primary Responsibilities |
| :--- | :--- | :--- |
| **Telemetry Ingestion** | `collector/` | Imports, validates, and standardizes physical or synthetic telemetry. Validates monotonic timestamps, positive capacity bounds, and unit consistency (Bytes, MB/s, ms). |
| **Forecasting Engine** | `ml/`, `capacity_runway_engine.py` | Chronologically split training without temporal leakage. Fits autoregressive Ridge, LightGBM, and persistence baselines; computes $p_{10}, p_{50}, p_{90}$ prediction intervals. |
| **Resilience Digital Twin** | `simulator/`, `scenarios.py` | Deterministic counterfactual simulation of capacity expansion, cold tiering, deduplication, and IO throttling across configured horizons (7, 14, 30, 90 days). |
| **Evidence-Gated Planner** | `evidence_gated_planner.py` | **Primary Candidate Contribution:** Evaluates forecast uncertainty, simulator discrepancy, evidence freshness, and safety constraints before proposing intervention. Rejects infeasible actions. |
| **Workload Forensics** | `services/oracle/` | Workload attribution, contention factor analysis, queue depth correlation, and counterfactual mitigation evaluation. |
| **Safe Incident Recovery** | `services/phoenix/` | Correlated incident clustering, runbook generation, human-in-the-loop policy approval gate, and post-action telemetry recovery verification. |
| **Examiner Workbench** | `services/gauntlet_service.py` | Reproducible benchmark execution, claim-to-evidence matrix validation, cryptographic experiment run hashing, and examiner report generation. |
| **Federated Storage** | `services/sovereign_service.py` | 4-site isolated decentralized learning simulation. Supports FedAvg, Reliability-Aware weighting, Personalized adaptation, and $(\epsilon, \delta)$ Differential Privacy. |

---

## 3. Data Flow Pathways

### Pathway A: Telemetry Ingestion & Risk Scoring
1. **Source:** Synthetic workload replay or Prometheus node exporter collects metrics at 1-minute intervals.
2. **Ingestion & Validation:** `collector/` asserts non-null timestamps, validates device identifiers, verifies $0 \le \text{utilization} \le 100\%$, and writes to the `telemetry` table.
3. **Forecasting:** `CapacityRunwayEngine` extracts causal lag and diurnal features, generates median forecast and $p_{10}$/$p_{90}$ bounds.
4. **Risk Calculation:** `RiskEngine` calculates days-to-breach (80% warning, 90% critical) and evaluates latency degradation risk.

### Pathway B: Evidence-Gated Intervention Planning
1. **Trigger:** Runway breach predicted within $< 14$ days or queue contention alert triggered.
2. **Candidate Generation:** `ActionPlanner` generates candidate actions (e.g., `EXPAND_VOLUME`, `TIER_COLD_DATA`, `THROTTLE_WORKLOAD`).
3. **Evidence Gating:**
   - Evaluates prediction interval width $\Delta_{90-10}$; if variance is excessive, flags uncertainty gate breach.
   - Evaluates Atlas reality calibration discrepancy; if simulation error $> 15\%$, requires human verification.
   - Verifies target device capacity headroom and maximum acceptable latency constraints.
4. **Outcome:** Returns an approved intervention proposal or explicitly emits `"NO FEASIBLE AUTOMATED ACTION — MANUAL REVIEW REQUIRED"`.

### Pathway C: Incident Orchestration & Safe Recovery
1. **Incident Creation:** Unresolved alerts correlate into an active `PhoenixIncident`.
2. **Runbook Selection:** Matched to approved runbook template.
3. **Human Approval:** Policy gate checks permissions; requires operator signoff.
4. **Digital Twin Execution:** Runs in sandbox; measures pre/post delta.
5. **Recovery Verification:** Monitors telemetry for 6 consecutive cycles to verify stabilization before closing incident.

---

## 4. Hardware Safety Boundary

Physical storage mutation is completely prohibited by architectural invariant:
- All action proposal executions run against in-memory or database-backed Digital Twin simulation states.
- The `action_gateway.py` enforces `PHYSICAL_MUTATION_DISABLED = True` at the core interface.
- Raw block device access, disk wiping, or partitioning tools are never invoked.
