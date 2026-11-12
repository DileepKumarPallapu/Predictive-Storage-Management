# AEGISSTOR — Sprint 1: Control Plane Foundation Audit

## 1. Existing Application Architecture
- **Backend**: FastAPI (`backend/app/main.py`) with modular v1 routers registered in `backend/app/api/v1/router.py` under `/api/v1`.
- **Database**: SQLAlchemy ORM (`backend/app/database.py`, `backend/app/models/entities.py`, `backend/app/models/enterprise_entities.py`) backed by SQLite (`backend/aegisstor.db`) with Alembic migrations in `backend/alembic/versions/`.
- **Frontend**: React 18 + TypeScript + Vite (`frontend/src/App.tsx`, `frontend/src/components/Sidebar.tsx`, `frontend/src/api/client.ts`) with lazy-loaded pages and permission-gated navigation.

## 2. Database & Migrations
- **Current Alembic Head**: `9fab869f7452_enterprise_transformation.py` (following `g7b8c9d0e1f2_realtime_outbox_tasks_notifications_versions.py`).
- **Existing Connector Table**: `telemetry_connectors` in `entities.py` handles read-only telemetry collection (`LINUX_HOST`, `PROMETHEUS`, `CSV_HISTORICAL`, `HTTP_API`). It is preserved untouched.
- **Sprint 1 Addition**: Dedicated Control Plane tables (`connectors`, `connector_capabilities`, `action_definitions`, `action_requests`, `action_approvals`, `action_preflight_results`, `action_executions`, `action_execution_steps`, `resource_execution_locks`, `control_plane_audit_events`) with foreign keys, `version` optimistic locking, and `idempotency_key` uniqueness.

## 3. Authentication & RBAC
- **Auth & Sessions**: JWT Bearer tokens (`app/auth/security.py`) with `User`, `UserSession`, and `RevokedToken` persistence.
- **Permissions**: Dynamic RBAC in `app/auth/permissions.py` (`PERMISSION_CATALOG`, `DEFAULT_ROLE_PERMISSIONS`, `require_permission(...)`) supporting `ADMIN`, `OPERATOR`, `VIEWER`, and `AUDITOR`.
- **Multi-Tenant Resolution**: `app/auth/tenant.py` (`resolve_organization_id`, `assert_org_resource`) enforces `organization_id` isolation via `X-Organization-ID` and `OrganisationMember`.

## 4. Administrator / Operator Real-Time Communication
- **Outbox & WebSocket Bus**: `app/realtime/event_bus.py` (`OutboxService.stage_event` / `emit_and_commit` / `publish_after_commit`, `RealtimeConnectionManager`) guarantees events are persisted in `outbox_events` inside the DB transaction and published only after commit.
- **Reconnect & Missed-Event Recovery**: `endpoints_realtime.py` (`/ws`, `/realtime/events?since_seq_id=...`) and `frontend/src/context/RealtimeContext.tsx` track `lastSeqId` and replay missed events on reconnect.
- **Secret Redaction**: `sanitize_payload()` recursively redacts `password`, `secret`, `token`, `api_key`, `credential`, `private_key`, `auth_header`.

## 5. Reusable Components Identified
- `OutboxService.emit_and_commit` & `raise_if_version_conflict` (`app/realtime/event_bus.py`)
- `require_permission` (`app/auth/permissions.py`) & `resolve_organization_id` (`app/auth/tenant.py`)
- `AuditService.log_event` (`app/services/audit_service.py`)
- `useRealtime` / `useRealtimeSubscription` (`frontend/src/context/RealtimeContext.tsx`)
- `api` client & `invalidateApiCache` (`frontend/src/api/client.ts`)
- Existing `Device`, `Telemetry`, `StoragePoolEntity`, `StorageVolume` models for real read-only inspection & preflight checks.

## 6. Sprint 1 Scope & Guardrails
- **No Plain-Text Credentials**: Connectors store `credential_ref` only (e.g., `env://...`, `vault://...`, or redacted metadata); raw secrets are never persisted in plain text or returned over API/WebSocket.
- **Read-Only Operations Only**: Sprint 1 implements `RESOURCE_INSPECT`, `CAPACITY_INSPECT`, `CONNECTOR_HEALTH_CHECK`, and `CONFIG_INSPECT`. No destructive infrastructure modifications are executed in Sprint 1.
