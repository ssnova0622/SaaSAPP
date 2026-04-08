# app/services/core/customer_service.py
from __future__ import annotations

import csv
import datetime as dt
import logging
import re
from io import StringIO
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

from app.services.db import customers_collection
from app.helpers.phone_util import PhoneUtil
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
    def _dial(tenant: str) -> str:
        return TenantService._get_tenant_country_code(tenant) or PhoneUtil.DEFAULT_DIAL_DIGITS

    @staticmethod
    def _prepare_phone(tenant: str, phone: str) -> Dict[str, str]:
        dial = CustomerService._dial(tenant)
        return PhoneUtil.from_raw(phone, dial)

    @staticmethod
    def _compile_search(search: str) -> re.Pattern:
        # Collapse multiple whitespace chars to a single space so "foo  bar" matches "foo bar"
        normalized = re.sub(r'\s+', ' ', (search or '').strip())
        if not normalized:
            return re.compile(r'(?!)', re.IGNORECASE)  # never-match sentinel
        tokens = normalized.split(' ')
        # Allow one-or-more whitespace between tokens so spaces in query match any spacing in value
        pattern_str = r'\s+'.join(re.escape(t) for t in tokens if t)
        return re.compile(pattern_str, re.IGNORECASE)

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
        raw_list = customer_repo.list_dicts_by_tenant(tenant)
        dial = CustomerService._dial(tenant)

        search_pattern = CustomerService._compile_search(search) if search else None

        customers: List[Dict[str, Any]] = []
        for d in raw_list:
            row = PhoneUtil.enrich_document(d, tenant_dial_digits=dial, phone_field="phone_number", legacy_plain_field="phone")
            active_ok = row.get("active", True)
            if active is not None and bool(active_ok) != active:
                continue
            if tag and tag not in (row.get("tags") or []):
                continue
            if search_pattern:
                e164 = PhoneUtil.to_e164(row.get("phone_number") or {})
                # Also match against just the national number digits (e.g. "9876543210")
                national = (row.get("phone_number") or {}).get("number") or ""
                # Also match against the legacy flat phone string stored in the original DB doc
                legacy_phone = d.get("phone") or ""
                if not (
                    search_pattern.search(row.get("name") or "")
                    or (e164 and search_pattern.search(e164))
                    or (national and search_pattern.search(national))
                    or (legacy_phone and search_pattern.search(legacy_phone))
                    or (row.get("email") and search_pattern.search(row["email"]))
                ):
                    continue
            customers.append(row)

        items = customers
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
        try:
            phone_struct = CustomerService._prepare_phone(tenant, phone)
        except ValueError as e:
            raise ValueError(str(e)) from e
        col = CustomerService._col()
        now = utcnow()
        flt = PhoneUtil.customer_filter(tenant, phone_struct)

        updates = {
            "name": (name or "").strip(),
            "phone_number": phone_struct,
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
            flt,
            {
                "$set": updates,
                "$unset": {"phone": ""},
                "$setOnInsert": {"created_at": now, "created_by": user_id},
            },
            upsert=True,
            return_document=True,
        )

        if doc:
            doc.pop("_id", None)
        out = dict(doc) if doc else {}
        return PhoneUtil.enrich_document(out, tenant_dial_digits=CustomerService._dial(tenant), phone_field="phone_number", legacy_plain_field="phone")

    @staticmethod
    def ensure_customer_if_absent(
            tenant: str,
            name: str,
            phone: str,
            email: Optional[str] = None,
            user_id: Optional[str] = None,
    ) -> None:
        """
        If no customer row exists for this tenant + normalized phone, insert one.
        Does not update existing rows (avoids duplicate customers for +91… / 91… / local digits).
        """
        try:
            struct = CustomerService._prepare_phone(tenant, phone)
        except ValueError:
            return
        e164 = PhoneUtil.to_e164(struct)
        digits = re.sub(r"\D", "", e164)
        if not e164 or len(digits) < 7:
            return
        col = CustomerService._col()
        now = utcnow()
        flt = PhoneUtil.customer_filter(tenant, struct)
        on_insert: Dict[str, Any] = {
            "tenant": tenant,
            "phone_number": struct,
            "name": (name or "").strip() or "Customer",
            "active": True,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "updated_by": user_id,
            "tags": [],
            "no_show_count": 0,
        }
        if email and str(email).strip():
            on_insert["email"] = str(email).strip()
        try:
            col.update_one(
                flt,
                {"$setOnInsert": on_insert, "$unset": {"phone": ""}},
                upsert=True,
            )
        except Exception as e:
            logger.warning("ensure_customer_if_absent failed tenant=%s phone=%s: %s", tenant, e164, e)

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
        try:
            struct = CustomerService._prepare_phone(tenant, phone)
        except ValueError:
            return {}
        col = CustomerService._col()
        flt = PhoneUtil.customer_filter(tenant, struct)

        doc = col.find_one_and_update(
            flt,
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
        out = dict(doc) if doc else {}
        return PhoneUtil.enrich_document(out, tenant_dial_digits=CustomerService._dial(tenant), phone_field="phone_number", legacy_plain_field="phone") if out else {}

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
    def import_customers_csv(
            tenant: str,
            csv_content: str,
            user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import customers from CSV.
        Expected columns: phone (required), name, email, tags. Headers are matched case-insensitively.
        """
        reader = csv.DictReader(StringIO(csv_content))

        inserted = updated = failed = 0
        errors: List[Dict[str, Any]] = []
        col = CustomerService._col()

        for row_index, row in enumerate(reader, start=2):
            try:
                row_norm = {(k or "").strip().lower(): v for k, v in (row or {}).items() if k}
                phone_raw = str(row_norm.get("phone", "")).strip()
                if not phone_raw:
                    raise ValueError("Missing phone")
                struct = CustomerService._prepare_phone(tenant, phone_raw)
                exists_before = col.find_one(PhoneUtil.customer_filter(tenant, struct)) is not None

                name = str(row_norm.get("name", "")).strip()
                email_raw = row_norm.get("email")
                email = str(email_raw).strip() if email_raw else None
                tags = CustomerService._parse_tags(row_norm.get("tags"))

                CustomerService.upsert_customer(
                    tenant=tenant,
                    name=name,
                    phone=phone_raw,
                    email=email,
                    tags=tags,
                    user_id=user_id,
                )

                if exists_before:
                    updated += 1
                else:
                    inserted += 1

            except Exception as exc:
                failed += 1
                errors.append({"row": row_index, "error": str(exc)})

        return {
            "inserted": inserted,
            "updated": updated,
            "failed": failed,
            "errors": errors[:20],
        }
