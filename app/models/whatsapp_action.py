# app/models/whatsapp_action.py
"""Global WhatsApp action definition (Super Admin creates; tenants get a subset assigned)."""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class WhatsAppAction(BaseModel):
    """One global WhatsApp action. Stored in whatsapp_actions collection (no tenant). One action = one output."""
    action_id: str = Field(..., description="Unique code e.g. SHOW_SERVICES, salon.book_appointment")
    label: str = Field(..., description="Display label")
    modules: List[str] = Field(default_factory=list, description="Modules e.g. core, salon, clinic, store")
    requires_caps: List[str] = Field(default_factory=list, description="Required capability ids")
    description: Optional[str] = Field(None, description="Short description")
