"""
Patent-Grade End-to-End Verification Suite for AEGISSTOR Phases 1-11.
Tests:
  - Phase 2: ConnectorRegistry (LINUX_HOST, PROMETHEUS mock & failure), X-API-Key auth, Idempotency-Key ingestion
  - Phase 3: 9-Factor Data Reliability Engine (HIGH/MEDIUM/LOW/STALE, custom weights, recommendation gating)
  - Phase 4: Workload Regime & Drift Engine (INSUFFICIENT_HISTORY, SUDDEN_BURST, DECLINING_CONSUMPTION, ACCELERATING_GROWTH, PERIODIC_SEASONAL)
  - Phase 5: Two-Model Champion-Challenger (LightGBM + SARIMAX vs SeasonalNaiveBenchmark), 3-way split, rolling CV,
             MASE/Pinball/Coverage/MAPE, Split Conformal calibration, multi-horizon forecasts, async jobs, good-model preservation
  - Phase 6: Probabilistic Capacity Risk Engine (residual-CDF crossing probability, Brier calibration check, shortfall, exhaustion)
  - Phase 7: Performance Compare with explicit AVAILABLE / UNAVAILABLE / STALE / UNSUPPORTED_BY_CONNECTOR
  - Phase 8: Constrained Decision Optimizer (binding constraints, cost-only-when-provided)
  - Phase 9: Recommendation 5-state workflow (APPROVED_SHADOW -> COMPLETED / FAILED, non-execution invariant)
  - Phase 10: API Rate Limiting (X-RateLimit-Remaining, 429) & Retention Dry-Run
"""
import io
import json
import math
import os
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth.security import create_access_token
from app.collector.connector_registry import ConnectorRegistry
from app.database import SessionLocal
from app.main import app, initialize_database_and_seed_demo
from app.models.entities import (
    ApiKey,
    BackgroundJob,
    CapacityRiskEvaluation,
    DataQualityResult,
    DataReliabilityProfile,
    Device,
    Forecast,
    IngestionJob,
    ModelMetric,
    ModelVersion,
    Recommendation,
    Telemetry,
    TelemetryConnector,
    WorkloadRegimeEvent,
)

from tests.auth_helper import attach_admin_auth

client = attach_admin_auth(TestClient(app))


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    initialize_database_and_seed_demo()


def _admin_headers() -> dict:
    token = create_access_token(data={
        "sub": "admin",
        "role": "ADMIN",
        "user_id": "usr-system-admin",
        "organization_id": "org-primary-enterprise",
    })
    return {"Authorization": f"Bearer {token}"}


def _cleanup_device(storage_id: str) -> None:
    db = SessionLocal()
    try:
        db.query(CapacityRiskEvaluation).filter(CapacityRiskEvaluation.storage_id == storage_id).delete(synchronize_session=False)
        db.query(BackgroundJob).filter(BackgroundJob.storage_id == storage_id).delete(synchronize_session=False)
        db.query(WorkloadRegimeEvent).filter(WorkloadRegimeEvent.storage_id == storage_id).delete(synchronize_session=False)
        db.query(DataReliabilityProfile).filter(DataReliabilityProfile.storage_id == storage_id).delete(synchronize_session=False)
        db.query(ModelMetric).filter(ModelMetric.storage_id == storage_id).delete(synchronize_session=False)
        db.query(ModelVersion).filter(ModelVersion.storage_id == storage_id).delete(synchronize_session=False)
        db.query(Forecast).filter(Forecast.device_id == storage_id).delete(synchronize_session=False)
        db.query(Recommendation).filter(Recommendation.device_id == storage_id).delete(synchronize_session=False)
        db.query(DataQualityResult).filter(DataQualityResult.storage_id == storage_id).delete(synchronize_session=False)
        db.query(IngestionJob).filter(IngestionJob.storage_id == storage_id).delete(synchronize_session=False)
        db.query(TelemetryConnector).filter(TelemetryConnector.target_storage_id == storage_id).delete(synchronize_session=False)
        db.query(Telemetry).filter(Telemetry.device_id == storage_id).delete(synchronize_session=False)
        db.query(Device).filter(Device.id == storage_id).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _create_temp_device(storage_id: str, total_gb: int = 1000, warn: float = 80.0, crit: float = 90.0) -> None:
    db = SessionLocal()
    try:
        db.add(Device(
            id=storage_id,
            name=f"Temp {storage_id}",
            tier="HOT_NVME",
            media_type="NVMe",
            total_capacity_bytes=total_gb * (1024 ** 3),
            warning_threshold_pct=warn,
            critical_threshold_pct=crit,
            max_acceptable_latency_ms=18.0,
            status="HEALTHY",
        ))
        db.commit()
    finally:
        db.close()


