"""
AEGISSTOR PHOENIX — Persistent 14-State Incident Lifecycle Machine
Enforces strict state transitions, invariant validation, and auditability.
"""
from typing import Dict, List, Set, Tuple
from enum import Enum


class PhoenixIncidentState(str, Enum):
    DETECTED = "DETECTED"
    EVIDENCE_COLLECTION = "EVIDENCE_COLLECTION"
    TRIAGE = "TRIAGE"
    INVESTIGATION = "INVESTIGATION"
    PLAN_GENERATION = "PLAN_GENERATION"
    SIMULATION = "SIMULATION"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    VERIFYING_RECOVERY = "VERIFYING_RECOVERY"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


# Strict Directed Transition Graph
VALID_TRANSITIONS: Dict[PhoenixIncidentState, Set[PhoenixIncidentState]] = {
    PhoenixIncidentState.DETECTED: {
        PhoenixIncidentState.EVIDENCE_COLLECTION,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.EVIDENCE_COLLECTION: {
        PhoenixIncidentState.TRIAGE,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.TRIAGE: {
        PhoenixIncidentState.INVESTIGATION,
        PhoenixIncidentState.ESCALATED,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.INVESTIGATION: {
        PhoenixIncidentState.PLAN_GENERATION,
        PhoenixIncidentState.ESCALATED,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.PLAN_GENERATION: {
        PhoenixIncidentState.SIMULATION,
        PhoenixIncidentState.ESCALATED,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.SIMULATION: {
        PhoenixIncidentState.AWAITING_APPROVAL,
        PhoenixIncidentState.INVESTIGATION,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.AWAITING_APPROVAL: {
        PhoenixIncidentState.APPROVED,
        PhoenixIncidentState.INVESTIGATION,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.APPROVED: {
        PhoenixIncidentState.EXECUTING,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.EXECUTING: {
        PhoenixIncidentState.VERIFYING_RECOVERY,
        PhoenixIncidentState.FAILED
    },
    PhoenixIncidentState.VERIFYING_RECOVERY: {
        PhoenixIncidentState.RESOLVED,
        PhoenixIncidentState.FAILED,
        PhoenixIncidentState.ESCALATED
    },
    PhoenixIncidentState.FAILED: {
        PhoenixIncidentState.INVESTIGATION,
        PhoenixIncidentState.ESCALATED,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.ESCALATED: {
        PhoenixIncidentState.INVESTIGATION,
        PhoenixIncidentState.AWAITING_APPROVAL,
        PhoenixIncidentState.CANCELLED
    },
    PhoenixIncidentState.RESOLVED: {
        # Allow reopen only under new investigation
        PhoenixIncidentState.INVESTIGATION
    },
    PhoenixIncidentState.CANCELLED: set()  # Terminal state
}


class InvalidStateTransitionError(Exception):
    def __init__(self, current_state: str, requested_state: str, reason: str = ""):
        self.current_state = current_state
        self.requested_state = requested_state
        self.reason = reason or f"Transition from {current_state} to {requested_state} is prohibited by Phoenix lifecycle rules."
        super().__init__(self.reason)


class IncidentLifecycleManager:
    """
    Validates and controls state transitions across the 14 Phoenix incident phases.
    """

    @classmethod
    def can_transition(cls, current_state: str, new_state: str) -> bool:
        try:
            curr = PhoenixIncidentState(current_state)
            target = PhoenixIncidentState(new_state)
            return target in VALID_TRANSITIONS.get(curr, set())
        except (ValueError, KeyError):
            return False

    @classmethod
    def validate_transition(cls, current_state: str, new_state: str) -> Tuple[bool, str]:
        if not cls.can_transition(current_state, new_state):
            valid_targets = [s.value for s in VALID_TRANSITIONS.get(PhoenixIncidentState(current_state), set())]
            return False, f"Cannot transition from {current_state} to {new_state}. Valid next states: {valid_targets}"
        return True, f"Transition from {current_state} to {new_state} is valid."

    @classmethod
    def get_allowed_next_states(cls, current_state: str) -> List[str]:
        try:
            curr = PhoenixIncidentState(current_state)
            return sorted([s.value for s in VALID_TRANSITIONS.get(curr, set())])
        except (ValueError, KeyError):
            return []
