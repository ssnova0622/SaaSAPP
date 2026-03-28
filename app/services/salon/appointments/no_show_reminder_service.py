# app/services/salon/appointments/no_show_reminder_service.py
"""Cron-callable: for each tenant with AI + no_show, get risk scores and send WhatsApp reminders when suggest_reminder."""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def run_no_show_reminders(window_days: int = 3) -> Dict[str, Any]:
    """
    For all tenants with ai module and ai.no_show capability:
    - Get upcoming appointments and no-show risk scores.
    - For each appointment with suggest_reminder=True, send a WhatsApp reminder.
    Returns { "tenants_processed": int, "reminders_sent": int, "errors": [] }.
    """
    from app.services.storage_mongo import Storage
    from app.services.storage.tenant_storage import TenantStorage
    from app.services.ai.config_schema import get_effective_ai_config, get_no_show_thresholds
    from app.services.core.ai_facade import AIService
    from app.services.messaging.messaging import Messaging

    try:
        tenants = Storage.list_tenants_basic()
    except Exception as e:
        logger.warning("no_show_reminders: failed to list tenants: %s", e)
        return {"tenants_processed": 0, "reminders_sent": 0, "errors": [str(e)]}

    reminders_sent = 0
    errors: List[str] = []

    for t in tenants:
        tenant = t.get("tenant") or t.get("_id")
        if not tenant:
            continue
        try:
            settings = TenantStorage.get_tenant_settings(tenant)
            if not settings:
                continue
            from app.services.ai.feature_gate import is_ai_capability_enabled
            if not is_ai_capability_enabled(tenant, "ai.no_show"):
                continue

            ai_cfg = get_effective_ai_config(settings)
            if not ai_cfg.get("features", {}).get("no_show_scores", True):
                continue

            reminder_threshold, _ = get_no_show_thresholds(ai_cfg)
            try:
                appts = AIService.list_upcoming_appointments(tenant=tenant, window_days=window_days)
            except Exception:
                appts = []

            for a in appts or []:
                phone = getattr(a, "customer_phone", None) or ""
                past = 0
                try:
                    from .no_show_block_service import get_no_show_count
                    past = get_no_show_count(tenant, phone)
                except Exception:
                    past = 0
                lead_minutes = 1440
                try:
                    lead_minutes = int(getattr(a, "lead_minutes", 1440))
                except Exception:
                    pass
                score = min(0.95, 0.2 + 0.15 * past + (0.1 if lead_minutes < 180 else 0))
                score_rounded = round(float(score), 2)
                if score_rounded < reminder_threshold:
                    continue
                phone = getattr(a, "customer_phone", None) or ""
                if not phone:
                    continue
                time_label = getattr(a, "time", None) or ""
                professional = getattr(a, "professional", None) or ""
                try:
                    msg = (
                        f"Reminder: You have an appointment with {professional} at {time_label}. "
                        "Please reply if you need to reschedule or cancel."
                    )
                    Messaging.send_whatsapp_text(phone.strip(), msg, tenant=tenant)
                    reminders_sent += 1
                except Exception as send_err:
                    errors.append(f"{tenant}: send to {phone[:8]}...: {send_err}")

        except Exception as e:
            errors.append(f"{tenant}: {e}")
            logger.warning("no_show_reminders tenant %s: %s", tenant, e)

    return {"tenants_processed": len(tenants), "reminders_sent": reminders_sent, "errors": errors}
