import os
import sys
import types
import pytest
from fastapi.testclient import TestClient

from app.collector.connector_registry import ConnectorRegistry
from app.main import app
from tests.auth_helper import attach_admin_auth


@pytest.fixture(scope="module")
def admin_client():
    os.environ["AEGISSTOR_ALLOW_DEV_SEED"] = "true"
    with TestClient(app) as c:
        yield attach_admin_auth(c)


def test_enterprise_database_connector_types_registered():
    types_list = ConnectorRegistry.list_supported_types()
    for expected in ("LINUX_HOST", "PROMETHEUS", "CSV_HISTORICAL", "HTTP_API", "POSTGRESQL", "MYSQL", "MARIADB", "MSSQL", "ORACLE"):
        assert expected in types_list


def test_database_connector_not_configured_returns_honest_status():
    for db_type in ("POSTGRESQL", "MYSQL", "MARIADB", "MSSQL", "ORACLE"):
        adapter = ConnectorRegistry.get_adapter(db_type)
        res = adapter.test_connection({})
        assert res["status"] == "NOT_CONFIGURED"
        assert res["read_only"] is True
        assert res["size_scope"] == "logical_database_metadata"
        assert "not configured" in res["error"].lower()


def test_postgres_connector_collect_readonly_metadata(monkeypatch):
    class FakeCursor:
        def __init__(self):
            self._q = ""

        def execute(self, sql):
            self._q = sql

        def fetchone(self):
            if "version()" in self._q:
                return ("PostgreSQL 16.2", "hospital_ehr", 104857600)
            return ("hospital_ehr", 104857600)

        def fetchall(self):
            return [("public", "patient_records", 62914560, 50331648, 12582912, 250000)]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeConn:
        def set_session(self, readonly=True, autocommit=True):
            assert readonly is True

        def cursor(self):
            return FakeCursor()

        def close(self):
            pass

    fake_psycopg2 = types.ModuleType("psycopg2")
    fake_psycopg2.connect = lambda *a, **kw: FakeConn()
    monkeypatch.setitem(sys.modules, "psycopg2", fake_psycopg2)

    adapter = ConnectorRegistry.get_adapter("POSTGRESQL")
    cfg = {"host": "127.0.0.1", "port": 5432, "database": "hospital_ehr", "username": "readonly_user", "password": "secret"}
    test_res = adapter.test_connection(cfg)
    assert test_res["status"] == "CONNECTED"
    assert test_res["logical_database_bytes"] == 104857600

    collect_res = adapter.collect(cfg)
    assert collect_res["status"] == "OK"
    assert collect_res["size_scope"] == "logical_database_metadata"
    assert collect_res["database_summary"]["database_name"] == "hospital_ehr"
    assert collect_res["tables"][0]["table"] == "patient_records"


def test_connectors_api_redacts_database_credentials(admin_client):
    reg = admin_client.post(
        "/api/v1/connectors",
        json={
            "name": "Test EHR Postgres",
            "connector_type": "POSTGRESQL",
            "config": {
                "host": "10.0.0.15",
                "port": 5432,
                "database": "ehr_prod",
                "username": "aegis_ro",
                "password": "super-secret-password",
            },
        },
    )
    assert reg.status_code == 200
    conn_id = reg.json()["connector"]["id"]

    listed = admin_client.get("/api/v1/connectors")
    assert listed.status_code == 200
    item = next(c for c in listed.json()["connectors"] if c["id"] == conn_id)
    assert item["config"]["password"] == "***REDACTED***"
    assert "super-secret-password" not in str(item)

    # Test connection honestly returns DRIVER_MISSING or ERROR (never fake CONNECTED)
    test_resp = admin_client.post(f"/api/v1/connectors/{conn_id}/test")
    assert test_resp.status_code == 200
    assert test_resp.json()["last_status"] in ("DRIVER_MISSING", "ERROR")

    # Clean up
    admin_client.delete(f"/api/v1/connectors/{conn_id}")
