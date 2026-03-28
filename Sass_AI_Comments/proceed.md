### How to access tenant WhatsApp config from the Admin screen

Here’s the fastest way to view and edit a tenant’s WhatsApp configuration in your current app:

1) Ensure access
- The tenant must have the capability `core.whatsapp_menu` enabled (Super Admin → Settings → Modules & Capabilities).
- Tenant Admins can access based on tenant capability; Staff need both tenant cap and user cap (or re-login after being granted caps).

2) Open the WhatsApp module
- In the left sidebar, click “WhatsApp” to go to the Menus page (`/whatsapp`).
- Click the “Config” button in the header to open the WhatsApp Config page (`/whatsapp/config`).

3) Review and edit fields
- Provider: `twilio` or `meta_cloud`
- From numbers: `from_numbers` (E.164 list)
- Secrets/keys: `webhook_secret`, `account_sid`, `auth_token` (Twilio) or `phone_number_id`, `access_token` (Meta)
- Defaults: `locale_default`, `active_menu_id` (set this to a published menu for Meta Cloud)
- Click Save to persist.

4) API behind the screen (for reference)
- GET `/v1/tenants/{tenant}/whatsapp/config` → loads the current config
- PUT `/v1/tenants/{tenant}/whatsapp/config` → saves changes

5) Troubleshooting
- WhatsApp menu/config not visible: enable `core.whatsapp_menu` for the tenant; Staff may need a re-login.
- Wrong tenant selected: use the top-left tenant selector.
- Messages not hitting the correct tenant: ensure the webhook ‘from’ number exists in `from_numbers`. For Meta Cloud, set `active_menu_id`.

That’s it—WhatsApp configuration is fully managed under the dedicated WhatsApp module and not from the Settings page. If you want, I can also add helper text/validation on `/whatsapp/config` (e.g., E.164 formatting, provider-specific hints).