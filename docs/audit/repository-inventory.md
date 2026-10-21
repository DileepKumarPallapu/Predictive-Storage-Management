# AEGISSTOR — Repository Inventory & Module Classification

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Audit Timestamp:** 2026-10-21T19:45:00Z  
**Branch:** `master`  
**Location:** `C:\Users\dilee\.gemini\antigravity\scratch\aegisstor`

---

## 1. Module Classification Taxonomy

Every module in the repository is audited according to the following strict classification criteria:
- **Implemented and Verified**: Code exists, tested via automated test suite, integrated end-to-end.
- **Implemented but Unverified**: Code exists but lacks complete integration or automated unit test coverage.
- **Partially Implemented**: Core skeleton or partial business logic exists, missing edge-case handling or full API exposure.
- **Mock or Placeholder Only**: Static mock data returned or UI components without real API hooks.
- **Missing**: Architectural component specified but not yet built.
- **Broken**: Code produces runtime exceptions or fails validation.
- **Security-Sensitive**: Handles credentials, execution paths, authentication, or physical hardware mutations.
- **Blocked by External Dependency**: Requires external services (e.g., real hardware SAN/NAS cluster, live external Prometheus).

---

## 2. Comprehensive Inventory Matrix

| Path / Module | Function / Responsibility | Current Status | Findings & Upgrade Needs |
| :--- | :--- | :--- | :--- |
| **`backend/app/main.py`** | FastAPI app lifespan, CORS, seed trigger, router mounting | **Implemented and Verified** | Clean startup; needs structured logging and request-tracing middleware. |
| **`backend/app/config.py`** | Pydantic V2 settings, environment resolution, safety invariants | **Implemented and Verified** | Invariants enforced (`SHADOW_MODE_ENABLED: True`). Needs JWT secret key configuration. |
| **`backend/app/database.py`** | SQLAlchemy engine, session management, SQLite fallback | **Implemented and Verified** | Working transaction scopes; needs query execution profiling and connection pool sizing. |
| **`backend/app/models/entities.py`** | Database schema (Devices, Telemetry, Forecasts, Risks, etc.) | **Implemented and Verified** | All 14 entity tables defined with foreign keys and UTC timestamps. Needs composite index optimization. |
| **`backend/alembic/`** | Database migration environment and version scripts | **Implemented and Verified** | Head migration `c00e12269790_initial_schema.py` active and verified. |
| **`backend/app/api/v1/endpoints_overview.py`** | Fleet resilience overview, aggregate KPIs, risk timeline | **Implemented and Verified** | Returns real calculated stats from database. Verified by unit tests. |
| **`backend/app/api/v1/endpoints_devices.py`** | Device list, registration, health query | **Implemented and Verified** | Returns all 4 monitored pools. Needs fleet search and tier filtering params. |
| **`backend/app/api/v1/endpoints_telemetry.py`** | Ingestion & query for capacity, IOPS, latency, queue | **Implemented and Verified** | Supports time-range bounding. Needs explicit pagination and sampling aggregation. |
| **`backend/app/api/v1/endpoints_forecasts.py`** | Quantile forecast retrieval [q10, q50, q90] | **Implemented and Verified** | Returns real ML projections. Needs multi-target forecasting (IOPS, latency). |
| **`backend/app/api/v1/endpoints_risks.py`** | Reserve runway & multi-horizon risk envelope | **Implemented and Verified** | Computes runway with edge-case handling (zero/negative growth). |
| **`backend/app/api/v1/endpoints_scenarios.py`** | Digital Twin counterfactual intervention execution | **Implemented and Verified** | Simulates 5 interventions with hard safety constraint checks. |
| **`backend/app/api/v1/endpoints_recommendations.py`** | Ranked constraint-aware recommendations & approval | **Implemented and Verified** | Lead-time aware ranking, human-in-the-loop approval workflow. |
| **`backend/app/api/v1/endpoints_experiments.py`** | Empirical ablation study runner | **Implemented and Verified** | Runs real ablation experiments (calibration, lead time, overhead). |
| **`backend/app/api/v1/endpoints_reliability.py`** | Model drift, error metrics, provenance validation | **Implemented and Verified** | Computes MAE, interval width, coverage on real data. |
| **`backend/app/api/v1/endpoints_alerts.py`** | Storage risk incidents, threshold warnings, acknowledge | **Implemented and Verified** | Full CRUD for alerts and incident acknowledgment. |
| **`backend/app/api/v1/endpoints_datasets.py`** | Dataset metadata, provenance, ingestion quality logs | **Implemented and Verified** | Verified data quality records. |
| **`backend/app/api/v1/endpoints_settings.py`** | System settings, safety envelope configuration | **Implemented and Verified** | Verified threshold configurations. |
| **`backend/app/collector/synthetic.py`** | Deterministic multi-pool telemetry generator | **Implemented and Verified** | Generates 4 distinct volume profiles with realistic physics. |
| **`backend/app/collector/host_collector.py`** | Read-only OS/hardware telemetry adapter (Shadow Mode) | **Implemented and Verified** | Zero-mutation safe collector. Needs Prometheus/node_exporter scrape adapter. |
| **`backend/app/ml/feature_pipeline.py`** | Leak-free chronological lag & rolling stats extraction | **Implemented and Verified** | Verified no future leakage; strict train/val/test splits. |
| **`backend/app/ml/models.py`** | Differenced LightGBM, Persistence, Seasonal-Naive | **Implemented and Verified** | Monotonic residual projection with quantile loss ($q_{10}, q_{50}, q_{90}$). |
| **`backend/app/ml/calibration.py`** | Conformal calibration, empirical coverage evaluation | **Implemented and Verified** | Verified pinball loss & coverage metrics. |
| **`backend/app/simulator/digital_twin.py`** | Digital Twin physics engine & Hard Safety Envelope | **Implemented and Verified** | Enforces hard constraints; rejects SLA-violating actions. |
| **`backend/app/services/risk_engine.py`** | Reserve runway calculation & risk attribution | **Implemented and Verified** | Edge cases handled: zero-growth, negative growth, already breached. |
| **`backend/app/services/recommendation_engine.py`** | Lead-time aware intervention ranking | **Implemented and Verified** | Deducts action duration from runway; filters unsafe options. |
| **`backend/app/services/drift_detector.py`** | Statistical data drift & KS test evaluation | **Implemented and Verified** | Tracks metric distribution shifts. |
| **`backend/app/services/audit_service.py`** | Immutable append-only audit trail | **Security-Sensitive** / **Verified** | Logs all simulations, approvals, and configurations. Needs JWT user context. |
| **`backend/app/auth/`** | Authentication & Role-Based Access Control (RBAC) | **Partially Implemented** | Uses mock/header user. Needs JWT token issuance, password hashing, and role checks. |
| **`frontend/src/api/client.ts`** | Centralized Axios/fetch API client | **Implemented and Verified** | Typed client for all endpoints. Needs request cancellation and token attachment. |
| **`frontend/src/components/ScientificForecastChart.tsx`** | Obsidian Aurora SVG fan chart | **Implemented and Verified** | Calibrated prediction intervals [q10, q90] and threshold lines. |
| **`frontend/src/pages/PageExecutiveOverview.tsx`** | Top-level resilience dashboard & fleet health | **Implemented and Verified** | Connects to `/api/v1/overview` and forecast endpoints. |
| **`frontend/src/pages/PageStorageFleet.tsx`** | Device list & pool capacity allocation | **Implemented and Verified** | Connects to `/api/v1/devices`. |
| **`frontend/src/pages/PageDeviceIntelligence.tsx`** | Per-volume deep dive & metric analysis | **Implemented and Verified** | Connects to telemetry and forecast endpoints. |
| **`frontend/src/pages/PageTelemetryExplorer.tsx`** | Raw telemetry query and metric inspection | **Implemented and Verified** | Connects to `/api/v1/devices/{id}/telemetry`. |
| **`frontend/src/pages/PageMLPredictionLab.tsx`** | Model versioning, hyperparams, training triggers | **Implemented and Verified** | Connects to models and forecasts. |
| **`frontend/src/pages/PageStorageDigitalTwin.tsx`** | Twin physics state and scenario creation | **Implemented and Verified** | Connects to scenarios API. |
| **`frontend/src/pages/PageInterventionStudio.tsx`** | Scenario comparative simulation | **Implemented and Verified** | Connects to scenario run API. |
| **`frontend/src/pages/PageAlertsIncidents.tsx`** | Incident management and alert triage | **Implemented and Verified** | Connects to alerts API with acknowledge actions. |
| **`frontend/src/pages/PageModelReliability.tsx`** | Calibration, coverage, and drift metrics | **Implemented and Verified** | Connects to reliability API. |
| **`frontend/src/pages/PageExperimentWorkbench.tsx`** | Scientific ablation study workbench | **Implemented and Verified** | Interactive ablation runner and empirical results view. |
| **`frontend/src/pages/PageDatasetsQuality.tsx`** | Dataset ingestion, provenance, and completeness | **Implemented and Verified** | Connects to datasets API. |
| **`frontend/src/pages/PageSettingsAudit.tsx`** | Audit log, system settings, safety envelope | **Implemented and Verified** | Connects to audit and settings APIs. |

