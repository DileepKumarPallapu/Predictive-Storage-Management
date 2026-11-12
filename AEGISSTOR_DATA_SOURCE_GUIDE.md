# AEGISSTOR — Data Source & Connector Guide

## 1. Supported Connector Types (`ConnectorRegistry`)
All connectors operate in **read-only** mode and report honest connection statuses (`CONNECTED`, `NOT_CONFIGURED`, `DRIVER_MISSING`, `CONNECTION_FAILED`, `CONFIGURED`, `ERROR`).

| Connector Type | Purpose | Scope / Provenance |
|---|---|---|
| `LINUX_HOST` | Local host filesystem & disk I/O counters (`psutil` / `/proc/diskstats`) | Physical host capacity & IOPS |
| `PROMETHEUS` | Prometheus HTTP instant query API | Time-series storage & latency metrics |
| `CSV_HISTORICAL` | Bulk CSV telemetry upload & validation preview | Historical capacity & performance |
| `HTTP_API` | Push-mode JSON telemetry ingestion (`/api/v1/telemetry/ingest`) | Agent / external collector push |
| `POSTGRESQL` | Read-only `pg_database_size` & `pg_stat_user_tables` metadata (`psycopg2`) | Logical database & table/index sizes |
| `MYSQL` / `MARIADB` | Read-only `information_schema.TABLES` metadata (`pymysql`) | Logical database metadata |
| `MSSQL` | Read-only `sys.database_files` metadata (`pyodbc`) | Logical database metadata |
| `ORACLE` | Read-only `dba_data_files` / `user_segments` metadata (`oracledb`) | Logical database metadata |

## 2. Security & Privacy Guarantees
- **Read-only enforcement**: PostgreSQL connections execute `conn.set_session(readonly=True, autocommit=True)` and query only system catalog size metadata — never application table rows or PII.
- **Credential redaction**: `GET /api/v1/connectors` redacts `password`, `token`, `secret`, `dsn`, `connection_string`, and `api_key` fields as `***REDACTED***`.
- **Logical vs. Physical Separation**: Database connectors tag outputs with `size_scope: "logical_database_metadata"` so logical DB size is never confused with physical array/host disk capacity.
- **Honest Driver & Config Checks**: Missing credentials return `NOT_CONFIGURED`; missing Python DB drivers return `DRIVER_MISSING`; unreachable hosts return `CONNECTION_FAILED` with the exact error.
