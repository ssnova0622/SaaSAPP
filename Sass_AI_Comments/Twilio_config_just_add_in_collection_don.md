### Acknowledged — Twilio config will only be stored in the tenants collection, not shown in Admin UI
- Backend: `POST /v1/tenants` accepts `whatsapp_config` and persists it in the tenant document. It’s also returned by `GET /v1/tenants/{tenant}` right now, but no Admin UI component renders or edits it.
- Admin UI: We do not display Twilio config anywhere. The Settings page sections (Payments, Fulfillment, Modules) remain unchanged and do not expose `whatsapp_config`.

If you want even tighter control (recommended), I can hide `whatsapp_config` from all tenant GET responses so it’s never sent to the browser:
- Option A (preferred): exclude `whatsapp_config` from `GET /v1/tenants/{tenant}` response, and add a separate, super‑admin‑only endpoint to read/update it.
- Option B: leave reads as-is but redact secrets (e.g., return `from_number` only, not `auth_token`).

### How to set Twilio config (API only)
Example curl to set during tenant creation:
```
curl -X POST http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant": "ss-salon",
    "category": "salon",
    "whatsapp_config": {
      "provider": "twilio",
      "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "auth_token": "your_twilio_auth_token",
      "from_number": "+12345550000"
    }
  }'
```
You can also update later via `PUT /v1/tenants/{tenant}` with a body containing only `whatsapp_config`.

### Security notes
- Secrets should not be sent to the front end. If you want, I can redact `whatsapp_config` in all GET responses or move it behind a super‑admin endpoint.
- Ensure your logs and backups don’t print these fields in plaintext.
- Consider using environment‑level secret management (Vault, AWS KMS) in production and store only references in Mongo.

Tell me if you want me to implement Option A (redact `whatsapp_config` from standard GET and add a super‑admin endpoint). It’s a small, safe change and keeps secrets fully server‑side.