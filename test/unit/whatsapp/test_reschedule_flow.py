"""Reschedule workflow / FSM regression tests."""
from __future__ import annotations

from app.services.whatsapp.usecases.salon.reschedule_flow import (
    _appt_display_date,
    _appt_iso_date,
    _normalize_professional_for_handoff,
)
from app.services.whatsapp.helpers import constants as WMSG
from app.services.whatsapp.usecases.utils import choice_to_index, parse_yes_no


def test_appt_iso_date_prefers_iso_field():
    appt = {"date": "27-06-2026", "date_iso": "2026-06-27"}
    assert _appt_iso_date(appt) == "2026-06-27"
    assert _appt_display_date(appt) == "27-06-2026"


def test_normalize_professional_empty_to_sentinel():
    assert _normalize_professional_for_handoff("") == WMSG.PROF_SENTINEL_NO_PROF
    assert _normalize_professional_for_handoff(None) == WMSG.PROF_SENTINEL_NO_PROF
    assert _normalize_professional_for_handoff("Mike") == "Mike"


def test_confirm_parsing_number_and_yes():
    def confirm_yes(raw: str) -> bool:
        idx = choice_to_index(str(raw).strip())
        if idx == 1:
            return True
        return parse_yes_no(str(raw).strip()) is True

    assert confirm_yes("1") is True
    assert confirm_yes("yes") is True
    assert confirm_yes("2") is False
