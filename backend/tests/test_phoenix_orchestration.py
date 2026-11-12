"""
AEGISSTOR PHOENIX — Automated Verification Suite (Drills A through J)
Tests end-to-end incident orchestration, 14-state lifecycle machine, Policy-as-Code safety gateway,
tamper-evident approval integrity, idempotency, independent recovery verification, and evidence graph.
"""
import pytest
from fastapi.testclient import TestClient
import json
import uuid

from app.main import app
from tests.auth_helper import attach_admin_auth
from app.database import SessionLocal
from app.models.entities import (
    Device, Telemetry, Forecast, RiskAssessment, PhoenixIncident,
    PhoenixActionProposal, PhoenixExecutionRecord, PhoenixRecoveryVerification
)
from app.services.phoenix import (
    IncidentLifecycleManager, InvalidStateTransitionError,
    PolicyGateway, ActionGateway, ActionGatewayError, compute_proposal_hash,
    IncidentCorrelationEngine
)

client = attach_admin_auth(TestClient(app))


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_drill_a_predictive_incident_detection_and_correlation(db_session):
    """
    DRILL A: Storage telemetry and predictive runway trigger automated incident correlation.
    Distinguishes PREDICTED vs OBSERVED evidence and generates transparent hypotheses.
    """
    response = client.post("/api/v1/phoenix/incidents/scan")
    assert response.status_code == 200
    scan_data = response.json()
    assert scan_data["status"] == "COMPLETED"
    assert scan_data["active_incidents_count"] >= 1

    # Fetch scanned incidents with symptoms
    scanned_inc = (
        db_session.query(PhoenixIncident)
        .filter(PhoenixIncident.symptoms_json != "[]")
        .order_by(PhoenixIncident.detection_timestamp.desc())
        .first()
    )
    assert scanned_inc is not None

    detail_res = client.get(f"/api/v1/phoenix/incidents/{scanned_inc.id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()

    assert detail["category"] in [
        "CAPACITY_EXHAUSTION", "LATENCY_SATURATION", "IOPS_THROTTLING",
        "POOL_UNBALANCE", "FAILOVER_DEGRADATION", "WORKLOAD_HOTSPOT"
    ]
    assert detail["evidence_type"] in ["PREDICTED", "OBSERVED", "SIMULATED"]
    assert len(detail["symptoms"]) > 0
    assert len(detail["hypotheses"]) > 0
    # Verify hypothesis structure
    for h in detail["hypotheses"]:
        assert h["status"] in [
            "CONFIRMED_OBSERVATION", "SUPPORTED_HYPOTHESIS",
            "UNCONFIRMED_HYPOTHESIS", "INSUFFICIENT_EVIDENCE"
        ]


def test_drill_b_14_state_lifecycle_machine_and_invalid_jump_guard(db_session):
    """
    DRILL B: Persistent 14-state lifecycle machine enforces valid state transitions
    and strictly rejects illegal jumps (e.g. DETECTED -> RESOLVED).
    """
    # 1. Test state transition manager directly
    assert IncidentLifecycleManager.can_transition("DETECTED", "EVIDENCE_COLLECTION") is True
    assert IncidentLifecycleManager.can_transition("DETECTED", "RESOLVED") is False
    assert IncidentLifecycleManager.can_transition("APPROVED", "EXECUTING") is True
    assert IncidentLifecycleManager.can_transition("CANCELLED", "DETECTED") is False

    # 2. Test via REST API
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-lifecycle-{uid}",
        title="Test Lifecycle Invariant Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV2_HIGH",
        status="DETECTED",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.commit()

    # Attempt illegal transition: DETECTED -> RESOLVED
    bad_res = client.post(
        f"/api/v1/phoenix/incidents/{inc.id}/transition",
        json={"target_state": "RESOLVED", "reason": "Attempting illegal shortcut"}
    )
    assert bad_res.status_code == 400
    assert "Cannot transition from DETECTED to RESOLVED" in bad_res.json()["detail"]

    # Execute valid transition: DETECTED -> EVIDENCE_COLLECTION
    step1_res = client.post(
        f"/api/v1/phoenix/incidents/{inc.id}/transition",
        json={"target_state": "EVIDENCE_COLLECTION", "reason": "Commencing evidence collection"}
    )
    assert step1_res.status_code == 200
    assert step1_res.json()["current_state"] == "EVIDENCE_COLLECTION"

    # Step: EVIDENCE_COLLECTION -> TRIAGE
    step2_res = client.post(
        f"/api/v1/phoenix/incidents/{inc.id}/transition",
        json={"target_state": "TRIAGE", "reason": "Evidence collected; classifying severity"}
    )
    assert step2_res.status_code == 200
    assert step2_res.json()["current_state"] == "TRIAGE"


def test_drill_c_policy_as_code_hard_safety_gate(db_session):
    """
    DRILL C: Hard safety constraint rejection cannot be overridden by high recommendation score.
    """
    inc = db_session.query(PhoenixIncident).first()
    assert inc is not None

    # Proposal with projected utilization 95.0% (free reserve 5.0% < required 10.0%)
    violating_proposal_payload = {
        "action_type": "WORKLOAD_RATE_LIMIT",
        "parameters": {"throttle_factor": 0.5},
        "simulated_outcome": {
            "projected_utilization_pct": 95.0,  # leaves only 5% reserve!
            "projected_latency_ms": 12.0
        }
    }

    prop_res = client.post(f"/api/v1/phoenix/incidents/{inc.id}/proposals", json=violating_proposal_payload)
    assert prop_res.status_code == 200
    data = prop_res.json()

    assert data["policy_verdict"] == "REJECTED_BY_POLICY"
    assert len(data["policy_violations"]) > 0
    assert any("minimum free capacity reserve invariant" in v for v in data["policy_violations"])

    # Attempting to approve a rejected proposal must fail
    appr_res = client.post(
        f"/api/v1/phoenix/proposals/{data['proposal_id']}/approve",
        json={"reviewer_id": "operator@aegisstor.internal", "rationale": "Attempting override"}
    )
    assert appr_res.status_code == 400
    assert "Cannot approve proposal that was REJECTED_BY_POLICY" in appr_res.json()["detail"]


def test_drill_d_safe_action_gateway_execution_modes(db_session):
    """
    DRILL D: Safe Action Gateway allows MODE_A_SIMULATE and MODE_B_DIAGNOSTIC_READONLY,
    blocks MODE_C_CONTROLLED_EXECUTION by default, and guarantees zero physical mutations.
    """
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-modes-{uid}",
        title="Test Mode Gateway Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV3_MEDIUM",
        status="APPROVED",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.flush()

    safe_params = {"target_reclaim_pct": 5.0}
    p_hash = compute_proposal_hash("COMPACT_SHADOW_SNAPSHOTS", "vol-nvme-tier1-db", safe_params)
    proposal = PhoenixActionProposal(
        id=f"prop-test-modes-{uid}",
        incident_id=inc.id,
        action_type="COMPACT_SHADOW_SNAPSHOTS",
        target_resource_id="vol-nvme-tier1-db",
        parameters_json=json.dumps(safe_params),
        policy_verdict="REQUIRES_HUMAN_REVIEW",
        approval_status="APPROVED",
        approved_by="lead_architect",
        proposal_hash=p_hash
    )
    db_session.add(proposal)
    db_session.commit()

    # 1. Mode C execution should be rejected (fail-closed)
    mode_c_res = client.post(
        f"/api/v1/phoenix/proposals/{proposal.id}/execute",
        json={"idempotency_token": f"tok-test-mode-c-{uid}", "execution_mode": "MODE_C_CONTROLLED_EXECUTION"}
    )
    assert mode_c_res.status_code == 400
    assert "MODE_C_CONTROLLED_EXECUTION is disabled by safety invariant" in mode_c_res.json()["detail"]

    # 2. Mode A simulation should succeed safely
    mode_a_res = client.post(
        f"/api/v1/phoenix/proposals/{proposal.id}/execute",
        json={"idempotency_token": f"tok-test-mode-a-{uid}", "execution_mode": "MODE_A_SIMULATE"}
    )
    assert mode_a_res.status_code == 200
    a_data = mode_a_res.json()
    assert a_data["status"] == "SUCCESS"
    assert a_data["execution_result"]["zero_physical_mutations_verified"] is True


def test_drill_e_human_approval_integrity_and_tamper_invalidation(db_session):
    """
    DRILL E: Any post-approval mutation to proposal parameters invalidates approval
    and prevents execution.
    """
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-tamper-{uid}",
        title="Tamper Invalidation Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV2_HIGH",
        status="APPROVED",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.flush()

    orig_params = {"throttle_reduction_pct": 10.0}
    p_hash = compute_proposal_hash("TIER_THROTTLE_ADJUSTMENT", "vol-nvme-tier1-db", orig_params)
    proposal = PhoenixActionProposal(
        id=f"prop-test-tamper-{uid}",
        incident_id=inc.id,
        action_type="TIER_THROTTLE_ADJUSTMENT",
        target_resource_id="vol-nvme-tier1-db",
        parameters_json=json.dumps(orig_params),
        policy_verdict="REQUIRES_HUMAN_REVIEW",
        approval_status="APPROVED",
        approved_by="security_officer",
        proposal_hash=p_hash
    )
    db_session.add(proposal)
    db_session.commit()

    # Tamper with the parameters in DB without re-computing proposal_hash
    proposal.parameters_json = json.dumps({"throttle_reduction_pct": 99.0})  # unauthorized alteration!
    db_session.commit()

    # Attempt execution: must detect hash mismatch and reject with INVALIDATED
    exec_res = client.post(
        f"/api/v1/phoenix/proposals/{proposal.id}/execute",
        json={"idempotency_token": f"tok-tamper-test-{uid}", "execution_mode": "MODE_A_SIMULATE"}
    )
    assert exec_res.status_code == 400
    assert "Proposal hash mismatch" in exec_res.json()["detail"]

    # Verify status changed to INVALIDATED
    db_session.refresh(proposal)
    assert proposal.approval_status == "INVALIDATED"


def test_drill_f_idempotency_token_deduplication(db_session):
    """
    DRILL F: Re-executing an action with the same idempotency token returns
    the prior execution record without duplicating steps.
    """
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-idempotent-{uid}",
        title="Idempotency Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV3_MEDIUM",
        status="APPROVED",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.flush()

    params = {"sample_interval_ms": 100}
    p_hash = compute_proposal_hash("NOOP_DIAGNOSTIC_SAMPLE", "vol-nvme-tier1-db", params)
    proposal = PhoenixActionProposal(
        id=f"prop-test-idempotent-{uid}",
        incident_id=inc.id,
        action_type="NOOP_DIAGNOSTIC_SAMPLE",
        target_resource_id="vol-nvme-tier1-db",
        parameters_json=json.dumps(params),
        policy_verdict="REQUIRES_HUMAN_REVIEW",
        approval_status="APPROVED",
        approved_by="operator",
        proposal_hash=p_hash
    )
    db_session.add(proposal)
    db_session.commit()

    token = f"idempotency-token-unique-{uid}"
    res1 = client.post(
        f"/api/v1/phoenix/proposals/{proposal.id}/execute",
        json={"idempotency_token": token, "execution_mode": "MODE_A_SIMULATE"}
    )
    assert res1.status_code == 200
    exec1 = res1.json()

    # Submit second time with identical token
    res2 = client.post(
        f"/api/v1/phoenix/proposals/{proposal.id}/execute",
        json={"idempotency_token": token, "execution_mode": "MODE_A_SIMULATE"}
    )
    assert res2.status_code == 200
    exec2 = res2.json()

    assert exec1["execution_id"] == exec2["execution_id"]
    assert exec1["status"] == exec2["status"]


def test_drill_g_recovery_verification_unsuccessful(db_session):
    """
    DRILL G: Independent recovery verifier flags non-recovery when telemetry remains degraded,
    transitioning incident to FAILED.
    """
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-unsuccessful-{uid}",
        title="Unsuccessful Recovery Test Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV2_HIGH",
        status="VERIFYING_RECOVERY",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.commit()

    verif_res = client.post(
        f"/api/v1/phoenix/incidents/{inc.id}/verify",
        json={"force_mock_outcome": "UNSUCCESSFUL", "observation_window_hours": 24.0}
    )
    assert verif_res.status_code == 200
    data = verif_res.json()

    assert data["status"] == "UNSUCCESSFUL"
    assert data["residual_risk_score"] > 0.5
    assert data["secondary_degradation_detected"] is True

    # Check incident transitioned to FAILED
    db_session.refresh(inc)
    assert inc.status == "FAILED"


def test_drill_h_recovery_verification_successful_resolution(db_session):
    """
    DRILL H: Independent recovery verifier confirms telemetry normalized,
    transitioning incident to RESOLVED.
    """
    uid = uuid.uuid4().hex[:6]
    inc = PhoenixIncident(
        id=f"inc-test-successful-{uid}",
        title="Successful Recovery Test Incident",
        category="CAPACITY_EXHAUSTION",
        severity="SEV2_HIGH",
        status="VERIFYING_RECOVERY",
        target_device_id="vol-nvme-tier1-db"
    )
    db_session.add(inc)
    db_session.commit()

    verif_res = client.post(
        f"/api/v1/phoenix/incidents/{inc.id}/verify",
        json={"force_mock_outcome": "RECOVERY_SATISFIED", "observation_window_hours": 24.0}
    )
    assert verif_res.status_code == 200
    data = verif_res.json()

    assert data["status"] == "RECOVERY_SATISFIED"
    assert data["residual_risk_score"] < 0.2

    # Check incident transitioned to RESOLVED
    db_session.refresh(inc)
    assert inc.status == "RESOLVED"
    assert inc.resolved_at is not None


def test_drill_i_incident_evidence_graph_generation(db_session):
    """
    DRILL I: Generates directed evidence graph connecting incident, target devices,
    forecast horizons, policy gateways, and verifications.
    """
    inc = db_session.query(PhoenixIncident).first()
    assert inc is not None

    graph_res = client.get(f"/api/v1/phoenix/incidents/{inc.id}/evidence-graph")
    assert graph_res.status_code == 200
    graph = graph_res.json()

    assert "nodes" in graph
    assert "edges" in graph
    assert graph["node_count"] >= 2
    # Verify node types present
    node_types = {n["type"] for n in graph["nodes"]}
    assert "INCIDENT" in node_types
    assert "STORAGE_DEVICE" in node_types


def test_drill_j_repeated_incident_pattern_analysis(db_session):
    """
    DRILL J: Aggregates historical incidents, identifies recurring hotspot patterns,
    and calculates MTTR.
    """
    patterns_res = client.get("/api/v1/phoenix/analytics/repeated-patterns")
    assert patterns_res.status_code == 200
    patterns = patterns_res.json()

    assert "total_incidents" in patterns
    assert "category_distribution" in patterns
    assert "device_hotspots" in patterns
    assert "recommended_preventive_action" in patterns

