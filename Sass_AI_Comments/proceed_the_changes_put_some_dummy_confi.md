### What I’m going to deliver now (scope confirmed)
You asked to proceed with the plan, add a dummy payment configuration, support both delivery and pickup, and clarify how to separate the scheduler from the WhatsApp store. Below is a concrete, step‑by‑step plan with exact data structures, endpoints, and process separation. If you approve, I can start implementing from “Milestone A” immediately.

---

### Milestone A — Tenant settings: payment + fulfillment (delivery/pickup)
Goal: add settings in the tenant profile so all new store features are configurable per tenant, with safe dummy defaults.

- Data model (tenants doc — Mongo):
  - Add/allow these fields (default values shown):
    - `store_enabled: true`
    - `payment_config: { provider: 'dummy', currency: 'INR', methods: ['ONLINE','COD'], test_mode: true, webhook_secret: 'dev' }`
    - `delivery_config: { delivery_enabled: true, pickup_enabled: true, service_areas: [], store_hours: [] }`
    - `whatsapp_config: { provider: 'twilio'|'meta'|'dummy', from_number?: string, token?: string }` (kept as optional for now)

- Backend (FastAPI):
  - Extend `Storage.get_tenant_settings` to include defaults for these fields when missing.
  - Extend `Storage.update_tenant_settings` to permit updating keys: `store_enabled, payment_config, delivery_config, whatsapp_config` (validate enum values and shapes).
  - No breaking changes to existing endpoints; the `PUT /v1/tenants/{tenant}` and `GET /v1/tenants/{tenant}` will simply return and persist these extra fields.

- Admin UI (Settings page):
  - Add a “Payments” tab section:
    - Provider select: Dummy (default), Stripe, Razorpay (disabled placeholders)
    - Currency input (default INR)
    - Methods multi‑select: ONLINE, COD
    - Test mode toggle
  - Add a “Fulfillment” tab section:
    - Toggles: Delivery enabled, Pickup enabled
    - Textareas (MVP): Service areas, Store hours (comma/newline separated)

- Env samples for dev (dummy config):
  - `PAYMENT_PROVIDER=dummy`
  - `PAYMENT_TEST_MODE=true`
  - `CURRENCY=INR`
  - (Webhook shared secret kept in settings doc; for dev use `webhook_secret=dev`)

Deliverable: you can turn on/off delivery vs pickup and see dummy payment settings in the UI and API.

---

### Milestone B — Dummy payments provider + checkout skeleton
Goal: Enable a realistic flow for placing orders with a fake (safe) payment link and a webhook that marks the order paid.

- New collections:
  - `carts`: `{ tenant, customer_phone, items:[{ sku, qty, price_snapshot }], totals:{...}, updated_at, status:'active'|'abandoned' }`
  - `orders`: `{ tenant, id, customer:{ name?, phone }, address?, fulfillment_mode:'delivery'|'pickup', items:[...], totals:{...}, status:'placed'|'confirmed'|'out_for_delivery'|'delivered'|'canceled', payment:{ method:'COD'|'ONLINE', status:'pending'|'paid'|'failed', provider, intent_id?, paid_at? }, timeline:[{ts,event,meta}], created_at, updated_at }`
  - `payments`: `{ tenant, order_id, provider:'dummy', intent_id, amount, currency, status:'pending'|'paid'|'failed', events:[{ts,type,meta}] }`

- Backend endpoints (JWT; tenant must be active):
  - Carts
    - `GET /v1/tenants/{tenant}/carts/{phone}` → return or create cart
    - `PUT /v1/tenants/{tenant}/carts/{phone}` → set items array (server re‑calculates totals)
  - Checkout
    - `POST /v1/tenants/{tenant}/carts/{phone}/checkout` body: `{ fulfillment_mode: 'delivery'|'pickup', address?: {...}, payment_method: 'COD'|'ONLINE' }`
      - Validate fulfillment rules:
        - if `fulfillment_mode=delivery` and `delivery_enabled=false` → 400
        - if `pickup` and `pickup_enabled=false` → 400
        - `address` required for delivery; not required for pickup
      - Create Order with `status:'placed'` and payment per method:
        - COD → `payment.status='pending'`, but allow status transition to `confirmed` server‑side
        - ONLINE → call Dummy provider (see below), create payment intent, return `{ order_id, payment_url }`
  - Payments
    - `POST /v1/payments/provider/dummy/webhook` (no signature in dev): body `{ intent_id, status:'paid'|'failed' }`
      - Find payment/order, mark payment status accordingly, set order payment status and append timeline. Idempotent.

- Payment service abstraction
  - `app/services/payments.py`:
    - `class PaymentsProvider` interface
    - `class DummyProvider(PaymentsProvider)` with:
      - `create_intent(order_id, amount, currency) -> { intent_id, payment_url }`
      - Payment URL is a static placeholder, e.g., `https://example.com/pay/{intent_id}`
      - Webhook simply accepts `{intent_id, status}` to mark paid/failed
  - Provider factory decides based on tenant `payment_config.provider`