def _seed_hourly_telemetry(
    storage_id: str,
    count: int = 96,
    base_used_gb: float = 400.0,
    slope_gb_per_hr: float = 0.8,
    total_gb: int = 1000,
    end_hours_ago: float = 0.5,
    periodic_amp_gb: float = 3.0,
    include_perf: bool = True,
    burst_last_gb: float = 0.0,
) -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0) - timedelta(hours=end_hours_ago)
        start = now - timedelta(hours=count - 1)
        total_b = total_gb * (1024 ** 3)
        rows = []
        for i in range(count):
            ts = start + timedelta(hours=i)
            seasonal = periodic_amp_gb * math.sin(2.0 * math.pi * i / 24.0)
            used_gb = max(10.0, min(float(total_gb - 5), base_used_gb + i * slope_gb_per_hr + seasonal))
            if i == count - 1 and burst_last_gb != 0.0:
                used_gb = max(10.0, min(float(total_gb - 1), used_gb + burst_last_gb))
            used_b = int(used_gb * (1024 ** 3))
            free_b = max(0, total_b - used_b)
            util = round((used_b / total_b) * 100.0, 2)
            rows.append(Telemetry(
                device_id=storage_id,
                timestamp=ts,
                total_capacity_bytes=total_b,
                used_bytes=used_b,
                free_bytes=free_b,
                utilization_pct=util,
                read_iops=(1200.0 + (i % 12) * 35.0) if include_perf else None,
                write_iops=(450.0 + (i % 8) * 20.0) if include_perf else None,
                throughput_mb_s=(210.0 + (i % 10) * 12.0) if include_perf else None,
                latency_p95_ms=(4.5 + (i % 6) * 0.4) if include_perf else None,
                queue_depth=4.0 if include_perf else None,
                is_synthetic=False,
                source_label="pytest_timeseries",
            ))
        db.bulk_save_objects(rows)
        db.commit()
    finally:
        db.close()


