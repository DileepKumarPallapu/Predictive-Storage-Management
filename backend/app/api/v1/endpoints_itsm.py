import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.auth.tenant import assert_org_resource, resolve_organization_id
from app.database import get_db
from app.models.entities import User
from app.models.enterprise_entities import (
    EnterpriseIncident,
    ExternalTicketMapping,
    ITSMIntegration,
)
from app.realtime.event_bus import OutboxService
from app.utils.datetime_utils import utc_now

router = APIRouter()


class ITSMIntegrationCreateRequest(BaseModel):
    provider: str  # SERVICENOW, JIRA_SM, WEBHOOK
    name: str = Field(..., min_length=2, max_length=128)
    endpoint_url: str = ""
    auth_type: str = "BEARER"
    secret_value: str = ""
    field_mapping_json: str = "{}"
    priority_mapping_json: str = "{}"


class SyncTicketRequest(BaseModel):
    integration_id: str
    dry_run: bool = False


def _serialize_integration(i: ITSMIntegration) -> dict:
    return {
        "id": i.id,
        "organization_id": i.organization_id,
        "provider": i.provider,
        "name": i.name,
        "endpoint_url": i.endpoint_url,
        "auth_type": i.auth_type,
        "has_secret": bool(i.secret_encrypted_or_ref),
        "status": i.status,
        "last_tested_at": i.last_tested_at.isoformat() if i.last_tested_at else None,
        "last_error": i.last_error,
    }


