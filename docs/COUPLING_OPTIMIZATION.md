# Coupling & Optimization Report (app + admin_ui)

This document describes the **decoupling and optimization** work done in the **app** (backend) and **admin_ui** (frontend) to reduce tight coupling and centralize configuration.

---

## 1. Backend (app folder)

### 1.1 Self-contained package (app_ref → app)

- **Issue:** Many services and repositories under `app/` were importing from `app_ref` (e.g. `app_ref.services.db`, `app_ref.repositories.base_repository`), making the app folder depend on an external package and increasing coupling.
- **Change:** All such imports were replaced with **`app.`** so that the app folder is self-contained:
  - `app_ref.services.db` → `app.services.db`
  - `app_ref.repositories.*` → `app.repositories.*`
  - `app_ref.models.*` → `app.models.*`
  - `app_ref.utils.*` → `app.utils.*`
  - `app_ref.modules.*` → `app.modules.*`
  - Same for `app_ref.services.core.*`, `app_ref.services.salon.*`, `app_ref.services.store.*`, `app_ref.services.whatsapp.*`, `app_ref.services.ai.*`, `app_ref.services.workflow.*`, `app_ref.core.*`.
- **Scope:** All Python files under `app/` that referenced `app_ref` were updated (single bulk replace). Logic and behavior are unchanged.

### 1.2 Container and DB wiring

- **`app/core/container.py`**
  - Now imports **`app.services.core.tenant_service.TenantService`** and **`app.services.core.user_service.UserService`** (no longer `app_ref`).
  - **`get_db()`** now uses **`app.services.db.get_db`** (single place for DB wiring).
  - Services that need tenant/user or DB should use `get_tenant_service()`, `get_user_service()`, or `get_db()` from the container instead of importing service classes directly where testability is needed.

- **`app/repositories/base_repository.py`**
  - Now uses **`app.services.db.get_db`** instead of `app_ref.services.db`.

### 1.3 Store facade

- **`app/services/store/facade.py`**
  - All store service and helper imports now use **`app.services.store.*`** (no `app_ref`). Use **`get_store_facade()`** in routers or other services instead of importing CartService, ProductService, etc. directly when you need multiple store dependencies.

### 1.4 Realtime notifier (services ↔ routers decoupling)

- **Issue:** Several services were importing **`from app.routers.ws import notifier`** to broadcast WebSocket events, creating a dependency from the service layer to the router layer (tight coupling and against a clean layering).
- **Change:**
  - **`app/core/realtime.py`** was added:
    - Defines a **`Notifier`** class (same interface as before: `connect`, `disconnect`, `broadcast`).
    - Exposes **`get_notifier()`** (singleton) and **`set_notifier()`** (for tests).
  - **`app/routers/ws.py`** now uses **`from app.core.realtime import get_notifier`** and exposes `notifier = get_notifier()` so existing router code (e.g. `app/routers/appointments.py`, `app/routers/integrations.py`) that imports `notifier` from `ws` still works.
  - All **services** that previously imported `notifier` from `app.routers.ws` (or relative `...routers.ws` / `..routers.ws`) now use **`from app.core.realtime import get_notifier`** and call **`await get_notifier().broadcast(...)`**:
    - `app/services/salon/appointments/appointment_creator.py`
    - `app/services/salon/appointments/appointment_canceler.py`
    - `app/services/salon/appointments/appointment_rescheduler.py`
    - `app/services/salon/appointments/helpers/ws_utils.py`
    - `app/services/core/promotions/helpers/ws_utils.py`
    - `app/services/core/followups_service.py`
    - `app/services/promotions.py`
    - `app/services/followups.py`

Services no longer depend on the routers package; they depend only on `app.core.realtime`.

---

## 2. Frontend (admin_ui)

### 2.1 Central API config

