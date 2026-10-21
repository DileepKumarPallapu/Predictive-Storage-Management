import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.entities import JurassicScenario, Device
from app.services.jurassic.scenario_engine import ScenarioEngine
from app.services.jurassic.chaos_engine import ChaosEngine
from app.services.jurassic.robustness_engine import RobustnessEngine
from app.services.jurassic.fallback_engine import FallbackEngine

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_jurassic_command_center_endpoint(client):
    """Verify Command Center metrics are calculated directly from stored records."""
    res = client.get("/api/v1/jurassic/command-center")
    assert res.status_code == 200
    data = res.json()

    assert "summary" in data
    summary = data["summary"]
    assert summary["total_experiments_run"] >= 3
    assert summary["scenarios_tested"] >= 3
    assert summary["scenarios_available"] >= 6
    assert summary["mean_resilience_index"] > 0.0
    assert summary["fault_injections_contained"] >= 3

    assert "recent_experiments" in data
    assert len(data["recent_experiments"]) >= 3


def test_jurassic_scenarios_listing_and_presets(client):
    """Verify preset scenario catalog across disturbance families."""
    res = client.get("/api/v1/jurassic/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 6

    families = {s["scenario_family"] for s in scenarios}
    assert "CAPACITY_DISTURBANCE" in families
    assert "PERFORMANCE_DISTURBANCE" in families
    assert "TEMPORAL_DISTURBANCE" in families
    assert "TELEMETRY_DISTURBANCE" in families
    assert "COMPOUND_DISTURBANCE" in families


def test_jurassic_deterministic_scenario_generation():
    """Verify reproducibility: identical seed and inputs produce byte-for-byte identical output."""
    scenario = JurassicScenario(
        id="scenario-test-repro",
        name="Repro Test Scenario",
        scenario_family="CAPACITY_DISTURBANCE",
        target_device_id="vol-nvme-tier1-db",
        seed=777,
        simulation_duration_hours=48,
        initial_capacity_pct=70.0,
        capacity_growth_gb_day=50.0,
        burst_events_json='[{"hour": 24, "size_gb": 100.0, "reason": "Test burst"}]',
        read_iops_base=10000.0,
        write_iops_base=8000.0,
        latency_noise_ms=0.5
    )
    device = Device(
        id="vol-nvme-tier1-db",
        name="Test NVMe",
        tier="NVME_TIER1",
        media_type="NVMe SSD",
        total_capacity_bytes=10 * 1024 * 1024 * 1024 * 1024
    )

    run_1 = ScenarioEngine.generate_scenario_telemetry(scenario, device)
    run_2 = ScenarioEngine.generate_scenario_telemetry(scenario, device)

    assert len(run_1) == 48
    assert len(run_2) == 48

    for i in range(48):
        assert run_1[i]["used_bytes"] == run_2[i]["used_bytes"]
        assert run_1[i]["latency_p95_ms"] == run_2[i]["latency_p95_ms"]
        assert run_1[i]["used_bytes"] >= 0
        assert run_1[i]["free_bytes"] >= 0


def test_jurassic_create_custom_scenario(client):
    """Verify authorized scenario designer can save a custom scenario configuration."""
    payload = {
        "name": "Custom Chaos Stress Test",
        "scenario_family": "COMPOUND_DISTURBANCE",
        "description": "User designed compound stress test",
        "target_device_id": "vol-nvme-tier1-db",
        "seed": 999,
        "simulation_duration_hours": 72,
        "initial_capacity_pct": 75.0,
        "capacity_growth_gb_day": 100.0,
        "burst_events": [{"hour": 12, "size_gb": 200.0, "reason": "Custom burst"}],
        "read_iops_base": 12000.0,
        "write_iops_base": 9000.0,
        "latency_noise_ms": 1.0,
        "telemetry_drop_rate": 0.10,
        "telemetry_delay_s": 0,
        "chaos_faults": [{"hour": 24, "duration_hours": 6, "fault_type": "TELEMETRY_PAUSE"}]
    }
    res = client.post("/api/v1/jurassic/scenarios", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert data["status"] == "CREATED"


def test_jurassic_execute_experiment_run(client):
    """Verify full resilience experiment execution pipeline and output scorecard."""
    payload = {
        "scenario_id": "scenario-jurassic-cap-burst-01",
        "target_device_id": "vol-nvme-tier1-db"
    }
    res = client.post("/api/v1/jurassic/experiments/run", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert "experiment_id" in data
    assert data["status"] == "COMPLETED"
    assert "resilience_score" in data
    assert "rating_tier" in data
    assert "final_fallback_state" in data
    assert "forensics" in data
    assert "scorecard" in data
    assert "dimensions" in data["scorecard"]


def test_jurassic_chaos_injection_safety():
    """Verify logical faults are contained with zero physical host mutations."""
    # Test Telemetry Pause
    r_tel = ChaosEngine.evaluate_injected_fault(
        fault_type="TELEMETRY_PAUSE",
        target_module="INGESTION_COLLECTOR",
        current_state={}
    )
    assert r_tel["test_passed"] is True
    assert r_tel["required_fallback_state"] == "STATE_2_DEGRADED_EVIDENCE"
    assert r_tel["physical_mutation_prevented"] is True

    # Test Inference Service Unavailable
    r_inf = ChaosEngine.evaluate_injected_fault(
        fault_type="INFERENCE_SERVICE_UNAVAILABLE",
        target_module="ML_INFERENCE_SERVICE",
        current_state={}
    )
    assert r_inf["test_passed"] is True
    assert r_inf["required_fallback_state"] == "STATE_5_SERVICE_UNAVAILABLE"

    # Test Infeasible Action Attempt
    r_act = ChaosEngine.evaluate_injected_fault(
        fault_type="INFEASIBLE_ACTION_ATTEMPT",
        target_module="ACTION_PLANNER",
        current_state={}
    )
    assert r_act["test_passed"] is True
    assert r_act["required_fallback_state"] == "STATE_4_PLANNING_UNSAFE"


def test_jurassic_distribution_shift_and_interval_stress():
    """Verify Page-Hinkley drift detection and prediction interval stress testing."""
    # Stable data
    base = [70.0 + (i % 5) for i in range(50)]
    obs_stable = [70.0 + (i % 5) for i in range(50)]
    shift_stable = RobustnessEngine.evaluate_distribution_shift(base, obs_stable)
    assert shift_stable["drift_status"] == "NO_DETECTED_SHIFT"
    assert shift_stable["shift_detected"] is False

    # Shifted burst data
    obs_shifted = [90.0 + (i % 8) for i in range(50)]
    shift_burst = RobustnessEngine.evaluate_distribution_shift(base, obs_shifted)
    assert shift_burst["drift_status"] == "CONFIRMED_EVALUATION_MISMATCH"
    assert shift_burst["shift_detected"] is True

    # Interval stress test where predictions fail to cover shifted values
    y_true = [95.0] * 50
    q10 = [70.0] * 50
    q90 = [80.0] * 50  # Upper bound breached
    interval_test = RobustnessEngine.stress_test_prediction_intervals(y_true, q10, q90)
    assert interval_test["empirical_coverage"] == 0.0
    assert interval_test["calibration_passed"] is False
    assert interval_test["error_attribution"] == "WORKLOAD_DISTRIBUTION_SHIFT"


def test_jurassic_fallback_states_endpoint(client):
    """Verify definitions and entry conditions for all 5 safe fallback states."""
    res = client.get("/api/v1/jurassic/fallback-states")
    assert res.status_code == 200
    states = res.json()

    assert "STATE_1_HEALTHY_EVIDENCE" in states
    assert "STATE_2_DEGRADED_EVIDENCE" in states
    assert "STATE_3_MODEL_UNRELIABLE" in states
    assert "STATE_4_PLANNING_UNSAFE" in states
    assert "STATE_5_SERVICE_UNAVAILABLE" in states

    for s_key, s_val in states.items():
        assert "permitted_operations" in s_val
        assert "prohibited_actions" in s_val
        assert "recovery_conditions" in s_val


def test_jurassic_report_download_markdown_and_csv(client):
    """Verify Markdown and CSV resilience report generation."""
    # Run an experiment to ensure an ID exists
    run_res = client.post("/api/v1/jurassic/experiments/run", json={"scenario_id": "scenario-jurassic-cap-burst-01"})
    exp_id = run_res.json()["experiment_id"]

    # Download Markdown
    md_res = client.get(f"/api/v1/jurassic/experiments/{exp_id}/report?format=markdown")
    assert md_res.status_code == 200
    assert "text/markdown" in md_res.headers["content-type"]
    assert "AEGISSTOR JURASSIC RESILIENCE EVALUATION REPORT" in md_res.text
    assert "Scorecard" in md_res.text

    # Download CSV
    csv_res = client.get(f"/api/v1/jurassic/experiments/{exp_id}/report?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "step_hour" in csv_res.text
    assert "used_bytes" in csv_res.text
