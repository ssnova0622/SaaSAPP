# app/models/retention.py
from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel


class RetentionSummaryResponse(BaseModel):
    tenant: str
    date: str
    active: int
    at_risk: int
    churned: int


class RetentionListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int
