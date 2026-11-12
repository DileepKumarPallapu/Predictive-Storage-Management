# AEGISSTOR — Initial Repository & Technical Assessment (`PROJECT_ASSESSMENT.md`)

**Official Project Title:** Predictive Storage Capacity and Performance Management Based on Machine Learning  
**Platform:** AEGISSTOR – Storage Resilience Intelligence Platform

---

## 1. Existing Architecture
AEGISSTOR is structured as a decoupled full-stack platform consisting of:
- **Backend (`backend/`)**: FastAPI REST service (`app/main.py`) mounted under `/api/v1` (with `/api` compatibility alias), backed by SQLAlchemy ORM (`app/models/entities.py`), Alembic schema migrations (`backend/alembic/`), read-only telemetry collectors (`app/collector/`), a multi-engine ML forecasting & drift pipeline (`app/ml/`), and deterministic domain engines (`app/services/`).
- **Frontend (`frontend/`)**: Single-page React + TypeScript + Vite application (`frontend/src/App.tsx`) using Tailwind CSS design tokens, light/dark themes, Lucide icons, lazy-loaded route pages (`35` files under `frontend/src/pages/`), and centralized API client caching (`frontend/src/api/client.ts`).
- **Deployment & Automation**: Dockerfiles (`backend/Dockerfile`, `frontend/Dockerfile`), `docker-compose.yml`, `render.yaml`, `vercel.json`, and GitHub workflow configuration (`.github/workflows`).

## 2. Technology Stack
- **Frontend**: React 19, TypeScript, Vite, Lucide Icons, custom SVG/canvas charts, `oxlint`, Playwright/manual E2E scripts.
- **Backend**: Python 3.11/3.13, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, Alembic 1.13+.
- **Database**: SQLAlchemy multi-backend engine supporting PostgreSQL (`psycopg2-binary`) via `DATABASE_URL` in containerized/production deployments and SQLite for standalone local runs.
- **Machine Learning & Analytics**: `lightgbm` (`LGBMRegressor`), `statsmodels` (`SARIMAX`), `scikit-learn` (`RandomForestRegressor`, `HistGradientBoostingRegressor`), `pandas`, `numpy`, `joblib`.
- **Security**: `argon2-cffi` (Argon2id primary password hashing), `bcrypt` (legacy verification compatibility), `pyjwt` (HS256 signed JWTs), persistent `user_sessions`, SHA-256 single-use password reset tokens, double-submit CSRF tokens (`X-CSRF-Token`), and tamper-evident chained `audit_logs`.

## 3. Completed Components
- **Authentication, Session Security & Central RBAC Engine (`app/auth/security.py`, `app/auth/permissions.py`, `app/api/v1/endpoints_auth.py`)**: Argon2id hashing, 58-key permission catalog mapped in `roles` / `permissions` / `role_permissions`, protected `/auth/setup` bootstrap, username/email login, brute-force lockout (`429`), `user_sessions` immediate revocation, `password_reset_tokens`, and fail-closed `401` / `403` enforcement.
- **Role-Specific Frontends**: Dedicated `/setup`, `/login`, `/forgot-password`, `/reset-password`, `/admin`, `/operator`, `/viewer`, `/access-denied` routes (`PageAuthPortal`, `PageOperatorDashboard`, `PageViewerDashboard`, `PageUserManagement`, `PageAccessDenied`).
- **Two-Model Champion-Challenger ML Pipeline (`app/ml/champion_challenger.py`)**: Causal lag/rolling/calendar feature engineering, chronological train/calibration/test split, LightGBM (`LGBMRegressor`) + `SARIMAX` + Seasonal-Naive baseline evaluation (MAE, RMSE, R², MASE, Pinball Loss, interval coverage), Split Conformal bounds, Data Reliability gating, and `.joblib` artifact persistence.
- **Real Telemetry Collectors (`app/collector/connector_registry.py`, `backend/scripts/linux_collector_agent.py`)**: Read-only Linux Host (`os.statvfs` / `shutil.disk_usage` / `/proc/diskstats` / `findmnt` / `lsblk` spaced rate deltas), configurable Prometheus PromQL querying, CSV template/preview/validation/commit workflow, and X-API-Key authenticated `/telemetry/ingest`.
- **Digital Twin, Risk, Recommendations, Alerts, Reports & Audit (`app/services/`, `app/api/v1/`)**: Constrained Digital Twin simulations (`CAPACITY_EXPANSION`, `TIER_COLD_DATA`/`DATA_TIERING_ARCHIVAL`, `WORKLOAD_REBALANCING`, etc.), Capacity Runway, Performance Risk, Alert lifecycle (`acknowledge`, `assign`, `resolve`, `reopen`), Non-self-approval recommendation queue, JSON/CSV/PDF report exports (`reportlab`), and hash-chained audit logs.

