from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError

from app.routers import appointments, slots, admin, integrations, ws
from app.routers import users as users_router
from app.routers import store as store_router
from app.routers import catalog as catalog_router
from app.services.storage_mongo import Storage
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
from app.routers import meta as meta_router
from settings import env
from app.services.core.cron_scheduled_jobs import (
    STANDARD_JOB_HANDLERS,
    register_per_tenant_daily_report_jobs,
    wrap_cron_execution,
)
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone


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
            {"name": "AI Assistant",
             "description": "Super Admin: configure AI keywords, intents, training data (new module)"},
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

    # Routers
    app.include_router(auth_router.router, prefix="/v1", tags=["Auth"])
    app.include_router(users_router.router, prefix="/v1", tags=["Users"])
    app.include_router(tenants_router.router, prefix="/v1", tags=["Tenants"])
    app.include_router(meta_router.router, prefix="/v1", tags=["Meta"])
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
                        "schedule_value": {"minutes": 5},
                        "enabled": True
                    },
                    {
                        "job_id": "dispatch_followups",
                        "name": "Dispatch Followups",
                        "type": "report",  # Using report as proxy for system tasks
                        "schedule_type": "interval",
                        "schedule_value": {"minutes": 5},
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
                    Storage.create_user(email=email, password=pwd, role="super_admin", tenant=None,
                                        display_name="Super Admin")
                    _logger.info("Bootstrapped super_admin user: %s", email)
                else:
                    _logger.warning(
                        "No super_admin found and BOOT_SUPER_ADMIN_EMAIL/PASSWORD not set; set them to bootstrap.")
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

                for dj in db_jobs:
                    jid = dj["job_id"]
                    if jid == "daily_reports_tenant":
                        continue

                    raw = STANDARD_JOB_HANDLERS.get(jid)
                    if not raw:
                        _logger.warning("No handler registered for job_id: %s", jid)
                        continue
                    func = wrap_cron_execution(jid, raw, _logger)

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
                to_remove = [eid for eid in existing_ids if
                             eid not in db_job_ids and eid not in ["sync_jobs_from_db"] and not eid.startswith(
                                 "daily_report_")]
                for rid in to_remove:
                    scheduler.remove_job(rid)
                    _logger.info("Removed disabled/deleted job: %s", rid)

                # Special handle for daily reports if enabled
                daily_rep_job = next((j for j in db_jobs if j["job_id"] == "daily_reports_tenant"), None)
                if daily_rep_job:
                    register_per_tenant_daily_report_jobs(
                        scheduler,
                        daily_rep_job.get("schedule_value"),
                        _logger,
                    )
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
