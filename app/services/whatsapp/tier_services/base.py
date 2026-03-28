"""
Base tier service: common interface for Basic, Enterprise, Pro.
All tier-specific behavior is implemented in subclasses.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.services.whatsapp.helpers import constants as WMSG


class BaseTierService(ABC):
    """Base for WhatsApp/AI tier behavior. Subclasses: Basic, Enterprise, Pro."""

    def __init__(self, tenant: str):
        self.tenant = tenant

    @property
    @abstractmethod
    def tier_name(self) -> str:
        """Return 'basic' | 'enterprise' | 'pro'."""
        pass

    def should_use_nl_intents(self) -> bool:
        """True if free-text intent detection should start flows (book, cancel, FAQ, etc.). Pro only."""
        return False

    def should_use_ai_in_flow(self) -> bool:
        """True if AI can be used inside flows (e.g. slot recommendations, time parsing). Enterprise + Pro when AI enabled."""
        return False

    def get_fallback_message(self) -> str:
        """Message when no intent matches and no menu option. Override in subclass if needed."""
        return WMSG.MSG_TIER_NL_FALLBACK
