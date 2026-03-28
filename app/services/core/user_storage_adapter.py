# app/services/core/user_storage_adapter.py
"""
Thin adapter that delegates user CRUD and resolve_user_names to Storage.
Allows routers to use get_user_service() without importing Storage directly.
Storage uses _id (ObjectId) as user id; this adapter preserves that behavior.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.storage_mongo import Storage


class UserStorageAdapter:
    """Delegates all user operations to Storage. Use via get_user_service() from container."""

    @staticmethod
    def list_users(
        tenant: Optional[str] = None,
        role: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> Dict[str, Any]:
        return Storage.list_users(tenant=tenant, role=role, search=search, page=page, size=size)

    @staticmethod
    def create_user(
        email: str,
        password: str,
        role: str,
        tenant: Optional[str] = None,
        display_name: str = "",
        phone: Optional[str] = None,
        caps: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return Storage.create_user(
            email=email,
            password=password,
            role=role,
            tenant=tenant,
            display_name=display_name,
            phone=phone,
            caps=caps or [],
        )

    @staticmethod
    def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        return Storage.get_user_by_id(user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
        return Storage.get_user_by_email(email)

    @staticmethod
    def update_user(user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        return Storage.update_user(user_id=user_id, patch=patch)

    @staticmethod
    def resolve_user_names(user_ids: List[str]) -> Dict[str, str]:
        return Storage.resolve_user_names(user_ids)