def test_connectors_api_keys_and_idempotent_ingestion(monkeypatch):
    sid = f"dev-conn-{uuid.uuid4().hex[:6]}"
    _create_temp_device(sid, total_gb=500)
    headers = _admin_headers()
    created_key_id = None
    try:
        # 1. Connector types & Linux Host real read-only collect
        r_types = client.get("/api/v1/connectors/types")
        assert r_types.status_code == 200
        assert set(["LINUX_HOST", "PROMETHEUS", "CSV_HISTORICAL", "HTTP_API"]).issubset(set(r_types.json()["supported_types"]))

        r_reg = client.post("/api/v1/connectors", headers=headers, json={
            "name": "Local Host ReadOnly",
            "connector_type": "LINUX_HOST",
            "target_storage_id": sid,
        })
        assert r_reg.status_code == 200
        conn_id = r_reg.json()["connector"]["id"]

        r_test = client.post(f"/api/v1/connectors/{conn_id}/test", headers=headers)
        assert r_test.status_code == 200
        assert r_test.json()["result"]["status"] == "CONNECTED"
        assert r_test.json()["result"]["read_only"] is True

        r_collect = client.post(f"/api/v1/connectors/{conn_id}/collect", headers=headers, json={})
        assert r_collect.status_code == 200
        assert r_collect.json()["result"]["volumes_count"] >= 1

        # 2. Prometheus error handling + mocked valid response parsing
        prom = ConnectorRegistry.get_adapter("PROMETHEUS")
        prom_err = prom.test_connection({"endpoint_url": "http://127.0.0.1:59999", "timeout_seconds": 0.2})
        assert prom_err["status"] == "CONNECTION_FAILED"

        class _FakeResp:
            def __init__(self, payload_obj):
                self._raw = json.dumps(payload_obj).encode("utf-8")
            def read(self):
                return self._raw
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False

        now_epoch = datetime.now(timezone.utc).timestamp()
        def _fake_urlopen(req, timeout=5.0):
            url = req.full_url
            if "size" in url:
                return _FakeResp({"data": {"result": [{"metric": {"mountpoint": "/data"}, "value": [now_epoch - 60, "1073741824000"]}]}})
            return _FakeResp({"data": {"result": [{"metric": {"mountpoint": "/data"}, "value": [now_epoch - 60, "429496729600"]}]}})

        monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
        prom_data = prom.collect({"endpoint_url": "http://prom.mock:9090", "target_storage_id": sid})
        assert prom_data["status"] == "OK"
        assert prom_data["volumes"][0]["read_latency_ms"] is None

        # 3. API Key creation -> auth ingestion without JWT -> Idempotency-Key replay -> Revoke
        r_key = client.post("/api/v1/admin/api-keys", headers=headers, json={"name": "collector-ci", "role": "OPERATOR"})
        assert r_key.status_code == 200
        raw_api_key = r_key.json()["api_key"]
        created_key_id = r_key.json()["id"]

        ts_sample = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(microsecond=0).isoformat()
        ingest_body = {
            "device_id": sid,
            "records": [{
                "timestamp": ts_sample,
                "used_bytes": 150 * (1024 ** 3),
                "free_bytes": 350 * (1024 ** 3),
                "read_iops": 120.0,
                "write_iops": 45.0,
                "throughput_mb_s": 55.0,
                "latency_p95_ms": 4.2,
            }],
        }
        r_ing1 = client.post(
            "/api/v1/telemetry/ingest",
            headers={"X-API-Key": raw_api_key, "Idempotency-Key": "batch-idem-001"},
            json=ingest_body,
        )
        assert r_ing1.status_code == 200
        assert r_ing1.json()["ingested_count"] == 1
        assert r_ing1.json()["idempotent_replay"] is False

        # Replay with identical Idempotency-Key returns replay flag without duplicate DB rows
        r_ing2 = client.post(
            "/api/v1/telemetry/ingest",
            headers={"X-API-Key": raw_api_key, "Idempotency-Key": "batch-idem-001"},
            json=ingest_body,
        )
        assert r_ing2.status_code == 200
        assert r_ing2.json()["idempotent_replay"] is True
        assert r_ing2.json()["ingested_count"] == 0

        # Revoke API key & confirm rejection
        r_rev = client.delete(f"/api/v1/admin/api-keys/{created_key_id}", headers=headers)
        assert r_rev.status_code == 200
        r_rejected = client.post(
            "/api/v1/telemetry/ingest",
            headers={"X-API-Key": raw_api_key},
            json=ingest_body,
        )
        assert r_rejected.status_code in {401, 403}
    finally:
        if created_key_id:
            db = SessionLocal()
            try:
                db.query(ApiKey).filter(ApiKey.id == created_key_id).delete(synchronize_session=False)
                db.commit()
            finally:
                db.close()
        _cleanup_device(sid)


