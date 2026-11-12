import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.capacity_runway_engine import CapacityRunwayEngine
from app.services.performance_risk_engine import PerformanceRiskEngine
from app.services.action_planner import ActionPlannerService
from app.simulator.digital_twin import DigitalTwinSimulator
from app.collector.synthetic import SyntheticGenerator
from tests.auth_helper import attach_admin_auth

client = attach_admin_auth(TestClient(app))

# -------------------------------------------------------------------
# 1. Capacity Runway Engine Tests
# -------------------------------------------------------------------
def test_capacity_runway_stable_positive_growth():
    """Verify runway estimation on steady linear growth."""
    gen = SyntheticGenerator(seed=42)
    dev_cfg = SyntheticGenerator.DEVICES_CONFIG[0]  # NVMe
    telemetry = gen.generate_device_telemetry(dev_cfg, hours_history=168)
    
    total_bytes = dev_cfg["total_capacity_bytes"]
    res = CapacityRunwayEngine.evaluate_runway(
        device_id="vol-nvme-tier1-db",
        total_capacity_bytes=total_bytes,
        telemetry_history=telemetry,
        critical_threshold_pct=90.0,
        warning_threshold_pct=80.0
    )
    assert res.current_utilization_pct > 60.0
    assert res.estimated_runway_hours > 0.0
    assert res.is_runway_reliable is True
    assert res.growth_rate_daily_gb > 0.0
    assert res.sensitivity_optimistic_hours >= res.estimated_runway_hours
    assert res.sensitivity_pessimistic_hours <= res.estimated_runway_hours

def test_capacity_runway_zero_growth():
    """Verify zero growth handling returns indefinitely safe status."""
    now = datetime.now(timezone.utc)
    flat_telemetry = [
        {"timestamp": now - timedelta(hours=i), "used_bytes": 5000000000000}
        for i in range(48, -1, -1)
    ]
    res = CapacityRunwayEngine.evaluate_runway(
        device_id="flat-vol",
        total_capacity_bytes=10000000000000,
        telemetry_history=flat_telemetry
    )
    assert res.breach_status == "ZERO_OR_NEGATIVE_GROWTH"
    assert res.estimated_runway_hours == 9999.0
    assert res.is_runway_reliable is False

def test_capacity_runway_negative_growth():
    """Verify shrinking capacity (evacuation) returns non-positive growth status."""
    now = datetime.now(timezone.utc)
    shrinking = [
        {"timestamp": now - timedelta(hours=i), "used_bytes": 7000000000000 + (i * 1000000000)}
        for i in range(48, -1, -1)
    ]
    res = CapacityRunwayEngine.evaluate_runway(
        device_id="shrinking-vol",
        total_capacity_bytes=10000000000000,
        telemetry_history=shrinking
    )
    assert res.breach_status == "ZERO_OR_NEGATIVE_GROWTH"

def test_capacity_runway_already_breached():
    """Verify instant breach detection when already over limit."""
    now = datetime.now(timezone.utc)
    breached = [
        {"timestamp": now - timedelta(hours=i), "used_bytes": 9500000000000}
        for i in range(12, -1, -1)
    ]
    res = CapacityRunwayEngine.evaluate_runway(
        device_id="breached-vol",
        total_capacity_bytes=10000000000000,
        telemetry_history=breached,
        critical_threshold_pct=90.0
    )
    assert res.breach_status == "ALREADY_BREACHED"
    assert res.estimated_runway_hours == 0.0

def test_capacity_runway_stale_observations():
    """Verify stale data flags unreliability when telemetry stops updating."""
    old_time = datetime.now(timezone.utc) - timedelta(hours=8)
    stale_records = [
        {"timestamp": old_time - timedelta(hours=i), "used_bytes": 6000000000000}
        for i in range(24, -1, -1)
    ]
    res = CapacityRunwayEngine.evaluate_runway(
        device_id="stale-vol",
        total_capacity_bytes=10000000000000,
        telemetry_history=stale_records
    )
    assert res.is_runway_reliable is False
    assert "stale" in res.unreliability_reason.lower()

