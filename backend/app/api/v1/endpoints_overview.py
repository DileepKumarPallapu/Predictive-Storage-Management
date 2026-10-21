from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, Alert, Recommendation, RiskAssessment

router = APIRouter()

@router.get("/overview")
def get_executive_overview(db: Session = Depends(get_db)):
    """
    Returns fleet-wide executive storage resilience summary:
    Total, used, free capacity, utilization %, shortest runway, highest risk,
    last collection timestamp, risk timeline, and data mode provenance.
    """
    devices = db.query(Device).all()
    device_count = len(devices)

    total_capacity = 0
    total_used = 0
    total_free = 0

    latest_timestamps = []
    min_runway = 999.0
    highest_risk_level = "NOMINAL"
    highest_risk_device = None

    for d in devices:
        total_capacity += d.total_capacity_bytes
        latest_t = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == d.id)
            .order_by(Telemetry.timestamp.desc())
            .first()
        )
        if latest_t:
            total_used += latest_t.used_bytes
            total_free += latest_t.free_bytes
            latest_timestamps.append(latest_t.timestamp)
        else:
            total_used += int(d.total_capacity_bytes * 0.70)
            total_free += int(d.total_capacity_bytes * 0.30)

        latest_r = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.device_id == d.id)
            .order_by(RiskAssessment.computed_at.desc())
            .first()
        )
        if latest_r:
            if latest_r.runway_hours_estimate < min_runway:
                min_runway = latest_r.runway_hours_estimate
            if latest_r.risk_level == "CRITICAL":
                highest_risk_level = "CRITICAL"
                highest_risk_device = d.id
            elif latest_r.risk_level == "ELEVATED" and highest_risk_level != "CRITICAL":
                highest_risk_level = "ELEVATED"
                highest_risk_device = d.id

    if min_runway == 999.0:
        min_runway = 46.5
        highest_risk_level = "CRITICAL"
        highest_risk_device = "vol-nvme-tier1-db"

    fleet_util_pct = round((total_used / total_capacity * 100.0), 2) if total_capacity > 0 else 0.0
    last_collection = max(latest_timestamps) if latest_timestamps else datetime.now(timezone.utc)

    # Risk timeline items
    alerts = db.query(Alert).filter(Alert.status == "ACTIVE").order_by(Alert.triggered_at.desc()).limit(5).all()
    timeline = [
        {
            "id": a.id,
            "timestamp": a.triggered_at.isoformat(),
            "category": a.category,
            "severity": a.severity,
            "title": a.title,
            "device_id": a.device_id,
            "is_forecasted": False
        }
        for a in alerts
    ]

    # Add projected breach marker
    timeline.append({
        "id": "projected-breach-nvme",
        "timestamp": (datetime.now(timezone.utc)).isoformat(),
        "category": "PROJECTED_BREACH",
        "severity": "CRITICAL",
        "title": f"Forecasted 90% Capacity Breach on {highest_risk_device} within {min_runway:.1f}h",
        "device_id": highest_risk_device,
        "is_forecasted": True
    })

    # Top fleet recommendation
    top_rec = (
        db.query(Recommendation)
        .order_by(Recommendation.rank.asc(), Recommendation.utility_score.desc())
        .first()
    )
    rec_summary = None
    if top_rec:
        rec_summary = {
            "id": top_rec.id,
            "device_id": top_rec.device_id,
            "title": top_rec.title,
            "action_type": top_rec.action_type,
            "utility_score": top_rec.utility_score,
            "estimated_runway_gain_hours": top_rec.estimated_runway_gain_hours,
            "approval_status": top_rec.approval_status
        }

    return {
        "total_capacity_bytes": total_capacity,
        "total_used_bytes": total_used,
        "total_free_bytes": total_free,
        "capacity_utilization_pct": fleet_util_pct,
        "estimated_reserve_runway_hours": round(min_runway, 1),
        "monitored_device_count": device_count,
        "highest_current_risk": {
            "level": highest_risk_level,
            "device_id": highest_risk_device
        },
        "last_successful_collection": last_collection.isoformat(),
        "data_mode_label": "SYNTHETIC DEMO DATA",
        "is_synthetic": True,
        "risk_timeline": timeline,
        "top_recommendation": rec_summary
    }
