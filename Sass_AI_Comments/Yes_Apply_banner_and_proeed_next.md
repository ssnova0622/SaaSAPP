### Banner added and proceeding to next step
I’ve added an informational banner in the Admin UI for non‑Super Admin users that clearly states which tenant they are managing, and that their access is limited to that tenant.

- Location: just below the top toolbar, on all pages inside the shell
- Visibility: shown only when the logged‑in user’s role is not `super_admin`
- Content: “You are managing tenant <tenant>. Access is limited to this tenant.”

File changed:
- `admin_ui/src/components/AppShell/AppShell.tsx`

This complements the UI lock and the backend scope enforcement you already have.

### Verify
1) Log in as a tenant_admin or staff (non‑super_admin).
2) You should see the info banner at the top: `You are managing tenant ss-salon...` (or your tenant name).
3) Tenants menu hidden; tenant picker restricted to the user’s tenant.

### Next steps (suggested)
- If you want, I can add a subtle “role chip” (e.g., Tenant Admin / Staff) next to the banner for clarity.
- Otherwise, I’ll move on to your next requested task. Let me know what you want to prioritize (e.g., Store features, Reports polish, or further role/capability UX tweaks).