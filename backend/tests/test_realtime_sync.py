import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.database import Base, get_db
from app.auth.permissions import seed_roles_and_permissions
from app.auth.security import hash_password
from app.models.entities import Alert, Device, OutboxEvent, Recommendation, Telemetry, User


@pytest.fixture()
def rt_env(tmp_path):
    db_file = tmp_path / "realtime_isolated.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    # Patch SessionLocal used inside endpoints_realtime.py & endpoints_intelligence.py
    import app.api.v1.endpoints_realtime as ep_rt
    import app.api.v1.endpoints_intelligence as ep_intel
    orig_rt_sl = ep_rt.SessionLocal
    orig_intel_sl = ep_intel.SessionLocal
    ep_rt.SessionLocal = SessionLocal
    ep_intel.SessionLocal = SessionLocal

    def _override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    db = SessionLocal()
    seed_roles_and_permissions(db)
    admin = User(
        id="usr-rt-admin",
        username="rt_admin",
        email="rt_admin@aegisstor.local",
        hashed_password=hash_password("AdminPass!2026"),
        role="ADMIN",
        is_active=True,
    )
    op = User(
        id="usr-rt-op",
        username="rt_operator",
        email="rt_op@aegisstor.local",
        hashed_password=hash_password("OpPass!2026"),
        role="OPERATOR",
        is_active=True,
    )
    viewer = User(
        id="usr-rt-view",
        username="rt_viewer",
        email="rt_view@aegisstor.local",
        hashed_password=hash_password("ViewPass!2026"),
        role="VIEWER",
        is_active=True,
    )
    dev = Device(
        id="vol-rt-01",
        name="Realtime Primary NVMe",
        tier="NVME_TIER1",
        media_type="NVMe SSD",
        total_capacity_bytes=2 * (1024 ** 4),
        warning_threshold_pct=80.0,
        critical_threshold_pct=90.0,
        max_acceptable_latency_ms=15.0,
        min_free_reserve_pct=10.0,
        status="HEALTHY",
        workload_profile="OLTP Database",
        version=1,
    )
    db.add_all([admin, op, viewer, dev])
    db.flush()

    base_t = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=85)
    for h in range(80):
        used = int(dev.total_capacity_bytes * (0.50 + h * 0.0025))
        db.add(
            Telemetry(
                device_id=dev.id,
                timestamp=base_t + timedelta(hours=h),
                total_capacity_bytes=dev.total_capacity_bytes,
                used_bytes=used,
                free_bytes=dev.total_capacity_bytes - used,
                utilization_pct=round(used / dev.total_capacity_bytes * 100.0, 2),
                read_iops=3000.0 + h * 10,
                write_iops=1500.0 + h * 5,
                throughput_mb_s=420.0,
                latency_p95_ms=2.2,
                queue_depth=4.0,
                is_synthetic=False,
                source_label="rt_test_seed",
            )
        )
    db.add(
        Alert(
            id="alt-rt-01",
            device_id=dev.id,
            category="CAPACITY",
            severity="WARNING",
            title="Realtime Test Capacity Alert",
            message="Test alert for live sync",
            status="ACTIVE",
        )
    )
    db.add(
        Recommendation(
            id="rec-rt-01",
            device_id=dev.id,
            action_type="TIER_MIGRATION",
            title="Migrate Cold Blocks to Tier-2",
            rationale="Move cold blocks to Tier-2",
            utility_score=85.0,
            estimated_runway_gain_hours=72.0,
            approval_status="PENDING_REVIEW",
            details_json="{}",
        )
    )
    db.commit()
    db.close()

    with TestClient(app) as client:
        yield client, SessionLocal

    app.dependency_overrides.clear()
    ep_rt.SessionLocal = orig_rt_sl
    ep_intel.SessionLocal = orig_intel_sl


def _login(client: TestClient, username: str, password: str):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], {"Authorization": f"Bearer {data['access_token']}"}


