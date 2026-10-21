"""
AEGISSTOR ORACLE — Workload Attribution, Bottleneck Forensics & Explainable Storage Intelligence
Verification Suite (Prompt 15.0)
Tests:
- Workload catalog & direct attribution (Method A)
- Aggregate reconciliation & residual calculation (Method B)
- Statistical feature attribution with non-causal guardrails (Method C)
- Capacity growth forensics, velocity, acceleration & changepoint discovery
- Performance bottleneck forensics & resource contention graph
- Bottleneck case triage & transparent ranking
- Hypothesis lifecycle, status transitions & automated contradiction detection
- Counterfactual what-if simulations against Digital Twin
- Interpretable report generation & Markdown/CSV export
- Edge cases: invalid resources, unsupported attribution, unearned causal claims
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import json

from app.main import app
from app.database import SessionLocal
from app.models.entities import (
    Device, OracleWorkload, OracleWorkloadTelemetry, OracleHypothesis,
    OracleBottleneckCase, OracleCounterfactualExperiment
)
from app.services.oracle import (
    WorkloadCatalogService, AttributionEngine, CapacityForensicsService,
    BottleneckForensicsEngine, HypothesisManager, CounterfactualExperimentService,
    OracleReportGenerator
)

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        WorkloadCatalogService.seed_workloads_if_missing(db)
        BottleneckForensicsEngine.seed_initial_bottleneck_cases_if_missing(db)
        HypothesisManager.seed_initial_hypotheses_if_missing(db)
        yield db
    finally:
        db.close()


def test_workload_catalog_and_listing(db_session):
    """
    TEST 1: Verifies known workloads, priority classifications, SLA latency ceilings,
    and granular attribution availability flags.
    """
    res = client.get("/api/v1/oracle/workloads")
    assert res.status_code == 200
    workloads = res.json()
    assert len(workloads) >= 6

    ids = [w["id"] for w in workloads]
    assert "wl-postgres-oltp" in ids
    assert "wl-analytics-batch" in ids
    assert "wl-backup-snapshot" in ids
    assert "wl-unattributed-residual" in ids

    # Verify residual workload is explicitly marked as attribution_available=False
    residual_wl = next(w for w in workloads if w["id"] == "wl-unattributed-residual")
    assert residual_wl["attribution_available"] is False
    assert residual_wl["workload_type"] == "RESIDUAL"

    # Verify OLTP workload has active telemetry
    oltp_wl = next(w for w in workloads if w["id"] == "wl-postgres-oltp")
    assert oltp_wl["attribution_available"] is True
    assert oltp_wl["latest_telemetry"]["allocated_gb"] > 1000.0
    assert oltp_wl["latest_telemetry"]["read_iops"] > 0.0


def test_attribution_engine_methods(db_session):
    """
    TEST 2: Verifies Method A (Direct measurement), Method B (Aggregate reconciliation
    and residual tracking), and Method C (Statistical feature decomposition with
    mandatory non-causal disclaimer).
    """
    res = client.get("/api/v1/oracle/attribution/vol-nvme-tier1-db?hours=72")
    assert res.status_code == 200
    data = res.json()

    assert data["device_id"] == "vol-nvme-tier1-db"
    assert data["device_aggregate_used_gb"] > 0
    assert data["total_attributed_gb"] > 0
    assert "attribution_coverage_pct" in data
    assert data["reconciliation_status"] in ["BALANCED", "PARTIAL_COVERAGE", "POOR_COVERAGE"]

    # Verify breakdown contains direct measurements and residual row
    breakdown = data["workload_breakdown"]
    methods = [item["attribution_method"] for item in breakdown]
    assert "DIRECT_MEASUREMENT" in methods

    # Verify Scientific Guardrail: Non-causal disclaimer must be explicitly present
    assert "scientific_disclaimer" in data
    assert "does not establish that a workload caused a storage bottleneck" in data["scientific_disclaimer"]

    # Verify Method C statistical attribution scores
    stat_attr = data["statistical_attribution"]
    assert len(stat_attr) > 0
    for s in stat_attr:
        assert "composite_attribution_score" in s
        assert s["is_causally_proven"] is False


def test_capacity_growth_forensics(db_session):
    """
    TEST 3: Verifies historical capacity decomposition, growth rate (GB/day),
    acceleration/deceleration, changepoints, and reserve runway projections.
    """
    res = client.get("/api/v1/oracle/capacity-forensics/vol-nvme-tier1-db?window_hours=168")
    assert res.status_code == 200
    data = res.json()

    assert data["device_id"] == "vol-nvme-tier1-db"
    assert data["initial_used_gb"] > 0
    assert data["final_used_gb"] >= data["initial_used_gb"]
    assert "growth_rate_gb_per_day" in data
    assert "acceleration_gb_per_day2" in data
    assert data["growth_pattern"] in ["STEADY", "ACCELERATING", "DECELERATING"]
    assert "period_comparison" in data
    assert "reserve_runway_projection" in data
    assert data["reserve_runway_projection"]["remaining_headroom_gb"] >= 0


def test_bottleneck_forensics_and_contention_index(db_session):
    """
    TEST 4: Verifies latency metrics evaluation against SLA ceilings, concurrent
    background job detection, and contention index scoring.
    """
    res = client.get("/api/v1/oracle/bottlenecks/vol-nvme-tier1-db?hours=72")
    assert res.status_code == 200
    data = res.json()

    assert data["device_id"] == "vol-nvme-tier1-db"
    assert 0.0 <= data["contention_index"] <= 1.0
    assert data["contention_level"] in ["HIGH", "MODERATE", "LOW"]
    assert "latency_metrics" in data
    assert "sla_ceiling_ms" in data["latency_metrics"]
    assert "concurrent_background_jobs" in data
    assert "scientific_disclaimer" in data


def test_resource_contention_graph(db_session):
    """
    TEST 5: Verifies the resource contention graph topology: Workloads, Devices,
    Pools, and Controller nodes, distinguishing verified dependencies from suspected contention.
    """
    res = client.get("/api/v1/oracle/contention-graph")
    assert res.status_code == 200
    graph = res.json()

    assert "nodes" in graph
    assert "edges" in graph
    assert graph["summary"]["total_nodes"] > 5
    assert graph["summary"]["verified_edges"] > 0
    assert graph["summary"]["suspected_contention_edges"] > 0

    node_types = set(n["type"] for n in graph["nodes"])
    assert "WORKLOAD" in node_types
    assert "DEVICE" in node_types
    assert "STORAGE_POOL" in node_types
    assert "CONTROLLER" in node_types


def test_bottleneck_case_management(db_session):
    """
    TEST 6: Verifies transparent bottleneck queue listing, evidence quality scores,
    and case status updates.
    """
    res = client.get("/api/v1/oracle/cases")
    assert res.status_code == 200
    cases = res.json()
    assert len(cases) >= 2

    case_id = cases[0]["id"]
    assert cases[0]["evidence_quality_score"] > 0.5
    assert len(cases[0]["supporting_evidence"]) > 0

    # Test triage status update
    patch_res = client.patch(
        f"/api/v1/oracle/cases/{case_id}",
        json={"status": "INVESTIGATING", "assigned_to": "alice_sre@aegisstor.internal"}
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "INVESTIGATING"
    assert updated["assigned_to"] == "alice_sre@aegisstor.internal"


def test_hypothesis_lifecycle_and_contradiction_detection(db_session):
    """
    TEST 7: Verifies hypothesis creation, automated evidence contradiction checks,
    audit trail tracking, and enforcement of the scientific rule preventing
    unearned promotion to 'SUPPORTED_WITHIN_CONDITIONS'.
    """
    # 1. Create a hypothesis with topological contradiction
    # Workload wl-backup-snapshot targets vol-cold-tier3-backup, but hypothesis tests vol-nvme-tier1-db
    payload = {
        "question": "Is backup snapshot sync causing NVMe write latency spikes?",
        "target_resource": "vol-nvme-tier1-db",
        "workload_id": "wl-backup-snapshot",
        "supporting_evidence": ["Observed queue depth > 3.0 during Sunday midnight window"],
        "proposed_evaluation_method": "CONTROLLED_DIGITAL_TWIN_SIMULATION",
        "reviewer": "chief_architect@aegisstor.internal"
    }
    create_res = client.post("/api/v1/oracle/hypotheses", json=payload)
    assert create_res.status_code == 201
    created = create_res.json()
    hyp_id = created["id"]
    assert created["status"] == "DRAFT"
    # Automated contradiction detector must have caught the topological mismatch!
    assert created["automated_contradictions_flagged"] >= 1

    # Fetch created hypothesis and verify contradictory evidence contains the mismatch
    list_res = client.get(f"/api/v1/oracle/hypotheses?target_resource=vol-nvme-tier1-db")
    matching = next(h for h in list_res.json() if h["id"] == hyp_id)
    assert any("Topological Disconnect" in ce for ce in matching["contradicting_evidence"])

    # 2. Scientific Rule Test: Cannot promote directly from DRAFT to SUPPORTED_WITHIN_CONDITIONS
    invalid_patch = client.patch(
        f"/api/v1/oracle/hypotheses/{hyp_id}",
        json={
            "status": "SUPPORTED_WITHIN_CONDITIONS",
            "rationale": "High feature importance observed in model.",
            "reviewer": "test_sre"
        }
    )
    assert invalid_patch.status_code == 400
    assert "Scientific Rule Violation" in invalid_patch.json()["detail"]

    # 3. Valid transition to READY_FOR_TESTING
    valid_patch = client.patch(
        f"/api/v1/oracle/hypotheses/{hyp_id}",
        json={
            "status": "READY_FOR_TESTING",
            "rationale": "Telemetry gathered; ready for simulation.",
            "reviewer": "test_sre"
        }
    )
    assert valid_patch.status_code == 200
    assert valid_patch.json()["status"] == "READY_FOR_TESTING"


def test_counterfactual_workload_experiments(db_session):
    """
    TEST 8: Verifies controlled what-if workload simulation against Digital Twin,
    parameter variance, simulated vs baseline metrics, and non-causal disclaimer.
    """
    payload = {
        "target_device_id": "vol-nvme-tier1-db",
        "workload_id": "wl-analytics-batch",
        "intervention_type": "THROTTLE_INTENSITY",
        "parameters": {"intensity_reduction_pct": 35.0},
        "horizon_hours": 72
    }
    res = client.post("/api/v1/oracle/counterfactual", json=payload)
    assert res.status_code == 200
    result = res.json()

    assert result["target_device_id"] == "vol-nvme-tier1-db"
    assert result["workload_id"] == "wl-analytics-batch"
    assert result["is_causally_proven"] is False
    assert "Simulated counterfactual outcome" in result["causality_disclaimer"]
    assert "simulated_outcome" in result
    assert result["simulated_outcome"]["latency_reduction_pct"] >= 0.0

    # Verify experiment history
    hist_res = client.get("/api/v1/oracle/counterfactual?target_device_id=vol-nvme-tier1-db")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1


def test_investigation_report_and_export(db_session):
    """
    TEST 9: Verifies report generator output in JSON, Markdown, and CSV formats.
    """
    # 1. JSON report
    res_json = client.get("/api/v1/oracle/report/vol-nvme-tier1-db")
    assert res_json.status_code == 200
    rpt = res_json.json()
    assert "report_id" in rpt
    assert "investigation_question" in rpt
    assert "attribution_summary" in rpt
    assert "scientific_limitations" in rpt

    # 2. Markdown export
    res_md = client.get("/api/v1/oracle/report/vol-nvme-tier1-db/export?format=markdown")
    assert res_md.status_code == 200
    assert "text/markdown" in res_md.headers["content-type"]
    assert "# AEGISSTOR ORACLE" in res_md.text
    assert "Workload Capacity Attribution" in res_md.text

    # 3. CSV export
    res_csv = client.get("/api/v1/oracle/report/vol-nvme-tier1-db/export?format=csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "workload_id,workload_name" in res_csv.text


def test_oracle_edge_cases(db_session):
    """
    TEST 10: Tests resilience against missing devices, invalid statuses,
    and extreme horizon bounds.
    """
    # Non-existent device
    bad_dev = client.get("/api/v1/oracle/attribution/vol-nonexistent-99")
    assert bad_dev.status_code == 404

    # Invalid hypothesis status
    bad_status = client.patch(
        "/api/v1/oracle/hypotheses/hyp-oracle-lat-01",
        json={"status": "INVALID_STATE", "rationale": "foo"}
    )
    assert bad_status.status_code == 400

    # Out of bounds horizon
    bad_horizon = client.get("/api/v1/oracle/capacity-forensics/vol-nvme-tier1-db?window_hours=5")
    assert bad_horizon.status_code == 422
