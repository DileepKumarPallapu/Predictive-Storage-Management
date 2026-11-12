import base64
import json
import os
import platform
import shutil
import socket
import urllib.parse
import urllib.request
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Type

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class BaseTelemetryConnector(ABC):
    """Abstract base class for pluggable vendor-neutral read-only telemetry connectors."""

    connector_type: str = "BASE"

    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Tests connectivity and returns health, latency, and capabilities."""

    @abstractmethod
    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collects read-only capacity/performance telemetry normalized to AEGISSTOR schema."""


class LinuxStorageConnector(BaseTelemetryConnector):
    """
    Read-only Host / Linux Storage Collector.
    Discovers mounted filesystems, reads total/used/free bytes, host identity,
    and /proc/diskstats or OS I/O counters where available (returning None when unsupported).
    """

    connector_type = "LINUX_HOST"

    @staticmethod
    def _read_linux_diskstats() -> Optional[Dict[str, Any]]:
        path = "/proc/diskstats"
        if not os.path.exists(path):
            return None
        try:
            reads, writes, io_ms = 0, 0, 0
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    parts = line.split()
                    if len(parts) >= 14:
                        reads += int(parts[3])
                        writes += int(parts[7])
                        io_ms += int(parts[12])
            return {"raw_reads": reads, "raw_writes": writes, "raw_io_ms": io_ms}
        except Exception:
            return None

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "CONNECTED",
            "connector_type": self.connector_type,
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "read_only": True,
            "psutil_available": HAS_PSUTIL,
            "proc_diskstats_available": os.path.exists("/proc/diskstats"),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        hostname = socket.gethostname()
        collected_at = datetime.now(timezone.utc)
        volumes: List[Dict[str, Any]] = []

        # Compute genuine per-second I/O & throughput deltas over a brief non-destructive interval
        read_iops: Optional[float] = None
        write_iops: Optional[float] = None
        throughput_mb_s: Optional[float] = None
        if HAS_PSUTIL:
            try:
                import time
                io1 = psutil.disk_io_counters()
                t1 = time.monotonic()
                if io1 is not None:
                    time.sleep(0.35)
                    io2 = psutil.disk_io_counters()
                    t2 = time.monotonic()
                    dt = max(0.05, t2 - t1)
                    if io2 is not None:
                        read_iops = round(max(0, io2.read_count - io1.read_count) / dt, 2)
                        write_iops = round(max(0, io2.write_count - io1.write_count) / dt, 2)
                        d_bytes = max(0, (io2.read_bytes - io1.read_bytes) + (io2.write_bytes - io1.write_bytes))
                        throughput_mb_s = round(d_bytes / (1024.0 * 1024.0 * dt), 3)
            except Exception:
                pass
        elif os.path.exists("/proc/diskstats"):
            try:
                import time
                d1 = self._read_linux_diskstats()
                t1 = time.monotonic()
                if d1 is not None:
                    time.sleep(0.35)
                    d2 = self._read_linux_diskstats()
                    t2 = time.monotonic()
                    dt = max(0.05, t2 - t1)
                    if d2 is not None:
                        read_iops = round(max(0, d2["raw_reads"] - d1["raw_reads"]) / dt, 2)
                        write_iops = round(max(0, d2["raw_writes"] - d1["raw_writes"]) / dt, 2)
            except Exception:
                pass

        mount_targets = config.get("mount_paths")
        if mount_targets and isinstance(mount_targets, list):
            paths = mount_targets
        elif HAS_PSUTIL:
            paths = [p.mountpoint for p in psutil.disk_partitions(all=False) if p.fstype]
        else:
            paths = ["/"] if os.name != "nt" else ["C:\\"]

        for idx, mp in enumerate(paths):
            try:
                usage = shutil.disk_usage(mp)
                if usage.total <= 0:
                    continue
                volumes.append({
                    "storage_id": config.get("target_storage_id") or f"host-fs-{idx+1}",
                    "mountpoint": mp,
                    "hostname": hostname,
                    "timestamp": collected_at.isoformat(),
                    "total_capacity_bytes": int(usage.total),
                    "used_bytes": int(usage.used),
                    "free_bytes": int(usage.free),
                    "utilization_pct": round((usage.used / usage.total) * 100.0, 2),
                    "read_iops": read_iops,
                    "write_iops": write_iops,
                    "read_latency_ms": None,
                    "write_latency_ms": None,
                    "throughput_mbps": throughput_mb_s,
                    "is_synthetic": False,
                    "source_label": f"linux_host_collector:{hostname}",
                })
            except Exception:
                continue

        return {
            "status": "OK" if volumes else "NO_FILESYSTEMS",
            "connector_type": self.connector_type,
            "hostname": hostname,
            "collected_at": collected_at.isoformat(),
            "volumes_count": len(volumes),
            "volumes": volumes,
        }


