"""
Bulk demo data for QuickMart (Online / Retail Store).
Covers: 50+ products with real images, categories, inventory,
customers, orders, promotions (WA / email / SMS), store browse
workflow, and rich WhatsApp triggers.
"""
import datetime as dt
import uuid
from typing import Any

from app.modules.plans import get_plan_defaults
from app.helpers.constants import DEFAULT_TIMEZONE

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _pn(e164: str, code: str = "+91") -> dict:
    return {"code": code, "number": e164[len(code):]}


def _prof_id(tenant: str, name: str, short_name: str) -> str:
    import re

    def slug(s: str, max_len: int) -> str:
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s[:max_len]

    sh = re.sub(r"[^a-z0-9_]", "", short_name.lower())[:20]
    return f"{slug(tenant, 48)}__{slug(name, 64)}__{sh}"

# ── Unsplash CDN images ───────────────────────────────────────────────────────
_E = "https://images.unsplash.com/photo-{id}?auto=format&fit=crop&w=400&q=80"

_IMG = {
    # Electronics
    "phone":      _E.format(id="1511707171634-5f897ff02aa9"),
    "laptop":     _E.format(id="1496181133206-80ce9b88a853"),
    "earbuds":    _E.format(id="1590658268037-6bf12165a8df"),
    "smartwatch": _E.format(id="1523275335684-37898b6baf30"),
    "tablet":     _E.format(id="1544244015-0df4b3ffc6b0"),
    "powerbank":  _E.format(id="1585771724684-38269d6639fd"),
    "monitor":    _E.format(id="1527443224154-c4a3942d3acf"),
    "keyboard":   _E.format(id="1587829741301-dc798b83add3"),
    "mouse":      _E.format(id="1605773527852-c546a8584ea3"),
    "headphones": _E.format(id="1505740420928-5e560c06d30e"),
    "speaker":    _E.format(id="1608043152269-423dbba4e7e1"),
    # Fashion
    "tshirt":     _E.format(id="1521572163474-6864f9cf17ab"),
    "jeans":      _E.format(id="1542272604-787c3835535d"),
    "sneakers":   _E.format(id="1542291026-7eec264c27ff"),
    "handbag":    _E.format(id="1548036161-59be4d55e3c8"),
    "sunglasses": _E.format(id="1572635196237-14b3f281503f"),
    "shirt":      _E.format(id="1596755094514-f87e34085b2c"),
    # Home
    "bed_sheet":  _E.format(id="1558618666-fcd25c85cd64"),
    "lamp":       _E.format(id="1507473885765-e6ed057f782c"),
    "cushion":    _E.format(id="1555041469-a586c61ea9bc"),
    # Grocery (generic warm/food)
    "grocery":    _E.format(id="1542838132-92702020f3f8"),
    "tea":        _E.format(id="1556679343-c7306c1976bc"),
    "coffee":     _E.format(id="1447933601652-54a0d43cc786"),
}

