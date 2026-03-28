"""
Pure time parsing and slot distance helpers for salon booking (no I/O).

Kept separate from :mod:`booking_flow` to shrink the FSM module and ease unit testing.
"""
from __future__ import annotations

import re
from typing import List, Optional


def parse_time_input(text: str) -> Optional[tuple]:
    """Parse user input as time. Returns (hour_24h, minute) or None."""
    if not text or not text.strip():
        return None
    t = text.strip().lower()
    if t in ("morning", "morn"):
        return (9, 0)
    if t in ("afternoon", "noon"):
        return (14, 0)
    if t in ("evening", "eve"):
        return (18, 0)
    if t in ("night", "late"):
        return (20, 0)
    if t in ("early morning", "early morn"):
        return (8, 0)
    if t in ("mid morning", "mid-morning"):
        return (10, 0)
    if t in ("late morning"):
        return (11, 0)
    if t in ("early afternoon"):
        return (13, 0)
    if t in ("late afternoon"):
        return (16, 0)
    if t in ("early evening"):
        return (17, 0)
    if t in ("late evening"):
        return (20, 0)
    m = re.match(r"^\s*after\s+(\d{1,2})\s+(evening|eve|morning|morn|afternoon|noon|night)\s*$", t)
    if m:
        h = int(m.group(1))
        period = m.group(2)
        if period in ("evening", "eve"):
            h = h + 12 if 1 <= h <= 11 else (12 if h == 12 else h)
        elif period in ("morning", "morn"):
            h = 0 if h == 12 else h
        elif period in ("afternoon", "noon"):
            h = (h + 12) if 1 <= h <= 11 else (12 if h == 12 else h)
        else:
            h = (h + 12) if 1 <= h <= 11 else (12 if h == 12 else h)
        if 0 <= h <= 23:
            return (h, 0)
    m = re.match(r"^\s*(\d{1,2})\s+(?:in\s+)?(the\s+)?(evening|eve|morning|morn|afternoon|noon|night)\s*$", t)
    if m:
        h = int(m.group(1))
        period = m.group(3)
        if period in ("evening", "eve", "night"):
            h = (h + 12) if 1 <= h <= 11 else (12 if h == 12 else h)
        elif period in ("afternoon", "noon"):
            h = (h + 12) if 1 <= h <= 11 else (12 if h == 12 else h)
        elif period in ("morning", "morn"):
            h = 0 if h == 12 else h
        if 0 <= h <= 23:
            return (h, 0)
    m = re.match(r"^\s*(around|about|by)\s+(\d{1,2})\s*(am|pm)?\s*$", t)
    if m:
        h = int(m.group(2))
        ampm = m.group(3)
        if ampm == "pm" and h != 12:
            h += 12
        elif ampm == "am" and h == 12:
            h = 0
        elif not ampm and 1 <= h <= 11:
            h += 12
        if 0 <= h <= 23:
            return (h, 0)
    m = re.match(r"^\s*after\s+(\d{1,2})\s*(am|pm)?\s*$", t)
    if m:
        h = int(m.group(1))
        if m.group(2):
            if m.group(2) == "pm" and h != 12:
                h += 12
            elif m.group(2) == "am" and h == 12:
                h = 0
        else:
            if 1 <= h <= 11:
                h += 12
            elif h == 12:
                h = 12
        if 0 <= h <= 23:
            return (h, 0)
    m = re.match(r"^\s*(\d{1,2})[.:]?(\d{2})\s*$", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return (h, mi)
    m = re.match(r"^\s*(\d{1,2})[.:]?(\d{0,2})\s*(am|pm)\s*$", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or "0")
        if m.group(3).lower() == "pm" and h != 12:
            h += 12
        elif m.group(3).lower() == "am" and h == 12:
            h = 0
        if 0 <= h <= 23 and 0 <= mi <= 59:
            return (h, mi)
    return None


def _slot_to_minutes(slot: str) -> int:
    try:
        parts = str(slot).strip().split(":")
        h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        return h * 60 + m
    except (ValueError, IndexError):
        return 0


def slots_near_time(
        slots: List[str], target_hour: int, target_min: int,
        window_minutes: int = 90, max_slots: int = 8,
) -> List[str]:
    target_m = target_hour * 60 + target_min
    with_dist = []
    for s in slots:
        if not s:
            continue
        dist = abs(_slot_to_minutes(s) - target_m)
        if dist <= window_minutes:
            with_dist.append((dist, s))
    with_dist.sort(key=lambda x: (x[0], x[1]))
    return [s for _, s in with_dist[:max_slots]]


def format_time_12h(hour: int, minute: int) -> str:
    if hour == 0:
        return f"12:{minute:02d} AM"
    if hour == 12:
        return f"12:{minute:02d} PM"
    if hour < 12:
        return f"{hour}:{minute:02d} AM"
    return f"{hour - 12}:{minute:02d} PM"
