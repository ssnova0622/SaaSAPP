#!/usr/bin/env python3
"""
Seed mock data for all app pages: demo tenant, demo user, customers, professionals,
staff, services, appointments, categories, products, inventory, orders, promotions,
workflows, WhatsApp menus/triggers, cron jobs. Uses app's DB and collections.
Run from project root: python scripts/seed_mock_data.py
"""
import uuid
import datetime as dt

from settings import MOCK_TENANT_ID, MOCK_EMAIL, MOCK_USER_ID, MOCK_PASSWORD
from app.helpers.constants import DEFAULT_TIMEZONE
from app.services.db import get_db, users_collection
from app.services.storage_mongo import Storage
from app.modules.plans import get_plan_defaults

NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def _db():
    return get_db()


def seed_tenant():
    col = _db().get_collection("tenants")
    wa_demo = {
        "enabled": True,
        "provider": "twilio",
        "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "auth_token": "replace_with_twilio_auth_token",
        "from_numbers": ["whatsapp:+919000111000"],
        "webhook_secret": "dev-webhook-secret",
        "locale_default": "en",
    }
    existing = col.find_one({"_id": MOCK_TENANT_ID})
    if existing:
        if existing.get("is_mock") and not (existing.get("whatsapp_config") or {}):
            col.update_one({"_id": MOCK_TENANT_ID}, {"$set": {"whatsapp_config": wa_demo}})
            print("  tenants: demo tenant whatsapp_config updated (was empty).")
        else:
            print("  tenants: demo tenant already exists.")
        return
    defaults = get_plan_defaults("pro")
    col.insert_one({
        "_id": MOCK_TENANT_ID,
        "plan": "pro",
        "category": "salon",
        "owner_email": MOCK_EMAIL,
        "owner_phone": "+919000111000",
        "tz": DEFAULT_TIMEZONE,
        "modules": defaults["modules"],
        "capabilities": defaults["capabilities"],
        "active": True,
        "whatsapp_config": wa_demo,
        "payment_config": {"provider": "dummy", "currency": "INR", "test_mode": True},
        "delivery_config": {},
        "smtp_config": {},
        "date_format": "DD-MM-YYYY",
        "is_mock": True,
    })
    print("  tenants: demo tenant created.")


def seed_demo_user():
    col = users_collection()
    if col.find_one({"email": MOCK_EMAIL.lower().strip()}):
        print("  users: demo user already exists.")
        return
    defaults = get_plan_defaults("pro")
    doc = {
        "id": MOCK_USER_ID,
        "email": MOCK_EMAIL.lower().strip(),
        "password_hash": Storage._hash_password(MOCK_PASSWORD),
        "role": "tenant_admin",
        "tenant": MOCK_TENANT_ID,
        "display_name": "Demo Admin",
        "caps": list(defaults["capabilities"]),
        "status": "active",
        "created_at": NOW,
        "updated_at": NOW,
        "is_mock": True,
    }
    col.insert_one(doc)
    print("  users: demo tenant admin created.")


def seed_customers():
    col = _db().get_collection("customers")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 3:
        print("  customers: mock data already present.")
        return
    # Use E.164 so display and APIs are consistent (no "IN" country code issue)
    for i, (name, phone, email) in enumerate([
        ("Demo Customer One", "+919000111101", "demo1@example.com"),
        ("Demo Customer Two", "+919000111102", "demo2@example.com"),
        ("Demo Customer Three", "+919000111103", "demo3@example.com"),
    ]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "phone": phone}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "phone": phone,
            "name": name,
            "email": email,
            "tags": ["demo"],
            "active": True,
            "created_at": NOW,
            "is_mock": True,
        })
    print("  customers: 3 mock customers inserted.")


def seed_professionals():
    col = _db().get_collection("professionals")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  professionals: mock data already present.")
        return
    for i, name in enumerate(["Dr. Demo One", "Dr. Demo Two"]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "name": name}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "name": name,
            "short_name": name[:12] if len(name) > 12 else name,
            "price": 500.0 if i == 0 else 750.0,
            "slots": [{"time": "09:00", "status": "available"}, {"time": "10:00", "status": "available"}],
            "active": True,
            "created_at": NOW,
            "is_mock": True,
        })
    print("  professionals: 2 mock professionals inserted.")


def seed_staff():
    col = _db().get_collection("staff")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  staff: mock data already present.")
        return
    for i, (name, role) in enumerate([("Staff Demo A", "receptionist"), ("Staff Demo B", "assistant")]):
        sid = f"staff_{MOCK_TENANT_ID}_mock_{i}"
        if col.find_one({"tenant": MOCK_TENANT_ID, "id": sid}):
            continue
        col.insert_one({
            "id": sid,
            "tenant": MOCK_TENANT_ID,
            "name": name,
            "role": role,
            "phone": f"+91900033330{i}",
            "email": f"staff{i}@demo.com",
            "skills": [],
            "active": True,
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        })
    print("  staff: 2 mock staff inserted.")


