"""
Bulk demo data for Clinic: monthly doctor, weekly doctor, consultants, appointments,
patients, no-show scenarios. Covers clinic + AI no-show and appointment recs.
"""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_tenant_id() -> str:
    return "ss_business_clinic"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    """Monthly doctor = Dr. Raj (Mon–Fri); Weekly = Dr. Sheela (Sat only); Consultant = Dr. Amit (Tue/Thu)."""
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {
            "_id": tenant_id,
            "plan": "pro",
            "category": "clinic",
            "owner_email": "admin@ssclinic.demo",
            "owner_phone": "+919876510001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules,
            "capabilities": capabilities,
            "active": True,
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR", "test_mode": True},
            "delivery_config": {},
            "smtp_config": {},
            "date_format": "DD-MM-YYYY",
            "ai_config": {
                "no_show_block_threshold": 3,
                "no_show_reminder_threshold": 0.5,
                "no_show_high_risk_threshold": 0.7,
                "no_show_reminder_lead_hours": 24,
            },
            "appointments": {"slot_duration_minutes": 15, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        "customers": [
            {"tenant": tenant_id, "phone": f"+9198765100{i:02d}", "name": name, "email": f"p{i}@clinic.demo", "tags": ["patient"], "active": True, "no_show_count": no_show_count, "created_at": NOW, "is_mock": True}
            for i, (name, no_show_count) in enumerate([
                ("Vikram Rao", 0), ("Sunita Desai", 1), ("Rajesh Kumar", 0),
                ("Deepa Nambiar", 2), ("Arun Pillai", 0), ("Latha Venkat", 0),
                ("Manoj Reddy", 3), ("Swati Joshi", 0), ("Kiran Bhat", 1),
                ("Uma Shankar", 0), ("Suresh Iyer", 0), ("Padma Krishnan", 2),
            ], start=1)
        ],
        "professionals": [
            {"tenant": tenant_id, "name": "Dr. Raj (Monthly)", "short_name": "Dr.Raj", "price": 500.0, "slots": _slots(["09:00", "09:15", "09:30", "09:45", "10:00", "10:15", "10:30", "11:00", "11:15", "14:00", "14:15", "14:30", "15:00"]), "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Dr. Sheela (Weekly Sat)", "short_name": "Dr.Sheela", "price": 600.0, "slots": _slots(["09:00", "09:30", "10:00", "10:30", "11:00"]), "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Dr. Amit (Consultant Tue/Thu)", "short_name": "Dr.Amit", "price": 800.0, "slots": _slots(["16:00", "16:30", "17:00", "17:30"]), "active": True, "created_at": NOW, "is_mock": True},
        ],
        "services": [
            {"tenant": tenant_id, "name": "General Consultation", "description": "OPD consultation", "price": 500, "duration": 15, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Follow-up", "description": "Follow-up visit", "price": 300, "duration": 10, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Health Check-up", "description": "Basic health check", "price": 800, "duration": 30, "active": True, "created_at": NOW, "is_mock": True},
        ],
        "staff": [
            {"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Reception", "role": "receptionist", "phone": "+919876510001", "email": "reception@ssclinic.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "appointments": _clinic_appointments(tenant_id),
        "categories": [{"tenant": tenant_id, "name": "Pharmacy", "active": True, "is_mock": True}],
        "products": [
            {"tenant": tenant_id, "sku": "CLINIC-MED-1", "name": "Vitamin D", "category": "Pharmacy", "price": 250.0, "mrp": 280.0, "active": True, "unit": "pcs", "is_mock": True},
        ],
        "inventory": [{"tenant": tenant_id, "sku": "CLINIC-MED-1", "available_qty": 100.0, "is_mock": True}],
        "promotions": [
            {"tenant": tenant_id, "name": "Health Camp", "channel": "both", "message": "Free BP check this week.", "audience": {"type": "all"}, "status": "active", "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book appointment."}, "enabled": True, "priority": 10, "is_mock": True}],
    }


def _slots(times: list[str]) -> list[dict]:
    return [{"time": t, "status": "available"} for t in times]


def _clinic_appointments(tenant_id: str) -> list[dict]:
    appts = []
    base = NOW.replace(hour=9, minute=0, second=0, microsecond=0)
    patients = ["Vikram Rao", "Sunita Desai", "Rajesh Kumar", "Deepa Nambiar", "Arun Pillai", "Latha Venkat"]
    phones = [f"+9198765100{i:02d}" for i in range(1, 7)]
    docs = ["Dr. Raj (Monthly)", "Dr. Sheela (Weekly Sat)", "Dr. Amit (Consultant Tue/Thu)"]
    for day in range(-5, 10):
        d = base + dt.timedelta(days=day)
        for slot_idx, t in enumerate(["09:00", "09:15", "09:30", "10:00", "10:30"]):
            start = d + dt.timedelta(hours=9, minutes=slot_idx * 20)
            end = start + dt.timedelta(minutes=15)
            status = "completed" if day < 0 else ("no_show" if slot_idx == 2 and day % 3 == 0 else "booked")
            i = (day + 5) * 5 + slot_idx
            appts.append({
                "tenant": tenant_id,
                "id": f"CL-{1000 + i}",
                "customer_name": patients[i % len(patients)],
                "customer_phone": phones[i % len(phones)],
                "professional": docs[slot_idx % len(docs)],
                "time": t,
                "price": 500.0,
                "status": status,
                "created_at": NOW,
                "start": start,
                "end": end,
                "created_by": "seed",
                "is_mock": True,
            })
    return appts
