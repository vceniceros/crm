# auth.microtv.ar Architecture Audit

Date: March 6, 2026

Scope:

- Repository: `auth.microtv.ar`
- Primary code under review: `backend/src/`
- Supporting documentation under review: `docs/`

Authoritative references used:

- `microtv-architecture/SERVICE_DOMAINS.md`
- `microtv-architecture/DATA_OWNERSHIP.md`
- `microtv-architecture/SECURITY_MODEL.md`
- `microtv-architecture/API_CONTRACT_PRINCIPLES.md`
- `auth.microtv.ar/docs/ARCHITECTURE.md`
- `auth.microtv.ar/docs/DOMAIN_MODEL.md`
- `auth.microtv.ar/docs/TECH_STACK.md`
- `auth.microtv.ar/docs/API_SPEC.md`

## 1. Executive Summary

The backend is partially aligned with the MicroTV platform architecture.

It stays within the Identity domain boundary: the implemented schema only covers `users`, `roles`, `memberships`, and `role_assignments`, and memberships store only `tenant_type` and `tenant_id` references rather than foreign-domain data. The token model also moves in the right direction by issuing membership-scoped JWTs with `iss`, `aud`, `iat`, `exp`, and `active_membership`.

The service is not yet fully consistent with the documented architecture. The main gaps are:

- documented identity entities are still missing from the implementation: `sessions`, `api_keys`, `identity_providers`, and `user_identities`
- refresh token handling is not backed by a revocable server-side session model
- the implemented API covers only part of `docs/API_SPEC.md`
- several response shapes do not match the documented contract
- the default JWT secret is unsafe

There is no evidence of cross-domain leakage into Entities, Transport, or analytics responsibilities. The main issue is architectural incompleteness and security/contract drift inside the Identity domain.

## 2. Architectural Compliance

### Identity domain ownership

Compliant in scope:

- `backend/src/models/__init__.py:1-6` exposes only identity-domain models.
- `backend/src/models/membership.py:18-20` stores only `tenant_type` and `tenant_id`, which is consistent with reference-by-identifier ownership.
- No implemented model stores company metadata, fleet structures, device records, routes, or campaigns.

Not fully compliant with the documented identity model:

- `backend/src/models/__init__.py:1-6` includes `Membership`, `Role`, `RoleAssignment`, and `User`, but omits `sessions`, `api_keys`, `identity_providers`, and `user_identities`.
- `docs/DOMAIN_MODEL.md:21-30` defines those entities as part of the core identity domain.

### Multi-tenant isolation

Partially compliant:

- `backend/src/security/jwt.py:42-58` includes `active_membership` in access and refresh tokens.
- `backend/src/security/jwt.py:20-39` normalizes the active membership and requires `membership_id`, `tenant_type`, and `tenant_id`.
- `backend/src/security/authorization.py:7-43` authorizes against `active_membership` and can enforce tenant-specific checks.

Architectural weakness:

- `backend/src/security/authorization.py:7-29` makes `tenant_id` optional in `require_role`. That allows downstream code to authorize only from the token's current membership without forcing an explicit tenant comparison at the call site.
- The audit did not find any protected service endpoints using these helpers, so there is not yet end-to-end evidence that tenant-bound authorization is consistently enforced in request handling.

### API contract and versioning

Partially compliant:

- `backend/src/api/auth.py:10` uses the required versioned prefix `/v1/auth`.

Not fully compliant:

- only `POST /v1/auth/login` and `POST /v1/auth/select-context` are implemented in `backend/src/api/auth.py:17-56`
- the documented API includes additional authentication, user, membership, role, and API key endpoints in `docs/API_SPEC.md:193-390`

## 3. Domain Boundary Violations

No direct cross-domain ownership violation was found in the current backend implementation.

Verified observations:

- No tables or models for `companies`, `fleets`, `devices`, `routes`, or other foreign-domain entities exist under `backend/src/models/`.
- `backend/src/models/membership.py:18-20` references tenants only by identifier, which is allowed by `DATA_OWNERSHIP.md` and `docs/DOMAIN_MODEL.md:253-263`.

Architectural drift inside the Identity domain does exist:

- The backend implements only part of the required identity domain model.
- `docs/DOMAIN_MODEL.md:178-210` requires `sessions` and `api_keys`, but no corresponding models or migrations exist.
- `docs/DOMAIN_MODEL.md:61-91` requires `identity_providers` and `user_identities`, but no corresponding models or migrations exist.

## 4. Security Assessment

### Positive findings

- `backend/src/security/passwords.py:1-11` uses Argon2 for password hashing, which matches `docs/TECH_STACK.md:124-137`.
- `backend/src/security/jwt.py:10-17` sets `iss`, `aud`, `iat`, and `exp`.
- `backend/src/security/jwt.py:71-106` validates signature, issuer, audience, and expiration through PyJWT decoding and explicit claim checks.
- `backend/src/security/jwt.py:42-48` keeps access-token claims small; it does not embed the user's full membership list.
- `backend/src/security/jwt.py:62-68` issues login tickets with a dedicated audience and a short lifetime from `backend/src/config.py:24`.

### Security risks

