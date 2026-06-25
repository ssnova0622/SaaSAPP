"""
Workflow input routing policies.

- ``WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT``: legacy frozenset – user text is stored as
  ``{action}_user_input_pending``, then only ``execute_run`` runs (no legacy chain).
- ``action_needs_user_input(code)`` – preferred query: checks both the frozenset and the
  central :mod:`~app.services.whatsapp.action_handler_registry` so newly registered
  actions do **not** require updating the frozenset.
- ``normalize_workflow_action_code`` / ``workflow_user_reply_*_key``: stable keys in
  ``session["ctx"]["flow_data"]``.

Adding a new action that needs user input
-----------------------------------------
Register it with ``needs_user_input=True`` in the registry – no edits here needed::

    from app.services.whatsapp.action_handler_registry import register
    register("my_collect_info", my_handler, needs_user_input=True)
"""
from __future__ import annotations

from app.helpers.constants_action import (
    AI_FREE_TEXT,
    ASK_NAME,
    ASK_NUM_SLOTS,
    AUTO_ASSIGN_TIME,
    BOOKING_SUMMARY,
    BROWSE_CATALOG,
    CANCEL_APPOINTMENT,
    CHECK_DOCTOR,
    CHECK_PRICE,
    CHECK_PRODUCT,
    COLLECT_DETAILS,
    COLLECT_PATIENT_INFO_ALIAS,
    CONFIRM_BOOKING,
    CONFIRM_PROMPT,
    LIST_DOCTORS,
    PRESET_PROFESSIONAL,
    SELECT_DATE,
    SELECT_TIME,
    SHOW_PROFESSIONALS,
    SHOW_SERVICES,
    SHOW_SERVICE_PRICES,
    RESCHEDULE_APPOINTMENT,
    SUBMIT_FEEDBACK,
    TRACK_ORDER,
    VIEW_PRODUCTS,
)

# Legacy: process_input + same step runs again (no members after store/clinic migrated to run-only).
WORKFLOW_STAY_ON_STEP_AFTER_INPUT = frozenset()

# Core + salon: pending reply in flow_data["{action}_user_input_pending"], then execute_run;
# committed answer in flow_data["{action}_user_input"].
WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT = frozenset(
    {
        ASK_NAME,
        ASK_NUM_SLOTS,
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

# Browse/display steps that may append trailing END text in the same turn (no dummy reply).
# Booking commit steps (date/time/confirm/name) must always wait for user input.
WORKFLOW_MERGE_END_WITH_PROMPT_WITHOUT_WAIT = frozenset(
    {
        SHOW_SERVICES,
        SHOW_SERVICE_PRICES,
        SHOW_PROFESSIONALS,
        LIST_DOCTORS,
        CHECK_DOCTOR,
        # PRESET_PROFESSIONAL and AUTO_ASSIGN_TIME are fully silent — no user
        # interaction — so the engine must continue immediately to the next step.
        PRESET_PROFESSIONAL,
        AUTO_ASSIGN_TIME,
        # NOTE: CHECK_PRODUCT, CHECK_PRICE, TRACK_ORDER are intentionally excluded —
        # they collect user input via the pending-reply mechanism and must NOT merge
        # the trailing END step in the same turn (that would close the workflow before
        # the user sends their query/order-id).
        BOOKING_SUMMARY,
        BROWSE_CATALOG,
        VIEW_PRODUCTS,
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


def action_needs_user_input(action_code: str) -> bool:
    """Return True if this step expects a user reply stored via flow_data before re-running.

    Checks the legacy ``WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT`` frozenset **and** the
    central action handler registry so newly registered actions with
    ``needs_user_input=True`` are automatically picked up without editing the frozenset.
    """
    norm = normalize_workflow_action_code(action_code)
    if norm in WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT:
        return True
    try:
        from app.services.whatsapp.action_handler_registry import action_needs_user_input as _reg_check
        return _reg_check(action_code)
    except Exception:
        return False


def can_merge_trailing_end_without_wait(action_code: str) -> bool:
    """True when this step may show its prompt and merge trailing END steps in one turn."""
    return normalize_workflow_action_code(action_code) in WORKFLOW_MERGE_END_WITH_PROMPT_WITHOUT_WAIT
