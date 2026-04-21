"""
Bulk demo data for HealthFirst Clinic.
Covers: doctors, patients, appointments (including no-shows),
pharmacy products, promotions (WA / email / SMS), multi-step
booking workflow, and rich WhatsApp triggers.
"""
import datetime as dt
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

_IMG = {
    "vitamins":  "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=400&q=80",
    "pharmacy":  "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=400&q=80",
    "bp_kit":    "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80",
    "glucometer":"https://images.unsplash.com/photo-1631549916768-4119b2e5f926?auto=format&fit=crop&w=400&q=80",
}


def get_tenant_id() -> str:
    return "ss_business_clinic"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()
    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "pro", "category": "clinic",
            "business_name": "HealthFirst Clinic",
            "display_name": "HealthFirst Clinic",
            "owner_email": "admin@healthfirst.demo",
            "owner_phone": "+919876510001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "3 Gandhi Nagar, Coimbatore – 641009",
            "location": "https://maps.google.com/?q=HealthFirst+Clinic+Coimbatore",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR", "test_mode": True},
            "delivery_config": {}, "smtp_config": {},
            "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {
                "no_show_block_threshold": 3,
                "no_show_reminder_threshold": 0.5,
                "no_show_high_risk_threshold": 0.7,
                "no_show_reminder_lead_hours": 24,
            },
            "appointments": {"slot_duration_minutes": 15, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        # ── Patients ─────────────────────────────────────────────────────────
        "customers": [
            {
                "tenant": tenant_id,
                "phone": f"+9198765100{i:02d}",
                "phone_number": _pn(f"+9198765100{i:02d}"),
                "name": name, "email": f"p{i}@healthfirst.demo",
                "tags": ["patient"],
                "active": True, "no_show_count": ns,
                "created_at": NOW - dt.timedelta(days=i * 15),
                "is_mock": True,
            }
            for i, (name, ns) in enumerate([
                ("Vikram Rao",       0), ("Sunita Desai",    1), ("Rajesh Kumar",     0),
                ("Deepa Nambiar",    2), ("Arun Pillai",     0), ("Latha Venkat",     0),
                ("Manoj Reddy",      3), ("Swati Joshi",     0), ("Kiran Bhat",       1),
                ("Uma Shankar",      0), ("Suresh Iyer",     0), ("Padma Krishnan",   2),
                ("Nalini Srinivas",  0), ("Gopalan Rajan",   0), ("Revathi Naidu",    1),
                ("Harikumar P",      0), ("Meenakshi A",     0), ("Senthil Kumar",    0),
            ], start=1)
        ],
        # ── Doctors (professionals) ───────────────────────────────────────────
        "professionals": [
            {
                "tenant": tenant_id,
                "professional_id": _prof_id(tenant_id, name, short),
                "employee_id": eid,
                "name": name, "short_name": short,
                "price": price, "specialization": spec,
                "slots": _slots(times),
                "active": True, "created_at": NOW, "is_mock": True,
            }
            for name, short, eid, price, spec, times in [
                ("Dr. Rajesh Menon",  "Dr.Rajesh",  "HF-D001", 500.0, "General Physician",
                 ["09:00","09:15","09:30","09:45","10:00","10:15","10:30","11:00","11:15","14:00","14:15","14:30","15:00","15:15"]),
                ("Dr. Sheela Raman",  "Dr.Sheela",  "HF-D002", 600.0, "Gynaecologist",
                 ["09:00","09:30","10:00","10:30","11:00","14:00","14:30","15:00"]),
                ("Dr. Amit Saxena",   "Dr.Amit",    "HF-D003", 800.0, "Orthopaedic Consultant",
                 ["16:00","16:30","17:00","17:30","18:00"]),
                ("Dr. Priya Nair",    "Dr.Priya",   "HF-D004", 700.0, "Paediatrician",
                 ["10:00","10:30","11:00","11:30","15:00","15:30"]),
            ]
        ],
        # ── Services ─────────────────────────────────────────────────────────
        "services": [
            {"tenant": tenant_id, "name": n, "description": d, "price": p, "duration": dur,
             "active": True, "created_at": NOW, "is_mock": True}
            for n, d, p, dur in [
                ("General Consultation", "OPD consultation with GP",              500, 15),
                ("Follow-up Visit",      "Follow-up within 30 days",              300, 10),
                ("Basic Health Check",   "BP, sugar, BMI, basic blood panel",     800, 30),
                ("Full Body Check-up",   "Comprehensive annual health check",    2500, 60),
                ("Paediatric Consult",   "Child health consultation",             500, 20),
                ("Gynaecology Consult",  "Women's health consultation",           600, 20),
                ("Ortho Consultation",   "Bone & joint consultation",             800, 20),
                ("ECG",                  "12-lead electrocardiogram",             300, 15),
                ("Blood Glucose Test",   "Fasting / random blood glucose",        150, 10),
                ("BP Monitoring",        "Blood pressure check & report",         100, 10),
            ]
        ],
        # ── Staff ─────────────────────────────────────────────────────────────
        "staff": [
            {
                "tenant": tenant_id, "id": f"staff_{tenant_id}_{i}",
                "name": name, "role": role,
                "phone": f"+91987651{100 + i}", "email": f"staff{i}@healthfirst.demo",
                "skills": skills, "active": True,
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            }
            for i, (name, role, skills) in enumerate([
                ("Meena Receptionist",   "receptionist", ["appointment_booking", "billing"]),
                ("Sathish Lab Tech",     "assistant",    ["lab_samples", "ecg"]),
                ("Ravi Pharmacist",      "assistant",    ["pharmacy", "inventory"]),
            ], start=1)
        ],
        "appointments": _clinic_appointments(tenant_id),
        # ── Pharmacy products ─────────────────────────────────────────────────
        "categories": [
            {"tenant": tenant_id, "name": "Pharmacy",     "active": True, "is_mock": True},
            {"tenant": tenant_id, "name": "Diagnostics",  "active": True, "is_mock": True},
        ],
        "products": [
            {
                "tenant": tenant_id, "sku": sku, "name": name, "category": cat,
                "price": float(price), "mrp": float(mrp), "active": True, "unit": "pcs",
                "description": desc,
                "image_urls": [img], "image_url": img,
                "is_mock": True,
            }
            for sku, name, cat, price, mrp, desc, img in [
                ("CLINIC-001", "Vitamin D3 + K2 (60 caps)", "Pharmacy", 250, 280,
                 "High-potency Vitamin D3 2000 IU with K2 for bone health. 60 capsules.", _IMG["vitamins"]),
                ("CLINIC-002", "Multivitamin Tablets (30)",  "Pharmacy", 180, 210,
                 "Complete daily multivitamin with 24 essential vitamins & minerals.", _IMG["vitamins"]),
                ("CLINIC-003", "Omron Digital BP Monitor",   "Diagnostics", 1499, 1799,
                 "Clinically validated upper arm monitor, memory for 60 readings, irregular heartbeat detection.", _IMG["bp_kit"]),
                ("CLINIC-004", "Glucometer Kit",             "Diagnostics", 999, 1299,
                 "Blood glucose monitoring kit with 25 test strips. No coding required.", _IMG["glucometer"]),
                ("CLINIC-005", "Calcium + Magnesium (60t)",  "Pharmacy", 220, 260,
                 "Bone support formula with Calcium, Magnesium and Zinc.", _IMG["vitamins"]),
                ("CLINIC-006", "Cough Syrup 100ml",          "Pharmacy",  95, 110,
                 "Non-drowsy formula for dry and wet cough. Sugar-free.", _IMG["pharmacy"]),
            ]
        ],
        "inventory": [
            {"tenant": tenant_id, "sku": f"CLINIC-00{i}", "available_qty": qty, "is_mock": True}
            for i, qty in enumerate([80, 120, 15, 25, 90, 60], start=1)
        ],
        # ── Promotions ────────────────────────────────────────────────────────
        "promotions": [
            {
                "tenant": tenant_id, "name": "Free Health Check Camp",
                "channel": "both",
                "message": "🏥 *Free Health Check Camp* at HealthFirst Clinic!\n\nGet a FREE BP check + blood glucose test this Saturday.\n\n📍 3 Gandhi Nagar, Coimbatore\n⏰ 9 AM – 1 PM\n\nBring this message for a *free token*. Limited slots!",
                "audience": {"type": "all"}, "status": "active",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Preventive Health Package",
                "channel": "email",
                "message": "Book our *Annual Preventive Health Package* at ₹2,499.\n\nIncludes: Complete Blood Count, Lipid Profile, Blood Sugar, Thyroid, Kidney Function, Liver Function + doctor consultation.\n\nEarly bird offer – valid this month.",
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Appointment Reminder – SMS Blast",
                "channel": "sms",
                "message": "HealthFirst Clinic reminder: Your health check-up is due! Book your appointment at +91 98765 10001 or visit healthfirst.demo. Early morning slots available.",
                "attachments": [{"type": "link", "url": "https://healthfirst.demo/book", "name": "Book Appointment"}],
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Triggers ─────────────────────────────────────────────────
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "👋 Welcome to *HealthFirst Clinic*!\n\nReply:\n1️⃣ Book appointment\n2️⃣ Our doctors & timings\n3️⃣ Services & fees\n4️⃣ Location\n5️⃣ Emergency contact"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "exact", "value": "book"},
             "action": {"kind": "workflow", "workflow_id": "clinic_booking_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_doctors",
             "match": {"type": "contains", "value": "doctor"},
             "action": {"kind": "static_text", "text": "👨‍⚕️ *Our Doctors*\n\n• Dr. Rajesh Menon – General Physician (Mon–Sat, 9–11 AM & 2–4 PM)\n• Dr. Sheela Raman – Gynaecologist (Mon–Fri, 9–11 AM & 2–4 PM)\n• Dr. Amit Saxena – Orthopaedic (Tue & Thu, 4–6 PM)\n• Dr. Priya Nair – Paediatrician (Mon–Fri, 10–11:30 AM & 3–5 PM)\n\nReply *book* to schedule."},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_emergency",
             "match": {"type": "contains", "value": "emergency"},
             "action": {"kind": "static_text", "text": "🚨 *Emergency?*\n\nCall us immediately: *+91 98765 10001*\n\nFor life-threatening emergencies please call 108 (Ambulance).\n\nWe are available Mon–Sat 9 AM – 7 PM."},
             "enabled": True, "priority": 11, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_location",
             "match": {"type": "contains", "value": "location"},
             "action": {"kind": "static_text", "text": "📍 *HealthFirst Clinic*\n3 Gandhi Nagar, Coimbatore – 641009\n\n🕐 Mon–Fri: 9 AM – 7 PM\n🕐 Saturday: 9 AM – 2 PM\n🔴 Sunday: Closed\n\nMaps: https://maps.google.com/?q=HealthFirst+Clinic+Coimbatore"},
             "enabled": True, "priority": 6, "is_mock": True},
        ],
        # ── Workflows ─────────────────────────────────────────────────────────
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "clinic_booking_flow",
                "name": "Clinic Appointment Booking",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Select the type of consultation:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",      "label": "Choose your preferred date:",      "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",      "label": "Choose an available time slot:",   "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your appointment",         "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",              "label": "✅ Appointment confirmed! Please arrive 10 minutes early. Bring any previous reports. Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "HealthFirst Clinic – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *HealthFirst Clinic* 🏥",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Book Appointment",      "next": "workflow.clinic_booking_flow"},
                                {"key": "2", "label": "Our Doctors & Timings", "next": "doctors_info"},
                                {"key": "3", "label": "Services & Fees",       "next": "services_info"},
                                {"key": "4", "label": "Location & Hours",      "next": "location_info"},
                                {"key": "5", "label": "🚨 Emergency",          "next": "emergency_info"},
                            ],
                        },
                        {
                            "id": "doctors_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "👨‍⚕️ *Our Doctors*\n\n"
                                "• Dr. Rajesh Menon – General Physician\n"
                                "  Mon–Sat: 9–11 AM & 2–4 PM\n\n"
                                "• Dr. Sheela Raman – Gynaecologist\n"
                                "  Mon–Fri: 9–11 AM & 2–4 PM\n\n"
                                "• Dr. Amit Saxena – Orthopaedic Surgeon\n"
                                "  Tue & Thu: 4–6 PM\n\n"
                                "• Dr. Priya Nair – Paediatrician\n"
                                "  Mon–Fri: 10–11:30 AM & 3–5 PM\n\n"
                                "Reply *book* to schedule your appointment."
                            ),
                        },
                        {
                            "id": "services_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🩺 *Services & Consultation Fees*\n\n"
                                "• General Consultation – ₹500\n"
                                "• Follow-up Visit – ₹300\n"
                                "• Gynaecology Consult – ₹700\n"
                                "• Paediatric Consult – ₹600\n"
                                "• Basic Health Check – ₹1,200\n"
                                "• Orthopaedic Consult – ₹800\n\n"
                                "Lab tests available on site.\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "location_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📍 *HealthFirst Clinic*\n"
                                "3 Gandhi Nagar, Coimbatore – 641009\n\n"
                                "🕐 Mon–Fri: 9 AM – 7 PM\n"
                                "🕐 Saturday: 9 AM – 2 PM\n"
                                "🔴 Sunday: Closed\n\n"
                                "📞 +91 98765 10001\n"
                                "🗺 https://maps.google.com/?q=HealthFirst+Clinic+Coimbatore\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "emergency_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🚨 *Emergency Contact*\n\n"
                                "📞 Clinic Emergency: *+91 98765 10001*\n"
                                "🚑 National Ambulance: *108*\n\n"
                                "For life-threatening situations please call 108 immediately.\n\n"
                                "Our clinic is available Mon–Sat 9 AM – 7 PM.\n\n"
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


def _slots(times: list[str]) -> list[dict]:
    return [{"time": t, "status": "available"} for t in times]


def _clinic_appointments(tenant_id: str) -> list[dict]:
    appts = []
    base = NOW.replace(hour=9, minute=0, second=0, microsecond=0)
    patients = [
        ("Vikram Rao",     "+919876510001"),
        ("Sunita Desai",   "+919876510002"),
        ("Rajesh Kumar",   "+919876510003"),
        ("Deepa Nambiar",  "+919876510004"),
        ("Arun Pillai",    "+919876510005"),
        ("Latha Venkat",   "+919876510006"),
        ("Manoj Reddy",    "+919876510007"),
        ("Swati Joshi",    "+919876510008"),
    ]
    docs = ["Dr. Rajesh Menon", "Dr. Sheela Raman", "Dr. Amit Saxena", "Dr. Priya Nair"]
    services = ["General Consultation", "Follow-up Visit", "Paediatric Consult", "Gynaecology Consult", "Basic Health Check"]
    slot_times_detail = [("09:00", 9, 0), ("09:15", 9, 15), ("09:30", 9, 30), ("09:45", 9, 45), ("10:00", 10, 0), ("10:15", 10, 15)]
    for day in range(-10, 10):
        d = base + dt.timedelta(days=day)
        for slot_idx, (t_str, h, m) in enumerate(slot_times_detail):
            start = d.replace(hour=h, minute=m)
            end = start + dt.timedelta(minutes=15)
            status = "completed" if day < 0 else ("no_show" if slot_idx == 2 and day % 3 == 0 else "booked")
            i = (day + 10) * 6 + slot_idx
            cname, cphone = patients[i % len(patients)]
            appts.append({
                "tenant": tenant_id,
                "id": f"HF-{2000 + i}",
                "customer_name": cname,
                "customer_phone": cphone,
                "professional": docs[slot_idx % len(docs)],
                "service": services[slot_idx % len(services)],
                "time": t_str,
                "price": 500.0,
                "status": status,
                "created_at": NOW - dt.timedelta(days=abs(day) + 1),
                "start": start, "end": end,
                "created_by": "seed",
                "is_mock": True,
            })
    return appts
