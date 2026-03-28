"""WhatsApp router package: menus, config, actions, bot, webhooks."""
from __future__ import annotations

from fastapi import APIRouter

from .menus import router as menus_router
from .routes import router as main_router

router = APIRouter()
router.include_router(menus_router)
router.include_router(main_router)
