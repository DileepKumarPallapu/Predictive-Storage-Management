import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.entities import Device, Telemetry, ModelTrustEvaluation
from app.services.sentinel_service import SentinelEngine

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_fresh_demo_data():
    from app.main import initialize_database_and_seed_demo
    initialize_database_and_seed_demo()


# ==============================================================================
# SENTINEL DRIFT & PREDICTION TRUST ENGINE TESTS
# ==============================================================================

def test_sentinel_psi_computation():
    """Validates Population Stability Index calculation across identical, moderate, and extreme shifts."""
    # 1. Identical distributions -> PSI ~ 0.0
    ref = [10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0, 35.0] * 10
    curr_identical = list(ref)
    psi_identical = SentinelEngine.compute_psi(ref, curr_identical)
    assert psi_identical < 0.05

    # 2. Moderate shift
    curr_mod = [x * 1.25 for x in ref]
    psi_mod = SentinelEngine.compute_psi(ref, curr_mod)
    assert psi_mod > psi_identical

    # 3. Extreme distribution shift
    curr_extreme = [x * 3.5 for x in ref]
    psi_extreme = SentinelEngine.compute_psi(ref, curr_extreme)
    assert psi_extreme >= 0.25


def test_sentinel_ks_2samp_test():
    """Validates Two-Sample Kolmogorov-Smirnov test statistics and p-values."""
    # Identical samples
    ref = [float(x) for x in range(100)]
    curr = [float(x) for x in range(100)]
    d, p = SentinelEngine.compute_ks_2samp(ref, curr)
    assert d == 0.0
    assert p >= 0.95

    # Distinct shifted distribution
    shifted = [float(x + 50) for x in range(100)]
    d_shift, p_shift = SentinelEngine.compute_ks_2samp(ref, shifted)
    assert d_shift > 0.40
    assert p_shift < 0.01


def test_sentinel_insufficient_samples_handling():
    """Validates that Sentinel handles insufficient samples without crashing or making false assumptions."""
    db = SessionLocal()
    try:
        # Create a temporary dummy device with only 5 telemetry points
        dummy_dev = Device(
            id="vol-test-insufficient",
            name="Test Volume Insufficient Samples",
            tier="HOST_LOCAL",
            media_type="NVMe SSD",
            total_capacity_bytes=1000 * (1024**3),
            warning_threshold_pct=80.0,
            critical_threshold_pct=90.0,
            max_acceptable_latency_ms=15.0,
            min_free_reserve_pct=10.0,
            status="ONLINE",
            workload_profile="TEST"
        )
        db.add(dummy_dev)
        db.commit()

        # Add 5 points
        now = datetime.now(timezone.utc)
        for i in range(5):
            t = Telemetry(
                device_id="vol-test-insufficient",
                timestamp=now - timedelta(hours=5 - i),
                used_bytes=500 * (1024**3),
                free_bytes=500 * (1024**3),
                utilization_pct=50.0,
                read_iops=100.0,
                write_iops=200.0,
                throughput_mb_s=50.0,
                latency_p95_ms=1.2,
                queue_depth=1.0,
                is_synthetic=True,
                source_label="test"
            )
            db.add(t)
        db.commit()

        # Assess trust
        res = SentinelEngine.assess_prediction_trust(db, "vol-test-insufficient")
        assert res["trust_status"] == "INSUFFICIENT_EVIDENCE"
        assert "Minimum 24 required" in res["status_reason"]
        assert res["recommended_action"] == "CONTINUE_DATA_COLLECTION"

    finally:
        # Cleanup dummy device
        db.query(Telemetry).filter(Telemetry.device_id == "vol-test-insufficient").delete()
        db.query(Device).filter(Device.id == "vol-test-insufficient").delete()
        db.commit()
        db.close()


def test_sentinel_missing_observations_and_staleness_detection():
    """Validates telemetry gap detection and staleness scoring."""
    db = SessionLocal()
    try:
        res = SentinelEngine.assess_prediction_trust(db, "vol-nvme-tier1-db")
        assert "data_quality" in res
        dq = res["data_quality"]
        assert dq["total_telemetry_samples"] >= 24
        assert "is_stale" in dq
        assert "missing_intervals_detected" in dq
    finally:
        db.close()


def test_sentinel_primary_volume_assessment():
    """Validates full drift-aware trust assessment for primary tier-1 volume."""
    resp = client.get("/api/v1/sentinel/trust?device_id=vol-nvme-tier1-db")
    assert resp.status_code == 200
    data = resp.json()

    assert data["device_id"] == "vol-nvme-tier1-db"
    assert data["trust_status"] in ("HEALTHY", "WATCH", "DEGRADED")
    assert len(data["status_reason"]) > 0
    assert "workload_data_drift" in data
    assert "prediction_drift" in data
    assert "performance_reliability" in data
    assert data["performance_reliability"]["empirical_coverage_pct"] >= 70.0
    assert len(data["performance_reliability"]["forecast_vs_actual_samples"]) > 0

    # Ensure all monitored metrics are accounted for
    breakdown = data["workload_data_drift"]["metrics_breakdown"]
    for m in [
        "capacity_growth_rate_gb_day", "utilization_pct",
        "write_iops", "read_iops", "throughput_mb_s", "latency_p95_ms"
    ]:
        assert m in breakdown
        assert "psi" in breakdown[m]
        assert "ks_p_value" in breakdown[m]
        assert "severity" in breakdown[m]


def test_sentinel_trust_history_persistence():
    """Validates that Sentinel assessments are persisted in DB and returned by history endpoint."""
    resp = client.get("/api/v1/sentinel/trust/history?device_id=vol-nvme-tier1-db&limit=10")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 1
    first = history[0]
    assert "trust_status" in first
    assert "max_metric_psi" in first
    assert "empirical_coverage_pct" in first


def test_sentinel_safe_model_recalibration():
    """Validates safe inflation of conformal bounds without modifying model weights."""
    resp = client.post(
        "/api/v1/sentinel/model/recalibrate",
        json={"device_id": "vol-nvme-tier1-db", "adjustment_factor_gamma": 1.15}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "RECALIBRATED_SUCCESS"
    assert data["conformal_adjustment_factor_gamma"] == 1.15
    assert data["governance"]["model_weights_modified"] is False
    assert data["governance"]["production_replacement_executed"] is False


def test_sentinel_chronological_holdout_retrain_evaluation():
    """Validates that candidate model evaluation enforces human approval and blocks automatic replacement."""
    resp = client.post(
        "/api/v1/sentinel/model/retrain-evaluation",
        json={"device_id": "vol-nvme-tier1-db", "candidate_model_type": "lightgbm_quantile_retrained"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["governance_decision"]["automatic_promotion"] == "BLOCKED_BY_POLICY"
    assert "LEAD_STORAGE_ADMINISTRATOR" in data["governance_decision"]["required_approver"]
    assert data["production_model"]["active_in_production"] is True
    assert data["candidate_evaluation"]["mae_improvement_pct"] > 0.0


def test_models_reliability_enriched_endpoint():
    """Validates that GET /api/v1/models/reliability incorporates live Sentinel trust status."""
    resp = client.get("/api/v1/models/reliability")
    assert resp.status_code == 200
    data = resp.json()
    assert "trust_status" in data
    assert data["trust_status"] in ("HEALTHY", "WATCH", "DEGRADED", "INSUFFICIENT_EVIDENCE")
    assert "status_reason" in data
    assert "max_metric_psi" in data
