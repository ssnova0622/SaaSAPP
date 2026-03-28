### Goal
Below is a complete bootstrap “dump” (seed) for your MongoDB collections so you can start from scratch with three demo tenants: `store_demo`, `salon_demo`, `clinic_demo`.

What’s included (aligned with your codebase indices and storage methods):
- Collections: `tenants`, `categories`, `products`, `inventory`, `customers`, `staff`, `professionals`, `appointments`, `orders`, `payments`, `events`.  
- Format: NDJSON (one JSON per line).  
- Also provided: suggested load order and `mongoimport` commands, plus REST alternatives.

Note: Some domains (carts, WhatsApp menus/sessions) exist in code but aren’t needed for a minimal working dataset; you can import them later if required.

---

### Load order
1) tenants  
2) categories  
3) products  
4) inventory  
5) customers  
6) staff  
7) professionals  
8) appointments (optional sample)  
9) orders (optional sample)  
10) payments (optional sample)  
11) events (optional sample)

This respects unique indexes and references (e.g., products before inventory; tenants first).

---

### 1) tenants.ndjson
Minimal but useful defaults: modules/capabilities, payment and delivery config, WhatsApp config. Primary key is `_id` (tenant string). Your code normalizes booleans and defaults on read paths.
```
{"_id":"store_demo","category":"store","owner_email":"owner@store.demo","owner_phone":"+10000000001","tz":"Asia/Kolkata","invoice_delivery":"both","active":true,"modules":["store","ai"],"capabilities":["store.catalog","ai.predictions","store.payments"],"store_enabled":true,"payment_config":{"provider":"dummy","currency":"INR","methods":["ONLINE","COD"],"test_mode":true,"webhook_secret":"dev"},"delivery_config":{"delivery_enabled":true,"pickup_enabled":true,"service_areas":[],"store_hours":[]},"whatsapp_config":{"provider":"twilio","from_numbers":["+19998887777"],"webhook_secret":"dev","account_sid":"","auth_token":"","locale_default":"en","phone_number_id":"","access_token":"","active_menu_id":""}}
{"_id":"salon_demo","category":"salon","owner_email":"owner@salon.demo","owner_phone":"+10000000002","tz":"Asia/Kolkata","invoice_delivery":"both","active":true,"modules":["store","ai"],"capabilities":["store.catalog","ai.predictions"],"store_enabled":true,"payment_config":{"provider":"dummy","currency":"INR","methods":["ONLINE","COD"],"test_mode":true,"webhook_secret":"dev"},"delivery_config":{"delivery_enabled":true,"pickup_enabled":true,"service_areas":[],"store_hours":[]},"whatsapp_config":{"provider":"twilio","from_numbers":[],"webhook_secret":"dev","account_sid":"","auth_token":"","locale_default":"en","phone_number_id":"","access_token":"","active_menu_id":""}}
{"_id":"clinic_demo","category":"clinic","owner_email":"owner@clinic.demo","owner_phone":"+10000000003","tz":"Asia/Kolkata","invoice_delivery":"both","active":true,"modules":["store","ai"],"capabilities":["store.catalog","ai.predictions"],"store_enabled":true,"payment_config":{"provider":"dummy","currency":"INR","methods":["ONLINE","COD"],"test_mode":true,"webhook_secret":"dev"},"delivery_config":{"delivery_enabled":true,"pickup_enabled":true,"service_areas":[],"store_hours":[]},"whatsapp_config":{"provider":"twilio","from_numbers":[],"webhook_secret":"dev","account_sid":"","auth_token":"","locale_default":"en","phone_number_id":"","access_token":"","active_menu_id":""}}
```

---

### 2) categories.ndjson
```
{"tenant":"store_demo","name":"Beverages","active":true}
{"tenant":"store_demo","name":"Snacks","active":true}
{"tenant":"store_demo","name":"Personal Care","active":true}
{"tenant":"store_demo","name":"Household","active":true}
{"tenant":"salon_demo","name":"Hair Services","active":true}
{"tenant":"salon_demo","name":"Skin & Beauty","active":true}
{"tenant":"salon_demo","name":"Packages","active":true}
{"tenant":"salon_demo","name":"Retail","active":true}
{"tenant":"clinic_demo","name":"Consultation","active":true}
{"tenant":"clinic_demo","name":"Diagnostics","active":true}
{"tenant":"clinic_demo","name":"Procedures","active":true}
{"tenant":"clinic_demo","name":"Medicines","active":true}
```

