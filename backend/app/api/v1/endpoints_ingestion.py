import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Response, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, IngestionJob, DataQualityResult, User
from app.auth.security import get_current_user, require_role
from app.auth.permissions import require_permission
from app.services.audit_service import AuditService
from app.services.data_quality_service import DataPreprocessingPipeline, _parse_iso_timestamp

router = APIRouter()

CSV_TEMPLATE_CONTENT = (
    "timestamp,storage_id,total_capacity_bytes,used_capacity_bytes,read_iops,write_iops,read_latency_ms,write_latency_ms,throughput_mbps\n"
    "2026-11-10T00:00:00Z,vol-nvme-tier1-db,10995116277760,7916483719987,6420,4180,1.4,2.1,640.5\n"
    "2026-11-10T01:00:00Z,vol-nvme-tier1-db,10995116277760,7921483719987,6110,3990,1.3,2.0,612.0\n"
    "2026-11-10T02:00:00Z,vol-nvme-tier1-db,10995116277760,7927483719987,5890,4120,1.5,2.2,598.4\n"
)


class CsvTextPayload(BaseModel):
    csv_content: str
    filename: str = "telemetry_upload.csv"
    default_storage_id: Optional[str] = None


class ManualTelemetryEntry(BaseModel):
    storage_id: str
    timestamp: str
    total_capacity_bytes: Optional[int] = None
    used_capacity_bytes: int = Field(..., ge=0)
    read_iops: Optional[float] = Field(default=None, ge=0.0)
    write_iops: Optional[float] = Field(default=None, ge=0.0)
    read_latency_ms: Optional[float] = Field(default=None, ge=0.0)
    write_latency_ms: Optional[float] = Field(default=None, ge=0.0)
    throughput_mbps: Optional[float] = Field(default=None, ge=0.0)


@router.get("/ingestion/template", tags=["Data Ingestion"])
def download_csv_template(current_user: User = Depends(require_permission("ingestion.export"))):
    """Downloads the standardized CSV template for historical and operational storage telemetry import."""
    return Response(
        content=CSV_TEMPLATE_CONTENT,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=aegisstor_telemetry_template.csv"}
    )


async def _extract_csv_text(
    file: Optional[UploadFile],
    csv_content: Optional[str]
) -> tuple[str, str]:
    if file is not None:
        raw = await file.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return text, file.filename or "upload.csv"
    if csv_content is not None:
        return csv_content, "inline_csv.csv"
    raise HTTPException(status_code=400, detail="Provide either a CSV file upload or csv_content text")


@router.post("/ingestion/csv/preview", tags=["Data Ingestion"])
async def preview_csv_import(
    file: Optional[UploadFile] = File(default=None),
    csv_content: Optional[str] = Form(default=None),
    default_storage_id: Optional[str] = Form(default=None),
    current_user: User = Depends(require_permission("ingestion.preview")),
    db: Session = Depends(get_db)
):
    """Previews CSV ingestion, validating columns, dates, bounds, duplicates, and row-level errors without committing."""
    text, filename = await _extract_csv_text(file, csv_content)
    result = DataPreprocessingPipeline.validate_and_preprocess_csv(db, text, default_storage_id=default_storage_id)
    return {
        "filename": filename,
        "valid": result["valid"],
        "error": result.get("error"),
        "total_rows": result["total_rows"],
        "accepted_rows": result["accepted_rows"],
        "rejected_rows": result["rejected_rows"],
        "duplicate_rows": result["duplicate_rows"],
        "missing_field_stats": result.get("missing_field_stats", {}),
        "outlier_count": result.get("outlier_count", 0),
        "data_completeness_pct": result.get("data_completeness_pct", 0.0),
        "latest_telemetry_timestamp": result.get("latest_telemetry_timestamp"),
        "preprocessing_decisions": result.get("preprocessing_decisions", []),
        "preview_rows": result["preview_rows"],
        "errors": result["errors"],
    }


