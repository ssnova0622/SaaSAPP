### Plan to fix: `'Professional' object has no attribute 'get'`

#### Summary of the problem
- The error indicates code is treating a `Professional` model instance like a dict and calling `.get(...)` on it.
- In the reviewed code, slot and professional handling already attempts dual support (object vs dict) using `getattr(..., default)` with a fallback that uses `s.get(...) if isinstance(s, dict)`. However, one remaining spot likely still assumes dict for a `Professional` or nested slot.
- The most probable sources are functions that iterate professionals/slots and access fields using `.get(...)` without first checking `isinstance(..., dict)`.

#### Where to look (high-signal areas)
- WhatsApp router functions that traverse professionals/slots:
  - `_list_slots_for_professional(tenant, professional)`
  - `_list_available_slots_for_first_professional(tenant)`
  - `_start_timeslot_flow(...)` and `_handle_timeslot_fsm(...)` (they already use `getattr` and guarded `.get`)
- AI router helpers (dual-path parsing):
  - `_list_available_slots_for_first_professional` (ai.py)
  - `_list_times_for_professional_label` (ai.py)
- Professionals/slots endpoints in `app/routers/slots.py` (already using Pydantic models; unlikely to be the cause during runtime in WhatsApp/AI flows).

#### Reproduction strategy
- Create a tenant with professionals where `Storage.get_professionals` returns model instances (most common) and invoke code paths that list slots:
  - Call `GET /v1/tenants/{t}/ai/recommend_slots` (hits `ai.py` helper code)
  - Simulate WhatsApp booking flow start that triggers `_start_timeslot_flow`.
- Observe stack trace to pinpoint the exact line where `.get` is invoked on `Professional`.

#### Likely root cause and fix approach
- A `Professional` (or its `Slot`) object is being treated as a dict in some branch that wasn’t guarded. The fix is to:
  - Replace direct `.get(...)` usage on possibly-object values with a guarded pattern:
    - Prefer `getattr(obj, "field", default)`
    - Only use `value.get("field")` when `isinstance(value, dict)`
- Ensure ALL locations that parse professional/slot structures follow this pattern.

#### Step-by-step plan
1) Add a minimal failing test (optional if quick manual reproduction is easier):
   - Arrange professionals via `Storage` so returned items are model objects.
   - Hit `GET /v1/tenants/{t}/ai/recommend_slots` and begin WhatsApp flow to capture errors.
2) Audit and patch the remaining spots:
   - Search in `app/routers` for patterns like `.get("name")`, `.get("slots")`, `.get("status")`, `.get("time")` used near professionals/slots.
   - For each, update to the guarded access pattern already used elsewhere in the repo.
3) Re-test: verify `recommend_slots` and WhatsApp timeslot flow both work without errors and return expected lists when professionals are objects.
4) Regression check for dict-shaped documents:
   - Ensure the dual handling still works if `Storage` ever returns dicts (dev fixtures or alternative stores).
5) Ship: Merge the patch.

#### Risk and mitigation
- Low risk: change is localized to attribute access. We will maintain the dict-compatible fallback to avoid breaking any code paths that still return raw dicts.

#### Acceptance criteria
- No `AttributeError: 'Professional' object has no attribute 'get'` occurs across AI recommend and WhatsApp booking flows.
- Slot/professional names/times render correctly for tenants using model objects.
- Existing unit/integration tests pass; add a small sanity check if available.
