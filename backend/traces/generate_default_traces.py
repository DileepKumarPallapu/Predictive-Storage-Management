import csv
import json
import math
from datetime import datetime, timedelta, timezone

def generate_snia_trace():
    base_time = datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)
    csv_file = "traces/snia_enterprise_block_trace.csv"
    
    rows = []
    # 168 hours = 7 full days of trace records
    for h in range(168):
        current_time = base_time + timedelta(hours=h)
        iso_time = current_time.isoformat()
        day_of_week = current_time.weekday()
        hour_of_day = current_time.hour
        
        # Diurnal pattern
        activity_factor = 0.4 + 0.6 * math.sin(math.pi * (hour_of_day - 6) / 12) if 6 <= hour_of_day <= 22 else 0.25
        if day_of_week in (5, 6): # weekend
            activity_factor *= 0.5
            
        # Volume 1: NVMe Primary OLTP (100 TB capacity)
        cap_nvme = 100 * (1024**4)
        used_nvme = int(cap_nvme * (0.68 + (h / 168.0) * 0.18 + 0.01 * math.sin(h / 6.0)))
        read_iops_nvme = round(12000 * activity_factor + 800, 1)
        write_iops_nvme = round(9500 * activity_factor + 600, 1)
        throughput_nvme = round(450.0 * activity_factor + 35.0, 2)
        latency_nvme = round(0.8 + 1.6 * activity_factor + (0.4 if used_nvme / cap_nvme > 0.82 else 0.0), 3)
        queue_depth_nvme = round(2.0 + 12.0 * activity_factor, 1)

        rows.append({
            "timestamp": iso_time,
            "volume_id": "vol-replay-nvme",
            "volume_name": "Tier-1 NVMe OLTP Cluster",
            "tier": "NVME",
            "total_capacity_bytes": cap_nvme,
            "used_bytes": used_nvme,
            "read_iops": read_iops_nvme,
            "write_iops": write_iops_nvme,
            "throughput_mb_s": throughput_nvme,
            "latency_p95_ms": latency_nvme,
            "queue_depth": queue_depth_nvme
        })

        # Volume 2: SAS High-Capacity Data Lake (500 TB capacity)
        cap_sas = 500 * (1024**4)
        used_sas = int(cap_sas * (0.55 + (h / 168.0) * 0.08 + 0.005 * math.cos(h / 8.0)))
        read_iops_sas = round(3200 * activity_factor + 300, 1)
        write_iops_sas = round(4800 * activity_factor + 400, 1)
        throughput_sas = round(280.0 * activity_factor + 25.0, 2)
        latency_sas = round(4.2 + 5.1 * activity_factor, 3)
        queue_depth_sas = round(4.0 + 18.0 * activity_factor, 1)

        rows.append({
            "timestamp": iso_time,
            "volume_id": "vol-replay-sas",
            "volume_name": "Tier-2 SAS Bulk Storage",
            "tier": "SAS",
            "total_capacity_bytes": cap_sas,
            "used_bytes": used_sas,
            "read_iops": read_iops_sas,
            "write_iops": write_iops_sas,
            "throughput_mb_s": throughput_sas,
            "latency_p95_ms": latency_sas,
            "queue_depth": queue_depth_sas
        })

    fieldnames = [
        "timestamp", "volume_id", "volume_name", "tier",
        "total_capacity_bytes", "used_bytes",
        "read_iops", "write_iops", "throughput_mb_s",
        "latency_p95_ms", "queue_depth"
    ]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} records in {csv_file}")

def generate_fiu_trace():
    base_time = datetime(2026, 3, 10, 0, 0, 0, tzinfo=timezone.utc)
    json_file = "traces/fiu_datacenter_trace.json"
    frames = []

    for h in range(72): # 3 days trace
        current_time = base_time + timedelta(hours=h)
        iso_time = current_time.isoformat()
        
        cap = 250 * (1024**4)
        used = int(cap * (0.60 + (h / 72.0) * 0.22)) # Rapid growth, nearing runway exhaustion
        
        frames.append({
            "timestamp": iso_time,
            "volumes": [
                {
                    "volume_id": "vol-fiu-analytics",
                    "volume_name": "FIU Analytics Production Store",
                    "tier": "SSD",
                    "total_capacity_bytes": cap,
                    "used_bytes": used,
                    "free_bytes": cap - used,
                    "utilization_pct": round(used / cap * 100.0, 2),
                    "read_iops": round(7500.0 + 1500.0 * math.sin(h / 3.0), 1),
                    "write_iops": round(11000.0 + 2000.0 * math.cos(h / 4.0), 1),
                    "throughput_mb_s": 320.0,
                    "latency_p95_ms": round(2.5 + (h / 72.0) * 8.0, 2),
                    "queue_depth": round(6.0 + (h / 72.0) * 20.0, 1)
                }
            ]
        })

    data = {
        "trace_name": "FIU Production Datacenter Trace (Rapid Influx)",
        "source": "Florida International University Storage Research",
        "total_frames": len(frames),
        "time_interval_hours": 1,
        "frames": frames
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Generated {len(frames)} frames in {json_file}")

if __name__ == "__main__":
    generate_snia_trace()
    generate_fiu_trace()
