# AEGISSTOR — Performance & Load Test Report (Phase 12)

**Test Date:** 2026-11-12
**Environment:** Local uvicorn backend (`127.0.0.1:8000`) + standalone `worker.py` + SQLite (`aegisstor.db`)
**Script:** `run_load_benchmark.py` (12 concurrent workers across simultaneous Admin & Operator sessions)

---

## Measured Results

| Metric | Measured Value | Target | Status |
| :--- | :--- | :--- | :--- |
| **Total Concurrent Requests** | `80` (Admin + Operator) | — | Executed |
| **Concurrency Level** | `12` simultaneous threads | — | Executed |
| **Total Wall Time** | `5,242.08 ms` | — | Executed |
| **Error Rate** | `0.0%` (`0 / 80` failed) | `< 1%` | **PASS** |
| **API Latency p50** | `510.69 ms` | — | **PASS** |
| **API Latency p95** | `1,906.77 ms` | `< 3,000 ms` | **PASS** |
| **API Latency p99** | `2,939.29 ms` | — | **PASS** |
| **API Max Latency** | `2,971.17 ms` | — | Measured |
| **Database Health Probe Latency** | `1.25 ms` | `< 50 ms` | **PASS** |
| **PDF Report Generation (`storage_inventory`)** | `180.02 ms` (`HTTP 200`) | `< 2,000 ms` | **PASS** |

*Note: Multi-instance Render + Managed PostgreSQL + Redis load testing is pending cloud credentials.*
