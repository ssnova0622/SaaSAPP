### Plan to enable “hi” and “book” messages to show options (Option 2 — Configurable Triggers)

#### What you’ll get
- Per‑tenant “triggers” that map incoming phrases to actions:
  - Match types: `exact`, `prefix`, `contains`, `regex` (case‑insensitive)
  - Actions on match: `render_submenu` (show a menu), `jump_node` (go to specific submenu), `static_text` (send custom text), `invoke_action` (run an action node)
  - Enabled flag, priority ordering, optional locale filter
- Evaluated before the normal menu flow, so “hi” or “book” will directly show the options you want.

---

### 1) Backend — Data model and APIs
- Collection: `whatsapp_triggers`
  - Shape:
    ```json
    {
      "tenant": "<tenant-id>",
      "trigger_id": "greeting-hi",
      "match": { "type": "exact|prefix|contains|regex", "value": "hi", "locale": "en" },
      "action": { "kind": "render_submenu|jump_node|static_text|invoke_action", "menu_id": "default", "node_id": "book_flow", "text": "..." },
      "enabled": true,
      "priority": 100,
      "updated_at": "...",
      "updated_by": "..."
    }
    ```
  - Indexes: `{ tenant, enabled, priority }` to fetch enabled triggers in priority order.
- Admin endpoints (JWT, requires `core.whatsapp_menu` capability):
  - `GET /v1/tenants/{tenant}/whatsapp/triggers` (list)
  - `POST /v1/tenants/{tenant}/whatsapp/triggers` (create)
  - `PATCH /v1/tenants/{tenant}/whatsapp/triggers/{trigger_id}` (update)
  - `DELETE /v1/tenants/{tenant}/whatsapp/triggers/{trigger_id}` (delete)
  - Optional: `POST /v1/tenants/{tenant}/whatsapp/triggers/reorder` (bulk set priorities)
- Validation:
  - Safe regex compilation and length limits
  - If action references a menu/node, verify the menu exists and node id is present (warn if not published yet)

---

### 2) Backend — Bot integration
- At the start of Twilio webhook and `/v1/bot/whatsapp/next`:
  1) Normalize text: trim + lowercase (keep original for logs)
  2) Fetch enabled triggers for tenant by priority
  3) Match by type:
     - `exact`: `text == value`
     - `prefix`: `text.startswith(value)`
     - `contains`: `value in text`
     - `regex`: safe compiled regex test
  4) On match, perform action:
     - `render_submenu`: load published menu and render root (or a given submenu)
     - `jump_node`: render specific submenu/node
     - `static_text`: send `action.text` (can include simple numbered options)
     - `invoke_action`: run action node and return its message
  5) If nothing matches: continue existing session logic (or show root if there’s no session)

---

### 3) Admin UI — WhatsApp > Triggers
- New page under the WhatsApp module:
  - List triggers: columns for `trigger_id`, match type/value, action, enabled, priority (drag to reorder)
  - Create/Edit dialog:
    - Match: type/value + optional locale
    - Action: picker for action kind; for `render_submenu`/`jump_node` show dropdowns of menus and nodes; for `static_text` show textarea; for `invoke_action` show action picker
    - Enabled toggle and priority
  - Test input box: type “hi” or “book” to preview what would be sent

---

### 4) Defaults and quick setup
- We’ll seed helpful defaults for each tenant (you can edit/delete later):
  - `exact: "hi"` → `render_submenu` of `default` menu
  - `exact: "hello"` → `render_submenu` of `default` menu
  - `contains: "book"` → `jump_node` to `book_flow` (if that node exists)

---

### 5) How you will configure “hi” and “book” (after delivery)
- Go to: Admin UI → WhatsApp → Triggers → New Trigger
- Example A — “hi” shows main options:
  - Match: type `exact`, value `hi`
  - Action: `render_submenu`, menu `default`
  - Enabled: ON, Priority: 100
- Example B — “book” jumps to booking options:
  - Match: type `contains`, value `book`
  - Action: `jump_node`, menu `default`, node `book_flow`
  - Enabled: ON, Priority: 90

---

### 6) Timeline and testing
- Delivery: ~1 day for backend + ~0.5 day for UI polish.
- Tests:
  - Configure the two triggers above
  - Send messages to the dummy Twilio webhook:
    - `Body=hi` → reply with the root submenu
    - `Body=book` → reply with the booking submenu text

---

### 7) What I need from you (optional now)
- Exact phrases you want pre‑seeded besides `hi`, `hello`, `book` (any language variants?)
- Whether you want `regex` matching enabled in v1 or keep it to exact/prefix/contains only.

If you confirm, I’ll implement the triggers now with `hi`, `hello`, and `book` as defaults for your target tenant(s).