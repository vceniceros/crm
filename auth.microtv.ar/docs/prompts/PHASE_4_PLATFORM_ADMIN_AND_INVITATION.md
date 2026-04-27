# Phase 4 — Platform Admin Panel, Company CRUD & company_admin Invitation Flow

## Context

Phases 1–3 are complete and working in production:

- Phase 1: Core auth (models, JWT, login, logout, token refresh)
- Phase 2: Email verification
- Phase 3: User types (`customer` / `company_employee`), company access model, `company_admin`
  can grant / revoke employee access to their companies

Current gap: `company_admin` users exist in the role model but there is no way for a
`platform_admin` to create companies, assign `company_admin` to a company, or invite new users
directly into that role. Additionally, there is no administrative frontend for the platform team.

This phase introduces:

1. Admin API endpoints in `auth.microtv.ar` — company CRUD, `company_admin` assignment and
   invitation flow, invitation acceptance.
2. A new frontend repo `entities-microtv.ar` — the platform admin panel (React SPA).
3. Small additions to `saas-microtv.ar` — admin app tile + accept-invitation page.

This prompt covers work in **three repositories**:
`auth.microtv.ar`, `entities-microtv.ar` (new), `saas-microtv.ar`.

---

## Design Decisions (locked, do not revisit)

1. **`company_admin` is a role on a Membership**, not a `user_type`. `user_type` remains
   `company_employee` for all company users regardless of admin status. Revoking the role does not
   change `user_type`.

2. **Two paths for assigning `company_admin`** to a company:
   - **Caso A — existing user**: the email is already registered as `company_employee`.
     Assign `company_admin` role directly (create membership if needed, or add role to existing
     membership in the target company). Immediate effect, no email sent.
   - **Caso B — new user**: email is not registered. Create an `Invitation` record with a token
     and send an invitation email. The link goes to
     `saas-microtv.ar/accept-invitation?token=…`. The user fills in `display_name` + `password`,
     and the account is created as `company_employee` with `company_admin` role pre-assigned for
     the invited company. Auto-logged in after acceptance.

3. **Caso B is only available for unregistered emails.** If the email exists in the system,
   the invitation path is not used — Caso A is applied instead.

4. **Multi-empresa conflict**: if the target email is already `company_admin` of one or more
   other companies (but not the current one), `POST .../admins` returns 409 with
   `{ "detail": "existing_admin", "companies": [...] }`. The frontend shows a confirmation dialog:
   *"Este email ya es company_admin de: [Empresa X, Empresa Y]. ¿Agregar también como
   company_admin de [Nueva Empresa]?"*. On confirmation the client retries with `?force=true`.

5. **Revoking `company_admin`**: removes only the `company_admin` RoleAssignment from that
   membership. If the membership has no remaining RoleAssignments after removal, the membership
   itself is deleted. Other company memberships are not affected.

6. `entities-microtv.ar` — new repo. Same technology stack as `saas-microtv.ar`:
   React 18 + TypeScript + Vite + TailwindCSS + React Router v6 + Zustand + React Hook Form +
   Zod + Axios + Vitest. Own login page. Calls the same `auth.microtv.ar` API.

7. `platform_admin` logs into `entities-microtv.ar` directly via its own `/login` page.
   They can also access `saas-microtv.ar` but their primary tool is the entities panel.

8. `company_admin` users log into `saas-microtv.ar` as usual. They see a **"Panel Admin"** tile
   in the dashboard app grid (filtered by role) that links to `entities-microtv.ar`. They must
   log in separately there. (SSO token passthrough is a future phase.)

9. Authorization in `entities-microtv.ar`:
   - `platform_admin` context: sees and manages all companies.
   - `company_admin` context: sees only the companies they administer; cannot create companies or
     manage other company_admins.

10. Company CRUD lives in `auth.microtv.ar` (identity data only: id, name, logo, status).
    Operational data (routes, schedules, etc.) is Phase 5+.

11. Invitation tokens expire after **48 hours**. Expired invitations surface a 410 response.
    The admin panel allows resending (creates a new Invitation row, marks the old one `revoked`).

12. `entities-microtv.ar` does **not** use reCAPTCHA — it is an internal tool, not a public
    self-registration surface.

---

## 1. Backend — `auth.microtv.ar/backend/`

### 1.1 New model: `Invitation`

File: `src/models/invitation.py`

