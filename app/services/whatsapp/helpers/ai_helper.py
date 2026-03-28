# app/services/whatsapp/helpers/ai_helper.py
from __future__ import annotations
from typing import Optional

try:
    from app.services.ai.ai_service import AiService as AIPredictor
except Exception:
    AIPredictor = None


def is_ai_enabled(tenant: str) -> bool:
    """Check if AI is enabled for this tenant (plan + modules; see feature_gate)."""
    from app.services.ai.feature_gate import is_ai_globally_enabled
    return is_ai_globally_enabled(tenant)


def ai_match_professional(tenant: str, query: str) -> Optional[str]:
    """Return best matching professional name using AI, if enabled."""
    if not AIPredictor or not is_ai_enabled(tenant):
        return None

    ai = AIPredictor()
    matches = ai.search_professionals(tenant, query)
    if matches:
        return matches[0].get("name")
    return None
