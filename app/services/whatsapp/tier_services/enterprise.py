"""
Enterprise tier: limited AI (slot suggestions, no-show, time parsing). No NL; flows remain menu-based.
No AI_ENABLED flag: limited AI works when AI module and capabilities are enabled.
"""
from __future__ import annotations

from app.services.whatsapp.tier_services.base import BaseTierService
from app.services.ai.feature_gate import should_use_ai_in_flow as _ai_in_flow_enabled


class EnterpriseTierService(BaseTierService):
    """Limited AI (slot recs, no-show, etc.). Menu-based flows. No AI_ENABLED check."""

    @property
    def tier_name(self) -> str:
        return "enterprise"

    def should_use_nl_intents(self) -> bool:
        return False

    def should_use_ai_in_flow(self) -> bool:
        return _ai_in_flow_enabled(self.tenant)