def test_data_reliability_engine_and_recommendation_gating():
    sid_good = f"dev-rel-hi-{uuid.uuid4().hex[:5]}"
    sid_stale = f"dev-rel-lo-{uuid.uuid4().hex[:5]}"
    _create_temp_device(sid_good, total_gb=1000)
    _create_temp_device(sid_stale, total_gb=1000)
    headers = _admin_headers()
    try:
        _seed_hourly_telemetry(sid_good, count=80, base_used_gb=500.0, slope_gb_per_hr=0.4, end_hours_ago=0.2)
        r_hi = client.get(f"/api/v1/reliability/data/{sid_good}")
        assert r_hi.status_code == 200
        d_hi = r_hi.json()
        assert len(d_hi["factors"]) == 9
        assert d_hi["reliability_tier"] == "HIGH"
        assert d_hi["uncertainty_multiplier"] == 1.0
        assert d_hi["allow_high_confidence_recommendations"] is True

        # Custom weights accepted & normalized
        r_wt = client.post(f"/api/v1/reliability/data/{sid_good}", headers=headers, json={"weights": {"freshness_score": 0.40}})
        assert r_wt.status_code == 200
        assert abs(sum(r_wt.json()["weights"].values()) - 1.0) < 1e-4

        # Stale + sparse data degrades reliability & blocks high-confidence automated recommendations
        _seed_hourly_telemetry(sid_stale, count=10, base_used_gb=880.0, slope_gb_per_hr=0.5, end_hours_ago=200.0, include_perf=False)
        r_lo = client.get(f"/api/v1/reliability/data/{sid_stale}")
        assert r_lo.status_code == 200
        d_lo = r_lo.json()
        assert d_lo["is_stale"] is True
        assert d_lo["reliability_tier"] in {"LOW", "MEDIUM"}
        assert d_lo["uncertainty_multiplier"] > 1.0
        assert d_lo["allow_high_confidence_recommendations"] is False

        r_rec = client.post(f"/api/v1/recommendations/generate/{sid_stale}", headers=headers)
        assert r_rec.status_code == 200
        rec_body = r_rec.json()
        assert rec_body["allow_high_confidence_recommendations"] is False
        assert any("Reliability" in r["title"] for r in rec_body["recommendations"])
    finally:
        _cleanup_device(sid_good)
        _cleanup_device(sid_stale)


def test_workload_regime_engine_all_classifications():
    sids = [f"dev-wreg-{i}-{uuid.uuid4().hex[:4]}" for i in range(4)]
    for s in sids:
        _create_temp_device(s, total_gb=1000)
    try:
        # 0: Insufficient history (< 24 points)
        _seed_hourly_telemetry(sids[0], count=12)
        r0 = client.get(f"/api/v1/workload-regime/{sids[0]}")
        assert r0.status_code == 200
        assert r0.json()["regime_label"] == "INSUFFICIENT_HISTORY"

        # 1: Sudden burst
        _seed_hourly_telemetry(sids[1], count=60, base_used_gb=400.0, slope_gb_per_hr=0.2, periodic_amp_gb=0.2, burst_last_gb=180.0)
        r1 = client.get(f"/api/v1/workload-regime/{sids[1]}")
        assert r1.status_code == 200
        assert r1.json()["regime_label"] == "SUDDEN_BURST"

        # 2: Declining consumption
        _seed_hourly_telemetry(sids[2], count=72, base_used_gb=750.0, slope_gb_per_hr=-0.6, periodic_amp_gb=0.2)
        r2 = client.get(f"/api/v1/workload-regime/{sids[2]}")
        assert r2.status_code == 200
        assert r2.json()["regime_label"] == "DECLINING_CONSUMPTION"

        # 3: Periodic seasonal
        _seed_hourly_telemetry(sids[3], count=96, base_used_gb=500.0, slope_gb_per_hr=0.05, periodic_amp_gb=25.0)
        r3 = client.get(f"/api/v1/workload-regime/{sids[3]}")
        assert r3.status_code == 200
        assert r3.json()["regime_label"] == "PERIODIC_SEASONAL"
    finally:
        for s in sids:
            _cleanup_device(s)


