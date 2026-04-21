from __future__ import annotations
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Body, Query
from fastapi import UploadFile, File

from .deps import (get_current_user, ensure_tenant_active, ensure_module_enabled, ensure_capability_enabled,
                   ensure_tenant_scope)
from ..core.container import get_user_service
from ..services.store.facade import get_store_facade
from ..models.schemas import CategoryIn, CategoryOut, ProductIn, ProductOut, InventoryUpsert

router = APIRouter()


# ===== Categories =====

@router.get(
    "/tenants/{tenant}/catalog/categories",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def list_categories(tenant: str) -> List[Dict[str, Any]]:
    items = get_store_facade().categories.list_categories(tenant)
    user_ids = {c.get("created_by") for c in items if c.get("created_by")} | {c.get("updated_by") for c in items if
                                                                              c.get("updated_by")}
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    for c in items:
        c["created_by"] = user_names.get(c.get("created_by")) or c.get("created_by") or "system"
        c["updated_by"] = user_names.get(c.get("updated_by")) or c.get("updated_by") or "-"
    return items


@router.post(
    "/tenants/{tenant}/catalog/categories",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def create_or_update_category(tenant: str, body: CategoryIn, user: dict = Depends(get_current_user)) -> CategoryOut:
    user_id = user.get("sub") or user.get("email")
    try:
        out = get_store_facade().categories.upsert_category(tenant=tenant, name=body.name, active=bool(body.active),
                                                            user_id=user_id)
        user_ids = {out.get("created_by"), out.get("updated_by")} - {None}
        user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
        return CategoryOut(
            name=out["name"],
            active=out["active"],
            created_by=user_names.get(out.get("created_by")) or out.get("created_by") or "system",
            updated_by=user_names.get(out.get("updated_by")) or out.get("updated_by") or "-",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/tenants/{tenant}/catalog/categories/{name}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def patch_category(tenant: str, name: str, body: Dict[str, Any] = Body(...),
                   user: dict = Depends(get_current_user)) -> CategoryOut:
    user_id = user.get("sub") or user.get("email")
    active = body.get("active")
    if active is None:
        raise HTTPException(status_code=400, detail="active is required")
    try:
        out = get_store_facade().categories.upsert_category(tenant=tenant, name=name, active=bool(active),
                                                            user_id=user_id)
        user_ids = {out.get("created_by"), out.get("updated_by")} - {None}
        user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
        return CategoryOut(
            name=out["name"],
            active=out["active"],
            created_by=user_names.get(out.get("created_by")) or out.get("created_by") or "system",
            updated_by=user_names.get(out.get("updated_by")) or out.get("updated_by") or "-",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/tenants/{tenant}/catalog/categories/{name}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def delete_category(tenant: str, name: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    ok = get_store_facade().categories.delete_category(tenant=tenant, name=name, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}


# ===== Products =====

@router.get(
    "/tenants/{tenant}/catalog/products",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def list_products(
        tenant: str,
        search: Optional[str] = Query(default=None),
        category: Optional[str] = Query(default=None),
        active: Optional[bool] = Query(default=None),
        page: int = Query(default=1, ge=1),
        size: int = Query(default=50, ge=1, le=200),
        flatten_variants: bool = Query(default=False,
                                       description="If true, expand variants as separate rows with effective fields"),
) -> Dict[str, Any]:
    data = get_store_facade().products.list_products(tenant=tenant, search=search, category=category, active=active,
                                                     page=page, size=size, flatten_variants=flatten_variants)
    items = data.get("items") or []
    user_ids = {p.get("created_by") for p in items if p.get("created_by")} | {p.get("updated_by") for p in items if
                                                                              p.get("updated_by")}
    user_names = get_user_service().resolve_user_names(list(user_ids)) if user_ids else {}
    for p in items:
        p["created_by"] = user_names.get(p.get("created_by")) or p.get("created_by") or "system"
        p["updated_by"] = user_names.get(p.get("updated_by")) or p.get("updated_by") or "-"
    return data


@router.post(
    "/tenants/{tenant}/catalog/products",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def upsert_product(tenant: str, body: ProductIn, user: dict = Depends(get_current_user)) -> ProductOut:
    user_id = user.get("sub") or user.get("email")
    try:
        out = get_store_facade().products.upsert_product(tenant=tenant, product_data=body.model_dump(), user_id=user_id)
        return ProductOut(**out)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put(
    "/tenants/{tenant}/catalog/products/{sku}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def update_product(tenant: str, sku: str, body: ProductIn, user: dict = Depends(get_current_user)) -> ProductOut:
    user_id = user.get("sub") or user.get("email")
    try:
        data = body.model_dump()
        data["sku"] = sku
        out = get_store_facade().products.upsert_product(tenant=tenant, product_data=data, user_id=user_id)
        return ProductOut(**out)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Exact SKU lookup (base or variant) returning effective fields
@router.get(
    "/tenants/{tenant}/catalog/products/by-sku/{sku}",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def get_product_by_sku(tenant: str, sku: str) -> Dict[str, Any]:
    doc = get_store_facade().products.get_product_by_sku(tenant=tenant, sku=sku)
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return doc


@router.delete(
    "/tenants/{tenant}/catalog/products/{sku}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def delete_product(tenant: str, sku: str, user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    ok = get_store_facade().products.delete_product(tenant=tenant, sku=sku, user_id=user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


# ===== Inventory =====

@router.get(
    "/tenants/{tenant}/inventory/{sku}",
    dependencies=[Depends(get_current_user), Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def get_inventory(tenant: str, sku: str) -> Dict[str, Any]:
    return get_store_facade().inventory.get_inventory(tenant=tenant, sku=sku)


@router.put(
    "/tenants/{tenant}/inventory/{sku}",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
def set_inventory_qty(tenant: str, sku: str, body: InventoryUpsert, user: dict = Depends(get_current_user)) -> Dict[
    str, Any]:
    user_id = user.get("sub") or user.get("email")
    try:
        if (body.sku or sku) != sku:
            # align to path
            pass
        return get_store_facade().inventory.set_inventory_qty(tenant=tenant, sku=sku, qty=float(body.available_qty),
                                                              user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===== Products CSV Import =====

@router.post(
    "/tenants/{tenant}/catalog/products/import",
    dependencies=[Depends(ensure_tenant_scope()), Depends(ensure_tenant_active),
                  Depends(ensure_module_enabled("store")), Depends(ensure_capability_enabled("store.catalog"))],
)
async def import_products_csv(
    tenant: str,
    file: UploadFile = File(..., description="CSV file. Required columns: sku, name. Optional: category, price, mrp, tax, unit, active, barcode, description, discount_type, discount_value, margin_type, margin_value, minimum_selling_price"),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Bulk-import products from a CSV file.
    - If a product with the same SKU already exists it is updated (no duplicate created).
    - Returns counts of inserted / updated / failed rows and up to 20 error details.
    """
    import csv
    from io import StringIO

    user_id = user.get("sub") or user.get("email")
    try:
        content = (await file.read()).decode("utf-8-sig", errors="ignore")  # utf-8-sig strips BOM from Excel exports
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read file. Make sure it is a valid UTF-8 CSV.")

    reader = csv.DictReader(StringIO(content))
    # Normalise header names (strip spaces, lower-case) once
    raw_headers = reader.fieldnames or []
    header_map: Dict[str, str] = {h.strip().lower(): h for h in raw_headers}
    headers_norm = set(header_map.keys())

    if not {"sku", "name"}.issubset(headers_norm):
        raise HTTPException(status_code=400, detail="CSV must contain at least 'sku' and 'name' columns.")

    def _cell(row: Dict[str, Any], col: str) -> str:
        """Return stripped string value for a (possibly differently-cased) column, or ''."""
        orig = header_map.get(col)
        if orig is None:
            return ""
        return str(row.get(orig) or "").strip()

    def _float_or_none(val: str) -> Optional[float]:
        return float(val) if val not in ("", None) else None

    # Pre-fetch existing SKUs for this tenant so we can cheaply decide insert vs update
    products_col = get_store_facade().products._col()
    existing_skus: set = {
        doc["sku"] for doc in products_col.find({"tenant": tenant}, {"sku": 1, "_id": 0})
    }

    inserted = 0
    updated = 0
    failed = 0
    errors: List[Dict[str, Any]] = []

    for i, row in enumerate(reader, start=2):
        try:
            sku = _cell(row, "sku")
            name = _cell(row, "name")
            if not sku:
                raise ValueError("sku is empty")
            if not name:
                raise ValueError("name is empty")

            active_raw = _cell(row, "active")
            active = active_raw.lower() not in ("false", "0", "no") if active_raw else True

            disc_type = _cell(row, "discount_type") or None
            if disc_type and disc_type not in ("amount", "percent"):
                raise ValueError(f"discount_type must be 'amount' or 'percent', got '{disc_type}'")

            margin_type = _cell(row, "margin_type") or None
            if margin_type and margin_type not in ("amount", "percent"):
                raise ValueError(f"margin_type must be 'amount' or 'percent', got '{margin_type}'")

            data: Dict[str, Any] = {
                "sku": sku,
                "name": name,
                "category": _cell(row, "category") or None,
                "price": float(_cell(row, "price") or 0.0),
                "mrp": _float_or_none(_cell(row, "mrp")),
                "tax": _float_or_none(_cell(row, "tax")),
                "unit": _cell(row, "unit") or None,
                "barcode": _cell(row, "barcode") or None,
                "description": _cell(row, "description") or None,
                "active": active,
                "discount_type": disc_type,
                "discount_value": _float_or_none(_cell(row, "discount_value")),
                "margin_type": margin_type,
                "margin_value": _float_or_none(_cell(row, "margin_value")),
                "minimum_selling_price": _float_or_none(_cell(row, "minimum_selling_price")),
            }

            is_new = sku not in existing_skus
            get_store_facade().products.upsert_product(tenant=tenant, product_data=data, user_id=user_id)
            # Mark as known after first successful upsert (handles duplicate rows within same file)
            existing_skus.add(sku)

            if is_new:
                inserted += 1
            else:
                updated += 1
        except Exception as exc:
            failed += 1
            errors.append({"row": i, "sku": _cell(row, "sku") if row else "", "error": str(exc)})

    return {
        "inserted": inserted,
        "updated": updated,
        "failed": failed,
        "errors": errors[:20],  # cap to avoid huge responses
    }
