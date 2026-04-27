# MicroTV — Identity Service Architecture

## Overview

The identity service provides centralized authentication and authorization for the MicroTV platform.

Service:

auth.microtv.ar

This service is responsible for managing user identities, authentication sessions, and access control information used by other platform services.

All applications and backend services rely on this service to validate user identity and determine access permissions.

The identity service does not manage operational entities such as companies, devices, or transport infrastructure.

---

# Domain Responsibility

The identity service belongs to the **Identity Domain**.

Its responsibility is to determine:

- who a user is
- how the user authenticates
- which roles the user has
- which organizational contexts the user belongs to

The service provides identity information that other services use to enforce access control.

---

# Core Responsibilities

The identity service is responsible for the following capabilities.

## Authentication

The service authenticates users through supported authentication methods.

Examples:

- email and password
- external identity providers (Google)

Successful authentication results in the creation of an authenticated session or token.

---

## User Registration and Email Verification

The service handles the full registration lifecycle for new users:

1. A new account is created with `status = "pending_verification"`.
2. A time-limited verification token (valid 24 hours) is generated and emailed to the user.
3. The user submits the token via `POST /v1/auth/verify-email`.
4. On success, the account status is updated to `active`, `email_verified` is set to `true`, and the token is cleared.
5. Tokens may be regenerated via `POST /v1/auth/resend-verification`.

Registration and resend endpoints are protected with Google reCAPTCHA v3 score validation and in-memory rate limiting.

---

## Identity Management

The service manages user accounts within the platform.

User accounts represent human identities interacting with MicroTV services.

User records contain identity-related information such as:

- email
- authentication credentials
- identity provider associations

---

## Authorization Metadata

The identity service manages authorization metadata used by other services.

Examples include:

- roles
- role assignments
- memberships

These entities allow applications to determine what a user is allowed to access.

---

## Session Management

The identity service manages authentication sessions.

Sessions represent authenticated user activity.

Sessions may be represented by:

- session tokens
- refresh tokens
- API tokens

Other services rely on tokens issued by the identity service.

---

## Identity Providers

The service may integrate with external identity providers.

Examples:

- Google login
- enterprise identity systems

External identities are linked to internal user accounts.

External authentication does not replace internal authorization rules.

---

# Entities Managed by the Service

The identity service owns the lifecycle of the following entities.

users  
roles  
user_roles  
sessions  
api_keys  
identity_providers  
user_identities  
memberships

These entities define user identity and access rights within the platform.

---

# Entities Not Managed by the Service

The identity service must not manage operational or infrastructure entities.

Examples include:

companies  
fleets  
devices  
routes  
stops  
stations  
terminals  

These entities belong to other domains.

Refer to:

DATA_OWNERSHIP.md

---

# Interaction with Other Services

The identity service interacts with other services through authentication tokens and identity claims.

Typical interaction pattern:

Application  
→ authenticate through identity service  
→ receive token  
→ use token to access other services

Other services validate tokens to determine the identity and permissions of the user.

---

# Token Model

The identity service issues authentication tokens.

Tokens may contain claims such as:

user_id  
roles  
membership identifiers  
tenant identifiers

Services use these claims to enforce authorization.

Tokens must not contain sensitive user data.

---

# Multi-Tenant Context

Users may belong to multiple organizational contexts.

Examples:

- company membership
- customer membership

Membership information is stored in the identity service.

Applications use membership information to determine which organizational context the user is operating in.

---

# Security Considerations

The identity service is a critical component of the platform security model.

Security responsibilities include:

- secure password storage
- token signing and validation
- session expiration
- authentication auditing

The service must enforce strong authentication and access control policies.

---

# Scalability Considerations

The identity service must support:

- multiple applications
- multiple organizations
- growing user populations

Authentication operations should remain lightweight and stateless whenever possible.

Token validation should not require expensive database queries.

---

# Relationship with Legacy Systems

Legacy systems may currently contain authentication mechanisms.

During the platform migration, authentication responsibilities will progressively move to the identity service.

Legacy systems should eventually rely on the identity service for authentication and authorization.

---

# Future Capabilities

The identity service may later support additional features such as:

- multi-factor authentication
- advanced access policies
- service-to-service authentication
- audit logging and security monitoring

These features must remain consistent with the overall security architecture of the platform.