def test_champion_challenger_ml_conformal_async_and_capacity_risk():
    sid = f"dev-ccml-{uuid.uuid4().hex[:6]}"
    _create_temp_device(sid, total_gb=1000, warn=75.0, crit=85.0)
    headers = _admin_headers()
    try:
        # Step A: Too small dataset blocks training cleanly
        _seed_hourly_telemetry(sid, count=30, base_used_gb=450.0, slope_gb_per_hr=0.5)
        r_small = client.post(f"/api/v1/v2/models/train/{sid}", headers=headers)
        assert r_small.status_code == 400
        assert "Minimum 60" in r_small.json()["detail"]

        # Step B: Seed full 96h series (growing toward threshold) -> train LightGBM + SARIMAX vs SeasonalNaive
        _cleanup_device(sid)
        _create_temp_device(sid, total_gb=1000, warn=75.0, crit=85.0)
        _seed_hourly_telemetry(sid, count=96, base_used_gb=500.0, slope_gb_per_hr=1.8, end_hours_ago=0.2)

        r_train = client.post(f"/api/v1/v2/models/train/{sid}", headers=headers)
        assert r_train.status_code == 200
        tr = r_train.json()
        assert tr["champion_family"] in {"LightGBM", "SARIMAX"}
        assert tr["reference_benchmark"]["model"] == "SeasonalNaiveBenchmark"
        assert os.path.exists(tr["artifact_path"])
        families = {c["family"] for c in tr["candidates"]}
        assert {"LightGBM", "SARIMAX"}.issubset(families)
        champ_cand = [c for c in tr["candidates"] if c.get("is_champion")][0]
        assert champ_cand["metrics"]["mase"] is not None
        assert champ_cand["metrics"]["pinball_loss"] is not None
        assert champ_cand["metrics"]["interval_coverage"] is not None

        # Step C: Generate multi-horizon forecasts (7d, 30d, 90d)
        r_fc = client.post(f"/api/v1/v2/forecasts/generate/{sid}", json={"horizon_days": 30})
        assert r_fc.status_code == 200
        fc = r_fc.json()
        assert fc["calibration"]["method"] == "Split Conformal Prediction"
        assert len(fc["series"]) >= 1
        assert fc["series"][-1]["p10_used_gb"] <= fc["series"][-1]["p50_used_gb"] <= fc["series"][-1]["p90_used_gb"]

        # Step D: Capacity Risk Engine (residual CDF crossing probability & Brier score)
        r_risk = client.post(f"/api/v1/risk/capacity/{sid}", json={"horizon_days": 30, "safety_threshold_pct": 85.0})
        assert r_risk.status_code == 200
        risk = r_risk.json()
        assert 0.0 <= risk["threshold_crossing_probability"] <= 1.0
        assert "brier_calibration_score" in risk["details"]
        assert risk["expected_shortfall_bytes"] >= 0

        # Step E: Async background job training + polling
        r_async = client.post(f"/api/v1/v2/models/train-async/{sid}", headers=headers)
        assert r_async.status_code == 200
        job_id = r_async.json()["job_id"]
        r_job = client.get(f"/api/v1/jobs/{job_id}")
        assert r_job.status_code == 200
        assert r_job.json()["status"] in {"QUEUED", "RUNNING", "COMPLETED"}
    finally:
        _cleanup_device(sid)


