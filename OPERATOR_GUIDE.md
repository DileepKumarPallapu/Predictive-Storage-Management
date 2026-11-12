# AEGISSTOR — Operator User Guide (`OPERATOR_GUIDE.md`)

**Role:** `OPERATOR` · **Landing Route:** `/operator`  
AEGISSTOR grants Storage Operators complete end-to-end operational authority over day-to-day storage, telemetry, ML forecasting, risk, Digital Twin simulation, alerting, and reporting — without exposing IAM user administration or platform security secrets.

---

## Day-to-Day Operational Workflow
1. **Sign In**: Navigate to `/login` and enter your Operator username/email and password. You land automatically on `/operator` (Storage Operations Command Workspace).
2. **Storage Inventory (`/fleet`)**:
   - Create (`+ Register Storage`), edit metadata, update host/location, or remove unused storage pools (`SAN`, `NAS`, `Local storage`, `Cloud storage`, `Object storage`, `Backup storage`).
   - Adjust delegated per-resource warning/critical thresholds and maximum latency SLA (`PATCH /storage/{id}/thresholds`).
3. **Telemetry Ingestion & Connectors (`/ingestion`, `/integrations`, `/live-telemetry`)**:
   - Download standardized CSV template -> upload/paste telemetry -> **Preview & Validate** (inspect duplicates and invalid rows) -> **Commit Import**.
   - Submit manual measurements or trigger **Test Connection** & **Collect Telemetry** on permitted connectors (`telemetry.collect`, `telemetry.configure` for non-secret polling parameters).
4. **Data Quality & Workload Intelligence (`/datasets`, `/workload`)**:
   - Inspect completeness, missing intervals, duplicates, and trigger reliability evaluation (`POST /reliability/data/{id}`) or workload regime/drift scans (`POST /workload-regime/{id}`).
5. **ML Training & Forecast Studio (`/ml-centre`, `/ml-lab`)**:
   - Launch Champion-Challenger training (LightGBM + SARIMAX) synchronously or asynchronously (`/v2/models/train-async/{id}`). Monitor real backend job states (`QUEUED`, `RUNNING`, `COMPLETED`) and compare MAE, RMSE, R², MASE, and baseline benchmarks.
   - Generate calibrated `1/7/14/30/60/90`-day forecasts and inspect `P10 / P50 / P90` bounds vs historical telemetry.
6. **Capacity Risk, Performance & Alert Triage (`/risk-centre`, `/telemetry`, `/alerts`)**:
   - Execute fleet/pool capacity risk evaluations (`POST /risk/capacity/{id}`).
   - **Acknowledge**, **Assign** to an operational owner (`POST /alerts/{id}/assign`), **Resolve** with resolution notes, or **Reopen** active alerts.
7. **Digital Twin & Decision Optimisation (`/twin`, `/optimizer`, `/interventions`, `/approvals`)**:
   - Create/edit/rerun non-destructive Digital Twin scenarios (`CAPACITY_EXPANSION`, `TIER_COLD_DATA`, `WORKLOAD_REBALANCING`, etc.), compare scenarios, run constrained optimization, and export results.
   - Generate and submit operational recommendations. Note: **Self-approval is blocked (`403`)** unless explicitly permitted by Administrator approval policy; Operators can approve/reject peer-submitted recommendations.
8. **Reports & Operational Audit (`/reports`, `/audit`)**:
   - Preview and export JSON/CSV/PDF reports (`storage_inventory`, `capacity_risk`, `model_performance`, etc.) and inspect permitted operational audit logs.

## Account Management & Blocked Actions
- Manage your own password and active sessions anytime from the top-right account menu.
- Creating/editing users, changing global role permissions, modifying global system security settings, managing API keys/connector secrets, and verifying/deleting the security audit ledger require Administrator privileges (`403` if attempted).
