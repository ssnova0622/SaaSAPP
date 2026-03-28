# test/unit/repositories/test_tenant_repository.py
import pytest
from app_ref.repositories.tenant_repository import TenantRepository

def test_create_tenant(mock_db):
    doc = {"id": "t1", "name": "Tenant 1", "active": True}
    result = TenantRepository.create(doc)
    assert result["id"] == "t1"
    assert "created_at" in result
    assert "updated_at" in result

def test_get_tenant(mock_db):
    TenantRepository.create({"id": "t1", "name": "Tenant 1"})
    tenant = TenantRepository.get("t1")
    assert tenant is not None
    assert tenant["name"] == "Tenant 1"

def test_update_tenant(mock_db):
    TenantRepository.create({"id": "t1", "name": "Tenant 1"})
    updated = TenantRepository.update("t1", {"name": "New Name"})
    assert updated["name"] == "New Name"
    
    tenant = TenantRepository.get("t1")
    assert tenant["name"] == "New Name"

def test_list_tenants(mock_db):
    TenantRepository.create({"id": "t1", "name": "T1"})
    TenantRepository.create({"id": "t2", "name": "T2"})
    tenants = TenantRepository.list()
    assert len(tenants) == 2
