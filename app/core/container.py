# app/core/container.py
"""
Service container: single place to obtain core services. Reduces tight coupling
by centralizing dependency wiring. Use get_* functions in routers and services
instead of importing service classes directly where you need testability.

Usage:
  from app.core.container import get_tenant_service, get_user_service
  tenant_svc = get_tenant_service()
  tenant_svc.get_tenant_settings(tenant)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

if TYPE_CHECKING:
    from app.services.core.tenant_service import TenantService
    from app.services.core.customer_service import CustomerService
    from app.services.salon.staff_service import StaffService

# Optional overrides for testing (set to None in production)
_tenant_service_override: Optional[Any] = None
_user_service_override: Optional[Any] = None
_customer_service_override: Optional[Any] = None
_staff_service_override: Optional[Any] = None


def set_tenant_service_override(svc: Any) -> None:
    """Test helper: inject a mock tenant service."""
    global _tenant_service_override
    _tenant_service_override = svc


def set_user_service_override(svc: Any) -> None:
    """Test helper: inject a mock user service."""
    global _user_service_override
    _user_service_override = svc


def set_customer_service_override(svc: Any) -> None:
    """Test helper: inject a mock customer service."""
    global _customer_service_override
    _customer_service_override = svc


def set_staff_service_override(svc: Any) -> None:
    """Test helper: inject a mock staff service."""
    global _staff_service_override
    _staff_service_override = svc


def clear_overrides() -> None:
    """Test helper: clear all overrides."""
    global _tenant_service_override, _user_service_override, _customer_service_override, _staff_service_override
    _tenant_service_override = _user_service_override = _customer_service_override = _staff_service_override = None


def get_tenant_service() -> "TenantService":
    """Return the tenant service. Override in tests via set_tenant_service_override."""
    if _tenant_service_override is not None:
        return _tenant_service_override
    from app.services.core.tenant_service import TenantService
    return TenantService


def get_user_service():
    """Return the user service (Storage-backed adapter). Override in tests via set_user_service_override."""
    if _user_service_override is not None:
        return _user_service_override
    from app.services.core.user_storage_adapter import UserStorageAdapter
    return UserStorageAdapter


def get_customer_service() -> "CustomerService":
    """Return the customer service. Override in tests via set_customer_service_override."""
    if _customer_service_override is not None:
        return _customer_service_override
    from app.services.core.customer_service import CustomerService
    return CustomerService


def get_staff_service() -> "StaffService":
    """Return the staff service. Override in tests via set_staff_service_override."""
    if _staff_service_override is not None:
        return _staff_service_override
    from app.services.salon.staff_service import StaffService
    return StaffService


def get_appointment_service():
    """Return the appointment service (salon). Use in routers instead of Storage."""
    from app.services.salon.appointments.appointment_service import AppointmentService
    return AppointmentService


def get_reports_service():
    """Return the reports service (facade over reports_store + Storage analytics)."""
    from app.services.core.reports_facade import ReportsService
    return ReportsService


def get_salon_services():
    """Return the salon services (categories/services) for list/create/update/delete service definitions."""
    from app.services.salon.categories_service import CategoriesServices
    return CategoriesServices


def get_professional_service():
    """Return the professional service (salon) for professionals/slots."""
    from app.services.salon.professional_service import ProfessionalService
    return ProfessionalService


def get_slot_service():
    """Return the slot service (salon) for availability and set_slot_status."""
    from app.services.salon.slot_service import SlotService
    return SlotService


def get_ai_service():
    """Return the AI/analytics service (facade over Storage for events, predictions, insights)."""
    from app.services.core.ai_facade import AIService
    return AIService


def get_whatsapp_service():
    """Return the WhatsApp service (facade over Storage for sessions, menus, triggers)."""
    from app.services.core.whatsapp_facade import WhatsAppService
    return WhatsAppService


def get_db():
    """Return the database instance. Single place for DB access wiring."""
    from app.services.db import get_db as _get_db
    return _get_db()
