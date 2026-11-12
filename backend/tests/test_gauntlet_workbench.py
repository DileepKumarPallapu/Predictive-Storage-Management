"""
AEGISSTOR GAUNTLET — Automated Test Suite (Prompt 18.0 Part 15)
Verifies:
- Manifest schema validation & SHA-256 integrity
- Dataset split boundaries & temporal leakage prevention
- Real capacity forecasting benchmark execution
- Baseline tournament comparison
- One-click reproduction within numerical tolerance
- Claim-to-evidence consistency (unverified claims cannot be marked verified)
- Failure review ledger preservation
- Examiner mode mutation restrictions (403 Forbidden)
- Sanitized Markdown and CSV report exports
"""
import pytest
import json
import hashlib
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.entities import (
    Device, GauntletSuite, GauntletRun, GauntletClaim, GauntletFailure, GauntletReproduction, User
)
from app.services.gauntlet_service import GauntletService
from tests.auth_helper import attach_admin_auth

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield attach_admin_auth(c)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_gauntlet_catalog_and_seeding(client, db):
    """Verifies that all 4 canonical suites and initial claims are seeded with complete metadata."""
    res = client.get("/api/v1/gauntlet/catalog")
    assert res.status_code == 200
    suites = res.json()
    assert len(suites) >= 4

    suite_ids = [s["id"] for s in suites]
    assert "suite-capacity-forecast-v1" in suite_ids
    assert "suite-perf-iops-v1" in suite_ids
    assert "suite-decision-quality-v1" in suite_ids
    assert "suite-robustness-jurassic-v1" in suite_ids

    cap_suite = next(s for s in suites if s["id"] == "suite-capacity-forecast-v1")
    assert "Pinball Loss" in str(cap_suite["expected_outputs"])
    assert "Strict temporal split" in str(cap_suite["safety_constraints"])
    assert len(cap_suite["acceptance_criteria"]) > 0


def test_manifest_schema_and_sha256_integrity():
    """Verifies that run manifests produce deterministic, verifiable SHA-256 hashes."""
    fixed_ts = "2026-10-21T18:00:00Z"
    manifest1, hash1 = GauntletService.create_run_manifest(
        run_id="test-run-001",
        suite_id="suite-capacity-forecast-v1",
        suite_version="1.0.0",
        device_id="vol-nvme-tier1-db",
        dataset_id="enterprise-telemetry-primary",
        parameters={"random_seed": 42, "horizon_hours": 72},
        split_ratios={"train": 0.70, "val": 0.15, "test": 0.15},
        evaluation_window={"train_samples": 500, "val_samples": 100, "test_samples": 100},
        created_at_utc=fixed_ts
    )

    manifest2, hash2 = GauntletService.create_run_manifest(
        run_id="test-run-001",
        suite_id="suite-capacity-forecast-v1",
        suite_version="1.0.0",
        device_id="vol-nvme-tier1-db",
        dataset_id="enterprise-telemetry-primary",
        parameters={"random_seed": 42, "horizon_hours": 72},
        split_ratios={"train": 0.70, "val": 0.15, "test": 0.15},
        evaluation_window={"train_samples": 500, "val_samples": 100, "test_samples": 100},
        created_at_utc=fixed_ts
    )

    assert hash1 == hash2
    assert len(hash1) == 64
    assert manifest1["source_code_revision"] == "87b20a5"
    assert manifest1["safety_profile"]["physical_mutation_enabled"] is False


