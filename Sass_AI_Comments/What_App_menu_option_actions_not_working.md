### Fix applied: menu number selections now trigger the correct actions
I’ve updated the WhatsApp webhook logic so when a user sends a number (1, 2, 3, …) the system reliably follows the chosen option and executes the linked action node. This addresses the issue where selecting numbers didn’t call the expected action.

#### What changed (server)
- Robust choice parsing
  - The webhook now extracts the key from common inputs like `1`, `1)`, `1.`, `1 - book`, or `  2  ` via a helper (`_extract_choice`).
- Action execution from submenus
  - For submenu options pointing to an action node, it checks `requires_caps` (tenant capability gates) and runs the action if allowed:
    - `select_timeslot` → returns a list of timeslots (MVP)
    - `open_ticket` → returns a ticket acknowledgement (MVP)
    - `show_offers` → returns a basic offers message (MVP)
    - `open_url` → echoes the URL configured in node `params`
- Session awareness (Twilio webhook)
  - The bridge now persists `last_node` per phone so the user continues from the last submenu, not always from root. After an action runs, it resets to root.
  - When a trigger fires (like `hi`, `book`) and returns a submenu, the node is saved to session so the next numeric answer is interpreted at that submenu.
- Better fallbacks and messages
  - If the user sends an invalid number, it replies “Invalid choice” and re-renders the current submenu.
  - If a `next` node is misconfigured/missing, it returns “Menu is invalid” (so you can fix the editor).

#### What changed (Admin UI)
- Menu Editor already lets you define submenu `options` with keys (`"key": "1"`, …) and `next` pointing to action or submenu nodes. No change needed in UI for number selection.

---

### How to test quickly
1) Publish a menu with a submenu that has numbered options linking to action nodes, for example:
```json
{
  "root": "root",
  "nodes": [
    {
      "id": "root",
      "type": "submenu",
      "title": "Welcome",
      "prompt": "Choose:",
      "options": [
        { "key": "1", "label": "Book appointment", "next": "book" },
        { "key": "2", "label": "View offers", "next": "offers" },
        { "key": "3", "label": "Open URL", "next": "help_link" }
      ]
    },
    { "id": "book", "type": "action", "action": "select_timeslot", "requires_caps": ["salon.appointments"] },
    { "id": "offers", "type": "action", "action": "show_offers" },
    { "id": "help_link", "type": "action", "action": "open_url", "params": { "url": "https://example.com/help" } }
  ]
}
```
2) Use the dummy Twilio webhook (no real Twilio required):
- POST `/v1/integrations/twilio/whatsapp/webhook`
```json
{ "From": "+911112223334", "To": "whatsapp:+14155238886", "Body": "1" }
```
- Expected: TwiML response with the booking flow/start of timeslots.
- Try `Body: "2"` → shows offers. `Body: "3"` → returns the open_url text.
- Try `Body: "1)"` or `Body: "1 - book"` → still recognized as option 1.

3) Try with triggers first
- If you configured `hi` or `book` triggers, send `Body: "hi"` first to land on the submenu, then send `Body: "2"` → should run the linked action.

---

### Troubleshooting checklist if an action still doesn’t fire
- Check the menu’s node ids and next links
  - In the Menu Editor, verify each submenu option `next` points to an existing node id.
- Verify tenant capabilities for action nodes
  - If an action node has `requires_caps` (e.g., `["salon.appointments"]`), ensure the tenant has these capabilities enabled (Super Admin → Settings → Modules & Capabilities). The response “This option is not available for this tenant.” indicates a missing capability.
- Confirm webhook routing
  - WhatsApp Config must include your Twilio To number with prefix: `whatsapp:+14155238886`.
  - We also accept `+14155238886` from Twilio payloads.
- Inspect the response
  - If it says “Menu is invalid”, a `next` node id is missing/typo.
  - If it says “Invalid choice”, the `key` didn’t match the user’s input; ensure `key` is exactly `"1"`, `"2"`, etc.
- Triggers interaction
  - If a trigger renders a submenu, the next numeric input should work (session saves `last_node`). If you see it always goes to root, share the trigger + menu ids so I can confirm the flow.

---

### If you want deeper flows
I can extend sessions to support multi‑step flows (e.g., choose service → choose professional → choose time) and confirm/persist bookings. For now, the actions reply with MVP messages so you can validate number selection and action dispatch end‑to‑end.

If you can share one example menu JSON (root + nodes) and the exact number you send that fails, I’ll pinpoint the exact node/key or capability mismatch and adjust quickly.