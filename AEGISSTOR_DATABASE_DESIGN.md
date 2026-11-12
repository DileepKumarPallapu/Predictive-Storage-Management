# AEGISSTOR — Database Design

## 1. Storage Engine
- Local development/verification runtime: SQLite (`backend/aegisstor.db`) via SQLAlchemy ORM (`backend/app/database.py`).
- Production target: PostgreSQL (configured via `DATABASE_URL`).

## 2. Core Entities (`backend/app/models/entities.py`)
- **Identity & Access**: `User`, `ApiKey` (SHA-256 hashed), `RolePermission`, `AuditLog`
- **Storage & Telemetry**: `Device` (storage pools/volumes), `Telemetry` (time-series capacity, IOPS, latency, throughput), `TelemetryConnector`, `IngestionJob`, `DataQualityResult`
- **ML & Forecasting**: `ModelVersion` (champion/challenger artifacts & status), `ModelMetric` (MAE, RMSE, R2, MAPE, WAPE, MASE, Pinball loss, interval coverage, width), `Forecast` (Q10/Q50/Q90 horizons)
- **Risk, Operations & Governance**: `Alert`, `OperationalTask`, `TaskComment`, `Recommendation`, `ApprovalRequest`, `ReportHistory`
- **Control Plane (Sprint 1)**: Persistent connector records, typed action definitions, action execution logs, and approval gates.

## 3. Data Integrity Principles
- Raw source ingestion jobs (`IngestionJob`) and quality evaluations (`DataQualityResult`) are persisted separately from accepted `Telemetry` rows.
- Duplicate timestamps are detected and counted without overwriting or silently deleting existing source history.
- Sensitive credentials in `TelemetryConnector.config_json` and `ApiKey` are never returned in plaintext on read endpoints.