@router.post("/ingestion/csv/import", tags=["Data Ingestion"])
async def commit_csv_import(
    file: Optional[UploadFile] = File(default=None),
    csv_content: Optional[str] = Form(default=None),
    default_storage_id: Optional[str] = Form(default=None),
    current_user: User = Depends(require_permission("ingestion.commit")),
    db: Session = Depends(get_db)
):
    """Validates and commits accepted CSV telemetry records into persistent storage, recording IngestionJob & DataQualityResult."""
    text, filename = await _extract_csv_text(file, csv_content)
    result = DataPreprocessingPipeline.validate_and_preprocess_csv(db, text, default_storage_id=default_storage_id)

    accepted = result["accepted_records"]
    job_id = f"job-{uuid.uuid4().hex[:10]}"

    if not result["valid"] and result["total_rows"] == 0:
        job = IngestionJob(
            id=job_id,
            storage_id=default_storage_id,
            source_type="CSV_UPLOAD",
            filename=filename,
            status="FAILED",
            total_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            duplicate_rows=0,
            errors_json=json.dumps(result["errors"]),
            uploaded_by=current_user.username,
        )
        db.add(job)
        db.commit()
        raise HTTPException(status_code=400, detail={"message": result.get("error", "Invalid CSV"), "job_id": job_id, "errors": result["errors"]})

    # Insert valid records
    touched_storages = set()
    telemetry_entities = []
    for rec in accepted:
        sid = rec["storage_id"]
        touched_storages.add(sid)
        telemetry_entities.append(Telemetry(
            device_id=sid,
            timestamp=rec["timestamp"],
            total_capacity_bytes=rec["total_capacity_bytes"],
            used_bytes=rec["used_bytes"],
            free_bytes=rec["free_bytes"],
            utilization_pct=rec["utilization_pct"],
            read_iops=rec["read_iops"],
            write_iops=rec["write_iops"],
            throughput_mb_s=rec["throughput_mb_s"],
            latency_p95_ms=rec["latency_p95_ms"],
            read_latency_ms=rec["read_latency_ms"],
            write_latency_ms=rec["write_latency_ms"],
            queue_depth=1.0,
            is_synthetic=False,
            source_label=f"csv_import:{job_id}",
        ))

    if telemetry_entities:
        db.bulk_save_objects(telemetry_entities)

    # Update device last_telemetry_at
    for sid in touched_storages:
        dev = db.query(Device).filter(Device.id == sid).first()
        if dev:
            latest_for_sid = max(r["timestamp"] for r in accepted if r["storage_id"] == sid)
            dev.last_telemetry_at = latest_for_sid

    job_status = "COMPLETED" if (result["rejected_rows"] == 0 and result["duplicate_rows"] == 0) else ("PARTIAL" if len(accepted) > 0 else "FAILED")
    primary_sid = next(iter(touched_storages), default_storage_id)
    job = IngestionJob(
        id=job_id,
        storage_id=primary_sid if len(touched_storages) == 1 else default_storage_id,
        source_type="CSV_UPLOAD",
        filename=filename,
        status=job_status,
        total_rows=result["total_rows"],
        accepted_rows=len(accepted),
        rejected_rows=result["rejected_rows"],
        duplicate_rows=result["duplicate_rows"],
        errors_json=json.dumps(result["errors"]),
        uploaded_by=current_user.username,
    )
    db.add(job)
    db.flush()

    for sid in touched_storages:
        dq = DataQualityResult(
            id=f"dq-{uuid.uuid4().hex[:10]}",
            storage_id=sid,
            ingestion_job_id=job_id,
            total_records_received=result["total_rows"],
            valid_records=len([r for r in accepted if r["storage_id"] == sid]),
            rejected_records=result["rejected_rows"],
            duplicate_records=result["duplicate_rows"],
            missing_field_stats_json=json.dumps(result.get("missing_field_stats", {})),
            outlier_count=result.get("outlier_count", 0),
            data_completeness_pct=result.get("data_completeness_pct", 100.0),
            latest_telemetry_timestamp=max(r["timestamp"] for r in accepted if r["storage_id"] == sid),
            preprocessing_decisions_json=json.dumps(result.get("preprocessing_decisions", [])),
        )
        db.add(dq)

    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="ingestion.completed",
        resource_type="ingestion_job",
        resource_id=job_id,
        actor_user=current_user,
        payload={
            "job_id": job_id,
            "filename": filename,
            "accepted_rows": len(accepted),
            "rejected_rows": result["rejected_rows"],
            "touched_storages": sorted(list(touched_storages)),
        },
        required_permission="ingestion.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="DATA_IMPORT",
        target_type="INGESTION_JOB",
        target_id=job_id,
        user=current_user.username,
        details={
            "filename": filename,
            "total_rows": result["total_rows"],
            "accepted": len(accepted),
            "rejected": result["rejected_rows"],
            "duplicates": result["duplicate_rows"],
        }
    )

    return {
        "job_id": job_id,
        "status": job_status,
        "filename": filename,
        "total_rows": result["total_rows"],
        "accepted_rows": len(accepted),
        "rejected_rows": result["rejected_rows"],
        "duplicate_rows": result["duplicate_rows"],
        "errors": result["errors"],
        "error_report_url": f"/api/v1/ingestion/jobs/{job_id}/errors",
    }


