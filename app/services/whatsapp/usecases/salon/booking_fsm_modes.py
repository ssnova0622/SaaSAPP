"""
Session ``ctx["mode"]`` values for the salon booking area.

``BOOKING_FSM_MODES_KEEP_CTX``: modes where :func:`start_timeslot_flow` must *not* reset context
to ``select_service`` (see :mod:`booking_timeslot_start`).
"""

from __future__ import annotations

# Modes that must not trigger the "reset to select_service" branch in ``start_timeslot_flow``.
BOOKING_FSM_MODES_KEEP_CTX: frozenset[str] = frozenset(
    {
        "select_service",
        "select_date",
        "select_prof",
        "select_prof_new",
        "select_slot",
        "confirm_booking",
        "returning_choice",
        "ask_name",
        "wait_reminder",
        "cancel_selection",
        "confirm_cancel",
        "reschedule_selection",
        "confirm_reschedule",
    }
)
