"""
Inbound WhatsApp message pipeline.

Stages run in order; first non-None result wins. Keeps orchestration separate from
menu tree, FSM, workflows, and action execution.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from app.core.container import get_tenant_service, get_whatsapp_service
from app.services.whatsapp.action_support import get_action_logger
from app.services.whatsapp.wa_templates import wa
from app.services.whatsapp.workflow.workflow_engine import WorkflowEngine
from app.services.whatsapp.session_flow_service import (
    get_session,
    save_session,
    reset_session_to_root,
    get_waiting_action_payload,
    is_waiting_for_any_input,
)
from app.services.whatsapp.menu_tree_service import (
    find_node,
    send_submenu_reply,
    resolve_active_menu_id,
    extract_choice_key,
)
from app.services.whatsapp.trigger_service import evaluate_triggers, execute_trigger_action
from app.services.whatsapp.usecases.salon.booking_flow import start_timeslot_flow, handle_timeslot_fsm
from app.services.whatsapp.action_executor_service import run_action as run_dispatcher_action
from app.services.whatsapp.helpers.constants import WORKFLOW_END_MAIN_MENU
from app.services.whatsapp.workflow_message_helper import (
    WORKFLOW_COMPLETE_SENTINEL,
    workflow_reply_or_welcome,
    workflow_has_custom_end_message,
)

BOOKING_ACTION_IDS = frozenset(
    {
        "salon.select_timeslot",
        "select_timeslot",
        "book_appointment",
        "clinic.book_doctor",
        "salon.cancel_appointment",
        "salon.reschedule_appointment",
        "salon.show_services",
    }
)


def normalize_booking_nl_action_id(action_id: str) -> str:
    """Strip ``salon.`` / ``clinic.`` so NL/menu aliases align with ``app.helpers.constants_action`` ids."""
    aid = (action_id or "").strip().lower()
    for prefix in ("salon.", "clinic."):
        if aid.startswith(prefix):
            return aid[len(prefix) :]
    return aid


def _log_inbound_resolution(stage: str, tenant: str, phone: str, payload: Dict[str, Any]) -> None:
    """Structured INFO log for support dashboards (grep ``whatsapp_inbound_resolved``)."""
    tail = (phone or "")[-4:] if phone else ""
    _log.info(
        "whatsapp_inbound_resolved stage=%s tenant=%s phone_tail=%s node=%s",
        stage,
        tenant,
        tail,
        payload.get("node"),
    )

try:
    from app.services.ai import AIPredictor  # type: ignore
except Exception:
    AIPredictor = None  # type: ignore

try:
    from app.services.whatsapp import pro_handlers  # type: ignore
except Exception:
    pro_handlers = None  # type: ignore

_log = get_action_logger("pipeline.inbound")


def _tier(tenant: str):
    from app.services.whatsapp.tier_services import get_tier_service

    return get_tier_service(tenant)


def _use_nl(tenant: str) -> bool:
    return _tier(tenant).should_use_nl_intents()


def _nl_fallback(tenant: str) -> str:
    return _tier(tenant).get_fallback_message()


async def _run_action(
        tenant: str, action_id: str, params: Optional[Dict[str, Any]], locale: str
) -> str:
    return await run_dispatcher_action(
        tenant, action_id, params
    )


def _load_menu(tenant: str, menu_id: Optional[str]) -> Tuple[str, Optional[dict], dict]:
    mid = menu_id or resolve_active_menu_id(tenant) or "welcome_message"
    mdoc = get_whatsapp_service().get_whatsapp_menu(tenant, mid, status="published")
    if not mdoc and mid == "welcome_message":
        menus = get_whatsapp_service().list_whatsapp_menus(tenant)
        published = [m for m in menus if m.get("status") == "published"]
        if published:
            published.sort(key=lambda m: int(m.get("version") or 0), reverse=True)
            mdoc = published[0]
            if mdoc:
                mid = mdoc.get("menu_id") or mid
    tree = (mdoc or {}).get("tree", {}) or {}
    return mid, mdoc, tree if isinstance(tree, dict) else {}


def _menu_reply(tenant: str, phone: str, root_node: Any, locale: str) -> str:
    if root_node:
        return send_submenu_reply(tenant, phone, root_node, locale)
    return wa(tenant, "wa_please_choose_option")


async def handle_incoming(
        tenant: str,
        phone: str,
        user_input: str,
        locale: str = "en",
        menu_id: Optional[str] = None,
        client_node: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run inbound stages in order; first stage that returns a dict wins.

    Logs at DEBUG; uncaught exceptions in a stage are logged and mapped to a safe user reply.
    """
    user_input = (user_input or "").strip()
    phone_tail = (phone or "")[-4:] if phone else ""
    _log.debug(
        "handle_incoming tenant=%s phone_tail=%s input_len=%s locale=%s",
        tenant,
        phone_tail,
        len(user_input),
        locale,
    )
    _mid, mdoc, tree = _load_menu(tenant, menu_id)
    root_id = tree.get("root")

    ctx: Dict[str, Any] = {
        "tenant": tenant,
        "phone": phone,
        "user_input": user_input,
        "locale": locale,
        "client_node": client_node,
        "mdoc": mdoc,
        "tree": tree,
        "root_id": root_id,
        "fsm_reply": None,
    }

    for stage in INBOUND_PIPELINE_STAGES:
        name = getattr(stage, "__name__", str(stage))
        try:
            out = await stage(ctx)
        except Exception:
            _log.exception("Inbound pipeline stage failed: %s tenant=%s", name, tenant)
            return {"reply": wa(tenant, "wa_inbound_pipeline_error"), "node": "error"}
        if out is not None:
            _log.debug("handle_incoming resolved by %s", name)
            _log_inbound_resolution(name, ctx["tenant"], ctx["phone"], out)
            return out

    fallback_out: Dict[str, Any] = {
        "reply": _nl_fallback(tenant),
        "node": ctx.get("current_id") or root_id or "root",
    }
    _log_inbound_resolution("_tier_nl_fallback", ctx["tenant"], ctx["phone"], fallback_out)
    return fallback_out


