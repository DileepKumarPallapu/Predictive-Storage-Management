# AEGISSTOR — Security Report

## 1. Authentication & Authorization
- **JWT Authentication**: Endpoints require valid bearer tokens (`get_current_user`).
- **RBAC & Permission Guards**: All routes enforce granular permissions (`require_permission(...)`) across `ADMIN`, `OPERATOR`, `VIEWER`, and `AUDITOR` roles.
- **API Keys**: Collector keys are hashed at rest using SHA-256 (`hash_token`) and shown only once at issuance.

## 2. Connector & Credential Protection
- **Secret Redaction**: `GET /api/v1/connectors` redacts any config key containing `password`, `token`, `secret`, `dsn`, `connection_string`, or `api_key` as `***REDACTED***`.
- **Control Plane Plain-Text Guard**: `POST /api/v1/control-plane/connectors` rejects plain-text credentials (`422`), requiring secret/env references (`env://...`).
- **Read-Only Database Metadata**: Enterprise database connectors enforce read-only sessions (`readonly=True` for PostgreSQL) and query only aggregate size catalogs (`pg_database_size`, `pg_stat_user_tables`), never reading application rows or PII.

## 3. Auditability
- Security-sensitive actions (connector registration, logins, approvals, user/role updates, Control Plane executions) are recorded in `AuditLog` via `AuditService.log_event`.
