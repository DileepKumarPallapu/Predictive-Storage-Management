# AEGISSTOR — Real-Time Implementation & Synchronization Audit

**Date:** 2026-11-12  
**Scope:** Backend APIs, Database Schema, Async ML Jobs, Eventing, Concurrency Control, Presence, Notifications, Task Collaboration, and Frontend State Synchronization.

---

## 1. Executive Audit Findings

Before the real-time synchronization upgrade, AEGISSTOR operated as a **request/response REST application with short-lived client query caching**, lacking push delivery, transactional event persistence, optimistic concurrency control, and multi-user collaboration primitives.

| Capability Area | Current State Observed | Gap / Risk | Required Real-Time Implementation |
|---|---|---|---|
| **WebSocket Transport** | No WebSocket endpoint in `backend/app/api/v1/router.py` or `main.py` | Clients only see updates after manual refresh or cache expiry | Authenticated `/api/realtime/ws` & `/api/v1/realtime/ws` supporting `HttpOnly` cookie + Bearer/query JWT validation and active session checks |
| **Transactional Outbox** | No `outbox_events` table in `backend/app/models/entities.py` | Emitting events before commit risks phantom UI updates on rollback; missed events on reconnect cannot be recovered | `OutboxEvent` table with monotonic `seq_id` cursor, written in the same DB transaction and published only after `db.commit()` |
| **Optimistic Concurrency** | `Device`, `Scenario`, `ApplicationSetting`, `BackgroundJob` lack `version` columns; no `409 Conflict` checks | Concurrent Admin + Operator edits silently overwrite each other (last-write-wins) | Add `version`, `updated_at`, `created_by`, `updated_by` to shared mutable entities; return `409 Conflict` with authoritative server state on stale writes |
| **ML Training Progress** | `BackgroundJob` (`endpoints_intelligence.py:48-82`) only transitions `QUEUED -> RUNNING -> COMPLETED/FAILED` | Clients have no visibility into validation, feature engineering, training, evaluation, or model saving stages | Real backend stage progression (`QUEUED`, `VALIDATING_DATA`, `PREPARING_FEATURES`, `TRAINING`, `EVALUATING`, `SAVING_MODEL`, `COMPLETED`, `FAILED`, `CANCELLED`) persisted to DB and emitted post-commit |
| **Operational Tasks & Comments** | Only `OperationalAssignment` (`entities.py:1472`) exists for basic alert assignment; no task lifecycle or comment thread | Admin cannot assign structured capacity/remediation tasks with due dates and track Operator progress in real time | `OperationalTask` (`ASSIGNED`, `ACKNOWLEDGED`, `IN_PROGRESS`, `WAITING`, `COMPLETED`, `CANCELLED`) + `TaskComment` + `/api/v1/tasks*` endpoints + live events |
| **Persistent Notifications** | No `user_notifications` table; alerts/approvals only appear when polling | Offline or temporarily disconnected users miss critical approvals, assignments, and threshold alerts | `UserNotification` table persisted alongside outbox events, with unread count, mark-read, and reconnect recovery |
| **Authenticated Presence & Activity Feed** | No live presence tracking; `AuditLog` has no push stream | Admin cannot see which Operators/Viewers are currently connected or view live activity stream | `UserPresence` table backed by WS connect/heartbeat/disconnect + `/realtime/presence` & `/realtime/activity` |
| **Immediate Access Revocation** | `UserSession` revocation (`endpoints_auth.py`) invalidates future REST calls only | Active WebSocket connections could remain open after user deactivation, role change, or session revocation | Explicit WebSocket registry termination hook triggered immediately upon user deactivation, role modification, or session revocation |
| **Frontend Sync & Cache Invalidation** | `frontend/src/api/client.ts` uses an in-memory `queryCache` with manual `invalidateApiCache` calls | Mutations by another user never invalidate the local client's stale cache | `RealtimeContext` managing WS lifecycle (`LIVE` / `RECONNECTING` / `DISCONNECTED`), `since_seq` replay, automatic `queryCache` invalidation, and `aegisstor:realtime-event` broadcast |

---

## 2. Target Architecture Summary

1. **Same-Transaction Outbox + Post-Commit Fan-Out**: Every successful state mutation (`Device`, `Telemetry`, `Ingestion`, `BackgroundJob`, `Forecast`, `CapacityRiskEvaluation`, `Alert`, `Scenario`, `Recommendation`, `OperationalTask`, `Report`, `ApplicationSetting`, `User`) writes an `OutboxEvent` (and target `UserNotification` rows when applicable) inside the active SQLAlchemy transaction. Only after `db.commit()` succeeds does the dispatcher push the sanitized envelope to Redis Pub/Sub (when `REDIS_URL` is configured) and to permission-filtered WebSocket connections.
2. **Permission-Filtered Delivery & Secret Hygiene**: Every WebSocket connection binds to a validated `UserSession` and resolved RBAC permission set. Events are delivered only to authorized recipients and never include connector credentials, passwords, or token hashes.
3. **Reconnect & Cursor Recovery**: Clients track `last_seq_id`. Upon WebSocket reconnect, the client replays missed events via `GET /api/v1/realtime/events?since_seq=<last_seq_id>` or `?since_seq=` on the WS handshake and reconciles cache state without losing updates.
