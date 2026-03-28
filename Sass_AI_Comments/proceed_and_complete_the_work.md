### Plan: Active/Inactive for Customers and Professionals, restrict WhatsApp to active only

#### Objectives
- Add soft-enable/disable (active flag) for Customers and Professionals.
- Only active Customers can receive WhatsApp communications.
- Only active Professionals are bookable and allowed in appointment-related flows.
- Minimal disruption: defaults keep current behavior (active=true by default).

---

### 1) Data model and storage (Mongo)

#### 1.1 Customers schema
- Add `active: bool` field (default `true`).
- Normalize in getters/listing: when reading, coerce missing `active` to `true`.
- Add methods:
  - `set_customer_active(tenant: str, phone: string, active: bool) -> Dict[str, Any]` — returns updated doc (sans `_id`).
  - Extend `list_customers(tenant, search?, tag?, active?: bool, page?, size?) -> { items, total, page, size }` to accept optional `active` filter. If omitted, return all; if true/false, filter accordingly.

#### 1.2 Professionals schema
- Add `active: bool` (default `true`) to the `professionals` collection.
- Normalize in `get_professional`/`get_professionals` to include `active` in returned structures, defaulting to `true` when missing.
- Add methods:
  - `set_professional_active(tenant: str, name: string, active: bool) -> Dict[str, Any]` — returns updated doc or raises if not found.
  - Extend a new listing util: `list_professionals_full(tenant: str, active?: bool) -> List[Dict]` to return full objects including `active` and optional filter.

#### 1.3 Migration helper
- Implement `ensure_active_flags()`:
  - Backfill `active=true` for any `customers` or `professionals` documents missing the field.
  - Idempotent; log counts of updated records per collection.

Acceptance criteria for Section 1:
- Creating a new customer/professional sets `active=true`.
- Existing documents (without `active`) read as active.
- Backfill logs indicate how many docs were updated at startup.

---

### 2) Backend API (FastAPI)

#### 2.1 Customers router (`app/routers/customers.py`)
- Schema changes:
  - Extend `CustomerUpsert` to accept optional `active: bool` (default `true`).
  - `CustomerListResponse.items` already generic; ensure each item includes `active` in payload.
- Endpoints:
  - GET `/v1/tenants/{tenant}/customers` — add query param `active: Optional[bool]`. Wire-through to storage filter.
  - POST `/v1/tenants/{tenant}/customers` — persist `active` if provided; default `true`.
  - NEW: PATCH `/v1/tenants/{tenant}/customers/{phone}/status` with body `{ "active": boolean }` → returns updated doc. Protected by JWT and `ensure_tenant_active`.

#### 2.2 Professionals/Slots router (`app/routers/slots.py`)
- On create professional (POST), persist `active: true` by default (and accept optional active later if needed).
- NEW: listing endpoint that returns full objects with `active` and optional filtering:
  - Option A: Replace current `GET /professionals` (returns `List[str]`) with richer payload.
  - Option B (backward-compatible): Add `GET /tenants/{tenant}/professionals/full?active=true|false` returning `List[{ name, price, active, slotsCount? }]`.
- NEW: PATCH `/v1/tenants/{tenant}/professionals/{name}/status` with body `{ "active": boolean }` → returns updated doc.
- Enforcement:
  - On appointment creation (`POST /appointments`), if professional is inactive → `HTTP 403` with message `"Professional is inactive"`.
  - On slot update (`PUT /professionals/{name}/slots`), if professional is inactive → `HTTP 403`. UI will prevent editing, but backend guards anyway.

Acceptance criteria for Section 2:
- PATCH endpoints toggle `active` and return updated docs.
- List endpoints support `active` filter.
- Attempting to book or modify slots for inactive professional fails with 403.

---

### 3) WhatsApp enforcement (promotions/follow-ups/direct send)

#### 3.1 Promotions pipeline (`app/services/promotions.py` and related)
- When resolving audience for WhatsApp channel:
  - Filter out inactive customers at query level wherever possible (prefer `active=true` condition in storage queries).
  - Before enqueue/send per recipient, double-check `active` and skip if inactive.
  - Log skipped counts: `{"skipped_inactive": N}`; reflect in job summary/metrics.

#### 3.2 Follow-ups (`app/services/followups.py`)
- Exclude inactive customers from scheduling/dispatch.
- When dispatching a due follow-up, re-verify `active` state and mark item as `skipped` with reason `inactive_customer` if necessary.

