import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.auth_helper import attach_admin_auth

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield attach_admin_auth(c)

def test_omega_topology_endpoint(client):
    """Verify fleet resource topology graph returns nodes, edges, provenance, and workloads."""
    res = client.get("/api/v1/omega/topology")
    assert res.status_code == 200
    data = res.json()

    assert "summary" in data
    assert data["summary"]["total_systems"] >= 3
    assert data["summary"]["total_pools"] >= 4
    assert data["summary"]["total_devices"] >= 4
    assert data["summary"]["total_relationships"] >= 7
    assert data["summary"]["total_workloads"] >= 4

    # Verify nodes
    node_ids = [n["id"] for n in data["nodes"]]
    assert "sys-flasharray-prime" in node_ids
    assert "pool-nvme-ultra" in node_ids
    assert "vol-nvme-tier1-db" in node_ids

    # Verify edge provenance
    provenances = {e["provenance"] for e in data["edges"]}
    assert "DISCOVERED" in provenances
    assert "USER_DEFINED" in provenances
    assert "INFERRED" in provenances

    # Verify workloads
    wl_names = [w["workload_name"] for w in data["workloads"]]
    assert any("E-Commerce" in name for name in wl_names)


def test_omega_fleet_risk_endpoint(client):
    """Verify fleet-wide risk aggregation, shared bottlenecks, and risk budget."""
    res = client.get("/api/v1/omega/fleet-risk")
    assert res.status_code == 200
    data = res.json()

    assert "fleet_metrics" in data
    assert "fleet_risk_budget" in data
    assert "device_risks" in data
    assert "correlated_bottlenecks" in data

    metrics = data["fleet_metrics"]
    assert metrics["total_devices"] >= 4
    assert metrics["fleet_utilization_pct"] > 0.0

    budget = data["fleet_risk_budget"]
    assert budget["max_budget_points"] == 100.0
    assert budget["consumed_risk_points"] >= 0.0
    assert budget["budget_status"] in ["BALANCED", "PRESSURE_ELEVATED", "BUDGET_EXCEEDED"]

    # Verify shared controller bottleneck detection
    bottlenecks = data["correlated_bottlenecks"]
    assert len(bottlenecks) > 0
    types = [b["type"] for b in bottlenecks]
    assert "SHARED_CONTROLLER_BUS_CONTENTION" in types


def test_omega_decision_evaluation_h1(client):
    """Verify Hypothesis H1 benchmark comparing MAE vs Operational Decision Loss."""
    res = client.get("/api/v1/omega/decision-evaluation?device_id=vol-nvme-tier1-db&horizon_hours=72")
    assert res.status_code == 200
    data = res.json()

    assert "models_comparison" in data
    models = data["models_comparison"]
    assert len(models) == 4

    # Find conventional MAE-minimizing LightGBM vs AEGISSTOR Omega
    lgbm = next(m for m in models if m["model_id"] == "standard_mae_lightgbm")
    omega = next(m for m in models if m["model_id"] == "aegisstor_omega_decision_aware")

    # Core empirical research invariant:
    # Standard ML has slightly lower symmetric MAE, but Omega has significantly lower decision loss!
    assert lgbm["mae_pct"] < omega["mae_pct"]
    assert omega["total_operational_decision_loss_usd"] < lgbm["total_operational_decision_loss_usd"]
    assert omega["missed_breaches_count"] == 0
    assert lgbm["missed_breaches_count"] > 0

    assert data["research_findings"]["hypothesis_h1_supported"] is True


def test_omega_adaptive_monitoring_h2(client):
    """Verify Hypothesis H2: Adaptive attention balances telemetry cost and warning margin."""
    res = client.get("/api/v1/omega/adaptive-monitoring?simulation_days=30")
    assert res.status_code == 200
    data = res.json()

    policies = data["policies"]
    assert len(policies) == 3

    pol_a = next(p for p in policies if p["policy_id"] == "POLICY_A_FIXED_HIGH")
    pol_b = next(p for p in policies if p["policy_id"] == "POLICY_B_THRESHOLD_TRIGGERED")
    pol_c = next(p for p in policies if p["policy_id"] == "POLICY_C_VALUE_OF_INFORMATION")

    # Policy C achieves highest Value of Information (VoI) score
    assert pol_c["value_of_information_score"] > pol_a["value_of_information_score"]
    assert pol_c["value_of_information_score"] > pol_b["value_of_information_score"]

    # Policy C saves substantial bandwidth vs Policy A
    assert pol_c["network_bandwidth_mb_day"] < pol_a["network_bandwidth_mb_day"]

    # Live allocations
    assert "live_device_attention_allocations" in data
    allocs = data["live_device_attention_allocations"]
    assert len(allocs) >= 4
    for a in allocs:
        assert "allocated_sampling_interval_s" in a
        assert a["allocated_sampling_interval_s"] in [30, 120, 900, 1800]