async def _stage_triggers(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Match tenant keyword triggers and run the configured action."""
    t, loc, ui = ctx["tenant"], ctx["locale"], ctx["user_input"]
    trig = evaluate_triggers(t, ui, loc)
    if not trig:
        return None
    res = await execute_trigger_action(
        t, trig, loc, phone=ctx["phone"], run_action=_run_action
    )
    return {"reply": res.get("reply") or "", "node": res.get("node") or "root"}


async def _stage_flow_ended_menu(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """After a flow sets flow_ended, reset session and show the root menu."""
    tenant, phone, tree, root_id, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["locale"],
    )
    session = get_session(tenant, phone)
    if not (session.get("ctx") or {}).get("flow_ended") or not tree or not root_id:
        return None
    reset_session_to_root(tenant, phone, tree)
    root_node = find_node(tree, root_id)
    return {"reply": _menu_reply(tenant, phone, root_node, loc), "node": root_id}


async def _stage_store_waiting_input(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """If session is waiting for store/free-text input, run the action and return to root menu."""
    tenant, phone, tree, root_id, ui, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
    )
    session = get_session(tenant, phone)
    _wk, action_id, param_key = get_waiting_action_payload(session)
    if not action_id:
        return None
    params = {"phone": phone, "input": ui, param_key: ui}
    reply = await _run_action(tenant, action_id, params, loc)
    c = dict(session.get("ctx") or {})
    c.pop("waiting_for_store_input", None)
    c.pop("waiting_for_action_input", None)
    save_session(tenant, phone, {"ctx": c})
    reset_session_to_root(tenant, phone, tree)
    root_node = find_node(tree, root_id) if tree else None
    menu_reply = _menu_reply(tenant, phone, root_node, loc)
    reply = f"{reply}\n\n{menu_reply}" if (reply and reply.strip()) else menu_reply
    return {"reply": reply, "node": root_id if tree else "root"}


async def _stage_rebook_feedback(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle loose keywords: rebook starts FSM; review/feedback sends thanks link."""
    tenant, phone, tree, root_id, ui = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
    )
    low = (ui or "").lower()
    if not any(k in low for k in ("rebook", "review", "feedback")):
        return None
    if "rebook" in low:
        reply = await start_timeslot_flow(tenant, phone, entities={})
        return {"reply": reply, "node": "fsm"}
    link = wa(tenant, "wa_feedback_thanks", review_link="[Review Link]").split(": ", 1)
    review = link[-1] if len(link) > 1 else "[Review Link]"
    return {
        "reply": wa(tenant, "wa_feedback_thanks", review_link=review),
        "node": root_id if tree else "root",
    }


