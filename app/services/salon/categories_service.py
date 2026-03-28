# app/services/salon/categories_service.py
from __future__ import annotations

# ============================================================
# Imports
# ============================================================

from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from app.helpers.audit_utils import audit_fields_for_create, audit_fields_for_update
from app.repositories.service_repository import ServiceRepository

service_repo = ServiceRepository()


# ============================================================
# DB Helpers
# ============================================================

def _services_col():
    from app.services.db import services_collection
    return services_collection()


# ============================================================
# Validation Helpers
# ============================================================

def _validate_service_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Service name must be a non-empty string")
    return name.strip()


def _validate_price(price: Any) -> float:
    try:
        return float(price or 0.0)
    except Exception:
        raise ValueError("Invalid price value")


def _validate_duration(duration: Any) -> int:
    try:
        d = int(duration or 30)
        if d <= 0:
            raise ValueError
        return d
    except Exception:
        raise ValueError("Duration must be a positive integer")


# ============================================================
# CategoriesServices
# ============================================================

class CategoriesServices:

    # --------------------------------------------------------
    # Repair
    # --------------------------------------------------------

    @staticmethod
    def repair_missing_tenants() -> int:
        """
        Backfill missing 'tenant' fields in 'services' collection.
        This is a safety measure for inconsistent legacy data.
        """
        col = _services_col()
        # Find all services where 'tenant' is missing or null
        res = col.update_many(
            {"tenant": {"$exists": False}},
            {"$set": {"tenant": "unknown"}}
        )
        return res.modified_count

    # --------------------------------------------------------
    # Create
    # --------------------------------------------------------

    @staticmethod
    def create_service(
            tenant: str,
            name: str,
            description: Optional[str] = None,
            price: float = 0.0,
            duration: int = 30,
            active: bool = True,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        name = _validate_service_name(name)

        if service_repo.find_by_name(tenant, name):
            raise ValueError(f"Service '{name}' already exists for this tenant")

        from app.models.services import ServiceOut as Service

        audit = audit_fields_for_create(user_id)
        service = Service(
            tenant=tenant,
            name=name,
            description=(description or "").strip(),
            price=_validate_price(price),
            duration=_validate_duration(duration),
            active=bool(active),
            created_at=audit["created_at"],
            updated_at=audit["updated_at"],
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        )

        service_repo.insert_one(service)
        out = service.model_dump() if hasattr(service, "model_dump") else service.dict()
        out["created_by"] = out.get("created_by") or "-"
        out["updated_by"] = out.get("updated_by") or "-"
        return out

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    @staticmethod
    def list_services(
            tenant: str,
            active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:

        services = service_repo.list_by_tenant(tenant, active)
        out = []
        for s in services:
            row = s.model_dump() if hasattr(s, "model_dump") else s.dict()
            row["created_by"] = row.get("created_by") or "-"
            row["updated_by"] = row.get("updated_by") or "-"
            out.append(row)
        return out

    # --------------------------------------------------------
    # Update
    # --------------------------------------------------------

    @staticmethod
    def update_service(
            tenant: str,
            name: str,
            body: Dict[str, Any],
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:

        col = _services_col()
        name = _validate_service_name(name)

        allowed = {"description", "price", "duration", "active", "name"}
        payload = {k: v for k, v in body.items() if k in allowed}

        if "name" in payload:
            payload["name"] = _validate_service_name(payload["name"])

        if "price" in payload:
            payload["price"] = _validate_price(payload["price"])

        if "duration" in payload:
            payload["duration"] = _validate_duration(payload["duration"])

        payload.update(audit_fields_for_update(user_id))

        updated = col.find_one_and_update(
            {"tenant": tenant, "name": name},
            {"$set": payload},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )

        if not updated:
            raise ValueError("Service not found")

        out = dict(updated)
        out["created_by"] = out.get("created_by") or "-"
        out["updated_by"] = out.get("updated_by") or "-"
        return out

    # --------------------------------------------------------
    # Delete
    # --------------------------------------------------------

    @staticmethod
    def delete_service(tenant: str, name: str) -> bool:
        col = _services_col()
        name = _validate_service_name(name)
        res = col.delete_one({"tenant": tenant, "name": name})
        return res.deleted_count > 0
