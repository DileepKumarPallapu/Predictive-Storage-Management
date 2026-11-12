"""Idempotent Control Plane reference-data bootstrap.

Only action definitions are registered here. No users, connectors, resources,
telemetry, or infrastructure capabilities are created.
"""
from sqlalchemy.orm import Session
from app.models.control_plane import ActionDefinition
from app.utils.datetime_utils import utc_now


ACTION_DEFINITIONS = [
    {
        "action_type": "resource.inspect",
        "title": "Inspect registered resource",
        "description": "Read AEGISSTOR's persisted inventory record and latest telemetry. No physical provider connection or mutation is performed.",
        "category": "READ_ONLY",
        "risk_level": "READ_ONLY",
        "input_schema_json": {"target_id": "string"},
        "required_capability": None,
        "requires_approval": False,
        "is_enabled": True,
        "is_executable": True,
    },
    {
        "action_type": "storage.capacity.plan",
        "title": "Prepare capacity expansion plan",
        "description": "Calculate a capacity plan from fresh, non-synthetic telemetry. Approval accepts the plan only; no volume is provisioned or resized.",
        "category": "PLANNING",
        "risk_level": "HIGH",
        "input_schema_json": {"additional_capacity_bytes": "positive integer"},
        "required_capability": None,
        "requires_approval": True,
        "is_enabled": True,
        "is_executable": False,
    },
    {
        "action_type": "storage.volume.resize",
        "title": "Resize storage volume",
        "description": "Reserved action definition. Disabled until a provider-specific adapter, capability checks and safety tests are implemented.",
        "category": "MUTATION",
        "risk_level": "CRITICAL",
        "input_schema_json": {"new_capacity_bytes": "positive integer"},
        "required_capability": "volume.resize",
        "requires_approval": True,
        "is_enabled": False,
        "is_executable": False,
    },
]


def ensure_control_plane_action_definitions(db: Session) -> int:
    inserted = 0
    for values in ACTION_DEFINITIONS:
        exists = db.query(ActionDefinition).filter(
            ActionDefinition.action_type == values["action_type"]
        ).first()
        if exists is None:
            db.add(ActionDefinition(**values, created_at=utc_now()))
            inserted += 1
    if inserted:
        db.commit()
    return inserted
