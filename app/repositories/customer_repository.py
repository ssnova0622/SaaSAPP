# app/repositories/customer_repository.py
from typing import Optional, List, Dict, Any
from app.repositories.base_repository import BaseRepository
from app.models.customers import Customer


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self):
        super().__init__("customers", Customer)

    def find_by_phone(self, tenant: str, phone: str) -> Optional[Customer]:
        return self.find_one({"tenant": tenant, "phone": phone})

    def list_by_tenant(self, tenant: str) -> List[Customer]:
        return self.find_many({"tenant": tenant})

    def list_dicts_by_tenant(self, tenant: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for doc in self.get_collection().find({"tenant": tenant}).sort("name", 1):
            d = dict(doc)
            d.pop("_id", None)
            items.append(d)
        return items
