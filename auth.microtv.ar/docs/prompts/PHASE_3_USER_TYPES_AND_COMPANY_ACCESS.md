# Phase 3 — User Types, Company Access Model & Role Seeding

## Context

The registration and email-verification flow (Phase 2) is complete and working in production.

The current problem: every user who completes the registration flow arrives at an account with zero
memberships, causing a 403 on login. The platform must distinguish two types of users from
registration, assign memberships automatically where appropriate, and allow Company Admins to
grant access to their companies.

This prompt covers work in **two repositories**: `auth.microtv.ar` (backend) and `saas-microtv.ar`
(frontend). No new repos are created in this phase.

---

## Design Decisions (locked, do not revisit)

1. **`user_type`** field on `User` model: `customer | company_employee | platform_admin`.
2. **`companies`** table owned by the identity service. `company_id` is the alphanumeric primary key
   used as `tenant_id` in `memberships`.
3. **After email verification**:
   - `customer` → membership auto-created: `(tenant_type="customer", tenant_id="platform")` + role `passenger_user`.
   - `company_employee` → no membership created. Account becomes `active` but access-pending.
4. **Login** for `company_employee` with 0 memberships returns HTTP 200 with
   `{ "access_pending": true }` — not a 403.
5. A `company_employee` with N ≥ 1 memberships uses the existing `select-context` flow unchanged.
6. `company_admin` role is assigned to a user by a `platform_admin` only (no self-service).
7. `company_admin` can grant / revoke `company_employee` access within companies they administer.
8. `platform_admin` is created exclusively via a CLI command — no HTTP endpoint.
9. Roles are database rows, not hardcoded strings. They must be seeded by a migration or seed script.
10. The tab "Cliente / Empresa" in the Login form changes only the link at the bottom (register route).
    Authentication logic is identical for both types.
11. `ContextSelect` already auto-selects if the user has exactly 1 membership — do not change that behaviour.
12. The `companies` table stores only identity-level data (id, name, logo). Operational data lives in
    `entities.microtv.ar`.

---

## 1. Backend — `auth.microtv.ar/backend/`

### 1.1 New model: `Company`

File: `src/models/company.py`

```python
class Company(Base):
    __tablename__ = "companies"

    company_id: Mapped[str]          # alphanumeric PK, e.g. "VIA", "FLECHA" — max 20 chars
    company_name: Mapped[str]        # display name
    logo_url: Mapped[str | None]     # nullable — URL to the company logo image
    status: Mapped[str]              # "active" | "suspended" — default "active"
    created_at: Mapped[datetime]
```

- `company_id` is `String(20)`, primary key, NOT a UUID. It is set explicitly by platform admins.
- Index on `status`.
- Export from `src/models/__init__.py`.

### 1.2 Update model: `User`

File: `src/models/user.py`

Add one field:

```python
user_type: Mapped[str]  # "customer" | "company_employee" | "platform_admin"
                        # server_default = "customer"
```

Column type: `String(30)`, non-nullable, server default `"customer"`.

### 1.3 Alembic migration

File: `migrations/versions/20260308_0005_add_user_type_and_companies.py`

- `down_revision = "20260308_0004"`
- `upgrade()`:
  1. Create table `companies`:
     - `company_id VARCHAR(20) PRIMARY KEY`
     - `company_name VARCHAR(255) NOT NULL`
     - `logo_url VARCHAR(512) NULL`
     - `status VARCHAR(20) NOT NULL DEFAULT 'active'`
     - `created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`
  2. Add column `user_type VARCHAR(30) NOT NULL DEFAULT 'customer'` to `users`.
- `downgrade()`: reverses the above in order.

### 1.4 Role seed migration

File: `migrations/versions/20260308_0006_seed_roles.py`

- `down_revision = "20260308_0005"`
- `upgrade()`: insert four rows into `roles` using `op.bulk_insert` (skip if already exists using
  `INSERT ... ON CONFLICT DO NOTHING`):
  - `passenger_user`
  - `company_operator`
  - `company_admin`
  - `platform_admin`
- `downgrade()`: delete those four role names from `roles`.

### 1.5 Update `AuthService`

File: `src/services/auth_service.py`

**`register_user()` — add `user_type` parameter**

