from __future__ import annotations
from typing import Any, Dict
import logging

from app.core.realtime import get_notifier

logger = logging.getLogger(__name__)


def broadcast_safe(event: Dict[str, Any]) -> None:
    try:
        import anyio

        async def _send():
            await get_notifier().broadcast(event)

        anyio.run(_send)
    except Exception:
        logger.debug("WS broadcast skipped: %s", event.get("type"))
