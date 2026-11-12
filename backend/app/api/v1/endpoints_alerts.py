import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Alert, Device, Telemetry, Forecast, User, OperationalAssignment
from app.schemas.payloads import AlertItem
from app.services.audit_service import AuditService
from app.services.data_quality_service import _parse_iso_timestamp
from app.ml.sklearn_engine import CapacityMLEngine
from app.auth.security import get_current_user, require_role
from app.auth.permissions import require_permission

router = APIRouter()


class AlertResolveRequest(BaseModel):
    resolution_details: Optional[str] = "Resolved by operator after inspection"


def _serialize_alert(a: Alert) -> AlertItem:
    try:
        ev = json.loads(getattr(a, "supporting_evidence_json", None) or "{}")
    except Exception:
        ev = {}
    return AlertItem(
        id=a.id,
        device_id=a.device_id,
        category=a.category,
        severity=a.severity,
        title=a.title,
        message=a.message,
        status=a.status,
        triggered_at=a.triggered_at,
        acknowledged_by=getattr(a, "acknowledged_by", None),
        acknowledged_at=getattr(a, "acknowledged_at", None),
        resolved_at=a.resolved_at,
        resolution_details=getattr(a, "resolution_details", None),
        supporting_evidence=ev,
    )


def _create_alert_if_absent(
    db: Session,
    device_id: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    evidence: Dict[str, Any]
) -> Optional[Alert]:
    existing = (
        db.query(Alert)
        .filter(
            Alert.device_id == device_id,
            Alert.category == category,
            Alert.status.in_(["ACTIVE", "ACKNOWLEDGED"])
        )
        .first()
    )
    if existing:
        existing.severity = severity
        existing.message = message
        existing.supporting_evidence_json = json.dumps(evidence)
        return None

    a = Alert(
        id=f"alert-{uuid.uuid4().hex[:10]}",
        device_id=device_id,
        category=category,
        severity=severity,
        title=title,
        message=message,
        status="ACTIVE",
        triggered_at=datetime.now(timezone.utc),
        supporting_evidence_json=json.dumps(evidence),
    )
    db.add(a)
    return a