# -------------------------------------------------------------------
# 2. Performance Risk Engine Tests
# -------------------------------------------------------------------
def test_performance_risk_tail_latency_breach():
    """Verify performance risk engine flags SLA violations when latency exceeds cap."""
    now = datetime.now(timezone.utc)
    high_lat_history = [{
        "timestamp": now,
        "latency_p95_ms": 32.5,
        "read_iops": 15000,
        "write_iops": 12000,
        "throughput_mb_s": 850,
        "queue_depth": 9.5,
        "utilization_pct": 75.0
    }]
    meta = {
        "tier": "NVME_TIER1",
        "max_acceptable_latency_ms": 20.0,
        "max_acceptable_queue_depth": 8.0
    }
    perf = PerformanceRiskEngine.evaluate_performance_risk(
        device_id="vol-nvme-tier1-db",
        device_metadata=meta,
        telemetry_history=high_lat_history
    )
    assert perf.latency_risk_level == "CRITICAL"
    assert perf.queue_saturation_risk == "CRITICAL_SATURATION"

def test_performance_risk_capacity_coupling():
    """Verify flash controller GC latency inflation when utilization > 80%."""
    now = datetime.now(timezone.utc)
    full_history = [{
        "timestamp": now,
        "latency_p95_ms": 1.8,
        "read_iops": 5000,
        "write_iops": 4000,
        "throughput_mb_s": 300,
        "queue_depth": 2.0,
        "utilization_pct": 92.0  # > 80% capacity trigger
    }]
    meta = {"tier": "NVME_TIER1", "max_acceptable_latency_ms": 20.0}
    perf = PerformanceRiskEngine.evaluate_performance_risk(
        device_id="vol-nvme-tier1-db",
        device_metadata=meta,
        telemetry_history=full_history
    )
    assert perf.capacity_latency_coupling_penalty_ms > 0.0
    assert "TRIM/GC" in perf.coupling_explanation

def test_performance_risk_missing_tail_metric():
    """Verify engine handles zero/missing latency readings without crash."""
    now = datetime.now(timezone.utc)
    missing_lat = [{
        "timestamp": now,
        "latency_p95_ms": 0.0,
        "queue_depth": 3.0,
        "utilization_pct": 50.0
    }]
    meta = {"tier": "SAS_TIER2", "max_acceptable_latency_ms": 25.0}
    perf = PerformanceRiskEngine.evaluate_performance_risk(
        device_id="vol-sas",
        device_metadata=meta,
        telemetry_history=missing_lat
    )
    assert perf.current_latency_p95_ms > 0.0  # Proxy estimated

# -------------------------------------------------------------------
# 3. Digital Twin Simulator Tests
# -------------------------------------------------------------------
def test_simulator_determinism():
    """Verify simulator generates strictly identical outcomes for identical seed."""
    now = datetime.now(timezone.utc)
    meta = {"total_capacity_bytes": 10e12, "critical_threshold_pct": 90.0, "max_acceptable_latency_ms": 20.0}
    base = {
        "timestamps": [now + timedelta(hours=h) for h in range(1, 25)],
        "q50": [7e12 + (h * 50e9) for h in range(1, 25)]
    }
    sim1 = DigitalTwinSimulator.simulate_scenario(
        device_id="vol-1", device_metadata=meta, base_forecast=base, action_type="TIER_COLD_DATA", seed=99
    )
    sim2 = DigitalTwinSimulator.simulate_scenario(
        device_id="vol-1", device_metadata=meta, base_forecast=base, action_type="TIER_COLD_DATA", seed=99
    )
    assert sim1["counterfactual_q50"] == sim2["counterfactual_q50"]
    assert sim1["duration_hours"] == sim2["duration_hours"]
    assert sim1["overhead_io_penalty_pct"] == sim2["overhead_io_penalty_pct"]

def test_simulator_custom_scenario_validation():
    """Verify custom scenario bounds validation."""
    meta = {"total_capacity_bytes": 10e12, "critical_threshold_pct": 90.0}
    base = {"timestamps": [], "q50": [5e12, 5.1e12]}
    out = DigitalTwinSimulator.simulate_scenario(
        device_id="vol-1",
        device_metadata=meta,
        base_forecast=base,
        action_type="CUSTOM_SCENARIO",
        parameters={"capacity_delta_gb": -500.0, "duration_hours": 4.0, "io_overhead_pct": 10.0}
    )
    assert out["action_type"] == "CUSTOM_SCENARIO"
    assert out["duration_hours"] == 4.0
    assert out["data_movement_gb"] == 500.0

def test_simulator_invalid_action_rejected():
    """Verify invalid scenario types raise ValueError."""
    meta = {"total_capacity_bytes": 10e12}
    with pytest.raises(ValueError) as exc:
        DigitalTwinSimulator.simulate_scenario(
            device_id="vol-1", device_metadata=meta, base_forecast={}, action_type="UNSUPPORTED_ACTION"
        )
    assert "Unsupported scenario type" in str(exc.value)