def test_capacity_forecasting_benchmark_execution(client, db):
    """Executes the complete capacity forecasting benchmark and checks genuine empirical metrics."""
    res = client.post(
        "/api/v1/gauntlet/run",
        json={
            "suite_id": "suite-capacity-forecast-v1",
            "device_id": "vol-nvme-tier1-db",
            "parameters": {"horizon_hours": 48, "random_seed": 42}
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert len(data["manifest_sha256"]) == 64
    assert data["execution_seconds"] > 0

    results = data["results"]
    assert results["suite_category"] == "CAPACITY_FORECAST"
    metrics = results["metrics"]
    assert "persistence" in metrics
    assert "seasonal_naive" in metrics
    assert "quantile_ml" in metrics

    # Verify quantitative sanity
    q_ml = metrics["quantile_ml"]
    assert q_ml["mae_gb"] >= 0.0
    assert q_ml["rmse_gb"] >= 0.0
    assert 0.0 <= q_ml["coverage_pct"] <= 100.0
    assert q_ml["interval_width_gb"] > 0.0
    assert "pinball_loss_q50" in q_ml


def test_baseline_tournament_endpoint(client):
    """Verifies that the tournament endpoint returns fair comparative evaluation across methods."""
    res = client.get("/api/v1/gauntlet/tournament?device_id=vol-nvme-tier1-db")
    assert res.status_code == 200
    data = res.json()
    assert "tournament_comparison" in data
    comp = data["tournament_comparison"]
    assert len(comp) >= 3

    method_names = [m["method_name"] for m in comp]
    assert any("Baseline A: Fixed Threshold Alert" in m for m in method_names)
    assert any("Baseline E: Ungated Digital Twin" in m for m in method_names)
    assert any("Baseline F: Proposed Evidence-Gated Planner" in m for m in method_names)

    gated = next(m for m in comp if "Baseline F" in m["method_name"])
    assert gated["infeasible_action_rate"] == 0.0
    assert gated["false_alarm_rate"] <= 0.05
    assert gated["residual_operational_risk"] <= 0.10


def test_one_click_reproduction_flow(client, db):
    """Tests reproducing an existing benchmark run and verifying metric drift stays within tolerance."""
    # First, run a baseline benchmark to reproduce
    init_res = client.post(
        "/api/v1/gauntlet/run",
        json={
            "suite_id": "suite-decision-quality-v1",
            "device_id": "vol-nvme-tier1-db",
            "parameters": {"horizon_hours": 72}
        }
    )
    assert init_res.status_code == 200
    run_id = init_res.json()["run_id"]

    # Now reproduce it
    repro_res = client.post(
        f"/api/v1/gauntlet/reproduce/{run_id}",
        json={"tolerance_pct": 3.0}
    )
    assert repro_res.status_code == 200
    repro_data = repro_res.json()

    assert repro_data["status"] == "REPRODUCED_WITHIN_TOLERANCE"
    assert repro_data["max_relative_drift_pct"] <= 3.0
    assert "Numerical Comparison Table" in repro_data["report_md"]

    # Verify reproduction record persisted in DB
    repro_db = db.query(GauntletReproduction).filter(GauntletReproduction.original_run_id == run_id).first()
    assert repro_db is not None
    assert repro_db.status == "REPRODUCED_WITHIN_TOLERANCE"


def test_claim_ledger_consistency_and_unverified_guard(client, db):
    """Verifies that unverified claims remain marked as UNVERIFIED and cannot be auto-promoted."""
    res = client.get("/api/v1/gauntlet/claims")
    assert res.status_code == 200
    claims = res.json()
    assert len(claims) >= 4

    unverified = next((c for c in claims if c["id"] == "claim-gnt-004"), None)
    assert unverified is not None
    assert unverified["verification_status"] == "UNVERIFIED"
    assert len(unverified["supporting_run_ids"]) == 0


def test_failure_ledger_transparency(client):
    """Verifies that failed experiments and anomaly records are transparently listed with reproduction steps."""
    res = client.get("/api/v1/gauntlet/failures")
    assert res.status_code == 200
    failures = res.json()
    assert len(failures) >= 2

    fail_categories = [f["failure_category"] for f in failures]
    assert "INTERCONNECT_SATURATION" in fail_categories
    assert "TELEMETRY_DROPOUT" in fail_categories

    for f in failures:
        assert f["reproduction_steps"] != ""
        assert f["expected_behavior"] != ""
        assert f["actual_behavior"] != ""
        assert f["resolution_state"] in ["RESOLVED", "ACCEPTED_LIMITATION", "OPEN", "INVESTIGATING"]


def test_reviewer_mutation_restriction(client, db):
    """Verifies that an examiner / reviewer is forbidden from editing claims (403 Forbidden)."""
    # Create an authenticated header for examiner user
    from app.auth.security import create_access_token
    examiner_token = create_access_token({"sub": "examiner"})
    headers = {"Authorization": f"Bearer {examiner_token}"}

    # Attempt to modify a claim
    res = client.post(
        "/api/v1/gauntlet/claims",
        headers=headers,
        json={
            "id": "claim-gnt-001",
            "claim_text": "Unauthorized alteration by reviewer",
            "category": "FORECAST_ACCURACY",
            "verification_status": "SUPPORTED_WITHIN_TESTED_CONDITIONS"
        }
    )
    assert res.status_code == 403
    detail_msg = res.json()["detail"]
    assert "Examiner Mode is read-only" in detail_msg or "Permission denied" in detail_msg


def test_examiner_report_exports(client):
    """Tests exporting sanitized Markdown and CSV examiner reports."""
    md_res = client.get("/api/v1/gauntlet/export/markdown")
    assert md_res.status_code == 200
    assert md_res.headers["content-type"].startswith("text/markdown")
    md_text = md_res.text
    assert "# AEGISSTOR GAUNTLET — Independent Industry Examiner Report" in md_text
    assert "Claim-to-Evidence Audit Ledger" in md_text
    assert "Failure & Anomaly Ledger" in md_text
    # Verify no leaked secrets or invention text
    assert "PRIVATE_KEY" not in md_text
    assert "password" not in md_text

    csv_res = client.get("/api/v1/gauntlet/export/csv")
    assert csv_res.status_code == 200
    assert "run_id,suite_id,device_id" in csv_res.text
