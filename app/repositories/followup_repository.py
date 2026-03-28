# app/repositories/followup_repository.py
from typing import Any, Dict, List
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Followup(BaseModel):
    id: str
    tenant: str
    appointment_id: str
    type: str
    status: str
    run_at: Any
    data: Dict[str, Any]


class FollowupRepository(BaseRepository[Followup]):
    def __init__(self):
        super().__init__("followups", Followup)

    def find_by_appointment(self, tenant: str, appointment_id: str) -> List[Followup]:
        return self.find_many({"tenant": tenant, "appointment_id": appointment_id})

    def delete_by_appointment(self, tenant: str, appointment_id: str):
        self.get_collection().delete_many({"tenant": tenant, "appointment_id": appointment_id})
