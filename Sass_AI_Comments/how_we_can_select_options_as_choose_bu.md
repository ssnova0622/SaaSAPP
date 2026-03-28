### Short answer
WhatsApp “buttons” are called Interactive Messages (Reply Buttons or List Messages). They cannot be returned in our current TwiML (XML) dummy webhook reply. To show buttons instead of asking users to type numbers, the server must send an outbound WhatsApp message using either:
- Meta WhatsApp Cloud API (recommended and simplest), or
- Twilio’s WhatsApp Interactive Messages (requires Twilio Content API or Conversations; not supported via TwiML).

Below I explain both options and exactly how to wire them into your current menu system so each submenu becomes a set of buttons or a list the user taps.

---

### Option A — Meta WhatsApp Cloud API (recommended)
Interactive types supported: `button` (max 3 reply buttons) and `list` (many options).

What we will do:
1) Extend tenant WhatsApp Config
   - Add provider: `meta_cloud`
   - Add fields: `phone_number_id`, `access_token`
2) Update webhook logic
   - When a submenu must be shown, send an outbound Interactive message (button or list) to the user’s phone using Meta’s `/messages` endpoint (instead of returning TwiML).
   - Keep your existing internal menu/session logic; only the rendering/response changes.
3) Map our menu nodes to Interactive messages
   - If submenu has ≤ 3 options → use `interactive.type = button`
   - If > 3 options → use `interactive.type = list`
4) Handle replies
   - Reply Buttons and List replies come back as structured payloads (`button_reply` or `list_reply` with an `id`) — map that `id` to our submenu option’s key/next node.

Meta send examples:
- Reply Buttons (≤ 3 options):
```
POST https://graph.facebook.com/v19.0/{phone_number_id}/messages
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "to": "+911112223334",
  "type": "interactive",
  "interactive": {
    "type": "button",
    "body": { "text": "Welcome to SS Salon\nPlease choose:" },
    "action": {
      "buttons": [
        { "type": "reply", "reply": { "id": "opt_1", "title": "Book" } },
        { "type": "reply", "reply": { "id": "opt_2", "title": "Offers" } },
        { "type": "reply", "reply": { "id": "opt_3", "title": "Cancel" } }
      ]
    }
  }
}
```
- List Message (> 3 options):
```
POST https://graph.facebook.com/v19.0/{phone_number_id}/messages
Authorization: Bearer {ACCESS_TOKEN}
Content-Type: application/json

{
  "messaging_product": "whatsapp",
  "to": "+911112223334",
  "type": "interactive",
  "interactive": {
    "type": "list",
    "body": { "text": "Welcome to SS Salon\nPlease choose:" },
    "action": {
      "button": "Choose",
      "sections": [
        {
          "title": "Menu",
          "rows": [
            { "id": "opt_1", "title": "Book" },
            { "id": "opt_2", "title": "Offers" },
            { "id": "opt_3", "title": "Cancel" },
            { "id": "opt_4", "title": "Test" }
          ]
        }
      ]
    }
  }
}
```
How we connect it to your menu tree:
- For each submenu option, set an `id` we control (e.g., `opt_1`, `opt_2`, …) and store a mapping `{id → submenu.options[key]}` (or simply use your option `key` as `id`).
- On inbound webhook, if the payload contains `interactive.button_reply.id` or `interactive.list_reply.id`, look it up, resolve `next` node, and continue the same way we do today.

Pros:
- Full WhatsApp feature set (buttons/lists) without Twilio constraints.
- No need to pre‑approve “session” content; messages are user‑initiated.

---

### Option B — Twilio Interactive Messages
Twilio supports WhatsApp Interactive Messages via their Content API/Conversations, not via TwiML response.

What changes:
- Keep `provider: twilio`.
- Instead of replying with TwiML XML, your webhook makes an outbound API call using Twilio’s Messages/Conversations + Content API to send an Interactive message.
- You must define Content templates or construct an interactive payload per Twilio docs, then send it using the Twilio REST API (the payload differs from Meta’s).

Basic flow (conceptual):
- Receive inbound webhook → detect we need to render a submenu → call Twilio’s API to send an interactive `button` or `list` message.
- Handle the reply webhook (Twilio will POST back the button/list selection payload); parse the `id` and map it to your menu option’s `next`.

Limitations:
- TwiML cannot render buttons; it only sends text/media. You must send a separate outbound message via the REST API.
- Twilio’s interactive support depends on Content API/Conversations features; setup is a bit more involved vs Meta Cloud.

---

### Changes needed in your app (small and safe)
- WhatsApp Config (Admin UI → WhatsApp → Config):
  - Add provider choice: `meta_cloud` (phone_number_id, access_token fields) in addition to existing `twilio`.
  - Optional: field `active_menu_id` to select which published menu to use by default.
- Backend (router):
  - If provider = `meta_cloud`:
    - When a submenu must be rendered, call Meta `/messages` with `interactive` payload as above (instead of returning TwiML).
    - When an action replies with text (e.g., `show_offers`), send a simple `text` message via the same endpoint.
  - If provider = `twilio` and you want buttons:
    - Replace TwiML reply with an outbound REST call that uses Twilio’s interactive format (Content API), and handle Twilio’s interactive reply webhook.
- Mapping:
  - For each submenu, choose `button` (≤3 options) or `list` (>3 options). Your Visual Menu Editor can auto‑choose and we can add a toggle to force list.

---

### Practical next step for you
- Easiest path: use Meta WhatsApp Cloud.
  1) Get a WhatsApp Business account and a test phone_number_id + access_token.
  2) In Admin UI → WhatsApp → Config set provider to `meta_cloud` and fill those fields.
  3) I’ll switch the webhook code path to render submenus as Interactive messages for `meta_cloud` (buttons for ≤3 options, list otherwise). No JSON editing needed in menus.

If you prefer to stay on Twilio and still want buttons, I can wire Twilio’s Interactive via Content API. It’s doable, just a bit more setup.

---

### FAQ
- Can I mix buttons and lists? Yes. We’ll auto‑select buttons for up to 3 options; lists for more. You can override per submenu.
- Are there limits? Buttons max 3; List supports up to 10 rows per section, multiple sections.
- Do triggers still work? Yes. You can keep “hi/book” triggers; they can also send an interactive reply instead of plain text.

---

### Tell me your preference
- Do you want me to implement `meta_cloud` interactive first (recommended) or Twilio interactive via Content API?
- If `meta_cloud`, please share your `phone_number_id` and a test `access_token` (you can DM securely), and I’ll enable button/list replies immediately.
- If Twilio interactive, I’ll add the Content API integration and a brief setup guide for your Twilio Console.