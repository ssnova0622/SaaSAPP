### Objective
Add all newly delivered store capabilities and settings into the Admin UI so tenants can configure and operate a WhatsApp‑first store: payments (dummy for now), delivery/pickup settings, carts/orders views, and basic operations. Keep it consistent with existing UI patterns (MUI + React + Vite) and tenant selection.

---

### Scope summary to bring into Admin UI
- Tenant Settings additions
  - Payments tab: provider, currency, methods (ONLINE/COD), test mode.
  - Fulfillment tab: delivery enabled, pickup enabled, simple service areas and store hours.
  - WhatsApp config placeholder (display-only fields for now).
- Store operations
  - Cart management (operator can view/update a customer’s cart by phone; useful for assisted orders).
  - Checkout starter (generate draft order + payment URL for ONLINE; COD supported) for admin-assisted flows.
  - Orders board
    - List with filters (status, date), detail drawer, status transitions.
    - Payment status display; quick link to dummy payment URL if present.
- Reports are already in UI; leave as-is.
- Keep active/inactive behavior (tenants/customers/professionals) as implemented.

---

### Milestone plan (Admin UI only)

#### Milestone 1 — Settings: Payments + Fulfillment
1. Routing/Navigation
   - Settings page already exists. Add tabs/sections for “Payments” and “Fulfillment”.
2. API wiring
   - Reuse `GET /v1/tenants/{tenant}` and `PUT /v1/tenants/{tenant}`.
   - Extend `TenantSettings` type in `admin_ui/src/api/tenants.tsx` with:
     - `store_enabled?: boolean`
     - `payment_config?: { provider: 'dummy' | 'stripe' | 'razorpay'; currency: string; methods: ('ONLINE'|'COD')[]; test_mode?: boolean; webhook_secret?: string }`
     - `delivery_config?: { delivery_enabled: boolean; pickup_enabled: boolean; service_areas: string[]; store_hours: string[] }`
     - `whatsapp_config?: Record<string, any>` (placeholder)
3. UI components
   - Payments
     - Provider Select (disabled options for Stripe/Razorpay as placeholders).
     - Currency TextField.
     - Methods MultiSelect (ONLINE, COD).
     - Test mode Switch.
     - Webhook secret (password field, masked) with helper text “dev only; backend ignores for dummy provider”.
     - “Save” button persists via `updateTenantSettings()`; show success/snackbar.
   - Fulfillment
     - Switches: Delivery enabled, Pickup enabled.
     - TextAreas or Chips input for Service areas and Store hours (comma/newline separated → string[] on save).
     - “Save” with optimistic UI + handle errors.
   - WhatsApp (read-only for now): show provider placeholder with a note “Configure later”.
4. Validation and UX
   - Disable Save if no tenant selected.
   - Basic client validation (currency non-empty; at least one method selected).
5. Acceptance
   - Settings can be updated and persisted; refresh reflects changes.

#### Milestone 2 — Carts (Assisted orders)
1. New route: `/store/carts` page
   - Inputs: Customer phone (E.164 suggested; no strict validation), tenant from selection.
   - Fetch cart: `GET /v1/tenants/{tenant}/carts/{phone}`.
   - Edit items (SKU, qty, price snapshot) in a table with Add/Remove rows.
   - Save cart: `PUT /v1/tenants/{tenant}/carts/{phone}` with `{ items }`.
   - Show computed totals (returned by API).
2. Checkout panel
   - Choose fulfillment mode (delivery/pickup).
   - If delivery: minimal address form (label, line1, city, pincode).
   - Choose payment method (ONLINE/COD) constrained by tenant `payment_config.methods`.
   - POST checkout to `/carts/{phone}/checkout`.
   - If ONLINE: show `payment_url` and `intent_id` (copy button). If COD: show Order ID.
3. UX details
   - Loading and error states, inline validation (e.g., cart cannot be empty per server response).
   - Persist last used phone in localStorage to streamline operator workflow.
4. Acceptance
   - Operator can create/update a cart and perform checkout; receives order id and payment URL for ONLINE.

#### Milestone 3 — Orders board
1. New routes and pages
   - `/store/orders` → Orders list
   - `/store/orders/:id` → Order detail (or a drawer on list page)
2. API wiring
   - List: `GET /v1/tenants/{tenant}/orders?status=placed,confirmed,...&page=1&size=50`
   - Detail: `GET /v1/tenants/{tenant}/orders/{id}`
   - Transition: `PATCH /v1/tenants/{tenant}/orders/{id}/status` with `{ status }`
