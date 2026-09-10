---
description: FastAPI controller, routing, Pydantic transport, dependency wiring, and error-mapping rules.
---

# REST Layer Rules

These rules apply to `apps/server/src/shifu/<module>/rest`, shared REST infrastructure,
and the web adapter consuming the API.

## One controller represents one action

Create one `<Action>Controller` class per HTTP action. It exposes a static
`handle(router: APIRouter) -> None` method that registers exactly one route:

```python
class CreateObjectiveController:
    @staticmethod
    def handle(router: APIRouter) -> None:
        @router.post('/objectives', status_code=201, response_model=ObjectiveDto)
        def _(
            body: _Body,
            learner_id: Annotated[Id, Depends(AuthPipe.get_learner_id)],
            objectives_repository: Annotated[
                ObjectivesRepository,
                Depends(DatabasePipe.get_objectives_repository),
            ],
        ) -> ObjectiveDto:
            use_case = CreateObjectiveUseCase(objectives_repository)
            return use_case.execute(
                learner_id=learner_id.value,
                title=body.title,
            )
```

The controller receives transport input, resolves dependencies, constructs the use
case, calls `execute`, and returns its result. It does not query SQLAlchemy directly,
call a vendor SDK, or implement domain policy.

## Use local Pydantic request schemas

Define a private `_Body`, `_Query`, or `_Response` Pydantic model in the controller
module when only that route uses it. Move a schema to `rest/schemas` only when several
controllers share the same transport shape.

Pydantic validates HTTP representation and basic shape. Business validation belongs in
domain structures and use cases. Do not expose SQLAlchemy models as request or response
models.

Use `response_model` for JSON responses so FastAPI generates an accurate OpenAPI
contract and filters unexpected fields. Never return passwords, tokens, private model
prompts, or infrastructure details from domain DTOs.

## Dependencies use Annotated ports

Declare dependencies with `Annotated[T, Depends(...)]`. Type repository and provider
parameters with core `Protocol` interfaces, not concrete adapters. Authentication pipes
return trusted domain identifiers or authorized entities rather than raw JWT payloads.

Construct the use case inside the route callback from those dependencies. Do not make
use cases FastAPI dependencies and do not store request-scoped dependencies on global
controller instances.

## Routes use resource language

- collection paths use plural nouns;
- dynamic parameters use semantic names such as `{objective_id}` or `{activity_id}`;
- nested resources express ownership only when the relationship matters to the API;
- action endpoints use a domain verb when ordinary HTTP resource semantics are not
  sufficient;
- route parameter names match controller arguments exactly.

Routers own prefixes and tags. Controllers register relative paths and do not repeat the
module prefix.

## Status codes and errors are explicit

Declare the successful `status_code` on every write route and use conventional HTTP
semantics: `200` for successful reads/updates with a body, `201` for creation, `202` for
accepted asynchronous work, and `204` for successful responses without a body.

Register one shared exception handler that maps transport-neutral domain errors:

- validation errors to `400`;
- authentication errors to `401`;
- authorization errors to `403`;
- not-found errors to `404`;
- conflicts to `409`;
- invalid preconditions or transitions to `422` when appropriate;
- unknown exceptions to `500` with a generic message.

The error body contains stable `title` and `message` fields. Log expected application
errors without stack-trace noise; log unexpected errors with diagnostic context but
never leak their implementation details to clients.

## Sync and async must match dependencies

Use a synchronous route callback when it executes synchronous SQLAlchemy repositories
or blocking providers. Use `async def` only for genuinely awaitable work. Never call a
blocking database or SDK operation directly from an async callback.

Long-running AI, indexing, email, or sandbox work returns an accepted response and
publishes an event for Inngest instead of holding the HTTP request open.

## Web transport preserves the boundary

The web REST client owns base URL, headers, credentials, timeouts, and transport-error
normalization. Feature services map typed operations to API methods and paths without
reimplementing backend business rules.

Browser code must not read or persist access tokens. Authenticated browser traffic uses
the BFF/session strategy defined in `documentation/architecture.md`; server-side BFF
calls attach the API credential at the trusted boundary.

## Keep API examples synchronized

When an endpoint changes, update its controller test, OpenAPI-facing schema, web
adapter, and any committed HTTP example in the same task. The controller integration
test is the authoritative executable HTTP contract.