---

## 3. Identified Gaps & Target Upgrades

1. **Authentication & RBAC (Phase 12)**:
   - System currently runs with open administrative rights.
   - Upgrade: Implement secure JWT authentication (`pyjwt`, `passlib`/`bcrypt`), password hashing, user entities (`ADMIN`, `OPERATOR`, `AUDITOR`), and route protection decorators.

2. **Telemetry Adapter Expansion (Phase 6)**:
   - Expand `host_collector.py` to support Prometheus `/metrics` scraping and mock node_exporter collector mode.
   - Implement data freshness warnings and missing-interval detection flags on all charts.

3. **Multi-Target Forecasting (Phase 7)**:
   - Add multi-target prediction models for **IOPS**, **Read/Write Throughput**, and **Tail Latency** ($p_{99}$) in addition to capacity.

4. **Interactive Charting & UI Polish (Phase 2 & 3)**:
   - Integrate interactive ECharts/enhanced time-series visualization option for multi-metric overlay.
   - Add centralized ErrorBoundary, route-level fallback skeletons, and keyboard shortcuts.

5. **Security, Rate Limiting & Structured Logging (Phase 4 & 12)**:
   - Request-tracing middleware with `X-Request-ID`.
   - Rate limiting for scenario simulation endpoints.
   - Bounded queries and SQL pagination for high-frequency telemetry.
