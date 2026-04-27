# MicroTV — Identity Service API Specification

## Overview

This document defines the public API exposed by the MicroTV identity service.

Service:

auth.microtv.ar

The API provides authentication, session management, and identity information used by other services and applications.

All endpoints return JSON responses.

Authentication is performed using tokens issued by the identity service.

---

# API Versioning

All endpoints are versioned.

Base path:

/v1/

Example:

/v1/auth/login

Future breaking changes will introduce new versions.

---

# Authentication Flow

The identity service implements a **multi-tenant login flow**.

Sequence:

1. User authenticates identity with credentials or external provider.
2. Identity service loads memberships associated with the user.
3. If only one membership is available → tokens are issued immediately.
4. If multiple memberships exist → client must select a tenant context.
5. Identity service issues tokens bound to the selected context.

---

# Token Format

Tokens may be implemented using JWT or similar signed tokens.

Token claims include:

sub  
email  
active_membership  
iss  
aud  
iat  
exp

Example token payload:

```json
{
  "sub": "user_123",
  "email": "user@example.com",
  "active_membership": {
    "membership_id": "m2",
    "tenant_type": "company",
    "tenant_id": "company_77",
    "roles": ["viewer"]
  },
  "iss": "auth.microtv.ar",
  "aud": "microtv-platform",
  "iat": 1710000000,
  "exp": 1710003600
}

Tokens must not contain sensitive information.

---

# Authentication Endpoints

## Login (Email / Password)

Authenticate using internal credentials.

POST  
/v1/auth/login

### Request

```json
{
  "email": "user@example.com",
  "password": "secret"
}
````

### Login Response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "user": {
    "user_id": "u123",
    "email": "user@example.com"
  },
  "active_membership": {
    "membership_id": "m1",
    "tenant_type": "company",
    "tenant_id": "company_42",
    "roles": ["company_admin"]
  },
  "requires_context_selection": false
}
```

---

## Select Tenant Context

Completes login when multiple memberships exist.

POST
/v1/auth/select-context

### Request

```json
{
  "login_ticket": "...",
  "membership_id": "m2"
}
```

### Response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "active_membership": {
    "membership_id": "m2",
    "tenant_type": "company",
    "tenant_id": "company_77",
    "roles": ["viewer"]
  }
}
```

---

### Login with Multiple Memberships

If the user belongs to multiple organizations, the identity service returns a login ticket and requires context selection.

Example response:

```json
{
  "login_ticket": "...",
  "user": {
    "user_id": "u123",
    "email": "user@example.com"
  },
  "memberships": [
    {
      "membership_id": "m1",
      "tenant_type": "company",
      "tenant_id": "company_42",
      "roles": ["company_admin"]
    },
    {
      "membership_id": "m2",
      "tenant_type": "company",
      "tenant_id": "company_77",
      "roles": ["viewer"]
    }
  ],
  "requires_context_selection": true
}
```

---

## Login with External Provider

Authenticate using external identity provider.

POST
/v1/auth/provider/login

### Request

```json
{
  "provider": "google",
  "provider_token": "external_oauth_token"
}
```

### Response

Same as `/auth/login`.

---

## Token Refresh

Obtain a new access token using a refresh token.

POST
/v1/auth/refresh

### Request

```json
{
  "refresh_token": "..."
}
```

### Response

```json
{
  "access_token": "...",
  "expires_in": 3600
}
```

---

## Logout

Invalidate current session.

POST
/v1/auth/logout

### Request

```json
{
  "refresh_token": "..."
}
```

### Response

```json
{
  "status": "ok"
}
```

---

## Register

Create a new user account with email + password.

POST
/v1/auth/register

Rate limit: 5 requests per hour per IP.

### Request

```json
{
  "display_name": "Juan Pérez",
  "email": "juan@example.com",
  "password": "mysecretpass",
  "recaptcha_token": "03AGdBq...",
  "user_type": "customer"
}
```

Field constraints:

- `display_name`: 2–80 characters
- `email`: valid email format, unique in the system
- `password`: minimum 8 characters
- `recaptcha_token`: reCAPTCHA v3 token obtained client-side
- `user_type`: `"customer"` (default) or `"company_employee"`

### Response (201)

```json
{
  "message": "Verification email sent. Please check your inbox."
}
```

### Errors

