### Goal
Add a complete “Book appointment” flow after `select_timeslot`: let the customer pick a slot, then confirm “Yes/No”, and on Yes create the appointment.

Below I show:
- The simplest way to do it with the current engine (session‑based FSM in the backend, no extra menu nodes)
- An alternative that uses explicit menu nodes (submenu → action → confirm submenu)
- Exactly what to configure in the Admin UI
- The backend hooks we’ll add (minimal changes to `app/routers/whatsapp.py`)

---

### Option A — Backend FSM (recommended: simplest for Admins)
You keep a single Action node in your menu: `salon.select_timeslot`. The backend manages these steps with session context:
1) User picks Book → Action `salon.select_timeslot` runs and replies with numbered timeslots (1..N)
2) User replies with a number → backend stores `ctx.selected_slot` and asks: “Confirm booking for HH:MM? 1) Yes 2) No”
3) User replies 1 → backend creates the appointment and replies with a confirmation (ID). On 2 → returns to the previous submenu/root

What you configure in the Admin UI (Menu Editor):
- Add a Submenu (root or child) with an option “Book appointment” (key `1`) → Next: node `book`
- Add Action node `book`:
  - Action type: `salon.select_timeslot`
  - Requires capabilities: `salon.appointments`
  - No parameters needed for v1
- Publish

What we do in backend (I’ll implement for you):
- Extend `_action_select_timeslot` + the webhook engine to support a mini‑FSM in `whatsapp_sessions`:
  - When action first runs: populate `ctx.mode = "select_slot"`, `ctx.available_slots = ["10:00", "10:30", …]` (up to N)
  - If the next inbound message is a number and `ctx.mode == "select_slot"`: resolve index → write `ctx.selected_slot = "10:30"`, set `ctx.mode = "confirm_booking"`, reply: “Confirm booking for 10:30? 1) Yes 2) No”
  - If message is `1` and `ctx.mode == "confirm_booking"`: create the appointment → clear/close session → reply “Booked! Appointment ID …”
  - If message is `2`: clear pending selection and return to root submenu
- Use existing create appointment logic:
  - If you want a lightweight persistence: call an internal function (or existing router) to insert: `{ tenant, professional, time, customer_phone }`
  - For MVP, we can book with the first available professional (like today), then improve to “pick professional” first (below)

Pros:
- No extra menu authoring for Admins; a single Action node drives the whole flow.
- Easy to evolve later (e.g., choose professional → choose slot → confirm → book)

---

### Option B — Explicit menu nodes (visual flow)
You can build it entirely with menu nodes if you prefer to “see” the confirm step in the editor:
- Submenu `root`: options → `1) Book appointment` → next: `book_flow`
- Submenu `book_flow`: options: `1) Choose Timeslot` → next: `select_slot`
- Action `select_slot`:
  - Action type: `salon.select_timeslot`
  - This action reply lists the timeslots and stores them in session, then jumps to `confirm` submenu (engine assistance), or you can:
- Submenu `confirm`: “Confirm booking for {ctx.selected_slot}? 1) Yes 2) No”
- Action `book_now`: a pseudo‑action with `action_id: core.open_ticket` (placeholder) that the engine maps to “book appointment now” — we will replace it with a real booking action, e.g., `salon.book_selected_slot`

However, Option B still needs backend FSM to remember which slot was chosen, so Option A (pure FSM) is simpler and results in fewer nodes for Admins.

---

### Exact changes I will add (server)
We’ll extend `app/routers/whatsapp.py` in three places:

1) Session helpers (already present) — we’ll store:
- `mode`: `"select_slot" | "confirm_booking"`
- `available_slots`: string[]
- `selected_slot`: string | null
- Optional: `selected_professional`

2) Inbound step processing (Twilio webhook + `/bot/whatsapp/next` + Meta dummy):
- When current node is a submenu: unchanged (key matching). When it’s an Action node:
  - If `action_id == 'salon.select_timeslot'`:
    - If `ctx.mode` is empty: compute slots, set ctx as above, reply with numbered slots
    - Else if `ctx.mode == 'select_slot'` and user sent a number: map index → `selected_slot`, set `mode='confirm_booking'`, reply “Confirm booking for HH:MM? 1) Yes 2) No”
    - Else if `ctx.mode == 'confirm_booking'` and user sent `1`: persist appointment, clear ctx, reply “Booked! …” and reset to root
    - Else if `2`: clear ctx and return to root
    - Else: repeat the current prompt

3) Appointment persistence call
- For MVP:
  - Use the first professional’s name (`Storage.get_professionals(tenant)`) and the `selected_slot` as `time`
  - Call a simple storage/service function (or existing appointments route) to insert the appointment document with status `booked`, and `customer_phone = From`
  - On success: include an appointment id in the reply

No API contract changes are needed; this stays internal to the bot engine.

---

### How you configure it from Admin UI (today)
- Open WhatsApp → Menus → Edit your menu (visual editor)
- Ensure there is a “Book” option pointing to an Action node with:
  - Action kind: `salon.select_timeslot`
  - Requires capability: `salon.appointments`
- Publish
That’s it. The confirmation and booking will happen automatically via the backend FSM.

Optional improvements you can configure later:
- Add a Submenu “Choose professional” before slot selection:
  - We will extend the engine to set `ctx.mode = 'select_prof'`, list professionals as numbered options, store `ctx.selected_professional`, then proceed to timeslots for that professional

---

### Example end‑to‑end messages (user → bot)
- User: “hi” → menu shows Book/Offers/…
- User: “1” (Book) → engine lists timeslots: `1) 10:00  2) 10:30  3) 11:00 …`
- User: “2” → engine: `Confirm booking for 10:30? 1) Yes  2) No`
- User: “1” → engine books the appointment, returns: `Booked! ID APT‑173316…  See you at 10:30.`

---

### What I’ll deliver next
- Implement the FSM around `salon.select_timeslot` as above (session read/write and booking step).
- Add a minimal appointment persistence call (MVP), reusing `Storage` or the existing appointments API.
- Clear, localized prompts; robust input parsing (accept `1`, `1)`, `1.` etc.).
- Guard with `salon.appointments` capability; Tenant Admin auto‑access per Option‑B.

If you confirm, I’ll implement this flow now. Later, we can add the “pick professional” step and Meta interactive button replies so customers can tap instead of typing numbers.