---
description: Python domain-event, broker, Inngest registration, durable-step, and delivery rules.
---

# Messaging Layer Rules

These rules apply to module-owned messaging code under
`apps/server/src/shifu/<module>/messaging`, shared Inngest infrastructure, and domain
events consumed asynchronously.

## Core owns events and the broker port

Domain events live in the originating module's `core/domain/events`. Each event class
declares one stable `name` and constructs a typed, serializable payload. Publishers,
jobs, and tests import the event class instead of repeating its name or payload shape.

The shared core exposes a narrow broker protocol:

```python
class Broker(Protocol):
    def publish(self, event: Event[object]) -> None: ...
```

Use cases depend on the protocol, never on the Inngest SDK. The concrete
`InngestBroker` converts a domain event to an Inngest event at the infrastructure
boundary.

## Event data is authoritative and serializable

The originating module authenticates the actor, validates permission, loads its own
state, and builds the event. A browser cannot supply an authoritative domain snapshot.

Payloads contain only the identifiers and immutable data required by consumers. Use
JSON-safe primitives and ISO 8601 UTC strings at the transport boundary. Do not include
ORM models, open sessions, provider clients, secrets, or mutable domain objects.

Consumers normalize and validate payloads before doing work. They must not reach into
another module's private repositories to reconstruct missing event data.

## Shared infrastructure owns one Inngest endpoint

Shared messaging creates the Inngest client, broker adapter, base job helpers, and one
FastAPI endpoint. Application composition registers every module-owned function with
that endpoint.

Modules own their jobs:

```text
<module>/messaging/inngest/jobs/
├── evaluate_activity_submission_job.py
└── award_learning_rewards_job.py
```

A module must not create another Inngest HTTP endpoint or register jobs as an import
side effect.

## Jobs expose explicit functions

Use one `<Action>Job` class per file. The class declares a stable `FUNCTION_ID` and a
static `handle(inngest)` method that returns the SDK function created with
`inngest.create_function`.

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

## Mutation and publication must be reliable

When an operation changes official state and must publish a corresponding event, the
state mutation and event record belong in one database transaction through a
transactional outbox. An Inngest relay publishes committed outbox rows and marks them
delivered only after acknowledgement.

Direct broker publication is acceptable only for explicitly best-effort effects or
operations with no coupled database mutation. Do not publish before a request
transaction commits and assume that this is atomic.

Consumers remain idempotent because delivery can occur more than once. Failed outbox
rows remain visible and retryable with bounded backoff; they are not silently dropped.

## Failures preserve domain truth

Known invalid input or terminal domain state is non-retriable. Transient database,
network, rate-limit, or provider failures remain retriable. Configure finite retries and
use a failure handler when the domain needs a visible failed state.

Never mark an operation successful before its required durable effects complete.
Preserve previously committed successful steps when a later step fails.
