### Short answer
No — these log lines are normal, successful RPC calls (HTTP 200) and a benign cron warning. They are not the cause of the earlier “UncaughtPromiseError: Component is destroyed”. Your earlier issue is a frontend lifecycle problem, not a backend error.

### What each group indicates
- `POST /web/dataset/call_button` and other `call_kw` 200s: expected Odoo web RPC traffic triggered by UI actions. If these were failing, you’d see 4xx/5xx and Python tracebacks.
- `[WEB_READ] ...` entries: custom info logs from your `ofh_base` module documenting data reads. All show successful fetches.
- `ir_cron: Skipping database ... modules to install/upgrade/remove.`: cron pausing because there’s a module in a non-stable state. This is common during development and unrelated to list-view button clicks or downloads.

### Why you still saw the frontend error
The web client error happens when a view component is destroyed while an async operation continues (e.g., returning an `act_url` with `target: 'self'` from a list view button). Changing your download action to open in a new tab (`target: 'new'`) avoids destroying the initiating component and should eliminate the error without affecting these server logs.