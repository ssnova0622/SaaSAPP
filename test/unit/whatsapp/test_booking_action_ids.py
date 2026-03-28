"""
Guardrail: ``BOOKING_ACTION_IDS`` (NL / menu booking handoff) stays aligned with
``app.helpers.constants_action`` base ids (after stripping ``salon.`` / ``clinic.``).
"""
from __future__ import annotations

import app.helpers.constants_action as ca
from app.services.whatsapp.pipeline.inbound_pipeline import (
    BOOKING_ACTION_IDS,
    normalize_booking_nl_action_id,
)


def test_normalize_booking_nl_action_id_strips_modules() -> None:
    assert normalize_booking_nl_action_id("salon.show_services") == "show_services"
    assert normalize_booking_nl_action_id("clinic.book_doctor") == "book_doctor"
    assert normalize_booking_nl_action_id("book_appointment") == "book_appointment"


def test_booking_action_ids_map_to_constants_action_bases() -> None:
    expected = frozenset(
        {
            ca.SELECT_TIMESLOT.lower(),
            ca.BOOK_APPOINTMENT.lower(),
            ca.BOOK_DOCTOR.lower(),
            ca.CANCEL_APPOINTMENT.lower(),
            ca.RESCHEDULE_APPOINTMENT.lower(),
            ca.SHOW_SERVICES.lower(),
        }
    )
    normalized = {normalize_booking_nl_action_id(aid) for aid in BOOKING_ACTION_IDS}
    assert normalized == expected, (
        f"BOOKING_ACTION_IDS normalized set mismatch.\n"
        f" extra={normalized - expected}\n missing={expected - normalized}"
    )
