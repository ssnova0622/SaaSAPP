"""Staff CRUD storage."""
from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Dict, List, Optional

from app.helpers.date_utils import utcnow
from app.services.db import staff_collection


class StaffStorage:
    @classmethod
    def create_staff(
            cls,
            tenant: str,
            name: str,
            role: str,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            skills: Optional[List[str]] = None,
            active: bool = True,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = staff_collection()
        if not tenant or not (name or "").strip() or not (role or "").strip():
            raise ValueError("tenant, name and role are required")
        now = utcnow()
        doc = {
            "tenant": tenant,
            "id": str(uuid.uuid4()),
            "name": name.strip(),
            "role": role.strip(),
            "phone": (phone or "").strip() or None,
            "email": (email or "").strip() or None,
            "skills": [s.strip() for s in (skills or []) if isinstance(s, str) and s.strip()],
            "active": bool(active),
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
        }
        col.insert_one(doc)
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def get_staff(cls, tenant: str, staff_id: str) -> Optional[Dict[str, Any]]:
        col = staff_collection()
        doc = col.find_one({"tenant": tenant, "id": staff_id}, {"_id": 0})
        return dict(doc) if doc else None

    @classmethod
    def list_staff(
            cls,
            tenant: str,
            search: Optional[str] = None,
            role: Optional[str] = None,
            active: Optional[bool] = None,
            page: int = 1,
            size: int = 50,
    ) -> Dict[str, Any]:
        col = staff_collection()
        q: Dict[str, Any] = {"tenant": tenant}
        if search:
            q["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"role": {"$regex": search, "$options": "i"}},
                {"phone": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]
        if role:
            q["role"] = role
        if active is not None:
            q["active"] = bool(active)
        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size
        total = col.count_documents(q)
        items = [dict(d) for d in col.find(q, {"_id": 0}).sort("name", 1).skip(skip).limit(size)]
        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def update_staff(
            cls,
            tenant: str,
            staff_id: str,
            updates: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = staff_collection()
        allowed = {"name", "role", "phone", "email", "skills", "active"}
        payload = {k: v for k, v in (updates or {}).items() if k in allowed}
        if not payload:
            doc = col.find_one({"tenant": tenant, "id": staff_id}, {"_id": 0})
            if not doc:
                raise ValueError("Staff not found")
            return dict(doc)
        if "name" in payload and isinstance(payload["name"], str):
            payload["name"] = payload["name"].strip()
        if "role" in payload and isinstance(payload["role"], str):
            payload["role"] = payload["role"].strip()
        if "phone" in payload and isinstance(payload["phone"], str):
            payload["phone"] = payload["phone"].strip() or None
        if "email" in payload and isinstance(payload["email"], str):
            payload["email"] = payload["email"].strip() or None
        if "skills" in payload and isinstance(payload["skills"], list):
            payload["skills"] = [str(s).strip() for s in payload["skills"] if str(s).strip()]
        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id
        res = col.update_one({"tenant": tenant, "id": staff_id}, {"$set": payload})
        if res.matched_count == 0:
            raise ValueError("Staff not found")
        doc = col.find_one({"tenant": tenant, "id": staff_id}, {"_id": 0})
        return dict(doc or {})

    @classmethod
    def delete_staff(cls, tenant: str, staff_id: str, user_id: Optional[str] = None) -> bool:
        col = staff_collection()
        res = col.delete_one({"tenant": tenant, "id": staff_id})
        return res.deleted_count > 0
