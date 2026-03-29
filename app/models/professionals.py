# app/models/professionals.py
from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.core import Slot


class Professional(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    professional_id: Optional[str] = None
    employee_id: Optional[str] = None
    short_name: Optional[str] = None
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


class ProfessionalCreate(BaseModel):
    name: str
    employee_id: str
    price: float = 0.0
    slots: Union[List[str], List[Slot]] = Field(default_factory=list)
    slot_interval_minutes: int = Field(default=30, ge=5, le=240)
    work_start: str = Field(default="09:00", pattern=r"^\d{2}:\d{2}$")
    work_end: str = Field(default="18:00", pattern=r"^\d{2}:\d{2}$")
    active: bool = True
    availability_criteria: str = "daily"
    available_days: List[int] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


class ProfessionalPatch(BaseModel):
    name: Optional[str] = None
    employee_id: Optional[str] = None
    price: Optional[float] = None
    slots: Optional[Union[List[str], List[Slot]]] = None
    active: Optional[bool] = None
    availability_criteria: Optional[str] = None
    available_days: Optional[List[int]] = None
    services: Optional[List[str]] = None
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


class ProfessionalListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int


class ProfessionalOut(BaseModel):
    name: str
    price: float
    slots: List[Slot]
    active: bool
    availability_criteria: Optional[str] = None
    available_days: Optional[List[int]] = None
    services: Optional[List[str]] = None
    phone: Optional[str] = None
    degree: Optional[str] = None
    address: Optional[str] = None
    bio: Optional[str] = None


class UpdateSlotsBody(BaseModel):
    slots: List[Union[str, Slot]] = Field(default_factory=list)
    date: Optional[str] = None


class SlotStatusPatch(BaseModel):
    status: str = Field(..., pattern="^(available|blocked)$")
    size: int