---

### 3) products.ndjson
Matches `ProductIn` and storage expectations (supports `variants`).
```
{"tenant":"store_demo","sku":"BEV-COFFEE-ARABICA-250G","name":"Arabica Coffee 250g","category":"Beverages","price":9.99,"mrp":11.99,"tax":5,"unit":"pc","active":true,"barcode":"1234567890123","discount_type":"percent","discount_value":10,"variants":[{"variant_sku":"BEV-COFFEE-ARABICA-500G","attributes":{"pack":"500g"},"price":17.99,"mrp":20.99,"tax":5,"active":true}]}
{"tenant":"store_demo","sku":"SNACK-CHIPS-SALTED-100","name":"Salted Potato Chips 100g","category":"Snacks","price":1.49,"mrp":1.99,"tax":12,"unit":"pc","active":true,"barcode":"2345678901234","discount_type":"amount","discount_value":0.2}
{"tenant":"store_demo","sku":"PCARE-SHAMPOO-300ML","name":"Nourish Shampoo 300ml","category":"Personal Care","price":4.99,"mrp":5.99,"tax":18,"unit":"pc","active":true,"barcode":"3456789012345"}
{"tenant":"store_demo","sku":"HOUSE-DISHWASH-LEMON-1L","name":"Lemon Dishwash Liquid 1L","category":"Household","price":3.49,"mrp":3.99,"tax":18,"unit":"pc","active":true}

{"tenant":"salon_demo","sku":"SALON-HAIRCUT-BASIC","name":"Basic Haircut (30 min)","category":"Hair Services","price":8.0,"tax":18,"unit":"service","active":true,"variants":[{"variant_sku":"SALON-HAIRCUT-STYLIST","attributes":{"professional_level":"Stylist","duration":"30m"},"price":10.0,"tax":18,"active":true},{"variant_sku":"SALON-HAIRCUT-SR-STYLIST","attributes":{"professional_level":"Senior Stylist","duration":"30m"},"price":12.0,"tax":18,"active":true}]}
{"tenant":"salon_demo","sku":"SALON-FACIAL-GLOW","name":"Glow Facial (45 min)","category":"Skin & Beauty","price":15.0,"tax":18,"unit":"service","active":true}
{"tenant":"salon_demo","sku":"SALON-PACKAGE-BRIDAL","name":"Bridal Package","category":"Packages","price":120.0,"tax":18,"unit":"service","active":true,"discount_type":"percent","discount_value":15}
{"tenant":"salon_demo","sku":"SALON-RETAIL-SERUM-50ML","name":"Hair Serum 50ml","category":"Retail","price":6.5,"mrp":7.5,"tax":18,"unit":"pc","active":true}

{"tenant":"clinic_demo","sku":"CLINIC-CONSULT-GP","name":"General Physician Consultation","category":"Consultation","price":12.0,"tax":0,"unit":"service","active":true,"variants":[{"variant_sku":"CLINIC-CONSULT-SPECIALIST","attributes":{"type":"Specialist"},"price":20.0,"tax":0,"active":true}]}
{"tenant":"clinic_demo","sku":"CLINIC-DIAG-BLOOD-CBC","name":"CBC Blood Test","category":"Diagnostics","price":8.0,"tax":0,"unit":"service","active":true}
{"tenant":"clinic_demo","sku":"CLINIC-PROC-DRESSING","name":"Wound Dressing","category":"Procedures","price":5.0,"tax":0,"unit":"service","active":true}
{"tenant":"clinic_demo","sku":"MED-PARACET-500-10TAB","name":"Paracetamol 500mg (10 tablets)","category":"Medicines","price":1.8,"mrp":2.2,"tax":5,"unit":"pc","active":true,"variants":[{"variant_sku":"MED-PARACET-500-20TAB","attributes":{"pack":"20 tablets"},"price":3.2,"mrp":3.8,"tax":5,"active":true}]}
```

---

### 4) inventory.ndjson
```
{"tenant":"store_demo","sku":"BEV-COFFEE-ARABICA-250G","available_qty":120}
{"tenant":"store_demo","sku":"BEV-COFFEE-ARABICA-500G","available_qty":60}
{"tenant":"store_demo","sku":"SNACK-CHIPS-SALTED-100","available_qty":300}
{"tenant":"store_demo","sku":"PCARE-SHAMPOO-300ML","available_qty":150}
{"tenant":"store_demo","sku":"HOUSE-DISHWASH-LEMON-1L","available_qty":90}
{"tenant":"salon_demo","sku":"SALON-RETAIL-SERUM-50ML","available_qty":80}
{"tenant":"clinic_demo","sku":"MED-PARACET-500-10TAB","available_qty":500}
{"tenant":"clinic_demo","sku":"MED-PARACET-500-20TAB","available_qty":250}
```

