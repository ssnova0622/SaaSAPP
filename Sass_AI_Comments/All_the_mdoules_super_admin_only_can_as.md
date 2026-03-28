### Acknowledged — Super Admin is the only one assigning modules per tenant
I’ve adjusted the backend normalization so modules/capabilities are no longer auto‑enabled based on tenant category. This ensures that after tenant creation, no modules/capabilities are implicitly active; only a Super Admin can assign them per tenant.

What changed (backend):
- `Storage.get_tenant_settings()` no longer derives `modules` and `capabilities` from `category`. It simply returns whatever is stored. If nothing is stored, both are empty lists.
- Tenant behavior now matches your policy: after creation, the tenant will have no modules/capabilities until a Super Admin assigns them. Once assigned, both API and Admin UI gating already enforce access accordingly.

Implications:
- A new tenant won’t be able to use Salon/Store/Core capabilities until a Super Admin enables them in Settings → Modules (which is visible/editable only to Super Admin in your UI).
- The Admin UI navigation will reflect enabled capabilities once assigned. Before assignment, guarded pages will be hidden/blocked.

If you want, I can also:
- Hide the Modules section completely for non‑Super Admin users in `Settings` (it’s already read‑only; we can fully hide it if you prefer).
- Provide a one‑click “Apply default bundle” action for Super Admin (e.g., for a Store tenant, preselect `store` + `store.orders` + `store.payments` + `store.catalog`) — only visible to Super Admin.

Would you like me to apply either of these optional UI adjustments?