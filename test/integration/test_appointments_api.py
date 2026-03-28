# test/integration/test_appointments_api.py
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app_ref.main import app
from app_ref.services.auth.user_service import UserService
from app_ref.services.tenant.tenant_service import TenantService
from app_ref.services.core.staff_service import StaffService
from app_ref.repositories.service_repository import ServiceRepository
from app_ref.repositories.staff_schedule_repository import StaffScheduleRepository
from app_ref.models.auth import UserCreate
from app_ref.models.tenant import TenantCreate
from app_ref.models.staff import StaffCreate

client = TestClient(app)

@pytest.fixture
def auth_header(mock_db):
    TenantService.create_tenant(TenantCreate(name="T1", code="t1"))
    from app_ref.repositories.tenant_repository import TenantRepository
    TenantRepository.update_by_code("t1", {"status": "active"})
    
    UserService.create_user(UserCreate(
        email="admin@t1.com", password="pwd", full_name="Admin", tenant="t1"
    ))
    token, _ = UserService.login("admin@t1.com", "pwd")
    return {"Authorization": f"Bearer {token}", "X-Tenant": "t1"}

def test_create_appointment_api(auth_header, mock_db):
    tenant = "t1"
    # Setup Service
    ServiceRepository.create({
        "id": "svc1", 
        "tenant": tenant, 
        "duration_minutes": 30, 
        "name": "S1", 
        "price": 50,
        "currency": "USD" # Ensure model defaults match
    })
    
    # Setup Staff
    StaffService.create_staff(StaffCreate(tenant=tenant, name="Staff 1", role="stylist", email="s@t1.com", phone="123"))
    staff_id = list(mock_db.staff.find())[0]["id"]
    
    # Setup Schedule
    start_dt = datetime(2025, 1, 6, 10, 0) # Monday
    StaffScheduleRepository.create({
        "id": "sch1", "tenant": tenant, "staff_id": staff_id,
        "availability": [{"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}]
    })
    
    response = client.post(
        "/tenants/t1/appointments",
        headers=auth_header,
        json={
            "tenant": "t1",
            "customer_id": "c1",
            "service_id": "svc1",
            "staff_id": staff_id,
            "start_at": start_dt.isoformat(),
            "end_at": (start_dt + timedelta(minutes=30)).isoformat()
        }
    )
    assert response.status_code == 200
    assert response.json()["customer_id"] == "c1"

def test_list_appointments_api(auth_header, mock_db):
    response = client.get("/tenants/t1/appointments", headers=auth_header)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_appointment_with_customer_name_phone(auth_header, mock_db):
    """Create appointment with free-text customer name and phone (no customer_id); tenant from path."""
    from app_ref.repositories.professional_repository import ProfessionalRepository
    from app_ref.models.professional import DEFAULT_WORKING_HOURS

    tenant = "t1"
    ProfessionalRepository.col().insert_one({
        "id": "prof_t1_1",
        "tenant": tenant,
        "name": "Dr. Test",
        "active": True,
        "working_hours": DEFAULT_WORKING_HOURS,
    })
    start_dt = datetime(2025, 1, 6, 10, 0)
    end_dt = datetime(2025, 1, 6, 11, 0)

    response = client.post(
        "/tenants/t1/appointments",
        headers=auth_header,
        json={
            "customer_name": "John Doe",
            "customer_phone": "+91 9876543210",
            "staff_id": "prof_t1_1",
            "start_at": start_dt.isoformat(),
            "end_at": end_dt.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("customer_name") == "John Doe"
    assert data.get("customer_phone") == "+91 9876543210"
    assert data.get("staff_id") == "prof_t1_1"
