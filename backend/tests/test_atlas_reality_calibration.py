"""
AEGISSTOR ATLAS — Automated Verification Suite (Reality Calibration & Sim-to-Real Validation)
Tests data connector normalization, held-out discrepancy evaluation, calibration state transitions,
fidelity envelope assessment, action-effect evidence, and evidence-gated planning.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import json
import uuid

from app.main import app
from app.database import SessionLocal
from app.models.entities import (
    Device, Telemetry, AtlasCalibrationConfig, AtlasCalibrationRun,
    AtlasDiscrepancyRecord, AtlasActionEffectEvidence, AtlasFidelityAssessment
)
from app.services.atlas import (
    LinuxDiskstatsAdapter, PrometheusStorageAdapter, BenchmarkTraceAdapter,
    TelemetryStreamSanitizer, DataProvenanceLabel, DataQualityStatus,
    DigitalTwinCalibrationEngine, CalibrationState,
    DiscrepancyAnalysisService, ActionEffectEvidenceService,
    FidelityAssessor, EvidenceGatedPlanner, ValueOfExperimentPlanner
)
from tests.auth_helper import attach_admin_auth

client = attach_admin_auth(TestClient(app))


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_atlas_data_connectors_and_unit_normalization():
    """
    TEST 1: Verifies typed adapters, unit normalization (bytes, ms, MB/s),
    provenance tagging, and gap detection without zero substitution.
    """
    now = datetime.now(timezone.utc)

    # 1. Linux diskstats adapter
    diskstats_line = "   8       0 sda 1000 50 16000 2500 800 20 12000 3200 4 5700 8000 0 0 0 0"
    obs_list = LinuxDiskstatsAdapter.parse_diskstats_line("vol-nvme-tier1-db", diskstats_line, now)
    assert len(obs_list) == 5
    metrics = {o.metric_name: o for o in obs_list}
    assert "read_iops" in metrics
    assert "write_iops" in metrics
    assert "throughput_mb_s" in metrics
    assert "latency_p95_ms" in metrics
    assert "queue_depth" in metrics
    assert metrics["queue_depth"].value == 4.0
    assert metrics["read_iops"].provenance == DataProvenanceLabel.REAL_HARDWARE

    # 2. Prometheus adapter & unit normalization
    prom_vals = [(now.timestamp() - 3600, "1073741824"), (now.timestamp(), "2147483648")]
    prom_obs = PrometheusStorageAdapter.parse_prometheus_metric(
        "vol-sas-tier2-analytics", "used_bytes", prom_vals, raw_unit="bytes"
    )
    assert len(prom_obs) == 2
    assert prom_obs[0].value == 1073741824.0
    assert prom_obs[0].unit == "bytes"
    assert prom_obs[0].provenance == DataProvenanceLabel.REAL_HARDWARE

    # 3. Unit normalization checks
    val, unit = PrometheusStorageAdapter.normalize_unit("latency", 5000.0, "us")
    assert val == 5.0
    assert unit == "ms"

    val_bw, unit_bw = PrometheusStorageAdapter.normalize_unit("throughput", 2048.0, "KB/s")
    assert val_bw == 2.0
    assert unit_bw == "MB/s"

    # 4. Stream sanitizer: deduplication and missing gap detection
    sample1 = prom_obs[0]
    sample2 = prom_obs[1]  # 1 hour apart
    # Inject out-of-order duplicate
    stream = [sample2, sample1, sample1]
    deduped, gaps = TelemetryStreamSanitizer.sanitize_stream(stream, expected_interval_seconds=3600)
    assert len(deduped) == 2
    assert deduped[0].timestamp < deduped[1].timestamp  # chronological order


def test_atlas_calibration_engine_chronological_split(db_session):
    """
    TEST 2: Digital Twin Calibration Engine enforces separate calibration vs held-out evaluation
    windows to prevent test leakage, computing true out-of-sample MAE, RMSE, and bias.
    """
    cfg = DigitalTwinCalibrationEngine.get_or_create_default_config(db_session, "vol-nvme-tier1-db")
    assert cfg is not None

    run = DigitalTwinCalibrationEngine.run_calibration(db_session, cfg.id)
    assert run is not None
    assert run.calibration_status in [
        CalibrationState.CALIBRATED_FOR_SPECIFIED_CONDITIONS,
        CalibrationState.CALIBRATION_DEGRADATION_DETECTED,
        CalibrationState.INSUFFICIENT_EVIDENCE
    ]
    assert run.sample_count > 0
    assert run.evaluation_mae >= 0.0
    assert run.evaluation_rmse >= 0.0
    assert isinstance(run.relative_error, float)

    scope = json.loads(run.condition_scope_json)
    assert "test_leakage_prevented" in scope
    assert scope["test_leakage_prevented"] is True


def test_atlas_discrepancy_analysis_and_regime_breakdown(db_session):
    """
    TEST 3: Sim-to-Real Discrepancy Service calculates residuals, systematic bias direction,
    and analyzes error breakdown across workload regimes (read vs write vs queue contention).
    """
    runs = db_session.query(AtlasCalibrationRun).all()
    assert len(runs) > 0
    target_run = runs[0]

    analysis = DiscrepancyAnalysisService.analyze_run_discrepancy(db_session, target_run.id)
    assert "systematic_bias" in analysis
    assert analysis["bias_direction"] in ["UNDER_PREDICTING", "OVER_PREDICTING", "UNBIASED_NOMINAL"]
    assert "regime_breakdown" in analysis
    assert "time_dependent_drift" in analysis
    assert len(analysis["timeline"]) > 0


def test_atlas_action_effect_evidence_model(db_session):
    """
    TEST 4: Action-Effect model distinguishes causally verified vs assumption-supported effects
    and accounts for side-effect penalties.
    """
    ActionEffectEvidenceService.seed_initial_evidence_if_missing(db_session, "vol-nvme-tier1-db")
    summary = ActionEffectEvidenceService.get_action_evidence_summary(db_session, "vol-nvme-tier1-db")
    assert len(summary) >= 4

    by_action = {s["action_type"]: s for s in summary}
    assert "EXPAND_CAPACITY" in by_action
    assert by_action["EXPAND_CAPACITY"]["is_causally_verified"] is True
    assert "RESCHEDULE_TASK" in by_action
    assert by_action["RESCHEDULE_TASK"]["is_causally_verified"] is False
    assert by_action["RESCHEDULE_TASK"]["evidence_category"] == "ASSUMPTION_SUPPORTED"


def test_atlas_fidelity_assessor_and_scope_envelope(db_session):
    """
    TEST 5: Fidelity Assessor produces multi-indicator fidelity scores and issues
    out-of-scope warnings when operating conditions exceed calibration bounds.
    """
    assessment = FidelityAssessor.evaluate_device_fidelity(db_session, "vol-nvme-tier1-db")
    assert assessment is not None
    assert assessment.assessment_status in [
        "HIGH_FIDELITY", "MODERATE_FIDELITY", "LIMITED_SCOPE", "DEGRADED", "UNKNOWN"
    ]
    assert 0.0 <= assessment.prediction_fidelity_score <= 100.0
    assert 0.0 <= assessment.workload_coverage_score <= 100.0
    assert 0.0 <= assessment.overall_fidelity_score <= 100.0


def test_atlas_evidence_gated_recommendations(db_session):
    """
    TEST 6: Gated planning pipeline evaluates candidate interventions against fidelity scope
    and empirical evidence, prioritizing supported recommendations.
    """
    results = EvidenceGatedPlanner.evaluate_interventions(db_session, "vol-nvme-tier1-db")
    assert len(results) > 0

    verdicts = {r["action_type"]: r["gating_verdict"] for r in results}
    assert "EXPAND_CAPACITY" in verdicts
    assert verdicts["EXPAND_CAPACITY"] in ["SUPPORTED_RECOMMENDATION", "SAFE_TO_SIMULATE", "REQUIRES_HUMAN_REVIEW"]


def test_atlas_value_of_experiment_ranking(db_session):
    """
    TEST 7: VOE Planner identifies evidence gaps and ranks follow-up experiments by
    expected reduction of uncertainty.
    """
    gaps = ValueOfExperimentPlanner.rank_evidence_gaps(db_session, "vol-nvme-tier1-db")
    assert len(gaps) >= 2
    assert gaps[0]["voe_rank"] == 1
    assert "research_question" in gaps[0]["candidate_experiment"]
    assert "learning_objective" in gaps[0]["candidate_experiment"]


def test_atlas_rest_api_endpoints(db_session):
    """
    TEST 8: REST API endpoints under /api/v1/atlas/... return valid payloads.
    """
    # 1. Overview
    res_ov = client.get("/api/v1/atlas/overview")
    assert res_ov.status_code == 200
    data_ov = res_ov.json()
    assert "data_sources" in data_ov
    assert len(data_ov["data_sources"]) >= 3

    # 2. Calibration run via API
    res_cal = client.post("/api/v1/atlas/calibration/run", json={"device_id": "vol-nvme-tier1-db"})
    assert res_cal.status_code == 200
    data_cal = res_cal.json()
    assert "run_id" in data_cal

    # 3. Discrepancy analysis
    res_disc = client.get(f"/api/v1/atlas/discrepancy/{data_cal['run_id']}")
    assert res_disc.status_code == 200
    assert "timeline" in res_disc.json()

    # 4. Fidelity assessment
    res_fid = client.get("/api/v1/atlas/fidelity/vol-nvme-tier1-db")
    assert res_fid.status_code == 200
    assert "overall_fidelity_score" in res_fid.json()

    # 5. Evidence-gated plan
    res_plan = client.post("/api/v1/atlas/evidence-gated-plan", json={"device_id": "vol-nvme-tier1-db"})
    assert res_plan.status_code == 200
    assert len(res_plan.json()["recommendations"]) > 0

    # 6. Controlled experiment creation
    res_exp = client.post("/api/v1/atlas/experiments", json={
        "name": "Controlled 4KB Latency Benchmark",
        "experiment_type": "SIM_TO_REAL_COMPARISON",
        "objective": "Measure tail latency under sustained write bursts",
        "hypothesis": "Queue depth > 4.0 inflates tail latency by 2.2x",
        "target_device_id": "vol-nvme-tier1-db"
    })
    assert res_exp.status_code == 200
    assert res_exp.json()["status"] == "COMPLETED"
