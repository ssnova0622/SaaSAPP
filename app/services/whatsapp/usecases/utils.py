"""Small WhatsApp use-case utilities (numeric menu parsing).

Kept free of I/O so any module can import without pulling Mongo or tier services.
"""
from __future__ import annotations
import re
from typing import Optional


def choice_to_index(text: str) -> Optional[int]:
    """Parse user input to 1-based index (e.g. '1', '1)', '1. Option')."""
    if not text:
        return None
    s = text.strip()
    if s.isdigit():
        return int(s)
    match = re.search(r"^\s*([0-9]+)", text)
    if match:
        return max(1, int(match.group(1)))
    return None


def parse_yes_no(text: str) -> Optional[bool]:
    """
    Interpret confirmation replies. Returns True (yes), False (no), or None if unclear.
    Accepts menu numbers 1/2 and common words so workflows are not stuck on strict digits.
    """
    if not text or not str(text).strip():
        return None
    raw = str(text).strip()
    low = raw.lower()
    idx = choice_to_index(raw)
    if idx == 1:
        return True
    if idx == 2:
        return False
    if low in (
        "yes", "y", "yeah", "yep", "sure", "ok", "okay", "confirm",
        "correct", "affirmative", "please", "proceed",
    ):
        return True
    if low in ("no", "n", "nope", "negative", "dont", "don't", "do not"):
        return False
    return None