async def _stage_exact_action_id(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """If user text equals a registered workflow/menu action id, run it directly."""
    tenant, phone, tree, root_id, ui, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
    )
    ids = [a.get("id") for a in WorkflowEngine.list_whatsapp_menu_items(tenant) if a.get("id")]
    if ui not in ids:
        return None
    entities: Dict[str, Any] = {}
    if AIPredictor and _use_nl(tenant):
        try:
            ai = AIPredictor()
            intent, _ = ai.detect_intent(ui, tenant=tenant)
            if intent:
                entities = ai.extract_entities(ui, intent) or {}
        except Exception:
            pass
    reply = await _run_action(
        tenant, ui, {**entities, "phone": phone, "input": ui}, loc
    )
    if str(ui).lower() not in BOOKING_ACTION_IDS:
        reset_session_to_root(tenant, phone, tree)
        return {"reply": reply, "node": root_id if tree else "root"}
    return {"reply": reply, "node": "fsm"}


async def _stage_run_fsm(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run booking FSM once; result is consumed by _stage_return_fsm."""
    ctx["fsm_reply"] = await handle_timeslot_fsm(
        ctx["tenant"], ctx["phone"], ctx["user_input"], ctx["tree"]
    )
    return None


async def _stage_active_workflow(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Advance an active workflow when session has workflow_id."""
    tenant, phone, tree, root_id, ui, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
    )
    # If the booking FSM produced a reply, it must win over workflow (e.g. after reschedule → timeslot flow).
    if ctx.get("fsm_reply") is not None:
        return None
    session = get_session(tenant, phone)
    if not (session.get("ctx") or {}).get("workflow_id"):
        return None
    wf_reply = await WorkflowEngine.execute_next_step(tenant, phone, session, user_input=ui)
    save_session(tenant, phone, session)
    if wf_reply and wf_reply.strip() == WORKFLOW_END_MAIN_MENU:
        reset_session_to_root(tenant, phone, tree)
        root_node = find_node(tree, root_id)
        return {"reply": _menu_reply(tenant, phone, root_node, loc), "node": root_id}
    if (
            wf_reply
            and wf_reply.strip() == WORKFLOW_COMPLETE_SENTINEL
            and not workflow_has_custom_end_message(tenant)
    ):
        reset_session_to_root(tenant, phone, tree)
        root_node = find_node(tree, root_id)
        return {"reply": _menu_reply(tenant, phone, root_node, loc), "node": root_id}
    return {"reply": workflow_reply_or_welcome(tenant, wf_reply), "node": "workflow"}


