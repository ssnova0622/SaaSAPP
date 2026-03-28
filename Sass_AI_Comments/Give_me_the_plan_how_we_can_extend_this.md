### Objective
Extend the existing multi‑tenant SaaS (FastAPI + Mongo + React/Vite Admin) into a WhatsApp‑first store platform suitable for supermarkets/grocery: product catalog, cart/checkout, payments, order tracking, reporting/analytics, promotions/offers — while preserving tenant isolation and active/inactive tenant gating.

---

### Guiding principles
- WhatsApp‑first UX: customers browse and place orders over WhatsApp using interactive messages (lists/buttons), with web fallback if needed.
- Multi‑tenant by design: each tenant (store) manages its own catalog, inventory, orders, offers, and brand templates.
- Simple, incremental rollout: start with MVP (catalog → cart → order → payment link → status) and iterate to richer flows (delivery slots, substitutions, loyalty).
- Compliance: use approved WhatsApp message templates, explicit opt‑in, 24‑hour session rules, and PCI‑DSS compliant payment links (no card data through our servers).

---

### Phase 0 — Foundations and readiness
- Auth & Roles: extend staff roles (Owner, Manager, Picker, Delivery). Ensure JWT roles guard new endpoints.
- Tenant status: only `active` tenants can transact (already in place). Add per‑tenant feature flags (e.g., `store_enabled`, `payments_enabled`).
- Messaging provider: choose Twilio WhatsApp or Meta Cloud API; store provider credentials per tenant.
- Payment provider(s): Stripe/Razorpay (IN), Cashfree/PayU (optional). Store API keys per tenant and allowed methods (UPI/Card/COD).
- Address & Geo: enable address models and delivery service areas; distance fee rules.

Deliverables:
- New `tenants` fields: `store_enabled`, `payment_config`, `whatsapp_config`, `delivery_config`.
- Secrets vaulting approach (env + encrypted fields in DB or KMS).

---

### Phase 1 — Catalog & Inventory (per tenant)
Data model (Mongo):
- `products`: { tenant, sku, name, description, category, images[], unit (kg/pc), variant?: {size/weight}, price, mrp?, tax%, active, created_at, updated_at }
- `inventory`: { tenant, sku, available_qty, reorder_level?, updated_at }
- `categories`: { tenant, name, sort }
- `media` (optional): S3 keys for images.

API (FastAPI):
- GET/POST/PUT/DELETE `/v1/tenants/{tenant}/products`
- GET `/products?search=&category=&active=...` with pagination, sorting
- PATCH `/products/{sku}/status` to (de)activate
- GET/PUT `/inventory/{sku}` and bulk adjustments endpoint for stock sync

Admin UI:
- Catalog manager: CRUD with image upload, category tree, price/stock editing, CSV import.

WhatsApp UX:
- “Browse catalog” → List message of categories → List of top items in category (name, price) with quick add buttons.

---

### Phase 2 — Cart & Checkout
Data model:
- `carts`: { tenant, customer_phone, items:[{ sku, qty, price_snapshot }], total, updated_at, status: active|abandoned }
- `addresses`: { tenant, customer_phone, label, line1, line2, area, city, pincode, latlng?, default }

API:
- POST/GET/PUT `/carts/{phone}` (server‑side cart by phone) — add/update/remove items
- POST `/carts/{phone}/checkout` → creates a draft order, returns payment intent link (if prepaid)

Admin UI:
- View active carts, convert cart to order, apply manual discounts.

WhatsApp UX:
- Button: “View cart” → message with items summary and total; quick actions: +/− qty, remove item, “Checkout”.

---

### Phase 3 — Orders & Payments
Data model:
- `orders`: {
  tenant, id, customer:{ name?, phone }, address, items:[{ sku, name, qty, unit_price, line_total }],
  totals:{ subtotal, tax, delivery_fee, discount, grand_total },
  status: placed|confirmed|picking|out_for_delivery|delivered|canceled,
  payment:{ method: COD|ONLINE, status: pending|paid|failed, provider, provider_ref?, paid_at? },
  timeline:[{ ts, event, meta }], created_at, updated_at
}
- `payments`: { tenant, order_id, provider, intent_id, amount, currency, status, events[], created_at }

