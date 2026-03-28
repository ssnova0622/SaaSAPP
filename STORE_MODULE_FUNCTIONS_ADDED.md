# Store Module – Functions & Features Added

This document lists all functions and scenarios implemented for the Store module (order status, view offers, view products) and related customer-facing flows.

---

## 1. Order status (track ID)

### Backend

| Location | Function / Endpoint | Description |
|----------|---------------------|-------------|
| `app/routers/store.py` | `get_order_status_public(tenant, order_id)` | **GET** `/v1/tenants/{tenant}/orders/track/{order_id}` – Public (no auth). Returns `order_id`, `status`, `created_at`, `fulfillment_mode`. 404 if order not found. |

### WhatsApp

| Location | Change | Description |
|----------|--------|-------------|
| `app/routers/whatsapp/routes.py` | `store.track_order` | When `order_id` is missing: reply “Please share your Order ID (e.g. ORD-XXXX) to check status.” When order not found: “Order {id} not found. Please check the ID and try again.” (no longer “In transit”). |

### Scenarios covered

- Customer sends order/track id → get real status from DB.
- Customer says “track” without id → prompt for Order ID.
- Invalid or unknown id → clear “not found” message.

---

## 2. View offers (tenant-created, time-bound)

### Backend – Offers service

| Location | Function | Description |
|----------|----------|-------------|
| `app/services/store/offers_service.py` | `OffersService.list_offers(tenant, active_only, page, size)` | List offers; optional filter by currently valid (valid_from ≤ now ≤ valid_until). |
| `app/services/store/offers_service.py` | `OffersService.list_active_offers(tenant)` | List of offers valid now (for customers). |
| `app/services/store/offers_service.py` | `OffersService.get_offer(tenant, offer_id)` | Get one offer by id. |
| `app/services/store/offers_service.py` | `OffersService.create_offer(...)` | Create offer (title, description, valid_from, valid_until, product_skus, discount_info, active). |
| `app/services/store/offers_service.py` | `OffersService.update_offer(tenant, offer_id, updates, user_id)` | Update offer. |
| `app/services/store/offers_service.py` | `OffersService.delete_offer(tenant, offer_id)` | Delete offer. |

### Backend – Store facade

| Location | Change | Description |
|----------|--------|-------------|
| `app/services/store/facade.py` | `StoreFacade.offers` | Exposes `OffersService` as `get_store_facade().offers`. |

### Backend – API routes

| Location | Endpoint | Auth | Description |
|----------|----------|------|-------------|
| `app/routers/store.py` | **GET** `/v1/tenants/{tenant}/offers/active` | No | List active offers (customer-facing). |
| `app/routers/store.py` | **GET** `/v1/tenants/{tenant}/offers` | Yes | List all offers (optional `active_only`, pagination). |
| `app/routers/store.py` | **POST** `/v1/tenants/{tenant}/offers` | Yes | Create offer (body: title, description, valid_from, valid_until, product_skus, discount_info, active). |
| `app/routers/store.py` | **GET** `/v1/tenants/{tenant}/offers/{offer_id}` | Yes | Get one offer. |
| `app/routers/store.py` | **PATCH** `/v1/tenants/{tenant}/offers/{offer_id}` | Yes | Update offer. |
| `app/routers/store.py` | **DELETE** `/v1/tenants/{tenant}/offers/{offer_id}` | Yes | Delete offer. |

### Backend – DB

| Location | Change | Description |
|----------|--------|-------------|
| `app/services/db.py` | Collection `store_offers` | Indexes: `(tenant, id)` unique, `(tenant, valid_from, valid_until)`, `(tenant, active)`. |

### WhatsApp

| Location | Change | Description |
|----------|--------|-------------|
| `app/routers/whatsapp/routes.py` | `core.show_offers` | Uses **tenant-created active offers** first (`get_store_facade().offers.list_active_offers(tenant)`). If none, falls back to catalog search for “offer”. |

### Scenarios covered

- Tenant creates offers with validity window → customers see only current offers.
- “View offers” in WhatsApp shows tenant’s active offers first, then catalog-based offers.

---

## 3. View products

### Backend – Public API

| Location | Function / Endpoint | Description |
|----------|---------------------|-------------|
| `app/routers/store.py` | `list_products_public(tenant, search, category, page, size)` | **GET** `/v1/tenants/{tenant}/products/public` – Public (no auth). Returns active products (optional search, category, pagination). |

### WhatsApp

| Location | Action | Description |
|----------|--------|-------------|
| `app/routers/whatsapp/routes.py` | `store.browse_catalog` | Calls `get_store_facade().products.list_products(tenant, active=True, page=1, size=15)` and formats as “Our Products: 1) Name - ₹price …”. Replaces previous hardcoded reply. |
| `app/routers/whatsapp/routes.py` | `store.check_product` | Uses `params.query` or `params.search`; calls `list_products(tenant, search=query, active=True, size=10)` and returns “Found N product(s): …”. If no query: “What product are you looking for? …”. |
| `app/routers/whatsapp/routes.py` | `store.check_price` | Same implementation as `store.check_product` (search products and show name + price). |

### Scenarios covered

- “View products” / “Browse catalog” → real product list from catalog.
- “Search product” / “Check price” with keyword → search by name/SKU and show prices.
- No keyword → prompt for product name or keyword.

---

## 4. Helper / shared

| Location | Function | Description |
|----------|----------|-------------|
| `app/routers/store.py` | `_parse_dt(s)` | Parses ISO datetime string for offer `valid_from` / `valid_until`. |

---

## Summary table

| Area | What was added |
|------|----------------|
| **Order status** | Public GET order status by track id; WhatsApp track_order fixed (prompt + not found message). |
| **Offers** | New `OffersService` + `store_offers` collection; CRUD APIs; public GET active offers; WhatsApp show_offers uses active offers first. |
| **View products** | Public GET products; WhatsApp browse_catalog and check_product/check_price use real catalog. |

All new store-related APIs and WhatsApp actions are covered above. For integration (e.g. Postman or admin UI), use the routes in `app/routers/store.py` and the WhatsApp action IDs: `store.track_order`, `store.browse_catalog`, `store.check_product`, `store.check_price`, `core.show_offers`.
