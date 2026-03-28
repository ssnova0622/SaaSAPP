#!/usr/bin/env python3
"""
Delete all demo data for a domain (tenant ss_business_{domain}) or for a specific tenant.
Usage: python scripts/run_delete_domain.py --domain salon
       python scripts/run_delete_domain.py --tenant ss_business_clinic
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
    parser = argparse.ArgumentParser(description="Delete demo data for a domain or tenant")
    parser.add_argument("--domain", type=str, help="Domain: salon, clinic, gym, school, store, camp, car_showroom")
    parser.add_argument("--tenant", type=str, help="Tenant id to delete (e.g. ss_business_salon)")
    parser.add_argument("--keep-tenant", action="store_true", help="Only delete collection data, keep tenant document")
    args = parser.parse_args()

    tenant_id = args.tenant
    if not tenant_id and args.domain:
        tenant_id = f"{TENANT_PREFIX}{args.domain.strip().lower().replace(' ', '_')}"
    if not tenant_id:
        print("Provide --domain or --tenant")
        sys.exit(1)

    db = get_db()
    total = 0

    for col_name in TENANT_SCOPED_COLLECTIONS:
        try:
            col = db.get_collection(col_name)
            res = col.delete_many({"tenant": tenant_id})
            if res.deleted_count:
                print(f"  {col_name}: deleted {res.deleted_count}")
                total += res.deleted_count
        except Exception:
            pass

    try:
        cron_col = db.get_collection("cron_jobs")
        res = cron_col.delete_many({"tenant": tenant_id})
        if res.deleted_count:
            print(f"  cron_jobs: deleted {res.deleted_count}")
            total += res.deleted_count
    except Exception:
        pass

    if not args.keep_tenant:
        try:
            tenants_col = db.get_collection("tenants")
            res = tenants_col.delete_one({"_id": tenant_id})
            if res.deleted_count:
                print(f"  tenants: deleted {tenant_id}")
                total += 1
        except Exception:
            pass

    if total == 0:
        print(f"No data found for tenant: {tenant_id}")
    else:
        print(f"Done. Deleted all data for tenant: {tenant_id}")


if __name__ == "__main__":
    main()
