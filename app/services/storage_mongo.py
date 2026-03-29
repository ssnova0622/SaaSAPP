from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
import uuid
import datetime as dt
from pymongo import ReturnDocument

logger = logging.getLogger(__name__)
from zoneinfo import ZoneInfo
import hashlib
import os
import hmac

try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover
    bcrypt = None

from app.helpers.constants import (
    DEFAULT_TIMEZONE,
    USER_STATUS_ACTIVE,
)
from app.helpers.date_utils import resolve_date_window, utcnow
from app.helpers.money_format import tenant_currency
from .db import collections, get_db, customers_collection
from .storage.tenant_storage import TenantStorage
from .storage.staff_storage import StaffStorage
from .storage.service_storage import ServiceStorage
from .salon.professional_storage import ProfessionalStorage
from .storage.whatsapp_storage import WhatsAppStorage
from .storage.customer_storage import CustomerStorage
from .storage.appointment_storage import AppointmentStorage


class Storage(
    TenantStorage,
    StaffStorage,
    ServiceStorage,
    ProfessionalStorage,
    WhatsAppStorage,
    CustomerStorage,
    AppointmentStorage,
):
    """
    MongoDB-backed storage composed from domain mixins.
    Collections: tenants, professionals, appointments, customers, staff, services,
    whatsapp_menus, whatsapp_sessions, whatsapp_triggers, carts, orders, events,
    categories, products, inventory, users.
    """

    # ---------- Remaining: report, cart/orders, catalog, users (see mixins for professionals, whatsapp, customers, appointments) ----------

    # ---------- Reports aggregation ----------
    @classmethod
    def get_report_snapshot(cls, tenant: str, from_date: dt.date, to_date: Optional[dt.date] = None) -> Dict[str, Any]:
        """
        Build a snapshot for the given tenant and date range using appointments.
        Uses tenant timezone to slice the window across UTC created_at timestamps.
        If to_date is None, it defaults to from_date (single day).
        """
        tenants_col, _pros, appts_col = collections()
        tenant_doc = tenants_col.find_one({"_id": tenant}) or {}
        tz_name = tenant_doc.get("tz") or DEFAULT_TIMEZONE
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)
            tz_name = DEFAULT_TIMEZONE

        effective_to = to_date or from_date
        start_local = dt.datetime.combine(from_date, dt.time(0, 0, 0)).replace(tzinfo=tz)
        end_local = dt.datetime.combine(effective_to, dt.time(0, 0, 0)).replace(tzinfo=tz) + dt.timedelta(days=1)
        start_utc = start_local.astimezone(dt.timezone.utc)
        end_utc = end_local.astimezone(dt.timezone.utc)

        q = {"tenant": tenant, "created_at": {"$gte": start_utc, "$lt": end_utc}}
        projection = {
            "_id": 0,
            "customer_name": 1,
            "customer_phone": 1,
            "professional": 1,
            "time": 1,
            "price": 1,
            "status": 1,
            "start": 1,
        }
        rows: List[Dict[str, Any]] = []
        for d in appts_col.find(q, projection):
            customer = d.get("customer_name") or d.get("customer_phone") or ""
            price_val = float(d.get("price", 0.0))

            # If range report, include date in time for clarity
            row_time = d.get("time", "")
            if to_date and from_date != to_date:
                if d.get("start"):
                    # Localize start time
                    start_dt = d["start"].replace(tzinfo=dt.timezone.utc).astimezone(tz)
                    row_time = f"{start_dt.strftime('%Y-%m-%d')} {row_time}"

            rows.append({
                "time": row_time,
                "professional": d.get("professional", ""),
                "customer": customer,
                "price": price_val,
                "status": d.get("status", "booked"),
                "start_utc": d.get("start"),
            })

        # Sort by start_utc if available, otherwise by time string
        rows.sort(
            key=lambda r: (r.get("start_utc") or dt.datetime.min.replace(tzinfo=dt.timezone.utc), r.get("time") or ""))

        status_counts = {
            "booked": 0,
            "completed": 0,
            "canceled": 0,
            "needs_reschedule": 0,
            "blocked": 0
        }
        for r in rows:
            st = str(r.get("status", ""))
            if st in status_counts:
                status_counts[st] += 1
            else:
                status_counts[st] = status_counts.get(st, 0) + 1

        appointments_count = status_counts.get("booked", 0) + status_counts.get("completed", 0)
        cancellations_count = status_counts.get("canceled", 0)
        revenue = sum(float(r.get("price") or 0.0) for r in rows if str(r.get("status", "")) == "completed")

        # --- Store Orders & insights ---
        orders_count = 0
        store_revenue = 0.0
        units_sold = 0
        order_rows = []
        order_status_breakdown: Dict[str, int] = {}
        top_selling_today: List[Dict[str, Any]] = []
        low_stock: List[Dict[str, Any]] = []
        top_customer_today: List[Dict[str, Any]] = []
        sku_qty_today: Dict[str, Dict[str, Any]] = {}
        customer_spend_today: Dict[str, Dict[str, Any]] = {}

        modules = tenant_doc.get("modules") or []
        if "store" in modules:
            db = get_db()
            orders_col = db.get_collection("orders")
            oq = {"tenant": tenant, "created_at": {"$gte": start_utc, "$lt": end_utc}}
            for o in orders_col.find(oq):
                ostatus = str(o.get("status", "")).lower().strip() or "placed"
                order_status_breakdown[ostatus] = order_status_breakdown.get(ostatus, 0) + 1

                o_total = float(o.get("totals", {}).get("grand_total") or o.get("totals", {}).get("total", 0.0))
                if ostatus != "canceled":
                    orders_count += 1
                    store_revenue += o_total
                    c_phone = (o.get("customer") or {}).get("phone") or o.get("customer_phone") or "Guest"
                    c_name = (o.get("customer") or {}).get("name") or ""
                    key = str(c_phone).strip() or "Guest"
                    if key not in customer_spend_today:
                        customer_spend_today[key] = {"phone": c_phone, "name": c_name, "orders": 0, "total": 0.0}
                    customer_spend_today[key]["orders"] += 1
                    customer_spend_today[key]["total"] += o_total

                items = o.get("items") or []
                for it in items:
                    qty = float(it.get("qty") or 0)
                    units_sold += qty if ostatus != "canceled" else 0
                    sku = str(it.get("sku") or "").strip() or "Unknown"
                    name = str(it.get("name") or sku)
                    if ostatus != "canceled":
                        if sku not in sku_qty_today:
                            sku_qty_today[sku] = {"sku": sku, "name": name, "qty": 0.0, "revenue": 0.0}
                        sku_qty_today[sku]["qty"] += qty
                        sku_qty_today[sku]["revenue"] += qty * float(it.get("price_snapshot") or 0.0)
                        order_rows.append({
                            "product": name,
                            "qty": qty,
                            "price": float(it.get("price_snapshot") or 0.0),
                            "total": qty * float(it.get("price_snapshot") or 0.0),
                            "profit": float(it.get("profit") or 0.0),
                            "customer": (o.get("customer") or {}).get("phone") or o.get("customer_phone") or "Guest",
                            "status": ostatus,
                            "is_order": True,
                        })

            # Top selling today (by qty)
            for v in sorted(sku_qty_today.values(), key=lambda x: -x["qty"])[:10]:
                top_selling_today.append(
                    {"sku": v["sku"], "name": v["name"], "qty": v["qty"], "revenue": round(v["revenue"], 2)})
            # Top customer today (by spend)
            for k, v in sorted(customer_spend_today.items(), key=lambda kv: -kv[1]["total"])[:5]:
                top_customer_today.append({
                    "phone": v.get("phone") or k,
                    "name": v.get("name") or k,
                    "orders": v["orders"],
                    "total": round(v["total"], 2),
                })

            # Low stock: inventory with available_qty <= threshold (default 10)
            inv_col = db.get_collection("inventory")
            low_threshold = 10
            for inv in inv_col.find({"tenant": tenant, "available_qty": {"$lte": low_threshold, "$gte": 0}}):
                sku = inv.get("sku", "")
                qty = float(inv.get("available_qty", 0.0))
                low_stock.append({"sku": sku, "name": sku, "available_qty": qty})
            # Optionally enrich with product name from products collection
            if low_stock:
                prods_col = db.get_collection("products")
                for ls in low_stock:
                    p = prods_col.find_one({"tenant": tenant, "sku": ls["sku"]}, {"name": 1})
                    if p:
                        ls["name"] = p.get("name") or ls["sku"]

        return {
            "tenant": tenant,
            "category": tenant_doc.get("category"),
            "modules": modules,
            "tz": tz_name,
            "currency": tenant_currency(tenant_doc),
            "rows": rows,
            "order_rows": order_rows,
            "order_status_breakdown": order_status_breakdown,
            "top_selling_today": top_selling_today,
            "low_stock": low_stock,
            "top_customer_today": top_customer_today,
            "totals": {
                "appointments": appointments_count,
                "cancellations": cancellations_count,
                "revenue": float(revenue),
                "status_counts": status_counts,
                "orders_count": orders_count,
                "store_revenue": float(store_revenue),
                "units_sold": units_sold,
                "order_status_breakdown": order_status_breakdown,
            },
        }

    # ---------- Carts & Orders (Store) ----------
    @classmethod
    def get_cart(cls, tenant: str, phone: str) -> Dict[str, Any]:
        db = get_db()
        carts = db.get_collection("carts")
        phone = str(phone).strip()
        doc = carts.find_one({"tenant": tenant, "customer_phone": phone})
        if not doc:
            now = utcnow()
            doc = {"tenant": tenant, "customer_phone": phone, "items": [], "totals": {"subtotal": 0.0},
                   "updated_at": now, "status": "active"}
            carts.insert_one(doc)
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def _calc_totals(cls, items: List[Dict[str, Any]]) -> Dict[str, float]:
        subtotal = 0.0
        for it in items:
            try:
                qty = float(it.get("qty", 0))
                price = float(it.get("price_snapshot", 0))
            except Exception:
                qty, price = 0.0, 0.0
            subtotal += qty * price
        return {"subtotal": float(subtotal)}

    # ---------- AI & Analytics ----------
    @classmethod
    def insert_event(cls, tenant: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a generic analytics event. Minimal validation; attach server ts if missing."""
        if not tenant:
            raise ValueError("tenant is required")
        db = get_db()
        col = db.get_collection("events")
        ev_type = str((data or {}).get("type") or "").strip()
        if not ev_type:
            raise ValueError("event 'type' is required")
        ts = data.get("ts")
        if not isinstance(ts, (int, float)):
            ts = utcnow().timestamp()
        doc: Dict[str, Any] = {
            "tenant": tenant,
            "id": str(uuid.uuid4()),
            "type": ev_type,
            "ts": float(ts),
            "data": data.get("data") or {},
            "created_at": utcnow(),
        }
        col.insert_one(doc)
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def forecast_low_stock(
            cls,
            tenant: str,
            days: int = 30,
            lead_time: int = 3,
            safety_days: int = 2,
            top: int = 50,
    ) -> List[Dict[str, Any]]:
        """Compute simple low-stock forecast using moving-average demand from orders.

        - Consider non-canceled orders in the last `days`.
        - For each SKU, compute daily_demand = total_qty / days.
        - Join with current inventory to compute days_to_stockout and suggested_reorder.
        """
        if not tenant:
            raise ValueError("tenant is required")
        days = max(7, min(120, int(days or 30)))
        lead_time = max(0, min(30, int(lead_time or 0)))
        safety_days = max(0, min(30, int(safety_days or 0)))
        top = max(1, min(200, int(top or 50)))
        db = get_db()
        orders_col = db.get_collection("orders")
        products_col = db.get_collection("products")
        inventory_col = db.get_collection("inventory")

        window_start = utcnow() - dt.timedelta(days=days)
        cursor = orders_col.find({
            "tenant": tenant,
            "status": {"$ne": "canceled"},
            "created_at": {"$gte": window_start},
        }, {"items": 1})
        demand: Dict[str, float] = {}
        for doc in cursor:
            for it in (doc.get("items") or []):
                sku = str(it.get("sku") or "").strip()
                if not sku:
                    continue
                try:
                    qty = float(it.get("qty", 0))
                except Exception:
                    qty = 0.0
                if qty <= 0:
                    continue
                demand[sku] = demand.get(sku, 0.0) + qty

        # Fetch inventory for SKUs seen in demand (and a few additional from low inventory)
        skus = list(demand.keys())
        inv_map: Dict[str, float] = {}
        if skus:
            for inv in inventory_col.find({"tenant": tenant, "sku": {"$in": skus}}, {"sku": 1, "available_qty": 1}):
                inv_map[str(inv.get("sku"))] = float(inv.get("available_qty", 0.0))

        # Also include SKUs with inventory but zero demand (optional): not included to prioritize actionable items

        # Fetch product names for display
        name_map: Dict[str, str] = {}
        if skus:
            # base sku names
            for p in products_col.find({"tenant": tenant, "sku": {"$in": skus}}, {"sku": 1, "name": 1}):
                name_map[str(p.get("sku"))] = str(p.get("name") or "")
            # variant names need mapping: find docs containing variants and map matching variant_sku
            variant_docs = products_col.find({"tenant": tenant, "variants.variant_sku": {"$in": skus}},
                                             {"name": 1, "variants": 1})
            for vdoc in variant_docs:
                base_name = str(vdoc.get("name") or "")
                for v in (vdoc.get("variants") or []):
                    vs = str((v.get("variant_sku") or "")).strip()
                    if vs and vs in demand:
                        attrs = v.get("attributes") or {}
                        # Compose name with attributes for clarity
                        if isinstance(attrs, dict) and attrs:
                            kv = ", ".join([f"{k}: {attrs[k]}" for k in attrs.keys()])
                            name_map[vs] = f"{base_name} ({kv})"
                        else:
                            name_map[vs] = base_name

        results: List[Dict[str, Any]] = []
        for sku, total_qty in demand.items():
            daily = float(total_qty) / float(days)
            avail = float(inv_map.get(sku, 0.0))
            days_to_so = float('inf') if daily <= 0 else (avail / daily)
            target_days = lead_time + safety_days
            target_stock = daily * target_days
            reorder_qty = max(0.0, target_stock - avail)
            results.append({
                "sku": sku,
                "name": name_map.get(sku, sku),
                "available_qty": round(avail, 2),
                "daily_demand": round(daily, 3),
                "days_to_stockout": (9999 if days_to_so == float('inf') else round(days_to_so, 1)),
                "suggested_reorder_qty": round(reorder_qty, 2),
            })

        # Sort by ascending days_to_stockout then by highest daily demand
        results.sort(key=lambda r: (r["days_to_stockout"], -r["daily_demand"]))
        return results[:top]

    @classmethod
    def top_sellers(
            cls,
            tenant: str,
            days: int = 30,
            top: int = 20,
    ) -> List[Dict[str, Any]]:
        """Aggregate top sellers by quantity and revenue over the last `days`.
        Uses order items (non-canceled). Returns list sorted by qty desc.
        """
        if not tenant:
            raise ValueError("tenant is required")
        days = max(7, min(120, int(days or 30)))
        top = max(1, min(200, int(top or 20)))
        db = get_db()
        orders_col = db.get_collection("orders")
        products_col = db.get_collection("products")
        window_start = utcnow() - dt.timedelta(days=days)
        agg: Dict[str, Dict[str, Any]] = {}
        for d in orders_col.find({
            "tenant": tenant,
            "status": {"$ne": "canceled"},
            "created_at": {"$gte": window_start},
        }, {"items": 1}):
            for it in (d.get("items") or []):
                sku = str(it.get("sku") or "").strip()
                if not sku:
                    continue
                try:
                    qty = float(it.get("qty", 0))
                except Exception:
                    qty = 0.0
                try:
                    price = float(it.get("price_snapshot", 0))
                except Exception:
                    price = 0.0
                if qty <= 0:
                    continue
                row = agg.get(sku)
                if not row:
                    row = {"sku": sku, "qty": 0.0, "revenue": 0.0}
                    agg[sku] = row
                row["qty"] += qty
                row["revenue"] += qty * price
        # Join names
        items = list(agg.values())
        skus = [r["sku"] for r in items]
        name_map: Dict[str, str] = {}
        if skus:
            for p in products_col.find({"tenant": tenant, "sku": {"$in": skus}}, {"sku": 1, "name": 1}):
                name_map[str(p.get("sku"))] = str(p.get("name") or "")
            variant_docs = products_col.find({"tenant": tenant, "variants.variant_sku": {"$in": skus}},
                                             {"name": 1, "variants": 1})
            for vdoc in variant_docs:
                base_name = str(vdoc.get("name") or "")
                for v in (vdoc.get("variants") or []):
                    vs = str((v.get("variant_sku") or "")).strip()
                    if vs and vs in name_map:
                        continue
                    if vs and vs in skus:
                        attrs = v.get("attributes") or {}
                        if isinstance(attrs, dict) and attrs:
                            kv = ", ".join([f"{k}: {attrs[k]}" for k in attrs.keys()])
                            name_map[vs] = f"{base_name} ({kv})"
                        else:
                            name_map[vs] = base_name
        for r in items:
            r["name"] = name_map.get(r["sku"], r["sku"])
            r["qty"] = float(round(r["qty"], 2))
            r["revenue"] = float(round(r["revenue"], 2))
        items.sort(key=lambda x: (-x["qty"], -x["revenue"]))
        return items[:top]

    @classmethod
    def predictions_summary(
            cls,
            tenant: str,
            days: int = 30,
    ) -> Dict[str, Any]:
        """Compute lightweight summary counters for the Predictions page header.
        Uses existing computations to avoid heavy processing.
        """
        if not tenant:
            raise ValueError("tenant is required")
        days = max(7, min(120, int(days or 30)))
        # Low stock quick count using default params
        try:
            low_items = cls.forecast_low_stock(tenant=tenant, days=days, lead_time=3, safety_days=2, top=200)
        except Exception:
            low_items = []
        low_stock_count = len([x for x in low_items if x.get("suggested_reorder_qty", 0) > 0])
        predicted_oos_next_7d = len([x for x in low_items if
                                     isinstance(x.get("days_to_stockout"), (int, float)) and x.get("days_to_stockout",
                                                                                                   9999) <= 7])
        # Top sellers
        try:
            top = cls.top_sellers(tenant=tenant, days=days, top=5)
        except Exception:
            top = []
        top_seller_skus = [t.get("sku") for t in top]
        # Abandoned carts (approx): carts updated in last 24h with items but no corresponding order id
        db = get_db()
        carts_col = db.get_collection("carts")
        since = utcnow() - dt.timedelta(hours=24)
        try:
            abandoned = carts_col.count_documents(
                {"tenant": tenant, "updated_at": {"$gte": since}, "items.0": {"$exists": True}})
        except Exception:
            abandoned = 0
        # Anomalies placeholder
        anomaly_alerts = 0
        return {
            "tenant": tenant,
            "days": days,
            "generated_at": utcnow().isoformat(),
            "low_stock_count": int(low_stock_count),
            "predicted_oos_next_7d": int(predicted_oos_next_7d),
            "top_seller_skus": top_seller_skus,
            "abandoned_carts_24h": int(abandoned),
            "anomaly_alerts": int(anomaly_alerts),
        }

    # ---------- Reports (analytics for graphs) ----------
    @classmethod
    def sales_timeseries(
            cls,
            tenant: str,
            days: Optional[int] = None,
            interval: str = "day",
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Return per-day totals for orders and appointments (excluding canceled)."""
        if not tenant:
            raise ValueError("tenant is required")

        tenant_doc = cls.get_tenant_settings(tenant) or {}
        modules = tenant_doc.get("modules") or []
        is_store = "store" in modules
        is_service = ("salon" in modules) or ("clinic" in modules)

        window_start, window_end, days_diff = resolve_date_window(
            days or 30, from_date, to_date, min_days=7, max_days=120
        )

        db = get_db()
        buckets: Dict[str, Dict[str, float]] = {}

        # 1. Store Orders
        if is_store:
            orders_col = db.get_collection("orders")
            cur = orders_col.find({
                "tenant": tenant,
                "status": {"$ne": "canceled"},
                "created_at": {"$gte": window_start, "$lte": window_end},
            }, {"created_at": 1, "items": 1, "totals": 1})
            for doc in cur:
                created: dt.datetime = doc.get("created_at") or utcnow()
                key = (created.date()).isoformat()
                b = buckets.setdefault(key,
                                       {"orders_count": 0.0, "units": 0.0, "store_revenue": 0.0, "appts_count": 0.0,
                                        "service_revenue": 0.0})
                b["orders_count"] += 1.0
                b["store_revenue"] += float(doc.get("totals", {}).get("subtotal", 0.0))
                for it in (doc.get("items") or []):
                    b["units"] += float(it.get("qty", 0))

        # 2. Appointments
        if is_service:
            _t, _p, appts_col = collections()
            cur = appts_col.find({
                "tenant": tenant,
                "status": {"$in": ["booked", "completed"]},
                "created_at": {"$gte": window_start, "$lte": window_end},
            }, {"created_at": 1, "price": 1, "status": 1})
            for doc in cur:
                created: dt.datetime = doc.get("created_at") or utcnow()
                key = (created.date()).isoformat()
                b = buckets.setdefault(key,
                                       {"orders_count": 0.0, "units": 0.0, "store_revenue": 0.0, "appts_count": 0.0,
                                        "service_revenue": 0.0})
                b["appts_count"] += 1.0
                if doc.get("status") == "completed":
                    b["service_revenue"] += float(doc.get("price", 0.0))

        # Fill missing days with zeros
        out: List[Dict[str, Any]] = []
        end_date = to_date if to_date else utcnow().date()
        for i in range(days_diff, -1, -1):
            d = (end_date - dt.timedelta(days=i)).isoformat()
            b = buckets.get(d) or {"orders_count": 0, "units": 0, "store_revenue": 0, "appts_count": 0,
                                   "service_revenue": 0}
            out.append({
                "date": d,
                "orders_count": int(b.get("orders_count", 0)),
                "units": float(round(b.get("units", 0), 2)),
                "store_revenue": float(round(b.get("store_revenue", 0), 2)),
                "appts_count": int(b.get("appts_count", 0)),
                "service_revenue": float(round(b.get("service_revenue", 0), 2)),
                "total_revenue": float(round(b.get("store_revenue", 0) + b.get("service_revenue", 0), 2))
            })
        return out

    @classmethod
    def orders_by_status(
            cls,
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Return counts of orders grouped by status in the last N days or date range."""
        if not tenant:
            raise ValueError("tenant is required")

        window_start, window_end, _ = resolve_date_window(
            days or 30, from_date, to_date, min_days=7, max_days=120
        )

        db = get_db()
        orders_col = db.get_collection("orders")
        counts: Dict[str, int] = {}
        for doc in orders_col.find({
            "tenant": tenant,
            "created_at": {"$gte": window_start, "$lte": window_end},
        }, {"status": 1}):
            st = str(doc.get("status") or "").lower() or "unknown"
            counts[st] = counts.get(st, 0) + 1
        items = [{"status": k, "count": int(v)} for k, v in counts.items()]
        items.sort(key=lambda x: (-x["count"], x["status"]))
        return items

    @classmethod
    def category_mix(
            cls,
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Return revenue/qty by product category for the last N days or date range (excluding canceled orders)."""
        if not tenant:
            raise ValueError("tenant is required")

        if from_date and to_date:
            window_start = dt.datetime.combine(from_date, dt.time.min)
            window_end = dt.datetime.combine(to_date, dt.time.max)
        else:
            days = max(7, min(120, int(days or 30)))
            window_end = utcnow()
            window_start = window_end - dt.timedelta(days=days)

        db = get_db()
        orders_col = db.get_collection("orders")
        products_col = db.get_collection("products")
        # Aggregate per SKU from orders
        per_sku: Dict[str, Dict[str, float]] = {}
        for od in orders_col.find({
            "tenant": tenant,
            "status": {"$ne": "canceled"},
            "created_at": {"$gte": window_start, "$lte": window_end},
        }, {"items": 1}):
            for it in (od.get("items") or []):
                sku = str(it.get("sku") or "").strip()
                if not sku:
                    continue
                try:
                    qty = float(it.get("qty", 0))
                except Exception:
                    qty = 0.0
                try:
                    price = float(it.get("price_snapshot", 0))
                except Exception:
                    price = 0.0
                if qty <= 0:
                    continue
                row = per_sku.get(sku)
                if not row:
                    row = {"qty": 0.0, "revenue": 0.0}
                    per_sku[sku] = row
                row["qty"] += qty
                row["revenue"] += qty * price
        if not per_sku:
            return []
        skus = list(per_sku.keys())
        # Join categories from products (base + variants)
        cat_map: Dict[str, str] = {}
        for p in products_col.find({"tenant": tenant, "sku": {"$in": skus}}, {"sku": 1, "category": 1}):
            cat_map[str(p.get("sku"))] = str(p.get("category") or "Uncategorized")
        variant_docs = products_col.find({"tenant": tenant, "variants.variant_sku": {"$in": skus}},
                                         {"category": 1, "variants": 1})
        for vdoc in variant_docs:
            cat = str(vdoc.get("category") or "Uncategorized")
            for v in (vdoc.get("variants") or []):
                vs = str((v.get("variant_sku") or "")).strip()
                if vs and vs in skus and vs not in cat_map:
                    cat_map[vs] = cat
        # Aggregate by category
        per_cat: Dict[str, Dict[str, float]] = {}
        for sku, agg in per_sku.items():
            cat = cat_map.get(sku, "Uncategorized")
            row = per_cat.get(cat)
            if not row:
                row = {"qty": 0.0, "revenue": 0.0}
                per_cat[cat] = row
            row["qty"] += agg["qty"]
            row["revenue"] += agg["revenue"]
        total_rev = sum(v["revenue"] for v in per_cat.values()) or 1.0
        items = [
            {
                "category": c,
                "qty": float(round(v["qty"], 2)),
                "revenue": float(round(v["revenue"], 2)),
                "share_revenue": float(round((v["revenue"] / total_rev) * 100.0, 2)),
            }
            for c, v in per_cat.items()
        ]
        items.sort(key=lambda x: (-x["revenue"], x["category"]))
        return items

    @classmethod
    def customers_timeseries(
            cls,
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Return daily new vs returning customers based on orders in the last N days or date range.

        Heuristic: identify customer by phone (preferred) or email in the order's customer field if present; if not,
        fall back to customers collection's created_at to determine new vs returning within window.
        """
        if not tenant:
            raise ValueError("tenant is required")

        if from_date and to_date:
            window_start = dt.datetime.combine(from_date, dt.time.min)
            window_end = dt.datetime.combine(to_date, dt.time.max)
            days_diff = (to_date - from_date).days
        else:
            days = max(7, min(120, int(days or 30)))
            window_end = utcnow()
            window_start = window_end - dt.timedelta(days=days)
            days_diff = days

        db = get_db()
        orders_col = db.get_collection("orders")
        customers_col_ref = customers_collection()
        # Preload first-seen map from customers collection
        first_seen: Dict[str, dt.datetime] = {}
        try:
            for c in customers_col_ref.find({"tenant": tenant}, {"phone": 1, "created_at": 1}):
                ph = str(c.get("phone") or "").strip()
                if not ph:
                    continue
                cs = c.get("created_at") or utcnow()
                first_seen[ph] = cs
        except Exception:
            first_seen = {}
        buckets: Dict[str, Dict[str, int]] = {}
        for od in orders_col.find({
            "tenant": tenant,
            "created_at": {"$gte": window_start, "$lte": window_end},
        }, {"created_at": 1, "customer": 1}):
            created: dt.datetime = od.get("created_at") or utcnow()
            key = (created.date()).isoformat()
            b = buckets.get(key)
            if not b:
                b = {"new_customers": 0, "returning_customers": 0}
                buckets[key] = b
            cust = od.get("customer") or {}
            phone = str(cust.get("phone") or cust.get("customer_phone") or "").strip()
            if phone and phone in first_seen:
                if first_seen[phone].date() == created.date():
                    b["new_customers"] += 1
                else:
                    b["returning_customers"] += 1
            else:
                # If phone not found, treat as new on that day (best-effort)
                b["new_customers"] += 1
        # Fill series
        out: List[Dict[str, Any]] = []
        end_date = to_date if to_date else utcnow().date()
        for i in range(days_diff, -1, -1):
            d = (end_date - dt.timedelta(days=i)).isoformat()
            b = buckets.get(d) or {"new_customers": 0, "returning_customers": 0}
            out.append({"date": d, "new_customers": int(b["new_customers"]),
                        "returning_customers": int(b["returning_customers"])})
        return out

    @classmethod
    def sales_forecast(
            cls,
            tenant: str,
            days: int = 30,
            horizon: int = 14,
    ) -> Dict[str, Any]:
        """Naive sales forecast using moving-average demand and average price.

        - Consider non-canceled orders in the last `days`.
        - Compute daily_demand = total_qty / days.
        - Compute avg_unit_price = total_revenue / total_qty (guarded).
        - Forecast next `horizon` days as flat daily_demand and revenue = demand * avg_unit_price.

        Returns:
        { items: [{ date: 'YYYY-MM-DD', demand_units: float, revenue_estimate: float }],
          days, horizon, daily_demand, avg_unit_price }
        """
        if not tenant:
            raise ValueError("tenant is required")
        days = max(7, min(120, int(days or 30)))
        horizon = max(1, min(90, int(horizon or 14)))
        db = get_db()
        orders_col = db.get_collection("orders")
        window_start = utcnow() - dt.timedelta(days=days)
        total_qty = 0.0
        total_rev = 0.0
        for d in orders_col.find({
            "tenant": tenant,
            "status": {"$ne": "canceled"},
            "created_at": {"$gte": window_start},
        }, {"items": 1}):
            for it in (d.get("items") or []):
                try:
                    qty = float(it.get("qty", 0))
                except Exception:
                    qty = 0.0
                try:
                    price = float(it.get("price_snapshot", 0))
                except Exception:
                    price = 0.0
                if qty <= 0:
                    continue
                total_qty += qty
                total_rev += qty * price
        daily_demand = (total_qty / float(days)) if days > 0 else 0.0
        avg_unit_price = (total_rev / total_qty) if total_qty > 0 else 0.0
        # Build horizon forecast from tomorrow (UTC) over horizon days
        base_date = utcnow().date()
        items: List[Dict[str, Any]] = []
        for i in range(1, horizon + 1):
            d = base_date + dt.timedelta(days=i)
            items.append({
                "date": d.isoformat(),
                "demand_units": float(round(daily_demand, 3)),
                "revenue_estimate": float(round(daily_demand * avg_unit_price, 2)),
            })
        return {
            "items": items,
            "days": days,
            "horizon": horizon,
            "daily_demand": float(round(daily_demand, 3)),
            "avg_unit_price": float(round(avg_unit_price, 2)),
        }

    @classmethod
    def cart_recovery(
            cls,
            tenant: str,
            window_hours: int = 24,
            top: int = 10,
    ) -> Dict[str, Any]:
        """Cart recovery insights over a rolling window.

        Approximation (schema-light):
        - Consider carts updated in the last `window_hours` with non-empty items.
        - Count them as abandoned prospects (we don't have a strong linkage to converted orders here).
        - Aggregate top SKUs by quantity in those carts.
        """
        if not tenant:
            raise ValueError("tenant is required")
        window_hours = max(1, min(168, int(window_hours or 24)))
        top = max(1, min(100, int(top or 10)))
        db = get_db()
        carts_col = db.get_collection("carts")
        since = utcnow() - dt.timedelta(hours=window_hours)
        q = {"tenant": tenant, "updated_at": {"$gte": since}, "items.0": {"$exists": True}}
        total_abandoned = 0
        agg: Dict[str, float] = {}
        try:
            cur = carts_col.find(q, {"items": 1})
            for c in cur:
                total_abandoned += 1
                for it in (c.get("items") or []):
                    sku = str(it.get("sku") or "").strip()
                    if not sku:
                        continue
                    try:
                        qty = float(it.get("qty", 0))
                    except Exception:
                        qty = 0.0
                    if qty <= 0:
                        continue
                    agg[sku] = agg.get(sku, 0.0) + qty
        except Exception:
            total_abandoned = 0
            agg = {}
        # Join product names (base + variants)
        products_col = db.get_collection("products")
        skus = list(agg.keys())
        name_map: Dict[str, str] = {}
        if skus:
            for p in products_col.find({"tenant": tenant, "sku": {"$in": skus}}, {"sku": 1, "name": 1}):
                name_map[str(p.get("sku"))] = str(p.get("name") or "")
            variant_docs = products_col.find({"tenant": tenant, "variants.variant_sku": {"$in": skus}},
                                             {"name": 1, "variants": 1})
            for vdoc in variant_docs:
                base_name = str(vdoc.get("name") or "")
                for v in (vdoc.get("variants") or []):
                    vs = str((v.get("variant_sku") or "")).strip()
                    if vs and vs in skus and vs not in name_map:
                        attrs = v.get("attributes") or {}
                        if isinstance(attrs, dict) and attrs:
                            kv = ", ".join([f"{k}: {attrs[k]}" for k in attrs.keys()])
                            name_map[vs] = f"{base_name} ({kv})"
                        else:
                            name_map[vs] = base_name
        items = [{"sku": s, "name": name_map.get(s, s), "qty": float(round(q, 2))} for s, q in agg.items()]
        items.sort(key=lambda x: (-x["qty"], x["sku"]))
        return {
            "window_hours": window_hours,
            "total_abandoned": int(total_abandoned),
            "top_skus": items[:top],
        }

    @classmethod
    def professional_performance(
            cls,
            tenant: str,
            days: Optional[int] = None,
            from_date: Optional[dt.date] = None,
            to_date: Optional[dt.date] = None,
    ) -> List[Dict[str, Any]]:
        """Return performance metrics per professional."""
        if not tenant:
            raise ValueError("tenant is required")

        if from_date and to_date:
            window_start = dt.datetime.combine(from_date, dt.time.min)
            window_end = dt.datetime.combine(to_date, dt.time.max)
        else:
            days = max(7, min(120, int(days or 30)))
            window_end = utcnow()
            window_start = window_end - dt.timedelta(days=days)

        _t, _p, appts_col = collections()
        # Aggregate by professional
        agg: Dict[str, Dict[str, Any]] = {}
        cur = appts_col.find({
            "tenant": tenant,
            "created_at": {"$gte": window_start, "$lte": window_end}
        }, {"professional": 1, "status": 1, "price": 1})

        for doc in cur:
            p = str(doc.get("professional") or "Unknown")
            st = str(doc.get("status") or "")
            price = float(doc.get("price") or 0.0)

            row = agg.setdefault(p,
                                 {"professional": p, "appointments": 0, "completed": 0, "revenue": 0.0, "canceled": 0})
            row["appointments"] += 1
            if st == "completed":
                row["completed"] += 1
                row["revenue"] += price
            elif st == "canceled":
                row["canceled"] += 1

        items = list(agg.values())
        items.sort(key=lambda x: (-x["revenue"], -x["appointments"]))
        return items

    @classmethod
    def get_order(cls, tenant: str, order_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        orders = db.get_collection("orders")
        doc = orders.find_one({"tenant": tenant, "id": order_id})
        if not doc:
            return None
        out = dict(doc)
        out.pop("_id", None)
        return out

    @classmethod
    def update_order_status(cls, tenant: str, order_id: str, status: str) -> Dict[str, Any]:
        db = get_db()
        orders = db.get_collection("orders")
        allowed = {"placed", "confirmed", "picking", "ready_for_pickup", "out_for_delivery", "delivered", "canceled"}
        if status not in allowed:
            raise ValueError("Invalid status")
        # Load current order to decide inventory actions
        doc = orders.find_one({"tenant": tenant, "id": order_id})
        if not doc:
            raise ValueError("Order not found")
        current_status = str(doc.get("status") or "")

        # Prepare updates and timeline
        now = utcnow()
        set_doc: Dict[str, Any] = {"status": status, "updated_at": now}
        push_timeline: Dict[str, Any] = {"ts": now, "event": status}

        # Inventory adjustment rules (updated):
        # - Inventory is decremented on order placement (checkout_cart)
        # - On transition to canceled: if inventory was decremented, revert (increment back)
        # - Delivered and other statuses do not change inventory
        def _aggregate_items(items: List[Dict[str, Any]]) -> Dict[str, float]:
            agg: Dict[str, float] = {}
            for it in (items or []):
                sku = str(it.get("sku") or "").strip()
                if not sku:
                    continue
                try:
                    qty = float(it.get("qty", 0))
                except Exception:
                    qty = 0.0
                if qty <= 0:
                    continue
                agg[sku] = agg.get(sku, 0.0) + qty
            return agg

        def _apply_inventory_delta(sku: str, delta: float) -> float:
            # Read current qty, apply delta, block negative quantities
            inv = cls.get_inventory(tenant=tenant, sku=sku)
            cur = float(inv.get("available_qty", 0.0))
            new_qty = cur + float(delta)
            if new_qty < 0:
                raise ValueError(f"Insufficient stock for SKU '{sku}' (have {cur}, need {abs(delta)})")
            cls.set_inventory(tenant=tenant, sku=sku, qty=new_qty)
            return new_qty

        inventory_event_meta: Dict[str, Any] = {}
        inv_ledger_entries: List[Dict[str, Any]] = []
        items_agg = _aggregate_items(doc.get("items") or [])
        inv_adjusted = bool(doc.get("inventory_adjusted", False))

        if status == "canceled" and inv_adjusted:
            # Revert inventory
            per_sku_after: Dict[str, float] = {}
            for sku, qty in items_agg.items():
                after_qty = _apply_inventory_delta(sku, +qty)
                per_sku_after[sku] = after_qty
                inv_ledger_entries.append({"ts": now, "sku": sku, "qty": +qty, "direction": "revert"})
            set_doc["inventory_adjusted"] = False
            inventory_event_meta = {"action": "revert", "items": items_agg}
            update_ops = {"$set": set_doc, "$push": {"timeline": {**push_timeline, "meta": inventory_event_meta}}}
            if inv_ledger_entries:
                update_ops.setdefault("$push", {})
                update_ops["$push"]["inventory_ledger"] = {"$each": inv_ledger_entries}
            res = orders.find_one_and_update({"tenant": tenant, "id": order_id}, update_ops,
                                             return_document=ReturnDocument.AFTER)
        else:
            # Simple status change; no inventory adjustments
            res = orders.find_one_and_update({"tenant": tenant, "id": order_id},
                                             {"$set": set_doc, "$push": {"timeline": push_timeline}},
                                             return_document=ReturnDocument.AFTER)
        if not res:
            raise ValueError("Order not found")
        out = dict(res)
        out.pop("_id", None)
        return out

    @classmethod
    def set_order_payment_status(cls, tenant: str, order_id: str, status: str) -> None:
        db = get_db()
        orders = db.get_collection("orders")
        set_doc: Dict[str, Any] = {"payment.status": status, "updated_at": utcnow()}
        if status == "paid":
            set_doc["payment.paid_at"] = utcnow()
        orders.update_one({"tenant": tenant, "id": order_id}, {"$set": set_doc, "$push": {
            "timeline": {"ts": utcnow(), "event": f"payment_{status}"}}})

    @classmethod
    def update_order_items(cls, tenant: str, order_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace items on an existing order, with validation and totals recompute.
        MVP rules:
        - Editable only when status in {placed, confirmed, picking}
        - If payment.method='ONLINE' and payment.status='paid' -> block
        - Sanitize items: drop rows with empty sku or qty<=0; price_snapshot>=0
        - Recompute totals via _calc_totals, update updated_at, add timeline event 'items_updated'
        """
        db = get_db()
        orders = db.get_collection("orders")
        doc = orders.find_one({"tenant": tenant, "id": order_id})
        if not doc:
            raise ValueError("Order not found")
        status = str(doc.get("status") or "")
        editable_status = {"placed", "confirmed", "picking"}
        if status not in editable_status:
            raise ValueError(f"Order not editable in status '{status}'")
        pay = doc.get("payment") or {}
        if (str(pay.get("method") or "").upper() == "ONLINE") and (str(pay.get("status") or "").lower() == "paid"):
            raise ValueError("Order already paid online; editing items is not allowed")

        # Sanitize items
        clean: List[Dict[str, Any]] = []
        for it in (items or []):
            sku = str(it.get("sku") or "").strip()
            if not sku:
                continue
            try:
                qty = max(0.0, float(it.get("qty", 0)))
            except Exception:
                qty = 0.0
            try:
                price = max(0.0, float(it.get("price_snapshot", 0)))
            except Exception:
                price = 0.0
            if qty <= 0:
                continue
            clean.append({"sku": sku, "qty": qty, "price_snapshot": price, "name": it.get("name"),
                          "manual": bool(it.get("manual", False))})
        if not clean:
            raise ValueError("items cannot be empty")

        before_totals = cls._calc_totals(doc.get("items") or [])
        totals = cls._calc_totals(clean)
        now = utcnow()

        # If inventory was already adjusted at placement, compute per-SKU delta and apply changes
        inv_adjusted = bool(doc.get("inventory_adjusted", False))
        inv_ledger_entries: List[Dict[str, Any]] = []
        inventory_event_meta: Dict[str, Any] = {}
        update_ops: Dict[str, Any]

        if inv_adjusted:
            def _aggregate(items_list: List[Dict[str, Any]]) -> Dict[str, float]:
                agg: Dict[str, float] = {}
                for it in (items_list or []):
                    if bool(it.get("manual", False)):
                        continue
                    sku = str(it.get("sku") or "").strip()
                    if not sku:
                        continue
                    try:
                        qty = float(it.get("qty", 0))
                    except Exception:
                        qty = 0.0
                    if qty <= 0:
                        continue
                    agg[sku] = agg.get(sku, 0.0) + qty
                return agg

            old_agg = _aggregate(doc.get("items") or [])
            new_agg = _aggregate(clean)
            # Combine keys
            all_skus = set(old_agg.keys()) | set(new_agg.keys())
            # Apply deltas with negative-stock guard; collect ledger entries
            # We will first check feasibility for all decrements before applying anything for safety
            # Gather tentative operations
            ops: List[tuple[str, float]] = []  # (sku, delta)
            for sku in all_skus:
                before_q = float(old_agg.get(sku, 0.0))
                after_q = float(new_agg.get(sku, 0.0))
                delta = after_q - before_q  # positive means need to decrement more stock; negative means return stock
                if delta != 0:
                    ops.append((sku, delta))
            # Pre-check for decrements that would go negative
            for sku, delta in ops:
                if delta > 0:
                    inv = cls.get_inventory(tenant=tenant, sku=sku)
                    cur = float(inv.get("available_qty", 0.0))
                    if cur - delta < 0:
                        raise ValueError(f"Insufficient stock for SKU '{sku}' (have {cur}, need additional {delta})")
            # Apply ops
            for sku, delta in ops:
                if delta > 0:
                    # need to decrement additional delta
                    inv = cls.get_inventory(tenant=tenant, sku=sku)
                    cls.set_inventory(tenant=tenant, sku=sku, qty=float(inv.get("available_qty", 0.0)) - delta)
                    inv_ledger_entries.append({"ts": now, "sku": sku, "qty": -delta, "direction": "decrement"})
                elif delta < 0:
                    # return stock
                    inv = cls.get_inventory(tenant=tenant, sku=sku)
                    cls.set_inventory(tenant=tenant, sku=sku, qty=float(inv.get("available_qty", 0.0)) + (-delta))
                    inv_ledger_entries.append({"ts": now, "sku": sku, "qty": +(-delta), "direction": "revert"})

            if inv_ledger_entries:
                inventory_event_meta = {
                    "inventory": {
                        "action": "adjust_delta",
                        "entries": [{"sku": e["sku"], "qty": e["qty"], "direction": e["direction"]} for e in
                                    inv_ledger_entries]
                    }
                }

            update_ops = {
                "$set": {"items": clean, "totals": totals, "updated_at": now},
                "$push": {
                    "timeline": {"ts": now, "event": "items_updated",
                                 "meta": {"before_subtotal": before_totals.get("subtotal", 0.0),
                                          "after_subtotal": totals.get("subtotal", 0.0), "items_count": len(clean),
                                          **inventory_event_meta}},
                }
            }
            if inv_ledger_entries:
                update_ops["$push"]["inventory_ledger"] = {"$each": inv_ledger_entries}
        else:
            update_ops = {
                "$set": {"items": clean, "totals": totals, "updated_at": now},
                "$push": {"timeline": {"ts": now, "event": "items_updated",
                                       "meta": {"before_subtotal": before_totals.get("subtotal", 0.0),
                                                "after_subtotal": totals.get("subtotal", 0.0),
                                                "items_count": len(clean)}}}
            }

        res = orders.find_one_and_update(
            {"tenant": tenant, "id": order_id},
            update_ops,
            return_document=ReturnDocument.AFTER,
        )
        out = dict(res)
        out.pop("_id", None)
        return out

    # ---------- Catalog / Inventory ----------
    @classmethod
    def list_categories(cls, tenant: str) -> List[Dict[str, Any]]:
        db = get_db()
        col = db.get_collection("categories")
        items: List[Dict[str, Any]] = []
        for d in col.find({"tenant": tenant}).sort("name", 1):
            row = {
                "name": d.get("name"),
                "active": bool(d.get("active", True)),
                "created_by": d.get("created_by"),
                "updated_by": d.get("updated_by"),
            }
            items.append(row)
        return items

    @classmethod
    def upsert_category(cls, tenant: str, name: str, active: bool = True, user_id: Optional[str] = None) -> Dict[
        str, Any]:
        db = get_db()
        col = db.get_collection("categories")
        name = (name or "").strip()
        if not name:
            raise ValueError("Category name is required")

        now = utcnow()
        payload = {
            "tenant": tenant,
            "name": name,
            "active": bool(active),
            "updated_at": now,
            "updated_by": user_id
        }

        existing = col.find_one({"tenant": tenant, "name": name})
        if not existing:
            payload["created_at"] = now
            payload["created_by"] = user_id

        col.update_one({"tenant": tenant, "name": name}, {"$set": payload}, upsert=True)
        return {"name": name, "active": bool(active)}

    @classmethod
    def delete_category(cls, tenant: str, name: str, user_id: Optional[str] = None) -> bool:
        db = get_db()
        col = db.get_collection("categories")
        res = col.delete_one({"tenant": tenant, "name": name})
        return res.deleted_count > 0

    @classmethod
    def list_products(
            cls,
            tenant: str,
            search: Optional[str] = None,
            category: Optional[str] = None,
            active: Optional[bool] = None,
            page: int = 1,
            size: int = 50,
            flatten_variants: bool = False,
    ) -> Dict[str, Any]:
        db = get_db()
        col = db.get_collection("products")
        q: Dict[str, Any] = {"tenant": tenant}
        if search:
            q["$or"] = [
                {"sku": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}},
                {"variants.variant_sku": {"$regex": search, "$options": "i"}},
            ]
        if category:
            q["category"] = category
        if active is True:
            q["active"] = True
        elif active is False:
            q["active"] = False
        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size
        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []
        for d in col.find(q).sort("name", 1).skip(skip).limit(size):
            row = dict(d)
            row.pop("_id", None)
            row["active"] = bool(row.get("active", True))

            # Ensure unit_conversions is present in flattened variant or base row
            unit_convs = row.get("unit_conversions") or []

            if flatten_variants and row.get("variants"):
                base_price = float(row.get("price", 0.0))
                base_mrp = row.get("mrp")
                base_tax = row.get("tax")
                base_disc_t = row.get("discount_type")
                base_disc_v = row.get("discount_value")
                base_img = row.get("image_url")
                for v in (row.get("variants") or []):
                    try:
                        sku_v = str((v.get("variant_sku") or "")).strip()
                    except Exception:
                        sku_v = ""
                    if not sku_v:
                        continue
                    var_item = {
                        "tenant": tenant,
                        "sku": sku_v,
                        "name": row.get("name"),
                        "category": row.get("category"),
                        "price": float(v.get("price", base_price)) if (v.get("price") is not None) else float(
                            base_price),
                        "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else base_mrp),
                        "tax": (float(v.get("tax")) if v.get("tax") is not None else base_tax),
                        "unit": row.get("unit"),
                        "unit_conversions": unit_convs,
                        "active": bool(v.get("active", True) and row.get("active", True)),
                        "image_url": (v.get("image_url") or base_img),
                        "discount_type": (
                            v.get("discount_type") if v.get("discount_type") is not None else base_disc_t),
                        "discount_value": (
                            float(v.get("discount_value")) if v.get("discount_value") is not None else base_disc_v),
                        "attributes": (v.get("attributes") or {}),
                    }
                    items.append(var_item)
            else:
                items.append(row)
        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def upsert_product(cls, tenant: str, data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        db = get_db()
        col = db.get_collection("products")
        sku = str((data.get("sku") or "")).strip()
        name = str((data.get("name") or "")).strip()
        if not sku or not name:
            raise ValueError("sku and name are required")

        now = utcnow()
        payload: Dict[str, Any] = {
            "tenant": tenant,
            "sku": sku,
            "name": name,
            "category": (data.get("category") or None),
            "price": float(data.get("price", 0.0)),
            "mrp": float(data.get("mrp", 0.0)) if data.get("mrp") is not None else None,
            "tax": float(data.get("tax", 0.0)) if data.get("tax") is not None else None,
            "unit": (data.get("unit") or None),
            "unit_conversions": (data.get("unit_conversions") or []),
            "active": bool(data.get("active", True)),
            # Optional barcode
            "barcode": (data.get("barcode") or None),
            # New optional fields
            "image_url": (data.get("image_url") or None),
            "discount_type": (data.get("discount_type") or None),
            "discount_value": (float(data.get("discount_value")) if data.get("discount_value") is not None else None),
            "updated_at": now,
            "updated_by": user_id,
        }

        # Check if creating or updating
        existing = col.find_one({"tenant": tenant, "sku": sku})
        if not existing:
            payload["created_at"] = now
            payload["created_by"] = user_id

        # Normalize discount_type
        if payload.get("discount_type") not in (None, "amount", "percent"):
            raise ValueError("discount_type must be one of: amount, percent")
        if payload.get("discount_type") is None:
            payload["discount_value"] = None
        # Prevent base SKU collision with any existing variant_sku on another product
        conflict_vs = col.find_one({
            "tenant": tenant,
            "variants.variant_sku": sku,
            "sku": {"$ne": sku},
        })
        if conflict_vs:
            raise ValueError("SKU already exists as a variant on another product")
        # Normalize and validate variants
        variants_raw = data.get("variants")
        variant_docs: List[Dict[str, Any]] = []
        if variants_raw:
            seen_vs: set[str] = set()
            for v in (variants_raw or []):
                if not isinstance(v, dict):
                    continue
                vs = str((v.get("variant_sku") or "")).strip()
                if not vs:
                    raise ValueError("variant_sku is required for each variant")
                if vs == sku:
                    raise ValueError("variant_sku cannot be same as base sku")
                if vs in seen_vs:
                    raise ValueError(f"Duplicate variant_sku '{vs}' in payload")
                seen_vs.add(vs)
                attrs = v.get("attributes") or {}
                if not isinstance(attrs, dict) or len(attrs.keys()) == 0:
                    raise ValueError("variant.attributes must be a non-empty object")
                disc_t = v.get("discount_type")
                if disc_t not in (None, "amount", "percent"):
                    raise ValueError("variant.discount_type must be one of: amount, percent")
                variant_docs.append({
                    "variant_sku": vs,
                    "attributes": {str(k): str(attrs[k]) for k in attrs.keys()},
                    "price": (float(v.get("price")) if v.get("price") is not None else None),
                    "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else None),
                    "tax": (float(v.get("tax")) if v.get("tax") is not None else None),
                    "discount_type": disc_t,
                    "discount_value": (float(v.get("discount_value")) if v.get("discount_value") is not None else None),
                    "image_url": (v.get("image_url") or None),
                    "active": bool(v.get("active", True)),
                })
            # Enforce tenant-wide uniqueness for variant SKUs against other products
            if variant_docs:
                var_skus = [v["variant_sku"] for v in variant_docs]
                conflict = col.find_one({
                    "tenant": tenant,
                    "$or": [
                        {"sku": {"$in": var_skus}},
                        {"variants.variant_sku": {"$in": var_skus}},
                    ]
                })
                if conflict and conflict.get("sku") != sku:
                    raise ValueError("One or more variant_sku values already exist on another product")
            payload["variants"] = variant_docs
        else:
            payload["variants"] = []
        col.update_one({"tenant": tenant, "sku": sku}, {"$set": payload}, upsert=True)
        doc = col.find_one({"tenant": tenant, "sku": sku}) or payload
        out = dict(doc)
        out.pop("_id", None)
        out["active"] = bool(out.get("active", True))
        return out

    @classmethod
    def get_product_by_sku(cls, tenant: str, sku: str) -> Optional[Dict[str, Any]]:
        """Resolve a base product or a variant and return effective fields."""
        db = get_db()
        col = db.get_collection("products")
        sku_n = str((sku or "")).strip()
        if not sku_n:
            return None
        # Try base product first
        base = col.find_one({"tenant": tenant, "sku": sku_n})
        if base:
            out = dict(base)
            out.pop("_id", None)
            out["active"] = bool(out.get("active", True))
            return out
        # Try variant match
        doc = col.find_one({"tenant": tenant, "variants.variant_sku": sku_n})
        if not doc:
            return None
        row = dict(doc)
        row.pop("_id", None)
        base_price = float(row.get("price", 0.0))
        base_mrp = row.get("mrp")
        base_tax = row.get("tax")
        base_disc_t = row.get("discount_type")
        base_disc_v = row.get("discount_value")
        base_img = row.get("image_url")
        v = next((vx for vx in (row.get("variants") or []) if (vx.get("variant_sku") or "").strip() == sku_n), None)
        if not v:
            return None
        eff = {
            "tenant": tenant,
            "sku": sku_n,
            "name": row.get("name"),
            "category": row.get("category"),
            "price": float(v.get("price", base_price)) if (v.get("price") is not None) else float(base_price),
            "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else base_mrp),
            "tax": (float(v.get("tax")) if v.get("tax") is not None else base_tax),
            "unit": row.get("unit"),
            "unit_conversions": row.get("unit_conversions") or [],
            "active": bool(v.get("active", True) and row.get("active", True)),
            "image_url": (v.get("image_url") or base_img),
            "discount_type": (v.get("discount_type") if v.get("discount_type") is not None else base_disc_t),
            "discount_value": (float(v.get("discount_value")) if v.get("discount_value") is not None else base_disc_v),
        }
        return eff

    @classmethod
    def delete_product(cls, tenant: str, sku: str, user_id: Optional[str] = None) -> bool:
        db = get_db()
        col = db.get_collection("products")
        res = col.delete_one({"tenant": tenant, "sku": sku})
        return res.deleted_count > 0

    @classmethod
    def get_inventory(cls, tenant: str, sku: str) -> Dict[str, Any]:
        db = get_db()
        col = db.get_collection("inventory")
        doc = col.find_one({"tenant": tenant, "sku": sku})
        qty = float(doc.get("available_qty", 0.0)) if doc else 0.0
        return {"sku": sku, "available_qty": qty}

    @classmethod
    def set_inventory(cls, tenant: str, sku: str, qty: float, user_id: Optional[str] = None) -> Dict[str, Any]:
        db = get_db()
        col = db.get_collection("inventory")
        now = utcnow()
        update_doc = {
            "$set": {
                "tenant": tenant,
                "sku": sku,
                "available_qty": float(qty),
                "updated_at": now,
                "updated_by": user_id
            },
            "$setOnInsert": {
                "created_at": now,
                "created_by": user_id
            }
        }
        col.update_one({"tenant": tenant, "sku": sku}, update_doc, upsert=True)
        return {"sku": sku, "available_qty": float(qty)}

    # ---------- Users & Auth ----------
    @staticmethod
    def _users_col():
        db = get_db()
        col = db.get_collection("users")
        # indexes
        from pymongo import ASCENDING
        col.create_index([("email", ASCENDING)], unique=True)
        col.create_index([("tenant", ASCENDING), ("role", ASCENDING)])
        return col

    @classmethod
    def _hash_password(cls, password: str) -> str:
        pw = (password or "").encode("utf-8")
        if bcrypt is not None:
            return bcrypt.hashpw(pw, bcrypt.gensalt(12)).decode("utf-8")
        # Fallback: salted sha256 (dev only)
        salt = os.urandom(16)
        digest = hashlib.sha256(salt + pw).hexdigest()
        return f"sha256${salt.hex()}${digest}"

    @classmethod
    def _verify_password(cls, password: str, password_hash: str) -> bool:
        if not password_hash:
            return False
        pw = (password or "").encode("utf-8")
        # PBKDF2 format (e.g. from UserService / scripts): "digest:salt"
        if ":" in password_hash and "$" not in password_hash:
            try:
                digest, salt_hex = password_hash.split(":", 1)
                salt = bytes.fromhex(salt_hex)
                check = hashlib.pbkdf2_hmac("sha256", pw, salt, 100000).hex()
                return hmac.compare_digest(digest, check)
            except Exception:
                return False
        if bcrypt is not None and not password_hash.startswith("sha256$"):
            try:
                return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
            except Exception:
                return False
        # sha256$salt$digest fallback
        try:
            algo, salt_hex, digest = password_hash.split("$", 2)
            if algo != "sha256":
                return False
            calc = hashlib.sha256(bytes.fromhex(salt_hex) + pw).hexdigest()
            return hmac.compare_digest(calc, digest)
        except Exception:
            return False

    @classmethod
    def create_user(
            cls,
            email: str,
            password: str,
            role: str,
            tenant: Optional[str] = None,
            display_name: Optional[str] = None,
            phone: Optional[str] = None,
            caps: Optional[List[str]] = None,
            status: str = USER_STATUS_ACTIVE,
    ) -> Dict[str, Any]:
        col = cls._users_col()
        email_n = (email or "").strip().lower()
        if not email_n or not password or role not in {"super_admin", "tenant_admin", "staff"}:
            raise ValueError("Invalid user payload")
        if role in {"tenant_admin", "staff"} and not (tenant or "").strip():
            raise ValueError("tenant is required for tenant_admin/staff")
        now = utcnow()
        doc = {
            "email": email_n,
            "password_hash": cls._hash_password(password),
            "role": role,
            "tenant": (tenant or None),
            "display_name": (display_name or ""),
            "phone": (phone or "").strip() or None,
            "caps": [str(c).lower() for c in (caps or [])],
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
        try:
            col.insert_one(doc)
        except Exception as e:
            from pymongo.errors import DuplicateKeyError
            if isinstance(e, DuplicateKeyError):
                raise ValueError("A user with this email already exists. Email must be unique across the application.")
            raise
        out = dict(doc)
        out["id"] = str(out.pop("_id")) if out.get("_id") else None
        return out

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[Dict[str, Any]]:
        col = cls._users_col()
        doc = col.find_one({"email": (email or "").strip().lower()})
        if not doc:
            return None
        out = dict(doc)
        out["id"] = str(out.pop("_id")) if out.get("_id") else None
        return out

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[Dict[str, Any]]:
        from bson import ObjectId
        col = cls._users_col()
        try:
            doc = col.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        if not doc:
            return None
        out = dict(doc)
        out["id"] = str(out.pop("_id")) if out.get("_id") else None
        return out

    @classmethod
    def update_user(cls, user_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        from bson import ObjectId
        col = cls._users_col()
        payload: Dict[str, Any] = {}
        for k in ["email", "role", "tenant", "display_name", "status", "phone"]:
            if k in patch:
                payload[k] = patch[k]
        if "password" in patch and patch["password"]:
            payload["password_hash"] = cls._hash_password(str(patch["password"]))
        if "caps" in patch:
            payload["caps"] = [str(c).lower() for c in (patch.get("caps") or [])]
        if not payload:
            raise ValueError("Empty update")
        payload["updated_at"] = utcnow()
        try:
            doc = col.find_one_and_update({"_id": ObjectId(user_id)}, {"$set": payload},
                                          return_document=ReturnDocument.AFTER)
        except Exception:
            raise
        if not doc:
            raise ValueError("User not found")
        out = dict(doc)
        out["id"] = str(out.pop("_id")) if out.get("_id") else None
        return out

    @classmethod
    def verify_user_password(cls, email: str, password: str) -> Optional[Dict[str, Any]]:
        u = cls.get_user_by_email(email)
        if not u or str(u.get("status", USER_STATUS_ACTIVE)) != USER_STATUS_ACTIVE:
            return None
        if not cls._verify_password(password, str(u.get("password_hash") or "")):
            return None
        return u

    @classmethod
    def list_users(
            cls,
            tenant: Optional[str] = None,
            role: Optional[str] = None,
            search: Optional[str] = None,
            page: int = 1,
            size: int = 50,
    ) -> Dict[str, Any]:
        col = cls._users_col()
        q: Dict[str, Any] = {}
        if tenant:
            q["tenant"] = tenant
        if role:
            q["role"] = role
        if search:
            q["$or"] = [
                {"email": {"$regex": search, "$options": "i"}},
                {"display_name": {"$regex": search, "$options": "i"}},
                {"role": {"$regex": search, "$options": "i"}},
            ]
        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size
        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []
        for d in col.find(q).sort("email", 1).skip(skip).limit(size):
            row = dict(d)
            row["id"] = str(row.pop("_id")) if row.get("_id") else None
            row.pop("password_hash", None)
            items.append(row)
        return {"items": items, "total": total, "page": page, "size": size}

    @classmethod
    def resolve_user_names(cls, user_ids: List[str]) -> Dict[str, str]:
        """Resolve a list of user IDs (emails or MongoDB ObjectIds) to their display names."""
        if not user_ids:
            return {}

        from bson import ObjectId
        col = cls._users_col()

        # We need to handle both emails and ObjectIds since created_by/updated_by
        # might be either depending on how they were set (usually email from get_current_user)

        emails = []
        object_ids = []
        for uid in set(user_ids):
            if not uid: continue
            uid_str = str(uid).strip()
            if "@" in uid_str:
                emails.append(uid_str.lower())
            else:
                try:
                    object_ids.append(ObjectId(uid_str))
                except Exception:
                    # Not an ObjectId, might be a random string or 'system'
                    emails.append(uid_str)

        query: Dict[str, Any] = {"$or": []}
        if emails:
            query["$or"].append({"email": {"$in": emails}})
        if object_ids:
            query["$or"].append({"_id": {"$in": object_ids}})

        if not query["$or"]:
            return {}

        mapping = {}
        for doc in col.find(query, {"email": 1, "display_name": 1}):
            name = doc.get("display_name") or doc.get("email")
            if doc.get("email"):
                mapping[doc["email"]] = name
            # Also map the ObjectId string
            mapping[str(doc["_id"])] = name

        # Ensure special IDs are handled
        if "WhatsApp" in user_ids and "WhatsApp" not in mapping:
            mapping["WhatsApp"] = "WhatsApp"

        return mapping