- `backend/src/config.py:17` defaults `JWT_SECRET` to `change-me`. This is an unsafe production default and a direct token forgery risk if not overridden.
- `backend/src/security/jwt.py:52-59` issues refresh tokens as standalone JWTs, but the implementation has no `sessions` model, no token hashing, no revocation state, and no logout/refresh processing path. That is inconsistent with `docs/DOMAIN_MODEL.md:178-193` and `docs/API_SPEC.md:215-262`.
- `backend/src/api/auth.py:21-22` returns `401` with `Invalid credentials.`, but `backend/src/services/auth_service.py:53-54` can also return `User is not active.`. That leaks account state and weakens authentication error uniformity.

## 5. API Contract Consistency

### Implemented endpoints

- `POST /v1/auth/login` in `backend/src/api/auth.py:17-38`
- `POST /v1/auth/select-context` in `backend/src/api/auth.py:41-56`
- `GET /health` in `backend/src/main.py:16-18`

### Missing documented endpoints

The following documented endpoints are absent from `backend/src/`:

- `POST /v1/auth/provider/login` from `docs/API_SPEC.md:193-212`
- `POST /v1/auth/refresh` from `docs/API_SPEC.md:215-238`
- `POST /v1/auth/logout` from `docs/API_SPEC.md:241-262`
- `GET /v1/users/me` from `docs/API_SPEC.md:266-290`
- `GET /v1/memberships` from `docs/API_SPEC.md:294-318`
- `GET /v1/roles` from `docs/API_SPEC.md:322-344`
- API key endpoints from `docs/API_SPEC.md:348-390`

### Response-shape mismatches

- `backend/src/schemas/auth.py:16-22` defines `TokenResponse` without the documented `user` and `active_membership` objects required by `docs/API_SPEC.md:103-122` and `docs/API_SPEC.md:142-156`.
- `backend/src/schemas/auth.py:25-28` defines `LoginTicketResponse` without the documented `user` object required by `docs/API_SPEC.md:160-189`.
- `backend/src/schemas/auth.py:16-22` adds `refresh_expires_in`, which is not documented in `docs/API_SPEC.md`.
- The implementation returns FastAPI's default `detail` error shape, while `docs/API_SPEC.md:394-405` documents an `{ "error": ..., "message": ... }` structure.

### HTTP semantics

- For the implemented auth flows, `POST` is appropriate.
- `GET /health` is acceptable as a system probe, though it is outside the documented public API.

## 6. Dependency Compliance

### Allowed stack in use

`backend/pyproject.toml` declares:

- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `alembic`
- `psycopg`
- `pydantic`
- `python-dotenv`
- `argon2-cffi`
- `pyjwt`
- `authlib`

Architectural assessment:

- No disallowed application framework was found.
- The primary backend choices are consistent with `docs/TECH_STACK.md:37-150`.
- `psycopg`, `pydantic`, and `python-dotenv` are support dependencies that are reasonable for the approved stack, but they are not explicitly documented in `docs/TECH_STACK.md`.

### Migration tooling

Compliant:

- `backend/alembic.ini` exists.
- `backend/migrations/versions/20260306_0001_initial_identity_tables.py` and `backend/migrations/versions/20260306_0002_add_role_assignments.py` show Alembic is in use, which matches `docs/TECH_STACK.md:93-102`.

Gap:

- migrations still cover only the implemented subset of the identity model.

## 7. Detected Risks

### High

- Refresh token handling is not architecture-compliant: refresh tokens are minted, but there is no `sessions` persistence, revocation model, refresh endpoint, or logout endpoint. This leaves long-lived bearer tokens without server-side invalidation.
- The backend and `docs/API_SPEC.md` materially diverge: major documented endpoints are missing, and implemented response bodies do not match the documented contract.
- The implemented schema is incomplete relative to `docs/DOMAIN_MODEL.md`: `sessions`, `api_keys`, `identity_providers`, and `user_identities` are missing.

### Medium

- `JWT_SECRET` defaults to `change-me` in `backend/src/config.py:17`, which creates an avoidable token-signing risk.
- Tenant-bound authorization can be bypassed at call sites that use `require_role` without supplying an explicit `tenant_id`, because `backend/src/security/authorization.py:7-29` permits implicit context checks.
- Authentication errors are not uniform: inactive accounts can be distinguished from invalid credentials.

### Low

- `docs/TECH_STACK.md` does not fully enumerate the support dependencies now present in `backend/pyproject.toml`.
- `backend/tests/` still contains only `.gitkeep`, which leaves architectural behavior unverified by automated tests.
- Generated `__pycache__` artifacts are present under `backend/src/` and `backend/migrations/`.

## 8. Recommended Corrections

The following corrections are required to restore alignment with the documented architecture.

1. Implement the missing documented identity entities: `sessions`, `api_keys`, `identity_providers`, and `user_identities`.
2. Move refresh-token handling onto an architecture-compliant session model so refresh and logout can revoke server-side state.
3. Bring the implemented API into line with `docs/API_SPEC.md`, including the missing endpoints and the documented response fields `user` and `active_membership`.
4. Remove the unsafe `JWT_SECRET` fallback and fail startup when the signing secret is not explicitly configured.
5. Tighten authorization helpers so tenant-scoped authorization always compares against an explicit tenant identifier where tenant access is being enforced.
6. Make `docs/TECH_STACK.md` reflect the actual support dependencies if they are intended to remain part of the approved stack.

Final assessment:

The service does not leak across domain boundaries, but it is not yet fully aligned with the MicroTV identity architecture. The main blockers are incomplete identity-domain coverage, refresh/session security gaps, and contract drift between `backend/src/` and `docs/API_SPEC.md`.
