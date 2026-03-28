### Plan: Configure Twilio WhatsApp for tenant `ss-salon` and verify end-to-end

#### 1) Enable tenant capability and prepare a menu (one-time)
- Super Admin → Settings → Modules & Capabilities
  - For tenant `ss-salon`, enable module `core` and capability `core.whatsapp_menu` → Save.
- Tenant Admin (or Super Admin) → WhatsApp → Menus
  - Create/Edit a menu and Publish it (recommended `menu_id = "default"`).

Outcome: `ss-salon` is allowed to configure WhatsApp and has a published menu the bot can serve.

---

#### 2) Save Twilio config for `ss-salon`
Use the Admin UI (preferred):
- WhatsApp → Config
  - Provider: `twilio`
  - From numbers: add `whatsapp:+14155238886` (you can paste `+14155238886`; the system now auto‑adds the `whatsapp:` prefix on save)
  - Account SID: `ACd8455419c9ff8c0e6b5bdbf9f870445f`
  - Auth Token: paste your Twilio Auth Token (optional for dev; required later if we enable signature validation)
  - Webhook secret: keep `dev` for now (used by the generic bot endpoint)
  - Default locale: `en`
  - Save

Or via API:
```
PUT /v1/tenants/ss-salon/whatsapp/config
Content-Type: application/json
{
  "provider": "twilio",
  "from_numbers": ["+14155238886"],           // prefix will be auto‑added
  "account_sid": "ACd8455419c9ff8c0e6b5bdbf9f870445f",
  "auth_token": "<YOUR_TWILIO_AUTH_TOKEN>",
  "webhook_secret": "dev",
  "locale_default": "en"
}
```
System behavior:
- On save, the backend normalizes `from_numbers` so each entry is stored as `whatsapp:<E164>`. Duplicate handling is case‑insensitive.

---

#### 3) Configure Twilio to call your webhook
In Twilio Console:
- Messaging → WhatsApp Sandbox (or your WhatsApp Sender)
- Set “When a message comes in” to:
  - `POST https://<your-domain>/v1/integrations/twilio/whatsapp/webhook`
- Save
- Sandbox note: Testers must first send `join <sandbox-code>` to `+1 415 523 8886`.

Outcome: Twilio forwards inbound messages to your app.

---

#### 4) Verify routing (prefix and non‑prefix)
- We updated tenant resolution to handle both forms:
  - With prefix: `whatsapp:+14155238886`
  - Without prefix: `+14155238886`
- The resolver now matches either form against tenant config.

Quick tests (no Twilio):
- Admin UI → WhatsApp → Triggers → “Test a phrase”
  - To: `whatsapp:+14155238886`
  - Message: `hi`
  - Expect TwiML XML with your menu.
  - Repeat with To: `+14155238886` (no prefix) — should also work.

---

#### 5) Configure phrase triggers (optional, recommended)
Admin UI → WhatsApp → Triggers → New Trigger
- “hi” → show main menu:
  - Match: type `exact`, value `hi`
  - Action: `render_submenu`, menu `default`
  - Priority: 100, Enabled: ON
- “book” → jump to booking submenu:
  - Match: type `contains`, value `book`
  - Action: `jump_node`, menu `default`, node `book_flow`
  - Priority: 90, Enabled: ON
- “enquiry” → enquiry response or submenu:
  - Match: `contains`, value `enquiry`
  - Action: `static_text` (your message) or `jump_node` → `enquiry`

---

#### 6) End‑to‑end sandbox test
- From your WhatsApp (after joining sandbox), send `hi` to `+1 415 523 8886`.
- Expect your menu reply.
- Send `book` to see booking submenu (if configured).

---

#### 7) (Optional) Harden for production
- Enable signature validation (env flag like `TWILIO_VALIDATE=true`) using the tenant’s `auth_token`.
- Add rate limiting per `From` number; enable structured logs.

---

### Acceptance criteria
- `ss-salon` WhatsApp Config saved with number `whatsapp:+14155238886` (auto‑prefixed if user enters plain E.164).
- Inbound WhatsApp messages to `+14155238886` (with or without `whatsapp:` prefix in Twilio’s payload) are routed to `ss-salon`.
- Published menu replies to messages; optional triggers (“hi”, “book”, “enquiry”) behave as configured.

### Notes
- If you share your public base URL, I’ll confirm the exact webhook URL and help test live.
- If multiple tenants share the same Twilio number, define clear routing rules; otherwise keep one number per tenant.