"""
Workflow input routing policies.

- ``WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT``: user text is stored as ``{action}_user_input_pending``,
  then only ``execute_run`` runs (no legacy ``process_input`` chain).
- ``normalize_workflow_action_code`` / ``workflow_user_reply_*_key``: stable keys in ``session["ctx"]["flow_data"]``.

See ``ADDING_WORKFLOW_ACTIONS.md`` in the whatsapp package to register new codes.
"""
from __future__ import annotations

from app.helpers.constants_action import (
    AI_FREE_TEXT,
    ASK_NAME,
    BOOKING_SUMMARY,
    CANCEL_APPOINTMENT,
    CHECK_DOCTOR,
    CHECK_PRICE,
    CHECK_PRODUCT,
    COLLECT_DETAILS,
    COLLECT_PATIENT_INFO_ALIAS,
    CONFIRM_BOOKING,
    CONFIRM_PROMPT,
    LIST_DOCTORS,
    SELECT_DATE,
    SELECT_TIME,
    SHOW_PROFESSIONALS,
    SHOW_SERVICES,
    RESCHEDULE_APPOINTMENT,
    SUBMIT_FEEDBACK,
    TRACK_ORDER,
)

# Legacy: process_input + same step runs again (no members after store/clinic migrated to run-only).
WORKFLOW_STAY_ON_STEP_AFTER_INPUT = frozenset()

# Core + salon: pending reply in flow_data["{action}_user_input_pending"], then execute_run;
# committed answer in flow_data["{action}_user_input"].
WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT = frozenset(
    {
        ASK_NAME,
        AI_FREE_TEXT,
        COLLECT_PATIENT_INFO_ALIAS,
        COLLECT_DETAILS,
        BOOKING_SUMMARY,
        SUBMIT_FEEDBACK,
        SHOW_SERVICES,
        SHOW_PROFESSIONALS,
        LIST_DOCTORS,
        CHECK_DOCTOR,
        SELECT_DATE,
        SELECT_TIME,
        CONFIRM_PROMPT,
        CONFIRM_BOOKING,
        CHECK_PRODUCT,
        CHECK_PRICE,
        TRACK_ORDER,
        CANCEL_APPOINTMENT,
        RESCHEDULE_APPOINTMENT,
    }
)


def normalize_workflow_action_code(action_code: str) -> str:
    c = (action_code or "").strip().lower()
    changed = True
    while changed:
        changed = False
        for prefix in ("store.", "core.", "salon.", "clinic.", "ai."):
            if c.startswith(prefix):
                c = c[len(prefix):]
                changed = True
                break
    return c


def workflow_user_reply_pending_key(action_code: str) -> str:
    """Inbound message for this step (written by WorkflowEngine, consumed by run handlers)."""
    return f"{normalize_workflow_action_code(action_code)}_user_input_pending"


def workflow_user_reply_flow_key(action_code: str) -> str:
    """Persisted user text / selection for this action, e.g. show_services → show_services_user_input."""
    return f"{normalize_workflow_action_code(action_code)}_user_input"
