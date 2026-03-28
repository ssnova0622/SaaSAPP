### Plan: Visual WhatsApp Menu Builder (no JSON editing required)

#### Objective
Deliver a simple, visual WhatsApp Menu Builder so Tenant Admins can create, edit, and publish menus without touching JSON. Keep existing backend endpoints and Option B RBAC. The editor will provide clear validations, a live preview, and starter templates.

#### Scope (what will change)
- Admin UI (new Visual Editor):
  - Node list and visual forms to add/edit Submenus and Actions
  - Option editor for submenu choices (keys 1–9, labels, next node)
  - Action picker (select_timeslot, open_ticket, show_offers, open_url, api_call) with parameter fields
  - Connection picker to link options to next nodes
  - Validation panel (root exists, unique ids, valid next links, unique option keys, depth ≤ 6)
  - Live Preview of current submenu rendering
  - Template import buttons (Salon/Clinic/Store/Empty)
  - Save Draft / Publish buttons (wired to existing APIs)
  - Optional “Advanced” toggle to view/edit JSON for power users
- Backend: no contract change (existing endpoints already support drafts/publish and validation)

#### Milestones
1) UX and State Model (0.5 day)
- Define visual state shape mirroring server: `tree = { root, nodes[] }`
- Node types:
  - submenu: `{ id, type:'submenu', title, prompt, options:[{key,label,next}] }`
  - action: `{ id, type:'action', action, title?, params?, requires_caps?[] }`
- Map visual state to/from API JSON

2) Visual Editor Skeleton (1 day)
- Build new editor UI (replacing JSON textarea as default)
- Components:
  - NodeList (with add/remove/rename)
  - NodeInspector (fields for submenu/action)
  - OptionEditor (add/remove/reorder options; pick next node from dropdown)
  - ActionPicker (select action and fill params)
  - ValidationSummary (shows current issues)
  - LivePreview (render root submenu)
- Load existing draft/published into visual state
- Save Draft builds JSON and calls POST /tenants/{t}/whatsapp/menus
- Publish calls POST /tenants/{t}/whatsapp/menus/{id}/publish

3) Validation & UX polish (0.5 day)
- Client-side validators:
  - root present and references an existing node
  - unique node ids
  - for each submenu: unique option keys; `next` references exist
  - simple depth check ≤ 6
- Highlight errors inline; disable Publish and show reasons
- Confirmations for destructive actions (delete node/option)

4) Templates & Preview (0.5 day)
- Import templates (Salon/Clinic/Store/Empty) into visual state
- Live preview of the root submenu (exactly as bot renders)

5) Advanced JSON toggle (0.25 day)
- Optional switch to reveal the JSON editor (read-only by default; with “Enable edits” confirmation)

6) Tests & Docs (0.5 day)
- UI unit tests for validation helpers and component rendering
- Manual e2e: create → save draft → publish → hit dummy Twilio webhook → verify TwiML
- Update Admin guide with screenshots and steps

Total estimate: ~3.25 days of focused work

#### Deliverables
- New visual WhatsApp Menu Editor UI (no JSON required by default)
- Updated WhatsApp module navigation (unchanged routes)
- Template import and Live Preview
- Strong client-side validation with clear messaging
- Optional Advanced JSON toggle

#### Acceptance criteria
- Tenant Admin can create and publish a menu without editing JSON
- Editor prevents structural errors and shows what to fix
- Published menus are consumed by `/v1/integrations/twilio/whatsapp/webhook` and `/v1/bot/whatsapp/next` without backend changes
- Option B policy preserved (Tenant Admin auto-access when tenant has `core.whatsapp_menu`)

#### Nice-to-have (phase 2)
- Drag-and-drop reordering and node connections
- Session-aware flows (collect service, professional, slot)
- Rich action helpers (e.g., parameter forms per action type)
- Server-side /validate endpoint to double-check graphs

If this plan looks good, I’ll start with Milestone 2 (Visual Editor Skeleton) and wire it to the current APIs. Would you like drag-and-drop in v1, or keep simple buttons for reorder/connect and add DnD later?