```python
class Invitation(Base):
    __tablename__ = "invitations"

    invitation_id: Mapped[str]             # UUID PK
    email: Mapped[str]                     # invited email address
    company_id: Mapped[str]                # FK → companies.company_id
    role: Mapped[str]                      # role to assign on acceptance ("company_admin")
    token: Mapped[str]                     # UUID, unique — used in the accept URL
    status: Mapped[str]                    # "pending" | "accepted" | "revoked" | "expired"
    invited_by: Mapped[str]                # FK → users.user_id (the platformadmin who sent it)
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]           # created_at + 48 hours
    accepted_at: Mapped[datetime | None]
```

- `token` column: unique index.
- `email` column: non-unique index.
- FK constraints on `company_id` → `companies.company_id` and `invited_by` → `users.user_id`.
- Export from `src/models/__init__.py`.

### 1.2 Alembic migration

File: `migrations/versions/20260308_0007_add_invitations.py`

- `down_revision = "20260308_0006"`
- `upgrade()`: create the `invitations` table with all columns above, FK constraints,
  and the two indexes.
- `downgrade()`: drop table `invitations`.

### 1.3 New schemas

File: `src/schemas/admin.py`

```python
class CreateCompanyRequest(BaseModel):
    company_id: str       # required; alphanumeric + hyphens, max 20 chars
    company_name: str
    logo_url: str | None = None

    @field_validator("company_id")
    @classmethod
    def validate_company_id(cls, v: str) -> str:
        if not re.match(r"^[A-Z0-9\-]{1,20}$", v.upper()):
            raise ValueError("company_id must be alphanumeric (A-Z, 0-9, hyphens), max 20 chars.")
        return v.upper()

class UpdateCompanyRequest(BaseModel):
    company_name: str | None = None
    logo_url: str | None = None

class AssignAdminRequest(BaseModel):
    user_email: str

class AssignAdminResponse(BaseModel):
    status: str                           # "assigned" | "invited"
    user: MemberResponse | None = None    # populated when status="assigned"
    invitation_id: str | None = None      # populated when status="invited"

class ConflictAdminResponse(BaseModel):
    detail: str                           # "existing_admin"
    companies: list[CompanyResponse]      # companies where user is already company_admin

class InvitationPreviewResponse(BaseModel):
    invitation_id: str
    email: str
    company_id: str
    company_name: str
    expires_at: datetime
    status: str

class AcceptInvitationRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=8)
```

Export all new schemas from `src/schemas/__init__.py`.

### 1.4 New service: `AdminService`

File: `src/services/admin_service.py`

Session-injected service. All write operations commit once at the end.

#### Company management

```python
def create_company(self, company_id: str, company_name: str, logo_url: str | None) -> Company:
    """Raises ValueError if company_id already exists."""

def list_companies(self) -> list[Company]:
    """Returns all companies ordered by company_name."""

def get_company(self, company_id: str) -> Company:
    """Raises 404 HTTPException if not found."""

def update_company(self, company_id: str, company_name: str | None, logo_url: str | None) -> Company:

def suspend_company(self, company_id: str) -> Company:
    """Sets status='suspended'."""

def reactivate_company(self, company_id: str) -> Company:
    """Sets status='active'."""
```

#### company_admin management

```python
def list_company_admins(self, company_id: str) -> list[dict]:
    """
    Returns all users who have membership in company_id with the company_admin role.
    Shape per item: { user_id, email, display_name, membership_id, roles }
    """

def assign_or_invite_company_admin(
    self,
    platform_admin_user_id: str,
    target_email: str,
    company_id: str,
    force: bool = False,
) -> dict:
    """
    Checks whether the email is registered:

    NOT registered:
      → Caso B: create Invitation(email, company_id, role="company_admin", token=uuid4(),
                expires_at=now()+48h, invited_by=platform_admin_user_id),
                send invitation email,
                return {"status": "invited", "invitation_id": str}.

    Registered as company_employee AND not yet company_admin anywhere:
      → Caso A: create/update membership + assign company_admin role,
                return {"status": "assigned", "user": MemberResponse}.

    Registered as company_employee AND already company_admin in OTHER companies, force=False:
      → raise ConflictError with list of existing companies. HTTP 409 in API layer.

    Registered as company_employee AND already company_admin in OTHER companies, force=True:
      → Caso A: assign company_admin to this company too,
                return {"status": "assigned", "user": MemberResponse}.

    Registered as company_employee AND already company_admin of THIS company:
      → raise ValueError("User is already company_admin of this company."). HTTP 409.

    Registered as customer or platform_admin:
      → raise ValueError("Incompatible user type."). HTTP 422.
    """

def revoke_company_admin(
    self,
    platform_admin_user_id: str,
    target_user_id: str,
    company_id: str,
) -> None:
    """
    Removes the company_admin RoleAssignment from the user's membership in company_id.
    If no other RoleAssignments remain on that membership, delete the membership too.
    Does NOT touch other company memberships.
    Raises ValueError if the user does not have company_admin in company_id.
    """
```

