### Action types: complete catalog (current + ready-to-add)

Below is a practical, admin-friendly catalog of “action types” you can use in your WhatsApp Menu Builder. It contains:
- The actions that already exist in your backend `ACTION_REGISTRY` and dispatcher
- Clean TypeScript types for the Admin UI
- JSON examples for each action
- A blueprint to add new actions safely (registry + handler + dispatcher)

All items below are aligned with your current code in `app/routers/whatsapp.py` and `admin_ui/src/api/whatsapp.tsx`.

---

### 1) Actions that exist today (from ACTION_REGISTRY)

Core
- `core.open_ticket` — Open Ticket / Enquiry
  - Params: `{ category?: string }`
- `core.show_offers` — Show Offers
  - Params: `{}` (none)
- `core.open_url` — Open URL
  - Params: `{ url?: string }`

Salon/Clinic
- `salon.select_timeslot` — Select Timeslot (Salon)
  - Params: `{}` (handled by the booking FSM)
- `clinic.book_doctor` — Book Doctor (Clinic)
  - Params: `{}` (currently mapped to timeslot flow)

Store
- `store.browse_catalog` — Browse Catalog
  - Params: `{ category?: string }`
- `store.check_product` — Search Product
  - Params: `{ query?: string }`
- `store.track_order` — Track Order
  - Params: `{ order_id?: string }`

Legacy aliases supported by `_legacy_to_action_id(...)`
- `select_timeslot` → `salon.select_timeslot`
- `open_ticket` → `core.open_ticket`
- `show_offers` → `core.show_offers`
- `open_url` → `core.open_url`

---

### 2) Admin UI TypeScript types you can drop in

Use discriminated unions so the form knows which params to render based on `action_id`.

```ts
// admin_ui/src/api/whatsapp-actions.ts

export type ActionId =
  | 'core.open_ticket'
  | 'core.show_offers'
  | 'core.open_url'
  | 'salon.select_timeslot'
  | 'clinic.book_doctor'
  | 'store.browse_catalog'
  | 'store.check_product'
  | 'store.track_order'

export type ActionParamsMap = {
  'core.open_ticket': { category?: string }
  'core.show_offers': Record<string, never>
  'core.open_url': { url?: string }
  'salon.select_timeslot': Record<string, never>
  'clinic.book_doctor': Record<string, never>
  'store.browse_catalog': { category?: string }
  'store.check_product': { query?: string }
  'store.track_order': { order_id?: string }
}

export type ActionNode<A extends ActionId = ActionId> = {
  id: string
  type: 'action'
  action_id: A
  params?: ActionParamsMap[A]
}
```

This makes the right-side properties panel trivial: switch on `action_id` and render the right fields.

---

### 3) JSON examples for each action

Core
- Open Ticket
```json
{ "id": "ticket", "type": "action", "action_id": "core.open_ticket", "params": { "category": "general" } }
```
- Show Offers
```json
{ "id": "offers", "type": "action", "action_id": "core.show_offers" }
```
- Open URL
```json
{ "id": "website", "type": "action", "action_id": "core.open_url", "params": { "url": "https://example.com" } }
```

Salon/Clinic
- Select Timeslot (Salon)
```json
{ "id": "book", "type": "action", "action_id": "salon.select_timeslot" }
```
- Book Doctor (Clinic)
```json
{ "id": "book_doctor", "type": "action", "action_id": "clinic.book_doctor" }
```

Store
- Browse Catalog
```json
{ "id": "browse", "type": "action", "action_id": "store.browse_catalog", "params": { "category": "Hair Care" } }
```
- Search Product
```json
{ "id": "search", "type": "action", "action_id": "store.check_product", "params": { "query": "shampoo" } }
```
- Track Order
```json
{ "id": "track", "type": "action", "action_id": "store.track_order", "params": { "order_id": "ORD-123" } }
```

---

### 4) Optional: Extended catalog (future-ready)

If you want to expose “all possible actions” an admin may expect, here’s a sensible, modular list. These are suggestions; enable as you implement backend handlers. I’ve grouped by domain and proposed `requires_caps` to keep them tenant-safe.

