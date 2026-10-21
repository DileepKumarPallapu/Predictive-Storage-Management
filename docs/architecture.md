# AEGISSTOR — Storage Resilience Intelligence Platform
## Architecture Specification Document
**Academic Subtitle**: Predictive Storage Capacity and Performance Management Using Machine Learning

---

## 1. System Overview & Philosophy

AEGISSTOR addresses a fundamental challenge in enterprise storage operations: storage administrators typically rely on static threshold alerts (e.g., "volume > 85% full" or "latency > 25ms"). By the time a static threshold fires, operational options are constrained, emergency ticket resolution causes downtime risks, and knee-jerk data movement can trigger severe I/O thrashing.

AEGISSTOR introduces the **Storage Resilience Digital Twin**, an integrated pipeline:
```
Real / Synthetic Telemetry
    │
    ▼
Data Validation & Provenance Ingestion (schema check, gap detection, outlier flag)
    │
    ▼
Multi-Horizon Quantile ML Forecasting (LightGBM Quantile, Seasonal Naive, Persistence)
    │
    ▼
Empirical Interval Calibration & Uncertainty Quantification (Conformal Coverage, Width)
    │
    ▼
Capacity & Latency Risk Envelope (Joint multi-target breach probability, Reserve Runway)
    │
    ▼
Counterfactual Intervention Studio (Deterministic simulator with documented physics/assumptions)
    │
    ▼
Constraint-Aware Recommendation Engine (Hard safety envelope filter, Pareto/multi-criteria ranking)
    │
    ▼
Human Approval & Governance (Shadow mode by default, audit logging, dual-approval workflow)
    │
    ▼
Outcome Tracking & Closed-Loop Model Evaluation (Drift detection, backtesting, ablation)
```

---

## 2. Core Architectural Components

### 2.1 Backend Services (`backend/app/`)
1. **API Layer (`backend/app/api/`)**:
   - Versioned REST endpoints (`/api/v1/*`)
   - JWT & Role-Based Access Control (Admin, Operator, Auditor, Researcher, Viewer)
   - Uniform response envelopes, standard error codes, structured request validation (Pydantic v2).
2. **Telemetry Ingestion & Adapters (`backend/app/collector/`)**:
   - `SyntheticGenerator`: Deterministic, configurable multi-workload generator with realistic diurnal seasonality, burst writes, scrub events, queue contention, and collector dropouts.
   - `LinuxStorageAdapter` / `WindowsStorageAdapter`: Pluggable host telemetry collectors (disk I/O, queue depth, partition space).
   - `ReplayEngine`: Time-indexed dataset reader replaying historical traces chronologically without lookahead leakage.
3. **Forecasting Engine (`backend/app/ml/`)**:
   - Feature engineering pipeline: rolling statistics, exponential moving averages, differencing, diurnal cyclical encodings, burst markers, queue pressure ratios.
   - Multi-quantile LightGBM regressors ($\alpha \in \{0.10, 0.50, 0.90\}$) for capacity, IOPS, throughput, and tail latency (P95).
   - Statistical & Naive baselines: Persistence ($t+h = t$), Seasonal-Naive ($t+h = t+h-S$), Rolling Mean.
   - Conformal Prediction / Empirical Calibration module measuring interval coverage, sharpness, and pinball loss.
   - Insufficient-evidence & Fallback gates: prevents ungrounded predictions when telemetry gaps exceed acceptable bounds.
4. **Risk & Runway Assessment Engine (`backend/app/services/risk_engine.py`)**:
   - Multi-horizon threshold breach evaluator: computes point-in-time breach probability curves.
   - Reserve Runway calculator: calculates $T_{\text{breach}}$ with upper/lower uncertainty bounds.
   - Risk classification: Nominal, Warning, Elevated, Critical.
5. **Digital Twin & Intervention Simulator (`backend/app/simulator/`)**:
   - In-memory state cloning of volume/pool geometry, I/O rates, capacity, and SLA bounds.
   - Actions:
     * `DO_NOTHING`: baseline trajectory under forecast workload.
     * `EXPAND_CAPACITY`: adds tier-specific storage with provisioning latency and cost.
     * `TIER_COLD_DATA`: moves inactive data to secondary tier with migration I/O overhead and temporary latency inflation.
     * `RESCHEDULE_TASK`: shifts intensive background tasks (scrubbing, backups) to off-peak hours.
     * `REBALANCE_WORKLOAD`: relocates noisy workloads across pool devices.
   - Evaluates Hard Safety Envelope constraints (e.g., minimum 10% emergency reserve, max 35ms latency during migration, max 4-hour migration window).
   - Explicitly tags simulated trajectories as synthetic estimates distinct from physical measurements.
6. **Recommendation & Governance Engine (`backend/app/services/recommendation_engine.py`)**:
   - Evaluates feasible candidate interventions against the Hard Safety Envelope.
   - Ranks by multi-objective utility: $\Delta \text{Risk} - \lambda_1 \text{Cost} - \lambda_2 \text{Overhead} - \lambda_3 \text{Duration}$.
   - Shadow Mode enforcement: physical writes disabled; human operator must approve or reject with audit trail.
7. **Drift & Reliability Monitor (`backend/app/services/drift_detector.py`)**:
   - Page-Hinkley and Wasserstein/KS distribution shift detection over sliding residual windows.
   - Alerts on telemetry staleness, coverage degradation, and input distribution shifts.

---

## 3. Frontend Architecture (`frontend/src/`)
- **Framework**: React 18 / Vite with TypeScript (strict mode).
- **Styling**: Tailwind CSS with "Obsidian Aurora" dark/light theme tokens via CSS variables.
- **Icons**: Lucide React.
- **Visualization**: Scientific canvas & SVG charts displaying:
  * Solid historical line
  * Emphasized forecast median ($q_{50}$)
  * Semi-transparent prediction interval band ($[q_{10}, q_{90}]$)
  * Dashed hard constraint threshold
  * Counterfactual simulation overlay curves
  * Incident markers & missing-data indicators
- **Navigation**: Collapsible sidebar, top status bar (mode toggle: Demo / Replay / Live, collector health, active alerts badge, role indicator), and 12 dedicated interactive views.

---

## 4. Operating Modes
1. **DEMO MODE**: Out-of-the-box self-contained mode with 4 realistic enterprise storage pools (NVMe Tier 1, SAS Tier 2, Cloud Archive, Backup Target), simulated workloads (E-Commerce DB, Analytics Batch, Media Archive, VM Cluster), and injected risk scenarios.
2. **REPLAY MODE**: Loads historical or public storage benchmark traces (e.g., SNIA, Alibaba Cloud Storage trace schemas) and steps through evaluation chronologically.
3. **LIVE READ-ONLY MODE**: Pulls real host disk metrics via non-destructive OS counters with strict read-only safety guarantees.

---

## 5. Security & Safety Envelope
- Zero host mutation by default (Shadow Mode is immutable).
- No arbitrary code execution or unvalidated system calls.
- Strict input sanitization via Pydantic schemas.
- Comprehensive audit log on all scenario approvals, threshold overrides, and role changes.