#### 3.3 Direct WhatsApp utilities
- Introduce helper `is_customer_active(tenant, phone) -> bool` in storage or service layer and guard all direct send paths (if any) with skip result structure: `{ status: "skipped", reason: "inactive_customer" }`.

Acceptance criteria for Section 3:
- Broadcasts and follow-ups never send to inactive customers.
- Logs/metrics reflect skipped recipients.

---

### 4) Admin UI changes (Vite + React)

#### 4.1 Customers page UI
- Table: add `Status` column with chip `Active`/`Inactive` (color-coded).
- Row actions: `Activate` or `Deactivate` button.
  - Calls `PATCH /customers/{phone}/status` with optimistic UI update; rollback on error.
- Filters: Add dropdown `All / Active / Inactive` wired to `active` query param.

#### 4.2 Professionals page UI
- List component shows `Active`/`Inactive` status.
- Row action: toggle `Activate`/`Deactivate`.
- If inactive:
  - Disable slot editing controls with tooltip `"Professional is inactive"`.
  - Opening booking flows for inactive professional should be blocked/shown as disabled.

#### 4.3 Promotions UI
- In audience preview or summary, display note: `Inactive customers are automatically excluded`. Optionally show computed counts (requires backend support to return precomputed counts excluding inactive).

Acceptance criteria for Section 4:
- Users can toggle active state from UI for both Customers and Professionals.
- Customer list filtering by active works.
- Slot editing is disabled for inactive professionals.

---

### 5) App startup and ops

- Call `ensure_active_flags()` in `app.main` within the startup hook, after DB connection is established.
- Log: `"Backfilled active=true: customers=X, professionals=Y"`.
- Feature flags (optional):
  - Env `ENFORCE_ACTIVE_CUSTOMERS=true` and `ENFORCE_ACTIVE_PROFESSIONALS=true` for progressive rollout. Defaults to `true` in non-prod; can be toggled in prod if needed.

---

### 6) Testing and verification

#### 6.1 Backend unit/integration (examples)
- Customers
  - Upsert without `active` → returned doc has `active=true`.
  - PATCH status to false → GET with `active=true` excludes it; with `active=false` includes it.
- Professionals
  - Create defaults `active=true`.
  - PATCH to inactive → `POST /appointments` with that professional returns 403; re-activate → booking works.
- Promotions/follow-ups
  - Prepare two customers (active/inactive); sending a WhatsApp promotion counts only the active; logs show one skipped.

#### 6.2 Manual E2E
- Toggle a customer to inactive in UI → send a promotion; verify it isn’t contacted.
- Toggle a professional to inactive → try to edit slots (disabled) and create an appointment (blocked).

---

### 7) Rollout plan
- Step 1: Deploy backend changes first (harmless defaults). Monitor logs for backfill and skipped counts.
- Step 2: Deploy Admin UI toggles and filters.
- Step 3: Enable any feature flags (if used) and monitor WhatsApp delivery metrics.

---

### 8) API contracts summary (for quick reference)

- Customers
  - GET `/v1/tenants/{tenant}/customers?active=true|false`
  - POST `/v1/tenants/{tenant}/customers` body: `{ name, phone, email?, tags?, active? }`
  - PATCH `/v1/tenants/{tenant}/customers/{phone}/status` body: `{ active: boolean }`

- Professionals
  - GET `/v1/tenants/{tenant}/professionals/full?active=true|false` (new; keeps current simple list for compatibility)
  - PATCH `/v1/tenants/{tenant}/professionals/{name}/status` body: `{ active: boolean }`

- Enforcement
  - POST `/v1/tenants/{tenant}/appointments` → 403 if `professional` is inactive.

---

### 9) Risks and mitigations
- Legacy data without `active` — mitigated by backfill and read-normalization.
- UI/Backend drift — keep simple PATCH endpoints and reuse existing list patterns to minimize changes.
- Performance on large lists — add compound indexes on `customers(tenant, active)` and `professionals(tenant, active)` if needed.

---

### 10) Success checklist
- [ ] Storage supports `active` for customers/professionals with backfill.
- [ ] API exposes PATCH status endpoints and active filters.
- [ ] Appointment and slot flows enforce professional active state.
- [ ] Promotions/follow-ups skip inactive customers by design.
- [ ] Admin UI provides clear toggle + filter UX.
- [ ] Tests and manual E2E validated.

If this plan looks good, I can proceed to implementation starting with storage and API changes (backend), followed by UI toggles and final verification.