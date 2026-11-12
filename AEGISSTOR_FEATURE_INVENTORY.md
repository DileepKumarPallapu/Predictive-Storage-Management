# AEGISSTOR — Feature Inventory & Classification

## Classification Legend
1. **REQUIRED AND WORKING**
2. **REQUIRED BUT INCOMPLETE**
3. **DUPLICATE**
4. **UNUSED**
5. **BROKEN**
6. **SIMULATION ONLY**
7. **NEEDS REPLACEMENT**
8. **BLOCKED BY EXTERNAL CONFIGURATION**

---

## Frontend Pages (`frontend/src/pages/`)

| Module / Page | Classification | Notes & Dependencies |
|---|---|---|
| `PageExecutiveOverview.tsx` | REQUIRED AND WORKING | Main Operations Overview; consumes `/overview` and `/realtime/*`. |
| `PageOperatorDashboard.tsx` | REQUIRED AND WORKING | Operator Command Workspace. |
| `PageViewerDashboard.tsx` | REQUIRED AND WORKING | Read-only Viewer Summary Workspace. |
| `PageAuthPortal.tsx` | REQUIRED AND WORKING | Login/session portal backed by `/auth/*`. |
| `PageAccessDenied.tsx` | REQUIRED AND WORKING | RBAC 403 boundary page. |
| `PageIntegrationManagement.tsx` | REQUIRED BUT INCOMPLETE | Handles telemetry connectors & API keys; needs enterprise DB source registration (PostgreSQL, MySQL, MariaDB, MSSQL, Oracle) and plain-English connection health messages. |
| `PageDataIngestion.tsx` | REQUIRED AND WORKING | CSV import preview/validate/commit + ingestion job history. |
| `PageStorageFleet.tsx` | REQUIRED AND WORKING | Storage inventory CRUD + capacity status. |
| `PageStorageTopology.tsx` | REQUIRED AND WORKING | Storage pool/device topology view. |
| `PageDeviceIntelligence.tsx` | REQUIRED AND WORKING | Per-device telemetry, tail latency, and details. |
| `PageLiveTelemetry.tsx` | REQUIRED AND WORKING | Live WebSocket/polling telemetry feed. |
| `PageTelemetryExplorer.tsx` | REQUIRED AND WORKING | Performance analytics (IOPS, latency, throughput). |
| `PageDatasetsQuality.tsx` | REQUIRED AND WORKING | Data quality, missingness, reliability scores. |
| `PageWorkloadIntelligence.tsx` | REQUIRED AND WORKING | Workload regime & changepoint detection. |
| `PageMLPredictionLab.tsx` | REQUIRED AND WORKING | Forecast generation & multi-horizon intervals. |
| `PageMLModelCentre.tsx` | REQUIRED AND WORKING | LightGBM & SARIMAX model training, champion-challenger comparison. |
| `PageModelReliability.tsx` | REQUIRED AND WORKING | Conformal calibration & prediction error metrics. |
| `PageExperimentWorkbench.tsx` | REQUIRED AND WORKING | Backtesting & ablation studies. |
| `PageCapacityRiskCentre.tsx` | REQUIRED AND WORKING | Capacity runway & threshold-crossing risk. |
| `PageAlertsIncidents.tsx` | REQUIRED AND WORKING | Alert acknowledgement, assignment, resolution. |
| `PageDecisionOptimisation.tsx` | REQUIRED AND WORKING | Constrained intervention optimisation. |
| `PageInterventionStudio.tsx` | REQUIRED AND WORKING | Evidence-based recommendations. |
| `PageStorageDigitalTwin.tsx` | SIMULATION ONLY (REQUIRED) | Counterfactual "What-If" Digital Twin simulator; must remain clearly labeled as simulation. |
| `PageTaskCentre.tsx` | REQUIRED AND WORKING | Operational tasks & real-time comments. |
| `PageApprovalCentre.tsx` | REQUIRED AND WORKING | Recommendation & action approval queue. |
| `PageControlPlane.tsx` | REQUIRED AND WORKING | Sprint 1 Control Plane (Connector Registry, Capability Matrix, Preflight, Dry-Run, Dual-Control Approvals, Execution Evidence). |
| `PageReports.tsx` | REQUIRED AND WORKING | JSON/CSV/PDF report generation & history. |
| `PageUserManagement.tsx` | REQUIRED AND WORKING | User accounts & dynamic RBAC configuration. |
| `PageAuditLogs.tsx` | REQUIRED AND WORKING | Cryptographically chained audit log viewer. |
| `PageSettingsAudit.tsx` | REQUIRED AND WORKING | Global thresholds & retention settings. |
| `PageOmegaControlRoom.tsx` | DUPLICATE | Codename prototype duplicating `PageStorageTopology` / `PageExecutiveOverview`. |
| `PageJurassicLab.tsx` | UNUSED / PROTOTYPE | Codename stress-testing prototype outside the 8-layer architecture. |
| `PagePhoenixOrchestrator.tsx` | DUPLICATE | Superseded by `PageControlPlane` + `PageTaskCentre` + `PageApprovalCentre`. |
| `PageAtlasRealityLab.tsx` | DUPLICATE | Codename prototype duplicating `PageModelReliability`. |
| `PageOracleIntelligence.tsx` | DUPLICATE | Codename prototype duplicating `PageWorkloadIntelligence` / `PageCapacityRiskCentre`. |
| `PageGauntletWorkbench.tsx` | DUPLICATE | Codename prototype duplicating `PageExperimentWorkbench`. |
| `PageSovereignFederation.tsx` | UNUSED / PROTOTYPE | Codename prototype outside core scope. |

