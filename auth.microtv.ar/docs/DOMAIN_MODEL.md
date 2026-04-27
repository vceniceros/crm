# MicroTV — Identity Service Domain Model

## Overview

The identity service manages the identity and authorization model of the MicroTV platform.

This document defines the entities owned by the identity service and their relationships.

The goal of the domain model is to support:

- centralized authentication
- multi-tenant access
- role-based authorization
- external identity providers
- multiple organizational memberships

---

# Core Entities

The identity domain is composed of the following primary entities.

users  
identity_providers  
user_identities  
memberships  
roles  
role_assignments  
sessions  
api_keys  
companies

Each entity serves a specific purpose in the identity system.

---

# Users

Users represent human identities interacting with the platform.

A user account is unique across the entire platform.

Users may authenticate using internal credentials or external identity providers.

### Fields

user_id  
email  
display_name  
password_hash (nullable if external auth only)  
created_at  
updated_at  
status  
email_verified  
user_type  
verification_token (nullable)  
verification_token_expires_at (nullable)

### User Type Values

| Value | Description |
|-------|-------------|
| `customer` | End-user / passenger. Automatically assigned platform membership on email verification. |
| `company_employee` | Employee of an operating company. Gains access only when granted by a `company_admin`. |
| `platform_admin` | Platform-level administrator. Created via CLI only; not self-registerable. |

### Status Values

| Value | Description |
|-------|-------------|
| `pending_verification` | Account created, email not yet confirmed |
| `active` | Email verified, account fully operational |
| `suspended` | Account disabled by platform admin |

### Notes

- email must be unique
- password_hash may be null if using external login only
- email_verified is set to true when the user successfully confirms their email address
- verification_token is a UUID4 generated at registration (and on resend); it is cleared after use
- verification_token_expires_at defines a 24-hour TTL for the verification token
- Users with `pending_verification` status cannot log in

---

# Identity Providers

Identity providers define authentication sources.

Examples:

local  
google  
enterprise_sso

### Fields

provider_id  
provider_name  
created_at

---

# User Identities

User identities link users to external identity providers.

This allows a single user account to authenticate through multiple providers.

### Fields

identity_id  
user_id  
provider_id  
provider_user_id  
created_at

### Notes

Example:

Google account → linked to user account.

---

# Memberships

Memberships define which organizational contexts a user belongs to.

A user may belong to multiple organizations.

Examples:

company membership  
customer membership

### Fields

membership_id  
user_id  
tenant_type  
tenant_id  
created_at

### tenant_type examples

company  
customer

### tenant_id

Identifier referencing an entity managed by another service.

Example:

company_id from entities service.

---

# Roles

Roles define permission groups.

Roles describe what actions a user may perform.

Examples:

platform_admin  
company_admin  
company_operator  
passenger_user

### Fields

role_id  
role_name  
description  
created_at

---

# Role Assignments

Role assignments connect roles to memberships.

This allows a user to have different roles depending on the organization context.

### Fields

assignment_id  
membership_id  
role_id  
created_at

### Example

User  
→ membership (company 42)  
→ role company_admin

---

# Sessions

Sessions represent authenticated user activity.

Sessions allow applications to maintain authenticated access.

### Fields

session_id  
user_id  
token_hash  
expires_at  
created_at  
revoked_at

Sessions may be backed by refresh tokens.

---

# API Keys

API keys allow programmatic access.

These are typically used by services or automation tools.

### Fields

api_key_id  
owner_user_id  
key_hash  
created_at  
expires_at  
revoked_at

---

# Companies

Companies represent operating companies on the platform.

Company records are owned by the identity service and referenced by memberships.  
Additional business data (schedules, routes, etc.) is managed by the entities service.

### Fields

company_id (String, 20 chars, set explicitly — alphanumeric identifier)  
company_name  
logo_url (nullable)  
status  
created_at

### Status Values

| Value | Description |
|-------|-------------|
| `active` | Company is operating normally |
| `inactive` | Company disabled by platform admin |

### Notes

- `company_id` is a short human-readable identifier (e.g. `"LINEABAR"`) supplied at company creation time.
- `logo_url` is returned in membership listings so clients can display company logos.

---

# Relationships

High-level relationships between entities:

User  
→ UserIdentity  
→ Membership  
→ Session  
→ APIKey

Membership  
→ RoleAssignment  
→ Role

UserIdentity  
→ IdentityProvider

---

# Multi-Tenant Model

Multi-tenancy is achieved through memberships.

Users may belong to multiple tenants.

Example:

User  
→ membership (company A)  
→ role company_admin

User  
→ membership (company B)  
→ role viewer

Applications must determine the active tenant context when processing requests.

---

# External Entity References

Some identifiers reference entities owned by other services.

Examples:

tenant_id → company_id (entities service)

The identity service must **not replicate those entities**.

Only identifiers are stored.

---

# Constraints

The domain model enforces several constraints.

- user email must be unique
- role assignments must reference a valid membership
- user identities must reference valid providers
- sessions must expire automatically

These constraints maintain identity consistency.

---

# Security Considerations

Sensitive fields must be handled securely.

Examples:

password_hash must use strong hashing algorithms  
token_hash must not store plaintext tokens  
api keys must never be stored in plaintext

Security practices are defined in SECURITY_MODEL.md.

---

# Invitations

Invitations allow a platform admin to onboard new company admins.

When a platform admin assigns an admin email that does not yet have a user account, the system creates an invitation record and dispatches an email with a unique link.

The recipient opens the link in `saas-microtv.ar`, fills in a display name and password, and the account is created and immediately authenticated.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `invitation_id` | UUID PK | Unique invitation identifier |
| `token` | String (unique) | URL-safe token embedded in the invitation link |
| `email` | String | Email address of the invitee |
| `company_id` | FK → companies | Company the invitee is being added to |
| `invited_by` | FK → users | Platform admin who created the invitation |
| `status` | Enum | Current state: `pending`, `accepted`, `revoked`, `expired` |
| `expires_at` | Timestamp | Invitation expires 48 hours after creation |
| `created_at` | Timestamp | When the invitation was created |
| `accepted_at` | Timestamp (nullable) | When the invitation was accepted |

### Status Values

| Value | Description |
|-------|-------------|
| `pending` | Awaiting acceptance |
| `accepted` | User followed the link and registered |
| `revoked` | Manually cancelled by a platform admin |
| `expired` | `expires_at` has passed without acceptance |

### Notes

- `token` is generated with `secrets.token_urlsafe(48)` — 64-character URL-safe random string.
- The invitation link points to `{SAAS_BASE_URL}/accept-invitation?token={token}`.
- Accepting an invitation creates a new `User` and assigns the `company_admin` role in the target company's membership.
- Attempting to accept an expired or already-accepted token returns `410 Gone`.

---

# Future Extensions

The domain model may evolve to support:

- multi-factor authentication
- fine-grained permissions
- service accounts
- delegated access
- audit logs

Future additions must remain consistent with the identity domain boundaries.