#### Invitation acceptance (Caso B)

```python
def get_invitation_by_token(self, token: str) -> Invitation:
    """
    Returns the Invitation.
    Raises 404 HTTPException if token not found.
    Raises 410 HTTPException if status != "pending" or expired.
    Also marks expired pending invitations as status="expired" on access.
    """

def accept_invitation(self, token: str, display_name: str, password: str) -> dict:
    """
    1. Calls get_invitation_by_token(token) — raises on invalid/expired.
    2. Creates User(email=invitation.email, display_name=display_name,
                    user_type="company_employee", status="active",
                    email_verified=True, password_hash=hash(password)).
    3. Creates Membership(user_id=user.user_id, tenant_type="company",
                          tenant_id=invitation.company_id).
    4. flush() to get membership_id.
    5. Assigns role company_admin via RoleAssignment.
    6. Sets invitation.status="accepted", invitation.accepted_at=now().
    7. Commits.
    8. Returns get_login_response(user) — will be a single-membership TokenResponse.
    """
```

#### Email sending

Add to the existing email service (or create `src/services/email_service.py` if it does not exist):

```python
def send_company_admin_invitation(
    email: str,
    company_name: str,
    platform_name: str,
    accept_url: str,        # f"{SAAS_BASE_URL}/accept-invitation?token={token}"
    expires_hours: int = 48,
) -> None:
```

The `SAAS_BASE_URL` is read from environment config (e.g. `SAAS_BASE_URL=https://saas.microtv.ar`).

### 1.5 New API router: `src/api/admin.py`

```python
router = APIRouter(prefix="/v1/admin", tags=["admin"])
```

**Dependency** `_require_platform_admin(token: str = Depends(oauth2_scheme)) -> str`:
1. Decode JWT.
2. Verify `"platform_admin" in active_membership.roles`.
3. Return `user_id` (sub claim).
4. Raise 403 on failure.

**Endpoints:**

```
GET    /v1/admin/companies
POST   /v1/admin/companies
GET    /v1/admin/companies/{company_id}
PATCH  /v1/admin/companies/{company_id}
POST   /v1/admin/companies/{company_id}/suspend
POST   /v1/admin/companies/{company_id}/reactivate

GET    /v1/admin/companies/{company_id}/admins
POST   /v1/admin/companies/{company_id}/admins          ?force=false
DELETE /v1/admin/companies/{company_id}/admins/{user_id}
```

`POST /v1/admin/companies/{company_id}/admins`:
- Body: `AssignAdminRequest { user_email }`.
- Query: `force: bool = False`.
- Returns 201 `AssignAdminResponse` on Caso A.
- Returns 202 `AssignAdminResponse` on Caso B.
- Returns 409 `ConflictAdminResponse` on multi-empresa conflict with `force=False`.
- Returns 409 plain `{ "detail": "..." }` if already admin of this company.
- Returns 422 `{ "detail": "..." }` if incompatible user type.

`DELETE /v1/admin/companies/{company_id}/admins/{user_id}`:
- Returns 204 No Content.
- 404 if user is not company_admin of this company.

All endpoints in this router return 403 if caller lacks `platform_admin` role.

### 1.6 New API router: `src/api/invitations.py`

```python
router = APIRouter(prefix="/v1/invitations", tags=["invitations"])
```

No authentication required (public endpoints).

```
GET  /v1/invitations/{token}
     → 200 InvitationPreviewResponse
     → 404 if token not found
     → 410 if expired / accepted / revoked

POST /v1/invitations/{token}/accept
     Body: AcceptInvitationRequest { display_name, password }
     → 200 TokenResponse  (single-membership auto-login)
     → 409 if email already registered (race condition guard)
     → 410 if invitation no longer valid
```

### 1.7 Update `src/main.py`

Register both new routers:

