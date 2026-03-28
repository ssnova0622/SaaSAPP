### Assessment of the JS action
Your custom action looks structurally correct for Odoo OWL (v15+), but it can indeed trigger “Component is destroyed” if the action is fired from a component that is about to unmount and the promise resolution or a dialog-opening side-effect interacts with the destroyed component. A few small adjustments improve safety and integration with the action system.

### Issues and recommendations
1. Missing `async` + ensured resolution microtask
   - Returning `Promise.resolve()` is fine, but using an `async` function and awaiting the dialog creation aligns with other actions and ensures the microtask queue runs predictably.

2. Avoid using raw `action.context` keys without guards
   - If `record_id` or `model_name` is missing, the dialog init might throw, and if the parent component is already unmounting you’ll see lifecycle errors. Defensive defaults help.

3. Use `await env.services.dialog.add(...)`
   - In OWL, `dialog.add` returns a controller; awaiting a next tick (or simply awaiting a resolved promise) after adding the dialog helps decouple from the caller’s lifecycle.

4. Optional: Provide `onClose` or ensure the action completes immediately
   - If your action is only to open a dialog and exit, return `{ type: 'ir.actions.act_window_close' }` or just resolve immediately. The critical part is to not trigger navigation right away.

### Safer version
```javascript
/** @odoo-module **/
import { registry } from "@web/core/registry";
import { SapDialogContent } from "@ofh_web/dialog/sap_dialog_content";

const actionRegistry = registry.category("actions");

async function OpenSapDialogAction(env, action = {}) {
    const ctx = action.context || {};
    const recordId = ctx.record_id ?? null;
    const modelName = ctx.model_name ?? null;

    // Open the dialog; await a microtask to detach from caller’s lifecycle
    env.services.dialog.add(SapDialogContent, {
        title: "Select Action",
        recordId,
        modelName,
    });

    // Yield control to ensure the caller finishes before we proceed
    await Promise.resolve();

    // Optionally return a no-op action to signal completion to the action service
    return;
}

actionRegistry.add("ofh_sale_order_sap.open_sap_dialog", OpenSapDialogAction);
```

### Additional tips
- If this action is triggered right after a server call that causes a view reload, the parent component might be unmounted. In that case, triggering the dialog from a stable parent (e.g., via a bus/event) or ensuring the server action does not force an immediate reload helps.
- If the dialog itself performs `rpc` calls on mount, wrap async code with try/catch and guard against unmount using `onWillUnmount` or by checking an `isMounted` flag before setting state.

### Cross-check with your earlier issue
If this action is used in conjunction with a button that also navigates or returns an `act_url` (especially with `target: 'self'`), the combination can reproduce the “Component is destroyed” error. Ensure any navigation uses `target: 'new'` or happens after the dialog completes/closing.

If you share how this action is invoked (XML button/type, server action payload), I can validate the end-to-end flow and provide an exact fix.