### Quick start: run the Admin UI locally

The Admin UI lives in `admin_ui/` and talks to the FastAPI backend on port 8100. Follow these steps.

#### 0) Prereqs
- Node.js 18+ (or 20+ preferred)
- Python 3.9+ (for the backend)
- MongoDB running locally (Docker or native install)


#### 1) Start MongoDB (one-time per session)
- Docker:
  ```bash
  docker run --name mongo -p 27017:27017 -d mongo:6
  ```
- Or ensure your local Mongo service is running.


#### 2) Start the FastAPI backend (port 8100)
From the project root:
```bash
python -m venv .venv          # optional if you don’t already have one
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Recommended dev env flags (keep external sends OFF)
export SCHEDULER_ENABLED=true
export CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
export TWILIO_ENABLED=false
export SMTP_ENABLED=false
export S3_ENABLED=false
# Admin login defaults (change later for security)
export ADMIN_DEFAULT_USER=admin
export ADMIN_DEFAULT_PASS=admin123

uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
```
Verify backend:
- Health: http://127.0.0.1:8100/health → `{ "status": "ok" }`
- Swagger: http://127.0.0.1:8100/docs


#### 3) Start the Admin UI (Vite dev server on port 5173)
Open a new terminal in the project root and run:
```bash
cd admin_ui
# Make sure the API base points at your backend
# admin_ui/.env.development already contains:
# VITE_API_BASE=http://127.0.0.1:8100/v1

npm install
npm run dev
```
Open the UI at:
- http://localhost:5173/

Login with the dev credentials:
- Username: `admin`
- Password: `admin123`

If you haven’t created tenants yet, go to Settings or use the existing seeded/demo tenants if present (e.g., `demo-salon`, `demo-clinic`).


### What you can do in the UI (Milestone 1)
- Settings: edit owner email/phone, timezone (IANA like `Asia/Kolkata`), and delivery preferences.
- Customers: list/search, add/update, CSV import.
- Promotions: create and send (runs in NO‑OP mode unless you enable Twilio/SMTP), see realtime progress and logs.
- Appointments: list/create/cancel.
- Follow‑ups: view scheduled, cancel; realtime updates.
- Reports: generate daily report and open link (file:// in dev, S3 presigned if enabled).
- Retention: view summary and segment lists; kick off a promotion for a segment.


### Production build (optional)
Create a static build and preview it locally:
```bash
cd admin_ui
npm run build
npm run preview   # serves the built app at http://localhost:5174
```
Deploy the `admin_ui/dist/` directory behind any static server (e.g., Nginx). Ensure `VITE_API_BASE` at build time points to your backend URL.


### Environment and config you might tweak
Backend (env vars) — set before starting `uvicorn`:
- `CORS_ORIGINS` → `http://127.0.0.1:5173,http://localhost:5173`
- `ADMIN_DEFAULT_USER`, `ADMIN_DEFAULT_PASS`
- `JWT_SECRET` (for signing tokens)
- `MONGO_URI` (default is fine for local)
- `SCHEDULER_ENABLED=true`
- External sends (keep false in dev): `TWILIO_ENABLED=false`, `SMTP_ENABLED=false`, `S3_ENABLED=false`

Frontend (admin_ui/.env.development):
- `VITE_API_BASE=http://127.0.0.1:8100/v1`


### Troubleshooting
- UI can’t login (401):
  - Ensure backend is running and `CORS_ORIGINS` includes your UI origin.
  - Check credentials (`ADMIN_DEFAULT_USER/PASS`).
- CORS error in browser console:
  - Confirm `CORS_ORIGINS` includes `http://localhost:5173` and restart backend.
- Port already in use:
  - Change UI (`vite.config.ts` → dev server port) or backend (`--port 8101`) and update `VITE_API_BASE` accordingly.
- Mongo connection error:
  - Ensure Mongo is running and `MONGO_URI` is correct.
- WebSocket not updating:
  - UI connects to `ws://127.0.0.1:8100/ws/{tenant}`. Make sure your selected tenant exists and backend is running.


### One‑liner recap
- Backend: `uvicorn ai_scheduler.main:create_app --factory --reload --port 8100`
- Frontend: `cd admin_ui && npm i && npm run dev` → http://localhost:5173 → login `admin/admin123`.

If you want a Docker setup (Mongo + backend + Admin UI) or a ready `Postman`/`REST Client` collection, say the word and I’ll include it.