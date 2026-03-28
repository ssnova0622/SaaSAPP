### Staff login troubleshooting and expected behavior

You reported: Staff login not working. When creating new staff, that staff should be able to log in using their username and password; Tenant Admin can assign modules. Here’s how it should work and what to check/fix.

#### How it’s intended to work
1) Create Staff user (Users page):
   - Role = `staff`
   - Tenant must be set (Super Admin picks; Tenant Admin is auto‑scoped to their tenant)
   - Set a password (or it defaults to `ChangeMe#123` if left empty at creation in the current UI)
   - Assign capabilities (`caps`) for the user — these must be a subset of tenant‑enabled capabilities
2) Login:
   - Staff uses their email + password
   - Backend returns JWT with `role=staff`, `tenant=<tenant_id>`, and `caps=[...]`
   - UI locks to that tenant and hides the tenant selector; only shows pages allowed by both tenant’s capabilities AND the user’s caps

#### Common reasons login appears to “not work” and how to resolve
- Wrong password: If you didn’t specify a password during creation, try `ChangeMe#123`, or set a new password via Users → Edit → “New Password”.
- User status is disabled: Ensure the user’s `status` is `active` in Users → Edit.
- Tenant missing or inactive: The staff user must have a `tenant` set and that tenant must be active.
- Missing or mismatched capabilities: After login, the UI may look empty if the tenant doesn’t have the module/capability enabled, or the user’s caps are empty. Tenant Admin should enable tenant modules/capabilities in Settings, and then assign matching caps to the staff user in Users.
- Email/username mismatch: Login uses the email saved for the user. Verify the exact email string.

#### What Tenant Admin controls
- Tenant‑level modules/capabilities: In Settings for the tenant, enable modules/capabilities (e.g., `store.catalog`, `store.orders`, WhatsApp, AI flags, etc.).
- User‑level caps: In Users, for a staff user, assign the specific capabilities (filtered to those the tenant has enabled). The navigation requires BOTH tenant caps and user caps.

#### Quick recovery steps
1) In Users, edit the staff user:
   - Ensure Status = Active
   - Ensure Tenant = correct tenant
   - Set New Password to a known value (e.g., `ChangeMe#123!`)
   - Assign required caps (e.g., `store.catalog`, `store.orders`, or other features the staff should access)
2) In Settings for that tenant:
   - Ensure the same capabilities/modules are enabled at the tenant level
3) Logout and login as the staff user with the set password

If this still fails, please provide the exact error shown on login (e.g., “invalid credentials” vs a blank screen after login). I can then pinpoint whether the issue is backend authentication, JWT contents, or front‑end gating. I can also add a small checklist page to display the current JWT role/tenant/caps after login to aid debugging, if you’d like.