def test_omega_fleet_planner_safe_rebalance_h3(client):
    """Verify Hypothesis H3: Dual-sided safety envelope on safe cross-device rebalancing."""
    payload = {
        "source_device_id": "vol-nvme-tier1-db",
        "destination_device_id": "vol-sas-tier2-analytics",
        "migration_size_gb": 800.0,
        "bandwidth_cap_mb_s": 200.0,
    }
    res = client.post("/api/v1/omega/fleet-plan", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "source_impact" in data
    assert "destination_impact" in data
    assert "dual_safety_envelope" in data

    env = data["dual_safety_envelope"]
    assert env["verdict"] in ["FEASIBLE_SAFE", "FEASIBLE_WITH_THROTTLING"]
    assert env["passed"] is True
    assert data["source_impact"]["runway_hours_gained"] > 0


def test_omega_fleet_planner_rejects_unsafe_secondary_breach_h3(client):
    """Verify Hypothesis H3: Hard Safety Envelope REJECTS action causing secondary breach."""
    payload = {
        "source_device_id": "vol-nvme-tier1-db",
        "destination_device_id": "vol-sas-tier2-analytics",
        "migration_size_gb": 45000.0,  # Far exceeds destination headroom
        "bandwidth_cap_mb_s": 350.0,
    }
    res = client.post("/api/v1/omega/fleet-plan", json=payload)
    assert res.status_code == 200
    data = res.json()

    env = data["dual_safety_envelope"]
    assert env["verdict"] == "REJECTED_UNSAFE_SECONDARY_BREACH"
    assert env["passed"] is False
    assert len(env["violations"]) > 0
    assert any("DESTINATION" in v for v in env["violations"])


def test_omega_outcome_ledger_h4(client):
    """Verify Hypothesis H4: Closed-loop outcome ledger tracks triples & 4 outcome classes."""
    res = client.get("/api/v1/omega/outcome-ledger?limit=20")
    assert res.status_code == 200
    data = res.json()

    assert "statistics" in data
    stats = data["statistics"]
    assert stats["total_ledger_events"] >= 6
    assert stats["correct_preventive_success"] > 0
    assert stats["intervention_precision_pct"] > 0.0

    records = data["records"]
    assert len(records) >= 6
    for r in records:
        assert r["counterfactual_outcome_class"] in [
            "CORRECT_PREVENTIVE_SUCCESS", "UNNECESSARY_INTERVENTION",
            "MISSED_BREACH", "INEFFECTIVE_INTERVENTION"
        ]
        assert "forecasted_used_pct" in r
        assert "simulated_used_pct" in r
        assert "observed_used_pct" in r


def test_omega_model_governance_rejection_h4(client):
    """Verify Hypothesis H4: Safety gate REJECTS model with lower MAE but higher decision loss."""
    payload = {
        "candidate_model_name": "DeepAR-Overfitted-v4",
        "candidate_version": "4.0.0",
        "candidate_mae": 1.85,  # Very low MAE
        "candidate_decision_loss": 1420.0,  # Unacceptable decision loss ($1,420 vs $320)
        "candidate_calibration_error": 0.075,
    }
    res = client.post("/api/v1/omega/governance/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["gate_verdict"] == "REJECTED"
    assert data["hard_safety_check_passed"] is False
    assert "DECISION LOSS REGRESSION" in data["verdict_rationale"]


def test_omega_model_governance_promotion_h4(client):
    """Verify Hypothesis H4: Safety gate PROMOTES model that improves operational decision loss."""
    payload = {
        "candidate_model_name": "LightGBM-Conformal-Quantile-v2.2",
        "candidate_version": "2.2.0",
        "candidate_mae": 2.50,
        "candidate_decision_loss": 290.0,  # Lower than baseline $320
        "candidate_calibration_error": 0.022,
    }
    res = client.post("/api/v1/omega/governance/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["gate_verdict"] == "PROMOTED"
    assert data["hard_safety_check_passed"] is True
