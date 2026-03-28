# app/repositories/inventory_repository.py
from typing import List
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Inventory(BaseModel):
    tenant: str
    sku: str
    available_qty: float


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self):
        super().__init__("inventory", Inventory)

    def find_by_skus(self, tenant: str, skus: List[str]) -> List[Inventory]:
        return self.find_many({"tenant": tenant, "sku": {"$in": skus}})
