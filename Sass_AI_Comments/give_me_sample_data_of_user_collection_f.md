### Sample document for `users` collection (Super Admin)
Below is a ready-to-insert MongoDB document shape for a Super Admin. You’ll need a valid `password_hash`. Paste the document into the correct database (default is `ai_appo` unless your `MONGO_URI` specifies another DB).

Suggested fields in `users` collection:
- `email`: string (unique)
- `password_hash`: string (bcrypt preferred; fallback format supported: `sha256$<salt_hex>$<digest>`)
- `role`: `super_admin | tenant_admin | staff`
- `tenant`: string or `null` (must be `null` for super_admin)
- `display_name`: string
- `caps`: string[] (capabilities; super_admin doesn’t need any)
- `status`: `active | disabled`
- `created_at`, `updated_at`: datetimes

---

### 1) Insert template (mongosh)
Replace `PASTE_HASH_HERE` with a generated hash (see next section). Use your actual DB name if not `ai_appo`.
```
use ai_appo

db.users.insertOne({
  email: "super@example.com",
  password_hash: "PASTE_HASH_HERE",  // bcrypt OR sha256$salt$digest
  role: "super_admin",
  tenant: null,
  display_name: "Super Admin",
  caps: [],
  status: "active",
  created_at: ISODate(),
  updated_at: ISODate()
})
```

---

### 2) Generate a valid password hash to paste
Pick ONE of the two options below and paste the output string as `password_hash`:

A) Generate a bcrypt hash for password `Super#12345` (recommended)
```
# From project root, use the project venv python so bcrypt is available
./saas_venv/bin/python - <<'PY'
import bcrypt
print(bcrypt.hashpw(b"Super#12345", bcrypt.gensalt(12)).decode("utf-8"))
PY
```
Output looks like: `"$2b$12$...long-string..."`

B) Generate a salted sha256 fallback hash for password `Super#12345` (also supported by your code)
```
./saas_venv/bin/python - <<'PY'
import os, hashlib
salt = os.urandom(16)
pw = b"Super#12345"
digest = hashlib.sha256(salt + pw).hexdigest()
print(f"sha256${salt.hex()}${digest}")
PY
```
Output looks like: `"sha256$<32-hex-salt>$<64-hex-digest>"`

Paste the output string into `password_hash` in the insert document.

---

### 3) Verify login (after insert)
Start your API, then call login:
```
curl -s -X POST http://127.0.0.1:8100/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"super@example.com","password":"Super#12345"}'
```
Expected: JSON with `access_token` and `user.role == "super_admin"`.

---

### 4) Optional sample docs for other roles (if you need them later)
Tenant Admin (manages one tenant, full access within tenant capabilities):
```
db.users.insertOne({
  email: "owner@ss-salon.com",
  password_hash: "PASTE_HASH_HERE",
  role: "tenant_admin",
  tenant: "ss-salon",
  display_name: "Salon Owner",
  caps: [],  // tenant_admin does not need caps list; staff does
  status: "active",
  created_at: ISODate(),
  updated_at: ISODate()
})
```

Staff (restricted by caps and tenant capabilities):
```
db.users.insertOne({
  email: "staff1@ss-salon.com",
  password_hash: "PASTE_HASH_HERE",
  role: "staff",
  tenant: "ss-salon",
  display_name: "Front Desk",
  caps: ["salon.appointments"],  // example: allow appointments page only
  status: "active",
  created_at: ISODate(),
  updated_at: ISODate()
})
```

Note: For `staff`, the effective permission is intersection of user `caps` and the tenant’s enabled capabilities. Super Admin can toggle tenant capabilities in Settings → Modules.

---

### 5) Ensure you’re inserting into the right DB
- If your `MONGO_URI` doesn’t include a DB name, the app defaults to `ai_appo` (see `app/services/db.py`).
- Use `use ai_appo` in `mongosh` before `insertOne` if that’s your default.

If you’d like, share your exact `MONGO_URI`, and I’ll confirm the DB name and give you an exact `insertOne` line ready to paste with a generated hash.