def seed_services():
    col = _db().get_collection("services")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  services: mock data already present.")
        return
    for i, (name, desc, dur, price) in enumerate([
        ("Consultation", "Initial consultation", 30, 50.0),
        ("Follow-up", "Follow-up visit", 15, 25.0),
    ]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "name": name}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "name": name,
            "description": desc,
            "price": price,
            "duration": dur,
            "active": True,
            "created_at": NOW,
            "is_mock": True,
        })
    print("  services: 2 mock services inserted.")


def seed_appointments():
    col = _db().get_collection("appointments")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  appointments: mock data already present.")
        return
    start = NOW + dt.timedelta(days=1)
    for i in range(2):
        aid = f"app_{MOCK_TENANT_ID}_mock_{i}"
        if col.find_one({"tenant": MOCK_TENANT_ID, "id": aid}):
            continue
        t = start + dt.timedelta(hours=i * 2)
        end = t + dt.timedelta(minutes=30)
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "id": aid,
            "customer_name": "Demo Customer One",
            "customer_phone": "+919000111101",
            "professional": "Dr. Demo One",
            "date": t.strftime("%Y-%m-%d"),
            "time": t.strftime("%H:%M"),
            "price": 500.0,
            "status": "booked",
            "created_at": NOW,
            "start": t,
            "end": end,
            "is_mock": True,
        })
    print("  appointments: 2 mock appointments inserted.")


def seed_categories():
    col = _db().get_collection("categories")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  categories: mock data already present.")
        return
    for i, name in enumerate(["Demo Category", "Electronics"]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "name": name}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "name": name,
            "active": True,
            "is_mock": True,
        })
    print("  categories: 2 mock categories inserted.")


def seed_products():
    col = _db().get_collection("products")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 3:
        print("  products: mock data already present.")
        return
    for i, (sku, name, cat, price) in enumerate([
        ("SKU-DEMO-1", "Demo Product A", "Demo Category", 29.99),
        ("SKU-DEMO-2", "Demo Product B", "Demo Category", 49.99),
        ("SKU-DEMO-3", "Demo Product C", "Electronics", 99.00),
    ]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "sku": sku}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "sku": sku,
            "name": name,
            "category": cat,
            "price": price,
            "mrp": price,
            "active": True,
            "unit": "pcs",
            "is_mock": True,
        })
    print("  products: 3 mock products inserted.")


def seed_inventory():
    col = _db().get_collection("inventory")
    for sku in ["SKU-DEMO-1", "SKU-DEMO-2", "SKU-DEMO-3"]:
        if col.find_one({"tenant": MOCK_TENANT_ID, "sku": sku}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "sku": sku,
            "available_qty": 100.0,
            "is_mock": True,
        })
    if col.count_documents({"tenant": MOCK_TENANT_ID, "is_mock": True}) > 0:
        print("  inventory: mock inventory inserted.")


def seed_orders():
    col = _db().get_collection("orders")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  orders: mock data already present.")
        return
    for i in range(2):
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        if col.find_one({"tenant": MOCK_TENANT_ID, "id": order_id}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "id": order_id,
            "customer": {"phone": "+919000111101", "name": "Demo Customer One"},
            "items": [
                {"sku": "SKU-DEMO-1", "name": "Demo Product A", "qty": 1, "unit": "pcs", "price": 29.99},
            ],
            "totals": {"subtotal": 29.99},
            "fulfillment": {"mode": "pickup", "address": None},
            "payment": {"method": "COD", "status": "pending"},
            "status": "placed",
            "created_at": NOW,
            "updated_at": NOW,
            "timeline": [{"ts": NOW, "event": "placed"}],
            "is_mock": True,
        })
    print("  orders: 2 mock orders inserted.")


def seed_promotions():
    col = _db().get_collection("promotions")

    def ensure_promo(name: str, extra: dict):
        if col.find_one({"tenant": MOCK_TENANT_ID, "name": name}):
            return
        doc = {
            "tenant": MOCK_TENANT_ID,
            "name": name,
            "channel": "both",
            "message": f"Demo message for {name}",
            "audience": {"type": "all"},
            "status": "draft",
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        }
        doc.update(extra)
        col.insert_one(doc)

    ensure_promo("Welcome Offer", {})
    ensure_promo("Season Sale", {})
    ensure_promo(
        "CTA URL Demo",
        {
            "channel": "whatsapp",
            "message": "This is a CTA URL demo promotion.\n\nTap the button below to open the link.",
            "interactive_type": "cta_url",
            "cta_entries": [{"id": "cta_1", "display_text": "Shop now", "url": "https://example.com/offers"}],
            "cta_append_urls_to_body": True,
        },
    )
    print("  promotions: mock promotions ensured (Welcome Offer, Season Sale, CTA URL Demo).")


