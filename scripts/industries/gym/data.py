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
                # ── PT / Training sessions ── duration drives booking slot per session ──
                ("PT Session – 1 Hr",    "Personal training with dedicated trainer (60 min)",  400, 60),
                ("PT Session – 30 Min",  "Express personal training session (30 min)",         250, 30),
                ("PT Session – 20 Min",  "Quick form-check or warm-up PT (20 min)",            150, 20),
                # ── Group / classes ──
                ("Group Class",          "Zumba / Yoga / Aerobics group class (60 min)",       200, 60),
                ("Diet Consultation",    "1-on-1 nutrition & diet planning (45 min)",          600, 45),
                ("Body Composition",     "Body fat % + lean mass measurement (20 min)",         300, 20),
                # ── Sports court bookings ── duration = single court slot length ──
                # For 2-hr court booking use SELECT_TIME with max_slots=2 in workflow params
                ("Badminton Court",      "Badminton court booking — 60 min slot",              300, 60),
                ("Squash Court",         "Squash court booking — 30 min slot",                 200, 30),
                ("Tennis Court",         "Tennis court booking — 90 min slot",                 400, 90),
                ("Swimming Lane",        "Swimming lane rental — 45 min slot",                 250, 45),
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
            {"tenant": tenant_id, "trigger_id": "trigger_court",
             "match": {"type": "contains", "value": "court,badminton,squash,tennis,swimming,pool"},
             "action": {"kind": "invoke_action", "action_id": "workflow.gym_court_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "contains", "value": "book,session,class,schedule"},
             "action": {"kind": "invoke_action", "action_id": "workflow.gym_booking_flow"},
             "enabled": True, "priority": 8, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_membership",
             "match": {"type": "contains", "value": "membership"},
             "action": {"kind": "static_text", "text": "💳 *Membership Plans*\n\n• Monthly: ₹1,500/month\n• Quarterly: ₹3,999 (save ₹500)\n• Half-Yearly: ₹7,000 (save ₹1,000)\n• Annual: ₹12,000 (save ₹6,000)\n\nAll plans include: Locker + WiFi + Basic equipment use.\nVisit us at 45 T. Nagar or call +91 98765 20001."},
             "enabled": True, "priority": 7, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_timing",
             "match": {"type": "contains", "value": "timing"},
             "action": {"kind": "static_text", "text": "⏰ *FitZone Gym Timings*\n\nMon–Fri: 5:30 AM – 10 PM\nSat–Sun: 6 AM – 8 PM\n\n📍 45 T. Nagar, Chennai – 600017\n\nFor class schedules reply *schedule*."},
             "enabled": True, "priority": 6, "is_mock": True},
        ],
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "gym_booking_flow",
                "name": "PT Session Booking (auto trainer)",
                "description": "Shows only PT/class services. Trainer auto-assigned. No professional selection menu.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    # No SHOW_PROFESSIONALS → system auto-detects no-professional mode
                    # No PRESET_PROFESSIONAL needed — smart detection handles it
                    {"action_code": "SHOW_SERVICES",
                     "label": "Choose a session type:",
                     "input_required": True, "ui_type": "list",
                     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "PT Session – 20 Min", "Group Class", "Diet Consultation", "Body Composition"]}},
                    {"action_code": "SELECT_DATE", "label": "Choose your preferred date:", "input_required": True, "ui_type": "list", "params": {}},
                    # slot_duration_minutes auto-read from selected service
                    {"action_code": "SELECT_TIME", "label": "Choose a time slot:", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "ASK_NAME",    "label": "Your name please:",    "input_required": True, "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your session",  "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Session booked! Come ready to sweat 💪 Reply *hi* for the main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "gym_trainer_flow",
                "name": "Book with Personal Trainer",
                "description": "Choose trainer → PT session type → date → time → confirm.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_PROFESSIONALS", "label": "Choose your trainer:",           "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "SHOW_SERVICES",
                     "label": "Choose a session type:",
                     "input_required": True, "ui_type": "list",
                     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "PT Session – 20 Min"]}},
                    {"action_code": "SELECT_DATE",        "label": "Choose your preferred date:",    "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",        "label": "Choose a time slot:",            "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "ASK_NAME",           "label": "Your name please:",              "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",    "label": "Confirm your session",           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",                "label": "✅ Booked with your trainer! See you at the gym 💪", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "gym_quick_flow",
                "name": "Quick Session Booking",
                "description": "Pick PT/class session — date and slot auto-assigned.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",
                     "label": "Pick a session — we'll book the next available slot:",
                     "input_required": True, "ui_type": "list",
                     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "Group Class"]}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your session",              "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Quick booked! Trainer and slot auto-assigned. Reply *hi* for main menu. 🏋️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                # ── MULTI-SLOT: Badminton Court — 2 × 60 min = 2-hr block ──────────
                # slot_duration_minutes is NOT set here — the system reads it from
                # the selected "Badminton Court" service duration (60 min) automatically.
                # max_slots=2 means: reserve 2 consecutive 60-min slots = 2 hours total.
                "tenant": tenant_id,
                "workflow_id": "gym_court_flow",
                "name": "Badminton / Sports Court Booking",
                "description": "Book a court for 1 or 2 hours. Duration auto-read from service. User selects start time.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    # No SHOW_PROFESSIONALS → system auto-detects court-as-resource mode
                    # No PRESET_PROFESSIONAL needed — smart detection handles it
                    # slot_duration_minutes auto-read from selected service:
                    #   Badminton 60 min | Squash 30 min | Tennis 90 min | Swimming 45 min
                    {"action_code": "SHOW_SERVICES",
                     "label": "Select court / lane type:",
                     "input_required": True, "ui_type": "list",
                     "params": {"services": ["Badminton Court", "Squash Court", "Tennis Court", "Swimming Lane"]}},
                    {"action_code": "SELECT_DATE", "label": "Choose your preferred date:", "input_required": True, "ui_type": "list", "params": {}},
                    # ASK_NUM_SLOTS: user chooses 1h or 2h
                    {"action_code": "ASK_NUM_SLOTS",
                     "label": "How many hours would you like to book?",
                     "input_required": True, "ui_type": "list",
                     "params": {"max_slots": 2, "slot_label": "hour"}},
                    # SELECT_TIME auto-shows service-filtered, booked-slots-removed hourly list
                    {"action_code": "SELECT_TIME",
                     "label": "Choose your start time:",
                     "input_required": True, "ui_type": "list",
                     "params": {"time_slots": ["06:00","07:00","08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00","18:00","19:00"]}},
                    {"action_code": "ASK_NAME",        "label": "Your name please:",          "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your court booking", "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Court booked! Please arrive 5 min early. 🏸 Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                # ── SINGLE-SLOT: PT Session — duration from selected service ─────────
                # PT Session – 1 Hr (60 min), PT Session – 30 Min (30 min), PT Session – 20 Min (20 min)
                "tenant": tenant_id,
                "workflow_id": "gym_pt_session_flow",
                "name": "PT Session Booking (any duration)",
                "description": "Book a PT session (20/30/60 min). Duration auto-set from selected service. Trainer selection included.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    # Only PT services — courts excluded
                    {"action_code": "SHOW_SERVICES",
                     "label": "Choose PT session type (20/30/60 min available):",
                     "input_required": True, "ui_type": "list",
                     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "PT Session – 20 Min"]}},
                    {"action_code": "SHOW_PROFESSIONALS", "label": "Choose your trainer:",                              "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",        "label": "Choose your preferred date:",                       "input_required": True,  "ui_type": "list", "params": {}},
                    # slot_duration_minutes NOT set → reads from selected service (20, 30, or 60 min)
                    {"action_code": "SELECT_TIME",        "label": "Choose a time slot:",                              "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "ASK_NAME",           "label": "Your name please:",                                "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",    "label": "Confirm your PT session",                         "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",                "label": "✅ PT session booked! Your trainer will be ready. 💪 Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "gym_reschedule_flow",
                "name": "Reschedule Booking",
                "description": "Lists existing bookings, confirms choice, then re-books on a new date/time.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "RESCHEDULE_APPOINTMENT", "label": "Which booking would you like to reschedule?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your booking has been rescheduled! Reply *hi* for main menu. 💪", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "gym_cancel_flow",
                "name": "Cancel Booking",
                "description": "Lists existing bookings and cancels the chosen one.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "CANCEL_APPOINTMENT", "label": "Which booking would you like to cancel?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your booking has been cancelled. Reply *hi* for main menu. 💪", "input_required": False, "ui_type": "list", "params": {}},
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
                                {"key": "1", "label": "Book PT Session (20/30/60 min)", "next": "workflow.gym_pt_session_flow"},
                                {"key": "2", "label": "Book Session (auto trainer)",    "next": "workflow.gym_booking_flow"},
                                {"key": "3", "label": "Book with Trainer",              "next": "workflow.gym_trainer_flow"},
                                {"key": "4", "label": "Quick Session Booking",          "next": "workflow.gym_quick_flow"},
                                {"key": "5", "label": "Book Sports Court",              "next": "workflow.gym_court_flow"},
                                {"key": "6", "label": "Reschedule Booking",            "next": "workflow.gym_reschedule_flow"},
                                {"key": "7", "label": "Cancel Booking",                "next": "workflow.gym_cancel_flow"},
                                {"key": "8", "label": "Membership Plans",              "next": "membership_info"},
                                {"key": "9", "label": "Location & Timings",            "next": "location_info"},
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
