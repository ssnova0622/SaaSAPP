### Plan: Implement dummy Meta Cloud (Interactive buttons) with Twilio fallback

You asked to proceed with a dummy configuration for Meta WhatsApp Cloud, while keeping Twilio as backup. Below is a concrete, low‑risk plan to wire Meta Cloud into your existing WhatsApp module without needing real Meta credentials yet. It will simulate interactive buttons/lists while preserving the current Twilio text flow.

#### Objectives
- Add `meta_cloud` provider support alongside `twilio`.
- When provider is `meta_cloud`, render submenus as Interactive messages (buttons ≤3, list >3) using a dummy sender that simulates the experience without calling Meta.
- Keep Twilio webhook path unchanged as the fallback.
- Expose Meta fields in Admin UI → WhatsApp → Config.
- Maintain all current triggers, menus, actions, sessions, and Option‑B RBAC.

---

### Deliverables
1) Backend
- Extend tenant `whatsapp_config` to include the following fields (read/write):
  - `provider: "twilio" | "meta_cloud"` (default remains `twilio`)
  - `phone_number_id: string` (Meta Cloud)
  - `access_token: string` (Meta Cloud; stored as plain text for dummy; later migrate to secret vault)
  - `active_menu_id?: string` (optional default published menu)
- Add a rendering adapter `send_submenu_reply(tenant, phone, node, locale)` that:
  - If `provider == "twilio"`: returns current text (TwiML path unchanged)
  - If `provider == "meta_cloud"`: in dummy mode logs a button/list payload and returns a friendly text that mimics buttons, e.g.:
    - "[buttons] 1) Book, 2) Offers, 3) Cancel — tap buttons (dummy) or reply with number"
- Keep current number‑based input working for both providers.
- (Optional) Add a no‑auth dummy endpoint to preview the interactive payload JSON for debugging: `GET /v1/debug/whatsapp/interactive-preview?tenant=..&node=..`.

2) Admin UI
- WhatsApp → Config
  - Add Provider select: `twilio` (default), `meta_cloud`.
  - When `meta_cloud` is selected, show `phone_number_id`, `access_token`, `active_menu_id` inputs.
  - Preserve Twilio fields and From Numbers behavior (prefix normalization already implemented).
  - Save continues to call `PUT /v1/tenants/{tenant}/whatsapp/config` with the extended shape.

3) Docs / Examples
- Update help text in Config to explain dummy Meta mode:
  - Without real Meta credentials, outbound messages are simulated; customers still receive standard text responses.
  - Number‑based replies continue to advance the flow.
- Add example payload shown in the preview endpoint and in logs.

---

### Implementation steps (backend)
1) Config schema update
- Update `Storage.get_tenant_settings` normalization to include defaults for `phone_number_id`, `access_token`, and `active_menu_id` when `provider == "meta_cloud"`.
- Update `PUT /tenants/{tenant}/whatsapp/config` to accept these fields and persist them (we already normalize numbers and provider).

2) Rendering adapter
- Introduce a helper in `app/routers/whatsapp.py`, e.g., `def _send_submenu_reply(tenant, phone, submenu_node, locale) -> str`:
  - Read tenant `whatsapp_config.provider`.
  - For `twilio`: return existing `_render_submenu` string (no change).
  - For `meta_cloud` (dummy):
    - Build a Meta Interactive payload (buttons or list) in memory.
    - Log it (INFO) with tenant, phone, and JSON payload.
    - Return a human‑readable text that clearly indicates dummy interactive buttons, e.g.:
      - For buttons: "[dummy-buttons] Book | Offers | Cancel\n(Reply with 1/2/3)"
      - For lists:   "[dummy-list] Choose one:\n1) Book\n2) Offers\n..."
- Replace direct calls to `_render_submenu` in Twilio webhook and bot next‑step with `_send_submenu_reply` so the provider path is respected.

3) Keep action execution unchanged
- Actions (`select_timeslot`, `show_offers`, `open_ticket`, `open_url`) continue to work the same; responses are simple text.

4) Logging and debug endpoint (optional but useful)
- Add `GET /v1/debug/whatsapp/interactive-preview` (JWT required) to output the exact interactive payload that would be sent for a given submenu node, based on provider and node options. Useful for QA without touching webhooks.

---

### Implementation steps (Admin UI)
1) Config UI
- Add Provider select.
- Conditionally show Meta Cloud fields (`phone_number_id`, `access_token`, `active_menu_id`).
- Keep Twilio fields and from‑number validation (both `+E164` and `whatsapp:+E164`).
- Update helper text to explain dummy Meta mode.

2) No UI changes needed for Menus/Triggers/Editor
- The existing Visual Menu Builder and Triggers remain unchanged; submenu rendering will switch automatically by provider at runtime.

---

### Testing plan
- Tenant setup:
  - Ensure capability `core.whatsapp_menu` enabled and a menu published (with 2–4 options; one >3 to test list layout).
- Config cases:
  1) Twilio provider
     - Send messages to Twilio dummy webhook. Expect classic text menus and number selection behavior.
  2) Meta Cloud provider (dummy)
     - Switch provider to `meta_cloud`, fill placeholders for `phone_number_id`, `access_token` (any strings are fine for dummy).
     - Trigger a submenu render via triggers or root (`Body="hi"`).
     - Check server logs for the interactive payload JSON.
     - User still receives a text that mimics buttons/list and can reply with numbers; flow advances as before.
- Optional: call the preview endpoint to inspect payload JSON for a specific submenu.

---

### Acceptance criteria
- Admin UI can save `meta_cloud` config (provider + fields) for a tenant.
- With provider `meta_cloud`, submenu render logs a Meta Interactive payload JSON and returns a text that clearly indicates dummy buttons/lists.
- With provider `twilio`, behavior remains identical to current TwiML text menus.
- Number‑based replies advance the menu for both providers.
- No regressions in Menus, Triggers, or Actions.

---

### Timeline
- Backend changes: 0.5 day (adapter, config defaults, optional preview endpoint).
- UI changes: 0.25 day (provider select + conditional fields + help text).
- Testing & docs: 0.25 day.

Total: ~1 day for the dummy Meta Cloud integration with Twilio fallback preserved.

---

### Next action
- I can start implementing immediately. If you already have preferred identifiers, provide an example `phone_number_id` and a placeholder `access_token` for `ss-salon` so I can prefill during testing; otherwise, I’ll use obvious dummy values like `"1234567890"` and `"dummy-access-token"`.