def evaluate_device_risk_and_alerts(db: Session, storage_id: str) -> Dict[str, Any]:
    """
    Evaluates real stored telemetry, thresholds, forecasts, runway, and staleness
    to compute risk category (NORMAL / WARNING / CRITICAL) and persist traceable alerts.
    Never generates alerts from invented measurements.
    """
    device = db.query(Device).filter(Device.id == storage_id).first()
    if not device:
        raise ValueError(f"Storage resource '{storage_id}' not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == storage_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    created_alerts: List[Alert] = []
    findings: List[Dict[str, Any]] = []
    risk_category = "NORMAL"

    now = datetime.now(timezone.utc)
    if not records:
        risk_category = "WARNING"
        ev = {"telemetry_count": 0}
        a = _create_alert_if_absent(
            db, storage_id, "TELEMETRY_STALE", "WARNING",
            f"Missing Telemetry on {device.name}",
            "No telemetry records exist for this storage resource.",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "MISSING_TELEMETRY", "severity": "WARNING", "evidence": ev})
        db.commit()
        return {
            "storage_id": storage_id,
            "risk_category": risk_category,
            "findings": findings,
            "new_alerts_created": len(created_alerts),
        }

    latest = records[-1]
    latest_ts = latest.timestamp.replace(tzinfo=timezone.utc) if latest.timestamp.tzinfo is None else latest.timestamp
    age_hours = (now - latest_ts).total_seconds() / 3600.0

    # 1. Stale telemetry check (> 24h)
    if age_hours > 24.0:
        if risk_category == "NORMAL":
            risk_category = "WARNING"
        ev = {"latest_timestamp": latest_ts.isoformat(), "age_hours": round(age_hours, 1)}
        a = _create_alert_if_absent(
            db, storage_id, "TELEMETRY_STALE", "WARNING",
            f"Stale Telemetry Detected on {device.name}",
            f"Latest observation is {age_hours:.1f} hours old (> 24h threshold).",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "STALE_TELEMETRY", "severity": "WARNING", "evidence": ev})

    # 2. Current capacity utilization check
    util = float(latest.utilization_pct)
    if util >= device.critical_threshold_pct:
        risk_category = "CRITICAL"
        ev = {"utilization_pct": util, "critical_threshold_pct": device.critical_threshold_pct, "timestamp": latest_ts.isoformat()}
        a = _create_alert_if_absent(
            db, storage_id, "CAPACITY_CRITICAL", "CRITICAL",
            f"Critical Capacity Threshold Breached ({util:.1f}%)",
            f"Actual utilization {util:.1f}% >= critical threshold {device.critical_threshold_pct}%.",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "UTILIZATION_CRITICAL", "severity": "CRITICAL", "evidence": ev})
    elif util >= device.warning_threshold_pct:
        if risk_category == "NORMAL":
            risk_category = "WARNING"
        ev = {"utilization_pct": util, "warning_threshold_pct": device.warning_threshold_pct, "timestamp": latest_ts.isoformat()}
        a = _create_alert_if_absent(
            db, storage_id, "CAPACITY_RISK", "WARNING",
            f"Warning Capacity Threshold Reached ({util:.1f}%)",
            f"Actual utilization {util:.1f}% >= warning threshold {device.warning_threshold_pct}%.",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "UTILIZATION_WARNING", "severity": "WARNING", "evidence": ev})

    # 3. Performance threshold check (only if actual non-zero latency exists)
    if latest.latency_p95_ms is not None and latest.latency_p95_ms > device.max_acceptable_latency_ms:
        if risk_category == "NORMAL":
            risk_category = "WARNING"
        ev = {"latency_p95_ms": latest.latency_p95_ms, "max_acceptable_latency_ms": device.max_acceptable_latency_ms, "timestamp": latest_ts.isoformat()}
        a = _create_alert_if_absent(
            db, storage_id, "LATENCY_SLA", "WARNING",
            f"Latency Threshold Breached ({latest.latency_p95_ms:.1f} ms)",
            f"Observed latency {latest.latency_p95_ms:.1f} ms exceeds SLA ceiling {device.max_acceptable_latency_ms:.1f} ms.",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "LATENCY_BREACH", "severity": "WARNING", "evidence": ev})

    # 4. Sudden consumption growth spike (recent step vs trailing median)
    if len(records) >= 12:
        deltas = [records[i].used_bytes - records[i - 1].used_bytes for i in range(1, len(records))]
        latest_delta = deltas[-1]
        pos_deltas = [d for d in deltas[:-1] if d > 0]
        if pos_deltas:
            avg_pos = sum(pos_deltas) / len(pos_deltas)
            if latest_delta > max(avg_pos * 4.0, 5 * (1024 ** 3)):
                if risk_category == "NORMAL":
                    risk_category = "WARNING"
                ev = {
                    "latest_step_growth_gb": round(latest_delta / (1024 ** 3), 2),
                    "baseline_step_growth_gb": round(avg_pos / (1024 ** 3), 2),
                    "timestamp": latest_ts.isoformat(),
                }
                a = _create_alert_if_absent(
                    db, storage_id, "ABNORMAL_GROWTH", "WARNING",
                    f"Abnormal Consumption Spike (+{ev['latest_step_growth_gb']} GB)",
                    f"Latest consumption jump (+{ev['latest_step_growth_gb']} GB) exceeds 4x trailing positive baseline.",
                    ev
                )
                if a:
                    created_alerts.append(a)
                findings.append({"rule": "SUDDEN_GROWTH_SPIKE", "severity": "WARNING", "evidence": ev})

    # 5. Forecasted breach & capacity runway check
    latest_forecast = (
        db.query(Forecast)
        .filter(Forecast.device_id == storage_id, Forecast.daily_predictions_json.isnot(None))
        .order_by(Forecast.generated_at.desc())
        .first()
    )
    daily_preds = json.loads(latest_forecast.daily_predictions_json) if latest_forecast and latest_forecast.daily_predictions_json else None
    runway = CapacityMLEngine.calculate_capacity_runway(device, int(latest.used_bytes), daily_predictions=daily_preds, records=records)

    est_days = runway.get("estimated_days_until_threshold")
    if (latest_forecast and getattr(latest_forecast, "projected_capacity_breach", False)) or (est_days is not None and est_days <= 30.0):
        sev = "CRITICAL" if (est_days is not None and est_days <= 7.0) else "WARNING"
        if sev == "CRITICAL":
            risk_category = "CRITICAL"
        elif risk_category == "NORMAL":
            risk_category = "WARNING"
        ev = {
            "estimated_days_until_threshold": est_days,
            "estimated_threshold_date": runway.get("estimated_threshold_date"),
            "forecast_id": latest_forecast.id if latest_forecast else None,
            "projected_capacity_breach": bool(latest_forecast and latest_forecast.projected_capacity_breach),
        }
        a = _create_alert_if_absent(
            db, storage_id, "FORECAST_BREACH", sev,
            f"Projected Threshold Breach in {est_days} Days" if est_days is not None else "Projected Capacity Breach",
            f"Runway analysis projects threshold breach in {est_days} days at current consumption rate.",
            ev
        )
        if a:
            created_alerts.append(a)
        findings.append({"rule": "FORECAST_RUNWAY_RISK", "severity": sev, "evidence": ev})

    # Update device status coherently
    device.status = "CRITICAL" if risk_category == "CRITICAL" else ("WARNING" if risk_category == "WARNING" else "HEALTHY")
    db.commit()

    return {
        "storage_id": storage_id,
        "risk_category": risk_category,
        "runway": runway,
        "findings": findings,
        "new_alerts_created": len(created_alerts),
        "created_alert_ids": [a.id for a in created_alerts],
    }