## 4. Incomplete Components & Remediation Applied During Audit
1. **Docker Compose Persistence**: Updated `docker-compose.yml` from SQLite demo config to `postgres:16-alpine` + `redis:7-alpine` with healthchecks and persistent volumes, and added `psycopg2-binary>=2.9.9` and `psutil>=5.9.0` to `backend/requirements.txt`.
2. **Linux Cumulative Counter vs Rate Bug**: `LinuxStorageConnector` previously returned monotonic cumulative I/O counts (`io.read_count`); repaired to compute spaced time-delta rates and added standalone `backend/scripts/linux_collector_agent.py`.
3. **Production Clean Startup Guarantee**: Gated synthetic seeding and legacy test credentials in `backend/app/main.py` behind `AEGISSTOR_SEED_SYNTHETIC_DEMO=true` / `PYTEST_CURRENT_TEST` so live deployments start cleanly without synthetic fixtures.
4. **Nullable Telemetry Field Guards**: Fixed `NoneType` exceptions in `incident_correlation.py`, `digital_twin.py`, `endpoints_metrics.py`, `performance_risk_engine.py`, `adaptive_monitor.py`, and `bottleneck_engine.py` when CSV/Prometheus sources omit latency/IOPS metrics.
5. **Overview Empty-State Hardcoding**: Removed synthetic 70% fallback utilization and hardcoded `vol-nvme-tier1-db` critical breach items in `endpoints_overview.py` when zero devices/telemetry exist.

## 5. Broken Components Identified & Fixed
- **Stale Token Storage Keys in Frontend**: Fixed `PageAuditLogs.tsx` and `PageReports.tsx` reading non-existent `aegisstor_auth_token` instead of `authStorage.getToken()` (`aegisstor_jwt`), and added authenticated blob export in `PageReports.tsx`.
- **OperationalAssignment / UserSession Schema Mismatches**: Aligned `endpoints_alerts.py` (`assigned_to_user_id`), `auth_helper.py` (`session_token_hash`), `PageAuthPortal.tsx` (`reset_token_dev`), and `PageUserManagement.tsx` (`permissions`/`role_matrix`/`logs`/`login_attempts`).
- **Atlas Discrepancy ID Collision**: Fixed truncated `run_id[:12]` primary key generation in `calibration_engine.py` that triggered SQLite `IntegrityError` across repeated calibration runs.

## 6. Placeholder & Synthetic-Data Assessment
- Synthetic telemetry generation (`app/collector/synthetic.py`) is retained exclusively for explicit test/demo fixtures (`PYTEST_CURRENT_TEST` or `AEGISSTOR_SEED_SYNTHETIC_DEMO=true`).
- No live endpoint silently generates fictional metrics when real collectors are unconfigured; unsupported metrics remain `None` (rendered as unavailable) rather than `0`.

## 7. Database Assessment
- Schema consists of **71 SQLAlchemy models** (`entities.py`) backed by Alembic migrations (`alembic/versions/a1b2c3d4e5f6` -> `f6a7b8c9d0e1`).
- Foreign keys, indexes, unique constraints (`users.username`, `users.email`, `user_sessions.session_token_hash`, `role_permissions`), and hash-chained `audit_logs` are implemented and operational.

## 8. ML Implementation Assessment
- **Verified**: `ChampionChallengerEngine` (`app/ml/champion_challenger.py`) trains both LightGBM and SARIMAX on chronological splits and compares against Seasonal-Naive baselines without target leakage.
- **Verified**: `CapacityMLEngine` (`app/ml/sklearn_engine.py`) trains RandomForestRegressor & HistGradientBoostingRegressor on chronological validation splits and saves `.joblib` artifacts to `backend/artifacts/`.

## 9. API Assessment
- Every API router under `/api/v1` enforces `require_permission(...)` or `require_method_permission(...)` (leaving only `/health`, `/auth/setup-status`, `/auth/setup`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, and `/metrics` open as designed).
- Background training jobs (`/v2/models/train-async/{storage_id}` + `/jobs/{job_id}`) run asynchronously without blocking API threads.

## 10. Ongoing External Configuration & Recommendations
- Real remote Linux host monitoring and Prometheus monitoring require target host OS / Prometheus URL + network credentials from the deployment environment.
- SMTP delivery for password resets is optional; when no external mail relay is integrated, Admins generate single-use out-of-band reset tokens directly in `/users`.
