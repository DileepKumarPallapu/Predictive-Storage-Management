import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.services.replay_service import replay_engine
from app.collector.host_collector import HostStorageCollector, PROVENANCE_LIVE, PROVENANCE_SYNTHETIC


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_operating_mode_switching(client):
    """Rule 3: Switching operating mode changes the real backend pipeline."""
    # 1. Switch to demo mode
    res = client.post("/api/v1/system/mode", json={"mode": "demo"})
    assert res.status_code == 200
    assert res.json()["mode"] == "demo"
    assert settings.OPERATING_MODE == "demo"

    ov = client.get("/api/v1/overview").json()
    assert ov["is_synthetic"] is True
    assert ov["data_mode_label"] == "SYNTHETIC DEMO DATA"

    # 2. Switch to replay mode
    res = client.post("/api/v1/system/mode", json={"mode": "replay"})
    assert res.status_code == 200
    assert res.json()["mode"] == "replay"
    assert settings.OPERATING_MODE == "replay"

    ov = client.get("/api/v1/overview").json()
    assert ov["is_synthetic"] is False
    assert ov["data_mode_label"] == "CHRONOLOGICAL REPLAY TRACE"

    # 3. Switch to live mode
    res = client.post("/api/v1/system/mode", json={"mode": "live"})
    assert res.status_code == 200
    assert res.json()["mode"] == "live"
    assert settings.OPERATING_MODE == "live"
    assert res.json()["diagnostics"]["native_host_active"] is True

    ov = client.get("/api/v1/overview").json()
    assert ov["is_synthetic"] is False
    assert ov["data_mode_label"] == "LIVE PASSIVE HOST"

    # Reset back to demo for clean state
    client.post("/api/v1/system/mode", json={"mode": "demo"})


def test_replay_pipeline_timeline_controls(client):
    """Rule 2.B: Replay pipeline timeline controls advance cursor and prevent future data leakage."""
    # Ensure replay mode is active
    client.post("/api/v1/system/mode", json={"mode": "replay"})
    replay_engine.load_trace("snia_enterprise_block_trace.csv")

    # 1. Check initial status
    status = client.get("/api/v1/replay/status").json()
    assert status["has_trace"] is True
    assert status["active_trace_id"] == "snia_enterprise_block_trace.csv"
    assert status["total_frames"] == 168

    # 2. Seek to frame 40
    res = client.post("/api/v1/replay/control", json={"action": "seek", "value": 40})
    assert res.status_code == 200
    assert res.json()["current_frame_index"] == 40
    assert "2026-03-02" in res.json()["current_timestamp"]

    # Check telemetry history length equals exactly 41 samples (frame 0 to 40)
    tel = client.get("/api/v1/devices/vol-replay-nvme/telemetry?metric=used_bytes").json()
    assert len(tel["timestamps"]) == 41
    assert len(tel["values"]) == 41

    # 3. Step forward by 10 frames
    res = client.post("/api/v1/replay/control", json={"action": "step", "value": 10})
    assert res.status_code == 200
    assert res.json()["current_frame_index"] == 50

    tel50 = client.get("/api/v1/devices/vol-replay-nvme/telemetry?metric=used_bytes").json()
    assert len(tel50["timestamps"]) == 51

    # 4. Set playback speed
    res = client.post("/api/v1/replay/control", json={"action": "speed", "value": 5.0})
    assert res.status_code == 200
    assert res.json()["playback_speed"] == 5.0

    # Reset
    replay_engine.seek(0)
    client.post("/api/v1/system/mode", json={"mode": "demo"})


def test_replay_empty_state_zero_fallback(client):
    """Rule 2.B: Zero silent fallback to synthetic data when no trace is loaded."""
    client.post("/api/v1/system/mode", json={"mode": "replay"})
    replay_engine.unload_trace()

    status = client.get("/api/v1/replay/status").json()
    assert status["has_trace"] is False

    # Overview must return empty/zeroed state, NOT synthetic demo data
    ov = client.get("/api/v1/overview").json()
    assert ov["total_capacity_bytes"] == 0
    assert ov["monitored_device_count"] == 0
    assert ov["data_mode_label"] == "CHRONOLOGICAL REPLAY TRACE"
    assert ov["is_synthetic"] is False

    # Devices list must be empty
    devs = client.get("/api/v1/devices").json()
    assert len(devs) == 0

    # Reload trace and reset mode
    replay_engine.load_trace("snia_enterprise_block_trace.csv")
    client.post("/api/v1/system/mode", json={"mode": "demo"})


def test_live_mode_real_host_telemetry(client):
    """Rule 2.C: Live read-only mode inspects actual host filesystem without synthetic generation."""
    client.post("/api/v1/system/mode", json={"mode": "live"})

    # Overview must query real host partitions
    ov = client.get("/api/v1/overview").json()
    assert ov["data_mode_label"] == "LIVE PASSIVE HOST"
    assert ov["is_synthetic"] is False
    assert ov["monitored_device_count"] >= 1
    assert ov["total_capacity_bytes"] > 0

    # Devices must ONLY contain host partitions (e.g. host-vol-C)
    devs = client.get("/api/v1/devices").json()
    assert len(devs) >= 1
    for d in devs:
        assert d["tier"] == "HOST_LOCAL"
        assert d["id"].startswith("host-vol")

    # Verify device telemetry returns valid timestamps and units
    host_dev_id = devs[0]["id"]
    tel = client.get(f"/api/v1/devices/{host_dev_id}/telemetry?metric=used_bytes").json()
    assert tel["device_id"] == host_dev_id
    assert tel["units"] == "Bytes"
    assert len(tel["values"]) > 0

    # Reset
    client.post("/api/v1/system/mode", json={"mode": "demo"})


def test_provenance_integrity():
    """Rule 1: Synthetic data is strictly forbidden from claiming LIVE provenance."""
    # Attempt to label synthetic sample as LIVE must fail validation
    invalid_sample = {
        "timestamp": "2026-10-22T10:00:00Z",
        "provenance": PROVENANCE_LIVE,
        "is_synthetic": True,
        "total_capacity_bytes": 1000,
        "used_bytes": 500
    }
    result = HostStorageCollector.validate_metric_sample(invalid_sample)
    assert result["is_valid"] is False
    assert any("PROVENANCE VIOLATION" in err for err in result["validation_errors"])
