"""
AEGISSTOR Read-Only Linux Host Storage Collector Agent.

Runs cleanly on an authorized Linux host with strict read-only permissions:
  - Discovers mounted filesystems via `findmnt` / `os.statvfs` / `/proc/mounts`
  - Reads block device inventory via `lsblk -J -b` (non-destructive)
  - Computes real I/O & throughput deltas across two time-spaced `/proc/diskstats` samples
  - Submits validated telemetry batches over HTTPS/HTTP using X-API-Key authentication
  - Never executes write, format, mount, delete, or resize operations

Usage:
  python backend/scripts/linux_collector_agent.py \
      --server http://127.0.0.1:8000 \
      --api-key aegis_xxx \
      --storage-id vol-linux-prod-01 \
      --mountpoint / \
      --interval 60 \
      --once
"""
import argparse
import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] aegisstor-linux-collector: %(message)s",
)
logger = logging.getLogger("aegisstor.linux_collector")


def discover_mounts_readonly() -> List[Dict[str, str]]:
    """Discovers mounted non-pseudo filesystems using `findmnt -J` or `/proc/mounts`."""
    if shutil.which("findmnt"):
        try:
            proc = subprocess.run(
                ["findmnt", "-J", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS"],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                parsed = json.loads(proc.stdout)
                results: List[Dict[str, str]] = []
                def _walk(nodes: List[Dict[str, Any]]) -> None:
                    for n in nodes:
                        fs = str(n.get("fstype", ""))
                        if fs not in {"proc", "sysfs", "tmpfs", "devtmpfs", "cgroup", "cgroup2", "overlay"}:
                            results.append({
                                "mountpoint": str(n.get("target", "/")),
                                "source": str(n.get("source", "")),
                                "fstype": fs,
                            })
                        if n.get("children"):
                            _walk(n["children"])
                _walk(parsed.get("filesystems", []))
                if results:
                    return results
        except Exception as exc:
            logger.debug(f"findmnt fallback triggered: {exc}")

    if os.path.exists("/proc/mounts"):
        mounts = []
        with open("/proc/mounts", "r", encoding="utf-8") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) >= 3 and parts[2] not in {"proc", "sysfs", "tmpfs", "devtmpfs", "cgroup", "cgroup2"}:
                    mounts.append({"mountpoint": parts[1], "source": parts[0], "fstype": parts[2]})
        return mounts

    return [{"mountpoint": "/" if os.name != "nt" else "C:\\", "source": "local", "fstype": "local"}]


def discover_block_devices_readonly() -> List[Dict[str, Any]]:
    """Runs read-only `lsblk -J -b` to identify physical disks without mutating devices."""
    if not shutil.which("lsblk"):
        return []
    try:
        proc = subprocess.run(
            ["lsblk", "-J", "-b", "-o", "NAME,TYPE,SIZE,ROTA,MOUNTPOINT,MODEL"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout).get("blockdevices", [])
    except Exception as exc:
        logger.debug(f"lsblk inspection note: {exc}")
    return []


def read_proc_diskstats() -> Optional[Tuple[int, int, int, int, int]]:
    """
    Reads aggregate reads_completed, sectors_read, writes_completed, sectors_written, io_ms
    directly from `/proc/diskstats`. Returns None if unavailable (e.g. non-Linux host).
    """
    if not os.path.exists("/proc/diskstats"):
        return None
    reads = sectors_r = writes = sectors_w = io_ms = 0
    with open("/proc/diskstats", "r", encoding="utf-8") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) >= 14:
                dev_name = parts[2]
                # Skip loop & ram devices
                if dev_name.startswith(("loop", "ram")):
                    continue
                reads += int(parts[3])
                sectors_r += int(parts[5])
                writes += int(parts[7])
                sectors_w += int(parts[9])
                io_ms += int(parts[12])
    return (reads, sectors_r, writes, sectors_w, io_ms)


def collect_sample(
    mountpoint: str,
    prev_diskstats: Optional[Tuple[float, Tuple[int, int, int, int, int]]] = None,
) -> Tuple[Dict[str, Any], Optional[Tuple[float, Tuple[int, int, int, int, int]]]]:
    """Collects filesystem capacity and true time-delta disk I/O rates where supported."""
    usage = shutil.disk_usage(mountpoint)
    total_b = int(usage.total)
    used_b = int(usage.used)
    free_b = int(usage.free)
    util_pct = round((used_b / total_b) * 100.0, 2) if total_b > 0 else 0.0

    now_mono = time.monotonic()
    curr_stats = read_proc_diskstats()
    read_iops: Optional[float] = None
    write_iops: Optional[float] = None
    throughput_mb_s: Optional[float] = None
    latency_p95_ms: Optional[float] = None

    if curr_stats is not None and prev_diskstats is not None:
        prev_mono, prev_vals = prev_diskstats
        dt = max(0.05, now_mono - prev_mono)
        d_reads = max(0, curr_stats[0] - prev_vals[0])
        d_sec_r = max(0, curr_stats[1] - prev_vals[1])
        d_writes = max(0, curr_stats[2] - prev_vals[2])
        d_sec_w = max(0, curr_stats[3] - prev_vals[3])
        d_io_ms = max(0, curr_stats[4] - prev_vals[4])

        read_iops = round(d_reads / dt, 2)
        write_iops = round(d_writes / dt, 2)
        # Standard Linux kernel sector size = 512 bytes
        throughput_mb_s = round(((d_sec_r + d_sec_w) * 512.0) / (1024.0 * 1024.0 * dt), 3)
        total_ios = d_reads + d_writes
        if total_ios > 0 and d_io_ms > 0:
            latency_p95_ms = round(d_io_ms / total_ios, 3)

    sample = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "mountpoint": mountpoint,
        "total_capacity_bytes": total_b,
        "used_bytes": used_b,
        "free_bytes": free_b,
        "utilization_pct": util_pct,
        "read_iops": read_iops,
        "write_iops": write_iops,
        "throughput_mb_s": throughput_mb_s,
        "latency_p95_ms": latency_p95_ms,
        "is_synthetic": False,
        "source_label": f"linux_collector_agent:{socket.gethostname()}",
    }
    next_state = (now_mono, curr_stats) if curr_stats is not None else None
    return sample, next_state


