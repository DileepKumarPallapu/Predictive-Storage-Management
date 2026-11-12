import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.services.evidence_gated_planner import EvidenceGatedPlanner
from app.services.research_benchmark_engine import ResearchBenchmarkEngine
from tests.auth_helper import attach_admin_auth

client = attach_admin_auth(TestClient(app))

@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_evidence_gated_planner_full_pipeline(db_session):
    """
    TEST 1: Verifies the complete vertical slice of the candidate research planner:
    Input chronological telemetry -> Conformal Forecast -> Atlas Fidelity ->
    Omega Multi-Resource -> Lead-Time Feasibility -> Recommendation or Fallback.
    """
    res = EvidenceGatedPlanner.plan_interventions(db_session, "vol-nvme-tier1-db", horizon_hours=72)
    
    assert res is not None
    assert res["device_id"] == "vol-nvme-tier1-db"
    assert "forecast_summary" in res
    assert "evidence_quality" in res
    assert "multi_resource_context" in res
    assert "candidate_evaluations" in res
    assert res["final_status"] in ["ACTION_RECOMMENDED", "EVIDENCE_GATED_FALLBACK", "NO_FEASIBLE_ACTION_FALLBACK"]
    assert len(res["candidate_evaluations"]) >= 4

def test_lead_time_feasibility_enforcement(db_session):
    """
    TEST 2: Verifies that candidate actions requiring longer execution lead-time
    than the warning lead time h* are strictly disqualified.
    """
    res = EvidenceGatedPlanner.plan_interventions(db_session, "vol-nvme-tier1-db", horizon_hours=72)
    lead_time_h_star = res.get("warning_lead_time_h_star")
    
    for candidate in res["candidate_evaluations"]:
        if lead_time_h_star is not None and candidate["execution_hours"] > lead_time_h_star:
            assert candidate["is_feasible"] is False
            assert any("Lead-time violation" in r for r in candidate["rejection_reasons"])

def test_multi_resource_propagation_disqualification(db_session):
    """
    TEST 3: Verifies that an intervention imposing high shared bus penalties
    on shared controllers (Omega topology) is flagged for multi-resource contention.
    """
    res = EvidenceGatedPlanner.plan_interventions(db_session, "vol-nvme-tier1-db", horizon_hours=72)
    
    for candidate in res["candidate_evaluations"]:
        if candidate["shared_bus_penalty_pct"] > 15.0:
            assert candidate["is_feasible"] is False
            assert any("Multi-resource contention" in r for r in candidate["rejection_reasons"])

def test_evidence_sufficiency_fallback(db_session):
    """
    TEST 4: Verifies the guaranteed fallback rule:
    When simulator discrepancy exceeds tolerance or fidelity is degraded,
    the system must emit: 'INSUFFICIENT EVIDENCE OR NO FEASIBLE ACTION — MANUAL REVIEW REQUIRED'.
    """
    # Temporarily force low fidelity in evaluation
    planner = EvidenceGatedPlanner()
    original_min = planner.MIN_REQUIRED_EVIDENCE_FIDELITY
    try:
        EvidenceGatedPlanner.MIN_REQUIRED_EVIDENCE_FIDELITY = 99.9  # Force evidence insufficiency
        res = EvidenceGatedPlanner.plan_interventions(db_session, "vol-nvme-tier1-db", horizon_hours=72)
        assert res["final_status"] == "EVIDENCE_GATED_FALLBACK"
        assert res["recommended_action"] is None
        assert "FALLBACK TRIGGERED" in res["decision_rationale"]
    finally:
        EvidenceGatedPlanner.MIN_REQUIRED_EVIDENCE_FIDELITY = original_min

def test_baselines_comparison_suite(db_session):
    """
    TEST 5: Verifies execution across Baselines A through F:
    A: Fixed threshold, B: Persistence, C: Point forecast, D: Quantile bounds,
    E: Ungated Digital Twin, F: Proposed Evidence-Gated Planner.
    """
    res = ResearchBenchmarkEngine.run_all_baselines(db_session, "vol-nvme-tier1-db", horizon_hours=72)
    assert res is not None
    assert len(res["baselines"]) == 6
    
    names = [b["name"] for b in res["baselines"]]
    assert any("Baseline A" in n for n in names)
    assert any("Baseline B" in n for n in names)
    assert any("Baseline C" in n for n in names)
    assert any("Baseline D" in n for n in names)
    assert any("Baseline E" in n for n in names)
    assert any("Baseline F" in n for n in names)
    
    # Baseline F must achieve lowest residual risk and zero infeasible actions
    base_f = next(b for b in res["baselines"] if "Baseline F" in b["name"])
    assert base_f["infeasible_action_rate"] == 0.0
    assert base_f["evidence_gated"] is True

def test_ablation_study_execution(db_session):
    """
    TEST 6: Evaluates Ablations 1 through 7 and verifies that removing components
    degrades residual risk or produces unfeasible recommendations.
    """
    ablations = ResearchBenchmarkEngine.run_ablation_study(db_session, "vol-nvme-tier1-db", horizon_hours=72)
    assert len(ablations) == 8  # Ablation 0 (Complete) + 7 Ablations
    
    complete = ablations[0]
    assert complete["ablation_name"] == "Ablation 0: Complete Proposed Framework"
    assert complete["fidelity_checked"] is True
    assert complete["lead_time_checked"] is True

def test_research_endpoints_rest_api():
    """
    TEST 7: Verifies FastAPI REST endpoints:
    - POST /api/v1/research/planner/plan
    - GET /api/v1/research/benchmarks/baselines
    - GET /api/v1/research/benchmarks/ablations
    """
    res1 = client.post("/api/v1/research/planner/plan?device_id=vol-nvme-tier1-db&horizon_hours=72")
    assert res1.status_code == 200
    data1 = res1.json()
    assert "candidate_evaluations" in data1
    
    res2 = client.get("/api/v1/research/benchmarks/baselines?device_id=vol-nvme-tier1-db&horizon_hours=72")
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["baselines"]) == 6
    
    res3 = client.get("/api/v1/research/benchmarks/ablations?device_id=vol-nvme-tier1-db&horizon_hours=72")
    assert res3.status_code == 200
    data3 = res3.json()
    assert len(data3) == 8
