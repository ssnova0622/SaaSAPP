### What is the WhatsApp Menu Builder in this project?

It’s a mini framework (backend + admin UI) to design, publish, and run interactive WhatsApp chat menus for each tenant. You draft a menu as a tree (submenus and actions), publish a version, attach “triggers” that recognize user messages (like keywords), and the bot renders the right submenu or runs an action. Sessions keep user progress so replies like “1” or “Back” move through the tree.

Below is a clear, practical overview of how it’s structured and how to use it.

---

### Core concepts

- Tenant-scoped content
  - Menus, triggers, sessions, and WhatsApp config are stored per tenant.
- Draft vs Published versions
  - You edit menus as drafts, then publish to freeze a version for the bot.
- Menu tree
  - Nodes are either `submenu` (with options) or `action` (runs logic).
- Triggers
  - Map a message match rule to a specific menu/node or to an action.
- Sessions
  - Track each phone’s position (`last_node`) and context (`ctx`) with a 30-minute TTL.
- Channels
  - Supports incoming webhooks from Twilio (XML replies) and Meta WhatsApp Cloud API (interactive payloads).

---

### Where to look in the code

- Backend router: `app/routers/whatsapp.py` (endpoints, rendering, trigger evaluation, session flow, actions, webhooks)
- Storage (Mongo): `app/services/storage_mongo.py` (menus, triggers, sessions CRUD)
- Admin UI API types: `admin_ui/src/api/whatsapp.tsx` (TypeScript types + client functions)

---

### Data model (high level)

- WhatsApp menu (admin UI type)
  - `admin_ui/src/api/whatsapp.tsx`
  - Type: `WhatsAppMenu` with fields: `tenant, menu_id, name, status, version?, tree?, locales?, updated_at/by, published_at/by`
- Menu tree
  - Validated by `_validate_menu_tree` in `whatsapp.py`.
  - Required:
    - `tree.root: string` – ID of the root node
    - `tree.nodes: Node[]` – each node must have a unique `id`
  - Node types:
    - `submenu`:
      - `title?: string`, `prompt?: string`
      - `options: { key: number|string, label: string, next?: node_id }[]`
      - Option `key`s must be unique within a submenu; `next` (if present) must point to an existing node.
    - `action`:
      - e.g., `{ id: 'nodeX', type: 'action', action_id: 'select_timeslot', params?: {...} }`
- Triggers
  - `admin_ui/src/api/whatsapp.tsx`
  - Type: `WhatsAppTrigger` with fields:
    - `match: { type: 'exact'|'prefix'|'contains'|'regex', value: string, locale?: string }`
    - `action: TriggerAction`
  - TriggerAction variants:
    - `{ kind: 'render_submenu', menu_id, node_id? }` – show root or a specified submenu
    - `{ kind: 'jump_node', menu_id, node_id }` – move session to a node without rendering text
    - `{ kind: 'static_text', text: string|Record<string,string> }`
    - `{ kind: 'invoke_action', menu_id, node_id }` – run the node’s backend action

---

### API endpoints you’ll use (tenant-scoped)

- Menus
  - `GET /tenants/{tenant}/whatsapp/menus` – list
  - `GET /tenants/{tenant}/whatsapp/menus/{menu_id}` – get draft/published/version
  - `POST /tenants/{tenant}/whatsapp/menus` – create or update draft
  - `POST /tenants/{tenant}/whatsapp/menus/{menu_id}/publish` – publish the draft
  - `DELETE /tenants/{tenant}/whatsapp/menus/{menu_id}` – delete draft and published history
- Triggers
  - `GET /tenants/{tenant}/whatsapp/triggers` – list
  - `POST /tenants/{tenant}/whatsapp/triggers` – create
  - `PATCH /tenants/{tenant}/whatsapp/triggers/{trigger_id}` – update
  - `DELETE /tenants/{tenant}/whatsapp/triggers/{trigger_id}` – delete
- Bot/test helpers
  - `GET /bot/menu?from=+..&locale=en&menu_id=default` – returns the rendered text for a given menu node
  - `POST /bot/next-step` – simulate a user reply with headers `X-Tenant`, `X-From`, `X-Signature` (used internally/testing)
- Webhooks
  - `POST /integrations/twilio/whatsapp/webhook` – Twilio inbound
  - `POST /integrations/meta/whatsapp/webhook` – Meta inbound
- WhatsApp config per tenant
  - `GET/PUT /tenants/{tenant}/whatsapp/config`

---

### How messages get handled at runtime

1. Inbound message hits Twilio or Meta webhook.
2. Tenant is resolved from the `To` number (`Storage.resolve_tenant_by_whatsapp_number`).
3. Triggers are evaluated against the message (`_evaluate_triggers`). If a trigger matches, its action is executed first.
4. If no trigger matches and there is an active session `last_node`, the reply is treated as a choice within the current submenu; numeric replies are decoded by `_extract_choice` and sent into the flow.
5. For submenu nodes:
   - The bot renders the submenu text (`_render_submenu`) or Meta interactive payload (`_build_meta_interactive_payload`).
   - The user replies with the option key (e.g., `1`).
