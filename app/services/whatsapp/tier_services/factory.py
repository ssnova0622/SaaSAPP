"""
Factory: return the correct tier service for a tenant (Basic, Enterprise, Pro).
Tier is determined by tenant plan (plan + modules + AI_ENABLED drive behavior inside each tier).
"""
from __future__ import annotations

from typing import Union
from app.services.whatsapp.tier_services.basic import BasicTierService
from app.services.whatsapp.tier_services.enterprise import EnterpriseTierService
from app.services.whatsapp.tier_services.pro import ProTierService
from app.services.ai.feature_gate import get_plan
from app.helpers.constants_plans import PLAN_BASIC, PLAN_PRO


def get_tier_service(tenant: str) -> Union[BasicTierService, EnterpriseTierService, ProTierService]:
    """Return the tier service for this tenant based on plan (Basic, Enterprise, or Pro)."""
    plan = get_plan(tenant)
    if plan == PLAN_BASIC:
        return BasicTierService(tenant)
    if plan == PLAN_PRO:
        return ProTierService(tenant)
    return EnterpriseTierService(tenant)
