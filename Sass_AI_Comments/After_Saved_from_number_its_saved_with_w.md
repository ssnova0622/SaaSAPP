### Change applied: accept `whatsapp:` prefix in WhatsApp Config UI and keep Save enabled

I fixed the Admin UI validation so numbers that already include the `whatsapp:` prefix are treated as valid. Previously, the UI validated only pure E.164 (`+1415…`), which caused the warning “Invalid numbers: whatsapp:+14155238886” and disabled the Save button when you reopened the page after the backend normalized and saved with the prefix.

#### What I changed
- Admin UI: WhatsApp → Config page (`admin_ui/src/pages/WhatsApp/Config.tsx`)
  - Validation now strips an initial `whatsapp:` prefix before checking the E.164 pattern. This means both `+14155238886` and `whatsapp:+14155238886` are accepted.
  - The error banner for invalid numbers now displays the numbers without the `whatsapp:` prefix for clarity.
- Backend (already done in previous step):
  - On save, the API normalizes every number to include the `whatsapp:` prefix and stores both `from_numbers` (array) and `from_number` (first item) consistently.

#### What this means for you
- You can enter either form in the UI:
  - `+14155238886` (recommended input)
  - `whatsapp:+14155238886` (also accepted)
- After saving, the backend will store it as `whatsapp:+14155238886`.
- When you reopen the page, the Save button will no longer be disabled and no invalid-number warning will appear just because the value has the prefix.

#### Next steps for you
1) Refresh the app (hard refresh) to load the updated UI code.
2) Go to WhatsApp → Config for `ss-salon` and verify:
   - From numbers shows `whatsapp:+14155238886`.
   - No “Invalid numbers” warning is shown.
   - Save button is enabled (unless other required fields are empty).
3) Optional: If you prefer to see plain E.164 in the textbox, you can replace the line with the bare `+14155238886`; the backend will normalize it back to `whatsapp:+…` on save.

#### Reminder: end‑to‑end setup recap for `ss-salon`
- Config saved with From numbers: `whatsapp:+14155238886` (now validated correctly)
- Twilio webhook URL set to `POST https://<your-domain>/v1/integrations/twilio/whatsapp/webhook`
- Published menu exists (e.g., `default`)
- Optional triggers for “hi”, “book”, “enquiry”

If you still see the warning after a hard refresh, please let me know the exact values shown in the “From numbers” box, and I’ll adjust the UI rendering to strip the prefix visually as well.