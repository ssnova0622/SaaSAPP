"""Bulk demo data for Car Showroom: 50+ car models, test drives = appointments, sales reps = professionals."""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

# 50 car models (name, price in INR)
CAR_MODELS = [
    ("Swift Dzire", 649000), ("Baleno", 629000), ("Alto K10", 399000), ("Wagon R", 489000), ("Ertiga", 849000),
    ("Brezza", 799000), ("Celerio", 499000), ("Ignis", 549000), ("Ciaz", 899000), ("Grand Vitara", 1049000),
    ("i20", 699000), ("Verna", 949000), ("Creta", 1099000), ("Venue", 749000), ("Grand i10", 549000),
    ("Punch", 599000), ("Nexon", 799000), ("Harrier", 1499000), ("Safari", 1549000), ("Tiago", 549000),
    ("XUV700", 1399000), ("Scorpio N", 1349000), ("Thar", 1049000), ("XUV300", 799000), ("Bolero", 949000),
    ("Honda City", 1149000), ("Amaze", 699000), ("Elevate", 1099000), ("Jazz", 799000), ("WR-V", 899000),
    ("Hyundai Tucson", 2899000), ("Kia Seltos", 1099000), ("Kia Sonet", 799000), ("Kia Carens", 1049000),
    ("Toyota Innova", 1999000), ("Fortuner", 3499000), ("Glanza", 629000), ("Urban Cruiser", 1049000),
    ("MG Hector", 1499000), ("MG ZS EV", 2199000), ("Mahindra XUV400", 1599000),
    ("Tata Nexon EV", 1499000), ("Tata Tigor EV", 1299000), ("Citroen C3", 599000), ("C3 Aircross", 999000),
    ("Skoda Kushaq", 1099000), ("Skoda Slavia", 1099000), ("VW Taigun", 1099000), ("VW Virtus", 1149000),
    ("Renault Duster", 1049000), ("Renault Kiger", 599000), ("Nissan Magnite", 599000), ("Nissan Kicks", 999000),
]


def get_tenant_id() -> str:
    return "ss_business_car_showroom"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots = [{"time": t, "status": "available"} for t in ["10:00", "11:00", "14:00", "15:00", "16:00"]]
    pros = [{"tenant": tenant_id, "name": n, "short_name": n.split()[0], "price": 0.0, "slots": slots, "active": True, "created_at": NOW, "is_mock": True} for n in ["Sales Rep Raj", "Sales Rep Priya"]]
    customers = [
        {"tenant": tenant_id, "phone": "+919876550001", "name": "Buyer One", "email": "c1@cars.demo", "tags": ["lead"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True},
        {"tenant": tenant_id, "phone": "+919876550002", "name": "Buyer Two", "email": "c2@cars.demo", "tags": ["lead"], "active": True, "no_show_count": 1, "created_at": NOW, "is_mock": True},
    ]
    appts = [{"tenant": tenant_id, "id": f"TD-{100+i}", "customer_name": "Buyer One", "customer_phone": "+919876550001", "professional": "Sales Rep Raj", "time": "11:00", "price": 0.0, "status": "completed" if i < 3 else "booked", "created_at": NOW, "start": NOW + dt.timedelta(days=i), "end": NOW + dt.timedelta(days=i, hours=1), "created_by": "seed", "is_mock": True} for i in range(5)]
    modules, capabilities = get_modules_capabilities()
    products = [
        {"tenant": tenant_id, "sku": f"CAR-{i:03d}", "name": name, "category": "Cars", "price": float(price), "mrp": float(price), "active": True, "unit": "pcs", "is_mock": True}
        for i, (name, price) in enumerate(CAR_MODELS, start=1)
    ]
    inventory = [
        {"tenant": tenant_id, "sku": f"CAR-{i:03d}", "available_qty": max(1, 10 - (i % 5)), "is_mock": True}
        for i in range(1, len(products) + 1)
    ]
    return {
        "tenant_doc": {"_id": tenant_id, "plan": "pro", "category": "car showroom", "owner_email": "showroom@sscars.demo", "owner_phone": "+919876550001", "tz": DEFAULT_TIMEZONE, "modules": modules, "capabilities": capabilities, "active": True, "whatsapp_config": {}, "payment_config": {"provider": "dummy", "currency": "INR"}, "delivery_config": {}, "smtp_config": {}, "date_format": "DD-MM-YYYY", "ai_config": {"no_show_block_threshold": 2}, "appointments": {"slot_duration_minutes": 60}, "is_mock": True},
        "customers": customers,
        "professionals": pros,
        "services": [{"tenant": tenant_id, "name": "Test Drive", "description": "30 min test drive", "price": 0, "duration": 60, "active": True, "created_at": NOW, "is_mock": True}],
        "staff": [{"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Reception", "role": "receptionist", "phone": "+919876550001", "email": "reception@sscars.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "appointments": appts,
        "categories": [{"tenant": tenant_id, "name": "Cars", "active": True, "is_mock": True}],
        "products": products,
        "inventory": inventory,
        "promotions": [{"tenant": tenant_id, "name": "Test Drive Weekend", "channel": "whatsapp", "message": "Book a test drive this weekend.", "audience": {"type": "all"}, "status": "active", "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book a test drive."}, "enabled": True, "priority": 10, "is_mock": True}],
    }
