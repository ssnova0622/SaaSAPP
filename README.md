# Multi-tenant SaaS Backend

A modular, production-grade backend for a multi-tenant SaaS platform with:

- Auth, Tenant, Staff, Store
- Customers, Catalog, Appointments
- Billing, Retention, WhatsApp
- Media / Uploads
- Reports (with AI summaries)
- Full AI module (LLM, prompts, embeddings, tools)
- Cron, Integrations

## Tech stack

- FastAPI
- MongoDB
- httpx
- JWT auth
- Passlib (password hashing)

## Architecture

- `routers/` — HTTP endpoints
- `services/` — domain logic
- `repositories/` — DB access
- `models/` — Pydantic schemas
- `security/` — auth, JWT, passwords
- `services/ai/` — AI orchestration, tools
- `services/cron/` — scheduled jobs

## Multi-tenancy

- Tenant entity (`models/tenant.py`)
- Tenant enforcement via `routers/deps.py`
- All domain models include `tenant` field
- Tenant lifecycle hooks in `tenant_lifecycle_service.py`

## AI

- `ai_client.py` — LLM client (OpenAI-style)
- `ai_chat_service.py` — chat orchestration + tool calls
- `ai_tool_executor.py` — HTTP/internal/custom tools
- `ai_prompt_service.py` — prompt templates
- `ai_embedding_service.py` — embeddings

## Running locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
