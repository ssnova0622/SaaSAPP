# old_app – Revamp Summary

This folder contains the **old SaaS backend** (Python). The revamp **preserves all logic and use cases**; no behavioral changes were made in this folder.

## Structure (unchanged)

- **services/** – Core, store, WhatsApp, workflow, AI, salon (appointments), promotions, etc.
- **repositories/** – Data access for tenants, customers, appointments, orders, products, etc.
- **models/** – Data models (customers, professionals, workflows, users, etc.).
- **utils/** – Helpers and constants.

## Optimization notes (for future work)

- Use `app.utils.constants` for status strings and shared literals.
- Prefer repository injection in services where it helps testing.
- Type hints and small refactors can be added without changing behavior.

## Full documentation

See **`docs/REVAMP_REPORT.md`** in the project root for the complete revamp report.
