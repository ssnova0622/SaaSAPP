"""Bulk demo data for Gym: trainers, sessions, members (as customers), appointments."""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_tenant_id() -> str:
    return "ss_business_gym"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots = [{"time": t, "status": "available"} for t in ["06:00", "07:00", "08:00", "17:00", "18:00", "19:00"]]
    pros = [{"tenant": tenant_id, "name": n, "short_name": n.split()[0], "price": 400.0, "slots": slots, "active": True, "created_at": NOW, "is_mock": True} for n in ["Trainer Mike", "Trainer Anjali", "Trainer Suresh"]]
    customers = [
        {"tenant": tenant_id, "phone": "+919876520001", "name": "Rahul M", "email": "m1@gym.demo", "tags": ["member"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True},
        {"tenant": tenant_id, "phone": "+919876520002", "name": "Priya K", "email": "m2@gym.demo", "tags": ["member"], "active": True, "no_show_count": 1, "created_at": NOW, "is_mock": True},
        {"tenant": tenant_id, "phone": "+919876520003", "name": "Amit S", "email": "m3@gym.demo", "tags": ["member"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True},
    ]
    base = NOW.replace(hour=6, minute=0, second=0, microsecond=0)
    appts = []
    for i in range(14):
        d = base + dt.timedelta(days=i)
        appts.append({
            "tenant": tenant_id, "id": f"GYM-{100+i}", "customer_name": "Rahul M", "customer_phone": "+919876520001",
            "professional": "Trainer Mike", "time": "07:00", "price": 400.0, "status": "completed" if i % 2 else "booked",
            "created_at": NOW, "start": d, "end": d + dt.timedelta(hours=1), "created_by": "seed", "is_mock": True,
        })
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {"_id": tenant_id, "plan": "pro", "category": "salon", "owner_email": "gym@ssgym.demo", "owner_phone": "+919876520001", "tz": DEFAULT_TIMEZONE, "modules": modules, "capabilities": capabilities, "active": True, "whatsapp_config": {}, "payment_config": {"provider": "dummy", "currency": "INR"}, "delivery_config": {}, "smtp_config": {}, "date_format": "DD-MM-YYYY", "ai_config": {"no_show_block_threshold": 2}, "appointments": {"slot_duration_minutes": 60}, "is_mock": True},
        "customers": customers,
        "professionals": pros,
        "services": [{"tenant": tenant_id, "name": "PT Session", "description": "Personal training", "price": 400, "duration": 60, "active": True, "created_at": NOW, "is_mock": True}],
        "staff": [{"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Front Desk", "role": "receptionist", "phone": "+919876520001", "email": "desk@ssgym.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "appointments": appts,
        "categories": [],
        "products": [],
        "inventory": [],
        "promotions": [{"tenant": tenant_id, "name": "New Member Offer", "channel": "both", "message": "First month 20% off.", "audience": {"type": "all"}, "status": "active", "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book a session."}, "enabled": True, "priority": 10, "is_mock": True}],
    }
