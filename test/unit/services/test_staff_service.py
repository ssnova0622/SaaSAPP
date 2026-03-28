# test/unit/services/test_staff_service.py
import pytest
from app_ref.services.core.staff_service import StaffService
from app_ref.models.staff import StaffCreate

def test_create_staff(mock_db):
    data = StaffCreate(tenant="t1", name="Staff 1", role="stylist", phone="123", email="s1@t1.com")
    res = StaffService.create_staff(data)
    assert res["name"] == "Staff 1"
    assert res["tenant"] == "t1"

def test_list_staff(mock_db):
    data = StaffCreate(tenant="t1", name="S1", role="r1", phone="1", email="e1")
    StaffService.create_staff(data)
    
    res = StaffService.list_staff("t1", active=None, page=1, size=10)
    assert res["total"] == 1
    assert len(res["items"]) == 1
