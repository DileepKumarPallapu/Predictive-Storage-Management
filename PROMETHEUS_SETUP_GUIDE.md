# AEGISSTOR — Prometheus Setup Guide (Phase 8)

## 1. Configuration
Set in environment (or via Integration Management UI):
- `PROMETHEUS_URL`: e.g. `https://prom.internal:9090/metrics` or `http://127.0.0.1:9100/metrics`
- `PROMETHEUS_BEARER_TOKEN`: optional Bearer token for authenticated Prometheus endpoints
- `PROMETHEUS_TLS_VERIFY`: `true` (default) or `false` for self-signed internal endpoints
- `PROMETHEUS_TIMEOUT_SEC`: `5.0` (default)

## 2. Security & Connectivity
- Never expose private Prometheus servers directly to the public internet; route through a private VPC, WireGuard/Tailscale tunnel, or outbound collector.
- When `PROMETHEUS_URL` is unconfigured, `HostStorageCollector.scrape_prometheus_node_exporter()` returns `status: "NOT_CONFIGURED"` (verified in `test_prometheus_unconfigured_returns_not_configured`) instead of hardcoded assumptions or fake metrics.
