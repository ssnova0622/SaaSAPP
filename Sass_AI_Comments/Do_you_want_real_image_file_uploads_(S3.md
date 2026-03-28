### Great — here’s a concrete design with real uploads, both discount types, and variant SKUs

You confirmed:
- Images: real file uploads (not just URLs)
- Discounts: both percent and amount
- Inventory: variant SKUs (size/color variants), i.e., inventory per variant

Below is an end‑to‑end plan (backend + Admin UI) tailored to your repo. It’s incremental, so you can ship it in phases.

---

### High-level data model

- Product (parent) — common info: name, category, tax, brand, etc.
- Variant (child) — each variant has its own SKU, price, discount, images, and stock.
- Inventory — tracked per variant SKU.

Example document (backend JSON):
```json
{
  "product_id": "prod_1001",
  "name": "Shampoo",
  "category": "Hair Care",
  "active": true,
  "attributes": ["size", "color"],
  "variants": [
    {
      "sku": "SKU-1001-250ML",
      "attrs": { "size": "250ml" },
      "price": 199,
      "mrp": 249,
      "discount": { "type": "percent", "value": 10, "starts_at": null, "ends_at": null },
      "images": [
        { "url": "https://cdn.example.com/p/1001-1.jpg", "alt": "Front", "is_primary": true, "sort": 1 }
      ],
      "active": true
    },
    {
      "sku": "SKU-1001-500ML",
      "attrs": { "size": "500ml" },
      "price": 349,
      "mrp": 399,
      "discount": { "type": "amount", "value": 20 },
      "images": [],
      "active": true
    }
  ]
}
```
Inventory is stored per `sku` using your existing inventory endpoints (extend to support variant SKUs — same API shape).

---

### Backend: API design (additions)

1) Media upload (real files)
- Endpoint: `POST /tenants/{tenant}/media/upload`
- Auth: same as admin JWT; capability `media.upload` (configurable)
- Request: Multipart form (`file`, optional `folder`)
- Response: `{ url: string, width?: number, height?: number, size: number, mime: string }`
- Storage options:
  - S3/Compatible: use `boto3` and generate a unique key (`products/{tenant}/{yyyy}/{mm}/{uuid}.ext`)
  - Local dev: save to `app_static/uploads/...` and serve via static files router
- Validation: max size (e.g., 5 MB), allowlist MIME (`image/jpeg`, `image/png`, `image/webp`), image sniffing (Pillow) to prevent spoofing

2) Catalog model: products with variants
- New endpoints (tenant-scoped):
  - `GET /tenants/{tenant}/catalog/products` → list products (flatten variants optionally)
  - `POST /tenants/{tenant}/catalog/products` → create product with variants
  - `GET /tenants/{tenant}/catalog/products/{product_id}` → get one
  - `PUT /tenants/{tenant}/catalog/products/{product_id}` → update
  - `DELETE /tenants/{tenant}/catalog/products/{product_id}` → delete
  - Variant helpers (if you want separate routes):
    - `POST /tenants/{tenant}/catalog/products/{product_id}/variants` → add variant
    - `PUT /tenants/{tenant}/catalog/products/{product_id}/variants/{sku}` → update variant
    - `DELETE /tenants/{tenant}/catalog/products/{product_id}/variants/{sku}` → remove variant

3) Inventory (per variant SKU)
- Keep your existing:
  - `GET /tenants/{tenant}/inventory/{sku}` → `{ sku, available_qty }`
  - `PUT /tenants/{tenant}/inventory/{sku}` → `{ sku, available_qty }`
- Use variant `sku` values.

4) Discounts (both types)
- Schema for discount on each variant:
```json
{ "type": "percent" | "amount", "value": number, "starts_at?": string, "ends_at?": string }
```
- Server-side compute: `effective_price` included in read responses when discount is active.
- Validation: percent 0 < value ≤ 90; amount 0 < value < price; `starts_at <= ends_at`.

---

### Backend: implementation notes

- Schemas (Pydantic):
  - `ProductIn`/`ProductOut` → now include `attributes?: string[]` and `variants: Variant[]`
  - `Variant` model → `sku, attrs: Dict[str,string], price, mrp?, discount?, images?, active`
  - `ImageRef` model → `url, alt?, is_primary?, sort?`
  - Avoid breaking the existing single‑SKU API by supporting both shapes during migration (see Migration section)
- Persistence:
  - Store as a single document per product with embedded `variants` array (Mongo-friendly)
  - Indexes: `tenant+product_id`, `tenant+variants.sku`, `tenant+category`.
