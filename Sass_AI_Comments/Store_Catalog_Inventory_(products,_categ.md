### Progress: Store Catalog/Inventory — API done, UI client done; proceeding with UI pages
I’ve completed the backend and initial client pieces for the Store Catalog/Inventory feature and wired them into your app. Next I will add the Admin UI pages for Categories and Products (with inventory editing) and wire navigation/routes.

### What’s implemented now
- Backend data storage and indexes (Mongo)
  - Collections and indexes added for `products`, `categories`, and `inventory` in `app/services/db.py`.
- Backend schemas
  - `CategoryIn/CategoryOut`, `ProductIn/ProductOut`, and `InventoryUpsert` added in `app/models/schemas.py`.
- Backend storage methods
  - Categories: list/upsert/delete
  - Products: list with filters (search/category/active), upsert, delete
  - Inventory: get/set available quantity by SKU
- Backend routes (FastAPI) in `app/routers/catalog.py`
  - Categories
    - `GET /v1/tenants/{tenant}/catalog/categories`
    - `POST /v1/tenants/{tenant}/catalog/categories` (create/update)
    - `PATCH /v1/tenants/{tenant}/catalog/categories/{name}` (toggle active)
    - `DELETE /v1/tenants/{tenant}/catalog/categories/{name}`
  - Products
    - `GET /v1/tenants/{tenant}/catalog/products?search=&category=&active=&page=&size=`
    - `POST /v1/tenants/{tenant}/catalog/products` (create/update)
    - `PUT /v1/tenants/{tenant}/catalog/products/{sku}` (update)
    - `DELETE /v1/tenants/{tenant}/catalog/products/{sku}`
  - Inventory
    - `GET /v1/tenants/{tenant}/inventory/{sku}`
    - `PUT /v1/tenants/{tenant}/inventory/{sku}` (set available_qty)
  - Security
    - All endpoints are tenant-scoped (`ensure_tenant_scope` + `ensure_tenant_active`).
    - Module/capability enforcement: require `store` module and `store.catalog` capability.
- Router inclusion
  - `app/main.py` includes the new Catalog router under tag “Store Catalog”.
- Admin UI API client
  - `admin_ui/src/api/catalog.ts` with functions for categories, products, and inventory.

### How to test API now (curl)
- Create a category:
```
curl -X POST 'http://127.0.0.1:8100/v1/tenants/ss-salon/c....