### Goal
Design and implement a dynamic WhatsApp Menu Builder that Tenant Admins can fully configure per tenant (salon, clinic, store, etc.). WhatsApp bot will read the published menu for the tenant, identified by the tenant’s WhatsApp number, and drive the chat flow (with sub‑menus and actions like book appointment, cancel, view offers, etc.).

---

### High‑level architecture
- Data source of truth: MongoDB collections under your existing storage service.
- Admin APIs (JWT): Tenant Admin builds menus (drafts), publishes them, and configures WhatsApp numbers/secrets from the Settings page.
- Bot APIs (tokenless but secured): WhatsApp integration fetches the published menu by WhatsApp “from” number and processes user replies with a small state engine.
- Access control: tied into your module/capability system — add `core.whatsapp_menu`. Tenant Admins (Option B) auto‑access tenant‑enabled capabilities; Staff need per‑user caps to access admin UIs (if applicable).

---

### Data model (Mongo)
1) Collection: `whatsapp_menus`
- One tenant can have multiple menus (e.g., experiments) with drafts and a single current published version per menu id.
- Document shape:
  ```json
  {
    "tenant": "ss-salon",
    "menu_id": "default",            // arbitrary id: "default", "promo_oct", etc.
    "name": "Default Menu",
    "status": "draft",               // draft | published
    "version": 3,                     // increment on publish
    "tree": {
      "root": "root",
      "nodes": [
        {
          "id": "root",
          "type": "submenu",
          "title": "Welcome to SS Salon!",
          "prompt": "Please choose an option:",
          "options": [
            { "key": "1", "label": "Book appointment", "next": "book_flow" },
            { "key": "2", "label": "View professional offers", "next": "offers" },
            { "key": "3", "label": "Enquiry", "next": "enquiry" }
          ]
        },
        {
          "id": "book_flow",
          "type": "submenu",
          "title": "Book Appointment",
          "prompt": "Select service:",
          "options": [
            { "key": "1", "label": "Haircut", "next": "pick_slot" },
            { "key": "2", "label": "Facial", "next": "pick_slot" }
          ]
        },
        {
          "id": "pick_slot",
          "type": "action",
          "action": "select_timeslot",
          "params": { "slot_source": "salon.professionals" },
          "requires_caps": ["salon.appointments"]
        },
        {
          "id": "offers",
          "type": "action",
          "action": "show_offers"  
        },
        {
          "id": "enquiry",
          "type": "action",
          "action": "open_ticket",
          "params": { "category": "general" }
        }
      ]
    },
    "locales": {
      "en": { /* optional per‑node label overrides */ },
      "ta": { /* Tamil overrides */ }
    },
    "created_at": "2025-12-02T10:00:00Z",
    "updated_at": "2025-12-02T10:05:00Z",
    "published_at": null,
    "published_by": null
  }
  ```
- Validation rules:
  - `root` must exist and be a node id in `nodes`.
  - Graph must be acyclic and max depth configurable (e.g., 6). 
  - `submenu.options[*].key` unique within node; keys typically `"1".."9"`.
  - `action` nodes can specify `requires_caps` which will be enforced at runtime; if capability is missing for tenant, the engine returns a friendly “not available” message.

2) Collection: `whatsapp_sessions` (optional but recommended)
- Keep simple conversational state per customer phone.
- Shape:
  ```json
  {
    "tenant": "ss-salon",
    "phone": "+91XXXXXXXXXX",
    "menu_id": "default",
    "last_node": "book_flow",
    "ctx": { "service": "Haircut" },
    "expires_at": ISODate("2025-12-02T10:30:00Z")
  }
  ```
- TTL index on `expires_at` (e.g., 30 minutes) to auto‑clear sessions.

3) Optional: `whatsapp_logs`
- Keep bot request/response logs for debugging (respect privacy and PII policies).

4) Tenant config extension
- In `tenants` document (already have `whatsapp_config`):
  ```json
  {
    "whatsapp_config": {
      "provider": "twilio",           // or "meta_cloud", "dummy"
      "from_numbers": ["+91XXXX"],     // numbers for this tenant; can support multiple
      "webhook_secret": "...",        // HMAC secret to validate bot webhook calls
      "locale_default": "en"
    }
  }
  ```
- Add index aiding quick lookup by `whatsapp_config.from_numbers` if you plan frequent reverse lookups.

---

### Capability & module integration
- Add to registry (`app/modules/registry.py`):
  - Module: already have `core`
  - New capability: `core.whatsapp_menu` (group: Core, default: false)
- Guard Admin endpoints with `ensure_capability_enabled("core.whatsapp_menu")` so only tenants enabled by Super Admin can use the menu builder. With Option B, Tenant Admin auto‑accesses once tenant has the cap.

---

### Backend APIs (FastAPI)
Admin (JWT; Tenant Admin or Super Admin depending on capability):
- `GET /v1/tenants/{tenant}/whatsapp/menus` → list menus (both draft and published latest)
- `GET /v1/tenants/{tenant}/whatsapp/menus/{menu_id}` → fetch a draft or latest published
- `POST /v1/tenants/{tenant}/whatsapp/menus` → upsert draft
  - Body: `{ menu_id, name, tree, locales }`
