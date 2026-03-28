# app/models/users.py
from __future__ import annotations
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field

from app.helpers.constants import USER_STATUS_ACTIVE


class User(BaseModel):
    id: str
    email: str
    password_hash: str
    role: str = Field(..., description="super_admin | tenant_admin | staff")
    tenant: Optional[str] = None
    display_name: str = ""
    phone: Optional[str] = None  # optional; used for login OTP when enabled
    caps: List[str] = Field(default_factory=list)
    status: str = Field(default=USER_STATUS_ACTIVE, description="active | disabled")
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class UserListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int

class PasswordBody(BaseModel):
    password: str = Field(..., min_length=8)