---

## Backend Services & Endpoints (`backend/app/`)

| Component | Classification | Notes |
|---|---|---|
| `endpoints_auth.py`, `auth/security.py`, `auth/permissions.py`, `auth/tenant.py` | REQUIRED AND WORKING | JWT, Argon2/bcrypt, sessions, dynamic RBAC, multi-org isolation. |
| `endpoints_realtime.py`, `realtime/event_bus.py` | REQUIRED AND WORKING | Outbox-backed WebSocket sync, presence, notifications, cursor replay. |
| `endpoints_connectors.py`, `collector/connector_registry.py`, `collector/host_collector.py` | REQUIRED BUT INCOMPLETE | Supports `LINUX_HOST`, `PROMETHEUS`, `CSV_HISTORICAL`, `HTTP_API`; needs real Enterprise DB Metadata Collectors (`POSTGRESQL`, `MYSQL`, `MARIADB`, `MSSQL`, `ORACLE`) and honest `NOT_CONFIGURED` / `CONNECTION_FAILED` status. |
| `endpoints_control_plane.py`, `control_plane_service.py` | REQUIRED AND WORKING | Governed Control Plane (Sprint 1 read-only actions, 8-check preflight, dry-run, approvals, locks, audit). |
| `endpoints_intelligence.py`, `ml/champion_challenger.py`, `ml/feature_pipeline.py`, `ml/calibration.py` | REQUIRED AND WORKING | LightGBM Quantile (Q10/Q50/Q90) & SARIMAX chronological validation, MAE/RMSE/WAPE/Pinball, conformal calibration. |
| `endpoints_risks.py`, `endpoints_scenarios.py`, `endpoints_recommendations.py` | REQUIRED AND WORKING | Capacity runway, risk scoring, Digital Twin counterfactuals, recommendations. |
| `endpoints_reports.py`, `reporting_service.py` | REQUIRED AND WORKING | Real DB-backed JSON/CSV/PDF reports. |
| `endpoints_organisations.py`, `endpoints_topology_services.py` | REQUIRED AND WORKING | Multi-organisation hierarchy & service impact traversal. |
| `endpoints_omega.py`, `endpoints_jurassic.py`, `endpoints_atlas.py`, `endpoints_oracle.py`, `endpoints_gauntlet.py`, `endpoints_sovereign.py`, `endpoints_phoenix.py` | DUPLICATE / PROTOTYPE | Legacy codename endpoints; retained in backend only where existing automated tests reference them, removed from primary UI navigation. |