- `POST /v1/tenants/{tenant}/whatsapp/menus/{menu_id}/publish` → validate + mark a new published version
  - Auto‑increment `version`, set `status="published"`, `published_at`, `published_by` (from JWT)
- `DELETE /v1/tenants/{tenant}/whatsapp/menus/{menu_id}` → delete draft (do not delete published history unless explicitly requested)
- `GET /v1/tenants/{tenant}/whatsapp/templates` → returns starter templates based on `category` (`salon`, `clinic`, `store`) to bootstrap a menu
- `PUT /v1/tenants/{tenant}/whatsapp/config` and `GET /v1/tenants/{tenant}/whatsapp/config`
  - Manage `whatsapp_config` (numbers, webhook_secret, provider settings)
  - Guard modification of config to Tenant Admin/Super Admin; numbers must be E.164.

Bot (secure):
- `GET /v1/bot/whatsapp/menu?from=+91xxx&locale=en&menu_id=default`
  - Resolve tenant by `from` number (inside `whatsapp_config.from_numbers`).
  - Return the latest `published` menu (or 404 if none).
- `POST /v1/bot/whatsapp/next`
  - Headers: `X-Tenant: <tenant>`, `X-From: <whatsapp-number>`, `X-Signature: HMAC-SHA256(body, webhook_secret)`
  - Body: `{ phone:"+91...", input:"2", session_id?:"...", menu_id?:"default", locale?:"en" }`
  - Engine resolves next node from session state and returns:
    ```json
    { "reply": "Choose a time slot:\n1) 10:00\n2) 10:30\n...", "session": { "last_node": "pick_slot", "ctx": { ... } } }
    ```
  - If node is an `action`, executes or delegates accordingly (see below). 

Security:
- Validate `X-Signature` using tenant’s `webhook_secret` to prevent abuse.
- Optionally restrict `POST /bot/whatsapp/next` by IP allowlist of your provider.

---

### Menu engine (server helper)
- Input: `menu tree`, `current node (or root)`, `user input (text)`, `session ctx`, `locale`, `tenant`.
- Behavior outline:
  ```python
  def step(menu, node_id, user_input, ctx, tenant, locale):
      node = find_node(menu, node_id)
      if node.type == 'submenu':
          # Map a numeric key to next node
          choice = user_input.strip()
          opt = next((o for o in node.options if o['key'] == choice), None)
          if not opt:
              return { 'reply': render_submenu(node, locale, error='Invalid choice'), 'next_node': node.id, 'ctx': ctx }
          return { 'reply': render_node(find_node(menu, opt['next']), locale), 'next_node': opt['next'], 'ctx': ctx }
      elif node.type == 'action':
          # Capability guards
          if not tenant_has_caps(tenant, node.get('requires_caps', [])):
              return { 'reply': 'This option is not available for this tenant.', 'next_node': 'root', 'ctx': ctx }
          # Execute action
          return execute_action(node.action, node.params, ctx, tenant)
      else:
          return { 'reply': 'Unsupported node', 'next_node': 'root', 'ctx': ctx }
  ```
- Common actions to implement initially:
  - `show_offers`: render a list from your promotions capability (`core.promotions` if you plan to use it)
  - `open_ticket`: collect a short free‑text and store as an enquiry document, return ticket id
  - `select_timeslot` (Salon): read professionals/slots (`salon.professionals`, `salon.appointments`) and render available slots; on next input, persist appointment via existing `appointments` logic or a dedicated endpoint
  - `book_doctor` (Clinic): similar to salon flow but with clinic data sources
  - `open_url`: reply with a URL; optionally shorten
  - `api_call`: POST to an internal API configured in `params` (use an allowlist)

- Rendering:
  - Locale fallback: try `locales[locale]` overrides for labels; else default strings.
  - Submenu prompt pattern:
    ```
    <title>\n<prompt>\n1) Option A\n2) Option B\n...\nReply with a number.
    ```

---

### Admin UI (Tenant Admin page)
- New page: “WhatsApp Menu” under Settings (requires `core.whatsapp_menu`).
- Features:
  - Select or create a menu (menu_id, name)
  - Tree editor:
    - Add node (submenu/action)
    - Edit labels/prompts; add options (key, label, next)
    - For action nodes: choose action type and fill params with small forms (e.g., pick professional resource for salon)
    - Reorder with drag‑and‑drop (optional v1 can use up/down buttons)
  - Validation: highlight missing next nodes, duplicate keys, depth limit
  - Publish button: shows validation result; on success, confirms and publishes (bumps version)
  - Templates: “Import template for Salon/Clinic/Store” (loads starter JSON into the editor)
  - WhatsApp Config panel: set from_numbers, webhook_secret, provider

