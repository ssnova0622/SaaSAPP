### Current status for Professionals & Slots in Admin UI
Already implemented:
- List professional names: `GET /v1/tenants/{tenant}/professionals`
- Create professional (with optional initial slots, else auto 09:00–18:30): `POST /v1/tenants/{tenant}/professionals`
- View slots for a selected professional: `GET /v1/tenants/{tenant}/professionals/{name}/slots`
- Update slots in bulk (replace list with comma‑separated `HH:MM` times; default status `available`):
  - `PUT /v1/tenants/{tenant}/professionals/{name}/slots`
- UI page: `Professionals`
  - Left: list of professionals
  - Right: slots editor (comma‑separated times) and Save button
  - “Add professional” dialog (name, price, optional initial slots)

This covers Create (C) and Read (R) and Update (U for slots). You requested full CRUD for Professionals and Slots. Below is what I’ll add and how it will work.

---

### What I will add (Backend API)
To complete full CRUD for professionals we’ll add these endpoints (JWT‑protected):
1) Update professional (rename and/or price)
- `PUT /v1/tenants/{tenant}/professionals/{name}`
  - Body: `{ "new_name?": string, "price?": number }`
  - Validates duplicates and updates `(tenant, name)` and/or `price`.

2) Delete professional
- `DELETE /v1/tenants/{tenant}/professionals/{name}`
  - Removes the professional document. If you prefer to prevent delete when there are future appointments, we can enforce that.

3) List professionals with details (name, price, slots count)
- `GET /v1/tenants/{tenant}/professionals/detail`
  - Returns `[ { name, price, slots_count } ]` (lightweight list; slots themselves fetched as needed)

4) Optional slot helpers (convenience)
- Reset slots to default business hours (09:00–18:30):
  - `POST /v1/tenants/{tenant}/professionals/{name}/slots/reset`
- Append/remove a single slot (if you want fine‑grained):
  - `POST /v1/tenants/{tenant}/professionals/{name}/slots/append` `{ time: "HH:MM" }`
  - `POST /v1/tenants/{tenant}/professionals/{name}/slots/remove` `{ time: "HH:MM" }`

Storage layer additions in `ai_scheduler/services/storage_mongo.py`:
- `update_professional(tenant, name, *, new_name=None, price=None)`
- `delete_professional(tenant, name)`
- `list_professionals_detail(tenant)`
- Slot helpers (optional) `reset_slots`, `append_slot`, `remove_slot`

Security: All write endpoints will include `dependencies=[Depends(get_current_user)]`.

---

### What I will add (Admin UI)
New/updated API client: `admin_ui/src/api/professionals.ts`
- `listProfessionalDetails(tenant)`
- `updateProfessional(tenant, name, payload)`
- `deleteProfessional(tenant, name)`
- `resetSlots(tenant, name)` and optional `appendSlot/removeSlot` if we include those endpoints

Professionals page updates: `admin_ui/src/pages/Professionals/Index.tsx`
- Table/list of professionals with columns: Name, Price, Slots (#)
- Actions per row:
  - Edit (opens dialog to change name/price)
  - Delete (confirm modal)
  - Edit Slots (already present — right panel) and “Reset slots to default” button
- Adding fine‑grained slot editing (optional):
  - Buttons to append/remove one time label at a time (uses optional append/remove endpoints)

Navigation: Already added “Professionals” item in the left drawer. Route will stay at `/professionals`.

---

### How to use (after I add the endpoints and UI controls)
- Create: click “Add”, enter name, price, and optional initial slots → Save.
- Read: left list shows professionals; click one to load its slots and summary.
- Update (professional): click “Edit” on a row → change name and/or price → Save.
- Update (slots): in the right panel edit the comma‑separated times, click Save. Or click “Reset slots to default” to revert to 09:00–18:30.
- Delete: click “Delete” on a row → confirm. (We can block delete if you have a policy about existing appointments.)

---

### Current endpoints you can already test
- Create professional (JWT/cookie required):
```bash
curl -X POST 'http://127.0.0.1:8100/v1/tenants/demo-salon/professionals' \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Charlie","price":45,"slots":["09:00","09:30","10:00"]}'
```
- List professionals (names):
```bash
curl 'http://127.0.0.1:8100/v1/tenants/demo-salon/professionals'
```
- Get slots:
```bash
curl 'http://127.0.0.1:8100/v1/tenants/demo-salon/professionals/Charlie/slots'
```
- Update slots (replace):
```bash
curl -X PUT 'http://127.0.0.1:8100/v1/tenants/demo-salon/professionals/Charlie/slots' \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"slots":["11:00","11:30","12:00","12:30"]}'
```

---

### Questions to confirm before I code the remaining parts
1) Delete behavior: Allow deleting a professional regardless of existing appointments, or block if any appointment exists (current or future)?
2) Rename behavior: If renaming changes the professional’s name, do you want us to also migrate any existing appointments to the new name? (Recommended)
3) Slot helpers: Do you want append/remove single slot endpoints, or is bulk replace + reset sufficient?

Reply with your preferences (defaults: allow delete, migrate appointments on rename, keep bulk replace + reset), and I’ll implement the backend endpoints and complete the UI controls accordingly, then share run and test steps.