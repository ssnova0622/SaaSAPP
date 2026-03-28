#!/usr/bin/env python3
"""
Delete all ss_business_* demo tenants and their data. Use after demos to reset.
Usage: python scripts/run_delete_all_demo.py
       python scripts/run_delete_all_demo.py --dry-run
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db import get_db
from scripts.industries._base import TENANT_PREFIX

TENANT_SCOPED_COLLECTIONS = [
    "customers", "professionals", "staff", "services", "appointments",
    "categories", "products", "inventory", "orders", "carts", "payments",
    "promotions", "promotion_logs", "workflows", "whatsapp_menus",
    "whatsapp_triggers", "followups", "events",
]


def main():
    parser = argparse.ArgumentParser(description="Delete all ss_business_* demo tenants and data")
    parser.add_argument("--dry-run", action="store_true", help="Only list tenants that would be deleted")
    args = parser.parse_args()

    db = get_db()
    tenants_col = db.get_collection("tenants")
    cursor = tenants_col.find({"_id": {"$regex": f"^{TENANT_PREFIX}"}}, {"_id": 1})
    tenant_ids = [d["_id"] for d in cursor]

    if not tenant_ids:
        print("No ss_business_* tenants found.")
        return

    print(f"Found tenants: {tenant_ids}")

    if args.dry_run:
        print("Dry run. No data deleted.")
        return

    total = 0
    for tenant_id in tenant_ids:
        for col_name in TENANT_SCOPED_COLLECTIONS:
            try:
                col = db.get_collection(col_name)
                res = col.delete_many({"tenant": tenant_id})
                if res.deleted_count:
                    print(f"  {col_name} ({tenant_id}): deleted {res.deleted_count}")
                    total += res.deleted_count
            except Exception:
                pass
        try:
            cron_col = db.get_collection("cron_jobs")
            res = cron_col.delete_many({"tenant": tenant_id})
            total += res.deleted_count
        except Exception:
            pass
        res = tenants_col.delete_one({"_id": tenant_id})
        if res.deleted_count:
            print(f"  tenants: deleted {tenant_id}")
            total += 1

    print(f"Done. Deleted all demo tenants and data (total ops: {total}).")


if __name__ == "__main__":
    main()
