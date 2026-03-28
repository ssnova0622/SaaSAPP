### Acknowledged choices and tailored plan
You chose:
- Admin UI: yes (server‑rendered first)
- Channels: both WhatsApp and Email
- Customer import: CSV
- Timezone: “Asia/Kolkat”
- PDF engine: ReportLab
- Storage for reports: S3

Important: The timezone looks misspelled. The canonical IANA name is likely `Asia/Kolkata`. Please confirm so we can store the correct TZ on tenants and schedule jobs reliably.

---

### What I will implement next (Milestone 1–2 scope)
1) Foundations
- Messaging abstraction (`services/messaging.py`):
  - WhatsApp via Twilio (text + media).
  - Email via SMTP.
  - Both support a dev no‑op mode for local testing.
- Scheduler (APScheduler): background jobs for promotions sending, follow‑ups, and daily PDF reports, TZ‑aware per tenant.
- Tenant settings: extend `tenants` docs to include `owner_email`, `owner_phone`, `tz`, `invoice_delivery` (will set `'both'`), `followup_prefs`, and `templates`.
- S3 integration (`services/storage_s3.py`): upload PDFs to S3 with either public object ACL or presigned URLs.

2) Admin UI skeleton and initial pages
- Login and session (simple password or API key from env).
- Dashboard: high‑level KPIs and tenant picker.
- Customers: list/create, CSV import page, simple tags management.
- Promotions: create/edit page (audience: all/tags/custom), “Send now” or schedule; progress live via WebSocket.
- Settings: edit tenant contact, timezone, delivery mode, follow‑up timings, and message templates.

I will then proceed with:
3) Follow‑ups (enqueue on appointment events; dispatcher)
4) Daily report PDF generation (ReportLab), store on S3, and send via email + WhatsApp
5) Retention metrics and views, with quick “win‑back” promotion actions

---

### Config you’ll need to provide (via .env or environment)
- Admin UI auth
  - `ADMIN_USERNAME=...`
  - `ADMIN_PASSWORD=...`
- Twilio (WhatsApp)
  - `TWILIO_ACCOUNT_SID=...`
  - `TWILIO_AUTH_TOKEN=...`
  - `TWILIO_WHATSAPP_FROM=whatsapp:+<your_number>`  (e.g., `whatsapp:+14155551234`)
- SMTP (Email)
  - `SMTP_HOST=...`
  - `SMTP_PORT=587` (or 465)
  - `SMTP_USER=...`
  - `SMTP_PASSWORD=...`
  - `SMTP_FROM="Your Brand <noreply@yourdomain.com>"`
- AWS S3 (for PDFs)
  - `AWS_ACCESS_KEY_ID=...`
  - `AWS_SECRET_ACCESS_KEY=...`
  - `AWS_REGION=ap-south-1` (or your region)
  - `REPORTS_BUCKET=your-bucket-name`
  - `REPORTS_PREFIX=reports/` (optional path prefix)
  - Optional: `REPORTS_PUBLIC_BASE_URL=https://your-bucket.s3.amazonaws.com/` (if using public objects) — otherwise we’ll generate presigned URLs per request.
- Defaults
  - `DEFAULT_TZ=Asia/Kolkata` (pending your confirmation)
  - `SCHEDULER_ENABLED=true`

Security note: share secrets through your deployment secrets manager or a secure channel, not in chat.

---

### S3 delivery model options (pick one)
- Public objects:
  - Upload PDFs with `ACL: public-read` and a predictable key like `reports/{tenant}/{YYYY-MM-DD}.pdf`.
  - Pros: Simpler WhatsApp media messages (just place the URL). Cons: Objects are public if someone guesses the URL.
- Presigned URLs (recommended):
  - Keep objects private, generate a short‑lived presigned URL and include it in the email/WhatsApp message.
  - Pros: Secure by default. Cons: Slightly more code; WhatsApp users must open the link in a browser (works fine).

Unless you prefer otherwise, I’ll implement presigned URLs.

---

### Data model additions (Mongo)
- `tenants` (extend): `owner_email`, `owner_phone`, `tz`, `invoice_delivery`, `followup_prefs`, `templates`
- `customers`: `{ tenant, phone, name, email?, tags:[], last_seen_at, total_bookings, score? }`
- `promotions`: `{ _id, tenant, name, channel: 'whatsapp'|'email'|'both', message, html_message?, media_url?, audience:{ type, tags?, phones? }, schedule_at?, status, created_at }`
- `promotion_logs`: `{ promotion_id, tenant, to, channel, status, error?, sent_at }`
- `followups`: `{ _id, tenant, appointment_id, to_phone, to_email?, type, run_at, status, last_error? }`
- `reports`: `{ tenant, date, s3_key, url_type: 'public'|'presigned', sent_via, status, error?, created_at }`

---

### Admin UI pages (first cut)
- `/admin/login` → login form
- `/admin` → dashboard + tenant picker
- `/admin/{tenant}/settings` → settings form (email, phone, tz, invoice delivery, templates)
- `/admin/{tenant}/customers` → list + create + CSV import
- `/admin/{tenant}/promotions` → list + create/edit + send/schedule, progress
- `/admin/{tenant}/appointments` → list + cancel
- `/admin/{tenant}/reports` → list PDFs + “Generate now”

We’ll use Jinja2 templates and Bootstrap for speed.

---

### Follow‑ups (initial templates)
- Confirmation: “Hi {{customer_name}}, your booking with {{professional}} at {{time}} is confirmed. Reply HELP for assistance.”
- Reminder (24h): “Reminder: {{professional}} at {{time}} tomorrow. Reply 1 to confirm, 2 to reschedule.”
- Reminder (2h): “You’re due in 2 hours for {{professional}} at {{time}}.”
- Post‑visit: “Thanks for visiting! Rate us: <link>. Book again and get 10% off.”

These can be edited per tenant from the Admin Settings.

---

### Next actions from you
- Confirm the timezone string: shall I set `Asia/Kolkata`? (Your message says “Asia/Kolkat”).
- Provide:
  - Twilio WhatsApp enabled sender number (format `whatsapp:+xxxxxxxxxxx`).
  - S3 bucket name and region; confirm presigned URL approach.
  - SMTP sender details.

Once confirmed, I’ll start implementing Foundations + Admin UI skeleton + Promotions API/UI and share a first running version. I’ll also wire daily report job using ReportLab and S3, with presigned links sent over both Email and WhatsApp.