- **Issue:** Base URL and upload URL logic were duplicated (e.g. `(import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/v1')` and `base.replace(/\/v1$/, '')` in several places), and some pages inlined the same upload-URL resolution.
- **Change:**
  - **`admin_ui/src/api/config.ts`** was added:
    - **`getApiBaseURL()`** – returns the API base URL (with `/v1`), used by axios and report/download links.
    - **`getUploadBaseURL()`** – returns base without `/v1` (e.g. for WebSocket or upload origin).
    - **`resolveUploadUrl(pathOrUrl)`** – resolves paths like `/v1/uploads/...` to the correct full URL (using upload base).
  - **`admin_ui/src/api/axios.ts`** now uses **`getApiBaseURL()`** from config instead of inlining env/default.
  - **`admin_ui/src/api/reports.ts`** uses **`getApiBaseURL()`** for **`reportDownloadUrl()`** instead of `api.defaults.baseURL`.

### 2.2 Shared upload URL resolution

- **Issue:** Promotions **Detail**, **New**, and **Simulator** each had the same `getFullUrl` logic (check for `http`, then `/v1/uploads`, then build URL with env base).
- **Change:** All three pages now use **`resolveUploadUrl`** from **`@api/config`**:
  - **`pages/Promotions/Detail.tsx`** – `getFullUrl = (url) => resolveUploadUrl(url)` and import `resolveUploadUrl` from `@api/config`.
  - **`pages/Promotions/New.tsx`** – same.
  - **`pages/Promotions/Simulator.tsx`** – same.

### 2.3 WebSocket and WhatsApp config URL

- **`admin_ui/src/hooks/useWebSocket.ts`** now uses **`getUploadBaseURL()`** from **`@api/config`** for building the WebSocket URL instead of inlining env and default port.
- **`admin_ui/src/pages/WhatsApp/Config.tsx`** – webhook URL is now built with **`getApiBaseURL()`** from **`@api/config`** instead of `api.defaults?.baseURL`.

---

## 3. File-level summary

### Backend (app) – new

- `app/core/realtime.py` – Notifier + get_notifier() / set_notifier().

### Backend (app) – modified

- `app/core/container.py` – app.services.* and app.services.db.
- `app/repositories/base_repository.py` – app.services.db.
- `app/services/store/facade.py` – app.services.store.*.
- `app/routers/ws.py` – use get_notifier() from app.core.realtime.
- All Python files under `app/` that contained `app_ref` – replaced with `app` (bulk).
- Services that imported notifier from routers.ws – switched to app.core.realtime get_notifier().

### Frontend (admin_ui) – new

- `admin_ui/src/api/config.ts` – getApiBaseURL, getUploadBaseURL, resolveUploadUrl.

### Frontend (admin_ui) – modified

- `admin_ui/src/api/axios.ts` – baseURL from getApiBaseURL().
- `admin_ui/src/api/reports.ts` – getApiBaseURL() for reportDownloadUrl.
- `admin_ui/src/hooks/useWebSocket.ts` – getUploadBaseURL() for WS URL.
- `admin_ui/src/pages/Promotions/Detail.tsx` – resolveUploadUrl from config.
- `admin_ui/src/pages/Promotions/New.tsx` – resolveUploadUrl from config.
- `admin_ui/src/pages/Promotions/Simulator.tsx` – resolveUploadUrl from config.
- `admin_ui/src/pages/WhatsApp/Config.tsx` – getApiBaseURL() for webhook URL.

---

## 4. What to do next (optional)

- **Backend:** Prefer **container** (`get_tenant_service`, `get_user_service`, `get_db`) and **facades** (e.g. `get_store_facade()`) in new code instead of direct service/repo imports where it improves testability and reduces coupling.
- **Backend:** One remaining cross-layer dependency is **`app.services.whatsapp.helpers.slot_helper`** (or similar) importing from **`app.routers.slots`** (e.g. `get_availability`). This can be refactored later by moving the slot-availability logic into a service and having both the router and the WhatsApp helper call that service.
- **Frontend:** Use **`getApiBaseURL()`**, **`getUploadBaseURL()`**, and **`resolveUploadUrl()`** from **`@api/config`** anywhere you need base or upload URLs; avoid repeating env checks and string logic.

All behavior and use cases are preserved; only wiring and duplication were optimized.
