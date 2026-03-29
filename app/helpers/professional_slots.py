"""Normalize slot payloads and build default / schedule-based slot lists."""
from __future__ import annotations

from typing import Any, List, Optional

from app.helpers.constants import SLOT_STATUS_AVAILABLE
from app.services.storage.models import Slot


def minutes_from_midnight(hhmm: str) -> int:
    parts = (hhmm or "").strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time {hhmm!r}; use HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"Invalid time {hhmm!r}; use HH:MM with valid hour/minute")
    return h * 60 + m


def format_hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def generate_slot_times(work_start: str, work_end: str, interval_minutes: int) -> List[str]:
    """Start times from ``work_start`` inclusive until ``work_end`` (exclusive), step ``interval_minutes``."""
    if interval_minutes < 5 or interval_minutes > 240:
        raise ValueError("slot_interval_minutes must be between 5 and 240")
    a = minutes_from_midnight(work_start)
    b = minutes_from_midnight(work_end)
    if a >= b:
        raise ValueError("work_start must be before work_end")
    out: List[str] = []
    cur = a
    while cur < b:
        out.append(format_hhmm(cur))
        cur += interval_minutes
    return out


def slots_from_schedule(work_start: str, work_end: str, interval_minutes: int) -> List[Slot]:
    return [
        Slot(time=t, status=SLOT_STATUS_AVAILABLE)
        for t in generate_slot_times(work_start, work_end, interval_minutes)
    ]


def normalize_slots(raw: Optional[Any]) -> List[Slot]:
    if not raw:
        return []
    out: List[Slot] = []
    for item in raw:
        if isinstance(item, str):
            t = item.strip()
            if t:
                out.append(Slot(time=t, status=SLOT_STATUS_AVAILABLE))
            continue
        if isinstance(item, dict):
            t = (item.get("time") or "").strip()
            status = (item.get("status") or SLOT_STATUS_AVAILABLE).strip() or SLOT_STATUS_AVAILABLE
            if t:
                out.append(Slot(time=t, status=status))
            continue
        t = getattr(item, "time", None)
        s = getattr(item, "status", SLOT_STATUS_AVAILABLE)
        if isinstance(t, str) and t.strip():
            out.append(Slot(time=t.strip(), status=s))
    return out


def default_business_slots(start_hour: int = 9, end_hour: int = 19) -> List[Slot]:
    slots: List[Slot] = []
    for h in range(start_hour, end_hour):
        slots.append(Slot(time=f"{h:02d}:00", status=SLOT_STATUS_AVAILABLE))
        slots.append(Slot(time=f"{h:02d}:30", status=SLOT_STATUS_AVAILABLE))
    return slots
