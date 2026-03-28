### Clarification on showing all AI functionality on the AI page

Currently, the AI page intentionally shows only the AI features applicable to the selected tenant (Salon/Clinic vs Store) to avoid confusion. Your new request is to show all AI functionality on the AI page regardless of tenant vertical/capabilities.

#### What this means
- The AI hub (`/ai`) would list all AI features (cards/links), not just those enabled by tenant modules/capabilities.
- Sub‑pages and API endpoints would still remain capability‑guarded; attempting to open a feature without the required capability will display a guidance message (via `RequireCapability`) or return 403 for APIs. 

#### Minimal implementation approach
- Admin UI: update `admin_ui/src/pages/AI/Index.tsx` to render all AI feature cards unconditionally and add badges/tooltips indicating whether each is “Enabled” or “Locked (enable AI / enable module)”.
- Keep sub‑routes guarded:
  - `Appointments Assist` → requires `ai.appointment_recs`
  - `Predictions` → requires `ai.predictions`
  - Additional features (when pages exist) should likewise be gated (e.g., no‑show, reschedule, pricing, insights).
- Provide clear CTAs that guide Super Admin to Settings → Modules to enable AI and the needed vertical module.

#### Proposed UI layout for AI hub (all features visible)
- Appointments Assist (Salon/Clinic) — status badge: Enabled/Locked
- Auto‑Rescheduling — status badge: Enabled/Locked
- No‑Show Prediction — status badge: Enabled/Locked
- Personalized Service Recommendation — status badge: Enabled/Locked
- Staff Load Balancing — status badge: Enabled/Locked
- Dynamic Pricing — status badge: Enabled/Locked
- WhatsApp Follow‑up & Retention — status badge: Enabled/Locked
- Treatment History & Insights (Clinic) — status badge: Enabled/Locked
- Business Insights Dashboard — status badge: Enabled/Locked
- (Optional) Store Predictions dashboard — status badge: Enabled/Locked

#### Guardrails
- We will not remove backend guards. Endpoints stay protected by `ensure_module_enabled('ai')` and feature capabilities.
- The hub becomes a “catalog” surface; clicking a locked card leads to a helpful message or to Settings for enablement.

#### Next steps
If you want, I can implement the AI hub page changes to always show all AI features with Enabled/Locked badges, while keeping deep‑links guarded. This is a front‑end–only change in `admin_ui/src/pages/AI/Index.tsx`, plus small helper text additions. No backend changes are required.
