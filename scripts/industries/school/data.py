"""Bulk demo data for Bright Future Academy (School)."""
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
    return "ss_business_school"


def get_modules_capabilities() -> tuple[list[str], list[str]]:
    defaults = get_plan_defaults("pro")
    return defaults["modules"], defaults["capabilities"]


def get_seed_data(tenant_id: str) -> dict[str, Any]:
    modules, capabilities = get_modules_capabilities()
    slot_times = ["13:00", "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45", "15:00", "15:15"]
    teacher_slots = [{"time": t, "status": "available"} for t in slot_times]

    parents = [
        ("Rajan Krishnan",   "+919876560001", "p1@brightfuture.demo"),
        ("Sunita Devi",      "+919876560002", "p2@brightfuture.demo"),
        ("Arun Pillai",      "+919876560003", "p3@brightfuture.demo"),
        ("Preethi Nair",     "+919876560004", "p4@brightfuture.demo"),
        ("Venkat Subbu",     "+919876560005", "p5@brightfuture.demo"),
        ("Geetha Raj",       "+919876560006", "p6@brightfuture.demo"),
        ("Mahesh Kumar",     "+919876560007", "p7@brightfuture.demo"),
        ("Kavitha Anand",    "+919876560008", "p8@brightfuture.demo"),
        ("Senthil Nathan",   "+919876560009", "p9@brightfuture.demo"),
        ("Radha Krishnaswamy","+919876560010","p10@brightfuture.demo"),
    ]
    appts = []
    for i in range(20):
        d = NOW + dt.timedelta(days=(i % 10) - 5)
        t = slot_times[i % len(slot_times)]
        start = d.replace(hour=int(t.split(":")[0]), minute=int(t.split(":")[1]))
        pname, pphone, _ = parents[i % len(parents)]
        appts.append({
            "tenant": tenant_id, "id": f"BFA-{200 + i}",
            "customer_name": pname, "customer_phone": pphone,
            "professional": ["Ms. Anita Rajan", "Mr. Suresh Iyer", "Ms. Deepa Menon"][i % 3],
            "service": "Parent-Teacher Meeting",
            "time": t, "price": 0.0,
            "status": "completed" if i < 10 else "booked",
            "created_at": NOW - dt.timedelta(days=3), "start": start,
            "end": start + dt.timedelta(minutes=15),
            "created_by": "seed", "is_mock": True,
        })

    return {
        "tenant_doc": {
            "_id": tenant_id, "plan": "pro", "category": "salon",
            "business_name": "Bright Future Academy",
            "display_name": "Bright Future Academy",
            "owner_email": "principal@brightfuture.demo",
            "owner_phone": "+919876560001",
            "tz": DEFAULT_TIMEZONE,
            "modules": modules, "capabilities": capabilities, "active": True,
            "address": "8 Railway Colony, Madurai – 625001",
            "whatsapp_config": {},
            "payment_config": {"provider": "dummy", "currency": "INR"},
            "delivery_config": {}, "smtp_config": {},
            "date_format": "DD-MM-YYYY", "currency": "INR",
            "ai_config": {"no_show_block_threshold": 2},
            "appointments": {"slot_duration_minutes": 15, "timezone": DEFAULT_TIMEZONE},
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
             "name": n, "short_name": n.split()[1], "price": 0.0,
             "specialization": s, "slots": teacher_slots, "active": True, "created_at": NOW, "is_mock": True}
            for n, eid, s in [
                ("Ms. Anita Rajan",  "BFA-T001", "Class Teacher – Grade 5"),
                ("Mr. Suresh Iyer",  "BFA-T002", "Mathematics – Grades 6-8"),
                ("Ms. Deepa Menon",  "BFA-T003", "English & Science – Grade 4"),
            ]
        ],
        "services": [
            {"tenant": tenant_id, "name": "Parent-Teacher Meeting", "description": "15-min one-on-one with class teacher", "price": 0, "duration": 15, "active": True, "created_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Academic Counselling",   "description": "30-min academic performance review",  "price": 0, "duration": 30, "active": True, "created_at": NOW, "is_mock": True},
        ],
        "staff": [
            {"tenant": tenant_id, "id": f"staff_{tenant_id}_1", "name": "Office Admin",
             "role": "receptionist", "phone": "+919876560001", "email": "office@brightfuture.demo",
             "skills": ["scheduling", "records"], "active": True,
             "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "appointments": appts,
        "categories": [], "products": [], "inventory": [],
        "promotions": [
            {"tenant": tenant_id, "name": "Annual Day Invitation",
             "channel": "sms+whatsapp",
             "message": "🎓 *Bright Future Academy Annual Day* – 15th April 2026\n\nDear Parents, you are cordially invited!\n📍 School Auditorium | ⏰ 5 PM onwards\n\nKindly confirm attendance by replying YES. Children performing please arrive by 4 PM.",
             "audience": {"type": "all"}, "status": "draft",
             "created_at": NOW, "updated_at": NOW, "is_mock": True},
            {"tenant": tenant_id, "name": "Parent Meeting Schedule – SMS",
             "channel": "sms",
             "message": "Bright Future Academy: Parent-Teacher Meetings scheduled for 20th April. Book your slot at brightfuture.demo/book or call +91 98765 60001. Slots: 1 PM – 3:30 PM.",
             "attachments": [{"type": "link", "url": "https://brightfuture.demo/book", "name": "Book Slot"}],
             "audience": {"type": "all"}, "status": "draft",
             "created_at": NOW, "updated_at": NOW, "is_mock": True},
        ],
        "whatsapp_triggers": [
            {"tenant": tenant_id, "trigger_id": "welcome_hi",
             "match": {"type": "exact", "value": "hi"},
             "action": {"kind": "static_text", "text": "👋 Welcome to *Bright Future Academy*!\n\nReply:\n1️⃣ Book parent meeting\n2️⃣ School timings\n3️⃣ Academic calendar\n4️⃣ Contact office"},
             "enabled": True, "priority": 10, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_book",
             "match": {"type": "contains", "value": "book,meeting,appointment,schedule"},
             "action": {"kind": "invoke_action", "action_id": "workflow.school_meeting_flow"},
             "enabled": True, "priority": 9, "is_mock": True},
            {"tenant": tenant_id, "trigger_id": "trigger_timing",
             "match": {"type": "contains", "value": "timing"},
             "action": {"kind": "static_text", "text": "⏰ *School Timings*\n\nMon–Fri: 8 AM – 2:30 PM\nSat: 8 AM – 12 PM\n\n📞 Office: +91 98765 60001\n📍 8 Railway Colony, Madurai"},
             "enabled": True, "priority": 7, "is_mock": True},
        ],
        "workflows": [
            {
                "tenant": tenant_id,
                "workflow_id": "school_meeting_flow",
                "name": "Parent-Teacher Meeting Booking",
                "description": "No professional selection — admin auto-assigns the available teacher.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    # No SHOW_PROFESSIONALS → smart detection treats as no-professional booking
                    # No PRESET_PROFESSIONAL needed
                    {"action_code": "SHOW_SERVICES",   "label": "Select meeting type:",                      "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",     "label": "Choose a date for the meeting:",             "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",     "label": "Choose a time slot (1 PM – 3:30 PM):",      "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "ASK_NAME",        "label": "Please share your name (parent/guardian):", "input_required": True,  "ui_type": "text", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm meeting",                           "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Meeting slot confirmed! Please bring your ward's progress report. See you there! 🎓", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "school_teacher_flow",
                "name": "Meet a Specific Teacher",
                "description": "Choose teacher → meeting type → date → time → confirm.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_PROFESSIONALS","label": "Choose the teacher:",             "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SHOW_SERVICES",     "label": "Select meeting type:",            "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_DATE",       "label": "Choose a date:",                  "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "SELECT_TIME",       "label": "Choose a time slot:",             "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING",   "label": "Confirm meeting",                 "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",               "label": "✅ Meeting scheduled with the teacher! See you on the day. 📚", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "school_quick_meeting_flow",
                "name": "Quick Meeting Request",
                "description": "Select meeting type — teacher and slot auto-assigned.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "SHOW_SERVICES",   "label": "Select meeting type — teacher will be assigned:", "input_required": True,  "ui_type": "list", "params": {}},
                    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your meeting request",                     "input_required": False, "ui_type": "list", "params": {}},
                    {"action_code": "END",             "label": "✅ Meeting requested! School admin will confirm the date & time. 🎓", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "school_reschedule_flow",
                "name": "Reschedule Meeting",
                "description": "Lists existing bookings and re-books on a new date/time.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "RESCHEDULE_APPOINTMENT", "label": "Which meeting would you like to reschedule?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your meeting has been rescheduled! Reply *hi* for main menu. 🎓", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
            {
                "tenant": tenant_id,
                "workflow_id": "school_cancel_flow",
                "name": "Cancel Meeting",
                "description": "Lists existing bookings and cancels the chosen one.",
                "active": True,
                "requires_caps": ["appointments"],
                "steps": [
                    {"action_code": "CANCEL_APPOINTMENT", "label": "Which meeting would you like to cancel?", "input_required": True, "ui_type": "list", "params": {}},
                    {"action_code": "END", "label": "✅ Your meeting has been cancelled. Reply *hi* for main menu. 🎓", "input_required": False, "ui_type": "list", "params": {}},
                ],
                "created_at": NOW, "updated_at": NOW, "is_mock": True,
            },
        ],
        # ── WhatsApp Menus ────────────────────────────────────────────────────
        "whatsapp_menus": [
            {
                "tenant": tenant_id,
                "menu_id": "welcome_message",
                "name": "Bright Future Academy – Main Menu",
                "status": "published",
                "version": 1,
                "tree": {
                    "root": "main",
                    "nodes": [
                        {
                            "id": "main",
                            "type": "submenu",
                            "title": "Welcome to *Bright Future Academy* 🎓",
                            "prompt": "How can we help you today?",
                            "options": [
                                {"key": "1", "label": "Book Parent Meeting",    "next": "workflow.school_meeting_flow"},
                                {"key": "2", "label": "Meet a Teacher",         "next": "workflow.school_teacher_flow"},
                                {"key": "3", "label": "Quick Meeting Request",  "next": "workflow.school_quick_meeting_flow"},
                                {"key": "4", "label": "Reschedule Meeting",     "next": "workflow.school_reschedule_flow"},
                                {"key": "5", "label": "Cancel Meeting",         "next": "workflow.school_cancel_flow"},
                                {"key": "6", "label": "School Timings",         "next": "timings_info"},
                                {"key": "7", "label": "Academic Calendar",      "next": "calendar_info"},
                                {"key": "6", "label": "Fee Structure",          "next": "fees_info"},
                                {"key": "7", "label": "Contact Office",         "next": "contact_info"},
                            ],
                        },
                        {
                            "id": "timings_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "⏰ *School Timings*\n\n"
                                "📅 Monday – Friday: 8:00 AM – 2:30 PM\n"
                                "📅 Saturday: 8:00 AM – 12:00 PM\n"
                                "🔴 Sunday: Closed\n\n"
                                "🏫 School gates open at 7:45 AM.\n"
                                "Late arrival after 8:30 AM requires slip from office.\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "calendar_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📆 *Academic Calendar 2025–26*\n\n"
                                "• Term 1 Exam: 12–22 Oct 2025\n"
                                "• Diwali Break: 23 Oct – 3 Nov 2025\n"
                                "• Term 2 Starts: 4 Nov 2025\n"
                                "• Annual Sports Day: 15 Jan 2026\n"
                                "• Annual Day: 15 Apr 2026\n"
                                "• Term 2 Exam: 18–28 Apr 2026\n"
                                "• Summer Vacation: 1 May – 14 Jun 2026\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "fees_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "💳 *Annual Fee Structure*\n\n"
                                "• Nursery – KG: ₹24,000/year\n"
                                "• Grade 1–5: ₹32,000/year\n"
                                "• Grade 6–8: ₹38,000/year\n"
                                "• Grade 9–10: ₹45,000/year\n\n"
                                "Fees include: Tuition, Library, Lab, Sports\n"
                                "Transport & Uniform are separate.\n\n"
                                "For fee payment contact: +91 98765 60001\n\n"
                                "Reply *hi* for main menu."
                            ),
                        },
                        {
                            "id": "contact_info",
                            "type": "action",
                            "action_type": "static_text",
                            "text": (
                                "📞 *Contact Bright Future Academy*\n\n"
                                "📍 8 Railway Colony, Madurai – 625001\n"
                                "📞 Office: +91 98765 60001\n"
                                "📧 Email: principal@brightfuture.demo\n\n"
                                "🕐 Office hours: Mon–Fri 8 AM – 4 PM\n"
                                "🕐 Saturday: 8 AM – 1 PM\n\n"
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
