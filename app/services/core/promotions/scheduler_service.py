# app/services/core/promotions/scheduler_service.py
from __future__ import annotations
import logging

from app.helpers.date_utils import utcnow
from .helpers.db_utils import promotions_col
from .sender_service import PromotionSenderService

logger = logging.getLogger(__name__)


class PromotionSchedulerService:
    @staticmethod
    def process_pending() -> None:
        col = promotions_col()
        now = utcnow()
        for p in col.find({"status": "scheduled", "schedule_at": {"$lte": now}}).sort("schedule_at", 1):
            prom_id = str(p["_id"])
            tenant = p.get("tenant")
            try:
                logger.info("Dispatching scheduled promotion %s for tenant %s", prom_id, tenant)
                PromotionSenderService.send_now(tenant, prom_id)
            except Exception as e:
                logger.error("Failed to dispatch promotion %s: %s", prom_id, e)
