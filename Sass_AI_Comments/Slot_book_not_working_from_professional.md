### Plan: Fix “Slot book not working from Professionals menu”

#### Objectives
- Make booking a slot from the Professionals page work reliably.
- Surface clear error messages in the UI (e.g., inactive professional, slot already booked).
- Keep slot state in sync (book/cancel reflects immediately).

---

### 1) Reproduce and gather evidence
- Steps:
  - Open Professionals page, select a professional, attempt to book a specific time.
  - Record tenant, professional name, time selected, and UI behavior.
  - In browser DevTools → Network, capture the POST request to `/v1/tenants/{tenant}/appointments` and the response status/body.
  - Check Console for any unhandled errors.
- Expected outcomes to classify issue:
  - 401 Unauthorized → token or baseURL problem.
  - 403 Forbidden with `Professional is inactive` → pro is inactive; UI must prevent booking.
  - 404 `Professional not found` → name mismatch.
  - 400 `Slot not available` → stale slot view; UI needs refresh/feedback.

### 2) Backend sanity checks (API level)
- Using curl/Postman with same payload from UI:
  - POST `/v1/tenants/{tenant}/appointments` → ensure it succeeds for an available slot and returns 201.
  - Failure cases return mapped codes/messages already implemented:
    - 404 `Professional not found`
    - 403 `Professional is inactive`
    - 400 `Slot not available`
- Verify GET `/v1/tenants/{tenant}/professionals/{professional}/slots` reflects slot status before/after booking and after cancel.

### 3) Identify likely root cause and fix path
- If 403 (inactive):
  - Confirm the professional status in left list chip. UI already disables actions when inactive; fix any edge path where booking still opens. Show tooltip/inline note.
- If 400 (unavailable):
  - Refresh slots when opening the booking dialog, and after cancel/confirm.
  - Keep the dialog open and show inline error; let the user pick another time.
- If 401:
  - Verify JWT present; ensure axios baseURL matches backend; redirect to login on 401 (already configured).
- If 404 (name mismatch):
  - Normalize names consistently; ensure selected item uses exact value passed to API.

### 4) Frontend improvements (Professionals page)
- Booking dialog UX:
  - Add error state in the dialog to display backend `detail` on failure (403/400/404).
  - Add `submitting` state; disable Confirm while submitting.
  - On open, refresh latest slots to reduce stale state.
- Slot status source of truth:
  - Use server slot statuses directly (from `/slots`) for the “Status” Select; keep current appointment list as a secondary indicator only.
- Inactive professionals:
  - Keep booking/slot-edit controls disabled when inactive (already implemented) and show a small hint banner.

### 5) Backend refinements (only if needed)
- Confirm error mappings are correct (they are in current code).
- No schema changes expected.

### 6) Verification
- E2E checks:
  - Book: choose available time, create appointment, see slot flip to booked row highlight and status.
  - Double-book prevention: try booking the same time again → see friendly error in dialog.
  - Cancel: cancel the appointment → slot flips back to available.
  - Toggle pro inactive → booking/edit controls disabled; forced API call returns 403.

### 7) Handover/testing notes
- If the issue persists, share:
  - Screenshot of the booking dialog and table row.
  - The Network request/response for the POST and any error JSON.
  - Console errors.

---

### What I need from you to proceed quickly
- When you click Book, do you see any error in the dialog or the browser console?
- Can you share the HTTP status code and `detail` message from the POST `/appointments` response (Network tab)?
- The tenant id, professional name, and the time you attempted to book.

With that info, I can apply the UI error-handling improvements and any necessary tweaks right away and verify booking works end-to-end.