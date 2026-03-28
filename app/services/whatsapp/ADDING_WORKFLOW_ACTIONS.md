# Adding a new WhatsApp workflow action

Keep new logic **loosely coupled**: one module owns the step; the engine only calls `execute_run`.

## 1. Register the action (admin dropdown + constants)

1. Add a constant in `app/helpers/constants_action.py` (lowercase snake_case value).
2. Add a row in `app/services/whatsapp/usecases/action_registry.py` (`DispatcherActionDef`).
3. If the step collects free text or a list reply, add the id to `_TEXT_INPUT_ACTION_IDS` when you want the UI to mark `input_required`.

## 2. Policy (run-only vs legacy)

- **Run-only + `flow_data`** (recommended): add the normalized code to  
  `WORKFLOW_RUN_ONLY_VIA_FLOW_DATA_INPUT` in `workflow/workflow_step_policy.py`.  
  The engine stores the user message under `{action}_user_input_pending`; your handler reads it and writes `{action}_user_input` via `CoreActions._flow_commit_user_reply` (or the same pattern).

## 3. Implement the handler module

**Standard `try_*_run` signature:**

```python
async def try_my_module_run(
    action_code: str,
    tenant: str,
    phone: str,
    session: dict,
    step: WorkflowStep,
) -> tuple[bool, str | None]:
    ...
```

- Return `(False, None)` if this module does not handle `action_code`.
- Return `(True, message)` when you handled the step (`message` is user-visible text, or `None` to auto-advance quietly).

Use:

- `CoreActions._workflow_pending_persist_keys(step)` for pending/persist keys.
- `run_handler_and_await(...)` from `app.services.whatsapp.action_support` when calling a sync/async handler map.

## 4. Wire the dispatcher chain

Append your `try_*_run` in **`app/services/whatsapp/action_executor.py`** inside the `runners` tuple  
(order matters: first match wins).

## 5. Logging

Use `get_action_logger("your_component")` from `app.services.whatsapp.action_support` for consistent log names under `app.services.whatsapp.*`.

## 6. Tests

Add or extend tests that call `WorkflowEngine.execute_next_step` / `execute_run` with a session containing `ctx.workflow_id` and the right `step_idx`.
