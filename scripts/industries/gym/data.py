"""
Bulk demo data for FitZone Gym.
Covers: trainers, members, PT sessions, membership plans,
equipment products, promotions (WA / email / SMS), session booking
workflow, and rich WhatsApp triggers.
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
    "gym":       "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=400&q=80",
    "protein":   "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=400&q=80",
    "gloves":    "https://images.unsplash.com/photo-1517963879433-6ad2b056d712?auto=format&fit=crop&w=400&q=80",
    "bottle":    "https://images.unsplash.com/photo-1576426863848-c21f53c60b19?auto=format&fit=crop&w=400&q=80",
    "band":      "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=400&q=80",
}


def get_tenant_id() -> str:
    return "ss_business_gym"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots_morning = [{"time": t, "status": "available"} for t in ["06:00", "06:30", "07:00", "07:30", "08:00", "08:30"]]
    slots_evening = [{"time": t, "status": "available"} for t in ["17:00", "17:30", "18:00", "18:30", "19:00", "19:30"]]
    slots_all = slots_morning + slots_evening

    modules, capabilities = get_modules_capabilities()

    customers = [
        {
            "tenant": tenant_id,
            "phone": f"+9198765200{i:02d}",
            "phone_number": _pn(f"+9198765200{i:02d}"),
            "name": name, "email": f"m{i}@fitzonegs.demo",
            "tags": tags, "active": True, "no_show_count": ns,
            "created_at": NOW - dt.timedelta(days=i * 20),
            "is_mock": True,
        }
        for i, (name, ns, tags) in enumerate([
            ("Rahul Menon",       0, ["member", "morning"]),
            ("Priya Krishnan",    1, ["member", "evening"]),
            ("Amit Singh",        0, ["member", "morning"]),
            ("Deepa Nair",        0, ["member", "pt-client"]),
            ("Suresh Babu",       2, ["member"]),
            ("Kavitha Iyer",      0, ["member", "pt-client"]),
            ("Arjun Rajan",       0, ["member", "morning"]),
            ("Meena Pillai",      1, ["member"]),
            ("Karthik Siva",      0, ["member", "evening"]),
            ("Lakshmi Gopal",     0, ["member", "pt-client", "vip"]),
            ("Sanjay Kumar",      0, ["member"]),
            ("Asha Venkat",       0, ["member", "morning"]),
        ], start=1)
    ]

    base = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
    appts = []
    for i in range(30):
        d = base + dt.timedelta(days=i - 10)
        t = "07:00" if i % 2 == 0 else "18:00"
        start = d.replace(hour=int(t.split(":")[0]), minute=0)
        end = start + dt.timedelta(hours=1)
        cust = customers[i % len(customers)]
        trainer = ["Trainer Mike Johnson", "Trainer Anjali Sharma", "Trainer Suresh Kumar"][i % 3]
        appts.append({
            "tenant": tenant_id,
            "id": f"FZ-{1000 + i}",
            "customer_name": cust["name"],
            "customer_phone": cust["phone"],
            "professional": trainer,
            "service": "PT Session",
            "time": t, "price": 400.0,
            "status": "completed" if i < 10 else "booked",
            "created_at": NOW - dt.timedelta(days=abs(i - 10) + 1),
            "start": start, "end": end,
            "created_by": "seed", "is_mock": True,
        })

    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "pro", "category": "salon",  # gym uses appointments module like salon
            "business_name": "FitZone Gym",
            "display_name": "FitZone Gym",
            "owner_email": "owner@fitzonegs.demo",
            "owner_phone": "+919876520001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "45 T. Nagar, Chennai – 600017",
            "location": "https://maps.google.com/?q=FitZone+Gym+Chennai",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR"},
            "delivery_config": {}, "smtp_config": {},
            "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {"no_show_block_threshold": 2, "no_show_reminder_lead_hours": 12},
            "appointments": {"slot_duration_minutes": 60, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        "customers": customers,
        "professionals": [
            {
                "tenant": tenant_id,
                "professional_id": _prof_id(tenant_id, name, short),
                "employee_id": eid,
                "name": name, "short_name": short,
                "price": 400.0, "specialization": spec,
                "slots": slots_all,
                "active": True, "created_at": NOW, "is_mock": True,
            }
            for name, short, eid, spec in [
                ("Trainer Mike Johnson",  "Mike",   "FZ-T001", "Strength & Conditioning"),
                ("Trainer Anjali Sharma", "Anjali", "FZ-T002", "Yoga & Flexibility"),
                ("Trainer Suresh Kumar",  "Suresh", "FZ-T003", "Cardio & Weight Loss"),
            ]
        ],
        "services": [
            {"tenant": tenant_id, "name": n, "description": d, "price": p, "duration": dur,
             "active": True, "created_at": NOW, "is_mock": True}
            for n, d, p, dur in [
                ("PT Session – 1 Hr",    "Personal training with dedicated trainer",     400, 60),
                ("Group Class",          "Zumba / Yoga / Aerobics group class",          200, 60),
                ("Monthly Membership",   "Unlimited gym access, 30 days",               1500, 30),
                ("Quarterly Membership", "Unlimited gym access, 90 days",               3999, 90),
                ("Diet Consultation",    "1-on-1 nutrition & diet planning session",     600, 45),
                ("Body Composition",     "Body fat % + lean mass measurement report",    300, 20),
            ]
        ],
        "staff": [
            {
                "tenant": tenant_id, "id": f"staff_{tenant_id}_{i}",
                "name": name, "role": role,
                "phone": f"+91987652{100 + i}", "email": f"staff{i}@fitzonegs.demo",
                "skills": skills, "active": True,
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            }
            for i, (name, role, skills) in enumerate([
                ("Deepak Front Desk",  "receptionist", ["membership", "billing"]),
                ("Nisha Instructor",   "assistant",    ["group_classes", "zumba"]),
            ], start=1)
        ],
        "appointments": appts,
        "categories": [
            {"tenant": tenant_id, "name": "Supplements", "active": True, "is_mock": True},
            {"tenant": tenant_id, "name": "Accessories",  "active": True, "is_mock": True},
        ],
        "products": [
            {
                "tenant": tenant_id, "sku": sku, "name": name, "category": cat,
                "price": float(price), "mrp": float(mrp), "active": True, "unit": "pcs",
                "description": desc, "image_urls": [img], "image_url": img,
                "is_mock": True,
            }
            for sku, name, cat, price, mrp, desc, img in [
                ("GYM-001", "Whey Protein 1kg (Chocolate)",  "Supplements", 1299, 1599,
                 "24g protein per serving, 5.5g BCAA, no added sugar. Mixes easily with water or milk.", _IMG["protein"]),
                ("GYM-002", "Creatine Monohydrate 250g",     "Supplements",  599,  699,
                 "Unflavoured micronised creatine. Increases strength and power output.", _IMG["protein"]),
                ("GYM-003", "Workout Gloves (M/L/XL)",       "Accessories",  349,  449,
                 "Anti-slip palm, wrist support, breathable mesh back. Unisex.", _IMG["gloves"]),
                ("GYM-004", "Gym Water Bottle 1L",            "Accessories",  299,  399,
                 "BPA-free Tritan bottle with measurement markings and carry loop.", _IMG["bottle"]),
                ("GYM-005", "Resistance Band Set (5 pcs)",    "Accessories",  499,  649,
                 "5 resistance levels (2–45 kg). Latex-free, suitable for physiotherapy.", _IMG["band"]),
            ]
        ],
        "inventory": [
            {"tenant": tenant_id, "sku": f"GYM-00{i}", "available_qty": qty, "is_mock": True}
            for i, qty in enumerate([30, 50, 40, 80, 60], start=1)
        ],
        "promotions": [
            {
                "tenant": tenant_id, "name": "New Member – First Month Free",
                "channel": "both",
                "message": "💪 *Join FitZone Gym Today!*\n\nGet your *FIRST MONTH FREE* on a 3-month membership.\n\n📍 45 T. Nagar, Chennai\n⏰ Open 5:30 AM – 10 PM daily\n\nUse code *NEWFIT* at reception. Offer valid this month only!",
                "audience": {"type": "all"}, "status": "active",
                "offer_code": "NEWFIT",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "PT Package – 12 Sessions",
                "channel": "whatsapp",
                "message": "🏋️ *Personal Training Package*\n\nBook 12 PT sessions and get *2 FREE*! With certified trainers Mike, Anjali & Suresh.\n\nAvailable morning & evening slots. Nutrition plan included.",
                "interactive_type": "cta_url",
                "cta_entries": [{"id": "cta_1", "display_text": "Book PT Session", "url": "https://wa.me/+919876520001?text=PT+Package"}],
                "cta_append_urls_to_body": True,
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Weekend Membership Drive – SMS",
                "channel": "sms",
                "message": "FitZone Gym: Quarterly membership at Rs.3,999 (save Rs.200). Includes unlimited gym access + 1 free PT session. Limited slots. Call +91 98765 20001 or visit 45 T.Nagar Chennai. Code: FIT3M",
                "audience": {"type": "all"}, "status": "draft",
                "offer_code": "FIT3M",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "💪 Welcome to *FitZone Gym*!\n\nReply:\n1️⃣ Book PT session\n2️⃣ Membership plans\n3️⃣ Class schedule\n4️⃣ Location & timings\n5️⃣ Talk to us"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "exact", "value": "book"},
             "action": {"kind": "workflow", "workflow_id": "gym_booking_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_membership",
             "match": {"type": "contains", "value": "membership"},
             "action": {"kind": "static_text", "text": "💳 *Membership Plans*\n\n• Monthly: ₹1,500/month\n• Quarterly: ₹3,999 (save ₹500)\n• Half-Yearly: ₹7,000 (save ₹1,000)\n• Annual: ₹12,000 (save ₹6,000)\n\nAll plans include: Locker + WiFi + Basic equipment use.\nVisit us at 45 T. Nagar or call +91 98765 20001."},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_timing",
             "match": {"type": "contains", "value": "timing"},
             "action": {"kind": "static_text", "text": "⏰ *FitZone Gym Timings*\n\nMon–Fri: 5:30 AM – 10 PM\nSat–Sun: 6 AM – 8 PM\n\n📍 45 T. Nagar, Chennai – 600017\n\nFor class schedules reply *schedule*."},
             "enabled": True, "priority": 7, "is_mock": True},
        ],
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "gym_booking_flow",
                "name": "PT Session Booking",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Choose a session type:",       "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",      "label": "Choose your preferred date:",   "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",      "label": "Choose morning or evening slot:","input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your session",          "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",              "label": "✅ Session booked! Come ready to sweat 💪 Reply *hi* for the main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "FitZone Gym – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *FitZone Gym* 💪",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Book PT Session",       "next": "workflow.gym_booking_flow"},
                                {"key": "2", "label": "Membership Plans",      "next": "membership_info"},
                                {"key": "3", "label": "Class Schedule",        "next": "schedule_info"},
                                {"key": "4", "label": "Location & Timings",    "next": "location_info"},
                                {"key": "5", "label": "Talk to Us",            "next": "contact_info"},
                            ],
                        },
                        {
                            "id": "membership_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🏋️ *Membership Plans*\n\n"
                                "• Monthly – ₹1,499/month\n"
                                "• Quarterly – ₹3,999 (save ₹500)\n"
                                "• Half-Yearly – ₹6,999 (save ₹2,000)\n"
                                "• Annual – ₹11,999 (save ₹6,000)\n\n"
                                "All plans include:\n"
                                "✅ Unlimited gym access\n"
                                "✅ Locker & shower\n"
                                "✅ 1 free nutrition consultation\n\n"
                                "PT sessions available as add-on.\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "schedule_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📅 *Class Schedule (Weekly)*\n\n"
                                "🔥 HIIT Training – Mon, Wed, Fri: 6 AM & 6 PM\n"
                                "🧘 Yoga – Tue, Thu, Sat: 7 AM\n"
                                "🥊 Kickboxing – Mon, Wed: 7 PM\n"
                                "🚴 Cycling – Tue, Thu: 6 AM\n"
                                "💃 Zumba – Sat: 8 AM\n\n"
                                "All classes are 45–60 minutes.\n\n"
                                "Reply *book* to reserve your PT session."
                            ),
                        },
                        {
                            "id": "location_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📍 *FitZone Gym*\n"
                                "88 Indiranagar 100 Ft Rd, Bengaluru – 560038\n\n"
                                "🕐 Mon–Sat: 5:30 AM – 10 PM\n"
                                "🕐 Sunday: 7 AM – 7 PM\n\n"
                                "📞 +91 98765 20001\n"
                                "🗺 https://maps.google.com/?q=FitZone+Gym+Indiranagar\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "contact_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "💬 *Contact FitZone Gym*\n\n"
                                "📞 Phone: +91 98765 20001\n"
                                "📧 Email: hello@fitzonegym.demo\n"
                                "📷 Instagram: @FitZoneIndiranagar\n\n"
                                "We reply within 1 hour during working hours.\n\n"
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