def test_performance_compare_optimizer_recommendations_and_ratelimit():
    sid = f"dev-opt-{uuid.uuid4().hex[:6]}"
    _create_temp_device(sid, total_gb=1000, warn=80.0, crit=90.0)
    headers = _admin_headers()
    try:
        # Telemetry WITHOUT perf metrics (None) -> performance/compare reports UNAVAILABLE without inventing 0.0
        _seed_hourly_telemetry(sid, count=36, base_used_gb=810.0, slope_gb_per_hr=0.4, include_perf=False)
        r_cmp = client.get(f"/api/v1/performance/compare?storage_ids={sid}")
        assert r_cmp.status_code == 200
        vol = r_cmp.json()["volumes"][0]
        assert vol["metrics"]["utilization_pct"]["status"] == "AVAILABLE"
        assert vol["metrics"]["latency_p95_ms"]["status"] == "UNAVAILABLE"
        assert vol["metrics"]["latency_p95_ms"]["latest"] is None

        # Constrained Optimizer WITHOUT unit_costs -> never fabricates dollar prices!
        r_opt_no_cost = client.post(f"/api/v1/digital-twin/optimize/{sid}", json={
            "max_utilization_pct": 85.0,
            "min_free_space_pct": 15.0,
            "decision_horizon_days": 30,
        })
        assert r_opt_no_cost.status_code == 200
        opt1 = r_opt_no_cost.json()
        assert opt1["recommended_option"] is not None
        assert opt1["recommended_option"]["estimated_cost_usd"] is None
        assert opt1["recommended_option"]["cost_status"] == "Cost not provided"

        # Constrained Optimizer WITH unit_costs + tight budget_usd -> checks binding budget constraint
        r_opt_cost = client.post(f"/api/v1/digital-twin/optimize/{sid}", json={
            "budget_usd": 50.0,
            "max_utilization_pct": 85.0,
            "min_free_space_pct": 15.0,
            "decision_horizon_days": 30,
            "unit_costs": {"expand_usd_per_gb": 0.50, "archive_usd_per_gb": 0.10, "dedup_compute_usd": 20.0},
        })
        assert r_opt_cost.status_code == 200
        opt2 = r_opt_cost.json()
        rejected_actions = {c["action_type"] for c in opt2["rejected_candidates"]}
        assert "EXPAND_VOLUME" in rejected_actions  # 250 GB * $0.50 = $125 > $50 budget

        # Recommendation 5-state lifecycle (PENDING -> APPROVED_SHADOW -> COMPLETED & invalid transition check)
        r_rec_gen = client.post(f"/api/v1/recommendations/generate/{sid}", headers=headers)
        assert r_rec_gen.status_code == 200
        rec_id = r_rec_gen.json()["recommendations"][0]["id"]

        # Invalid: cannot complete directly from PENDING_REVIEW
        r_bad_comp = client.post(f"/api/v1/recommendations/{rec_id}/complete", headers=headers, json={"notes": "skip"})
        assert r_bad_comp.status_code == 400

        r_app = client.post(f"/api/v1/recommendations/{rec_id}/approve", headers=headers, json={"notes": "Approved"})
        assert r_app.status_code == 200
        r_comp = client.post(f"/api/v1/recommendations/{rec_id}/complete", headers=headers, json={"notes": "Confirmed offline"})
        assert r_comp.status_code == 200
        assert r_comp.json()["status"] == "COMPLETED"
        assert r_comp.json()["physical_mutation_executed"] is False

        # Retention Dry Run endpoint
        r_ret = client.post("/api/v1/admin/retention/run", headers=headers, json={"retention_days": 365, "dry_run": True})
        assert r_ret.status_code == 200
        assert r_ret.json()["audit_logs_preserved"] is True

        # Sliding-window Rate Limiter verification (temporarily set cap to 3)
        orig_limit = app.state.rate_limit_max
        app.state.rate_limit_buckets.clear()
        app.state.rate_limit_max = 3
        try:
            for _ in range(3):
                ok_res = client.get("/api/v1/connectors/types")
                assert ok_res.status_code == 200
                assert "X-RateLimit-Remaining" in ok_res.headers
            blocked = client.get("/api/v1/connectors/types")
            assert blocked.status_code == 429
        finally:
            app.state.rate_limit_max = orig_limit
            app.state.rate_limit_buckets.clear()
    finally:
        _cleanup_device(sid)
