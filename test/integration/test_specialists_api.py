# test/integration/test_specialists_api.py
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


def test_list_specialists_empty(auth_header):
    response = client.get("/tenants/t1/specialists", headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 0


def test_create_and_list_specialist(auth_header):
    response = client.post(
        "/tenants/t1/specialists",
        headers=auth_header,
        json={"tenant": "t1", "name": "Dental", "code": "dental", "active": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Dental"
    assert data["code"] == "dental"
    assert "id" in data

    response2 = client.get("/tenants/t1/specialists", headers=auth_header)
    assert response2.status_code == 200
    assert response2.json()["total"] >= 1


def test_get_update_delete_specialist(auth_header):
    create_resp = client.post(
        "/tenants/t1/specialists",
        headers=auth_header,
        json={"tenant": "t1", "name": "Ortho", "active": True},
    )
    assert create_resp.status_code == 200
    sid = create_resp.json()["id"]

    get_resp = client.get(f"/tenants/t1/specialists/{sid}", headers=auth_header)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Ortho"

    patch_resp = client.patch(
        f"/tenants/t1/specialists/{sid}",
        headers=auth_header,
        json={"name": "Orthopedic"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Orthopedic"

    del_resp = client.delete(f"/tenants/t1/specialists/{sid}", headers=auth_header)
    assert del_resp.status_code == 200