```python
def register_user(self, display_name: str, email: str, password: str, user_type: str = "customer") -> User:
```

- Validate `user_type` is one of `{"customer", "company_employee"}`. Raise `ValueError` if not.
- Pass `user_type` to the `User` constructor.

**`verify_email_token()` — auto-assign membership for customers**

After setting `user.status = "active"` and `user.email_verified = True`, check `user.user_type`:

```python
if user.user_type == "customer":
    # 1. Look up the role row for "passenger_user"
    role = self.session.scalar(select(Role).where(Role.role_name == "passenger_user"))
    if role is None:
        raise RuntimeError("Role 'passenger_user' not seeded.")
    # 2. Create membership
    membership = Membership(
        user_id=user.user_id,
        tenant_type="customer",
        tenant_id="platform",
    )
    self.session.add(membership)
    self.session.flush()  # get membership_id
    # 3. Create role assignment
    self.session.add(RoleAssignment(
        membership_id=membership.membership_id,
        role_id=role.role_id,
    ))
```

Commit once at the end. `company_employee` gets no membership here.

**`login` flow — new method `get_login_response()`**

Replace the inline membership-check logic in `api/auth.py` (and in `verify-email`) with:

```python
def get_login_response(self, user: User) -> dict[str, Any]:
    """
    Returns the appropriate login payload dict for a user.
    Possible shapes:
      - TokenResponse dict (single membership)
      - LoginTicketResponse dict (multiple memberships)
      - {"access_pending": True, "user_type": user.user_type} (0 memberships, company_employee)
    Raises ValueError if a customer has 0 memberships (data integrity error — should not happen).
    """
    memberships = get_user_memberships(self.session, user.user_id)

    if len(memberships) == 0:
        if user.user_type == "company_employee":
            return {"access_pending": True, "user_type": "company_employee"}
        # customer with 0 memberships = data integrity problem
        raise ValueError("User has no valid memberships.")

    if len(memberships) == 1:
        return self.issue_tokens(user, memberships[0])

    return {
        "login_ticket": self.issue_login_ticket(user),
        "memberships": memberships,
        "requires_context_selection": True,
    }
```

**New method: `grant_company_access()`**

```python
def grant_company_access(
    self,
    granting_admin_user_id: str,
    target_user_id: str,
    company_id: str,
) -> Membership:
    """
    Grants company_operator access for target_user in company_id.
    Caller must have company_admin role in that company.
    Raises ValueError on any violation.
    """
```

Steps:
1. Verify `company_id` exists in `companies` and is `status="active"`.
2. Verify the granting admin has an active membership with `tenant_type="company"`,
   `tenant_id=company_id`, and role `company_admin`.
3. Verify `target_user` exists and has `user_type="company_employee"`.
4. Check no existing membership for target in that company (idempotency — if already exists, raise
   `ValueError("User already has access to this company.")`).
5. Create `Membership(user_id=target_user_id, tenant_type="company", tenant_id=company_id)`.
6. Assign role `company_operator` (look up by name).
7. Commit and return the new `Membership`.

**New method: `revoke_company_access()`**

```python
def revoke_company_access(
    self,
    granting_admin_user_id: str,
    target_user_id: str,
    company_id: str,
) -> None:
```

Steps:
1. Verify caller has `company_admin` in that company (same as above).
2. Find the membership for `target_user_id` in `company_id`.
3. Delete all `RoleAssignment` rows for that `membership_id`.
4. Delete the `Membership` row.
5. Commit.

### 1.6 Update schemas

File: `src/schemas/auth.py`

**Update `RegisterRequest`** — add `user_type` field:

```python
user_type: str = "customer"

@field_validator("user_type")
@classmethod
def validate_user_type(cls, v: str) -> str:
    if v not in {"customer", "company_employee"}:
        raise ValueError("user_type must be 'customer' or 'company_employee'.")
    return v
```

**New schema `AccessPendingResponse`**:

```python
class AccessPendingResponse(BaseModel):
    access_pending: bool = True
    user_type: str
```

**New schemas for company member management**:

```python
class GrantAccessRequest(BaseModel):
    user_email: str  # look up target by email

class MemberResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    membership_id: str
    roles: list[str]
```

Export all new schemas from `src/schemas/__init__.py`.