| Status | Condition |
|--------|-----------|
| 409 Conflict | Email already registered |
| 422 Unprocessable Entity | Validation failure (field constraints) |
| 429 Too Many Requests | Rate limit exceeded |

### Notes

- The user account is created with `status = "pending_verification"`.
- A verification email is sent to the provided address.
- The user cannot log in until email is verified.
- reCAPTCHA token is validated server-side. In development, the check is bypassed when `RECAPTCHA_SECRET_KEY` is not set.

---

## Verify Email

Activate a user account using the token from the verification email.

POST
/v1/auth/verify-email

### Request

```json
{
  "token": "a1b2c3d4-..."
}
```

### Response — Single Membership (200)

If the user has exactly one membership, tokens are issued immediately:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 3600,
  "user": {
    "user_id": "u123",
    "email": "juan@example.com"
  },
  "active_membership": {
    "membership_id": "m1",
    "tenant_type": "company",
    "tenant_id": "company_42",
    "roles": ["company_admin"]
  },
  "requires_context_selection": false
}
```

### Response — Multiple Memberships (200)

If the user belongs to multiple organizations, a login ticket is returned:

```json
{
  "login_ticket": "...",
  "user": {
    "user_id": "u123",
    "email": "juan@example.com"
  },
  "memberships": [...],
  "requires_context_selection": true
}
```

### Response — Access Pending (200)

Returned for `company_employee` users who have no memberships yet (awaiting company admin approval):

```json
{
  "access_pending": true
}
```

### Response — No Membership (403)

Returned only for `customer` users who somehow have no platform membership (should not occur in normal flow).

```json
{
  "detail": "No memberships found for this user."
}
```

### Errors

| Status | Condition |
|--------|-----------|
| 422 Unprocessable Entity | Token missing or invalid format |
| 400 Bad Request | Token not found, already used, or expired |

### Notes

- Verification tokens are valid for 24 hours.
- Tokens are single-use: the token is cleared after successful verification.
- The user `status` is updated to `active` and `email_verified` is set to `true`.

---

## Resend Verification Email

Re-send the verification email to a pending account.

POST
/v1/auth/resend-verification

Rate limit: 3 requests per hour per email address.

### Request

```json
{
  "email": "juan@example.com",
  "recaptcha_token": "03AGdBq..."
}
```

### Response (200)

```json
{
  "message": "If the email is registered and pending verification, a new email has been sent."
}
```

### Notes

- Response is intentionally generic to prevent user enumeration.
- Returns the same response regardless of whether the email exists or is already verified.
- A new token and expiry (24h) are generated on each resend.
- reCAPTCHA validation is applied before processing.

---

## Forgot Password

Request a password reset link for an active local account.

POST
/v1/auth/forgot-password

Rate limit: 3 requests per hour per email address.

### Request

```json
{
  "email": "juan@example.com",
  "recaptcha_token": "03AGdBq..."
}
```

### Response (200)

```json
{
  "message": "If an active account exists for this email, a password reset link has been sent."
}
```

### Errors

| Status | Condition |
|--------|-----------|
| 422 Unprocessable Entity | reCAPTCHA validation failure |
| 429 Too Many Requests | Rate limit exceeded |

### Notes

- Response is intentionally generic to prevent user enumeration.
- Returns the same response whether the account exists or is eligible for local-password reset.
- A one-time reset token is sent by email and points to the SaaS frontend.

---

## Reset Password

Consume a password reset token and update the stored local password.

POST
/v1/auth/reset-password

### Request

```json
{
  "token": "a1b2c3d4-...",
  "new_password": "mynewsecretpass"
}
```

### Response (200)

```json
{
  "message": "Password updated successfully."
}
```

### Errors

| Status | Condition |
|--------|-----------|
| 422 Unprocessable Entity | Token missing, invalid, expired, or already used |
| 429 Too Many Requests | Rate limit exceeded |

### Notes

- Reset tokens are single-use.
- The reset link is time-limited.
- Successful reset does not automatically log the user in.

---

# User Endpoints

## Get Current User

Returns information about the authenticated user.

GET
/v1/users/me

Authentication required.

### Response

```json
{
  "user_id": "u123",
  "email": "user@example.com",
  "active_membership": {
    "membership_id": "m2",
    "tenant_type": "company",
    "tenant_id": "company_77",
    "roles": ["viewer"]
  }
}
```

---

# Membership Endpoints

## List Memberships

Returns the organizations the user belongs to.

GET
/v1/memberships

Authentication required.

### Response

```json
[
  {
    "membership_id": "m1",
    "tenant_type": "company",
    "tenant_id": "c42",
    "roles": [
      "company_admin"
    ]
  }
]
```

---

# Role Endpoints

## List Roles

GET
/v1/roles

Returns available roles.

### Response

```json
[
  {
    "role_id": "r1",
    "role_name": "company_admin"
  },
  {
    "role_id": "r2",
    "role_name": "passenger_user"
  }
]
```

---

# Company Endpoints

All company endpoints require a valid Bearer token.

---

## List My Companies

Returns the companies where the authenticated user has the `company_admin` role.

GET
/v1/companies/mine

Authentication required.

### Response (200)

```json
[
  {
    "company_id": "ABC123",
    "company_name": "Empresa SA",
    "logo_url": null,
    "status": "active"
  }
]
```

---

## List Company Members

Returns all users with an active membership in the specified company.

GET
/v1/companies/{company_id}/members

Requires `company_admin` role for the specified company.

### Response (200)

```json
[
  {
    "user_id": "u123",
    "display_name": "María García",
    "email": "maria@empresa.com",
    "roles": ["company_operator"]
  }
]
```

### Errors

| Status | Condition |
|--------|-----------|
| 403 Forbidden | Caller does not have `company_admin` role for this company |
| 404 Not Found | Company does not exist |

---

## Grant Company Access

Grants a `company_employee` user access to the specified company with the `company_operator` role.

POST
/v1/companies/{company_id}/members

Requires `company_admin` role for the specified company.

### Request

```json
{
  "user_email": "nueva@empresa.com"
}
```

### Response (201)

```json
{
  "user_id": "u456",
  "display_name": "Nueva Empleada",
  "email": "nueva@empresa.com",
  "roles": ["company_operator"]
}
```

### Errors

| Status | Condition |
|--------|-----------|
| 403 Forbidden | Caller does not have `company_admin` role for this company |
| 404 Not Found | No active `company_employee` user found with that email |
| 409 Conflict | User already has access to this company |

---

## Revoke Company Access

Removes a user's membership and role assignments from the specified company.

DELETE
/v1/companies/{company_id}/members/{user_id}

Requires `company_admin` role for the specified company.

### Response (204)

No content.

### Errors

| Status | Condition |
|--------|-----------|
| 403 Forbidden | Caller does not have `company_admin` role for this company |
| 404 Not Found | User does not have a membership in this company |

---

# API Key Endpoints

## Create API Key

POST
/v1/api-keys

Authentication required.

### Request

```json
{
  "description": "integration key"
}
```

### Response

```json
{
  "api_key": "generated_key",
  "api_key_id": "k123"
}
```

---

## List API Keys

GET
/v1/api-keys

Returns API keys owned by the authenticated user.

---

## Revoke API Key

POST
/v1/api-keys/{key_id}/revoke

Revokes an existing key.

---

# Error Responses

Errors follow a consistent structure.

Example:

```json
{
  "error": "invalid_credentials",
  "message": "Email or password incorrect"
}
```

---

# Common HTTP Status Codes

200 — success
400 — invalid request
401 — authentication required
403 — permission denied
404 — resource not found
409 — conflict
500 — internal error

---

# Security Notes

Passwords must never be returned in responses.

Refresh tokens must be stored securely.

API keys must be shown only at creation time.

Sensitive tokens should never appear in logs.

---

# Rate Limiting

Authentication endpoints may apply rate limiting to prevent abuse.

Typical protected endpoints:

/auth/login
/auth/provider/login
/auth/refresh

---

# Future Extensions

The API may later include additional capabilities.

Examples:

* multi-factor authentication
* session management
* service accounts
* delegated access

New features must remain compatible with the identity domain boundaries.

---

# Platform Admin Endpoints

All endpoints under `/v1/admin` require a valid Bearer token where `active_membership.roles` contains `"platform_admin"`. Returns `403 Forbidden` if the claim is absent.

---

## List Companies

```
GET /v1/admin/companies
Authorization: Bearer <platform_admin_token>
```

**Response 200**

```json
[
  {
    "company_id": "LINEABAR",
    "company_name": "Línea Barcelona",
    "logo_url": null,
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

---

## Create Company

```
POST /v1/admin/companies
Authorization: Bearer <platform_admin_token>
Content-Type: application/json
```

**Body**

```json
{
  "company_id": "LINEABAR",
  "company_name": "Línea Barcelona",
  "logo_url": "https://cdn.microtv.ar/logos/lineabar.png"
}
```

`company_id` is a short alphanumeric identifier (max 20 chars) supplied explicitly. `logo_url` is optional.

**Responses**

| Status | Description |
|--------|-------------|
| 201 | Company created — returns `CompanyInfo` |
| 409 | `company_id` already exists |

---

## Get Company

```
GET /v1/admin/companies/{company_id}
Authorization: Bearer <platform_admin_token>
```

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Returns `CompanyInfo` |
| 404 | Company not found |

---

## Update Company

```
PATCH /v1/admin/companies/{company_id}
Authorization: Bearer <platform_admin_token>
Content-Type: application/json
```

**Body** (all fields optional)

```json
{
  "company_name": "Línea Barcelona S.A.",
  "logo_url": "https://cdn.microtv.ar/logos/lineabar-v2.png"
}
```

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Returns updated `CompanyInfo` |
| 404 | Company not found |

---

## Suspend Company

```
POST /v1/admin/companies/{company_id}/suspend
Authorization: Bearer <platform_admin_token>
```

Sets company `status` to `"inactive"`.

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Returns updated `CompanyInfo` |
| 404 | Company not found |

---

## Reactivate Company

```
POST /v1/admin/companies/{company_id}/reactivate
Authorization: Bearer <platform_admin_token>
```

Sets company `status` back to `"active"`.

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Returns updated `CompanyInfo` |
| 404 | Company not found |

---

## List Company Admins

```
GET /v1/admin/companies/{company_id}/admins
Authorization: Bearer <platform_admin_token>
```

**Response 200**

```json
[
  {
    "user_id": "uuid",
    "email": "admin@empresa.com",
    "display_name": "Juan García",
    "assigned_at": "2025-01-10T00:00:00Z"
  }
]
```

---

## Assign or Invite Company Admin

```
POST /v1/admin/companies/{company_id}/admins?force=false
Authorization: Bearer <platform_admin_token>
Content-Type: application/json
```

**Body**

```json
{
  "user_email": "admin@empresa.com"
}
```

**Query parameter**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | boolean | `false` | Override existing-admin conflict and assign anyway |

**Behavior by case**

| Case | Condition | Status | Response |
|------|-----------|--------|----------|
| A — Direct assign | User exists, no conflict | 201 | `AssignAdminResponse` |
| B — Invitation sent | User does not exist | 202 | `AssignAdminResponse` + invitation email dispatched |
| Conflict | User is already admin elsewhere + `force=false` | 409 | `{ "detail": "existing_admin", "companies": [...] }` |
| Already admin | User is already admin of this company | 409 | `{ "detail": "..." }` |
| Customer user | User exists but is a `customer_user` | 422 | `{ "detail": "..." }` |

---

## Revoke Company Admin

```
DELETE /v1/admin/companies/{company_id}/admins/{user_id}
Authorization: Bearer <platform_admin_token>
```

Removes the `company_admin` role assignment for the user in this company's membership.

**Responses**

| Status | Description |
|--------|-------------|
| 204 | Admin revoked successfully |
| 404 | Company or user not found |

---

# Invitation Endpoints

These endpoints are **public** — no authentication required.

---

## Preview Invitation

Returns metadata about a pending invitation so the frontend can display context before the user fills in the form.

```
GET /v1/invitations/{token}
```

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Returns `InvitationPreviewResponse` |
| 404 | Token not found |
| 410 | Token expired, already accepted, or revoked |

**Response 200**

```json
{
  "email": "invitado@empresa.com",
  "company_name": "Línea Barcelona",
  "expires_at": "2025-06-15T12:00:00Z"
}
```

---

## Accept Invitation

Registers a new user account and issues authentication tokens in a single step.

```
POST /v1/invitations/{token}/accept
Content-Type: application/json
```

**Body**

```json
{
  "display_name": "Juan García",
  "password": "SecurePassword123!"
}
```

**Responses**

| Status | Description |
|--------|-------------|
| 200 | Account created, auto-login — returns `TokenResponse` |
| 409 | The invitation email is already registered as a user |
| 410 | Token expired, already accepted, or revoked |

After a successful `200`, the client receives `access_token` and `refresh_token` and the invitation `status` is set to `"accepted"`. The new user is automatically assigned the `company_admin` role for the invited company.

---
