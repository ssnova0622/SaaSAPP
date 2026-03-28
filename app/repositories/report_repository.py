# app/repositories/report_repository.py
from app.repositories.base_repository import BaseRepository
from pydantic import BaseModel


class Report(BaseModel):
    tenant: str
    date: str
    storage: str
    url_type: str
    created_at: str
    sent_via: list = []
    status: str = "generated"


class ReportRepository(BaseRepository[Report]):
    def __init__(self):
        super().__init__("reports", Report)
