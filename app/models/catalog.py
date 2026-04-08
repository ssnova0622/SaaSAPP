# app/models/catalog.py
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Service(BaseModel):
    tenant: str
    name: str
    description: Optional[str] = ""
    price: float = 0.0
    duration: int = 30
    active: bool = True
    created_at: Optional[Any] = None
    updated_at: Optional[Any] = None


class ServiceListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


class CategoryIn(BaseModel):
    name: str
    active: bool = True


class CategoryOut(CategoryIn):
    pass


class ProductIn(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    price: float = 0.0
    mrp: Optional[float] = None
    tax: Optional[float] = None

    unit: Optional[str] = None
    unit_conversions: Optional[List[Dict[str, Any]]] = None

    active: bool = True
    barcode: Optional[str] = None
    image_url: Optional[str] = None
    image_urls: Optional[List[str]] = None
    description: Optional[str] = None

    discount_type: Optional[str] = None
    discount_value: Optional[float] = None

    variants: Optional[List[Dict[str, Any]]] = None


class ProductOut(ProductIn):
    pass


class ProductListResponse(BaseModel):
    items: List[Dict[str, Any]]
    total: int
    page: int
    size: int


class InventoryUpsert(BaseModel):
    sku: str
    available_qty: float = 0.0


class CategoryPatch(BaseModel):
    active: bool


class ProductImportResult(BaseModel):
    total: int
    created: int
    updated: int
    failed: int
    errors: Optional[list] = None
