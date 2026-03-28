#!/usr/bin/env python3
"""
List all demo tenants (ss_business_*) and print a short guide on what to show per domain
for exploring all modules (like tenant_demo). Use this to run client demos.
Usage: python scripts/explore_all_modules.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db import get_db
from scripts.industries._base import TENANT_PREFIX, DOMAINS

GUIDE = {
    "salon": [
        "Dashboard: appointments, revenue, no-show blocked link",
        "Appointments: list, filter by date/pro, mark no-show/completed",
        "No-Show Blocked: search, reset (AI threshold in AI Config)",
        "Professionals & Services: slots, pricing",
        "Customers: list, no_show_count column",
        "AI → Appointments: slot recommendations",
        "AI → Config: no_show_block_threshold, reminder thresholds",
        "Promotions, Follow-ups, Reports",
    ],
    "clinic": [
        "Same as salon; professionals = doctors (Monthly Dr. Raj, Weekly Dr. Sheela, Consultant Dr. Amit)",
        "Appointments: 15 min slots, OPD style",
        "No-Show Blocked, AI Config, AI Appointments",
    ],
    "gym": [
        "Professionals = Trainers; appointments = PT sessions",
        "Appointments, No-Show Blocked, AI Config",
    ],
    "school": [
        "Professionals = Teachers; appointments = parent meetings",
        "Appointments, Customers (parents)",
    ],
    "store": [
        "Store — Products, Categories, Inventory",
        "Store — Orders, Store — Carts",
        "AI → Predictions: low-stock forecast, cart recovery (if AI module)",
        "AI Config: low_stock_*, cart_recovery_*",
    ],
    "camp": [
        "Professionals = Instructors; appointments = day camp sessions",
        "Appointments, Customers (participants)",
    ],
    "car_showroom": [
        "Professionals = Sales Reps; appointments = test drives",
        "Store — Products = car models; Orders",
        "Appointments, No-Show Blocked",
    ],
}


def main():
    db = get_db()
    tenants_col = db.get_collection("tenants")
    cursor = tenants_col.find({"_id": {"$regex": f"^{TENANT_PREFIX}"}}, {"_id": 1, "category": 1})
    tenants = list(cursor)

    print("=== Demo tenants (ss_business_*) ===\n")
    if not tenants:
        print("None found. Seed with: python scripts/run_seed_domain.py --domain salon")
        return

    for t in tenants:
        tid = t["_id"]
        domain = tid.replace(TENANT_PREFIX, "") if tid.startswith(TENANT_PREFIX) else "?"
        steps = GUIDE.get(domain, ["Same as salon/clinic"])
        print(f"  {tid}  (category: {t.get('category', '—')})")
        for step in steps:
            print(f"    • {step}")
        print()

    print("=== Quick seed commands ===")
    for d in DOMAINS:
        print(f"  python scripts/run_seed_domain.py --domain {d}")
    print("\n  python scripts/run_delete_domain.py --domain <domain>   # delete one domain")
    print("  python scripts/run_delete_all_demo.py                    # delete all ss_business_*")


if __name__ == "__main__":
    main()
