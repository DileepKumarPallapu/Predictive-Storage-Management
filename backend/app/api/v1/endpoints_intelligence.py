import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import require_role
from app.auth.permissions import require_permission
from app.database import SessionLocal, get_db
from app.ml.champion_challenger import ChampionChallengerEngine, SUPPORTED_HORIZON_DAYS
from app.models.entities import (
    BackgroundJob,
    CapacityRiskEvaluation,
    DataReliabilityProfile,
    Device,
    Forecast,
    ModelMetric,
    ModelVersion,
    Telemetry,
    User,
    WorkloadRegimeEvent,
)
from app.services.audit_service import AuditService
from app.services.capacity_risk_engine import CapacityRiskEngine
from app.services.data_reliability_engine import DataReliabilityEngine
from app.services.workload_regime_engine import WorkloadRegimeEngine

router = APIRouter()


class ReliabilityEvalRequest(BaseModel):
    weights: Optional[Dict[str, float]] = None


class V2ForecastRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=180)
    persist: bool = True


class RiskEvalRequest(BaseModel):
    horizon_days: int = Field(default=30, ge=1, le=180)
    safety_threshold_pct: Optional[float] = Field(default=None, ge=10.0, le=99.9)


def _emit_job_stage(
    db: Session,
    job: BackgroundJob,
    stage: str,
    progress_pct: int,
    event_type: str = "model.training_stage",
    extra_payload: Optional[dict] = None,
) -> None:
    from app.realtime.event_bus import OutboxService
    job.status = stage if stage in {"QUEUED", "COMPLETED", "FAILED", "CANCELLED"} else "RUNNING"
    job.stage = stage
    job.progress_pct = progress_pct
    job.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    payload = {
        "job_id": job.id,
        "storage_id": job.storage_id,
        "status": job.status,
        "stage": stage,
        "progress_pct": progress_pct,
        "triggered_by": job.triggered_by,
    }
    if extra_payload:
        payload.update(extra_payload)
    OutboxService.emit_and_commit(
        db,
        event_type=event_type,
        resource_type="ml_job",
        resource_id=job.id,
        actor_username=job.triggered_by,
        actor_role="OPERATOR",
        changed_fields=["status", "stage", "progress_pct"],
        payload=payload,
        required_permission="models.read",
    )


def _run_async_training_job(job_id: str, storage_id: str, username: str) -> None:
    db = SessionLocal()
    try:
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if not job:
            return
        _emit_job_stage(db, job, "VALIDATING_DATA", 15)
        DataReliabilityEngine.evaluate(db, storage_id, persist=False)

        _emit_job_stage(db, job, "PREPARING_FEATURES", 35)
        WorkloadRegimeEngine.analyze(db, storage_id, persist=False)

        _emit_job_stage(db, job, "TRAINING", 60)
        result = ChampionChallengerEngine.train_and_select(db, storage_id, triggered_by=username)

        _emit_job_stage(db, job, "EVALUATING", 82)
        safe_result = {
            "champion_model_version_id": result.get("champion_model_version_id"),
            "champion_family": result.get("champion_family"),
            "champion_model_type": result.get("champion_model_type"),
            "version_tag": result.get("version_tag"),
            "splits": result.get("splits"),
            "reference_benchmark": result.get("reference_benchmark"),
            "data_reliability": result.get("data_reliability"),
            "workload_regime": result.get("workload_regime"),
            "candidates": result.get("candidates"),
        }
        _emit_job_stage(db, job, "SAVING_MODEL", 94)

        job.status = "COMPLETED"
        job.stage = "COMPLETED"
        job.progress_pct = 100
        job.result_json = json.dumps(safe_result)
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        _emit_job_stage(
            db,
            job,
            "COMPLETED",
            100,
            event_type="model.training_completed",
            extra_payload={
                "champion_family": result.get("champion_family"),
                "champion_model_type": result.get("champion_model_type"),
                "version_tag": result.get("version_tag"),
            },
        )
    except Exception as exc:
        job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.stage = "FAILED"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
            _emit_job_stage(
                db,
                job,
                "FAILED",
                job.progress_pct or 0,
                event_type="model.training_failed",
                extra_payload={"error_message": str(exc)},
            )
    finally:
        db.close()


# --- Phase 3: Data Reliability Engine ---

