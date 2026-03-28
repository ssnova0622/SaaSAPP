# app/repositories/order_repository.py
from typing import Any, Dict, List, Optional
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Order(BaseModel):
    tenant: str
    items: List[Dict[str, Any]]
    status: str
    created_at: Any


class OrderRepository(BaseRepository[Order]):
    def __init__(self):
        super().__init__("orders", Order)

    def list_by_tenant(self, tenant: str, status_ne: Optional[str] = None, since: Optional[Any] = None) -> List[Order]:
        query = {"tenant": tenant}
        if status_ne:
            query["status"] = {"$ne": status_ne}
        if since:
            query["created_at"] = {"$gte": since}
        return self.find_many(query)
