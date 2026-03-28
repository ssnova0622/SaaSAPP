### Variants (color/size) — Implementation plan

I’ve prepared a concrete plan to add product variants (e.g., color/size) across backend, admin UI, and the Carts flow. Please review and confirm so I can start implementing.

#### 1) Data model and rules
- Add `variants[]` on a product. Each variant has:
  - `variant_sku` (unique per tenant)
  - `attributes` object (e.g., `{ color: "Red", size: "M" }`)
  - Optional overrides: `price`, `mrp`, `tax`, `discount_type` (`amount|percent`), `discount_value`, `image_url`, `active`
- Purchasing rules:
  - If a product has variants, customers add the variant SKU to cart (not the base SKU).
  - If no variants, the base SKU remains purchasable (current behavior).
- Inventory: tracked by the `sku` string as today. For variants, use `variant_sku` as the SKU for stock.

#### 2) Backend changes (schemas + storage)
- `app/models/schemas.py`:
  - Add a `Variant` Pydantic model and extend `ProductIn/ProductOut` with `variants: list[Variant] = []`.
  - Validate: unique `variant_sku` within the product, non-empty attributes, allowed discount types.
- `app/services/storage_mongo.py`:
  - Persist `variants` in `products` documents; enforce tenant-wide uniqueness across all base SKUs and variant SKUs (no collisions with other products or their variants).
  - Add `get_product_by_sku(tenant, sku)` to resolve either a base product or a variant; when variant, compute “effective” fields by applying variant overrides, else inherit from base.
  - Keep inventory methods unchanged (they already work by SKU string); we’ll just call them with `variant_sku` when variants exist.
- `app/routers/catalog.py`:
  - Add `GET /tenants/{tenant}/catalog/products/by-sku/{sku}` to return the effective product/variant view (with final price/discount/image).
  - Optionally extend `GET /catalog/products` with `flatten_variants=true` to include each variant as a row (useful for Autocomplete).

#### 3) Admin UI — Products page
- Add a “Variants” section to the create/edit dialog:
  - Table with rows: `variant_sku`, `color`, `size` (as common attributes; also allow custom attribute key/value pairs), `active`.
  - Optional overrides: price/mrp/tax/discount/image.
  - Stock per variant: inline “Edit Stock” should target `variant_sku`.
- UX rules:
  - When variants exist, hide base product’s stock and clarify that the top-level price is the default; variants can override as needed.

#### 4) Admin UI — Carts page
- Update the SKU Autocomplete to search base products and their variants. Display variant options like:
  - `tee123-red-m — T-Shirt (Color: Red, Size: M)` with variant image.
- Selection logic:
  - If the chosen product has variants, force selection of a variant (don’t allow adding the base SKU).
  - Compute price from variant override or fall back to base discount rules; set cart line `sku = variant_sku` and `price_snapshot = computed price`.

#### 5) Pricing logic consistency
- Precedence: variant fields override base; if variant lacks a field (e.g., discount), inherit from base.
- Final unit price: same formula as today, applied to the chosen price (variant or base):
  - amount: `max(0, price - discount_value)`
  - percent: `max(0, price - price*(discount_value/100))`

#### 6) Validation and integrity
- Tenant-wide uniqueness across all SKUs (base and variant SKUs).
- Attributes non-empty, string values, and limited count (e.g., up to 5 keys) to avoid misuse.
- Clear error messages for collisions or invalid payloads.

#### 7) Backward compatibility
- Existing products (no variants) keep working as-is; no migrations required.
- Inventory remains per-SKU. For variantized products, stock is managed on variant SKUs.

#### 8) Verification
- Create a product with color/size variants, set different prices/images, set stock per variant.
- In Carts, select a variant via Autocomplete, observe correct `price_snapshot` and line total.
- Checkout flow remains unchanged.

### Questions to confirm before I implement
1) Attributes: Is it sufficient to start with `color` and `size`, plus a flexible `attributes` map for other keys? Or strictly only `color` and `size` for now?
2) Inheritance: Should variants inherit all base fields by default and only override what’s provided? (Recommended.)
3) UI scope: Do you want CSV import/export for variants now, or later?
4) Autocomplete: Should we list both base and variants, or only variants when a product has variants? (I propose: show only variants to prevent adding base SKU by mistake.)

If you approve this plan (with any answers/changes to the questions), I’ll start implementing backend schema + storage + the by-SKU API first, then the Products UI variants section, and finally make the Carts Autocomplete variant-aware.