```python
from src.api.admin import router as admin_router
from src.api.invitations import router as invitations_router

app.include_router(admin_router)
app.include_router(invitations_router)
```

### 1.8 Tests

New file: `backend/tests/test_admin.py`

Service-level:
- `create_company` happy path — company created.
- `create_company` — duplicate company_id → ValueError.
- `assign_or_invite_company_admin` — email not registered → Invitation created,
  verify status="pending", expires_at ≈ now+48h.
- `assign_or_invite_company_admin` — existing company_employee, no admin role → assigned.
- `assign_or_invite_company_admin` — existing company_admin of other company, force=False
  → ConflictError with companies list.
- `assign_or_invite_company_admin` — same conflict, force=True → assigned.
- `assign_or_invite_company_admin` — already admin of this company → ValueError.
- `assign_or_invite_company_admin` — customer email → ValueError.
- `revoke_company_admin` happy path — role assignment deleted, membership deleted (no other roles).
- `revoke_company_admin` — membership kept when other role assignment exists.
- `accept_invitation` happy path — user created, membership created, role assigned,
  invitation marked accepted, tokens returned.
- `accept_invitation` — expired token → 410.
- `accept_invitation` — already accepted → 410.

API-level (`test_admin.py`):
- `POST /v1/admin/companies` — 201, company created.
- `POST /v1/admin/companies` — 403 when caller lacks platform_admin.
- `POST /v1/admin/companies/{id}/admins` — 202 for Caso B (invited).
- `POST /v1/admin/companies/{id}/admins` — 201 for Caso A (assigned).
- `POST /v1/admin/companies/{id}/admins` — 409 conflict, force=False.
- `POST /v1/admin/companies/{id}/admins?force=true` — 201 on forced assign.
- `DELETE /v1/admin/companies/{id}/admins/{uid}` — 204.
- `GET /v1/admin/companies/{id}/admins` — returns current list.

New file: `backend/tests/test_invitations.py`

- `GET /v1/invitations/{token}` — valid pending → 200 with company details.
- `GET /v1/invitations/{token}` — expired → 410.
- `GET /v1/invitations/{token}` — unknown token → 404.
- `POST /v1/invitations/{token}/accept` — creates user, membership, company_admin role,
  returns tokens.
- `POST /v1/invitations/{token}/accept` — already accepted → 410.

Update `conftest.py`:
- Add `invitation` fixture: inserts a pending `Invitation` row for a test email + TESTCO.

### 1.9 Documentation updates

- `docs/API_SPEC.md`: add `GET/POST/PATCH /v1/admin/companies/*` and
  `GET/POST /v1/admin/companies/{id}/admins/*` sections; add
  `GET/POST /v1/invitations/{token}` section.
- `docs/DOMAIN_MODEL.md`: add `Invitation` entity.

---

## 2. New repo: `entities-microtv.ar`

### 2.1 Scaffold

Bootstrap with `npm create vite@latest entities-microtv-ar -- --template react-ts`.

Exact same dependency set as `saas-microtv.ar`:
`react-router-dom`, `zustand`, `react-hook-form`, `@hookform/resolvers`, `zod`, `axios`,
`@tailwindcss/vite`, `vitest`, `@testing-library/react`, `@testing-library/user-event`, `jsdom`.

Directory structure:

```
src/
  assets/
  components/
    ui/           (Button, Input, Table, Badge, Modal, Spinner)
    layout/       (Sidebar, Topbar)
  config/
    env.ts        (VITE_AUTH_API_URL, VITE_APP_ENV)
  hooks/
    useAuth.ts
  layouts/
    AdminLayout.tsx     (sidebar + topbar, requires context)
    PublicLayout.tsx    (centered card, logo)
  lib/
    api.ts        (Axios instance + interceptors — identical pattern to saas)
    auth.ts       (login, logout, selectContext, refresh — same as saas)
    admin.ts      (company CRUD + admin management functions)
  pages/
    Login.tsx
    ContextSelect.tsx
    Dashboard.tsx           (redirect to /companies)
    companies/
      CompanyList.tsx
      CompanyCreate.tsx
      CompanyDetail.tsx
      CompanyEdit.tsx
      AdminList.tsx
      AssignAdminFlow.tsx   (modal component used inside AdminList)
  stores/
    authStore.ts            (same shape as saas)
    contextStore.ts         (same shape as saas)
  types/
    auth.ts       (TokenResponse, LoginTicketResponse, etc. — same as saas)
    company.ts    (CompanyInfo, AdminInfo, InvitationPreview, AssignAdminResponse)
  App.tsx
  main.tsx
deploy/
  entities-microtv.service   (systemd unit)
  nginx/
    entities.conf
```