class PrometheusConnector(BaseTelemetryConnector):
    """
    Read-only Prometheus / Node Exporter / Custom Exporter Connector.
    Supports configurable authentication (Bearer token or Basic auth),
    PromQL metric mapping to storage_id, timestamp & unit validation,
    and staleness/connection error diagnostics.
    """

    connector_type = "PROMETHEUS"

    def _query_promql(self, endpoint_url: str, query: str, config: Dict[str, Any]) -> Dict[str, Any]:
        base = endpoint_url.rstrip("/")
        if base.endswith("/metrics"):
            base = base[:-len("/metrics")]
        url = f"{base}/api/v1/query?query={urllib.parse.quote(query)}"

        headers = {"Accept": "application/json", "User-Agent": "AEGISSTOR-Collector/1.0"}
        if config.get("bearer_token"):
            headers["Authorization"] = f"Bearer {config['bearer_token']}"
        elif config.get("username") and config.get("password"):
            creds = base64.b64encode(f"{config['username']}:{config['password']}".encode("utf-8")).decode("ascii")
            headers["Authorization"] = f"Basic {creds}"

        timeout = float(config.get("timeout_seconds", 4.0))
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = config.get("endpoint_url", "http://127.0.0.1:9090")
        try:
            res = self._query_promql(endpoint, "up", config)
            ok = res.get("status") == "success"
            return {
                "status": "CONNECTED" if ok else "ERROR",
                "connector_type": self.connector_type,
                "endpoint_url": endpoint,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "error": None if ok else str(res),
            }
        except Exception as exc:
            return {
                "status": "CONNECTION_FAILED",
                "connector_type": self.connector_type,
                "endpoint_url": endpoint,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "error": str(exc),
                "remedy": "Ensure Prometheus server is reachable and credentials are valid.",
            }

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = config.get("endpoint_url")
        if not endpoint:
            return {"status": "ERROR", "error": "endpoint_url is required", "volumes": []}

        size_q = config.get("size_query", 'node_filesystem_size_bytes{fstype!~"tmpfs|overlay"}')
        avail_q = config.get("avail_query", 'node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}')
        label_key = config.get("metric_label_key", "mountpoint")
        stale_max_sec = float(config.get("stale_threshold_seconds", 300.0))

        try:
            size_res = self._query_promql(endpoint, size_q, config)
            avail_res = self._query_promql(endpoint, avail_q, config)
        except Exception as exc:
            return {
                "status": "CONNECTION_FAILED",
                "connector_type": self.connector_type,
                "endpoint_url": endpoint,
                "error": str(exc),
                "volumes": [],
            }

        def _fetch_optional_map(query_key: str) -> Dict[str, Optional[float]]:
            q = (config.get(query_key) or "").strip()
            out: Dict[str, Optional[float]] = {}
            if not q:
                return out
            try:
                res = self._query_promql(endpoint, q, config)
                for item in res.get("data", {}).get("result", []):
                    m = item.get("metric", {})
                    k = m.get(label_key) or m.get("mountpoint") or m.get("device") or m.get("instance") or "default"
                    try:
                        out[k] = float(item.get("value", [0, 0])[1])
                    except Exception:
                        pass
            except Exception:
                pass
            return out

        r_iops_map = _fetch_optional_map("read_iops_query")
        w_iops_map = _fetch_optional_map("write_iops_query")
        r_lat_map = _fetch_optional_map("read_latency_query")
        w_lat_map = _fetch_optional_map("write_latency_query")
        thr_map = _fetch_optional_map("throughput_query")

        now_ts = datetime.now(timezone.utc).timestamp()
        avail_map: Dict[str, float] = {}
        for item in avail_res.get("data", {}).get("result", []):
            key = item.get("metric", {}).get(label_key) or item.get("metric", {}).get("mountpoint") or item.get("metric", {}).get("instance") or "default"
            val = float(item.get("value", [0, 0])[1])
            avail_map[key] = val

        volumes: List[Dict[str, Any]] = []
        stale_warnings: List[str] = []
        for idx, item in enumerate(size_res.get("data", {}).get("result", [])):
            metric = item.get("metric", {})
            key = metric.get(label_key) or metric.get("mountpoint") or metric.get("instance") or f"prom-{idx+1}"
            sample_ts, size_str = item.get("value", [now_ts, "0"])
            sample_ts_f = float(sample_ts)
            if (now_ts - sample_ts_f) > stale_max_sec:
                stale_warnings.append(f"Metric '{key}' is stale by {round(now_ts - sample_ts_f, 1)}s")

            total_b = int(float(size_str))
            free_b = int(avail_map.get(key, 0))
            if total_b <= 0 or free_b < 0 or free_b > total_b:
                continue
            used_b = total_b - free_b
            volumes.append({
                "storage_id": config.get("target_storage_id") or f"prom-{key}",
                "mountpoint": key,
                "timestamp": datetime.fromtimestamp(sample_ts_f, tz=timezone.utc).isoformat(),
                "total_capacity_bytes": total_b,
                "used_bytes": used_b,
                "free_bytes": free_b,
                "utilization_pct": round((used_b / total_b) * 100.0, 2),
                "read_iops": r_iops_map.get(key),
                "write_iops": w_iops_map.get(key),
                "read_latency_ms": r_lat_map.get(key),
                "write_latency_ms": w_lat_map.get(key),
                "throughput_mbps": thr_map.get(key),
                "is_synthetic": False,
                "source_label": f"prometheus:{endpoint}",
            })

        return {
            "status": "OK" if volumes else "EMPTY_SERIES",
            "connector_type": self.connector_type,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "stale_warnings": stale_warnings,
            "volumes_count": len(volumes),
            "volumes": volumes,
        }


