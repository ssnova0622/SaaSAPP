#!/usr/bin/env python3
"""
Seed default WhatsApp actions into the global whatsapp_actions collection.
Actions are defined here (no hardcoded registry dependency). Super Admin can add more from UI.
Run from project root: python scripts/super_admin/seed_default_whatsapp_actions.py
"""
from __future__ import annotations

from app.services.db import get_db, whatsapp_actions_collection

# Minimal default actions per module (action_id, label, modules, requires_caps, description)
DEFAULT_ACTIONS = [
    ("SHOW_SERVICES", "List / Select Service", ["salon"], ["salon.appointments"], "List services and let user select"),
    ("SHOW_PROFESSIONALS", "List / Select Staff", ["salon"], ["salon.appointments"], "List staff and let user select"),
    ("SELECT_DATE", "Select Date", ["salon"], ["salon.appointments"], "Choose booking date"),
    ("SELECT_TIME", "Select Time", ["salon"], ["salon.appointments"], "Choose time slot"),
    ("AUTO_ASSIGN", "Auto Assign", ["salon"], ["salon.appointments"], "Auto pick staff and slot"),
    ("CONFIRM_BOOKING", "Confirm Booking", ["salon"], ["salon.appointments"], "Show summary and confirm"),
    ("FINALIZE_BOOKING", "Finalize Booking", ["salon"], ["salon.appointments"], "Save appointment"),
    ("ASK_NAME", "Ask Name", ["core"], [], "Ask for customer name"),
    ("END", "End", ["core"], [], "End workflow with message"),
]


def seed_default_whatsapp_actions() -> int:
    """Insert default actions if not already present. Returns count inserted."""
    col = whatsapp_actions_collection()
    existing = set(doc["action_id"] for doc in col.find({}, {"action_id": 1}))
    inserted = 0
    for action_id, label, modules, requires_caps, description in DEFAULT_ACTIONS:
        if action_id in existing:
            continue
        col.insert_one({
            "action_id": action_id,
            "label": label,
            "modules": modules,
            "requires_caps": requires_caps,
            "description": description,
        })
        existing.add(action_id)
        inserted += 1
        print(f"  inserted: {action_id} ({label})")
    return inserted


def main():
    get_db()
    print("Seeding default WhatsApp actions...")
    n = seed_default_whatsapp_actions()
    print(f"Done. Inserted {n} default actions.")


if __name__ == "__main__":
    main()
