"""
Bulk demo data for Salon: appointments, professionals, customers, services, staff,
promotions, no-show scenarios, AI config. Covers all salon + AI functionality for demos.
"""
import datetime as dt
from typing import Any

from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def get_tenant_id() -> str:
    return "ss_business_salon"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    """Return dict of collection_name -> list of docs to insert (or single doc for tenant)."""
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {
            "_id": tenant_id,
            "plan": "pro",
            "category": "salon",
            "owner_email": "owner@sssalon.demo",
            "owner_phone": "+919876500001",
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
            "appointments": {"slot_duration_minutes": 30, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        "customers": [
            {"tenant": tenant_id, "phone": f"+9198765000{i:02d}", "name": name, "email": f"c{i}@salon.demo", "tags": ["walk-in"], "active": True, "no_show_count": no_show_count, "created_at": NOW, "is_mock": True}
            for i, (name, no_show_count) in enumerate([
                ("Priya Sharma", 0), ("Anita Reddy", 0), ("Meera Krishnan", 1),
                ("Sneha Patel", 0), ("Kavitha Nair", 2), ("Lakshmi Iyer", 0),
                ("Divya Menon", 4), ("Rekha Pillai", 0), ("Pooja Gupta", 1),
                ("Shruti Singh", 0), ("Neha Kapoor", 3), ("Anjali Verma", 0),
                ("Ritu Malhotra", 0), ("Sonal Mehta", 2), ("Preeti Joshi", 0),
            ], start=1)
        ],
        "professionals": [
            {"tenant": tenant_id, "name": name, "short_name": short, "price": price, "slots": [{"time": t, "status": "available"} for t in ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"]], "active": True, "created_at": NOW, "is_mock": True}
            for name, short, price in [
                ("Riya Hair Expert", "Riya", 600.0),
                ("Sana Stylist", "Sana", 750.0),
                ("Nidhi Color Specialist", "Nidhi", 1200.0),
                ("Aisha Bridal", "Aisha", 2500.0),
            ]
        ],
        "services": [
            {"tenant": tenant_id, "name": name, "description": desc, "price": price, "duration": dur, "active": True, "created_at": NOW, "is_mock": True}
            for name, desc, price, dur in [
                ("Haircut Women", "Cut and style", 600, 45),
                ("Haircut Men", "Cut and finish", 400, 30),
                ("Hair Color", "Full color application", 1200, 90),
                ("Bridal Package", "Full bridal styling", 2500, 180),
                ("Blow Dry", "Wash and blow dry", 350, 30),
                ("Facial", "Basic facial", 800, 60),
            ]
        ],
        "staff": [
            {"tenant": tenant_id, "id": f"staff_{tenant_id}_{i}", "name": name, "role": role, "phone": f"+9198766{i:05d}", "email": f"staff{i}@sssalon.demo", "skills": [], "active": True, "created_at": NOW, "updated_at": NOW, "is_mock": True}
            for i, (name, role) in enumerate([("Reception Main", "receptionist"), ("Reception 2", "receptionist"), ("Assistant Lead", "assistant")], start=1)
        ],
        "appointments": _salon_appointments(tenant_id),
        "categories": [
            {"tenant": tenant_id, "name": "Hair Care", "active": True, "is_mock": True},
            {"tenant": tenant_id, "name": "Skincare", "active": True, "is_mock": True},
        ],
        "products": [
            {"tenant": tenant_id, "sku": f"SALON-SKU-{i}", "name": name, "category": cat, "price": price, "mrp": price, "active": True, "unit": "pcs", "is_mock": True}
            for i, (name, cat, price) in enumerate([
                ("Shampoo Pro", "Hair Care", 450.0),
                ("Conditioner", "Hair Care", 380.0),
                ("Face Cream", "Skincare", 620.0),
            ], start=1)
        ],
        "inventory": [{"tenant": tenant_id, "sku": f"SALON-SKU-{i}", "available_qty": 50.0, "is_mock": True} for i in range(1, 4)],
        "promotions": [
            {"tenant": tenant_id, "name": "First Visit 20% Off", "channel": "both", "message": "Welcome! Get 20% off your first visit.", "audience": {"type": "all"}, "status": "active", "created_at": NOW, "updated_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Bridal Season", "channel": "whatsapp", "message": "Book your bridal package this month.", "audience": {"type": "all"}, "status": "draft", "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "whatsapp_triggers": [{"tenant": tenant_id, "trigger_id": "welcome_hi", "match": {"type": "exact", "value": "hi"}, "action": {"kind": "static_text", "text": "Hello! Reply 1 to book, 2 to cancel."}, "enabled": True, "priority": 10, "is_mock": True}],
    }


def _salon_appointments(tenant_id: str) -> list[dict]:
    appts = []
    base = NOW.replace(hour=9, minute=0, second=0, microsecond=0)
    customers = ["Priya Sharma", "Anita Reddy", "Meera Krishnan", "Sneha Patel", "Kavitha Nair", "Lakshmi Iyer", "Divya Menon", "Rekha Pillai"]
    phones = [f"+9198765000{i:02d}" for i in range(1, 9)]
    pros = ["Riya Hair Expert", "Sana Stylist", "Nidhi Color Specialist"]
    for day in range(-7, 14):
        d = base + dt.timedelta(days=day)
        for slot_idx, (t, status) in enumerate([("09:00", "completed"), ("10:00", "completed"), ("11:00", "no_show"), ("14:00", "booked"), ("15:00", "booked"), ("16:00", "completed")]):
            if day < 0 and status == "booked":
                status = "completed"
            start = d + dt.timedelta(hours=slot_idx + 9)
            end = start + dt.timedelta(minutes=45)
            i = (day + 7) * 6 + slot_idx
            c_idx = i % len(customers)
            appts.append({
                "tenant": tenant_id,
                "id": f"WA-{tenant_id[:4]}-{1000 + i}",
                "customer_name": customers[c_idx],
                "customer_phone": phones[c_idx],
                "professional": pros[slot_idx % len(pros)],
                "time": t,
                "price": 600.0,
                "status": status,
                "created_at": NOW,
                "start": start,
                "end": end,
                "created_by": "seed",
                "is_mock": True,
            })
    return appts
