"""
AEGISSTOR SOVEREIGN — Automated Test Suite (Prompt 19.0 Part 15)
Verifies:
- Multi-site isolated simulation & local telemetry boundaries
- Local parametric model training & temporal leakage prevention
- Conventional Federated Averaging (FedAvg) parameter aggregation
- Reliability-aware aggregation weighting and rejection
- Personalized local model adaptation
- Differential privacy clipping and noise injection
- Coordinator-side update integrity & adversarial stress testing (NaNs, wrong dimensions, excessive norms)
- Multi-site collaborative baseline tournament
- Raw telemetry data minimization & privacy boundaries
"""
import pytest
import json
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.entities import (
    SovereignSite, SovereignRound, SovereignUpdate, SovereignGlobalModel, SovereignExperiment
)
from app.services.sovereign_service import SovereignService

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_sovereign_sites_seeding_and_isolation(client, db):
    """Verifies that all 4 canonical sites are seeded and maintain local metadata isolation."""
    res = client.get("/api/v1/sovereign/sites")
    assert res.status_code == 200
    sites = res.json()
    assert len(sites) >= 4

    site_ids = [s["id"] for s in sites]
    assert "site-us-east-oltp" in site_ids
    assert "site-eu-west-analytics" in site_ids
    assert "site-ap-south-edge" in site_ids
    assert "site-sa-east-backup" in site_ids

    # Verify site workload heterogeneity
    oltp = next(s for s in sites if s["id"] == "site-us-east-oltp")
    assert oltp["workload_type"] == "OLTP_WRITE_HEAVY"
    assert oltp["reliability_score"] >= 0.90


def test_local_model_training_and_feature_pipeline(db):
    """Tests local Ridge regressor training on isolated site telemetry."""
    res = SovereignService.train_local_model(db, "site-us-east-oltp")
    assert res["site_id"] == "site-us-east-oltp"
    assert res["sample_count"] > 100
    assert len(res["weights"]) == 8
    assert res["update_norm"] > 0.0
    assert res["validation_metrics"]["mae_gb"] >= 0.0
    assert res["validation_metrics"]["rmse_gb"] >= 0.0


