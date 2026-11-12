"""Control Plane Sprint 1 tests: strict auth, tenant scope, planning and event tickets."""
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.entities import Device, Telemetry, User
from app.auth.security import hash_password, create_access_token
from app.utils.datetime_utils import utc_now


def _user(role: str, org: str):
    db = SessionLocal()
    username = f"cp-{role.lower()}-{uuid.uuid4().hex[:10]}"
    user = User(
        id=f"usr-{uuid.uuid4().hex[:12]}",
        username=username,
        email=f"{username}@test.invalid",
        hashed_password=hash_password("test-only-password"),
        role=role,
        organization_id=org,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    token = create_access_token({
        "sub": username,
        "user_id": user.id,
        "role": role,
        "organization_id": org,
    })
    return user.id, token


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _device(org: str, telemetry_synthetic: bool = False):
    db = SessionLocal()
    device_id = f"cp-device-{uuid.uuid4().hex[:10]}"
    device = Device(
        id=device_id,
        name="Control Plane Test Resource",
        tier="TEST_TIER",
        media_type="TEST",
        total_capacity_bytes=10_000_000,
        warning_threshold_pct=80.0,
        critical_threshold_pct=90.0,
        status="HEALTHY",
        organization_id=org,
    )
    db.add(device)
    db.flush()
    db.add(Telemetry(
        device_id=device_id,
        timestamp=utc_now(),
        used_bytes=4_000_000,
        free_bytes=6_000_000,
        utilization_pct=40.0,
        read_iops=1.0,
        write_iops=1.0,
        throughput_mb_s=1.0,
        latency_p95_ms=1.0,
        queue_depth=0.0,
        is_synthetic=telemetry_synthetic,
        source_label="CONTROL_PLANE_TEST_FIXTURE",
    ))
    db.commit()
    db.close()
    return device_id


def test_control_plane_requires_bearer_authentication():
    with TestClient(app) as client:
        response = client.get("/api/v1/control-plane/connectors")
        assert response.status_code == 401


def test_operator_cannot_register_connector():
    _, operator_token = _user("OPERATOR", "org-cp-rbac")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/control-plane/connectors",
            headers=_headers(operator_token),
            json={"provider": "PROMETHEUS", "name": "test-prom"},
        )
        assert response.status_code == 403


