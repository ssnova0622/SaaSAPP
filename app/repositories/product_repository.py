# app/repositories/product_repository.py
from typing import Any, Dict, List, Optional
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Product(BaseModel):
    tenant: str
    sku: str
    name: str
    variants: Optional[List[Dict[str, Any]]] = None


class ProductRepository(BaseRepository[Product]):
    def __init__(self):
        super().__init__("products", Product)

    def find_by_skus(self, tenant: str, skus: List[str]) -> List[Product]:
        return self.find_many({"tenant": tenant, "sku": {"$in": skus}})

    def find_by_variant_skus(self, tenant: str, skus: List[str]) -> List[Product]:
        return self.find_many({"tenant": tenant, "variants.variant_sku": {"$in": skus}})
