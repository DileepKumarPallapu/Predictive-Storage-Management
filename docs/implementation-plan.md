# AEGISSTOR — Implementation Plan & Phase Roadmap

## Phase Breakdown

### Phase 1: Foundation & Specifications (Current)
- [x] Architecture document (`docs/architecture.md`)
- [x] Implementation plan (`docs/implementation-plan.md`)
- [x] API Contracts specification (`docs/api-contracts.md`)
- [x] Relational Database Schema (`docs/database-schema.md`)
- [x] Acceptance Criteria (`docs/acceptance-criteria.md`)
- [x] Research Protocol & IEEE Skeleton (`docs/research-protocol.md`)

### Phase 2: Core Backend Engine & Vertical Slice
- [ ] Backend foundation: FastAPI, SQLite/SQLAlchemy ORM setup, Alembic migrations/tables, Pydantic schemas.
- [ ] Deterministic Synthetic Telemetry Generator (`SyntheticGenerator`) with diurnal seasonality, burst noise, scrub events, and realistic storage distributions.
- [ ] Baseline Forecasting models: Persistence, Seasonal-Naive, Linear/Polynomial trend.
- [ ] Quantile ML Forecaster: LightGBM / HistGradientBoosting multi-quantile (`q10`, `q50`, `q90`).
- [ ] Reserve Runway & Risk Envelope calculation service.
- [ ] End-to-end API vertical slice verification: `/api/v1/health`, `/api/v1/devices`, `/api/v1/devices/{id}/telemetry`, `/api/v1/devices/{id}/forecasts`, `/api/v1/devices/{id}/risks`.
- [ ] Backend test suite running via pytest.

### Phase 3: Digital Twin, Simulator & Recommendation Engine
- [ ] Digital Twin storage state model (`StorageDeviceState`, `WorkloadProfile`, `ConstraintEnvelope`).
- [ ] Counterfactual Action Simulator: `DO_NOTHING`, `EXPAND_CAPACITY`, `TIER_COLD_DATA`, `RESCHEDULE_TASK`, `REBALANCE_WORKLOAD`.
- [ ] Constraint checker (Hard Safety Envelope vs Soft Preferences).
- [ ] Decision ranking engine (Multi-criteria utility optimization).
- [ ] Human Approval & Governance workflow (Shadow mode, approval lifecycle, audit trails).
- [ ] Drift & Reliability Monitor (Residual tracking, coverage diagnostics, fallback trigger).

### Phase 4: Frontend Development ("Obsidian Aurora" UI)
- [ ] Vite + React + TypeScript + Tailwind CSS setup with design tokens.
- [ ] Core layout: Collapsible Navigation, Top Command Bar, Mode Selector, Alerts Pill, Status Center.
- [ ] Page 1: Executive Overview (KPIs, Forecast Horizon selector, Reserve Runway, Central Fan Chart, Risk Timeline, Action Queue).
- [ ] Page 2: Storage Fleet (Search, filtering, health badges, capacity/utilization bar, threshold config).
- [ ] Page 3: Device Intelligence (Deep dive, multi-metric fan charts, risk contributors, breakdown).
- [ ] Page 4: Storage Digital Twin (Interactive sandbox, scenario builder, parameter sliders, side-by-side run).
- [ ] Page 5: Intervention Studio (Ranked recommendation cards, constraint checks, approval modal).
- [ ] Page 6: Telemetry Explorer (Multi-metric graphing, date-range picker, gap visualization, CSV export).
- [ ] Page 7: ML Prediction Lab (Observed vs predicted, horizon selection, quantile bands, inference latency).
- [ ] Page 8: Experiment Workbench (Backtest executor, baseline vs ML comparison, pinball loss/RMSE table).
- [ ] Page 9: Model Reliability (Calibration curves, drift alerts, fallback state indicator).
- [ ] Page 10: Alerts and Incidents (Capacity/Performance/Data-quality alerts, acknowledge/resolve workflow).
- [ ] Page 11: Datasets and Data Quality (Provenance, synthetic/real badge, schema, missingness metrics).
- [ ] Page 12: Settings and Audit (Thresholds, hard safety envelope, audit logs, safe mode toggle).

### Phase 5: Verification, Packaging & Demonstration
- [ ] Automated end-to-end tests (backend tests, frontend type-check, build verification).
- [ ] Demo dataset initialization script (`scripts/seed_demo_data.py`).
- [ ] Live execution smoke test confirming frontend and backend communicate flawlessly.
- [ ] Complete documentation: `README.md`, developer guides, quickstart instructions.
