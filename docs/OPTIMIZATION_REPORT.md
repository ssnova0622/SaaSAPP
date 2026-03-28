# Optimization Report: Frontend (admin_ui) & Backend (old_app)

This document summarizes the optimizations applied to reduce coupling and make the codebase easier to handle.

---

## 1. old_app (Backend) Optimizations

### 1.1 Service container (`app/core/container.py`)

- **Purpose:** Single place to obtain core services (tenant, user, db). Reduces direct imports of `TenantService` / `UserService` across the codebase.
- **Usage:**
  ```python
  from app.core.container import get_tenant_service, get_user_service
  tenant_svc = get_tenant_service()
  settings = tenant_svc.get_tenant_settings(tenant)
  ```
- **Testability:** In tests, call `set_tenant_service_override(mock_svc)` and `clear_overrides()` in teardown to inject mocks.

### 1.2 Interfaces (`app/core/interfaces.py`)

- **Purpose:** Protocol definitions (`ITenantSettingsProvider`, `ITenantProvider`) for dependency injection and clearer contracts.
- Use these types as parameter types when a function accepts “any tenant provider” so implementations can be swapped (e.g. in tests).

### 1.3 Router deps use container

- **File:** `app/routers/deps.py`
- **Change:** All tenant checks now use `get_tenant_service()` from the container instead of importing `TenantService` directly.
- **Functions updated:** `ensure_tenant_active`, `ensure_module_enabled`, `ensure_capability_enabled`.

### 1.4 Store facade (`app/services/store/facade.py`)

- **Purpose:** Single entry point for store-related services: cart, products, inventory, categories, orders, price_helper, unit_conversion.
- **Usage:**
  ```python
  from app.services.store.facade import get_store_facade
  facade = get_store_facade()
  facade.cart.get_cart(tenant, phone)
  facade.products.get_product(tenant, sku)
  ```
- New code that needs multiple store services should prefer the facade over importing each service separately.

### 1.5 WhatsApp helpers – optional dependency injection

- **phone_helper.standardize_phone(tenant, phone, get_tenant_country_code=...)**  
  If `get_tenant_country_code` is omitted, it uses the container’s tenant service. Callers can pass a custom callable for tests.

- **date_helper.get_tenant_tz(tenant, get_tenant_settings=...)**  
- **date_helper.format_tenant_date(tenant, date, get_tenant_settings=...)**  
  Same pattern: optional provider for tenant settings; default is container’s tenant service.

Behavior is unchanged when the new optional arguments are not passed.

### 1.6 Architecture guide

- **File:** `old_app/ARCHITECTURE.md`
- Describes the container, interfaces, store facade, and how to use them. Also documents dependency flow and what to avoid.

---

## 2. admin_ui (Frontend) Optimizations

### 2.1 Shared hooks

- **`hooks/useList.ts`**
  - Generic list-loading hook: `items`, `loading`, `error`, `refresh`.
  - Options: `fetch`, `enabled`, `deps` (e.g. `[tenant]` to refetch when tenant changes), `onError`.
  - Use for any page that loads a list from an API to avoid duplicated loading/error/refresh logic.

### 2.2 UI primitives (`components/ui/`)

- **PageHeader** – Title, optional subtitle, optional action buttons. Keeps page headers consistent.
- **DataCard** – Wrapper for content (slate border, rounded). Use for tables, forms, sections.
- **AppTable** – `AppTable`, `AppTableHead`, `AppTableBody`, `AppTableRow`, `AppTh`, `AppTd` with shared styling and support for `colSpan` etc.
- **AppButton** – Variants: `primary`, `secondary`, `danger`, `ghost`. Consistent button styling.
- **Alert** – Variants: `error`, `success`, `warning`, `info`. Consistent alert styling.

All under `@components/ui` (see `components/ui/index.ts`).

### 2.3 Constants

- **`constants/routes.ts`** – Centralized route paths (`ROUTES.HOME`, `ROUTES.PROMOTIONS_DETAIL(id)`, etc.). Use for `Link` and `navigate` instead of string literals.

### 2.4 Path alias

- **tsconfig:** `@constants/*` → `src/constants/*` (in addition to existing `@api`, `@components`, `@hooks`, `@pages`, `@utils`).

### 2.5 Example refactor: Promotions/Index

- Uses `useList` for loading the promotions list (with `deps: [tenant]`).
- Uses `PageHeader` for title and actions.
- Uses `DataCard`, `AppTable`, `AppTh`, `AppTd`, `AppTableRow` for the table.
- Uses `ROUTES.PROMOTIONS_*` for links.
- Logic (data shape, links, behavior) unchanged; only structure and shared pieces are used.

Other list pages (Customers, WhatsApp Menus, etc.) can be refactored the same way: `useList` + `PageHeader` + `DataCard` + `AppTable` + `ROUTES`.

---

## 3. Summary table

| Area | Change | Benefit |
|------|--------|--------|
| old_app | Service container | Single wiring point; test overrides |
| old_app | Router deps use container | Consistent tenant/auth access |
| old_app | Store facade | One entry point for store services |
| old_app | WhatsApp helpers optional DI | Testable without global tenant service |
| old_app | ARCHITECTURE.md | Clear rules for dependencies |
| admin_ui | useList hook | Less duplicated list-loading code |
| admin_ui | UI primitives (PageHeader, DataCard, AppTable, AppButton, Alert) | Consistent layout and styling |
| admin_ui | ROUTES constants | Safer navigation and refactors |
| admin_ui | Promotions/Index refactor | Example for other pages |

---

## 4. Suggested next steps

- **old_app:** Gradually switch other routers and services to use `get_tenant_service()` / `get_user_service()` from the container; use `get_store_facade()` where multiple store services are needed.
- **admin_ui:** Migrate other list pages to `useList` + UI primitives + `ROUTES` using Promotions/Index as the template.

All changes preserve existing behavior; they only improve structure and make the code easier to handle and test.
