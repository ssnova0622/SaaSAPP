# app/repositories/analytics_repository.py
from typing import Any, Dict
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class AnalyticsEvent(BaseModel):
    id: str
    tenant: str
    type: str
    ts: float
    data: Dict[str, Any] = {}
    created_at: Any


class AnalyticsRepository(BaseRepository[AnalyticsEvent]):
    def __init__(self):
        super().__init__("events", AnalyticsEvent)