class AlertAssignRequest(BaseModel):
    assigned_to: str
    notes: Optional[str] = ""


@router.get("/alerts", response_model=List[AlertItem])
def list_alerts(
    storage_id: Optional[str] = Query(None, description="Filter by storage_id / device_id"),
    device_id: Optional[str] = Query(None, description="Alias for storage_id"),
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(require_permission("alerts.read")),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    target_id = storage_id or device_id
    if target_id:
        query = query.filter(Alert.device_id == target_id)
    if category:
        query = query.filter(Alert.category == category)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)
    if start_date:
        dt_start = _parse_iso_timestamp(start_date)
        if dt_start:
            query = query.filter(Alert.triggered_at >= dt_start)
    if end_date:
        dt_end = _parse_iso_timestamp(end_date)
        if dt_end:
            query = query.filter(Alert.triggered_at <= dt_end)

    alerts = query.order_by(Alert.triggered_at.desc()).all()
    return [_serialize_alert(a) for a in alerts]


@router.post("/alerts/evaluate", tags=["Alerts & Incidents"])
def evaluate_all_alerts(
    current_user: User = Depends(require_permission("risk.evaluate")),
    db: Session = Depends(get_db)
):
    """Runs risk & alert evaluation engine across all monitored storage resources."""
    devices = db.query(Device).filter(Device.tier != "HOST_LOCAL").all()
    summaries = []
    for d in devices:
        summaries.append(evaluate_device_risk_and_alerts(db, d.id))
    return {"evaluated_resources": len(summaries), "results": summaries}


@router.post("/alerts/evaluate/{storage_id}", tags=["Alerts & Incidents"])
def evaluate_single_storage_alerts(
    storage_id: str,
    current_user: User = Depends(require_permission("risk.evaluate")),
    db: Session = Depends(get_db)
):
    """Runs risk & alert evaluation engine for a single storage resource."""
    try:
        return evaluate_device_risk_and_alerts(db, storage_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    current_user: User = Depends(require_permission("alerts.acknowledge")),
    db: Session = Depends(get_db)
):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    a.status = "ACKNOWLEDGED"
    a.acknowledged_by = current_user.username
    a.acknowledged_at = now
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="alert.acknowledged",
        resource_type="alert",
        resource_id=alert_id,
        actor_user=current_user,
        changed_fields=["status", "acknowledged_by", "acknowledged_at"],
        payload=_serialize_alert(a).model_dump(mode="json"),
        required_permission="alerts.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="ACKNOWLEDGE_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        user=current_user.username,
        details={"status": a.status, "acknowledged_by": current_user.username}
    )

    return {
        "message": "Alert marked as acknowledged",
        "alert_id": alert_id,
        "status": a.status,
        "acknowledged_by": a.acknowledged_by,
        "acknowledged_at": now.isoformat(),
    }


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    payload: Optional[AlertResolveRequest] = Body(default=None),
    current_user: User = Depends(require_permission("alerts.resolve")),
    db: Session = Depends(get_db)
):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    details_txt = payload.resolution_details if payload else "Resolved by operator"
    a.status = "RESOLVED"
    a.resolved_at = now
    a.resolution_details = details_txt
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="alert.resolved",
        resource_type="alert",
        resource_id=alert_id,
        actor_user=current_user,
        changed_fields=["status", "resolved_at", "resolution_details"],
        payload=_serialize_alert(a).model_dump(mode="json"),
        required_permission="alerts.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="RESOLVE_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        user=current_user.username,
        details={"status": a.status, "resolved_at": now.isoformat(), "resolution_details": details_txt}
    )

    return {
        "message": "Alert marked as resolved",
        "alert_id": alert_id,
        "status": a.status,
        "resolution_details": details_txt,
    }


