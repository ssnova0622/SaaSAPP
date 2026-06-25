#!/usr/bin/env python3
"""
Seed mock data for all app pages: demo tenant, demo user, customers, professionals,
staff, services, appointments, categories, products, inventory, orders, promotions,
workflows (including demo_price_list_flow with SHOW_SERVICE_PRICES), WhatsApp menus/triggers,
cron jobs. Uses app's DB and collections.

Run from project root: python scripts/super_admin/seed_mock_data.py
Re-seed requires clearing tenant_demo data first (or use run_seed_domain --force for industry tenants).
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
        "business_name": "Demo Salon",
        "display_name": "Demo Salon",
        "owner_email": MOCK_EMAIL,
        "owner_phone": "+919000111000",
        "tz": DEFAULT_TIMEZONE,
        "modules": defaults["modules"],
        "capabilities": defaults["capabilities"],
        "active": True,
        "address": "1 Demo Street, Chennai – 600001",
        "location": "https://maps.google.com/?q=Demo+Salon+Chennai",
        "whatsapp_config": wa_demo,
        "payment_config": {"provider": "dummy", "currency": "INR", "test_mode": True},
        "delivery_config": {},
        "smtp_config": {},
        "date_format": "DD-MM-YYYY",
        "currency": "INR",
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
    for i, (name, phone, email, tags) in enumerate([
        ("Priya Sharma",    "+919000111101", "priya@demo.com",    ["vip"]),
        ("Anita Reddy",     "+919000111102", "anita@demo.com",    ["regular"]),
        ("Meera Krishnan",  "+919000111103", "meera@demo.com",    ["regular"]),
        ("Sneha Patel",     "+919000111104", "sneha@demo.com",    ["new"]),
        ("Kavitha Nair",    "+919000111105", "kavitha@demo.com",  ["at-risk"]),
        ("Lakshmi Iyer",    "+919000111106", "lakshmi@demo.com",  ["vip"]),
    ]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "phone": phone}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "phone": phone,
            "phone_number": {"code": "+91", "number": phone[3:]},
            "name": name,
            "email": email,
            "tags": tags,
            "active": True,
            "no_show_count": 1 if "at-risk" in tags else 0,
            "created_at": NOW - dt.timedelta(days=i * 30),
            "is_mock": True,
        })
    print("  customers: 6 demo customers inserted.")


def seed_professionals():
    from app.helpers.professional_slots import slots_from_schedule
    from app.services.salon.professional_service import ProfessionalService

    col = _db().get_collection("professionals")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  professionals: mock data already present.")
        return
    specs = [
        ("Dr. Demo One", "DEMO-E001", 500.0),
        ("Dr. Demo Two", "DEMO-E002", 750.0),
    ]
    slots = slots_from_schedule("09:00", "18:00", 60)
    for name, eid, price in specs:
        if col.find_one({"tenant": MOCK_TENANT_ID, "name": name}):
            continue
        try:
            ProfessionalService.add_professional(
                MOCK_TENANT_ID,
                name,
                employee_id=eid,
                price=price,
                slots=slots,
            )
        except ValueError as e:
            print(f"  professionals: skip {name!r}: {e}")
    print("  professionals: mock professionals ensured.")


def seed_staff():
    """Seed staff records + matching portal login users for each demo role."""
    col = _db().get_collection("staff")
    users_col = users_collection()

    # ---------- Staff records -------------------------------------------------
    staff_specs = [
        # (name, job_role, email, portal_role, caps_profile)
        ("Ravi Kumar",   "manager",      "manager@demo.com",    "staff",   "manager"),
        ("Priya Das",    "receptionist", "reception@demo.com",  "staff",   "editor"),
        ("Anand Singh",  "therapist",    "therapist@demo.com",  "staff",   "viewer"),
        ("Suma Raj",     "intern",       "intern@demo.com",     "staff",   "custom"),
    ]

    for i, (name, job_role, email, portal_role, caps_profile) in enumerate(staff_specs):
        sid = f"staff_{MOCK_TENANT_ID}_mock_{i}"
        if not col.find_one({"tenant": MOCK_TENANT_ID, "id": sid}):
            col.insert_one({
                "id": sid,
                "tenant": MOCK_TENANT_ID,
                "name": name,
                "role": job_role,
                "phone": f"+9190003333{i:02d}",
                "email": email,
                "skills": [],
                "active": True,
                "created_at": NOW,
                "updated_at": NOW,
                "is_mock": True,
            })

    # ---------- Portal login users per caps profile ---------------------------
    from app.helpers.permission_profiles import caps_for_profile

    # Viewer caps: can see everything but cannot change anything
    viewer_caps = caps_for_profile("viewer")

    # Editor caps: can view and create/edit records
    editor_caps = caps_for_profile("editor")

    # Manager caps: full operational access, no sensitive data
    manager_caps = caps_for_profile("manager")

    # Custom: only appointments view + customer view (minimal example)
    custom_caps = [
        "core.dashboard.view",
        "salon.appointments.view",
        "core.customers.view",
    ]

    portal_users = [
        {
            "id":           f"user_demo_manager",
            "email":        "manager@demo.com",
            "role":         "staff",
            "display_name": "Ravi Kumar (Manager)",
            "caps":         manager_caps,
            "description":  "Manager profile — full operations, no financial/PII sensitive access",
        },
        {
            "id":           f"user_demo_reception",
            "email":        "reception@demo.com",
            "role":         "staff",
            "display_name": "Priya Das (Receptionist)",
            "caps":         editor_caps,
            "description":  "Editor profile — can view and create/edit records",
        },
        {
            "id":           f"user_demo_therapist",
            "email":        "therapist@demo.com",
            "role":         "staff",
            "display_name": "Anand Singh (Therapist)",
            "caps":         viewer_caps,
            "description":  "Viewer profile — read-only access across all pages",
        },
        {
            "id":           f"user_demo_intern",
            "email":        "intern@demo.com",
            "role":         "staff",
            "display_name": "Suma Raj (Intern)",
            "caps":         custom_caps,
            "description":  "Custom profile — only appointments and customers, view only",
        },
    ]

    created = 0
    for u in portal_users:
        if users_col.find_one({"email": u["email"].lower().strip()}):
            continue
        users_col.insert_one({
            **u,
            "tenant":       MOCK_TENANT_ID,
            "email":        u["email"].lower().strip(),
            "password_hash": Storage._hash_password("Demo@1234"),
            "status":       "active",
            "created_at":   NOW,
            "updated_at":   NOW,
            "is_mock":      True,
        })
        created += 1

    print(f"  staff: 4 demo staff records seeded.")
    print(f"  portal_users: {created} staff portal logins seeded (password: Demo@1234)")
    if created == 0:
        print("  portal_users: already present.")


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
        pros = _db().get_collection("professionals")
        pro_doc = pros.find_one({"tenant": MOCK_TENANT_ID, "name": "Dr. Demo One"})
        pid = (pro_doc or {}).get("professional_id")
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "id": aid,
            "customer_name": "Demo Customer One",
            "customer_phone": "+919000111101",
            "professional": "Dr. Demo One",
            "professional_id": pid,
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
    for i, (sku, name, cat, price, mrp, desc, img_urls) in enumerate([
        (
            "SKU-DEMO-1",
            "Demo Product A",
            "Demo Category",
            29.99,
            34.99,
            "A versatile everyday product for all occasions. Comes in multiple sizes.",
            ["/v1/media/tenant_demo/product_a_front.jpg", "/v1/media/tenant_demo/product_a_back.jpg"],
        ),
        (
            "SKU-DEMO-2",
            "Demo Product B",
            "Demo Category",
            49.99,
            59.99,
            "Premium quality with extended durability. Ideal for professional use.",
            ["/v1/media/tenant_demo/product_b_main.jpg"],
        ),
        (
            "SKU-DEMO-3",
            "Demo Product C",
            "Electronics",
            99.00,
            119.00,
            "High-performance electronic device. Includes 1-year manufacturer warranty.",
            ["/v1/media/tenant_demo/product_c_main.jpg", "/v1/media/tenant_demo/product_c_box.jpg"],
        ),
    ]):
        if col.find_one({"tenant": MOCK_TENANT_ID, "sku": sku}):
            continue
        col.insert_one({
            "tenant": MOCK_TENANT_ID,
            "sku": sku,
            "name": name,
            "category": cat,
            "price": price,
            "mrp": mrp,
            "active": True,
            "unit": "pcs",
            "description": desc,
            "image_urls": img_urls,
            "image_url": img_urls[0],  # backward-compat primary image
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


def seed_offers():
    col = _db().get_collection("offers")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 2:
        print("  offers: mock data already present.")
        return

    valid_from = NOW
    valid_until = NOW + dt.timedelta(days=90)

    def ensure_offer(title: str, extra: dict):
        if col.find_one({"tenant": MOCK_TENANT_ID, "title": title}):
            return
        doc = {
            "tenant": MOCK_TENANT_ID,
            "title": title,
            "description": f"Demo offer: {title}",
            "valid_from": valid_from,
            "valid_until": valid_until,
            "active": True,
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        }
        doc.update(extra)
        col.insert_one(doc)

    ensure_offer(
        "Summer Sale",
        {
            "description": "20% off Demo Category products — limited time.",
            "product_skus": ["SKU-DEMO-1", "SKU-DEMO-2"],
            "discount_info": {"type": "percent", "value": 20},
        },
    )
    ensure_offer(
        "Flat 10 Off Electronics",
        {
            "description": "Get ₹10 off on all electronics.",
            "product_skus": ["SKU-DEMO-3"],
            "discount_info": {"type": "amount", "value": 10},
        },
    )
    print("  offers: 2 mock offers inserted (Summer Sale, Flat 10 Off Electronics).")


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

    ensure_promo(
        "Welcome – 20% Off First Visit",
        {
            "channel": "both",
            "message": "💇‍♀️ Welcome to Demo Salon!\n\nEnjoy *20% OFF* your first service. Book now and look your best!\nUse code FIRST20.\n\n📍 1 Demo Street, Chennai",
            "offer_code": "FIRST20",
        },
    )
    ensure_promo(
        "Season Sale – Hair Color",
        {
            "channel": "sms+whatsapp",
            "message": "🎨 Season Sale at Demo Salon! 15% OFF on all Hair Color services this week. Book your slot today. Code: COLOR15.",
            "offer_code": "COLOR15",
        },
    )
    ensure_promo(
        "WhatsApp CTA – Book Now",
        {
            "channel": "whatsapp",
            "message": "Exclusive offer for our WhatsApp customers!\n\nTap below to book your appointment online and get a *₹100 discount* on your next visit.",
            "interactive_type": "cta_url",
            "cta_entries": [{"id": "cta_1", "display_text": "Book Appointment", "url": "https://example.com/book"}],
            "cta_append_urls_to_body": True,
            "offer_code": "WA100",
        },
    )
    ensure_promo(
        "SMS Flash Deal",
        {
            "channel": "sms",
            "message": "Demo Salon: Flash deal today only! Any service above Rs.500 at 10% OFF. Call +91 9000 111 000 to book. Code: FLASH10. Valid till 8 PM.",
            "attachments": [{"type": "link", "url": "https://example.com/book", "name": "Book Online"}],
            "offer_code": "FLASH10",
        },
    )
    print("  promotions: 4 demo promotions ensured.")


def seed_workflows():
    col = _db().get_collection("workflows")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  workflows: mock data already present.")
        return

    # Full booking: service → date → time → confirm (4 steps + END)
    full_booking_steps = [
        {"action_code": "SHOW_SERVICES",   "label": "Please choose a service:",        "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "SELECT_DATE",      "label": "Select your preferred date:",     "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "SELECT_TIME",      "label": "Choose an available time slot:",  "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your booking",            "input_required": False, "ui_type": "list", "params": {}},
        {"action_code": "END",              "label": "✅ Your appointment is confirmed! We'll send you a reminder 24 hours before. Reply *hi* anytime to return to the main menu.",
         "input_required": False, "ui_type": "list", "params": {}},
    ]

    # Express booking: service → date → confirm (no time step — system auto-picks first slot)
    express_booking_steps = [
        {"action_code": "SHOW_SERVICES",   "label": "Please choose a service:",     "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "SELECT_DATE",      "label": "Select your preferred date:", "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "CONFIRM_BOOKING",  "label": "Confirm your booking",        "input_required": False, "ui_type": "list", "params": {}},
        {"action_code": "END",              "label": "✅ Booked! We'll assign your slot and send a reminder. Reply *hi* for the main menu.", "input_required": False, "ui_type": "list", "params": {}},
    ]

    # Quick booking: service → confirm (system auto-assigns date & slot)
    quick_booking_steps = [
        {"action_code": "SHOW_SERVICES",  "label": "Pick a service and we'll book the next available slot:", "input_required": True,  "ui_type": "list", "params": {}},
        {"action_code": "CONFIRM_BOOKING","label": "Confirm your appointment",                                "input_required": False, "ui_type": "list", "params": {}},
        {"action_code": "END",            "label": "✅ Done! We've booked your next available slot. Reply *hi* anytime.", "input_required": False, "ui_type": "list", "params": {}},
    ]

    price_list_steps = [
        {"action_code": "SHOW_SERVICE_PRICES", "label": "💇 *Our Services & Prices*", "input_required": False, "ui_type": "list", "params": {}},
        {"action_code": "END", "label": "Reply *hi* for the main menu or *book* to schedule an appointment.", "input_required": False, "ui_type": "list", "params": {}},
    ]

    workflows = [
        {
            "tenant": MOCK_TENANT_ID,
            "workflow_id": "demo_booking_flow",
            "name": "Appointment Booking Flow (Full)",
            "description": "Full booking: choose service → date → time → confirm.",
            "steps": full_booking_steps,
            "active": True,
            "requires_caps": ["appointments"],
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        },
        {
            "tenant": MOCK_TENANT_ID,
            "workflow_id": "demo_express_booking_flow",
            "name": "Express Booking (Service + Date)",
            "description": "Short booking: choose service and date — time auto-assigned.",
            "steps": express_booking_steps,
            "active": True,
            "requires_caps": ["appointments"],
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        },
        {
            "tenant": MOCK_TENANT_ID,
            "workflow_id": "demo_quick_booking_flow",
            "name": "Quick Booking (Service Only)",
            "description": "Fastest booking: choose service — date and time auto-assigned to next available slot.",
            "steps": quick_booking_steps,
            "active": True,
            "requires_caps": ["appointments"],
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        },
        {
            "tenant": MOCK_TENANT_ID,
            "workflow_id": "demo_price_list_flow",
            "name": "Services & Price List",
            "description": "Live price list from tenant services catalog.",
            "steps": price_list_steps,
            "active": True,
            "requires_caps": ["appointments"],
            "created_at": NOW,
            "updated_at": NOW,
            "is_mock": True,
        },
    ]
    col.insert_many(workflows)
    print(f"  workflows: {len(workflows)} flows inserted (full / express / quick / price list).")


def seed_whatsapp_menus():
    col = _db().get_collection("whatsapp_menus")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  whatsapp_menus: mock data already present.")
        return
    col.insert_one({
        "tenant": MOCK_TENANT_ID,
        "menu_id": "welcome_message",
        "name": "Demo Salon – Main Menu",
        "status": "published",
        "version": 1,
        "tree": {
            "root": "main",
            "nodes": [
                {
                    "id": "main",
                    "type": "submenu",
                    "title": "Welcome to *Demo Salon* ✨",
                    "prompt": "How can we help you today?",
                    "options": [
                        {"key": "1", "label": "Book Appointment (Full)",    "next": "workflow.demo_booking_flow"},
                        {"key": "2", "label": "Express Booking",            "next": "workflow.demo_express_booking_flow"},
                        {"key": "3", "label": "Quick Booking (Auto-Slot)",  "next": "workflow.demo_quick_booking_flow"},
                        {"key": "4", "label": "Services & Prices",          "next": "workflow.demo_price_list_flow"},
                        {"key": "5", "label": "Location & Hours",           "next": "location_info"},
                        {"key": "6", "label": "Contact Us",                 "next": "contact_info"},
                    ],
                },
                {
                    "id": "services_info",
                    "type": "action",
                    "action_type": "static_text",
                    "text": (
                        "💇 *Our Services & Prices*\n\n"
                        "• Haircut (Women) – ₹600\n"
                        "• Haircut (Men) – ₹400\n"
                        "• Hair Color – ₹1,200\n"
                        "• Facial – ₹800\n"
                        "• Blow Dry & Style – ₹350\n"
                        "• Manicure & Pedicure – ₹700\n\n"
                        "Reply *hi* to return to the main menu."
                    ),
                },
                {
                    "id": "location_info",
                    "type": "action",
                    "action_type": "static_text",
                    "text": (
                        "📍 *Demo Salon*\n"
                        "23 MG Road, Bengaluru – 560001\n\n"
                        "🕐 Mon–Sat: 9 AM – 7 PM\n"
                        "🕐 Sunday: 10 AM – 5 PM\n\n"
                        "📞 +91 98765 00001\n\n"
                        "Reply *hi* for main menu."
                    ),
                },
                {
                    "id": "cancel_info",
                    "type": "action",
                    "action_type": "static_text",
                    "text": (
                        "❌ *Cancel Appointment*\n\n"
                        "To cancel, reply: CANCEL <your name>\n"
                        "Or call: +91 98765 00001\n\n"
                        "We'll confirm within 30 minutes.\n\n"
                        "Reply *hi* for main menu."
                    ),
                },
                {
                    "id": "contact_info",
                    "type": "action",
                    "action_type": "static_text",
                    "text": (
                        "💬 *Get in Touch*\n\n"
                        "📞 +91 98765 00001\n"
                        "📧 admin@tenant.demo\n\n"
                        "We reply within 1 hour.\n\n"
                        "Reply *hi* for main menu."
                    ),
                },
            ],
            "edges": [],
        },
        "locales": {},
        "updated_at": NOW,
        "is_mock": True,
    })
    print("  whatsapp_menus: 1 demo menu inserted (published, 6-node tree with quick booking).")


def seed_whatsapp_triggers():
    col = _db().get_collection("whatsapp_triggers")
    if col.count_documents({"tenant": MOCK_TENANT_ID}) >= 1:
        print("  whatsapp_triggers: mock data already present.")
        return
    triggers = [
        {
            "tenant": MOCK_TENANT_ID,
            "trigger_id": "demo_hi",
            "match": {"type": "exact", "value": "hi"},
            "action": {"kind": "static_text", "text": "👋 Welcome to *Demo Salon*!\n\nReply:\n1️⃣ Book appointment\n2️⃣ Our services & prices\n3️⃣ Location & hours\n4️⃣ Cancel appointment"},
            "enabled": True, "priority": 10, "updated_at": NOW, "is_mock": True,
        },
        {
            "tenant": MOCK_TENANT_ID,
            "trigger_id": "demo_book",
            "match": {"type": "exact", "value": "book"},
            "action": {"kind": "invoke_action", "action_id": "workflow.demo_booking_flow"},
            "enabled": True, "priority": 9, "updated_at": NOW, "is_mock": True,
        },
        {
            "tenant": MOCK_TENANT_ID,
            "trigger_id": "demo_prices",
            "match": {"type": "contains", "value": "price"},
            "action": {"kind": "invoke_action", "action_id": "show_service_prices"},
            "enabled": True, "priority": 8, "updated_at": NOW, "is_mock": True,
        },
    ]
    col.insert_many(triggers)
    print("  whatsapp_triggers: 3 demo triggers inserted.")


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
    seed_offers()
    seed_promotions()
    seed_workflows()
    seed_whatsapp_menus()
    seed_whatsapp_triggers()
    seed_cron_jobs()
    seed_ai_knowledge_base()
    print("Done. Demo tenant:", MOCK_TENANT_ID)
    print()
    print("─── Login credentials ───────────────────────────────────────")
    print(f"  Tenant Admin  : {MOCK_EMAIL}          | {MOCK_PASSWORD}")
    print("  Manager       : manager@demo.com      | Demo@1234  (staff, manager caps)")
    print("  Receptionist  : reception@demo.com    | Demo@1234  (staff, editor caps)")
    print("  Therapist     : therapist@demo.com    | Demo@1234  (staff, viewer caps)")
    print("  Intern        : intern@demo.com       | Demo@1234  (staff, custom caps)")


if __name__ == "__main__":
    main()
