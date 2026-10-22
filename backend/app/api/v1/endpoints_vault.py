from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.entities import User
from app.auth.security import get_current_user, require_role
from app.services.vault_backup_engine import VaultBackupEngine

router = APIRouter(prefix="/vault", tags=["AEGISSTOR VAULT — Backup & Disaster Recovery"])


class CreateBackupRequest(BaseModel):
    notes: Optional[str] = Field(default="", description="Operator notes or reason for backup")


class RestoreProductionRequest(BaseModel):
    confirmation_token: str = Field(..., description="Must be 'CONFIRM_OVERWRITE_PRODUCTION_DATA'")


@router.post("/backups")
def create_vault_backup(
    payload: CreateBackupRequest = CreateBackupRequest(),
    current_user: User = Depends(require_role(["ADMIN", "OPERATOR"])),
    db: Session = Depends(get_db)
):
    """
    Creates an atomic, transaction-consistent live snapshot of the database, safe configurations,
    model metadata, and audit ledger. Computes cryptographic SHA-256 checksums.
    """
    try:
        manifest = VaultBackupEngine.create_backup(
            db=db,
            created_by=current_user.username,
            notes=payload.notes or ""
        )
        return {
            "status": "BACKUP_CREATED_SUCCESS",
            "backup": manifest
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups")
def list_vault_backups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all available backup archives, their integrity state, and last tested recovery metrics."""
    backups = VaultBackupEngine.list_backups(db)
    return {
        "status": "ok",
        "backups_count": len(backups),
        "backups": backups
    }


@router.get("/backups/{backup_id}/integrity")
def verify_backup_integrity(
    backup_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Verifies SHA-256 checksums of database, configuration, and model metadata files
    against the immutable backup manifest to detect corruption or missing resources.
    """
    result = VaultBackupEngine.verify_backup_integrity(backup_id)
    return result


@router.post("/backups/{backup_id}/test-restore")
def test_isolated_restoration(
    backup_id: str,
    current_user: User = Depends(require_role(["ADMIN", "OPERATOR", "AUDITOR"])),
    db: Session = Depends(get_db)
):
    """
    Executes a verified disaster recovery test in a disposable isolated sandbox database.
    Validates SQLite integrity, verifies table record counts, and measures actual RTO/RPO metrics.
    Guaranteed zero mutation to the active production database.
    """
    try:
        result = VaultBackupEngine.test_isolated_restoration(backup_id, db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/{backup_id}/restore-production")
def restore_production_database(
    backup_id: str,
    payload: RestoreProductionRequest,
    current_user: User = Depends(require_role(["ADMIN"])),
    db: Session = Depends(get_db)
):
    """
    Executes an authorized production database restore from a verified backup bundle.
    Requires explicit confirmation token and takes an automatic emergency safety snapshot.
    """
    try:
        result = VaultBackupEngine.restore_to_production(
            backup_id=backup_id,
            confirmation_token=payload.confirmation_token,
            db=db,
            admin_username=current_user.username
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