Core
- `core.static_text` — Send static text (multi-lingual friendly)
  - Params: `{ text: string | Record<string,string> }`
- `core.language_switch` — Switch session locale
  - Params: `{ locale: string }`
- `core.go_to_node` — Jump to a submenu node
  - Params: `{ menu_id: string, node_id: string }`

Support
- `support.create_ticket` (alias for `core.open_ticket` if you prefer a separate module)
  - Params: `{ category?: string, priority?: 'low'|'normal'|'high' }`
- `support.agent_handover` — Flag for human handover routing
  - Params: `{ queue?: string }`

Salon/Clinic
- `salon.reschedule_appointment`
  - Params: `{ appointment_id?: string }`
- `salon.cancel_appointment`
  - Params: `{ appointment_id?: string, reason?: string }`
- `clinic.select_specialty`
  - Params: `{ specialty?: string }`

Store/Commerce
- `store.add_to_cart`
  - Params: `{ sku: string, qty?: number }`
- `store.view_cart`
  - Params: `{}`
- `store.checkout`
  - Params: `{ payment_method?: 'cod'|'upi'|'card' }`
- `store.order_status` (alias of `store.track_order`)
  - Params: `{ order_id?: string }`

Payments
- `payments.pay_link`
  - Params: `{ url: string, label?: string }`
- `payments.collect_upi`
  - Params: `{ upi_id?: string, amount?: number }`

Logistics
- `logistics.track_shipment`
  - Params: `{ tracking_id: string, provider?: string }`

CRM/Marketing
- `crm.subscribe_newsletter`
  - Params: `{ topic?: string }`
- `crm.apply_coupon`
  - Params: `{ code: string }`

For each of the above, you’d add a registry entry + a lightweight handler. You can implement them incrementally; they’ll appear in the Admin UI dropdown as soon as the registry returns them.

---

### 5) How to add a new action in the backend (pattern)

1) Register it in `ACTION_REGISTRY` (with capability gating and a JSON params schema):
```py
ACTION_REGISTRY.append({
  "id": "payments.pay_link",
  "label": "Send Pay Link",
  "module": "payments",
  "business_types": ["*"],
  "requires_caps": ["payments.links"],
  "params_schema": {
    "type": "object",
    "properties": { "url": {"type": "string"}, "label": {"type": "string"} },
    "required": ["url"]
  },
})
```
2) Implement a handler function:
```py
def _action_payments_pay_link(tenant: str, params: Dict[str, Any] | None, locale: str) -> str:
    url = str((params or {}).get("url") or "").strip()
    label = str((params or {}).get("label") or "Pay now")
    if not url:
        return "Payment link is missing."
    return f"{label}: {url}"
```
3) Map it in `_run_action(...)`:
```py
if aid == "payments.pay_link":
    return _action_payments_pay_link(tenant, params, locale)
```
4) (Optional) Add a legacy alias in `_legacy_to_action_id(...)` if you need backward-compatible IDs.

It will instantly be available to the Admin UI via `GET /whatsapp/actions`.

---

### 6) Admin UI: rendering forms from the registry

Because each registry item has `params_schema`, you can render the form dynamically:
- `type: 'string'` → text input
- `enum` → dropdown
- field descriptions → tooltips
- `required` → validation

This lets you expose new actions to admins without shipping a new UI build.

---

### 7) Bonus: post-completion routing

If you want to make actions chainable (e.g., after booking, go to another submenu), standardize a shared optional param:
```ts
export type AfterParam =
  | { mode: 'root' }
  | { mode: 'goto_node'; node_id: string }
  | { mode: 'followup_text'; text: string }
```
Have action handlers check `params?.after` and decide whether to reset to root or navigate elsewhere. This gives admins a simple dropdown to control “what happens next.”

---

### 8) Do you want me to add any of the extended actions now?

Tell me which domains you need first (Support, Store, Payments, CRM), and I’ll give you the exact `ACTION_REGISTRY` entries, handler stubs, and the `_run_action` mappings so your admin can start using them immediately.