API:
- POST `/orders` (from checkout). Server validates inventory, reserves stock, creates payment intent if ONLINE.
- Webhooks `/payments/provider/{name}/webhook` — update payment status to paid/failed (idempotent).
- GET `/orders` (filters by date,status,phone) + GET `/orders/{id}`
- PATCH `/orders/{id}/status` (role‑guarded) transitions with validation and timeline append.

WhatsApp UX:
- After checkout: send payment link (Stripe/Razorpay hosted page). On payment success webhook → WhatsApp receipt message with order id and ETA.
- For COD: confirm order summary and provide ETA immediately.

---

### Phase 4 — Fulfillment & Order Tracking
- Staff screens:
  - Picking UI: suggested pick list by aisle/category, substitution options, mark item unavailable (auto adjust order & refund/collect difference flow policy).
  - Delivery UI: assign driver, start route, mark delivered with proof (photo/signature optional).
- Customer tracking (WhatsApp):
  - Proactive updates: confirmed → picking → out for delivery → delivered.
  - Live status link (optional short web page) with order status and contact.

API additions:
- `fulfillment_tasks`: picking assignments, delivery assignments.
- PATCH endpoints to transition `orders.status` with role checks & timeline logging.

---

### Phase 5 — Offers, Coupons, and Pricing Rules
Data model:
- `coupons`: { tenant, code, type: percent|flat, value, min_cart?, max_discount?, valid_from..to, usage_limit, per_user_limit, active }
- `offers`: { tenant, title, type: BOGO|bundle|category_pct, rules, active, valid_from..to }
- `price_rules`: { tenant, sku/category, type, value, priority }

API:
- Apply coupon to cart: POST `/carts/{phone}/apply-coupon`
- Evaluate best offer engine during cart totals calculation.

Admin UI:
- Offer builder, coupon management, analytics on redemption.

WhatsApp UX:
- Broadcast approved promotional templates to active customers; deep link adds coupon to cart.

---

### Phase 6 — Reports & Analytics
- Sales summary by day/week/month, AOV, payment mix, fulfillment SLA, top products, category performance, coupon redemptions.
- Inventory reports: low stock, aging, shrinkage.
- Customer: RFM segments, repeat rate.

Implementation:
- New aggregations in Mongo using indexes: `(tenant, created_at)`, `(tenant, status)`, `(tenant, items.sku)`.
- Extend existing daily PDF pipeline to Sales/Orders reports; add CSV/Excel exports.
- Schedule daily summary via existing scheduler; deliver via Email/WhatsApp link.

---

### Phase 7 — WhatsApp Automation & Compliance
- Entry points: “Hi” keyword or Click‑to‑WhatsApp ad → onboarding template with opt‑in capture and menu.
- Interactive flows:
  - Main menu: Browse Categories, View Cart, Track Order, Support.
  - Use List and Quick‑Reply messages within 24‑hour service window.
- Templates: Order confirmation, Payment reminder, Out‑for‑delivery, Delivered, Abandoned cart reminder.
- Opt‑in/Opt‑out: store consent per `customers` doc, respect per‑tenant template approval.
- Rate limiting: per tenant and global to respect provider limits.

---

### Phase 8 — Admin UI additions (React/Vite)
- Catalog: products grid with image upload, category management, stock editing.
- Orders board: Kanban by status; detail drawer with timeline; actions (confirm, cancel, refund, reassign).
- Offers/Coupons: CRUD, activation toggles, usage stats.
- Reports: Sales, Inventory, Customer tabs with date filters and export.
- Settings → Payments and WhatsApp tabs: configure provider keys and templates per tenant.

---

### Phase 9 — Security, Observability, Quality
- RBAC: route guards by role; audit logs for sensitive actions (price change, refund).
- Validation: Pydantic schemas for all inputs; server‑side price re‑calc on checkout to avoid tampering.
- Webhooks: verify signatures for payment providers.
- Logs/metrics: structured logs with request ids; counters for orders, GMV, failures; alerts on webhook errors.
- Backups and migrations for new collections; load testing for peak hours.

---

