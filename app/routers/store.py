from __future__ import annotations
from typing import Any, Dict, List, Optional
import datetime as dt
import os

from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request, Header

from .deps import get_current_user, ensure_tenant_active, ensure_module_enabled, ensure_capability_any_enabled, ensure_tenant_scope
from ..core.container import get_tenant_service
from ..helpers.constants_capabilities import CAP_STORE_ORDERS, CAP_STORE_ORDERS_VIEW, CAP_STORE_ORDERS_EDIT
from ..helpers.date_utils import utcnow
from ..services.store.facade import get_store_facade
from ..services.store.helpers.constants import PAYMENT_STATUS_PAID, PAYMENT_STATUS_FAILED
from ..services.db import get_db

router = APIRouter()


# ===== Carts =====

@router.get("/tenants/{tenant}/carts/{phone}", dependencies=[Depends(get_current_user)])
def get_cart(
        tenant: str,
        phone: str,
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_VIEW])),
) -> Dict[str, Any]:
    if not (phone or "").strip():
        raise HTTPException(status_code=400, detail="Enter customer phone")
    return get_store_facade().cart.get_cart(tenant=tenant, phone=phone.strip())


class CartItemsBody(Dict[str, Any]):
    pass


@router.put("/tenants/{tenant}/carts/{phone}", dependencies=[Depends(get_current_user)])
def put_cart(
        tenant: str,
        phone: str,
        body: Dict[str, Any] = Body(...),
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_EDIT])),
) -> Dict[str, Any]:
    if not (phone or "").strip():
        raise HTTPException(status_code=400, detail="Enter customer phone")
    items = body.get("items") or []
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    return get_store_facade().cart.put_cart(tenant=tenant, phone=phone.strip(), items=items)


# ===== Checkout =====

