# app/services/salon/staff_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional
import re
import uuid

from pymongo import ReturnDocument

from app.helpers.date_utils import utcnow
from app.helpers.phone_util import PhoneUtil
from app.services.core.tenant_service import TenantService
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

    @staticmethod
    def _hydrate_staff_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(doc)
        pn = d.get("phone_number")
        if isinstance(pn, dict) and pn:
            d["phone"] = PhoneUtil.to_e164(pn) or d.get("phone")
        return d

    @staticmethod
    def _staff_to_api_dict(s: Any) -> Dict[str, Any]:
        d = s.model_dump() if hasattr(s, "model_dump") else s.dict()
        return StaffService._hydrate_staff_doc(d)

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

        hydrated = [StaffService._staff_to_api_dict(s) for s in staff_list]

        if search:
            pattern = re.compile(re.escape(search), re.IGNORECASE)
            hydrated = [
                s for s in hydrated
                if pattern.search(s.get("name") or "")
                   or (s.get("phone") and pattern.search(s["phone"]))
                   or (s.get("email") and pattern.search(s["email"]))
            ]

        total = len(hydrated)
        start = (page - 1) * size
        end = start + size

        slice_list = hydrated[start:end]
        items = list(slice_list)

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
            position: Optional[str] = None,
            phone: Optional[str] = None,
            email: Optional[str] = None,
            skills: Optional[List[str]] = None,
            active: bool = True,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        from app.models.staff import Staff

        tenant = _validate_required(tenant, "tenant")
        name = _validate_required(name, "name")

        now = utcnow()
        phone_struct = None
        if phone and str(phone).strip():
            dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
            phone_struct = PhoneUtil.prepare_storage(str(phone).strip(), dial)

        staff = Staff(
            tenant=tenant,
            id=str(uuid.uuid4()),
            name=name,
            role=role or "",
            position=_clean_str(position),
            phone_number=phone_struct,
            phone=None,
            email=_clean_str(email),
            skills=[s.strip() for s in (skills or []) if isinstance(s, str) and s.strip()],
            active=bool(active),
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )

        staff_repo.insert_one(staff)
        doc = StaffService._staff_to_api_dict(staff)

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

        doc = StaffService._staff_to_api_dict(staff)

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

        allowed = {"name", "role", "position", "phone", "email", "skills", "active"}
        payload = {k: v for k, v in updates.items() if k in allowed}

        if "name" in payload:
            payload["name"] = _validate_required(payload["name"], "name")
        if "position" in payload:
            payload["position"] = _clean_str(payload["position"])

        if "phone" in payload:
            raw_ph = payload.pop("phone", None)
            if raw_ph is None or (isinstance(raw_ph, str) and not str(raw_ph).strip()):
                payload["phone_number"] = None
            elif isinstance(raw_ph, str):
                dial = TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS
                payload["phone_number"] = PhoneUtil.prepare_storage(raw_ph.strip(), dial)
        if "email" in payload:
            payload["email"] = _clean_str(payload["email"])

        payload["updated_at"] = utcnow()
        payload["updated_by"] = user_id

        update_doc: Dict[str, Any] = {"$set": payload}
        if "phone_number" in payload or "phone" in (updates or {}):
            update_doc["$unset"] = {"phone": ""}

        doc = col.find_one_and_update(
            {"tenant": tenant, "id": staff_id},
            update_doc,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

        if not doc:
            raise ValueError("Staff member not found")

        doc = StaffService._hydrate_staff_doc(dict(doc))

        user_ids = {doc.get("created_by"), doc.get("updated_by")} - {None}
        user_names = UserService.resolve_user_names(list(user_ids)) if user_ids else {}

        doc["created_by"] = user_names.get(doc.get("created_by")) or doc.get("created_by") or "system"
        doc["updated_by"] = user_names.get(doc.get("updated_by")) or doc.get("updated_by") or "-"

        return doc

    # --------------------------------------------------------
    # CSV Import
    # --------------------------------------------------------

    @staticmethod
    def import_staff_csv(
            tenant: str,
            csv_content: str,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Bulk-import staff from CSV.
        Required columns: name, role.
        Optional columns: phone, email, skills, active.
        Deduplication: if a staff member with the same email already exists they are updated; otherwise a new record is created.
        Returns {inserted, updated, failed, errors[]}.
        """
        import csv
        from io import StringIO

        reader = csv.DictReader(StringIO(csv_content))

        inserted = updated = failed = 0
        errors: List[Dict[str, Any]] = []
        col = _staff_col()

        for row_index, row in enumerate(reader, start=2):
            name_raw = ""
            try:
                row_norm = {(k or "").strip().lower(): v for k, v in (row or {}).items() if k}
                name_raw = str(row_norm.get("name", "")).strip()
                role_raw = str(row_norm.get("role", "")).strip()
                if not name_raw:
                    raise ValueError("name is empty")
                if not role_raw:
                    raise ValueError("role is empty")

                email_raw = str(row_norm.get("email", "")).strip() or None
                phone_raw = str(row_norm.get("phone", "")).strip() or None
                skills_raw = str(row_norm.get("skills", "")).strip()
                skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else []
                active_val = str(row_norm.get("active", "")).strip().lower()
                active = active_val not in ("false", "0", "no", "inactive") if active_val else True

                # Dedup: update existing staff with the same email (case-insensitive)
                existing_doc = None
                if email_raw:
                    existing_doc = col.find_one(
                        {"tenant": tenant, "email": {"$regex": f"^{re.escape(email_raw)}$", "$options": "i"}},
                        {"id": 1},
                    )

                if existing_doc:
                    updates: Dict[str, Any] = {
                        "name": name_raw,
                        "role": role_raw,
                        "active": active,
                    }
                    if email_raw:
                        updates["email"] = email_raw
                    if phone_raw:
                        updates["phone"] = phone_raw
                    if skills:
                        updates["skills"] = skills
                    StaffService.update_staff(
                        tenant=tenant,
                        staff_id=str(existing_doc["id"]),
                        updates=updates,
                        user_id=user_id,
                    )
                    updated += 1
                else:
                    StaffService.create_staff(
                        tenant=tenant,
                        name=name_raw,
                        role=role_raw,
                        phone=phone_raw,
                        email=email_raw,
                        skills=skills,
                        active=active,
                        user_id=user_id,
                    )
                    inserted += 1

            except Exception as exc:
                failed += 1
                errors.append({"row": row_index, "name": name_raw, "error": str(exc)})

        return {
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "errors": errors[:20],
        }

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