# (sku_suffix, name, category, price, mrp, description, image_key)
PRODUCTS_SPEC = [
    # Electronics
    ("E001", "Samsung Galaxy A55",         "Electronics", 29999, 32999,
     "6.6-inch FHD+ display, 50MP camera, 5000mAh battery. 5G ready with 8GB RAM + 128GB storage.",
     ["phone"]),
    ("E002", "HP Pavilion Laptop 15",       "Electronics", 55000, 60000,
     "Intel Core i5 12th Gen, 16GB RAM, 512GB SSD, Windows 11. 15.6-inch FHD display.",
     ["laptop"]),
    ("E003", "boAt Airdopes 141",           "Electronics",  2499,  3499,
     "True wireless earbuds with 42Hr total playback, IPX4 water-resistant, Type-C charging.",
     ["earbuds"]),
    ("E004", "Fire-Boltt Ring 3 Smartwatch","Electronics",  4499,  5999,
     "1.8-inch AMOLED display, SpO2, heart rate, 100+ sports modes, 7-day battery life.",
     ["smartwatch"]),
    ("E005", "Lenovo Tab M10 Plus",         "Electronics", 18999, 21999,
     "10.61-inch 2K display, Snapdragon 680, 4GB RAM, 128GB storage, 7700mAh.",
     ["tablet"]),
    ("E006", "Ambrane 20000mAh Power Bank", "Electronics",  1299,  1999,
     "20W fast charge, dual USB + Type-C output, LED indicator, airline-approved.",
     ["powerbank"]),
    ("E007", "LG 24-inch FHD Monitor",      "Electronics", 12999, 15499,
     "Full HD IPS panel, 75Hz, HDMI + VGA, AMD FreeSync, eye-care technology.",
     ["monitor"]),
    ("E008", "Logitech MK215 Keyboard+Mouse","Electronics",  899,  1299,
     "Wireless combo with 10-metre range, spill-resistant, 2-year battery life.",
     ["keyboard", "mouse"]),
    ("E009", "Sony WH-1000XM4 Headphones",  "Electronics",  1799,  2499,
     "Industry-leading noise cancellation, 30Hr battery, multi-device pairing.",
     ["headphones"]),
    ("E010", "JBL Flip 6 Bluetooth Speaker","Electronics",  2199,  2799,
     "IP67 waterproof, 12Hr playtime, powerful sound with dual radiators.",
     ["speaker"]),
    # Groceries
    ("G001", "India Gate Basmati Rice 5kg", "Groceries",  450,  520, "Premium aged basmati. Long grain, aromatic.", ["grocery"]),
    ("G002", "Fortune Sunflower Oil 5L",    "Groceries",  850,  950, "Refined sunflower oil, rich in Vitamin E.", ["grocery"]),
    ("G003", "Tata Tea Gold 500g",          "Groceries",  200,  230, "Blend of long and medium leaf teas for a rich cup.", ["tea"]),
    ("G004", "Nescafé Classic 200g",        "Groceries",  350,  395, "Rich pure soluble coffee. Best enjoyed hot or cold.", ["coffee"]),
    ("G005", "Aashirvaad Atta 10kg",        "Groceries",  580,  650, "Whole wheat flour with natural bran. No preservatives.", ["grocery"]),
    ("G006", "Amul Butter 500g",            "Groceries",  270,  295, "Pasteurised butter from fresh cream. Best for cooking.", ["grocery"]),
    ("G007", "Parle-G Biscuits 1kg Pack",   "Groceries",  120,  140, "India's favourite glucose biscuits. Pack of 8.", ["grocery"]),
    ("G008", "Dove Body Soap (Pack of 4)",  "Groceries",  280,  320, "Moisturising cream bar with ¼ moisturising milk.", ["grocery"]),
    ("G009", "Head & Shoulders Shampoo 400ml","Groceries", 340,  380, "Anti-dandruff shampoo with zinc pyrithione.", ["grocery"]),
    ("G010", "Colgate MaxFresh 300g x2",    "Groceries",  160,  190, "Cooling crystals toothpaste, fights bacteria 12Hr.", ["grocery"]),
    # Fashion
    ("F001", "Levis Regular Fit T-Shirt",   "Fashion",  599,  899, "100% cotton crew-neck tee. Available in 8 colours.", ["tshirt"]),
    ("F002", "Flying Machine Slim Jeans",   "Fashion", 1299, 1799, "Stretch denim, slim fit. Mid-rise, 5-pocket style.", ["jeans"]),
    ("F003", "Raymond Formal Shirt",        "Fashion",  999, 1499, "Pure cotton formal shirt. Wrinkle-resistant.", ["shirt"]),
    ("F004", "Nike Revolution 6 Sneakers",  "Fashion", 2499, 3499, "Lightweight mesh upper, foam midsole for all-day comfort.", ["sneakers"]),
    ("F005", "Caprese Sling Bag",           "Fashion", 1499, 1999, "Vegan leather sling, multiple pockets, magnetic closure.", ["handbag"]),
    ("F006", "Ray-Ban Polarised Sunglasses","Fashion",  799, 1299, "UV400 protection, polarised lens, lightweight frame.", ["sunglasses"]),
    ("F007", "Van Heusen Formal Trousers",  "Fashion",  899, 1399, "Slim fit, flat front, easy-iron poly-viscose blend.", ["shirt"]),
    ("F008", "Ladies Kurti (3-pc set)",     "Fashion",  649,  899, "Printed cotton kurtis. Sizes S–XXL available.", ["tshirt"]),
    # Home
    ("H001", "Spaces Cotton Bed Sheet (King)","Home",  799, 1099, "280 thread-count pure cotton. 1 flat sheet + 2 pillow covers.", ["bed_sheet"]),
    ("H002", "Philips LED Desk Lamp",       "Home",  449,  599, "5W warm-white LED, flexible neck, USB charging port.", ["lamp"]),
    ("H003", "Maspar Velvet Cushion (Set 5)","Home",  599,  799, "Velvet cover with PP fibre filling. Machine washable.", ["cushion"]),
    ("H004", "Milton Thermosteel Bottle 1L","Home",  699,  999, "24Hr hot / 24Hr cold. BPA-free stainless steel.", ["grocery"]),
    ("H005", "Nilkamal Foldable Storage Box","Home",  249,  349, "50L capacity. Collapsible, stackable, with lid.", ["grocery"]),
    ("H006", "Trident Towel Set (4 pcs)",   "Home",  599,  799, "400GSM quick-dry cotton. 2 bath + 2 hand towels.", ["bed_sheet"]),
]


