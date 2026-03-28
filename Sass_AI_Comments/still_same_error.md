I patched the array mutation bug in the Modules section, but your browser is still executing an older chunk (the error points to the line numbers from the previous version). Let’s clear that and double‑check the code path.

Quick steps:
1) Hard refresh the Admin UI tab
- On macOS: Cmd+Shift+R (Chrome/Edge) or Cmd+Option+R (Safari)
- On Windows: Ctrl+F5
- Or fully stop and re‑start Vite: `npm run dev`

2) Confirm the fixed code is running
- In DevTools → Sources, open `src/pages/Settings.tsx` around the “Modules (per tenant)” section.
- You should see `const curMods = Array.from(new Set((prev.modules || []).map(...)))` and no `.add(...)` calls on `curMods`/`curCaps`.

3) If you still get the error, there’s likely a second call site using `.add()`
- Please copy the top 2–3 lines of the error after the refresh (file/line). I’ll target that exact block.

What I changed already (recap):
- Replaced all `.add()` calls in `toggleModule()` and `toggleCap()` with array copies and `includes`/`filter`.
- Ensured uniqueness using `Array.from(new Set(...))` before we build the updated arrays.

Fallback quick patch (if you want me to force‑replace at runtime):
- I can also move the toggling logic into small helpers that always return new arrays, so even if a stale state shape sneaks in, we don’t call methods that don’t exist on arrays.

Let me know the new console frames if the hard refresh doesn’t help; I’ll patch the exact location within minutes.