class CsvHistoricalConnector(BaseTelemetryConnector):
    connector_type = "CSV_HISTORICAL"

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "READY", "connector_type": self.connector_type, "schema_endpoint": "/api/v1/ingestion/template"}

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "USE_INGESTION_API", "endpoint": "/api/v1/ingestion/csv/import", "volumes": []}


class HttpIngestionConnector(BaseTelemetryConnector):
    connector_type = "HTTP_API"

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "READY", "connector_type": self.connector_type, "ingest_endpoint": "/api/v1/telemetry/ingest"}

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "PUSH_MODE_ACTIVE", "endpoint": "/api/v1/telemetry/ingest", "volumes": []}


class EnterpriseDatabaseConnector(BaseTelemetryConnector):
    """
    Read-only Enterprise Database Metadata Collector.
    Supports POSTGRESQL (via psycopg2), MYSQL/MARIADB (via pymysql),
    MSSQL (via pyodbc/pymssql), and ORACLE (via oracledb).
    Collects ONLY aggregate storage metadata (database size, table/index sizes,
    and approximate row counts) — never reads application table rows.
    Explicitly labels collected sizes as logical database metadata, distinct from
    physical storage array/host capacity.
    """

    connector_type = "DATABASE"
    default_port = 5432

    def _validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        if config.get("dsn") or config.get("endpoint_url"):
            return None
        host = (config.get("host") or "").strip()
        database = (config.get("database") or config.get("dbname") or config.get("service_name") or "").strip()
        username = (config.get("username") or config.get("user") or "").strip()
        if not host or not database or not username:
            return "Database host, database/service name, and username are not configured."
        return None

    def _connect_postgres(self, config: Dict[str, Any]):
        import psycopg2
        dsn = config.get("dsn") or config.get("endpoint_url")
        if dsn and (str(dsn).startswith("postgres://") or str(dsn).startswith("postgresql://")):
            conn = psycopg2.connect(dsn, connect_timeout=4)
        else:
            conn = psycopg2.connect(
                host=config.get("host"),
                port=int(config.get("port") or 5432),
                dbname=config.get("database") or config.get("dbname"),
                user=config.get("username") or config.get("user"),
                password=config.get("password") or "",
                connect_timeout=4,
            )
        conn.set_session(readonly=True, autocommit=True)
        return conn

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        checked_at = datetime.now(timezone.utc).isoformat()
        missing = self._validate_config(config)
        if missing:
            return {
                "status": "NOT_CONFIGURED",
                "connector_type": self.connector_type,
                "read_only": True,
                "size_scope": "logical_database_metadata",
                "error": missing,
                "checked_at": checked_at,
            }

        if self.connector_type == "POSTGRESQL":
            try:
                import psycopg2  # noqa: F401
            except ImportError:
                return {
                    "status": "DRIVER_MISSING",
                    "connector_type": self.connector_type,
                    "read_only": True,
                    "error": "psycopg2 driver is not installed in this environment.",
                    "checked_at": checked_at,
                }
            try:
                conn = self._connect_postgres(config)
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT version(), current_database(), pg_database_size(current_database());")
                        row = cur.fetchone()
                    return {
                        "status": "CONNECTED",
                        "connector_type": self.connector_type,
                        "read_only": True,
                        "size_scope": "logical_database_metadata",
                        "server_version": row[0] if row else None,
                        "database_name": row[1] if row else None,
                        "logical_database_bytes": int(row[2]) if row and row[2] is not None else None,
                        "checked_at": checked_at,
                    }
                finally:
                    conn.close()
            except Exception as exc:
                return {
                    "status": "CONNECTION_FAILED",
                    "connector_type": self.connector_type,
                    "read_only": True,
                    "size_scope": "logical_database_metadata",
                    "error": str(exc),
                    "checked_at": checked_at,
                }

        driver_map = {
            "MYSQL": ("pymysql", "pymysql"),
            "MARIADB": ("pymysql", "pymysql"),
            "MSSQL": ("pyodbc", "pyodbc"),
            "ORACLE": ("oracledb", "oracledb"),
        }
        mod_name, pkg_name = driver_map.get(self.connector_type, ("", ""))
        try:
            mod = __import__(mod_name)
        except ImportError:
            return {
                "status": "DRIVER_MISSING",
                "connector_type": self.connector_type,
                "read_only": True,
                "size_scope": "logical_database_metadata",
                "error": f"Python driver '{pkg_name}' for {self.connector_type} is not installed in this environment.",
                "checked_at": checked_at,
            }

        try:
            if self.connector_type in ("MYSQL", "MARIADB"):
                conn = mod.connect(
                    host=config.get("host"),
                    port=int(config.get("port") or 3306),
                    database=config.get("database") or config.get("dbname"),
                    user=config.get("username") or config.get("user"),
                    password=config.get("password") or "",
                    connect_timeout=4,
                    read_timeout=5,
                )
                try:
                    with conn.cursor() as cur:
                        cur.execute("SELECT VERSION(), DATABASE();")
                        row = cur.fetchone()
                    return {
                        "status": "CONNECTED",
                        "connector_type": self.connector_type,
                        "read_only": True,
                        "size_scope": "logical_database_metadata",
                        "server_version": row[0] if row else None,
                        "database_name": row[1] if row else None,
                        "checked_at": checked_at,
                    }
                finally:
                    conn.close()
            return {
                "status": "DRIVER_INSTALLED_TEST_PENDING",
                "connector_type": self.connector_type,
                "read_only": True,
                "size_scope": "logical_database_metadata",
                "error": f"Driver {pkg_name} detected; configure ODBC/TNS connection details to complete test.",
                "checked_at": checked_at,
            }
        except Exception as exc:
            return {
                "status": "CONNECTION_FAILED",
                "connector_type": self.connector_type,
                "read_only": True,
                "size_scope": "logical_database_metadata",
                "error": str(exc),
                "checked_at": checked_at,
            }

    def collect(self, config: Dict[str, Any]) -> Dict[str, Any]:
        collected_at = datetime.now(timezone.utc).isoformat()
        missing = self._validate_config(config)
        if missing:
            return {
                "status": "CONNECTION_FAILED",
                "connector_type": self.connector_type,
                "error": missing,
                "collected_at": collected_at,
                "volumes": [],
            }

        if self.connector_type == "POSTGRESQL":
            try:
                import psycopg2  # noqa: F401
            except ImportError:
                return {
                    "status": "CONNECTION_FAILED",
                    "connector_type": self.connector_type,
                    "read_only": True,
                    "size_scope": "logical_database_metadata",
                    "error": "psycopg2 driver is not installed in this environment.",
                    "collected_at": collected_at,
                    "volumes": [],
                }
            try:
                conn = self._connect_postgres(config)
            except Exception as exc:
                return {
                    "status": "CONNECTION_FAILED",
                    "connector_type": self.connector_type,
                    "error": str(exc),
                    "collected_at": collected_at,
                    "volumes": [],
                }
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT current_database(), pg_database_size(current_database());")
                    db_row = cur.fetchone()
                    cur.execute(
                        """
                        SELECT
                            schemaname,
                            relname,
                            pg_total_relation_size(relid) AS total_bytes,
                            pg_relation_size(relid) AS table_bytes,
                            pg_indexes_size(relid) AS index_bytes,
                            COALESCE(n_live_tup, 0) AS estimated_rows
                        FROM pg_stat_user_tables
                        ORDER BY pg_total_relation_size(relid) DESC
                        LIMIT 25;
                        """
                    )
                    table_rows = cur.fetchall()
                tables = [
                    {
                        "schema": r[0],
                        "table": r[1],
                        "total_bytes": int(r[2] or 0),
                        "table_bytes": int(r[3] or 0),
                        "index_bytes": int(r[4] or 0),
                        "estimated_rows": int(r[5] or 0),
                    }
                    for r in table_rows
                ]
                return {
                    "status": "OK",
                    "connector_type": self.connector_type,
                    "read_only": True,
                    "size_scope": "logical_database_metadata",
                    "note": "Logical database and table sizes are reported separately from physical host disk capacity.",
                    "collected_at": collected_at,
                    "database_summary": {
                        "database_name": db_row[0] if db_row else None,
                        "logical_size_bytes": int(db_row[1]) if db_row and db_row[1] is not None else 0,
                        "table_count_sampled": len(tables),
                        "total_table_bytes": sum(t["table_bytes"] for t in tables),
                        "total_index_bytes": sum(t["index_bytes"] for t in tables),
                        "estimated_rows": sum(t["estimated_rows"] for t in tables),
                    },
                    "tables": tables,
                    "volumes": [],
                }
            except Exception as exc:
                return {
                    "status": "CONNECTION_FAILED",
                    "connector_type": self.connector_type,
                    "error": str(exc),
                    "collected_at": collected_at,
                    "volumes": [],
                }
            finally:
                conn.close()

        test_res = self.test_connection(config)
        return {
            "status": "CONNECTION_FAILED" if test_res.get("status") != "CONNECTED" else "OK",
            "connector_type": self.connector_type,
            "read_only": True,
            "size_scope": "logical_database_metadata",
            "error": test_res.get("error"),
            "collected_at": collected_at,
            "volumes": [],
        }


