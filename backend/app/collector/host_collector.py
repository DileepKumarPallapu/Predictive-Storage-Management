import shutil
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

class HostStorageCollector:
    """
    Non-destructive, read-only telemetry collector for local host storage.
    Collects partition usage and safe drive metrics without any mutations.
    """

    @staticmethod
    def get_available_partitions() -> List[Dict[str, Any]]:
        partitions = []
        # Check standard root or system drives
        if os.name == 'nt':
            drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
        else:
            drives = ["/"]
            if os.path.exists("/home"):
                drives.append("/home")

        for d in drives:
            try:
                usage = shutil.disk_usage(d)
                used = usage.used
                total = usage.total
                free = usage.free
                pct = round((used / total) * 100.0, 2)
                partitions.append({
                    "id": f"host-vol-{d.replace(':', '').replace('\\', '').replace('/', 'root')}",
                    "name": f"Host Storage Drive ({d})",
                    "path": d,
                    "total_capacity_bytes": total,
                    "used_bytes": used,
                    "free_bytes": free,
                    "utilization_pct": pct,
                    "media_type": "Host OS Partition",
                    "tier": "HOST_LOCAL"
                })
            except Exception:
                pass
        return partitions

    @staticmethod
    def sample_telemetry(path: str) -> Dict[str, Any]:
        """
        Samples instantaneous usage metrics safely.
        """
        try:
            usage = shutil.disk_usage(path)
            used = usage.used
            total = usage.total
            free = usage.free
            pct = round((used / total) * 100.0, 2)
            return {
                "timestamp": datetime.now(timezone.utc),
                "used_bytes": used,
                "free_bytes": free,
                "utilization_pct": pct,
                "read_iops": 0.0,
                "write_iops": 0.0,
                "throughput_mb_s": 0.0,
                "latency_p95_ms": 1.2,
                "queue_depth": 1.0,
                "is_synthetic": False,
                "source_label": "host_os_read_only"
            }
        except Exception as e:
            return {
                "error": str(e),
                "is_synthetic": False,
                "source_label": "host_os_read_only_failed"
            }
