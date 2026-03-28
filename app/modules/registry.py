from __future__ import annotations
from typing import Dict, List, Tuple

# Simple built-in module/capability registry
# type: 'module' or 'capability'
_REGISTRY: List[Dict] = [
    # Modules (top-level switches assignable per tenant)
    {"id": "core", "type": "module", "group": "Modules", "label": "Core", "description": "Core platform features"},
    {"id": "store", "type": "module", "group": "Modules", "label": "Store",
     "description": "Storefront: catalog, orders, payments"},
    {"id": "salon", "type": "module", "group": "Modules", "label": "Salon",
     "description": "Salon/appointments features"},
    {"id": "clinic", "type": "module", "group": "Modules", "label": "Clinic",
     "description": "Clinic/appointments features"},
    {"id": "ai", "type": "module", "group": "Modules", "label": "AI",
     "description": "AI features for salon/clinic and store"},

    # Capabilities — RBAC: view / edit / edit_sensitive / delete per entity (Tenant/Super Admin = all; Staff = by caps; Viewer = view only)
    # Core
    {"id": "core.dashboard.view", "type": "capability", "module": "core", "group": "Core", "label": "Dashboard — View",
     "description": "View dashboard", "default": True},
    {"id": "core.settings.view", "type": "capability", "module": "core", "group": "Core", "label": "Settings — View",
     "description": "View tenant settings", "default": False},
    {"id": "core.settings.edit", "type": "capability", "module": "core", "group": "Core", "label": "Settings — Edit",
     "description": "Edit non-sensitive settings", "default": False},
    {"id": "core.settings.edit_sensitive", "type": "capability", "module": "core", "group": "Core",
     "label": "Settings — Edit sensitive", "description": "Edit sensitive tenant/config", "default": False},
    {"id": "core.tenants", "type": "capability", "module": "core", "group": "Core", "label": "Tenants",
     "description": "Manage tenants (Super Admin)", "default": False},
    {"id": "core.users.view", "type": "capability", "module": "core", "group": "Core", "label": "Users — View",
     "description": "View users/staff list", "default": False},
    {"id": "core.users.edit", "type": "capability", "module": "core", "group": "Core", "label": "Users — Edit",
     "description": "Create/edit users (staff)", "default": False},
    {"id": "core.users.edit_sensitive", "type": "capability", "module": "core", "group": "Core",
     "label": "Users — Edit sensitive", "description": "Edit roles, caps, passwords", "default": False},
    {"id": "core.customers.view", "type": "capability", "module": "core", "group": "Core", "label": "Customers — View",
     "description": "View customers list", "default": False},
    {"id": "core.customers.edit", "type": "capability", "module": "core", "group": "Core", "label": "Customers — Edit",
     "description": "Edit customer data (non-sensitive)", "default": False},
    {"id": "core.customers.edit_sensitive", "type": "capability", "module": "core", "group": "Core",
     "label": "Customers — Edit sensitive", "description": "Edit PII, payment info", "default": False},
    {"id": "core.staff", "type": "capability", "module": "core", "group": "Core", "label": "Staff",
     "description": "Manage staff members", "default": False},
    {"id": "core.promotions", "type": "capability", "module": "core", "group": "Core", "label": "Promotions",
     "description": "Create and send promotions", "default": False},
    {"id": "core.followups", "type": "capability", "module": "core", "group": "Core", "label": "Follow-ups",
     "description": "Automated follow-ups", "default": False},
    {"id": "core.reports.view", "type": "capability", "module": "core", "group": "Core", "label": "Reports — View",
     "description": "View reports and analytics", "default": False},
    {"id": "core.retention", "type": "capability", "module": "core", "group": "Core", "label": "Retention",
     "description": "Retention metrics", "default": False},
    {"id": "core.whatsapp_menu", "type": "capability", "module": "core", "group": "Core",
     "label": "WhatsApp Menu Builder", "description": "Configure WhatsApp bot menus", "default": False},
    # Legacy core (backward compat)
    {"id": "core.dashboard", "type": "capability", "module": "core", "group": "Core", "label": "Dashboard (legacy)",
     "description": "Alias for core.dashboard.view", "default": True},
    {"id": "core.settings", "type": "capability", "module": "core", "group": "Core", "label": "Settings (legacy)",
     "description": "Tenant settings", "default": False},
    {"id": "core.users", "type": "capability", "module": "core", "group": "Core", "label": "Users (legacy)",
     "description": "Manage users", "default": False},
    {"id": "core.customers", "type": "capability", "module": "core", "group": "Core", "label": "Customers (legacy)",
     "description": "Manage customers", "default": False},
    {"id": "core.reports", "type": "capability", "module": "core", "group": "Core", "label": "Reports (legacy)",
     "description": "Reports", "default": False},

    # Salon — Services (service definitions: Haircut, Facial, etc.)
    {"id": "salon.services.view", "type": "capability", "module": "salon", "group": "Salon", "label": "Services — View",
     "description": "View service definitions (Haircut, Facial, Hair Specialist, etc.)", "default": True},
    {"id": "salon.services.edit", "type": "capability", "module": "salon", "group": "Salon", "label": "Services — Edit",
     "description": "Create, edit, delete service definitions", "default": False},
    {"id": "salon.services", "type": "capability", "module": "salon", "group": "Salon", "label": "Services (legacy)",
     "description": "Full access to service definitions", "default": False},
    # Salon — Professionals
    {"id": "salon.professionals.view", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals — View", "description": "View professionals list and slots", "default": True},
    {"id": "salon.professionals.edit", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals — Edit", "description": "Slots, availability, activate/deactivate (no fees/contact)",
     "default": True},
    {"id": "salon.professionals.edit_sensitive", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals — Edit sensitive", "description": "Fees, education, phone, address, bio",
     "default": False},
    {"id": "salon.professionals.create", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals — Create", "description": "Create new professionals", "default": False},
    {"id": "salon.professionals.delete", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals — Delete", "description": "Delete/deactivate professionals", "default": False},
    {"id": "salon.professionals", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals view (legacy)", "description": "View professionals", "default": True},
    {"id": "salon.professionals.manage", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Professionals edit_sensitive (legacy)", "description": "Edit sensitive details", "default": False},
    # Salon — Appointments
    {"id": "salon.appointments.view", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Appointments — View", "description": "View appointments list", "default": True},
    {"id": "salon.appointments.edit", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Appointments — Edit", "description": "Complete, cancel, reschedule, no-show, create", "default": True},
    {"id": "salon.appointments.delete", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Appointments — Delete", "description": "Cancel/delete appointments", "default": True},
    {"id": "salon.appointments", "type": "capability", "module": "salon", "group": "Salon",
     "label": "Appointments view (legacy)", "description": "View appointments", "default": True},
    # Salon — No-Show Blocked
    {"id": "salon.no_show_blocked.view", "type": "capability", "module": "salon", "group": "Salon",
     "label": "No-Show Blocked — View", "description": "View blocked list", "default": False},
    {"id": "salon.no_show_blocked.edit", "type": "capability", "module": "salon", "group": "Salon",
     "label": "No-Show Blocked — Edit", "description": "Reset no-show count", "default": False},
    {"id": "salon.no_show_blocked", "type": "capability", "module": "salon", "group": "Salon",
     "label": "No-Show Blocked view (legacy)", "description": "View list", "default": False},

    # Store — Orders
    {"id": "store.orders.view", "type": "capability", "module": "store", "group": "Store", "label": "Orders — View",
     "description": "View orders and carts", "default": True},
    {"id": "store.orders.edit", "type": "capability", "module": "store", "group": "Store", "label": "Orders — Edit",
     "description": "Update status, fulfill (non-sensitive)", "default": True},
    {"id": "store.orders.edit_sensitive", "type": "capability", "module": "store", "group": "Store",
     "label": "Orders — Edit sensitive", "description": "Refunds, payment details", "default": False},
    {"id": "store.orders.delete", "type": "capability", "module": "store", "group": "Store", "label": "Orders — Delete",
     "description": "Cancel/void orders", "default": False},
    {"id": "store.orders", "type": "capability", "module": "store", "group": "Store", "label": "Orders (legacy)",
     "description": "Orders access", "default": True},
    {"id": "store.payments", "type": "capability", "module": "store", "group": "Store", "label": "Payments",
     "description": "Online payments", "default": True},
    {"id": "store.catalog", "type": "capability", "module": "store", "group": "Store", "label": "Catalog",
     "description": "Product catalog", "default": False},
    {"id": "store.inventory", "type": "capability", "module": "store", "group": "Store", "label": "Inventory",
     "description": "Inventory management", "default": False},

    # AI capabilities (derived automatically from modules by tenants router)
    {"id": "ai.whatsapp_intents", "type": "capability", "module": "ai", "group": "AI",
     "label": "AI Pro (WhatsApp Intents)",
     "description": "Understand natural language and run workflows (e.g. book, cancel, reschedule, 'book with X at 2pm tomorrow')",
     "default": False},
    {"id": "ai.appointment_recs", "type": "capability", "module": "ai", "group": "AI",
     "label": "AI Appointment Recommendations", "description": "Recommend best time slots for Salon/Clinic",
     "default": False},
    {"id": "ai.reschedule", "type": "capability", "module": "ai", "group": "AI", "label": "AI Auto-Rescheduling",
     "description": "Propose and automate rescheduling", "default": False},
    {"id": "ai.no_show", "type": "capability", "module": "ai", "group": "AI", "label": "AI No-Show Prediction",
     "description": "Predict and prevent no-shows", "default": False},
    {"id": "ai.personalize", "type": "capability", "module": "ai", "group": "AI", "label": "AI Personalized Services",
     "description": "Next-best service recommendations", "default": False},
    {"id": "ai.staff_balance", "type": "capability", "module": "ai", "group": "AI", "label": "AI Staff Load Balancing",
     "description": "Distribute workload across staff", "default": False},
    {"id": "ai.dynamic_pricing", "type": "capability", "module": "ai", "group": "AI", "label": "AI Dynamic Pricing",
     "description": "Suggest price adjustments with guardrails", "default": False},
    {"id": "ai.whatsapp_followup", "type": "capability", "module": "ai", "group": "AI",
     "label": "AI WhatsApp Follow-ups", "description": "Retention and post-visit follow-ups", "default": False},
    {"id": "ai.treatment_insights", "type": "capability", "module": "ai", "group": "AI",
     "label": "AI Treatment Insights", "description": "Clinic treatment history insights", "default": False},
    {"id": "ai.voice_actions", "type": "capability", "module": "ai", "group": "AI", "label": "AI Voice → Actions",
     "description": "Convert voice notes to actions", "default": False},
    {"id": "ai.biz_insights", "type": "capability", "module": "ai", "group": "AI", "label": "AI Business Insights",
     "description": "Owner dashboard summaries", "default": False},
]


def list_registry() -> List[Dict]:
    return list(_REGISTRY)


def ids_map() -> Dict[str, Dict]:
    return {e["id"]: e for e in _REGISTRY}


def is_module(id_: str) -> bool:
    e = ids_map().get(id_)
    return bool(e and e.get("type") == "module")


def is_capability(id_: str) -> bool:
    e = ids_map().get(id_)
    return bool(e and e.get("type") == "capability")


def capability_module(cap_id: str) -> str | None:
    e = ids_map().get(cap_id)
    if not e or e.get("type") != "capability":
        return None
    return e.get("module")


def module_defaults(module_ids: List[str]) -> List[str]:
    """Return default capabilities for the given enabled modules."""
    mids = {str(m).lower().strip() for m in (module_ids or [])}
    out: List[str] = []
    for e in _REGISTRY:
        if e.get("type") == "capability" and e.get("default", False):
            mod = str(e.get("module") or "").lower()
            if mod in mids:
                out.append(e["id"])
    return sorted(set(out))


def normalize_selection(modules: List[str] | None, capabilities: List[str] | None) -> Tuple[List[str], List[str]]:
    """Normalize module and capability selections.
    - Validate modules against registry
    - Capabilities must belong to selected modules
    - Include default capabilities of selected modules
    """
    m = ids_map()
    # Normalize modules
    mods_norm: List[str] = []
    for mod in (modules or []):
        mid = str(mod).strip().lower()
        if not mid:
            continue
        e = m.get(mid)
        if e and e.get("type") == "module":
            mods_norm.append(mid)
    mods = sorted(set(mods_norm))

    # Defaults for selected modules
    caps_set = set(module_defaults(mods))

    # Add requested capabilities that belong to selected modules
    for c in (capabilities or []):
        cid = str(c).strip().lower()
        if not cid or cid not in m or not is_capability(cid):
            continue
        mod = capability_module(cid)
        if mod and mod in mods:
            caps_set.add(cid)

    caps = sorted(caps_set)
    return mods, caps
