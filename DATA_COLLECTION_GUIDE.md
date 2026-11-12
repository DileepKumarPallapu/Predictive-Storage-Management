# AEGISSTOR — Data Collection & Ingestion Guide (`DATA_COLLECTION_GUIDE.md`)

## Supported Telemetry Connectors & Sources
AEGISSTOR separates **observed telemetry** (`is_synthetic=False`) from isolated test fixtures across four read-only collection paths:

1. **Linux Host Storage Collector (`LINUX_HOST`)**: Collects mounted filesystem capacity (`total`, `used`, `free`, `utilization_pct`), host identity, and spaced `/proc/diskstats` or `psutil.disk_io_counters()` rate deltas. See [LINUX_COLLECTOR_GUIDE.md](LINUX_COLLECTOR_GUIDE.md).
2. **Prometheus / Exporter Collector (`PROMETHEUS`)**: Executes read-only PromQL instant queries over HTTP/HTTPS with Bearer or Basic authentication and configurable metric mappings. See [PROMETHEUS_INTEGRATION_GUIDE.md](PROMETHEUS_INTEGRATION_GUIDE.md).
3. **Historical CSV Import (`CSV_HISTORICAL`)**: Interactive Upload -> Column Inspection -> Validation -> Preview -> Duplicate & Error Report -> Commit pipeline (`/api/v1/ingestion/csv/preview` & `/import`).
4. **Authenticated Push API (`HTTP_API`)**: Batch JSON telemetry ingestion (`POST /api/v1/telemetry/ingest`) authenticated by `X-API-Key` (or Operator/Admin session) with `Idempotency-Key` deduplication.

## CSV Telemetry Schema
Retrieve the canonical CSV header via `GET /api/v1/ingestion/template`:
```csv
timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps
```
- **Required fields**: `timestamp` (ISO-8601 UTC), `storage_id`, `used_capacity_bytes` (>= 0), `total_capacity_bytes` (> 0, >= used).
- **Optional performance fields**: `read_iops`, `write_iops`, `read_latency_ms`, `write_latency_ms`, `throughput_mbps`. Leave blank when unmeasured; AEGISSTOR stores omitted optional metrics as `NULL` (unavailable) rather than fabricating zeros.

## Connector Status Lifecycle
- `CONFIGURED`: Registered, awaiting initial probe.
- `CONNECTED`: Explicit connection test succeeded with valid response.
- `ERROR` / `CONNECTION_FAILED`: Reachability or authentication failure with safe diagnostic detail.
- `NOT_CONFIGURED`: External infrastructure URL or credentials not yet provided.
