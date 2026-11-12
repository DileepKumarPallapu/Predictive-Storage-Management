from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import Device, Telemetry, TelemetryConnector
from app.services.data_quality_service import _parse_iso_timestamp
from app.api.v1.endpoints_settings import _load_persisted_settings
from app.auth.permissions import require_permission
from app.models.entities import User

router = APIRouter()


def _summarize_series(
    values: List[Optional[float]],
    unit: str,
    is_stale: bool = False,
    unsupported_by_connector: bool = False,
) -> Dict[str, Any]:
    clean = [float(v) for v in values if v is not None]
    if not clean:
        status = "UNSUPPORTED_BY_CONNECTOR" if unsupported_by_connector else "UNAVAILABLE"
        return {
            "available": False,
            "status": status,
            "display": "Unsupported by connector" if unsupported_by_connector else "No data available",
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
            "p95": None,
            "latest": None,
            "unit": unit,
        }
    arr = np.array(clean, dtype=float)
    status = "STALE" if is_stale else "AVAILABLE"
    return {
        "available": True,
        "status": status,
        "display": f"{round(float(clean[-1]), 2)} {unit}",
        "count": len(clean),
        "min": round(float(np.min(arr)), 2),
        "max": round(float(np.max(arr)), 2),
        "avg": round(float(np.mean(arr)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "latest": round(float(clean[-1]), 2),
        "unit": unit,
    }


@router.get("/performance/compare", tags=["Storage Performance Monitoring"])
def compare_storage_performance(
    storage_ids: Optional[str] = Query(None, description="Comma-separated storage IDs; omits to compare all volumes"),
    limit: int = Query(200, ge=10, le=1000),
    current_user: User = Depends(require_permission("performance.read")),
    db: Session = Depends(get_db),
):
    """
    Compares storage utilization, IOPS, throughput, and latency across multiple volumes
    with explicit AVAILABLE / UNAVAILABLE / STALE / UNSUPPORTED_BY_CONNECTOR metric statuses.
    """
    ids = [s.strip() for s in storage_ids.split(",") if s.strip()] if storage_ids else None
    q_dev = db.query(Device)
    if ids:
        q_dev = q_dev.filter(Device.id.in_(ids))
    devices = q_dev.all()

    persisted = _load_persisted_settings(db)
    stale_hours = float(persisted.get("data_retention_settings", {}).get("stale_telemetry_hours", 24.0))
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    comparisons = []
    for d in devices:
        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == d.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(limit)
            .all()
        )
        records.reverse()
        connectors = db.query(TelemetryConnector).filter(TelemetryConnector.target_storage_id == d.id).all()
        unsupported_perf = any(c.connector_type == "PROMETHEUS" for c in connectors)

        is_stale = True
        if records:
            last_ts = records[-1].timestamp.replace(tzinfo=None)
            age_h = (now_utc - last_ts).total_seconds() / 3600.0
            is_stale = age_h > stale_hours

        r_iops = [r.read_iops for r in records]
        w_iops = [r.write_iops for r in records]
        lat = [r.latency_p95_ms for r in records]
        thr = [r.throughput_mb_s for r in records]
        util = [r.utilization_pct for r in records]

        comparisons.append({
            "storage_id": d.id,
            "name": d.name,
            "tier": d.tier,
            "points_count": len(records),
            "is_stale": is_stale,
            "metrics": {
                "utilization_pct": _summarize_series(util, "%", is_stale=is_stale),
                "read_iops": _summarize_series(r_iops, "IOPS", is_stale=is_stale, unsupported_by_connector=unsupported_perf),
                "write_iops": _summarize_series(w_iops, "IOPS", is_stale=is_stale, unsupported_by_connector=unsupported_perf),
                "latency_p95_ms": _summarize_series(lat, "ms", is_stale=is_stale, unsupported_by_connector=unsupported_perf),
                "throughput_mbps": _summarize_series(thr, "MB/s", is_stale=is_stale, unsupported_by_connector=unsupported_perf),
            },
        })

    return {"compared_count": len(comparisons), "stale_threshold_hours": stale_hours, "volumes": comparisons}


@router.get("/performance/{storage_id}", tags=["Storage Performance Monitoring"])
def get_storage_performance(
    storage_id: str,
    start_date: Optional[str] = Query(None, description="ISO start timestamp filter"),
    end_date: Optional[str] = Query(None, description="ISO end timestamp filter"),
    limit: int = Query(500, ge=1, le=2000),
    current_user: User = Depends(require_permission("performance.read")),
    db: Session = Depends(get_db)
):
    """
    Returns actual storage performance telemetry (IOPS, read/write latency, throughput, utilization),
    summary statistics, and threshold breach evaluation. Missing fields show 'No data available'.
    """
    device = db.query(Device).filter(Device.id == storage_id).first()
    if not device:
        raise HTTPException(status_code=404, detail=f"Storage resource '{storage_id}' not found")

    q = db.query(Telemetry).filter(Telemetry.device_id == storage_id)
    if start_date:
        dt_start = _parse_iso_timestamp(start_date)
        if not dt_start:
            raise HTTPException(status_code=400, detail=f"Invalid start_date '{start_date}'")
        q = q.filter(Telemetry.timestamp >= dt_start)
    if end_date:
        dt_end = _parse_iso_timestamp(end_date)
        if not dt_end:
            raise HTTPException(status_code=400, detail=f"Invalid end_date '{end_date}'")
        q = q.filter(Telemetry.timestamp <= dt_end)

    records = q.order_by(Telemetry.timestamp.desc()).limit(limit).all()
    records.reverse()

    series = []
    r_iops, w_iops, r_lat, w_lat, p95_lat, thr, util = [], [], [], [], [], [], []
    breaches = []

    for r in records:
        rl = getattr(r, "read_latency_ms", None)
        wl = getattr(r, "write_latency_ms", None)
        lat_val = r.latency_p95_ms
        # Note: manual/CSV entries without latency may store None or leave rl/wl None
        r_iops.append(r.read_iops)
        w_iops.append(r.write_iops)
        r_lat.append(rl if rl is not None else lat_val)
        w_lat.append(wl if wl is not None else lat_val)
        p95_lat.append(lat_val)
        thr.append(r.throughput_mb_s)
        util.append(r.utilization_pct)

        if lat_val is not None and lat_val > device.max_acceptable_latency_ms:
            breaches.append({
                "timestamp": r.timestamp.isoformat(),
                "metric": "latency_p95_ms",
                "observed_value": round(float(lat_val), 2),
                "threshold": device.max_acceptable_latency_ms,
            })

        series.append({
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "read_iops": r.read_iops,
            "write_iops": r.write_iops,
            "read_latency_ms": rl if rl is not None else (lat_val if lat_val is not None else None),
            "write_latency_ms": wl if wl is not None else (lat_val if lat_val is not None else None),
            "latency_p95_ms": lat_val,
            "throughput_mbps": r.throughput_mb_s,
            "utilization_pct": r.utilization_pct,
        })

    return {
        "storage_id": storage_id,
        "device_name": device.name,
        "points_count": len(records),
        "thresholds": {
            "warning_utilization_pct": device.warning_threshold_pct,
            "critical_utilization_pct": device.critical_threshold_pct,
            "max_acceptable_latency_ms": device.max_acceptable_latency_ms,
        },
        "summary": {
            "read_iops": _summarize_series(r_iops, "IOPS"),
            "write_iops": _summarize_series(w_iops, "IOPS"),
            "read_latency_ms": _summarize_series(r_lat, "ms"),
            "write_latency_ms": _summarize_series(w_lat, "ms"),
            "latency_p95_ms": _summarize_series(p95_lat, "ms"),
            "throughput_mbps": _summarize_series(thr, "MB/s"),
            "utilization_pct": _summarize_series(util, "%"),
        },
        "threshold_breaches_count": len(breaches),
        "threshold_breaches": breaches[-20:],
        "series": series,
    }
