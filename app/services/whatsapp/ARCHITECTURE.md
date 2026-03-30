# WhatsApp module — layout

## Principles

- **Tenant templates (primary)**: Prefer `wa_templates.wa(tenant, key, **vars)` for strings you want tenants to edit. Keys are seeded from `app/services/core/default_message_service.py` / templates storage; overrides merge in tenant settings.
- **Code constants (fallbacks)**: `helpers/constants.py` holds `MSG_*`, labels, FSM keywords, and formatted fallbacks when `get_message` / `wa()` is not used or returns empty. New features should either call `wa()` with a new template key **or** add a named constant—avoid inline user-facing strings in handlers.
- **Loose coupling**: Orchestration → pipeline stages → domain services (menu, FSM, workflow, dispatcher). No stage imports another stage.
- **Flexibility**: Workflows are tenant-defined in MongoDB. Action catalog in `usecases/action_registry.py` only lists *available step types*; composition is unrestricted.

### Pipeline stages (inbound)

`pipeline/inbound_pipeline.handle_incoming` runs stages **in this order**; the first stage that returns a `dict` wins:

1. `_stage_flow_ended_menu` (workflow just finished — show main menu before keyword triggers)  
2. `_stage_triggers`  
3. `_stage_store_waiting_input`  
4. `_stage_rebook_feedback`  
5. `_stage_exact_action_id`  
6. `_stage_run_fsm` (booking FSM)  
7. `_stage_active_workflow`  
8. `_stage_return_fsm`  
9. `_stage_menu_inactive_goodbye`  
10. `_stage_nl_intent_high_confidence`  
11. `_stage_no_menu_error`  
12. `_stage_menu_navigation`  

Inserting a stage changes precedence; add a test or comment when extending.

### NL booking action ids

`pipeline/inbound_pipeline.BOOKING_ACTION_IDS` controls which detected intents **do not** reset the session to the menu root (booking flows need sticky `ctx`). Each entry must normalize (via `normalize_booking_nl_action_id`) to a booking-related id in `app/helpers/constants_action.py`. Unit test: `test/unit/whatsapp/test_booking_action_ids.py`.

### Observability

Successful inbound handling logs at **INFO**: `whatsapp_inbound_resolved stage=<function_name> tenant=… phone_tail=… node=…`. Tier fallback uses `stage=_tier_nl_fallback`. Pair with your log stack filters / dashboards.

### Testing

Run WhatsApp unit tests (no DB) from repo root:

`saas_venv/bin/pytest test/unit/whatsapp/ -q`

(`pytest.ini` sets `pythonpath = .` so `app` imports resolve.)

Included under `test/unit/whatsapp/`:

- `test_usecases_utils.py`, `test_booking_helpers.py` (`booking_time_utils`) — pure parsers.
- `test_booking_action_ids.py` — NL booking id set vs `constants_action`.
- `test_inbound_pipeline_stages.py` — pipeline stage order vs `INBOUND_PIPELINE_STAGES`.
- `test_booking_fsm_integration.py` — in-memory session + mocks: menu exit, invalid service, service→date→staff→slots chain.

Expand with more paths (confirm, cancel FSM) when needed.

## Structure: keep or reshape?

**Verdict: the current folder layout is sound.** Subfolders match real boundaries (inbound pipeline, workflow engine, booking FSM, domain use cases, small helpers). You do *not* need one mega-module.

**When to avoid merging classes**

- **`CoreActions` → `SalonActions` / `StoreActions` / `AIActions`**: Inheritance (or a future shared *module* of plain functions) exists so booking/store/core steps share `flow_data`, pending keys, and validators without copy-paste. Folding everything into one class increases conflict surface and review cost.
- **`tier_services/*`**: Strategy pattern (basic / pro / enterprise) stays readable as separate small classes + factory.
- **Booking/cancel/reschedule**: Inbound path uses ``usecases/salon/booking_flow.py``, ``cancel_flow.py``, ``reschedule_flow.py``, and ``session_flow_service`` — not a second FSM stack.

**Low-cost cleanups (optional)**

- Prefer **module-level `try_*_run` functions** for tiny domains (clinic already does this) instead of a class that is only `@staticmethod`s.
- Static-only facades like **`WhatsAppMenuService`** could become module functions later (`render_menu`, `choice_to_index`); keep the class if you like a stable import path for HMAC + menu rendering.
- **`action_executor_service.run_action`**: Today starts `workflow.*` only; other menu wiring may live at the menu/workflow definition layer. If you add direct menu dispatch again, keep it in this thin service rather than bloating `pipeline/inbound_pipeline.py`.

