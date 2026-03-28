### Plan to continue the implementation

1. Review Admin UI WhatsApp module to locate Menus index/editor and routing; identify where to hook the wizard. *
2. Create `admin_ui/src/modules/WhatsApp/templates.ts` with built‑in presets (Retail, Restaurant, Salon, Blank) and a helper `defaultTrigger(menu_id)`. *
3. Implement `admin_ui/src/modules/WhatsApp/MenuWizard.tsx` (4 steps): Basics → Items & Actions → Triggers → Preview & Publish.
   - 3.1. State model with menu draft, selected template, items editing, and locales.
   - 3.2. Step 1: Basics form (menu_id auto default, name, template selection).
   - 3.3. Step 2: Item editor (label/action/submenu), presets for common actions.
   - 3.4. Step 3: Triggers UI with default hello trigger and synonyms add/remove.
   - 3.5. Step 4: Preview WhatsApp‑style bubbles; Test via `testTriggerWebhook`; buttons Save Draft / Publish.
   - 3.6. Wire API calls: `upsertMenu` → `createTrigger(s)` → `publishMenu`; error handling and toasts.
4. Integrate Wizard entry points: add a “Create Menu” button in `WhatsApp/MenusIndex` to open the wizard; preserve existing advanced `MenuEditor` route.
5. Tenancy awareness: read selected tenant from the existing tenant selector/context; ensure all API calls include the active tenant.
6. Admin booking UI: surface AI recommendations using `getRecommendedSlots`.
   - 6.1. Add a “Use AI recommendations” toggle (default on if capability present) in the booking screen.
   - 6.2. Fetch and display top 3 recommended times above the availability list; fallback gracefully if unavailable.
7. Capability checks: read tenant capabilities from tenant settings; gate features by `ai.appointment_recs` and `core.whatsapp_menu`.
8. Testing
   - 8.1. Backend tests: `recommend_slots` endpoint happy path, professional filter, capability gate (403), and error handling.
   - 8.2. WhatsApp flow test: with AI enabled, recommended times appear before full list and session stores merged `available_slots`.
   - 8.3. Admin UI quick checks: TypeScript compile and minimal component render test if present (optional).
9. Documentation: update README/admin guide with Wizard usage, templates, and AI recommendations toggle; include screenshots placeholders.
10. Verification: run backend tests and a manual pass in dev (create a tenant with professionals, enable capabilities, create menu via wizard, send test webhook to see menu and timeslot with AI).

Progress markers:
- `*` = in progress
- `✓` = completed during this session
- `!` = failed