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
│   ├── enums/
│   ├── errors/
│   └── events/
├── interfaces/
└── use_cases/
```

Do not move module-specific behavior into `shared`. Shared core contains only stable
primitives and contracts genuinely used by multiple modules.

## Entities are mutable identity records

Entities are data-only declarations with stable identity. Decorate them with the shared
`entity` decorator: the bare `id` is immutable after initialization, equality and
hashing use the entity type and `id`, and every other declared attribute remains
mutable. Entities do not define factories, validators, transitions, projections, or
other business methods.

Use cases create entities, normalize and validate their input, and mutate entity state
when applying an approved transition. Do not expose SQLAlchemy models as domain
entities, and do not make the `entity` decorator or an entity depend on Pydantic,
SQLAlchemy, or another framework.

## Structures are immutable values

Structures represent composite inputs, filters, snapshots, projections, or
relationships without independent identity. Decorate them with the shared `structure`
decorator so every attribute is immutable and equality compares every field. Structures
are data-only and do not define factories, validators, projections, or business
methods. Use cases normalize and validate primitives before constructing them.

Only entities own a bare `id`. A structure may carry an explicitly named reference such
as `objective_id` or `learner_id`.

DTOs are serializable data carriers. They do not validate business policy or perform
I/O. Use cases or boundary mappers construct projections; domain data objects do not
expose projection methods. HTTP schemas and persistence models remain outside core.

## Enums are controlled values

Place domain states and other controlled values under `domain/enums`, using one
`StrEnum` class per file. Enums are framework-independent and immutable. Simple scalar
values remain standard Python primitives unless a composite structure has independent
domain meaning.

## Use cases own application actions

Create one use-case class per application action under `core/use_cases`. Name it with a
business verb and the `UseCase` suffix, and expose one `execute` method.

A use case may extend another use case when the derived action is a genuine
specialization and remains substitutable for the base action. Prefer dependency
composition when the actions merely share steps or one action needs to invoke another;
inheritance must not move business behavior back into domain data objects.

Use cases:

- normalize primitive input into domain structures;
- construct entities and apply their state changes;
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

Persistence ports, delivery ports, and transaction ports should remain separate when
they represent different capabilities. Module ports use only their owning module's
domain values and shared contracts; they never import another module's entities,
expose an SDK, or accept a SQLAlchemy session. Cross-module requests are translated at
an application or messaging boundary.

## Domain errors are transport-neutral

Expected failures derive from the shared `AppError` hierarchy or a module-specific
subclass. Errors expose stable domain meaning and a safe user-facing message; they do
not contain HTTP status codes or FastAPI response objects.

Error defaults use explicitly annotated `message: str` and `title: str` attributes.
Subclasses override those same names when they need a more specific safe default; do
not introduce parallel `default_message` or `default_title` attributes. An error may
still accept per-instance message and title overrides when the shared base contract
allows them.

The REST layer maps domain error classes to HTTP responses. Jobs decide which failures
are retryable without changing the domain error itself.

## Events describe facts or requests

Domain events belong to the module that owns their meaning. Each event declares its
name once and owns a typed, serializable payload. Declare the payload structure in the
same `*_event.py` module as its event; do not create standalone payload modules. Names
use a stable namespace such as:

```text
learning/activity-submission.requested
learning/activity-evaluated
identity/account-deletion.requested
```

The producing module imports its own event class rather than repeating event-name
literals or rebuilding payload dictionaries independently. Cross-module consumer
adapters deserialize and translate the event at an application or messaging boundary;
a consuming business module's core does not import the producer module. Payloads
contain identifiers and immutable snapshots needed by the consumer, never ORM models
or secrets.

## Module boundaries remain explicit

A business module does not import another business module. Cross-module coordination
uses module-neutral identifiers and contracts owned by Shared, plus serialized domain
events translated through application or messaging adapters as described in
`documentation/modules.md`. Application composition may import multiple business
modules to bind those contracts, but it must not transfer business authority into
Shared or into an adapter.

Learning remains authoritative for learner progress and official evaluation;
Curriculum for official content; Identity for account state; Gamification for rewards;
and Intelligence for AI-assisted experiences. Technical adapters do not transfer that
authority.

## Fakers build valid domain objects

Domain fakers belong beside the concept they build: entity fakers under
`apps/server/src/shifu/<module>/core/domain/entities/fakers` and structure fakers under
`apps/server/src/shifu/<module>/core/domain/structures/fakers`. Use one
`<Entity>Faker` class per concept with a `fake` method and add `fake_many` only when
collection scenarios need it repeatedly.

Defaults must produce valid domain objects. Allow explicit keyword overrides so tests
state only the behavior-specific differences. Fakers contain no business behavior and
never replace repository or provider mocks.

Dedicated core unit tests are reserved for use cases under
`apps/server/tests/core/<module>/use_cases`. Domain declarations, decorators, enums,
events, errors, fakers, and interface protocols are exercised through use-case tests
and validated by typing, architecture checks, package construction, and applicable
adapter or boundary tests; do not create direct unit-test suites for them.
