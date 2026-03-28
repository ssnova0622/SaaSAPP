### Plan: Configure “hi”, “book”, “enquiry” text in Admin UI and trigger menus to customers

#### 1) Preconditions (one‑time per tenant)
- Super Admin enables for the tenant:
  - Modules: core
  - Capability: core.whatsapp_menu
- Tenant Admin (or Super Admin) publishes at least one WhatsApp menu:
  - WhatsApp → Menus → Create/Edit → Publish (e.g., menu_id = "default")
  - Ensure it contains nodes you want to jump to (e.g., `book_flow`, `enquiry`).
- Configure WhatsApp number:
  - WhatsApp → Config → set `from_numbers` (e.g., +911234567890) and `webhook_secret` (dev: "dev"). Save.

#### 2) Where to configure triggers in Admin UI
- Go to Admin UI → WhatsApp → Triggers (visible when capability `core.whatsapp_menu` is enabled).
- You can Create/Edit/Delete triggers that map incoming free‑text to menu actions.

#### 3) Trigger fields to fill
- trigger_id: short unique id (e.g., `greeting-hi`, `book-shortcut`, `enquiry-shortcut`).
- match:
  - type: exact | prefix | contains | regex (case‑insensitive)
  - value: the phrase to match (e.g., `hi`, `book`, `enquiry`).
  - locale (optional): limit to a locale (e.g., `en`).
- action:
  - kind: render_submenu | jump_node | static_text | invoke_action
  - menu_id: menu to use (usually `default`).
  - node_id: submenu/action node id within that menu (required for jump_node/invoke_action).
  - text: for static_text replies (optional localized map).
- enabled: ON/OFF.
- priority: higher number wins when multiple triggers match; order by importance (e.g., greeting > book > help).

#### 4) Examples you asked for
- “hi” → show main options:
  - trigger_id: greeting-hi
  - match: { type: exact, value: "hi" }
  - action: { kind: render_submenu, menu_id: "default" }
  - enabled: true, priority: 100
- “book” → go to booking submenu:
  - trigger_id: book-shortcut
  - match: { type: contains, value: "book" }
  - action: { kind: jump_node, menu_id: "default", node_id: "book_flow" }
  - enabled: true, priority: 90
- “enquiry” → go to enquiry submenu (or send a text):
  - Option A (menu jump):
    - trigger_id: enquiry-shortcut
    - match: { type: contains, value: "enquiry" }
    - action: { kind: jump_node, menu_id: "default", node_id: "enquiry" }
  - Option B (static text):
    - trigger_id: enquiry-text
    - match: { type: contains, value: "enquiry" }
    - action: { kind: static_text, text: "Please reply with your question; our team will contact you." }

#### 5) Test the triggers quickly
- Use the built‑in Test box on the Triggers page (if available), or call the dummy Twilio webhook:
  - POST /v1/integrations/twilio/whatsapp/webhook
  - JSON body: { "From":"+911112223334", "To":"+911234567890", "Body":"hi" }
  - Expected: TwiML XML with your root menu options. Try `Body: "book"` and see booking submenu.

#### 6) How it works at runtime
- When a message arrives (e.g., “hi”):
  1) System normalizes the text (lowercase, trim) and loads enabled triggers for the tenant.
  2) Matches in priority order. On first match, runs the trigger action.
  3) If no trigger matches, it falls back to the current menu session (or renders the default menu root).

#### 7) Best practices
- Keep trigger phrases short and unambiguous; prefer `exact` or `contains` over `regex` unless needed.
- Use priorities to control overlaps:
  - Example: `hi` (100) above `help` (80)
- For multilingual tenants, add locale‑specific triggers (e.g., `ta: வணக்கம்` → render_submenu).
- Ensure the `node_id` you jump to exists in the published menu.

#### 8) Limits and validation (safety)
- trigger_id ≤ 64 characters.
- match.value ≤ 256 characters.
- static_text ≤ 1000 characters.
- Regex patterns are compiled safely; invalid regex returns 422.

#### 9) Roles and permissions
- Super Admin can manage triggers for any tenant.
- Tenant Admin can manage triggers for their tenant (Option B: they auto‑access when capability is enabled).
- Staff do not access WhatsApp admin pages unless you grant them `core.whatsapp_menu` explicitly and your UI allows it.

#### 10) Troubleshooting
- Trigger doesn’t fire: check Enabled = true, Priority ordering, and that the match type/value is correct (lowercased).
- 404 “No published menu”: publish the menu first (WhatsApp → Menus → Publish).
- Jump to node fails: verify `node_id` exists in the menu.
- Webhook says “Unknown destination number”: ensure tenant’s `from_numbers` includes the `To` number used.

#### 11) Rollout checklist (per tenant)
- [ ] core module + core.whatsapp_menu capability enabled
- [ ] WhatsApp Config saved with at least one from_number
- [ ] Menu published (menu_id = default recommended)
- [ ] Triggers created for “hi”, “book”, “enquiry” (enabled, with sensible priorities)
- [ ] Webhook tested with “hi” and “book”

If you want, I can also add the WhatsApp → Triggers UI (List + Create/Edit + Priority + Test box) in your Admin UI now so you can manage these without using API calls.