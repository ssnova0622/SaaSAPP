#!/usr/bin/env python3
"""
Seed bulk demo data for a specific industry/domain. Creates tenant ss_business_{domain},
inserts all collections, and creates a tenant_admin user (password 123456) for that tenant.
Usage: python scripts/run_seed_domain.py --domain salon
       python scripts/run_seed_domain.py --domain clinic
       python scripts/run_seed_domain.py --tenant ss_business_gym
"""
import argparse
import sys
import os
import datetime as dt

# Project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.db import get_db, users_collection
from app.services.storage_mongo import Storage

# Password for all industry tenant users
INDUSTRY_USER_PASSWORD = "123456"

DOMAIN_MODULES = {
    "salon": "scripts.industries.salon.data",
    "clinic": "scripts.industries.clinic.data",
    "gym": "scripts.industries.gym.data",
    "school": "scripts.industries.school.data",
    "store": "scripts.industries.store.data",
    "camp": "scripts.industries.camp.data",
    "car_showroom": "scripts.industries.car_showroom.data",
}


def main():
    parser = argparse.ArgumentParser(description="Seed demo data for an industry domain")
    parser.add_argument("--domain", type=str, help="Domain: salon, clinic, gym, school, store, camp, car_showroom")
    parser.add_argument("--tenant", type=str, help="Override tenant id (e.g. ss_business_salon)")
    parser.add_argument("--force", action="store_true", help="Replace existing tenant/data for this tenant")
    args = parser.parse_args()

    tenant_id = args.tenant
    domain = args.domain

    if not tenant_id and not domain:
        print("Provide --domain or --tenant")
        sys.exit(1)
    if not tenant_id:
        tenant_id = f"ss_business_{domain.strip().lower().replace(' ', '_')}"
    if not domain:
        if tenant_id.startswith("ss_business_"):
            domain = tenant_id.replace("ss_business_", "")
        else:
            print("When using --tenant, use a tenant id like ss_business_salon so domain can be inferred, or pass --domain")
            sys.exit(1)

    if domain not in DOMAIN_MODULES:
        print(f"Unknown domain: {domain}. Choose from: {list(DOMAIN_MODULES.keys())}")
        sys.exit(1)

    import importlib
    mod = importlib.import_module(DOMAIN_MODULES[domain])
    seed_data = mod.get_seed_data(tenant_id)
    _, tenant_capabilities = mod.get_modules_capabilities()

    db = get_db()
    tenants_col = db.get_collection("tenants")
    if tenants_col.find_one({"_id": tenant_id}) and not args.force:
        print(f"Tenant {tenant_id} already exists. Use --force to replace.")
        sys.exit(1)

    # 1. Upsert tenant
    tenant_doc = seed_data.pop("tenant_doc", None)
    if tenant_doc:
        tenant_doc["_id"] = tenant_id
        tenants_col.replace_one({"_id": tenant_id}, tenant_doc, upsert=True)
        print(f"  tenants: upserted {tenant_id}")

    # 2. Insert collections (skip tenant_doc)
    tenant_scoped = [
        "customers", "professionals", "staff", "services", "appointments",
        "categories", "products", "inventory", "orders", "promotions",
        "whatsapp_triggers",
    ]
    for col_name in tenant_scoped:
        items = seed_data.get(col_name)
        if not items:
            continue
        col = db.get_collection(col_name)
        if args.force:
            col.delete_many({"tenant": tenant_id})
        if isinstance(items, list):
            for doc in items:
                doc["tenant"] = tenant_id
            col.insert_many(items)
            print(f"  {col_name}: inserted {len(items)}")
        else:
            items["tenant"] = tenant_id
            col.insert_one(items)
            print(f"  {col_name}: inserted 1")

    # 3. Create tenant_admin user for this tenant (password: 123456) with same capabilities as tenant so menus show
    user_id = f"user_{tenant_id}_admin"
    email = f"admin_{domain}@ssbusiness.demo"
    display_name = f"{domain.replace('_', ' ').title()} Admin"
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    user_doc = {
        "id": user_id,
        "email": email.lower().strip(),
        "password_hash": Storage._hash_password(INDUSTRY_USER_PASSWORD),
        "role": "tenant_admin",
        "tenant": tenant_id,
        "display_name": display_name,
        "caps": list(tenant_capabilities),
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "is_mock": True,
    }
    users_col = users_collection()
    if args.force:
        users_col.delete_many({"tenant": tenant_id})
    existing = users_col.find_one({"tenant": tenant_id})
    if existing:
        users_col.replace_one({"id": existing["id"]}, user_doc)
        print(f"  users: updated tenant admin {email} (password: {INDUSTRY_USER_PASSWORD})")
    else:
        users_col.insert_one(user_doc)
        print(f"  users: created tenant admin {email} (password: {INDUSTRY_USER_PASSWORD})")

    # Seed global intent keywords in ai_knowledge_base (idempotent) so AI/WhatsApp intents work
    try:
        from app.services.ai.knowledge_storage import seed_global_intent_keywords
        count = seed_global_intent_keywords()
        print(f"  ai_knowledge_base: global intent keywords seeded ({count} intents).")
    except Exception as e:
        print(f"  ai_knowledge_base: skip or failed: {e}")

    print(f"Done. Tenant: {tenant_id} (domain: {domain})")
    print(f"  Login as tenant admin: {email} / {INDUSTRY_USER_PASSWORD}")
    print("  Or login as Super Admin and select this tenant to explore.")


if __name__ == "__main__":
    main()
