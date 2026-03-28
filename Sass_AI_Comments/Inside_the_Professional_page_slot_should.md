### Professionals page updated: interactive slot booking/cancel with proper format
I’ve implemented the requested changes so that the Professionals page shows slots in a clear table with a status dropdown per time, and lets an admin book or cancel slots directly.

#### What’s new (Admin UI)
- Page: `admin_ui/src/pages/Professionals/Index.tsx`
  - Left: list of professionals (select one)
  - Right: Slots table with columns: Time | Status | Actions
    - Status is a dropdown with values `available` or `booked`
    - If you switch to `booked`, a booking dialog opens to collect customer name and phone, and creates an appointment for that time
    - If the time is already booked, you can cancel the appointment from the row
  - Bulk edit slots (comma‑separated times) remains available in a separate card below, to replace the day’s slots in one go
  - “Add professional” dialog (name, price, initial slots optional) remains available

#### Backend endpoints used
- List professional names (no auth):
  - `GET /v1/tenants/{tenant}/professionals`
- Get slots for a professional (no auth):
  - `GET /v1/tenants/{tenant}/professionals/{name}/slots`
- Create professional (auth required — JWT header or login cookie):
  - `POST /v1/tenants/{tenant}/professionals`
- Update slots (bulk replace, auth required):
  - `PUT /v1/tenants/{tenant}/professionals/{name}/slots`
- Create appointment (books slot; auth not required for read but required typically for Admin flow):
  - `POST /v1/tenants/{tenant}/appointments`
- Cancel appointment:
  - `DELETE /v1/tenants/{tenant}/appointments/{appointment_id}`

Note: I also wired the UI to load all appointments (`GET /v1/tenants/{tenant}/appointments`) to determine per‑slot booking status and which appointment to cancel. The slot’s dropdown reflects whether there’s a `booked` appointment for that exact `time` for the currently selected professional.

---

### How to use (step‑by‑step)
1) Start backend and UI (recap)
   - Backend (port 8100):
     ```bash
     export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
     export ADMIN_DEFAULT_USER=admin
     export ADMIN_DEFAULT_PASS=admin123
     uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
     ```
   - Frontend (port 5173):
     ```bash
     cd admin_ui
     npm i -D vite-tsconfig-paths  # if not installed yet
     npm install
     npm run dev
     ```
2) Open http://localhost:5173 and login (`admin/admin123`).
3) In the left drawer, pick a tenant (e.g., `demo-salon`).
4) Click “Professionals”.
5) Select a professional from the left list.
6) In the Slots table:
   - To book a time: change Status to `booked` or click the “Book” button → fill in customer details → Confirm.
   - To cancel: for a `booked` time, click “Cancel”.
7) To bulk edit slots: use the “Times (comma separated)” field and click “Save Slots” to replace the schedule for that pro.
8) To add a new professional: click the “Add” button in the left card.

---

### If the Professionals page still shows the Dashboard text
That means the `/professionals` route didn’t load. Do these quick checks:
- In `admin_ui/src/App.tsx`, ensure:
  ```tsx
  import Professionals from '@pages/Professionals/Index'
  ...
  <Route path="professionals" element={<Professionals />} />
  ```
- In `admin_ui/src/components/AppShell/AppShell.tsx`, ensure the nav contains `{ label: 'Professionals', to: '/professionals' }`.
- Confirm alias support (either `vite-tsconfig-paths` plugin installed and referenced in `vite.config.ts`, or manual `resolve.alias`). Restart `npm run dev` and hard refresh.
- Directly open http://localhost:5173/professionals and check the browser console for any import errors.

---

### Notes & next enhancements
- The booking dialog creates an appointment via `POST /appointments`; cancellation calls `DELETE /appointments/{id}`.
- If you’d like per‑slot add/remove endpoints (instead of the bulk replace), or a “Reset slots to default 09:00–18:30” button, I can add those quickly.
- If you want rename/delete for professionals and a detailed professionals list (name, price, slots count), I can wire those too. Defaults I’d implement unless you say otherwise:
  - Deleting allowed even if appointments exist (or we can block if you prefer)
  - Renaming migrates existing appointments from old name → new name

Tell me your preferences for delete/rename and reset/append/remove, and I’ll finalize those endpoints and UI controls next.