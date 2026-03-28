### Plan: Configure Twilio WhatsApp for tenant `ss-salon` and ensure inbound routing works

#### Objective
Set up Twilio (SID and WhatsApp number) for tenant `ss-salon`, store config in the app, wire the webhook, and verify that inbound messages (e.g., “hi”, “book”) reach the correct tenant menu, regardless of whether Twilio sends the `whatsapp:` prefix in the `To` value.

---

### 1) Tenant capability and menu prerequisites
- Super Admin → Settings → Modules & Capabilities for `ss-salon`:
  - Enable modules: `core`
  - Enable capability: `core.whatsapp_menu`
- Tenant Admin (or Super Admin) → WhatsApp → Menus:
  - Create or import a menu and Publish it (recommend `menu_id = "default"`)

Outcome: tenant is allowed to use the WhatsApp module and has a published menu for the bot.

---

### 2) Save Twilio config for `ss-salon`
Use UI or API.

- UI: WhatsApp → Config (for `ss-salon`)
  - Provider: `twilio`
  - From numbers: add `whatsapp:+14155238886` (keep the `whatsapp:` prefix)
  - Webhook secret: keep `dev` for now (used by our generic bot endpoint)
  - Account SID: `ACd8455419c9ff8c0e6b5bdbf9f870445f`
  - Auth Token: paste your real Twilio Auth Token (optional for dummy mode; required when enabling signature validation)
  - Default locale: `en`
  - Save

- API equivalent:
```
PUT /v1/tenants/ss-salon/whatsapp/config
Content-Type: application/json
{
  "provider": "twilio",
  "from_numbers": ["whatsapp:+14155238886"],
  "webhook_secret": "dev",
  "account_sid": "ACd8455419c9ff8c0e6b5bdbf9f870445f",
  "auth_token": "<YOUR_TWILIO_AUTH_TOKEN>",
  "locale_default": "en"
}
```

Outcome: tenant config is saved and will be used to resolve inbound WhatsApp messages.

---

### 3) Webhook in Twilio Console
- Go to Twilio → Messaging → WhatsApp Sandbox (or your WhatsApp Sender)
- Set When a message comes in:
  - `POST https://<your-domain>/v1/integrations/twilio/whatsapp/webhook`
- Save
- Sandbox note: Testers must send `join <your-sandbox-code>` to `+1 415 523 8886` first.

Outcome: Twilio forwards inbound WhatsApp messages to your app.

---

### 4) Routing fix for missing `whatsapp:` prefix (implemented)
- Server resolves tenant by `To` with or without the prefix.
  - We normalize the `To` variants: `raw`, `plain` (no prefix), and `prefixed` (with `whatsapp:`) and match any.
- No change needed on Twilio’s side — both `+14155238886` and `whatsapp:+14155238886` will route to `ss-salon` if configured.

Outcome: Inbound routing works whether Twilio includes the prefix or not.

---

### 5) Configure triggers for phrases (optional but recommended)
- WhatsApp → Triggers (tenant auto‑selected):
  - "hi" → `render_submenu` (menu `default`, priority 100)
  - "book" → `jump_node` (menu `default`, node `book_flow`, priority 90)
  - "enquiry" → `static_text` or `jump_node` to an `enquiry` node

Outcome: Users get friendly responses when sending common phrases.

---

### 6) Verify end‑to‑end
- Local test (no Twilio): Admin UI → WhatsApp → Triggers → Test a phrase
  - To: `whatsapp:+14155238886`
  - Message: `hi`
  - Expect TwiML with your menu text
- Sandbox test (real WhatsApp):
  - From your WhatsApp, send `hi` to `+1 415 523 8886` (after joining the sandbox)
  - Expect your menu reply; try `book` to hit the booking submenu

Outcome: Confidence that the path from Twilio to your tenant menu works.

---

### 7) (Optional) Harden for production
- Enable Twilio signature validation in your webhook (behind an env flag like `TWILIO_VALIDATE=true`) using the tenant’s `auth_token`.
- Add rate limiting per `From` number and structured logs.

Outcome: More secure and robust production behavior.

---

### Checklist for `ss-salon`
- [ ] Enable `core` module + `core.whatsapp_menu` capability
- [ ] Publish menu `default`
- [ ] Save WhatsApp Config with `from_numbers=["whatsapp:+14155238886"]`, SID, Auth Token
- [ ] Set Twilio webhook URL to `/v1/integrations/twilio/whatsapp/webhook`
- [ ] Add triggers for `hi`, `book`, `enquiry`
- [ ] Test via UI and Twilio Sandbox
- [ ] (Optional) Turn on signature validation in prod

If you share your public base URL, I can confirm the exact webhook URL and help test the flow right away.