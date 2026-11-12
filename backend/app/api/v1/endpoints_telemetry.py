import io
import csv
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, IngestionJob, User
from app.auth.security import require_role
from app.auth.permissions import require_permission
from app.services.audit_service import AuditService
from app.schemas.payloads import TelemetryResponse, TelemetryIngestBatch
from app.config import settings
from app.services.replay_service import replay_engine
from app.collector.host_collector import HostStorageCollector, PROVENANCE_LIVE

router = APIRouter()

class PrometheusScrapeRequest(BaseModel):
    endpoint_url: str = Field(default="http://127.0.0.1:9100/metrics", description="Prometheus Node Exporter scrape target")
    timeout_seconds: float = Field(default=3.0, ge=0.5, le=30.0, description="Read-only request timeout in seconds")

class TelemetryValidationRequest(BaseModel):
    sample: Dict[str, Any] = Field(..., description="Telemetry sample to validate")
    max_age_hours: float = Field(default=24.0, ge=0.1, description="Max acceptable age in hours before flagging as stale")


METRIC_UNITS = {
    "used_bytes": "Bytes",
    "free_bytes": "Bytes",
    "utilization_pct": "%",
    "read_iops": "IOPS",
    "write_iops": "IOPS",
    "throughput_mb_s": "MB/s",
    "latency_p95_ms": "ms",
    "queue_depth": "Queue Depth"
}

@router.get("/devices/{device_id}/telemetry", response_model=TelemetryResponse)
def get_device_telemetry(
    device_id: str,
    metric: str = Query("used_bytes", description="used_bytes, utilization_pct, read_iops, write_iops, throughput_mb_s, latency_p95_ms, queue_depth"),
    hours: int = Query(720, description="Hours of historical telemetry to fetch"),
    current_user: User = Depends(require_permission("telemetry.read")),
    db: Session = Depends(get_db)
):
    mode = settings.OPERATING_MODE.lower()

    if mode == "replay":
        history = replay_engine.get_telemetry_history(device_id, metric, hours)
        if not history.get("timestamps"):
            # Check if volume exists in replay
            cur_devices = replay_engine.get_current_devices()
            v_match = [d for d in cur_devices if d["id"] == device_id]
            if not v_match:
                raise HTTPException(status_code=404, detail=f"Volume '{device_id}' not found in active trace")
        return TelemetryResponse(**history)

    if device_id.startswith("host-vol"):
        from app.collector.host_collector import HostStorageCollector
        HostStorageCollector.sync_live_partitions_to_db(db)

    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id, Telemetry.timestamp >= cutoff)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    if not records:
        # Fallback to all records available for device
        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == device_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

    timestamps = [r.timestamp for r in records]
    values = [float(getattr(r, metric, 0.0) or 0.0) for r in records]
    is_synth = any(r.is_synthetic for r in records) if records else True

    # Identify missing intervals (> 2 hour jump between timestamps)
    missing = []
    for i in range(1, len(timestamps)):
        delta_h = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600.0
        if delta_h > 1.8:
            missing.append({
                "from": timestamps[i-1].isoformat(),
                "to": timestamps[i].isoformat(),
                "missing_hours": round(delta_h, 1)
            })

    return TelemetryResponse(
        device_id=device_id,
        metric=metric,
        total_capacity_bytes=device.total_capacity_bytes,
        is_synthetic=is_synth,
        timestamps=timestamps,
        values=values,
        units=METRIC_UNITS.get(metric, "Value"),
        missing_intervals=missing
    )

