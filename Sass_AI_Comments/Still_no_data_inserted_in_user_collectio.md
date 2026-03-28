### Why you still don’t see a user in Mongo
From your repo, users are inserted in two supported ways:
- Startup bootstrap (preferred): on API start, if no super_admin exists and env vars are set, it inserts one.
- Seeding script: `scripts/seed_super_admin.py` inserts directly into Mongo.

Based on your earlier logs, both paths likely failed due to environment mismatches:
- The seeding script was run with the wrong Python (no `pymongo` installed), so it crashed.
- The API probably started without `BOOT_SUPER_ADMIN_EMAIL/PASSWORD` set, so it skipped bootstrapping.
- Or the script/API wrote to a different database than the one you are checking (DB name in `MONGO_URI` vs default fallback `ai_appo`).

Below are precise, copy‑pasteable steps to get a user inserted and verified.

---

### Option A (recommended): bootstrap on API startup (idempotent)
1) Set env and start API on your usual port (e.g., 8100):
```
# In your project root
export JWT_SECRET="change-me"
export BOOT_SUPER_ADMIN_EMAIL="super@example.com"
export BOOT_SUPER_ADMIN_PASSWORD="Super#12345"
# If your Mongo is not the default, also export the URI used by the app
# export MONGO_URI="mongodb://localhost:27017/ai_appo"

uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
```
You should see a log like:
```
Bootstrapped super_admin user: super@example.com
```

2) Verify you can log in:
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"super@example.com","password":"Super#12345"}'
```
If successful, you’ll get `{ access_token, user: { role: "super_admin" } }`.

Note: The bootstrap runs only when there is no super_admin in the `users` collection. It’s safe to rerun — it will log a warning if the envs are missing or a user already exists.

---

### Option B: seed via the script using the project venv (idempotent)
Your earlier run failed because you used the system Python (no `pymongo`). Use the project venv’s Python:
```
cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject

# Ensure the venv interpreter is used (it has pymongo from requirements.txt)
./saas_venv/bin/python scripts/seed_super_admin.py \
  --email super@example.com \
  --password Super#12345 \
  --display-name "Super Admin"
```
If your Mongo URI is not set in `settings.py`, export it first:
```
export MONGO_URI="mongodb://localhost:27017/ai_appo"
```
You should see either:
- `CREATED super_admin: super@example.com`, or
- `User already exists: super@example.com` (idempotent safeguard)

Then test login as in Option A.

---

### Option C: one‑liner using your project venv (quick dev path)
Run a one‑liner that calls the app storage helper directly (again use the venv Python):
```
./saas_venv/bin/python - <<'PY'
from app.services.storage_mongo import Storage
u = Storage.get_user_by_email('super@example.com')
if not u:
    Storage.create_user(email='super@example.com', password='Super#12345', role='super_admin', tenant=None, display_name='Super Admin')
    print('CREATED super@example.com')
else:
    print('EXISTS', u.get('email'))
PY
```
Then test login.

---

### Make sure the script/API and your checks point to the SAME database
- Where the app points: `settings.py` uses `MONGO_URI`; if that URI doesn’t include a DB name, the app falls back to DB name `ai_appo` (see `app/services/db.py`).
- The seeding script also tries `settings.MONGO_URI` first; if missing, it uses `MONGO_URI` env and falls back to `ai_appo`.
- If you’re inspecting Mongo with a tool, make sure you’re opening the same database (`ai_appo` by default) and looking for the `users` collection there.

Quick Python check (using your venv) to list DB and count users:
```
./saas_venv/bin/python - <<'PY'
import os
from pymongo import MongoClient
uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/ai_appo')
client = MongoClient(uri, serverSelectionTimeoutMS=3000)
client.admin.command('ping')
db = client.get_default_database() or client.get_database('ai_appo')
print('DB =', db.name)
print('collections =', db.list_collection_names())
print('users count =', db.get_collection('users').count_documents({}))
PY
```
If `users count` is 0 after seeding, the URI or DB name is not aligned — fix `MONGO_URI` so both the app and the seeding method use the same DB.

---

### Common pitfalls and fixes
- “No module named pymongo” when running the seed script: you used system Python. Use the project venv: `./saas_venv/bin/python scripts/seed_super_admin.py`.
- API starts but no bootstrap user: you didn’t export `BOOT_SUPER_ADMIN_EMAIL/PASSWORD` before starting, or there is already a super_admin in the collection (bootstrap is skipped by design).
- Seeded but login 401: make sure `JWT_SECRET` is set consistently (the API verifies tokens using this secret). The login endpoint does not depend on `JWT_SECRET`, but any tokens you mint manually must use the same secret.
- Wrong database: `MONGO_URI` lacks a DB name and your seed ran pointing at a different DB than your check; set `MONGO_URI` explicitly with the DB name (e.g., `mongodb://localhost:27017/ai_appo`) and re‑run.

---

### Minimal, do‑this‑now recipe (macOS/Linux zsh)
```
cd /Users/rahmath.shihabudeen/PycharmProjects/SaasProject
export MONGO_URI="mongodb://localhost:27017/ai_appo"
export JWT_SECRET="change-me"
export BOOT_SUPER_ADMIN_EMAIL="super@example.com"
export BOOT_SUPER_ADMIN_PASSWORD="Super#12345"
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100 --reload
```
Watch for the “Bootstrapped super_admin” log, then:
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"super@example.com","password":"Super#12345"}'
```
If that still fails, run the venv seeding script:
```
./saas_venv/bin/python scripts/seed_super_admin.py --email super@example.com --password Super#12345
```
…and re‑try the login.

---

If you’d like, tell me:
- what `MONGO_URI` you’re using right now, and
- whether you prefer the startup bootstrap or the script method,

and I’ll give you the exact commands tailored to your environment (including Windows PowerShell versions if needed).