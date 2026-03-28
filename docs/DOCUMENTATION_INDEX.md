# Documentation Index

This index helps you find **business** and **technical** documentation for the multi-tenant SaaS application. All paths are under the `docs/` folder.

---

## Quick links

| Document | Audience | Contents |
|----------|----------|----------|
| [**APPLICATION_GUIDE.md**](APPLICATION_GUIDE.md) | Everyone | Overview, architecture, tenant model, RBAC, use cases by industry, demo setup |
| [**BUSINESS_GUIDE.md**](BUSINESS_GUIDE.md) | Product, Business, Support | Module-by-module **business** description, feature examples (like No-Show), use case diagrams |
| [**TECHNICAL_REFERENCE.md**](TECHNICAL_REFERENCE.md) | Developers | **Technical** reference: APIs, fields, functions, sequence diagrams |
| [**AI_CAPABILITIES.md**](AI_CAPABILITIES.md) | Product, Developers | AI module capabilities, `ai_config` fields, endpoints |
| [**whatsapp-workflow.md**](whatsapp-workflow.md) | Business, Support | WhatsApp menu and conversation flow |
| [**whatsapp-workflow-actions.md**](whatsapp-workflow-actions.md) | Developers | WhatsApp dynamic actions and triggers |
| [**DEPLOYMENT.md**](DEPLOYMENT.md) | DevOps | Deployment and environment |

---

## Business documentation

Use these when you need to understand **what** the system does and **how** it behaves for users and tenants.

- **[BUSINESS_GUIDE.md](BUSINESS_GUIDE.md)**  
  - What each **module** does (Auth, Tenants, Users, Customers, Appointments, No-Show, Store, Reports, Promotions, WhatsApp, AI, etc.).  
  - **Examples** for each major feature (e.g. No-Show flow step-by-step, booking, orders, OTP login).  
  - **Use case diagrams** (Mermaid) by actor (Super Admin, Tenant Admin, Staff, Customer).  
  - **Feature matrix** and industry mapping.

- **[APPLICATION_GUIDE.md](APPLICATION_GUIDE.md)**  
  - High-level architecture, tenant isolation, RBAC, use cases by industry (salon, clinic, store, etc.), demo tenants and scripts.

- **[AI_CAPABILITIES.md](AI_CAPABILITIES.md)**  
  - AI features from a product perspective: no-show, predictions, reschedule, etc., and how they are configured.

---

## Technical documentation

Use these when you need **APIs**, **data fields**, **functions**, and **flows** for implementation or integration.

- **[TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md)**  
  - **Module-by-module** technical reference:  
    - API endpoints (method, path, purpose).  
    - Main **fields** (request/response and storage).  
    - Main **functions** (routers and services).  
  - **Sequence diagrams** (Mermaid) for: Login (with OTP), Book appointment, No-show flow, Place order, Reports, Promotions.

- **[APPLICATION_GUIDE.md](APPLICATION_GUIDE.md)** §4  
  - Stack, key API groups, no-show flow (technical steps), AI config persistence.

- **[whatsapp-workflow-actions.md](whatsapp-workflow-actions.md)**  
  - WhatsApp webhook, dynamic actions, and integration details.

---

## Module → documents mapping

| Module / Area | Business view | Technical view |
|---------------|----------------|----------------|
| **Auth & Login** | BUSINESS_GUIDE § Auth, Login OTP | TECHNICAL_REFERENCE § Auth |
| **Tenants & Settings** | BUSINESS_GUIDE § Tenants | TECHNICAL_REFERENCE § Tenants |
| **Users** | BUSINESS_GUIDE § Users | TECHNICAL_REFERENCE § Users |
| **Customers** | BUSINESS_GUIDE § Customers | TECHNICAL_REFERENCE § Customers |
| **Appointments** | BUSINESS_GUIDE § Appointments | TECHNICAL_REFERENCE § Appointments |
| **No-Show Blocked** | BUSINESS_GUIDE § No-Show (detailed example) | TECHNICAL_REFERENCE § No-Show, APPLICATION_GUIDE §4.3 |
| **Store (Orders, Carts)** | BUSINESS_GUIDE § Store | TECHNICAL_REFERENCE § Store |
| **Catalog (Products, Categories)** | BUSINESS_GUIDE § Store / Catalog | TECHNICAL_REFERENCE § Catalog |
| **Reports** | BUSINESS_GUIDE § Reports | TECHNICAL_REFERENCE § Reports |
| **Promotions** | BUSINESS_GUIDE § Promotions | TECHNICAL_REFERENCE § Promotions |
| **WhatsApp** | whatsapp-workflow.md, BUSINESS_GUIDE § WhatsApp | TECHNICAL_REFERENCE § WhatsApp, whatsapp-workflow-actions.md |
| **AI** | AI_CAPABILITIES.md, BUSINESS_GUIDE § AI | TECHNICAL_REFERENCE § AI, APPLICATION_GUIDE §4.4 |

---

## Diagrams

- **Use case diagrams**: [BUSINESS_GUIDE.md](BUSINESS_GUIDE.md) (Mermaid, by actor).
- **Sequence diagrams**: [TECHNICAL_REFERENCE.md](TECHNICAL_REFERENCE.md) (Login, Book appointment, No-show, Place order, Reports, Promotions).
- **Architecture / tenant model**: [APPLICATION_GUIDE.md](APPLICATION_GUIDE.md) §2 (Mermaid).

---

## Document conventions

- **Base URL**: API examples use prefix `/v1` (e.g. `POST /v1/auth/login`).
- **Tenant scope**: Most APIs use path parameter `{tenant}`; auth enforces tenant scope for tenant_admin and staff.
- **Roles**: `super_admin`, `tenant_admin`, `staff` — see APPLICATION_GUIDE §2.4 for RBAC.
