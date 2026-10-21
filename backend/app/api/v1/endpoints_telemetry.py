import io
import csv
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry
from app.schemas.payloads import TelemetryResponse, TelemetryIngestBatch

router = APIRouter()

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
    values = [float(getattr(r, metric, 0.0)) for r in records]
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
