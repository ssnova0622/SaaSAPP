"""Unit tests for WhatsApp use-case utilities (no I/O)."""
from __future__ import annotations

import pytest

from app.services.whatsapp.usecases.utils import choice_to_index, parse_yes_no


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", None),
        ("  ", None),
        ("1", 1),
        ("12", 12),
        ("1)", 1),
        ("2. Haircut", 2),
        ("10) Option text", 10),
    ],
)
def test_choice_to_index(text: str, expected: int | None) -> None:
    assert choice_to_index(text) == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", None),
        ("1", True),
        ("2", False),
        ("yes", True),
        ("YES", True),
        ("y", True),
        ("no", False),
        ("n", False),
        ("maybe", None),
        ("hello", None),
    ],
)
def test_parse_yes_no(text: str, expected: bool | None) -> None:
    assert parse_yes_no(text) == expected
