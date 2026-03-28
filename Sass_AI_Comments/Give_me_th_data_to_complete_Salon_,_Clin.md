### What you’ll get here
Below is a ready-to-use set of seed data and exact API call sequences to “complete the workflow” for three verticals in your SaaS app using the existing endpoints and models:
- Store (retail products with inventory)
- Salon (services as catalog items; optional retail products)
- Clinic (services + medicines; inventory for medicines)

I’ve aligned all payloads to the existing APIs and types implemented in your repo:
- Categories/products: `app/routers/catalog.py` with `CategoryIn`, `ProductIn`
- Inventory: `GET/PUT /tenants/{tenant}/inventory/{sku}`
- Optional events/analytics: `POST /tenants/{tenant}/events` and AI endpoints under `app/routers/ai.py`

Where dedicated appointment/staff endpoints are absent, Salon and Clinic “services” are represented as catalog products with `unit: "service"`. This lets you complete an end‑to‑end workflow in the current system. If you later add appointment modules, you can migrate seamlessly.

---

### 1) Endpoints you’ll use
- Categories
  - `GET /tenants/{tenant}/catalog/categories`
  - `POST /tenants/{tenant}/catalog/categories` (body: `{ name, active }`)
  - `PATCH /tenants/{tenant}/catalog/categories/{name}` (body: `{ active }`)
  - `DELETE /tenants/{tenant}/catalog/categories/{name}`
- Products
  - `GET /tenants/{tenant}/catalog/products` (supports `search`, `category`, `active`, paging, and `flatten_variants`)
  - `POST /tenants/{tenant}/catalog/products` (body: `ProductIn`)
  - `PUT /tenants/{tenant}/catalog/products/{sku}`
  - `GET /tenants/{tenant}/catalog/products/by-sku/{sku}`
  - CSV import: `POST /tenants/{tenant}/catalog/import_products_csv` (CSV headers: `sku,name,category,price,mrp,tax,unit,active`)
- Inventory
  - `GET /tenants/{tenant}/inventory/{sku}`
  - `PUT /tenants/{tenant}/inventory/{sku}` (body: `{ sku, available_qty }`)
- Events (optional analytics, funnel tracking)
  - `POST /tenants/{tenant}/events` (body: `{ type: string, ts?: number, data?: object }`)

Note: Category/product routes require the `store` module and `store.catalog` capability (already wired via dependencies).

---

### 2) Categories: common seeds for each vertical
You can post these as-is for each tenant. Adjust names if you prefer.

- Store categories
  - `{"name":"Beverages","active":true}`
  - `{"name":"Snacks","active":true}`
  - `{"name":"Personal Care","active":true}`
  - `{"name":"Household","active":true}`

- Salon categories
  - `{"name":"Hair Services","active":true}`
  - `{"name":"Skin & Beauty","active":true}`
  - `{"name":"Packages","active":true}`
  - `{"name":"Retail","active":true}`

- Clinic categories
  - `{"name":"Consultation","active":true}`
  - `{"name":"Diagnostics","active":true}`
  - `{"name":"Procedures","active":true}`
  - `{"name":"Medicines","active":true}`

Example cURL for a category (repeat per item):
```
curl -X POST \
  "/tenants/{tenant}/catalog/categories" \
  -H 'Content-Type: application/json' \
  -d '{"name":"Beverages","active":true}'
```

---

### 3) Products/Services: API‑ready JSON payloads
These match `ProductIn` (supports variants, tax, discount fields, barcode, image).

#### 3A. Store products (with some variants and inventory)
```
[
  {
    "sku": "BEV-COFFEE-ARABICA-250G",
    "name": "Arabica Coffee 250g",
    "category": "Beverages",
    "price": 9.99,
    "mrp": 11.99,
    "tax": 5,
    "unit": "pc",
    "active": true,
    "barcode": "1234567890123",
    "image_url": null,
    "discount_type": "percent",
    "discount_value": 10,
    "variants": [
      {
        "variant_sku": "BEV-COFFEE-ARABICA-500G",
        "attributes": {"pack": "500g"},
        "price": 17.99,
        "mrp": 20.99,
        "tax": 5,
        "discount_type": null,
        "discount_value": null,
        "image_url": null,
        "active": true
      }
    ]
  },
  {
    "sku": "SNACK-CHIPS-SALTED-100",
    "name": "Salted Potato Chips 100g",
    "category": "Snacks",
    "price": 1.49,
    "mrp": 1.99,
    "tax": 12,
    "unit": "pc",
    "active": true,
    "barcode": "2345678901234",
    "discount_type": "amount",
    "discount_value": 0.2
  },
  {
    "sku": "PCARE-SHAMPOO-300ML",
    "name": "Nourish Shampoo 300ml",
    "category": "Personal Care",
    "price": 4.99,
    "mrp": 5.99,
    "tax": 18,
    "unit": "pc",
    "active": true,
    "barcode": "3456789012345"
  },
  {
    "sku": "HOUSE-DISHWASH-LEMON-1L",
    "name": "Lemon Dishwash Liquid 1L",
    "category": "Household",
    "price": 3.49,
    "mrp": 3.99,
    "tax": 18,
    "unit": "pc",
    "active": true
  }
]
```

