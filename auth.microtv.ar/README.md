# auth.microtv.ar

Identity service for the MicroTV platform.

This repository defines the service-level documentation for `auth.microtv.ar`, the component responsible for centralized authentication, authorization metadata, session handling, and identity provider integration across the platform.

`auth.microtv.ar` is not an isolated project. Its domain boundaries, security rules, API constraints, and migration context depend on the architecture defined in the `microtv-architecture` repository.

## Dependency on microtv-architecture

This repository must be read together with `microtv-architecture`, which is the architectural source of truth for:

- domain boundaries
- data ownership rules
- service interaction rules
- security model
- API contract conventions
- repository structure expectations
- migration roadmap

If this repository documentation conflicts with `microtv-architecture`, the architecture repository takes precedence.

## Service Scope

`auth.microtv.ar` belongs to the Identity Domain and is responsible for:

- user authentication
- user identities
- roles and role assignments
- memberships and tenant context
- sessions and refresh flows
- API keys
- external identity provider integration

This service must not manage operational entities such as companies, fleets, devices, routes, stops, or analytics data.

## Documentation

Service documentation lives in [`/docs`](./docs):

- [Architecture](./docs/ARCHITECTURE.md)
- [Domain Model](./docs/DOMAIN_MODEL.md)
- [API Specification](./docs/API_SPEC.md)
- [Diagrams](./docs/diagrams)

Recommended reading order:

1. [Architecture](./docs/ARCHITECTURE.md)
2. [Domain Model](./docs/DOMAIN_MODEL.md)
3. [API Specification](./docs/API_SPEC.md)
4. [Domain Model Diagram](./docs/diagrams/domain_model.md)
5. [Authentication Flow Diagram](./docs/diagrams/auth_flow.md)

## Repository Status

At the moment, this repository is documentation-first.

The current contents define the service contract and boundaries before or alongside implementation. Any future code, schema, or operational setup should remain consistent with the documentation in this repository and with `microtv-architecture`.

## Integration Role

Applications authenticate against `auth.microtv.ar`, receive tokens, and use those tokens to access other MicroTV services.

Other services rely on identity claims issued by this service, but they remain responsible for enforcing authorization within their own domain.

## Non-Goals

This repository does not redefine the platform architecture.

It also does not authorize:

- cross-service database access
- shared ownership of entities
- service-local authentication models outside the centralized identity model
- operational data management outside the Identity Domain
