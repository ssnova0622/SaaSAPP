# app/services/core/default_message_service.py
"""
Application-wide default copy in MongoDB collection ``default_message`` (document ``_id``: platform).

- Runtime reads are cached (Redis when configured).
- ``MESSAGE_SEED_TEMPLATES`` only seeds **missing** keys; DB is source of truth.
- Tenant overrides live in ``tenant_message_templates`` only, never in ``default_message``.
- Optional migration: copies legacy ``whatsapp_messages`` platform doc if ``default_message`` is empty.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from app.helpers.audit_utils import audit_fields_for_create, audit_fields_for_update
from app.services.db import default_message_collection, get_db
from app.core.cache import (
    cache_delete_default_message_bundle,
    cache_get_default_message_bundle,
    cache_set_default_message_bundle,
    cache_invalidate_all_tenant_settings,
)

PLATFORM_DOC_ID = "platform"
_DEFAULT_MESSAGE_CACHE_TTL = 300
LEGACY_COLLECTION = "whatsapp_messages"

# Bootstrap: inserted only when a key is absent in DB.
MESSAGE_SEED_TEMPLATES: Dict[str, str] = {
    "whatsapp_hello": "Hello!",
    "whatsapp_service_offline": "Service offline",
    "whatsapp_feature_not_available": "Feature not available.",
    "whatsapp_processing": "Processing...",
    "whatsapp_done": "Done.",
    "booking_confirmation": (
        "Your appointment is confirmed, {customer_name}! 🎉\n"
        "📅 Date: {date}\n"
        "⏰ Time: {time}\n"
        "📍 Location: {location}\n"
        "{specialist_line}"
    ),
    "booking_confirm_prompt": "Confirm booking for {service} with {professional} at {time} on {date}?\n1) Yes\n2) No",
    "goodbye": "See you then! 😊\nType *menu* when you need something.",
    "welcome": "Welcome to {tenant_name}! Choose an option below.",
    "reschedule_confirm_prompt": "Confirm reschedule to {date} at {time} with {professional}?\n1) Yes\n2) No",
    "workflow_complete": "Your booking is all set! 🎉\nType anything to return to the main menu.",
    "followup_confirm": "Hi {name}, your booking with {pro} at {time} is confirmed. - {tenant}",
    "followup_reminder24": "Reminder: {pro} at {time} tomorrow. Reply 1 to confirm, 2 to reschedule. - {tenant}",
    "followup_reminder2": "Reminder: you are due in 2 hours for {pro} at {time}. - {tenant}",
    "followup_post": "Thanks for visiting! Please share feedback and book again. - {tenant}",
    "followup_recovery": "We're sorry to miss you. Would you like to rebook? - {tenant}",
    "followup_default": "Message from {tenant}",
    "wa_please_choose_option": "Please choose an option.",
    "wa_no_menu_published": "No published WhatsApp menu found. Please create and publish a menu in the Menu Editor first.",
    "wa_menu_error": "Menu error.",
    "wa_feedback_thanks": "Thank you for your feedback! You can leave a review here: {review_link}",
    "wa_invalid_fsm_menu_digit": "Invalid selection for the current step. Please try again or type 'menu' to restart.",
    "wa_type_menu_hint": "Type *menu* for options.",
    "wa_no_active_workflow": "No active workflow. Type 'menu' to start over.",
    "wa_flow_not_available": "This flow is not available. Type 'menu' to see options.",
    "wa_workflow_complete_menu": "Workflow complete. Type 'menu' to start over.",
    "wa_workflow_end_success": "Thank you — this flow is complete. Type *menu* when you need anything else.",
    "wa_invalid_input_retry": "Invalid input. Please try again.",
    "wa_workflow_step_error": "Something went wrong with this step. Please try again or type *menu* to restart.",
    "wa_inbound_pipeline_error": "Something went wrong. Please try again or type *menu* to restart.",
    "wa_option_not_available": "This option is not available for your account.",
    "wa_salon_pick_service": "What service would you like to book?",
    "wa_salon_pick_service_number": "Please choose a number between 1 and {max_n}.",
    "wa_salon_no_services": "No services available.",
    "wa_salon_service_prices_header": "💇 Our services & prices:",
    "wa_salon_service_price_on_request": "Price on request",
    "wa_salon_pick_staff": "Do you prefer a specific staff member?",
    "wa_salon_no_staff": "No staff available for {service}. Please choose another date or service.",
    "wa_salon_pick_staff_range": "Please choose 1-{max_n}.",
    "wa_salon_no_staff_options": "No options available.",
    "wa_salon_choose_date": "Please choose a date:",
    "wa_salon_invalid_date": "Invalid date. Use {date_format}.",
    "wa_salon_date_past": "Cannot book in the past.",
    "wa_salon_missing_prof_date": "Missing professional or date for time selection.",
    "wa_salon_no_slots_any_pro": "No available slots for any professional on this date.",
    "wa_salon_no_slots": "No slots available for {professional} on {date}.",
    "wa_salon_time_slots_header": "Available time slots with {professional} on {date}:",
    "wa_salon_pick_time_range": "Please choose 1-{max_n}.",
    "wa_salon_no_slots_list": "No slots available.",
    "wa_salon_pick_time_hint": "Reply with a number to choose a slot.",
    "wa_salon_auto_no_slots": "No available slots found for today.",
    "wa_salon_booking_cancelled": "Booking cancelled. Type 'menu' to start again.",
    "wa_salon_confirm_yes_no": "Please reply with 1 (Yes) or 2 (No).",
    "wa_core_ask_name": "May I have your name to confirm your appointment?",
    "wa_core_ask_details": "May I have your name and other details?",
    "wa_core_name_short": "Please enter at least 2 characters for your name.",
    "wa_core_name_long": "Name is too long. Please use a shorter name.",
    "wa_core_confirm_yes_no": "Please reply with 1 (Yes) or 2 (No).",
    "wa_core_confirm_intro": "Please confirm your booking:",
    "wa_core_no_details_yet": "(no details yet)",
    "wa_core_confirm_footer": "Reply 1 to confirm, 2 to cancel.",
    "wa_core_cancelled": "Cancelled. Type 'menu' to start again.",
    "wa_core_missing_fields": "Missing: {fields}. Go back or type 'menu' to restart.",
    "wa_core_feedback_prompt": "Please share your feedback in a few words. We'd love to hear from you.",
    "wa_core_feedback_thanks": "Thank you for your feedback! We appreciate it.",
    "wa_workflow_label_service": "Service: {value}",
    "wa_workflow_label_name": "Name: {value}",
    "wa_workflow_label_date": "Date: {value}",
    "wa_workflow_label_time": "Time: {value}",
    "wa_workflow_label_professional": "Professional: {value}",
    "wa_salon_auto_assign_option": "No, auto-assign best available",
    "wa_salon_date_option_other": "Other date (Reply with {date_format})",
    "wa_workflow_menu_item_label": "Workflow: {name}",
}

CATEGORY_ORDER: List[str] = [
    "whatsapp_wa",
    "whatsapp_general",
    "booking_workflow",
    "followups",
    "application_other",
]
CATEGORY_TITLES: Dict[str, str] = {
    "whatsapp_wa": "WhatsApp — wa_* (workflow, salon, core strings)",
    "whatsapp_general": "WhatsApp — whatsapp_* (generic)",
    "booking_workflow": "Booking & workflow",
    "followups": "Follow-ups",
    "application_other": "Application & other",
}


def message_category_id(key: str) -> str:
    """Group keys for admin UI (prefix-based)."""
    k = (key or "").lower()
    if k.startswith("wa_"):
        return "whatsapp_wa"
    if k.startswith("whatsapp_"):
        return "whatsapp_general"
    if k.startswith("followup_"):
        return "followups"
    if k.startswith("booking_") or k.startswith("reschedule_") or k in (
            "goodbye", "welcome", "workflow_complete",
    ):
        return "booking_workflow"
    return "application_other"


def build_category_sections(keys: List[str]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[str]] = defaultdict(list)
    for key in keys:
        buckets[message_category_id(key)].append(key)
    for cid in buckets:
        buckets[cid].sort()
    out: List[Dict[str, Any]] = []
    seen = set()
    for cid in CATEGORY_ORDER:
        ks = buckets.get(cid) or []
        if ks:
            out.append({"id": cid, "title": CATEGORY_TITLES.get(cid, cid), "keys": ks})
            seen.add(cid)
    for cid, ks in sorted(buckets.items()):
        if cid not in seen and ks:
            out.append({"id": cid, "title": CATEGORY_TITLES.get(cid, cid), "keys": ks})
    return out


def _key_to_label(key: str) -> str:
    s = key
    if s.startswith("wa_"):
        s = s[3:]
    elif s.startswith("whatsapp_"):
        s = s[9:]
    return s.replace("_", " ").strip().title() or key


def _build_labels_for_templates(templates: Dict[str, str]) -> Dict[str, str]:
    return {k: _key_to_label(k) for k in templates}


def _migrate_from_legacy_if_empty() -> bool:
    """If default_message has no platform doc, copy from legacy whatsapp_messages. Returns True if copied."""
    col = default_message_collection()
    if col.find_one({"_id": PLATFORM_DOC_ID}):
        return False
    legacy = get_db().get_collection(LEGACY_COLLECTION).find_one({"_id": PLATFORM_DOC_ID})
    if not legacy:
        return False
    audit = audit_fields_for_create("migration")
    doc = {
        "_id": PLATFORM_DOC_ID,
        "templates": dict(legacy.get("templates") or {}),
        "labels": dict(legacy.get("labels") or {}),
        **audit,
    }
    col.insert_one(doc)
    cache_delete_default_message_bundle()
    return True


def ensure_default_messages_synced(user_id: Optional[str] = None) -> bool:
    """
    Migrate legacy collection if needed, then ensure platform doc exists and seed missing keys.
    Returns True if this call wrote to MongoDB.
    """
    if _migrate_from_legacy_if_empty():
        user_id = user_id or "system"

    col = default_message_collection()
    doc = col.find_one({"_id": PLATFORM_DOC_ID})
    labels_seed = _build_labels_for_templates(MESSAGE_SEED_TEMPLATES)

    if not doc:
        audit = audit_fields_for_create(user_id or "system")
        col.insert_one(
            {
                "_id": PLATFORM_DOC_ID,
                "templates": dict(MESSAGE_SEED_TEMPLATES),
                "labels": labels_seed,
                **audit,
            }
        )
        cache_delete_default_message_bundle()
        return True

    t = dict(doc.get("templates") or {})
    lbl = dict(doc.get("labels") or {})
    changed = False
    for k, v in MESSAGE_SEED_TEMPLATES.items():
        if k not in t:
            t[k] = v
            changed = True
        if k not in lbl:
            lbl[k] = labels_seed.get(k, _key_to_label(k))
            changed = True

    if changed:
        audit = audit_fields_for_update(user_id or "system")
        col.update_one(
            {"_id": PLATFORM_DOC_ID},
            {"$set": {"templates": t, "labels": lbl, **audit}},
        )
        cache_delete_default_message_bundle()
        return True
    return False


def _load_platform_doc() -> Optional[Dict[str, Any]]:
    return default_message_collection().find_one({"_id": PLATFORM_DOC_ID})


def get_default_message_bundle() -> Dict[str, Any]:
    """
    Full platform doc: templates + labels (from ``default_message`` only).
    Cached under Redis key ``default_message_bundle`` when Redis is enabled.
    """
    cached = cache_get_default_message_bundle()
    if isinstance(cached, dict) and "templates" in cached:
        return cached

    ensure_default_messages_synced()
    doc = _load_platform_doc() or {}
    db_t = doc.get("templates") or {}
    if not isinstance(db_t, dict):
        db_t = {}
    templates = {k: str(v) for k, v in db_t.items()}
    labels_in = doc.get("labels") or {}
    if not isinstance(labels_in, dict):
        labels_in = {}
    labels: Dict[str, str] = {}
    for k in templates:
        labels[k] = str(labels_in[k]) if k in labels_in else _key_to_label(k)

    bundle = {"templates": templates, "labels": labels}
    cache_set_default_message_bundle(bundle, ttl_seconds=_DEFAULT_MESSAGE_CACHE_TTL)
    return bundle


def get_default_template(key: str) -> str:
    """Generic accessor: one template body from the default_message collection."""
    return str(get_default_message_bundle().get("templates", {}).get(key, "") or "")


def get_default_templates_merged() -> Dict[str, str]:
    """All default template bodies (copy for merge with tenant overrides)."""
    return dict(get_default_message_bundle()["templates"])


def get_default_labels() -> Dict[str, str]:
    return dict(get_default_message_bundle()["labels"])


def list_all_default_message_keys() -> List[str]:
    return sorted(get_default_templates_merged().keys())


def upsert_default_messages(
        templates_patch: Dict[str, str],
        labels_patch: Optional[Dict[str, str]] = None,
        user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Super-admin: update platform defaults in ``default_message``.
    Invalidates cache and tenant settings callers should refresh merges.
    """
    col = default_message_collection()
    ensure_default_messages_synced(user_id=user_id)
    doc = _load_platform_doc() or {}
    cur_t = dict(doc.get("templates") or {})
    cur_l = dict(doc.get("labels") or {})
    cur_t.update({k: str(v) for k, v in (templates_patch or {}).items()})
    if labels_patch:
        cur_l.update({k: str(v) for k, v in labels_patch.items()})
    audit = audit_fields_for_update(user_id or "system")
    col.update_one(
        {"_id": PLATFORM_DOC_ID},
        {"$set": {"templates": cur_t, "labels": cur_l, **audit}},
        upsert=True,
    )
    cache_delete_default_message_bundle()
    cache_invalidate_all_tenant_settings()
    return get_default_message_bundle()
