# test/unit/repositories/test_user_repository.py
import pytest
from app_ref.repositories.user_repository import UserRepository

def test_create_user(mock_db):
    doc = {"id": "u1", "email": "test@example.com", "role": "admin"}
    result = UserRepository.create(doc)
    assert result["email"] == "test@example.com"
    assert "created_at" in result

def test_get_by_email(mock_db):
    UserRepository.create({"id": "u1", "email": "test@example.com"})
    user = UserRepository.get_by_email("test@example.com")
    assert user is not None
    assert user["id"] == "u1"

def test_list_users_by_tenant(mock_db):
    UserRepository.create({"id": "u1", "email": "t1@ex.com", "tenant": "t1"})
    UserRepository.create({"id": "u2", "email": "t2@ex.com", "tenant": "t2"})
    
    t1_users = UserRepository.list(tenant="t1")
    assert len(t1_users) == 1
    assert t1_users[0]["tenant"] == "t1"
