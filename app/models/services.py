# app/models/services.py
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel


class ServiceIn(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = 0.0
    duration: int = 30
    active: bool = True
    # Booking window for this service (e.g. "09:00" / "18:00").
    # When set, WhatsApp slot generation uses these times instead of the tenant-wide defaults.
    start_time: Optional[str] = None   # "HH:MM" — when bookings open for this service
    end_time: Optional[str] = None     # "HH:MM" — when bookings close for this service


class ServiceOut(ServiceIn):
    tenant: Optional[str] = "unknown"
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
