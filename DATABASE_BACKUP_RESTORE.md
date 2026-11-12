# AEGISSTOR — Database Backup & Restore Guide (Phase 5)

## 1. Recovery Objectives
- **Recovery Point Objective (RPO):** <= 1 hour (automated continuous WAL / point-in-time recovery on Managed PostgreSQL; 1-hour snapshot cadence for local Vault backups).
- **Recovery Time Objective (RTO):** <= 60 seconds for local snapshot restore; <= 15 minutes for Managed PostgreSQL PITR / `pg_restore`.

## 2. Production PostgreSQL Strategy
- **Backup Frequency:** Daily automated full base backups + continuous WAL archiving (Render Managed PostgreSQL PITR) with 7–30 day retention.
- **Connection Security:** TLS enforced (`DB_SSL_MODE=require`) with SQLAlchemy pooling (`DB_POOL_SIZE=10..20`, `DB_MAX_OVERFLOW=20..30`, `pool_pre_ping=True`).
- **Migrations:** `cd backend && python -m alembic upgrade head` (current head: `g7b8c9d0e1f2`).
- **Rollback Strategy:** `python -m alembic downgrade -1` for reversible schema changes, or restore from pre-migration snapshot before redeploying previous release.

## 3. Restore Verification Executed (2026-11-12)
An isolated online backup-and-restore test was executed against `backend/aegisstor.db` (`77,615,104` bytes) into an isolated temporary database:
- **Backup Duration:** `495.38 ms`
- **Restore Duration:** `340.17 ms`
- **SHA-256 Checksum Match:** `true`
- **SQLite `PRAGMA integrity_check`:** `ok`
- **Verified Entity Counts Post-Restore:**
  - Users: `7`
  - Storage Resources: `13`
  - Telemetry History: `3,027`
  - Model Metadata: `46`
  - Forecasts: `48`
  - Alerts: `4`
  - Recommendations / Approvals: `33`
  - Reports: `126`
  - Audit History: `2,762`
- **Managed PostgreSQL Restore Status:** `BLOCKED_BY_INFRASTRUCTURE` (Docker daemon and `psql` not running/installed in this environment).
