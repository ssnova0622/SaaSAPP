"""Bulk demo data for School: parent meetings = appointments, teachers = professionals."""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_tenant_id() -> str:
    return "ss_business_school"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {"_id": tenant_id, "plan": "pro", "category": "salon", "owner_email": "school@ssschool.demo", "owner_phone": "+919876560001", "tz": DEFAULT_TIMEZONE, "modules": modules, "capabilities": capabilities, "active": True, "whatsapp_config": {}, "payment_config": {"provider": "dummy", "currency": "INR"}, "delivery_config": {}, "smtp_config": {}, "date_format": "DD-MM-YYYY", "ai_config": {"no_show_block_threshold": 2}, "appointments": {"slot_duration_minutes": 15}, "is_mock": True},
        "customers": [{"tenant": tenant_id, "phone": f"+9198765600{i:02d}", "name": name, "email": f"p{i}@school.demo", "tags": ["parent"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True} for i, name in enumerate(["Parent 1", "Parent 2", "Parent 3", "Parent 4", "Parent 5"], start=1)],
        "professionals": [{"tenant": tenant_id, "name": name, "short_name": name.split()[0], "price": 0.0, "slots": [{"time": t, "status": "available"} for t in ["14:00", "14:15", "14:30", "14:45", "15:00"]], "active": True, "created_at": NOW, "is_mock": True} for name in ["Teacher Anita", "Teacher Suresh"]],
        "services": [{"tenant": tenant_id, "name": "Parent Meeting", "description": "15 min slot", "price": 0, "duration": 15, "active": True, "created_at": NOW, "is_mock": True}],
        "staff": [{"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Office", "role": "receptionist", "phone": "+919876560001", "email": "office@ssschool.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}],
        "appointments": [{"tenant": tenant_id, "id": f"SCH-{100+i}", "customer_name": "Parent 1", "customer_phone": "+919876560001", "professional": "Teacher Anita", "time": "14:00", "price": 0.0, "status": "booked", "created_at": NOW, "start": NOW + dt.timedelta(days=i), "end": NOW + dt.timedelta(days=i, minutes=15), "created_by": "seed", "is_mock": True} for i in range(5)],
        "categories": [],
        "products": [],
        "inventory": [],
        "promotions": [],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book a parent meeting."}, "enabled": True, "priority": 10, "is_mock": True}],
    }