### 2.2 Environment configuration

`src/config/env.ts`:

```typescript
import { z } from 'zod'

const envSchema = z.object({
  VITE_AUTH_API_URL: z.string().url(),
  VITE_APP_ENV: z.enum(['development', 'staging', 'production']).default('development'),
})

export const env = envSchema.parse(import.meta.env)
```

`.env.example`:
```
VITE_AUTH_API_URL=https://auth.microtv.ar
VITE_APP_ENV=production
```

### 2.3 Auth / stores

`src/stores/authStore.ts` and `src/stores/contextStore.ts` — copy the same implementation from
`saas-microtv.ar`, they are identical. Do not import across repos.

`src/lib/auth.ts` — identical implementation to `saas-microtv.ar/src/lib/auth.ts` except:
- Does not import or call reCAPTCHA.
- Does not export `register()` or `resendVerification()`.
- `login()` on `access_pending` response: returns `access_pending` object (same as saas);
  the entities login page shows the message
  *"Tu cuenta no tiene acceso a este panel."* instead of redirecting.

`src/lib/api.ts` — identical Axios instance + interceptors pattern as saas.

### 2.4 Route protection

`src/components/ProtectedRoute.tsx`:

```tsx
// requireRole: if provided, checks active_membership.roles.includes(requireRole)
interface Props {
  requireRole?: string
  children: React.ReactNode
}
```

- No `access_token` in store → redirect to `/login`.
- No active context (`hasContext` false) → redirect to `/context-select`.
- Role check fails → show 403 page ("No tenés acceso a esta sección.").

Route table in `src/App.tsx`:

```
/login                    — public
/context-select           — requires auth, no context required
/companies                — requires context
/companies/new            — requires context + platform_admin role
/companies/:id            — requires context
/companies/:id/edit       — requires context + platform_admin role
/companies/:id/admins     — requires context
*                         — redirect to /companies
```

### 2.5 Pages

#### `pages/Login.tsx`

- Email + password form. No reCAPTCHA. Same visual style as saas login.
- On `access_pending` response: show inline error
  *"Tu cuenta no tiene acceso a este panel."* (do not redirect).
- On success: navigate to `/companies`.

#### `pages/ContextSelect.tsx`

- Identical behavior to saas `ContextSelect.tsx`.
- Used when a `company_admin` with multiple company memberships logs in.

#### `pages/companies/CompanyList.tsx`

- Route: `/companies`.
- `GET /v1/admin/companies` (platform_admin) or
  `GET /v1/companies/mine` (company_admin — already implemented in Phase 3).
- Table columns: `Company ID`, `Nombre`, `Estado` (badge: active=green / suspended=gray),
  action `Ver detalle`.
- `platform_admin` only: "Nueva empresa" button → `/companies/new`.

#### `pages/companies/CompanyCreate.tsx`

- Route: `/companies/new` (platform_admin only).
- Form: `company_id` (uppercase, alphanumeric + hyphens, max 20), `company_name`,
  `logo_url` (optional, URL field).
- `POST /v1/admin/companies` → on 201: navigate to `/companies/{company_id}`.
- Inline validation using Zod + React Hook Form.
- On 409: show "Ya existe una empresa con ese ID."

#### `pages/companies/CompanyDetail.tsx`

- Route: `/companies/:id`.
- Shows: company_name, logo (if present), status badge, company_id.
- `platform_admin` only: "Editar" button (→ `/companies/:id/edit`),
  "Suspender" / "Reactivar" button.
- Tabs:
  - **Administradores**: renders `AdminList` component.
  - **Empleados** (read-only for Phase 4): list from
    `GET /v1/companies/{id}/members` (Phase 3 endpoint), showing all members with their roles.

#### `pages/companies/CompanyEdit.tsx`

- Route: `/companies/:id/edit` (platform_admin only).
- Pre-fills `company_name` and `logo_url` from the existing company.
- `PATCH /v1/admin/companies/{id}` → on success: navigate back to `/companies/{id}`.

#### `pages/companies/AdminList.tsx`

