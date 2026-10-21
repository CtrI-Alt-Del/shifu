---
description: FastAPI application composition, router registration, middleware, and dependency-pipe rules.
---

# Server Application Rules

These rules apply to the FastAPI entrypoint, application class, composition layer,
routers, middleware registration, and dependency pipes under `apps/server/src/shifu`.

## Keep the entrypoint minimal

`apps/server/src/main.py` exports the application created by `shifu.app`. It must not
construct repositories, register individual controllers, or contain business logic.

`shifu.app.FastAPIApp.register` owns FastAPI creation and top-level registration. The
class may contain the application lifespan and static registration helpers, while the
module-level `app` remains the export consumed by `main.py`. Keep registration safe to
call repeatedly in tests; do not hide global mutable application state in imports.

Register the shared `AppErrorHandler` from the application class once. Controllers do
not install exception handlers or translate unexpected exceptions locally.
The shared handler owns safe client-facing error serialization; messages returned by
the server API must be in Brazilian Portuguese, including framework request-validation
and HTTP errors.

## Composition owns concrete wiring

Composition is the only layer allowed to know the complete set of modules and concrete
adapters. It registers:

- module routers;
- global exception handlers;
- middleware in deliberate order;
- shared lifecycle hooks;
- the single Inngest endpoint;
- the Intelligence and Learning AgentOS registry lifecycles;
- environment-specific infrastructure.

The local FastAPI application uses the explicit `SHIFU_SERVER_APP_PORT` setting;
`7777` is only its fallback when the setting is absent. When Inngest runs in Docker,
the application must bind an address reachable through the host-gateway mapping and
expose the single `/api/inngest` callback registered by composition. The callback URL
must use the configured port rather than assuming `7777`.

Business modules must not import the application factory or another module's
composition code.

The application class is also the composition boundary for the shared Inngest
endpoint, destination-aware outbox relay, module-owned non-AI job functions, and the
two active module AgentOS registries. It enters Intelligence then Learning and exits
in reverse order. It exposes existing Core consumer ports and shared technical
providers, but does not import individual Workflow classes or assemble module
business dependencies. Each registry registers only its own native workflows and
owns its queue, schemas, pools, clients, and shutdown. Keep registration explicit and
idempotent; importing a module must not start a listener, open a connection, run a
migration, or register a route.

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
- invoke the shared `AuthenticationProvider` and return `AuthenticatedUser`;
- load and authorize a resource reused by several controllers;
- construct an AI workflow or external provider.

Owning modules may also expose ordinary request-independent `create_*` factories for
their workflow registry to assemble providers and Core use cases. Such factories
return typed Core ports/actions and accept explicit dependencies; they do not accept
FastAPI `Request`, use `Depends` outside HTTP getters, or capture a request session.
Only each active module's named workflow registry may compose its own providers,
Core operations, native AgentOS runtime, and registrations. This narrow exception
does not permit generic workflow catalogues, cross-module concrete imports, or AI
code to own authorization and persistence policy.

Use `typing.Annotated` with `fastapi.Depends` at controller boundaries. Dependency
return types are core interfaces or domain values whenever possible.

Pipes are application wiring. They may perform authentication and reusable resource
authorization, but must not become a general home for use-case business logic.

## Request-wide lifecycle has one owner

Middleware may manage technical concerns that must wrap the complete request. When a
request-scoped SQLAlchemy middleware is selected as the transaction owner, it:

1. creates the session;
2. places it on `request.state`;
3. calls the next handler;
4. commits only after a successful response path;
5. rolls back when an exception escapes;
6. always closes the session.

Do not create or close the request session inside each repository or controller.
Middleware must not swallow domain exceptions or serialize application errors.

A module may instead expose a database context manager as the sole transaction owner
for an operation. In that model, application composition provides the database port,
the use case enters the context manager, and no middleware creates, commits, rolls
back, or closes the same transaction. Never combine the two ownership models in one
execution path.

## Lifecycles are explicit

Use FastAPI lifespan hooks for process-owned resources such as pools, clients, and
background relays. Request-owned resources belong in dependencies or middleware.
Importing a module must not open network connections, run migrations, seed data, or
start workers.

The shared outbox broker and both module AgentOS registries are process-owned
resources. Application lifespan starts them in dependency order and shuts them down
in reverse order; each registry closes only its own queues, schemas/pools, clients,
and workers. A Learning provider borrowed from Intelligence remains alive until
Learning has stopped. Module registrars do not start resources during import.

Application bootstrap never resets or seeds a database. Migrations and seed commands
remain explicit operational commands.
