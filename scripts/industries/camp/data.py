"""Bulk demo data for Adventure Camp (Summer/Weekend Camp)."""
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


def get_tenant_id() -> str:
    return "ss_business_camp"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    slots = [{"time": t, "status": "available"} for t in ["09:00", "10:00", "11:00", "14:00", "15:00"]]
    modules, capabilities = get_modules_capabilities()
    parents = [
        ("Suresh Rajan",   "+919876540001", "p1@adventurecamp.demo"),
        ("Meena Pillai",   "+919876540002", "p2@adventurecamp.demo"),
        ("Arvind Nair",    "+919876540003", "p3@adventurecamp.demo"),
        ("Shalini Kumar",  "+919876540004", "p4@adventurecamp.demo"),
        ("Deepak Bose",    "+919876540005", "p5@adventurecamp.demo"),
        ("Priya Menon",    "+919876540006", "p6@adventurecamp.demo"),
        ("Ramesh Iyer",    "+919876540007", "p7@adventurecamp.demo"),
        ("Nithya Sivan",   "+919876540008", "p8@adventurecamp.demo"),
    ]
    appts = []
    for i in range(20):
        d = NOW + dt.timedelta(days=i % 14 - 5)
        start = d.replace(hour=9, minute=0)
        pname, pphone, _ = parents[i % len(parents)]
        instr = ["Instructor Ravi Shankar", "Instructor Sneha Pillai", "Instructor Mohan Doss"][i % 3]
        appts.append({
            "tenant": tenant_id, "id": f"CAMP-{200 + i}",
            "customer_name": pname, "customer_phone": pphone,
            "professional": instr,
            "service": ["Day Camp – Adventure", "Day Camp – Arts & Craft", "Swimming Session"][i % 3],
            "time": "09:00", "price": 1200.0,
            "status": "completed" if i < 8 else "booked",
            "created_at": NOW - dt.timedelta(days=3), "start": start,
            "end": start + dt.timedelta(hours=4),
            "created_by": "seed", "is_mock": True,
        })
    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "pro", "category": "salon",
            "business_name": "Adventure Camp",
            "display_name": "Adventure Camp",
            "owner_email": "director@adventurecamp.demo",
            "owner_phone": "+919876540001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "Eco Park, Ooty Road, Coimbatore – 641035",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR"},
            "delivery_config": {}, "smtp_config": {},
            "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {"no_show_block_threshold": 2},
            "appointments": {"slot_duration_minutes": 240, "timezone": DEFAULT_TIMEZONE},
            "is_mock": True,
        },
        "customers": [
            {"tenant": tenant_id, "phone": phone, "phone_number": _pn(phone),
             "name": name, "email": email,
             "tags": ["parent"], "active": True, "no_show_count": 0, "created_at": NOW, "is_mock": True}
            for name, phone, email in parents
        ],
        "professionals": [
            {"tenant": tenant_id,
             "professional_id": _prof_id(tenant_id, n, n.split()[1]),
             "employee_id": eid,
             "name": n, "short_name": n.split()[1], "price": 1200.0,
             "specialization": s, "slots": slots, "active": True, "created_at": NOW, "is_mock": True}
            for n, eid, s in [
                ("Instructor Ravi Shankar",  "AC-I001", "Outdoor Adventure & Survival"),
                ("Instructor Sneha Pillai",  "AC-I002", "Arts, Crafts & Creative Activities"),
                ("Instructor Mohan Doss",    "AC-I003", "Swimming & Water Sports"),
            ]
        ],
        "services": [
            {"tenant": tenant_id, "name": "Day Camp – Adventure",   "description": "Trekking, rock climbing & team games", "price": 1200, "duration": 240, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Day Camp – Arts & Craft", "description": "Painting, pottery and creative arts", "price": 800,  "duration": 180, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Swimming Session",       "description": "2-hour supervised swimming & water games", "price": 500, "duration": 120, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Weekend Package (2 days)","description": "Full 2-day outdoor adventure package",   "price": 2000, "duration": 480, "active": True, "created_at": NOW, "is_mock": True},
        ],
        "staff": [
            {"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Camp Coordinator",
             "role": "receptionist", "phone": "+919876540001", "email": "coord@adventurecamp.demo",
             "skills": ["registration", "scheduling"], "active": True,
             "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "appointments": appts,
        "categories": [], "products": [], "inventory": [],
        "promotions": [
            {
                "tenant": tenant_id, "name": "Summer Camp Enrollment Open",
                "channel": "both",
                "message": "🏕️ *Adventure Camp – Summer 2026 is OPEN!*\n\nEnroll your child for an unforgettable experience:\n🧗 Rock climbing & trekking\n🎨 Arts & crafts\n🏊 Swimming lessons\n\nEarly bird discount: ₹200 off for registrations before May 1st!\n\nLimited seats. Reply *book* or call +91 98765 40001.",
                "audience": {"type": "all"}, "status": "active",
                "offer_code": "EARLY200",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id, "name": "Camp Reminder – SMS",
                "channel": "sms",
                "message": "Adventure Camp reminder: Camp starts this Monday! Bring sunscreen, water bottle & comfortable shoes. Gate opens at 8:30 AM. Questions? Call +91 98765 40001.",
                "audience": {"type": "all"}, "status": "draft",
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "🏕️ Welcome to *Adventure Camp*!\n\nReply:\n1️⃣ Enroll for summer camp\n2️⃣ Camp schedule & activities\n3️⃣ Fees & packages\n4️⃣ Location & timings"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "contains", "value": "book,enroll,register,camp"},
             "action": {"kind": "invoke_action", "action_id": "workflow.camp_booking_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_fees",
             "match": {"type": "contains", "value": "fee"},
             "action": {"kind": "static_text", "text": "💰 *Camp Fees*\n\n• Day Camp – Adventure: ₹1,200/day\n• Day Camp – Arts: ₹800/day\n• Swimming Session: ₹500\n• Weekend Package (2 days): ₹2,000\n\n*Early bird discount*: ₹200 off before 1st May!\n\nCall +91 98765 40001 to enroll."},
             "enabled": True, "priority": 7, "is_mock": True},
        ],
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "camp_booking_flow",
                "name": "Camp Session Enrollment",
                "description": "No counselor selection — counselor auto-assigned. Use camp_counselor_flow to pick a specific one.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    # No SHOW_PROFESSIONALS + no SELECT_TIME → date-only, no-professional booking
                    # Smart detection handles both automatically — no PRESET_PROFESSIONAL needed
                    {"action_code": "SHOW_SERVICES",   "label": "Select a camp program:",                "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",     "label": "Choose your preferred date:",           "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "ASK_NAME",        "label": "Please share your child's name:",       "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm enrollment",                    "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Enrollment confirmed! Pack light & come ready for adventure! 🏕️ Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "camp_counselor_flow",
                "name": "Book with Specific Counselor",
                "description": "Choose counselor → program → date → confirm.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_PROFESSIONALS","label": "Choose your camp counselor:",  "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SHOW_SERVICES",     "label": "Select a camp program:",       "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",       "label": "Choose your preferred date:",  "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",   "label": "Confirm enrollment",           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",               "label": "✅ Enrolled with your counselor! Come ready for adventure! 🏕️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "camp_quick_flow",
                "name": "Quick Camp Enrollment",
                "description": "Select program — date auto-assigned to next available.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Pick a camp program — we'll assign the next available slot:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm enrollment",                                           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Quick enrolled! We'll confirm your camp date soon. 🏕️", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "Adventure Camp – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *Adventure Camp* 🏕️",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Enroll for Camp",        "next": "workflow.camp_booking_flow"},
                                {"key": "2", "label": "Book with Counselor",    "next": "workflow.camp_counselor_flow"},
                                {"key": "3", "label": "Quick Enrollment",       "next": "workflow.camp_quick_flow"},
                                {"key": "4", "label": "Activities & Programs",  "next": "activities_info"},
                                {"key": "5", "label": "Fees & Packages",        "next": "fees_info"},
                                {"key": "6", "label": "Location & Timings",     "next": "location_info"},
                                {"key": "7", "label": "Contact Us",             "next": "contact_info"},
                            ],
                        },
                        {
                            "id": "activities_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "🏕️ *Camp Activities & Programs*\n\n"
                                "🧗 *Adventure Day Camp*\n"
                                "  Rock climbing, trekking & team games (4 hours)\n\n"
                                "🎨 *Arts & Craft Day Camp*\n"
                                "  Painting, pottery & creative arts (3 hours)\n\n"
                                "🏊 *Swimming Sessions*\n"
                                "  Supervised swimming & water games (2 hours)\n\n"
                                "🏕️ *Weekend Package (2 days)*\n"
                                "  Full outdoor adventure with bonfire & camping\n\n"
                                "Age group: 6–16 years\n\n"
                                "Reply *1* to enroll your child!"
                            ),
                        },
                        {
                            "id": "fees_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "💰 *Fees & Packages*\n\n"
                                "• Day Camp – Adventure: ₹1,200/day\n"
                                "• Day Camp – Arts & Craft: ₹800/day\n"
                                "• Swimming Session: ₹500\n"
                                "• Weekend Package (2 days): ₹2,000\n\n"
                                "🎁 Early Bird Discount: ₹200 off before 1st May!\n"
                                "Use code: *EARLY200*\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "location_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📍 *Adventure Camp*\n"
                                "Eco Park, Ooty Road, Coimbatore – 641035\n\n"
                                "⏰ Camp Hours: 9 AM – 5 PM\n"
                                "🚪 Gates open at 8:30 AM\n\n"
                                "📞 +91 98765 40001\n"
                                "🗺 https://maps.google.com/?q=Adventure+Camp+Coimbatore\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "contact_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📞 *Contact Adventure Camp*\n\n"
                                "📞 Phone: +91 98765 40001\n"
                                "📧 Email: director@adventurecamp.demo\n\n"
                                "We are available Mon–Sat 8 AM – 6 PM.\n\n"
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
