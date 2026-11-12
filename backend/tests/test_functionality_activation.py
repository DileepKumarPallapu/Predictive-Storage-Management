import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from tests.auth_helper import attach_admin_auth

@pytest.fixture
def client():
    client_instance = attach_admin_auth(TestClient(app))
    settings.OPERATING_MODE = "demo"
    yield client_instance
    settings.OPERATING_MODE = "demo"

def test_operating_mode_lifecycle(client):
    """Test switching across Demo, Replay, and Live operating modes with provenance verification."""
    # 1. Switch to demo mode
    res = client.post("/api/v1/system/mode", json={"mode": "demo"})
    assert res.status_code == 200
    assert res.json()["mode"] == "demo"
    assert settings.OPERATING_MODE == "demo"

    # Verify overview in demo mode
    ov_demo = client.get("/api/v1/overview").json()
    assert ov_demo["data_mode_label"] == "SYNTHETIC DEMO DATA"
    assert ov_demo["is_synthetic"] is True

    # 2. Switch to replay mode
    res = client.post("/api/v1/system/mode", json={"mode": "replay"})
    assert res.status_code == 200
    assert res.json()["mode"] == "replay"
    assert settings.OPERATING_MODE == "replay"

    # Verify overview in replay mode
    ov_replay = client.get("/api/v1/overview").json()
    assert ov_replay["data_mode_label"] == "CHRONOLOGICAL REPLAY TRACE"
    assert ov_replay["is_synthetic"] is False

    # 3. Switch to live mode
    res = client.post("/api/v1/system/mode", json={"mode": "live"})
    assert res.status_code == 200
    assert res.json()["mode"] == "live"
    assert settings.OPERATING_MODE == "live"
    assert "diagnostics" in res.json()
    assert res.json()["diagnostics"]["native_host_active"] is True

    # Verify overview in live mode
    ov_live = client.get("/api/v1/overview").json()
    assert ov_live["data_mode_label"] == "LIVE PASSIVE HOST"
    assert ov_live["is_synthetic"] is False
    assert ov_live["monitored_device_count"] >= 1

    # Verify devices in live mode include host local partition
    devices_live = client.get("/api/v1/devices").json()
    host_devs = [d for d in devices_live if d["tier"] == "HOST_LOCAL"]
    assert len(host_devs) >= 1
    assert host_devs[0]["id"].startswith("host-vol")

    # 4. Revert cleanly to demo mode
    res = client.post("/api/v1/system/mode", json={"mode": "demo"})
    assert res.status_code == 200
    assert settings.OPERATING_MODE == "demo"

def test_invalid_mode_rejected(client):
    """Verify invalid mode selection is rejected cleanly."""
    res = client.post("/api/v1/system/mode", json={"mode": "unsupported_mode_xyz"})
    assert "error" in res.json()

def test_live_host_storage_read_only_guarantee(client):
    """Verify live host storage returns valid non-synthetic capacity."""
    res = client.get("/api/v1/telemetry/live-host")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["provenance"] == "LIVE"
    assert data["is_synthetic"] is False
    assert data["read_only"] is True
    assert len(data["partitions"]) >= 1
    part = data["partitions"][0]
    assert part["total_capacity_bytes"] > 0
    assert part["used_bytes"] > 0
    assert 0 <= part["utilization_pct"] <= 100
