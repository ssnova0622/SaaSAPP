### Interpreting what you’re seeing
You’re comparing two different RPC calls and their raw responses, and also looking at the WSGI server’s `execute()` loop that streams bytes back to the client. The difference in the response bodies you pasted is expected because they’re different endpoints/methods, not because of a transport problem.

- Clicking a button in the same module that operates on `ofh.sale.order.sap` returns a recordset representation (e.g., `"ofh.sale.order.sap(205080,)"`). That’s the method’s result, not an error.
- Clicking a button in another module which, as part of its flow, triggers reading UI config returns `{"default_maximize": false}` (from `ir.config_parameter.get_web_dialog_size_config`). That’s a different RPC endpoint with a different response payload, also not an error.

In both cases, the WSGI `write(data)` you’re looking at is simply streaming the JSON-RPC response bytes that the called method produced. The server is behaving normally.

### How this relates to the “Component is destroyed” issue
The discrepancy in payloads isn’t the cause. The "Component is destroyed" error occurs on the frontend when a view component is torn down while an async promise is still resolving (e.g., a list-view button returning an `act_url` with `target: 'self'`, which navigates away immediately). The backend responses you posted are both HTTP 200 and well-formed JSON — they don’t indicate a server-side error.

### What to do next
- For the download button in `ofh.export.request` that generates a presigned S3 URL, return the URL with `target: 'new'` so the list view isn’t destroyed while the Promise finishes:

```python
return {
    'name': _('Download File'),
    'type': 'ir.actions.act_url',
    'url': presigned_url,
    'target': 'new',
    'target_type': 'public',
}
```

- If you’re seeing the same frontend error when clicking other buttons (from a different module), identify which action they return. Any action that replaces the current page synchronously while an awaited RPC is still pending can trigger the same OWL error. Opening in a new tab (or deferring navigation until after the promise resolves) avoids it.

### If you want me to patch it for you
Tell me which exact button/view is still causing the error after applying `target: 'new'`, and I’ll point you to the file and exact change (or prepare the patch).