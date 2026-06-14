"""Pure helpers for aligning WhatsApp booking session ``ctx`` with ``flow_data`` (no I/O)."""
from __future__ import annotations

from typing import Any, Dict

# Workflow steps often write picks only under ``flow_data``; legacy FSM reads top-level ``ctx``.
BOOKING_KEYS_SYNC_FROM_FLOW = (
    "date",
    "professional",
    "service",
    "selected_slot",
    "available_slots",
    "professionals",
    "customer_name",
    "customer_phone",
)

BOOKING_HANDOFF_CLEAR_KEYS = (
    "date",
    "selected_slot",
    "available_slots",
    "available_services",
    "professionals",
    "time",
    "appointment_time",
    "appointment_date",
)

# Keys owned by WorkflowEngine — must be cleared before legacy FSM handoff.
WORKFLOW_SESSION_KEYS = (
    "workflow_id",
    "step_idx",
    "waiting_for_input",
    "flow_ended",
    "_wa_skip_input_wait_once",
)


def sync_booking_ctx_from_flow_data(ctx: Dict[str, Any]) -> None:
    """Copy booking fields from ``ctx.flow_data`` onto top-level ``ctx`` when missing."""
    if not isinstance(ctx, dict):
        return
    fd = ctx.get("flow_data")
    if not isinstance(fd, dict):
        return
    for k in BOOKING_KEYS_SYNC_FROM_FLOW:
        if ctx.get(k) in (None, "") and fd.get(k) not in (None, ""):
            ctx[k] = fd[k]


def exit_workflow_for_fsm_handoff(session: Dict[str, Any]) -> None:
    """Drop workflow cursor so legacy FSM (``ctx.mode``) owns the next turns."""
    ctx = session.get("ctx")
    if not isinstance(ctx, dict):
        return
    for k in WORKFLOW_SESSION_KEYS:
        ctx.pop(k, None)


def new_workflow_session(workflow_id: str) -> Dict[str, Any]:
    """Fresh ctx for starting a saved tenant workflow (no stale FSM ``mode``)."""
    return {
        "workflow_id": (workflow_id or "").strip().lower(),
        "step_idx": 0,
        "waiting_for_input": False,
        "flow_data": {},
    }


def clear_stale_booking_calendar_keys(ctx: Dict[str, Any]) -> None:
    """Remove prior date/slot state from ``ctx`` and nested ``flow_data`` (e.g. before reschedule handoff)."""
    for k in BOOKING_HANDOFF_CLEAR_KEYS:
        ctx.pop(k, None)
    fd = ctx.get("flow_data")
    if isinstance(fd, dict):
        for k in BOOKING_HANDOFF_CLEAR_KEYS:
            fd.pop(k, None)
