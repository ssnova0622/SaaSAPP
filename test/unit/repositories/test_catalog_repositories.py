# test/unit/repositories/test_catalog_repositories.py
import pytest
from app_ref.repositories.catalog_category_repository import CategoryRepository
from app_ref.repositories.catalog_product_repository import ProductRepository
from app_ref.repositories.catalog_variant_repository import VariantRepository
from app_ref.repositories.catalog_inventory_repository import InventoryRepository

def test_category_repo(mock_db):
    CategoryRepository.create({"id": "c1", "tenant": "t1", "name": "Cat 1"})
    res = CategoryRepository.get("c1", "t1")
    assert res["name"] == "Cat 1"

def test_product_repo(mock_db):
    ProductRepository.create({"id": "p1", "tenant": "t1", "name": "Prod 1"})
    res = ProductRepository.get("p1", "t1")
    assert res["name"] == "Prod 1"

def test_variant_repo(mock_db):
    VariantRepository.create({"id": "v1", "tenant": "t1", "product_id": "p1", "name": "V1"})
    res = VariantRepository.get("v1", "t1")
    assert res["name"] == "V1"

def test_inventory_repo(mock_db):
    InventoryRepository.create({"id": "i1", "tenant": "t1", "product_id": "p1", "quantity": 10})
    res = InventoryRepository.get("i1", "t1")
    assert res["quantity"] == 10
