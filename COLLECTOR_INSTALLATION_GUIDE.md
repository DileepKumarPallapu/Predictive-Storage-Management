# AEGISSTOR — Linux Collector Installation Guide (Phase 7)

## 1. Overview
`backend/scripts/linux_collector_agent.py` (v2.1.0) is a **read-only** host storage telemetry collector (`findmnt`, `os.statvfs`, `lsblk -J -b`, `/proc/diskstats`). It never executes destructive disk operations and requires no inbound ports on the monitored Linux server.

## 2. Features
- **Authentication:** `X-API-Key` header (`--api-key` or `AEGISSTOR_COLLECTOR_API_KEY`).
- **Offline Buffering:** Bounded JSONL spool (`--buffer-path /var/lib/aegisstor/collector_buffer.jsonl`, `--buffer-max-records 1440`) when the backend is unreachable.
- **Duplicate Prevention:** Deterministic `idempotency_key` per batch.
- **Health Status:** Writes local JSON status to `--health-file /var/lib/aegisstor/collector_health.json`.

## 3. Systemd Deployment
1. Copy `backend/scripts/linux_collector_agent.py` to `/opt/aegisstor/linux_collector_agent.py`.
2. Copy `backend/deploy/aegisstor-collector.service` to `/etc/systemd/system/aegisstor-collector.service`.
3. Create `/etc/aegisstor/collector.env` with `AEGISSTOR_SERVER_URL`, `AEGISSTOR_COLLECTOR_API_KEY`, `AEGISSTOR_STORAGE_ID`, `AEGISSTOR_MOUNTPOINT`, `AEGISSTOR_INTERVAL_SEC=60`.
4. Enable and start:
   ```bash
   sudo useradd --system --no-create-home aegisstor-collector
   sudo mkdir -p /var/lib/aegisstor && sudo chown aegisstor-collector:aegisstor-collector /var/lib/aegisstor
   sudo systemctl daemon-reload && sudo systemctl enable --now aegisstor-collector
   ```
5. **Verification Status:** Isolated unit tests (`test_linux_collector_local_buffer_retention_and_clear`) passed; live remote Linux host enrollment is `BLOCKED_BY_INFRASTRUCTURE` (no remote Linux server attached in this Windows session).
