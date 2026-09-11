---
description: FastAPI controller, route grouping, dependency wiring, and HTTP boundary rules.
---

# REST Layer Rules

These rules apply to FastAPI code under `apps/server/src/shifu/*/rest` and its
matching tests under `apps/server/tests/rest`.

## Routers own module prefixes

Each module exposes a router class ending in `Router`. Its static `register` method
creates and returns an `APIRouter`, including the module prefix and tags when
applicable. The application factory composes these routers; controllers must not
create applications or include module routers directly.

```python
class LearningRouter:
    @staticmethod
    def register() -> APIRouter:
        router = APIRouter(prefix='/learning', tags=['learning'])
        StartSessionController.handle(router)
        return router
```

Router registration must be safe when `create_app()` is called repeatedly. Do not
store mutable routers or application instances in controller class state.

## Controllers register routes consistently

Controller modules follow the structure established by
`shifu/shared/rest/controllers/check_health_controller.py`:

- expose a controller class ending in `Controller`;
- expose a `@staticmethod` named `handle` that receives an `APIRouter` and returns
  `None`;
- register routes through nested functions declared inside `handle`;
- name nested route handlers `_`; multiple `_` declarations are allowed because
  FastAPI retains each decorated function when it is registered;
- declare the path, `response_model`, and numeric `status_code` explicitly on each
  route decorator;
- return the declared Pydantic response model instead of an ad hoc dictionary; and
- never define `__all__`.

```python
from fastapi import APIRouter
from pydantic import BaseModel


class Response(BaseModel):
    status: str


class CheckHealthController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.get('/health', response_model=Response, status_code=200)
        def _() -> Response:
            return Response(status='ok')
```

## Response models stay with their controllers

Declare HTTP response models in the controller module and name the response model
`Response`. Keep one response contract per controller.

Response models own transport validation and serialization only. They must not
authorize requests, access persistence, execute business rules, or become domain
entities. Nested response objects may use additional private controller-local
Pydantic models when needed.

## Controllers remain HTTP adapters

A business controller normally represents one application action. It may only:

- receive and validate HTTP input;
- obtain dependencies through FastAPI dependency injection;
- translate transport input into a use-case request;
- execute the use case; and
- translate the result or expected failure into the declared HTTP response.

Validation beyond transport shape, authorization decisions, persistence operations,
domain mapping, and business rules belong outside controllers.

## Dependencies point inward

Controllers depend on core interfaces and use cases, never concrete database,
messaging, or provider implementations. FastAPI dependency functions may resolve
infrastructure implementations, but the value received by the controller remains
typed by the core interface.

Construct a use case from its required interfaces at the boundary unless an approved
application-layer factory owns that construction. Do not place use cases, repositories,
or sessions in module-level mutable state.

## Inputs use semantic names and Pydantic validation

Dynamic route parameters identify the represented resource or relationship. Use
names such as `{account_id}`, `{session_id}`, and `{lesson_id}`; never use a generic
`{id}`. The handler argument and tests must use the same name.

Use Pydantic request models for JSON bodies. Query and path primitives may remain
typed handler parameters when no reusable validation object is needed. Transport
models must not duplicate domain behavior or expose persistence models.

## HTTP contracts are explicit

Use plural resource paths for collections and nest resources beneath their owner
when ownership matters. Keep module prefixes in routers and action-specific path
segments in controllers.

Every endpoint must define its successful response model and status. Document and
test expected error statuses. Do not expose exception details, credentials,
authorization headers, database errors, or internal implementation names in error
responses.

Health endpoints must remain deterministic and must not perform destructive checks.
Readiness checks may inspect required dependencies but must use bounded operations
and report only safe status information.

## Async handlers require async work

Use `async def` only when the handler awaits non-blocking operations. Keep handlers
synchronous when their dependency chain is synchronous. Never run synchronous
SQLAlchemy sessions or blocking SDK calls directly on the event loop.

## Controller tests use HTTP

Place controller integration tests under
`apps/server/tests/rest/controllers/<module>/`. Keep one test file per controller
route contract. Tests must use FastAPI `TestClient` or the project-approved async HTTP
client against an application created by `create_app()`; do not call nested handlers
or controller methods directly.

Controller tests cover, as applicable:

- the successful status and serialized body;
- request validation failures;
- authentication and authorization outcomes;
- expected use-case error translation; and
- dependency overrides without real network or persistence access.

Define shared application and HTTP-client fixtures in `apps/server/tests/conftest.py`.
Keep scenario-specific dependency overrides near the owning tests and ensure they are
cleared after each scenario.

## Keep contracts synchronized

When a route path, parameter, request body, response model, or status changes, update
its router registration, controller tests, API examples, web REST client contract,
and applicable Spec in the same delivery. A mocked controller test does not prove a
real database, authentication, message, or streaming integration; validate those
boundaries at the narrowest real integration level that can establish the criterion.
