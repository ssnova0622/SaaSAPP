# Postman Collection – SaasProject API

## Import

1. Open Postman → **Import** → select `SaasProject_API.postman_collection.json` (lightweight) or `saas_application.json` (full API).
2. Collection variables: see each file’s **Variables** tab (`base_url`, `token` or `access_token`, `tenant`, etc.).

## Setup

1. **base_url**: Default `http://127.0.0.1:8000` (or `127.0.0.1` vs `localhost` depending on your run).
2. **tenant**: Default **`tenant_demo`** to match `MOCK_TENANT_ID` and `scripts/super_admin/seed_mock_data.py`. Use another id if your data lives elsewhere.
3. **Auth**: Run **Auth → Login** with the seeded demo admin (`testtenant@example.com` / `123456` by default, from `MOCK_EMAIL` / `MOCK_PASSWORD` in `settings`).  
   - `SaasProject_API`: Tests on Login set `token` from `access_token`.  
   - `saas_application.json`: Tests set `access_token`.

## Folders (`SaasProject_API`)

- **Auth** – Login (auto-save token), Me  
- **Tenants** – List, Get, Status, Modules, Plans, Message templates, WhatsApp templates bundle  
- **Admin** – Super admin overview, Analytics, Dashboard, Cron  
- **Users** – List, Create  
- **WhatsApp** – Menus, Config (Twilio + Meta Cloud examples), Triggers  
- **Appointments** – List, Create, Reschedule  
- **Slots** – Professionals, Slots (mock: `Dr. Demo One`)  
- **Customers**, **Store / Catalog**, **Reports**, **Promotions** (list, create CTA, get/update, send, logs), **Services**, **Staff**  
- **Workflows** – Available actions, list/get/upsert (matches seeded `demo_workflow_1`)  
- **Retention**, **Health**

## Seed mock data

From project root:

```bash
python scripts/super_admin/seed_mock_data.py
```

Removes tenant-scoped mock data and demo user (optional tenant): `python scripts/super_admin/delete_mock_data.py`.

All authenticated requests use **Bearer** from the collection auth.
