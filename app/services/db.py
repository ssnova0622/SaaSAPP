from __future__ import annotations
from typing import Tuple
import uuid
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError

from settings import MONGO_URI

_client: MongoClient | None = None
_db = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    global _db
    if _db is None:
        client = get_client()
        # will raise if cannot connect (lazy otherwise)
        try:
            client.admin.command("ping")
        except ServerSelectionTimeoutError as e:
            raise RuntimeError(f"Unable to connect to MongoDB at {MONGO_URI}: {e}")
        # get_default_database() may raise ConfigurationError if no DB in URI
        default_db = None
        try:
            default_db = client.get_default_database()
        except ConfigurationError:
            default_db = None
        # Important: PyMongo Database objects do not support truthiness; compare with None explicitly
        _db = default_db if default_db is not None else client.get_database("ai_appo")
        _ensure_indexes()
    return _db


def collections() -> Tuple:
    db = get_db()
    return (
        db.get_collection("tenants"),
        db.get_collection("professionals"),
        db.get_collection("appointments"),
    )


def customers_collection():
    db = get_db()
    return db.get_collection("customers")


def staff_collection():
    db = get_db()
    return db.get_collection("staff")


def services_collection():
    db = get_db()
    return db.get_collection("services")


def workflows_collection():
    db = get_db()
    return db.get_collection("workflows")


def tenant_message_templates_collection():
    """Per-tenant message template overrides (key -> body). Linked by tenant_id."""
    return get_db().get_collection("tenant_message_templates")


def default_message_collection():
    """Platform-wide default copy (single doc _id='platform'). Super admin editable."""
    return get_db().get_collection("default_message")


def users_collection():
    db = get_db()
    return db.get_collection("users")


def whatsapp_sessions_collection():
    """Collection for WhatsApp session state (tenant, phone, ctx, etc.)."""
    return get_db().get_collection("whatsapp_sessions")


def events_collection():
    """Collection for analytics/AI events."""
    return get_db().get_collection("events")


def counters_collection():
    """Collection for atomic counters (e.g. appointment ID sequence)."""
    return get_db().get_collection("counters")


def whatsapp_actions_collection():
    """Global WhatsApp actions (Super Admin CRUD). No tenant; one collection for all actions."""
    return get_db().get_collection("whatsapp_actions")


def _migrate_professionals_professional_id(professionals) -> None:
    """Backfill professional_id and employee_id; unique (tenant, professional_id), (tenant, name), (tenant, employee_id)."""
    try:
        for doc in professionals.find(
                {
                    "$or": [
                        {"professional_id": {"$exists": False}},
                        {"professional_id": None},
                        {"professional_id": ""},
                    ]
                }
        ):
            professionals.update_one(
                {"_id": doc["_id"]},
                {"$set": {"professional_id": str(uuid.uuid4())}},
            )

        for doc in professionals.find(
                {
                    "$or": [
                        {"employee_id": {"$exists": False}},
                        {"employee_id": None},
                        {"employee_id": ""},
                    ]
                }
        ):
            pid = str(doc.get("professional_id") or "")
            base = "".join(c for c in pid if c.isalnum())[:20] or "EMP"
            eid = base.upper()
            n = 0
            tid = doc["tenant"]
            while True:
                cand = eid if n == 0 else f"{eid}-{n}"
                clash = professionals.find_one(
                    {"tenant": tid, "employee_id": cand, "_id": {"$ne": doc["_id"]}}
                )
                if not clash:
                    break
                n += 1
            professionals.update_one({"_id": doc["_id"]}, {"$set": {"employee_id": cand}})

        for idx in list(professionals.list_indexes()):
            key = idx.get("key")
            if key is None:
                continue
            keys = dict(key)
            if keys.get("tenant") == 1 and keys.get("name") == 1:
                try:
                    professionals.drop_index(idx["name"])
                except Exception:
                    pass

        professionals.create_index([("tenant", ASCENDING), ("professional_id", ASCENDING)], unique=True)
        try:
            professionals.create_index([("tenant", ASCENDING), ("name", ASCENDING)], unique=True)
        except Exception:
            pass
        try:
            # sparse=True: skip docs where employee_id is null/missing so multiple
            # professionals without an employee_id don't conflict.
            professionals.create_index(
                [("tenant", ASCENDING), ("employee_id", ASCENDING)],
                unique=True,
                sparse=True,
            )
        except Exception:
            pass
    except Exception:
        # Non-fatal: app can still run; creation paths may fail until DB is fixed
        pass


