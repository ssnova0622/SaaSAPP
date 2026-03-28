### Implemented: auto-create tenant admin on new tenant creation (saved in users collection)
I’ve updated the backend so that every time you create a new tenant via `POST /v1/tenants`, an admin account (role `tenant_admin`) is created and stored in the `users` collection for that tenant. The admin email and password are required in the create-tenant request and are validated.

Key points:
- Request schema now requires fields `admin_email` and `admin_password` (min length 8). Optional `admin_display_name` is supported.
- The user is saved only in the `users` collection (not in tenants). The tenant document remains clean of any credentials. 
- If a user already exists with the given `admin_email`, the API returns `409` conflict.
- You can also pass `whatsapp_config` (Twilio settings) in tenant creation; it is stored under `tenants.whatsapp_config` but is not displayed in Admin UI as requested.

Files changed (already in your codebase):
- `app/models/schemas.py` — `TenantCreate` now includes required `admin_email` and `admin_password`, optional `admin_display_name`, plus optional `whatsapp_config`, `owner_email/phone`, `tz`.
- `app/routers/tenants.py` — `POST /v1/tenants` persists `whatsapp_config` and creates the `tenant_admin` user in `users` collection. It validates timezone and password length; returns 409 if admin email exists.
- `app/services/storage_mongo.py` — `seed_if_absent` persists optional `whatsapp_config`, `owner_email`, `owner_phone`, `tz` into the tenants document.

---

### How to use (curl example)
```
curl -X POST http://127.0.0.1:8100/v1/tenants \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant": "ss-salon",
    "category": "salon",
    "admin_email": "admin@ss-salon.com",
    "admin_password": "StrongPass#123",
    "admin_display_name": "Salon Admin",
    "owner_email": "owner@ss-salon.com",
    "owner_phone": "+911234567890",
    "tz": "Asia/Kolkata",
    "whatsapp_config": {
      "provider": "twilio",
      "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "auth_token": "twilio_auth_token",
      "from_number": "+12345550000"
    }
  }'
```
- Result: Tenant created; a `tenant_admin` user is inserted into `users` with `tenant = "ss-salon"` and the provided credentials.
- Then log in as that admin:
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@ss-salon.com","password":"StrongPass#123"}'
```

---

### Behavior details
- Required fields on `POST /v1/tenants`: `tenant`, `admin_email`, `admin_password` (>= 8 chars).
- `409` if `admin_email` already exists in `users` (any tenant).
- `400` if timezone invalid or password too short.
- Admin user is created with:
  - `role = "tenant_admin"`
  - `tenant = <new tenant id>`
  - `email = admin_email`, `password_hash` (secure hash)
  - `display_name = admin_display_name || "Tenant Admin"`

---

### Admin UI
- As requested, Twilio config is not displayed in the UI. The “New Tenant” dialog currently does not include admin email/password inputs. If you want, I can add those fields to the dialog so you can provision admin creds from the UI as well. For now, use the API to pass them.

Would you like me to add admin email/password fields to the Admin UI’s create-tenant modal, or keep it API-only?