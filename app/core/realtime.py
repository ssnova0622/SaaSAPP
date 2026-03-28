# app/core/realtime.py
"""
Shared WebSocket notifier so services can broadcast without importing routers.
Routers/ws registers the Notifier instance here; services use get_notifier().
"""
from __future__ import annotations

from typing import Any, List, Optional
import json

try:
    from fastapi import WebSocket
except Exception:
    WebSocket = Any  # type: ignore


class Notifier:
    """Broadcasts messages to connected WebSocket clients."""

    def __init__(self) -> None:
        self.active: List[Any] = []

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: Any) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: Any) -> None:
        data = message if isinstance(message, str) else json.dumps(message)
        living = []
        for ws in self.active:
            try:
                await ws.send_text(data)
                living.append(ws)
            except Exception:
                pass
        self.active = living


_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Return the global notifier instance. Created on first use."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


def set_notifier(notifier: Notifier) -> None:
    """Test helper: inject a mock notifier."""
    global _notifier
    _notifier = notifier
