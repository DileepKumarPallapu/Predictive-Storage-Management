import io
import csv
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry
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
    db: Session = Depends(get_db)
):
    if metric not in METRIC_UNITS:
        raise HTTPException(status_code=422, detail=f"Unsupported telemetry metric '{metric}'.")

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

    observed_records = [
        r for r in records
        if getattr(r, metric, None) is not None
    ]
    timestamps = [r.timestamp for r in observed_records]
    values = [float(getattr(r, metric)) for r in observed_records]
    is_synth = any(r.is_synthetic for r in records) if records else False

    # Identify missing intervals (> 2 hour jump between actual observations).
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
def ingest_telemetry(payload: TelemetryIngestBatch, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Target storage device not found")

    new_entities = []
    for item in payload.records:
        util_pct = round((item.used_bytes / device.total_capacity_bytes) * 100.0, 2)
        t = Telemetry(
            device_id=payload.device_id,
            timestamp=item.timestamp,
            used_bytes=item.used_bytes,
            free_bytes=item.free_bytes,
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

    db.bulk_save_objects(new_entities)
    db.commit()

    return {"status": "ok", "ingested_count": len(new_entities), "device_id": payload.device_id}

@router.get("/telemetry/export")
def export_telemetry_csv(device_id: str, db: Session = Depends(get_db)):
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
def get_telemetry_sources():
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
def get_live_host_telemetry():
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
def scrape_prometheus_metrics(payload: PrometheusScrapeRequest = PrometheusScrapeRequest()):
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
def validate_telemetry_sample(payload: TelemetryValidationRequest):
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

