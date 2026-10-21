import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import numpy as np
from fastapi.testclient import TestClient
from app.main import app

def run_performance_benchmarks(iterations: int = 50):
    client = TestClient(app)
    endpoints = [
        ("GET /api/v1/health", lambda: client.get("/api/v1/health")),
        ("GET /api/v1/overview", lambda: client.get("/api/v1/overview")),
        ("GET /api/v1/devices", lambda: client.get("/api/v1/devices")),
        ("GET /devices/{id}/reserve-runway", lambda: client.get("/api/v1/devices/vol-nvme-tier1-db/reserve-runway")),
        ("GET /devices/{id}/risk-assessment", lambda: client.get("/api/v1/devices/vol-nvme-tier1-db/risk-assessment")),
        ("POST /planning/evaluate", lambda: client.post("/api/v1/planning/evaluate", json={"device_id": "vol-nvme-tier1-db"})),
        ("POST /scenarios (Simulation)", lambda: client.post("/api/v1/scenarios", json={
            "device_id": "vol-nvme-tier1-db",
            "name": "Benchmark Scenario",
            "action_type": "TIER_COLD_DATA",
            "parameters": {"data_volume_gb": 1000.0, "migration_rate_mb_s": 150.0}
        })),
        ("GET /api/v1/metrics (Prometheus)", lambda: client.get("/api/v1/metrics")),
    ]

    print("================================================================================")
    print("AEGISSTOR TITAN — REAL MEASURED API & SIMULATOR BENCHMARK REPORT")
    print(f"Sample Size per Endpoint: {iterations} sequential requests | Host: Windows Python 3.13")
    print("================================================================================")
    print(f"{'Endpoint':<36} | {'Median':<8} | {'P95':<8} | {'P99':<8} | {'RPS':<8}")
    print("--------------------------------------------------------------------------------")

    results = {}
    for name, call_fn in endpoints:
        latencies = []
        # Warmup
        call_fn()
        
        t_start = time.perf_counter()
        for _ in range(iterations):
            t0 = time.perf_counter()
            resp = call_fn()
            t1 = time.perf_counter()
            assert resp.status_code == 200, f"{name} failed with status {resp.status_code}"
            latencies.append((t1 - t0) * 1000.0)
        t_total = time.perf_counter() - t_start

        med = np.median(latencies)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        rps = iterations / t_total

        results[name] = {"median": med, "p95": p95, "p99": p99, "rps": rps}
        print(f"{name:<36} | {med:6.2f}ms | {p95:6.2f}ms | {p99:6.2f}ms | {rps:6.1f}")

    print("================================================================================")
    return results

if __name__ == "__main__":
    run_performance_benchmarks(iterations=30)