## Entry points

| Import | Role |
|--------|------|
| `app.services.whatsapp.pipeline.inbound_pipeline.handle_incoming` | Single inbound message → `{reply, node}` (used from `app/routers/whatsapp/routes.py`) |
| `app.services.whatsapp.workflow.workflow_engine.WorkflowEngine` | Run/save workflows, menu item list |
| `app.services.whatsapp.action_executor.execute_run` | One workflow step → first matching use-case `try_*_run` |
| `app.services.whatsapp.action_executor_service.run_action` | Starts `workflow.<id>` sessions (normalize phone, first step) |

## Folders / files

| Path | Responsibility |
|------|----------------|
| `wa_templates.py` | Resolve `wa_*` / shared template keys |
| `helpers/constants.py` | WhatsApp `MSG_*`, FSM keywords, fallbacks (pair with `wa()` where possible) |
| `pipeline/inbound_pipeline.py` | Ordered stages for inbound handling; tuple ``INBOUND_PIPELINE_STAGES`` (asserted in tests) |
| `workflow/` | Workflow CRUD + step execution |
| `action_support.py` | Shared logging + `await_if_needed` / `try_run_chain` (loose coupling between use cases) |
| `action_executor.py` | Ordered `try_*_run` dispatch for workflow steps |
| `ADDING_WORKFLOW_ACTIONS.md` | Checklist for new workflow action codes |
| `usecases/` | Step handlers (core, salon, clinic, store, ai) + action catalog |
| `menu_tree_service.py` | Published menu tree navigation |
| `usecases/salon/booking_flow.py` | Salon booking: `get_available_slots`, `list_professionals`, `_finalize_booking`, `handle_timeslot_fsm`; re-exports `start_timeslot_flow` |
| `usecases/salon/booking_timeslot_start.py` | `start_timeslot_flow` — first screen / continuation; lazy-imports `booking_flow` for slots and professional listing |
| `usecases/salon/booking_fsm_modes.py` | `BOOKING_FSM_MODES_KEEP_CTX` — modes that must not reset ctx in `start_timeslot_flow` (asserted vs handlers in tests) |
| `usecases/salon/booking_ai_gate.py` | `is_ai_enabled_in_flow` — tier gate without depending on `booking_flow` |
| `usecases/salon/booking_fsm_handlers.py` | FSM mode dispatch (`dispatch_booking_fsm_mode`, `handle_fsm_back`; re-exports `is_ai_enabled_in_flow` from `booking_ai_gate`) |
| `usecases/salon/booking_time_utils.py` | Pure time parsing, slot distance, 12h display |
| `usecases/salon/cancel_flow.py` | Cancel: workflow phases + session FSM (`handle_cancel_fsm`) |
| `usecases/salon/reschedule_flow.py` | Reschedule: workflow phases + session FSM; hands off to `booking_flow` after confirm |
| `usecases/salon/booking_ctx_utils.py` | Pure helpers: sync ``ctx`` from ``flow_data``, clear stale date/slot keys on reschedule handoff |
| `action_executor_service.py` | Orchestrates menu → `CoreActions`, `StoreActions`, `SalonActions` + workflows |
| `usecases/core/core_actions.py` | Workflow steps + `CoreActions` menu (`open_ticket`, `show_offers`, `submit_feedback`, …) |
| `usecases/core/feedback_messaging.py` | Persist feedback → `customer_feedback` collection |
| `usecases/store/store_actions.py` | `StoreActions`: store workflow + catalog / order menu text |
| `usecases/clinic/clinic_actions.py` | `try_clinic_run` / `try_clinic_input` — list doctors / check doctor → `SalonActions.run_show_professionals` |
| `usecases/salon/salon_actions.py` | `SalonActions`: booking workflow + slots + cancel / reschedule / AI staff menu |
| `usecases/ai/ai_actions.py` | `AIActions`: placeholder workflow hooks |
| `workflow/workflow_step_policy.py` | Steps that re-run on same index after text input (prompt → result) |
| `session_flow_service.py` | Session read/write |

## Adding a message

1. **Editable copy:** Add a `wa_*` seed in `default_message_service` (or your template seed path), then call `wa(tenant, "wa_your_key", ...)`.  
2. **Fixed / structural copy:** Add `MSG_*` in `helpers/constants.py` and import as `WMSG` in the handler.  
3. Tenants customize `wa_*` keys via Message Templates admin / API; constant-only strings are not per-tenant unless you later add a matching `wa` key and switch the code path.