**Update the `MembershipOption` schema** to include optional company metadata:

```python
class MembershipOption(BaseModel):
    membership_id: str
    tenant_type: str
    tenant_id: str
    roles: list[str]
    company_name: str | None = None   # populated when tenant_type == "company"
    company_logo_url: str | None = None
```

### 1.7 Update `get_user_memberships()` to enrich company memberships

In `auth_service.py`, after building `memberships_with_roles`, for memberships where
`tenant_type == "company"`, query `companies` and attach `company_name` and `logo_url` (or `None`
if the company row is not found).

### 1.8 Update API endpoints

File: `src/api/auth.py`

**`POST /v1/auth/login`** — change response model and logic:

```python
@router.post("/login", response_model=TokenResponse | LoginTicketResponse | AccessPendingResponse)
```

Replace the inline 403 block with a call to `auth_service.get_login_response(user)`. Map
`ValueError` from that call to 403 (for the customer-with-no-memberships data integrity case only).

**`POST /v1/auth/verify-email`** — change response model:

```python
@router.post("/verify-email", response_model=TokenResponse | LoginTicketResponse | AccessPendingResponse)
```

After `auth_service.verify_email_token(token)` returns the user, call
`auth_service.get_login_response(user)` instead of the inline membership check.

**`POST /v1/auth/register`** — pass `user_type` through:

```python
user = auth_service.register_user(
    display_name=payload.display_name,
    email=payload.email,
    password=payload.password,
    user_type=payload.user_type,
)
```

**New router: `src/api/companies.py`**

```python
router = APIRouter(prefix="/v1/companies", tags=["companies"])
```

Endpoints (all require a valid `Authorization: Bearer` token of a user with `company_admin` role
in the relevant company):

- `GET  /v1/companies/mine`
  Returns the list of companies where the caller has `company_admin` role.
  Response: `list[CompanyResponse]` where `CompanyResponse = { company_id, company_name, logo_url, status }`.

- `GET  /v1/companies/{company_id}/members`
  Returns all members of that company.
  Response: `list[MemberResponse]`.
  Authorization: caller must be `company_admin` of `company_id`.

- `POST /v1/companies/{company_id}/members`
  Body: `GrantAccessRequest { user_email }`.
  Calls `auth_service.grant_company_access()`.
  Response: `MemberResponse` (201).
  Authorization: caller must be `company_admin` of `company_id`.

- `DELETE /v1/companies/{company_id}/members/{user_id}`
  Calls `auth_service.revoke_company_access()`.
  Response: HTTP 204 No Content.
  Authorization: caller must be `company_admin` of `company_id`.

**Token validation for company endpoints**: create a dependency
`require_company_admin(company_id: str, token: str = Depends(oauth2_scheme))` that:
1. Decodes the `access_token` JWT.
2. Checks that `active_membership.tenant_type == "company"`, `active_membership.tenant_id == company_id`,
   and `"company_admin" in active_membership.roles`.
3. Returns the `user_id` (subject claim).

Register `companies.router` in `src/main.py`.

### 1.9 CLI command: `create_admin`

File: `src/cli.py` (new file)

```bash
python -m src.cli create_admin --email=admin@microtv.ar --display-name="MicroTV Admin"
```

- Reads `DATABASE_URL` from environment (same as the app).
- Creates a `User` with `user_type="platform_admin"`, `status="active"`, `email_verified=True`,
  random secure password printed **once** to stdout and not stored anywhere beyond the hash.
- Creates `Membership(tenant_type="platform", tenant_id="platform")`.
- Assigns role `platform_admin`.
- Prints a confirmation with the `user_id`.
- If the email already exists: print an error and exit 1.
- Uses `argparse`. No third-party CLI framework.

### 1.10 Tests

Update/add tests in `backend/tests/`:

- `test_register.py`: add `user_type="company_employee"` case — assert no membership is created on verify.
- `test_verify_email.py`: add case for customer — assert membership + role assignment created after verify.
- `test_company_access.py` (new):
  - Setup: create a company, a platform_admin, a company_admin (with membership), a company_employee.
  - `grant_company_access` happy path.
  - `grant_company_access` — caller not admin → ValueError.
  - `grant_company_access` — company not found → ValueError.
  - `grant_company_access` — target already has access → ValueError.
  - `revoke_company_access` happy path — membership + role_assignment deleted.
  - `GET /v1/companies/{company_id}/members` — returns correct list.
  - `POST /v1/companies/{company_id}/members` — 201 with member data.
  - `DELETE /v1/companies/{company_id}/members/{user_id}` — 204.
  - All endpoints — 403 when caller lacks `company_admin` role.