- Used inside `CompanyDetail` Administradores tab.
- `GET /v1/admin/companies/{id}/admins` → renders table.
- Table columns: `Nombre`, `Email`, action "Revocar admin" (`DELETE`, platform_admin only).
- "Agregar admin" button → opens `AssignAdminFlow` modal.

#### `pages/companies/AssignAdminFlow.tsx`

Modal component (or inline expandable form). Steps:

**Step 1 — Email input**

- Text input for email + "Verificar" button.
- On submit: `POST /v1/admin/companies/{id}/admins` with `{ user_email }`.

**Step 2 — Outcome handling**

| API response | UI shown |
|---|---|
| 201 `{ status: "assigned" }` | *"Acceso otorgado a [display_name]."* Refresh admin list. Close. |
| 202 `{ status: "invited" }` | *"Invitación enviada a [email]. El link expira en 48 horas."* Close. |
| 409 `{ detail: "existing_admin", companies: [...] }` | Warning card: *"Este email ya es company_admin de: [Empresa X, Empresa Y]. ¿Agregar también como company_admin de [Esta Empresa]?"* — Confirm / Cancel buttons. |
| Confirm (retry with `?force=true`) | 201 assigned → same as above. |
| 409 `already_admin` | *"Este usuario ya es company_admin de esta empresa."* |
| 422 incompatible type | *"Este email pertenece a un usuario de tipo cliente y no puede ser company_admin."* |

### 2.6 Types (`src/types/`)

`src/types/auth.ts`:
```typescript
// TokenResponse, LoginTicketResponse, AccessPendingResponse, AuthenticatedLoginResponse
// — identical to saas-microtv.ar/src/types/auth.ts
```

`src/types/company.ts`:
```typescript
export interface CompanyInfo {
  company_id: string
  company_name: string
  logo_url: string | null
  status: 'active' | 'suspended'
}

export interface AdminInfo {
  user_id: string
  email: string
  display_name: string
  membership_id: string
  roles: string[]
}

export interface AssignAdminResponse {
  status: 'assigned' | 'invited'
  user?: AdminInfo
  invitation_id?: string
}

export interface ConflictAdminResponse {
  detail: 'existing_admin'
  companies: CompanyInfo[]
}
```

### 2.7 `src/lib/admin.ts`

```typescript
// Company CRUD (platform_admin)
export async function getAdminCompanies(): Promise<CompanyInfo[]>
// GET /v1/admin/companies

export async function createCompany(data: CreateCompanyPayload): Promise<CompanyInfo>
// POST /v1/admin/companies

export async function updateCompany(id: string, data: UpdateCompanyPayload): Promise<CompanyInfo>
// PATCH /v1/admin/companies/{id}

export async function suspendCompany(id: string): Promise<CompanyInfo>
// POST /v1/admin/companies/{id}/suspend

export async function reactivateCompany(id: string): Promise<CompanyInfo>
// POST /v1/admin/companies/{id}/reactivate

// company_admin management (platform_admin)
export async function getCompanyAdmins(companyId: string): Promise<AdminInfo[]>
// GET /v1/admin/companies/{companyId}/admins

export async function assignOrInviteAdmin(
  companyId: string,
  userEmail: string,
  force = false,
): Promise<AssignAdminResponse>
// POST /v1/admin/companies/{companyId}/admins[?force=true]

export async function revokeAdmin(companyId: string, userId: string): Promise<void>
// DELETE /v1/admin/companies/{companyId}/admins/{userId}
```

### 2.8 Tests

`src/tests/unit/company-list.test.tsx`:
- Renders list of companies from mock API.
- "Nueva empresa" button visible for platform_admin, hidden for company_admin.

`src/tests/unit/assign-admin-flow.test.tsx`:
- Email input → 201 assigned → shows success message + invokes admin list refresh.
- Email input → 202 invited → shows "Invitación enviada" message.
- Email input → 409 conflict → shows confirmation dialog.
- Confirm on conflict → retries with `force=true` → shows success.
- 422 incompatible type → shows error message.

`src/tests/unit/admin-list.test.tsx`:
- Renders admin table from mock API.
- "Revocar admin" calls `revokeAdmin()` and removes row from list.

### 2.9 Deploy files

`deploy/entities-microtv.service` — systemd service, same pattern as `saas-microtv.service`.

`deploy/nginx/entities.conf` — Nginx config to serve the built SPA.

---

## 3. `saas-microtv.ar` additions

### 3.1 Admin app tile in the dashboard

File: `src/config/apps.ts` (or wherever the app tiles catalogue is defined)

