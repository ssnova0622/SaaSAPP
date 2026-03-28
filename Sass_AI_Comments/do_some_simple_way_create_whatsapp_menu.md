### Goal
A very simple way for a store owner (non-technical) to create and manage a WhatsApp menu.

Good news: your project already has a WhatsApp menu system in the backend and an admin UI module. We can make it “owner‑friendly” by adding a no‑code wizard and templates on top of the existing APIs, without heavy backend changes.

### What “simple” should look like
- Zero JSON editing. Plain forms with presets.
- 4 short steps, always skippable with safe defaults.
- Built‑in templates for common store types.
- Instant preview and one‑click publish.

### Proposed owner flow (4‑step wizard)
1) Basics
   - Fields: `Menu name`, optional `Welcome message` per language, default `menu_id` auto = `default`.
   - Pick a Template: Retail, Restaurant, Salon, Pharmacy, “Blank”.

2) Items & Actions
   - Drag‑drop list of options (buttons) with: `Label`, `Action` (select from a dropdown), optional `Submenu`.
   - Common actions already implemented in backend:
     - `render_submenu` / `jump_node`
     - `invoke_action` with your built‑in actions like `store.browse_catalog`, `store.check_product`, `store.track_order`, `core.open_url`.
   - For each item, show a short hint of what it does.

3) Triggers (how users start)
   - Offer a default trigger: “hi/hello” → show root menu.
   - Let owner add synonyms (exact/prefix/contains), per locale if needed.
   - Example: `match: { type: 'contains', value: 'menu' }` → `action: { kind: 'render_submenu', menu_id: 'default' }`.

4) Preview & Publish
   - Live preview: WhatsApp‑style bubble rendering of the root menu and submenus.
   - Test message: send a test via your existing Twilio webhook helper (client already has a `testTriggerWebhook` in `admin_ui/src/api/whatsapp.tsx`).
   - Buttons: Save Draft, Publish.

### How this maps to your existing APIs
Backend routes (already present in `app/routers/whatsapp.py`):
- Menus
  - `POST /tenants/{tenant}/whatsapp/menus` → upsert draft (`upsert_whatsapp_menu`).
  - `POST /tenants/{tenant}/whatsapp/menus/{menu_id}/publish` → publish.
  - `GET /tenants/{tenant}/whatsapp/menus` and `GET /tenants/{tenant}/whatsapp/menus/{menu_id}`.
- Triggers
  - `POST /tenants/{tenant}/whatsapp/triggers` (create)
  - `PATCH /tenants/{tenant}/whatsapp/triggers/{trigger_id}` (update)
  - `GET /tenants/{tenant}/whatsapp/triggers` (list)

Admin UI client (already present in `admin_ui/src/api/whatsapp.tsx`):
- `upsertMenu`, `publishMenu`, `listMenus`, `getMenu`, `createTrigger`, `updateTrigger`, `listTriggers`, and `testTriggerWebhook`.

This means you can implement the simple wizard entirely in the admin UI with minimal or zero backend changes.

### Templates (ready to plug in)
You can ship a small JSON catalog in the UI with safe defaults. Here are 3 examples you can paste into a `templates.ts` file in the WhatsApp UI module and feed into the wizard.

Retail example (catalog + order status):
```ts
export const retailTemplate = {
  menu_id: 'default',
  name: 'Retail Store Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome! How can we help?' },
    items: [
      { id: 'browse', label: { en: '🛍️ Browse Catalog' }, action: { kind: 'invoke_action', action_id: 'store.browse_catalog' } },
      { id: 'check', label: { en: '🔎 Check Product' }, action: { kind: 'invoke_action', action_id: 'store.check_product' } },
      { id: 'track', label: { en: '📦 Track Order' }, action: { kind: 'invoke_action', action_id: 'store.track_order' } },
      { id: 'offers', label: { en: '✨ Offers' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Latest offers coming soon!' } } }
    ]
  },
  locales: { en: {} }
}
```

Restaurant example (book table + menu URL):
```ts
export const restaurantTemplate = {
  menu_id: 'default',
  name: 'Restaurant Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome to our restaurant!' },
    items: [
      { id: 'table', label: { en: '🍽️ Book a Table' }, action: { kind: 'invoke_action', action_id: 'core.open_url', params: { url: 'https://example.com/book' } } },
      { id: 'menu', label: { en: '📖 View Menu' }, action: { kind: 'core.open_url', action_id: 'core.open_url', params: { url: 'https://example.com/menu' } } },
      { id: 'offers', label: { en: '✨ Today’s Specials' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Ask for chef special!' } } }
    ]
  },
  locales: { en: {} }
}
```

Salon example (timeslot flow):
```ts
export const salonTemplate = {
  menu_id: 'default',
  name: 'Salon Menu',
  tree: {
    id: 'root',
    title: { en: 'Welcome to our salon!' },
    items: [
      { id: 'book', label: { en: '💇 Book a Slot' }, action: { kind: 'invoke_action', action_id: 'core.select_timeslot' } },
      { id: 'offers', label: { en: '✨ Offers' }, action: { kind: 'invoke_action', action_id: 'core.static_text', params: { title: 'Festive offers available!' } } }
    ]
  },
  locales: { en: {} }
}
```

Default trigger for any template:
```ts
export const defaultTrigger = (menu_id = 'default') => ({
  trigger_id: 'hello_default',
  match: { type: 'contains', value: 'hello' },
  action: { kind: 'render_submenu', menu_id },
  enabled: true,
  priority: 100,
})
```

Wizard should take the chosen template, let the owner tweak labels/URLs, then call:
```ts
await upsertMenu(tenant, { menu_id, name, tree, locales })
await createTrigger(tenant, defaultTrigger(menu_id))
await publishMenu(tenant, menu_id)
```

### UI components to add (minimal)
- `WhatsApp/Templates.ts` with the presets above.
- `WhatsApp/MenuWizard.tsx`: steps, state, and calls to the existing API helpers.
- Add a “Create Menu” button in `WhatsApp/MenusIndex` that opens the wizard. Keep `MenuEditor` for advanced users.
- In step 4, use `testTriggerWebhook(toNumber, 'hello')` to validate the flow to a sandbox number.

### Permissions and safety
- Capability gate is already in place: `core.whatsapp_menu` check exists on endpoints.
- Store owners will only see their tenant; make sure UI reads `tenant` from the auth/tenant selector.
- Validation already exists server‑side (`_validate_menu_tree`, trigger payload validation). Keep UI validation light and friendly.

### Optional tiny backend helpers (if you want it even simpler)
- A read‑only endpoint that returns the built‑in templates so UI doesn’t ship them hardcoded.
- A convenience endpoint `POST /tenants/{tenant}/whatsapp/menus/simple` that accepts a compact payload `{ template: 'retail', tweaks: {...} }` and internally performs upsert + default trigger + publish. This is optional because the UI can already orchestrate the 3 existing calls.

### Summary
- You already have the backend and client APIs required.
- Add a small wizard and templates in the admin UI to make it "one‑click" for store owners.
- Publish flow: choose template → tweak labels/links → save draft → create default trigger → publish → test.

If you want, I can draft the exact `MenuWizard.tsx` skeleton and the `templates.ts` file to paste into your UI.