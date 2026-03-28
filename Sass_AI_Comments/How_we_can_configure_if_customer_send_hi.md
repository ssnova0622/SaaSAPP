### Short answer
- Right now (with the current bot), if a customer sends any free text like “hi” or “book” while they’re at the menu, the bot replies with the menu options automatically. It does this by returning “Invalid choice” followed by the menu, so the user sees the options without you needing to configure anything.
- If you want “hi” or “book” to jump directly to a specific menu or action (e.g., go straight to the booking submenu), add a small “trigger” layer to the bot. This lets you configure phrases → responses per tenant.

Below are both options in detail.

---

### Option 1 — Use current behavior (no extra setup)
- The WhatsApp webhook and bot handler already behave like this for non‑numeric input:
  - If the incoming message isn’t a recognized menu key (1–9), the bot responds with: “Invalid choice” + the current submenu rendered.
  - This means if a customer sends “hi” or “book”, they will see the options right away.
- To make the experience friendlier, edit the root submenu prompt in the Menu Builder to include a hint like: “Reply with a number. You can also type ‘hi’ to see this menu again.” The system will still show the menu when they type “hi”.

Pros:
- Zero additional configuration; works today.

Trade‑off:
- “book” (or any phrase) won’t jump into a specific submenu/action; it only shows the menu.

---

### Option 2 — Add configurable triggers (recommended)
If you want specific phrases to immediately show certain options or jump to a flow (e.g., “book” → booking submenu), add a Trigger layer. Here’s the design we can implement:

#### What you’ll be able to configure (per tenant)
- A list of triggers with:
  - Match type: `exact`, `prefix`, `contains`, or `regex` (case‑insensitive)
  - Phrase/value: e.g., `"hi"`, `"book"`, `"hello"`
  - Action on match:
    - `render_submenu` (show root or a specific submenu)
    - `jump_node` (move to a specific submenu node and render it)
    - `static_text` (send a prepared text with quick replies)
    - `invoke_action` (run an action node like `select_timeslot`)
  - Optional locale (so you can map “வணக்கம்” to the same behavior for Tamil)
  - Enabled flag and priority (higher priority triggers evaluated first)

Example trigger records:
```json
[
  {
    "tenant": "ss-salon",
    "trigger_id": "greeting-hi",
    "match": { "type": "exact", "value": "hi" },
    "action": { "kind": "render_submenu", "menu_id": "default" },
    "enabled": true,
    "priority": 100
  },
  {
    "tenant": "ss-salon",
    "trigger_id": "book-shortcut",
    "match": { "type": "contains", "value": "book" },
    "action": { "kind": "jump_node", "menu_id": "default", "node_id": "book_flow" },
    "enabled": true,
    "priority": 90
  }
]
```

#### Where it plugs into the bot
- At the start of the webhook handling (Twilio bridge or `/v1/bot/whatsapp/next`):
  1) Normalize input (trim, lower‐case).
  2) Load enabled triggers for the tenant, ordered by priority.
  3) Evaluate matches; on the first match, perform the configured action.
  4) If no trigger matches:
     - If there’s an active menu session, continue the normal flow.
     - If there’s no session, render the default menu’s root.

#### Admin UI (WhatsApp module → Triggers)
- You’ll get a simple page to:
  - Add/edit triggers (match type/value, pick action, select menu/node from dropdowns)
  - Enable/disable triggers
  - Drag to reorder priorities
  - Test a phrase against triggers with a preview reply

#### Behavior for your question
- “hi” → `render_submenu` of the default menu (shows options)
- “book” → `jump_node` to your booking submenu (immediate booking options)

---

### Which should you use?
- If your only requirement is “when user types hi/show menu” → you already have it. The current bot will respond with the menu for any non‑numeric text.
- If you also want shortcuts like “book” to jump right into a specific flow → use the Trigger feature. I can implement this now.

---

### If you want me to implement Triggers now
Here’s the minimal scope I’ll add:
- Backend (admin):
  - `GET/POST/PATCH/DELETE /v1/tenants/{tenant}/whatsapp/triggers` (guarded by `core.whatsapp_menu` capability)
  - Mongo collection `whatsapp_triggers` with indexes on `{ tenant, enabled, priority }`
- Backend (bot):
  - Evaluate triggers before menu/session logic
- Admin UI:
  - New page under WhatsApp: Triggers (list/create/edit/reorder)
- Defaults:
  - Auto‑create two greeting triggers for `"hi"` and `"hello"` to show the default menu

Time to deliver: about 1 working day for MVP (admin CRUD + bot evaluation), plus 0.5 day for UI polish.

If you approve, tell me the phrases you want out‑of‑the‑box (e.g., "hi", "hello", "book"). I’ll proceed with those as defaults and enable them for your target tenants.