"""
Ensure ``BOOKING_FSM_MODES_KEEP_CTX`` stays aligned with real ``ctx["mode"]`` values.

If a new mode is added to handlers or cancel/reschedule flows but omitted from the keep-set,
``start_timeslot_flow`` may incorrectly reset the user to service selection.
"""
from __future__ import annotations

from app.services.whatsapp.usecases.salon.booking_fsm_modes import BOOKING_FSM_MODES_KEEP_CTX

# Modes branched on in ``dispatch_booking_fsm_mode`` / ``handle_fsm_back``.
_FSM_BOOKING_MODES = frozenset(
    {
        "select_service",
        "select_date",
        "select_prof_new",
        "select_prof",
        "select_slot",
        "confirm_booking",
        "returning_choice",
        "ask_name",
        "wait_reminder",
    }
)

# Session modes from ``cancel_flow`` / ``reschedule_flow`` while still in booking session.
_CANCEL_RESCHEDULE_MODES = frozenset(
    {
        "cancel_selection",
        "confirm_cancel",
        "reschedule_selection",
        "confirm_reschedule",
    }
)


def test_keep_ctx_covers_booking_fsm_handler_modes() -> None:
    assert _FSM_BOOKING_MODES <= BOOKING_FSM_MODES_KEEP_CTX


def test_keep_ctx_covers_cancel_reschedule_modes() -> None:
    assert _CANCEL_RESCHEDULE_MODES <= BOOKING_FSM_MODES_KEEP_CTX