@router.post("/ingestion/manual", tags=["Data Ingestion"], status_code=201)
def manual_telemetry_entry(
    payload: ManualTelemetryEntry,
    current_user: User = Depends(require_permission("telemetry.ingest")),
    db: Session = Depends(get_db)
):
    """Records a validated manual telemetry entry into the persistent database."""
    device = db.query(Device).filter(Device.id == payload.storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Storage resource '{payload.storage_id}' not found")

    ts = _parse_iso_timestamp(payload.timestamp)
    if ts is None:
        raise HTTPException(status_code=400, detail=f"Invalid timestamp '{payload.timestamp}'. Use ISO-8601 format.")

    total_cap = payload.total_capacity_bytes or int(device.total_capacity_bytes)
    if total_cap <= 0:
        raise HTTPException(status_code=400, detail="total_capacity_bytes must be positive")
    if payload.used_capacity_bytes < 0 or payload.used_capacity_bytes > total_cap:
        raise HTTPException(
            status_code=400,
            detail=f"used_capacity_bytes ({payload.used_capacity_bytes}) cannot exceed total_capacity_bytes ({total_cap})"
        )

    # Check duplicate timestamp
    existing = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == payload.storage_id, Telemetry.timestamp == ts)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate telemetry entry already exists for {payload.storage_id} at {ts.isoformat()}"
        )

    free_cap = total_cap - payload.used_capacity_bytes
    util_pct = round((payload.used_capacity_bytes / total_cap) * 100.0, 2)
    rl = payload.read_latency_ms
    wl = payload.write_latency_ms
    comb_lat = max([x for x in (rl, wl) if x is not None], default=None)

    tel = Telemetry(
        device_id=payload.storage_id,
        timestamp=ts,
        total_capacity_bytes=total_cap,
        used_bytes=payload.used_capacity_bytes,
        free_bytes=free_cap,
        utilization_pct=util_pct,
        read_iops=payload.read_iops,
        write_iops=payload.write_iops,
        throughput_mb_s=payload.throughput_mbps,
        latency_p95_ms=comb_lat,
        read_latency_ms=rl,
        write_latency_ms=wl,
        queue_depth=1.0,
        is_synthetic=False,
        source_label="manual_entry",
    )
    db.add(tel)
    device.last_telemetry_at = ts

    job_id = f"job-{uuid.uuid4().hex[:10]}"
    db.add(IngestionJob(
        id=job_id,
        storage_id=payload.storage_id,
        source_type="MANUAL_ENTRY",
        filename="manual_form",
        status="COMPLETED",
        total_rows=1,
        accepted_rows=1,
        rejected_rows=0,
        duplicate_rows=0,
        errors_json="[]",
        uploaded_by=current_user.username,
    ))
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="telemetry.received",
        resource_type="telemetry",
        resource_id=payload.storage_id,
        actor_user=current_user,
        payload={
            "job_id": job_id,
            "storage_id": payload.storage_id,
            "utilization_pct": util_pct,
            "used_bytes": payload.used_capacity_bytes,
        },
        required_permission="telemetry.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="MANUAL_TELEMETRY_ENTRY",
        target_type="TELEMETRY",
        target_id=payload.storage_id,
        user=current_user.username,
        details={"timestamp": ts.isoformat(), "used_bytes": payload.used_capacity_bytes, "utilization_pct": util_pct}
    )

    return {
        "status": "ok",
        "job_id": job_id,
        "storage_id": payload.storage_id,
        "timestamp": ts.isoformat(),
        "utilization_pct": util_pct,
        "free_capacity_bytes": free_cap,
    }