async def _stage_return_fsm(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return FSM reply if _stage_run_fsm produced one."""
    fr = ctx.get("fsm_reply")
    if fr is not None:
        return {"reply": fr, "node": "fsm"}
    return None


async def _stage_menu_inactive_goodbye(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """When menu is inactive and mode is wait_reminder, send goodbye / type-menu hint."""
    tenant, session = ctx["tenant"], get_session(ctx["tenant"], ctx["phone"])
    mode = str((session.get("ctx") or {}).get("mode") or "").lower()
    if mode != "wait_reminder":
        return None
    settings = get_tenant_service().get_tenant_settings(tenant) or {}
    tn = str(settings.get("business_name") or settings.get("tenant") or tenant)
    msg = wa(tenant, "goodbye", tenant_name=tn)
    if not msg.strip():
        msg = wa(tenant, "wa_type_menu_hint")
    return {"reply": msg, "node": "fsm"}


async def _stage_nl_intent_high_confidence(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """If NL is enabled and intent confidence is high, run the mapped action."""
    tenant, phone, tree, root_id, ui, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
    )
    if not (_use_nl(tenant) and AIPredictor):
        return None
    intent, score = None, 0.0
    entities: Dict[str, Any] = {}
    try:
        intent, score = AIPredictor().detect_intent(ui, tenant=tenant)
        if intent:
            entities = AIPredictor().extract_entities(ui, intent) or {}
    except Exception:
        pass
    if not (intent and score > 0.7):
        return None
    action_id = str(intent).strip().lower()
    params = {**entities, "entities": entities, "phone": phone, "input": ui}
    if pro_handlers and action_id in getattr(pro_handlers, "PRO_HANDLED_ACTIONS", []):
        reply = await pro_handlers.run_pro_action(tenant, phone, action_id, params)
    else:
        reply = await _run_action(tenant, action_id, params, loc)
    if str(action_id).lower() not in BOOKING_ACTION_IDS:
        reset_session_to_root(tenant, phone, tree)
        return {"reply": reply, "node": root_id if tree else "root"}
    return {"reply": reply, "node": "fsm"}


async def _stage_no_menu_error(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """No published menu document: tell user to publish a menu."""
    if ctx.get("mdoc"):
        return None
    return {
        "reply": wa(ctx["tenant"], "wa_no_menu_published"),
        "node": "error",
    }


async def _stage_menu_navigation(ctx: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Navigate submenu/options, run linked actions, or fall back to NL."""
    tenant, phone, tree, root_id, ui, loc, client_node = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
        ctx["client_node"],
    )
    session = get_session(tenant, phone)
    current_id = session.get("last_node") or client_node or root_id
    node = find_node(tree, current_id) or find_node(tree, root_id)
    if not node:
        return {"reply": wa(tenant, "wa_menu_error"), "node": "error"}

    if node.get("type") == "submenu" and not ui:
        reply = send_submenu_reply(tenant, phone, node, loc)
        save_session(tenant, phone, {"last_node": current_id})
        return {"reply": reply, "node": current_id}

    key = extract_choice_key(ui)
    match = next((o for o in (node.get("options") or []) if str(o.get("key")) == key), None)
    s_session = get_session(tenant, phone)
    fsm_mode = (s_session.get("ctx") or {}).get("mode")
    if fsm_mode and key and key.isdigit():
        return {
            "reply": wa(tenant, "wa_invalid_fsm_menu_digit"),
            "node": "fsm",
        }

    if not match:
        return await _stage_menu_no_match(ctx, node, current_id, key)

    next_id = match.get("next") or root_id
    if next_id and isinstance(next_id, str) and next_id.strip().lower().startswith("workflow."):
        action_id = next_id.strip()
        reply = await _run_action(tenant, action_id, {"phone": phone}, loc)
        session_after = get_session(tenant, phone)
        if is_waiting_for_any_input(session_after):
            return {"reply": reply, "node": root_id}
        keep_fsm = (
            "salon.select_timeslot",
            "select_timeslot",
            "book_appointment",
            "clinic.book_doctor",
            "salon.cancel_appointment",
            "salon.reschedule_appointment",
        )
        aid_l = action_id.lower()
        # Workflows carry their own closing text (e.g. END step); do not append root menu here
        # (same idea as ``is_wf`` below for actions on submenu nodes).
        if aid_l not in keep_fsm and not aid_l.startswith("workflow."):
            reset_session_to_root(tenant, phone, tree)
            root_node = find_node(tree, root_id)
            menu_reply = _menu_reply(tenant, phone, root_node, loc)
            reply = f"{reply}\n\n{menu_reply}" if reply else menu_reply
        elif aid_l.startswith("workflow."):
            reset_session_to_root(tenant, phone, tree)
        return {"reply": reply, "node": root_id}

    next_node = find_node(tree, next_id)
    if next_node and next_node.get("type") == "submenu":
        reply = send_submenu_reply(tenant, phone, next_node, loc)
        save_session(tenant, phone, {"last_node": next_id})
        return {"reply": reply, "node": next_id}
    if next_node:
        action_id = next_node.get("action") or next_node.get("action_id")
        reply = await _run_action(
            tenant, action_id, {**(next_node.get("params") or {}), "phone": phone}, loc
        )
        session_after = get_session(tenant, phone)
        if is_waiting_for_any_input(session_after):
            return {"reply": reply, "node": root_id}
        is_wf = str(action_id or "").strip().lower().startswith("workflow.")
        if str(action_id).lower() not in BOOKING_ACTION_IDS and not is_wf:
            reset_session_to_root(tenant, phone, tree)
            root_node = find_node(tree, root_id)
            menu_reply = _menu_reply(tenant, phone, root_node, loc)
            reply = f"{reply}\n\n{menu_reply}" if reply else menu_reply
        return {"reply": reply, "node": root_id}

    if not _use_nl(tenant):
        root_node = find_node(tree, root_id)
        return {
            "reply": _menu_reply(tenant, phone, root_node, loc),
            "node": root_id,
        }
    return {"reply": _nl_fallback(tenant), "node": current_id}


