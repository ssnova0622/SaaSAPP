# app/repositories/whatsapp_trigger_repository.py
from typing import List, Optional
from app.repositories.base_repository import BaseRepository
from app.models.whatsapp import WhatsAppTrigger


class WhatsAppTriggerRepository(BaseRepository[WhatsAppTrigger]):
    def __init__(self):
        super().__init__("whatsapp_triggers", WhatsAppTrigger)

    def list_by_tenant(self, tenant: str) -> List[WhatsAppTrigger]:
        return self.find_many({"tenant": tenant})

    def find_by_trigger_id(self, tenant: str, trigger_id: str) -> Optional[WhatsAppTrigger]:
        return self.find_one({"tenant": tenant, "trigger_id": trigger_id})

    def delete_by_trigger_id(self, tenant: str, trigger_id: str) -> bool:
        return self.delete_one({"tenant": tenant, "trigger_id": trigger_id})
