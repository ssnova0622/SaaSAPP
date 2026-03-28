"""
Pro-tier AI handlers: Store, Core (FAQ). Used when Pro AI is confident.

Handlers return a reply string. No session/menu dependency; when data is not
trained or not found, return a friendly fallback so flow can continue as Basic/Enterprise.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.services.whatsapp.helpers import constants as WMSG

logger = logging.getLogger(__name__)


def _get_tenant_service():
    from app.core.container import get_tenant_service
    return get_tenant_service()


def _get_storage():
    from app.services.storage_mongo import Storage
    return Storage


def _get_predictor():
    try:
        from app.services.ai import AIPredictor
        return AIPredictor()
    except Exception:
        return None


# Action IDs that this module handles (Store/Core Pro-only). Salon/book/cancel/reschedule stay in routes _run_action.
PRO_HANDLED_ACTIONS = frozenset({
    "store.product_recommendation",
    "core.refund_policy",
    "core.delivery_eta",
    "core.faq",
})


async def handle_product_recommendation(tenant: str, params: Dict[str, Any]) -> str:
    """AI product recommendation: 'show cheap running shoes', 'I need a birthday cake'."""
    user_input = str((params or {}).get("input") or "").strip()
    if not user_input:
        return WMSG.MSG_PRO_PRODUCT_PROMPT
    predictor = _get_predictor()
    items: list = []
    if predictor:
        try:
            items = predictor.search_catalog(tenant, user_input)
        except Exception as e:
            logger.warning("product_recommendation search_catalog failed: %s", e)
    if not items:
        try:
            storage = _get_storage()
            res = storage.list_products(tenant, search=user_input, active=True, page=1, size=5)
            items = res.get("items") or []
        except Exception:
            pass
    if not items:
        return WMSG.MSG_PRO_NO_CATALOG_MATCH.format(query=user_input)
    lines = [WMSG.MSG_PRO_OPTIONS_HEADER]
    for i, it in enumerate(items[:5], start=1):
        name = it.get("name", WMSG.LABEL_ITEM)
        price = it.get("price", 0)
        unit = it.get("unit", "")
        lines.append(f"{i}) {name} - ₹{price}{' per ' + unit if unit else ''}")
    return "\n".join(lines)


async def handle_refund_policy(tenant: str, params: Dict[str, Any]) -> str:
    """FAQ: refund / return policy. From tenant faq.refund_policy or default."""
    settings = _get_tenant_service().get_tenant_settings(tenant) or {}
    faq = settings.get("faq") or {}
    text = faq.get("refund_policy") or faq.get("return_policy")
    if text:
        return str(text).strip()
    return WMSG.MSG_PRO_REFUND_DEFAULT


async def handle_delivery_eta(tenant: str, params: Dict[str, Any]) -> str:
    """FAQ: when to expect order / delivery time. From tenant faq.delivery_eta or delivery_config."""
    settings = _get_tenant_service().get_tenant_settings(tenant) or {}
    faq = settings.get("faq") or {}
    text = faq.get("delivery_eta") or faq.get("delivery_time")
    if text:
        return str(text).strip()
    delivery = settings.get("delivery_config") or {}
    if isinstance(delivery, dict) and delivery.get("estimated_days"):
        return f"Orders typically ship within {delivery.get('estimated_days', 3)} business days. Type *track* with your order number for status."
    return "Orders typically ship within 2-3 business days. Type your order number or *track* for status. Type *menu* for more options."


async def handle_faq(tenant: str, params: Dict[str, Any]) -> str:
    """Generic FAQ: hours, contact, policy. From tenant faq.* or default."""
    settings = _get_tenant_service().get_tenant_settings(tenant) or {}
    faq = settings.get("faq") or {}
    user_input = str((params or {}).get("input") or "").lower()
    # Map keywords to faq keys
    if "hour" in user_input or "open" in user_input or "close" in user_input:
        text = faq.get("hours") or faq.get("opening_hours")
        if text:
            return str(text).strip()
        return WMSG.MSG_PRO_BUSINESS_HOURS
    if "contact" in user_input or "phone" in user_input or "address" in user_input:
        text = faq.get("contact") or faq.get("address")
        if text:
            return str(text).strip()
        owner = settings.get("owner_phone") or settings.get("owner_email") or ""
        if owner:
            return WMSG.MSG_PRO_CONTACT_OWNER.format(owner=owner)
        return WMSG.MSG_PRO_CONTACT_SUPPORT
    if "policy" in user_input or "refund" in user_input:
        return await handle_refund_policy(tenant, params)
    # Default
    text = faq.get("general") or faq.get("help")
    if text:
        return str(text).strip()
    return WMSG.MSG_PRO_HELP_GENERIC


async def run_pro_action(tenant: str, phone: str, action_id: str, params: Dict[str, Any]) -> Optional[str]:
    """Dispatch to the correct Pro handler. Returns reply or None if not handled."""
    aid = (action_id or "").strip().lower()
    if aid not in PRO_HANDLED_ACTIONS:
        return None
    if aid == "store.product_recommendation":
        return await handle_product_recommendation(tenant, params)
    if aid == "core.refund_policy":
        return await handle_refund_policy(tenant, params)
    if aid == "core.delivery_eta":
        return await handle_delivery_eta(tenant, params)
    if aid == "core.faq":
        return await handle_faq(tenant, params)
    return None
