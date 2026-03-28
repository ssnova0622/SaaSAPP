"""Persist general customer feedback (WhatsApp); used by core menu and SUBMIT_FEEDBACK workflow step."""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Single collection for all tenant feedback from WhatsApp (store-agnostic name).
FEEDBACK_COLLECTION = "customer_feedback"


def persist_customer_feedback(
        tenant: str,
        phone: str,
        feedback_text: str,
        *,
        extra: Optional[dict[str, Any]] = None,
) -> bool:
    doc: dict[str, Any] = {
        "tenant": tenant,
        "phone": phone,
        "feedback": feedback_text,
        "created_at": dt.datetime.now(dt.timezone.utc),
    }
    if extra:
        doc.update(extra)
    try:
        from app.services.db import get_db

        get_db().get_collection(FEEDBACK_COLLECTION).insert_one(doc)
        return True
    except Exception as e:
        logger.warning("Failed to save feedback: %s", e)
        return False