@router.post("/alerts/{alert_id}/reopen")
def reopen_alert(
    alert_id: str,
    current_user: User = Depends(require_permission("alerts.reopen")),
    db: Session = Depends(get_db)
):
    """Reopens a previously resolved or acknowledged alert back to ACTIVE state."""
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    prev_status = a.status
    a.status = "ACTIVE"
    a.resolved_at = None
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="alert.reopened",
        resource_type="alert",
        resource_id=alert_id,
        actor_user=current_user,
        changed_fields=["status", "resolved_at"],
        payload=_serialize_alert(a).model_dump(mode="json"),
        required_permission="alerts.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="REOPEN_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        user=current_user.username,
        details={"previous_status": prev_status, "new_status": "ACTIVE"}
    )
    return {"message": "Alert reopened", "alert_id": alert_id, "status": "ACTIVE"}


class AlertEscalateRequest(BaseModel):
    escalation_tier: str = "L2_STORAGE_SRE"
    reason: Optional[str] = "Escalated due to sustained SLA/capacity threshold breach."


@router.post("/alerts/{alert_id}/assign")
def assign_alert(
    alert_id: str,
    payload: AlertAssignRequest,
    current_user: User = Depends(require_permission("alerts.assign")),
    db: Session = Depends(get_db),
):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    assignee = payload.assigned_to.strip()
    if not assignee:
        raise HTTPException(status_code=400, detail="assigned_to is required")

    target_user = db.query(User).filter((User.username == assignee) | (User.id == assignee)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"Assignee user '{assignee}' not found")
    if not target_user.is_active:
        raise HTTPException(status_code=400, detail="Cannot assign alert to an inactive user")

    now = datetime.now(timezone.utc)
    assignment = OperationalAssignment(
        id=f"asgn-{uuid.uuid4().hex[:10]}",
        target_type="ALERT",
        target_id=alert_id,
        assigned_to_user_id=target_user.id,
        assigned_by=current_user.username,
        status="ASSIGNED",
        notes=payload.notes or "",
    )
    db.add(assignment)

    try:
        ev = json.loads(a.supporting_evidence_json or "{}")
    except Exception:
        ev = {}
    ev["assigned_to"] = target_user.username
    ev["assigned_by"] = current_user.username
    ev["assigned_at"] = now.isoformat()
    a.supporting_evidence_json = json.dumps(ev)
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="alert.assigned",
        resource_type="alert",
        resource_id=alert_id,
        actor_user=current_user,
        changed_fields=["assigned_to"],
        payload={
            "alert_id": alert_id,
            "device_id": a.device_id,
            "severity": a.severity,
            "title": a.title,
            "assigned_to": target_user.username,
            "assigned_to_user_id": target_user.id,
            "assigned_by": current_user.username,
        },
        required_permission="alerts.read",
        notify_user_ids=[target_user.id],
        notification_title=f"Alert Assigned: {a.title}",
        notification_message=f"{current_user.username} assigned {a.severity} alert on {a.device_id} to you.",
        notification_severity=("CRITICAL" if a.severity == "CRITICAL" else "WARNING"),
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="ASSIGN_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        user=current_user.username,
        details={"assigned_to": target_user.username, "notes": payload.notes},
    )
    return {
        "message": f"Alert assigned to {target_user.username}",
        "alert_id": alert_id,
        "assigned_to": target_user.username,
        "assigned_by": current_user.username,
        "assignment_id": assignment.id,
        "assigned_at": now.isoformat(),
    }


@router.post("/alerts/{alert_id}/escalate")
def escalate_alert(
    alert_id: str,
    payload: AlertEscalateRequest = Body(default=AlertEscalateRequest()),
    current_user: User = Depends(require_permission("alerts.assign")),
    db: Session = Depends(get_db),
):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.now(timezone.utc)
    a.status = "ESCALATED"
    try:
        ev = json.loads(a.supporting_evidence_json or "{}")
    except Exception:
        ev = {}
    ev["escalation_tier"] = payload.escalation_tier
    ev["escalation_reason"] = payload.reason
    ev["escalated_by"] = current_user.username
    ev["escalated_at"] = now.isoformat()
    a.supporting_evidence_json = json.dumps(ev)
    db.commit()

    AuditService.log_event(
        db=db,
        action="ESCALATE_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        user=current_user.username,
        details={"status": a.status, "escalation_tier": payload.escalation_tier, "reason": payload.reason},
    )
    return {
        "message": f"Alert escalated to {payload.escalation_tier}",
        "alert_id": alert_id,
        "status": a.status,
        "escalation_tier": payload.escalation_tier,
        "escalated_at": now.isoformat(),
    }
