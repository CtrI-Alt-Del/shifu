---
description: Pytest integration rules for Inngest functions, durable execution, persistence, and effects.
---

# Job Testing Rules

These rules apply to Inngest integration tests under
`apps/server/tests/messaging/inngest/jobs`, including the job tests that enter a
registered AgentOS workflow, and their separate runtime fixtures.

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

The canonical shared fixture is
`apps/server/tests/fixtures/inngest_fixture.py`, which exposes the
`inngest_fixture` pytest fixture and `InngestFixture` runtime handle. Shared pytest
fixtures under `apps/server/tests/fixtures` own:

- a FastAPI server on the configured local application port, using `7777` only as
  the fallback when no callback-port override is supplied;
- an isolated Inngest Dev Server container;
- PostgreSQL and other required Testcontainers;
- temporary environment configuration;
- readiness checks, bounded polling, and teardown.

The FastAPI callback port is an explicit configuration value so the Inngest container
can reach `http://host.docker.internal:<configured-port>/api/inngest` through the Linux
host-gateway mapping. `7777` is only the fallback configured port. The Inngest Dev
Server's mapped host port remains disposable and may be randomized. Wait for explicit
readiness rather than relying on fixed sleeps as the only synchronization mechanism.
Stop threads and containers and restore the environment in `finally` paths.

Job tests use the disposable Inngest and PostgreSQL Testcontainers owned by this
fixture. They must not depend on or mutate the persistent Docker Compose Inngest
instance used for local development. If Docker or the configured callback port is
unavailable, skip with the precise reason; CI must execute the same real-runtime
selection on a Docker-capable runner.

Start only infrastructure required by the job. A notification-only job does not need a
database unless its behavior actually persists state.

## Publish canonical events

Instantiate the domain event and send its `name` and serialized payload through the
Inngest event endpoint. Do not repeat event-name literals or build an alternative test
payload when the event class already defines the contract.

Dates use UTC ISO strings and IDs come from deterministic fixtures or domain factories.
Add malformed-payload coverage when transport validation or failure handling is part of
the job contract.

The integration fixture must use the same registered job group and real application
endpoint as production composition. For payload-validation jobs, include at least one
malformed or extra-field event assertion and verify that the job produces no forbidden
effect. Do not bypass Pydantic normalization by invoking private job helpers directly.

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

## AI/NLP jobs and subprocess behavior

When a job owns an AI/NLP capability, its integration scenarios also verify the
concrete local adapters and Agno composition under AI Layer Rules. Controlled
external inference/review endpoints may supply deterministic outputs and failures;
assert call counts, bounded retries/review, and persisted/public effects. Do not
invoke workflow internals or replace the composition with an approved-output mock
for scenarios intended to prove that composition.

## Workflows are tested in process, with mocked agents

Do not create a dedicated fixture to start an AgentOS registry or a test that sends
directly to its queue to verify a workflow. Controller tests may start the registries
as part of the application's normal lifespan through the shared TestClient. Those
tests prove HTTP behavior, persistence, and destination selection. A manual journey
may verify real registered execution. Changes to the workflow itself use the
in-process boundary below.

A workflow test lives under
`apps/server/tests/<module>/ai/workflows/test_<name>_workflow.py`, builds the Agno
`Workflow` with its real use cases over the disposable PostgreSQL and Redis, replaces
every agent with a `unittest.mock.Mock` specced from the agent class, and runs it with
`arun` as the runtime does. Mocked agents script approvals, rejections, failures and
their usage reports; routing, context and catalog providers are mocks. Answer quality
is proved by the evals under `apps/server/evals`, not by workflow tests. A job test
proves only the job's own admission, idempotency and persisted effect through the real
Inngest runtime.
