# app/models/auth.py
from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]


class MeResponse(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    role: str
    tenant: Optional[str] = None
    display_name: Optional[str] = None
    caps: Optional[list] = None
