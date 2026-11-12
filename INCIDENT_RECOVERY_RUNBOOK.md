# AEGISSTOR — Incident Recovery Runbook (Phase 11)

## Scenario A: Database Temporarily Unavailable
- **Detection:** `/health/ready` and `/health/database` return `503 Service Unavailable` (`connected: false`).
- **System Behavior:** Transactions roll back cleanly; no partial commits; API returns explicit error rather than fake success.
- **Recovery:** Restore Managed PostgreSQL connectivity / failover primary; `pool_pre_ping=True` automatically recycles stale connections.

## Scenario B: Redis / Event Distribution Unavailable
- **Detection:** `/health/realtime` reports `redis_configured: false` or Pub/Sub connection warning in logs.
- **System Behavior:** Authoritative state and `OutboxEvent` rows remain persisted in PostgreSQL/SQLite. Connected clients on the same instance still receive events; cross-instance clients recover missed events via `GET /api/v1/realtime/events?since_seq=...`.
- **Recovery:** Restore Redis service; `event_bus.py` resumes Pub/Sub fan-out.

## Scenario C: Background Worker Crashes During ML Training
- **Detection:** `/health/worker` reports `status: stale` (heartbeat age > `3 * WORKER_HEARTBEAT_INTERVAL_SEC`) or `BackgroundJob` stuck in `RUNNING`.
- **System Behavior:** On worker restart, `worker.recover_stale_jobs()` marks abandoned `RUNNING` jobs as `FAILED` (never falsely `COMPLETED`). Partial `.joblib` artifacts are not promoted; the previous `CHAMPION` model remains active. Verified in `test_worker_stale_job_recovery_marks_failed`.
- **Recovery:** Inspect `BackgroundJob.error_message` and re-queue training safely.

## Scenario D: Linux Collector Loses Network Connectivity
- **Detection:** Collector local health file (`/var/lib/aegisstor/collector_health.json`) reports `disconnected_buffering`; backend `/health` / fleet shows stale `last_telemetry_at`.
- **System Behavior:** `linux_collector_agent.py` spools samples to bounded JSONL buffer (`--buffer-max-records`, default `1440`) and replays in batch with deterministic `idempotency_key` upon reconnect. Verified in `test_linux_collector_local_buffer_retention_and_clear`.

## Scenario E: Frontend Disconnects During Update
- **System Behavior:** Backend determines authoritative outcome (`200`/`409`/`4xx`). Client `RealtimeContext` reconciles latest server state upon reconnect and optimistic concurrency (`expected_version`) prevents silent overwrites (`409 VERSION_CONFLICT`).

## Scenario F: Deployment Interrupts WebSockets
- **System Behavior:** `main.py` shutdown closes active WebSockets cleanly (`1001 server_shutdown`); clients reconnect with exponential backoff, re-authenticate, replay missed `OutboxEvent` sequence IDs via `since_seq`, and refresh affected UI views.
