### What is an Action node and how it works
In your WhatsApp menu tree, every node is either:
- `submenu` — shows a list of numbered options (1, 2, 3, …) that point to other nodes, or
- `action` — executes a specific action (e.g., show offers, open URL, list time slots) and replies to the user.

When a user types a number in a submenu, the system finds the matching option’s `next` node. If that `next` node is an `action`, it runs that action and sends the reply. If that `next` node is another `submenu`, it renders that submenu.

Behind the scenes, we also enforce capability guards: if an action node lists `requires_caps`, the tenant must have those capabilities enabled (Super Admin → Modules & Capabilities) or the system will reply with “This option is not available for this tenant.”

---

### Supported Action types (current MVP)
You can choose these values in the Action node’s `action` field:
- `select_timeslot`
  - Purpose: list near‑term available slots (MVP demo) and let the user pick.
  - Typical use: Salon/Clinic booking flows.
  - Optional `requires_caps`: `salon.appointments` (or your domain capability for booking).
  - UI reply: lists a few slots; in the current MVP, it does not yet create a booking (we can extend it next).

- `show_offers`
  - Purpose: show a short list of promotions/offers (placeholder now; can be connected to Promotions later).
  - No params required.

- `open_ticket`
  - Purpose: acknowledge an enquiry/ticket (MVP placeholder; can be extended to persist tickets).
  - Optional params: `{ "category": "general" }` (stored/echoed in the MVP).

- `open_url`
  - Purpose: reply with a link.
  - Params: `{ "url": "https://example.com/help" }`.

- `api_call` (planned)
  - Purpose: call an internal API with allowlisting (to be added if you need it now).

We can add more handlers on request (e.g., `catalog_browse`, `order_status`, `cancel_appointment`).

---

### How to configure actions in the Admin UI (no JSON editing needed)
1) Go to Admin UI → WhatsApp → Menus → Edit (or New → then Edit)
2) In the Visual editor:
   - Add a new node → choose type `Action`.
   - In the Inspector (right side):
     - Action Kind: pick one of `select_timeslot`, `show_offers`, `open_ticket`, `open_url`.
     - Title (optional): a human‑friendly label shown to the user if needed (fallback text).
     - Params (only for some actions):
       - `open_url`: set `url` field.
       - `open_ticket`: set optional `category`.
     - Requires capabilities (optional but recommended): add capability ids needed (e.g., `salon.appointments`).
3) Link your submenu to the action:
   - Select your `submenu` node (often `root`).
   - In “Options”, add or edit an option:
     - Key: numeric string like `1`, `2`, `3`.
     - Label: what the user sees (e.g., “Book”, “Offers”).
     - Next: choose the Action node you created (from the dropdown of nodes).
4) Save Draft → Publish.

That’s it. When a user sends the number (e.g., `1`), the system follows the option’s `next` to the Action node and runs it.

---

### Example configuration from the Visual editor
- Submenu (root):
  - Options → Key `1`, Label `Book`, Next `book`
  - Options → Key `2`, Label `Offers`, Next `offers`
- Action node `book`:
  - Kind: `select_timeslot`
  - Requires caps: `salon.appointments`
- Action node `offers`:
  - Kind: `show_offers`

User flow:
- User sends `1` → engine jumps to node `book` → runs `select_timeslot` → replies with slot list.
- User sends `2` → engine runs `show_offers`.

---

### Versioning and publishing
- You can create/edit in Draft; publish creates a new version (v1, v2, …).
- Menus list shows all Published versions; “View” opens a specific version read‑only; “Fork as Draft” lets you clone that version to the Draft and edit.

---

### Triggers and actions working together
- You can define triggers (WhatsApp → Triggers) to jump straight to an action or submenu:
  - Example: `book` (contains) → Action: `jump_node` → menu `default` (or your menu id), node `book`.
  - Then user types “book” and the flow shows timeslots immediately.

---

### Troubleshooting tips
- Number typed but action didn’t run:
  - Check the submenu option’s `key` matches the user’s number exactly (e.g., `"1"`).
  - Check the option’s `next` points to an Action node id (case‑sensitive).
  - Ensure tenant has the `requires_caps` enabled if you set them (Super Admin → Modules & Capabilities).
  - If the reply says “Invalid choice”, the key didn’t match; “Menu is invalid” means the node id in `next` doesn’t exist.

- Wrong menu loaded:
  - If you have multiple published menus, set `active_menu_id` in WhatsApp Config (or ensure the intended menu is the latest published). The system picks: active_menu_id → `default` (if published) → global latest published.

---

### Quick checklist to add a new action from UI
- [ ] Create or edit a menu (Visual editor)
- [ ] Add an Action node (select Kind, fill Params if needed)
- [ ] Link it from a Submenu option (key/label/next)
- [ ] (Optional) Add `requires_caps` on the Action node and enable those caps for the tenant
- [ ] Save Draft → Publish
- [ ] Test via WhatsApp → Triggers → Test a phrase (or the Twilio sandbox)

If you tell me which specific action flow you want (e.g., full appointment booking with multi‑step service → professional → slot → confirm), I can extend the action handlers and session logic next so it actually creates bookings instead of just listing slots.