- Admin UI (optional in this milestone):
  - Show Orders (list page) with filters by status and payment status; detail drawer shows items and timeline.

Deliverable: You can checkout a cart and get a fake payment URL. Hitting the dummy webhook marks the order paid.

---

### Milestone C — Delivery vs Pickup in order lifecycle
Goal: Persist and enforce fulfillment mode through to staff workflows and WhatsApp updates.

- Order shape additions:
  - `fulfillment_mode` (enum)
  - `address` (if delivery): `{ label, line1, line2?, area?, city, pincode, latlng? }`

- Status transitions examples (role‑guarded):
  - COD: `placed → confirmed → picking → out_for_delivery → delivered`
  - ONLINE: `placed (pending payment) → [webhook paid] → confirmed → ...`
  - Pickup orders skip delivery steps (e.g., `confirmed → ready_for_pickup → delivered`)

- Admin UI changes:
  - Orders board columns depend on fulfillment mode (show/hide delivery steps).

Deliverable: Orders respect selected fulfillment mode; the system allows both modes simultaneously per tenant.

---

### Separation of concerns — Scheduler vs WhatsApp Store
You will have three cooperating processes. This makes scaling and deployments clean, and isolates concerns.

- 1) Core API service (your current FastAPI app)
  - Responsibility: Tenants, catalog (later), carts, orders, payments, reports endpoints, admin JWT auth, webhooks.
  - Runs on port e.g., 8100.

- 2) Scheduler service (separate process/app)
  - Responsibility: periodic jobs (daily sales reports, abandoned cart reminders, inventory alerts). It does NOT expose public endpoints.
  - Implementation options:
    - Simple: APScheduler in a separate module `app/scheduler.py` with jobs registered on startup. Run with: `python -m app.scheduler`.
    - Scalable: a queue worker (RQ/Celery) where scheduler enqueues jobs and workers execute; still a separate process from Core API.
  - Config: `SCHEDULER_ENABLED=true` for local dev; reads the same Mongo and Settings as API.

- 3) WhatsApp Bot service (separate FastAPI app)
  - Responsibility: receive inbound WhatsApp webhooks from Twilio/Meta, maintain the conversation state, and call the Core API (carts/orders) on behalf of customers.
  - Security: inbound webhooks validated with provider signatures; outbound calls to Core API authenticated via a per‑tenant `BOT_TOKEN` (stored in tenant settings). Customers never need JWT.
  - Runs on a different port (e.g., 8200). Deployment can be independent to scale message throughput.

- Local orchestration example (docker‑compose.yml outline):
  - `api`: build current app; expose 8100
  - `scheduler`: same image; command `python -m app.scheduler`; no port exposure
  - `whatsapp-bot`: build `app/whatsapp_bot.py` (another FastAPI); expose 8200
  - All share the same Mongo network and environment (CORS, MONGO_URI, etc.)

This separation keeps time‑based tasks (Scheduler) and chat automation (WhatsApp Bot) independent from the Admin/API path. Failures in one do not take down the others.

---

### Data & indexes to add up front (quick list)
- `orders` indexes: `(tenant, created_at)`, `(tenant, status)`, `(tenant, 'customer.phone')`
- `carts` index: `(tenant, customer_phone)`
- `payments` index: `(tenant, order_id)`, `(tenant, status)`
- (Later) `products`/`inventory` indexes as we add catalog

---

### End‑to‑end test script (manual, MVP)
1) Configure tenant in Settings → Payments (Dummy, ONLINE+COD) and Fulfillment (Delivery+Pickup). Ensure `store_enabled=true`.
2) Create a cart via REST:
   - `PUT /v1/tenants/ss-salon/carts/+919999999999` body `{ items:[{sku:'apple-1kg', qty:2, price_snapshot:120}] }`
3) Checkout ONLINE:
   - `POST /v1/tenants/ss-salon/carts/+919999999999/checkout` body `{ fulfillment_mode:'delivery', address:{...}, payment_method:'ONLINE' }`
   - Receive `{ order_id, payment_url, intent_id }`
4) Simulate payment webhook:
   - `POST /v1/payments/provider/dummy/webhook` body `{ intent_id:'...', status:'paid' }`
   - Order should now be `payment.status='paid'`, timeline updated.
5) List orders:
   - `GET /v1/tenants/ss-salon/orders?status=placed,confirmed,paid`

---

### What I need from you to finalize details
- Confirm payment provider for production later (Stripe/Razorpay). For dev we will use Dummy only.
- For WhatsApp provider, confirm Twilio or Meta Cloud (for later Milestone; we’ll retain current Messaging until then).

---

### Proposed immediate sequence (2–3 days for this slice)
- Day 1: Implement tenant settings extensions (Milestone A) backend + Admin UI.
- Day 2: Add Dummy payments provider, carts + checkout endpoints, and dummy webhook (Milestone B).
- Day 3: Add fulfillment_mode handling and order storage; basic Orders list UI; prepare `app.scheduler` scaffold and `whatsapp_bot` app skeleton with README instructions.

If you approve this sequence, I’ll proceed with Milestone A implementation first and report back with endpoints and UI screenshots.