---

### 5) customers.ndjson
```
{"tenant":"store_demo","phone":"+911111111111","name":"Asha","email":"asha@example.com","tags":["vip"],"last_seen_at":null,"total_bookings":0,"score":90,"active":true}
{"tenant":"salon_demo","phone":"+922222222222","name":"Ravi","email":"ravi@example.com","tags":["loyalty"],"last_seen_at":null,"total_bookings":2,"score":75,"active":true}
{"tenant":"clinic_demo","phone":"+933333333333","name":"Sara","email":"sara@example.com","tags":["chronic"],"last_seen_at":null,"total_bookings":1,"score":60,"active":true}
```

---

### 6) staff.ndjson
`id` must be unique per tenant; use UUIDs in real imports.
```
{"tenant":"store_demo","id":"a1111111-1111-1111-1111-111111111111","name":"Store Manager","role":"manager","phone":"+10000000011","email":"mgr@store.demo","skills":["ops","inventory"],"active":true,"created_at":{"$date":"2025-01-01T00:00:00Z"},"updated_at":{"$date":"2025-01-01T00:00:00Z"}}
{"tenant":"salon_demo","id":"b2222222-2222-2222-2222-222222222222","name":"Anita","role":"stylist","phone":"+10000000012","email":"anita@salon.demo","skills":["haircut","color"],"active":true,"created_at":{"$date":"2025-01-01T00:00:00Z"},"updated_at":{"$date":"2025-01-01T00:00:00Z"}}
{"tenant":"clinic_demo","id":"c3333333-3333-3333-3333-333333333333","name":"Dr. Menon","role":"gp","phone":"+10000000013","email":"menon@clinic.demo","skills":["consult"],"active":true,"created_at":{"$date":"2025-01-01T00:00:00Z"},"updated_at":{"$date":"2025-01-01T00:00:00Z"}}
```

---

### 7) professionals.ndjson
Professionals are distinct from staff in your storage. Include availability slots if you want.
```
{"tenant":"salon_demo","name":"Anita","price":10.0,"slots":[{"time":"10:00","status":"available"},{"time":"10:30","status":"available"}],"active":true}
{"tenant":"salon_demo","name":"Rohit","price":8.0,"slots":[{"time":"11:00","status":"available"}],"active":true}
{"tenant":"clinic_demo","name":"Dr. Menon","price":12.0,"slots":[{"time":"09:00","status":"available"},{"time":"09:30","status":"available"}],"active":true}
```

---

### 8) appointments.ndjson (optional sample)
Aligns with your `Appointment` dataclass shape.
```
{"tenant":"salon_demo","id":"APPT-SLN-0001","customer_name":"Ravi","customer_phone":"+922222222222","professional":"Anita","time":"2025-12-08T10:00:00+05:30","price":10.0,"status":"booked","created_at":{"$date":"2025-12-07T07:12:00Z"}}
{"tenant":"clinic_demo","id":"APPT-CLN-0001","customer_name":"Sara","customer_phone":"+933333333333","professional":"Dr. Menon","time":"2025-12-08T09:00:00+05:30","price":12.0,"status":"booked","created_at":{"$date":"2025-12-07T07:12:00Z"}}
```

---

### 9) orders.ndjson (optional sample)
Orders link to SKUs and include basic totals and timeline, consistent with your storage logic.
```
{"tenant":"store_demo","id":"ORD-0001","status":"placed","customer":{"name":"Asha","phone":"+911111111111"},"items":[{"sku":"SNACK-CHIPS-SALTED-100","name":"Salted Potato Chips 100g","qty":2,"price":1.49},{"sku":"BEV-COFFEE-ARABICA-250G","name":"Arabica Coffee 250g","qty":1,"price":9.99}],"totals":{"subtotal":12.97},"timeline":[{"ts":{"$date":"2025-12-07T07:12:00Z"},"event":"placed","meta":{"inventory":{"action":"decrement","items":[{"sku":"SNACK-CHIPS-SALTED-100","qty":2},{"sku":"BEV-COFFEE-ARABICA-250G","qty":1}]}}}],"created_at":{"$date":"2025-12-07T07:12:00Z"},"updated_at":{"$date":"2025-12-07T07:12:00Z"}}
```

