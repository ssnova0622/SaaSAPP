# app/models/promotions.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# -----------------------------
# Shared Components
# -----------------------------

class Segment(BaseModel):
    type: str = Field(..., description="active|at_risk|churned")
    days: Optional[int] = None


class Audience(BaseModel):
    type: str = Field("all", description="all|tags|custom|segment")
    tags: Optional[List[str]] = None
    phones: Optional[List[str]] = None
    emails: Optional[List[str]] = None
    segment: Optional[Segment] = None


class Attachment(BaseModel):
    type: str = Field(..., description="image|video|link")
    url: str
    name: Optional[str] = None


class Button(BaseModel):
    id: str
    title: str
    url: Optional[str] = None


class ListRow(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None


class ListSection(BaseModel):
    title: Optional[str] = None
    rows: List[ListRow]


# -----------------------------
# Create / Update Schemas
# -----------------------------

class PromotionBase(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = Field(None, description="whatsapp|email|both")
    message: Optional[str] = None
    html_message: Optional[str] = None
    media_url: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    interactive_type: Optional[str] = Field(None, description="button|list")
    buttons: Optional[List[Button]] = None
    list_sections: Optional[List[ListSection]] = None
    audience: Optional[Audience] = None
    schedule_at: Optional[datetime] = None


class PromotionCreate(PromotionBase):
    name: str
    channel: str = "both"
    message: str
    audience: Audience = Field(default_factory=Audience)


class PromotionUpdate(PromotionBase):
    status: Optional[str] = Field(None, description="draft|scheduled|canceled")


# -----------------------------
# Response Schemas
# -----------------------------

class PromotionResponse(BaseModel):
    id: str
    tenant: str
    name: str
    channel: str
    message: str
    html_message: Optional[str] = None
    media_url: Optional[str] = None
    attachments: Optional[List[Attachment]] = None
    interactive_type: Optional[str] = None
    buttons: Optional[List[Button]] = None
    list_sections: Optional[List[ListSection]] = None
    audience: Dict[str, Any]
    status: str
    schedule_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class PromotionSendResponse(BaseModel):
    id: str
    tenant: str
    status: str
    total: int
    sent: int
    failed: int


class PromotionLogsResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