Inventory seeds for Store (PUT per SKU):
```
[
  {"sku":"BEV-COFFEE-ARABICA-250G","available_qty":120},
  {"sku":"BEV-COFFEE-ARABICA-500G","available_qty":60},
  {"sku":"SNACK-CHIPS-SALTED-100","available_qty":300},
  {"sku":"PCARE-SHAMPOO-300ML","available_qty":150},
  {"sku":"HOUSE-DISHWASH-LEMON-1L","available_qty":90}
]
```

CSV alternative for Store import (use your `import_products_csv`):
```
sku,name,category,price,mrp,tax,unit,active
BEV-COFFEE-ARABICA-250G,Arabica Coffee 250g,Beverages,9.99,11.99,5,pc,true
SNACK-CHIPS-SALTED-100,Salted Potato Chips 100g,Snacks,1.49,1.99,12,pc,true
PCARE-SHAMPOO-300ML,Nourish Shampoo 300ml,Personal Care,4.99,5.99,18,pc,true
HOUSE-DISHWASH-LEMON-1L,Lemon Dishwash Liquid 1L,Household,3.49,3.99,18,pc,true
```
Note: Variants aren’t covered by the CSV importer; add them afterwards via product `POST`/`PUT`.


#### 3B. Salon services (modeled as products; optional retail)
```
[
  {
    "sku": "SALON-HAIRCUT-BASIC",
    "name": "Basic Haircut (30 min)",
    "category": "Hair Services",
    "price": 8.00,
    "tax": 18,
    "unit": "service",
    "active": true,
    "variants": [
      {
        "variant_sku": "SALON-HAIRCUT-STYLIST",
        "attributes": {"professional_level": "Stylist", "duration": "30m"},
        "price": 10.00,
        "tax": 18,
        "active": true
      },
      {
        "variant_sku": "SALON-HAIRCUT-SR-STYLIST",
        "attributes": {"professional_level": "Senior Stylist", "duration": "30m"},
        "price": 12.00,
        "tax": 18,
        "active": true
      }
    ]
  },
  {
    "sku": "SALON-FACIAL-GLOW",
    "name": "Glow Facial (45 min)",
    "category": "Skin & Beauty",
    "price": 15.00,
    "tax": 18,
    "unit": "service",
    "active": true
  },
  {
    "sku": "SALON-PACKAGE-BRIDAL",
    "name": "Bridal Package",
    "category": "Packages",
    "price": 120.00,
    "tax": 18,
    "unit": "service",
    "active": true,
    "discount_type": "percent",
    "discount_value": 15
  },
  {
    "sku": "SALON-RETAIL-SERUM-50ML",
    "name": "Hair Serum 50ml",
    "category": "Retail",
    "price": 6.50,
    "mrp": 7.50,
    "tax": 18,
    "unit": "pc",
    "active": true
  }
]
```
Inventory (only for retail SKUs):
```
[{"sku":"SALON-RETAIL-SERUM-50ML","available_qty":80}]
```


#### 3C. Clinic services and medicines
```
[
  {
    "sku": "CLINIC-CONSULT-GP",
    "name": "General Physician Consultation",
    "category": "Consultation",
    "price": 12.00,
    "tax": 0,
    "unit": "service",
    "active": true,
    "variants": [
      {
        "variant_sku": "CLINIC-CONSULT-SPECIALIST",
        "attributes": {"type":"Specialist"},
        "price": 20.00,
        "tax": 0,
        "active": true
      }
    ]
  },
  {
    "sku": "CLINIC-DIAG-BLOOD-CBC",
    "name": "CBC Blood Test",
    "category": "Diagnostics",
    "price": 8.00,
    "tax": 0,
    "unit": "service",
    "active": true
  },
  {
    "sku": "CLINIC-PROC-DRESSING",
    "name": "Wound Dressing",
    "category": "Procedures",
    "price": 5.00,
    "tax": 0,
    "unit": "service",
    "active": true
  },
  {
    "sku": "MED-PARACET-500-10TAB",
    "name": "Paracetamol 500mg (10 tablets)",
    "category": "Medicines",
    "price": 1.80,
    "mrp": 2.20,
    "tax": 5,
    "unit": "pc",
    "active": true,
    "variants": [
      {
        "variant_sku": "MED-PARACET-500-20TAB",
        "attributes": {"pack":"20 tablets"},
        "price": 3.20,
        "mrp": 3.80,
        "tax": 5,
        "active": true
      }
    ]
  }
]
```
Inventory (only for medicines):
```
[
  {"sku":"MED-PARACET-500-10TAB","available_qty":500},
  {"sku":"MED-PARACET-500-20TAB","available_qty":250}
]
```

