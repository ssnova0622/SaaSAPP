I’ve hardened the Modules UI code further and normalized the loaded settings so we always work with plain string arrays. This removes any lingering cases where a non‑array (or proxied structure) would cause `push is not a function`.

What I just changed
- In `Settings.tsx`:
  - On load of tenant settings, I normalize `modules` and `capabilities` to arrays of lowercase strings before putting them in component state.
  - In `toggleModule()`, I now:
    - Coerce `prev.modules` and `prev.capabilities` to arrays defensively (if not arrays, use empty array).
    - Build new arrays via `Array.from(new Set(...))` and array spread, never calling Set methods.
    - Lower‑case the module id and capability ids consistently.
    - On enable: append module id (if missing) and default child capabilities (if missing), using array spread into a new unique array.
    - On disable: filter the module id and all child capabilities of that module.
  - All updates return `{ ...prev, modules, capabilities }` with new arrays.

Why the error happened
- Your browser was likely running a hot-reload mix of new and old compiled chunks, or `settings.modules` in the current state wasn’t an array (e.g., stale object from an earlier save). The new code now coerces inputs and works with fresh arrays, so `push` is always available.

Please try this to ensure you’re on the new code
1) Stop and restart the dev server, and hard refresh the browser:
   - Stop `npm run dev`, start it again; then press Cmd+Shift+R (macOS) or Ctrl+F5 (Windows).
2) Try toggling a module checkbox again in Settings → Modules (as Super Admin).
3) Click “Save Modules”, then reload; verify no errors.

If it still errors:
- Copy the first 2–3 frames of the new error (file + line), it should point to the new lines (~281–310 region) and I’ll patch that exact spot immediately.
- Also open DevTools → Network → `GET /v1/tenants/{tenant}` and confirm the JSON has `modules: [...]` and `capabilities: [...]` arrays (not objects). The code now enforces this on load, but a sanity check helps.

Next small UX polish (optional)
- I can add toasts on “Modules saved” and “Default bundle applied”, and disable buttons while saving to make it feel smoother. Let me know if you want me to add those.
