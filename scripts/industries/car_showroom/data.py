"""Bulk demo data for AutoElite Car Showroom: 50+ car models, test drives, sales reps."""
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

_CAR_IMG = "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?auto=format&fit=crop&w=400&q=80"
_SUV_IMG  = "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?auto=format&fit=crop&w=400&q=80"
_EV_IMG   = "https://images.unsplash.com/photo-1593941707882-a5bba14938c7?auto=format&fit=crop&w=400&q=80"

# (name, category, price_inr, img_key)
CAR_MODELS = [
    ("Maruti Swift Dzire",   "Sedan",    649000,  _CAR_IMG),
    ("Maruti Baleno",        "Hatchback",629000,  _CAR_IMG),
    ("Maruti Alto K10",      "Hatchback",399000,  _CAR_IMG),
    ("Maruti Wagon R",       "Hatchback",489000,  _CAR_IMG),
    ("Maruti Ertiga",        "MPV",      849000,  _SUV_IMG),
    ("Maruti Brezza",        "SUV",      799000,  _SUV_IMG),
    ("Maruti Grand Vitara",  "SUV",     1049000,  _SUV_IMG),
    ("Hyundai i20",          "Hatchback",699000,  _CAR_IMG),
    ("Hyundai Verna",        "Sedan",    949000,  _CAR_IMG),
    ("Hyundai Creta",        "SUV",     1099000,  _SUV_IMG),
    ("Hyundai Venue",        "SUV",      749000,  _SUV_IMG),
    ("Tata Punch",           "SUV",      599000,  _SUV_IMG),
    ("Tata Nexon",           "SUV",      799000,  _SUV_IMG),
    ("Tata Harrier",         "SUV",     1499000,  _SUV_IMG),
    ("Tata Safari",          "SUV",     1549000,  _SUV_IMG),
    ("Tata Tiago",           "Hatchback",549000,  _CAR_IMG),
    ("Tata Nexon EV",        "EV",      1499000,  _EV_IMG),
    ("Tata Tigor EV",        "EV",      1299000,  _EV_IMG),
    ("Mahindra XUV700",      "SUV",     1399000,  _SUV_IMG),
    ("Mahindra Scorpio N",   "SUV",     1349000,  _SUV_IMG),
    ("Mahindra Thar",        "SUV",     1049000,  _SUV_IMG),
    ("Mahindra XUV300",      "SUV",      799000,  _SUV_IMG),
    ("Mahindra XUV400 EV",   "EV",      1599000,  _EV_IMG),
    ("Honda City",           "Sedan",   1149000,  _CAR_IMG),
    ("Honda Amaze",          "Sedan",    699000,  _CAR_IMG),
    ("Honda Elevate",        "SUV",     1099000,  _SUV_IMG),
    ("Toyota Innova Crysta", "MPV",     1999000,  _SUV_IMG),
    ("Toyota Fortuner",      "SUV",     3499000,  _SUV_IMG),
    ("Toyota Glanza",        "Hatchback",629000,  _CAR_IMG),
    ("Toyota Urban Cruiser",  "SUV",    1049000,  _SUV_IMG),
    ("Kia Seltos",           "SUV",     1099000,  _SUV_IMG),
    ("Kia Sonet",            "SUV",      799000,  _SUV_IMG),
    ("Kia Carens",           "MPV",     1049000,  _SUV_IMG),
    ("MG Hector",            "SUV",     1499000,  _SUV_IMG),
    ("MG ZS EV",             "EV",      2199000,  _EV_IMG),
    ("MG Astor",             "SUV",     1199000,  _SUV_IMG),
    ("Skoda Kushaq",         "SUV",     1099000,  _SUV_IMG),
    ("Skoda Slavia",         "Sedan",   1099000,  _CAR_IMG),
    ("Volkswagen Taigun",    "SUV",     1099000,  _SUV_IMG),
    ("Volkswagen Virtus",    "Sedan",   1149000,  _CAR_IMG),
    ("Renault Duster",       "SUV",     1049000,  _SUV_IMG),
    ("Renault Kiger",        "SUV",      599000,  _SUV_IMG),
    ("Nissan Magnite",       "SUV",      599000,  _SUV_IMG),
    ("Citroen C3",           "Hatchback",599000,  _CAR_IMG),
    ("Citroen C3 Aircross",  "SUV",      999000,  _SUV_IMG),
    ("Jeep Compass",         "SUV",     2099000,  _SUV_IMG),
    ("Jeep Meridian",        "SUV",     2999000,  _SUV_IMG),
    ("Hyundai Tucson",       "SUV",     2899000,  _SUV_IMG),
    ("Ford Endeavour",       "SUV",     3699000,  _SUV_IMG),
    ("BMW 3 Series",         "Luxury",  4599000,  _CAR_IMG),
]


