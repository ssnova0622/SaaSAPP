"""Bulk demo data for Store: 50+ products, categories, inventory, orders, cart recovery, low-stock AI."""
import datetime as dt
import uuid
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

# At least 50 products across Electronics, Groceries, Fashion, Home
STORE_PRODUCTS = [
    ("Phone X", "Electronics", 29999.0), ("Laptop Pro", "Electronics", 55000.0), ("Wireless Earbuds", "Electronics", 2499.0),
    ("Tablet 10", "Electronics", 18999.0), ("Smart Watch", "Electronics", 4499.0), ("Power Bank 20K", "Electronics", 1299.0),
    ("USB-C Hub", "Electronics", 1999.0), ("Monitor 24\"", "Electronics", 12999.0), ("Keyboard Wireless", "Electronics", 899.0),
    ("Mouse Wireless", "Electronics", 599.0), ("Webcam HD", "Electronics", 3499.0), ("Headphones", "Electronics", 1799.0),
    ("Speaker Bluetooth", "Electronics", 2199.0), ("Charger Fast", "Electronics", 799.0), ("Cable USB 2m", "Electronics", 299.0),
    ("Rice 5kg", "Groceries", 450.0), ("Rice 10kg", "Groceries", 850.0), ("Oil 1L", "Groceries", 180.0),
    ("Oil 5L", "Groceries", 850.0), ("Dal 1kg", "Groceries", 120.0), ("Sugar 1kg", "Groceries", 55.0),
    ("Salt 1kg", "Groceries", 25.0), ("Tea 500g", "Groceries", 200.0), ("Coffee 200g", "Groceries", 350.0),
    ("Biscuits Pack", "Groceries", 45.0), ("Milk 1L", "Groceries", 60.0), ("Bread Loaf", "Groceries", 40.0),
    ("Eggs Dozen", "Groceries", 90.0), ("Soap Bar", "Groceries", 35.0), ("Shampoo 200ml", "Groceries", 180.0),
    ("T-Shirt", "Fashion", 599.0), ("Jeans", "Fashion", 1299.0), ("Shirt Formal", "Fashion", 999.0),
    ("Saree Cotton", "Fashion", 899.0), ("Kurti", "Fashion", 649.0), ("Sneakers", "Fashion", 2499.0),
    ("Sandal", "Fashion", 499.0), ("Belt", "Fashion", 349.0), ("Socks Pack", "Fashion", 199.0),
    ("Cap", "Fashion", 299.0), ("Sunglasses", "Fashion", 799.0), ("Handbag", "Fashion", 1499.0),
    ("Wallet", "Fashion", 599.0), ("Scarf", "Fashion", 349.0), ("Tie", "Fashion", 449.0),
    ("Bed Sheet", "Home", 799.0), ("Pillow", "Home", 399.0), ("Towel Set", "Home", 599.0),
    ("Curtains Pair", "Home", 1299.0), ("Cushion", "Home", 299.0), ("Lamp LED", "Home", 449.0),
    ("Storage Box", "Home", 249.0), ("Hanger Pack", "Home", 149.0), ("Laundry Basket", "Home", 399.0),
]


def get_tenant_id() -> str:
    return "ss_business_store"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("enterprise")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()
    categories = sorted(set(p[1] for p in STORE_PRODUCTS))
    products = [
        {"tenant": tenant_id, "sku": f"STORE-{i:03d}", "name": name, "category": cat, "price": p, "mrp": p, "active": True, "unit": "pcs", "is_mock": True}
        for i, (name, cat, p) in enumerate(STORE_PRODUCTS, start=1)
    ]
    inventory = [
        {"tenant": tenant_id, "sku": f"STORE-{i:03d}", "available_qty": max(5, (i % 20) * 10), "is_mock": True}
        for i in range(1, len(products) + 1)
    ]
    orders = [
        {"tenant": tenant_id, "id": f"ORD-{uuid.uuid4().hex[:8].upper()}", "customer": {"phone": "+919876530001", "name": "Retail User 1"},
         "items": [{"sku": products[j % len(products)]["sku"], "name": products[j % len(products)]["name"], "qty": 1, "unit": "pcs", "price": products[j % len(products)]["price"]}],
         "totals": {"subtotal": products[j % len(products)]["price"]}, "fulfillment": {"mode": "pickup"}, "payment": {"method": "ONLINE", "status": "paid"},
         "status": "placed", "created_at": NOW, "updated_at": NOW, "timeline": [{"ts": NOW, "event": "placed"}], "is_mock": True}
        for j in range(15)
    ]
    return {
        "tenant_doc": {"_id": tenant_id, "plan": "enterprise", "category": "store", "owner_email": "store@ssstore.demo", "owner_phone": "+919876530001", "tz": DEFAULT_TIMEZONE, "modules": modules, "capabilities": capabilities, "active": True, "whatsapp_config": {}, "payment_config": {"provider": "dummy", "currency": "INR"}, "delivery_config": {}, "smtp_config": {}, "date_format": "DD-MM-YYYY", "ai_config": {"low_stock_days_default": 30, "low_stock_alert_days": 7, "cart_recovery_window_hours": 24}, "is_mock": True},
        "customers": [{"tenant": tenant_id, "phone": f"+9198765300{i:02d}", "name": name, "email": f"c{i}@store.demo", "tags": [], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True} for i, name in enumerate(["Retail User 1", "Retail User 2", "Retail User 3", "Retail User 4", "Retail User 5"], start=1)],
        "professionals": [],
        "services": [],
        "staff": [{"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Store Manager", "role": "receptionist", "phone": "+919876530001", "email": "mgr@ssstore.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "appointments": [],
        "categories": [{"tenant": tenant_id, "name": cat, "active": True, "is_mock": True} for cat in categories],
        "products": products,
        "inventory": inventory,
        "orders": orders,
        "promotions": [{"tenant": tenant_id, "name": "Flash Sale", "channel": "both", "message": "20% off today.", "audience": {"type": "all"}, "status": "active", "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 for products, 2 for orders."}, "enabled": True, "priority": 10, "is_mock": True}],
    }
