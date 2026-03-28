# app/services/salon/staff_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import uuid

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.services.core.user_service import UserService
from app.repositories.staff_repository import StaffRepository

staff_repo = StaffRepository()


# ============================================================
# DB Helpers
# ============================================================

def _staff_col():
    from app.services.db import staff_collection
    return staff_collection()


# ============================================================
# Validation Helpers
# ============================================================

def _clean_str(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    return v or None


def _validate_required(value: Optional[str], field: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


# ============================================================
# StaffService
# ============================================================

class StaffService:

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    @staticmethod
    def list_staff(
            tenant: str,
            search: Optional[str] = None,
            role: Optional[str] = None,
            active: Optional[bool] = None,
            page: int = 1,
            size: int = 50,
    ) -> Dict[str, Any]:

        staff_list = staff_repo.list_by_tenant(tenant, active)

        if role:
            staff_list = [s for s in staff_list if s.role == role]

        if search:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            staff_list = [
                s for s in staff_list
                if pattern.search(s.name)
                   or (s.phone and pattern.search(s.phone))
                   or (s.email and pattern.search(s.email))
            ]

        total = len(staff_list)
        start = (page - 1) * size
        end = start + size

        slice_list = staff_list[start:end]
        use_model_dump = hasattr(slice_list[0], "model_dump") if slice_list else False
        items = [(s.model_dump() if use_model_dump else s.dict()) for s in slice_list]

        # Resolve created_by / updated_by names
        user_ids = {
                       s.get("created_by")
                       for s in items
                       if s.get("created_by")
                   } | {
                       s.get("updated_by")
                       for s in items
                       if s.get("updated_by")
                   }

        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        for s in items:
            s["created_by"] = user_names.get(s.get("created_by")) or s.get("created_by") or "system"
            s["updated_by"] = user_names.get(s.get("updated_by")) or s.get("updated_by") or "-"

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
        }

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    @staticmethod
    def create_staff(
            tenant: str,
            name: str,
            role: str,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            skills: Optional[List[str]] = None,
            active: bool = True,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        from app.models.staff import Staff

        tenant = _validate_required(tenant, "tenant")
        name = _validate_required(name, "name")
        role = _validate_required(role, "role")

        now = utcnow()

        staff = Staff(
            tenant=tenant,
            id=str(uuid.uuid4()),
            name=name,
            role=role,
            phone=_clean_str(phone),
            email=_clean_str(email),
            skills=[s.strip() for s in (skills or []) if isinstance(s, str) and s.strip()],
            active=bool(active),
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )

        staff_repo.insert_one(staff)
        doc = staff.model_dump() if hasattr(staff, "model_dump") else staff.dict()

        # Resolve names
        user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or "-"

        return doc

    # --------------------------------------------------------
    # Get
    # --------------------------------------------------------

    @staticmethod
    def get_staff(tenant: str, staff_id: str) -> Optional[Dict[str, Any]]:
        staff = staff_repo.find_by_id(tenant, staff_id)
        if not staff:
            return None

        doc = staff.model_dump() if hasattr(staff, "model_dump") else staff.dict()

        user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or "-"

        return doc

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    @staticmethod
    def update_staff(
            tenant: str,
            staff_id: str,
            updates: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        col = _staff_col()

        allowed = {"name", "role", "phone", "email", "skills", "active"}
        payload = {k: v for k, v in updates.items() if k in allowed}

        if "name" in payload:
            payload["name"] = _validate_required(payload["name"], "name")
        if "role" in payload:
            payload["role"] = _validate_required(payload["role"], "role")

        if "phone" in payload:
            payload["phone"] = _clean_str(payload["phone"])
        if "email" in payload:
            payload["email"] = _clean_str(payload["email"])

        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id

        doc = col.find_one_and_update(
            {"tenant": tenant, "id": staff_id},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

        if not doc:
            raise ValueError("Staff member not found")

        # Resolve names (doc is a dict from find_one_and_update)
        user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or "-"

        return doc

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    @staticmethod
    def delete_staff(
            tenant: str,
            staff_id: str,
            user_id: Optional[str] = None,
    ) -> bool:

        col = _staff_col()
        res = col.delete_one({"tenant": tenant, "id": staff_id})
        return res.deleted_count > 0
