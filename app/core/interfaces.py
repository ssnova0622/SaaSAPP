# app/core/interfaces.py
"""
Abstract interfaces for key dependencies. Use these for dependency injection
and to reduce tight coupling between services. Implementations can be
swapped in tests or for different runtimes.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class ITenantSettingsProvider(Protocol):
    """Provider of tenant settings. Implemented by TenantService."""

    @staticmethod
    def get_tenant_settings(tenant: str) -> Optional[Dict[str, Any]]:
        ...


class ITenantProvider(Protocol):
    """Provider of tenant existence and basic info."""

    @staticmethod
    def get_tenant(tenant: str) -> Optional[Dict[str, Any]]:
        ...

    @staticmethod
    def tenant_exists(tenant: str) -> bool:
        ...
