### Plan: How to view and manage a tenant’s WhatsApp configuration from the Admin screen

#### Goal
Enable admins to access all tenant WhatsApp configuration details from the Admin UI, using the existing dedicated WhatsApp module pages (not from Settings).

#### What already exists in this project
- Backend endpoints (in `app/routers/whatsapp.py`):
  - `GET /v1/tenants/{tenant}/whatsapp/config` — fetch tenant WhatsApp config
  - `PUT /v1/tenants/{tenant}/whatsapp/config` — update tenant WhatsApp config
  - Gated by `core.whatsapp_menu` capability and tenant scope
- Admin UI routes (in `admin_ui/src/App.tsx`):
  - `/whatsapp` — Menus index
  - `/whatsapp/config` — WhatsApp Config page
  - `/whatsapp/triggers` — Triggers index
  - All routes guarded by `RequireCapability("core.whatsapp_menu")`
- Admin UI API client (in `admin_ui/src/api/tenants.tsx`):
  - `getWhatsAppConfig(tenant)` and `putWhatsAppConfig(tenant, cfg)`
- Menus page has a “Config” button that navigates to `/whatsapp/config`.

#### Proposed user flow (Admin UI)
1) Open Admin UI → left sidebar → WhatsApp
2) On the WhatsApp page (Menus), click the “Config” button to go to `/whatsapp/config`.
3) Review and edit WhatsApp Config fields (via `getWhatsAppConfig` / `putWhatsAppConfig`):
   - `provider`: `twilio` or `meta_cloud`
   - `from_numbers` (array) and legacy `from_number` (read-only)
   - `webhook_secret`
   - `account_sid` / `auth_token` (Twilio)
   - `phone_number_id` / `access_token` (Meta Cloud)
   - `locale_default`
   - `active_menu_id` (which published WhatsApp menu to use by default)
4) Save. The page persists via `PUT /whatsapp/config` and shows confirmation.

#### Preconditions / Access
- Tenant must have capability `core.whatsapp_menu`. Super Admin can enable it for the tenant (Settings → Modules & Capabilities).
- The user must be:
  - Super Admin, or
  - Tenant Admin with the tenant capability (no user-cap intersection needed), or
  - Staff with both tenant capability and matching user capability.

#### Troubleshooting checklist
- If WhatsApp menu/config pages don’t appear:
  - Check tenant has `core.whatsapp_menu` in Settings → Modules & Capabilities.
  - For staff, ensure their JWT caps include `core.whatsapp_menu` or have them re-login after Tenant Admin updates caps.
  - Ensure you selected the correct tenant via the top-left tenant selector.
- If messages aren’t routed to the correct tenant:
  - For Twilio: confirm `from_numbers` include the sending number used in webhooks.
  - For Meta Cloud: set `active_menu_id` to the correct published menu.

#### Small UX polish (optional)
- On `/whatsapp/config`, add helper text:
  - Twilio fields applicability
  - Meta Cloud fields applicability
  - Note about `active_menu_id` needed for Meta Cloud provider
- Add validation: non-empty `webhook_secret`, normalized E.164 phone numbers in `from_numbers`.

#### Acceptance criteria
- Admin can open `/whatsapp/config` and see all tenant WhatsApp configuration details.
- Saving updates the backend and reflects on subsequent fetch.
- If capability is missing, the UI shows a clear guidance message via `RequireCapability` guard.

#### Quick reference (where to click)
- Sidebar: WhatsApp → “Config” button → WhatsApp Config page.
- API methods: `getWhatsAppConfig(tenant)`, `putWhatsAppConfig(tenant, cfg)`.
