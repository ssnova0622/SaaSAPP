# app/repositories/service_repository.py
from typing import Optional, List
from app.repositories.base_repository import BaseRepository
from app.models.services import ServiceOut


class ServiceRepository(BaseRepository[ServiceOut]):
    def __init__(self):
        super().__init__("services", ServiceOut)

    def find_by_name(self, tenant: str, name: str) -> Optional[ServiceOut]:
        return self.find_one({"tenant": tenant, "name": name})

    def list_by_tenant(self, tenant: str, active: Optional[bool] = None) -> List[ServiceOut]:
        query = {"tenant": tenant}
        if active is not None:
            query["active"] = active
        return self.find_many(query)