@router.get("/itsm/integrations")
def list_itsm_integrations(
    current_user: User = Depends(require_permission("incidents.read")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    rows = db.query(ITSMIntegration).filter(ITSMIntegration.organization_id == org_id).all()
    mappings = db.query(ExternalTicketMapping).filter(ExternalTicketMapping.organization_id == org_id).all()
    return {
        "organization_id": org_id,
        "integrations": [_serialize_integration(i) for i in rows],
        "ticket_mappings": [
            {
                "id": m.id, "integration_id": m.integration_id, "incident_id": m.incident_id,
                "external_ticket_id": m.external_ticket_id, "external_status": m.external_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in mappings
        ],
    }


@router.post("/itsm/integrations", status_code=status.HTTP_201_CREATED)
def create_itsm_integration(
    payload: ITSMIntegrationCreateRequest,
    current_user: User = Depends(require_permission("itsm.configure")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    provider = payload.provider.upper()
    if provider not in ("SERVICENOW", "JIRA_SM", "WEBHOOK"):
        raise HTTPException(status_code=422, detail="Provider must be SERVICENOW, JIRA_SM, or WEBHOOK.")

    has_url = bool(payload.endpoint_url.strip())
    has_secret = bool(payload.secret_value.strip())
    initial_status = "CONFIGURED" if (has_url and has_secret) else "NOT_CONFIGURED"

    integ = ITSMIntegration(
        id=f"itsm-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        provider=provider,
        name=payload.name.strip(),
        endpoint_url=payload.endpoint_url.strip(),
        auth_type=payload.auth_type.upper(),
        secret_encrypted_or_ref="***REDACTED***" if has_secret else "",
        status=initial_status,
        field_mapping_json=payload.field_mapping_json,
        priority_mapping_json=payload.priority_mapping_json,
    )
    db.add(integ)
    OutboxService.emit_and_commit(
        db=db, event_type="itsm.updated", resource_type="ITSMIntegration", resource_id=integ.id,
        actor_user=current_user, organization_id=org_id,
        payload={"id": integ.id, "provider": integ.provider, "status": integ.status},
        required_permission="incidents.read",
    )
    return _serialize_integration(integ)


@router.post("/itsm/integrations/{integ_id}/validate")
def validate_itsm_integration(
    integ_id: str,
    current_user: User = Depends(require_permission("itsm.configure")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    integ = assert_org_resource(db.query(ITSMIntegration).filter(ITSMIntegration.id == integ_id).first(), org_id, "ITSMIntegration")
    integ.last_tested_at = utc_now()
    if not integ.endpoint_url or not integ.secret_encrypted_or_ref:
        integ.status = "NOT_CONFIGURED"
        integ.last_error = "BLOCKED_BY_EXTERNAL_CONFIGURATION: Missing endpoint URL or authentication secret."
        db.commit()
        return {
            "id": integ.id,
            "status": integ.status,
            "validated": False,
            "reason": integ.last_error,
        }
    if not (integ.endpoint_url.startswith("https://") or integ.endpoint_url.startswith("http://")):
        integ.status = "ERROR"
        integ.last_error = "Invalid endpoint URL scheme; expected http:// or https://."
        db.commit()
        return {"id": integ.id, "status": integ.status, "validated": False, "reason": integ.last_error}

    # In offline/test environments without live external ServiceNow/Jira instances,
    # never fabricate CONNECTED unless an external ping succeeds; report CONFIGURED/BLOCKED honestly.
    integ.status = "CONFIGURED"
    integ.last_error = "Endpoint syntax & credentials present; live external handshake requires reachable ITSM instance."
    db.commit()
    return {
        "id": integ.id,
        "status": integ.status,
        "validated": True,
        "note": integ.last_error,
    }


@router.post("/itsm/incidents/{inc_id}/sync-ticket")
def sync_incident_to_itsm(
    inc_id: str,
    payload: SyncTicketRequest,
    current_user: User = Depends(require_permission("incidents.write")),
    org_id: str = Depends(resolve_organization_id),
    db: Session = Depends(get_db),
):
    inc = assert_org_resource(db.query(EnterpriseIncident).filter(EnterpriseIncident.id == inc_id).first(), org_id, "EnterpriseIncident")
    integ = assert_org_resource(db.query(ITSMIntegration).filter(ITSMIntegration.id == payload.integration_id).first(), org_id, "ITSMIntegration")

    idem_key = f"{org_id}:{integ.id}:{inc.id}"
    existing = db.query(ExternalTicketMapping).filter(ExternalTicketMapping.idempotency_key == idem_key).first()
    if existing:
        return {
            "idempotent_replay": True,
            "mapping_id": existing.id,
            "external_ticket_id": existing.external_ticket_id,
            "external_status": existing.external_status,
        }

    if integ.status == "NOT_CONFIGURED":
        raise HTTPException(
            status_code=400,
            detail=f"BLOCKED_BY_EXTERNAL_CONFIGURATION: Integration '{integ.name}' is NOT_CONFIGURED.",
        )

    if not payload.dry_run:
        # Without live external credentials/network, refuse to fabricate an external ServiceNow/Jira ticket ID
        raise HTTPException(
            status_code=503,
            detail=f"BLOCKED_BY_EXTERNAL_CONFIGURATION: External {integ.provider} instance at '{integ.endpoint_url}' is not reachable in this environment. Use dry_run=true to preview mapped payload.",
        )

    mapping = ExternalTicketMapping(
        id=f"tmap-{uuid.uuid4().hex[:10]}",
        organization_id=org_id,
        integration_id=integ.id,
        incident_id=inc.id,
        external_ticket_id=f"DRYRUN-{inc.severity}-{inc.id[-6:].upper()}",
        external_status="DRY_RUN_VALIDATED",
        idempotency_key=idem_key,
        response_json=json.dumps({"mode": "DRY_RUN", "provider": integ.provider, "title": inc.title, "severity": inc.severity}),
    )
    db.add(mapping)
    OutboxService.emit_and_commit(
        db=db, event_type="itsm.ticket_mapped", resource_type="ExternalTicketMapping", resource_id=mapping.id,
        actor_user=current_user, organization_id=org_id,
        payload={"incident_id": inc.id, "external_ticket_id": mapping.external_ticket_id},
        required_permission="incidents.read",
    )
    return {
        "idempotent_replay": False,
        "mapping_id": mapping.id,
        "external_ticket_id": mapping.external_ticket_id,
        "external_status": mapping.external_status,
    }
