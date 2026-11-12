import json
import uuid
from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.auth.tenant import assert_org_resource, resolve_organization_id
from app.database import get_db
from app.models.entities import Telemetry, User
from app.models.enterprise_entities import (
    BackupEvent,
    EnterpriseIncident,
    IncidentPostmortem,
    IncidentTimelineEvent,
    SLIDefinition,
    SLOEvaluation,
    SLORecord,
)
from app.realtime.event_bus import OutboxService
from app.utils.datetime_utils import utc_now

router = APIRouter()

VALID_INCIDENT_TRANSITIONS = {
    "DETECTED": {"OPEN", "ACKNOWLEDGED", "INVESTIGATING"},
    "OPEN": {"ACKNOWLEDGED", "INVESTIGATING", "MITIGATING", "RESOLVED"},
    "ACKNOWLEDGED": {"INVESTIGATING", "MITIGATING", "RESOLVED"},
    "INVESTIGATING": {"MITIGATING", "RESOLVED"},
    "MITIGATING": {"RESOLVED", "INVESTIGATING"},
    "RESOLVED": {"CLOSED", "OPEN"},
    "CLOSED": {"OPEN"},
}


class SLICreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    service_id: Optional[str] = None
    device_id: Optional[str] = None
    metric_type: str = "CAPACITY_HEADROOM"  # CAPACITY_HEADROOM, READ_LATENCY, WRITE_LATENCY, TELEMETRY_FRESHNESS, BACKUP_FRESHNESS
    unit: str = "pct"
    evaluation_window_days: int = Field(30, ge=1, le=365)
    warning_threshold: float
    critical_threshold: float


class SLOCreateRequest(BaseModel):
    sli_id: str
    service_id: Optional[str] = None
    name: str = Field(..., min_length=2, max_length=128)
    target_pct: float = Field(99.9, gt=0.0, le=100.0)
    is_contractual_sla: bool = False


class IncidentCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: str = "CAPACITY_RISK"
    severity: Optional[str] = None  # Auto-classified if omitted
    linked_device_id: Optional[str] = None
    linked_service_id: Optional[str] = None
    severity_policy_reason: str = ""
    evidence_json: str = "{}"


class IncidentTransitionRequest(BaseModel):
    target_status: str
    note: str = ""


class PostmortemRequest(BaseModel):
    impact_summary: str
    timeline_summary: str = ""
    root_cause_findings: str = ""
    contributing_factors: str = ""
    detection_method: str = "Telemetry / SLO Monitor"
    resolution_summary: str = ""
    preventive_actions: str = ""
    follow_up_owner: Optional[str] = None