def _ensure_indexes() -> None:
    db = get_db() if _db is None else _db
    tenants = db.get_collection("tenants")
    professionals = db.get_collection("professionals")
    appointments = db.get_collection("appointments")
    customers = db.get_collection("customers")
    staff = db.get_collection("staff")
    carts = db.get_collection("carts")
    orders = db.get_collection("orders")
    payments = db.get_collection("payments")
    products = db.get_collection("products")
    categories = db.get_collection("categories")
    inventory = db.get_collection("inventory")

    # Tenants: primary key is _id (tenant string)

    _migrate_professionals_professional_id(professionals)
    professionals.create_index([("tenant", ASCENDING)])
    professionals.create_index([("tenant", ASCENDING), ("active", ASCENDING)])

    # Appointments: frequent queries by tenant, professional, time, status
    appointments.create_index([("tenant", ASCENDING)])
    appointments.create_index([("tenant", ASCENDING), ("professional", ASCENDING)])
    appointments.create_index([("tenant", ASCENDING), ("professional_id", ASCENDING)])
    appointments.create_index([("tenant", ASCENDING), ("time", ASCENDING)])
    appointments.create_index([("tenant", ASCENDING), ("status", ASCENDING)])
    # Daily reports slice by created_at within tenant
    appointments.create_index([("tenant", ASCENDING), ("created_at", ASCENDING)])

    # Customers: unique per tenant + phone_number {code, number}
    try:
        customers.drop_index("tenant_1_phone_1")
    except Exception:
        pass
    customers.create_index(
        [("tenant", ASCENDING), ("phone_number.code", ASCENDING), ("phone_number.number", ASCENDING)],
        unique=True,
        name="tenant_phone_number_unique",
    )
    customers.create_index([("tenant", ASCENDING)])
    customers.create_index([("tenant", ASCENDING), ("tags", ASCENDING)])
    customers.create_index([("tenant", ASCENDING), ("name", ASCENDING)])
    customers.create_index([("tenant", ASCENDING), ("active", ASCENDING)])

    # Staff: unique per tenant+id and search by tenant/name/role/active
    staff.create_index([( "tenant", ASCENDING ), ( "id", ASCENDING )], unique=True)
    staff.create_index([( "tenant", ASCENDING )])
    staff.create_index([( "tenant", ASCENDING ), ( "name", ASCENDING )])
    staff.create_index([( "tenant", ASCENDING ), ( "role", ASCENDING )])
    staff.create_index([( "tenant", ASCENDING ), ( "active", ASCENDING )])

    try:
        carts.drop_index("tenant_1_customer_phone_1")
    except Exception:
        pass
    carts.create_index(
        [
            ("tenant", ASCENDING),
            ("customer_phone_number.code", ASCENDING),
            ("customer_phone_number.number", ASCENDING),
        ],
        unique=True,
        name="tenant_cart_phone_number_unique",
    )
    carts.create_index([( "tenant", ASCENDING ), ( "updated_at", ASCENDING )])

    # Orders
    orders.create_index([( "tenant", ASCENDING ), ( "id", ASCENDING )], unique=True)
    orders.create_index([( "tenant", ASCENDING ), ( "created_at", ASCENDING )])
    orders.create_index([( "tenant", ASCENDING ), ( "status", ASCENDING )])
    orders.create_index([( "tenant", ASCENDING ), ( "customer.phone", ASCENDING )])

    # Payments
    payments.create_index([( "tenant", ASCENDING ), ( "order_id", ASCENDING )])
    payments.create_index([( "tenant", ASCENDING ), ( "status", ASCENDING )])

    # Catalog / Inventory
    products.create_index([( "tenant", ASCENDING ), ( "sku", ASCENDING )], unique=True)
    products.create_index([( "tenant", ASCENDING ), ( "name", ASCENDING )])
    products.create_index([( "tenant", ASCENDING ), ( "category", ASCENDING )])
    products.create_index([( "tenant", ASCENDING ), ( "active", ASCENDING )])

    categories.create_index([( "tenant", ASCENDING ), ( "name", ASCENDING )], unique=True)
    categories.create_index([( "tenant", ASCENDING ), ( "active", ASCENDING )])

    inventory.create_index([( "tenant", ASCENDING ), ( "sku", ASCENDING )], unique=True)
    inventory.create_index([( "tenant", ASCENDING ), ( "available_qty", ASCENDING )])

    # Store offers (tenant-created, time-bound offers for customers)
    store_offers = db.get_collection("store_offers")
    store_offers.create_index([("tenant", ASCENDING), ("id", ASCENDING)], unique=True)
    store_offers.create_index([("tenant", ASCENDING), ("valid_from", ASCENDING), ("valid_until", ASCENDING)])
    store_offers.create_index([("tenant", ASCENDING), ("active", ASCENDING)])

    # Cron Jobs
    cron_jobs = db.get_collection("cron_jobs")
    cron_jobs.create_index([("job_id", ASCENDING)], unique=True)
    cron_jobs.create_index([("type", ASCENDING)])

    # Services (Tenant-based services like Dentist, Eye Doctor, Hair Cut, etc.)
    services = db.get_collection("services")
    services.create_index([("tenant", ASCENDING), ("name", ASCENDING)], unique=True)
    services.create_index([("tenant", ASCENDING)])
    services.create_index([("tenant", ASCENDING), ("active", ASCENDING)])

    # Workflows
    workflows = db.get_collection("workflows")
    workflows.create_index([("tenant", ASCENDING), ("workflow_id", ASCENDING)], unique=True)
    workflows.create_index([("tenant", ASCENDING)])

    # Tenant message templates (one doc per tenant)
    tenant_message_templates = db.get_collection("tenant_message_templates")
    tenant_message_templates.create_index([("tenant_id", ASCENDING)], unique=True)

    db.get_collection("default_message")

    # Users
    users = db.get_collection("users")
    users.create_index([("email", ASCENDING)], unique=True)
    users.create_index([("tenant", ASCENDING)])
    users.create_index([("role", ASCENDING)])

    # Global WhatsApp actions (Super Admin)
    whatsapp_actions = db.get_collection("whatsapp_actions")
    whatsapp_actions.create_index([("action_id", ASCENDING)], unique=True)
