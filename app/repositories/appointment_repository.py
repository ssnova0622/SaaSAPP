# app/repositories/appointment_repository.py
from typing import List, Optional
from app.repositories.base_repository import BaseRepository
from app.models.appointments import AppointmentOut as Appointment


class AppointmentRepository(BaseRepository[Appointment]):
    def __init__(self):
        super().__init__("appointments", Appointment)

    def list_by_tenant(self, tenant: str, professional: Optional[str] = None, date: Optional[str] = None) -> List[
        Appointment]:
        query = {"tenant": tenant}
        if professional:
            query["professional"] = professional
        if date:
            query["date"] = date
        return self.find_many(query)

    def find_by_id(self, tenant: str, appointment_id: str) -> Optional[Appointment]:
        return self.find_one({"tenant": tenant, "id": appointment_id})