@router.get("/ingestion/jobs", tags=["Data Ingestion"])
def list_ingestion_jobs(
    storage_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_permission("quality.read")),
    db: Session = Depends(get_db)
):
    """Lists historical data import and ingestion jobs with acceptance/rejection metrics."""
    q = db.query(IngestionJob)
    if storage_id:
        q = q.filter(IngestionJob.storage_id == storage_id)
    jobs = q.order_by(IngestionJob.created_at.desc()).limit(limit).all()
    return [
        {
            "id": j.id,
            "storage_id": j.storage_id,
            "source_type": j.source_type,
            "filename": j.filename,
            "status": j.status,
            "total_rows": j.total_rows,
            "accepted_rows": j.accepted_rows,
            "rejected_rows": j.rejected_rows,
            "duplicate_rows": j.duplicate_rows,
            "uploaded_by": j.uploaded_by,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


@router.get("/ingestion/jobs/{job_id}/errors", tags=["Data Ingestion"])
def download_job_error_report(
    job_id: str,
    format: str = Query("csv", description="csv or json"),
    current_user: User = Depends(require_permission("ingestion.export")),
    db: Session = Depends(get_db)
):
    """Downloads row-level validation and duplicate errors for a given ingestion job."""
    job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Ingestion job not found")

    errors = json.loads(job.errors_json or "[]")
    if format.lower() == "json":
        return {"job_id": job_id, "filename": job.filename, "error_count": len(errors), "errors": errors}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "storage_id", "error_type", "reason"])
    for err in errors:
        writer.writerow([
            err.get("row_number", ""),
            err.get("storage_id", ""),
            err.get("type", "VALIDATION_ERROR"),
            err.get("reason", ""),
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=ingestion_errors_{job_id}.csv"}
    )


@router.get("/data-quality", tags=["Data Quality"])
def list_fleet_data_quality(
    current_user: User = Depends(require_permission("quality.read")),
    db: Session = Depends(get_db),
):
    """Evaluates and returns data quality summaries across all storage resources."""
    devices = db.query(Device).filter(Device.tier != "HOST_LOCAL").all()
    results = []
    for d in devices:
        results.append(DataPreprocessingPipeline.evaluate_storage_data_quality(db, d.id))
    return results


@router.get("/data-quality/{storage_id}", tags=["Data Quality"])
def get_storage_data_quality(
    storage_id: str,
    current_user: User = Depends(require_permission("quality.read")),
    db: Session = Depends(get_db),
):
    """Runs deterministic preprocessing inspection and returns data quality metrics for a storage resource."""
    try:
        return DataPreprocessingPipeline.evaluate_storage_data_quality(db, storage_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/telemetry/records", tags=["Data Quality"])
def inspect_telemetry_records(
    storage_id: Optional[str] = Query(None),
    is_synthetic: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_permission("telemetry.read")),
    db: Session = Depends(get_db),
):
    """Record-level persisted telemetry inspector for auditing quality, missing metrics, and provenance."""
    q = db.query(Telemetry)
    if storage_id:
        q = q.filter(Telemetry.device_id == storage_id)
    if is_synthetic is not None:
        q = q.filter(Telemetry.is_synthetic == is_synthetic)
    total = q.count()
    rows = q.order_by(Telemetry.timestamp.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "records": [
            {
                "id": r.id,
                "storage_id": r.device_id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "total_capacity_bytes": r.total_capacity_bytes,
                "used_bytes": r.used_bytes,
                "free_bytes": r.free_bytes,
                "utilization_pct": r.utilization_pct,
                "read_iops": r.read_iops,
                "write_iops": r.write_iops,
                "throughput_mb_s": r.throughput_mb_s,
                "latency_p95_ms": r.latency_p95_ms,
                "is_synthetic": r.is_synthetic,
                "source_label": r.source_label,
            }
            for r in rows
        ],
    }
