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


class ServiceOut(ServiceIn):
    tenant: Optional[str] = "unknown"
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
