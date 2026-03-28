# app/services/core/customer_service.py
from __future__ import annotations

import csv
import datetime as dt
import re
from io import StringIO
from typing import Optional, Dict, Any, List, Tuple

from app.services.db import customers_collection
from app.helpers.phone_utils import normalize_phone
from app.repositories.customer_repository import CustomerRepository
from .tenant_service import TenantService
from .user_service import UserService
from ...helpers.date_utils import utcnow

customer_repo = CustomerRepository()


class CustomerService:
    """
    Customer management service:
    - Listing with filters & pagination
    - Upsert & activation
    - Timeseries analytics
    - CSV import
    """

    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 200
    DEFAULT_TIMESERIES_DAYS = 30

    # ----------------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------------

    @staticmethod
    def _col():
        return customers_collection()

    @staticmethod
    def _normalize_phone(tenant: str, phone: str) -> str:
        cc = TenantService._get_tenant_country_code(tenant)
        return normalize_phone(phone, country_code=cc)

    @staticmethod
    def _compile_search(search: str) -> re.Pattern:
        return re.compile(re.escape(search), re.IGNORECASE)

    @staticmethod
    def _paginate(items: List[Any], page: int, size: int) -> Tuple[List[Any], int]:
        size = max(1, min(size or CustomerService.DEFAULT_PAGE_SIZE, CustomerService.MAX_PAGE_SIZE))
        page = max(1, int(page or 1))
        total = len(items)
        start = (page - 1) * size
        return items[start:start + size], total

    @staticmethod
    def _resolve_user_names(items: List[Dict[str, Any]]) -> None:
        user_ids = {
                       c.get("created_by")
                       for c in items
                       if c.get("created_by")
                   } | {
                       c.get("updated_by")
                       for c in items
                       if c.get("updated_by")
                   }

        if not user_ids:
            return

        name_map = UserService.resolve_user_names(list(user_ids)) or {}

        for c in items:
            c["created_by"] = name_map.get(c.get("created_by")) or c.get("created_by") or "system"
            c["updated_by"] = name_map.get(c.get("updated_by")) or c.get("updated_by") or "-"

    @staticmethod
    def _parse_tags(raw: Any) -> List[str]:
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(t).strip() for t in raw if str(t).strip()]
        if isinstance(raw, str):
            return [t.strip() for t in raw.split(",") if t.strip()]
        return []

    # ----------------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------------

    @staticmethod
    def list_customers(
            tenant: str,
            search: Optional[str] = None,
            tag: Optional[str] = None,
            active: Optional[bool] = None,
            page: int = 1,
            size: int = DEFAULT_PAGE_SIZE,
    ) -> Dict[str, Any]:
        """
        List customers with optional filters and pagination.
        """
        customers = customer_repo.list_by_tenant(tenant)

        # Filter by active
        if active is not None:
            customers = [c for c in customers if c.active == active]

        # Filter by tag
        if tag:
            customers = [c for c in customers if tag in (c.tags or [])]

        # Search filter
        if search:
            pattern = CustomerService._compile_search(search)
            customers = [
                c for c in customers
                if pattern.search(c.name or "")
                   or pattern.search(c.phone or "")
                   or (c.email and pattern.search(c.email))
            ]

        # Pagination
        items = [c.dict() for c in customers]
        page_items, total = CustomerService._paginate(items, page, size)

        # Resolve user names
        CustomerService._resolve_user_names(page_items)

        return {
            "items": page_items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
        }

    @staticmethod
    def upsert_customer(
            tenant: str,
            name: str,
            phone: str,
            email: Optional[str] = None,
            tags: Optional[List[str]] = None,
            active: Optional[bool] = None,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create or update a customer identified by phone.
        """
        phone_norm = CustomerService._normalize_phone(tenant, phone)
        col = CustomerService._col()
        now = utcnow()

        updates = {
            "name": (name or "").strip(),
            "updated_at": now,
            "updated_by": user_id,
        }

        if email:
            updates["email"] = email.strip()
        if tags is not None:
            updates["tags"] = CustomerService._parse_tags(tags)
        if active is not None:
            updates["active"] = bool(active)

        doc = col.find_one_and_update(
            {"tenant": tenant, "phone": phone_norm},
            {
                "$set": updates,
                "$setOnInsert": {"created_at": now, "created_by": user_id},
            },
            upsert=True,
            return_document=True,
        )

        if doc:
            doc.pop("_id", None)
        return dict(doc) if doc else {}

    @staticmethod
    def set_customer_active(
            tenant: str,
            phone: str,
            active: bool,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Activate or deactivate a customer.
        """
        phone_norm = CustomerService._normalize_phone(tenant, phone)
        col = CustomerService._col()

        doc = col.find_one_and_update(
            {"tenant": tenant, "phone": phone_norm},
            {
                "$set": {
                    "active": bool(active),
                    "updated_at": utcnow(),
                    "updated_by": user_id,
                }
            },
            return_document=True,
        )

        if doc:
            doc.pop("_id", None)
        return dict(doc) if doc else {}

    @staticmethod
    def customers_timeseries(
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return daily counts of newly created customers.
        """
        col = CustomerService._col()

        if from_date and to_date:
            start = dt.datetime.combine(from_date, dt.time.min)
            end = dt.datetime.combine(to_date, dt.time.max)
        else:
            d = int(days or CustomerService.DEFAULT_TIMESERIES_DAYS)
            end = utcnow()
            start = end - dt.timedelta(days=d)

        pipeline = [
            {"$match": {"tenant": tenant, "created_at": {"$gte": start, "$lte": end}}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        return [{"date": d["_id"], "count": d["count"]} for d in col.aggregate(pipeline)]

    @staticmethod
    async def import_customers(
            tenant: str,
            csv_content: str,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import customers from CSV.
        Expected columns: phone, name, email, tags
        """
        reader = csv.DictReader(StringIO(csv_content))

        inserted = updated = failed = 0
        errors: List[Dict[str, Any]] = []

        for row_index, row in enumerate(reader, start=2):
            try:
                phone_raw = str(row.get("phone", "")).strip()
                phone = CustomerService._normalize_phone(tenant, phone_raw)
                if not phone:
                    raise ValueError(f"Invalid phone: {phone_raw}")

                name = str(row.get("name", "")).strip()
                email = str(row.get("email", "")).strip() if row.get("email") else None
                tags = CustomerService._parse_tags(row.get("tags"))

                # Check if exists
                exists = CustomerService.list_customers(
                    tenant=tenant,
                    search=phone,
                    page=1,
                    size=1,
                )
                is_new = exists["total"] == 0

                CustomerService.upsert_customer(
                    tenant=tenant,
                    name=name,
                    phone=phone,
                    email=email,
                    tags=tags,
                    user_id=user_id,
                )

                inserted += 1 if is_new else 1
                if not is_new:
                    updated += 1

            except Exception as exc:
                failed += 1
                errors.append({"row": row_index, "error": str(exc)})

        return {
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "errors": errors[:20],
        }
