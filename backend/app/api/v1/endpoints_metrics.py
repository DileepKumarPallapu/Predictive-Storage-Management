from fastapi import APIRouter, Response, Depends
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Gauge, CollectorRegistry
from app.database import get_db
from app.models.entities import Device, Telemetry

router = APIRouter(prefix="/metrics", tags=["Prometheus Telemetry"])

# Dedicated registry for AEGISSTOR storage metrics
storage_registry = CollectorRegistry()

STORAGE_CAPACITY_BYTES = Gauge(
    "aegisstor_storage_total_bytes",
    "Total provisioned storage capacity in bytes",
    ["device_id", "tier"],
    registry=storage_registry
)
STORAGE_USED_BYTES = Gauge(
    "aegisstor_storage_used_bytes",
    "Current used storage capacity in bytes",
    ["device_id", "tier"],
    registry=storage_registry
)
STORAGE_LATENCY_MS = Gauge(
    "aegisstor_storage_latency_p95_ms",
    "Recent p95 storage access latency in milliseconds",
    ["device_id", "tier"],
    registry=storage_registry
)
STORAGE_IOPS = Gauge(
    "aegisstor_storage_total_iops",
    "Combined read and write IOPS",
    ["device_id", "tier"],
    registry=storage_registry
)
STORAGE_RUNWAY_HOURS = Gauge(
    "aegisstor_storage_reserve_runway_hours",
    "Estimated hours remaining until capacity or latency SLA breach",
    ["device_id"],
    registry=storage_registry
)

@router.get("", summary="Prometheus metric scrape target")
def scrape_prometheus_metrics(db: Session = Depends(get_db)):
    """
    Exposes storage telemetry metrics in standard Prometheus exposition format.
    Suitable for scraping by Prometheus, VictoriaMetrics, or Datadog agents.
    """
    devices = db.query(Device).all()
    for dev in devices:
        tot_cap = float(dev.total_capacity_bytes)
        STORAGE_CAPACITY_BYTES.labels(device_id=dev.id, tier=dev.tier).set(tot_cap)
        
        # Get latest 2 telemetry samples to calculate slope
        recent_tels = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == dev.id)
            .order_by(Telemetry.timestamp.desc())
            .limit(2)
            .all()
        )
        if recent_tels:
            latest = recent_tels[0]
            STORAGE_USED_BYTES.labels(device_id=dev.id, tier=dev.tier).set(float(latest.used_bytes or 0.0))
            STORAGE_LATENCY_MS.labels(device_id=dev.id, tier=dev.tier).set(float(latest.latency_p95_ms or 0.0))
            STORAGE_IOPS.labels(device_id=dev.id, tier=dev.tier).set(float((latest.read_iops or 0.0) + (latest.write_iops or 0.0)))

            # Fast linear runway estimate for scrape target
            crit_bytes = (float(dev.critical_threshold_pct) / 100.0) * tot_cap
            if latest.used_bytes >= crit_bytes:
                runway = 0.0
            elif len(recent_tels) > 1:
                prev = recent_tels[1]
                growth_rate = max(1.0, float(latest.used_bytes - prev.used_bytes))
                runway = max(0.0, (crit_bytes - latest.used_bytes) / growth_rate)
            else:
                runway = 999.0
            STORAGE_RUNWAY_HOURS.labels(device_id=dev.id).set(round(float(runway), 1))
    
    data = generate_latest(storage_registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
