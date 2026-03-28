from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from app.core.realtime import get_notifier

router = APIRouter()
notifier = get_notifier()


@router.websocket("/ws/{tenant}")
async def websocket_endpoint(websocket: WebSocket, tenant: str):
    await notifier.connect(websocket)
    try:
        while True:
            # Simple echo/ping; clients can send {"type":"ping"}
            _ = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong", "tenant": tenant}))
    except WebSocketDisconnect:
        notifier.disconnect(websocket)
    except Exception:
        notifier.disconnect(websocket)