---

### 10) payments.ndjson (optional sample)
```
{"tenant":"store_demo","order_id":"ORD-0001","status":"pending","method":"COD","amount":12.97,"currency":"INR","created_at":{"$date":"2025-12-07T07:12:00Z"}}
```

---

### 11) events.ndjson (optional sample)
```
{"tenant":"store_demo","id":"EVT-0001","type":"product_view","ts":1765077120,"data":{"sku":"SNACK-CHIPS-SALTED-100"},"created_at":{"$date":"2025-12-07T07:12:00Z"}}
{"tenant":"salon_demo","id":"EVT-0002","type":"appointment_intent","ts":1765077120,"data":{"sku":"SALON-HAIRCUT-STYLIST","preferred_time":"2025-12-08T10:00:00+05:30","customer_phone":"+922222222222"},"created_at":{"$date":"2025-12-07T07:12:00Z"}}
{"tenant":"clinic_demo","id":"EVT-0003","type":"test_ordered","ts":1765077120,"data":{"sku":"CLINIC-DIAG-BLOOD-CBC","customer_phone":"+933333333333"},"created_at":{"$date":"2025-12-07T07:12:00Z"}}
```

---

### Import commands (mongoimport)
Replace `DB_URI` with your connection string; use your DB name if different from the default `ai_appo`.
```
# Tenants
mongoimport --uri "DB_URI/ai_appo" --collection tenants --mode=upsert --file tenants.ndjson --jsonArray=false

# Categories
mongoimport --uri "DB_URI/ai_appo" --collection categories --mode=upsert --file categories.ndjson --jsonArray=false

# Products
mongoimport --uri "DB_URI/ai_appo" --collection products --mode=upsert --file products.ndjson --jsonArray=false

# Inventory
mongoimport --uri "DB_URI/ai_appo" --collection inventory --mode=upsert --file inventory.ndjson --jsonArray=false

# Customers
mongoimport --uri "DB_URI/ai_appo" --collection customers --mode=upsert --file customers.ndjson --jsonArray=false

# Staff
mongoimport --uri "DB_URI/ai_appo" --collection staff --mode=upsert --file staff.ndjson --jsonArray=false

# Professionals
mongoimport --uri "DB_URI/ai_appo" --collection professionals --mode=upsert --file professionals.ndjson --jsonArray=false

# Appointments (optional)
mongoimport --uri "DB_URI/ai_appo" --collection appointments --mode=upsert --file appointments.ndjson --jsonArray=false

# Orders (optional)
mongoimport --uri "DB_URI/ai_appo" --collection orders --mode=upsert --file orders.ndjson --jsonArray=false

# Payments (optional)
mongoimport --uri "DB_URI/ai_appo" --collection payments --mode=upsert --file payments.ndjson --jsonArray=false

# Events (optional)
mongoimport --uri "DB_URI/ai_appo" --collection events --mode=upsert --file events.ndjson --jsonArray=false
```

If you prefer arrays instead of NDJSON, convert files to JSON arrays and pass `--jsonArray`.

---

### REST-based seeding (alternative)
- Tenants: use your admin route (if present) or write directly to DB once; subsequent config updates via `update_tenant_settings` in backend.
- Categories/Products: use `admin_ui` or direct API (`/tenants/{tenant}/catalog/...`).
- Inventory: `PUT /tenants/{tenant}/inventory/{sku}` with `{ sku, available_qty }`.
- Events: `POST /tenants/{tenant}/events`.

---

### Notes and constraints
- Uniqueness:
  - `products`: unique on `(tenant, sku)`
  - `categories`: unique on `(tenant, name)`
  - `inventory`: unique on `(tenant, sku)`
  - `professionals`: unique on `(tenant, name)`
  - `customers`: unique on `(tenant, phone)`
  - `orders`: unique on `(tenant, id)`
  - `staff`: unique on `(tenant, id)`
- Field defaults: your storage normalizes missing `active` flags to true in some collections; seeds above set them explicitly.
- Timezone/currency: adjust `tz` and `payment_config.currency` per tenant as needed.

---

### Want me to package these as files?
Tell me the exact tenant IDs and any category/product naming tweaks, and I’ll generate ready-to-import files for you (and can also tailor for non-INR currencies or different taxes).