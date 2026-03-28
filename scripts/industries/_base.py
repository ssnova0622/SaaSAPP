"""
Base constants and helpers for industry demo data.
Tenant ID convention: ss_business_{domain} e.g. ss_business_salon, ss_business_clinic.
"""
TENANT_PREFIX = "ss_business_"

DOMAINS = [
    "salon",
    "clinic",
    "gym",
    "school",
    "store",
    "camp",
    "car_showroom",
]


def get_tenant_id(domain: str) -> str:
    """Return tenant id for domain e.g. salon -> ss_business_salon."""
    d = (domain or "").strip().lower().replace(" ", "_")
    if not d:
        raise ValueError("domain is required")
    return f"{TENANT_PREFIX}{d}"


def get_domain_from_tenant_id(tenant_id: str) -> str | None:
    """Extract domain from tenant id e.g. ss_business_salon -> salon."""
    if not tenant_id or not tenant_id.startswith(TENANT_PREFIX):
        return None
    return tenant_id[len(TENANT_PREFIX):].strip() or None
