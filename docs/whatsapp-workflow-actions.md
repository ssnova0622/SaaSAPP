# WhatsApp Workflow Actions – Use Cases and Flows

This document describes the **real actions** behind each WhatsApp menu option: what happens when the user selects "Book appointment", "Cancel appointment", etc., and how multi-step flows work.

---

## Overview

| Action | Type | Flow | Use cases |
|--------|------|------|-----------|
| **Book appointment** | Multi-step | `book_appointment` | List specialists (optional) → List professionals → Choose date → Choose slot → Confirm → Create appointment → Update slot (booked) → Send confirmation with reference |
| **Cancel appointment** | Single interaction | `cancel_appointment` | List upcoming appointments → User replies with number → Cancel that appointment → Update status to `cancelled` → Slot reopens → Send confirmation |
| **Reschedule appointment** | Multi-step | `reschedule_appointment` | List upcoming appointments → User picks one → Choose new date → Choose new slot → Confirm → Update appointment → Send confirmation |
| **My appointments** | Single reply | — | List upcoming appointments for customer phone (no session) |
| **Check price** | Single reply | — | List services and prices |
| **View professionals** | Single reply | — | List professionals (or under a specialist when used in booking) |
| **View offers** | Single reply | — | List catalog products/offers |
| **Contact us** | Single reply | — | Custom text or default contact message |

---

## 1. Book appointment flow

**When the user chooses "Book appointment" (e.g. option 1):**

1. **Start**  
   - If the tenant has **specialists**: show "Choose a specialist" with a numbered list.  
   - If the tenant has **no specialists**: show "Choose a professional" with a numbered list.  
   - Session is set to `flow: "book_appointment"` with initial `context`.

2. **Choose specialist** (if applicable)  
   - User replies with a number (e.g. `2`).  
   - Use case: list professionals for that specialist.  
   - Show "Choose a professional" with a numbered list.  
   - Context: `step: "professional"`, `specialist_id`, `professional_ids[]`.

3. **Choose professional**  
   - User replies with a number.  
   - Use case: list available dates for that professional (next 14 days, respecting working hours).  
   - Show "Choose a date" with a numbered list (e.g. "1. Mon 03 Mar").  
   - Context: `step: "date"`, `professional_id`, `date_options[]`.

4. **Choose date**  
   - User replies with a number or a date (e.g. `2025-03-05`).  
   - Use case: get available slots for that professional on that date (from working hours, minus already booked).  
   - Show "Choose a time" with a numbered list (e.g. "1. 09:00", "2. 09:30").  
   - Context: `step: "slot"`, `date_str`, `slot_options[]`.

5. **Choose slot**  
   - User replies with a number.  
   - Show confirmation: "Confirm booking with *Dr. X* on 05 Mar 2025 at 10:00? Reply *1* for Yes, *2* for No."  
   - Context: `step: "confirm"`, `slot_time`.

6. **Confirm**  
   - User replies `1` or `yes` → **use cases**:  
     - Create appointment (tenant, professional/staff_id, date, slot_time, customer_phone).  
     - Slot is considered "booked" (appointment has status `confirmed`; conflicts are prevented by `AppointmentService`).  
     - Optional: reference/token = short appointment id in confirmation message.  
     - Send confirmation message (body) and clear session.  
   - User replies `2` or `no` → "Booking cancelled." and clear session.

**Use cases (backend):**

- `use_case_list_specialists(tenant)` → list of specialists (id, name).
- `use_case_list_professionals(tenant, specialist_id=None)` → list of professionals (id, name); if `specialist_id` given, only those with that specialist.
- `use_case_available_dates(tenant, professional_id, days_ahead=14)` → list of (date_str, display_label).
- `use_case_available_slots(tenant, professional_id, date_str)` → list of `{ "time", "available" }`.
- `use_case_create_appointment(tenant, staff_id, date_str, slot_time, customer_phone, customer_name=None)` → (appointment_doc, confirmation_message) or (None, error_message).

**Session:** `flow: "book_appointment"`, `context: { step, specialist_id?, professional_id?, date_str?, slot_time?, ... }`.

---

## 2. Cancel appointment flow

**When the user chooses "Cancel appointment":**

1. **Start**  
   - Use case: list upcoming appointments for customer phone (`list_upcoming_by_customer_phone`).  
   - Show "Select the appointment to cancel (reply with the number):" and a numbered list.  
   - Session: `flow: "cancel_appointment"`, `context: { appointment_ids: [id1, id2, ...] }`.

