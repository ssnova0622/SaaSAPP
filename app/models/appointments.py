# app/models/appointments.py
from __future__ import annotations
from typing import Optional,  List
from pydantic import BaseModel, Field


class AvailabilityItem(BaseModel):
    start: str
    end: str
    capacity: int = Field(ge=1)
    remaining: int = Field(ge=0)
    bookable: bool
    blocked: Optional[bool] = None


class AppointmentIn(BaseModel):
    tenant: str
    customer_name: str
    customer_phone: str
    professional: str = ""
    professional_id: Optional[str] = None
    time: str
    date: Optional[str] = None


class AppointmentOut(BaseModel):
    id: str = "unknown"
    tenant: str = "unknown"
    customer_name: str = ""
    customer_phone: str = ""
    professional: str = ""
    professional_id: Optional[str] = None
    time: str = ""
    date: Optional[str] = None
    price: float = 0.0
    status: str = "unknown"
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class AppointmentListResponse(BaseModel):
    items: List[AppointmentOut]
    total: int
    page: int
    size: int


class AppointmentListItem(AppointmentOut):
    """Alias for list responses."""
    pass


class ReschedulePayload(BaseModel):
    new_time: str
    new_date: Optional[str] = Field(None, description="YYYY-MM-DD")


class StatusUpdatePayload(BaseModel):
    status: str = Field(..., pattern="^(booked|completed)$")
