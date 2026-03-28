"""
Basic tier: no AI by default. Super admin can enable AI module for testing (then limited AI works, like Enterprise).
"""
from __future__ import annotations

from app.services.whatsapp.tier_services.base import BaseTierService
from app.services.ai.feature_gate import should_use_ai_in_flow as _ai_in_flow_enabled


class BasicTierService(BaseTierService):
    """No NL. AI in flow only when super admin has enabled AI module for testing."""

    @property
    def tier_name(self) -> str:
        return "basic"

    def should_use_nl_intents(self) -> bool:
        return False

    def should_use_ai_in_flow(self) -> bool:
        return _ai_in_flow_enabled(self.tenant)
