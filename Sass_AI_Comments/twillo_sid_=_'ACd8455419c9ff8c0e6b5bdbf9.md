### Goal
Configure Twilio for tenant `ss-salon` so messages sent to `whatsapp:+14155238886` (Twilio’s WhatsApp Sandbox/number) are routed to this tenant’s WhatsApp Menu and Triggers.

---

### What you have
- Twilio Account SID: `ACd8455419c9ff8c0e6b5bdbf9f870445f`
- Twilio WhatsApp number: `whatsapp:+14155238886` (this is Twilio Sandbox’s default WhatsApp number)

You’ll also need the Twilio Auth Token (from Twilio Console → Account) to fully secure webhooks later. For now, our dummy webhook works without signature validation.

---

### One-time prerequisites
1) Enable the WhatsApp module capability for the tenant:
   - Super Admin → Settings → Modules & Capabilities → for tenant `ss-salon` enable module `core` and capability `core.whatsapp_menu` → Save.
2) Create and publish at least one WhatsApp menu for `ss-salon`:
   - Admin UI → WhatsApp → New Menu → build (or import a template) → Publish. Recommended `menu_id = "default"`.

---

### Configure Twilio for tenant `ss-salon`
You can do this entirely in the Admin UI.

- Admin UI → WhatsApp → Config
  - Provider: `twilio`
  - From numbers: add exactly `whatsapp:+14155238886`
    - Important: keep the `whatsapp:` prefix so routing matches the webhook payload’s `To` value.
  - Webhook secret: keep `dev` for now (used by our generic bot endpoint; not required for the Twilio webhook bridge).
  - Account SID: `ACd8455419c9ff8c0e6b5bdbf9f870445f`
  - Auth Token: paste your Twilio Auth Token (from Twilio Console) — optional for the current dummy mode, required later if we enable signature validation.
  - Default locale: `en`
  - Click Save.

If you prefer API:
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

---

### Point Twilio to your webhook
In Twilio Console:
- Messaging → Try it out → WhatsApp Sandbox (or your WhatsApp Sender if you have one)
- Set “WHEN A MESSAGE COMES IN” to your app’s webhook URL:
  - `POST https://<your-domain>/v1/integrations/twilio/whatsapp/webhook`
- Save.

Notes for Sandbox testing:
- Users must first join your sandbox by sending `join <your-sandbox-code>` to `+1 415 523 8886` on WhatsApp.
- After joining, messages they send to the sandbox number will hit your webhook.

---

### Configure triggers for “hi”, “book”, “enquiry” (optional but recommended)
- Admin UI → WhatsApp → Triggers → New Trigger
  - Example 1: Show main menu on “hi”
    - Match: type `exact`, value `hi`
    - Action: `render_submenu`, menu `default`
    - Enabled: ON, Priority: 100
  - Example 2: Jump to booking on “book”
    - Match: type `contains`, value `book`
    - Action: `jump_node`, menu `default`, node `book_flow` (ensure this node exists in your menu)
    - Enabled: ON, Priority: 90
  - Example 3: Enquiry text or submenu on “enquiry”
    - Match: type `contains`, value `enquiry`
    - Action: `static_text` with your message, or `jump_node` → `enquiry`

You can test triggers from the same page using the “Test a phrase” box.

---

### Verify end-to-end
1) Quick local test (no real Twilio needed):
   - Admin UI → WhatsApp → Triggers → Test a phrase
   - To: `whatsapp:+14155238886` (your configured From number)
   - Message: `hi`
   - Click Send Test → you should see a TwiML XML response with your menu.

2) Through Twilio Sandbox:
   - From your WhatsApp, send `join <sandbox-code>` to `+1 415 523 8886` if not already joined.
   - Then send `hi` — you should receive your menu options.
   - Send `book` — you should receive the booking submenu (if you created the corresponding trigger and node).

---

### Common pitfalls
- Number mismatch: store `from_numbers` with the `whatsapp:` prefix (e.g., `whatsapp:+14155238886`). Our webhook routes tenants by an exact match on the `To` value.
- No published menu: the Twilio webhook returns “No menu published yet” until you publish one.
- Missing capability: ensure the tenant has `core` module and `core.whatsapp_menu` capability enabled.
- Trigger references node that doesn’t exist: edit your menu so the node id (e.g., `book_flow`) is present.

---

### (Optional) Harden security for production
- Once you’re ready, enable Twilio signature validation (we can add an env flag like `TWILIO_VALIDATE=true`) and store `auth_token` in the tenant config or environment. Then the webhook will reject unsigned/invalid requests.

---

### Summary checklist for `ss-salon`
- [ ] Super Admin: enable `core` module + `core.whatsapp_menu` for `ss-salon`
- [ ] Tenant Admin: publish menu `default`
- [ ] Tenant Admin: WhatsApp Config → set provider `twilio`, add `from_numbers = ["whatsapp:+14155238886"]`, paste Account SID, Auth Token, Save
- [ ] (Optional) Triggers: add `hi`, `book`, `enquiry`
- [ ] Twilio Console: set webhook to `POST https://<your-domain>/v1/integrations/twilio/whatsapp/webhook`
- [ ] Test via Admin UI “Test a phrase” and via real WhatsApp Sandbox

If you share your public base URL, I can double‑check the exact Twilio webhook URL and confirm everything is wired correctly.