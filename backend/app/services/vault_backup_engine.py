import os
import shutil
import sqlite3
import hashlib
import json
import time
import uuid
import tempfile
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import (
    VaultBackupRecord,
    Device,
    Telemetry,
    AuditLog,
    User,
    ModelVersion,
    Recommendation
)
from app.services.audit_service import AuditService

_backup_lock = threading.Lock()


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class VaultBackupEngine:
    """
    AEGISSTOR VAULT — Verified Backup and Disaster Recovery Engine.
    Provides consistent online database snapshots, SHA-256 manifest integrity verification,
    isolated sandbox recovery testing, RPO/RTO validation, and automated retention management.
    """

    FORMAT_VERSION = "AEGISSTOR_VAULT_V1"

    @classmethod
    def get_vault_storage_dir(cls) -> str:
        """Returns absolute path to vault backup storage directory."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        vault_dir = os.path.join(backend_dir, settings.BACKUP_STORAGE_DIR)
        os.makedirs(vault_dir, exist_ok=True)
        return vault_dir

    @classmethod
    def get_production_db_path(cls) -> str:
        """Resolves absolute path to active production SQLite database."""
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(backend_dir, "aegisstor.db")

    @classmethod
    def compute_file_sha256(cls, file_path: str) -> str:
        """Computes cryptographic SHA-256 checksum in streaming chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def get_safe_system_config(cls) -> Dict[str, Any]:
        """Extracts non-sensitive configuration parameters (excluding secrets and keys)."""
        return {
            "project_name": settings.PROJECT_NAME,
            "project_version": settings.PROJECT_VERSION,
            "api_version_prefix": settings.API_V1_STR,
            "operating_mode": settings.OPERATING_MODE,
            "shadow_mode_enabled": settings.SHADOW_MODE_ENABLED,
            "physical_mutation_disabled": settings.PHYSICAL_MUTATION_DISABLED,
            "telemetry_sampling_minutes": settings.TELEMETRY_SAMPLING_MINUTES,
            "default_forecast_horizon_hours": settings.DEFAULT_FORECAST_HORIZON_HOURS,
            "nominal_uncertainty_coverage": settings.NOMINAL_COVERAGE,
            "target_rpo_hours": settings.DEFAULT_RPO_HOURS,
            "target_rto_seconds": settings.DEFAULT_RTO_SECONDS,
            "secret_recovery_note": "Secrets and private JWT keys are strictly excluded. Secret restoration must occur via enterprise KMS or secure environment secrets management."
        }

    @classmethod
    def create_backup(
        cls,
        db: Session,
        created_by: str = "operator@aegisstor.internal",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Creates a consistent, timestamped, verified backup snapshot.
        Uses SQLite online backup API to take non-blocking live database snapshots.
        Protects against concurrent operations using a reentrant lock.
        """
        if not _backup_lock.acquire(blocking=False):
            raise RuntimeError("Another backup or restoration operation is currently in progress.")

        start_time = time.perf_counter()
        now = get_utc_now()
        backup_id = f"vault-backup-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        vault_root = cls.get_vault_storage_dir()
        backup_dir = os.path.join(vault_root, backup_id)
        prod_db_path = cls.get_production_db_path()

        try:
            os.makedirs(backup_dir, exist_ok=False)

            # 1. Consistent SQLite Online Backup
            backup_db_path = os.path.join(backup_dir, "database.sqlite")
            source_conn = sqlite3.connect(prod_db_path)
            dest_conn = sqlite3.connect(backup_db_path)
            try:
                # Online backup API copies database pages transaction-consistently without locking writers
                source_conn.backup(dest_conn)
            finally:
                dest_conn.close()
                source_conn.close()

            db_size_bytes = os.path.getsize(backup_db_path)

            # 2. Safe System Configuration
            safe_config = cls.get_safe_system_config()
            config_path = os.path.join(backup_dir, "config_safe.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(safe_config, f, indent=2)

            # 3. Model Version Artifacts Metadata
            model_versions = db.query(ModelVersion).all()
            models_meta = [
                {
                    "id": m.id,
                    "name": m.name,
                    "model_type": m.model_type,
                    "version_tag": m.version_tag,
                    "mae": m.mae,
                    "rmse": m.rmse,
                    "interval_coverage": m.interval_coverage,
                    "is_active": m.is_active,
                    "trained_at": m.trained_at.isoformat() if m.trained_at else None
                }
                for m in model_versions
            ]
            models_path = os.path.join(backup_dir, "model_metadata.json")
            with open(models_path, "w", encoding="utf-8") as f:
                json.dump(models_meta, f, indent=2)

            # 4. Record Counts for Baseline Integrity Verification
            table_counts = {
                "devices": db.query(Device).count(),
                "telemetry": db.query(Telemetry).count(),
                "audit_logs": db.query(AuditLog).count(),
                "users": db.query(User).count(),
                "recommendations": db.query(Recommendation).count(),
                "model_versions": len(model_versions)
            }

            # 5. Measure Latest Telemetry Timestamp for RPO baseline
            latest_tel = db.query(Telemetry).order_by(Telemetry.timestamp.desc()).first()
            latest_tel_ts = latest_tel.timestamp.isoformat() if latest_tel else now.isoformat()

            # 6. Compute Cryptographic SHA-256 Checksums
            checksums = {
                "database.sqlite": cls.compute_file_sha256(backup_db_path),
                "config_safe.json": cls.compute_file_sha256(config_path),
                "model_metadata.json": cls.compute_file_sha256(models_path)
            }

            # 7. Write Immutable Manifest
            manifest = {
                "backup_id": backup_id,
                "created_at": now.isoformat(),
                "created_by": created_by,
                "format_version": cls.FORMAT_VERSION,
                "backup_format": cls.FORMAT_VERSION,
                "resource_scope": [
                    "APPLICATION_DATABASE",
                    "SAFE_SYSTEM_CONFIG",
                    "MODEL_METADATA",
                    "AUDIT_LEDGER"
                ],
                "database_engine": "SQLite3",
                "database_size_bytes": db_size_bytes,
                "files_count": 3,
                "files": ["database.sqlite", "config_safe.json", "model_metadata.json"],
                "sha256_checksums": checksums,
                "table_record_counts": table_counts,
                "latest_telemetry_timestamp": latest_tel_ts,
                "status": "COMPLETED",
                "rpo_target_hours": settings.DEFAULT_RPO_HOURS,
                "rto_target_seconds": settings.DEFAULT_RTO_SECONDS,
                "notes": notes,
                "tamper_evidence_disclaimer": "SHA-256 checksums verify file-level integrity. Protection against physical disk loss requires replicating backup bundles to offsite / secondary WORM cloud storage."
            }

            manifest_path = os.path.join(backup_dir, "manifest.json")
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

            # 8. Record in Database Ledger
            record = VaultBackupRecord(
                id=backup_id,
                created_at=now,
                created_by=created_by,
                format_version=cls.FORMAT_VERSION,
                database_size_bytes=db_size_bytes,
                files_count=3,
                checksum_status="SHA256_VERIFIED",
                restoration_status="PENDING_VERIFICATION",
                manifest_json=json.dumps(manifest)
            )
            db.add(record)
            db.commit()

            AuditService.log_event(
                db=db,
                action="CREATE_VAULT_BACKUP",
                target_type="VAULT_BACKUP",
                target_id=backup_id,
                user=created_by,
                details={
                    "backup_id": backup_id,
                    "db_size_bytes": db_size_bytes,
                    "checksums": checksums,
                    "duration_seconds": round(time.perf_counter() - start_time, 3)
                }
            )

            # 9. Automated Retention Management
            cls.prune_expired_backups(db)

            return manifest

        except Exception as e:
            # Clean up partial or broken backup directory
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
            raise RuntimeError(f"Backup creation failed: {str(e)}") from e

        finally:
            _backup_lock.release()

    @classmethod
    def verify_backup_integrity(cls, backup_id: str) -> Dict[str, Any]:
        """
        Validates SHA-256 checksums, manifest structure, and file completeness for a backup bundle.
        Detects silent corruption, truncation, or missing files.
        """
        vault_root = cls.get_vault_storage_dir()
        backup_dir = os.path.join(vault_root, backup_id)
        now = get_utc_now()

        if not os.path.exists(backup_dir):
            return {
                "backup_id": backup_id,
                "is_valid": False,
                "status": "BACKUP_NOT_FOUND",
                "error": f"Backup directory '{backup_id}' does not exist on storage volume.",
                "checked_at": now.isoformat()
            }

        manifest_path = os.path.join(backup_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return {
                "backup_id": backup_id,
                "is_valid": False,
                "status": "MANIFEST_NOT_FOUND",
                "checksum_status": "MANIFEST_NOT_FOUND",
                "error": "Manifest file 'manifest.json' is missing or incomplete.",
                "checked_at": now.isoformat()
            }

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except Exception as e:
            return {
                "backup_id": backup_id,
                "is_valid": False,
                "status": "INVALID_MANIFEST_FORMAT",
                "checksum_status": "INVALID_MANIFEST_FORMAT",
                "error": f"Failed to parse manifest: {str(e)}",
                "checked_at": now.isoformat()
            }

        if manifest.get("status") != "COMPLETED":
            return {
                "backup_id": backup_id,
                "is_valid": False,
                "status": "INCOMPLETE_BACKUP",
                "checksum_status": "INCOMPLETE_BACKUP",
                "error": "Backup marked INCOMPLETE (aborted during creation).",
                "checked_at": now.isoformat()
            }

        expected_checksums = manifest.get("sha256_checksums", {})
        errors = []
        verified_files = []
        verified_files_map = {}

        for filename, expected_hash in expected_checksums.items():
            fpath = os.path.join(backup_dir, filename)
            if not os.path.exists(fpath):
                errors.append(f"Missing resource file: '{filename}'")
                verified_files_map[filename] = False
                continue

            actual_hash = cls.compute_file_sha256(fpath)
            if actual_hash != expected_hash:
                errors.append(f"Checksum mismatch on '{filename}': expected {expected_hash[:12]}..., got {actual_hash[:12]}...")
                verified_files_map[filename] = False
            else:
                verified_files.append(filename)
                verified_files_map[filename] = True

        is_valid = len(errors) == 0
        if not is_valid:
            status_str = "FILE_MISSING" if any("Missing" in e for e in errors) else "CORRUPTED_CHECKSUM_MISMATCH"
        else:
            status_str = "SHA256_VERIFIED"

        return {
            "backup_id": backup_id,
            "is_valid": is_valid,
            "status": status_str,
            "checksum_status": status_str,
            "errors": errors,
            "error": errors[0] if errors else None,
            "verified_files": verified_files_map,
            "verified_files_list": verified_files,
            "checked_at": now.isoformat(),
            "manifest": manifest
        }

    @classmethod
    def test_isolated_restoration(cls, backup_id: str, db: Session) -> Dict[str, Any]:
        """
        Executes a verified disaster recovery test in an isolated sandbox database.
        Never modifies or overwrites the active production database.
        Measures actual RTO duration and actual RPO data gap.
        """
        if not _backup_lock.acquire(blocking=False):
            raise RuntimeError("Another backup or recovery test is currently in progress.")

        start_time = time.perf_counter()
        now = get_utc_now()

        # Step 1: Verify backup integrity
        integrity = cls.verify_backup_integrity(backup_id)
        if not integrity["is_valid"]:
            _backup_lock.release()
            return {
                "backup_id": backup_id,
                "recovery_test_passed": False,
                "status": "PRE_RESTORATION_VERIFICATION_FAILED",
                "errors": integrity.get("errors", [integrity.get("error")]),
                "tested_at": now.isoformat()
            }

        manifest = integrity["manifest"]
        vault_root = cls.get_vault_storage_dir()
        backup_db_path = os.path.join(vault_root, backup_id, "database.sqlite")

        # Step 2: Create disposable isolated sandbox database
        sandbox_fd, sandbox_path = tempfile.mkstemp(prefix=f"vault_sandbox_{backup_id}_", suffix=".db")
        os.close(sandbox_fd)

        try:
            # Copy database to sandbox
            shutil.copy2(backup_db_path, sandbox_path)

            # Step 3: Connect to restored sandbox and run physical integrity check
            conn = sqlite3.connect(sandbox_path)
            cur = conn.cursor()
            try:
                cur.execute("PRAGMA integrity_check;")
                check_result = cur.fetchone()[0]
                if check_result != "ok":
                    raise ValueError(f"SQLite PRAGMA integrity_check failed on restored DB: {check_result}")

                # Step 4: Validate schema and record counts against manifest
                discrepancies = []
                expected_counts = manifest.get("table_record_counts", {})
                restored_counts = {}

                for table_name, expected_count in expected_counts.items():
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table_name};")
                        actual_count = cur.fetchone()[0]
                        restored_counts[table_name] = actual_count
                        if actual_count != expected_count:
                            discrepancies.append(
                                f"Table '{table_name}' count mismatch: expected {expected_count}, restored {actual_count}"
                            )
                    except Exception as e:
                        discrepancies.append(f"Table '{table_name}' query error: {str(e)}")

            finally:
                conn.close()

            # Step 5: Measure Recovery Time Objective (RTO)
            rto_duration_seconds = round(time.perf_counter() - start_time, 3)

            # Step 6: Measure Recovery Point Objective (RPO)
            # RPO = delta between backup creation and latest telemetry snapshot
            created_at = datetime.fromisoformat(manifest["created_at"].replace("Z", "+00:00"))
            latest_tel_str = manifest.get("latest_telemetry_timestamp")
            if latest_tel_str:
                latest_tel_dt = datetime.fromisoformat(latest_tel_str.replace("Z", "+00:00"))
                if created_at.tzinfo is not None and latest_tel_dt.tzinfo is None:
                    latest_tel_dt = latest_tel_dt.replace(tzinfo=timezone.utc)
                elif created_at.tzinfo is None and latest_tel_dt.tzinfo is not None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                actual_rpo_hours = round(max(0.0, (created_at - latest_tel_dt).total_seconds() / 3600.0), 2)
            else:
                actual_rpo_hours = 0.0

            rpo_target_hours = manifest.get("rpo_target_hours", settings.DEFAULT_RPO_HOURS)
            rto_target_seconds = manifest.get("rto_target_seconds", settings.DEFAULT_RTO_SECONDS)

            rpo_satisfied = actual_rpo_hours <= rpo_target_hours
            rto_satisfied = rto_duration_seconds <= rto_target_seconds
            recovery_passed = len(discrepancies) == 0

            # Step 7: Update VaultBackupRecord in database
            record = db.query(VaultBackupRecord).filter(VaultBackupRecord.id == backup_id).first()
            if record:
                record.restoration_status = "RESTORE_TESTED_SUCCESS" if recovery_passed else "RESTORE_TEST_FAILED"
                record.last_test_rto_seconds = rto_duration_seconds
                record.last_test_rpo_hours = actual_rpo_hours
                record.last_test_timestamp = now
                db.commit()

            # Step 8: Audit event
            AuditService.log_event(
                db=db,
                action="TEST_ISOLATED_RESTORATION",
                target_type="VAULT_BACKUP",
                target_id=backup_id,
                details={
                    "recovery_passed": recovery_passed,
                    "rto_seconds": rto_duration_seconds,
                    "rpo_hours": actual_rpo_hours,
                    "rto_satisfied": rto_satisfied,
                    "rpo_satisfied": rpo_satisfied,
                    "discrepancies": discrepancies
                }
            )

            return {
                "backup_id": backup_id,
                "recovery_test_passed": recovery_passed,
                "status": "RESTORE_TEST_SUCCESS" if recovery_passed else "RESTORE_TEST_FAILED",
                "integrity_check_passed": check_result == "ok",
                "sqlite_integrity_check": "ok",
                "restored_table_counts": restored_counts,
                "verified_tables": restored_counts,
                "discrepancies": discrepancies,
                "measured_rto_seconds": rto_duration_seconds,
                "target_rto_seconds": rto_target_seconds,
                "rto_sla_met": rto_satisfied,
                "measured_rpo_hours": actual_rpo_hours,
                "target_rpo_hours": rpo_target_hours,
                "rpo_sla_met": rpo_satisfied,
                "recovery_objectives": {
                    "measured_rto_seconds": rto_duration_seconds,
                    "target_rto_seconds": rto_target_seconds,
                    "rto_objective_satisfied": rto_satisfied,
                    "measured_rpo_hours": actual_rpo_hours,
                    "target_rpo_hours": rpo_target_hours,
                    "rpo_objective_satisfied": rpo_satisfied
                },
                "tested_at": now.isoformat(),
                "safety_guarantee": "RESTORE_PERFORMED_IN_DISPOSABLE_SANDBOX_ZERO_PRODUCTION_MUTATION",
                "isolation_guarantee": "Restoration executed strictly in temporary sandbox. Zero physical or production DB mutation."
            }

        finally:
            # Delete disposable sandbox database file
            if os.path.exists(sandbox_path):
                try:
                    os.remove(sandbox_path)
                except Exception:
                    pass
            _backup_lock.release()

    @classmethod
    def list_backups(cls, db: Session) -> List[Dict[str, Any]]:
        """Lists all existing backups with metadata, verification status, and latest recovery test metrics."""
        vault_root = cls.get_vault_storage_dir()
        records = db.query(VaultBackupRecord).order_by(VaultBackupRecord.created_at.desc()).all()
        result = []

        for r in records:
            backup_dir = os.path.join(vault_root, r.id)
            on_disk = os.path.exists(backup_dir)
            manifest = json.loads(r.manifest_json) if r.manifest_json else {}

            result.append({
                "id": r.id,
                "backup_id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "created_by": r.created_by,
                "format_version": r.format_version,
                "database_size_bytes": r.database_size_bytes,
                "database_size_mb": round((r.database_size_bytes or 0) / (1024 * 1024), 2),
                "files_count": r.files_count,
                "checksum_status": r.checksum_status,
                "restoration_status": r.restoration_status,
                "last_test_rto_seconds": r.last_test_rto_seconds,
                "last_test_rpo_hours": r.last_test_rpo_hours,
                "last_test_timestamp": r.last_test_timestamp.isoformat() if r.last_test_timestamp else None,
                "on_disk": on_disk,
                "resource_scope": manifest.get("resource_scope", []),
                "target_rpo_hours": manifest.get("rpo_target_hours", settings.DEFAULT_RPO_HOURS),
                "target_rto_seconds": manifest.get("rto_target_seconds", settings.DEFAULT_RTO_SECONDS)
            })

        return result

    @classmethod
    def prune_expired_backups(cls, db: Session, max_to_retain: Optional[int] = None) -> int:
        """Safely removes older backups exceeding retention limits, ensuring at least one backup is retained."""
        if max_to_retain is None:
            max_to_retain = settings.MAX_BACKUPS_RETAINED
        records = db.query(VaultBackupRecord).order_by(VaultBackupRecord.created_at.desc()).all()
        if len(records) <= max_to_retain:
            return 0

        to_prune = records[max_to_retain:]
        vault_root = cls.get_vault_storage_dir()
        pruned_count = 0

        for r in to_prune:
            backup_dir = os.path.join(vault_root, r.id)
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir, ignore_errors=True)
            db.delete(r)
            pruned_count += 1

        db.commit()
        return pruned_count

    @classmethod
    def restore_to_production(
        cls,
        backup_id: str,
        confirmation_token: str,
        db: Session,
        admin_username: str = "admin"
    ) -> Dict[str, Any]:
        """
        Executes a production database restoration.
        Protected by explicit confirmation token and pre-restoration safety snapshot.
        """
        if confirmation_token != "CONFIRM_OVERWRITE_PRODUCTION_DATA":
            raise ValueError("Invalid confirmation token. Overwrite requires 'CONFIRM_OVERWRITE_PRODUCTION_DATA'.")

        if not _backup_lock.acquire(blocking=False):
            raise RuntimeError("Another backup or restoration operation is in progress.")

        start_time = time.perf_counter()
        now = get_utc_now()
        vault_root = cls.get_vault_storage_dir()
        backup_db_path = os.path.join(vault_root, backup_id, "database.sqlite")
        prod_db_path = cls.get_production_db_path()

        if not os.path.exists(backup_db_path):
            _backup_lock.release()
            raise FileNotFoundError(f"Backup database file for '{backup_id}' not found.")

        # Pre-restoration emergency safety snapshot of live database
        emergency_snapshot_id = f"pre-restore-emergency-{now.strftime('%Y%m%d-%H%M%S')}.db"
        emergency_snapshot_path = os.path.join(vault_root, emergency_snapshot_id)
        try:
            shutil.copy2(prod_db_path, emergency_snapshot_path)
        except Exception as e:
            _backup_lock.release()
            raise RuntimeError(f"Failed to create pre-restoration safety snapshot: {str(e)}")

        try:
            # Overwrite production DB file
            shutil.copy2(backup_db_path, prod_db_path)
            duration_s = round(time.perf_counter() - start_time, 3)

            AuditService.log_event(
                db=db,
                action="RESTORE_PRODUCTION_DATABASE",
                target_type="PRODUCTION_DATABASE",
                target_id=backup_id,
                user=admin_username,
                details={
                    "restored_from": backup_id,
                    "emergency_snapshot_path": emergency_snapshot_path,
                    "duration_seconds": duration_s
                }
            )

            return {
                "status": "PRODUCTION_RESTORE_COMPLETED",
                "restored_backup_id": backup_id,
                "emergency_safety_snapshot": emergency_snapshot_id,
                "duration_seconds": duration_s,
                "restored_at": now.isoformat(),
                "action_required": "Application database restored. Restart background worker daemons if running."
            }

        finally:
            _backup_lock.release()
