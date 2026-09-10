---
description: FastAPI application composition, router registration, middleware, and dependency-pipe rules.
---

# Server Application Rules

These rules apply to the FastAPI entrypoint, application factory, composition layer,
routers, middleware registration, and dependency pipes under `apps/server/src/shifu`.

## Keep the entrypoint minimal

`apps/server/src/main.py` exports the application created by `shifu.app`. It must not
construct repositories, register individual controllers, or contain business logic.

`shifu.app.create_app` owns FastAPI creation and top-level registration. Keep it safe to
call repeatedly in tests; do not hide global mutable application state in imports.

## Composition owns concrete wiring

Composition is the only layer allowed to know the complete set of modules and concrete
adapters. It registers:

- module routers;
- global exception handlers;
- middleware in deliberate order;
- shared lifecycle hooks;
- the single Inngest endpoint;
- environment-specific infrastructure.

Business modules must not import the application factory or another module's
composition code.

## Routers group controllers

Each business module exposes one top-level router from its `rest/router.py`. A router
sets the module prefix and tags, then registers controller classes through their
`handle(router)` methods. Large modules may compose smaller routers by resource.

Routers contain no use cases, validation, persistence, or business rules. Route
registration remains explicit so the application surface can be reviewed from the
composition tree.

## Pipes provide FastAPI dependencies

Dependency factories belong in the owning module's `pipes` package or in
`shifu/shared/pipes` when genuinely shared. A pipe may:

- obtain a request-scoped SQLAlchemy session or Inngest client;
- construct a concrete adapter behind a core `Protocol`;
- validate authentication and return a trusted identity;
- load and authorize a resource reused by several controllers;
- construct an AI workflow or external provider.

Use `typing.Annotated` with `fastapi.Depends` at controller boundaries. Dependency
return types are core interfaces or domain values whenever possible.

Pipes are application wiring. They may perform authentication and reusable resource
authorization, but must not become a general home for use-case business logic.

## Middleware owns request-wide lifecycle

Middleware may manage technical concerns that must wrap the complete request. A
request-scoped SQLAlchemy middleware:

1. creates the session;
2. places it on `request.state`;
3. calls the next handler;
4. commits only after a successful response path;
5. rolls back when an exception escapes;
6. always closes the session.

Do not create or close the request session inside each repository or controller.
Middleware must not swallow domain exceptions or serialize application errors.

## Lifecycles are explicit

Use FastAPI lifespan hooks for process-owned resources such as pools, clients, and
background relays. Request-owned resources belong in dependencies or middleware.
Importing a module must not open network connections, run migrations, seed data, or
start workers.

Application bootstrap never resets or seeds a database. Migrations and seed commands
remain explicit operational commands.
