### Likely reasons the WhatsApp menu is not reflecting in tenant login and how to fix

From the current codebase and guards, the WhatsApp Menus page only appears when both the tenant and the user are allowed to see it. The most common causes are capability gating and token refresh. Use this checklist:

#### 1) Confirm the tenant has the capability `core.whatsapp_menu`
- Backend requires this cap for all WhatsApp menu/triggers/config endpoints (see `app/routers/whatsapp.py` routes guarded by `ensure_capability_enabled("core.whatsapp_menu")`).
- UI also checks it in multiple places:
  - Sidebar nav item for WhatsApp is gated in `admin_ui/src/components/AppShell/AppShell.tsx` via capabilities + user caps.
  - Routes are gated with `<RequireCapability cap="core.whatsapp_menu">` in `admin_ui/src/App.tsx`.
- Where to enable:
  - Super Admin → Settings → Modules & Capabilities → add capability `core.whatsapp_menu` for the tenant, then Save.

Tip: You already have an informational WhatsApp card in Settings guarded by this cap (see `Settings.tsx`), so if you don’t see that, the tenant doesn’t have the capability yet.

#### 2) Check the user’s role and JWT caps
- The sidebar shows items only when the intersection of tenant capabilities and the user’s token caps allows it (except for Super Admin):
  - For Tenant Admin, `RequireCapability` grants access if the tenant has the cap (token cap not required). See `admin_ui/src/components/RequireCapability.tsx` lines 55–63.
  - For Staff, both must be true: tenant has `core.whatsapp_menu` AND the user’s JWT caps include `core.whatsapp_menu`.
- If Super Admin just enabled the capability, tenant users may need to log out/in to refresh their JWT so `userCaps` include the new cap. Your backend does attempt to sync caps to tenant_admin users on settings save (`app/routers/tenants.py` lines 144–167), but existing tokens won’t update until next login. Staff users still require explicit caps.

What to do:
- If the user is Staff, grant `core.whatsapp_menu` to that user or have them relogin after the Tenant Admin assigns it.
- If the user is Tenant Admin, verify they are actually logged in as that tenant (top-left tenant badge/selector).
- As a quick test, try navigating directly to `/whatsapp`. If you see an access warning from `RequireCapability`, it will tell you whether the tenant cap or user cap is missing.

#### 3) Ensure you actually have menus and at least one is published
- Open Admin UI → WhatsApp → Menus. Create a menu (ID like `default`) and Publish it.
- The listing itself should appear even with only drafts, but publishing is needed for WhatsApp runtime to serve it.

#### 4) If using Meta Cloud provider, set the Active Menu ID
- For WhatsApp runtime reflection (incoming messages):
  - Active menu resolution order (see `app/routers/whatsapp.py`):
    1) `whatsapp_config.active_menu_id` if set
    2) `default`
    3) latest published of any id
- In Admin UI → WhatsApp → Config, set `Active menu id` to your published menu id when using Meta Cloud. The UI even hints this in `MenusIndex.tsx` after publish.

#### 5) Verify endpoint access quickly
- If the page still doesn’t show, call the list API:
  - `GET /tenants/{tenant}/whatsapp/menus`
  - If this returns 403, the tenant capability `core.whatsapp_menu` is missing.

#### 6) Settings cache/refresh
- After Super Admin saves modules/capabilities, the UI clears the tenant settings cache and dispatches `tenantSettingsChanged`; `AppShell` listens and refetches. If a user still doesn’t see the menu, it’s usually because their JWT didn’t refresh yet (see step 2).

### Summary of the most probable root cause
- The tenant capability `core.whatsapp_menu` is not enabled, or the logged-in user (especially Staff) doesn’t have matching JWT caps yet. Enabling the tenant capability and having the user log out/in typically resolves it. For WhatsApp runtime, ensure a published menu and set `Active menu id` if using Meta Cloud.

### Quick resolution steps
1) As Super Admin, enable tenant capability `core.whatsapp_menu` and Save.
2) For Tenant Admin: re-open the app; for Staff: grant `core.whatsapp_menu` to the user, then have them log out/in.
3) Create/Publish a menu; set `Active menu id` in WhatsApp Config if using Meta Cloud.
4) Retry visiting `/whatsapp` from tenant login.