2. **User replies with a number**  
   - Use case: `use_case_cancel_appointment(tenant, appointment_id)` → update appointment status to `cancelled`.  
   - Slot is effectively reopened (no longer in "pending" or "confirmed").  
   - Reply: "Your appointment has been cancelled. The slot is now open for rebooking."  
   - Clear session.

If the user sends an invalid number or text, the session is cleared and they see: "Cancellation cancelled. Reply with *hi* to see options."

**Use case:** `use_case_cancel_appointment(tenant, appointment_id)` → (success: bool, message: str).

---

## 3. Reschedule appointment flow

**When the user chooses "Reschedule appointment":**

1. **Start**  
   - Use case: list upcoming appointments for customer phone.  
   - If none: show "You have no upcoming appointments to reschedule..." (no session).  
   - If any: show "Select the appointment to reschedule (reply with the number):" and list.  
   - Session: `flow: "reschedule_appointment"`, `context: { step: "pick_appointment", appointment_ids[] }`.

2. **Pick appointment**  
   - User replies with a number.  
   - Resolve professional (staff_id) from that appointment.  
   - Use case: available dates for that professional.  
   - Show "Choose a new date" and list.  
   - Context: `step: "date"`, `selected_appointment_id`, `professional_id`, `date_options[]`.

3. **Choose date**  
   - User replies with a number.  
   - Use case: available slots for that professional on chosen date.  
   - Show "Choose a time" and list.  
   - Context: `step: "slot"`, `date_str`, `slot_options[]`.

4. **Choose slot**  
   - User replies with a number.  
   - Show: "Reschedule to 05 Mar 2025 at 10:00? Reply *1* for Yes, *2* for No."  
   - Context: `step: "confirm"`, `slot_time`.

5. **Confirm**  
   - User replies `1` or `yes` → **use case**: `use_case_reschedule_appointment(tenant, appointment_id, date_str, slot_time)` → update appointment `start_at`/`end_at`.  
   - Reply: "Your appointment has been rescheduled to ..."  
   - Clear session.  
   - User replies `2` or `no` → "Reschedule cancelled." and clear session.

**Use case:** `use_case_reschedule_appointment(tenant, appointment_id, date_str, slot_time)` → (success: bool, message: str).

---

## 4. Other actions (single reply, no session flow)

- **My appointments:** List upcoming appointments for `from_phone`; no session.
- **Check price:** List services and prices from `ServiceRepository`.
- **View professionals:** List professionals (optionally under a specialist in booking flow).
- **View offers:** List catalog products.
- **Order product:** List products with order instructions.
- **Payment options:** Custom text.
- **Contact us:** Custom text or default.

These are implemented in `_build_dynamic_body` in `whatsapp_menu_service.py` and do not start a multi-step session.

---

## Where it’s implemented

| What | Where |
|------|--------|
| **Workflow registry** (add new flows here) | `app/services/whatsapp/whatsapp_workflow_registry.py` |
| Use cases and flow handlers | `app/services/whatsapp/whatsapp_workflow_actions.py` |
| Dispatch by session flow | Engine and menu service use `has_flow()` / `handle_flow()` / `start_flow()` from registry |
| Professionals by specialist | `ProfessionalRepository.list_by_specialist(tenant, specialist_id)` |
| Availability (dates/slots) | `ProfessionalService.get_availability()`, `AppointmentRepository.get_booked_times_on_date()` |

### Adding a new workflow

1. In **whatsapp_workflow_actions.py**: implement `your_flow_handle(tenant, from_phone, text, context) -> (body, new_context, clear_session)` and optionally a starter `(tenant, from_phone) -> (body, context)`.
2. In **whatsapp_workflow_registry.py**: call `register_flow("your_flow_name", your_flow_handle, starter)` inside `_register_builtin_flows()`.
3. Add the action to **WHATSAPP_ACTION_CATALOG** in `whatsapp_menu_service.py` if it should appear in the admin menu. No other changes needed—engine and menu service use the registry.

---

## Testing the full flow

- **Webhook:** Real WhatsApp messages go through the same engine; session is loaded/saved by phone.
- **Simulator:** Menu flow (hi → 1 → 2) works with `current_menu_id`. For **multi-step booking/reschedule**, use the **conversation process** endpoint so session is persisted:
  - `POST /tenants/{tenant}/whatsapp/conversation/process`  
  - Body: `{ "from_phone": "9876543210", "message": "hi" }` then `"1"` then `"2"` (professional), then date number, then slot number, then `"1"` (confirm).
- **Cancel:** Send "hi" → "2" (Cancel appointment) → then reply with the number of the appointment to cancel.

This gives you real actions end-to-end: fetch professionals → slot selection → confirm → update slot status (booked) → create appointment → send confirmation (with reference token), and the same idea for cancel and reschedule.
