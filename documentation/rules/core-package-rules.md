---
description: Framework-independent domain organization and dependency rules for Python core modules.
---

# Core Domain Rules

These rules apply to `apps/server/src/shifu/<module>/core` and shared domain primitives
under `apps/server/src/shifu/shared/core`.

## Core is framework-independent

Core code may use the Python standard library and provider-neutral domain abstractions.
It must not import FastAPI, Pydantic request models, SQLAlchemy, Inngest, HTTP clients,
environment settings, or vendor SDKs.

Each business module owns its core:

```text
<module>/core/
├── domain/
│   ├── entities/
│   ├── structures/
│   ├── errors/
│   └── events/
├── interfaces/
└── use_cases/
```

Do not move module-specific behavior into `shared`. Shared core contains only stable
primitives and contracts genuinely used by multiple modules.

## Entities own identity and behavior

Entities have stable identity and encapsulate state transitions that are valid for one
instance. Construct them through a `create` classmethod or another explicit named
factory that validates and normalizes input.

Entity equality is based on domain identity. Do not expose SQLAlchemy models as domain
entities, and do not make an entity inherit from Pydantic or SQLAlchemy classes.

An entity may protect its own invariants, such as a valid state transition. Decisions
that coordinate repositories, providers, several aggregates, permissions, or external
effects belong in a use case.

## Structures are immutable values

Structures and value objects represent validated values, states, filters, snapshots,
or relationships without independent identity. Keep them immutable and compare them by
value. Use explicit factories such as `Id.create`, `Email.create`, or
`LearningStatus.normalize` to validate primitive input.

Only entities own a bare `id`. A structure may carry an explicitly named reference such
as `objective_id` or `learner_id`.

DTOs are serializable data carriers. They do not validate business policy or perform
I/O. Domain objects may expose a `dto` projection, but HTTP schemas and persistence
models remain outside core.

## Use cases own application actions

Create one use-case class per application action under `core/use_cases`. Name it with a
business verb and the `UseCase` suffix, and expose one `execute` method.

Use cases:

- normalize primitive input into domain structures;
- enforce authorization and cross-entity business rules;
- coordinate entities, repositories, providers, and events;
- return a domain DTO, structure, primitive, or `None`;
- raise typed domain errors for expected failures.

Use cases must not receive `Request`, `Session`, FastAPI dependencies, SQLAlchemy
models, Inngest contexts, or vendor clients.

## Interfaces are structural ports

Repository, provider, broker, storage, AI workflow, clock, and external-service
contracts belong in the owning module's `core/interfaces` directory. Define them as
`typing.Protocol` unless a shared implementation base contains real reusable behavior.

```python
from typing import Protocol


class ObjectivesRepository(Protocol):
    def find_by_id(self, objective_id: Id) -> Objective | None: ...

    def add(self, objective: Objective) -> None: ...
```

Keep ports narrow and domain-oriented. They must not expose query builders, database
sessions, HTTP responses, Inngest events, or SDK-specific types. Implementations live
in database, provider, messaging, or AI adapter layers.

## Domain errors are transport-neutral

Expected failures derive from the shared `AppError` hierarchy or a module-specific
subclass. Errors expose stable domain meaning and a safe user-facing message; they do
not contain HTTP status codes or FastAPI response objects.

The REST layer maps domain error classes to HTTP responses. Jobs decide which failures
are retryable without changing the domain error itself.

## Events describe facts or requests

Domain events belong to the module that owns their meaning. Each event declares its
name once and owns a typed, serializable payload. Names use a stable namespace such as:

```text
learning/activity-submission.requested
learning/activity-evaluated
identity/account-deletion.requested
```

Publishers and consumers import the event class; they do not repeat event-name literals
or rebuild payload dictionaries independently. Payloads contain identifiers and
immutable snapshots needed by the consumer, never ORM models or secrets.

## Module boundaries remain explicit

A module may consume another module through identifiers, public contracts, and domain
events described in `documentation/modules.md`. It must not import another module's
entities, repositories, database models, or implementation details merely to avoid a
contract.

Learning remains authoritative for learner progress and official evaluation;
Curriculum for official content; Identity for account state; Gamification for rewards;
and Intelligence for AI-assisted experiences. Technical adapters do not transfer that
authority.

## Fakers build valid domain objects

Domain fakers belong under `apps/server/src/shifu/fakers/<module>` and mirror entities
or structures. Use one `<Entity>Faker` class per concept with a `fake` method and add
`fake_many` only when collection scenarios need it repeatedly.

Defaults must produce valid domain objects. Allow explicit keyword overrides so tests
state only the behavior-specific differences. Fakers contain no business behavior and
never replace repository or provider mocks.
