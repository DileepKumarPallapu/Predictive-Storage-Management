# AEGISSTOR — Linux Host Storage Collector Guide (`LINUX_COLLECTOR_GUIDE.md`)

## Overview
AEGISSTOR provides both a built-in server connector (`LinuxStorageConnector` in `backend/app/collector/connector_registry.py`) for local host collection and a standalone read-only agent (`backend/scripts/linux_collector_agent.py`) for remote authorized Linux servers.

## Read-Only Interfaces Used
- **Filesystem Capacity**: `shutil.disk_usage` / POSIX `statvfs`, plus `findmnt -J -o TARGET,SOURCE,FSTYPE,OPTIONS` and `/proc/mounts` discovery (ignoring pseudo-filesystems `proc`, `sysfs`, `tmpfs`, `devtmpfs`, `overlay`).
- **Block Device Discovery**: Non-destructive `lsblk -J -b -o NAME,TYPE,SIZE,ROTA,MOUNTPOINT,MODEL`.
- **I/O & Throughput Rates**: Reads cumulative `/proc/diskstats` sectors & completions across two time-spaced samples (`dt >= 0.35s`) to derive actual IOPS (`delta_ops / dt`) and MB/s (`(delta_sectors * 512) / (1024^2 * dt)`). Latency is only reported when cumulative `io_ms` deltas and completed I/O counts are non-zero; otherwise omitted as unavailable (`null`).

## Deploying the Standalone Linux Agent
1. As an **Administrator**, issue a scoped collector API key in `/integrations` (`POST /api/v1/admin/api-keys`, role `OPERATOR`).
2. As an **Operator** (or Admin), register the target storage volume in `/fleet` (e.g. `storage_id: vol-linux-db-01`).
3. On the Linux host, perform a read-only dry-run first:
   ```bash
   python3 backend/scripts/linux_collector_agent.py --mountpoint /var/lib/postgresql --dry-run --once
   ```
4. Start authenticated collection (single run or continuous interval):
   ```bash
   export AEGISSTOR_COLLECTOR_API_KEY="aegis_<your_key>"
   python3 backend/scripts/linux_collector_agent.py \
     --server https://aegisstor.example.com \
     --storage-id vol-linux-db-01 \
     --mountpoint /var/lib/postgresql \
     --interval 60
   ```

## Safety Guarantees
The collector opens only `/proc/mounts`, `/proc/diskstats`, and invokes read-only `findmnt`/`lsblk` listing flags. Zero storage write, mount, format, or resize commands exist in the collector codebase.
