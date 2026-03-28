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
async def import_products_csv(tenant: str, file: UploadFile = File(...,
                                                                   description="CSV with headers: sku,name,category,price,mrp,tax,unit,active"),
                              user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("email")
    try:
        content = (await file.read()).decode("utf-8", errors="ignore")
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to read CSV file")
    import csv
    from io import StringIO

    reader = csv.DictReader(StringIO(content))
    required = {"sku", "name"}
    headers = set([h.strip().lower() for h in (reader.fieldnames or [])])
    if not required.issubset(headers):
        raise HTTPException(status_code=400, detail="CSV must include at least 'sku' and 'name' headers")

    inserted = 0
    updated = 0
    failed = 0
    errors: list[dict[str, Any]] = []

    for i, row in enumerate(reader, start=2):
        try:
            sku = str(row.get("sku") or "").strip()
            name = str(row.get("name") or "").strip()
            if not sku or not name:
                raise ValueError("Missing sku or name")
            data: Dict[str, Any] = {
                "sku": sku,
                "name": name,
                "category": (str(row.get("category") or "").strip() or None),
                "price": float(row.get("price") or 0.0),
                "mrp": (float(row.get("mrp")) if (row.get("mrp") not in (None, "")) else None),
                "tax": (float(row.get("tax")) if (row.get("tax") not in (None, "")) else None),
                "unit": (str(row.get("unit") or "").strip() or None),
                "active": (str(row.get("active") or "true").strip().lower() not in ("false", "0", "no")),
            }
            # Detect insert vs update by checking presence (simple approach: try to upsert; count as insert if prior not found)
            before = get_store_facade().products.list_products(tenant=tenant, search=sku, page=1, size=1)
            get_store_facade().products.upsert_product(tenant=tenant, product_data=data, user_id=user_id)
            after = get_store_facade().products.list_products(tenant=tenant, search=sku, page=1, size=1)
            if before["total"] == 0 and after["total"] >= 1:
                inserted += 1
            else:
                updated += 1
        except Exception as e:
            failed += 1
            errors.append({"row": i, "error": str(e)})

    # cap errors output
    if len(errors) > 20:
        errors = errors[:20]
    return {"inserted": inserted, "updated": updated, "failed": failed, "errors": errors}
