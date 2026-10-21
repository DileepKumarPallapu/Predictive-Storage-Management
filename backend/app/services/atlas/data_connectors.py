"""
AEGISSTOR ATLAS — Reality Data Connector Layer
Provides typed adapters for real Linux diskstats, Prometheus metrics, node_exporter,
and controlled benchmark traces with schema validation, unit normalization, and provenance.
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
import re
from enum import Enum


class DataProvenanceLabel(str, Enum):
    REAL_HARDWARE = "REAL_HARDWARE"
    PUBLIC_BENCHMARK = "PUBLIC_BENCHMARK"
    CONTROLLED_EXPERIMENT = "CONTROLLED_EXPERIMENT"
    SYNTHETIC_SIMULATION = "SYNTHETIC_SIMULATION"


class DataQualityStatus(str, Enum):
    VALID = "VALID"
    SUSPICIOUS = "SUSPICIOUS"
    MISSING_INTERPOLATED = "MISSING_INTERPOLATED"
    OUT_OF_BOUNDS = "OUT_OF_BOUNDS"
    CORRUPTED = "CORRUPTED"


class NormalizedStorageObservation:
    """
    Standardized atomic observation record preserving rigorous provenance and context.
    """
    def __init__(
        self,
        device_id: str,
        timestamp: datetime,
        metric_name: str,
        value: float,
        unit: str,
        source_adapter: str,
        provenance: DataProvenanceLabel,
        quality_status: DataQualityStatus = DataQualityStatus.VALID,
        collection_interval_s: Optional[int] = 3600,
        workload_context: Optional[Dict[str, Any]] = None
    ):
        self.device_id = device_id
        self.timestamp = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        self.ingestion_timestamp = datetime.now(timezone.utc)
        self.metric_name = metric_name
        self.value = float(value)
        self.unit = unit
        self.source_adapter = source_adapter
        self.provenance = provenance
        self.quality_status = quality_status
        self.collection_interval_s = collection_interval_s
        self.workload_context = workload_context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp.isoformat(),
            "ingestion_timestamp": self.ingestion_timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "source_adapter": self.source_adapter,
            "provenance": self.provenance.value,
            "quality_status": self.quality_status.value,
            "collection_interval_s": self.collection_interval_s,
            "workload_context": self.workload_context
        }


class BaseStorageAdapter:
    """
    Abstract adapter defining validation, normalization, and provenance rules.
    """
    ADAPTER_NAME = "BASE_STORAGE_ADAPTER"
    DEFAULT_PROVENANCE = DataProvenanceLabel.REAL_HARDWARE

    @classmethod
    def normalize_unit(cls, metric_name: str, raw_value: float, raw_unit: str) -> Tuple[float, str]:
        """
        Normalizes metrics to standard storage units:
        - Capacity -> Bytes or Percent (%)
        - Throughput -> MB/s
        - Latency -> Milliseconds (ms)
        - Operations -> IOPS
        """
        u = raw_unit.lower().strip()
        v = float(raw_value)

        # Capacity normalizations
        if u in ("tb", "terabytes"):
            return v * (1024 ** 4), "bytes"
        if u in ("gb", "gigabytes"):
            return v * (1024 ** 3), "bytes"
        if u in ("mb", "megabytes"):
            return v * (1024 ** 2), "bytes"
        if u in ("kb", "kilobytes"):
            return v * 1024, "bytes"
        if u in ("b", "bytes"):
            return v, "bytes"
        if u in ("%", "pct", "percent"):
            return v, "pct"

        # Latency normalizations
        if u in ("s", "sec", "seconds"):
            return v * 1000.0, "ms"
        if u in ("us", "microseconds"):
            return v / 1000.0, "ms"
        if u in ("ns", "nanoseconds"):
            return v / 1000000.0, "ms"
        if u in ("ms", "milliseconds"):
            return v, "ms"

        # Throughput normalizations
        if u in ("bytes/s", "b/s"):
            return v / (1024.0 * 1024.0), "MB/s"
        if u in ("kb/s", "kbytes/s"):
            return v / 1024.0, "MB/s"
        if u in ("gb/s", "gbytes/s"):
            return v * 1024.0, "MB/s"
        if u in ("mb/s", "mbytes/s"):
            return v, "MB/s"

        return v, raw_unit

    @classmethod
    def validate_and_normalize(cls, raw_records: List[Dict[str, Any]]) -> List[NormalizedStorageObservation]:
        raise NotImplementedError


class LinuxDiskstatsAdapter(BaseStorageAdapter):
    """
    Parses Linux kernel /proc/diskstats lines and iostat counters.
    Format: [major minor dev_name reads_completed reads_merged sectors_read time_reading ... writes ... time_io ...]
    """
    ADAPTER_NAME = "LINUX_DISKSTATS_ADAPTER"
    DEFAULT_PROVENANCE = DataProvenanceLabel.REAL_HARDWARE

    @classmethod
    def parse_diskstats_line(cls, device_id: str, line: str, timestamp: datetime, sector_size_bytes: int = 512) -> List[NormalizedStorageObservation]:
        tokens = line.strip().split()
        if len(tokens) < 14:
            return []

        dev_name = tokens[2]
        reads_completed = float(tokens[3])
        sectors_read = float(tokens[5])
        time_reading_ms = float(tokens[6])
        writes_completed = float(tokens[7])
        sectors_written = float(tokens[9])
        time_writing_ms = float(tokens[10])
        io_in_flight = float(tokens[11])

        # Sector conversion to MB
        read_mb = (sectors_read * sector_size_bytes) / (1024.0 * 1024.0)
        write_mb = (sectors_written * sector_size_bytes) / (1024.0 * 1024.0)

        read_lat_avg = (time_reading_ms / reads_completed) if reads_completed > 0 else 0.5
        write_lat_avg = (time_writing_ms / writes_completed) if writes_completed > 0 else 0.8

        observations = [
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="read_iops",
                value=reads_completed,
                unit="IOPS",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE,
                workload_context={"kernel_device": dev_name}
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="write_iops",
                value=writes_completed,
                unit="IOPS",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE,
                workload_context={"kernel_device": dev_name}
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="throughput_mb_s",
                value=read_mb + write_mb,
                unit="MB/s",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE,
                workload_context={"kernel_device": dev_name}
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="latency_p95_ms",
                value=max(read_lat_avg, write_lat_avg) * 1.5,  # Approx P95 from mean
                unit="ms",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE,
                workload_context={"kernel_device": dev_name}
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="queue_depth",
                value=io_in_flight,
                unit="requests",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE,
                workload_context={"kernel_device": dev_name}
            )
        ]
        return observations


class PrometheusStorageAdapter(BaseStorageAdapter):
    """
    Ingests Prometheus time-series query results (e.g. node_disk_read_bytes_total, node_disk_io_time_seconds_total).
    """
    ADAPTER_NAME = "PROMETHEUS_STORAGE_ADAPTER"
    DEFAULT_PROVENANCE = DataProvenanceLabel.REAL_HARDWARE

    @classmethod
    def parse_prometheus_metric(
        cls,
        device_id: str,
        metric_name: str,
        values: List[Tuple[float, str]],  # [(timestamp_epoch_s, value_str)]
        raw_unit: str = "bytes"
    ) -> List[NormalizedStorageObservation]:
        observations = []
        for ts_epoch, val_str in values:
            try:
                raw_val = float(val_str)
                ts = datetime.fromtimestamp(ts_epoch, tz=timezone.utc)
                norm_val, norm_unit = cls.normalize_unit(metric_name, raw_val, raw_unit)

                # Quality check
                quality = DataQualityStatus.VALID
                if norm_val < 0.0:
                    quality = DataQualityStatus.OUT_OF_BOUNDS

                obs = NormalizedStorageObservation(
                    device_id=device_id,
                    timestamp=ts,
                    metric_name=metric_name,
                    value=norm_val,
                    unit=norm_unit,
                    source_adapter=cls.ADAPTER_NAME,
                    provenance=cls.DEFAULT_PROVENANCE,
                    quality_status=quality
                )
                observations.append(obs)
            except (ValueError, TypeError):
                continue
        return observations


class BenchmarkTraceAdapter(BaseStorageAdapter):
    """
    Parses controlled storage benchmark outputs (such as FIO JSON logs or SNIA block traces).
    """
    ADAPTER_NAME = "BENCHMARK_TRACE_ADAPTER"
    DEFAULT_PROVENANCE = DataProvenanceLabel.CONTROLLED_EXPERIMENT

    @classmethod
    def parse_fio_json_summary(
        cls,
        device_id: str,
        fio_job: Dict[str, Any],
        timestamp: datetime
    ) -> List[NormalizedStorageObservation]:
        read_info = fio_job.get("read", {})
        write_info = fio_job.get("write", {})

        r_iops = read_info.get("iops", 0.0)
        w_iops = write_info.get("iops", 0.0)
        r_bw_kb = read_info.get("bw", 0.0)
        w_bw_kb = write_info.get("bw", 0.0)

        # FIO lat_ns -> ms
        clat_r_p95 = read_info.get("clat_ns", {}).get("percentile", {}).get("95.000000", 2000000) / 1000000.0
        clat_w_p95 = write_info.get("clat_ns", {}).get("percentile", {}).get("95.000000", 2500000) / 1000000.0

        obs = [
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="read_iops",
                value=float(r_iops),
                unit="IOPS",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="write_iops",
                value=float(w_iops),
                unit="IOPS",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="throughput_mb_s",
                value=(r_bw_kb + w_bw_kb) / 1024.0,
                unit="MB/s",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE
            ),
            NormalizedStorageObservation(
                device_id=device_id,
                timestamp=timestamp,
                metric_name="latency_p95_ms",
                value=max(clat_r_p95, clat_w_p95),
                unit="ms",
                source_adapter=cls.ADAPTER_NAME,
                provenance=cls.DEFAULT_PROVENANCE
            )
        ]
        return obs


class TelemetryStreamSanitizer:
    """
    Enforces stream integrity: sorting, deduplication, gap identification, and quality marking.
    Invariant: Never silently replaces missing values with zero!
    """

    @classmethod
    def sanitize_stream(
        cls,
        observations: List[NormalizedStorageObservation],
        expected_interval_seconds: int = 3600
    ) -> Tuple[List[NormalizedStorageObservation], List[Dict[str, Any]]]:
        if not observations:
            return [], []

        # 1. Sort chronologically
        sorted_obs = sorted(observations, key=lambda x: x.timestamp)

        # 2. Deduplicate by (timestamp, metric_name)
        seen_keys = set()
        deduped = []
        for o in sorted_obs:
            key = (o.timestamp, o.metric_name)
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(o)

        # 3. Detect missing gaps without filling zeros
        detected_gaps = []
        for i in range(1, len(deduped)):
            if deduped[i].metric_name == deduped[i - 1].metric_name:
                dt = (deduped[i].timestamp - deduped[i - 1].timestamp).total_seconds()
                if dt > (expected_interval_seconds * 1.5):
                    missing_hours = dt / 3600.0
                    detected_gaps.append({
                        "metric_name": deduped[i].metric_name,
                        "gap_start": deduped[i - 1].timestamp.isoformat(),
                        "gap_end": deduped[i].timestamp.isoformat(),
                        "duration_hours": round(missing_hours, 2),
                        "missing_intervals_count": int(round(dt / expected_interval_seconds)) - 1
                    })

        return deduped, detected_gaps