def get_tenant_id() -> str:
    return "ss_business_car_showroom"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots = [{"time": t, "status": "available"} for t in ["10:00", "11:00", "12:00", "14:00", "15:00", "16:00", "17:00"]]
    modules, capabilities = get_modules_capabilities()

    customers = [
        {
            "tenant": tenant_id,
            "phone": f"+9198765500{i:02d}",
            "phone_number": _pn(f"+9198765500{i:02d}"),
            "name": name, "email": f"c{i}@autoelite.demo",
            "tags": tags, "active": True, "no_show_count": ns, "created_at": NOW, "is_mock": True,
        }
        for i, (name, ns, tags) in enumerate([
            ("Aravind Srinivasan",  0, ["lead", "suv-segment"]),
            ("Meena Rajagopalan",   1, ["lead", "hatchback"]),
            ("Sathish Venkatesh",   0, ["lead", "sedan"]),
            ("Nithya Kumar",        0, ["lead", "ev-interested"]),
            ("Rajesh Pillai",       0, ["lead", "suv-segment"]),
            ("Kavitha Balan",       0, ["lead"]),
            ("Senthil Rajan",       1, ["lead", "luxury"]),
            ("Deepa Natarajan",     0, ["lead", "hatchback"]),
            ("Pradeep Anand",       0, ["test-driven", "suv-segment"]),
            ("Latha Govindarajan",  0, ["test-driven"]),
        ], start=1)
    ]

    base = NOW.replace(hour=10, minute=0, second=0, microsecond=0)
    appts = []
    for i in range(20):
        d = base + dt.timedelta(days=i - 7)
        t = ["10:00", "11:00", "14:00", "15:00", "16:00"][i % 5]
        start = d.replace(hour=int(t.split(":")[0]), minute=0)
        cust = customers[i % len(customers)]
        car_name = CAR_MODELS[i % len(CAR_MODELS)][0]
        rep = ["Sales Rep Raj Kumar", "Sales Rep Priya Nair", "Sales Rep Sanjay M"][i % 3]
        appts.append({
            "tenant": tenant_id, "id": f"TD-{300 + i}",
            "customer_name": cust["name"], "customer_phone": cust["phone"],
            "professional": rep,
            "service": "Test Drive",
            "notes": f"Interested in: {car_name}",
            "time": t, "price": 0.0,
            "status": "completed" if i < 7 else "booked",
            "created_at": NOW - dt.timedelta(days=abs(i - 7) + 1),
            "start": start, "end": start + dt.timedelta(hours=1),
            "created_by": "seed", "is_mock": True,
        })

    categories = sorted(set(m[1] for m in CAR_MODELS))
    products = []
    for i, (name, cat, price, img) in enumerate(CAR_MODELS, start=1):
        products.append({
            "tenant": tenant_id, "sku": f"CAR-{i:03d}", "name": name, "category": cat,
            "price": float(price), "mrp": float(price), "active": True, "unit": "pcs",
            "description": f"{name} – {cat}. Ex-showroom price ₹{price:,}. Contact showroom for test drive & finance options.",
            "image_urls": [img], "image_url": img,
            "is_mock": True,
        })
    inventory = [{"tenant": tenant_id, "sku": f"CAR-{i:03d}", "available_qty": max(1, 8 - (i % 4)), "is_mock": True} for i in range(1, len(products) + 1)]

    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "pro", "category": "car_showroom",
            "business_name": "AutoElite Motors",
            "display_name": "AutoElite Motors",
            "owner_email": "owner@autoelite.demo",
            "owner_phone": "+919876550001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "100 OMR Road, Sholinganallur, Chennai – 600119",
            "location": "https://maps.google.com/?q=AutoElite+Motors+Chennai",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR"},
            "delivery_config": {}, "smtp_config": {},
            "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {"no_show_block_threshold": 2},
            "appointments": {"slot_duration_minutes": 60, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        "customers": customers,
        "professionals": [
            {
                "tenant": tenant_id,
                "professional_id": _prof_id(tenant_id, n, n.split()[2]),
                "employee_id": eid,
                "name": n, "short_name": n.split()[2],
                "price": 0.0, "specialization": s, "slots": slots,
                "active": True, "created_at": NOW, "is_mock": True,
            }
            for n, eid, s in [
                ("Sales Rep Raj Kumar",  "AE-S001", "SUVs & Premium Segment"),
                ("Sales Rep Priya Nair", "AE-S002", "Hatchbacks & Sedans"),
                ("Sales Rep Sanjay M",   "AE-S003", "EVs & Luxury Segment"),
            ]
        ],
        "services": [
            {"tenant": tenant_id, "name": "Test Drive – 30 Min",    "description": "In-city test drive with sales consultant", "price": 0, "duration": 60, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Finance Consultation",   "description": "EMI options & loan eligibility check",     "price": 0, "duration": 30, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Trade-in Evaluation",    "description": "Old car valuation & exchange offer",       "price": 0, "duration": 45, "active": True, "created_at": NOW, "is_mock": True},
        ],
        "staff": [
            {
                "tenant": tenant_id, "id": f"staff_{tenant_id}_{i}",
                "name": name, "role": role,
                "phone": f"+91987655{100 + i}", "email": f"staff{i}@autoelite.demo",
                "skills": skills, "active": True,
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            }
            for i, (name, role, skills) in enumerate([
                ("Deepa Reception",   "receptionist", ["appointment", "customer_greeting"]),
                ("Finance Manager",   "assistant",    ["loan", "emi_calculation"]),
            ], start=1)
        ],
        "appointments": appts,
        "categories": [{"tenant": tenant_id, "name": cat, "active": True, "is_mock": True} for cat in categories],
        "products": products,
        "inventory": inventory,
        "promotions": [
            {
                "tenant": tenant_id, "name": "Test Drive Weekend Event",
                "channel": "both",
                "message": "🚗 *Test Drive Weekend at AutoElite Motors!*\n\nDrive the latest SUVs, Sedans & EVs this Saturday & Sunday.\n\n⏰ 10 AM – 6 PM\n📍 100 OMR Road, Sholinganallur, Chennai\n\nPre-book your slot and get a *₹5,000 accessory voucher* on purchase!\n\nCall +91 98765 50001 or reply *book* to schedule.",
                "audience": {"type": "all"}, "status": "active",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Year-End Exchange Offer – SMS",
                "channel": "sms",
                "message": "AutoElite Motors: Exchange your old car & drive home a new one! Get up to Rs.50,000 extra on your old car. Offer valid till month end. Visit 100 OMR Road Chennai or call +91 98765 50001. T&C apply.",
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "🚗 Welcome to *AutoElite Motors*!\n\nReply:\n1️⃣ Book a test drive\n2️⃣ Browse car models\n3️⃣ Finance & EMI options\n4️⃣ Showroom location & timings\n5️⃣ Talk to a sales rep"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "exact", "value": "book"},
             "action": {"kind": "invoke_action", "action_id": "workflow.car_testdrive_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_finance",
             "match": {"type": "contains", "value": "emi"},
             "action": {"kind": "static_text", "text": "💳 *Finance & EMI Options*\n\nWe partner with leading banks for easy car loans:\n• HDFC Bank – 8.5% p.a.\n• ICICI Bank – 8.75% p.a.\n• SBI – 8.25% p.a.\n• Bajaj Finserv – special rates\n\nDown payment as low as 10%. Zero processing fee this month!\n\nReply *book* for a finance consultation."},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_timing",
             "match": {"type": "contains", "value": "timing"},
             "action": {"kind": "static_text", "text": "⏰ *Showroom Timings*\n\nMon–Sat: 9 AM – 7 PM\nSun: 10 AM – 5 PM\n\n📍 100 OMR Road, Sholinganallur, Chennai – 600119\n📞 +91 98765 50001"},
             "enabled": True, "priority": 7, "is_mock": True},
        ],
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "car_testdrive_flow",
                "name": "Test Drive Booking",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Select service type:",             "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",      "label": "Choose a date for your visit:",    "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",      "label": "Choose a time slot:",              "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your test drive",          "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",              "label": "✅ Test drive booked! Please carry your driving licence. Our sales rep will be ready for you. 🚗", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "car_advisor_flow",
                "name": "Book with Sales Advisor",
                "description": "Choose advisor → service → date → time → confirm.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_PROFESSIONALS","label": "Choose your sales advisor:",       "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SHOW_SERVICES",     "label": "Select appointment type:",        "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",       "label": "Choose a date for your visit:",   "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",       "label": "Choose a time slot:",             "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",   "label": "Confirm your appointment",        "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",               "label": "✅ Appointment confirmed with your advisor! Bring a valid ID. 🚗", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "car_express_flow",
                "name": "Express Visit Booking",
                "description": "Select appointment type and date — slot auto-assigned.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Select appointment type:",          "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",      "label": "Choose a date for your visit:",    "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your visit",               "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",              "label": "✅ Visit booked! Advisor will be assigned. Please carry your driving licence. 🚗", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "car_reschedule_flow",
                "name": "Reschedule Visit / Test Drive",
                "description": "Lists existing bookings and re-books on a new date/time.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "RESCHEDULE_APPOINTMENT", "label": "Which appointment would you like to reschedule?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your visit has been rescheduled! Reply *hi* for main menu. 🚗", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "car_cancel_flow",
                "name": "Cancel Visit / Test Drive",
                "description": "Lists existing bookings and cancels the chosen one.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "CANCEL_APPOINTMENT", "label": "Which appointment would you like to cancel?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your appointment has been cancelled. Reply *hi* for main menu. 🚗", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "AutoElite Motors – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *AutoElite Motors* 🚗",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Book a Test Drive",      "next": "workflow.car_testdrive_flow"},
                                {"key": "2", "label": "Book with Advisor",      "next": "workflow.car_advisor_flow"},
                                {"key": "3", "label": "Express Visit Booking",  "next": "workflow.car_express_flow"},
                                {"key": "4", "label": "Reschedule Visit",       "next": "workflow.car_reschedule_flow"},
                                {"key": "5", "label": "Cancel Visit",           "next": "workflow.car_cancel_flow"},
                                {"key": "6", "label": "Browse Our Cars",        "next": "cars_info"},
                                {"key": "7", "label": "Finance & EMI Plans",    "next": "finance_info"},
                                {"key": "8", "label": "Showroom Location",      "next": "location_info"},
                            ],
                        },
                        {
                            "id": "cars_info",
                            "type": "submenu",
                            "title": "🚗 *Our Car Range*",
                            "prompt": "Select a category to explore:",
                            "options": [
                                {"key": "1", "label": "Hatchbacks & Sedans",    "next": "hatch_info"},
                                {"key": "2", "label": "SUVs & Crossovers",      "next": "suv_info"},
                                {"key": "3", "label": "Electric Vehicles (EV)", "next": "ev_info"},
                                {"key": "0", "label": "⬅️ Main Menu",           "next": "main"},
                            ],
                        },
                        {
                            "id": "hatch_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🚗 *Hatchbacks & Sedans*\n\n"
                                "• Swift VXi – ₹6.49 L (Ex-showroom)\n"
                                "• Baleno Alpha – ₹8.90 L\n"
                                "• City ZX – ₹15.30 L\n"
                                "• Verna SX(O) – ₹17.49 L\n\n"
                                "EMI from ₹8,500/month (36 months)\n\n"
                                "Reply *1* to book a test drive!"
                            ),
                        },
                        {
                            "id": "suv_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🚙 *SUVs & Crossovers*\n\n"
                                "• Brezza ZXi+ – ₹13.96 L\n"
                                "• Creta SX(O) Turbo – ₹19.45 L\n"
                                "• Thar LX Diesel – ₹16.78 L\n"
                                "• XUV700 AX7 Petrol – ₹24.99 L\n\n"
                                "All prices are ex-showroom, Hyderabad.\n\n"
                                "Reply *1* to book a test drive!"
                            ),
                        },
                        {
                            "id": "ev_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "⚡ *Electric Vehicles*\n\n"
                                "• Tata Nexon EV Max – ₹19.54 L\n"
                                "• MG ZS EV Excite+ – ₹22.58 L\n"
                                "• Hyundai Ioniq 5 – ₹44.95 L\n\n"
                                "🔋 Range: 300–450 km per charge\n"
                                "🏠 Home charger installation included!\n\n"
                                "Reply *1* to book a test drive!"
                            ),
                        },
                        {
                            "id": "finance_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "💳 *Finance & EMI Plans*\n\n"
                                "• Zero down payment options available\n"
                                "• EMI from ₹8,500/month\n"
                                "• Loan tenure: 12–84 months\n"
                                "• Interest rate: 7.5% – 9.5% p.a.\n\n"
                                "Partner banks: SBI, HDFC, ICICI, Axis\n\n"
                                "📞 Call our finance desk: +91 98765 30001\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "service_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🔧 *Service & Maintenance*\n\n"
                                "• Free first service for all new cars\n"
                                "• Periodic service: every 10,000 km\n"
                                "• Express service available (2–4 hrs)\n"
                                "• Genuine spare parts used\n\n"
                                "📞 Service booking: +91 98765 30002\n"
                                "⏰ Service centre: Mon–Sat 8 AM – 6 PM\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "location_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📍 *AutoElite Motors*\n"
                                "45 Banjara Hills Rd No. 12, Hyderabad – 500034\n\n"
                                "🕐 Mon–Sat: 9 AM – 7 PM\n"
                                "🕐 Sunday: 10 AM – 5 PM\n\n"
                                "📞 Sales: +91 98765 30001\n"
                                "🗺 https://maps.google.com/?q=AutoElite+Motors+Hyderabad\n\n"
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
