import csv
import io
import json
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from app.models.entities import Device, Telemetry, IngestionJob, DataQualityResult
from app.utils.datetime_utils import utc_now

REQUIRED_CSV_COLUMNS = [
    "timestamp",
    "storage_id",
    "total_capacity_bytes",
    "used_capacity_bytes",
]

OPTIONAL_PERF_COLUMNS = [
    "read_iops",
    "write_iops",
    "read_latency_ms",
    "write_latency_ms",
    "throughput_mbps",
]

ALL_CSV_COLUMNS = REQUIRED_CSV_COLUMNS + OPTIONAL_PERF_COLUMNS


def _parse_iso_timestamp(val: str) -> Optional[datetime]:
    if not val or not isinstance(val, str):
        return None
    s = val.strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(s, fmt)
            except Exception:
                continue
        return None


def _parse_optional_float(val: Optional[str], field_name: str) -> Tuple[Optional[float], Optional[str]]:
    if val is None:
        return None, None
    s = str(val).strip()
    if s == "" or s.lower() in ("na", "n/a", "null", "none", "nan"):
        return None, None
    try:
        num = float(s)
        if math.isnan(num) or math.isinf(num):
            return None, f"{field_name} cannot be NaN or Inf"
        if num < 0:
            return None, f"{field_name} cannot be negative ({num})"
        return num, None
    except ValueError:
        return None, f"{field_name} must be numeric (got '{s}')"