def seed_workflows():
    col = _db().get_collection("workflows")
    steps = [
        {"action_code": "SHOW_SERVICES", "label": None, "input_required": False, "ui_type": "list", "params": {}},
        {
            "action_code": "END",
            "label": "Thanks! Reply START anytime to return to the main menu.",
            "input_required": False,
            "ui_type": "list",
            "params": {},
        },
    ]
    demo = col.find_one({"tenant": MOCK_TENANT_ID, "workflow_id": "demo_workflow_1"})
    if demo:
        first = (demo.get("steps") or [{}])[0] if demo.get("steps") else {}
        if isinstance(first, dict) and first.get("action_code") == "send_message":
            col.update_one(
                {"_id": demo["_id"]},
                {"$set": {"steps": steps, "updated_at": NOW}},
            )
            print("  workflows: demo_workflow_1 steps updated (SHOW_SERVICES + END).")
        else:
            print("  workflows: mock data already present.")
        return
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  workflows: other workflow exists; skip inserting demo_workflow_1.")
        return
    col.insert_one({
        "tenant": MOCK_TENANT_ID,
        "workflow_id": "demo_workflow_1",
        "name": "Demo Workflow",
        "steps": steps,
        "active": True,
        "requires_caps": [],
        "created_at": NOW,
        "updated_at": NOW,
        "is_mock": True,
    })
    print("  workflows: 1 mock workflow inserted.")


def seed_whatsapp_menus():
    col = _db().get_collection("whatsapp_menus")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  whatsapp_menus: mock data already present.")
        return
    col.insert_one({
        "tenant": MOCK_TENANT_ID,
        "menu_id": "demo_main",
        "name": "Demo Main Menu",
        "status": "draft",
        "version": 1,
        "tree": {"nodes": [], "edges": []},
        "locales": {},
        "updated_at": NOW,
        "is_mock": True,
    })
    print("  whatsapp_menus: 1 mock menu inserted.")


def seed_whatsapp_triggers():
    col = _db().get_collection("whatsapp_triggers")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  whatsapp_triggers: mock data already present.")
        return
    col.insert_one({
        "tenant": MOCK_TENANT_ID,
        "trigger_id": "demo_hello",
        "match": {"type": "exact", "value": "hello"},
        "action": {"kind": "static_text", "text": "Hello! How can I help?"},
        "enabled": True,
        "priority": 0,
        "updated_at": NOW,
        "is_mock": True,
    })
    print("  whatsapp_triggers: 1 mock trigger inserted.")


def seed_ai_knowledge_base():
    """Seed global intent keywords in ai_knowledge_base (idempotent)."""
    try:
        from app.services.ai.knowledge_storage import seed_global_intent_keywords
        count = seed_global_intent_keywords()
        print(f"  ai_knowledge_base: global intent keywords seeded ({count} intents).")
    except Exception as e:
        print(f"  ai_knowledge_base: skip or failed: {e}")


def seed_cron_jobs():
    col = _db().get_collection("cron_jobs")
    job_id = f"mock_demo_{MOCK_TENANT_ID}"
    if col.find_one({"job_id": job_id}):
        print("  cron_jobs: mock job already present.")
        return
    col.insert_one({
        "job_id": job_id,
        "type": "promotions",
        "tenant": MOCK_TENANT_ID,
        "schedule": "0 9 * * *",
        "enabled": True,
        "config": {},
        "last_run": None,
        "next_run": NOW + dt.timedelta(days=1),
        "is_mock": True,
    })
    print("  cron_jobs: 1 mock cron job inserted.")


def main():
    get_db()
    print("Seeding mock data for tenant:", MOCK_TENANT_ID)
    seed_tenant()
    seed_demo_user()
    seed_customers()
    seed_professionals()
    seed_staff()
    seed_services()
    seed_appointments()
    seed_categories()
    seed_products()
    seed_inventory()
    seed_orders()
    seed_promotions()
    seed_workflows()
    seed_whatsapp_menus()
    seed_whatsapp_triggers()
    seed_cron_jobs()
    seed_ai_knowledge_base()
    print("Done. Demo tenant:", MOCK_TENANT_ID)
    print("  Login (tenant admin):", MOCK_EMAIL, "| Password:", MOCK_PASSWORD)


if __name__ == "__main__":
    main()