Update `conftest.py` fixtures:
- Add a `company` fixture that inserts a `Company` row.
- Add a helper `make_company_admin_token(user_id, company_id)` that creates a JWT manually
  with `company_admin` in `active_membership.roles`.

---

## 2. Frontend — `saas-microtv.ar/`

### 2.1 Types

File: `src/types/auth.ts`

Add to `RegisterRequest`:

```typescript
export interface RegisterRequest {
  display_name: string
  email: string
  password: string
  recaptcha_token: string
  user_type: 'customer' | 'company_employee'   // ADD THIS
}
```

Add new type:

```typescript
export interface AccessPendingResponse {
  access_pending: true
  user_type: string
}
```

File: `src/types/membership.ts`

Add optional company fields to `MembershipOption`:

```typescript
export interface MembershipOption {
  membership_id: string
  tenant_type: string
  tenant_id: string
  roles: string[]
  company_name?: string        // ADD — populated for tenant_type="company"
  company_logo_url?: string    // ADD
}
```

### 2.2 `lib/auth.ts`

Update `LoginApiResponse` union type to include `AccessPendingResponse`.

Update `verifyEmail()` return type to `LoginApiResponse | AccessPendingResponse`.

Update `login()` return type to `LoginApiResponse | AccessPendingResponse`.

In both `login()` and `verifyEmail()`, after receiving the API response:
- If `response.data.access_pending === true` → return the `AccessPendingResponse` as-is (do not hydrate stores).
- Existing paths unchanged.

Add new company management functions:

```typescript
export async function getMyCompanies(): Promise<CompanyInfo[]>
// GET /v1/companies/mine

export async function getCompanyMembers(companyId: string): Promise<MemberInfo[]>
// GET /v1/companies/{companyId}/members

export async function grantAccess(companyId: string, userEmail: string): Promise<MemberInfo>
// POST /v1/companies/{companyId}/members

export async function revokeAccess(companyId: string, userId: string): Promise<void>
// DELETE /v1/companies/{companyId}/members/{userId}
```

Add new types to `src/types/company.ts` (new file):

```typescript
export interface CompanyInfo {
  company_id: string
  company_name: string
  logo_url: string | null
  status: string
}

export interface MemberInfo {
  user_id: string
  email: string
  display_name: string
  membership_id: string
  roles: string[]
}
```

### 2.3 Routes: two registration paths

File: `src/App.tsx`

Replace the single `/register` route with two routes:

```tsx
<Route path="/register/customer" element={<Suspense fallback={<PageLoader />}><RegisterPage userType="customer" /></Suspense>} />
<Route path="/register/company" element={<Suspense fallback={<PageLoader />}><RegisterPage userType="company_employee" /></Suspense>} />
```

Keep `/register` as a redirect to `/register/customer` for backward compatibility.

### 2.4 `pages/Register.tsx`

Accept a `userType: 'customer' | 'company_employee'` prop.

Pass it as `user_type` in the `register()` call. No UI change — the form is identical for both.

Update the "Ya tenés cuenta" link to use `Link` to `/login` (unchanged).

### 2.5 `components/auth/LoginForm.tsx`

The `userType` state already exists. Use it to change the registration link text and target:

```tsx
const registerHref = userType === 'empresa' ? '/register/company' : '/register/customer'
const registerLabel = userType === 'empresa' ? '¿No tenés cuenta empresa? Registrate' : '¿No tenés cuenta? Registrate'
```

Replace the static link at the bottom with these dynamic values.

### 2.6 `pages/Login.tsx` — handle `access_pending` response

After a successful login call, check the response:

```typescript
if ('access_pending' in result && result.access_pending) {
  navigate('/access-pending', { replace: true })
  return
}
```

Same check in `pages/VerifyEmail.tsx` (after the `verifyEmail()` call succeeds).