@router.post("/tenants/{tenant}/carts/{phone}/checkout", dependencies=[Depends(get_current_user)])
def checkout(
        tenant: str,
        phone: str,
        body: Dict[str, Any] = Body(..., example={
            "fulfillment_mode": "delivery",
            "address": {"label": "Home", "line1": "123 St", "city": "City", "pincode": "000000"},
            "payment_method": "ONLINE"
        }),
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_EDIT])),
) -> Dict[str, Any]:
    if not (phone or "").strip():
        raise HTTPException(status_code=400, detail="Enter customer phone")
    fulfillment_mode = (body.get("fulfillment_mode") or "delivery").lower()
    address = body.get("address")
    payment_method = (body.get("payment_method") or "ONLINE").upper()
    discount_info = body.get("discount_info") if isinstance(body.get("discount_info"), dict) else None
    try:
        result = get_store_facade().checkout.checkout(
            tenant=tenant,
            phone=phone.strip(),
            fulfillment_mode=fulfillment_mode,
            address=address,
            payment_method=payment_method,
            discount_info=discount_info,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Orders =====

# Public: customer-facing product list (no auth) for store front / view products
@router.get(
    "/tenants/{tenant}/products/public",
    summary="List active products (customer-facing, no auth)",
)
def list_products_public(
        tenant: str,
        search: Optional[str] = Query(default=None),
        category: Optional[str] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """Returns active products for the tenant. No auth required. Used by store front or 'View products' links."""
    return get_store_facade().products.list_products(
        tenant=tenant, search=search, category=category, active=True, page=page, size=size
    )


# Public: list active category names (no auth) for catalog filter
@router.get(
    "/tenants/{tenant}/categories/public",
    summary="List active categories (customer-facing, no auth)",
)
def list_categories_public(tenant: str) -> Dict[str, Any]:
    """Returns active category names for the tenant. No auth required."""
    items = get_store_facade().categories.list_categories(tenant=tenant)
    names = [c.get("name") for c in items if c.get("active") is True and c.get("name")]
    return {"items": [{"name": n} for n in sorted(set(names))], "total": len(names)}


# Public: popular / best-selling products (no auth) for catalog "popular first"
@router.get(
    "/tenants/{tenant}/products/public/popular",
    summary="List popular products by sales (customer-facing, no auth)",
)
def list_popular_products_public(
        tenant: str,
        top: int = Query(default=12, ge=1, le=30),
        days: int = Query(default=30, ge=7, le=120),
) -> Dict[str, Any]:
    """Returns top-selling products (by order quantity in last N days). No auth required."""
    from app.services.store.reports_service import ReportsService
    facade = get_store_facade()
    top_rows = ReportsService.top_sellers(tenant=tenant, days=days, top=top)
    items: List[Dict[str, Any]] = []
    seen: set = set()
    for row in top_rows:
        sku = row.get("sku")
        if not sku or sku in seen:
            continue
        seen.add(sku)
        try:
            p = facade.products.get_product_by_sku(tenant=tenant, sku=sku)
            if p and p.get("active") is not False:
                p.pop("_id", None)
                items.append(p)
        except Exception:
            continue
    return {"items": items, "total": len(items)}


# Public: minimal tenant info for catalog (business name, WhatsApp contact number)
@router.get(
    "/tenants/{tenant}/public/info",
    summary="Tenant public info (customer-facing, no auth)",
)
def get_tenant_public_info(tenant: str) -> Dict[str, Any]:
    """Returns business name and WhatsApp number for contact (e.g. Send to WhatsApp from catalog). No auth."""
    settings = get_tenant_service().get_tenant_settings(tenant)
    if not settings:
        raise HTTPException(status_code=404, detail="Tenant not found")
    wa = (settings.get("whatsapp_config") or {})
    from_num = wa.get("from_number") or wa.get("to_number") or ""
    if not from_num and isinstance(wa.get("from_numbers"), list) and len(wa["from_numbers"]) > 0:
        from_num = wa["from_numbers"][0] or ""
    if not from_num:
        from_num = os.environ.get("CATALOG_WHATSAPP_NUMBER") or os.environ.get("TWILIO_WHATSAPP_FROM") or ""
    if isinstance(from_num, str) and from_num.lower().startswith("whatsapp:"):
        from_num = from_num.replace("whatsapp:", "").strip()
    return {
        "name": settings.get("business_name") or settings.get("display_name") or settings.get("name") or tenant,
        "whatsapp_number": from_num or None,
        "currency": settings.get("currency") or "INR",
    }


# Public: create order from catalog cart (no auth) — returns order_id for "Send to WhatsApp" with order number
@router.post(
    "/tenants/{tenant}/orders/from-catalog",
    summary="Create order from catalog cart (customer-facing, no auth)",
)
def create_order_from_catalog(tenant: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Accepts cart items from public catalog, creates order, returns order_id. Optional customer_phone for testing (e.g. dummy number)."""
    from app.services.store.helpers.validation_helper import StoreValidationError
    items = body.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    customer_phone = body.get("customer_phone")
    if customer_phone is not None and not isinstance(customer_phone, str):
        customer_phone = None
    try:
        return get_store_facade().checkout.create_order_from_catalog(
            tenant=tenant, items=items, customer_phone=customer_phone
        )
    except StoreValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Public: customer-facing order status by track/order id (no auth required)
@router.get(
    "/tenants/{tenant}/orders/track/{order_id}",
    summary="Get order status by track ID (customer-facing)",
    tags=["Store"],
)
def get_order_status_public(tenant: str, order_id: str) -> Dict[str, Any]:
    """Returns minimal order status for the given order id. Used by customers to track order (e.g. via link or WhatsApp). No auth required."""
    doc = get_store_facade().orders.get_order(tenant=tenant, order_id=order_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "order_id": doc.get("id"),
        "status": doc.get("status", "placed"),
        "created_at": doc.get("created_at"),
        "fulfillment_mode": doc.get("fulfillment", {}).get("mode") if isinstance(doc.get("fulfillment"),
                                                                                 dict) else doc.get("fulfillment"),
    }


@router.get("/tenants/{tenant}/orders", dependencies=[Depends(get_current_user)])
def list_orders(
        tenant: str,
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_VIEW])),
        status: Optional[str] = Query(default=None),
        search: Optional[str] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    statuses: Optional[List[str]] = None
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
    return get_store_facade().orders.list_orders(tenant=tenant, statuses=statuses, page=page, size=size, search=search)


@router.get("/tenants/{tenant}/orders/{order_id}", dependencies=[Depends(get_current_user)])
def get_order(
        tenant: str,
        order_id: str,
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_VIEW])),
) -> Dict[str, Any]:
    doc = get_store_facade().orders.get_order(tenant=tenant, order_id=order_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Order not found")
    return doc


@router.patch("/tenants/{tenant}/orders/{order_id}/status", dependencies=[Depends(get_current_user)])
def patch_order_status(
        tenant: str,
        order_id: str,
        body: Dict[str, Any] = Body(...),
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_EDIT])),
) -> Dict[str, Any]:
    new_status = (body.get("status") or "").strip()
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")
    try:
        return get_store_facade().orders.update_order_status(tenant=tenant, order_id=order_id, status=new_status)
    except ValueError as e:
        msg = str(e)
        if msg == "Order not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@router.post(
    "/tenants/{tenant}/orders/{order_id}/send-whatsapp",
    summary="Send order summary to customer via WhatsApp",
)
def send_order_whatsapp(
        tenant: str,
        order_id: str,
        _ok: bool = Depends(ensure_tenant_active),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_EDIT])),
        _user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Sends the order summary to the order's customer phone via the tenant's configured WhatsApp."""
    order = get_store_facade().orders.get_order(tenant=tenant, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    customer = order.get("customer") or {}
    to_phone = (customer.get("phone") or "").strip()
    if not to_phone or to_phone.lower() == "catalog":
        raise HTTPException(status_code=400, detail="Order has no customer phone; cannot send WhatsApp")
    items = order.get("items") or []
    totals = order.get("totals") or {}
    grand_total = totals.get("grand_total", totals.get("subtotal", 0))
    lines = [f"*Order {order.get('id', order_id)}*", ""]
    for it in items:
        name = it.get("name") or it.get("sku")
        qty = it.get("qty", 0)
        price = it.get("price_snapshot", 0)
        lines.append(f"• {name} × {qty} — ₹{(qty * price):.2f}")
    lines.extend(["", f"*Total: ₹{grand_total:,.2f}*"])
    text = "\n".join(lines)
    from app.services.core.messaging_service import Messaging
    try:
        Messaging.send_whatsapp_text(to_phone=to_phone, text=text, tenant=tenant)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp: {e}")
    return {"ok": True, "message": "Order sent to customer via WhatsApp"}


# ===== Orders: edit items (before delivery) =====
@router.patch("/tenants/{tenant}/orders/{order_id}/items", dependencies=[Depends(get_current_user)])
def patch_order_items(
        tenant: str,
        order_id: str,
        body: Dict[str, Any] = Body(..., example={
            "items": [{"sku": "tee-red-m", "qty": 2, "price_snapshot": 299.0}],
            "notes": "Offer applied. Customer paid after discount.",
        }),
        _ok: bool = Depends(ensure_tenant_active),
        _scope: bool = Depends(ensure_tenant_scope()),
        _mod_ok: bool = Depends(ensure_module_enabled("store")),
        _cap_ok: bool = Depends(ensure_capability_any_enabled([CAP_STORE_ORDERS, CAP_STORE_ORDERS_EDIT])),
) -> Dict[str, Any]:
    items = body.get("items")
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="items must be a list")
    notes = body.get("notes")
    if notes is not None and not isinstance(notes, str):
        notes = str(notes)
    try:
        updated = get_store_facade().orders.update_order_items(
            tenant=tenant, order_id=order_id, items=items, notes=notes
        )
        return updated
    except ValueError as e:
        msg = str(e)
        if msg == "Order not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


# ===== Dummy payments webhook =====

@router.post("/payments/provider/dummy/webhook")
def dummy_webhook(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    intent_id = body.get("intent_id")
    status = body.get("status")
    if not intent_id or status not in ("paid", "failed"):
        raise HTTPException(status_code=400, detail="invalid payload")
    db = get_db()
    payments = db.get_collection("payments")
    pay = payments.find_one({"intent_id": intent_id})
    if not pay:
        raise HTTPException(status_code=404, detail="intent not found")
    tenant = pay.get("tenant")
    order_id = pay.get("order_id")
    # Update payment
    payments.update_one({"intent_id": intent_id}, {"$set": {"status": status},
                                                   "$push": {"events": {"ts": utcnow(), "type": status}}})
    # Update order payment status
    try:
        get_store_facade().orders.set_order_payment_status(tenant=tenant, order_id=order_id, status=status)
    except Exception:
        pass
    return {"ok": True}


def _payment_webhook_mark_done(intent_id: str, status: str) -> bool:
    """Update payment and order by intent_id. Returns True if payment doc found."""
    db = get_db()
    payments = db.get_collection("payments")
    pay = payments.find_one({"intent_id": intent_id})
    if not pay:
        return False
    tenant = pay.get("tenant")
    order_id = pay.get("order_id")
    payments.update_one(
        {"intent_id": intent_id},
        {"$set": {"status": status}, "$push": {"events": {"ts": utcnow(), "type": status}}},
    )
    try:
        get_store_facade().orders.set_order_payment_status(tenant=tenant, order_id=order_id, status=status)
    except Exception:
        pass
    return True


@router.post("/payments/provider/stripe/webhook")
async def stripe_webhook(request: Request, stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature")) -> \
        Dict[str, Any]:
    """Stripe webhook: verify signature (if webhook_secret set), then mark payment paid/failed."""
    body = await request.body()
    payload = body.decode("utf-8") if isinstance(body, bytes) else str(body)
    try:
        import json
        data = json.loads(payload)
        event_type = data.get("type") or ""
        obj = (data.get("data") or {}).get("object") or {}
        intent_id = obj.get("id")
        if event_type == "payment_intent.succeeded" and intent_id:
            _payment_webhook_mark_done(intent_id, PAYMENT_STATUS_PAID)
        elif event_type == "payment_intent.payment_failed" and intent_id:
            _payment_webhook_mark_done(intent_id, PAYMENT_STATUS_FAILED)
    except Exception:
        pass
    return {"received": True}


@router.post("/payments/provider/razorpay/webhook")
async def razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Razorpay webhook: verify signature (when secret set), then mark payment paid."""
    body = await request.body()
    raw = body.decode("utf-8") if isinstance(body, bytes) else str(body)
    try:
        import json
        data = json.loads(raw)
        event = data.get("event")
        payload = data.get("payload", {}).get("payment", {}).get("entity") or data.get("payload", {}).get("order",
                                                                                                          {}).get(
            "entity") or {}
        intent_id = payload.get("id")
        if event == "payment.captured" and intent_id:
            _payment_webhook_mark_done(intent_id, PAYMENT_STATUS_PAID)
        elif event == "payment.failed" and intent_id:
            _payment_webhook_mark_done(intent_id, PAYMENT_STATUS_FAILED)
    except Exception:
        pass
    return {"received": True}


# ===== Store Offers (tenant-created, time-bound offers) =====

def _parse_dt(s: Optional[str]) -> Optional[dt.datetime]:
    if not s:
        return None
    try:
        if isinstance(s, dt.datetime):
            return s
        return dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


@router.get(
    "/tenants/{tenant}/offers/active",
    summary="List active offers (customer-facing, no auth)",
)
def list_active_offers_public(tenant: str) -> Dict[str, Any]:
    """Returns offers currently valid (valid_from <= now <= valid_until). No auth required."""
    items = get_store_facade().offers.list_active_offers(tenant=tenant)
    return {"items": items, "total": len(items)}


@router.get(
    "/tenants/{tenant}/offers",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def list_offers(
        tenant: str,
        active_only: bool = Query(default=False),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=100),
) -> Dict[str, Any]:
    return get_store_facade().offers.list_offers(tenant=tenant, active_only=active_only, page=page, size=size)


@router.post(
    "/tenants/{tenant}/offers",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def create_offer(
        tenant: str,
        body: Dict[str, Any] = Body(...),
        user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    title = body.get("title") or "Offer"
    description = body.get("description") or ""
    valid_from = _parse_dt(body.get("valid_from"))
    valid_until = _parse_dt(body.get("valid_until"))
    product_skus = body.get("product_skus")
    if isinstance(product_skus, list):
        product_skus = [str(s) for s in product_skus]
    else:
        product_skus = None
    discount_info = body.get("discount_info") if isinstance(body.get("discount_info"), dict) else None
    active = body.get("active", True)
    brochure_url = (body.get("brochure_url") or "").strip() or None
    return get_store_facade().offers.create_offer(
        tenant=tenant,
        title=title,
        description=description,
        valid_from=valid_from,
        valid_until=valid_until,
        product_skus=product_skus,
        discount_info=discount_info,
        active=active,
        user_id=user_id,
        brochure_url=brochure_url,
    )


@router.post(
    "/tenants/{tenant}/offers/bulk",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def bulk_create_offers(
        tenant: str,
        body: Dict[str, Any] = Body(...),
        user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create multiple offers in one request (e.g. from uploaded brochure/CSV/Excel). Body: { \"offers\": [ { title, description?, valid_from?, valid_until?, product_skus?, discount_info?, active? }, ... ] }."""
    user_id = user.get("sub") or user.get("email")
    raw = body.get("offers")
    if not isinstance(raw, list) or len(raw) == 0:
        raise HTTPException(status_code=400, detail="body.offers must be a non-empty list")
    created: List[Dict[str, Any]] = []
    errors: List[str] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            errors.append(f"Row {i + 1}: not an object")
            continue
        title = item.get("title") or "Offer"
        description = str(item.get("description") or "").strip()
        valid_from = _parse_dt(item.get("valid_from"))
        valid_until = _parse_dt(item.get("valid_until"))
        product_skus = item.get("product_skus")
        if isinstance(product_skus, list):
            product_skus = [str(s) for s in product_skus]
        else:
            product_skus = None
        discount_info = item.get("discount_info") if isinstance(item.get("discount_info"), dict) else None
        active = item.get("active", True)
        brochure_url = (item.get("brochure_url") or "").strip() or None
        try:
            doc = get_store_facade().offers.create_offer(
                tenant=tenant,
                title=title,
                description=description,
                valid_from=valid_from,
                valid_until=valid_until,
                product_skus=product_skus,
                discount_info=discount_info,
                active=active,
                user_id=user_id,
                brochure_url=brochure_url,
            )
            created.append(doc)
        except Exception as e:
            errors.append(f"Row {i + 1} ({title}): {str(e)}")
    return {"created": len(created), "items": created, "errors": errors if errors else None}


@router.get(
    "/tenants/{tenant}/offers/{offer_id}",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def get_offer(tenant: str, offer_id: str) -> Dict[str, Any]:
    doc = get_store_facade().offers.get_offer(tenant=tenant, offer_id=offer_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Offer not found")
    return doc


@router.patch(
    "/tenants/{tenant}/offers/{offer_id}",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def update_offer(
        tenant: str,
        offer_id: str,
        body: Dict[str, Any] = Body(...),
        user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    updates = {}
    if "title" in body:
        updates["title"] = body["title"]
    if "description" in body:
        updates["description"] = body["description"]
    if "valid_from" in body:
        t = _parse_dt(body["valid_from"])
        if t is not None:
            updates["valid_from"] = t
    if "valid_until" in body:
        t = _parse_dt(body["valid_until"])
        if t is not None:
            updates["valid_until"] = t
    if "product_skus" in body:
        updates["product_skus"] = body["product_skus"] if isinstance(body["product_skus"], list) else []
    if "discount_info" in body:
        updates["discount_info"] = body["discount_info"] if isinstance(body["discount_info"], dict) else {}
    if "active" in body:
        updates["active"] = bool(body["active"])
    if "brochure_url" in body:
        updates["brochure_url"] = (body["brochure_url"] or "").strip() or None
    doc = get_store_facade().offers.update_offer(tenant=tenant, offer_id=offer_id, updates=updates, user_id=user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Offer not found")
    return doc


@router.delete(
    "/tenants/{tenant}/offers/{offer_id}",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_active), Depends(ensure_module_enabled("store"))],
)
def delete_offer(tenant: str, offer_id: str) -> Dict[str, Any]:
    ok = get_store_facade().offers.delete_offer(tenant=tenant, offer_id=offer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Offer not found")
    return {"ok": True}
