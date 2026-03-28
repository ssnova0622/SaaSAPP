# old_app Architecture & Decoupling Guide

## Service container (app/core/container.py)

All core service access should go through the container so that:

- **Single place to wire dependencies** – change implementations in one file.
- **Testability** – override with mocks via `set_tenant_service_override()`, `set_user_service_override()`, then `clear_overrides()` in teardown.

**Use in routers and new code:**

```python
from app.core.container import get_tenant_service, get_user_service, get_db

tenant_svc = get_tenant_service()
settings = tenant_svc.get_tenant_settings(tenant)
```

**Do not** import `TenantService` or `UserService` directly in new code unless you have a good reason (e.g. the service module itself).

## Routers (deps.py)

`app/routers/deps.py` uses `get_tenant_service()` from the container for:

- `ensure_tenant_active`
- `ensure_module_enabled`
- `ensure_capability_enabled`

So auth and tenant checks are wired through the container.

## Interfaces (app/core/interfaces.py)

Protocols define the contracts:

- `ITenantSettingsProvider` – `get_tenant_settings(tenant)`
- `ITenantProvider` – `get_tenant(tenant)`, `tenant_exists(tenant)`

Use these types for function parameters when you want to accept any implementation (e.g. in tests).

## Store facade (app/services/store/facade.py)

Store-related services are grouped behind a single entry point:

```python
from app.services.store.facade import get_store_facade

facade = get_store_facade()
facade.cart.get_cart(tenant, phone)
facade.products.get_product(tenant, sku)
facade.price_helper.compute_totals(...)
```

Use `get_store_facade()` when you need multiple store services instead of importing CartService, ProductService, etc. separately. Existing code can keep direct imports; new code should prefer the facade.

## WhatsApp helpers and optional injection

Helpers that need tenant settings can accept an optional provider so callers can inject (e.g. from container or a test double):

- **phone_helper.standardize_phone(tenant, phone, get_tenant_country_code=...)**  
  If omitted, uses `get_tenant_service()._get_tenant_country_code(tenant)`.

- **date_helper.get_tenant_tz(tenant, get_tenant_settings=...)**  
- **date_helper.format_tenant_date(tenant, date, get_tenant_settings=...)**  
  If omitted, use container’s tenant service.

This keeps backward compatibility (no args = use container) while allowing tests to pass custom providers.

## Dependency flow (target state)

1. **Routers** → use `deps.py` and `get_*` from `app.core.container`.
2. **Services** → get other services via container or facade where possible; avoid deep service→service imports.
3. **Helpers** → accept optional callables for tenant/settings when they need tenant data; default to container.
4. **Repositories** → stay as-is; services and facades use repositories, not the other way around.

## What not to do

- Do not add new module-level `from app.services.X import Y` in a service when you could get Y from the container or a facade.
- Do not import routers inside services (e.g. `from app.routers.ws import notifier`); use events or a small notification interface if needed.
- Do not put business logic in routers; keep it in services and call services from routers.

## Files touched in this refactor

- **app/core/container.py** – new; lazy getters for tenant, user, db.
- **app/core/interfaces.py** – new; protocols for tenant providers.
- **app/routers/deps.py** – uses `get_tenant_service()` instead of direct TenantService import.
- **app/services/store/facade.py** – new; StoreFacade + get_store_facade().
- **app/services/whatsapp/helpers/phone_helper.py** – optional get_tenant_country_code for DI.
- **app/services/whatsapp/helpers/date_helper.py** – optional get_tenant_settings for DI.

All existing behavior is preserved; only wiring and optional parameters were added.