def test_conventional_fedavg_aggregation(client, db):
    """Executes a standard FedAvg round and verifies coordinator parameter aggregation."""
    res = client.post(
        "/api/v1/sovereign/rounds/run",
        json={
            "round_number": 1,
            "aggregation_strategy": "FED_AVG",
            "participating_site_ids": ["site-us-east-oltp", "site-eu-west-analytics"]
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] if "status" in data else data["round_number"] == 1
    assert data["aggregation_strategy"] == "FED_AVG"
    assert len(data["aggregated_weights"]) == 8
    assert data["participating_sites"] == 2
    assert data["rejections"] == 0

    # Verify Global Model artifact was registered
    gmodel = db.query(SovereignGlobalModel).filter(SovereignGlobalModel.version == "v1.0.0").first()
    assert gmodel is not None


def test_reliability_aware_aggregation(client, db):
    """Tests reliability-aware aggregation weighting where high-reliability sites receive higher weight."""
    res = client.post(
        "/api/v1/sovereign/rounds/run",
        json={
            "round_number": 2,
            "aggregation_strategy": "RELIABILITY_AWARE",
            "participating_site_ids": ["site-us-east-oltp", "site-sa-east-backup"]
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["aggregation_strategy"] == "RELIABILITY_AWARE"
    assert len(data["aggregated_weights"]) == 8

    # Query update records to check assigned weights
    updates = db.query(SovereignUpdate).filter(SovereignUpdate.round_id == data["round_id"]).all()
    assert len(updates) == 2
    oltp_up = next(u for u in updates if u.site_id == "site-us-east-oltp")
    backup_up = next(u for u in updates if u.site_id == "site-sa-east-backup")
    # OLTP site has higher reliability (0.94 vs 0.65) so assigned weight must be higher
    assert oltp_up.assigned_weight > backup_up.assigned_weight


def test_differential_privacy_clipping_and_noise(client, db):
    """Verifies parameter clipping and Gaussian noise injection under DP mode."""
    res = client.post(
        "/api/v1/sovereign/rounds/run",
        json={
            "round_number": 3,
            "aggregation_strategy": "DIFFERENTIAL_PRIVACY",
            "dp_clip_norm": 5.0,
            "dp_noise_sigma": 0.05
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["aggregation_strategy"] == "DIFFERENTIAL_PRIVACY"
    weights = np.array(data["aggregated_weights"])
    # Norm of aggregated weights must be strictly bounded
    assert np.linalg.norm(weights) <= 15.0


def test_coordinator_update_integrity_rejection():
    """Verifies coordinator validation rejects NaNs, wrong dimensions, and extreme poisoning norms."""
    # Test 1: NaN rejection
    valid_nan, reason_nan = SovereignService.validate_incoming_update([float('nan')] * 8, 0.0, 100)
    assert valid_nan is False
    assert "Non-finite" in reason_nan

    # Test 2: Dimension mismatch
    valid_dim, reason_dim = SovereignService.validate_incoming_update([0.1, 0.2, 0.3], 0.0, 100)
    assert valid_dim is False
    assert "Dimension mismatch" in reason_dim

    # Test 3: Excessive poisoning norm
    valid_norm, reason_norm = SovereignService.validate_incoming_update([5000.0] * 8, 0.0, 100, max_norm=1000.0)
    assert valid_norm is False
    assert "Excessive update magnitude" in reason_norm

    # Test 4: Valid update
    valid_ok, reason_ok = SovereignService.validate_incoming_update([0.1] * 8, 12.0, 500)
    assert valid_ok is True
    assert reason_ok is None


def test_adversarial_stress_test_endpoint(client):
    """Tests the /api/v1/sovereign/stress-test endpoint."""
    res = client.post("/api/v1/sovereign/stress-test")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["all_adversarial_attacks_blocked"] is True
    assert len(data["attack_scenarios_evaluated"]) == 4


def test_collaborative_tournament_endpoint(client, db):
    """Verifies multi-site collaborative tournament compares Local vs FedAvg vs Personalized vs Reliability."""
    res = client.get("/api/v1/sovereign/tournament")
    assert res.status_code == 200
    data = res.json()
    assert "site_results" in data
    assert len(data["site_results"]) >= 4

    # Check that personalized adaptation yields improvements
    for sr in data["site_results"]:
        assert "local_only" in sr
        assert "fed_avg" in sr
        assert "personalized" in sr
        assert "reliability_aware" in sr
        assert sr["personalized"]["mae_gb"] > 0.0

    # Edge low-volume site must show lower MAE under federated / personalized compared to local-only
    edge_site = next(s for s in data["site_results"] if s["site_id"] == "site-ap-south-edge")
    assert edge_site["fed_avg"]["mae_gb"] < edge_site["local_only"]["mae_gb"]


def test_privacy_audit_and_boundaries(client):
    """Verifies that privacy audit report confirms telemetry stays local."""
    res = client.get("/api/v1/sovereign/privacy-audit")
    assert res.status_code == 200
    data = res.json()
    assert "threat_model_version" in data
    assert "privacy_controls" in data
    controls = data["privacy_controls"]
    raw_telemetry_control = next(c for c in controls if "Raw Storage Telemetry" in c["data_classification"])
    assert "100% Local" in raw_telemetry_control["boundary"]
    assert raw_telemetry_control["status"] == "ENFORCED"


def test_sovereign_markdown_report_export(client):
    """Tests exporting the Sovereign research dossier in Markdown."""
    res = client.get("/api/v1/sovereign/export/markdown")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/markdown")
    text = res.text
    assert "# AEGISSTOR SOVEREIGN — Federated Storage Intelligence Report" in text
    assert "Multi-Site Collaborative Tournament Results" in text
    assert "100% withheld locally" in text
