### Plan: Make the Menu Editor load the selected version (not always the latest)

You observed: when you click Edit for an old published version, the editor still shows the latest options. I’ve added backend support to fetch a specific version; now we’ll wire the Admin UI to use it and make the UX clear for editing historical versions.

---

### What is already implemented (server)
- API now accepts an optional `version` when reading a menu:
  - `GET /v1/tenants/{tenant}/whatsapp/menus/{menu_id}?status=published&version=3`
  - Still supports fetching the latest `draft` or latest `published` when you omit `version`.

---

### UI changes to implement
1) Menus list should expose each version clearly
- In WhatsApp → Menus:
  - Show both Draft and each Published version row with its version number.
  - For Published rows, add a “View” button that opens the editor in read-only mode for that exact version.
  - Add a “Create Draft from this version” button to fork a new draft using that version’s tree.

2) Pass version to the Menu Editor
- When clicking View for a published row, navigate with status and version in the query:
  - Route: `/whatsapp/menus/:id?status=published&version=3` → Editor loads exactly v3.
- Keep the existing “Edit Draft” button for the draft row (no version param, `status=draft`).

3) Menu Editor behavior
- On load, read `status` and `version` from URL search params.
  - If `status=published` and `version` present → call `getMenu(tenant, id, 'published')` with the `version` query → set `readOnly=true` (disable Save Draft/Publish buttons, show “Read‑only: Published vX”).
  - If `status=draft` → load the current draft and allow edits as today.
- Add a button “Create Draft from this version” when viewing a published version:
  - Action: clones the loaded tree into a draft (via `upsertMenu`) and navigates to edit the draft (no `version` in query).

4) Data loading changes
- Extend the `getMenu` API client to accept optional `status` and `version` params and pass them through to the backend.
- In `MenusIndex`, when listing rows:
  - Group/label published versions by version number.
  - Button behavior:
    - Published → View (versioned read‑only), Create Draft from this version
    - Draft → Edit (normal edit)

5) Safeguards
- Prevent overwriting published history: editing is only allowed on Drafts.
- Publishing creates a new Published version (which you already have).

---

### Acceptance criteria
- Clicking a Published version loads that exact version in the editor (read‑only).
- You can fork any published version into a Draft with one click and then edit/publish it as a new version.
- Draft editing remains unchanged.

---

### Optional UX polish
- Add a Version selector inside the editor header to quickly switch between versions (read‑only) and a “Fork as Draft” action.
- Show a banner in the editor indicating the loaded context: Draft vs Published vX.

---

### Quick verification steps
1) Publish two updates (v1 and v2) of a menu; keep no draft.
2) In Menus list, click View on v1 → Editor shows v1 read‑only (not v2).
3) Click “Create Draft from this version” in the editor → go to Draft; edit and publish → v3 appears in list.

If you’d like me to proceed with these UI updates now, I can implement them right away since the backend is already ready for versioned reads.