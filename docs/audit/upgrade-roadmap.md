# AEGISSTOR — Full-System Upgrade Roadmap (v3.0)

**Platform:** AEGISSTOR — Storage Resilience Intelligence Platform  
**Target Milestone:** Full Production & Scientific Research Grade Upgrade  
**Execution Strategy:** Incremental, non-destructive upgrades with continuous verification  

---

## 1. Upgrade Phases & Sequencing

### Phase 1: Dependency & Runtime Hardening
- Ensure `alembic`, `pyjwt`, `bcrypt`, `prometheus-client` are pinned and verified in `requirements.txt`.
- Verify runtime compatibility on Python 3.13 and Node.js v24.

### Phase 2 & 3: Frontend Architecture & UI/UX Excellence
- Add a centralized `ErrorBoundary` and notification toast system.
- Standardize all modal dialogs (Add Device, New Scenario, Acknowledge Alert, Approve Recommendation).
- Enhance the Obsidian Aurora UI with keyboard shortcuts (`Cmd/Ctrl+K` for global device search, quick-switch between views).
- Ensure high contrast, accessible charts, and crisp layout responsiveness.

### Phase 3 & 4: API & Backend Engineering Upgrade
- Request tracing middleware with unique `X-Request-ID` and latency header.
- Structured JSON logging.
- Advanced query pagination, filtering, and time-range clamping on all telemetry and audit endpoints.
- Separation of Operational Health (`/api/v1/health`) from Model Reliability (`/api/v1/reliability`).

### Phase 5 & 6: Telemetry Adapter & Storage Monitoring Upgrade
- Add Prometheus-compatible `/metrics` scrape endpoint.
- Enhance data provenance indicators (`SYNTHETIC DEMO DATA` vs `OBSERVED HARDWARE`).
- Add Telemetry Freshness warning flags and automated missing-interval detection.

### Phase 7 & 8: Machine Learning & Multi-Target Forecasting
- Expand forecasting models to handle multiple targets:
  1. `used_bytes` (Capacity runway)
  2. `total_iops` (I/O load)
  3. `latency_ms` (SLA breach risk)
- Add Mean Absolute Scaled Error (MASE) calculation alongside MAE and RMSE.
- Calibrate prediction intervals using conformal quantile adjustment.

### Phase 9 & 10: Storage Resilience Digital Twin & Action Planner
- Enhance counterfactual intervention simulations with detailed contention modeling (I/O bandwidth degradation during live migration).
- Support custom what-if scenario parameter overrides (e.g. migration rate, compression ratio).
- Enforce Hard Safety Envelope: automatically reject any action that breaches SLA limits or cannot complete before estimated runway exhaustion.

### Phase 11: Scientific Research & Experiment Workbench
- Formalize reproducible ablation experiments with exportable JSON/CSV results.
- Add an IEEE manuscript structure template in `docs/` with empirical data tables.

### Phase 12: Security, RBAC & Audit Integrity
- Add JWT token issuance and validation (`/api/v1/auth/login`, `/api/v1/auth/me`).
- Enforce Role-Based Access Control: `ADMIN`, `OPERATOR`, `AUDITOR`.
- Secure password hashing using bcrypt.
- Pass authenticated identity into append-only audit logs.

### Phase 13 & 14: Testing, Performance & Verification
- Expand test suite to test authentication, RBAC, telemetry freshness, multi-target forecasting, and Prometheus metrics.
- Verify 100% test pass rate with zero regressions.
- Verify production frontend build (`npm run build`).

### Phase 15 & 16: Documentation & Acceptance Report
- Complete setup manuals, API specifications, and the Final Upgrade Report.
