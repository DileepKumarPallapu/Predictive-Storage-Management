import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.collector.host_collector import (
    HostStorageCollector,
    PROVENANCE_LIVE,
    PROVENANCE_SYNTHETIC,
    PROVENANCE_IMPORTED,
    PROVENANCE_SIMULATED
)
from app.database import SessionLocal
from app.models.entities import Device, Recommendation, Telemetry
from app.services.research_benchmark_engine import ResearchBenchmarkEngine

client = TestClient(app)


# ==============================================================================
# UPGRADE 1: REAL-WORLD TELEMETRY INTEGRATION TESTS
# ==============================================================================

def test_telemetry_sources_permission_boundary():
    """Validates that all registered telemetry sources enforce read-only permission boundaries."""
    sources = HostStorageCollector.get_configured_sources()
    assert len(sources) >= 2
    for s in sources:
        assert s["read_only"] is True
        assert s["permission_enforced"] is True
        assert s["physical_mutation_permitted"] is False
        assert "STORAGE_READ_ONLY" in s["permission_boundary"]

    # Test via API
    resp = client.get("/api/v1/telemetry/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["permission_mode"] == "READ_ONLY"
    assert data["physical_mutation_disabled"] is True
    assert len(data["sources"]) >= 2


def test_live_host_storage_discovery():
    """Validates non-destructive host partition discovery with provenance='LIVE'."""
    partitions = HostStorageCollector.get_available_partitions()
    assert len(partitions) >= 1
    for p in partitions:
        assert p["provenance"] == PROVENANCE_LIVE
        assert p["is_synthetic"] is False
        assert p["read_only"] is True
        assert p["total_capacity_bytes"] > 0
        assert 0 <= p["used_bytes"] <= p["total_capacity_bytes"]
        assert 0.0 <= p["utilization_pct"] <= 100.0
        assert p["validation"]["is_valid"] is True

    # Test via API
    resp = client.get("/api/v1/telemetry/live-host")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provenance"] == PROVENANCE_LIVE
    assert data["is_synthetic"] is False
    assert data["partitions_count"] >= 1


def test_prometheus_node_exporter_parser():
    """Validates accurate parsing of Prometheus Node Exporter text metric format."""
    sample_prometheus_text = """
# HELP node_filesystem_size_bytes Filesystem size in bytes.
# TYPE node_filesystem_size_bytes gauge
node_filesystem_size_bytes{device="/dev/nvme0n1p2",fstype="ext4",mountpoint="/"} 1000000000000
node_filesystem_size_bytes{device="tmpfs",fstype="tmpfs",mountpoint="/run"} 16000000000
# HELP node_filesystem_free_bytes Filesystem free space in bytes.
# TYPE node_filesystem_free_bytes gauge
node_filesystem_free_bytes{device="/dev/nvme0n1p2",fstype="ext4",mountpoint="/"} 250000000000
node_filesystem_free_bytes{device="tmpfs",fstype="tmpfs",mountpoint="/run"} 15000000000
# HELP node_disk_read_bytes_total The total number of bytes read successfully.
# TYPE node_disk_read_bytes_total counter
node_disk_read_bytes_total{device="nvme0n1"} 543210000
# HELP node_disk_written_bytes_total The total number of bytes written successfully.
# TYPE node_disk_written_bytes_total counter
node_disk_written_bytes_total{device="nvme0n1"} 987650000
"""
    parsed = HostStorageCollector.parse_prometheus_text(sample_prometheus_text)
    assert parsed["status"] == "PARSED_SUCCESS"
    assert parsed["provenance"] == PROVENANCE_LIVE
    assert parsed["total_filesystems_discovered"] == 1  # tmpfs filtered out
    
    fs = parsed["filesystems"][0]
    assert fs["mountpoint"] == "/"
    assert fs["total_capacity_bytes"] == 1000000000000
    assert fs["free_bytes"] == 250000000000
    assert fs["used_bytes"] == 750000000000
    assert fs["utilization_pct"] == 75.0
    assert fs["provenance"] == PROVENANCE_LIVE
    assert fs["is_synthetic"] is False
    assert fs["validation"]["is_valid"] is True

    # Disks
    assert parsed["total_disks_discovered"] == 1
    disk = parsed["disks"][0]
    assert disk["device"] == "nvme0n1"
    assert disk["read_bytes_total"] == 543210000


def test_prometheus_unreachable_endpoint_handling():
    """Validates graceful failure handling when Prometheus Node Exporter is unreachable."""
    resp = client.post(
        "/api/v1/telemetry/prometheus/scrape",
        json={"endpoint_url": "http://127.0.0.1:59999/metrics", "timeout_seconds": 1.0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["collection_failure"] is True
    assert data["provenance"] == PROVENANCE_LIVE
    assert data["status"] in ("ENDPOINT_UNREACHABLE", "COLLECTION_EXCEPTION")
    assert len(data["filesystems"]) == 0


def test_telemetry_validation_invariants():
    """Validates invariant checking, staleness, future timestamp detection, and provenance integrity."""
    now = datetime.now(timezone.utc)

    # 1. Valid live sample
    valid_sample = {
        "provenance": PROVENANCE_LIVE,
        "is_synthetic": False,
        "timestamp": now.isoformat(),
        "total_capacity_bytes": 1000000000,
        "used_bytes": 600000000,
        "free_bytes": 400000000,
        "utilization_pct": 60.0
    }
    v1 = HostStorageCollector.validate_metric_sample(valid_sample)
    assert v1["is_valid"] is True
    assert v1["is_stale"] is False

    # 2. Rule: Synthetic data cannot claim LIVE provenance
    fake_live = {
        "provenance": PROVENANCE_LIVE,
        "is_synthetic": True,
        "timestamp": now.isoformat(),
        "total_capacity_bytes": 1000,
        "used_bytes": 500,
        "free_bytes": 500,
        "utilization_pct": 50.0
    }
    v2 = HostStorageCollector.validate_metric_sample(fake_live)
    assert v2["is_valid"] is False
    assert any("PROVENANCE VIOLATION" in err for err in v2["validation_errors"])

    # 3. Staleness detection (> 24h old)
    old_time = now - timedelta(hours=36)
    stale_sample = dict(valid_sample)
    stale_sample["timestamp"] = old_time.isoformat()
    v3 = HostStorageCollector.validate_metric_sample(stale_sample, max_age_hours=24.0)
    assert v3["is_valid"] is True
    assert v3["is_stale"] is True

    # 4. Out-of-bounds metrics
    invalid_sample = {
        "provenance": PROVENANCE_LIVE,
        "timestamp": now.isoformat(),
        "total_capacity_bytes": -500,
        "used_bytes": 1500,
        "utilization_pct": 140.0,
        "read_iops": -10.0
    }
    v4 = HostStorageCollector.validate_metric_sample(invalid_sample)
    assert v4["is_valid"] is False
    assert len(v4["validation_errors"]) >= 3

    # Test via API
    resp = client.post("/api/v1/telemetry/validate", json={"sample": fake_live})
    assert resp.status_code == 200
    assert resp.json()["is_valid"] is False


# ==============================================================================
# UPGRADE 2: SAFE DECISION AND VERIFICATION LOOP TESTS
# ==============================================================================

def test_recommendation_safety_metadata_enrichment():
    """Validates that recommendations are enriched with evidence, impact, assumptions, risks, and rollback guidance."""
    resp = client.get("/api/v1/devices/vol-nvme-tier1-db/recommendations")
    assert resp.status_code == 200
    recs = resp.json()
    assert len(recs) >= 1

    first = recs[0]
    assert first["evidence_summary"] is not None
    assert "trigger_condition" in first["evidence_summary"]
    assert first["expected_impact"] is not None
    assert "capacity_freed_gb" in first["expected_impact"]
    assert 0.0 <= first["confidence_score"] <= 1.0
    assert len(first["assumptions"]) >= 1
    assert len(first["constraints_checked"]) >= 1
    assert len(first["possible_risks"]) >= 1
    assert first["rollback_guidance"] is not None
    assert "rollback_command" in first["rollback_guidance"]


def test_recommendation_dry_run_preview():
    """Validates dry-run preview simulation within Digital Twin sandbox without physical storage mutations."""
    # Fetch a recommendation
    recs_resp = client.get("/api/v1/devices/vol-nvme-tier1-db/recommendations")
    recs = recs_resp.json()
    assert len(recs) >= 1
    rec_id = recs[0]["id"]

    # Preview dry run
    prev_resp = client.post(f"/api/v1/recommendations/{rec_id}/preview")
    assert prev_resp.status_code == 200
    preview = prev_resp.json()

    assert preview["recommendation_id"] == rec_id
    assert preview["dry_run_success"] is True
    assert preview["pre_capacity_used_gb"] >= preview["post_capacity_used_gb"]
    assert preview["capacity_freed_gb"] > 0
    assert preview["estimated_duration_minutes"] > 0
    assert "rollback_plan" in preview
    assert len(preview["constraints_passed"]) >= 1


def test_recommendation_approval_and_outcome_verification():
    """Validates human approval audit trail and post-action outcome verification comparison."""
    # Fetch a recommendation
    recs_resp = client.get("/api/v1/devices/vol-nvme-tier1-db/recommendations")
    recs = recs_resp.json()
    rec_id = recs[0]["id"]

    # 1. Approve recommendation
    app_resp = client.post(
        f"/api/v1/recommendations/{rec_id}/approve",
        json={"notes": "Approved for shadow verification in digital twin."}
    )
    assert app_resp.status_code == 200
    assert app_resp.json()["status"] == "APPROVED_SHADOW"

    # 2. Outcome verification - Within tolerance (< 10% discrepancy)
    verif_resp = client.post(
        f"/api/v1/recommendations/{rec_id}/verify-outcome",
        json={"notes": "Post-action shadow telemetry evaluated."}
    )
    assert verif_resp.status_code == 200
    v_data = verif_resp.json()
    assert v_data["verification_status"] == "VERIFIED_WITHIN_TOLERANCE"
    assert v_data["discrepancy_pct"] <= 10.0
    assert v_data["rollback_recommended"] is False
    assert "rollback_guidance" in v_data

    # 3. Outcome verification - Large discrepancy (> 10%) triggers rollback
    verif_bad_resp = client.post(
        f"/api/v1/recommendations/{rec_id}/verify-outcome",
        json={"measured_used_bytes": int(v_data["predicted_used_bytes"] * 1.35), "notes": "Simulated breach discrepancy"}
    )
    assert verif_bad_resp.status_code == 200
    bad_data = verif_bad_resp.json()
    assert bad_data["verification_status"] == "DISCREPANCY_FLAGGED"
    assert bad_data["discrepancy_pct"] > 10.0
    assert bad_data["rollback_recommended"] is True

    # 4. Query historical verifications
    history_resp = client.get(f"/api/v1/recommendations/{rec_id}/verifications")
    assert history_resp.status_code == 200
    assert history_resp.json()["verifications_count"] >= 2


# ==============================================================================
# UPGRADE 3: REPRODUCIBLE RESEARCH VALIDATION TESTS
# ==============================================================================

def test_chronological_validation_zero_leakage():
    """Validates zero temporal leakage in 70/15/15 chronological split and baselines evaluation."""
    db = SessionLocal()
    try:
        res = ResearchBenchmarkEngine.run_chronological_validation(
            db=db,
            device_id="vol-nvme-tier1-db",
            horizon_hours=72,
            random_seed=42
        )

        assert res["random_seed"] == 42
        assert res["split_summary"]["zero_leakage_verified"] is True
        assert res["split_summary"]["train_percentage"] == 70.0
        assert res["split_summary"]["val_percentage"] == 15.0
        assert res["split_summary"]["test_percentage"] == 15.0

        # Assert chronological monotonicity
        assert res["split_summary"]["train_window_end"] <= res["split_summary"]["val_window_start"]
        assert res["split_summary"]["val_window_end"] <= res["split_summary"]["test_window_start"]

        # Models evaluated
        model_ids = [m["model_id"] for m in res["models"]]
        assert "baseline_persistence" in model_ids
        assert "baseline_seasonal_naive" in model_ids
        assert "baseline_ar_linear" in model_ids
        assert "baseline_lightgbm_point" in model_ids
        assert "proposed_egsip_conformal" in model_ids

        # Proposed model beats uncalibrated persistence
        egsip = next(m for m in res["models"] if m["model_id"] == "proposed_egsip_conformal")
        persist = next(m for m in res["models"] if m["model_id"] == "baseline_persistence")
        assert egsip["mae_gb"] < persist["mae_gb"]
        assert egsip["interval_coverage_pct"] >= 80.0
    finally:
        db.close()


def test_gauntlet_reproducible_research_endpoints():
    """Validates GAUNTLET API endpoints for reproducible validation and JSON/CSV exports."""
    # 1. API validation endpoint
    resp = client.get("/api/v1/gauntlet/benchmarks/reproducible-research?device_id=vol-nvme-tier1-db")
    assert resp.status_code == 200
    data = resp.json()
    assert data["split_summary"]["zero_leakage_verified"] is True
    assert len(data["models"]) == 5

    # 2. JSON export
    resp_json = client.get("/api/v1/gauntlet/benchmarks/export?device_id=vol-nvme-tier1-db&format=json")
    assert resp_json.status_code == 200
    assert resp_json.json()["random_seed"] == 42

    # 3. CSV export
    resp_csv = client.get("/api/v1/gauntlet/benchmarks/export?device_id=vol-nvme-tier1-db&format=csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    csv_text = resp_csv.text
    assert "experiment_id,device_id,dataset_provenance" in csv_text
    assert "proposed_egsip_conformal" in csv_text
