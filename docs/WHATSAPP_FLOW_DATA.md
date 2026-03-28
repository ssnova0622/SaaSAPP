# WhatsApp workflow: `flow_data` + action chain

**Module map & pipeline:** `app/services/whatsapp/ARCHITECTURE.md`  
**Public API:** `from app.services.whatsapp.api import handle_incoming, WorkflowEngine`

## Executor order

`action_executor.execute_run` / `process_input` tries in order:

1. **core** — `try_core_run` / `try_core_input` (`ASK_NAME`, `CONFIRM`, `END`, …)
2. **clinic** — `try_clinic_run` / `try_clinic_input` (`CLINIC.LIST_DOCTORS`, `CLINIC.CHECK_DOCTOR`)
3. **salon** — `try_salon_run` / `try_salon_input` (`SHOW_SERVICES`, `SELECT_DATE`, …)
4. **store** — `try_store_run` / `try_store_input` (extend when needed)
5. **ai** — `try_ai_run` / `try_ai_input` (extend when needed)
6. Then `ACTION:…` → dispatcher.

No global `register_run_handler` for these modules; each module owns its `try_*` API and internal handler maps.

## `flow_data`

`session["ctx"]["flow_data"]` grows across steps. Salon uses `_flow_patch`; core uses `get_flow_data` / validators in `core_actions.py`.

### Workflow user replies (run-only steps: core, salon, clinic, store, ai)

- **Pending** (one turn): `flow_data["{action}_user_input_pending"]` — set by `WorkflowEngine` when the user sends a message while `waiting_for_input`.
- **Committed** (audit / downstream): `flow_data["{action}_user_input"]` — e.g. `show_services_user_input` stores the chosen service name (or raw confirm text) after a successful step; see `workflow_step_policy.workflow_user_reply_*_key`.