@router.get("/reliability/overview")
def get_reliability_overview(
    current_user: User = Depends(require_permission("slo.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    slis = db.query(SLIDefinition).filter(SLIDefinition.organization_id == org_id).all()
    slos = db.query(SLORecord).filter(SLORecord.organization_id == org_id).all()
    evals = (
        db.query(SLOEvaluation)
        .filter(SLOEvaluation.organization_id == org_id)
        .order_by(SLOEvaluation.evaluated_at.desc())
        .limit(100)
        .all()
    )
    return {
        "organization_id": org_id,
        "slis": [
            {
                "id": s.id, "name": s.name, "service_id": s.service_id, "device_id": s.device_id,
                "metric_type": s.metric_type, "unit": s.unit, "evaluation_window_days": s.evaluation_window_days,
                "warning_threshold": s.warning_threshold, "critical_threshold": s.critical_threshold,
            }
            for s in slis
        ],
        "slos": [
            {
                "id": o.id, "sli_id": o.sli_id, "service_id": o.service_id, "name": o.name,
                "target_pct": o.target_pct, "is_contractual_sla": o.is_contractual_sla,
                "contractual_sla_approved_by": o.contractual_sla_approved_by, "status": o.status,
            }
            for o in slos
        ],
        "evaluations": [
            {
                "id": e.id, "slo_id": e.slo_id, "actual_sli_value": e.actual_sli_value,
                "compliance_pct": e.compliance_pct, "error_budget_remaining_pct": e.error_budget_remaining_pct,
                "burn_rate": e.burn_rate, "breached": e.breached, "insufficient_data": e.insufficient_data,
                "evaluated_at": e.evaluated_at.isoformat() if e.evaluated_at else None,
            }
            for e in evals
        ],
    }


@router.post("/reliability/slis", status_code=status.HTTP_201_CREATED)
def create_sli(
    payload: SLICreateRequest,
    current_user: User = Depends(require_permission("slo.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    sli = SLIDefinition(
        id=f"sli-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        service_id=payload.service_id,
        device_id=payload.device_id,
        name=payload.name.strip(),
        metric_type=payload.metric_type.upper(),
        unit=payload.unit,
        evaluation_window_days=payload.evaluation_window_days,
        warning_threshold=payload.warning_threshold,
        critical_threshold=payload.critical_threshold,
        owner_user_id=current_user.id,
    )
    db.add(sli)
    OutboxService.emit_and_commit(
        db=db, event_type="reliability.updated", resource_type="SLIDefinition", resource_id=sli.id,
        actor_user=current_user, organization_id=org_id, payload={"id": sli.id, "name": sli.name},
        required_permission="slo.read",
    )
    return {"id": sli.id, "organization_id": org_id, "name": sli.name, "metric_type": sli.metric_type}


@router.post("/reliability/slos", status_code=status.HTTP_201_CREATED)
def create_slo(
    payload: SLOCreateRequest,
    current_user: User = Depends(require_permission("slo.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    sli = assert_org_resource(db.query(SLIDefinition).filter(SLIDefinition.id == payload.sli_id).first(), org_id, "SLIDefinition")
    if payload.is_contractual_sla and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only ADMIN may designate a contractual SLA; Operators may create technical SLOs.",
        )
    slo = SLORecord(
        id=f"slo-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        sli_id=sli.id,
        service_id=payload.service_id or sli.service_id,
        name=payload.name.strip(),
        target_pct=payload.target_pct,
        is_contractual_sla=payload.is_contractual_sla,
        contractual_sla_approved_by=current_user.username if payload.is_contractual_sla else None,
        owner_user_id=current_user.id,
        status="ACTIVE",
    )
    db.add(slo)
    OutboxService.emit_and_commit(
        db=db, event_type="reliability.updated", resource_type="SLORecord", resource_id=slo.id,
        actor_user=current_user, organization_id=org_id, payload={"id": slo.id, "name": slo.name, "target_pct": slo.target_pct},
        required_permission="slo.read",
    )
    return {
        "id": slo.id, "organization_id": org_id, "name": slo.name,
        "target_pct": slo.target_pct, "is_contractual_sla": slo.is_contractual_sla,
    }


@router.post("/reliability/slos/{slo_id}/evaluate")
def evaluate_slo(
    slo_id: str,
    current_user: User = Depends(require_permission("slo.manage")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    slo = assert_org_resource(db.query(SLORecord).filter(SLORecord.id == slo_id).first(), org_id, "SLORecord")
    sli = assert_org_resource(db.query(SLIDefinition).filter(SLIDefinition.id == slo.sli_id).first(), org_id, "SLIDefinition")

    now = utc_now()
    window_start = now - timedelta(days=sli.evaluation_window_days)
    actual_val: Optional[float] = None
    compliance_pct: Optional[float] = None
    err_budget_rem: Optional[float] = None
    burn_rate: Optional[float] = None
    breached = False
    insufficient = False
    details = {}

    if sli.metric_type in ("CAPACITY_HEADROOM", "READ_LATENCY", "WRITE_LATENCY", "TELEMETRY_FRESHNESS"):
        q = db.query(Telemetry).filter(Telemetry.timestamp >= window_start)
        if sli.device_id:
            q = q.filter(Telemetry.device_id == sli.device_id)
        rows = q.order_by(Telemetry.timestamp.desc()).limit(1000).all()
        if not rows:
            insufficient = True
            details = {"reason": "No telemetry samples found in evaluation window"}
        else:
            if sli.metric_type == "CAPACITY_HEADROOM":
                vals = [max(0.0, 100.0 - float(r.used_pct)) for r in rows if r.used_pct is not None]
                good = sum(1 for v in vals if v >= sli.critical_threshold)
            elif sli.metric_type == "READ_LATENCY":
                vals = [float(r.read_latency_ms) for r in rows if r.read_latency_ms is not None]
                good = sum(1 for v in vals if v <= sli.critical_threshold)
            elif sli.metric_type == "WRITE_LATENCY":
                vals = [float(r.write_latency_ms) for r in rows if r.write_latency_ms is not None]
                good = sum(1 for v in vals if v <= sli.critical_threshold)
            else:
                age_hours = (now - rows[0].timestamp).total_seconds() / 3600.0
                vals = [age_hours]
                good = 1 if age_hours <= sli.critical_threshold else 0

            if not vals:
                insufficient = True
                details = {"reason": "Metric column empty in telemetry rows"}
            else:
                actual_val = round(sum(vals) / len(vals), 4)
                compliance_pct = round((good / len(vals)) * 100.0, 4)
                allowed_bad = max(1e-6, 100.0 - slo.target_pct)
                actual_bad = max(0.0, 100.0 - compliance_pct)
                err_budget_rem = round(max(-100.0, ((allowed_bad - actual_bad) / allowed_bad) * 100.0), 2)
                burn_rate = round(actual_bad / allowed_bad, 3)
                breached = compliance_pct < slo.target_pct
                details = {"samples": len(vals), "good_samples": good}
    elif sli.metric_type == "BACKUP_FRESHNESS":
        events = (
            db.query(BackupEvent)
            .filter(BackupEvent.organization_id == org_id, BackupEvent.completed_at >= window_start)
            .all()
        )
        if not events:
            insufficient = True
            details = {"reason": "No backup events recorded in evaluation window"}
        else:
            good = sum(1 for e in events if e.status == "SUCCESS")
            actual_val = round((good / len(events)) * 100.0, 2)
            compliance_pct = actual_val
            allowed_bad = max(1e-6, 100.0 - slo.target_pct)
            actual_bad = max(0.0, 100.0 - compliance_pct)
            err_budget_rem = round(max(-100.0, ((allowed_bad - actual_bad) / allowed_bad) * 100.0), 2)
            burn_rate = round(actual_bad / allowed_bad, 3)
            breached = compliance_pct < slo.target_pct
            details = {"backup_events": len(events), "successful": good}
    else:
        insufficient = True
        details = {"reason": f"Unsupported metric_type '{sli.metric_type}'"}

    ev = SLOEvaluation(
        id=f"sloev-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        slo_id=slo.id,
        actual_sli_value=actual_val,
        compliance_pct=compliance_pct,
        error_budget_remaining_pct=err_budget_rem,
        burn_rate=burn_rate,
        breached=breached,
        insufficient_data=insufficient,
        details_json=json.dumps(details),
    )
    db.add(ev)
    OutboxService.emit_and_commit(
        db=db, event_type="reliability.evaluated", resource_type="SLOEvaluation", resource_id=ev.id,
        actor_user=current_user, organization_id=org_id,
        payload={"slo_id": slo.id, "breached": breached, "insufficient_data": insufficient, "compliance_pct": compliance_pct},
        required_permission="slo.read",
    )
    return {
        "id": ev.id,
        "slo_id": slo.id,
        "actual_sli_value": ev.actual_sli_value,
        "compliance_pct": ev.compliance_pct,
        "error_budget_remaining_pct": ev.error_budget_remaining_pct,
        "burn_rate": ev.burn_rate,
        "breached": ev.breached,
        "insufficient_data": ev.insufficient_data,
        "details": details,
    }


@router.get("/enterprise-incidents")
def list_enterprise_incidents(
    current_user: User = Depends(require_permission("incidents.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(EnterpriseIncident)
        .filter(EnterpriseIncident.organization_id == org_id)
        .order_by(EnterpriseIncident.created_at.desc())
        .all()
    )
    return {
        "organization_id": org_id,
        "incidents": [
            {
                "id": i.id, "title": i.title, "category": i.category, "severity": i.severity,
                "status": i.status, "linked_device_id": i.linked_device_id,
                "linked_service_id": i.linked_service_id, "severity_policy_reason": i.severity_policy_reason,
                "version": i.version, "created_by": i.created_by,
                "created_at": i.created_at.isoformat() if i.created_at else None,
                "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
            }
            for i in rows
        ],
    }


@router.post("/enterprise-incidents", status_code=status.HTTP_201_CREATED)
def create_enterprise_incident(
    payload: IncidentCreateRequest,
    current_user: User = Depends(require_permission("incidents.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    sev = (payload.severity or "").upper()
    policy_reason = payload.severity_policy_reason
    if sev not in ("SEV-1", "SEV-2", "SEV-3", "SEV-4"):
        if "SLO_BREACH" in payload.category.upper() or "OUTAGE" in payload.title.upper():
            sev = "SEV-1"
            policy_reason = policy_reason or "Policy: SLO breach or service outage classified as SEV-1"
        elif "CAPACITY" in payload.category.upper():
            sev = "SEV-2"
            policy_reason = policy_reason or "Policy: Storage capacity risk classified as SEV-2"
        else:
            sev = "SEV-3"
            policy_reason = policy_reason or "Policy: Default operational incident SEV-3"

    inc = EnterpriseIncident(
        id=f"inc-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        title=payload.title.strip(),
        category=payload.category.upper(),
        severity=sev,
        status="OPEN",
        owner_user_id=current_user.id,
        linked_device_id=payload.linked_device_id,
        linked_service_id=payload.linked_service_id,
        severity_policy_reason=policy_reason,
        evidence_json=payload.evidence_json,
        created_by=current_user.username,
    )
    db.add(inc)
    db.add(
        IncidentTimelineEvent(
            id=f"ite-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            incident_id=inc.id,
            event_type="CREATED",
            actor_username=current_user.username,
            note=f"Incident created ({sev}): {policy_reason}",
        )
    )
    OutboxService.emit_and_commit(
        db=db, event_type="incident.created", resource_type="EnterpriseIncident", resource_id=inc.id,
        actor_user=current_user, organization_id=org_id,
        payload={"id": inc.id, "title": inc.title, "severity": inc.severity, "status": inc.status},
        required_permission="incidents.read",
    )
    return {"id": inc.id, "organization_id": org_id, "severity": inc.severity, "status": inc.status, "title": inc.title}


@router.post("/enterprise-incidents/{inc_id}/transition")
def transition_enterprise_incident(
    inc_id: str,
    payload: IncidentTransitionRequest,
    current_user: User = Depends(require_permission("incidents.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    inc = assert_org_resource(db.query(EnterpriseIncident).filter(EnterpriseIncident.id == inc_id).first(), org_id, "EnterpriseIncident")
    target = payload.target_status.upper()
    allowed = VALID_INCIDENT_TRANSITIONS.get(inc.status, set())
    if target not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid transition {inc.status} -> {target}. Allowed: {sorted(allowed)}")

    old = inc.status
    inc.status = target
    inc.version += 1
    if target == "MITIGATING" and payload.note:
        inc.mitigation_notes = payload.note
    if target == "RESOLVED":
        inc.resolved_at = utc_now()
        if payload.note:
            inc.resolution_notes = payload.note
    if target == "CLOSED":
        inc.closed_at = utc_now()

    db.add(
        IncidentTimelineEvent(
            id=f"ite-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            incident_id=inc.id,
            event_type=f"STATE_{target}",
            actor_username=current_user.username,
            note=payload.note or f"Transitioned {old} -> {target}",
        )
    )
    OutboxService.emit_and_commit(
        db=db, event_type="incident.updated", resource_type="EnterpriseIncident", resource_id=inc.id,
        actor_user=current_user, organization_id=org_id,
        payload={"id": inc.id, "status": inc.status, "version": inc.version},
        required_permission="incidents.read",
    )
    return {"id": inc.id, "status": inc.status, "version": inc.version}


@router.get("/enterprise-incidents/{inc_id}/timeline")
def get_incident_timeline(
    inc_id: str,
    current_user: User = Depends(require_permission("incidents.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    assert_org_resource(db.query(EnterpriseIncident).filter(EnterpriseIncident.id == inc_id).first(), org_id, "EnterpriseIncident")
    events = (
        db.query(IncidentTimelineEvent)
        .filter(IncidentTimelineEvent.incident_id == inc_id, IncidentTimelineEvent.organization_id == org_id)
        .order_by(IncidentTimelineEvent.created_at.asc())
        .all()
    )
    pm = db.query(IncidentPostmortem).filter(IncidentPostmortem.incident_id == inc_id, IncidentPostmortem.organization_id == org_id).first()
    return {
        "incident_id": inc_id,
        "timeline": [
            {
                "id": e.id, "event_type": e.event_type, "actor_username": e.actor_username,
                "note": e.note, "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
        "postmortem": {
            "id": pm.id, "impact_summary": pm.impact_summary, "root_cause_findings": pm.root_cause_findings,
            "resolution_summary": pm.resolution_summary, "preventive_actions": pm.preventive_actions,
        } if pm else None,
    }


@router.post("/enterprise-incidents/{inc_id}/postmortem", status_code=status.HTTP_201_CREATED)
def upsert_incident_postmortem(
    inc_id: str,
    payload: PostmortemRequest,
    current_user: User = Depends(require_permission("incidents.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    inc = assert_org_resource(db.query(EnterpriseIncident).filter(EnterpriseIncident.id == inc_id).first(), org_id, "EnterpriseIncident")
    pm = db.query(IncidentPostmortem).filter(IncidentPostmortem.incident_id == inc.id).first()
    if pm:
        pm.impact_summary = payload.impact_summary
        pm.timeline_summary = payload.timeline_summary
        pm.root_cause_findings = payload.root_cause_findings
        pm.contributing_factors = payload.contributing_factors
        pm.detection_method = payload.detection_method
        pm.resolution_summary = payload.resolution_summary
        pm.preventive_actions = payload.preventive_actions
        pm.follow_up_owner = payload.follow_up_owner
    else:
        pm = IncidentPostmortem(
            id=f"pm-{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            incident_id=inc.id,
            impact_summary=payload.impact_summary,
            timeline_summary=payload.timeline_summary,
            root_cause_findings=payload.root_cause_findings,
            contributing_factors=payload.contributing_factors,
            detection_method=payload.detection_method,
            resolution_summary=payload.resolution_summary,
            preventive_actions=payload.preventive_actions,
            follow_up_owner=payload.follow_up_owner,
            created_by=current_user.username,
        )
        db.add(pm)
    OutboxService.emit_and_commit(
        db=db, event_type="incident.postmortem_saved", resource_type="IncidentPostmortem", resource_id=pm.id,
        actor_user=current_user, organization_id=org_id,
        payload={"incident_id": inc.id, "postmortem_id": pm.id},
        required_permission="incidents.read",
    )
    return {"id": pm.id, "incident_id": inc.id, "impact_summary": pm.impact_summary}
