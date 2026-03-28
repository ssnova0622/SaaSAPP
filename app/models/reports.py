# app/models/reports.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import date
from pydantic import BaseModel


class ReportListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


class ReportRunResponse(BaseModel):
    id: str
    tenant: str
    date: str
    links: Optional[Dict[str, str]] = None


class TimeseriesResponse(BaseModel):
    items: List[Dict[str, Any]]
    days: Optional[int]
    interval: str = "day"
