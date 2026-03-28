# app/models/workflows.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class WorkflowStep(BaseModel):
    action_code: str
    label: Optional[str] = None
    input_required: bool = False
    output_key: Optional[str] = None
    ui_type: str = "list"
    params: Dict[str, Any] = Field(default_factory=dict)

    skipped: bool = False
    auto_assign: bool = False


class WorkflowDefinition(BaseModel):
    tenant: str
    workflow_id: str
    name: str
    steps: List[WorkflowStep]
    active: bool = True
    requires_caps: List[str] = Field(default_factory=list)
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class WorkflowActionMeta(BaseModel):
    action_code: str
    label: str
    input_required: bool
    output_key: Optional[str] = None
    ui_type: str
    description: Optional[str] = None
    module: Optional[str] = None
    group: Optional[str] = None
    requires_caps: List[str] = Field(default_factory=list)
