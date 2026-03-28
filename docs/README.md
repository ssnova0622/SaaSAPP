# Scripts

Programs for mock data, **industry demo data**, and super admin. **Run from project root** with the project virtualenv so `app` and dependencies (FastAPI, PyMongo, etc.) are available.

## Setup

- MongoDB must be running (e.g. `mongodb://localhost:27017/saas_db` or set `MONGO_URI` in project root `.env`).
- From project root, activate the project venv then run the commands below.

---

## Industry demo (ss_business_* tenants)

Tenant IDs follow **`ss_business_{domain}`**: e.g. `ss_business_salon`, `ss_business_clinic`, `ss_business_gym`, `ss_business_school`, `ss_business_store`, `ss_business_camp`, `ss_business_car_showroom`.

### Seed one domain

```bash
python scripts/run_seed_domain.py --domain salon
python scripts/run_seed_domain.py --domain clinic --force   # replace existing
python scripts/run_seed_domain.py --tenant ss_business_gym   # domain inferred from tenant
```

### Seed all domains (one script)

Seeds every industry tenant in sequence: salon, clinic, gym, school, store, camp, car_showroom. Each domain gets full data (customers, professionals, services, appointments, categories, products, inventory, orders, promotions, **whatsapp_triggers**). Store and car_showroom each have **50+ products** for demos.

```bash
python scripts/run_seed_all_domains.py
python scripts/run_seed_all_domains.py --force   # replace existing data for each tenant
```

### Delete one domain’s data and tenant

```bash
python scripts/run_delete_domain.py --domain salon
python scripts/run_delete_domain.py --tenant ss_business_clinic
python scripts/run_delete_domain.py --domain store --keep-tenant   # only delete collection data
```

### Delete all demo tenants (all ss_business_*)

```bash
python scripts/run_delete_all_demo.py
python scripts/run_delete_all_demo.py --dry-run   # list what would be deleted
```

### Explore: list demo tenants and what to show

```bash
python scripts/explore_all_modules.py
```

Prints all `ss_business_*` tenants and a short guide (per domain) for demos: which pages to open, which features to show (appointments, no-show blocked, AI config, store, etc.).

### Industry data layout

```
scripts/industries/
  _base.py              # TENANT_PREFIX, DOMAINS, get_tenant_id(domain)
  salon/data.py         # Bulk data: customers, professionals, appointments, no_show_count, ai_config, whatsapp_triggers
  clinic/data.py        # Monthly/weekly/consultant doctors, OPD-style slots, whatsapp_triggers
  gym/data.py           # Trainers, PT sessions, whatsapp_triggers
  school/data.py        # Teachers, parent meetings, whatsapp_triggers
  store/data.py         # 50+ products, categories, inventory, orders, promotions, whatsapp_triggers
  camp/data.py          # Instructors, day camp sessions, whatsapp_triggers
  car_showroom/data.py  # 50 car models, sales reps, test drives, whatsapp_triggers
```

Each `data.py` exposes: `get_tenant_id()`, `get_modules_capabilities()`, `get_seed_data(tenant_id)`. Seed data covers all tenant-scoped collections (including **whatsapp_triggers** with at least one trigger per tenant). Store and car_showroom include **at least 50 products** each.

---

## Postman collection

A Postman collection for the REST API is in **`postman/SaasProject_API.postman_collection.json`**.

- **Import** it in Postman. Collection variables: `base_url` (default `http://127.0.0.1:8000`), `token` (set after **Auth → Login**), `tenant` (e.g. `ss_business_salon`).
- **Folders**: Auth, Tenants, Admin (tenants overview, cron), Users, WhatsApp (menus, config, triggers), Appointments, Slots, Customers, Store/Catalog, Reports, Promotions, Services, Staff, Retention, Health.
- See **`postman/README.md`** for setup and saving the token after login.

---

## Legacy demo tenant (tenant_demo)

| Command | Description |
|--------|-------------|
| `python scripts/create_super_admin.py` | Create super admin user (global login) |
| `python scripts/seed_mock_data.py` | Seed **tenant_demo** with customers, professionals, appointments, store, promotions, workflows, WhatsApp, cron |
| `python scripts/delete_mock_data.py` | Delete all mock data and **tenant_demo** (and demo user); does not remove super admin |

## Configuration

Settings are in project root `settings.py` or environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MOCK_TENANT_ID` | `tenant_demo` | Demo tenant id for seed_mock_data / delete_mock_data |
| `MOCK_EMAIL` | (see settings.py) | Demo tenant admin login email |
| `MOCK_PASSWORD` | (see settings.py) | Demo tenant admin password |
| `SUPER_ADMIN_EMAIL` | (see settings.py) | Super admin login email |
| `SUPER_ADMIN_PASSWORD` | (see settings.py) | Super admin password |

---

## Generate complete documentation (DOCX)

To produce a single Word document with all business and technical documentation (overview, use cases with examples, feature matrix, architecture, API, data model, demo scripts):

```bash
pip install python-docx
python3 docs/generate_application_docx.py
```

Output: **`docs/Application_Complete_Documentation.docx`**

The DOCX includes: Part 1 — Business (overview, tenant model, use cases by industry with examples, feature matrix); Part 2 — Technical (architecture, stack, API groups, no-show flow, AI config, API examples, data model); Part 3 — Demo tenants and scripts; Appendix — references.

---

## Documentation

- **Application functionality, use cases, architecture**: `docs/APPLICATION_GUIDE.md`
- **Complete DOCX (business + technical)**: run `python3 docs/generate_application_docx.py` → `docs/Application_Complete_Documentation.docx`
- **AI capabilities and config**: `docs/AI_CAPABILITIES.md`
- **Deployment**: `docs/DEPLOYMENT.md`