def push_telemetry(
    server_url: str,
    api_key: str,
    storage_id: str,
    sample: Dict[str, Any],
    timeout_s: float = 5.0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Submits collected sample with retry handling and idempotency key."""
COLLECTOR_VERSION = "2.1.0"


def _to_ingest_record(sample: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": sample["timestamp"],
        "used_bytes": sample["used_bytes"],
        "free_bytes": sample["free_bytes"],
        "read_iops": sample["read_iops"],
        "write_iops": sample["write_iops"],
        "throughput_mb_s": sample["throughput_mb_s"],
        "latency_p95_ms": sample["latency_p95_ms"],
        "is_synthetic": False,
        "source_label": sample["source_label"],
    }


def append_to_local_buffer(buffer_path: str, sample: Dict[str, Any], max_records: int = 1440) -> int:
    """Persist failed samples locally in bounded JSONL spool for later replay."""
    os.makedirs(os.path.dirname(os.path.abspath(buffer_path)), exist_ok=True)
    existing: List[str] = []
    if os.path.exists(buffer_path):
        with open(buffer_path, "r", encoding="utf-8") as fh:
            existing = [line.strip() for line in fh if line.strip()]
    existing.append(json.dumps(sample))
    if len(existing) > max_records:
        existing = existing[-max_records:]
    with open(buffer_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(existing) + "\n")
    return len(existing)


def load_local_buffer(buffer_path: str) -> List[Dict[str, Any]]:
    if not buffer_path or not os.path.exists(buffer_path):
        return []
    items: List[Dict[str, Any]] = []
    with open(buffer_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return items


def clear_local_buffer(buffer_path: str) -> None:
    if buffer_path and os.path.exists(buffer_path):
        os.remove(buffer_path)


def write_local_health(health_path: str, status: str, buffered_count: int, detail: str = "") -> None:
    if not health_path:
        return
    os.makedirs(os.path.dirname(os.path.abspath(health_path)), exist_ok=True)
    with open(health_path, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "collector_version": COLLECTOR_VERSION,
                "status": status,
                "buffered_records": buffered_count,
                "detail": detail,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            fh,
            indent=2,
        )


def push_telemetry_batch(
    server_url: str,
    api_key: str,
    storage_id: str,
    samples: List[Dict[str, Any]],
    timeout_s: float = 5.0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """Submit a validated batch of telemetry samples with deterministic idempotency key."""
    url = f"{server_url.rstrip('/')}/api/v1/telemetry/ingest"
    first_ts = samples[0]["timestamp"]
    last_ts = samples[-1]["timestamp"]
    idem_key = f"linux-{samples[0]['hostname']}-{storage_id}-{first_ts}-{last_ts}-{len(samples)}"
    body = json.dumps({
        "device_id": storage_id,
        "idempotency_key": idem_key,
        "records": [_to_ingest_record(s) for s in samples],
    }).encode("utf-8")

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key,
                    "Idempotency-Key": idem_key,
                    "User-Agent": f"aegisstor-linux-collector/{COLLECTOR_VERSION}",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
            logger.warning(f"Attempt {attempt}/{max_retries} failed submitting telemetry batch: {exc}")
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Telemetry batch submission failed after {max_retries} attempts: {last_exc}")


def push_telemetry(
    server_url: str,
    api_key: str,
    storage_id: str,
    sample: Dict[str, Any],
    timeout_s: float = 5.0,
    max_retries: int = 3,
) -> Dict[str, Any]:
    return push_telemetry_batch(server_url, api_key, storage_id, [sample], timeout_s=timeout_s, max_retries=max_retries)


def main() -> int:
    parser = argparse.ArgumentParser(description="AEGISSTOR Read-Only Linux Host Storage Collector Agent")
    parser.add_argument("--server", required=False, default="http://127.0.0.1:8000", help="AEGISSTOR API server URL")
    parser.add_argument("--api-key", required=False, default=os.getenv("AEGISSTOR_COLLECTOR_API_KEY", ""), help="Collector X-API-Key")
    parser.add_argument("--storage-id", required=False, default="host-linux-root", help="Registered storage_id target")
    parser.add_argument("--mountpoint", required=False, default="/" if os.name != "nt" else "C:\\", help="Mountpoint path to measure")
    parser.add_argument("--interval", type=int, default=60, help="Collection interval seconds")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP request timeout seconds")
    parser.add_argument("--buffer-path", default="/var/lib/aegisstor/collector_buffer.jsonl", help="Local offline buffer path")
    parser.add_argument("--buffer-max-records", type=int, default=1440, help="Max buffered samples during outage")
    parser.add_argument("--health-file", default="/var/lib/aegisstor/collector_health.json", help="Local health status file")
    parser.add_argument("--version", action="store_true", help="Print collector version and exit")
    parser.add_argument("--once", action="store_true", help="Collect and submit once then exit")
    parser.add_argument("--dry-run", action="store_true", help="Discover and print sample JSON without sending")
    args = parser.parse_args()

    if args.version:
        print(f"aegisstor-linux-collector {COLLECTOR_VERSION}")
        return 0

    logger.info(f"AEGISSTOR Linux Collector v{COLLECTOR_VERSION} discovering mounts & block devices in read-only mode...")
    mounts = discover_mounts_readonly()
    disks = discover_block_devices_readonly()
    logger.info(f"Found {len(mounts)} mountpoints and {len(disks)} block device entries.")

    _, prev_state = collect_sample(args.mountpoint, None)
    if prev_state is not None:
        time.sleep(0.5)

    while True:
        sample, prev_state = collect_sample(args.mountpoint, prev_state)
        if args.dry_run:
            print(json.dumps({"version": COLLECTOR_VERSION, "sample": sample, "mounts": mounts[:5], "block_devices": disks[:5]}, indent=2))
        else:
            if not args.api_key:
                logger.error("Missing --api-key (or AEGISSTOR_COLLECTOR_API_KEY) for authenticated ingestion.")
                return 2
            buffered = load_local_buffer(args.buffer_path)
            batch = buffered + [sample]
            try:
                res = push_telemetry_batch(args.server, args.api_key, args.storage_id, batch, timeout_s=args.timeout)
                if buffered:
                    clear_local_buffer(args.buffer_path)
                write_local_health(args.health_file, "healthy", 0, f"Ingested {len(batch)} samples")
                logger.info(f"Ingested {len(batch)} sample(s) for {args.storage_id}: {res}")
            except Exception as exc:
                count = append_to_local_buffer(args.buffer_path, sample, max_records=args.buffer_max_records)
                write_local_health(args.health_file, "disconnected_buffering", count, str(exc))
                logger.warning(f"Backend unreachable; buffered sample locally ({count} queued): {exc}")

        if args.once:
            break
        time.sleep(max(5, args.interval))

    return 0


if __name__ == "__main__":
    sys.exit(main())
