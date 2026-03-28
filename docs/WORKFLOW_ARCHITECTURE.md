# WhatsApp & Workflow Architecture

## High-level flow (one incoming message)

1. **Triggers** – If the message matches a trigger (exact/prefix/regex), run the trigger action (static text, invoke_action by `action_id`, or menu node) and return the reply.
2. **Workflow** – If the session has `ctx.workflow_id`, call `WorkflowEngine.execute_next_step(tenant, phone, session, user_input)`. The engine advances the step, runs the step action, and returns the reply. Session is updated (step_idx, outputs, waiting_for_input).
3. **FSM (booking flow)** – If the session has `ctx.mode` (e.g. select_service, select_date), handle the input in the timeslot/booking FSM and return the reply.
4. **Menu** – Resolve current menu node from `session.last_node`. If the user’s input matches an option, go to the next node. If the next node is an action, call `_run_action(tenant, action_id, params, locale)` and return the reply.
5. **Intent (optional)** – If AI/NL is enabled and the input matches an intent, map to `action_id` and run `_run_action`.

Entry points:

- **Twilio:** `POST /integrations/twilio/whatsapp/webhook` → parse body → resolve tenant → run flow → return TwiML.
- **Meta:** `POST /integrations/meta/whatsapp/webhook` → parse payload → same flow → return JSON `{ "reply": "..." }`.
- **Bot API:** `POST /bot/whatsapp/next` (Super Admin) → same flow → return `{ "reply", "node" }`.

## Action registry

All WhatsApp/system actions are defined in **`app/services/whatsapp/action_registry.py`**:

- `ACTION_REGISTRY` – list of `{ id, label, module, requires_caps }`.
- `get_actions_for_tenant(tenant)` – filtered list for tenant (by modules/capabilities) plus workflow actions.
- `get_action_meta(action_id)` – metadata for capability checks.

Execution is in **`app/routers/whatsapp/routes.py`** (`_run_action`): workflow actions, booking FSM, core/store/salon handlers.

## Workflow engine

**`app/services/workflow_engine.py`**:

- `execute_next_step(tenant, phone, session, user_input)` – main entry; runs one step and returns the reply.
- `get_workflow` / `list_workflows` / `upsert_workflow` – CRUD for workflow definitions.
- Steps reference action codes (e.g. SHOW_SERVICES, SELECT_TIME, CONFIRM_BOOKING); the engine runs them and updates `ctx`.

Workflow definitions are stored per tenant; menu builder can add “Workflow: &lt;name&gt;” as an action that sets `ctx.workflow_id` and then each message is handled by `execute_next_step`.