def get_tenant_id() -> str:
    return "ss_business_store"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("enterprise")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()

    categories = sorted(set(p[2] for p in PRODUCTS_SPEC))
    products = []
    for sku_sfx, name, cat, price, mrp, desc, img_keys in PRODUCTS_SPEC:
        imgs = [_IMG.get(k, _IMG["grocery"]) for k in img_keys]
        products.append({
            "tenant": tenant_id,
            "sku": f"STORE-{sku_sfx}",
            "name": name, "category": cat,
            "price": float(price), "mrp": float(mrp),
            "active": True, "unit": "pcs",
            "description": desc,
            "image_urls": imgs,
            "image_url": imgs[0],
            "is_mock": True,
        })

    inventory = [
        {"tenant": tenant_id, "sku": f"STORE-{sfx}", "available_qty": max(5, qty), "is_mock": True}
        for (sfx, *_), qty in zip(PRODUCTS_SPEC, [
            120, 45, 200, 80, 60, 150, 30, 90, 70, 110,   # Electronics
            300, 250, 400, 350, 280, 320, 500, 420, 380, 450,  # Groceries
            180, 220, 160, 90, 70, 130, 140, 200,          # Fashion
            100, 85, 160, 120, 200, 95,                    # Home
        ])
    ]

    # 20 realistic customers
    cust_data = [
        ("Rajan Krishnaswamy", "+919876530001", "rajan@store.demo"),
        ("Pooja Mehta",         "+919876530002", "pooja@store.demo"),
        ("Arjun Nair",          "+919876530003", "arjun@store.demo"),
        ("Sunita Patel",        "+919876530004", "sunita@store.demo"),
        ("Ramesh Babu",         "+919876530005", "ramesh@store.demo"),
        ("Divya Subramaniam",   "+919876530006", "divya@store.demo"),
        ("Karthik Rajan",       "+919876530007", "karthik@store.demo"),
        ("Ananya Iyer",         "+919876530008", "ananya@store.demo"),
        ("Vijay Kumar",         "+919876530009", "vijay@store.demo"),
        ("Preethi Narayanan",   "+919876530010", "preethi@store.demo"),
        ("Sanjay Sharma",       "+919876530011", "sanjay@store.demo"),
        ("Meena Gopal",         "+919876530012", "meena@store.demo"),
        ("Arun Venkatesh",      "+919876530013", "arun@store.demo"),
        ("Nithya Chandran",     "+919876530014", "nithya@store.demo"),
        ("Balaji Sundaram",     "+919876530015", "balaji@store.demo"),
        ("Lakshmi Venkat",      "+919876530016", "lakshmi@store.demo"),
        ("Suresh Pillai",       "+919876530017", "suresh@store.demo"),
        ("Geeta Harish",        "+919876530018", "geeta@store.demo"),
        ("Praveen Raj",         "+919876530019", "praveen@store.demo"),
        ("Kavitha Balan",       "+919876530020", "kavitha@store.demo"),
    ]
    customers = [
        {
            "tenant": tenant_id, "phone": phone, "phone_number": _pn(phone),
            "name": name, "email": email,
            "tags": ["customer"], "active": True, "no_show_count": 0,
            "created_at": NOW - dt.timedelta(days=(i * 7)),
            "is_mock": True,
        }
        for i, (name, phone, email) in enumerate(cust_data)
    ]

    # 30 orders spread over the last 30 days
    orders = _store_orders(tenant_id, products, customers)

    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "enterprise", "category": "store",
            "business_name": "QuickMart", "display_name": "QuickMart",
            "owner_email": "owner@quickmart.demo",
            "owner_phone": "+919876530001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "Plot 22, Anna Nagar, Chennai – 600040",
            "location": "https://maps.google.com/?q=QuickMart+Chennai",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR"},
            "delivery_config": {"modes": ["delivery", "pickup"], "delivery_fee": 49},
            "smtp_config": {}, "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {
                "low_stock_days_default": 30,
                "low_stock_alert_days": 7,
                "cart_recovery_window_hours": 24,
            },
            "is_mock": True,
        },
        "customers": customers,
        "professionals": [],
        "services": [],
        "staff": [
            {
                "tenant": tenant_id, "id": f"staff_{tenant_id}_{i}",
                "name": name, "role": role,
                "phone": f"+91987653{100 + i}", "email": f"staff{i}@quickmart.demo",
                "skills": skills, "active": True,
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            }
            for i, (name, role, skills) in enumerate([
                ("Ravi Store Manager",   "receptionist", ["inventory", "billing"]),
                ("Priya Customer Care",  "assistant",    ["customer_service", "returns"]),
                ("Arun Delivery Lead",   "assistant",    ["delivery", "dispatch"]),
            ], start=1)
        ],
        "appointments": [],
        "categories": [{"tenant": tenant_id, "name": cat, "active": True, "is_mock": True} for cat in categories],
        "products": products,
        "inventory": inventory,
        "orders": orders,
        # ── Promotions ──────────────────────────────────────────────────────
        "promotions": [
            {
                "tenant": tenant_id, "name": "Weekend Flash Sale – 20% Off",
                "channel": "both",
                "message": "🔥 *FLASH SALE at QuickMart!*\n\nGet 20% OFF on Electronics this weekend.\n\nShop now → https://quickmart.demo/sale\n\nOffer valid Sat–Sun only. Limited stock!",
                "interactive_type": "cta_url",
                "cta_entries": [{"id": "cta_1", "display_text": "Shop Now", "url": "https://quickmart.demo/sale"}],
                "cta_append_urls_to_body": True,
                "audience": {"type": "all"}, "status": "active",
                "offer_code": "FLASH20",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "New Arrivals – Fashion",
                "channel": "email",
                "message": "New styles just landed at QuickMart!\n\nShop the latest in Fashion — Kurtis, Jeans, Sneakers and more at unbeatable prices.\n\nFree delivery on orders above ₹499.",
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Grocery Restock Alert – SMS",
                "channel": "sms",
                "message": "QuickMart: Your favourite groceries are back in stock! Basmati Rice, Sunflower Oil, Tata Tea and more. Order now at quickmart.demo or call +91 98765 30001. Free delivery over Rs.499.",
                "audience": {"type": "all"}, "status": "draft",
                "attachments": [{"type": "link", "url": "https://quickmart.demo/groceries", "name": "Browse Groceries"}],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Loyalty Rewards – Existing Customers",
                "channel": "sms+whatsapp",
                "message": "🎁 *Thank you for shopping with QuickMart!*\n\nAs a valued customer, enjoy *₹100 off* on your next order above ₹999.\n\nUse code *LOYAL100* at checkout. Valid 7 days.",
                "audience": {"type": "all"}, "status": "draft",
                "offer_code": "LOYAL100",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Triggers ────────────────────────────────────────────────
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "👋 Welcome to *QuickMart*!\n\nReply:\n1️⃣ Browse products\n2️⃣ Track my order\n3️⃣ Return / Refund\n4️⃣ Talk to support"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_order_status",
             "match": {"type": "contains", "value": "order"},
             "action": {"kind": "static_text", "text": "📦 To track your order, please share your *Order ID* (e.g. ORD-XXXX) and we'll update you right away!"},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_delivery",
             "match": {"type": "contains", "value": "delivery"},
             "action": {"kind": "static_text", "text": "🚚 *Delivery Info*\n\n• Orders above ₹499: FREE delivery\n• Below ₹499: ₹49 delivery charge\n• Estimated time: 2–4 working days\n\nFor express delivery call +91 98765 30001."},
             "enabled": True, "priority": 7, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_return",
             "match": {"type": "contains", "value": "return"},
             "action": {"kind": "static_text", "text": "🔄 *Return Policy*\n\n• Returns accepted within 7 days of delivery\n• Product must be unused and in original packaging\n\nTo initiate a return, reply *RETURN <Order ID>* or call +91 98765 30001."},
             "enabled": True, "priority": 6, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_shop",
             "match": {"type": "exact", "value": "shop"},
             "action": {"kind": "invoke_action", "action_id": "workflow.store_browse_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
        ],
        # ── Workflows ──────────────────────────────────────────────────────
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "store_browse_flow",
                "name": "Store Product Browse & Order",
                "active": True,
                "requires_caps": ["store"],
                "steps": [
                    {"action_code": "BROWSE_CATALOG", "label": "Browse our products:", "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "CHECK_PRODUCT",   "label": "Type a product name for details:", "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "END",              "label": "✅ Thanks for browsing! Visit our catalog anytime or reply *hi* for the main menu. 🛍️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "store_support_flow",
                "name": "Order Support & Returns",
                "active": True,
                "requires_caps": ["store"],
                "steps": [
                    {"action_code": "TRACK_ORDER", "label": "Please share your Order ID (e.g. ORD-XXXX):", "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "END",         "label": "Reply *hi* anytime for the main menu. Our support team is here to help! 🙏", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "QuickMart – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *QuickMart* 🛍️",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Browse & Order Products", "next": "workflow.store_browse_flow"},
                                {"key": "2", "label": "Track My Order",          "next": "workflow.store_support_flow"},
                                {"key": "3", "label": "Return / Refund",         "next": "returns_info"},
                                {"key": "4", "label": "Offers & Discounts",      "next": "offers_info"},
                                {"key": "5", "label": "Talk to Support",         "next": "support_info"},
                            ],
                        },
                        {
                            "id": "track_order",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📦 *Track Your Order*\n\n"
                                "Please share your Order ID (e.g. ORD-QM-XXXXXX)\n"
                                "and we will fetch the latest status for you.\n\n"
                                "Or tap below to use our Order Support flow:"
                            ),
                        },
                        {
                            "id": "returns_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🔄 *Returns & Refunds*\n\n"
                                "• Items can be returned within 7 days of delivery.\n"
                                "• Perishables & opened products are non-returnable.\n"
                                "• Refunds are processed in 3–5 business days.\n\n"
                                "To initiate a return, reply with: RETURN <Order ID>\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "offers_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🏷️ *Today's Offers*\n\n"
                                "• Use code FRESH10 – 10% off Fresh Produce\n"
                                "• Free delivery on orders above ₹499\n"
                                "• Buy 2 Get 1 Free on Beverages this week!\n\n"
                                "Reply *1* to start shopping and apply your offer.\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "support_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "💬 *QuickMart Support*\n\n"
                                "📞 Phone: +91 98765 10001\n"
                                "📧 Email: support@quickmart.demo\n"
                                "⏰ Mon–Sat: 8 AM – 9 PM\n\n"
                                "For order issues reply with your Order ID and we'll help!\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                    ],
                    "edges": [],
                },
                "locales": {},
                "updated_at": NOW,
                "is_mock": True,
            },
        ],
    }


