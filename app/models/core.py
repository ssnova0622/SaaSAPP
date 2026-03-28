# app/models/core.py
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

from app.helpers.constants import SLOT_STATUS_AVAILABLE


class Slot(BaseModel):
    time: str
    status: str = Field(
        default=SLOT_STATUS_AVAILABLE,
        description="available | booked | blocked | completed"
    )


class Professional(BaseModel):
    name: str
    price: float
    slots: List[Slot] = Field(default_factory=list)
    active: bool = True
    availability_criteria: str = Field(default="daily", description="daily | weekly | monthly")
    available_days: List[int] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None
