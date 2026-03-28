### What I implemented for your request
- Tenants can now store Twilio/WhatsApp configuration in their document under `whatsapp_config` (along with optional owner contact and timezone).
- When creating a new tenant via `POST /v1/tenants`, you can optionally provide initial admin credentials; the API will create a `tenant_admin` user for that tenant.

This allows you to keep all Twilio details inside the tenant’s collection document and provision an admin user at tenant creation time.

---

### New/extended request body for creating a tenant
Endpoint: `POST /v1/tenants` (JWT required)

Accepted fields (all optional except `tenant`):
- Core
  - `tenant: string` (required)
  - `category?: string` (e.g., `salon | clinic | store | showroom`; default `salon`)
  - `professionals?: Array<{ name: string; price?: number; slots?: string[] | Slot[] }>`
- Owner & settings
  - `owner_email?: string`
  - `owner_phone?: string`
  - `tz?: string` — IANA timezone (e.g., `Asia/Kolkata`)
- WhatsApp/Twilio config (stored under `whatsapp_config` in the tenant doc)
  - `whatsapp_config?: { provider?: 'twilio'|'meta'|'dummy', account_sid?: string, auth_token?: string, from_number?: string, [other provider keys...] }`
- Bootstrap tenant admin user
  - `admin_email?: string`
  - `admin_password?: string` (min length 8)
  - `admin_display_name?: string`

On success, the response stays the same `TenantCreateResponse` (tenant basic info and seeded professionals). The admin creation is a side-effect when admin creds are provided.

---

### Example 1 — Create a Salon tenant with Twilio config and admin user (curl)
```
curl -X POST http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant": "ss-salon",
    "category": "salon",
    "owner_email": "owner@ss-salon.com",
    "owner_phone": "+911234567890",
    "tz": "Asia/Kolkata",
    "whatsapp_config": {
      "provider": "twilio",
      "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "auth_token": "your_twilio_auth_token",
      "from_number": "+12345550000"
    },
    "admin_email": "admin@ss-salon.com",
    "admin_password": "StrongPass#123",
    "admin_display_name": "Salon Admin"
  }'
```
Result:
- Tenants collection upserts a document (key `_id = "ss-salon"`) with:
  - `owner_email`, `owner_phone`, `tz`, and `whatsapp_config` persisted
- Users collection gets a `tenant_admin` user for `tenant="ss-salon"` with the given email/password.

Then the new admin can log in:
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@ss-salon.com","password":"StrongPass#123"}'
```

---

### Example 2 — Create a Store tenant with only Twilio config (no admin)
```
curl -X POST http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant": "freshmart-store",
    "category": "store",
    "whatsapp_config": { "provider": "twilio", "account_sid": "...", "auth_token": "...", "from_number": "+1..." }
  }'
```
You can add the admin later via `POST /v1/users` (as super_admin or tenant_admin appropriately).

---

### Where the data is stored
- Tenants: `tenants` collection document (`_id = <tenant>`)
  - `whatsapp_config` (entire object you send)
  - `owner_email`, `owner_phone`, `tz`
- Users: `users` collection
  - A `tenant_admin` user is created only if `admin_email` AND `admin_password` are provided and valid. It’s scoped to the new tenant.

---

### Notes and validation
- Timezone (`tz`) is validated against IANA names (e.g., `Asia/Kolkata`). Invalid tz returns 400.
- `admin_password` must be at least 8 chars. If `admin_email` already exists, the API returns 409.
- The `whatsapp_config` structure is stored as-is; for Twilio, typical keys are `provider`, `account_sid`, `auth_token`, `from_number`.

---

### Admin UI (next steps, optional)
Currently the Admin UI’s “New Tenant” dialog doesn’t yet expose the Twilio fields or bootstrap admin fields. If you want, I can add inputs for:
- Owner email/phone, tz (dropdown)
- Twilio fields (provider/account SID/auth token/from number)
- Admin email/password/display name
…so you can set everything from the UI in one step.

Would you like me to wire these fields into the Admin UI create tenant dialog now, and also mask the Twilio secret on display (with an edit flow)?