def _store_orders(tenant_id: str, products: list, customers: list) -> list[dict]:
    """Generate 30 realistic orders spread across the last 30 days."""
    statuses = ["placed", "confirmed", "shipped", "delivered", "delivered", "delivered"]
    payment_methods = ["ONLINE", "ONLINE", "ONLINE", "COD", "COD", "UPI"]
    orders = []
    for j in range(30):
        age_days = j % 30
        cust = customers[j % len(customers)]
        # pick 1-3 products
        items = []
        total = 0.0
        for k in range(1 + (j % 3)):
            p = products[(j * 3 + k) % len(products)]
            qty = 1 + (k % 2)
            items.append({
                "sku": p["sku"], "name": p["name"],
                "qty": qty, "unit": "pcs", "price": p["price"],
            })
            total += p["price"] * qty
        delivery_fee = 0.0 if total >= 499 else 49.0
        status = statuses[j % len(statuses)]
        pm = payment_methods[j % len(payment_methods)]
        created = NOW - dt.timedelta(days=age_days, hours=j % 12)
        timeline = [{"ts": created, "event": "placed"}]
        if status != "placed":
            timeline.append({"ts": created + dt.timedelta(hours=2), "event": "confirmed"})
        if status in ("shipped", "delivered"):
            timeline.append({"ts": created + dt.timedelta(hours=24), "event": "shipped"})
        if status == "delivered":
            timeline.append({"ts": created + dt.timedelta(hours=72), "event": "delivered"})
        orders.append({
            "tenant": tenant_id,
            "id": f"ORD-QM-{uuid.uuid4().hex[:6].upper()}",
            "customer": {"phone": cust["phone"], "name": cust["name"]},
            "items": items,
            "totals": {"subtotal": round(total, 2), "delivery_fee": delivery_fee, "grand_total": round(total + delivery_fee, 2)},
            "fulfillment": {"mode": "delivery" if j % 3 != 0 else "pickup", "address": cust.get("address", "")},
            "payment": {"method": pm, "status": "paid" if pm == "ONLINE" else "pending"},
            "status": status,
            "created_at": created,
            "updated_at": created + dt.timedelta(hours=24),
            "timeline": timeline,
            "is_mock": True,
        })
    return orders
