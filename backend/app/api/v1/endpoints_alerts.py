from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Alert
from app.schemas.payloads import AlertItem
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/alerts", response_model=List[AlertItem])
def list_alerts(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if category:
        query = query.filter(Alert.category == category)
    if severity:
        query = query.filter(Alert.severity == severity)
    if status:
        query = query.filter(Alert.status == status)

    alerts = query.order_by(Alert.triggered_at.desc()).all()
    return [
        AlertItem(
            id=a.id,
            device_id=a.device_id,
            category=a.category,
            severity=a.severity,
            title=a.title,
            message=a.message,
            status=a.status,
            triggered_at=a.triggered_at,
            resolved_at=a.resolved_at
        )
        for a in alerts
    ]

@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    a.status = "ACKNOWLEDGED"
    db.commit()

    AuditService.log_event(
        db=db,
        action="ACKNOWLEDGE_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        details={"status": a.status}
    )

    return {"message": "Alert marked as acknowledged", "alert_id": alert_id, "status": a.status}

@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    a = db.query(Alert).filter(Alert.id == alert_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Alert not found")

    a.status = "RESOLVED"
    a.resolved_at = datetime.now(timezone.utc)
    db.commit()

    AuditService.log_event(
        db=db,
        action="RESOLVE_ALERT",
        target_type="ALERT",
        target_id=alert_id,
        details={"status": a.status, "resolved_at": a.resolved_at.isoformat()}
    )

    return {"message": "Alert marked as resolved", "alert_id": alert_id, "status": a.status}