# -------------------------------------------------------------------
# 4. Lead-Time-Aware Action Planner Tests
# -------------------------------------------------------------------
def test_action_planner_disqualifies_too_late_action():
    """Verify actions taking longer than time to breach are rejected."""
    meta = {"total_capacity_bytes": 10e12, "critical_threshold_pct": 90.0, "max_acceptable_latency_ms": 20.0}
    # Time to breach is only 1.0 hour!
    runway = {"estimated_runway_hours": 1.0, "current_used_bytes": 8.9e12}
    perf = {"current_latency_p95_ms": 2.0}
    
    plan = ActionPlannerService.evaluate_and_plan(
        device_id="vol-imminent",
        device_metadata=meta,
        runway_result=runway,
        perf_result=perf
    )
    # Actions like expansion (2.0h) or tiering (3.0h) must be rejected because duration > breach time!
    rejections = [r["feasibility"] for r in plan["rejected_candidates"]]
    assert "INFEASIBLE_LEAD_TIME" in rejections

def test_action_planner_all_infeasible_fallback():
    """Verify fallback to manual review when all automated actions violate safety."""
    meta = {"total_capacity_bytes": 10e12, "critical_threshold_pct": 90.0, "max_acceptable_latency_ms": 1.5}
    # Imminent breach (0.1h) + ultra low latency SLA (1.5ms) causes all actions to fail
    runway = {"estimated_runway_hours": 0.1, "current_used_bytes": 8.99e12}
    perf = {"current_latency_p95_ms": 2.0}  # Already over SLA
    
    plan = ActionPlannerService.evaluate_and_plan(
        device_id="vol-crisis",
        device_metadata=meta,
        runway_result=runway,
        perf_result=perf
    )
    assert plan["recommendation_status"] == "NO_SAFE_AUTOMATED_RECOMMENDATION"
    assert "MANUAL REVIEW REQUIRED" in plan["recommendation_message"]

# -------------------------------------------------------------------
# 5. API Endpoints Integration Tests
# -------------------------------------------------------------------
def test_api_reserve_runway_endpoint():
    """Verify GET /api/v1/devices/{id}/reserve-runway."""
    resp = client.get("/api/v1/devices/vol-nvme-tier1-db/reserve-runway")
    assert resp.status_code == 200
    data = resp.json()
    assert "estimated_runway_hours" in data
    assert "sensitivity_optimistic_hours" in data
    assert "sensitivity_pessimistic_hours" in data
    assert "breach_status" in data

def test_api_risk_assessment_endpoint():
    """Verify GET /api/v1/devices/{id}/risk-assessment."""
    resp = client.get("/api/v1/devices/vol-nvme-tier1-db/risk-assessment")
    assert resp.status_code == 200
    data = resp.json()
    assert "capacity_runway" in data
    assert "performance_risk" in data
    assert "overall_resilience_status" in data

def test_api_planning_evaluate_endpoint():
    """Verify POST /api/v1/planning/evaluate."""
    resp = client.post("/api/v1/planning/evaluate", json={"device_id": "vol-nvme-tier1-db"})
    assert resp.status_code == 200
    data = resp.json()
    assert "recommendation_status" in data
    assert "feasible_candidates" in data
    assert "rejected_candidates" in data
    assert data["physical_mutations_allowed"] is False

def test_api_scenarios_lifecycle():
    """Verify scenarios listing, execution, and result retrieval."""
    # 1. Create scenario
    create_resp = client.post("/api/v1/scenarios", json={
        "device_id": "vol-nvme-tier1-db",
        "name": "Integration Test Expansion",
        "action_type": "EXPAND_CAPACITY",
        "parameters": {"added_capacity_gb": 1000.0, "provisioning_lead_hours": 1.0}
    })
    assert create_resp.status_code == 200
    sc_id = create_resp.json()["scenario_id"]

    # 2. Get scenario definition
    get_resp = client.get(f"/api/v1/scenarios/{sc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Integration Test Expansion"

    # 3. Get scenario results
    res_resp = client.get(f"/api/v1/scenarios/{sc_id}/results")
    assert res_resp.status_code == 200
    assert "trajectory" in res_resp.json()

    # 4. Rerun scenario
    rerun_resp = client.post(f"/api/v1/scenarios/{sc_id}/run?seed=123")
    assert rerun_resp.status_code == 200
    assert rerun_resp.json()["is_simulated_estimate"] is True
