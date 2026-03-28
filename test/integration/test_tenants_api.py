# test/integration/test_tenants_api.py
import pytest
from fastapi.testclient import TestClient
from app_ref.main import app
from app_ref.services.auth.user_service import UserService
from app_ref.models.auth import UserCreate

client = TestClient(app)

def test_list_tenants_super_admin(mock_db):
    # Setup super admin
    user = UserService.create_user(UserCreate(
        email="super@test.com", password="pwd", full_name="Super Admin", tenant=None
    ))
    token, _ = UserService.login("super@test.com", "pwd")
    
    response = client.get("/admin/tenants", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_list_tenants_forbidden(mock_db):
    # Setup tenant admin
    UserService.create_user(UserCreate(
        email="admin@test.com", password="pwd", full_name="Admin", tenant="t1"
    ))
    token, _ = UserService.login("admin@test.com", "pwd")
    
    # Super admin endpoint called by tenant admin
    response = client.get("/admin/tenants", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
