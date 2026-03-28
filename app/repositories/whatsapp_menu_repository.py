# app/repositories/whatsapp_menu_repository.py
from typing import List, Optional
from app.repositories.base_repository import BaseRepository
from app.models.whatsapp import WhatsAppMenu


class WhatsAppMenuRepository(BaseRepository[WhatsAppMenu]):
    def __init__(self):
        super().__init__("whatsapp_menus", WhatsAppMenu)

    def list_by_tenant(self, tenant: str) -> List[WhatsAppMenu]:
        return self.find_many({"tenant": tenant})

    def find_by_menu_id(self, tenant: str, menu_id: str, status: Optional[str] = None) -> Optional[WhatsAppMenu]:
        query = {"tenant": tenant, "menu_id": menu_id}
        if status:
            query["status"] = status
        # Note: We might want to sort by version if we support multiple versions
        return self.find_one(query)

    def upsert_menu(self, menu: WhatsAppMenu) -> WhatsAppMenu:
        query = {"tenant": menu.tenant, "menu_id": menu.menu_id, "status": menu.status}
        doc = menu.dict()
        self.get_collection().update_one(query, {"$set": doc}, upsert=True)
        return menu

    def delete_by_menu_id(self, tenant: str, menu_id: str) -> bool:
        return self.delete_one({"tenant": tenant, "menu_id": menu_id})
