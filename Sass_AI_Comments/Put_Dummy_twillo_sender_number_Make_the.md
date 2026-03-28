### Acknowledged — will wire with dummy creds and JWT
I’ll proceed with React Admin UI + FastAPI backend using:
- Dummy Twilio WhatsApp sender number
- Dummy S3 credentials/bucket (presigned URL flow)
- SMTP placeholders (code present; you will replace creds later)
- JWT‑based auth for Admin/API

Below are the exact placeholders, environment variables, and how auth will work so you can run everything immediately. You can swap real values later without code changes.

---

### Environment variables (backend) — with safe dummy defaults
Add these to your `.env` (or environment) for the AI Scheduler backend:

Auth/JWT
- `ADMIN_DEFAULT_USER=admin`
- `ADMIN_DEFAULT_PASS=admin123`  (Change in non‑dev!)
- `JWT_SECRET=dev-secret-change-me`
- `JWT_EXP_MINUTES=120`

Twilio WhatsApp (dummy — code won’t send unless enabled)
- `TWILIO_ENABLED=false`  (set `true` in prod)
- `TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
- `TWILIO_AUTH_TOKEN=your_auth_token_here`
- `TWILIO_WHATSAPP_FROM=whatsapp:+14155550123`  (dummy test sender)

SMTP Email (placeholders)
- `SMTP_ENABLED=false`  (set `true` in prod)
- `SMTP_HOST=smtp.example.com`
- `SMTP_PORT=587`
- `SMTP_USER=noreply@example.com`
- `SMTP_PASSWORD=your_smtp_password`
- `SMTP_FROM="Your Brand <noreply@example.com>"`

AWS S3 (dummy — presigned URLs; no upload unless enabled)
- `S3_ENABLED=false`  (set `true` in prod)
- `AWS_ACCESS_KEY_ID=AKIADEVEXAMPLEKEY`
- `AWS_SECRET_ACCESS_KEY=devsecretkeyexample`
- `AWS_REGION=ap-south-1`
- `REPORTS_BUCKET=demo-reports-bucket`
- `REPORTS_PREFIX=reports/`

Scheduler + defaults
- `SCHEDULER_ENABLED=true`
- `DEFAULT_TZ=Asia/Kolkata`
- `INVOICE_DELIVERY=both`  (per your preference)

Mongo (already present, reminder)
- `MONGO_URI=mongodb://localhost:27017/ss_salon`

CORS (for React dev server)
- `CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173`

Notes
- With `TWILIO_ENABLED=false`, `SMTP_ENABLED=false`, `S3_ENABLED=false`, the app will run in no‑op mode: messages are logged only; PDFs are generated in memory and discarded or saved locally for preview.
- Flip these flags to `true` and supply real creds to activate live sending and S3 uploads.

---

### JWT authentication design
Backend
- `POST /v1/auth/login` → body: `{username, password}`
  - Validates against an in‑app user store (initially just `ADMIN_DEFAULT_USER/PASS` in env; can add Mongo users later).
  - Returns `{ access_token, token_type:"bearer", expires_in }`
- Protect Admin/API routes with JWT bearer middleware:
  - Required header: `Authorization: Bearer <token>`
  - Token signed with `HS256` using `JWT_SECRET`, expiry `JWT_EXP_MINUTES`.
- Optional refresh token endpoint can be added later.

Frontend (React)
- Login form posts to `/v1/auth/login`.
- Store token (HTTP‑only cookie preferred; for simplicity we can start with memory/localStorage).
- All subsequent API calls include the `Authorization` header.

Roles (later)
- We can extend token claims to include a role (`admin`, `ops`, `viewer`) and gate endpoints accordingly. For MVP all Admin UI features require `admin`.

---

### Messaging behavior with dummies
- WhatsApp via Twilio
  - When `TWILIO_ENABLED=false`, `send_whatsapp_text` and `send_whatsapp_media` will log the request and succeed without external calls.
  - When set to `true`, they use `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_FROM` to send real messages.
- Email via SMTP
  - With `SMTP_ENABLED=false`, `send_email` logs only.
  - When `true`, it connects to `SMTP_HOST/PORT` using user/password, sends from `SMTP_FROM`.

---

### S3 reports with dummies
- With `S3_ENABLED=false`, PDFs will be generated and either:
  - saved locally under `./reports/{tenant}/{date}.pdf` (dev mode), and served by a dev download endpoint, or
  - discarded but metadata logged (choose preferred dev behavior; I’ll default to local save).
- With `S3_ENABLED=true`, the service uploads to `REPORTS_BUCKET` using `REPORTS_PREFIX`, then generates a presigned URL for 24h.

---

### React Admin UI (unchanged high‑level)
- Uses JWT login → tokens on requests.
- Sends promotions via both channels by default (if recipient has both phone and email; otherwise whichever exists).
- CSV import for customers maps `name, phone, email, tags` (optional columns ok).
- Per‑tenant timezone set to `Asia/Kolkata` by default; daily report at 19:30 local.

---

### Immediate next deliverables I’ll implement
1) Backend foundations
- Auth router (`/v1/auth/login`) with JWT.
- Messaging service stubs honoring `*_ENABLED` flags.
- S3 storage stub with local fallback when disabled.
- CORS configured for React dev.

2) Admin‑supporting endpoints
- Tenants settings GET/PUT
- Customers list/create/import
- Promotions CRUD + send (queued)
- Follow‑ups: schedule on appointment create/cancel; list scheduled
- Reports: manual generate (PDF via ReportLab) → upload (S3 or local) → return URL

3) React Admin shell (Vite + MUI)
- Login → Dashboard → Settings → Customers (incl. CSV) → Promotions basics

If you want me to start coding now, I’ll proceed with these modules and provide run instructions for both backend and React dev server in the next update.