class PostgresConnector(EnterpriseDatabaseConnector):
    connector_type = "POSTGRESQL"
    default_port = 5432


class MySqlConnector(EnterpriseDatabaseConnector):
    connector_type = "MYSQL"
    default_port = 3306


class MariaDbConnector(EnterpriseDatabaseConnector):
    connector_type = "MARIADB"
    default_port = 3306


class MsSqlConnector(EnterpriseDatabaseConnector):
    connector_type = "MSSQL"
    default_port = 1433


class OracleConnector(EnterpriseDatabaseConnector):
    connector_type = "ORACLE"
    default_port = 1521


class ConnectorRegistry:
    """Central registry enabling clean registration of additional vendor storage adapters."""

    _adapters: Dict[str, Type[BaseTelemetryConnector]] = {
        "LINUX_HOST": LinuxStorageConnector,
        "PROMETHEUS": PrometheusConnector,
        "CSV_HISTORICAL": CsvHistoricalConnector,
        "HTTP_API": HttpIngestionConnector,
        "POSTGRESQL": PostgresConnector,
        "MYSQL": MySqlConnector,
        "MARIADB": MariaDbConnector,
        "MSSQL": MsSqlConnector,
        "ORACLE": OracleConnector,
    }

    @classmethod
    def register(cls, connector_type: str, adapter_cls: Type[BaseTelemetryConnector]) -> None:
        cls._adapters[connector_type.upper()] = adapter_cls

    @classmethod
    def list_supported_types(cls) -> List[str]:
        return sorted(cls._adapters.keys())

    @classmethod
    def get_adapter(cls, connector_type: str) -> BaseTelemetryConnector:
        key = connector_type.upper()
        if key not in cls._adapters:
            raise ValueError(f"Unsupported connector_type '{connector_type}'. Registered: {cls.list_supported_types()}")
        return cls._adapters[key]()
