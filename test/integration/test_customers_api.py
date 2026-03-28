# test/integration/test_customers_api.py
import pytest
from fastapi.testclient import TestClient
from app_ref.main import app
from app_ref.services.auth.user_service import UserService
from app_ref.services.tenant.tenant_service import TenantService
from app_ref.models.auth import UserCreate
from app_ref.models.tenant import TenantCreate

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


def test_create_customer_without_tenant_in_body(auth_header):
    """Create customer without sending tenant in body (tenant set from path in router)."""
    response = client.post(
        "/tenants/t1/customers",
        headers=auth_header,
        json={
            "name": "Jane Doe",
            "phone": "+91 9876543210",
            "email": "jane@example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["phone"] == "+91 9876543210"
    assert data.get("tenant") == "t1" or data.get("id", "").startswith("cust_")


def test_list_customers(auth_header):
    response = client.get("/tenants/t1/customers", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