---

### 4) End‑to‑end workflow sequences (per vertical)
Use your Admin UI where available or run the HTTP calls directly.

#### Store workflow
1. Create categories (Beverages, Snacks, Personal Care, Household).
2. Upsert products (JSON `POST /catalog/products` or CSV import). Then add variants via `POST`/`PUT` where needed.
3. Set inventory for each SKU using `PUT /inventory/{sku}`.
4. (Optional) Track events for analytics/AI features:
   - `POST /tenants/{tenant}/events` with `type: "product_view"`, `add_to_cart`, `checkout_start`, `order_placed`, etc.
5. Use AI endpoints for insights (requires module/capability):
   - `GET /tenants/{tenant}/ai/top_sellers?days=30&top=20`
   - `GET /tenants/{tenant}/ai/forecast_low_stock?days=30&lead_time=3&safety_days=2&top=50`
   - `GET /tenants/{tenant}/ai/sales_forecast?days=30&horizon=14`

#### Salon workflow
1. Create categories (Hair Services, Skin & Beauty, Packages, Retail).
2. Upsert services as products with `unit: "service"`; use variants to differentiate professional levels or duration.
3. (Optional) Add retail products under Retail category and set inventory for those SKUs only.
4. (Optional) Track events like `service_view`, `appointment_intent`, `checkout_start`, `order_placed` using the generic events endpoint. Example:
```
POST /tenants/{tenant}/events
{
  "type": "appointment_intent",
  "data": {
    "sku": "SALON-HAIRCUT-STYLIST",
    "preferred_time": "2025-12-08T10:00:00+05:30",
    "customer_phone": "+91..."
  }
}
```
5. Until a dedicated appointments API is added, you can capture booking intents via events and convert them manually or in back-office flows.

#### Clinic workflow
1. Create categories (Consultation, Diagnostics, Procedures, Medicines).
2. Upsert services (consultations, tests, procedures) with `unit: "service"`.
3. Upsert medicines as products under Medicines; set inventory for medicines.
4. (Optional) Track events like `appointment_intent`, `test_ordered`, `prescription_filled` via events API.

---

### 5) Example HTTP calls
- Upsert a product (works for services too):
```
curl -X POST \
  "/tenants/{tenant}/catalog/products" \
  -H 'Content-Type: application/json' \
  -d '{
    "sku":"SALON-HAIRCUT-BASIC",
    "name":"Basic Haircut (30 min)",
    "category":"Hair Services",
    "price":8.00,
    "tax":18,
    "unit":"service",
    "active":true
  }'
```

- Set inventory for one SKU:
```
curl -X PUT \
  "/tenants/{tenant}/inventory/MED-PARACET-500-10TAB" \
  -H 'Content-Type: application/json' \
  -d '{"sku":"MED-PARACET-500-10TAB","available_qty":500}'
```

- Post an event:
```
curl -X POST \
  "/tenants/{tenant}/events" \
  -H 'Content-Type: application/json' \
  -d '{"type":"order_placed","data":{"order_id":"ORD123","items":[{"sku":"SNACK-CHIPS-SALTED-100","qty":2}]}}'
```

---

### 6) Admin UI notes
- The Admin UI already calls these endpoints via `admin_ui/src/api/catalog.ts`.
- For listing variants in tables, use `flatten_variants=true` in `GET /catalog/products` to view variant rows with effective fields from their parent.

---

### 7) What might be “missing” for a truly complete Salon/Clinic journey
- Dedicated appointment scheduling, staff rosters, patient profiles, prescriptions, etc., aren’t implemented in the exposed routers. For now, model services as products and use the generic events collector to capture booking intents and funnel analytics. If you want, I can propose minimal appointment endpoints next.

---

### 8) Quick checks before loading
- Decide the tenant id(s) where you’ll load data.
- Confirm your tax regime (examples use simple percentages; set to 0 where tax-exempt).
- Currency formatting is left to UI/business rules; numbers are stored as floats.

---

### 9) Would you like me to tailor this to your tenant(s)?
Share:
- Tenant ids, desired currency/tax defaults, and any category name changes.
- For Salon/Clinic: list of staff/practitioners and typical slot durations if you’d like pre-baked variants reflecting duration/level.
