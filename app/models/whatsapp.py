# app/models/whatsapp.py
from __future__ import annotations
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone

# --- Menus ---

class WhatsAppMenu(BaseModel):
    tenant: str
    menu_id: str
    name: str
    status: str = "draft"  # draft | published
    version: int = 1
    tree: Dict[str, Any] = Field(default_factory=dict)
    locales: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    published_at: Optional[datetime] = None
    published_by: Optional[str] = None

class WhatsAppMenuUpsert(BaseModel):
    menu_id: str
    name: str
    tree: Dict[str, Any]
    locales: Optional[Dict[str, Any]] = None

class WhatsAppMenuListResponse(BaseModel):
    items: List[WhatsAppMenu]
    total: int

# --- Triggers ---

class TriggerMatch(BaseModel):
    type: str  # exact | prefix | contains | regex
    value: str
    locale: Optional[str] = None

class TriggerAction(BaseModel):
    kind: str  # render_submenu | jump_node | static_text | invoke_action
    menu_id: Optional[str] = None
    node_id: Optional[str] = None
    text: Optional[Union[str, Dict[str, str]]] = None

class WhatsAppTrigger(BaseModel):
    tenant: str
    trigger_id: str
    match: TriggerMatch
    action: TriggerAction
    enabled: bool = True
    priority: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None

class WhatsAppTriggerCreate(BaseModel):
    trigger_id: str
    match: TriggerMatch
    action: TriggerAction
    enabled: bool = True
    priority: int = 0

class WhatsAppTriggerListResponse(BaseModel):
    items: List[WhatsAppTrigger]
    total: int

# --- Actions ---

class WhatsAppActionMeta(BaseModel):
    id: str
    label: str
    module: str
    requires_caps: List[str] = Field(default_factory=list)

class WhatsAppActionListResponse(BaseModel):
    items: List[WhatsAppActionMeta]
    total: int

# --- Bot simulation ---

class BotNextStepRequest(BaseModel):
    phone: str
    input: str
    menu_id: Optional[str] = None
    node: Optional[str] = None
    locale: Optional[str] = "en"

class BotNextStepResponse(BaseModel):
    reply: str
    node: Optional[str] = None
    session: Optional[Dict[str, Any]] = None
