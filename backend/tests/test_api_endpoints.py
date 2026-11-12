import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.auth_helper import attach_admin_auth

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield attach_admin_auth(c)

def test_api_health(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["mode"] == "demo"

def test_api_overview(client):
    res = client.get("/api/v1/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_capacity_bytes" in data
    assert "total_used_bytes" in data
    assert "capacity_utilization_pct" in data
    assert "estimated_reserve_runway_hours" in data
    assert "monitored_device_count" in data
    assert data["monitored_device_count"] >= 4
    assert data["data_mode_label"] == "SYNTHETIC DEMO DATA"
    assert "risk_timeline" in data
    assert len(data["risk_timeline"]) > 0

def test_api_devices_list(client):
    res = client.get("/api/v1/devices")
    assert res.status_code == 200
    devices = res.json()
    assert len(devices) >= 4
    dev_ids = [d["id"] for d in devices]
    assert "vol-nvme-tier1-db" in dev_ids
    assert "vol-sas-tier2-analytics" in dev_ids

def test_api_telemetry_query(client):
    res = client.get("/api/v1/devices/vol-nvme-tier1-db/telemetry?metric=used_bytes&hours=48")
    assert res.status_code == 200
    data = res.json()
    assert data["device_id"] == "vol-nvme-tier1-db"
    assert data["is_synthetic"] is True
    assert len(data["timestamps"]) > 0
    assert len(data["values"]) == len(data["timestamps"])

def test_api_forecasts(client):
    res = client.get("/api/v1/devices/vol-nvme-tier1-db/forecasts?target_metric=used_bytes&model_type=lightgbm_quantile&horizon_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert len(data["q50"]) == 24
    assert len(data["q10"]) == 24
    assert len(data["q90"]) == 24
    assert data["hard_constraint_value"] is not None

def test_api_risks(client):
    res = client.get("/api/v1/devices/vol-nvme-tier1-db/risks")
    assert res.status_code == 200
    data = res.json()
    assert "runway_hours_estimate" in data
    assert "risk_level" in data
    assert len(data["risk_contributors"]) > 0

def test_api_scenarios_run(client):
    payload = {
        "device_id": "vol-nvme-tier1-db",
        "name": "Test Cold Tiering Simulation",
        "action_type": "TIER_COLD_DATA",
        "parameters": {"data_volume_gb": 1000.0, "migration_rate_mb_s": 150.0}
    }
    res = client.post("/api/v1/scenarios", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["action_type"] == "TIER_COLD_DATA"
    assert data["is_simulated_estimate"] is True
    assert "baseline_q50" in data
    assert "counterfactual_q50" in data

def test_api_recommendations_and_approval(client):
    res = client.get("/api/v1/devices/vol-nvme-tier1-db/recommendations")
    assert res.status_code == 200
    recs = res.json()
    assert len(recs) > 0
    top_rec = recs[0]
    rec_id = top_rec["id"]

    # Test shadow approval
    appr_res = client.post(f"/api/v1/recommendations/{rec_id}/approve", json={"notes": "Approved dry run in test"})
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED_SHADOW"

def test_api_alerts_and_acknowledge(client):
    res = client.get("/api/v1/alerts")
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0
    first_alert = alerts[0]

    ack_res = client.post(f"/api/v1/alerts/{first_alert['id']}/acknowledge")
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "ACKNOWLEDGED"

def test_api_experiments(client):
    res = client.get("/api/v1/experiments")
    assert res.status_code == 200
    exps = res.json()
    assert len(exps) > 0

def test_api_reliability(client):
    res = client.get("/api/v1/models/reliability")
    assert res.status_code == 200
    data = res.json()
    assert "overall_interval_coverage" in data
    assert data["target_nominal_coverage"] == 0.80

def test_api_audit_log(client):
    res = client.get("/api/v1/audit")
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) > 0
