from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError
from app.helpers.constants import DEFAULT_TIMEZONE

from app.routers import appointments, slots, admin, integrations, ws
from app.routers import users as users_router
from app.routers import store as store_router
from app.routers import catalog as catalog_router
from app.services.storage_mongo import Storage, get_db
from app.routers import tenants as tenants_router
from app.routers import auth as auth_router
from app.routers import customers as customers_router
from app.routers import promotions as promotions_router
from app.routers import followups as followups_router
from app.routers import reports as reports_router
from app.routers import cron as cron_router
from app.routers import retention as retention_router
from app.routers import staff as staff_router
from app.routers import upload as upload_router
from app.routers import whatsapp as whatsapp_router
from app.routers import services as services_router
from app.routers import workflows as workflows_router
from app.routers import ai as ai_router
from app.routers import ai_assistant as ai_assistant_router
from settings import env
from app.services.core.promotions import promotions as promotions_service
from app.services import followups as followups_service
from app.services import retention as retention_service
from app.services.reports.reports_store import generate_and_store_report, deliver_report_links

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date, timezone, timedelta
from zoneinfo import ZoneInfo


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Powered Appointment & Scheduling API",
        version="0.1.0",
        description="Multi-domain appointment booking with AI slot prediction, REST + WebSocket, and Twilio integration.",
        openapi_tags=[
            {"name": "Auth", "description": "Authentication (JWT) for Admin UI"},
            {"name": "Users", "description": "User management (Super Admin, Tenant Admin, Staff)"},
            {"name": "Tenants", "description": "Tenant onboarding and management"},
            {"name": "Appointments", "description": "Create, list, and cancel appointments"},
            {"name": "Slots", "description": "List and predict available slots"},
            {"name": "Promotions", "description": "Create and send promotions via WhatsApp and Email"},
            {"name": "Followups", "description": "Automated follow-up messages"},
            {"name": "Reports", "description": "Daily reports and analytics exports"},
            {"name": "Retention", "description": "Customer retention metrics"},
            {"name": "Staff", "description": "Staff management (CRUD)"},
            {"name": "Admin", "description": "Analytics and dashboards"},
            {"name": "Integrations", "description": "Webhooks for WhatsApp/Twilio"},
            {"name": "Realtime", "description": "WebSocket updates for slots and appointments"},
            {"name": "AI Assistant", "description": "Super Admin: configure AI keywords, intents, training data (new module)"},
        ],
    )

    # CORS configuration (supports React dev server origins via CORS_ORIGINS env)
    origins = [o.strip() for o in env.str("CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handling: map AppError to JSON response
    @app.exception_handler(AppError)
    def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValueError)
    def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    # Seed demo data for a default tenant for quick start
    # seed_demo_data("demo-salon")
    # seed_demo_data("demo-clinic")

    # Routers
    app.include_router(auth_router.router, prefix="/v1", tags=["Auth"]) 
    app.include_router(users_router.router, prefix="/v1", tags=["Users"]) 
    app.include_router(tenants_router.router, prefix="/v1", tags=["Tenants"]) 
    app.include_router(customers_router.router, prefix="/v1", tags=["Customers"]) 
    app.include_router(appointments.router, prefix="/v1", tags=["Appointments"]) 
    app.include_router(slots.router, prefix="/v1", tags=["Slots"]) 
    app.include_router(promotions_router.router, prefix="/v1", tags=["Promotions"]) 
    app.include_router(followups_router.router, prefix="/v1", tags=["Followups"]) 
    app.include_router(reports_router.router, prefix="/v1", tags=["Reports"]) 
    app.include_router(cron_router.router, prefix="/v1", tags=["Admin"])
    app.include_router(services_router.router, prefix="/v1", tags=["Services"])
    app.include_router(workflows_router.router, prefix="/v1", tags=["Workflows"])
    app.include_router(retention_router.router, prefix="/v1", tags=["Retention"])
    app.include_router(staff_router.router, prefix="/v1", tags=["Staff"]) 
    app.include_router(upload_router.router, prefix="/v1", tags=["Upload"])
    app.include_router(admin.router, prefix="/v1", tags=["Admin"]) 
    app.include_router(integrations.router, prefix="/v1", tags=["Integrations"]) 
    app.include_router(store_router.router, prefix="/v1", tags=["Store"]) 
    app.include_router(catalog_router.router, prefix="/v1", tags=["Store Catalog"]) 
    app.include_router(whatsapp_router.router, prefix="/v1", tags=["WhatsApp"]) 
    app.include_router(ai_router.router, prefix="/v1", tags=["AI"])
    app.include_router(ai_assistant_router.router, prefix="/v1", tags=["AI Assistant"])
    app.include_router(ws.router, tags=["Realtime"]) 

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # --- Scheduler startup/shutdown hooks (Milestone 1 scaffold) ---
    import logging as _logging
    _logger = _logging.getLogger(__name__)

    def _job_dispatch_promotions():
        _logger.info("[Scheduler] dispatch_promotions tick at %s", datetime.now(timezone.utc).isoformat())
        try:
            promotions_service.process_pending_promotions()
        except Exception as e:
            _logger.error("dispatch_promotions error: %s", e)

    def _job_dispatch_followups():
        _logger.info("[Scheduler] dispatch_followups tick at %s", datetime.now(timezone.utc).isoformat())
        try:
            followups_service.process_due_followups()
        except Exception as e:
            _logger.error("dispatch_followups error: %s", e)

    def _job_stock_alerts():
        _logger.info("[Scheduler] stock_alerts tick at %s", datetime.now(timezone.utc).isoformat())
        try:
            # Simple stock alert logic: find products with qty < 5
            tenants = Storage.list_tenants_basic()
            db = get_db()
            inv_col = db.get_collection("inventory")
            for t in tenants:
                tid = t.get("tenant") or t.get("_id")
                low_stock = list(inv_col.find({"tenant": tid, "available_qty": {"$lt": 5}}))
                if low_stock:
                    msg = f"Low stock alert for {tid}: " + ", ".join([f"{i['sku']} ({i['available_qty']})" for i in low_stock])
                    _logger.info(msg)
                    # Could send email/whatsapp here
        except Exception as e:
            _logger.error("stock_alerts error: %s", e)

    def _job_daily_reports_tick():
        _logger.info("[Scheduler] daily_reports_tick at %s", datetime.now(timezone.utc).isoformat())

    def _job_retention_nightly():
        _logger.info("[Scheduler] retention_nightly at %s", datetime.now(timezone.utc).isoformat())
        try:
            retention_service.aggregate_and_store_for_all_tenants()
        except Exception as e:
            _logger.error("retention_nightly error: %s", e)

    def _job_no_show_reminders():
        _logger.info("[Scheduler] no_show_reminders at %s", datetime.now(timezone.utc).isoformat())
        try:
            from app.services.salon.appointments.no_show_reminder_service import run_no_show_reminders
            result = run_no_show_reminders(window_days=3)
            if result.get("reminders_sent"):
                _logger.info("no_show_reminders: sent %s reminders", result["reminders_sent"])
            for err in result.get("errors") or []:
                _logger.warning("no_show_reminders: %s", err)
        except Exception as e:
            _logger.error("no_show_reminders error: %s", e)

    def _job_trial_expiry():
        _logger.info("[Scheduler] trial_expiry at %s", datetime.now(timezone.utc).isoformat())
        try:
            n = Storage.deactivate_expired_trials()
            if n:
                _logger.info("trial_expiry: deactivated %d tenant(s)", n)
        except Exception as e:
            _logger.error("trial_expiry error: %s", e)

    def _job_trial_expiring_tomorrow():
        """Notify super admin by email and optionally WhatsApp about tenants whose trial expires tomorrow."""
        _logger.info("[Scheduler] trial_expiring_tomorrow at %s", datetime.now(timezone.utc).isoformat())
        try:
            tomorrow_start = (datetime.now(timezone.utc).date() + timedelta(days=1))
            tomorrow_end = tomorrow_start + timedelta(days=1)
            tenants = Storage.list_tenants_basic()
            expiring = []
            for t in tenants:
                te = t.get("trial_ends_at")
                if te is None:
                    continue
                if hasattr(te, "date"):
                    d = te.date() if te.tzinfo else (te.replace(tzinfo=timezone.utc).date())
                else:
                    d = te if isinstance(te, date) else None
                if d is not None and tomorrow_start <= d < tomorrow_end:
                    expiring.append({"tenant": t.get("tenant") or t.get("_id"), "trial_ends_at": te, "owner_email": t.get("owner_email")})
            if not expiring:
                return
            super_admin = Storage._users_col().find_one({"role": "super_admin"}, {"email": 1})
            to_email = (super_admin or {}).get("email") or env.str("BOOT_SUPER_ADMIN_EMAIL", "")
            from app.services.core.messaging_service import Messaging
            lines = ["Trials expiring tomorrow (UTC date %s):" % tomorrow_start]
            for e in expiring:
                lines.append("  - %s (owner: %s)" % (e["tenant"], e.get("owner_email") or "—"))
            body = "\n".join(lines)
            if to_email:
                try:
                    Messaging.send_email(to_email, "Tenant trials expiring tomorrow", body, None)
                    _logger.info("trial_expiring_tomorrow: emailed %s", to_email)
                except Exception as ex:
                    _logger.warning("trial_expiring_tomorrow email failed: %s", ex)
            super_phone = env.str("SUPER_ADMIN_PHONE", "")
            if super_phone:
                try:
                    Messaging.send_whatsapp_text(super_phone, "Trials expiring tomorrow: " + ", ".join(e["tenant"] for e in expiring), tenant=None)
                    _logger.info("trial_expiring_tomorrow: WhatsApp sent to SUPER_ADMIN_PHONE")
                except Exception as ex:
                    _logger.warning("trial_expiring_tomorrow WhatsApp failed: %s", ex)
        except Exception as e:
            _logger.error("trial_expiring_tomorrow error: %s", e)

    def _register_daily_report_jobs(scheduler: BackgroundScheduler):
        """Register daily report jobs per tenant using the tenant's IANA timezone (default Asia/Kolkata)."""
        try:
            tenants = Storage.list_tenants_basic()
        except Exception as e:
            _logger.warning("Unable to list tenants for daily report jobs: %s", e)
            tenants = []

        # Job configuration: (hour, minute, name_suffix) — daily report once per day at 8 PM tenant local time
        job_times = [(20, 0, "daily")]

        for t in tenants:
            tenant_id = t.get("tenant") or t.get("_id")
            tz_str = (t.get("tz") or env.str("DEFAULT_TZ", DEFAULT_TIMEZONE)).strip()
            try:
                tz = ZoneInfo(tz_str)
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)

            for hour, minute, suffix in job_times:
                try:
                    trigger = CronTrigger(hour=hour, minute=minute, timezone=tz)
                    job_id = f"daily_report_{tenant_id}_{suffix}"

                    def _make_job(tenant: str, timezone: ZoneInfo):
                        def _job():
                            _logger.info("[Scheduler] running daily report (%s) for tenant=%s", suffix, tenant)
                            try:
                                # Use tenant-local date for label
                                today_local = datetime.now(timezone).date()
                                doc = generate_and_store_report(tenant, today_local)
                                try:
                                    deliver_report_links(tenant, doc)
                                except Exception as de:
                                    _logger.warning("Report delivery failed for %s: %s", tenant, de)
                            except Exception as ge:
                                _logger.error("Report generation failed for %s: %s", tenant, ge)
                        return _job

                    scheduler.add_job(_make_job(tenant_id, tz), trigger, id=job_id, replace_existing=True)
                    _logger.info("Registered daily report job for %s at %02d:%02d %s", tenant_id, hour, minute, tz_str)
                except Exception as je:
                    _logger.warning("Failed to register %s report job for %s: %s", suffix, tenant_id, je)

    @app.on_event("startup")
    def _startup_scheduler():
        # Backfill missing active flags on startup (idempotent)
        try:
            counts = Storage.ensure_active_flags()
            _logger.info("Backfilled active flags: %s", counts)
        except Exception as e:
            _logger.warning("Failed to backfill active flags: %s", e)

        # Platform defaults — ``default_message`` collection (migrates legacy whatsapp_messages if needed)
        try:
            from app.services.core.default_message_service import ensure_default_messages_synced

            changed = ensure_default_messages_synced()
            _logger.info(
                "default_message platform sync%s",
                " (written)" if changed else "",
            )
        except Exception as e:
            _logger.warning("Failed to sync default_message: %s", e)

        # One tenant_message_templates doc per tenant (override storage; may be empty)
        try:
            from app.services.core.tenant_message_templates_service import ensure_all_tenants_have_default_templates
            created = ensure_all_tenants_have_default_templates()
            if created:
                _logger.info("Created empty tenant_message_templates rows for %s tenant(s)", created)
        except Exception as e:
            _logger.warning("Failed to seed tenant_message_templates: %s", e)

        # Seed default cron jobs if none exist
        try:
            col = cron_router._cron_col()
            if col.count_documents({}) == 0:
                defaults = [
                    {
                        "job_id": "dispatch_promotions",
                        "name": "Dispatch Promotions",
                        "type": "promotion",
                        "schedule_type": "interval",
                        "schedule_value": {"seconds": 30},
                        "enabled": True
                    },
                    {
                        "job_id": "dispatch_followups",
                        "name": "Dispatch Followups",
                        "type": "report", # Using report as proxy for system tasks
                        "schedule_type": "interval",
                        "schedule_value": {"seconds": 60},
                        "enabled": True
                    },
                    {
                        "job_id": "retention_nightly",
                        "name": "Nightly Retention Aggregation",
                        "type": "retention",
                        "schedule_type": "cron",
                        "schedule_value": {"hour": 2, "minute": 0},
                        "enabled": True
                    },
                    {
                        "job_id": "daily_reports_tenant",
                        "name": "Per-Tenant Daily Reports",
                        "type": "report",
                        "schedule_type": "cron",
                        "schedule_value": {"hour": 20, "minute": 0},
                        "enabled": True,
                        "params": {"per_tenant": True}
                    },
                    {
                        "job_id": "stock_alerts",
                        "name": "Out of Stock Alerts",
                        "type": "stock_alert",
                        "schedule_type": "interval",
                        "schedule_value": {"minutes": 60},
                        "enabled": True
                    },
                    {
                        "job_id": "no_show_reminders",
                        "name": "No-Show Reminders (WhatsApp)",
                        "type": "report",
                        "schedule_type": "cron",
                        "schedule_value": {"hour": 9, "minute": 0},
                        "enabled": True
                    },
                    {
                        "job_id": "trial_expiry",
                        "name": "Deactivate Expired 14-day Trials",
                        "type": "report",
                        "schedule_type": "cron",
                        "schedule_value": {"hour": 0, "minute": 5},
                        "enabled": True
                    },
                    {
                        "job_id": "trial_expiring_tomorrow",
                        "name": "Notify Super Admin: Trials Expiring Tomorrow",
                        "type": "report",
                        "schedule_type": "cron",
                        "schedule_value": {"hour": 8, "minute": 0},
                        "enabled": True
                    }
                ]
                for d in defaults:
                    col.update_one({"job_id": d["job_id"]}, {"$set": d}, upsert=True)
                _logger.info("Seeded default cron jobs")
            # Always ensure daily report cron entry exists (runs at 20:00 tenant local time per tenant)
            col.update_one(
                {"job_id": "daily_reports_tenant"},
                {"$set": {
                    "job_id": "daily_reports_tenant",
                    "name": "Per-Tenant Daily Reports",
                    "type": "report",
                    "schedule_type": "cron",
                    "schedule_value": {"hour": 20, "minute": 0},
                    "enabled": True,
                    "params": {"per_tenant": True},
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }},
                upsert=True,
            )
            # Ensure trial expiry job exists (deactivates tenants after 14-day trial ends)
            col.update_one(
                {"job_id": "trial_expiry"},
                {"$set": {
                    "job_id": "trial_expiry",
                    "name": "Deactivate Expired 14-day Trials",
                    "type": "report",
                    "schedule_type": "cron",
                    "schedule_value": {"hour": 0, "minute": 5},
                    "enabled": True,
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }},
                upsert=True,
            )
            col.update_one(
                {"job_id": "trial_expiring_tomorrow"},
                {"$set": {
                    "job_id": "trial_expiring_tomorrow",
                    "name": "Notify Super Admin: Trials Expiring Tomorrow",
                    "type": "report",
                    "schedule_type": "cron",
                    "schedule_value": {"hour": 8, "minute": 0},
                    "enabled": True,
                    "updated_at": datetime.now(timezone.utc).replace(tzinfo=None),
                }},
                upsert=True,
            )
        except Exception as e:
            _logger.warning("Failed to seed cron jobs: %s", e)

        # Bootstrap super admin user if none exists and env provides credentials
        try:
            from settings import env as _env
            ucol = Storage._users_col()
            if ucol.count_documents({"role": "super_admin"}) == 0:
                email = _env.str("BOOT_SUPER_ADMIN_EMAIL", "")
                pwd = _env.str("BOOT_SUPER_ADMIN_PASSWORD", "")
                if email and pwd:
                    Storage.create_user(email=email, password=pwd, role="super_admin", tenant=None, display_name="Super Admin")
                    _logger.info("Bootstrapped super_admin user: %s", email)
                else:
                    _logger.warning("No super_admin found and BOOT_SUPER_ADMIN_EMAIL/PASSWORD not set; set them to bootstrap.")
        except Exception as e:
            _logger.warning("Failed to bootstrap super admin: %s", e)

        if not env.bool("SCHEDULER_ENABLED", True):
            _logger.info("Scheduler disabled by env SCHEDULER_ENABLED")
            return

        scheduler = BackgroundScheduler()
        app.state.scheduler = scheduler

        def _sync_jobs():
            _logger.info("[Scheduler] Syncing jobs from DB...")
            try:
                col = cron_router._cron_col()
                db_jobs = list(col.find({"enabled": True}))
                existing_ids = [j.id for j in scheduler.get_jobs()]
                
                # Dynamic mapping of job_id to function
                job_map = {
                    "dispatch_promotions": _job_dispatch_promotions,
                    "dispatch_followups": _job_dispatch_followups,
                    "retention_nightly": _job_retention_nightly,
                    "daily_reports_tenant": None, # Handled specially
                    "stock_alerts": _job_stock_alerts,
                    "no_show_reminders": _job_no_show_reminders,
                    "trial_expiry": _job_trial_expiry,
                    "trial_expiring_tomorrow": _job_trial_expiring_tomorrow,
                }

                for dj in db_jobs:
                    jid = dj["job_id"]
                    if jid == "daily_reports_tenant":
                        # We use the existing _register_daily_report_jobs but could also refactor it
                        # For now, let's just ensure it's called or handled.
                        # Since it registers MANY jobs (per tenant), we handle it separately.
                        continue
                    
                    func = job_map.get(jid)
                    if not func:
                        _logger.warning("No function mapped for job_id: %s", jid)
                        continue
                    
                    stype = dj["schedule_type"]
                    sval = dj["schedule_value"]
                    
                    trigger = None
                    if stype == "interval":
                        trigger = IntervalTrigger(**sval)
                    elif stype == "cron":
                        trigger = CronTrigger(**sval)
                    
                    if trigger:
                        scheduler.add_job(func, trigger, id=jid, replace_existing=True)
                        _logger.info("Scheduled/Updated job: %s (%s)", jid, stype)

                # Remove jobs that are disabled in DB or no longer present
                db_job_ids = [j["job_id"] for j in db_jobs]
                # Filter system sync job itself and daily report jobs
                to_remove = [eid for eid in existing_ids if eid not in db_job_ids and eid not in ["sync_jobs_from_db"] and not eid.startswith("daily_report_")]
                for rid in to_remove:
                    scheduler.remove_job(rid)
                    _logger.info("Removed disabled/deleted job: %s", rid)
                
                # Special handle for daily reports if enabled
                daily_rep_job = next((j for j in db_jobs if j["job_id"] == "daily_reports_tenant"), None)
                if daily_rep_job:
                    _register_daily_report_jobs(scheduler)
                else:
                    # Remove all daily report jobs if main toggle is off
                    for j in scheduler.get_jobs():
                        if j.id.startswith("daily_report_"):
                            scheduler.remove_job(j.id)

            except Exception as e:
                _logger.error("Error syncing jobs: %s", e)

        # Sync once at startup
        _sync_jobs()
        # And every 5 minutes
        scheduler.add_job(_sync_jobs, IntervalTrigger(minutes=5), id="sync_jobs_from_db", replace_existing=True)
        
        scheduler.start()
        _logger.info("Scheduler started with jobs: %s", [j.id for j in scheduler.get_jobs()])

    @app.on_event("shutdown")
    def _shutdown_scheduler():
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler:
            try:
                scheduler.shutdown(wait=False)
                _logger.info("Scheduler shutdown complete")
            except Exception as e:
                _logger.warning("Scheduler shutdown error: %s", e)

    return app


# ---------- Run with auto-reload in development ----------
# Start with:  python -m app.main   (from project root)
# This uses --reload so Python changes apply without restarting the server.
if __name__ == "__main__":
    import uvicorn
    import os
    # Use reload by default unless RELOAD=false (e.g. in production)
    use_reload = os.environ.get("RELOAD", "true").lower() in ("1", "true", "yes")
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=use_reload,
    )
