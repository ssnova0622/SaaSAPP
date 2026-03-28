# test/unit/services/test_appointment_service.py
import pytest
from datetime import datetime, timedelta
from app_ref.services.appointments.appointment_service import AppointmentService
from app_ref.repositories.service_repository import ServiceRepository
from app_ref.repositories.staff_schedule_repository import StaffScheduleRepository
from app_ref.models.appointments import AppointmentCreate

def test_create_appointment_success(mock_db):
    tenant = "t1"
    staff_id = "s1"
    service_id = "svc1"
    
    # Setup service
    ServiceRepository.create({"id": service_id, "tenant": tenant, "duration_minutes": 30, "name": "S1", "price": 50})
    
    # Setup schedule (Monday)
    StaffScheduleRepository.create({
        "id": "sch1", "tenant": tenant, "staff_id": staff_id,
        "availability": [{"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}]
    })
    
    # Create appointment on a Monday (2025-01-06 is a Monday)
    start_at = datetime(2025, 1, 6, 10, 0)
    end_at = start_at + timedelta(minutes=30)
    
    data = AppointmentCreate(
        tenant=tenant, customer_id="c1", service_id=service_id, 
        staff_id=staff_id, start_at=start_at, end_at=end_at
    )
    
    res = AppointmentService.create_appointment(data)
    assert res["id"].startswith("apt_")
    assert res["customer_id"] == "c1"

def test_create_appointment_staff_unavailable(mock_db):
    tenant = "t1"
    staff_id = "s1"
    service_id = "svc1"
    ServiceRepository.create({"id": service_id, "tenant": tenant, "duration_minutes": 30, "name": "S1", "price": 50})
    
    # Sunday (dow=6)
    start_at = datetime(2025, 1, 5, 10, 0)
    end_at = start_at + timedelta(minutes=30)
    
    data = AppointmentCreate(
        tenant=tenant, customer_id="c1", service_id=service_id, 
        staff_id=staff_id, start_at=start_at, end_at=end_at
    )
    
    with pytest.raises(ValueError, match="Staff not available"):
        AppointmentService.create_appointment(data)
