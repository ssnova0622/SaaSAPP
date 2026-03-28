### Plan: Add Staff navigation and CRUD in Admin UI

#### Goal
Expose full Staff management (list, create, edit, delete) in the React-based admin UI, leveraging the new backend endpoints under `Staff` tag. Ensure UX matches existing pages (MUI, React Router, React Query) and respects tenant context and JWT auth.

#### Assumptions
- Admin UI stack: React + React Router + MUI + React Query.
- Auth: `useAuth` provides access token and login state; token is sent via `Authorization: Bearer <JWT>` or cookie.
- Tenant: `useTenant` supplies current tenant string and setter.
- API base URL and helpers follow existing `src/api/*` patterns (e.g., `customers.ts`).

---

### 1) Wire navigation and routes
- Add a primary navigation item “Staff” in the app shell/sidebar.
  - Destination routes:
    - `/staff` → list page
    - `/staff/new` → create form
    - `/staff/:id` → edit form
- Route guard: reuse existing auth guard pattern (if present in `App.tsx` / `AppShell`).
- Only render Staff nav when authenticated.

Deliverables:
- Update `src/components/AppShell/AppShell.tsx` to include a `NavLink` to `/staff` with active highlighting.
- Update `src/App.tsx` to register the 3 routes.

---

### 2) API client for Staff
Create `src/api/staff.tsx` mirroring `customers.ts` conventions.
- Methods:
  - `listStaff({ tenant, search?, role?, active?, page=1, size=50 })` → `GET /v1/tenants/{tenant}/staff`
  - `createStaff({ tenant, payload })` → `POST /v1/tenants/{tenant}/staff`
  - `getStaff({ tenant, id })` → `GET /v1/tenants/{tenant}/staff/{id}`
  - `updateStaff({ tenant, id, payload })` → `PUT /v1/tenants/{tenant}/staff/{id}`
  - `deleteStaff({ tenant, id })` → `DELETE /v1/tenants/{tenant}/staff/{id}`
- Read tenant from `useTenant()` and token from `useAuth()` at call sites; attach headers `Authorization: Bearer <token>` if not using cookie auth.
- Uniform error handling (throw on non-2xx; surface message string).

Deliverables:
- `src/api/staff.tsx` exported functions and accompanying types.

---

### 3) Staff List page
Implement `src/pages/Staff/Index.tsx`:
- UI
  - Page header with title and a “New Staff” button linking to `/staff/new`.
  - Filters row:
    - Search text (debounced; maps to `search` query param)
    - Role select (free-text or populated from current list)
    - Active select: All/Active/Inactive
  - Data table (MUI `Table` or `DataGrid`) with columns:
    - Name, Role, Phone, Email, Skills (comma-separated chips), Active (chip/toggle), Actions
  - Pagination controls bound to `page` and `size` (URL query synced with React Router search params).
- Data
  - Use React Query to fetch from `listStaff` with `tenant` and current filters.
  - Show loading/error/empty states.
- Actions
  - Edit → navigate to `/staff/:id`
  - Delete → confirm dialog; call `deleteStaff`, then invalidate/refetch list.

Deliverables:
- `src/pages/Staff/Index.tsx` with full list, filters, pagination, and delete.

---

### 4) Staff Form (Create/Edit)
Implement shared component and pages:
- `src/pages/Staff/Form.tsx` (or `Edit.tsx` and `New.tsx` using shared inner form)
- Fields: `name` (required), `role` (required), `phone`, `email`, `skills` (chips or comma-separated input), `active` (checkbox)
- Validation: basic required fields and simple email/phone checks.
- Create flow (`/staff/new`): submit → `createStaff` → redirect to `/staff` and show success toast.
- Edit flow (`/staff/:id`): on mount, load `getStaff`; submit → `updateStaff`; redirect back to list with success toast.
- Disable buttons during requests; surface server validation errors inline.

Deliverables:
- `src/pages/Staff/New.tsx` and `src/pages/Staff/Edit.tsx` (or unified `Form.tsx`) wired to routes.

---

### 5) Hook integration and state
- `useTenant`: ensure tenant must be selected; if absent, show a message or redirect to tenant picker (consistent with app behavior).
- `useAuth`: ensure token presence; attach to all API requests or rely on cookie.
- React Query: set stable keys like `['staff', tenant, { search, role, active, page, size }]` and invalidate on mutations.

Deliverables:
- Consistent usage across pages; query invalidation after create/update/delete.

---

### 6) UX polish
- Toast notifications on success/error (use existing toast/snackbar pattern if present; otherwise MUI `Snackbar`/`Alert`).
- Confirm dialog for delete.
- Persist page size in local storage or URL if consistent with app patterns.
- Accessibility: labels for inputs, keyboard navigation for form and table.

---

### 7) Testing and verification
- Manual:
  - With backend running, authenticate, select a tenant, and verify:
    - List loads with correct totals and pagination.
    - Search/role/active filters propagate to API and update results.
    - Create/Edit/Delete work and reflect instantly in list.
  - Verify auth error behavior (401) and tenant mismatch handling.
- Optional automated:
  - Add lightweight React tests (render list with mocked API; form submit success path).
  - Extend `test_main.http` with Staff endpoints for quick backend checks.

---

### 8) Documentation
- Update project README/admin_ui section:
  - New navigation “Staff” and page routes.
  - Required envs (API base URL), auth notes, and tenant context.
  - Brief usage walkthrough and screenshots.

---

### File plan (expected additions/edits)
- Add: `src/api/staff.tsx`
- Add: `src/pages/Staff/Index.tsx`
- Add: `src/pages/Staff/New.tsx`
- Add: `src/pages/Staff/Edit.tsx` (or shared `Form.tsx`)
- Edit: `src/components/AppShell/AppShell.tsx` (navigation item)
- Edit: `src/App.tsx` (routes registration)

---

### Acceptance criteria
- Navigation shows “Staff,” routes resolve correctly, and pages are protected by auth.
- List page supports search, role, active filters and paginates, showing `{ items, total, page, size }` data.
- Create/Edit/Delete operations succeed against API and update UI state.
- Tenant context is respected in all requests.
- Error and loading states are user-friendly; success actions show feedback.

---

### Risks and mitigations
- Missing common API helper: replicate minimal fetch wrapper in `staff.tsx` following `customers.ts` style.
- JWT handling differences (cookie vs header): mirror `customers.ts` usage of headers/cookies.
- Role list population: if roles aren’t predefined, keep role filter as free-text input.

---

### Next steps
1) Confirm existing API helper and toast pattern to mirror. 2) Implement `src/api/staff.tsx`. 3) Add routes and pages; wire nav. 4) Test end-to-end with a demo tenant.