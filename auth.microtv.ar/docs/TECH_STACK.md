# MicroTV — Identity Service Technical Stack

## Overview

This document defines the approved technology stack for the MicroTV identity service.

Service:

auth.microtv.ar

The purpose of this document is to ensure consistency across the codebase and prevent uncontrolled introduction of dependencies or frameworks.

All implementation must follow this stack unless an RFC explicitly approves a change.

Refer to:

RFC_PROCESS.md

---

# Backend Stack

The backend service implements the identity API and authentication logic.

## Language

Python 3.12+

Reason:

- strong ecosystem
- compatibility with existing MicroTV services
- async capabilities

---

## Web Framework

FastAPI

Responsibilities:

- HTTP API
- request validation
- authentication endpoints
- service endpoints

FastAPI provides:

- async support
- automatic OpenAPI specification
- high performance

---

## ASGI Server

Uvicorn

Used to run the FastAPI application.

---

## Database

PostgreSQL

Reason:

- relational integrity
- strong indexing
- transactional guarantees
- future scalability

SQLite must not be used in production.

---

## ORM / Data Layer

SQLAlchemy 2.x

Responsibilities:

- model mapping
- database queries
- schema definitions

SQLAlchemy must be used in modern 2.x style.

---

## Database Migrations

Alembic

Responsibilities:

- schema migrations
- database versioning

All schema changes must be introduced through migrations.

---

## Authentication Tokens

JWT

Library:

PyJWT

Responsibilities:

- token signing
- token verification
- claim extraction

Tokens must be signed using secure keys.

---

## Password Hashing

Argon2

Library:

argon2-cffi

Responsibilities:

- secure password storage
- password verification

Plaintext password storage is forbidden.

---

## OAuth / External Login

Authlib

Used for:

- Google login
- OAuth2 flows

External providers must integrate through this library.

---

## Email Delivery

aiosmtplib ≥ 3.0

Used for:

- Sending transactional email (e.g., email verification)
- Async SMTP with STARTTLS on port 587

Templates are inline HTML + plaintext.

In development, if `SMTP_USER` or `SMTP_PASSWORD` is not set, the service logs the verification URL to stdout instead of sending an email.

---

## HTTP Client

httpx

Used for:

- Server-side HTTP requests
- reCAPTCHA v3 token verification against Google's API

---

## Bot Protection

Google reCAPTCHA v3

Used for:

- Registration endpoint
- Resend verification endpoint

The service performs a server-side score validation against `https://www.google.com/recaptcha/api/siteverify`. Requests scoring below `RECAPTCHA_MIN_SCORE` (default `0.5`) are rejected.

In development, if `RECAPTCHA_SECRET_KEY` is not set, all tokens are accepted (score `1.0`).

---

## Rate Limiting

In-memory sliding window rate limiter (`InMemoryRateLimiter`)

Applied to:

- `POST /v1/auth/register`: 5 requests per hour per IP
- `POST /v1/auth/resend-verification`: 3 requests per hour per email

Note: The in-memory implementation is process-local. For multi-process deployments, replace with a Redis-backed solution.

---

# Backend Project Structure

Backend code should follow the structure below.