async def _stage_menu_no_match(
        ctx: Dict[str, Any], node: dict, current_id: str, key: str
) -> Dict[str, Any]:
    """No option key matched: try NL intent, else re-show submenu or NL fallback."""
    tenant, phone, tree, root_id, ui, loc = (
        ctx["tenant"],
        ctx["phone"],
        ctx["tree"],
        ctx["root_id"],
        ctx["user_input"],
        ctx["locale"],
    )
    intent, score = None, 0.0
    entities: Dict[str, Any] = {}
    if _use_nl(tenant) and AIPredictor:
        try:
            intent, score = AIPredictor().detect_intent(ui, tenant=tenant)
            if intent:
                entities = AIPredictor().extract_entities(ui, intent) or {}
        except Exception:
            pass
    if intent and score > 0.5:
        action_id = str(intent).strip().lower()
        params = {**entities, "entities": entities, "phone": phone, "input": ui}
        if pro_handlers and action_id in getattr(pro_handlers, "PRO_HANDLED_ACTIONS", []):
            reply = await pro_handlers.run_pro_action(tenant, phone, action_id, params)
        else:
            reply = await _run_action(tenant, action_id, params, loc)
        return {"reply": reply, "node": root_id if tree else "root"}
    if not _use_nl(tenant):
        target = node if (node and node.get("type") == "submenu") else find_node(tree, root_id)
        reply = send_submenu_reply(tenant, phone, target, loc) if target else wa(tenant, "wa_please_choose_option")
        return {"reply": reply, "node": current_id}
    return {"reply": _nl_fallback(tenant), "node": current_id}


# Ordered stages for ``handle_incoming`` (first non-None wins). Exposed for tests and docs.
INBOUND_PIPELINE_STAGES: Tuple[Callable[..., Any], ...] = (
    _stage_triggers,
    _stage_flow_ended_menu,
    _stage_store_waiting_input,
    _stage_rebook_feedback,
    _stage_exact_action_id,
    _stage_run_fsm,
    _stage_active_workflow,
    _stage_return_fsm,
    _stage_menu_inactive_goodbye,
    _stage_nl_intent_high_confidence,
    _stage_no_menu_error,
    _stage_menu_navigation,
)