@router.get("/reliability/data/{storage_id}")
def get_data_reliability(
    storage_id: str,
    current_user: User = Depends(require_permission("quality.read")),
    db: Session = Depends(get_db),
):
    try:
        return DataReliabilityEngine.evaluate(db, storage_id, persist=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/reliability/data/{storage_id}")
def evaluate_data_reliability(
    storage_id: str,
    payload: ReliabilityEvalRequest = ReliabilityEvalRequest(),
    current_user: User = Depends(require_permission("quality.process")),
    db: Session = Depends(get_db),
):
    try:
        res = DataReliabilityEngine.evaluate(db, storage_id, custom_weights=payload.weights, persist=True)
        return res
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# --- Phase 4: Workload Regime & Drift Engine ---

@router.get("/workload-regime/{storage_id}")
def get_workload_regime(
    storage_id: str,
    current_user: User = Depends(require_permission("workload.read")),
    db: Session = Depends(get_db),
):
    try:
        analysis = WorkloadRegimeEngine.analyze(db, storage_id, persist=True)
        history = (
            db.query(WorkloadRegimeEvent)
            .filter(WorkloadRegimeEvent.storage_id == storage_id)
            .order_by(WorkloadRegimeEvent.detected_at.desc())
            .limit(10)
            .all()
        )
        analysis["recent_history"] = [
            {
                "id": h.id,
                "regime_label": h.regime_label,
                "event_type": h.event_type,
                "severity": h.severity,
                "confidence": h.confidence,
                "explanation": h.explanation,
                "detected_at": h.detected_at.isoformat() if h.detected_at else None,
            }
            for h in history
        ]
        return analysis
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/workload-regime/{storage_id}")
def trigger_workload_regime(
    storage_id: str,
    current_user: User = Depends(require_permission("workload.analyse")),
    db: Session = Depends(get_db),
):
    try:
        return WorkloadRegimeEngine.analyze(db, storage_id, persist=True)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# --- Phase 5 & 10: Champion-Challenger ML Engine (Sync & Async Jobs) ---

@router.post("/v2/models/train/{storage_id}")
def train_v2_champion_challenger(
    storage_id: str,
    current_user: User = Depends(require_permission("models.train")),
    db: Session = Depends(get_db),
):
    try:
        result = ChampionChallengerEngine.train_and_select(db, storage_id, triggered_by=current_user.username)
        from app.realtime.event_bus import OutboxService
        OutboxService.emit_and_commit(
            db,
            event_type="model.training_completed",
            resource_type="model_version",
            resource_id=result.get("champion_model_version_id") or storage_id,
            actor_user=current_user,
            payload={
                "storage_id": storage_id,
                "champion_family": result.get("champion_family"),
                "champion_model_type": result.get("champion_model_type"),
                "version_tag": result.get("version_tag"),
            },
            required_permission="models.read",
        )
        AuditService.log_event(
            db=db,
            action="V2_CHAMPION_CHALLENGER_TRAINED",
            target_type="DEVICE",
            target_id=storage_id,
            user=current_user.username,
            details={"champion": result["champion_model_type"], "version": result["version_tag"]},
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/v2/models/train-async/{storage_id}")
def train_v2_champion_challenger_async(
    storage_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_permission("models.train")),
    db: Session = Depends(get_db),
):
    dev = db.query(Device).filter(Device.id == storage_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Storage volume not found")

    job_id = f"bgjob-{uuid.uuid4().hex[:10]}"
    job = BackgroundJob(
        id=job_id,
        job_type="ML_TRAIN_CHAMPION_CHALLENGER",
        storage_id=storage_id,
        status="QUEUED",
        stage="QUEUED",
        progress_pct=5,
        triggered_by=current_user.username,
    )
    db.add(job)
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="model.training_queued",
        resource_type="ml_job",
        resource_id=job_id,
        actor_user=current_user,
        payload={
            "job_id": job_id,
            "storage_id": storage_id,
            "status": "QUEUED",
            "stage": "QUEUED",
            "progress_pct": 5,
        },
        required_permission="models.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    background_tasks.add_task(_run_async_training_job, job_id, storage_id, current_user.username)
    return {
        "job_id": job_id,
        "status": "QUEUED",
        "stage": "QUEUED",
        "progress_pct": 5,
        "job_type": "ML_TRAIN_CHAMPION_CHALLENGER",
        "storage_id": storage_id,
        "poll_endpoint": f"/api/v1/jobs/{job_id}",
    }


@router.get("/jobs/{job_id}")
def get_background_job_status(
    job_id: str,
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    job = db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Background job not found")
    return {
        "job_id": job.id,
        "job_type": job.job_type,
        "storage_id": job.storage_id,
        "status": job.status,
        "stage": getattr(job, "stage", job.status),
        "progress_pct": getattr(job, "progress_pct", 0),
        "result": json.loads(job.result_json or "{}"),
        "error_message": job.error_message,
        "triggered_by": job.triggered_by,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.get("/v2/models/reliability")
def get_v2_fleet_reliability(
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).all()
    summaries = []
    for d in devices:
        champ = (
            db.query(ModelVersion)
            .filter(
                ModelVersion.storage_id == d.id,
                ModelVersion.is_active == True,
                ModelVersion.feature_version.like("v3.%"),
            )
            .order_by(ModelVersion.trained_at.desc())
            .first()
        )
        rel = (
            db.query(DataReliabilityProfile)
            .filter(DataReliabilityProfile.storage_id == d.id)
            .order_by(DataReliabilityProfile.evaluated_at.desc())
            .first()
        )
        summaries.append({
            "storage_id": d.id,
            "name": d.name,
            "champion_model": champ.model_type if champ else None,
            "champion_rmse": champ.rmse if champ else None,
            "interval_coverage": champ.interval_coverage if champ else None,
            "data_reliability_score": rel.reliability_score if rel else None,
            "data_reliability_tier": rel.reliability_tier if rel else None,
            "is_stale": rel.is_stale if rel else None,
        })
    return {"fleet_v2_reliability": summaries, "count": len(summaries)}


@router.get("/v2/models/by-family")
def get_v2_models_by_family(
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    """
    Returns dedicated fleet-wide status, version history, resource coverage,
    train/validation ranges, metrics, and drift context grouped for LightGBM and SARIMAX.
    """
    devices = db.query(Device).all()
    eligible_ids = []
    for d in devices:
        cnt = db.query(Telemetry).filter(Telemetry.device_id == d.id).count()
        if cnt >= ChampionChallengerEngine.MIN_RECORDS:
            eligible_ids.append(d.id)

    versions = (
        db.query(ModelVersion)
        .filter(ModelVersion.feature_version.like("v3.%"))
        .order_by(ModelVersion.trained_at.desc())
        .all()
    )
    jobs = db.query(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(25).all()

    def _build_family(family_label: str, type_prefix: str) -> Dict[str, Any]:
        fam_versions = [v for v in versions if (v.model_type or "").upper().startswith(type_prefix)]
        covered_storage = sorted({v.storage_id for v in fam_versions if v.storage_id})
        champion_wins = sum(1 for v in fam_versions if v.is_active)
        records = []
        for v in fam_versions[:30]:
            mm = db.query(ModelMetric).filter(ModelMetric.model_version_id == v.id).first()
            schema = json.loads(v.feature_schema_json or "{}")
            latest_reg = (
                db.query(WorkloadRegimeEvent)
                .filter(WorkloadRegimeEvent.storage_id == v.storage_id)
                .order_by(WorkloadRegimeEvent.detected_at.desc())
                .first()
            )
            records.append({
                "id": v.id,
                "storage_id": v.storage_id,
                "name": v.name,
                "model_type": v.model_type,
                "version_tag": v.version_tag,
                "status": v.status,
                "is_champion": v.is_active,
                "train_samples": v.train_samples_count,
                "validation_samples": v.validation_samples,
                "train_start_at": v.train_start_at.isoformat() if v.train_start_at else None,
                "train_end_at": v.train_end_at.isoformat() if v.train_end_at else None,
                "trained_at": v.trained_at.isoformat() if v.trained_at else None,
                "trained_by": v.trained_by,
                "drift_state": latest_reg.regime_label if latest_reg else "NOT_ANALYZED",
                "rolling_cv": schema.get("rolling_cv"),
                "metrics": {
                    "mae": mm.mae if mm else v.mae,
                    "rmse": mm.rmse if mm else v.rmse,
                    "r2_score": mm.r2_score if mm else None,
                    "mape": mm.mape if mm else None,
                    "mase": mm.mase if mm else None,
                    "pinball_loss": mm.pinball_loss if mm else None,
                    "interval_coverage": mm.interval_coverage if mm else v.interval_coverage,
                    "mean_interval_width": mm.mean_interval_width if mm else None,
                    "vs_baseline_status": mm.vs_baseline_status if mm else None,
                    "selection_reason": mm.selection_reason if mm else "",
                },
            })
        return {
            "family": family_label,
            "total_versions": len(fam_versions),
            "champion_wins": champion_wins,
            "covered_storage_ids": covered_storage,
            "eligible_storage_ids": eligible_ids,
            "coverage_ratio": f"{len(covered_storage)}/{max(1, len(eligible_ids))}",
            "latest_status": records[0]["status"] if records else "NOT_TRAINED",
            "versions": records,
        }

    return {
        "families": {
            "LightGBM": _build_family("LightGBM", "LGBM"),
            "SARIMAX": _build_family("SARIMAX", "SARIMAX"),
        },
        "recent_jobs": [
            {
                "job_id": j.id,
                "storage_id": j.storage_id,
                "status": j.status,
                "error_message": j.error_message,
                "triggered_by": j.triggered_by,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            }
            for j in jobs
        ],
    }


@router.get("/v2/models/{storage_id}")
def get_v2_models_for_storage(
    storage_id: str,
    current_user: User = Depends(require_permission("models.read")),
    db: Session = Depends(get_db),
):
    dev = db.query(Device).filter(Device.id == storage_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Storage volume not found")

    versions = (
        db.query(ModelVersion)
        .filter(ModelVersion.storage_id == storage_id, ModelVersion.feature_version.like("v3.%"))
        .order_by(ModelVersion.trained_at.desc())
        .limit(12)
        .all()
    )
    items = []
    for v in versions:
        m = db.query(ModelMetric).filter(ModelMetric.model_version_id == v.id).first()
        items.append({
            "id": v.id,
            "name": v.name,
            "model_type": v.model_type,
            "version_tag": v.version_tag,
            "is_active": v.is_active,
            "status": v.status,
            "train_samples": v.train_samples_count,
            "validation_samples": v.validation_samples,
            "trained_at": v.trained_at.isoformat() if v.trained_at else None,
            "feature_schema": json.loads(v.feature_schema_json or "{}"),
            "metrics": {
                "mae": m.mae if m else v.mae,
                "rmse": m.rmse if m else v.rmse,
                "r2_score": m.r2_score if m else None,
                "mape": m.mape if m else None,
                "mase": m.mase if m else None,
                "pinball_loss": m.pinball_loss if m else None,
                "interval_coverage": m.interval_coverage if m else v.interval_coverage,
                "mean_interval_width": m.mean_interval_width if m else None,
                "vs_baseline_status": m.vs_baseline_status if m else None,
                "is_selected": m.is_selected if m else v.is_active,
                "selection_reason": m.selection_reason if m else "",
            },
        })
    return {"storage_id": storage_id, "versions": items, "count": len(items)}


@router.post("/v2/forecasts/generate/{storage_id}")
def generate_v2_forecast(
    storage_id: str,
    payload: V2ForecastRequest = V2ForecastRequest(),
    current_user: User = Depends(require_permission("forecasts.generate")),
    db: Session = Depends(get_db),
):
    try:
        res = ChampionChallengerEngine.generate_forecast(
            db, storage_id, horizon_days=payload.horizon_days, persist=payload.persist
        )
        from app.realtime.event_bus import OutboxService
        OutboxService.emit_and_commit(
            db,
            event_type="forecast.generated",
            resource_type="forecast",
            resource_id=res.get("forecast_id") or storage_id,
            actor_user=current_user,
            payload={
                "storage_id": storage_id,
                "forecast_id": res.get("forecast_id"),
                "horizon_days": payload.horizon_days,
                "champion_family": res.get("champion_family"),
            },
            required_permission="forecasts.read",
        )
        return res
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/v2/forecasts/schedule")
def run_scheduled_forecasts(
    horizon_days: int = Query(default=30, ge=1, le=180),
    current_user: User = Depends(require_permission("forecasts.generate")),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).all()
    results = []
    for d in devices:
        try:
            res = ChampionChallengerEngine.generate_forecast(db, d.id, horizon_days=horizon_days, persist=True)
            results.append({
                "storage_id": d.id,
                "status": "GENERATED",
                "forecast_id": res["forecast_id"],
                "champion_family": res["champion_family"],
            })
        except Exception as exc:
            results.append({"storage_id": d.id, "status": "SKIPPED", "reason": str(exc)})
    return {"status": "completed", "horizon_days": horizon_days, "results": results}


@router.get("/v2/forecasts/{storage_id}")
def get_v2_forecast_history(
    storage_id: str,
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(require_permission("forecasts.read")),
    db: Session = Depends(get_db),
):
    """
    Returns saved forecast versions AND separated chronological historical actual telemetry
    for side-by-side inspection and version comparison in Forecast Studio.
    """
    dev = db.query(Device).filter(Device.id == storage_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Storage volume not found")

    tel_rows = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == storage_id)
        .order_by(Telemetry.timestamp.desc())
        .limit(96)
        .all()
    )
    tel_rows.reverse()
    total_gb = float(dev.total_capacity_bytes) / (1024.0 ** 3)
    historical_actuals = [
        {
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "used_gb": round(float(r.used_bytes or 0) / (1024.0 ** 3), 4),
            "utilization_pct": r.utilization_pct,
            "is_synthetic": r.is_synthetic,
        }
        for r in tel_rows
    ]

    fc_rows = (
        db.query(Forecast)
        .filter(Forecast.device_id == storage_id)
        .order_by(Forecast.generated_at.desc())
        .limit(limit)
        .all()
    )
    saved_forecasts = []
    for f in fc_rows:
        ts_list = json.loads(f.timestamps_json or "[]")
        q10_b = json.loads(f.q10_json or "[]")
        q50_b = json.loads(f.q50_json or "[]")
        q90_b = json.loads(f.q90_json or "[]")
        mv = db.query(ModelVersion).filter(ModelVersion.id == f.model_version_id).first() if f.model_version_id else None
        mm = db.query(ModelMetric).filter(ModelMetric.model_version_id == mv.id).first() if mv else None
        saved_forecasts.append({
            "forecast_id": f.id,
            "storage_id": f.device_id,
            "model_name": f.model_name,
            "model_version_id": f.model_version_id,
            "horizon_hours": f.horizon_hours,
            "horizon_days": f.horizon_days or max(1, f.horizon_hours // 24),
            "generated_at": f.generated_at.isoformat() if f.generated_at else None,
            "historical_cutoff": f.historical_cutoff.isoformat() if f.historical_cutoff else None,
            "interval_coverage": f.interval_coverage,
            "validation_metrics": {
                "mae": mm.mae if mm else (mv.mae if mv else None),
                "rmse": mm.rmse if mm else (mv.rmse if mv else None),
                "mase": mm.mase if mm else None,
                "pinball_loss": mm.pinball_loss if mm else None,
                "interval_coverage": mm.interval_coverage if mm else f.interval_coverage,
                "vs_baseline_status": mm.vs_baseline_status if mm else None,
            },
            "series": [
                {
                    "timestamp": ts_list[i] if i < len(ts_list) else None,
                    "p10_used_gb": round(float(q10_b[i]) / (1024.0 ** 3), 4) if i < len(q10_b) else None,
                    "p50_used_gb": round(float(q50_b[i]) / (1024.0 ** 3), 4) if i < len(q50_b) else None,
                    "p90_used_gb": round(float(q90_b[i]) / (1024.0 ** 3), 4) if i < len(q90_b) else None,
                }
                for i in range(len(ts_list))
            ],
        })

    return {
        "storage_id": storage_id,
        "device_name": dev.name,
        "total_capacity_gb": round(total_gb, 3),
        "historical_actuals": historical_actuals,
        "saved_forecasts": saved_forecasts,
        "count": len(saved_forecasts),
    }


# --- Phase 6: Capacity Risk Engine ---

@router.get("/risk/capacity/{storage_id}")
def get_capacity_risk(
    storage_id: str,
    horizon_days: int = Query(default=30, ge=1, le=180),
    safety_threshold_pct: Optional[float] = Query(default=None, ge=10.0, le=99.9),
    current_user: User = Depends(require_permission("risk.read")),
    db: Session = Depends(get_db),
):
    try:
        return CapacityRiskEngine.evaluate(
            db, storage_id, horizon_days=horizon_days, safety_threshold_pct=safety_threshold_pct, persist=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/risk/capacity/{storage_id}")
def evaluate_capacity_risk(
    storage_id: str,
    payload: RiskEvalRequest = RiskEvalRequest(),
    current_user: User = Depends(require_permission("risk.evaluate")),
    db: Session = Depends(get_db),
):
    try:
        return CapacityRiskEngine.evaluate(
            db, storage_id, horizon_days=payload.horizon_days, safety_threshold_pct=payload.safety_threshold_pct, persist=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
