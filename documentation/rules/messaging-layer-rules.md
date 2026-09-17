---
description: Python domain-event repository, database-listening Inngest relay, job registration, durable-step, and delivery rules.
---

# Messaging Layer Rules

These rules apply to module-owned messaging code under
`apps/server/src/shifu/<module>/messaging`, shared Inngest infrastructure, and domain
events consumed asynchronously.

## Core owns events and the event-repository port

Domain events live in the originating module's `core/domain/events`. Each event class
declares one stable `name` and constructs a typed, serializable payload. Publishers,
jobs, and tests import the event class instead of repeating its name or payload shape.

The shared core exposes `EventsRepository`. Use cases add canonical events through the
repository available in their module database transaction:

```python
class EventsRepository(Protocol):
    def add(self, event: Event[object]) -> None: ...
```

Use cases never depend on `InngestBroker`, the Inngest SDK, or a network publisher.
`EventsRepository.add` persists the event in the shared outbox through the active
module transaction. Shared infrastructure may extend the repository contract with
typed subscription, reservation, retry and completion operations; these operations
are for the relay and do not become use-case dependencies.

## Event data is authoritative and serializable

The originating module authenticates the actor, validates permission, loads its own
state, and builds the event. A browser cannot supply an authoritative domain snapshot.

Payloads contain only the identifiers and immutable data required by consumers. Use
JSON-safe primitives and ISO 8601 UTC strings at the transport boundary. Do not include
ORM models, open sessions, provider clients, secrets, or mutable domain objects.

Consumers normalize and validate payloads before doing work. They must not reach into
another module's private repositories to reconstruct missing event data.

## Shared infrastructure owns one Inngest endpoint

Shared messaging creates the Inngest client, database-listening broker relay, base job
helpers, and one FastAPI endpoint. Application composition starts one broker listener
and registers every module-owned function with that endpoint.

Shared Inngest infrastructure uses the `shared/messaging/inngest` package boundary:

```text
shared/messaging/inngest/
├── __init__.py
├── inngest_broker.py
├── inngest_client.py
├── inngest_messaging.py
├── inngest_settings.py
└── jobs/
```

`InngestBroker` belongs in `inngest/inngest_broker.py` and is exported from that
package when composition needs it. Do not place it in a generic `brokers` package,
create a second shared Inngest endpoint, or expose the Inngest SDK through core
interfaces.

Use one shared `InngestMessaging.register(...)` call to create the client and serve the
endpoint. Each business module declares its own functions through a module boundary
such as `IdentityInngestMessaging.register_jobs(inngest)`, which returns the functions
to the shared registrar. The module registrar must not call `serve`, create another
client, or register functions during import.

Modules own their jobs:

```text
<module>/messaging/inngest/jobs/
├── evaluate_activity_submission_job.py
└── award_learning_rewards_job.py
```

A module must not create another Inngest HTTP endpoint or register jobs as an import
side effect.

The shared Inngest settings boundary lives at
`apps/server/src/shifu/shared/messaging/inngest/inngest_settings.py`; client creation
lives in `inngest_client.py`. `InngestMessaging.register()` must create the client
through `InngestClient.create()` and pass the resulting client to the single shared
serve registration.

## Jobs expose explicit functions

Use one `<Action>Job` class per file. The class declares a stable `FUNCTION_ID` and a
static `handle(inngest)` method that returns the SDK function created with
`inngest.create_function`.

Each job class also declares its trigger as a static class attribute named
`_EVENT_NAME: ClassVar[str]`. The trigger must reference that attribute rather than
repeating a string literal. The Identity main-page logging job therefore keeps
`_EVENT_NAME = 'app/main-page.entered'` as its canonical trigger declaration.

Validate every incoming job payload with a strict Pydantic model at the job boundary.
Reject unknown fields, require non-empty identifiers, and validate timestamp fields as
UTC ISO-8601 values before durable steps construct or log normalized data. Pydantic
validation belongs at the transport boundary; domain rules remain in core use cases.

Jobs translate events into durable work. They may:

- normalize a payload;
- open explicit infrastructure scopes;
- execute core use cases or AI workflows;
- publish follow-up domain events;
- map terminal failure to a recoverable domain status.

Jobs do not reproduce business rules from use cases. Do not call one job's callback
directly from another job; publish an event or use an explicitly modeled child function.

## Durable steps are small and idempotent

Place independently retryable side effects in named `context.step.run` calls. Step names
are stable identifiers, not prose that changes casually. Normalize transport data in an
early step before constructing domain structures.

A retried step must not duplicate official attempts, progress, XP, achievements,
notifications, or files. Use domain idempotency keys, unique constraints, expected
state, or compare-and-set persistence where necessary.

Synchronous SQLAlchemy and blocking SDK work must not block the async event loop. Run
it in a worker thread or use a synchronous execution boundary supported by the SDK.
Each durable database step opens its own session context and commits the state needed by
later steps.

## Fan-out publishes individual events

Batch work uses one fan-out job that emits an existing individual event per item. Each
child remains independently retryable and observable. Do not process an unbounded
collection in one step or erase successful siblings when one item fails.

## Events are persisted before Inngest publication

Every use-case-originated event is added through `EventsRepository`, including events
whose only purpose is observability. When an operation also changes official state,
the state mutation and event row belong to the same module database transaction.
Operations with no business mutation still open the owning module transaction for the
event insert.

`InngestBroker` is a long-lived shared database listener and relay, not a use-case
publisher. PostgreSQL notifies it of committed event changes. It reserves eligible
rows, sends them directly through the Inngest client using the stable event-row ID,
and marks them published only after acknowledgement. Never call Inngest directly from
a use case, controller, repository, or page request.

Database notifications are a latency optimization, not the durability boundary. The
broker drains eligible rows on startup and reconnect before waiting for subsequent
notifications, so missed notifications do not lose committed events. Its wait ends on
either a database notification or the repository's earliest event-availability or
reservation-expiry deadline, with a bounded maximum idle interval. Before claiming more
work it releases expired reservations. This timer path guarantees retries even when no
new database change produces another notification. Listener shutdown must unlisten and
release owned resources cleanly. A PostgreSQL `LISTEN` connection is a dedicated
psycopg connection, not a SQLAlchemy pooled wrapper whose rollback can block while
`notifies()` is waiting. Close that owned driver connection during unlisten and never
share it with transactional repository work.

Consumers remain idempotent because delivery can occur more than once. Failed outbox
rows remain visible and retryable with bounded backoff; they are not silently dropped.

Keep broker tuning values as typed `ClassVar` constants on `InngestBroker`, including
the drain limit, reservation duration, idle limit, attempt limit, delivery backoff,
and reconnect backoff. Current time comes from an injected `ClockProvider` (normally
`SystemClockProvider`), never from a free `_utc_now()` helper or direct clock access
inside relay logic.

The PostgreSQL notification implementation belongs under
`shared/database/sqlalchemy/repositories/listeners/`. The events repository delegates
to that listener boundary and remains responsible for transactional outbox operations;
the listener owns its dedicated driver connection and notification lifecycle.

## Failures preserve domain truth

Known invalid input or terminal domain state is non-retriable. Transient database,
network, rate-limit, or provider failures remain retriable. Configure finite retries and
use a failure handler when the domain needs a visible failed state.

Never mark an operation successful before its required durable effects complete.
Preserve previously committed successful steps when a later step fails.
