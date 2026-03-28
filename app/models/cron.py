# app/models/cron.py
from __future__ import annotations
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CronJobSchema(BaseModel):
    job_id: str
    name: str
    type: str = Field(..., description="promotion|report|stock_alert|retention")
    schedule_type: str = Field(..., description="interval|cron")
    schedule_value: Dict[str, Any]
    enabled: bool = True
    params: Optional[Dict[str, Any]] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class CronJobToggle(BaseModel):
    enabled: bool
