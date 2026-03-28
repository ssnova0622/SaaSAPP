# test/integration/test_catalog_api.py
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
    # Ensure it's active as per ensure_tenant_active check
    from app_ref.repositories.tenant_repository import TenantRepository
    TenantRepository.update_by_code("t1", {"status": "active"})
    
    UserService.create_user(UserCreate(
        email="admin@t1.com", password="pwd", full_name="Admin", tenant="t1"
    ))
    token, _ = UserService.login("admin@t1.com", "pwd")
    return {"Authorization": f"Bearer {token}", "X-Tenant": "t1"}

def test_create_category_api(auth_header, mock_db):
    response = client.post(
        "/tenants/t1/catalog/categories",
        headers=auth_header,
        json={"tenant": "t1", "name": "New Cat", "slug": "new-cat"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Cat"

def test_list_categories_api(auth_header, mock_db):
    client.post(
        "/tenants/t1/catalog/categories",
        headers=auth_header,
        json={"tenant": "t1", "name": "C1", "slug": "c1"}
    )
    response = client.get("/tenants/t1/catalog/categories", headers=auth_header)
    assert response.status_code == 200
    assert len(response.json()) >= 1
