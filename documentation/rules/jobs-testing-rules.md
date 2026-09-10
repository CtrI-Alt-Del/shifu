---
description: Pytest integration rules for Inngest functions, durable execution, persistence, and effects.
---

# Job Testing Rules

These rules apply to Inngest integration tests under
`apps/server/tests/messaging/inngest/jobs` and their shared runtime fixtures.

## Test jobs through a real Inngest runtime

A job integration test exercises the actual applicable path:

```text
domain event → Inngest Dev Server → FastAPI Inngest endpoint
             → registered job → durable steps → use case/adapters → effect
```

Do not call `Job.handle`, the generated function callback, a step callback, or the core
use case directly. Direct invocation cannot prove event discovery, serialization,
registration, retries, durable steps, or failure handling.

Use one mirrored test module per job and a class named `Test<Action>Job`.

## Runtime fixtures own infrastructure

Shared pytest fixtures under `apps/server/tests/fixtures` own:

- a FastAPI server on an available local port;
- an isolated Inngest Dev Server container;
- PostgreSQL and other required Testcontainers;
- temporary environment configuration;
- readiness checks, bounded polling, and teardown.

Use random available ports and wait for explicit readiness. Do not rely on fixed sleeps
as the only synchronization mechanism. Stop threads and containers and restore the
environment in `finally` paths.

Start only infrastructure required by the job. A notification-only job does not need a
database unless its behavior actually persists state.

## Publish canonical events

Instantiate the domain event and send its `name` and serialized payload through the
Inngest event endpoint. Do not repeat event-name literals or build an alternative test
payload when the event class already defines the contract.

Dates use UTC ISO strings and IDs come from deterministic fixtures or domain factories.
Add malformed-payload coverage when transport validation or failure handling is part of
the job contract.

## Assert completion and observable effects

Wait with a monotonic, bounded timeout until the run reaches a terminal state or the
expected effect appears. On timeout, fail with diagnostic information rather than
polling forever.

Assert the result that matters:

- persisted state through a new inspection session;
- published child events and payloads;
- provider calls captured by an approved controlled fake;
- created or removed files;
- idempotency after duplicate delivery;
- failed state and absence of forbidden effects.

Do not treat an HTTP `200` from event submission or a completed run as sufficient proof
when the job is expected to change state.

## Use real adapters where practical

Keep SQLAlchemy repositories and local infrastructure real. Prefer Testcontainers or an
emulator for services that can run reliably in CI. Monkeypatch the outer provider method
only when no practical local service exists, and assert the complete interaction.

Core use-case unit tests own exhaustive business-rule coverage. Job tests select the
critical scenarios that can fail because of event mapping, durable execution, retries,
provider composition, transactions, or idempotency.

## Isolate scenarios

Clean database tables and fake interaction history before every test. Complete the
current Inngest run before resetting shared state. Tests must pass independently and in
any order.

Use a separate, Docker-capable pytest selection for Inngest integration tests. CI must
run it; local Docker unavailability may produce an explicit skip but does not count as
passing integration evidence.
