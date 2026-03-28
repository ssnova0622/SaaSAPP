# WhatsApp Menu Workflow – How It Works

The WhatsApp flow is driven by a **conversation engine** (`whatsapp_conversation_engine.process`): one entry point that loads the user’s session, resolves the message (menu vs option vs workflow step), and returns the reply plus any session update. The webhook calls this engine and then persists the session so the next message sees the correct state (e.g. “in menu” after “hi”, so “1” is resolved as option 1).

This guide explains how the flow behaves:

1. **When a customer sends a message** (e.g. *hi* or *hello*), they receive a **welcome message** with your list of options, and the session is set to “in menu” with that menu’s id.
2. **When they choose an option** (e.g. *1*, *5*), the engine uses the session’s menu id to resolve the step and the **correct flow runs** (Book appointment, Check price, template, etc.).
3. **When they enter a wrong number** (e.g. *9* when you only have 1–6), they get an **alert** and the **same options** are shown again.

---

## How the flow behaves

### 1. Customer opens WhatsApp and sends a message

- Customer sends: **hi** or **hello** (or whatever trigger you set).
- System finds the **welcome menu** (the step with reply type **Menu** and trigger *hi* / *hello*).
- Customer receives:
  ```
  Please choose an option:
  1. Book appointment
  2. Cancel appointment
  3. Reschedule appointment
  4. My appointments
  5. Check price
  6. View professionals
  ```

### 2. Customer chooses a valid option

- Customer sends: **1** → system finds the step with trigger **1** → runs **Book appointment** (text, template, or dynamic action).
- Customer sends: **5** → system finds the step with trigger **5** → runs **Check price** (e.g. list of services and prices).
- Same for **2**, **3**, **4**, **6**: each trigger runs the flow you configured for that number.

So: **1 = Book appointment, 2 = Cancel appointment, 3 = Reschedule, 4 = My appointments, 5 = Check price, 6 = View professionals** — each number runs the right flow.

### 3. Customer enters a wrong number (e.g. 9)

- Customer sends: **9** (or any text that is not a valid trigger, e.g. *xyz*).
- No menu step matches.
- System sends an **alert** and **the same options again**:
  ```
  That option isn't available. Please choose one of the options below:
  1. Book appointment
  2. Cancel appointment
  3. Reschedule appointment
  4. My appointments
  5. Check price
  6. View professionals
  ```

So the customer sees clearly that they must choose a valid number, and the options stay visible.

---

## How to create the WhatsApp workflow (admin steps)

Do this in **Admin → WhatsApp → Menu** (for the correct tenant).

### Step 1: Create the welcome menu

This is what customers see when they first message you.

1. Click **Add step**.
2. **When customer says:** `hi` (you can add another step later for `hello` with the same options, or use one trigger like `hi`).
3. **We reply with:** **Menu (list of options)**.
4. **Menu options** – enter one option per line in the form **number|Label**:
   ```
   1|Book appointment
   2|Cancel appointment
   3|Reschedule appointment
   4|My appointments
   5|Check price
   6|View professionals
   ```
5. Click **Create step**.

Result: when a customer sends **hi** (or **hello** if you add that trigger too), they get the message “Please choose an option:” and the list 1.–6.

---

### Step 2: Create one step per option (what happens when they choose 1, 2, 3, …)

For **each** number (1, 2, 3, 4, 5, 6) you must add a **separate step** that defines what happens when the customer sends that number.

| When customer says | We reply with | What to set |
|-------------------|---------------|-------------|
| **1** | Dynamic action → **Book appointment** | Optional custom message (e.g. booking link or instructions). |
| **2** | Dynamic action → **Cancel appointment** | Lists their appointments; they reply with a number to cancel that one; slot reopens. |
| **3** | Dynamic action → **Reschedule appointment** | Lists their appointments with reschedule instructions. |
| **4** | Dynamic action → **My appointments** | Lists upcoming appointments for their WhatsApp number. |
| **5** | Dynamic action → **Check price** | Lists your services and prices (from Appointments → Services). |
| **6** | Dynamic action → **View professionals** | Lists your professionals (from your tenant data). |

**Example for option 1 (Book appointment):**

1. Click **Add step**.
2. **When customer says:** `1`
3. **We reply with:** **Dynamic action**
4. **Action:** choose **Book appointment**
5. Optionally add **Custom message** (e.g. “Reply with your preferred date and time” or your booking link).
6. Click **Create step**.

**Example for option 5 (Check price):**

1. Click **Add step**.
2. **When customer says:** `5`
3. **We reply with:** **Dynamic action**
4. **Action:** choose **Check price**
5. Click **Create step** (no custom message needed; system will list services and prices).

Repeat the same idea for 2, 3, 4, and 6 with the corresponding dynamic actions.

---

### Step 3: (Optional) Same welcome for “hello”

If you want **hello** to show the same menu as **hi**:

1. Click **Add step**.
2. **When customer says:** `hello`
3. **We reply with:** **Menu (list of options)**
4. **Menu options:** use the **same** lines as in Step 1 (1|Book appointment, 2|Cancel appointment, …).
5. Click **Create step**.

Now both **hi** and **hello** show the same welcome and options.

---

## Quick setup: “Create example flow”

- Click **Create example flow** to auto-create:
  - Welcome menu (triggers **hi** and **hello**) with 6 options.
  - Six steps for triggers **1**–**6** (Book appointment, Cancel appointment, View offers, Check price, My appointments, Contact us).
- You can then **edit** each step (e.g. change 3 to Reschedule, 6 to View professionals) or add more options and steps.

---

## Summary

| Customer sends | What happens |
|----------------|--------------|
| **hi** or **hello** | Welcome message with: 1. Book appointment, 2. Cancel appointment, 3. Reschedule…, 4. My appointments, 5. Check price, 6. View professionals. |
| **1** | Book appointment flow runs. |
| **2** | Cancel appointment flow runs (list → they choose → cancel & slot reopens). |
| **3** | Reschedule appointment flow runs. |
| **4** | My appointments flow runs. |
| **5** | Check price flow runs (services and prices). |
| **6** | View professionals flow runs. |
| **9** (or any invalid) | Alert: “That option isn’t available. Please choose one of the options below:” and the **same options** (1.–6.) are shown again. |

---

## Where to configure

- **Admin UI:** Select tenant → **WhatsApp** → **Menu**.
- **Test:** **WhatsApp** → **Simulator** (send *hi*, then *1*, *5*, *9* to see welcome, option 1, option 5, and wrong-number behaviour).

---

## Backend: conversation engine and testing

- **Single entry point:** All reply logic runs in `app/services/whatsapp/whatsapp_conversation_engine.process(tenant, from_phone, text, session=None, config=None)`. It returns `{ "body", "session_update", "clear_session" }`. The webhook calls this and then applies session update so the next message sees the correct state.
- **Session:** Stored in `whatsapp_sessions` with id `wa_sess_{tenant}_{normalized_phone}` (phone normalized to digits, last 10 for long numbers). After “hi” the session holds `flow: "in_menu"` and `context: { "menu_id": "<main menu id>" }` so “1” is resolved under that menu.
- **Test endpoint:** `POST /tenants/{tenant}/whatsapp/conversation/process` with body `{ "from_phone": "9876543210", "message": "hi" }` then `{ "from_phone": "9876543210", "message": "1" }` to test the full flow with persisted session (same as webhook behaviour).
- **AI fallback:** If no menu matches and the default “Reply with *hi* to see options.” would be sent, and the WhatsApp config has `ai_autoreply_enabled` and `ai_autoreply_prompt_code`, the engine can call the AI prompt to generate a reply instead.
