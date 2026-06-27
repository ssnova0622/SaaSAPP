"""Unit tests for user-facing booking labels (no internal sentinels)."""
from app.services.whatsapp.helpers import constants as WMSG
from app.services.whatsapp.usecases.salon.booking_display import (
    build_choose_new_date_prompt,
    build_reschedule_confirm_prompt,
    format_appt_list_party,
    format_booking_party_label,
    is_no_professional_name,
)


def test_is_no_professional_name_sentinels():
    assert is_no_professional_name(None)
    assert is_no_professional_name("")
    assert is_no_professional_name(WMSG.PROF_SENTINEL_NO_PROF)
    assert is_no_professional_name(WMSG.LABEL_AUTO_ASSIGNED)
    assert not is_no_professional_name("Sana Khan")


def test_format_booking_party_label():
    assert format_booking_party_label("Sana Khan", "Blow Dry") == "Sana Khan"
    assert format_booking_party_label(WMSG.PROF_SENTINEL_NO_PROF, "Badminton Court") == "Badminton Court"
    assert format_booking_party_label(WMSG.LABEL_NA, "Badminton Court") == "Badminton Court"
    assert format_booking_party_label(WMSG.PROF_SENTINEL_NO_PROF, None) == "your appointment"


def test_build_reschedule_confirm_no_professional():
    appt = {
        "professional": WMSG.PROF_SENTINEL_NO_PROF,
        "service": "Badminton Court",
        "time": "06:00",
    }
    msg = build_reschedule_confirm_prompt(appt, "28-06-2026")
    assert "__no_professional__" not in msg
    assert "N/A" not in msg
    assert "Badminton Court" in msg
    assert "06:00" in msg


def test_build_reschedule_confirm_with_stylist():
    appt = {"professional": "Sana Khan", "service": "Blow Dry", "time": "09:00"}
    msg = build_reschedule_confirm_prompt(appt, "28-06-2026")
    assert "Sana Khan" in msg
    assert "09:00" in msg


def test_build_choose_new_date_reschedule_no_professional():
    msg = build_choose_new_date_prompt(
        WMSG.PROF_SENTINEL_NO_PROF,
        "Badminton Court",
        is_reschedule=True,
    )
    assert "__no_professional__" not in msg
    assert "same professional" not in msg.lower()
    assert "Badminton Court" in msg


def test_build_choose_new_date_reschedule_with_stylist():
    msg = build_choose_new_date_prompt("Sana Khan", "Blow Dry", is_reschedule=True)
    assert "Sana Khan" in msg
    assert "same professional" in msg.lower()


def test_format_appt_list_party():
    assert format_appt_list_party({"professional": WMSG.LABEL_NA, "service": "Court A"}) == "Court A"
