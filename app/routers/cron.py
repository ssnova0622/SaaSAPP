from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from .deps import get_current_user
from ..helpers.constants_roles import ROLE_SUPER_ADMIN
from ..services.db import get_db
from ..services.core.cron_scheduled_jobs import (
    catalog_for_api,
    execute_job,
    run_daily_reports_all_tenants_manual,
    STANDARD_JOB_HANDLERS,
    merge_db_doc_with_definition,
)
from pymongo import ASCENDING

router = APIRouter()
_logger = logging.getLogger(__name__)


def _cron_col():
    db = get_db()
    return db.get_collection("cron_jobs")


def _cron_last_run_utc_naive() -> datetime:
    """BSON DateTime in MongoDB is typically stored as UTC naive."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _touch_cron_last_run(job_id: str) -> None:
    """Persist last_run as UTC-naive (reliable BSON). No upsert — avoids orphan rows."""
    _cron_col().update_one(
        {"job_id": job_id},
        {"$set": {"last_run": _cron_last_run_utc_naive()}},
    )


@router.get("/admin/cron-jobs/available-actions", tags=["Admin"])
def list_available_cron_actions(user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    return catalog_for_api()


@router.post("/admin/cron-jobs/{job_id}/run", tags=["Admin"])
def run_cron_job_now(job_id: str, request: Request, user: dict = Depends(get_current_user)):
    if str(user.get("role")).lower() != ROLE_SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin only")

    if job_id == "daily_reports_tenant":
        try:
            results = run_daily_reports_all_tenants_manual()
            _touch_cron_last_run(job_id)
            ok_n = sum(1 for r in results if r.get("status") == "ok")
            err_n = sum(1 for r in results if r.get("status") == "error")
            return {
                "ok": err_n == 0,
                "detail": f"Daily reports: {ok_n} ok, {err_n} failed, {len(results)} total row(s)",
                "results": results,
            }
        except Exception as e:
            _logger.exception("daily_reports_tenant manual run failed: %s", e)
            raise HTTPException(status_code=500, detail=str(e) or type(e).__name__)

    if job_id in STANDARD_JOB_HANDLERS:
        try:
            execute_job(job_id, _logger)
            _touch_cron_last_run(job_id)
            return {"ok": True, "detail": f"Job {job_id} executed immediately"}
        except Exception as e:
            _logger.exception("Cron manual run failed job_id=%s: %s", job_id, e)
            raise HTTPException(status_code=500, detail=str(e) or type(e).__name__)

    scheduler = getattr(request.app.state, "scheduler", None)
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler not initialized or unknown job_id")

    try:
        job = scheduler.get_job(job_id)
        if job:
            job.func()
            _touch_cron_last_run(job_id)
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
    out = []
    for item in items:
        item["id"] = str(item.pop("_id"))
        if scheduler:
            job = scheduler.get_job(item["job_id"])
            if job and job.next_run_time:
                item["next_run"] = job.next_run_time
            if item.get("job_id") == "daily_reports_tenant" and not item.get("next_run"):
                item["next_run_note"] = "One scheduler job per tenant (id: daily_report_<tenant>_daily)"
        out.append(merge_db_doc_with_definition(item))
    return out


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
