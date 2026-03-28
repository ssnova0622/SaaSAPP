# app/repositories/staff_repository.py
from typing import Optional, List
from app.repositories.base_repository import BaseRepository
from app.models.staff import Staff


class StaffRepository(BaseRepository[Staff]):
    def __init__(self):
        super().__init__("staff", Staff)

    def find_by_id(self, tenant: str, staff_id: str) -> Optional[Staff]:
        return self.find_one({"tenant": tenant, "id": staff_id})

    def list_by_tenant(self, tenant: str, active: Optional[bool] = None) -> List[Staff]:
        query = {"tenant": tenant}
        if active is not None:
            query["active"] = active
        return self.find_many(query)
