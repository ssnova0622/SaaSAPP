"""Bulk demo data for Camp: slots = sessions, professionals = instructors."""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_tenant_id() -> str:
    return "ss_business_camp"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots = [{"time": t, "status": "available"} for t in ["09:00", "14:00"]]
    pros = []
    for n in ["Instructor Ravi", "Instructor Sneha"]:
        pros.append({"tenant": tenant_id, "name": n, "short_name": n.split()[0], "price": 1200.0, "slots": slots, "active": True, "created_at": NOW, "is_mock": True})
    customers = []
    for i, name in enumerate(["Parent A", "Parent B", "Parent C"], start=1):
        customers.append({"tenant": tenant_id, "phone": f"+9198765400{i:02d}", "name": name, "email": f"p{i}@camp.demo", "tags": ["participant"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True})
    appts = []
    for i in range(7):
        appts.append({"tenant": tenant_id, "id": f"CAMP-{100+i}", "customer_name": "Parent A", "customer_phone": "+919876540001", "professional": "Instructor Ravi", "time": "09:00", "price": 1200.0, "status": "booked", "created_at": NOW, "start": NOW + dt.timedelta(days=i), "end": NOW + dt.timedelta(days=i, hours=2), "created_by": "seed", "is_mock": True})
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {"_id": tenant_id, "plan": "pro", "category": "salon", "owner_email": "camp@sscamp.demo", "owner_phone": "+919876540001", "tz": DEFAULT_TIMEZONE, "modules": modules, "capabilities": capabilities, "active": True, "whatsapp_config": {}, "payment_config": {"provider": "dummy", "currency": "INR"}, "delivery_config": {}, "smtp_config": {}, "date_format": "DD-MM-YYYY", "ai_config": {"no_show_block_threshold": 2}, "appointments": {"slot_duration_minutes": 120}, "is_mock": True},
        "customers": customers,
        "professionals": pros,
        "services": [{"tenant": tenant_id, "name": "Day Camp", "description": "Full day session", "price": 1200, "duration": 120, "active": True, "created_at": NOW, "is_mock": True}],
        "staff": [{"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Camp Admin", "role": "receptionist", "phone": "+919876540001", "email": "admin@sscamp.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "appointments": appts,
        "categories": [],
        "products": [],
        "inventory": [],
        "promotions": [],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book a camp slot."}, "enabled": True, "priority": 10, "is_mock": True}],
    }
