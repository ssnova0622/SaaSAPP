# app/models/staff.py
from __future__ import annotations
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class Staff(BaseModel):
    id: str
    tenant: str
    name: str
    role: str
    position: Optional[str] = None
    phone_number: Optional[Dict[str, str]] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    active: bool = True
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class StaffListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
