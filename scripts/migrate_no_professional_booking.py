"""
Migration: Upgrade school / gym / camp booking workflows to support
'no professional' booking (PRESET_PROFESSIONAL step) and fix trigger
action kind from legacy "workflow" → "invoke_action".

Run once against your live MongoDB:
    python scripts/migrate_no_professional_booking.py

Set MONGO_URI env var if your DB is not on localhost:
    MONGO_URI="mongodb+srv://..." python scripts/migrate_no_professional_booking.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

# ── Allow running from the project root ────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME", "saas_db")

NOW = datetime.now(timezone.utc)

client = MongoClient(MONGO_URI)
db     = client[DB_NAME]

# ══════════════════════════════════════════════════════════════════════════════
#  1. Fix trigger kind: "workflow" → "invoke_action" for school / gym / camp
# ══════════════════════════════════════════════════════════════════════════════

TRIGGER_FIXES = [
    # (tenant_id, trigger_id, new_action)
    (
        "ss_business_school", "trigger_book",
        {"kind": "invoke_action", "action_id": "workflow.school_meeting_flow"},
    ),
    (
        "ss_business_gym", "trigger_book",
        {"kind": "invoke_action", "action_id": "workflow.gym_booking_flow"},
    ),
    (
        "ss_business_camp", "trigger_book",
        {"kind": "invoke_action", "action_id": "workflow.camp_booking_flow"},
    ),
]

triggers_col = db["whatsapp_triggers"]
for tenant_id, trigger_id, new_action in TRIGGER_FIXES:
    res = triggers_col.update_one(
        {"tenant": tenant_id, "trigger_id": trigger_id},
        {"$set": {"action": new_action, "match.type": "contains", "updated_at": NOW}},
    )
    status = "updated" if res.modified_count else "not found / already up-to-date"
    print(f"[trigger] {tenant_id}/{trigger_id}: {status}")

# ══════════════════════════════════════════════════════════════════════════════
#  2. Patch school_meeting_flow — insert PRESET_PROFESSIONAL + ASK_NAME steps
# ══════════════════════════════════════════════════════════════════════════════

SCHOOL_MEETING_STEPS = [
    # No SHOW_PROFESSIONALS → smart detection → no-professional / meeting-room-as-resource
    # No PRESET_PROFESSIONAL needed
    {"action_code": "SHOW_SERVICES",   "label": "Select meeting type:",                       "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_DATE",     "label": "Choose a date for the meeting:",              "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_TIME",     "label": "Choose a time slot (1 PM – 3:30 PM):",       "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "ASK_NAME",        "label": "Please share your name (parent/guardian):",  "input_required": True,  "ui_type": "text", "params": {}},
    {"action_code": "CONFIRM_BOOKING", "label": "Confirm meeting",                             "input_required": False, "ui_type": "list", "params": {}},
    {"action_code": "END",             "label": "✅ Meeting slot confirmed! Please bring your ward's progress report. See you there! 🎓", "input_required": False, "ui_type": "list", "params": {}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  3. Patch gym_booking_flow — insert PRESET_PROFESSIONAL + ASK_NAME steps
# ══════════════════════════════════════════════════════════════════════════════

GYM_BOOKING_STEPS = [
    # No SHOW_PROFESSIONALS + No PRESET_PROFESSIONAL → smart detection → no-professional mode
    {"action_code": "SHOW_SERVICES",
     "label": "Choose a session type:",
     "input_required": True,  "ui_type": "list",
     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "PT Session – 20 Min",
                             "Group Class", "Diet Consultation", "Body Composition"]}},
    {"action_code": "SELECT_DATE",     "label": "Choose your preferred date:", "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_TIME",     "label": "Choose a time slot:",         "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "ASK_NAME",        "label": "Your name please:",           "input_required": True,  "ui_type": "text", "params": {}},
    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your session",        "input_required": False, "ui_type": "list", "params": {}},
    {"action_code": "END",             "label": "✅ Session booked! Come ready to sweat 💪 Reply *hi* for the main menu.", "input_required": False, "ui_type": "list", "params": {}},
]

GYM_COURT_STEPS = [
    # No SHOW_PROFESSIONALS → smart detection → court-as-resource (service-level overlap check)
    # No PRESET_PROFESSIONAL needed
    {"action_code": "SHOW_SERVICES",
     "label": "Select court / lane type:",
     "input_required": True,  "ui_type": "list",
     "params": {"services": ["Badminton Court", "Squash Court", "Tennis Court", "Swimming Lane"]}},
    {"action_code": "SELECT_DATE",   "label": "Choose your preferred date:",          "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "ASK_NUM_SLOTS", "label": "How many hours would you like to book?",
     "input_required": True,  "ui_type": "list", "params": {"max_slots": 2, "slot_label": "hour"}},
    {"action_code": "SELECT_TIME",   "label": "Choose your start time:",              "input_required": True,  "ui_type": "list",
     "params": {"time_slots": ["06:00","07:00","08:00","09:00","10:00","11:00",
                               "14:00","15:00","16:00","17:00","18:00","19:00"]}},
    {"action_code": "ASK_NAME",        "label": "Your name please:",                 "input_required": True,  "ui_type": "text", "params": {}},
    {"action_code": "CONFIRM_BOOKING", "label": "Confirm your court booking",        "input_required": False, "ui_type": "list", "params": {}},
    {"action_code": "END",             "label": "✅ Court booked! Please arrive 5 min early. 🏸 Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
]

GYM_PT_SESSION_STEPS = [
    # Has SHOW_PROFESSIONALS → professional booking mode (trainer selected by user)
    {"action_code": "SHOW_SERVICES",
     "label": "Choose PT session type (20/30/60 min available):",
     "input_required": True,  "ui_type": "list",
     "params": {"services": ["PT Session – 1 Hr", "PT Session – 30 Min", "PT Session – 20 Min"]}},
    {"action_code": "SHOW_PROFESSIONALS", "label": "Choose your trainer:",  "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_DATE",        "label": "Choose your preferred date:", "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_TIME",        "label": "Choose a time slot:",         "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "ASK_NAME",           "label": "Your name please:",           "input_required": True,  "ui_type": "text", "params": {}},
    {"action_code": "CONFIRM_BOOKING",    "label": "Confirm your PT session",     "input_required": False, "ui_type": "list", "params": {}},
    {"action_code": "END",                "label": "✅ PT session booked! Your trainer will be ready. 💪 Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
]

# ══════════════════════════════════════════════════════════════════════════════
#  4. Patch camp_booking_flow — insert PRESET_PROFESSIONAL + ASK_NAME steps
# ══════════════════════════════════════════════════════════════════════════════

CAMP_BOOKING_STEPS = [
    # No SHOW_PROFESSIONALS + No SELECT_TIME → date-only, no-professional enrollment
    # Smart detection handles both — no PRESET_PROFESSIONAL needed
    {"action_code": "SHOW_SERVICES",   "label": "Select a camp program:",             "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "SELECT_DATE",     "label": "Choose your preferred date:",         "input_required": True,  "ui_type": "list", "params": {}},
    {"action_code": "ASK_NAME",        "label": "Please share your child's name:",     "input_required": True,  "ui_type": "text", "params": {}},
    {"action_code": "CONFIRM_BOOKING", "label": "Confirm enrollment",                 "input_required": False, "ui_type": "list", "params": {}},
    {"action_code": "END",             "label": "✅ Enrollment confirmed! Pack light & come ready for adventure! 🏕️ Reply *hi* for main menu.", "input_required": False, "ui_type": "list", "params": {}},
]

WORKFLOW_PATCHES = [
    ("ss_business_school", "school_meeting_flow", "Parent-Teacher Meeting Booking",   SCHOOL_MEETING_STEPS),
    ("ss_business_gym",    "gym_booking_flow",    "PT Session Booking (auto trainer)", GYM_BOOKING_STEPS),
    ("ss_business_gym",    "gym_court_flow",      "Badminton / Sports Court Booking",  GYM_COURT_STEPS),
    ("ss_business_gym",    "gym_pt_session_flow", "PT Session Booking (any duration)", GYM_PT_SESSION_STEPS),
    ("ss_business_camp",   "camp_booking_flow",   "Camp Session Enrollment",           CAMP_BOOKING_STEPS),
]

workflows_col = db["workflows"]
for tenant_id, workflow_id, name, steps in WORKFLOW_PATCHES:
    res = workflows_col.update_one(
        {"tenant": tenant_id, "workflow_id": workflow_id},
        {"$set": {
            "steps":      steps,
            "name":       name,
            "updated_at": NOW,
        }},
        upsert=False,
    )
    if res.matched_count:
        status = "updated" if res.modified_count else "already up-to-date"
    else:
        status = "NOT FOUND in DB (will be created on next seed run)"
    print(f"[workflow] {tenant_id}/{workflow_id}: {status}")

print("\nMigration complete.")