@router.post("/telemetry/ingest")
def ingest_telemetry(
    payload: TelemetryIngestBatch,
    idempotency_key_header: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    current_user: User = Depends(require_permission("telemetry.ingest")),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target storage device not found")

    idem_key = (idempotency_key_header or payload.idempotency_key or "").strip() or None
    if idem_key:
        existing_job = (
            db.query(IngestionJob)
            .filter(IngestionJob.storage_id == payload.device_id, IngestionJob.idempotency_key == idem_key)
            .first()
        )
        if existing_job:
            return {
                "status": "idempotent_replay",
                "idempotent_replay": True,
                "idempotency_key": idem_key,
                "job_id": existing_job.id,
                "ingested_count": 0,
                "original_accepted_count": existing_job.accepted_rows,
                "rejected_count": existing_job.rejected_rows,
                "duplicate_count": existing_job.duplicate_rows,
                "errors": json.loads(existing_job.errors_json or "[]"),
                "device_id": payload.device_id,
            }

    existing_ts = {
        (r[0].replace(tzinfo=None) if r[0].tzinfo else r[0]).replace(microsecond=0)
        for r in db.query(Telemetry.timestamp).filter(Telemetry.device_id == payload.device_id).all()
        if r[0] is not None
    }

    new_entities = []
    errors = []
    duplicates = 0
    rejected = 0
    seen_batch = set()

    for idx, item in enumerate(payload.records):
        ts_naive = (item.timestamp.astimezone(timezone.utc).replace(tzinfo=None) if item.timestamp.tzinfo else item.timestamp).replace(microsecond=0)
        if item.used_bytes < 0 or item.used_bytes > device.total_capacity_bytes:
            rejected += 1
            errors.append({"index": idx, "type": "IMPOSSIBLE_CAPACITY", "reason": f"used_bytes ({item.used_bytes}) out of [0, {device.total_capacity_bytes}]"})
            continue
        if item.read_iops < 0 or item.write_iops < 0 or item.throughput_mb_s < 0 or item.latency_p95_ms < 0:
            rejected += 1
            errors.append({"index": idx, "type": "NEGATIVE_METRIC", "reason": "Performance metrics cannot be negative"})
            continue
        if ts_naive in existing_ts or ts_naive in seen_batch:
            duplicates += 1
            errors.append({"index": idx, "type": "DUPLICATE_TIMESTAMP", "reason": f"Duplicate timestamp {ts_naive.isoformat()}"})
            continue

        seen_batch.add(ts_naive)
        util_pct = round((item.used_bytes / device.total_capacity_bytes) * 100.0, 2)
        free_b = max(0, device.total_capacity_bytes - item.used_bytes)
        t = Telemetry(
            device_id=payload.device_id,
            timestamp=ts_naive,
            total_capacity_bytes=device.total_capacity_bytes,
            used_bytes=item.used_bytes,
            free_bytes=free_b,
            utilization_pct=util_pct,
            read_iops=item.read_iops,
            write_iops=item.write_iops,
            throughput_mb_s=item.throughput_mb_s,
            latency_p95_ms=item.latency_p95_ms,
            queue_depth=item.queue_depth,
            is_synthetic=item.is_synthetic,
            source_label="api_ingestion"
        )
        new_entities.append(t)

    if new_entities:
        db.bulk_save_objects(new_entities)
        device.last_telemetry_at = max(e.timestamp for e in new_entities)

    job_id = f"job-{uuid.uuid4().hex[:10]}"
    db.add(IngestionJob(
        id=job_id,
        storage_id=payload.device_id,
        source_type="API_COLLECTOR",
        filename="rest_api_batch",
        status="COMPLETED" if rejected == 0 and duplicates == 0 else ("PARTIAL" if new_entities else "FAILED"),
        total_rows=len(payload.records),
        accepted_rows=len(new_entities),
        rejected_rows=rejected,
        duplicate_rows=duplicates,
        errors_json=json.dumps(errors),
        idempotency_key=idem_key,
        uploaded_by=current_user.username,
    ))
    from app.realtime.event_bus import OutboxService
    evt = OutboxService.stage_event(
        db,
        event_type="telemetry.batch_completed",
        resource_type="telemetry",
        resource_id=payload.device_id,
        actor_user=current_user,
        payload={
            "job_id": job_id,
            "storage_id": payload.device_id,
            "accepted": len(new_entities),
            "rejected": rejected,
            "duplicates": duplicates,
        },
        required_permission="telemetry.read",
    )
    db.commit()
    db.refresh(evt)
    OutboxService.publish_after_commit(db, evt)

    AuditService.log_event(
        db=db,
        action="API_TELEMETRY_INGEST",
        target_type="DEVICE",
        target_id=payload.device_id,
        user=current_user.username,
        details={"accepted": len(new_entities), "rejected": rejected, "duplicates": duplicates, "idempotency_key": idem_key}
    )

    return {
        "status": "ok",
        "idempotent_replay": False,
        "idempotency_key": idem_key,
        "job_id": job_id,
        "ingested_count": len(new_entities),
        "rejected_count": rejected,
        "duplicate_count": duplicates,
        "errors": errors,
        "device_id": payload.device_id,
    }

@router.get("/telemetry/export")
def export_telemetry_csv(
    device_id: str,
    current_user: User = Depends(require_permission("telemetry.read")),
    db: Session = Depends(get_db),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    records = (
        db.query(Telemetry)
        .filter(Telemetry.device_id == device_id)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp_utc", "device_id", "used_bytes", "free_bytes", "utilization_pct",
        "read_iops", "write_iops", "throughput_mb_s", "latency_p95_ms", "queue_depth",
        "is_synthetic", "source_label"
    ])

    for r in records:
        writer.writerow([
            r.timestamp.isoformat(), r.device_id, r.used_bytes, r.free_bytes, r.utilization_pct,
            r.read_iops, r.write_iops, r.throughput_mb_s, r.latency_p95_ms, r.queue_depth,
            r.is_synthetic, r.source_label
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=telemetry_{device_id}.csv"}
    )

@router.get("/telemetry/sources")
def get_telemetry_sources(current_user: User = Depends(require_permission("telemetry.read"))):
    """
    Returns registered telemetry sources, configured boundaries, read-only guarantees,
    and supported metrics. Enforces strict zero-mutation policy.
    """
    sources = HostStorageCollector.get_configured_sources()
    return {
        "status": "ok",
        "permission_mode": "READ_ONLY",
        "physical_mutation_disabled": True,
        "sources": sources
    }

@router.get("/telemetry/live-host")
def get_live_host_telemetry(current_user: User = Depends(require_permission("telemetry.read"))):
    """
    Collects real filesystem capacity and usage from host storage partitions.
    Guarantees non-destructive read-only sampling with provenance='LIVE'.
    """
    partitions = HostStorageCollector.get_available_partitions()
    return {
        "status": "ok",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "provenance": PROVENANCE_LIVE,
        "is_synthetic": False,
        "read_only": True,
        "partitions_count": len(partitions),
        "partitions": partitions
    }

@router.post("/telemetry/prometheus/scrape")
def scrape_prometheus_metrics(
    payload: PrometheusScrapeRequest = PrometheusScrapeRequest(),
    current_user: User = Depends(require_permission("telemetry.collect")),
):
    """
    Scrapes Prometheus Node Exporter metrics in read-only mode.
    Parses node_filesystem and node_disk counters with failure diagnostics and validation.
    """
    result = HostStorageCollector.scrape_prometheus_node_exporter(
        endpoint_url=payload.endpoint_url,
        timeout_seconds=payload.timeout_seconds
    )
    return result

@router.post("/telemetry/validate")
def validate_telemetry_sample(
    payload: TelemetryValidationRequest,
    current_user: User = Depends(require_permission("ingestion.validate")),
):
    """
    Validates a telemetry sample against physical invariants (positive capacity,
    utilization bounds 0-100%, non-negative IOPS), timestamp validity,
    staleness threshold, and provenance rules (synthetic data cannot claim LIVE provenance).
    """
    validation = HostStorageCollector.validate_metric_sample(
        sample=payload.sample,
        max_age_hours=payload.max_age_hours
    )
    return validation

