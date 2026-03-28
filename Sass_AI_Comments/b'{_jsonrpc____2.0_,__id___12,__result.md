### What these responses are
They’re raw JSON-RPC responses from Odoo backend calls and they look normal:
- `{"default_maximize": false}` is the result of `ir.config_parameter.get_web_dialog_size_config` — the client asks whether dialogs should open maximized. `false` is a valid, benign value.
- `"ofh.sale.order.sap(205080,)"` is the string representation of a recordset returned by some method (your log earlier shows `visualize_sap_order`). Odoo often returns recordset reprs in logs or certain RPC replies; this indicates the method completed and returned a record (ID 205080), not an error.

### Relation to the “Component is destroyed” error
These responses are successful results and not errors. They are unrelated to the UI lifecycle exception. The frontend error stems from navigating/replacing the page while a Promise is still resolving (e.g., a list button returning `act_url` with `target: 'self'`).

If you haven’t yet, change your download action to open in a new tab:

```python
return {
    'name': _('Download File'),
    'type': 'ir.actions.act_url',
    'url': presigned_url,
    'target': 'new',
    'target_type': 'public',
}
```

If you already applied this and the error persists, tell me exactly which button/view triggers it now, and I’ll inspect that path for the same pattern.