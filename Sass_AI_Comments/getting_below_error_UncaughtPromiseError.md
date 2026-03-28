### What the error means
The Odoo web client is telling you that an async operation (a Promise) tried to update a UI component that has already been destroyed/unmounted. In OWL/Odoo 15+ this often happens when:
- A button triggers an RPC/action that navigates away or opens a URL, and
- The current view/component is torn down before the Promise resolves, so when the Promise resolves it throws “Component is destroyed”.

Your stack trace points to a read/load sequence: `webRead → _loadRecords → _loadData → _updateConfig` — that’s the list view model reloading while the view component is being destroyed.

### Where it’s likely coming from in your code
You have a tree-view button added by `ofh_reporting` that returns a URL action:
- View: `odoo/addons/ofh_reporting/views/ofh_export_request.xml`
  - Button: `<button name="download_request_file" ... type="object"/>`
- Method: `odoo/addons/ofh_reporting/models/ofh_export_request.py` → `download_request_file()`
  - Returns an `ir.actions.act_url` with `target: 'self'` and `target_type: 'public'`.

When a list-view object button returns an URL action with `target: 'self'`, the browser navigates immediately (to the presigned S3 URL). The Odoo component that started the RPC is destroyed while its Promise is still resolving, which produces the UncaughtPromiseError you see.

### Minimal, safe fix
Open the presigned URL in a new tab instead of replacing the current Odoo view. That avoids destroying the initiating component before the Promise finishes.

Change the returned action to use `target: 'new'`:

```python
# odoo/addons/ofh_reporting/models/ofh_export_request.py
return {
    'name': _('Download File'),
    'type': 'ir.actions.act_url',
    'url': presigned_url,
    'target': 'new',           # open in new tab/window to avoid destroying the list component
    'target_type': 'public',
}
```

This is the least invasive change and is consistent with Odoo’s common pattern for file downloads initiated from list/tree buttons.

### Alternative approaches (if you prefer not to open a new tab)
- Keep `target: 'self'`, but return an intermediate action first (so the RPC completes without immediate navigation), then programmatically trigger the download on the client. This requires a small JS action or a controller + redirect, which is more work.
- Expose a server route (`/my/download/<id>`) that streams the file with proper headers and return `act_url` to that route (still using `target: 'new'` recommended). This keeps S3 details server-side and often feels cleaner.

### Quick checks to confirm
1. Click the “Uploaded File” button in the Export Request tree after switching `target` to `'new'`.
2. The file should open/download in a new tab without the console error.
3. Staying on the list view while the RPC resolves should eliminate the `Component is destroyed` error.

### Notes on visibility and safety
- Your button is already guarded with `invisible="export_type != 'ofh.audit.report' or not upload_file_name"`, so it only appears when a file is available.
- The method doesn’t mutate state, so opening in a new tab has no side effects on the list state.

### If the error still appears
If you still see the error after switching to `'new'`, please share:
- Exact user action sequence (which view/menu, what filter/sort, which button clicked).
- Whether any list auto-refresh or auto-redirect happens on click.
- Any custom JS in your modules that might be doing additional reads after the click (search for usages of `orm.webRead`, `onWillStart`, or any `await` in components attached to this view).

I can prepare a ready-to-apply patch for you once you confirm you’re fine with opening downloads in a new tab.