# app/models/analytics.py
from __future__ import annotations
from pydantic import BaseModel


class AnalyticsResponse(BaseModel):
    tenant: str
    total_appointments: int
    cancellations: int
    revenue: float