### 2.7 New page: `pages/AccessPending.tsx`

Route: `/access-pending` (public).

Content:
- Heading: "Cuenta activa — acceso pendiente"
- Body: "Tu cuenta está verificada. Un administrador de empresa debe habilitarte el acceso.
  Una vez habilitado, podrás iniciar sesión y ver las empresas disponibles desde el dashboard."
- Button: "Volver al inicio de sesión" → navigates to `/login`.
- No API calls. Pure informational screen.

Register the route in `App.tsx` (public, no auth required).

### 2.8 `pages/ContextSelect.tsx` — enrich membership cards with company data

The `MembershipOption` type now carries optional `company_name` and `company_logo_url`. Update
`MembershipCard` to show the company logo (as an `<img>` with `alt=company_name`) if available,
falling back to the current text-based rendering.

File: `src/components/auth/MembershipCard.tsx`

Add an optional `<img>` at the top of the card:

```tsx
{membership.company_logo_url && (
  <img
    src={membership.company_logo_url}
    alt={membership.company_name ?? membership.tenant_id}
    className="h-10 object-contain mb-2"
  />
)}
```

### 2.9 New page: `pages/dashboard/CompanyAdmin.tsx`

Route: `/dashboard/admin/company` (protected, requires `company_admin` role).

Features:
- Loads the list of companies where the user is `company_admin` using `getMyCompanies()`.
- If managing only 1 company, opens that company's member list directly.
- If managing N > 1, shows a company selector first.
- Per-company member list:
  - Table: `display_name`, `email`, `roles`, action "Revocar acceso" (DELETE button).
  - Form at the top: email input + "Otorgar acceso" button (calls `grantAccess()`).
  - Inline success/error feedback on each operation.
  - On 404 from grant: "No se encontró un usuario con ese email registrado como usuario empresa."
  - On 409/422 from grant: show backend message.

Register the route in `App.tsx` inside `ProtectedRoute` with `requireContext={true}`.

Add a navigation link to this page in the Dashboard sidebar/menu for users with `company_admin`
role (check `activeMembership.roles.includes('company_admin')`).

### 2.10 Tests

- `tests/unit/register-flow.test.tsx`:
  - Add: `userType="company_employee"` — assert `user_type: "company_employee"` sent in request body.
  - Add: `userType="customer"` — assert `user_type: "customer"` sent in request body.

- `tests/unit/access-pending.test.tsx` (new):
  - Login returns `access_pending: true` → navigates to `/access-pending`.
  - VerifyEmail returns `access_pending: true` → navigates to `/access-pending`.
  - AccessPending page renders correctly.
  - "Volver al inicio" button navigates to `/login`.

- `tests/unit/company-admin.test.tsx` (new):
  - Renders member list from mock `getMyCompanies()` + `getCompanyMembers()`.
  - Grant access — success → member appears in list.
  - Grant access — 404 → shows "no se encontró usuario" error.
  - Revoke access — calls `revokeAccess()` with correct args, member removed from list.

---

## 3. Documentation updates

After implementation is complete, update the following files:

- `auth.microtv.ar/docs/API_SPEC.md`: add `GET/POST/DELETE /v1/companies/*` endpoints.
- `auth.microtv.ar/docs/DOMAIN_MODEL.md`: add `Company` entity; update `User` with `user_type`.
- `saas-microtv.ar/docs/ARCHITECTURE.md`: add `/access-pending`, `/register/customer`,
  `/register/company`, `/dashboard/admin/company` to route table; update auth flow diagram.

---

## 4. Migrations execution order on server

```
alembic upgrade 20260308_0005  # adds companies table + user_type column
alembic upgrade 20260308_0006  # seeds roles
```

These must run before deploying the new application code.

---

## 5. Commit plan

After all tests pass:

**`auth.microtv.ar`**:
```
feat(auth): add user types, company access model, and company admin endpoints
```

**`saas-microtv.ar`**:
```
feat(saas): add company/customer registration paths, access-pending state, and company admin panel
```

---

## Out of scope for this phase

- `admin.microtv.ar` — Master Admin panel — separate phase.
- `company_admin` assignment by `platform_admin` — part of the admin panel phase.
- Company SSO / enterprise login.
- Billing context (`tenant_type="billing"`).