Add an entry for the admin panel:

```typescript
{
  id: 'entities',
  name: 'Panel Admin',
  description: 'Gestión de empresas y administradores',
  url: env.ENTITIES_URL,    // VITE_ENTITIES_URL env var
  icon: 'shield-check',     // existing icon set
  requiredRoles: ['company_admin', 'platform_admin'],
}
```

Add `VITE_ENTITIES_URL` to `src/config/env.ts` and `.env.example`.

The tile is already filtered by `activeMembership.roles` via the existing `appStore` logic —
no changes needed to the filtering mechanism itself.

### 3.2 New page: `pages/AcceptInvitation.tsx`

Route: `/accept-invitation` (public, no auth required).

Register in `App.tsx` before the `ProtectedRoute` wrapper.

**Flow:**

1. Read `token` from `useSearchParams()`.
2. On mount: `GET /v1/invitations/{token}`.
   - Success → show company name and invited email in a summary card above the form.
   - 404 → show error state: *"Este link de invitación no es válido."*
   - 410 → show error state: *"Este link de invitación ya fue utilizado o expiró."*
3. Form fields: `display_name` (required, 2–80 chars), `password` (min 8 chars),
   `confirm_password`.
4. Validation via React Hook Form + Zod (same pattern as `Register.tsx`).
5. On submit: `POST /v1/invitations/{token}/accept` with `{ display_name, password }`.
6. On success (200):
   - Response is a `TokenResponse` (auto-logged in, single company_admin membership).
   - Hydrate auth store + context store.
   - Navigate to `/dashboard`.
7. On 410 during submit: show inline error *"La invitación expiró. Solicitá al administrador que reenvíe la invitación."*

Add to `src/lib/auth.ts`:

```typescript
export async function previewInvitation(token: string): Promise<InvitationPreview>
// GET /v1/invitations/{token}

export async function acceptInvitation(
  token: string,
  data: { display_name: string; password: string },
): Promise<TokenResponse>
// POST /v1/invitations/{token}/accept
```

Add `InvitationPreview` to `src/types/auth.ts`:

```typescript
export interface InvitationPreview {
  invitation_id: string
  email: string
  company_id: string
  company_name: string
  expires_at: string   // ISO8601
  status: string
}
```

### 3.3 Tests

`src/tests/unit/accept-invitation.test.tsx` (new):

- Valid token → renders company name and email in summary card.
- Invalid token (404) → shows "Este link de invitación no es válido."
- Expired token (410) → shows "Este link de invitación ya fue utilizado o expiró."
- Submit success → `acceptInvitation()` called, store hydrated, navigate to `/dashboard`.
- Submit 410 → shows inline expiry error.

### 3.4 Documentation update

`docs/ARCHITECTURE.md`:
- Add `/accept-invitation` to the public routes table.
- Add `entities-microtv.ar` to the service diagram and notes.

---

## 4. Architecture documentation update

`microtv-architecture/ARCHITECTURE.md` and `microtv-architecture/SERVICE_DOMAINS.md`:
- Add `entities-microtv.ar` as a new frontend service in the Platform Admin domain.
- Note that its auth backend is `auth.microtv.ar` (same as all other frontends).
- Note domain: `admin.microtv.ar` or `entities.microtv.ar` (TBD at deploy time).

---

## 5. Migration execution order on server

```bash
alembic upgrade 20260308_0007   # adds invitations table
```

No data migration required. Existing data is unaffected.

---

## 6. Out of scope for this phase

- Entity management (bus routes, schedules, stops, vehicles) — Phase 5.
- User listing / search / suspension in admin panel — Phase 5.
- Role editor (custom roles beyond the 4 seeded roles) — future.
- Audit log for admin actions — future.
- SSO / token passthrough between `saas-microtv.ar` and `entities-microtv.ar` — future.
- Billing context (`tenant_type="billing"`) — future.
- Company SSO / enterprise login — future.

---

## 7. Commit plan

**`auth.microtv.ar`**:
```
feat(admin): add platform admin API, invitation model, and company CRUD endpoints
```

**`entities-microtv.ar`** (initial commit):
```
feat: scaffold entities admin panel — auth, company list, assign-admin flow
```

**`saas-microtv.ar`**:
```
feat(saas): add admin app tile and accept-invitation page
```

**`microtv-architecture`**:
```
docs: add entities-microtv.ar service to architecture and domain model
```
