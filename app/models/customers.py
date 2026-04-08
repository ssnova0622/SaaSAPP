# app/models/customers.py
from __future__ import annotations
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class Customer(BaseModel):
    model_config = {"extra": "ignore"}
    tenant: str
    phone_number: Optional[Dict[str, str]] = None
    name: str
    email: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    active: bool = True
    no_show_count: int = Field(default=0, description="Number of no-shows; used to block booking when >= threshold")
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class CustomerListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


class StatusPatch(BaseModel):
    active: bool
