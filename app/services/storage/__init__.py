"""
Domain storage package. Storage is composed from domain modules for maintainability.
Import Storage, Slot, Professional, Appointment, seed_demo_data, get_db from
app.services.storage_mongo for backward compatibility.
"""
from __future__ import annotations

from app.services.storage.models import Slot, Professional, Appointment
from app.services.storage.tenant_storage import TenantStorage
from app.services.storage.staff_storage import StaffStorage
from app.services.storage.service_storage import ServiceStorage

__all__ = [
    "Slot",
    "Professional",
    "Appointment",
    "TenantStorage",
    "StaffStorage",
    "ServiceStorage",
]