class DataPreprocessingPipeline:
    """
    AEGISSTOR Module 3 & 4 — Deterministic Ingestion Validation & Data Quality Engine.
    Never modifies raw source records silently; tracks duplicates, rejections,
    missing fields, outliers, and preprocessing decisions transparently.
    """

    @classmethod
    def validate_and_preprocess_csv(
        cls,
        db: Session,
        csv_text: str,
        default_storage_id: Optional[str] = None
    ) -> Dict[str, Any]:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            return {
                "valid": False,
                "error": "CSV file is empty or missing header row.",
                "total_rows": 0,
                "accepted_rows": 0,
                "rejected_rows": 0,
                "duplicate_rows": 0,
                "missing_columns": REQUIRED_CSV_COLUMNS,
                "preview_rows": [],
                "accepted_records": [],
                "errors": [{"row_number": 1, "reason": "Missing CSV header row"}],
            }

        normalized_headers = [h.strip() for h in reader.fieldnames if h]
        missing_cols = [c for c in REQUIRED_CSV_COLUMNS if c not in normalized_headers]
        if missing_cols:
            return {
                "valid": False,
                "error": f"Missing required CSV columns: {', '.join(missing_cols)}",
                "total_rows": 0,
                "accepted_rows": 0,
                "rejected_rows": 0,
                "duplicate_rows": 0,
                "missing_columns": missing_cols,
                "preview_rows": [],
                "accepted_records": [],
                "errors": [{"row_number": 1, "reason": f"Missing required columns: {missing_cols}"}],
            }

        known_devices = {d.id: d for d in db.query(Device).all()}
        seen_in_file = set()

        # Preload existing (device_id, timestamp) pairs for duplicate detection
        existing_pairs = set()
        for dev_id in known_devices:
            for (ts,) in db.query(Telemetry.timestamp).filter(Telemetry.device_id == dev_id).all():
                if ts:
                    ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                    existing_pairs.add((dev_id, ts_naive.replace(microsecond=0)))

        raw_rows = list(reader)
        total_rows = len(raw_rows)
        accepted_records: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        duplicate_count = 0
        rejected_count = 0
        missing_field_stats: Dict[str, int] = {col: 0 for col in OPTIONAL_PERF_COLUMNS}

        for idx, raw in enumerate(raw_rows, start=2):  # Header is row 1
            row = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}

            ts = _parse_iso_timestamp(row.get("timestamp", ""))
            if ts is None:
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": row.get("storage_id"), "type": "VALIDATION_ERROR", "reason": f"Invalid ISO timestamp '{row.get('timestamp')}'"})
                continue

            sid = row.get("storage_id") or default_storage_id
            if not sid or sid not in known_devices:
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "UNKNOWN_STORAGE_ID", "reason": f"Unknown storage_id '{sid}'"})
                continue

            # Parse total & used capacity
            try:
                total_cap = int(float(row["total_capacity_bytes"]))
                used_cap = int(float(row["used_capacity_bytes"]))
            except (ValueError, TypeError, KeyError):
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "VALIDATION_ERROR", "reason": "total_capacity_bytes and used_capacity_bytes must be valid integers"})
                continue

            if total_cap <= 0:
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "IMPOSSIBLE_CAPACITY", "reason": f"total_capacity_bytes must be > 0 (got {total_cap})"})
                continue

            if used_cap < 0 or used_cap > total_cap:
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "IMPOSSIBLE_CAPACITY", "reason": f"used_capacity_bytes ({used_cap}) must be between 0 and total_capacity_bytes ({total_cap})"})
                continue

            ts_key = (sid, ts.replace(microsecond=0))
            if ts_key in seen_in_file:
                duplicate_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "DUPLICATE_IN_FILE", "reason": f"Duplicate record for {sid} at {ts.isoformat()}"})
                continue
            if ts_key in existing_pairs:
                duplicate_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "DUPLICATE_IN_DB", "reason": f"Telemetry already exists in DB for {sid} at {ts.isoformat()}"})
                continue

            # Optional performance metrics (never manufactured if missing!)
            perf_vals: Dict[str, Optional[float]] = {}
            perf_err = None
            for col in OPTIONAL_PERF_COLUMNS:
                val, err = _parse_optional_float(row.get(col), col)
                if err:
                    perf_err = err
                    break
                if val is None:
                    missing_field_stats[col] += 1
                perf_vals[col] = val

            if perf_err:
                rejected_count += 1
                errors.append({"row_number": idx, "storage_id": sid, "type": "VALIDATION_ERROR", "reason": perf_err})
                continue

            seen_in_file.add(ts_key)
            free_cap = total_cap - used_cap
            util_pct = round((used_cap / total_cap) * 100.0, 2)

            # Combined p95 latency representation when read/write latency provided
            rl = perf_vals["read_latency_ms"]
            wl = perf_vals["write_latency_ms"]
            combined_lat: Optional[float] = None
            if rl is not None and wl is not None:
                combined_lat = round(max(rl, wl), 3)
            elif rl is not None:
                combined_lat = rl
            elif wl is not None:
                combined_lat = wl

            accepted_records.append({
                "row_number": idx,
                "storage_id": sid,
                "timestamp": ts,
                "total_capacity_bytes": total_cap,
                "used_bytes": used_cap,
                "free_bytes": free_cap,
                "utilization_pct": util_pct,
                "read_iops": perf_vals["read_iops"],
                "write_iops": perf_vals["write_iops"],
                "read_latency_ms": rl,
                "write_latency_ms": wl,
                "latency_p95_ms": combined_lat,
                "throughput_mb_s": perf_vals["throughput_mbps"],
            })

        # Sort chronologically
        accepted_records.sort(key=lambda r: (r["storage_id"], r["timestamp"]))

        # Outlier detection on utilization / throughput (Z-score > 3.0)
        outlier_count = 0
        decisions: List[str] = [
            f"Validated {total_rows} received rows against schema and physical invariants.",
            "Sorted valid records chronologically per storage resource.",
            f"Flagged {duplicate_count} duplicate timestamp records and {rejected_count} invalid rows without silent removal."
        ]
        if len(accepted_records) >= 5:
            utils = np.array([r["utilization_pct"] for r in accepted_records], dtype=float)
            std = float(np.std(utils))
            if std > 0:
                mean = float(np.mean(utils))
                z_outliers = [r for r in accepted_records if abs(r["utilization_pct"] - mean) / std > 3.0]
                outlier_count = len(z_outliers)
                if outlier_count > 0:
                    decisions.append(f"Detected {outlier_count} statistical utilization outliers (|z| > 3.0); retained with audit annotation.")

        completeness = round((len(accepted_records) / total_rows) * 100.0, 2) if total_rows > 0 else 0.0
        latest_ts = max((r["timestamp"] for r in accepted_records), default=None)

        preview = [
            {
                **{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in rec.items()}
            }
            for rec in accepted_records[:20]
        ]

        return {
            "valid": len(missing_cols) == 0,
            "total_rows": total_rows,
            "accepted_rows": len(accepted_records),
            "rejected_rows": rejected_count,
            "duplicate_rows": duplicate_count,
            "missing_field_stats": missing_field_stats,
            "outlier_count": outlier_count,
            "data_completeness_pct": completeness,
            "latest_telemetry_timestamp": latest_ts.isoformat() if latest_ts else None,
            "preprocessing_decisions": decisions,
            "preview_rows": preview,
            "accepted_records": accepted_records,
            "errors": errors,
        }

    @classmethod
    def evaluate_storage_data_quality(cls, db: Session, storage_id: str) -> Dict[str, Any]:
        """Evaluates persisted telemetry data quality for a storage resource and stores a DataQualityResult snapshot."""
        device = db.query(Device).filter(Device.id == storage_id).first()
        if not device:
            raise ValueError(f"Storage resource '{storage_id}' not found")

        records = (
            db.query(Telemetry)
            .filter(Telemetry.device_id == storage_id)
            .order_by(Telemetry.timestamp.asc())
            .all()
        )

        total = len(records)
        if total == 0:
            res_obj = DataQualityResult(
                id=f"dq-{uuid.uuid4().hex[:10]}",
                storage_id=storage_id,
                total_records_received=0,
                valid_records=0,
                rejected_records=0,
                duplicate_records=0,
                missing_field_stats_json=json.dumps({}),
                outlier_count=0,
                data_completeness_pct=0.0,
                latest_telemetry_timestamp=None,
                preprocessing_decisions_json=json.dumps(["No telemetry records present for this storage resource."]),
            )
            db.add(res_obj)
            db.commit()
            return cls._serialize_dq(res_obj)

        seen_ts = set()
        duplicates = 0
        invalid_cap = 0
        missing_stats = {
            "read_iops": 0,
            "write_iops": 0,
            "throughput_mb_s": 0,
            "read_latency_ms": 0,
            "write_latency_ms": 0,
            "latency_p95_ms": 0,
        }
        valid_utils = []
        valid_count = 0

        for r in records:
            ts_key = r.timestamp.replace(microsecond=0) if r.timestamp else None
            if ts_key in seen_ts:
                duplicates += 1
            elif ts_key:
                seen_ts.add(ts_key)

            cap_ref = r.total_capacity_bytes or device.total_capacity_bytes
            if r.used_bytes < 0 or (cap_ref and r.used_bytes > cap_ref):
                invalid_cap += 1
            else:
                valid_count += 1
                valid_utils.append(r.utilization_pct)

            if r.read_iops is None:
                missing_stats["read_iops"] += 1
            if r.write_iops is None:
                missing_stats["write_iops"] += 1
            if r.throughput_mb_s is None:
                missing_stats["throughput_mb_s"] += 1
            if getattr(r, "read_latency_ms", None) is None:
                missing_stats["read_latency_ms"] += 1
            if getattr(r, "write_latency_ms", None) is None:
                missing_stats["write_latency_ms"] += 1
            if r.latency_p95_ms is None:
                missing_stats["latency_p95_ms"] += 1

        outliers = 0
        if len(valid_utils) >= 5:
            arr = np.array(valid_utils, dtype=float)
            std = float(np.std(arr))
            if std > 0:
                mean = float(np.mean(arr))
                outliers = int(np.sum(np.abs(arr - mean) / std > 3.0))

        # Check hourly completeness over span
        latest_ts = records[-1].timestamp
        first_ts = records[0].timestamp
        span_hours = max(1, int((latest_ts - first_ts).total_seconds() / 3600.0) + 1)
        completeness = min(100.0, round((len(seen_ts) / max(1, total)) * 100.0, 2))
        if total >= 2 and span_hours > 1:
            temporal_cov = min(100.0, round((len(seen_ts) / span_hours) * 100.0, 2))
            completeness = round(min(completeness, temporal_cov) if total < span_hours else completeness, 2)

        decisions = [
            f"Chronologically inspected {total} stored telemetry records from {first_ts.isoformat()} to {latest_ts.isoformat()}.",
            f"Verified physical capacity consistency (0 <= used_bytes <= total_capacity_bytes): {valid_count} valid, {invalid_cap} inconsistent.",
            f"Identified {duplicates} duplicate timestamps and {outliers} statistical utilization outliers.",
        ]

        res_obj = DataQualityResult(
            id=f"dq-{uuid.uuid4().hex[:10]}",
            storage_id=storage_id,
            total_records_received=total,
            valid_records=valid_count,
            rejected_records=invalid_cap,
            duplicate_records=duplicates,
            missing_field_stats_json=json.dumps(missing_stats),
            outlier_count=outliers,
            data_completeness_pct=completeness,
            latest_telemetry_timestamp=latest_ts,
            preprocessing_decisions_json=json.dumps(decisions),
        )
        db.add(res_obj)
        db.commit()
        return cls._serialize_dq(res_obj)

    @staticmethod
    def _serialize_dq(obj: DataQualityResult) -> Dict[str, Any]:
        return {
            "id": obj.id,
            "storage_id": obj.storage_id,
            "ingestion_job_id": obj.ingestion_job_id,
            "total_records_received": obj.total_records_received,
            "valid_records": obj.valid_records,
            "rejected_records": obj.rejected_records,
            "duplicate_records": obj.duplicate_records,
            "missing_field_stats": json.loads(obj.missing_field_stats_json or "{}"),
            "outlier_count": obj.outlier_count,
            "data_completeness_pct": obj.data_completeness_pct,
            "latest_telemetry_timestamp": obj.latest_telemetry_timestamp.isoformat() if obj.latest_telemetry_timestamp else None,
            "preprocessing_decisions": json.loads(obj.preprocessing_decisions_json or "[]"),
            "evaluated_at": obj.evaluated_at.isoformat() if obj.evaluated_at else None,
        }
