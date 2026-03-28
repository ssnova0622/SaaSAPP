# app/services/store/products_service.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.helpers.date_utils import utcnow
from app.services.db import get_db
from app.services.store.helpers.validation_helper import StoreValidationHelper, StoreValidationError


class ProductService:
    @staticmethod
    def _col():
        return get_db().get_collection("products")

    # ---------------- Catalog / Products ----------------

    @classmethod
    def list_products(
        cls,
        tenant: str,
        search: Optional[str] = None,
        category: Optional[str] = None,
        active: Optional[bool] = None,
        page: int = 1,
        size: int = 50,
        flatten_variants: bool = False,
    ) -> Dict[str, Any]:
        col = cls._col()
        q: Dict[str, Any] = {"tenant": tenant}

        if search:
            q["$or"] = [
                {"sku": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}},
                {"variants.variant_sku": {"$regex": search, "$options": "i"}},
            ]
        if category:
            q["category"] = category
        if active is True:
            q["active"] = True
        elif active is False:
            q["active"] = False

        page = max(1, int(page or 1))
        size = max(1, min(200, int(size or 50)))
        skip = (page - 1) * size

        total = col.count_documents(q)
        items: List[Dict[str, Any]] = []

        for d in col.find(q).sort("name", 1).skip(skip).limit(size):
            row = dict(d)
            row.pop("_id", None)
            row["active"] = bool(row.get("active", True))
            if "minimum_selling_price" not in row and row.get("final_price") is not None:
                row["minimum_selling_price"] = row["final_price"]
            row.pop("final_price", None)

            if flatten_variants and row.get("variants"):
                # Include base product (single SKU) plus each variant as separate row
                items.append(row)
                items.extend(cls._flatten_variants_row(tenant, row))
            else:
                items.append(row)

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    def _flatten_variants_row(tenant: str, row: Dict[str, Any]) -> List[Dict[str, Any]]:
        base_price = float(row.get("price", 0.0))
        base_mrp = row.get("mrp")
        base_tax = row.get("tax")
        base_disc_t = row.get("discount_type")
        base_disc_v = row.get("discount_value")

        out: List[Dict[str, Any]] = []
        for v in (row.get("variants") or []):
            sku_v = str((v.get("variant_sku") or "")).strip()
            if not sku_v:
                continue
            var_item = {
                "tenant": tenant,
                "sku": sku_v,
                "name": row.get("name"),
                "category": row.get("category"),
                "price": float(v.get("price", base_price)) if (v.get("price") is not None) else float(base_price),
                "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else base_mrp),
                "tax": (float(v.get("tax")) if v.get("tax") is not None else base_tax),
                "unit": row.get("unit"),
                "unit_conversions": row.get("unit_conversions") or [],
                "active": bool(v.get("active", True) and row.get("active", True)),
                "image_url": (v.get("image_url") or row.get("image_url")),
                "discount_type": (v.get("discount_type") if v.get("discount_type") is not None else base_disc_t),
                "discount_value": (
                    float(v.get("discount_value")) if v.get("discount_value") is not None else base_disc_v
                ),
                "minimum_selling_price": row.get("minimum_selling_price") or row.get("final_price"),
                "final_selling_price": row.get("final_selling_price"),
                "margin_type": row.get("margin_type"),
                "margin_value": row.get("margin_value"),
                "attributes": (v.get("attributes") or {}),
            }
            out.append(var_item)
        return out

    @classmethod
    def upsert_product(
        cls,
        tenant: str,
        product_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        col = cls._col()

        sku = StoreValidationHelper.require_non_empty_str(product_data.get("sku"), "sku")
        name = StoreValidationHelper.require_non_empty_str(product_data.get("name"), "name")

        now = utcnow()
        payload: Dict[str, Any] = {
            "tenant": tenant,
            "sku": sku,
            "name": name,
            "category": (product_data.get("category") or None),
            "price": float(product_data.get("price", 0.0)),
            "mrp": float(product_data.get("mrp", 0.0)) if product_data.get("mrp") is not None else None,
            "tax": float(product_data.get("tax", 0.0)) if product_data.get("tax") is not None else None,
            "unit": (product_data.get("unit") or None),
            "unit_conversions": (product_data.get("unit_conversions") or []),
            "active": bool(product_data.get("active", True)),
            "barcode": (product_data.get("barcode") or None),
            "image_url": (product_data.get("image_url") or None),
            "discount_type": (product_data.get("discount_type") or None),
            "discount_value": (
                float(product_data.get("discount_value"))
                if product_data.get("discount_value") is not None
                else None
            ),
            "minimum_selling_price": (
                float(product_data["minimum_selling_price"])
                if product_data.get("minimum_selling_price") is not None
                else (float(product_data["final_price"]) if product_data.get("final_price") is not None else None)
            ),
            "final_selling_price": (
                float(product_data["final_selling_price"])
                if product_data.get("final_selling_price") is not None
                else None
            ),
            "margin_type": (product_data.get("margin_type") or None),
            "margin_value": (
                float(product_data["margin_value"])
                if product_data.get("margin_value") is not None
                else None
            ),
            "updated_at": now,
            "updated_by": user_id,
        }

        existing = col.find_one({"tenant": tenant, "sku": sku})
        if not existing:
            payload["created_at"] = now
            payload["created_by"] = user_id

        disc_t = payload.get("discount_type")
        if disc_t not in (None, "amount", "percent"):
            raise StoreValidationError("discount_type must be one of: amount, percent")
        if disc_t is None:
            payload["discount_value"] = None

        # MSP (minimum_selling_price): Cost + margin (markup), or client value when margin not set
        margin_t = payload.get("margin_type")
        margin_v = payload.get("margin_value")
        if margin_t not in (None, "percent", "amount"):
            raise StoreValidationError("margin_type must be one of: percent, amount")
        if margin_t and margin_v is not None:
            cost = float(payload.get("price", 0.0))
            if margin_t == "percent":
                payload["minimum_selling_price"] = max(0.0, cost + (cost * float(margin_v) / 100.0))
            else:
                payload["minimum_selling_price"] = max(0.0, cost + float(margin_v))
        elif payload.get("minimum_selling_price") is not None:
            payload["minimum_selling_price"] = max(0.0, float(payload["minimum_selling_price"]))

        # Final selling price = Selling Price − Discount + VAT (stored for offer/cart checks)
        selling_base = float(payload.get("mrp") or payload.get("price", 0.0))
        after_discount = selling_base
        if disc_t == "amount":
            after_discount = max(0.0, selling_base - float(payload.get("discount_value") or 0))
        elif disc_t == "percent":
            after_discount = max(0.0, selling_base - (selling_base * (float(payload.get("discount_value") or 0) / 100.0)))
        tax_pct = float(payload.get("tax") or 0) / 100.0
        payload["final_selling_price"] = round(after_discount * (1.0 + tax_pct), 2)

        conflict_vs = col.find_one(
            {
                "tenant": tenant,
                "variants.variant_sku": sku,
                "sku": {"$ne": sku},
            }
        )
        if conflict_vs:
            raise StoreValidationError("SKU already exists as a variant on another product")

        payload["variants"] = cls._build_variant_docs(col, tenant, sku, product_data.get("variants"))

        col.update_one({"tenant": tenant, "sku": sku}, {"$set": payload}, upsert=True)
        doc = col.find_one({"tenant": tenant, "sku": sku}) or payload
        out = dict(doc)
        out.pop("_id", None)
        out["active"] = bool(out.get("active", True))
        return out

    @staticmethod
    def _build_variant_docs(
        col,
        tenant: str,
        base_sku: str,
        variants_raw: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        if not variants_raw:
            return []

        variant_docs: List[Dict[str, Any]] = []
        seen_vs: set[str] = set()

        for v in variants_raw or []:
            if not isinstance(v, dict):
                continue
            vs = StoreValidationHelper.require_non_empty_str(v.get("variant_sku"), "variant_sku")
            if vs == base_sku:
                raise StoreValidationError("variant_sku cannot be same as base sku")
            if vs in seen_vs:
                raise StoreValidationError(f"Duplicate variant_sku '{vs}' in payload")
            seen_vs.add(vs)

            attrs = v.get("attributes") or {}
            if not isinstance(attrs, dict) or len(attrs.keys()) == 0:
                raise StoreValidationError("variant.attributes must be a non-empty object")

            disc_t = v.get("discount_type")
            if disc_t not in (None, "amount", "percent"):
                raise StoreValidationError("variant.discount_type must be one of: amount, percent")

            variant_docs.append(
                {
                    "variant_sku": vs,
                    "attributes": {str(k): str(attrs[k]) for k in attrs.keys()},
                    "price": (float(v.get("price")) if v.get("price") is not None else None),
                    "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else None),
                    "tax": (float(v.get("tax")) if v.get("tax") is not None else None),
                    "discount_type": disc_t,
                    "discount_value": (
                        float(v.get("discount_value")) if v.get("discount_value") is not None else None
                    ),
                    "image_url": (v.get("image_url") or None),
                    "active": bool(v.get("active", True)),
                }
            )

        if variant_docs:
            var_skus = [v["variant_sku"] for v in variant_docs]
            conflict = col.find_one(
                {
                    "tenant": tenant,
                    "$or": [
                        {"sku": {"$in": var_skus}},
                        {"variants.variant_sku": {"$in": var_skus}},
                    ],
                }
            )
            if conflict and conflict.get("sku") != base_sku:
                raise StoreValidationError("One or more variant_sku values already exist on another product")

        return variant_docs

    @classmethod
    def get_product_by_sku(cls, tenant: str, sku: str) -> Optional[Dict[str, Any]]:
        col = cls._col()
        sku_n = str((sku or "")).strip()
        row = col.find_one({"tenant": tenant, "$or": [{"sku": sku_n}, {"variants.variant_sku": sku_n}]})
        if not row:
            return None

        if row.get("sku") == sku_n:
            out = dict(row)
            out.pop("_id", None)
            if "minimum_selling_price" not in out and out.get("final_price") is not None:
                out["minimum_selling_price"] = out["final_price"]
            out.pop("final_price", None)
            return out

        v = next((x for x in (row.get("variants") or []) if x.get("variant_sku") == sku_n), None)
        if not v:
            return None

        base_price = float(row.get("price", 0.0))
        base_mrp = row.get("mrp")
        base_tax = row.get("tax")
        base_disc_t = row.get("discount_type")
        base_disc_v = row.get("discount_value")
        base_img = row.get("image_url")

        eff = {
            "tenant": tenant,
            "sku": sku_n,
            "base_sku": row.get("sku"),
            "name": row.get("name"),
            "category": row.get("category"),
            "attributes": v.get("attributes") or {},
            "price": float(v.get("price", base_price)) if (v.get("price") is not None) else float(base_price),
            "mrp": (float(v.get("mrp")) if v.get("mrp") is not None else base_mrp),
            "tax": (float(v.get("tax")) if v.get("tax") is not None else base_tax),
            "unit": row.get("unit"),
            "unit_conversions": row.get("unit_conversions") or [],
            "active": bool(v.get("active", True) and row.get("active", True)),
            "image_url": (v.get("image_url") or base_img),
            "discount_type": (v.get("discount_type") if v.get("discount_type") is not None else base_disc_t),
            "discount_value": (
                float(v.get("discount_value")) if v.get("discount_value") is not None else base_disc_v
            ),
            "minimum_selling_price": row.get("minimum_selling_price") or row.get("final_price"),
            "final_selling_price": row.get("final_selling_price"),
            "margin_type": row.get("margin_type"),
            "margin_value": row.get("margin_value"),
        }
        return eff

    @classmethod
    def delete_product(cls, tenant: str, sku: str, user_id: Optional[str] = None) -> bool:
        col = cls._col()
        res = col.delete_one({"tenant": tenant, "sku": sku})
        return res.deleted_count > 0
