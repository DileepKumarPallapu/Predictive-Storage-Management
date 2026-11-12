import os
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.auth_helper import attach_admin_auth


@pytest.fixture(scope="module")
def admin_client():
    os.environ["AEGISSTOR_ALLOW_DEV_SEED"] = "true"
    with TestClient(app) as c:
        yield attach_admin_auth(c)


def _login_headers(client: TestClient, username: str, password: str) -> dict:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_sprint1_connector_capability_rbac_and_plaintext_guard(admin_client):
    op_headers = _login_headers(admin_client, "operator", "AegisOperator!2026")
    vw_headers = _login_headers(admin_client, "viewer", "AegisViewer!2026")

    # Plain-text credential rejected
    bad_cred = admin_client.post(
        "/api/v1/control-plane/connectors",
        json={"name": "Bad Conn", "provider": "LINUX_STORAGE", "credential_ref": "my-raw-password-123"},
    )
    assert bad_cred.status_code == 422

    # Operator cannot register connector
    op_reg = admin_client.post(
        "/api/v1/control-plane/connectors",
        headers=op_headers,
        json={"name": "Op Conn", "provider": "LINUX_STORAGE", "credential_ref": "env://OP_KEY"},
    )
    assert op_reg.status_code == 403

    # Admin registers connector
    conn_resp = admin_client.post(
        "/api/v1/control-plane/connectors",
        json={
            "name": f"ONTAP-Core-{uuid.uuid4().hex[:6]}",
            "provider": "ONTAP_READONLY",
            "version": "9.14.1",
            "credential_ref": "vault://storage/ontap-readonly",
        },
    )
    assert conn_resp.status_code == 201, conn_resp.text
    conn = conn_resp.json()
    assert conn["connection_status"] == "CONFIGURED"

    # Invalid capability rejected
    bad_cap = admin_client.post(
        f"/api/v1/control-plane/connectors/{conn['id']}/capabilities",
        json={"action_key": "DELETE_VOLUME", "dry_run_mode": "NATIVE_PROVIDER"},
    )
    assert bad_cap.status_code == 422

    # Register valid capabilities
    for op, mode in [
        ("RESOURCE_INSPECT", "NATIVE_PROVIDER"),
        ("CAPACITY_INSPECT", "AEGISSTOR_PREFLIGHT"),
        ("CONNECTOR_HEALTH_CHECK", "AEGISSTOR_PREFLIGHT"),
        ("CONFIG_INSPECT", "AEGISSTOR_PREFLIGHT"),
    ]:
        cap_resp = admin_client.post(
            f"/api/v1/control-plane/connectors/{conn['id']}/capabilities",
            json={"action_key": op, "dry_run_mode": mode},
        )
        assert cap_resp.status_code == 201, cap_resp.text

    # Operator runs connector health check
    hc = admin_client.post(
        f"/api/v1/control-plane/connectors/{conn['id']}/health-check",
        headers=op_headers,
    )
    assert hc.status_code == 200
    assert hc.json()["connection_status"] == "CONNECTED"

    # Viewer can read connectors, cannot create actions
    vw_list = admin_client.get("/api/v1/control-plane/connectors", headers=vw_headers)
    assert vw_list.status_code == 200
    vw_act = admin_client.post(
        "/api/v1/control-plane/actions",
        headers=vw_headers,
        json={"connector_id": conn["id"], "operation": "RESOURCE_INSPECT", "resource_type": "CONNECTOR", "resource_id": conn["id"]},
    )
    assert vw_act.status_code == 403


