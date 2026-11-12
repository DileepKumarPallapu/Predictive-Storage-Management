# AEGISSTOR — Viewer User Guide (`VIEWER_GUIDE.md`)

**Role:** `VIEWER` · **Landing Route:** `/viewer`

## Read-Only Stakeholder Scope
The `VIEWER` role is designed for executives, capacity planners, and external stakeholders requiring visibility into storage health and projections without operational write risk.

### Permitted Modules & Actions
- **Viewer Dashboard (`/viewer`)**: Read-only fleet summary, capacity headroom table, forecast breach counters, trained model summary, and recent reports.
- **Inspection Pages**: Storage Inventory (`/fleet`), Topology (`/topology`), Live Telemetry (`/live-telemetry`), Data Quality (`/datasets`), Workload Intelligence (`/workload`), ML Model Centre metrics (`/ml-centre`), Forecast Studio views (`/ml-lab`), Capacity Risk (`/risk-centre`), Performance Analytics (`/telemetry`), Digital Twin scenario views (`/twin`), Recommendations (`/interventions`), and Alerts (`/alerts`).
- **Reports & Exports (`/reports`)**: Preview reports and download permitted **CSV** and **PDF** exports.

### Enforced Restrictions (`403 Forbidden`)
Viewers cannot register/modify/delete storage resources, upload/ingest telemetry, train or retrain ML models, execute Digital Twin simulations, acknowledge/assign/resolve alerts, approve recommendations, create reports via `POST /reports/generate`, view `/audit` or `/integrations` secrets, or access `/users` and `/settings`.
