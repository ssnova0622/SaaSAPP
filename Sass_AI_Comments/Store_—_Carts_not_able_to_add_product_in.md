### Store — Carts: not able to add product to cart

Here’s how it currently works and the common reasons an item “doesn’t get added.”

#### How to add items (current flow)
1. Go to Store → Carts (`admin_ui/src/pages/Store/Carts.tsx`).
2. Enter the customer phone number and click “Load”. This loads or creates a cart for that phone.
3. Click “Add” to insert a new row (defaults: `qty=1`, `price=0`).
4. Fill SKU (e.g., `apple-1kg`), adjust `Qty` (must be > 0), and optionally set `Price`.
5. Click “Save cart”.

After saving, reloading the cart should show your line(s).

#### Why your item might disappear or “not add”
- Qty is blank or 0: The backend sanitizes items and removes any line with `qty <= 0`.
  - Code: `Storage.put_cart` in `app/services/storage_mongo.py` filters out items with `qty <= 0` (lines ~939–943). If you clear the Qty field (empty → `Number('')` → 0), the line will be dropped on save.
- SKU left empty: Empty SKUs are also dropped by the backend (lines ~936–939).
- Not clicking Save: The UI shows items locally; they persist only after “Save cart”.
- No tenant/phone: Save is disabled if tenant or phone is missing.
- Capability/module not enabled: The cart endpoints require module+capability guards.
  - Router: `app/routers/store.py`
    - `GET/PUT /tenants/{tenant}/carts/{phone}` require `ensure_module_enabled("store")` and `ensure_capability_enabled("store.orders")`.
  - If not enabled, you’ll see an error like 403 or “Failed to save cart” in the UI.

#### Quick checklist
- Enter phone and click “Load” before adding lines.
- Ensure each line has:
  - `SKU` not empty
  - `Qty` > 0 (don’t leave it blank; blank becomes 0)
  - `Price` can be 0 if you want (allowed)
- Click “Save cart”.
- If you get an error banner, tell me the exact message.
- Verify the tenant has the capability `store.orders` and module `store` enabled.

#### Useful references
- UI: `admin_ui/src/pages/Store/Carts.tsx`
  - `addRow()` starts with `{ sku:'', qty:1, price_snapshot:0 }` (so qty defaults to 1).
- Backend sanitization: `app/services/storage_mongo.py`
  - Drops lines with empty `sku` or `qty <= 0` and recalculates subtotal.
- Endpoints: `app/routers/store.py`
  - `GET /tenants/{tenant}/carts/{phone}`
  - `PUT /tenants/{tenant}/carts/{phone}`
  - `POST /tenants/{tenant}/carts/{phone}/checkout`

#### If you want it to be easier
I can implement any (or all) of these improvements:
- Auto-fill price from product catalog on SKU input (apply product discount rules automatically).
- SKU selector with search (instead of free-text SKU), pulling from `/catalog/products`.
- Client-side validation to prevent saving with blank qty/SKU.
- “Add to cart” button from the Products list for a given phone (quick POS action).

Would you like me to add SKU search+auto-price and validation to the Carts page, or add per-product “Add to cart” actions on the Products page? If you’re seeing an error banner, please share the exact text so I can pinpoint the cause quickly.