### Phase 10 — DevOps & Scalability
- Background workers for webhooks/notifications using a task queue (RQ/Celery) if needed.
- Caching layer for catalog and price rules (Redis) to speed up WhatsApp response times.
- CDN/S3 for product images.
- Horizontal scaling of API; idempotency keys for checkout/order creation.

---

### Database schema (new collections summary)
- `products`, `categories`, `inventory`, `carts`, `orders`, `payments`, `coupons`, `offers`, `price_rules`, `fulfillment_tasks`, `addresses`.
- Index suggestions:
  - products: (tenant, sku unique), (tenant, category), (tenant, active)
  - inventory: (tenant, sku), (tenant, available_qty)
  - carts: (tenant, customer_phone), TTL for abandoned carts (optional)
  - orders: (tenant, created_at), (tenant, status), (tenant, customer.phone)
  - payments: (tenant, order_id), (tenant, status)
  - coupons/offers: (tenant, code), (tenant, active, valid_from..to)

---

### API surface (representative)
- Catalog:
  - GET/POST/PUT/DELETE `/tenants/{t}/products`, GET `/products/{sku}`
  - GET `/categories`, POST/PUT `/categories`
  - GET/PUT `/inventory/{sku}`; POST `/inventory/bulk`
- Cart & Checkout:
  - GET/POST/PUT `/carts/{phone}`; POST `/carts/{phone}/apply-coupon`; POST `/carts/{phone}/checkout`
- Orders & Payments:
  - GET `/orders` (filters), POST `/orders`, GET `/orders/{id}`
  - PATCH `/orders/{id}/status`
  - POST `/payments/provider/{name}/webhook` (Stripe/Razorpay)
- Tracking & Notifications:
  - GET `/orders/{id}/track` (tokenized), WhatsApp send endpoints/handlers
- Offers:
  - CRUD `/coupons`, `/offers`, `/price-rules`
- Reports:
  - Sales, Inventory endpoints similar to current reports pipeline

All endpoints guarded with `Depends(get_current_user)` and `ensure_tenant_active`. Public tracking endpoints use signed short tokens.

---

### WhatsApp conversation design (examples)
- Browse flow:
  - Template: “Welcome to <Store>. Choose an option.” → List: Categories
  - List pick → Send 5 items with buttons: “Add +1”, “More”, “Back”
- Cart flow:
  - “Your cart: 3 items, ₹540. Actions: +/−/Remove/Checkout” (buttons)
- Checkout & payment:
  - Generate order draft → payment link → on webhook success send receipt template + ETA
- Tracking updates:
  - Send template for `confirmed`, `out_for_delivery`, `delivered` with order id and summary.

---

### Incremental delivery plan (8–12 weeks, indicative)
1. Foundations (wk 1): models, indexes, settings, provider stubs, Admin settings tabs.
2. Catalog & Inventory (wks 2–3): backend + Admin UI.
3. Cart & Checkout (wks 3–4): server cart, draft order, payment links, webhooks.
4. Orders & Fulfillment (wks 5–6): order lifecycle, staff boards, WhatsApp confirmations.
5. Offers/Coupons (wk 7): rules engine, UI management, cart integration.
6. Reports/Analytics (wk 8): sales & inventory reports; schedule delivery.
7. WhatsApp automation (parallel wks 4–8): templates, flows, opt‑in, rate limits.

---

### Acceptance criteria (MVP)
- Customers can place and pay for an order via WhatsApp, receive confirmations, and track status.
- Admins can manage catalog, inventory, orders, and offers in the Admin UI.
- Payments settle via provider; webhooks update order status to `paid` reliably (idempotent).
- Reports show daily sales and top items; exports available.

---

### Configuration you’ll need per tenant
- WhatsApp provider credentials (phone number id, access token or Twilio SID/Auth).
- Payment provider keys and enabled methods.
- Delivery zones and fees; store hours; holiday blackout days.
- Tax settings and invoice preferences.

---

### Next step
If you confirm the providers (WhatsApp and Payments) you prefer and whether you want delivery or pickup‑only for MVP, I can translate this plan into concrete issue tickets (backend endpoints, UI screens, data models) and start with Phase 1 implementation immediately.