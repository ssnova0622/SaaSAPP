### Overview
You have two FastAPI apps in this repo:
- ai_scheduler/ — the new AI‑Powered Appointment & Scheduling API (in‑memory, no DB required)
- app/ — the existing WhatsApp Store app (uses MongoDB)

You can run either (or both) depending on what you want to try.

---

### 1) Quick start: run the AI Scheduler API (no database needed)

Prereqs:
- Python 3.9+ recommended

Install deps (once):
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run the server (factory mode):
```bash
uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
```

Verify it’s up:
- Health: http://127.0.0.1:8100/health → `{ "status": "ok" }`
- Swagger UI: http://127.0.0.1:8100/docs

Pre‑seeded demo tenants: `demo-salon`, `demo-clinic`.

Try endpoints:
- Professionals:
  ```bash
  curl http://127.0.0.1:8100/v1/tenants/demo-salon/professionals
  ```
- Slots for a professional:
  ```bash
  curl http://127.0.0.1:8100/v1/tenants/demo-salon/professionals/Alice/slots
  ```
- AI slot prediction:
  ```bash
  curl -X POST http://127.0.0.1:8100/v1/tenants/demo-salon/slots/predict \
    -H 'Content-Type: application/json' \
    -d '{"tenant":"demo-salon","professional":"Alice","top_k":3}'
  ```
- Create appointment:
  ```bash
  curl -X POST http://127.0.0.1:8100/v1/tenants/demo-salon/appointments \
    -H 'Content-Type: application/json' \
    -d '{"tenant":"demo-salon","customer_name":"John Doe","customer_phone":"+15551234567","professional":"Alice","time":"11:30"}'
  ```
- Cancel appointment:
  ```bash
  curl -X DELETE http://127.0.0.1:8100/v1/tenants/demo-salon/appointments/<appointment_id>
  ```

WebSocket (realtime updates):
- Connect to: `ws://127.0.0.1:8100/ws/demo-salon`
- You’ll receive JSON events on appointment create/cancel and Twilio webhook messages.

Twilio/WhatsApp webhook stub:
- Endpoint: `POST /v1/integrations/twilio/whatsapp`
- Example:
  ```bash
  curl -X POST http://127.0.0.1:8100/v1/integrations/twilio/whatsapp \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'WaId=demo-user&From=+15551234567&Body=book&tenant=demo-salon'
  ```

Optional AI predictor tuning:
- This module (`ai_scheduler/services/ai.py`) is heuristic by default; no external API key required.

---

### 2) Run the WhatsApp Store app (requires MongoDB)
This app initializes a Mongo connection on startup and needs a running MongoDB.

Start MongoDB (choose one):
- Docker (recommended):
  ```bash
  docker run --name mongo -p 27017:27017 -d mongo:6
  ```
- Local service: Install MongoDB Community and start it.

Environment (optional): create a `.env` in project root if you want to override defaults from `settings.py`:
```
MONGO_URI=mongodb://localhost:27017/ss_salon
DEBUG=true
OPENAI_API_KEY=
AI_MODEL=gpt-4o-mini
AI_ENABLED=false
```

Run the server:
```bash
uvicorn app.main:app --reload --port 8000
```

Open:
- Swagger UI: http://127.0.0.1:8000/docs
- Root page (Jinja template): http://127.0.0.1:8000/

Note on AI features in this app:
- `app/usecases/ai_service.py` will call OpenAI if `OPENAI_API_KEY` and `AI_ENABLED=true` are set; otherwise it falls back to heuristics. If you don’t want external calls, leave `AI_ENABLED` as `false` or empty.

---

### 3) Running both apps together
You can run both simultaneously on different ports in two terminals:
- Terminal A (AI Scheduler):
  ```bash
  uvicorn ai_scheduler.main:create_app --factory --reload --port 8100
  ```
- Terminal B (WhatsApp Store):
  ```bash
  uvicorn app.main:app --reload --port 8000
  ```

---

### 4) Common troubleshooting
- Port already in use → change `--port` (e.g., 8101/8001) or free the port.
- Import error for packages → ensure the virtualenv is activated and `pip install -r requirements.txt` completed without errors.
- Mongo connection errors (for the `app/` app) → verify Mongo is running and `MONGO_URI` points to it.
- CORS for testing from a browser → `ai_scheduler` already enables permissive CORS.

---

### 5) Quick verification checklist
- AI Scheduler: `GET /health` returns `{status: "ok"}` on port 8100.
- AI Scheduler: `GET /v1/tenants/demo-salon/professionals` returns a list (seeded data).
- WhatsApp Store: `GET /` on port 8000 renders the welcome page.
- Swagger docs load on `/docs` for both apps.

If you tell me which app you’d like to focus on (AI Scheduler only vs. full WhatsApp Store), I can provide tailored sample flows or Postman collections.