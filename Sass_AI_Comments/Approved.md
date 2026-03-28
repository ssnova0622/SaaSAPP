### Short answer
Yes. We can allow editing an order (e.g., add one more item) any time before delivery. Below is a focused plan to add this capability safely across backend and admin UI.

### Proposed plan (MVP)

#### 1) Rules and scope
- Editable statuses: `placed`, `confirmed`, `picking`.
- Non-editable statuses: `ready_for_pickup`, `out_for_delivery`, `delivered`, `canceled`.
- Payments:
  - COD: edits allowed while order is editable.
  - ONLINE: if already paid, block edits in MVP (show clear message). Phase 2 can support top‑up/refund flows.
- Pricing for newly added items: default to current catalog price after discount (same logic as on Products/Carts), but allow manual override in the editor.
- Inventory: unchanged in MVP (no extra reservation adjustments on edit). Inventory continues to be handled by your existing flow.

#### 2) Backend changes
- New endpoint: `PATCH /tenants/{tenant}/orders/{order_id}/items`
  - Body: `{ items: Array<{ sku: string; qty: number; price_snapshot: number }> }`
  - Validates status/payment rules; sanitizes items (non-empty `sku`, `qty > 0`, non-negative `price_snapshot`).
  - Recalculates totals server‑side; updates `updated_at`.
  - Appends timeline event: `items_updated` with before/after diff (for audit).
- Storage method: `Storage.update_order_items(tenant, order_id, items)` implementing all of the above and returning the updated order.

#### 3) Frontend API
- Add `updateOrderItems(tenant, orderId, items)` to `admin_ui/src/api/store.ts`.

#### 4) Admin UI — Orders page
- In `Store — Orders` detail dialog:
  - Add an “Edit items” mode (button visible only for editable statuses and when ONLINE isn’t paid).
  - Editor table similar to Carts: columns `SKU` (with Autocomplete search of products + variants), `Qty` (min 1), `Price` (auto‑filled from catalog on SKU selection; editable).
  - Add/Remove item rows; live subtotal display.
  - Save → calls `updateOrderItems`; refreshes the order detail with new totals.
  - Clear inline validation errors when `SKU` empty or `Qty <= 0`.

#### 5) Pricing consistency
- For existing items not changed by the user, keep their stored `price_snapshot`.
- For new items or when user changes SKU, compute default `price_snapshot` using `getProductBySku` and the same discount formula used elsewhere.

#### 6) Errors and messages
- If order is not in an editable status, show: “Order cannot be edited in status ‘…’.”
- If ONLINE payment is already `paid`, show: “Order was already paid online. Editing items is disabled (top‑ups coming soon).”

#### 7) Tests and verification
- Backend unit tests: happy path, non‑editable status, paid ONLINE, invalid payload, totals recompute.
- API tests for the new endpoint with capability/module guards.
- Manual UI checks: edit COD order; add a new line; verify totals; try on delivered and paid ONLINE orders → blocked with proper messages.

#### 8) Phase 2 (optional)
- Payments top‑up for ONLINE paid orders when total increases (create new payment intent for delta).
- Optional refund/credit path when total decreases.
- Inventory reservations adjustment (if you choose to reserve prior to delivery in future).

#### 9) Timeline
- Day 1: Backend endpoint + storage logic + tests.
- Day 2: Admin UI editor with Autocomplete, auto‑price, validation.
- Day 3 (optional): ONLINE top‑up flow and polish.

### Next steps
- If you approve the MVP rules above, I’ll implement the backend endpoint and the Orders UI editor. If you want different editable statuses or payment behavior, tell me and I’ll adjust before coding.