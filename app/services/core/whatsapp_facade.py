# app/services/core/whatsapp_facade.py
"""
WhatsApp facade: single entry point for WhatsApp sessions, menus, triggers.
Routers use get_whatsapp_service() instead of Storage directly.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.storage_mongo import Storage


class WhatsAppService:
    """Facade over Storage for WhatsApp sessions, menus, triggers."""

    @staticmethod
    def get_whatsapp_session(tenant: str, phone: str) -> Optional[Dict[str, Any]]:
        return Storage.get_whatsapp_session(tenant, phone)

    @staticmethod
    def upsert_whatsapp_session(
        tenant: str, phone: str, data: Dict[str, Any], ttl_minutes: int = 30
    ) -> Dict[str, Any]:
        return Storage.upsert_whatsapp_session(tenant, phone, data, ttl_minutes=ttl_minutes)

    @staticmethod
    def get_whatsapp_menu(
        tenant: str,
        menu_id: str,
        status: Optional[str] = None,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        return Storage.get_whatsapp_menu(tenant, menu_id, status=status, version=version)

    @staticmethod
    def list_whatsapp_menus(tenant: str) -> List[Dict[str, Any]]:
        return Storage.list_whatsapp_menus(tenant)

    @staticmethod
    def upsert_whatsapp_menu_draft(tenant: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        return Storage.upsert_whatsapp_menu_draft(tenant, doc)

    @staticmethod
    def publish_whatsapp_menu(tenant: str, menu_id: str, user_id: str) -> Dict[str, Any]:
        return Storage.publish_whatsapp_menu(tenant, menu_id, user_id)

    @staticmethod
    def delete_whatsapp_menu(tenant: str, menu_id: str, user_id: Optional[str] = None) -> bool:
        return Storage.delete_whatsapp_menu(tenant, menu_id, user_id=user_id)

    @staticmethod
    def fetch_enabled_triggers(tenant: str) -> List[Dict[str, Any]]:
        return Storage.fetch_enabled_triggers(tenant)

    @staticmethod
    def list_whatsapp_triggers(tenant: str) -> List[Dict[str, Any]]:
        return Storage.list_whatsapp_triggers(tenant)

    @staticmethod
    def get_whatsapp_trigger(tenant: str, trigger_id: str) -> Optional[Dict[str, Any]]:
        return Storage.get_whatsapp_trigger(tenant, trigger_id)

    @staticmethod
    def upsert_whatsapp_trigger(tenant: str, trigger: Dict[str, Any]) -> Dict[str, Any]:
        return Storage.upsert_whatsapp_trigger(tenant, trigger)

    @staticmethod
    def delete_whatsapp_trigger(tenant: str, trigger_id: str, user_id: Optional[str] = None) -> bool:
        return Storage.delete_whatsapp_trigger(tenant, trigger_id, user_id=user_id)

    @staticmethod
    def list_tenant_whatsapp_actions(tenant: str) -> List[Dict[str, Any]]:
        return Storage.list_tenant_whatsapp_actions(tenant)

    @staticmethod
    def get_tenant_whatsapp_action(tenant: str, action_id: str) -> Optional[Dict[str, Any]]:
        return Storage.get_tenant_whatsapp_action(tenant, action_id)

    @staticmethod
    def upsert_tenant_whatsapp_action(tenant: str, doc: Dict[str, Any]) -> Dict[str, Any]:
        return Storage.upsert_tenant_whatsapp_action(tenant, doc)

    @staticmethod
    def delete_tenant_whatsapp_action(tenant: str, action_id: str) -> bool:
        return Storage.delete_tenant_whatsapp_action(tenant, action_id)

    @staticmethod
    def increment_whatsapp_inbound(tenant: str) -> None:
        Storage.increment_whatsapp_inbound(tenant)
