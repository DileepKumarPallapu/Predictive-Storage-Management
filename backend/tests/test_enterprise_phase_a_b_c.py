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


def _get_operator_headers(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "AegisOperator!2026"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_phase_a_multitenancy_and_isolation(admin_client):
    orgs_resp = admin_client.get("/api/v1/organisations")
    assert orgs_resp.status_code == 200
    org_ids = [o["id"] for o in orgs_resp.json()["organisations"]]
    assert "org-primary-enterprise" in org_ids

    slug = f"org-b-{uuid.uuid4().hex[:6]}"
    create_resp = admin_client.post(
        "/api/v1/organisations",
        json={"name": "Tenant B Corp", "slug": slug, "plan": "ENTERPRISE", "default_currency": "EUR"},
    )
    assert create_resp.status_code == 201, create_resp.text
    org_b_id = create_resp.json()["id"]

    bu_resp = admin_client.post(
        "/api/v1/hierarchy/business-units",
        headers={"X-Organization-ID": org_b_id},
        json={"name": "Tenant B Payments", "code": "TBPAY", "cost_centre": "CC-TB-01"},
    )
    assert bu_resp.status_code == 201, bu_resp.text
    assert bu_resp.json()["organization_id"] == org_b_id

    op_headers = _get_operator_headers(admin_client)
    denied = admin_client.get(
        "/api/v1/hierarchy/overview",
        headers={**op_headers, "X-Organization-ID": org_b_id},
    )
    assert denied.status_code == 403

    primary_hier = admin_client.get("/api/v1/hierarchy/overview", headers=op_headers)
    assert primary_hier.status_code == 200
    bu_names = [b["name"] for b in primary_hier.json()["business_units"]]
    assert "Tenant B Payments" not in bu_names


def test_phase_a_b_c_hierarchy_topology_and_impact(admin_client):
    reg = admin_client.post(
        "/api/v1/hierarchy/regions",
        json={"name": "US East", "code": "USE1", "residency_zone": "US"},
    ).json()
    site = admin_client.post(
        "/api/v1/hierarchy/sites",
        json={"region_id": reg["id"], "name": "Ashburn DC1", "site_code": f"DC-{uuid.uuid4().hex[:4]}"},
    ).json()
    env = admin_client.post(
        "/api/v1/hierarchy/environments",
        json={"site_id": site["id"], "name": "Production", "env_type": "PRODUCTION"},
    ).json()
    clu = admin_client.post(
        "/api/v1/hierarchy/clusters",
        json={"site_id": site["id"], "environment_id": env["id"], "name": "SAN-Cluster-01"},
    ).json()
    pool = admin_client.post(
        "/api/v1/hierarchy/pools",
        json={
            "cluster_id": clu["id"],
            "name": "Pool-NVMe-01",
            "tier": "NVME_TIER1",
            "total_capacity_bytes": 5000000000000,
            "used_bytes": 4100000000000,
        },
    ).json()
    vol = admin_client.post(
        "/api/v1/hierarchy/volumes",
        json={
            "pool_id": pool["id"],
            "name": "vol-ledger-01",
            "total_capacity_bytes": 1000000000000,
            "used_bytes": 850000000000,
        },
    ).json()

    r1 = admin_client.post(
        "/api/v1/topology/relationships",
        json={
            "source_type": "VOLUME", "source_id": vol["id"],
            "target_type": "POOL", "target_id": pool["id"],
            "relationship_type": "ALLOCATED_FROM",
        },
    )
    assert r1.status_code == 201, r1.text

    r2 = admin_client.post(
        "/api/v1/topology/relationships",
        json={
            "source_type": "POOL", "source_id": pool["id"],
            "target_type": "CLUSTER", "target_id": clu["id"],
            "relationship_type": "HOSTS",
        },
    )
    assert r2.status_code == 201

    dup = admin_client.post(
        "/api/v1/topology/relationships",
        json={
            "source_type": "POOL", "source_id": pool["id"],
            "target_type": "CLUSTER", "target_id": clu["id"],
            "relationship_type": "HOSTS",
        },
    )
    assert dup.status_code == 409

    cyc = admin_client.post(
        "/api/v1/topology/relationships",
        json={
            "source_type": "CLUSTER", "source_id": clu["id"],
            "target_type": "VOLUME", "target_id": vol["id"],
            "relationship_type": "DEPENDS_ON",
        },
    )
    assert cyc.status_code == 422

    app_db = admin_client.post(
        "/api/v1/services/applications",
        json={"name": "LedgerDB", "criticality": "TIER_1", "department": "Core Banking"},
    ).json()
    app_api = admin_client.post(
        "/api/v1/services/applications",
        json={"name": "CheckoutAPI", "criticality": "TIER_1", "department": "Payments"},
    ).json()
    svc = admin_client.post(
        "/api/v1/services/business-services",
        json={"name": "Global Card Settlement", "criticality": "MISSION_CRITICAL"},
    ).json()

    # LedgerDB depends on cluster; CheckoutAPI depends on LedgerDB; Service maps to CheckoutAPI
    d1 = admin_client.post(
        "/api/v1/services/dependencies",
        json={"application_id": app_db["id"], "depends_on_type": "CLUSTER", "depends_on_id": clu["id"]},
    )
    assert d1.status_code == 201, d1.text
    d2 = admin_client.post(
        "/api/v1/services/dependencies",
        json={"application_id": app_api["id"], "depends_on_type": "APPLICATION", "depends_on_id": app_db["id"]},
    )
    assert d2.status_code == 201, d2.text

    mapping = admin_client.post(
        "/api/v1/services/resource-mappings",
        json={"service_id": svc["id"], "resource_type": "APPLICATION", "resource_id": app_api["id"]},
    )
    assert mapping.status_code == 201, mapping.text

    impact_resp = admin_client.post(
        f"/api/v1/services/impact/{vol['id']}/evaluate",
        json={"create_incident": True, "trigger_reason": "Pool-NVMe-01 crossed 82% utilization"},
    )
    assert impact_resp.status_code == 200, impact_resp.text
    impact = impact_resp.json()
    assert impact["highest_criticality"] == "MISSION_CRITICAL"
    assert len(impact["impacted_applications"]) == 2
    assert len(impact["impacted_business_services"]) == 1
    assert impact["created_incident_id"] is not None
