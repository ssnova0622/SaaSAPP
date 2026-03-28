# app/repositories/cart_repository.py
from typing import Any, Dict, List
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Cart(BaseModel):
    tenant: str
    items: List[Dict[str, Any]]
    updated_at: Any


class CartRepository(BaseRepository[Cart]):
    def __init__(self):
        super().__init__("carts", Cart)

    def count_abandoned(self, tenant: str, since: Any) -> int:
        query = {
            "tenant": tenant,
            "updated_at": {"$gte": since},
            "items.0": {"$exists": True}
        }
        return self.get_collection().count_documents(query)
