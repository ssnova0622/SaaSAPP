"""
Central registry for scheduled (APScheduler) cron jobs.

- **Operations** jobs: background work only (no tenant-owner digest email/WhatsApp).
- **Notifications** jobs: send email and/or WhatsApp to tenant owners, customers, or super admin.

Use ``execute_job()`` for manual "run now" and the same handlers for the scheduler.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo

from app.helpers.constants import DEFAULT_TIMEZONE
from settings import env

logger = logging.getLogger(__name__)


class CronUsage(str, Enum):
    """High-level bucket for admin UI and operators."""

    OPERATIONS = "operations"
    NOTIFICATIONS = "notifications"


class NotifyAudience(str, Enum):
    """Who receives outbound messages, if any."""

    NONE = "none"
    TENANT_OWNER = "tenant_owner"
    TENANT_CUSTOMERS = "tenant_customers"
    SUPER_ADMIN = "super_admin"


@dataclass(frozen=True)
class CronJobDefinition:
    job_id: str
    name: str
    usage: CronUsage
    audience: NotifyAudience
    notify_summary: str
    """Human-readable: what is sent and to whom."""
    handler: Optional[Callable[[], None]]
    """None for meta-jobs (e.g. daily_reports_tenant) registered per tenant."""
    is_meta: bool = False


# ---------------------------------------------------------------------------
# Handlers (lazy service imports inside each body to limit import cycles)
# ---------------------------------------------------------------------------


def _handle_dispatch_promotions() -> None:
    from app.services.core.promotions import promotions as promotions_service

    promotions_service.process_pending_promotions()


def _handle_dispatch_followups() -> None:
    from app.services import followups as followups_service

    followups_service.process_due_followups()


def _handle_retention_nightly() -> None:
    from app.services import retention as retention_service

    retention_service.aggregate_and_store_for_all_tenants()


def _handle_stock_alerts() -> None:
    from app.services.storage_mongo import Storage, get_db

    tenants = Storage.list_tenants_basic()
    db = get_db()
    inv_col = db.get_collection("inventory")
    for t in tenants:
        tid = t.get("tenant") or t.get("_id")
        low_stock = list(inv_col.find({"tenant": tid, "available_qty": {"$lt": 5}}))
        if low_stock:
            msg = f"Low stock alert for {tid}: " + ", ".join(
                [f"{i['sku']} ({i['available_qty']})" for i in low_stock]
            )
            logger.info(msg)


def _handle_no_show_reminders() -> None:
    from app.services.salon.appointments.no_show_reminder_service import run_no_show_reminders

    result = run_no_show_reminders(window_days=3)
    if result.get("reminders_sent"):
        logger.info("no_show_reminders: sent %s reminders", result["reminders_sent"])
    for err in result.get("errors") or []:
        logger.warning("no_show_reminders: %s", err)


def _handle_trial_expiry() -> None:
    from app.services.storage_mongo import Storage

    n = Storage.deactivate_expired_trials()
    if n:
        logger.info("trial_expiry: deactivated %d tenant(s)", n)


def _handle_trial_expiring_tomorrow() -> None:
    from app.services.core.messaging_service import Messaging
    from app.services.storage_mongo import Storage

    tomorrow_start = datetime.now(timezone.utc).date() + timedelta(days=1)
    tomorrow_end = tomorrow_start + timedelta(days=1)
    tenants = Storage.list_tenants_basic()
    expiring: List[Dict[str, Any]] = []
    for t in tenants:
        te = t.get("trial_ends_at")
        if te is None:
            continue
        if hasattr(te, "date"):
            d = te.date() if te.tzinfo else (te.replace(tzinfo=timezone.utc).date())
        else:
            d = te if isinstance(te, date) else None
        if d is not None and tomorrow_start <= d < tomorrow_end:
            expiring.append(
                {
                    "tenant": t.get("tenant") or t.get("_id"),
                    "trial_ends_at": te,
                    "owner_email": t.get("owner_email"),
                }
            )
    if not expiring:
        return
    super_admin = Storage._users_col().find_one({"role": "super_admin"}, {"email": 1})
    to_email = (super_admin or {}).get("email") or env.str("BOOT_SUPER_ADMIN_EMAIL", "")
    lines = ["Trials expiring tomorrow (UTC date %s):" % tomorrow_start]
    for e in expiring:
        lines.append("  - %s (owner: %s)" % (e["tenant"], e.get("owner_email") or "—"))
    body = "\n".join(lines)
    if to_email:
        try:
            Messaging.send_email(to_email, "Tenant trials expiring tomorrow", body, None)
            logger.info("trial_expiring_tomorrow: emailed %s", to_email)
        except Exception as ex:
            logger.warning("trial_expiring_tomorrow email failed: %s", ex)
    super_phone = env.str("SUPER_ADMIN_PHONE", "")
    if super_phone:
        try:
            Messaging.send_whatsapp_text(
                super_phone,
                "Trials expiring tomorrow: " + ", ".join(e["tenant"] for e in expiring),
                tenant=None,
            )
            logger.info("trial_expiring_tomorrow: WhatsApp sent to SUPER_ADMIN_PHONE")
        except Exception as ex:
            logger.warning("trial_expiring_tomorrow WhatsApp failed: %s", ex)


CRON_DEFINITIONS: List[CronJobDefinition] = [
    CronJobDefinition(
        job_id="dispatch_promotions",
        name="Dispatch Promotions",
        usage=CronUsage.OPERATIONS,
        audience=NotifyAudience.TENANT_CUSTOMERS,
        notify_summary="Sends queued promotion messages to customers (not a tenant-owner digest).",
        handler=_handle_dispatch_promotions,
    ),
    CronJobDefinition(
        job_id="dispatch_followups",
        name="Dispatch Followups",
        usage=CronUsage.OPERATIONS,
        audience=NotifyAudience.TENANT_CUSTOMERS,
        notify_summary="Sends due follow-up messages to customers per follow-up rules.",
        handler=_handle_dispatch_followups,
    ),
    CronJobDefinition(
        job_id="retention_nightly",
        name="Nightly Retention Aggregation",
        usage=CronUsage.OPERATIONS,
        audience=NotifyAudience.NONE,
        notify_summary="Writes retention metrics only; no email or WhatsApp.",
        handler=_handle_retention_nightly,
    ),
    CronJobDefinition(
        job_id="daily_reports_tenant",
        name="Per-Tenant Daily Reports",
        usage=CronUsage.NOTIFICATIONS,
        audience=NotifyAudience.TENANT_OWNER,
        notify_summary="PDF report to tenant owner via email and/or WhatsApp (invoice_delivery).",
        handler=None,
        is_meta=True,
    ),
    CronJobDefinition(
        job_id="stock_alerts",
        name="Out of Stock Alerts",
        usage=CronUsage.OPERATIONS,
        audience=NotifyAudience.NONE,
        notify_summary="Logs low stock in app logs only; extend to notify owners if needed.",
        handler=_handle_stock_alerts,
    ),
    CronJobDefinition(
        job_id="no_show_reminders",
        name="No-Show Reminders",
        usage=CronUsage.NOTIFICATIONS,
        audience=NotifyAudience.TENANT_CUSTOMERS,
        notify_summary="WhatsApp reminders to customers with at-risk appointments.",
        handler=_handle_no_show_reminders,
    ),
    CronJobDefinition(
        job_id="trial_expiry",
        name="Deactivate Expired Trials",
        usage=CronUsage.OPERATIONS,
        audience=NotifyAudience.NONE,
        notify_summary="Deactivates expired trial tenants; no outbound message.",
        handler=_handle_trial_expiry,
    ),
    CronJobDefinition(
        job_id="trial_expiring_tomorrow",
        name="Trials Expiring Tomorrow (Super Admin)",
        usage=CronUsage.NOTIFICATIONS,
        audience=NotifyAudience.SUPER_ADMIN,
        notify_summary="Email and optional WhatsApp to super admin only.",
        handler=_handle_trial_expiring_tomorrow,
    ),
]

DEFINITION_BY_ID: Dict[str, CronJobDefinition] = {d.job_id: d for d in CRON_DEFINITIONS}
STANDARD_JOB_HANDLERS: Dict[str, Callable[[], None]] = {
    d.job_id: d.handler for d in CRON_DEFINITIONS if d.handler is not None
}


def wrap_cron_execution(job_id: str, fn: Callable[[], None], log: Optional[logging.Logger] = None) -> Callable[[], None]:
    """Uniform logging around every scheduled job body."""

    lg = log or logger

    def _wrapped() -> None:
        lg.info("[Cron] %s start", job_id)
        try:
            fn()
        except Exception as e:
            lg.error("[Cron] %s error: %s", job_id, e)
        else:
            lg.info("[Cron] %s done", job_id)

    return _wrapped


def execute_job(job_id: str, log: Optional[logging.Logger] = None) -> None:
    """
    Run a single standard (non-meta) job by id. Used by APScheduler and manual triggers.
    Raises KeyError if unknown or meta-only id.
    """
    fn = STANDARD_JOB_HANDLERS.get(job_id)
    if fn is None:
        raise KeyError(job_id)
    wrap_cron_execution(job_id, fn, log)()


def run_daily_reports_all_tenants_manual() -> List[Dict[str, Any]]:
    """Meta-job: all active tenants, tenant-local today. Delegates to reports facade."""
    from app.core.container import get_reports_service

    return get_reports_service().run_daily_reports_all_tenants()


def register_per_tenant_daily_report_jobs(
    scheduler: BackgroundScheduler,
    schedule_value: Optional[dict] = None,
    log: Optional[logging.Logger] = None,
) -> None:
    """One APScheduler job per tenant at local hour:minute from DB schedule."""
    from app.services.core.reports_facade import ReportsService
    from app.services.storage_mongo import Storage

    lg = log or logger
    try:
        tenants = Storage.list_tenants_basic()
    except Exception as e:
        lg.warning("Unable to list tenants for daily report jobs: %s", e)
        tenants = []

    hour, minute = 20, 0
    if isinstance(schedule_value, dict):
        try:
            hour = int(schedule_value.get("hour", 20))
            minute = int(schedule_value.get("minute", 0))
        except (TypeError, ValueError):
            hour, minute = 20, 0

    for t in tenants:
        tenant_id = t.get("tenant") or t.get("_id")
        tz_str = (t.get("tz") or env.str("DEFAULT_TZ", DEFAULT_TIMEZONE)).strip()
        try:
            tz = ZoneInfo(tz_str)
        except Exception:
            tz = ZoneInfo(DEFAULT_TIMEZONE)

        try:
            trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
            job_id = f"daily_report_{tenant_id}_daily"

            def _make_job(tenant: str, tenant_tz: ZoneInfo) -> Callable[[], None]:
                def _job() -> None:
                    lg.info("[Cron] daily_report tenant=%s", tenant)
                    try:
                        today_local = datetime.now(tenant_tz).date()
                        ReportsService.run_daily_report(tenant, day=today_local)
                    except Exception as ge:
                        lg.error("[Cron] daily_report failed tenant=%s: %s", tenant, ge)

                return _job

            scheduler.add_job(_make_job(tenant_id, tz), trigger, id=job_id, replace_existing=True)
            lg.info("Registered daily report job for %s at %02d:%02d %s", tenant_id, hour, minute, tz_str)
        except Exception as je:
            lg.warning("Failed to register daily report job for %s: %s", tenant_id, je)


# Backward-compatible ``type`` for admin UI / Postman (original cron router contract).
_LEGACY_JOB_TYPE: Dict[str, str] = {
    "dispatch_promotions": "promotion",
    "dispatch_followups": "report",
    "retention_nightly": "retention",
    "daily_reports_tenant": "report",
    "stock_alerts": "stock_alert",
    "no_show_reminders": "report",
    "trial_expiry": "report",
    "trial_expiring_tomorrow": "report",
}


def catalog_for_api() -> List[Dict[str, Any]]:
    """Serializable job list for admin UI (ids, usage, who gets notified)."""
    out: List[Dict[str, Any]] = []
    for d in CRON_DEFINITIONS:
        row: Dict[str, Any] = {
            "job_id": d.job_id,
            "name": d.name,
            "type": _LEGACY_JOB_TYPE.get(d.job_id, "report"),
            "usage": d.usage.value,
            "audience": d.audience.value,
            "notify_summary": d.notify_summary,
            "is_meta": d.is_meta,
        }
        if d.job_id == "daily_reports_tenant":
            row["notes"] = (
                "Run now processes all active tenants (tenant-local today). "
                "Independent of per-tenant schedule. Tenants may also POST .../reports/daily/run."
            )
        out.append(row)
    return out


def merge_db_doc_with_definition(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Attach registry fields to a Mongo cron_jobs document."""
    jid = doc.get("job_id")
    meta = DEFINITION_BY_ID.get(jid) if jid else None
    enriched = dict(doc)
    if meta:
        enriched["usage"] = meta.usage.value
        enriched["audience"] = meta.audience.value
        enriched["notify_summary"] = meta.notify_summary
        enriched["is_meta"] = meta.is_meta
    else:
        enriched.setdefault("usage", "unknown")
        enriched.setdefault("audience", "unknown")
        enriched.setdefault("notify_summary", "Unregistered job id")
        enriched.setdefault("is_meta", False)
    return enriched
