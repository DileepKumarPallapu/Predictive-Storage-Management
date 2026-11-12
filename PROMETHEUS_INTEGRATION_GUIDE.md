# AEGISSTOR — Prometheus Integration Guide (`PROMETHEUS_INTEGRATION_GUIDE.md`)

## Architecture
`PrometheusConnector` (`backend/app/collector/connector_registry.py`) executes read-only HTTP/HTTPS `GET /api/v1/query` calls against a configured Prometheus server or storage exporter target.

## Supported Configuration Fields
When registering or editing a Prometheus connector:
- **`endpoint_url`**: Base URL of your Prometheus server (e.g. `https://prometheus.internal:9090`).
- **Authentication (Optional)**: `bearer_token` OR Basic Auth `username` + `password` (stored redacted `***REDACTED***` in list responses; secret modification requires `integrations.manage_secrets`).
- **Required Capacity Metric Queries** (customizable for any exporter):
  - `size_query` (default: `node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}`)
  - `avail_query` (default: `node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}`)
- **Optional Performance Metric Mapping Queries**:
  - `read_iops_query`, `write_iops_query`, `read_latency_query`, `write_latency_query`, `throughput_query`
  - `metric_label_key` (default: `mountpoint`; falls back to `device` or `instance`)
- **Staleness Guard**: `stale_threshold_seconds` (default `300.0`). Samples older than threshold emit explicit `stale_warnings`.

## Unconfigured & Error Handling
- If an optional performance PromQL query is empty or returns no matching series, `read_iops` / `write_iops` / latency remain `null` (rendered as `METRIC UNAVAILABLE` in Performance Analytics — never fabricated as zero).
- If the Prometheus endpoint is unreachable or returns authentication errors, `/connectors/{id}/test` and `/collect` record `CONNECTION_FAILED` alongside the safe error diagnostic and remediation guidance.
