# app/repositories/tenant_repository.py
from typing import Optional, List

from app.models.tenant import Tenant
from app.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[Tenant]):
    def __init__(self):
        super().__init__("tenants", Tenant)

    def find_by_id(self, tenant_id: str) -> Optional[Tenant]:
        # Tenant uses _id as the primary identifier
        doc = self.get_collection().find_one({"_id": tenant_id})
        if doc:
            # We don't pop _id here because Tenant model uses it via alias
            return Tenant(**doc)
        return None

    def list_all(self) -> List[Tenant]:
        cursor = self.get_collection().find({})
        results = []
        for doc in cursor:
            # We don't pop _id here because Tenant model uses it via alias
            results.append(Tenant(**doc))
        return results
