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

## Entities own identity and local behavior

Entities have stable identity and encapsulate state transitions that are valid for one
instance. Decorate mutable entities with `entity` and immutable historical entities
with `frozen_entity`: the bare `id` is immutable, equality and hashing use the entity
type and `id`, and immutable records cannot be changed after construction.
Construct them through a `create` classmethod or another explicit named factory that
validates and normalizes input.

An entity may protect its own invariants, such as a valid state transition. Decisions
that coordinate repositories, providers, several aggregates, permissions, or external
effects belong in a use case. Do not expose SQLAlchemy models as domain entities, and
do not make the decorators or an entity depend on Pydantic, SQLAlchemy, or another
framework.

## Structures are immutable values

Structures represent composite inputs, filters, snapshots, projections, or
relationships without independent identity. Decorate them with the shared `structure`
decorator so every attribute is immutable and equality compares every field. Use
explicit factories or `__post_init__` validation for value invariants; structures do
not perform I/O or coordinate other aggregates.

Only entities own a bare `id`. A structure may carry an explicitly named reference such
as `objective_id` or `learner_id`.

DTOs are serializable data carriers. They do not validate business policy or perform
I/O. Use cases or boundary mappers construct projections; domain data objects do not
expose projection methods. HTTP schemas and persistence models remain outside core.

### Structure module organization

Keep one domain structure class per module under `domain/structures/`. Name the file
after the structure in `snake_case`, such as `curriculum_skill_snapshot.py` for
`CurriculumSkillSnapshot`. A module may contain that structure’s local validation and
private helpers, but it must not become a collection of unrelated structures.

Reusable type aliases, unions, and validation helpers get their own narrowly named
modules when they are shared by multiple structures. Package `__init__.py` files are
barrels for stable re-exports only; they must not contain structure definitions or
business validation.

Do not decorate core structures with `pydantic.dataclasses.dataclass`, import
Pydantic into `structure.py`, or add transport serialization configuration to domain
types. Pydantic integration belongs at the REST, job, or other adapter boundary, where
the adapter validates the framework-independent structure against its transport
contract.

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

Shared technical provider ports belong under `shared/core/interfaces` only when more
than one module needs the same capability. For example, `ClockProvider` and
`IdentifierProvider` are shared protocols; their system implementations belong under
`shared/providers/<provider_name>/`, never beside the protocol or as a flat shared
module. Inngest delivery is not a core provider port: use cases persist events through
`EventsRepository`, and shared messaging relays committed rows to Inngest.

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

Domain fakers belong under `apps/server/src/shifu/fakers/<module>` and mirror the
entities or structures they build. Use one `<Entity>Faker` class per concept with a
`fake` method and add `fake_many` only when collection scenarios need it repeatedly.

Defaults must produce valid domain objects. Allow explicit keyword overrides so tests
state only the behavior-specific differences. Fakers contain no business behavior and
never replace repository or provider mocks.

Event timestamp strings use UTC ISO 8601 with a `Z` suffix. Answer-key fields such as
`is_correct` stay in domain contracts only; client projections must remove them when
the product rules keep the answer hidden.

Dedicated core unit tests are reserved for use cases under
`apps/server/tests/<module>/core/use_cases`. Domain declarations, decorators, enums,
events, errors, fakers, and interface protocols are exercised through use-case tests
and validated by typing, architecture checks, package construction, and applicable
adapter or boundary tests; do not create direct unit-test suites for them.