- Media:
  - If S3: environment vars (`S3_BUCKET`, `S3_REGION`, creds), set `Cache-Control` headers for CDN
  - If local: mount StaticFiles in FastAPI; generate absolute URL for `url`

---

### Admin UI: UX changes

One screen with sections/tabs:

- Product basics
  - `name`, `category`, `active`, optional shared `attributes` (like `size`, `color`) to guide variant creation

- Variants (table with inline edit + modal)
  - Columns: SKU, Attributes (chips), Price, MRP, Discount type/value, Effective Price (computed), Stock, Active, Images
  - Actions per row:
    - Edit (opens variant modal)
    - Manage Images (opens image manager)
    - Edit Stock (inline numeric) → calls inventory endpoint
  - Add Variant button → create SKU + set attrs/price/discount

- Variant modal (full detail)
  - Fields: `sku`, `attrs` (dynamic key/value from product attributes), `price`, `mrp`, `discount` (type/value/dates), `active`
  - Effective price preview (client-calculated)

- Image manager (per variant)
  - Drag & drop for multiple files → call `media/upload` for each
  - Thumbnails with: set primary, alt text, reorder (drag), delete

Validation in UI:
- Unique SKUs per product
- Discount guardrails (see backend)
- Stock: integer >= 0
- At least one primary image if images exist

---

### API contracts (examples)

1) Upload image
```
POST /tenants/acme/media/upload
Content-Type: multipart/form-data

file: <binary>
folder: products
```
Response
```json
{ "url": "https://cdn.example.com/acme/products/2025/12/uuid.jpg", "mime": "image/jpeg", "size": 183423, "width": 1000, "height": 1000 }
```

2) Create product with variants
```
POST /tenants/acme/catalog/products
```
Body
```json
{
  "name": "Shampoo",
  "category": "Hair Care",
  "active": true,
  "attributes": ["size"],
  "variants": [
    {
      "sku": "SKU-1001-250ML",
      "attrs": { "size": "250ml" },
      "price": 199,
      "mrp": 249,
      "discount": { "type": "percent", "value": 10 },
      "images": [ { "url": "https://cdn.../xx.jpg", "is_primary": true } ],
      "active": true
    }
  ]
}
```
Response
```json
{ "product_id": "prod_1001", ... }
```

3) Set inventory
```
PUT /tenants/acme/inventory/SKU-1001-250ML
{ "sku": "SKU-1001-250ML", "available_qty": 20 }
```

---

### WhatsApp actions (optional enhancements)

- Enhance `store.browse_catalog` and `store.check_product` to display variants:
  - Show primary image (URL) and list variant options with keys (1/2/3)
  - If Meta channel is used, send a product list with buttons for variants
- New action ideas:
  - `store.select_variant` — start a small FSM: choose variant → confirm → add to cart or proceed
  - `store.add_to_cart` — params `{ sku, qty }`

---

### Security & limits

- Upload: validate MIME and size; strip EXIF; reject SVG if not needed
- Rate-limit uploads per tenant/user
- Use unique file keys; avoid overwriting
- Consider virus scan (optional) or rely on image decoding as safety gate

---

### Migration plan (no downtime)

1) Phase 1 — Backend accepts new shape
- Add new product schema with `variants[]` but continue serving the old `Product` endpoints
- For old products (no variants): treat the single product as one implicit variant under the hood

2) Phase 2 — Admin UI
- Introduce Variants tab in `Products.tsx` (keep existing fields, map to first variant under the hood for old data)
- Add Image Manager + Discount fields; wire Upload API
- Bind Stock to variant SKU in the same dialog

3) Phase 3 — Cleanup
- Migrate existing products into `variants` structure (script)
- Switch list view to variants-aware cards/rows

---

### Next steps (I can produce exact code stubs)
- Backend
  - FastAPI route: `media/upload` (S3 or local)
  - Pydantic models: `ProductIn/Out`, `Variant`, `ImageRef`, `Discount`
  - Handlers for create/update product and variants
  - Extend inventory to variant SKUs (same endpoints)
- Admin UI
  - Update `catalog.ts` types and API functions
  - Update `Products.tsx` to add Variants table, Discount fields, and Image Manager
  - Wire uploads to the new endpoint

Tell me your storage preference for images (S3 vs local disk for dev). If S3, share whether you have bucket/credentials ready — I’ll provide the exact code snippets (Python FastAPI for upload + React for the uploader and forms).