6. For action nodes:
   - The bot executes `_run_action` with `action_id` and optional `params`.
   - Built-in actions include things like `select_timeslot`, store functions, `open_ticket`, `open_url`, etc.
7. Sessions are stored in Mongo with a TTL (default 30 minutes) via `Storage.upsert_whatsapp_session`.

---

### Built-in actions (examples)

- Timeslot booking FSM
  - `_start_timeslot_flow` and `_handle_timeslot_fsm` drive a small finite-state machine: pick professional → pick timeslot → confirm.
- Store-related examples
  - `_action_store_browse_catalog`, `_action_store_check_product`, `_action_store_track_order`
- Other actions
  - `_action_open_ticket`, `_action_show_offers`, `_action_open_url`
- Action registry
  - `_get_action_meta`, `_legacy_to_action_id`, and `_run_action` map `action_id` to the actual function. To add a new kind, implement a function and register it in `_run_action`.

---

### Minimal JSON examples

- Draft a simple menu
```json
{
  "menu_id": "default",
  "name": "Main menu",
  "tree": {
    "root": "root",
    "nodes": [
      {
        "id": "root",
        "type": "submenu",
        "title": "Welcome!",
        "prompt": "Choose an option:",
        "options": [
          { "key": 1, "label": "Book appointment", "next": "book" },
          { "key": 2, "label": "Track order", "next": "track" },
          { "key": 9, "label": "Open website", "next": "open_url" }
        ]
      },
      { "id": "book", "type": "action", "action_id": "select_timeslot" },
      { "id": "track", "type": "action", "action_id": "store_track_order" },
      { "id": "open_url", "type": "action", "action_id": "open_url", "params": { "url": "https://example.com" } }
    ]
  },
  "locales": { "en": { "root.title": "Welcome!" } }
}
```

- A trigger to open the menu when users say “menu”
```json
{
  "match": { "type": "exact", "value": "menu", "locale": "en" },
  "action": { "kind": "render_submenu", "menu_id": "default" },
  "enabled": true,
  "priority": 10,
  "trigger_id": "menu_en"
}
```

- A trigger to run an action directly
```json
{
  "match": { "type": "contains", "value": "book" },
  "action": { "kind": "invoke_action", "menu_id": "default", "node_id": "book" },
  "enabled": true,
  "priority": 5,
  "trigger_id": "book_any"
}
```

---

### Admin UI flows (what you’ll do)

1. Create/Update a draft menu
   - Use `POST /tenants/{tenant}/whatsapp/menus` with body `{ menu_id, name, tree, locales? }`.
2. Publish it
   - `POST /tenants/{tenant}/whatsapp/menus/{menu_id}/publish`.
3. Add triggers
   - Create via `POST /tenants/{tenant}/whatsapp/triggers` to map keywords to menus/nodes/actions.
4. Configure WhatsApp numbers and signing
   - `PUT /tenants/{tenant}/whatsapp/config` to set `from_number(s)` and webhook signing secret(s).
5. Test
   - Call `admin_ui/src/api/whatsapp.tsx:testTriggerWebhook(toNumber, "menu")` or hit the webhook with test payloads.

---

### Twilio vs Meta channel specifics

- Twilio webhook
  - Endpoint: `/integrations/twilio/whatsapp/webhook`
  - Input: Twilio-form fields like `From`, `To`, `Body`.
  - Output: XML `<Response><Message>...</Message></Response>`.
  - Signature: request can be HMAC-checked if configured.
- Meta WhatsApp Cloud API
  - Endpoint: `/integrations/meta/whatsapp/webhook`
  - Uses interactive message payloads (`_build_meta_interactive_payload`) where possible (list/buttons) for richer UX.

---

### How to add more actions when an option is chosen

- Add a new action handler in `whatsapp.py` (similar to `_action_open_url` etc.).
- Register it in `_run_action(tenant, action_id, params, locale)` so the `action_id` in your menu node can call it.
- If you need capability gating, add a check via `_tenant_has_caps(tenant, required_caps)`.
- Optionally expose any necessary admin configuration in the tenant settings or menu `params` to keep it no-code friendly from the UI.

---

### Validation and safety nets

- Menu tree integrity checks in `_validate_menu_tree` (unique IDs, valid `root`, no duplicate option keys, `next` nodes must exist).
- Triggers validated by `_validate_trigger_payload` (match/action schemas, required fields).
- Sessions are always coerced to `{ last_node, ctx }` structure and defaulted when missing.

---

### Practical checklist to get started

- [ ] Draft a menu JSON with a root submenu and a few actions
- [ ] Publish the menu
- [ ] Create at least one trigger to open the menu (e.g., “menu” or a greeting)
- [ ] Configure tenant WhatsApp settings (numbers, webhook secret)
- [ ] Test via webhook or the bot helper endpoints

---

### Want me to tailor this to your use case?
Tell me:
- Which business flow you need (booking, orders, support, payments, FAQs, multi-language?)
- What action(s) to add or parameters to expose in the menu editor
- Whether you’ll use Twilio or Meta Cloud API (UX differs slightly)

I can then propose the exact node JSON, trigger rules, and any small backend action additions needed.