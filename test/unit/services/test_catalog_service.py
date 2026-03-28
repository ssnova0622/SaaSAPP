# test/unit/services/test_catalog_service.py
import pytest
from app_ref.services.catalog.category_service import CategoryService
from app_ref.services.catalog.product_service import ProductService
from app_ref.models.catalog import CategoryCreate, ProductCreate

def test_create_category(mock_db):
    data = CategoryCreate(tenant="t1", name="Electronics", slug="elec")
    res = CategoryService.create_category(data)
    assert res["name"] == "Electronics"
    assert res["tenant"] == "t1"

def test_create_product(mock_db):
    data = ProductCreate(
        tenant="t1", name="Phone", slug="phone", price=999.0, currency="USD"
    )
    res = ProductService.create_product(data)
    assert res["name"] == "Phone"
    assert res["price"] == 999.0
