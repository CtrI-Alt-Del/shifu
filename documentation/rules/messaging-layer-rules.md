---
description: Domain-event, broker, Inngest job, fan-out, and NestJS messaging composition rules.
---

# Messaging Layer Rules

These rules apply to shared messaging infrastructure, module-owned messaging
adapters, domain events consumed asynchronously, and application composition of
Inngest functions.

## Core owns domain events and the broker contract

Domain events belong to the module that defines their meaning under:

```text
packages/core/src/<module>/domain/events/
```

Each event is a class that extends the shared `Event`, declares a static `_NAME`,
and types its complete payload. Event names must describe the domain occurrence;
do not expose an implementation detail such as the AI provider in the name.

```ts
export class DocumentGenerationRequestedEvent extends Event<Payload> {
  static readonly _NAME = 'document-production/document.generation-requested'
}
```

Publishers and consumers import `_NAME`; they must not repeat the event-name
literal. When a job creates a child event, instantiate the domain event and send
its `name` and `payload` instead of recreating an untyped object.

The shared event repository contract remains deliberately small:

```ts
export interface EventsRepository {
  add(event: Event): Promise<void>
}
```

Core use cases depend on their module database and call
`scope.eventsRepository.add(event)`, never on `InngestClient`. The repository is
available in every module database scope and inserts one pending row in the shared
`events` table through that transaction. `InngestBroker` is the shared Server
relay: it listens for committed rows and sends them directly through
`InngestClient`; it is not injected into use cases.

## The originating module builds authoritative event data

A module that requests asynchronous work must load and authorize its own data
before publishing the event. Consumers must not reach into repositories owned by
the originating module merely to reconstruct the request.

For document generation, Consulta, Formalização, or Caso builds the complete
`DocumentGenerationSource` snapshot before publishing. The snapshot contains a
discriminated `type`, the owning entity reference, and its unstructured `data`.
Document Production may persist that snapshot for traceability, but it must not
replace it by reading repositories from those modules.

Do not accept an authoritative source snapshot assembled by the browser. A
controller receives references and action options; its module use case validates
permission, loads domain data, builds the snapshot, and then publishes.

## Shared messaging owns the Inngest infrastructure

Shared infrastructure belongs under:

```text
apps/server/src/shared/messaging/
├── inngest/
│   ├── inngest-client.ts
│   ├── inngest-job.ts
│   ├── inngest-options.ts
│   ├── jobs/
│   │   └── inngest-broker.ts
│   └── inngest.module.ts
└── shared-messaging.module.ts
```

There is exactly one Inngest HTTP endpoint, served by the controller under the
shared REST layer. A feature must not create its own Inngest controller or reuse
another feature's controller. Adding a job must not alter the behavior or route
of existing jobs such as WhatsApp processing.

The application composition registers every exported Inngest job function in the
single Inngest endpoint. A feature messaging module owns and exports its jobs; the
feature root module imports that messaging module. Database-triggered workers are
Nest providers, not Inngest functions: they do not expose `this.function` and are
not added to the Inngest function registry. An environment-gated recovery function
may be provided by the application root when its owning shared module must remain
free of that provider in environments where recovery is disabled; the root must
use the validated environment mode for both provider construction and function
registration so the two sets cannot diverge.

## Inngest jobs expose `this.function`

Every Inngest job is an injectable class that extends `InngestJob` and assigns a
typed function in its constructor:

```ts
@Injectable()
export class ExampleJob extends InngestJob {
  readonly function: InngestFunction.Like

  constructor(inngest: InngestClient, dependency: Dependency) {
    super(inngest)
    this.function = this.inngest.createFunction(/* ... */)
  }
}
```

Do not put a generic `handle(context)` method in the base class and do not pass a
handler through `super`. Those shapes erase the event-specific inference that
`createFunction` provides. Dependencies, including repository tokens or core
interfaces, may be injected normally through NestJS.

Jobs coordinate durable execution and translation between events. Business
decisions belong to core use cases. A job may invoke a workflow or use case, but
must not reproduce its rules inline.

## Event schemas validate transport payloads

An Inngest trigger uses `eventType` with the domain event's `_NAME` and a Zod
schema for its serialized payload. Dates cross the transport boundary as ISO
date-time strings and are converted back to `Date` only when constructing a
domain event or domain input that requires it.

The transport schema and domain payload must describe the same fields. A job
must forward the full validated input required by the next workflow rather than
silently loading an alternative payload from unrelated modules.

## Fan-out publishes individual domain events

Batch work uses a dedicated batch domain event and a dedicated fan-out job. The
fan-out job publishes one existing individual event per item with
`step.sendEvent`; it does not call another job's function directly and does not
use `step.invoke`.

```text
DocumentBatchGenerationRequestedEvent
  -> GenerateDocumentsInBatchJob
      -> DocumentGenerationRequestedEvent (one per document)
          -> GenerateDocumentJob
```

Use the array form of `step.sendEvent` so the fan-out is a durable, memoized
Inngest step. Each child event must remain independently retryable and
reprocessable. Success or failure of one child must not erase successful sibling
work.

## Transactional event persistence is the reliability boundary

The originating module persists events through its database scope. Do not publish
directly from a use case after the transaction commits, because a process failure
between the mutation and publication could lose the event.

When an approved requirement does require atomic mutation and publication, call
`scope.eventsRepository.add(event)` while the originating module's database
transaction is active. The module-scoped EventsRepository persists the complete
event through that transaction.
Shared database owns the `events` outbox model and persistence types under
`apps/server/src/shared/database/drizzle/outbox/`, and the Drizzle adapter at
`apps/server/src/shared/database/drizzle/drizzle-outbox-database.ts`, while the
provider-neutral `OutboxDatabase` contract belongs in
`packages/core/src/shared/interfaces/`; shared messaging owns `InngestBroker`.
The Server composition layer owns the Nest worker that listens to a PostgreSQL
`LISTEN/NOTIFY` channel emitted after an outbox
insert commits, reads and reserves pending rows through a database interface,
publishes each row directly through `InngestClient` with the event row ID as the
external event ID, then marks the row published only after acknowledgement. It
must not write a second event row. Notifications
are a latency optimization and are not the durability boundary: startup and
reconnect drain pending rows, while `ReprocessEventsJob` remains the periodic
recovery path. Inngest owns consumer retries; the outbox does not track
per-consumer delivery.
The consuming feature still owns its jobs and business side effects, and the
outbox does not move Communication email ownership into Identity or shared
infrastructure.

Shared database infrastructure provides the singleton `DatabaseTransactionContext`.
Shared messaging imports that database module and owns `InngestBroker`,
`InngestClient`, and publish/reprocessing/cleanup jobs in one acyclic module; do not
create an outbox module that imports its parent messaging module. `InngestBroker` claims
only pending rows. Failed publication uses bounded backoff and a finite automatic
attempt cap; a separate reprocessing job returns only eligible failed or
expired-reservation rows to pending, while terminal failures remain visible for operator
action.

`ReprocessEventsJob` is registered and scheduled only in local and test environments.
Staging and production rely on startup/reconnect draining; environment composition
must not instantiate or register the reprocessor in `stg` or `prod`.

Call the expiring worker ownership a `reservation`, not a lease or database lock.
Reservation columns use `reserved_by` and `reservation_expires_at`; guarded completion
updates must match the current reservation owner. Feature Specs fix batch size,
reservation duration, ownership format, operational signals, and any manual recovery
contract when those details affect concurrency or recovery evidence.
