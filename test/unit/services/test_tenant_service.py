# test/unit/services/test_tenant_service.py
import pytest
from app_ref.services.tenant.tenant_service import TenantService
from app_ref.models.tenant import TenantCreate

def test_create_tenant_service(mock_db):
    data = TenantCreate(name="Test Tenant", code="ttenant")
    result = TenantService.create_tenant(data)
    assert result["code"] == "ttenant"
    assert result["id"] == "tenant_ttenant"

def test_create_duplicate_tenant_code(mock_db):
    data = TenantCreate(name="T1", code="dup")
    TenantService.create_tenant(data)
    with pytest.raises(ValueError, match="Tenant code already exists"):
        TenantService.create_tenant(data)

def test_get_tenant_service(mock_db):
    TenantService.create_tenant(TenantCreate(name="T1", code="t1"))
    tenant = TenantService.get_by_code("t1")
    assert tenant["name"] == "T1"
