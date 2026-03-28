from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from .deps import get_current_user
from ..helpers.constants_roles import ROLE_SUPER_ADMIN
from ..services.db import get_db
from pymongo import ASCENDING

router = APIRouter()


def _cron_col():
    db = get_db()
    return db.get_collection("cron_jobs")


@router.get("/admin/cron-jobs/available-actions", tags=["Admin"])
def list_available_cron_actions(user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    # These are the hardcoded actions mapped in app/main.py
    actions = [
        {"job_id": "dispatch_promotions", "name": "Dispatch Promotions", "type": "promotion"},
        {"job_id": "dispatch_followups", "name": "Dispatch Followups", "type": "report"},
        {"job_id": "retention_nightly", "name": "Nightly Retention Aggregation", "type": "retention"},
        {"job_id": "daily_reports_tenant", "name": "Per-Tenant Daily Reports", "type": "report"},
        {"job_id": "stock_alerts", "name": "Out of Stock Alerts", "type": "stock_alert"},
        {"job_id": "no_show_reminders", "name": "No-Show Reminders (WhatsApp)", "type": "report"},
        {"job_id": "trial_expiry", "name": "Deactivate Expired 14-day Trials", "type": "report"},
        {"job_id": "trial_expiring_tomorrow", "name": "Notify Super Admin: Trials Expiring Tomorrow", "type": "report"},
    ]
    return actions


@router.post("/admin/cron-jobs/{job_id}/run", tags=["Admin"])
def run_cron_job_now(job_id: str, request: Request, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    from ..core.container import get_reports_service
    # Special case: daily_reports_tenant is a meta-job (per-tenant jobs in scheduler). Run reports for all tenants now.
    if job_id == "daily_reports_tenant":
        try:
            results = get_reports_service().run_daily_reports_all_tenants()
            col = _cron_col()
            col.update_one({"job_id": job_id}, {"$set": {"last_run": datetime.now(timezone.utc)}})
            return {
                "ok": True,
                "detail": f"Daily reports run for {len(results)} tenant(s)",
                "results": results,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")

    try:
        job = scheduler.get_job(job_id)
        if job:
            job.func()
            col = _cron_col()
            col.update_one({"job_id": job_id}, {"$set": {"last_run": datetime.now(timezone.utc)}})
            return {"ok": True, "detail": f"Job {job_id} executed immediately"}
        raise HTTPException(status_code=404, detail=f"Active job {job_id} not found in scheduler")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CronJobSchema(BaseModel):
    job_id: str
    name: str
    type: str = Field(..., description="promotion|report|stock_alert|retention")
    schedule_type: str = Field(..., description="interval|cron")
    schedule_value: Dict[str, Any] = Field(..., description="e.g. {'seconds': 30} or {'hour': 9, 'minute': 30}")
    enabled: bool = True
    params: Optional[Dict[str, Any]] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@router.get("/admin/cron-jobs", tags=["Admin"])
def list_cron_jobs(request: Request, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    # Access the scheduler from app state to get next_run_time
    scheduler = getattr(request.app.state, "scheduler", None)

    col = _cron_col()
    items = list(col.find().sort("job_id", ASCENDING))
    for item in items:
        item["id"] = str(item.pop("_id"))
        # Try to get next run time from scheduler if it's active
        if scheduler:
            job = scheduler.get_job(item["job_id"])
            if job and job.next_run_time:
                item["next_run"] = job.next_run_time
    return items


@router.post("/admin/cron-jobs", tags=["Admin"])
def upsert_cron_job(body: CronJobSchema, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    col = _cron_col()
    doc = body.model_dump()
    doc["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)

    col.update_one({"job_id": body.job_id}, {"$set": doc}, upsert=True)
    return {"ok": True}


@router.patch("/admin/cron-jobs/{job_id}/toggle", tags=["Admin"])
def toggle_cron_job(job_id: str, enabled: bool, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    col = _cron_col()
    res = col.update_one({"job_id": job_id},
                         {"$set": {"enabled": enabled, "updated_at": datetime.now(timezone.utc).replace(tzinfo=None)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True}


@router.delete("/admin/cron-jobs/{job_id}", tags=["Admin"])
def delete_cron_job(job_id: str, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    col = _cron_col()
    col.delete_one({"job_id": job_id})
    return {"ok": True}
