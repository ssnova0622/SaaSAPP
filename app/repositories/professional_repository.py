# app/repositories/professional_repository.py
from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.professionals import Professional


class ProfessionalRepository(BaseRepository[Professional]):
    def __init__(self):
        super().__init__("professionals", Professional)

    def find_by_name(self, tenant: str, name: str) -> Optional[Professional]:
        return self.find_one({"tenant": tenant, "name": name})

    def list_by_tenant(self, tenant: str, active: Optional[bool] = None) -> list[Professional]:
        query = {"tenant": tenant}
        if active is not None:
            query["active"] = active
        return self.find_many(query)
