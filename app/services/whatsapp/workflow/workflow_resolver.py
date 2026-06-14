"""
Resolve default workflows for legacy menu / NL action aliases.
"""
from __future__ import annotations

from typing import Optional, Sequence, Set

from app.helpers.constants_action import END
from app.models.workflows import WorkflowDefinition
from app.services.whatsapp.workflow.workflow_service import list_workflows
from app.services.whatsapp.workflow.workflow_step_policy import normalize_workflow_action_code

# Conventional workflow ids seeded per industry (first match wins).
_DEFAULT_BOOKING_WORKFLOW_IDS: Sequence[str] = (
    "salon_booking_flow",
    "demo_booking_flow",
    "clinic_booking_flow",
    "gym_booking_flow",
    "school_meeting_flow",
    "camp_booking_flow",
    "car_testdrive_flow",
    "store_browse_flow",
)

_BOOKING_STEP_CODES: Set[str] = {
    "show_services",
    "show_professionals",
    "list_doctors",
    "select_date",
    "select_time",
    "confirm_booking",
    "confirm_prompt",
}


def _active_workflows(tenant: str) -> list[WorkflowDefinition]:
    return [w for w in (list_workflows(tenant) or []) if getattr(w, "active", True)]


def _workflow_has_booking_step(wf: WorkflowDefinition) -> bool:
    for step in wf.steps or []:
        code = normalize_workflow_action_code(getattr(step, "action_code", None) or "")
        if code in _BOOKING_STEP_CODES:
            return True
    return False


def resolve_default_booking_workflow(tenant: str) -> Optional[str]:
    """
    Pick the best active booking workflow for legacy ``book_appointment`` / NL intents.

    Priority: conventional id → any workflow with booking steps → first active workflow.
    """
    active = _active_workflows(tenant)
    if not active:
        return None

    by_id = {w.workflow_id.lower(): w.workflow_id for w in active}
    for candidate in _DEFAULT_BOOKING_WORKFLOW_IDS:
        wf_id = by_id.get(candidate.lower())
        if wf_id:
            return wf_id

    for wf in active:
        if _workflow_has_booking_step(wf):
            return wf.workflow_id

    # Last resort: first active workflow that ends with END (valid saved flow).
    for wf in active:
        steps = wf.steps or []
        if steps and normalize_workflow_action_code(steps[-1].action_code) == END:
            return wf.workflow_id

    return active[0].workflow_id if active else None
