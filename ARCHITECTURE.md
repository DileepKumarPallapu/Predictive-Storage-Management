# AEGISSTOR — System Architecture (`ARCHITECTURE.md`)

## 1. Application Architecture
AEGISSTOR implements a four-layer decoupled storage resilience architecture:
1. **Presentation Layer (`frontend/`)**: React 19 + TypeScript + Vite SPA serving role-based routes (`/setup`, `/login`, `/admin`, `/operator`, `/viewer`, `/access-denied`, plus operational modules). Communicates over REST with JWT Bearer + `HttpOnly` cookie sessions + `X-CSRF-Token`.
2. **API & Security Gateway (`backend/app/main.py`, `backend/app/auth/`, `backend/app/api/v1/`)**: FastAPI application with request tracing (`X-Request-ID`, `X-Process-Time-Ms`), sliding-window rate limiting (`X-RateLimit-Remaining`), security headers (CSP, `X-Frame-Options`, `X-Content-Type-Options`), Argon2id auth, and central DB-backed RBAC (`require_permission`).
3. **Domain, Telemetry & ML Engines (`backend/app/collector/`, `app/ml/`, `app/services/`, `app/simulator/`)**:
   - Collectors: `LinuxStorageConnector`, `PrometheusConnector`, `CsvHistoricalConnector`, `HttpIngestionConnector`, and standalone `linux_collector_agent.py`.
   - Data Quality & Workload Engines: `DataPreprocessingPipeline`, `DataReliabilityEngine`, `WorkloadRegimeEngine`.
   - ML & Forecasting: `ChampionChallengerEngine` (LightGBM + SARIMAX + Split Conformal calibration), `CapacityMLEngine`.
   - Decision & Governance: `CapacityRiskEngine`, `PerformanceRiskEngine`, `DigitalTwinSimulator`, `DecisionOptimizer`, `RecommendationEngine`, `ReportingService`, `AuditService`.
4. **Persistence Layer (`backend/app/database.py`, PostgreSQL / SQLite, Artifacts)**: Relational database via SQLAlchemy ORM + Alembic migrations, plus disk-persisted `.joblib` model binaries and vault backup bundles.

## 2. Component Relationships
```
[External Linux Host / Prometheus / CSV / API Clients]
                  │ (X-API-Key / Read-Only Pull)
                  ▼
     [ConnectorRegistry & Ingestion Pipeline]
                  │ (Validate Schema & Bounds)
                  ▼
  [PostgreSQL / SQLite Telemetry + DataQualityResult]
        │                          │
        ▼                          ▼
[DataReliabilityEngine]    [WorkloadRegimeEngine]
        │                          │
        └──────────┬───────────────┘
                   ▼
     [ChampionChallengerEngine (LightGBM + SARIMAX)]
                   │ (Chronological Val + Split Conformal)
                   ▼
   [Forecasts] ──► [CapacityRiskEngine & Alert Engine]
        │                          │
        └──────────┬───────────────┘
                   ▼
[DigitalTwinSimulator & DecisionOptimizer] ──► [Recommendations / Non-Self-Approval Queue]
                   │
                   ▼
    [AuditService (Hash-Chained) & ReportingService (JSON/CSV/PDF)]
```

## 3. Database Architecture
- See [DATABASE_DESIGN.md](DATABASE_DESIGN.md) for full entity groups across IAM (`users`, `roles`, `permissions`, `role_permissions`, `user_sessions`, `password_reset_tokens`, `login_attempts`), Storage Inventory, Telemetry & Data Quality, ML Training & Forecasts, Digital Twin Scenarios, Alerts, Recommendations, Reports, and Immutable Audit Logs.

## 4. API Architecture
- RESTful endpoints organized by resource domain under `/api/v1/`:
  - `/auth/*`, `/users/*`, `/permissions/*`: Auth, sessions, resets, RBAC catalog & live matrix editing.
  - `/storage/*` & `/devices/*`: Storage pool inventory, topology, per-resource threshold configuration.
  - `/connectors/*`, `/ingestion/*`, `/telemetry/*`: Connector testing/collection, CSV preview/import/template/error export, batch API ingestion.
  - `/data-quality/*`, `/reliability/*`, `/workload-regime/*`: Completeness scoring, changepoints, distribution drift.
  - `/v2/models/*`, `/models/*`, `/jobs/*`, `/v2/forecasts/*`, `/forecasts/*`: Sync/async training, metric comparison, calibrated quantile forecasts, runway.
  - `/risk/*`, `/performance/*`, `/alerts/*`, `/digital-twin/*`, `/planning/*`, `/recommendations/*`, `/reports/*`, `/settings`, `/audit`: Risk, SLA monitoring, scenarios, optimization, approvals, exports, audit ledger.

## 5. Core Processing Flows
- **Data Collection Flow**: Authenticated connector (`LINUX_HOST`, `PROMETHEUS`, CSV, or `HTTP_API`) reads storage bytes & rate deltas -> validates positive capacity (`0 <= used <= total`) and valid ISO-8601 UTC timestamps -> rejects impossible values into `errors_json` -> writes unique telemetry rows (`device_id`, `timestamp`) -> computes `DataQualityResult` & `DataReliabilityProfile`.
- **ML Training Flow**: Checks `MIN_RECORDS` (`>= 60`) and reliability eligibility -> builds strictly causal lag/rolling/calendar/exogenous features -> splits chronologically into Train / Calibration / Validation windows -> fits LightGBM (`LGBMRegressor`) and `SARIMAX` -> scores MAE/RMSE/R²/MASE/interval coverage against Seasonal-Naive baseline -> persists winning `.joblib` artifact + `ModelVersion` + `ModelMetric` without overwriting healthy existing models if training fails.
- **Forecasting Flow**: Loads active model artifact for target `storage_id` -> produces `1/7/14/30/60/90`-day median (`q50`) and conformal (`q10`, `q90`) trajectories -> evaluates capacity threshold crossing dates -> persists `Forecast` row.
- **Risk Evaluation Flow**: Computes remaining safe capacity (`total * threshold_pct - used`), growth rate statistics, threshold crossing probability, and classifies `NORMAL`, `WARNING`, `CRITICAL`, or `UNKNOWN`.
- **Digital Twin Flow**: Reads baseline telemetry + saved forecast -> simulates non-destructive interventions (`CAPACITY_EXPANSION`, `TIER_COLD_DATA`, `WORKLOAD_REBALANCING`, `CAPACITY_GROWTH_CHANGE`, `MAINTENANCE_PLANNING`) -> validates hard safety bounds (`max_latency_sla`, capacity ceiling) -> saves `Scenario` & `SimulatedOutcome`.