- UI API usage:
  - Load: `GET /tenants/{tenant}/whatsapp/menus`, `GET /tenants/{tenant}/whatsapp/menus/{id}`
  - Save Draft: `POST /tenants/{tenant}/whatsapp/menus`
  - Publish: `POST /tenants/{tenant}/whatsapp/menus/{id}/publish`
  - Config: `GET/PUT /tenants/{tenant}/whatsapp/config`

---

### Mapping to current codebase
- Registry: add capability entry
  ```python
  {"id": "core.whatsapp_menu", "type": "capability", "module": "core", "group": "Core", "label": "WhatsApp Menu Builder", "description": "Configure WhatsApp bot menus", "default": False}
  ```
- Deps/guards: use `ensure_capability_enabled("core.whatsapp_menu")` for the admin menu endpoints. With Option B, Tenant Admins auto‑access once enabled.
- Tenants storage: `whatsapp_config` already normalized in `Storage.get_tenant_settings`; extend to handle `from_numbers` and ensure it’s a list of E.164 strings.
- New Storage methods in `app/services/storage_mongo.py`:
  - `list_whatsapp_menus(tenant)`
  - `get_whatsapp_menu(tenant, menu_id, status=None)`
  - `upsert_whatsapp_menu_draft(tenant, doc)`
  - `publish_whatsapp_menu(tenant, menu_id, user_id)` (atomically set status/version)
  - `delete_whatsapp_menu(tenant, menu_id)` (draft only)
  - `resolve_tenant_by_whatsapp_number(number)` → searches `tenants` by `whatsapp_config.from_numbers`
  - `upsert_whatsapp_session`, `get_whatsapp_session` (with TTL index)

---

### Salon vs Clinic vs Store — templates (examples)
- Salon template:
  - Root: Book appointment, View professional offers, Enquiry
  - Submenu: Select service → Select time slot → Confirm booking
  - Requires caps: `salon.professionals`, `salon.appointments`
- Clinic template:
  - Root: Book doctor, Cancel appointment, Enquiry
  - Submenus: Select department → Select doctor → Select time slot
  - Requires caps: `salon.appointments` (or introduce `clinic.appointments` later)
- Store template:
  - Root: View catalog, Track order, Enquiry
  - Actions: `store.catalog` listing top items, order status lookup by order id

We can store these starter JSONs server‑side and return through `GET /tenants/{tenant}/whatsapp/templates?category=salon|clinic|store`.

---

### Security & compliance
- HMAC validation for bot endpoints using tenant’s `webhook_secret` prevents spoofing.
- Rate limiting and abuse detection on bot endpoints by `from` number and phone.
- Sanitize and validate all text sent back to WhatsApp (length limits, character sets).
- PII: protect `whatsapp_logs`; allow disabling logging in prod.

---

### Testing plan
- Unit: menu validation (root exists, no cycles, unique keys), capability gating, number→tenant resolution, engine step transitions.
- API: CRUD draft, publish, fetch published by `from` number, config update authorization.
- Engine integration: salon booking happy path and invalid inputs.
- UI: editor validation, publish flow, templates import.

---

### Rollout plan
1) Backend:
- Add capability to registry and deploy.
- Implement storage and admin endpoints; add indexes (menu unique by `tenant+menu_id+status=pending/published`, session TTL).
- Implement bot endpoints + HMAC.
2) UI:
- Add WhatsApp Menu page (Tenant Admin). Use existing auth and tenant selection.
- Add WhatsApp Config panel under Settings.
3) Configure tenants:
- Super Admin enables `core` module and `core.whatsapp_menu` capability for target tenants.
- Tenant Admin configures `from_numbers`, builds menu, and publishes.
4) Integrate provider webhook to call `/bot/whatsapp/next`.

---

### Example payloads
- Create/update draft:
  ```http
  POST /v1/tenants/ss-salon/whatsapp/menus
  {
    "menu_id": "default",
    "name": "Default Menu",
    "tree": { ... },
    "locales": { "en": { /* optional */ } }
  }
  ```
- Publish:
  ```http
  POST /v1/tenants/ss-salon/whatsapp/menus/default/publish
  ```
- Bot fetch by number:
  ```http
  GET /v1/bot/whatsapp/menu?from=%2B91XXXX&locale=en&menu_id=default
  ```
- Bot step:
  ```http
  POST /v1/bot/whatsapp/next
  X-Tenant: ss-salon
  X-From: +91XXXX
  X-Signature: <hmac>

  { "phone": "+91USER", "input": "1", "menu_id": "default", "locale": "en" }
  ```

---

### Decisions requested
- Confirm new capability `core.whatsapp_menu` is acceptable under the `core` module.
- For first release, are these actions enough: `select_timeslot`, `show_offers`, `open_ticket`, `open_url`, `api_call`? We can add `catalog_browse` and `order_status` for Store soon after.
- Do you want sessions (to support multi‑step flows) in v1, or keep stateless (return submenu text only) for the first cut?

Once you confirm, I’ll proceed to implement the backend endpoints and the Tenant Admin UI page following this plan.