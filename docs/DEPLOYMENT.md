# Deployment

## Run with Docker (API + MongoDB)

From the project root:

```bash
# Build and start API + MongoDB
docker compose up --build

# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# MongoDB: localhost:27017 (only from host; API uses internal hostname `mongo`)
```

Optional env (create `.env` or set in shell):

- `JWT_SECRET` – set in production.
- `CORS_ORIGINS` – comma-separated origins for the admin UI (default includes localhost:5173, 5174).
- `SCHEDULER_ENABLED` – `true` (default) to run cron/promotions/followups/reports jobs.
- `REDIS_URI` – if set, tenant settings are cached in Redis (5 min TTL). Omit for no cache.

## Run API locally (no Docker)

1. Install Python 3.10+ and MongoDB (or use a remote `MONGO_URI`).
2. Create a venv, install deps, set env:

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   cp .env.example .env       # edit .env with MONGO_URI, JWT_SECRET, etc.
   ```

3. Run (use one of these so **code changes apply without restarting**):

   ```bash
   # Option A: run script (recommended — reload on by default)
   python run_api.py

   # Option B: run app module
   python -m app.main

   # Option C: uvicorn with --reload (required for live reload)
   uvicorn app.main:create_app --factory --reload --port 8000
   ```

   **Why do I need to restart the server for Python changes to apply?**  
   You're likely running uvicorn **without** `--reload`. Without it, uvicorn does not watch files and will not restart on code changes. Use one of the commands above (they all enable reload by default), or add `--reload` to your uvicorn command. For production, set `RELOAD=false` or run without `--reload`.

   **PyCharm / IDE:** To get auto-reload, run the script `run_api.py` (right‑click → Run), or run module `app.main` (`python -m app.main`). If you use an "Uvicorn" or custom run configuration, add the parameter `--reload` to the run options.

4. Optional: bootstrap super admin (if no super_admin user exists):

   Set `BOOT_SUPER_ADMIN_EMAIL` and `BOOT_SUPER_ADMIN_PASSWORD` in `.env`; the app creates the user on startup.

## Admin UI

Run separately (e.g. for local dev):

```bash
cd admin_ui
npm install
echo "VITE_API_BASE=http://localhost:8000/v1" > .env.development
npm run dev
```

Open the URL shown (e.g. http://localhost:5173). For Docker API, use `VITE_API_BASE=http://localhost:8000/v1` so the UI talks to the API.

Production: build with `npm run build` and serve the `dist/` folder (e.g. nginx, or same host as API with static files).

---

## Production checklist

Before going live, ensure:

- **Secrets**
  - Set a strong, random `JWT_SECRET` (e.g. 32+ bytes). Never commit it or use the default.
  - Use a secure `MONGO_URI` (auth, network restriction). Prefer TLS to MongoDB in production.
  - If using Twilio/WhatsApp or payment providers, store API keys in env (e.g. `TWILIO_*`) or a secrets manager; do not hardcode.

- **Redis (optional but recommended)**
  - Set `REDIS_URI` for caching tenant settings, list_tenants, and user-by-id. Cache TTLs and invalidation are handled in code (e.g. tenant create/delete invalidates list_tenants; user update invalidates user cache). If unset, caching is no-op.

- **TLS / reverse proxy**
  - Serve the API behind HTTPS (e.g. nginx, Caddy, or cloud LB). Terminate TLS at the proxy; do not expose the API directly on the public internet without TLS.
  - Set `CORS_ORIGINS` to the exact admin UI and allowed origins (no wildcards in production).

- **Limits and safety**
  - Apply rate limiting and/or request size limits at the proxy or via middleware to protect against abuse.
  - Ensure debug mode is off (e.g. no `--reload`, no `DEBUG=true`). Do not expose stack traces to clients in production.

- **Environment**
  - Use env-based config only (`.env` or platform env vars). Keep `.env` out of version control and deploy secrets via your platform’s secret store.
  - For scheduler (cron, promotions, followups, reports), set `SCHEDULER_ENABLED=true` only on one instance to avoid duplicate jobs.
