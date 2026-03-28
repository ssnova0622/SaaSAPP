"""Unit tests for booking_flow pure helpers (time parsing, slot distance, display)."""
from __future__ import annotations

import pytest

from app.services.whatsapp.usecases.salon.booking_time_utils import (
    format_time_12h,
    parse_time_input,
    slots_near_time,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", None),
        ("morning", (9, 0)),
        ("evening", (18, 0)),
        ("14:30", (14, 30)),
        ("2:30 pm", (14, 30)),
        ("12:00 am", (0, 0)),
        ("12:00 pm", (12, 0)),
    ],
)
def test_parse_time_input(text: str, expected: tuple[int, int] | None) -> None:
    assert parse_time_input(text) == expected


def test_slots_near_time_orders_by_distance() -> None:
    slots = ["09:00", "10:30", "12:00"]
    out = slots_near_time(slots, target_hour=10, target_min=0, window_minutes=120, max_slots=8)
    assert out[0] == "10:30"
    assert "09:00" in out


@pytest.mark.parametrize(
    "hour,minute,expected",
    [
        (0, 0, "12:00 AM"),
        (12, 0, "12:00 PM"),
        (13, 5, "1:05 PM"),
        (9, 30, "9:30 AM"),
    ],
)
def test_format_time_12h(hour: int, minute: int, expected: str) -> None:
    assert format_time_12h(hour, minute) == expected
