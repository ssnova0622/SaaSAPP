# app/services/whatsapp/helpers/phone_helper.py
from __future__ import annotations
from typing import Callable, Optional
from app.helpers.phone_util import PhoneUtil


def _default_country_code(tenant: str) -> Optional[str]:
    from app.core.container import get_tenant_service
    return get_tenant_service()._get_tenant_country_code(tenant)


def standardize_phone(
    tenant: str,
    phone: str,
    get_tenant_country_code: Optional[Callable[[str], Optional[str]]] = None,
) -> str:
    """Normalize phone using tenant country code. Optional provider for DI/testing."""
    get_cc = get_tenant_country_code or _default_country_code
    cc = get_cc(tenant)
    return PhoneUtil.normalize_e164_input(phone, cc) or phone
