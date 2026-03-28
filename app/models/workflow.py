from __future__ import annotations
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class WorkflowStep(BaseModel):
    action_code: str = Field(..., description="Action ID like SHOW_SERVICES, SELECT_DATE")
    label: Optional[str] = None
    input_required: bool = False
    output_key: Optional[str] = None
    ui_type: str = "list" # list|text|button|date
    params: Dict[str, Any] = Field(default_factory=dict)

class WorkflowDefinition(BaseModel):
    tenant: str
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    active: bool = True
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None

class WorkflowActionMeta(BaseModel):
    action_code: str
    label: str
    input_required: bool
    output_key: Optional[str] = None
    ui_type: str
    description: Optional[str] = None
