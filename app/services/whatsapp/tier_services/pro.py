"""
Pro tier: full AI + NL when AI module + AI_ENABLED + ai.whatsapp_intents.
When AI_ENABLED=false, behaves like Enterprise (limited AI, menu-based, no NL).
"""
from __future__ import annotations

from app.services.whatsapp.tier_services.base import BaseTierService
from app.services.ai.feature_gate import is_ai_nl_enabled, should_use_ai_in_flow as _ai_in_flow_enabled


class ProTierService(BaseTierService):
    """Full NL when AI enabled; when AI_ENABLED=false, limited AI like Enterprise."""

    @property
    def tier_name(self) -> str:
        return "pro"

    def should_use_nl_intents(self) -> bool:
        return is_ai_nl_enabled(self.tenant)

    def should_use_ai_in_flow(self) -> bool:
        return _ai_in_flow_enabled(self.tenant)

    def get_fallback_message(self) -> str:
        try:
            from app.services.ai.config_schema import get_effective_ai_config
            from app.core.container import get_tenant_service
            settings = get_tenant_service().get_tenant_settings(self.tenant) or {}
            config = get_effective_ai_config(settings)
            msg = (config.get("whatsapp_intent_fallback_message") or "").strip()
            if msg:
                return msg
        except Exception:
            pass
        return super().get_fallback_message()
