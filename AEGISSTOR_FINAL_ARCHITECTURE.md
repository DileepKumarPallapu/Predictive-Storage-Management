# AEGISSTOR — Final System Architecture

## 1. Platform Overview
**AEGISSTOR** (*Predictive Storage Capacity and Performance Management Using Machine Learning*) is an enterprise storage intelligence, forecasting, risk evaluation, and controlled-operations platform.

## 2. Layered Architecture
1. **Presentation Layer (`frontend/src/`)**
   - React + TypeScript + Vite single-page application organized into **11 user-friendly sections**:
     `Overview`, `Data Sources`, `Storage`, `Monitoring`, `Predictions`, `Risk and Alerts`, `Optimisation`, `Digital Twin`, `Tasks and Approvals`, `Reports`, and `Administration`.
   - Real-time synchronization via WebSocket / event subscription (`RealtimeContext.tsx`) so Administrator and Operator views update automatically without manual page refresh.
   - Plain-English labels with contextual info tooltips (`KpiCard`, `ContextualHelp`).
2. **API & Security Layer (`backend/app/api/v1/`, `backend/app/auth/`)**
   - FastAPI REST endpoints with JWT authentication, role-based access control (`ADMIN`, `OPERATOR`, `VIEWER`, `AUDITOR`), fine-grained permission checks (`require_permission`), and SHA-256 hashed collector API keys.
   - Control Plane governance (`endpoints_control_plane.py`) with typed action definitions, approval gates, and immutable audit trails.
3. **Data Collection & Ingestion Layer (`backend/app/collector/`, `backend/app/services/data_quality_service.py`)**
   - Pluggable read-only connectors in `ConnectorRegistry`:
     - Infrastructure & Telemetry: `LINUX_HOST`, `PROMETHEUS`, `CSV_HISTORICAL`, `HTTP_API`
     - Enterprise Database Metadata (`EnterpriseDatabaseConnector`): `POSTGRESQL`, `MYSQL`, `MARIADB`, `MSSQL`, `ORACLE` (read-only aggregate metadata only, explicitly separated from physical disk capacity).
   - `DataPreprocessingPipeline` validates schemas, timestamps, bounds, duplicates, outliers, and completeness without silently altering raw source history.
4. **ML & Analytical Intelligence Layer (`backend/app/ml/`)**
   - `ChampionChallengerEngine` (`champion_challenger.py`) trains and evaluates `LightGBM` (`LGBMRegressor`) and `SARIMAX` (`statsmodels`) against a `Seasonal-Naive` benchmark using chronological Train / Calibration / Holdout Test splits and Split Conformal uncertainty calibration (`Q10/Q50/Q90`).
   - `DataReliabilityEngine` and `WorkloadRegimeEngine` gate and contextualize predictions.
5. **Persistence Layer (`backend/app/models/entities.py`, `backend/app/database.py`)**
   - SQLAlchemy ORM backed by SQLite (`backend/aegisstor.db` in local runtime) or PostgreSQL in production deployments.