3. UI features
   - Filters: status multi-select, quick chips for common sets (Open: placed/confirmed/picking/out_for_delivery/ready_for_pickup).
   - Columns: Order ID (short), Created at, Customer phone, Fulfillment mode, Items count, Grand total, Order status, Payment method/status.
   - Row actions: View (opens drawer), Status change (menu: Confirm, Picking, Ready for pickup, Out for delivery, Delivered, Canceled). Disable invalid transitions on client but rely on server validation.
   - In drawer: full items list with qtyxprice, address (if delivery), timeline (from `order.timeline`), payment block showing `payment.intent_id`, `payment.status`, and link if `payment_url` available (from checkout step; if not persisted in order, display last known URL after checkout step only).
4. Acceptance
   - List, filter, open detail, transition statuses; errors shown inline.

#### Milestone 4 — Navigation, permissions, polish
1. Navigation
   - Add “Store” group in sidebar with: Carts, Orders (Reports already exists elsewhere).
   - Keep Tenants/Settings/Customers/Professionals/Staff as-is.
2. Guardrails
   - If tenant is inactive → show banner and prevent store actions (reuse existing tenant-active logic if available; otherwise add a check on selected tenant settings).
   - If `store_enabled=false` → show banner on store pages and disable inputs.
   - Respect `payment_config.methods`: if no ONLINE, hide/disable ONLINE option in checkout.
3. Shared helpers
   - Types for `Order`, `Payment`, `Cart` in `admin_ui/src/api/store.ts`.
   - Reusable Address form component.
4. Error handling
   - Map server errors: 400 (validation), 401 (relogin), 403 (tenant inactive), 404 (not found).
5. Acceptance
   - Consistent UX across pages; empty states; responsive layout.

---

### API client tasks (Admin UI)
- Create `admin_ui/src/api/store.ts`:
  - `getCart(tenant, phone)`
  - `putCart(tenant, phone, items)`
  - `checkout(tenant, phone, payload)` returns `{ order_id, payment_url?, intent_id? }`
  - `listOrders(tenant, params)` returns paginated orders
  - `getOrder(tenant, id)`
  - `updateOrderStatus(tenant, id, status)`
- Update `tenants.tsx` types to include new settings keys (if not already extended locally).

---

### UX sketches (concise)
- Settings → Payments: small form with Save; toast on success.
- Settings → Fulfillment: toggles + chips inputs; Save.
- Carts: phone selector on top; cart editor table; checkout panel on right.
- Orders: data grid with filters; clicking row opens drawer with timeline and payment details; status menu.

---

### Testing plan
- Unit-ish (front-end):
  - API clients call correct URLs and handle typical errors.
- Manual E2E:
  - Configure payments/fulfillment in Settings; refresh and verify values persist.
  - Build a cart and checkout ONLINE; click payment URL; call dummy webhook; verify order payment status updates to paid in the list/detail after refresh.
  - Checkout COD; transition status flow until delivered; verify UI prevents invalid transitions.
  - Toggle tenant inactive and verify store pages are blocked with a banner.

---

### Rollout and timeline
- Milestone 1 (0.5–1 day): Settings tabs + API wiring + validations.
- Milestone 2 (1–1.5 days): Carts page with checkout flow.
- Milestone 3 (1–1.5 days): Orders list + detail + transitions.
- Milestone 4 (0.5 day): Navigation, banners/guardrails, QA pass.

Total estimated: ~3–4.5 days of UI work.

---

### Risks and mitigations
- CORS/baseURL drift in dev: ensure Admin UI `.env` `VITE_API_BASE` matches backend port; keep both localhost/127.0.0.1 origins in CORS.
- Payment URL not persisted on order: currently returned by checkout; we won’t store the URL on the order by design (dummy). UI will show the URL immediately post‑checkout; later providers (Stripe/Razorpay) will allow fetching hosted page URL by intent id.
- Data validation for service areas/hours: keep as string arrays in MVP; formalize later.

---

### Next steps (need your confirmation)
- Approve the milestones above. If approved, I will:
  1) Implement Settings tabs and types.
  2) Build Carts page with checkout.
  3) Build Orders board with transitions and details.
  4) Wire navigation and banners.

If you prefer a different navigation label or want the Orders page before the Carts page, let me know and I’ll reorder the milestones.