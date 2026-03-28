# test/unit/services/test_user_service.py
import pytest
from app_ref.services.auth.user_service import UserService
from app_ref.models.auth import UserCreate

def test_create_user_service(mock_db):
    data = UserCreate(email="user@test.com", password="pwd", full_name="Test User")
    result = UserService.create_user(data)
    assert result["email"] == "user@test.com"
    assert "password_hash" in result
    assert result["password_hash"] != "pwd"

def test_authenticate_success(mock_db):
    data = UserCreate(email="auth@test.com", password="pwd")
    UserService.create_user(data)
    user = UserService.authenticate("auth@test.com", "pwd")
    assert user is not None
    assert user["email"] == "auth@test.com"

def test_authenticate_fail(mock_db):
    data = UserCreate(email="auth@test.com", password="pwd")
    UserService.create_user(data)
    # Wrong password
    assert UserService.authenticate("auth@test.com", "wrong") is None
    # Wrong email
    assert UserService.authenticate("none@test.com", "pwd") is None
