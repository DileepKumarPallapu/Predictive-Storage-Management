from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, Recommendation
from app.schemas.payloads import RecommendationItem, RecommendationApprovalRequest
from app.services.recommendation_engine import RecommendationEngine
from app.services.action_planner import ActionPlannerService
from app.services.capacity_runway_engine import CapacityRunwayEngine
from app.services.performance_risk_engine import PerformanceRiskEngine
from app.services.risk_engine import RiskEngine
from app.services.audit_service import AuditService
from app.ml.models import run_forecast

router = APIRouter()

class PlanningEvaluateRequest(BaseModel):
    device_id: str

@router.post("/planning/evaluate")
def evaluate_action_planning(payload: PlanningEvaluateRequest, db: Session = Depends(get_db)):
    """
    Evaluates candidate preventive interventions using the Lead-Time-Aware Action Planner.
    Filters candidate actions against operational lead times (T_action < T_breach)
    and tail latency safety bounds before computing multi-objective utility rankings.
    """
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    records = db.query(Telemetry).filter(Telemetry.device_id == payload.device_id).order_by(Telemetry.timestamp.asc()).all()
    if not records:
        raise HTTPException(status_code=400, detail="No telemetry available for planning")

    latest = records[-1]
    telemetry_dicts = [
        {
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "used_bytes": r.used_bytes,
            "free_bytes": r.free_bytes,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "throughput_mb_s": r.throughput_mb_s,
            "latency_p95_ms": r.latency_p95_ms,
            "queue_depth": r.queue_depth,
            "is_synthetic": r.is_synthetic
        }
        for r in records
    ]

    device_meta = {
        "id": device.id,
        "tier": device.tier,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms,
        "current_throughput_mb_s": latest.throughput_mb_s
    }

    # 1. Capacity Runway
    cap_forecast = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    runway_res = CapacityRunwayEngine.evaluate_runway(
        device_id=payload.device_id,
        total_capacity_bytes=device.total_capacity_bytes,
        telemetry_history=telemetry_dicts,
        forecast_contract=cap_forecast,
        critical_threshold_pct=device.critical_threshold_pct,
        warning_threshold_pct=device.warning_threshold_pct
    )

    # 2. Performance Risk
    perf_res = PerformanceRiskEngine.evaluate_performance_risk(
        device_id=payload.device_id,
        device_metadata=device_meta,
        telemetry_history=telemetry_dicts
    )

    # 3. Action Planning
    plan_result = ActionPlannerService.evaluate_and_plan(
        device_id=payload.device_id,
        device_metadata=device_meta,
        runway_result=runway_res.model_dump(),
        perf_result=perf_res.model_dump()
    )

    return plan_result

@router.get("/devices/{device_id}/recommendations", response_model=List[RecommendationItem])
def get_recommendations(device_id: str, db: Session = Depends(get_db)):
    """Retrieves ranked recommendations for a specific storage device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    existing = db.query(Recommendation).filter(Recommendation.device_id == device_id).order_by(Recommendation.rank.asc()).all()
    if existing:
        return [
            RecommendationItem(
                id=r.id,
                device_id=r.device_id,
                action_type=r.action_type,
                title=r.title,
                rationale=r.rationale,
                rank=r.rank,
                utility_score=r.utility_score,
                estimated_runway_gain_hours=r.estimated_runway_gain_hours,
                hard_constraints_checked=r.hard_constraints_checked,
                approval_status=r.approval_status,
                reviewed_by=r.reviewed_by,
                review_notes=r.review_notes,
                created_at=r.created_at
            )
            for r in existing
        ]

    # Dynamically compute
    records = db.query(Telemetry).filter(Telemetry.device_id == device_id).order_by(Telemetry.timestamp.asc()).all()
    if not records:
        return []

    latest = records[-1]
    telemetry_dicts = [
        {
            "timestamp": r.timestamp,
            "device_id": r.device_id,
            "used_bytes": r.used_bytes,
            "free_bytes": r.free_bytes,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "throughput_mb_s": r.throughput_mb_s,
            "latency_p95_ms": r.latency_p95_ms,
            "queue_depth": r.queue_depth,
            "is_synthetic": r.is_synthetic
        }
        for r in records
    ]

    base_forecast = run_forecast(
        telemetry_records=telemetry_dicts,
        target_metric="used_bytes",
        model_type="lightgbm_quantile",
        horizon_hours=72,
        total_capacity=float(device.total_capacity_bytes)
    )

    device_meta = {
        "id": device.id,
        "total_capacity_bytes": device.total_capacity_bytes,
        "warning_threshold_pct": device.warning_threshold_pct,
        "critical_threshold_pct": device.critical_threshold_pct,
        "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        "current_used_bytes": latest.used_bytes,
        "current_latency_p95_ms": latest.latency_p95_ms
    }

    risk_eval = RiskEngine.assess_device_risk(
        device_id=device_id,
        device_meta=device_meta,
        forecast_result=base_forecast
    )

    ranked = RecommendationEngine.evaluate_and_rank_interventions(
        device_id=device_id,
        device_meta=device_meta,
        base_forecast=base_forecast,
        risk_profile=risk_eval
    )

    # Persist in DB
    results = []
    for r in ranked:
        rec = Recommendation(
            id=r["id"],
            device_id=device_id,
            action_type=r["action_type"],
            title=r["title"],
            rationale=r["rationale"],
            rank=r["rank"],
            utility_score=r["utility_score"],
            estimated_runway_gain_hours=r["estimated_runway_gain_hours"],
            hard_constraints_checked=True,
            approval_status="PENDING_REVIEW"
        )
        db.add(rec)
        results.append(rec)
    db.commit()

    return [
        RecommendationItem(
            id=r.id,
            device_id=r.device_id,
            action_type=r.action_type,
            title=r.title,
            rationale=r.rationale,
            rank=r.rank,
            utility_score=r.utility_score,
            estimated_runway_gain_hours=r.estimated_runway_gain_hours,
            hard_constraints_checked=r.hard_constraints_checked,
            approval_status=r.approval_status,
            reviewed_by=r.reviewed_by,
            review_notes=r.review_notes,
            created_at=r.created_at
        )
        for r in results
    ]

@router.post("/recommendations/{rec_id}/approve")
def approve_recommendation(rec_id: str, payload: RecommendationApprovalRequest, db: Session = Depends(get_db)):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.approval_status = "APPROVED_SHADOW"
    rec.reviewed_by = "lead_storage_admin"
    rec.review_notes = payload.notes or "Approved for dry-run shadow simulation."
    db.commit()

    AuditService.log_event(
        db=db,
        action="APPROVE_RECOMMENDATION",
        target_type="RECOMMENDATION",
        target_id=rec_id,
        details={"status": rec.approval_status, "notes": rec.review_notes}
    )

    return {"message": "Recommendation approved in SHADOW MODE. Physical storage unchanged.", "status": rec.approval_status}

@router.post("/recommendations/{rec_id}/reject")
def reject_recommendation(rec_id: str, payload: RecommendationApprovalRequest, db: Session = Depends(get_db)):
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    rec.approval_status = "REJECTED"
    rec.reviewed_by = "lead_storage_admin"
    rec.review_notes = payload.notes or "Rejected by administrator."
    db.commit()

    AuditService.log_event(
        db=db,
        action="REJECT_RECOMMENDATION",
        target_type="RECOMMENDATION",
        target_id=rec_id,
        details={"status": rec.approval_status, "notes": rec.review_notes}
    )

    return {"message": "Recommendation rejected.", "status": rec.approval_status}
