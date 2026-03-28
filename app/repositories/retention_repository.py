# app/repositories/retention_repository.py
from typing import Any, Dict, Optional
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class RetentionMetric(BaseModel):
    tenant: str
    date: str
    active: int
    at_risk: int
    churned: int
    created_at: Any


class RetentionRepository(BaseRepository[RetentionMetric]):
    def __init__(self):
        super().__init__("retention_metrics", RetentionMetric)

    def find_latest(self, tenant: str) -> Optional[RetentionMetric]:
        return self.find_one({"tenant": tenant})  # Note: find_one doesn't support sort in base, might need override

    def upsert_metric(self, tenant: str, date_str: str, data: Dict[str, Any]):
        self.get_collection().update_one(
            {"tenant": tenant, "date": date_str},
            {"$set": data},
            upsert=True
        )
