# test/unit/repositories/test_appointment_repository.py
import pytest
from datetime import datetime, timedelta, timezone
from app_ref.repositories.appointment_repository import AppointmentRepository

def test_create_appointment(mock_db):
    doc = {
        "id": "app1",
        "tenant": "t1",
        "staff_id": "s1",
        "start_at": datetime.now(timezone.utc),
        "end_at": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    result = AppointmentRepository.create(doc)
    assert result["id"] == "app1"
    assert "created_at" in result

def test_list_for_staff(mock_db):
    start = datetime(2025, 1, 1, 10, 0)
    end = datetime(2025, 1, 1, 11, 0)
    AppointmentRepository.create({
        "id": "app1", "tenant": "t1", "staff_id": "s1",
        "start_at": start, "end_at": end
    })
    
    # Within range
    appts = AppointmentRepository.list_for_staff("t1", "s1", datetime(2025, 1, 1), datetime(2025, 1, 2))
    assert len(appts) == 1
    
    # Outside range
    appts = AppointmentRepository.list_for_staff("t1", "s1", datetime(2025, 1, 2), datetime(2025, 1, 3))
    assert len(appts) == 0