def test_realtime_ws_auth_presence_tasks_notifications_and_409_conflict(rt_env):
    client, SessionLocal = rt_env

    # Unauthenticated WS must be rejected before any login cookie exists
    with pytest.raises(Exception):
        with client.websocket_connect("/api/realtime/ws"):
            pass

    adm_tok, adm_hdrs = _login(client, "rt_admin", "AdminPass!2026")
    op_tok, op_hdrs = _login(client, "rt_operator", "OpPass!2026")
    client.cookies.clear()

    # Open simultaneous authenticated WS connections for Admin and Operator
    with client.websocket_connect(f"/api/realtime/ws?token={adm_tok}&route=/admin") as ws_adm:
        adm_hello = ws_adm.receive_json()
        assert adm_hello["event_type"] == "system.connected"
        assert adm_hello["role"] == "ADMIN"

        with client.websocket_connect(f"/api/realtime/ws?token={op_tok}&route=/operator") as ws_op:
            op_hello = ws_op.receive_json()
            assert op_hello["event_type"] == "system.connected"
            assert op_hello["role"] == "OPERATOR"

            # Verify live presence reflects both users
            pres = client.get("/api/v1/realtime/presence", headers=adm_hdrs)
            assert pres.status_code == 200
            usernames = {u["username"] for u in pres.json()["users"]}
            assert {"rt_admin", "rt_operator"}.issubset(usernames)

            # 1. Admin creates a task assigned to Operator -> Operator receives live WS event + persistent notification
            t_res = client.post(
                "/api/v1/tasks",
                headers=adm_hdrs,
                json={
                    "title": "Inspect NVMe Tier-1 growth",
                    "description": "Verify compaction window",
                    "priority": "HIGH",
                    "assigned_to_user_id": "usr-rt-op",
                    "linked_device_id": "vol-rt-01",
                },
            )
            assert t_res.status_code == 201, t_res.text
            task_data = t_res.json()
            assert task_data["version"] == 1

            # Drain WS until task.assigned arrives on Operator WS
            op_events = []
            for _ in range(5):
                ev = ws_op.receive_json()
                op_events.append(ev)
                if ev.get("event_type") == "task.assigned":
                    break
            assert any(e.get("event_type") == "task.assigned" and e.get("resource_id") == task_data["id"] for e in op_events)

            # Persistent notification created for Operator
            notifs = client.get("/api/v1/notifications", headers=op_hdrs)
            assert notifs.status_code == 200
            assert notifs.json()["unread_count"] >= 1
            notif_id = notifs.json()["notifications"][0]["id"]
            assert client.post(f"/api/v1/notifications/{notif_id}/read", headers=op_hdrs).status_code == 200

            # 2. Operator updates task status with expected_version=1 -> version becomes 2
            u_res = client.patch(
                f"/api/v1/tasks/{task_data['id']}",
                headers=op_hdrs,
                json={"status": "IN_PROGRESS", "expected_version": 1},
            )
            assert u_res.status_code == 200
            assert u_res.json()["version"] == 2
            assert u_res.json()["status"] == "IN_PROGRESS"

            # 3. Stale update with expected_version=1 must fail with HTTP 409 Conflict
            stale = client.patch(
                f"/api/v1/tasks/{task_data['id']}",
                headers=adm_hdrs,
                json={"status": "COMPLETED", "expected_version": 1},
            )
            assert stale.status_code == 409
            assert stale.json()["detail"]["code"] == "VERSION_CONFLICT"
            assert stale.json()["detail"]["server_version"] == 2

            # 4. Storage optimistic concurrency 409 check
            s1 = client.put(
                "/api/v1/storage/vol-rt-01",
                headers=op_hdrs,
                json={"environment_location": "DC-East-2", "expected_version": 1},
            )
            assert s1.status_code == 200
            assert s1.json()["version"] == 2
            s_stale = client.put(
                "/api/v1/storage/vol-rt-01",
                headers=adm_hdrs,
                json={"environment_location": "DC-West-9", "expected_version": 1},
            )
            assert s_stale.status_code == 409

            # 5. Cursor replay endpoint returns committed outbox events after seq 0
            replay = client.get("/api/v1/realtime/events?since_seq=0", headers=op_hdrs)
            assert replay.status_code == 200
            ev_types = [e["event_type"] for e in replay.json()["events"]]
            assert "task.assigned" in ev_types
            assert "task.updated" in ev_types
            assert "storage.updated" in ev_types

            # 6. Admin deactivates Operator -> active WS connection receives termination frame
            deact = client.patch(
                "/api/v1/users/usr-rt-op",
                headers=adm_hdrs,
                json={"is_active": False},
            )
            assert deact.status_code == 200
            term_ev = None
            for _ in range(5):
                ev = ws_op.receive_json()
                if ev.get("event_type") == "auth.connection_terminated":
                    term_ev = ev
                    break
            assert term_ev is not None
            assert term_ev["reason"] == "admin_account_change"


def test_async_ml_training_emits_real_stages_and_outbox(rt_env):
    client, _ = rt_env
    _, adm_hdrs = _login(client, "rt_admin", "AdminPass!2026")
    _, op_hdrs = _login(client, "rt_operator", "OpPass!2026")

    r = client.post("/api/v1/v2/models/train-async/vol-rt-01", headers=op_hdrs)
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]

    job = client.get(f"/api/v1/jobs/{job_id}", headers=adm_hdrs)
    assert job.status_code == 200
    data = job.json()
    assert data["status"] in {"COMPLETED", "QUEUED", "RUNNING"}, f"Job failed: {data.get('error_message')} | {data}"

    replay = client.get("/api/v1/realtime/events?since_seq=0", headers=adm_hdrs).json()
    stage_events = [
        e["relevant_safe_payload"].get("stage")
        for e in replay["events"]
        if e["event_type"] in {"model.training_queued", "model.training_stage", "model.training_completed"}
    ]
    assert "QUEUED" in stage_events
    assert "VALIDATING_DATA" in stage_events
    assert "PREPARING_FEATURES" in stage_events
    assert "TRAINING" in stage_events
    assert "COMPLETED" in stage_events
