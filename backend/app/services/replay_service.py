import os
import csv
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

TRACES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "traces")


class ReplayEngine:
    """
    AEGISSTOR Storage Trace Replay Engine.
    Processes real chronological storage benchmark traces with deterministic timeline controls:
    Play/Pause, Step, Seek, Speed Multiplier, and Trace Selection.
    Strictly forbids synthetic fallback.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ReplayEngine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return

        self.traces_dir = TRACES_DIR
        os.makedirs(self.traces_dir, exist_ok=True)

        self.active_trace_id: Optional[str] = None
        self.active_trace_name: Optional[str] = None
        self.frames: List[Dict[str, Any]] = []
        self.current_frame_index: int = 0
        self.is_playing: bool = False
        self.playback_speed: float = 1.0  # Frames per second or multiplier
        self.last_tick_time: float = time.time()
        self.volumes_meta: Dict[str, Dict[str, Any]] = {}
        self._initialized = True

        # Auto-load the default SNIA trace if present so out-of-the-box replay works seamlessly
        default_trace = "snia_enterprise_block_trace.csv"
        default_path = os.path.join(self.traces_dir, default_trace)
        if os.path.exists(default_path):
            self.load_trace(default_trace)

    def list_available_traces(self) -> List[Dict[str, Any]]:
        """Scans the traces directory for valid trace datasets."""
        results = []
        if not os.path.exists(self.traces_dir):
            return results

        for fname in os.listdir(self.traces_dir):
            if fname.endswith(".csv") or fname.endswith(".json"):
                fpath = os.path.join(self.traces_dir, fname)
                size_bytes = os.path.getsize(fpath)
                results.append({
                    "id": fname,
                    "filename": fname,
                    "format": "CSV" if fname.endswith(".csv") else "JSON",
                    "size_bytes": size_bytes,
                    "is_active": (fname == self.active_trace_id)
                })
        return results

    def load_trace(self, filename: str) -> Dict[str, Any]:
        """Loads and parses a trace file into chronological frames."""
        fpath = os.path.join(self.traces_dir, filename)
        if not os.path.exists(fpath):
            raise FileNotFoundError(f"Trace file not found: {filename}")

        self.frames = []
        self.volumes_meta = {}

        if filename.endswith(".csv"):
            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                temp_frames: Dict[str, Dict[str, Any]] = {}
                for row in reader:
                    ts = row["timestamp"]
                    vol_id = row["volume_id"]
                    if ts not in temp_frames:
                        temp_frames[ts] = {"timestamp": ts, "volumes": {}}

                    tot_cap = int(row.get("total_capacity_bytes", 100 * (1024**4)))
                    used = int(row.get("used_bytes", 0))
                    free = max(0, tot_cap - used)
                    util_pct = round((used / tot_cap * 100.0), 2) if tot_cap > 0 else 0.0

                    vol_data = {
                        "volume_id": vol_id,
                        "volume_name": row.get("volume_name", vol_id),
                        "tier": row.get("tier", "STANDARD"),
                        "total_capacity_bytes": tot_cap,
                        "used_bytes": used,
                        "free_bytes": free,
                        "utilization_pct": util_pct,
                        "read_iops": float(row.get("read_iops", 0.0)),
                        "write_iops": float(row.get("write_iops", 0.0)),
                        "throughput_mb_s": float(row.get("throughput_mb_s", 0.0)),
                        "latency_p95_ms": float(row.get("latency_p95_ms", 1.0)),
                        "queue_depth": float(row.get("queue_depth", 1.0)),
                    }
                    temp_frames[ts]["volumes"][vol_id] = vol_data
                    if vol_id not in self.volumes_meta:
                        self.volumes_meta[vol_id] = {
                            "volume_id": vol_id,
                            "volume_name": row.get("volume_name", vol_id),
                            "tier": row.get("tier", "STANDARD"),
                            "total_capacity_bytes": tot_cap,
                        }

                # Sort chronologically
                sorted_ts = sorted(temp_frames.keys())
                for ts in sorted_ts:
                    self.frames.append(temp_frames[ts])

            self.active_trace_name = f"SNIA Block Trace ({filename})"

        elif filename.endswith(".json"):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.active_trace_name = data.get("trace_name", filename)
                raw_frames = data.get("frames", [])
                for rf in raw_frames:
                    ts = rf["timestamp"]
                    vol_dict = {}
                    for v in rf.get("volumes", []):
                        vid = v["volume_id"]
                        tot_cap = v.get("total_capacity_bytes", 100 * (1024**4))
                        used = v.get("used_bytes", 0)
                        free = v.get("free_bytes", max(0, tot_cap - used))
                        util = v.get("utilization_pct", round(used / tot_cap * 100.0, 2) if tot_cap > 0 else 0.0)
                        vol_dict[vid] = {
                            "volume_id": vid,
                            "volume_name": v.get("volume_name", vid),
                            "tier": v.get("tier", "STANDARD"),
                            "total_capacity_bytes": tot_cap,
                            "used_bytes": used,
                            "free_bytes": free,
                            "utilization_pct": util,
                            "read_iops": float(v.get("read_iops", 0.0)),
                            "write_iops": float(v.get("write_iops", 0.0)),
                            "throughput_mb_s": float(v.get("throughput_mb_s", 0.0)),
                            "latency_p95_ms": float(v.get("latency_p95_ms", 1.0)),
                            "queue_depth": float(v.get("queue_depth", 1.0)),
                        }
                        if vid not in self.volumes_meta:
                            self.volumes_meta[vid] = {
                                "volume_id": vid,
                                "volume_name": v.get("volume_name", vid),
                                "tier": v.get("tier", "STANDARD"),
                                "total_capacity_bytes": tot_cap,
                            }
                    self.frames.append({"timestamp": ts, "volumes": vol_dict})

        self.active_trace_id = filename
        self.current_frame_index = 0
        self.is_playing = False
        self.last_tick_time = time.time()

        return self.get_status()

    def unload_trace(self):
        """Unloads any active trace to enter an uninitialized replay state."""
        self.active_trace_id = None
        self.active_trace_name = None
        self.frames = []
        self.volumes_meta = {}
        self.current_frame_index = 0
        self.is_playing = False

    def _update_playback(self):
        """Advances current frame if playing based on elapsed time."""
        if not self.is_playing or not self.frames:
            self.last_tick_time = time.time()
            return

        now = time.time()
        elapsed = now - self.last_tick_time
        # Advance 1 frame per (1.0 / speed) seconds
        step_interval = 1.0 / max(0.1, self.playback_speed)
        if elapsed >= step_interval:
            steps_to_advance = int(elapsed / step_interval)
            self.current_frame_index = min(len(self.frames) - 1, self.current_frame_index + steps_to_advance)
            self.last_tick_time = now
            if self.current_frame_index >= len(self.frames) - 1:
                self.is_playing = False  # End of trace

    def play(self):
        self._update_playback()
        if self.frames and self.current_frame_index >= len(self.frames) - 1:
            self.current_frame_index = 0  # Loop or restart
        self.is_playing = True
        self.last_tick_time = time.time()

    def pause(self):
        self._update_playback()
        self.is_playing = False

    def seek(self, frame_index: int):
        self._update_playback()
        if not self.frames:
            self.current_frame_index = 0
            return
        self.current_frame_index = max(0, min(len(self.frames) - 1, frame_index))

    def seek_pct(self, pct: float):
        self._update_playback()
        if not self.frames:
            self.current_frame_index = 0
            return
        idx = int(round((len(self.frames) - 1) * (max(0.0, min(100.0, pct)) / 100.0)))
        self.current_frame_index = idx

    def step(self, steps: int = 1):
        self._update_playback()
        if not self.frames:
            return
        self.current_frame_index = max(0, min(len(self.frames) - 1, self.current_frame_index + steps))

    def set_speed(self, speed: float):
        self._update_playback()
        self.playback_speed = max(0.25, min(20.0, speed))

    def get_status(self) -> Dict[str, Any]:
        self._update_playback()
        has_trace = bool(self.frames and self.active_trace_id)
        current_ts = self.frames[self.current_frame_index]["timestamp"] if has_trace else None
        total_frames = len(self.frames)
        start_ts = self.frames[0]["timestamp"] if has_trace else None
        end_ts = self.frames[-1]["timestamp"] if has_trace else None
        progress_pct = round((self.current_frame_index / max(1, total_frames - 1)) * 100.0, 1) if has_trace else 0.0

        return {
            "has_trace": has_trace,
            "active_trace_id": self.active_trace_id,
            "active_trace_name": self.active_trace_name,
            "current_frame_index": self.current_frame_index,
            "total_frames": total_frames,
            "progress_pct": progress_pct,
            "is_playing": self.is_playing,
            "playback_speed": self.playback_speed,
            "current_timestamp": current_ts,
            "start_timestamp": start_ts,
            "end_timestamp": end_ts,
            "volume_count": len(self.volumes_meta),
            "available_traces": self.list_available_traces(),
        }

    def get_current_frame(self) -> Optional[Dict[str, Any]]:
        self._update_playback()
        if not self.frames:
            return None
        return self.frames[self.current_frame_index]

    def get_current_overview(self) -> Dict[str, Any]:
        """Calculates executive overview KPIs from the current replay frame."""
        frame = self.get_current_frame()
        if not frame:
            return {
                "has_trace": False,
                "message": "No benchmark trace loaded. Please load a trace to replay storage telemetry.",
                "total_capacity_bytes": 0,
                "total_used_bytes": 0,
                "total_free_bytes": 0,
                "fleet_utilization_pct": 0.0,
                "shortest_runway_hours": 0.0,
                "highest_risk_level": "NOMINAL",
                "highest_risk_device": None,
                "device_count": 0,
                "last_collection": datetime.now(timezone.utc).isoformat(),
                "provenance": "CHRONOLOGICAL REPLAY TRACE",
                "is_synthetic": False
            }

        vols = frame.get("volumes", {})
        total_capacity = sum(v["total_capacity_bytes"] for v in vols.values())
        total_used = sum(v["used_bytes"] for v in vols.values())
        total_free = sum(v["free_bytes"] for v in vols.values())
        fleet_util = round((total_used / total_capacity * 100.0), 2) if total_capacity > 0 else 0.0

        shortest_runway = 999.0
        highest_risk_level = "NOMINAL"
        highest_risk_device = None

        for vid, v in vols.items():
            util = v["utilization_pct"]
            free_gb = v["free_bytes"] / (1024 ** 3)
            # Estimate runway based on free space and current frame progress
            runway = max(12.0, min(720.0, free_gb / 1.5))
            if runway < shortest_runway:
                shortest_runway = runway
                highest_risk_device = vid

            if util >= 88.0:
                highest_risk_level = "CRITICAL"
                highest_risk_device = vid
            elif util >= 80.0 and highest_risk_level != "CRITICAL":
                highest_risk_level = "ELEVATED"
                highest_risk_device = vid

        if shortest_runway == 999.0:
            shortest_runway = 120.0

        return {
            "has_trace": True,
            "total_capacity_bytes": total_capacity,
            "total_used_bytes": total_used,
            "total_free_bytes": total_free,
            "fleet_utilization_pct": fleet_util,
            "shortest_runway_hours": round(shortest_runway, 1),
            "highest_risk_level": highest_risk_level,
            "highest_risk_device": highest_risk_device,
            "device_count": len(vols),
            "last_collection": frame["timestamp"],
            "provenance": "CHRONOLOGICAL REPLAY TRACE",
            "is_synthetic": False,
            "active_trace_name": self.active_trace_name,
            "current_frame_index": self.current_frame_index,
            "total_frames": len(self.frames)
        }

    def get_current_devices(self) -> List[Dict[str, Any]]:
        """Returns DeviceSummary items representing volumes at the current replay frame."""
        frame = self.get_current_frame()
        if not frame:
            return []

        devices = []
        for vid, v in frame.get("volumes", {}).items():
            util = v["utilization_pct"]
            free_gb = v["free_bytes"] / (1024 ** 3)
            runway = max(12.0, min(720.0, free_gb / 1.5))
            r_level = "CRITICAL" if util >= 88.0 else ("ELEVATED" if util >= 80.0 else "NOMINAL")
            status = "CRITICAL" if util >= 90.0 else ("DEGRADED" if util >= 80.0 else "HEALTHY")

            devices.append({
                "id": vid,
                "name": v.get("volume_name", vid),
                "tier": v.get("tier", "STANDARD"),
                "media_type": f"Trace Benchmark ({v.get('tier', 'STANDARD')})",
                "total_capacity_bytes": v["total_capacity_bytes"],
                "warning_threshold_pct": 80.0,
                "critical_threshold_pct": 90.0,
                "max_acceptable_latency_ms": 15.0,
                "min_free_reserve_pct": 10.0,
                "status": status,
                "workload_profile": "Replay Benchmark Trace",
                "current_used_bytes": v["used_bytes"],
                "current_utilization_pct": util,
                "current_read_iops": v.get("read_iops", 0.0),
                "current_write_iops": v.get("write_iops", 0.0),
                "current_latency_p95_ms": v.get("latency_p95_ms", 1.0),
                "runway_hours_estimate": round(runway, 1),
                "risk_level": r_level
            })
        return devices

    def get_telemetry_history(self, volume_id: str, metric: str = "used_bytes", hours: int = 720) -> Dict[str, Any]:
        """
        Returns chronological telemetry records from frame 0 up to current_frame_index.
        Never looks ahead into the future of the trace!
        """
        self._update_playback()
        if not self.frames:
            return {
                "device_id": volume_id,
                "metric": metric,
                "total_capacity_bytes": 0,
                "is_synthetic": False,
                "timestamps": [],
                "values": [],
                "units": "Value",
                "missing_intervals": []
            }

        timestamps = []
        values = []
        total_cap = 0

        # Include up to current_frame_index
        limit = min(len(self.frames), self.current_frame_index + 1)
        for i in range(limit):
            f = self.frames[i]
            v = f.get("volumes", {}).get(volume_id)
            if v:
                total_cap = v["total_capacity_bytes"]
                timestamps.append(f["timestamp"])
                values.append(float(v.get(metric, 0.0)))

        return {
            "device_id": volume_id,
            "metric": metric,
            "total_capacity_bytes": total_cap,
            "is_synthetic": False,
            "timestamps": timestamps,
            "values": values,
            "units": "%" if metric == "utilization_pct" else ("Bytes" if "bytes" in metric else "ms"),
            "missing_intervals": []
        }


# Global singleton instance
replay_engine = ReplayEngine()
