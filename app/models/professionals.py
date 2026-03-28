# app/models/professionals.py
from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field
from app.models.core import Slot


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


class ProfessionalCreate(BaseModel):
    name: str
    price: float = 0.0
    slots: Union[List[str], List[Slot]] = Field(
        default_factory=list,
        description="List of HH:MM strings or Slot objects"
    )
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
