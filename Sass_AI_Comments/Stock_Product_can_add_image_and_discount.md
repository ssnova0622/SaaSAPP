### Clarifying your request
You want the Product creation/edit screen to include, on the same screen:
- Product images (upload, preview, pick primary)
- Discounts (percent or fixed amount; optional start/end date)
- Available stock (current inventory quantity)

Below is a concrete design that fits your current project (back end + Admin UI) and can be implemented incrementally.

---

### What you have today (quick audit)
- Admin UI screen: `admin_ui/src/pages/Store/Products.tsx`
  - Form fields: `sku, name, category, price, mrp, tax, unit, active`
  - Inventory is managed via separate inline editor that calls `getInventory`/`setInventory`
- API types: `admin_ui/src/api/catalog.ts`
  - `Product` type mirrors backend product: does not include images or discount fields
  - Inventory has its own endpoint (`/inventory/{sku}`)

So, the UI shows price fields but no image/discount fields, and stock is not in the main dialog.

---

### Target UX (single product screen)
One dialog with tabs or collapsible sections:
- Basic Info: `SKU, Name, Category, Unit, Active`
- Pricing & Discount: `MRP, Price, Tax, Discount Type, Discount Value, Effective Dates, Auto-calc price`
- Inventory: `Available Stock` (bound to the inventory endpoint)
- Images: drag-and-drop uploader, image list with preview, primary flag, delete

Admins can complete everything in one save cycle.

---

### Data model changes (backend + API)
Add fields to `Product`:
- Images
  - `images?: { url: string; alt?: string; is_primary?: boolean; sort?: number }[]`
- Discount
  - `discount?: { type: 'percent' | 'amount'; value: number; starts_at?: string; ends_at?: string }`
- Optional convenience fields (derived on read):
  - `effective_price?: number` (server-calculated for listings)

Example Product JSON with new fields:
```json
{
  "sku": "SKU-1001",
  "name": "Shampoo 250ml",
  "category": "Hair Care",
  "price": 199,
  "mrp": 249,
  "tax": 18,
  "unit": "bottle",
  "active": true,
  "discount": { "type": "percent", "value": 10, "starts_at": "2025-12-05T00:00:00Z" },
  "images": [
    { "url": "https://cdn.example.com/p/sku-1001-1.jpg", "alt": "Front", "is_primary": true, "sort": 1 },
    { "url": "https://cdn.example.com/p/sku-1001-2.jpg", "alt": "Back", "sort": 2 }
  ]
}
```

Inventory remains separate but you can surface it in the dialog by calling inventory endpoints.

Server-side calculation for `effective_price` (if discount is active):
- If type = percent: `effective_price = round(price * (1 - value/100))`
- If type = amount: `effective_price = max(0, price - value)`
- Only apply when now is within `starts_at..ends_at` (if provided). Return this in GET responses for convenience.

---

### Admin UI changes (exact steps)
1) Extend the form type in `Products.tsx`:
```ts
type ProductForm = {
  sku: string
  name: string
  category?: string
  price: number
  mrp?: number
  tax?: number
  unit?: string
  active: boolean
  discount?: { type: 'percent'|'amount'; value: number; starts_at?: string; ends_at?: string }
  images?: { url: string; alt?: string; is_primary?: boolean; sort?: number }[]
  stockQty?: number // bind to inventory service
}
```

2) Add UI controls:
- Pricing & Discount section:
  - Dropdown: Discount Type (None | Percent | Amount)
  - Numeric input: Discount Value
  - Date/time pickers: Starts At, Ends At
  - Read-only: Effective Price (auto-computed client-side for preview)
- Inventory section:
  - Numeric input: Available Stock
  - On dialog open: call `getInventory(tenant, form.sku)` to prefill
  - On Save: after product save, call `setInventory(tenant, form.sku, form.stockQty ?? 0)`
- Images section:
  - Drag-and-drop or file input; after upload, show thumbnails
  - Allow setting `is_primary` and reordering (`sort`)

3) Image upload flow:
- Minimal option (fast): paste URL field for external images (no upload infra). Store `url` directly.
- Better option: add a small media API:
  - `POST /tenants/{tenant}/media/upload` → returns `{ url }` after uploading to S3/Cloud/Local
  - Use the returned `url` to push to `form.images`

4) Update save logic in `Products.tsx`:
- When creating new product: call `upsertProduct` with new fields `discount` and `images` (backend must accept extra fields)
- After product save succeeds: call `setInventory` with `stockQty`

5) List view improvements (optional):
- Show primary image thumbnail
- Show price with strikethrough MRP if discounted, and a badge like “-10%”
- Show available stock

---

### Backend changes (exact points)
- Schemas
  - Python model (`app/models/schemas.py`, `ProductIn`/`ProductOut`): add optional `images`, `discount` fields
  - Validate discount (`value >= 0`, `0 < value <= 100` for percent, `0 <= value < price` for amount) and date ranges (`starts_at <= ends_at`)
- Persistence layer
  - Update Mongo/DB product serializer to store these new fields
  - Consider indexing `active` and `category` as before
- Media endpoint (if you want uploads)
  - New route (FastAPI) to accept multipart file, store, and return URL
- Derived field
  - Compute `effective_price` in GET responses for convenience (or compute on client if you prefer)

No change needed for inventory endpoints — reuse `GET/PUT /inventory/{sku}` in the save flow.

---

### Validation rules (admin-friendly)
- Images: max 6 images; require 1 primary; allow reorder
- Discount:
  - If type is set, `value` is required and positive
  - Percent: 0 < value ≤ 90 (guardrails); Amount: 0 < value < price
  - Date range optional; if provided, must be valid and not in the past (soft warning)
- Stock: integer ≥ 0

---

### WhatsApp integration (nice-to-have)
- Enhance `store.browse_catalog` and `store.check_product` actions to include primary image and discounted price in replies:
  - “Shampoo 250ml — ₹199 (₹249, -20%)”
  - If Meta channel is used, consider interactive message with image thumbnail.

---

### Minimal incremental plan
1) Extend backend Product schema to accept `discount` and `images` (don’t break existing clients)
2) Update Admin UI form to show discount fields and an image URL list (no upload yet)
3) Bind stock field to existing inventory endpoints within the dialog save
4) Later add upload endpoint + drag-and-drop uploader

---

### Quick questions to tailor it
- Do you want real image file uploads (S3/local) or just paste URLs for now?
- Discount: percent only, or both percent and amount?
- Should discount have a schedule (start/end) or always-on?
- For inventory: do you need variants (size/color) later, or one SKU = one stock is enough?

Give me those preferences, and I’ll provide exact code snippets (backend schema updates + UI changes) aligned with your stack.