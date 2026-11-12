import os
import shutil
import time
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

PROVENANCE_LIVE = "LIVE"
PROVENANCE_IMPORTED = "IMPORTED"
PROVENANCE_SYNTHETIC = "SYNTHETIC"
PROVENANCE_SIMULATED = "SIMULATED"

VALID_PROVENANCES = {PROVENANCE_LIVE, PROVENANCE_IMPORTED, PROVENANCE_SYNTHETIC, PROVENANCE_SIMULATED}


class HostStorageCollector:
    """
    AEGISSTOR Real-World Telemetry Collector (Read-Only).
    Provides non-destructive host storage discovery, Prometheus Node Exporter parsing,
    strict validation, staleness detection, and immutable provenance labeling.
    """

    SOURCES_REGISTRY = [
        {
            "id": "host_native",
            "name": "Host Native Storage Collector",
            "type": "NATIVE_OS",
            "read_only": True,
            "permission_boundary": "STORAGE_READ_ONLY_FILESYSTEM",
            "default_endpoint": "localhost (os/shutil)",
            "supported_metrics": ["total_capacity_bytes", "used_bytes", "free_bytes", "utilization_pct"],
            "provenance": PROVENANCE_LIVE
        },
        {
            "id": "prometheus_node_exporter",
            "name": "Prometheus Node Exporter",
            "type": "PROMETHEUS_METRICS",
            "read_only": True,
            "permission_boundary": "STORAGE_READ_ONLY_HTTP_METRICS",
            "default_endpoint": "http://127.0.0.1:9100/metrics",
            "supported_metrics": [
                "node_filesystem_size_bytes",
                "node_filesystem_free_bytes",
                "node_disk_read_bytes_total",
                "node_disk_written_bytes_total",
                "node_disk_reads_completed_total",
                "node_disk_writes_completed_total",
                "node_disk_io_time_seconds_total"
            ],
            "provenance": PROVENANCE_LIVE
        }
    ]

    @staticmethod
    def get_configured_sources() -> List[Dict[str, Any]]:
        """Returns registered sources with explicit permission boundaries."""
        sources = []
        for s in HostStorageCollector.SOURCES_REGISTRY:
            source_info = dict(s)
            source_info["permission_enforced"] = True
            source_info["physical_mutation_permitted"] = False
            sources.append(source_info)
        return sources

    @staticmethod
    def validate_metric_sample(sample: Dict[str, Any], max_age_hours: float = 24.0) -> Dict[str, Any]:
        """
        Validates telemetry sample units, ranges, timestamps, staleness, and provenance.
        Returns dictionary with `is_valid: bool`, `validation_errors: List[str]`, and `is_stale: bool`.
        """
        errors = []
        now = datetime.now(timezone.utc)

        # 1. Provenance validation
        prov = sample.get("provenance")
        if not prov:
            errors.append("Missing provenance label")
        elif prov not in VALID_PROVENANCES:
            errors.append(f"Invalid provenance '{prov}'. Must be one of {sorted(list(VALID_PROVENANCES))}")

        # Rule: Never allow synthetic data to claim LIVE provenance
        if sample.get("is_synthetic") is True and prov == PROVENANCE_LIVE:
            errors.append("PROVENANCE VIOLATION: Generated/synthetic data cannot be labeled as LIVE provenance")

        # 2. Timestamp validation & staleness
        ts = sample.get("timestamp")
        is_stale = False
        if ts is None:
            errors.append("Missing timestamp")
        else:
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except Exception:
                    errors.append(f"Invalid ISO timestamp format: {ts}")
                    ts = None
            if ts:
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                age = (now - ts).total_seconds()
                if age < -300:  # More than 5 minutes in future
                    errors.append(f"Timestamp is in the future: {ts.isoformat()}")
                elif age > (max_age_hours * 3600):
                    is_stale = True

        # 3. Capacity units and bounds
        total = sample.get("total_capacity_bytes")
        used = sample.get("used_bytes")
        free = sample.get("free_bytes")

        if total is not None:
            if not isinstance(total, (int, float)) or total <= 0:
                errors.append(f"total_capacity_bytes must be positive: got {total}")
        if used is not None:
            if not isinstance(used, (int, float)) or used < 0:
                errors.append(f"used_bytes must be non-negative: got {used}")
        if free is not None:
            if not isinstance(free, (int, float)) or free < 0:
                errors.append(f"free_bytes must be non-negative: got {free}")

        if total is not None and used is not None and total > 0:
            if used > total * 1.05:  # Allow 5% margin for root reserve accounting
                errors.append(f"used_bytes ({used}) exceeds total_capacity_bytes ({total})")

        # 4. Utilization range
        util = sample.get("utilization_pct")
        if util is not None:
            if not isinstance(util, (int, float)) or util < 0.0 or util > 100.0:
                errors.append(f"utilization_pct must be within [0.0, 100.0]: got {util}")

        # 5. I/O Metrics non-negativity
        for m in ["read_iops", "write_iops", "throughput_mb_s", "latency_p95_ms", "queue_depth"]:
            val = sample.get(m)
            if val is not None and (not isinstance(val, (int, float)) or val < 0):
                errors.append(f"Metric '{m}' must be non-negative: got {val}")

        return {
            "is_valid": len(errors) == 0,
            "validation_errors": errors,
            "is_stale": is_stale,
            "checked_at": now.isoformat()
        }

    @staticmethod
    def get_available_partitions() -> List[Dict[str, Any]]:
        """
        Discovers local OS filesystem partitions read-only with provenance='LIVE'.
        """
        partitions = []
        now = datetime.now(timezone.utc)

        if os.name == 'nt':
            drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
        else:
            drives = ["/"]
            for test_dir in ["/home", "/var", "/tmp"]:
                if os.path.exists(test_dir):
                    drives.append(test_dir)

        for d in drives:
            try:
                usage = shutil.disk_usage(d)
                used = usage.used
                total = usage.total
                free = usage.free
                pct = round((used / total) * 100.0, 2) if total > 0 else 0.0
                vol_id = f"host-vol-{d.replace(':', '').replace('\\', '').replace('/', 'root')}"

                sample = {
                    "id": vol_id,
                    "name": f"Host Storage Drive ({d})",
                    "path": d,
                    "mount_point": d,
                    "device_identity": f"OS_STORAGE_NODE::{vol_id.upper()}",
                    "total_capacity_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "utilization_pct": pct,
                    "media_type": "Host OS Partition",
                    "tier": "HOST_LOCAL",
                    "provenance": PROVENANCE_LIVE,
                    "is_synthetic": False,
                    "collection_timestamp": now.isoformat(),
                    "read_only": True
                }

                val_result = HostStorageCollector.validate_metric_sample({
                    "provenance": PROVENANCE_LIVE,
                    "is_synthetic": False,
                    "timestamp": now,
                    "total_capacity_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "utilization_pct": pct
                })
                sample["validation"] = val_result
                partitions.append(sample)
            except Exception:
                continue

        return partitions

    @staticmethod
    def sample_telemetry(path: str) -> Dict[str, Any]:
        """
        Samples real filesystem capacity only.

        Standard Python filesystem APIs do not provide disk IOPS, throughput,
        queue depth or request-latency percentiles. Those metrics remain None
        until a real OS/performance collector supplies them.
        """
        now = datetime.now(timezone.utc)
        try:
            usage = shutil.disk_usage(path)
            used = usage.used
            total = usage.total
            free = usage.free
            pct = round((used / total) * 100.0, 2) if total > 0 else 0.0

            result = {
                "timestamp": now.isoformat(),
                "path": path,
                "total_capacity_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "utilization_pct": pct,
                "read_iops": None,
                "write_iops": None,
                "throughput_mb_s": None,
                "latency_p95_ms": None,
                "queue_depth": None,
                "is_synthetic": False,
                "provenance": PROVENANCE_LIVE,
                "source_label": "host_filesystem_capacity_only",
                "metrics_available": ["capacity"],
                "read_only": True
            }

            result["validation"] = HostStorageCollector.validate_metric_sample({
                "provenance": PROVENANCE_LIVE,
                "is_synthetic": False,
                "timestamp": now,
                "total_capacity_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "utilization_pct": pct
            })
            return result
        except Exception as e:
            return {
                "error": type(e).__name__,
                "timestamp": now.isoformat(),
                "path": path,
                "is_synthetic": False,
                "provenance": PROVENANCE_LIVE,
                "source_label": "host_os_read_only_failed",
                "collection_failure": True
            }

    @staticmethod
    def sync_live_partitions_to_db(db) -> List[Dict[str, Any]]:
        """
        Persists only observed host filesystem capacity.

        It deliberately does not generate historical values, IOPS, throughput,
        latency or risk scores. Forecasts become available after enough actual
        timestamped observations have accumulated.
        """
        from app.models.entities import Device, Telemetry
        partitions = HostStorageCollector.get_available_partitions()
        now = datetime.now(timezone.utc)
        synced = []

        for p in partitions:
            dev = db.query(Device).filter(Device.id == p["id"]).first()
            if not dev:
                dev = Device(
                    id=p["id"],
                    name=p["name"],
                    tier="HOST_LOCAL",
                    media_type="Host OS Partition",
                    total_capacity_bytes=p["total_capacity_bytes"],
                    warning_threshold_pct=80.0,
                    critical_threshold_pct=90.0,
                    max_acceptable_latency_ms=15.0,
                    min_free_reserve_pct=10.0,
                    status="HEALTHY",
                    workload_profile="Host Filesystem Capacity",
                    organization_id="org-primary-enterprise",
                )
                db.add(dev)
            else:
                dev.total_capacity_bytes = p["total_capacity_bytes"]
                dev.status = (
                    "CRITICAL" if p["utilization_pct"] >= dev.critical_threshold_pct
                    else "WARNING" if p["utilization_pct"] >= dev.warning_threshold_pct
                    else "HEALTHY"
                )

            latest = (
                db.query(Telemetry)
                .filter(Telemetry.device_id == p["id"])
                .order_by(Telemetry.timestamp.desc())
                .first()
            )
            latest_time = latest.timestamp if latest else None
            if latest_time and latest_time.tzinfo is None:
                latest_time = latest_time.replace(tzinfo=timezone.utc)
            age_seconds = (now - latest_time).total_seconds() if latest_time else None

            # Avoid generating an observation more frequently than every 5 minutes.
            if latest is None or age_seconds is None or age_seconds >= 300:
                db.add(Telemetry(
                    device_id=p["id"],
                    timestamp=now.replace(tzinfo=None),
                    used_bytes=p["used_bytes"],
                    free_bytes=p["free_bytes"],
                    utilization_pct=p["utilization_pct"],
                    read_iops=None,
                    write_iops=None,
                    throughput_mb_s=None,
                    latency_p95_ms=None,
                    queue_depth=None,
                    is_synthetic=False,
                    source_label="host_filesystem_capacity_only",
                ))

            synced.append(p)

        db.commit()
        return synced

    @staticmethod
    def parse_prometheus_text(raw_text: str) -> Dict[str, Any]:
        """
        Parses Prometheus Node Exporter metrics text format safely into structured storage telemetry.
        Extracts filesystem metrics and disk I/O metrics with validation.
        """
        filesystems: Dict[str, Dict[str, Any]] = {}
        disks: Dict[str, Dict[str, Any]] = {}

        now = datetime.now(timezone.utc)

        # Regex for prometheus metric lines: metric_name{labels} value
        metric_regex = re.compile(r'^([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(?:\{([^}]*)\})?\s+([0-9eE\.\+\-]+)(?:\s+[0-9]+)?$')
        label_regex = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*"([^"]*)"')

        for line in raw_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            match = metric_regex.match(line)
            if not match:
                continue

            metric_name, raw_labels, raw_value = match.groups()
            try:
                val = float(raw_value)
            except ValueError:
                continue

            labels = {}
            if raw_labels:
                for lbl_match in label_regex.finditer(raw_labels):
                    k, v = lbl_match.groups()
                    labels[k] = v

            # Parse filesystem metrics
            if metric_name in ("node_filesystem_size_bytes", "node_filesystem_free_bytes", "node_filesystem_avail_bytes"):
                mount = labels.get("mountpoint", "unknown")
                device = labels.get("device", "unknown")
                fstype = labels.get("fstype", "unknown")

                # Filter pseudo filesystems
                if fstype in ("tmpfs", "devtmpfs", "overlay", "squashfs", "iso9660"):
                    continue

                if mount not in filesystems:
                    filesystems[mount] = {
                        "mountpoint": mount,
                        "device": device,
                        "fstype": fstype,
                        "size_bytes": None,
                        "free_bytes": None,
                        "avail_bytes": None
                    }

                if metric_name == "node_filesystem_size_bytes":
                    filesystems[mount]["size_bytes"] = int(val)
                elif metric_name == "node_filesystem_free_bytes":
                    filesystems[mount]["free_bytes"] = int(val)
                elif metric_name == "node_filesystem_avail_bytes":
                    filesystems[mount]["avail_bytes"] = int(val)

            # Parse disk I/O metrics
            elif metric_name in (
                "node_disk_read_bytes_total",
                "node_disk_written_bytes_total",
                "node_disk_reads_completed_total",
                "node_disk_writes_completed_total",
                "node_disk_io_time_seconds_total"
            ):
                disk_name = labels.get("device", "unknown")
                if disk_name not in disks:
                    disks[disk_name] = {"device": disk_name}

                if metric_name == "node_disk_read_bytes_total":
                    disks[disk_name]["read_bytes_total"] = val
                elif metric_name == "node_disk_written_bytes_total":
                    disks[disk_name]["written_bytes_total"] = val
                elif metric_name == "node_disk_reads_completed_total":
                    disks[disk_name]["reads_completed_total"] = val
                elif metric_name == "node_disk_writes_completed_total":
                    disks[disk_name]["writes_completed_total"] = val
                elif metric_name == "node_disk_io_time_seconds_total":
                    disks[disk_name]["io_time_seconds_total"] = val

        # Format parsed filesystem telemetry
        structured_fs = []
        for mount, fs in filesystems.items():
            total = fs.get("size_bytes")
            free = fs.get("free_bytes")
            if total and total > 0 and free is not None:
                used = max(0, total - free)
                pct = round((used / total) * 100.0, 2)
            else:
                used = 0
                pct = 0.0

            fs_record = {
                "mountpoint": mount,
                "device_identity": fs.get("device"),
                "filesystem_type": fs.get("fstype"),
                "total_capacity_bytes": total or 0,
                "used_bytes": used,
                "free_bytes": free or 0,
                "utilization_pct": pct,
                "timestamp": now.isoformat(),
                "provenance": PROVENANCE_LIVE,
                "is_synthetic": False,
                "source": "prometheus_node_exporter",
                "read_only": True
            }

            validation = HostStorageCollector.validate_metric_sample({
                "provenance": PROVENANCE_LIVE,
                "is_synthetic": False,
                "timestamp": now,
                "total_capacity_bytes": total or 0,
                "used_bytes": used,
                "free_bytes": free or 0,
                "utilization_pct": pct
            })
            fs_record["validation"] = validation
            structured_fs.append(fs_record)

        return {
            "status": "PARSED_SUCCESS",
            "timestamp": now.isoformat(),
            "provenance": PROVENANCE_LIVE,
            "filesystems": structured_fs,
            "disks": list(disks.values()),
            "total_filesystems_discovered": len(structured_fs),
            "total_disks_discovered": len(disks)
        }

    @staticmethod
    def scrape_prometheus_node_exporter(endpoint_url: str = "http://127.0.0.1:9100/metrics", timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Executes a non-destructive, read-only HTTP GET to the specified Prometheus Node Exporter.
        Captures network failures, timeouts, and malformed outputs without crashing.
        """
        now = datetime.now(timezone.utc)
        req = urllib.request.Request(
            endpoint_url,
            headers={"User-Agent": "AegisStor-TelemetryCollector/2.0 (read-only)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                if response.status != 200:
                    return {
                        "status": "HTTP_ERROR",
                        "status_code": response.status,
                        "endpoint_url": endpoint_url,
                        "timestamp": now.isoformat(),
                        "provenance": PROVENANCE_LIVE,
                        "error_message": f"Non-200 HTTP response: {response.status}",
                        "collection_failure": True,
                        "filesystems": []
                    }
                content = response.read().decode('utf-8', errors='replace')
                parsed = HostStorageCollector.parse_prometheus_text(content)
                parsed["endpoint_url"] = endpoint_url
                return parsed

        except urllib.error.URLError as e:
            return {
                "status": "ENDPOINT_UNREACHABLE",
                "endpoint_url": endpoint_url,
                "timestamp": now.isoformat(),
                "provenance": PROVENANCE_LIVE,
                "error_message": f"Connection failed: {str(e.reason)}",
                "collection_failure": True,
                "is_operational": False,
                "remedy": "Ensure prometheus node_exporter is running on port 9100 or configure custom endpoint.",
                "filesystems": []
            }
        except Exception as e:
            return {
                "status": "COLLECTION_EXCEPTION",
                "endpoint_url": endpoint_url,
                "timestamp": now.isoformat(),
                "provenance": PROVENANCE_LIVE,
                "error_message": str(e),
                "collection_failure": True,
                "filesystems": []
            }
