# app/models/tenant.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.professionals import ProfessionalCreate
from app.models.core import Professional
from app.helpers.constants import DEFAULT_DISPLAY_DATE_FORMAT, DEFAULT_TIMEZONE


class Tenant(BaseModel):
    id: str = Field(..., alias="_id")
    category: str = "salon"
    plan: str = "pro"  # subscription plan: basic | pro | enterprise
    display_name: Optional[str] = None  # shown in UI instead of tenant id when set
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    tz: Optional[str] = DEFAULT_TIMEZONE
    modules: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)
    active: bool = True

    whatsapp_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    payment_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    delivery_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    smtp_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    ai_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    messaging_channels: Optional[Dict[str, Any]] = Field(default_factory=dict)  # email, whatsapp, sms
    sms_config: Optional[Dict[str, Any]] = Field(default_factory=dict)

    date_format: Optional[str] = DEFAULT_DISPLAY_DATE_FORMAT
    address: Optional[str] = None   # business address for messages
    location: Optional[str] = None  # map link (e.g. Google Maps URL)

    class Config:
        populate_by_name = True
        extra = "ignore"


class TenantCreate(BaseModel):
    tenant: str
    category: Optional[str] = "salon"
    professionals: Optional[List[ProfessionalCreate]] = None

    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    tz: Optional[str] = None

    whatsapp_config: Optional[Dict[str, Any]] = None

    admin_email: str
    admin_password: str = Field(..., min_length=8)
    admin_display_name: Optional[str] = None


class TenantCreateResponse(BaseModel):
    tenant: str
    category: str
    professionals: List[Professional] = Field(default_factory=list)
    appointments: int
    revenue: float
