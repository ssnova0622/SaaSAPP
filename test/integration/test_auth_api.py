# test/integration/test_auth_api.py
import pytest
from fastapi.testclient import TestClient
from app_ref.main import app
from app_ref.services.auth.user_service import UserService
from app_ref.models.auth import UserCreate

client = TestClient(app)

def test_login_success(mock_db):
    # Setup user
    UserService.create_user(UserCreate(
        email="login@test.com", 
        password="pwd",
        full_name="Login User"
    ))
    
    # Attempt login
    response = client.post("/auth/login", json={
        "email": "login@test.com",
        "password": "pwd"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@test.com"

def test_login_failure(mock_db):
    response = client.post("/auth/login", json={
        "email": "wrong@test.com",
        "password": "password"
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"
