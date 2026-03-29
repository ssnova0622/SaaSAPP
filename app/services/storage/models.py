"""Shared dataclasses for storage layer (compatibility with in-memory backend)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import datetime as dt

from app.helpers.constants import SLOT_STATUS_AVAILABLE


@dataclass
class Slot:
    time: str
    status: str = SLOT_STATUS_AVAILABLE  # available|booked


@dataclass
class Professional:
    name: str
    professional_id: Optional[str] = None
    employee_id: Optional[str] = None
    short_name: Optional[str] = None
    price: float = 0.0
    slots: List[Slot] = field(default_factory=list)
    active: bool = True
    date_overrides: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    availability_criteria: str = "daily"  # daily|weekly|monthly
    available_days: List[int] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


@dataclass
class Appointment:
    id: str
    customer_name: str
    customer_phone: str
    professional: str
    time: str
    price: float
    status: str = "booked"  # booked|canceled|needs_reschedule
    service: Optional[str] = None
    created_at: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))
    created_by: Optional[str] = None
    updated_at: Optional[dt.datetime] = None
    updated_by: Optional[str] = None
    start: Optional[dt.datetime] = None
    end: Optional[dt.datetime] = None
    professional_id: Optional[str] = None
