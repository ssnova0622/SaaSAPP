#!/usr/bin/env python3
"""
Delete all mock data for the demo tenant. Removes tenant-scoped data and the demo user;
optionally removes the demo tenant and mock cron job. Does not remove the super admin.
Run from project root: python scripts/delete_mock_data.py
"""
from scripts.super_admin.seed_mock_data import MOCK_TENANT_ID
from settings import MOCK_EMAIL, MOCK_USER_ID

from app.services.db import get_db

# Collections that are scoped by tenant: delete docs where tenant == MOCK_TENANT_ID
TENANT_SCOPED_COLLECTIONS = [
    "customers",
    "professionals",
    "staff",
    "services",
    "appointments",
    "categories",
    "products",
    "inventory",
    "orders",
    "carts",
    "payments",
    "promotions",
    "promotion_logs",
    "workflows",
    "whatsapp_menus",
    "whatsapp_triggers",
    "followups",
    "reports",
    "retention_metrics",
    "events",
]


def main():
    db = get_db()
    total = 0

    for cname in TENANT_SCOPED_COLLECTIONS:
        try:
            col = db.get_collection(cname)
        except Exception:
            continue
        try:
            res = col.delete_many({"tenant": MOCK_TENANT_ID})
        except Exception:
            continue
        if res.deleted_count:
            print(f"  {cname}: deleted {res.deleted_count}")
            total += res.deleted_count

    # Cron jobs: delete mock jobs for this tenant
    try:
        cron_col = db.get_collection("cron_jobs")
        res = cron_col.delete_many({"tenant": MOCK_TENANT_ID})
        if res.deleted_count:
            print(f"  cron_jobs: deleted {res.deleted_count}")
            total += res.deleted_count
    except Exception:
        pass

    # Demo user (tenant_admin for demo tenant)
    try:
        users = db.get_collection("users")
        res = users.delete_one({"id": MOCK_USER_ID})
        if res.deleted_count:
            print("  users: deleted demo user", MOCK_USER_ID)
            total += res.deleted_count
        # Also by email in case id differs
        res2 = users.delete_one({"email": MOCK_EMAIL.lower().strip()})
        if res2.deleted_count:
            total += res2.deleted_count
    except Exception:
        pass

    # Demo tenant
    try:
        tenants = db.get_collection("tenants")
        res = tenants.delete_one({"_id": MOCK_TENANT_ID})
        if res.deleted_count:
            print("  tenants: deleted demo tenant", MOCK_TENANT_ID)
            total += 1
    except Exception:
        pass

    if total == 0:
        print("No mock data found for", MOCK_TENANT_ID)
    else:
        print("Done. Deleted all mock data for", MOCK_TENANT_ID)


if __name__ == "__main__":
    main()