def test_sprint1_action_lifecycle_preflight_approval_execution_and_realtime(admin_client):
    op_headers = _login_headers(admin_client, "operator", "AegisOperator!2026")

    # Baseline realtime seq cursor for recovery verification
    ev_before = admin_client.get("/api/v1/realtime/events?since_seq=0&limit=1", headers=op_headers)
    assert ev_before.status_code == 200
    baseline_seq = ev_before.json()["latest_seq"]

    # Admin registers connector + capabilities
    conn = admin_client.post(
        "/api/v1/control-plane/connectors",
        json={
            "name": f"Local-Storage-{uuid.uuid4().hex[:6]}",
            "provider": "AEGISSTOR_LOCAL",
            "credential_ref": "none://local-readonly",
        },
    ).json()
    for op, mode in [("CONFIG_INSPECT", "AEGISSTOR_PREFLIGHT"), ("CAPACITY_INSPECT", "NATIVE_PROVIDER")]:
        admin_client.post(
            f"/api/v1/control-plane/connectors/{conn['id']}/capabilities",
            json={"action_key": op, "dry_run_mode": mode},
        )
    admin_client.post(f"/api/v1/control-plane/connectors/{conn['id']}/health-check", headers=op_headers)

    # Pick an existing device or fallback to connector resource
    devs = admin_client.get("/api/v1/devices", headers=op_headers).json()
    target_type = "DEVICE" if devs else "CONNECTOR"
    target_id = devs[0]["id"] if devs else conn["id"]

    # 1. Operator creates CONFIG_INSPECT action with idempotency key
    idem = f"cp-idem-{uuid.uuid4().hex[:8]}"
    a1 = admin_client.post(
        "/api/v1/control-plane/actions",
        headers=op_headers,
        json={
            "connector_id": conn["id"],
            "operation": "CONFIG_INSPECT",
            "resource_type": target_type,
            "resource_id": target_id,
            "parameters": {"scope": "summary"},
            "idempotency_key": idem,
        },
    )
    assert a1.status_code == 201, a1.text
    act = a1.json()
    assert act["status"] == "DRAFT"
    assert act["approval_required"] is True

    # Duplicate idempotency key returns replay without creating second row
    replay = admin_client.post(
        "/api/v1/control-plane/actions",
        headers=op_headers,
        json={
            "connector_id": conn["id"],
            "operation": "CONFIG_INSPECT",
            "resource_type": target_type,
            "resource_id": target_id,
            "idempotency_key": idem,
        },
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == act["id"]
    assert replay.json()["idempotent_replay"] is True

    # 2. Cannot execute directly from DRAFT
    bad_exec = admin_client.post(f"/api/v1/control-plane/actions/{act['id']}/execute", headers=op_headers)
    assert bad_exec.status_code == 422

    # 3. Run Preflight & Dry-Run
    pf = admin_client.post(f"/api/v1/control-plane/actions/{act['id']}/preflight", headers=op_headers)
    assert pf.status_code == 200, pf.text
    assert pf.json()["action"]["status"] == "DRY_RUN"
    assert pf.json()["preflight"]["overall_status"] == "PASS"
    assert pf.json()["preflight"]["dry_run_mode"] == "AEGISSTOR_PREFLIGHT"

    # 4. Submit for approval
    sub = admin_client.post(f"/api/v1/control-plane/actions/{act['id']}/submit-approval", headers=op_headers)
    assert sub.status_code == 200
    assert sub.json()["status"] == "PENDING_APPROVAL"

    # Operator cannot approve own request
    op_appr = admin_client.post(
        f"/api/v1/control-plane/actions/{act['id']}/approve",
        headers=op_headers,
        json={"comment": "self-approve"},
    )
    assert op_appr.status_code == 403

    # Stale expected_version triggers 409
    stale = admin_client.post(
        f"/api/v1/control-plane/actions/{act['id']}/approve",
        json={"comment": "stale", "expected_version": 1},
    )
    assert stale.status_code == 409

    # 5. Admin approves
    appr = admin_client.post(
        f"/api/v1/control-plane/actions/{act['id']}/approve",
        json={"comment": "Approved for read-only config inspection", "expected_version": sub.json()["entity_version"]},
    )
    assert appr.status_code == 200, appr.text
    assert appr.json()["status"] == "APPROVED"

    # 6. Execute read-only inspection
    ex = admin_client.post(f"/api/v1/control-plane/actions/{act['id']}/execute", headers=op_headers)
    assert ex.status_code == 200, ex.text
    assert ex.json()["action"]["status"] == "SUCCEEDED"

    # Verify detail & audit history & lock released
    detail = admin_client.get(f"/api/v1/control-plane/actions/{act['id']}", headers=op_headers).json()
    assert len(detail["preflights"]) == 1
    assert len(detail["approvals"]) == 1
    assert len(detail["executions"]) == 1
    assert len(detail["executions"][0]["steps"]) == 3
    assert len(detail["audit_events"]) >= 4

    locks = admin_client.get("/api/v1/control-plane/locks", headers=op_headers).json()["locks"]
    assert all(not l["is_active"] for l in locks if l["locked_by_action_id"] == act["id"])

    # 7. Cancel & Reject flows
    a_cancel = admin_client.post(
        "/api/v1/control-plane/actions",
        headers=op_headers,
        json={"connector_id": conn["id"], "operation": "CAPACITY_INSPECT", "resource_type": target_type, "resource_id": target_id},
    ).json()
    c_resp = admin_client.post(
        f"/api/v1/control-plane/actions/{a_cancel['id']}/cancel",
        headers=op_headers,
        json={"reason": "No longer needed"},
    )
    assert c_resp.status_code == 200
    assert c_resp.json()["status"] == "CANCELLED"

    # Reject flow
    a_rej = admin_client.post(
        "/api/v1/control-plane/actions",
        headers=op_headers,
        json={"connector_id": conn["id"], "operation": "CONFIG_INSPECT", "resource_type": target_type, "resource_id": target_id},
    ).json()
    admin_client.post(f"/api/v1/control-plane/actions/{a_rej['id']}/preflight", headers=op_headers)
    admin_client.post(f"/api/v1/control-plane/actions/{a_rej['id']}/submit-approval", headers=op_headers)
    rej_resp = admin_client.post(
        f"/api/v1/control-plane/actions/{a_rej['id']}/reject",
        json={"comment": "Denied in Sprint 1 test"},
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["status"] == "REJECTED"

    # 8. Verify missed-event recovery returns all Control Plane outbox events
    ev_after = admin_client.get(f"/api/v1/realtime/events?since_seq={baseline_seq}&limit=200", headers=op_headers)
    assert ev_after.status_code == 200
    event_types = {e["event_type"] for e in ev_after.json().get("events", [])}
    for expected in (
        "action.created",
        "action.preflight_completed",
        "action.approval_requested",
        "action.approved",
        "action.rejected",
        "action.cancelled",
    ):
        assert expected in event_types, f"Missing realtime event: {expected}"
