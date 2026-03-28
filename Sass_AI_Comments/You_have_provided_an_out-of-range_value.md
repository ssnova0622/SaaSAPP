### Fix applied for Payment method select and guidance for adding SKU in Store — Carts

I’ve implemented a fix so the Payment select never shows an out‑of‑range value:
- Default is now `COD`.
- If the tenant doesn’t have `store.payments` capability, the component coerces the value to `COD` (hides ONLINE), so you won’t see the “out‑of‑range value `ONLINE`” warning again.
- File updated: `admin_ui/src/pages/Store/Carts.tsx`

#### Why “SKU add” may seem not working
The Carts page saves only valid rows. The backend sanitizes input and discards lines that don’t meet requirements:
- `SKU` must not be empty.
- `Qty` must be > 0. If you leave Qty blank, it becomes 0 and the row is dropped.
- `Price` can be 0 — it is allowed and will be saved if `SKU` and `Qty` are valid.

Reference (backend): `app/services/storage_mongo.py` → `Storage.put_cart(...)`
- Drops items with empty `sku` or `qty <= 0` and recalculates subtotal.

#### How to add an item correctly (current flow)
1. Go to Store → Carts.
2. Enter customer phone and click “Load”.
3. Click “Add” to add a new row (defaults to `qty = 1`).
4. Fill `SKU` (e.g., an existing product SKU like `apple-1kg`). Ensure `Qty > 0`. `Price` is optional (0 is fine for testing).
5. Click “Save cart”. Reloading the cart should show your line(s).

If you still face an issue, please share the exact error shown in the red banner so I can pinpoint quickly.

#### Would you like me to make it easier?
I can implement these usability improvements quickly:
- Auto‑price by SKU: When you type a SKU, we fetch the product, apply its discount (`amount|percent`) and set `price_snapshot` automatically.
- SKU selector with search: Replace the free‑text SKU cell with a searchable dropdown sourced from `/catalog/products`.
- Client‑side validation: Prevent saving if a row has empty `SKU` or `Qty <= 0`, with inline errors.

Tell me which enhancements you prefer and I’ll implement them next.