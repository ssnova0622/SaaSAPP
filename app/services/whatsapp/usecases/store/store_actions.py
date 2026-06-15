from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.helpers.constants_action import (BROWSE_CATALOG, CHECK_PRICE, CHECK_PRODUCT, TRACK_ORDER,
                                          VIEW_PRODUCTS, VIEW_OFFERS)
from app.models.workflow import WorkflowStep
from app.services.core.messaging_service import Messaging
from app.services.whatsapp.action_support import get_action_logger, run_handler_and_await
from app.services.whatsapp.usecases.core.core_actions import CoreActions
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow.workflow_step_policy import (
    normalize_workflow_action_code,
    workflow_user_reply_flow_key,
    workflow_user_reply_pending_key,
)
from app.services.whatsapp.helpers import constants as WMSG

logger = get_action_logger("usecases.store")

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore


class StoreActions(CoreActions):
    """
    Store workflow steps: catalog, product/price search, order tracking, offers.

    Uses :class:`CoreActions` for ``flow_data`` and the same pending-reply keys as other modules.
    """

    @staticmethod
    def _mark_skip_input_wait(ctx: Dict[str, Any]) -> None:
        ctx["_wa_skip_input_wait_once"] = True

    @staticmethod
    async def text_product_search(tenant: str, query: str, *, mode: str, phone: str = "") -> str:
        q = (query or "").strip()
        if not q:
            return WMSG.MSG_STORE_PRODUCT_QUERY
        try:
            from app.services.store.facade import get_store_facade

            data = get_store_facade().products.list_products(tenant=tenant, search=q, active=True, page=1, size=10)
            items = data.get("items") or []
            if items:
                lines = [WMSG.MSG_STORE_FOUND_COUNT.format(n=len(items))]
                for i, p in enumerate(items, 1):
                    name = p.get("name") or p.get("sku") or WMSG.LABEL_ITEM
                    price = p.get("price")
                    price_str = f" - ₹{price}" if price is not None else ""
                    lines.append(f"{i}) {name}{price_str}")
                return "\n".join(lines)
        except Exception:
            logger.debug("product search failed", exc_info=True)
        if mode == "price" and AIPredictor and CoreActions._is_ai_enabled(tenant):
            ai = AIPredictor()
            ai_items = ai.search_catalog(tenant, q)
            if ai_items:
                lines = [WMSG.MSG_STORE_PRICES_HEADER]
                for it in ai_items:
                    price = it.get("price")
                    unit = it.get("unit")
                    lines.append(f"- {it.get('name')}: ₹{price}{' per ' + unit if unit else ''}")
                    conversions = it.get("unit_conversions") or []
                    for conv in conversions:
                        c_unit = conv.get("unit")
                        c_factor = float(conv.get("factor") or 1.0)
                        c_price = float(price or 0.0) * c_factor
                        lines.append(f"  • {c_unit}: ₹{c_price:.2f}")
                return "\n".join(lines)
            return WMSG.MSG_STORE_PRODUCT_NOT_IN_CATALOG
        return WMSG.MSG_NO_PRODUCTS_FOR_QUERY.format(query=q)

    @staticmethod
    async def text_track_order(tenant: str, order_id: str) -> str:
        oid = (order_id or "").strip() or WMSG.ORDER_ID_PLACEHOLDER
        if not oid or oid == WMSG.ORDER_ID_PLACEHOLDER:
            return WMSG.MSG_PLEASE_SHARE_ORDER_ID
        if oid.upper().startswith("ORD-"):
            oid = oid.upper()
        try:
            from app.services.store.facade import get_store_facade

            order = get_store_facade().orders.get_order(tenant=tenant, order_id=oid)
            if order:
                status = str(order.get("status") or WMSG.ORDER_STATUS_FALLBACK_PLACED).replace("_", " ").title()
                lines = [
                    WMSG.MSG_STORE_ORDER_HEADER.format(oid=oid),
                    WMSG.MSG_STORE_ORDER_STATUS_LINE.format(status=status),
                ]
                if order.get("totals", {}).get("grand_total") is not None:
                    lines.append(
                        WMSG.MSG_STORE_ORDER_TOTAL_LINE.format(
                            amount=f"{order['totals'].get('grand_total', 0):,.2f}",
                        )
                    )
                return "\n".join(lines)
        except Exception:
            logger.debug("track_order failed", exc_info=True)
        return WMSG.MSG_STORE_ORDER_NOT_FOUND.format(oid=oid)

    @staticmethod
    async def text_view_products(tenant: str) -> str:
        base_url = (os.environ.get("FRONTEND_BASE_URL") or os.environ.get("VITE_APP_URL") or "").strip().rstrip("/")
        if not base_url:
            base_url = os.environ.get("PUBLIC_APP_URL", WMSG.ENV_DEFAULT_PUBLIC_APP_URL)
        catalog_url = f"{base_url}/ss-business/{tenant}/catalog".strip()
        link_intro = WMSG.MSG_STORE_CATALOG_LINK_INTRO
        try:
            from app.services.store.facade import get_store_facade
            from app.services.store.reports_service import ReportsService

            facade = get_store_facade()
            items: List[Dict[str, Any]] = []
            try:
                top = ReportsService.top_sellers(tenant, days=30, top=10)
                for row in top:
                    sku = row.get("sku")
                    if sku:
                        p = facade.products.get_product_by_sku(tenant, sku)
                        if p and (p.get("active") is not False):
                            items.append({"name": p.get("name") or sku, "sku": sku, "price": p.get("price")})
            except Exception:
                pass
            if not items:
                data = facade.products.list_products(tenant=tenant, active=True, page=1, size=10)
                items = data.get("items") or []
            lines = [link_intro, "", catalog_url, ""]
            if items:
                lines.append(WMSG.MSG_STORE_MOST_POPULAR_HEADER)
                for i, p in enumerate(items[:10], 1):
                    name = p.get("name") or p.get("sku") or WMSG.LABEL_ITEM
                    price = p.get("price")
                    price_str = f" - ₹{price}" if price is not None else ""
                    lines.append(f"{i}) {name}{price_str}")
            return "\n".join(lines)
        except Exception:
            logger.debug("view_products failed", exc_info=True)
        return f"{link_intro}\n\n{catalog_url}"

    # RUN ACTIONS STARTS HERE

    @staticmethod
    async def _run_browse_catalog(tenant: str) -> str:
        try:
            from app.services.store.facade import get_store_facade

            data = get_store_facade().products.list_products(tenant=tenant, active=True, page=1, size=15)
            items = data.get("items") or []
            if items:
                lines = [WMSG.MSG_STORE_BROWSE_HEADER]
                for i, p in enumerate(items, 1):
                    name = p.get("name") or p.get("sku") or WMSG.LABEL_ITEM
                    price = p.get("price")
                    price_str = f" - ₹{price}" if price is not None else ""
                    lines.append(f"{i}) {name}{price_str}")
                return "\n".join(lines)
        except Exception:
            logger.debug("browse_catalog failed", exc_info=True)
        return WMSG.MSG_NO_PRODUCTS

    @staticmethod
    async def _run_check_product(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        ctx, flow = CoreActions._ctx_and_flow(session)
        pend = workflow_user_reply_pending_key(step.action_code)
        persist = workflow_user_reply_flow_key(step.action_code)
        raw = flow.get(pend)
        if raw is not None:
            q = str(raw).strip()
            if not q:
                return wa(tenant, "wa_invalid_input_retry")
            text = await StoreActions.text_product_search(tenant, q, mode="product", phone=phone or "")
            flow[persist] = q
            flow.pop(pend, None)
            flow.pop("store_query", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        q = (flow.get("store_query") or "").strip()
        if q:
            text = await StoreActions.text_product_search(tenant, q, mode="product", phone=phone or "")
            flow.pop("store_query", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        return (step.label or "").strip() or WMSG.MSG_STORE_PRODUCT_QUERY

    @staticmethod
    async def _run_check_price(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        ctx, flow = CoreActions._ctx_and_flow(session)
        pend = workflow_user_reply_pending_key(step.action_code)
        persist = workflow_user_reply_flow_key(step.action_code)
        raw = flow.get(pend)
        if raw is not None:
            q = str(raw).strip()
            if not q:
                return wa(tenant, "wa_invalid_input_retry")
            text = await StoreActions.text_product_search(tenant, q, mode="price", phone=phone or "")
            flow[persist] = q
            flow.pop(pend, None)
            flow.pop("store_query", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        q = (flow.get("store_query") or "").strip()
        if q:
            text = await StoreActions.text_product_search(tenant, q, mode="price", phone=phone or "")
            flow.pop("store_query", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        return (step.label or "").strip() or WMSG.MSG_STORE_WHICH_PRODUCT_PRICE

    @staticmethod
    async def _run_view_offers(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        from app.services.store.facade import get_store_facade

        facade = get_store_facade()
        offers = facade.offers.list_active_offers(tenant)
        if offers:

            def _apply_offer_discount(price: float, discount_info: dict) -> float:
                if not discount_info:
                    return price
                t = (discount_info or {}).get("type")
                v = float((discount_info or {}).get("value") or 0)
                if t == "percent":
                    return max(0.0, price - (price * v / 100))
                if t == "amount":
                    return max(0.0, price - v)
                return price

            lines = [WMSG.MSG_STORE_OFFERS_SECTION_HEADER, ""]
            for o in offers:
                title = o.get("title") or WMSG.LABEL_OFFER
                desc = (o.get("description") or "").strip()
                skus = o.get("product_skus") or []
                discount_info = o.get("discount_info") or {}
                lines.append(f"*{title}*")
                if desc:
                    lines.append(desc)
                    lines.append("")
                if skus:
                    for sku in skus:
                        prod = facade.products.get_product_by_sku(tenant, sku)
                        if prod:
                            name = prod.get("name") or prod.get("sku") or sku
                            was_price = float(prod.get("mrp") or 0)
                            now_price = _apply_offer_discount(was_price, discount_info)
                            if was_price > 0 and now_price < was_price:
                                lines.append(f"• {name}: Was ₹{was_price:,.0f}, Now ₹{now_price:,.0f}")
                            elif was_price > 0:
                                lines.append(f"• {name}: ₹{now_price:,.0f}")
                            else:
                                lines.append(f"• {name}")
                        else:
                            lines.append(f"• {sku}")
                    lines.append("")
                else:
                    if not desc:
                        lines.append("")
                    lines.append("")
            text = "\n".join(lines).strip()
            if phone:
                for o in offers:
                    brochure_url = (o.get("brochure_url") or "").strip()
                    if brochure_url:
                        try:
                            Messaging.send_whatsapp_document(
                                phone, brochure_url, caption=o.get("title") or WMSG.MSG_STORE_OFFER_BROCHURE_CAPTION, tenant=tenant
                            )
                        except Exception as e:
                            logger.warning("Failed to send offer brochure: %s", e)
            return text
        items = []
        if AIPredictor and CoreActions._is_ai_enabled(tenant):
            ai = AIPredictor()
            items = ai.search_catalog(tenant, "offer")
        if items:
            lines = [WMSG.MSG_STORE_OFFERS_AI_FALLBACK_HEADER]
            for it in items:
                lines.append(f"- {it.get('name')}: {it.get('price')}")
            return "\n".join(lines)
        return WMSG.MSG_NO_ACTIVE_OFFERS

    @staticmethod
    async def _run_track_order(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        ctx, flow = CoreActions._ctx_and_flow(session)
        pend = workflow_user_reply_pending_key(step.action_code)
        persist = workflow_user_reply_flow_key(step.action_code)
        raw = flow.get(pend)
        if raw is not None:
            t = str(raw).strip()
            if not t:
                return wa(tenant, "wa_invalid_input_retry")
            oid = t.upper() if t.upper().startswith("ORD-") else t
            text = await StoreActions.text_track_order(tenant, oid)
            flow[persist] = oid
            flow.pop(pend, None)
            flow.pop("store_order_id", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        oid = (flow.get("store_order_id") or "").strip()
        if oid:
            text = await StoreActions.text_track_order(tenant, oid)
            flow.pop("store_order_id", None)
            StoreActions._mark_skip_input_wait(ctx)
            return text
        return (step.label or "").strip() or WMSG.MSG_PLEASE_SHARE_ORDER_ID

    @staticmethod
    async def _run_view_products(tenant: str, phone: str, session: Dict[str, Any], step: WorkflowStep) -> Optional[str]:
        return await StoreActions.text_view_products(tenant)

    # RUN ACTIONS ENDS HERE

    @staticmethod
    async def try_run(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
    ) -> Tuple[bool, Optional[str]]:
        """Handle store workflow codes; return ``(False, None)`` if unknown to this module."""
        code = normalize_workflow_action_code(action_code)
        handler = _STORE_RUN_HANDLERS.get(code)
        if not handler:
            return False, None
        return True, await run_handler_and_await(
            handler, tenant=tenant, phone=phone, session=session, step=step
        )

    @staticmethod
    def try_input(
            action_code: str,
            tenant: str,
            phone: str,
            session: Dict[str, Any],
            step: WorkflowStep,
            user_input: str,
    ) -> Tuple[bool, bool, Optional[str]]:
        # Store text steps use run-only + flow_data (pending keys) via WorkflowEngine.
        return False, True, None


# Handler maps (after class; use .lower() keys)
_STORE_RUN_HANDLERS: Dict[str, Callable[..., Any]] = {
    CHECK_PRODUCT: StoreActions._run_check_product,
    CHECK_PRICE: StoreActions._run_check_price,
    TRACK_ORDER: StoreActions._run_track_order,
    VIEW_PRODUCTS: StoreActions._run_view_products,
    VIEW_OFFERS: StoreActions._run_view_offers,
    BROWSE_CATALOG: StoreActions._run_browse_catalog,

}


async def try_store_run(
        action_code: str,
        tenant: str,
        phone: str,
        session: Dict[str, Any],
        step: WorkflowStep,
) -> Tuple[bool, Optional[str]]:
    """Registered in :mod:`app.services.whatsapp.action_executor` (after salon, before ai)."""
    return await StoreActions.try_run(action_code, tenant, phone, session, step)


def _register_store_handlers() -> None:
    from app.services.whatsapp.action_handler_registry import register_many
    from app.services.whatsapp.workflow.workflow_step_policy import WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT
    register_many(
        _STORE_RUN_HANDLERS,
        needs_input_codes=WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT,
        keeps_session_codes=frozenset(),
    )


_register_store_handlers()