def test_admin_connector_registration_does_not_claim_connection_or_capabilities():
    _, admin_token = _user("ADMIN", "org-cp-connector")
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/control-plane/connectors",
            headers=_headers(admin_token),
            json={
                "provider": "PROMETHEUS",
                "name": f"prom-{uuid.uuid4().hex[:8]}",
                "configuration": {"base_url": "https://prometheus.invalid"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "NOT_CONFIGURED"
        assert data["capabilities"] == []
        assert data["credential_ref_configured"] is False


def test_resource_inspection_reads_saved_inventory_and_telemetry():
    org = f"org-cp-inspect-{uuid.uuid4().hex[:6]}"
    _, operator_token = _user("OPERATOR", org)
    device_id = _device(org, telemetry_synthetic=True)
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "resource.inspect",
                "target_type": "DEVICE",
                "target_id": device_id,
                "parameters": {},
                "idempotency_key": f"inspect-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 201
        action = created.json()
        assert action["status"] == "DRY_RUN"
        assert action["preflight"]["data_provenance"] == "SYNTHETIC"

        executed = client.post(
            f"/api/v1/control-plane/actions/{action['id']}/execute-read-only",
            headers=_headers(operator_token),
        )
        assert executed.status_code == 200
        result = executed.json()
        assert result["status"] == "SUCCEEDED"
        assert result["output"]["physical_mutation"] is False
        assert result["output"]["latest_telemetry"]["provenance"] == "SYNTHETIC"


def test_capacity_plan_requires_non_synthetic_fresh_telemetry_and_separate_admin_approval():
    org = f"org-cp-plan-{uuid.uuid4().hex[:6]}"
    operator_id, operator_token = _user("OPERATOR", org)
    admin_id, admin_token = _user("ADMIN", org)
    device_id = _device(org, telemetry_synthetic=False)

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "storage.capacity.plan",
                "target_type": "DEVICE",
                "target_id": device_id,
                "parameters": {"additional_capacity_bytes": 5_000_000},
                "idempotency_key": f"plan-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 201
        action = created.json()
        assert action["status"] == "PENDING_APPROVAL"
        assert action["approval_required"] is True
        assert action["dry_run"]["proposed_total_capacity_bytes"] == 15_000_000

        self_approval = client.post(
            f"/api/v1/control-plane/actions/{action['id']}/approve",
            headers=_headers(operator_token),
            json={"expected_version": action["entity_version"], "rationale": "Should not be allowed"},
        )
        assert self_approval.status_code == 403

        approved = client.post(
            f"/api/v1/control-plane/actions/{action['id']}/approve",
            headers=_headers(admin_token),
            json={"expected_version": action["entity_version"], "rationale": "Reviewed capacity plan and supporting telemetry."},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"
        assert approved.json()["approved_by_id"] == admin_id

        # Approval records acceptance of a plan; it does not provision infrastructure.
        assert approved.json()["output"] == {}


def test_synthetic_data_blocks_real_capacity_plan():
    org = f"org-cp-synth-{uuid.uuid4().hex[:6]}"
    _, operator_token = _user("OPERATOR", org)
    device_id = _device(org, telemetry_synthetic=True)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "storage.capacity.plan",
                "target_type": "DEVICE",
                "target_id": device_id,
                "parameters": {"additional_capacity_bytes": 5_000_000},
                "idempotency_key": f"synthetic-{uuid.uuid4().hex}",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "BLOCKED"
        checks = response.json()["preflight"]["checks"]
        assert any(c["name"] == "telemetry_provenance" and c["passed"] is False for c in checks)


def test_realtime_ticket_is_short_lived_and_only_hash_is_persisted():
    _, token = _user("OPERATOR", "org-cp-ws")
    with TestClient(app) as client:
        response = client.post("/api/v1/control-plane/realtime/ticket", headers=_headers(token))
        assert response.status_code == 200
        data = response.json()
        assert data["single_use"] is True
        assert data["expires_in_seconds"] == 60
        assert len(data["ticket"]) >= 20



def test_action_definitions_are_bootstrapped_on_application_startup():
    with TestClient(app) as client:
        _, token = _user("OPERATOR", f"org-cp-defs-{uuid.uuid4().hex[:6]}")
        response = client.get("/api/v1/control-plane/action-definitions", headers=_headers(token))
        assert response.status_code == 200
        definitions = {item["action_type"]: item for item in response.json()}
        assert set(definitions) >= {"resource.inspect", "storage.capacity.plan", "storage.volume.resize"}
        assert definitions["resource.inspect"]["is_executable"] is True
        assert definitions["storage.capacity.plan"]["requires_approval"] is True
        assert definitions["storage.volume.resize"]["is_enabled"] is False


def test_resource_inspection_is_available_without_telemetry():
    org = f"org-cp-no-telemetry-{uuid.uuid4().hex[:6]}"
    _, operator_token = _user("OPERATOR", org)
    db = SessionLocal()
    device_id = f"cp-empty-{uuid.uuid4().hex[:10]}"
    db.add(Device(
        id=device_id,
        name="Inventory-only resource",
        tier="TEST_TIER",
        media_type="TEST",
        total_capacity_bytes=10_000_000,
        warning_threshold_pct=80.0,
        critical_threshold_pct=90.0,
        status="HEALTHY",
        organization_id=org,
    ))
    db.commit()
    db.close()

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "resource.inspect",
                "target_type": "DEVICE",
                "target_id": device_id,
                "parameters": {},
                "idempotency_key": f"inspect-empty-{uuid.uuid4().hex}",
            },
        )
        assert created.status_code == 201
        assert created.json()["status"] == "DRY_RUN"
        assert created.json()["preflight"]["data_provenance"] == "UNKNOWN"
        assert created.json()["preflight"]["warnings"]

        executed = client.post(
            f"/api/v1/control-plane/actions/{created.json()['id']}/execute-read-only",
            headers=_headers(operator_token),
        )
        assert executed.status_code == 200
        assert executed.json()["status"] == "SUCCEEDED"
        assert executed.json()["output"]["latest_telemetry"] is None


def test_idempotency_key_cannot_be_reused_for_a_different_action():
    org = f"org-cp-idem-{uuid.uuid4().hex[:6]}"
    _, operator_token = _user("OPERATOR", org)
    device_a = _device(org, telemetry_synthetic=True)
    device_b = _device(org, telemetry_synthetic=True)
    key = f"same-key-{uuid.uuid4().hex}"

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "resource.inspect",
                "target_type": "DEVICE",
                "target_id": device_a,
                "parameters": {},
                "idempotency_key": key,
            },
        )
        assert first.status_code == 201

        changed = client.post(
            "/api/v1/control-plane/actions",
            headers=_headers(operator_token),
            json={
                "action_type": "resource.inspect",
                "target_type": "DEVICE",
                "target_id": device_b,
                "parameters": {},
                "idempotency_key": key,
            },
        )
        assert changed.status_code == 409
