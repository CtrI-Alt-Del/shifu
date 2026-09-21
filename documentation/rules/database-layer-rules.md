---
description: SQLAlchemy models, sessions, mappers, repositories, migrations, and seeding rules.
---

# Database Layer Rules

These rules apply to module persistence under
`apps/server/src/shifu/<module>/database/sqlalchemy`, shared SQLAlchemy infrastructure,
Alembic migrations, and database test fixtures.

## Modules own persistence adapters

Use this structure for a persisted module:

```text
<module>/database/sqlalchemy/
├── models/
├── mappers/
└── repositories/
```

Models, mappers, and repositories remain in the module that owns the data. Shared
database code owns the engine, session factory, declarative base, migration metadata,
and infrastructure with no business owner.

A module must not import another module's SQLAlchemy model or repository. Cross-module
coordination uses public contracts, identifiers, and events.

Shared SQLAlchemy infrastructure follows the class boundary defined by its public
module. `shared/database/sqlalchemy/serialization.py` exports `Serialization` and
`shared/database/sqlalchemy/session.py` exports `Session`; their stateless operations
are static methods on those classes. Consumers import the class and call the explicit
method (`Serialization.serialize_value(...)`, `Session.database_session(...)`) rather
than relying on free module functions or duplicated engine/session helpers.

## Sessions define transaction boundaries

Create the engine and `sessionmaker` once in shared database infrastructure. Every
execution path has exactly one transaction owner and all repositories participating in
that operation use the same SQLAlchemy `Session`.

A module database context manager may own the operation boundary for HTTP and non-HTTP
use cases: it creates the shared-session repository group, commits only on normal exit,
rolls back escaped exceptions, and always closes the session. Alternatively, an HTTP
application may select request middleware as that sole owner and make one session
available through `request.state` and dependency pipes. Never combine both ownership
models in one execution path or allow both middleware and a use case to commit.

Repositories do not call `commit`. Use cases do not receive the session. A job may use
an explicit session context per durable step and commit at the step boundary when that
state must survive later retries.

Every module database repository group exposes the shared `EventsRepository`. A use
case that emits an event calls `repositories.events.add(event)` inside the same module
transaction as its business mutation. An event-only operation still uses that module
transaction as the sole owner of the outbox insert.

The shared SQLAlchemy adapter persists canonical events in the shared `events` outbox
table. Its insert participates in the caller's transaction and emits a PostgreSQL
notification that becomes visible only after commit. The repository does not call
Inngest. Shared messaging owns the long-lived database listener that reserves eligible
rows, sends them with their stable IDs, and marks them published after acknowledgement.
Startup and reconnect draining must recover committed rows whose notifications were
missed. The repository exposes the earliest event-availability or reservation-expiry
deadline so the listener can wake for retries without depending on a later database
notification, and it can release expired reservations before the next claim.

## SQLAlchemy models are persistence-only

Use SQLAlchemy 2 declarative models with `Mapped[...]` and `mapped_column`. One model
class belongs in one `*_model.py` module and ends in `Model`.

```python
class ObjectiveModel(Model):
    __tablename__ = 'objectives'

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
```

Models define columns, constraints, indexes, foreign keys, and ORM relationships needed
for persistence. They do not expose domain methods or inherit from domain entities.
Store timestamps as timezone-aware UTC values.

Keep database nullability and defaults explicit. Enforce invariants that protect data
integrity with database constraints in addition to domain validation where appropriate.

## Mappers isolate representations

Every repository returning domain objects uses a mapper from `mappers`. Mappers expose
explicit methods such as `to_entity` and `to_model`; projection-specific names are
allowed when a query does not hydrate a complete entity.

Mappers translate IDs, enums, timestamps, nullability, nested values, and persistence
representations. They do not query the database, publish events, or make business
decisions.

Never return an ORM model outside the database adapter. Never accept an ORM model in a
core interface.

## Repositories implement core Protocols

Concrete classes use names such as `SqlalchemyObjectivesRepository` and implement the
owning core `Protocol`. Inject the session through the constructor and keep it private.
Each concrete repository class has its own `<entity>_repository.py` module; do not
combine multiple repository classes in a shared `repositories.py` file. The package
`__init__.py` may re-export the canonical repository classes for composition imports.

Repository methods describe persistence capabilities:

- `find_by_id` or a semantically precise `find_*` returns one value or `None`;
- `find_many_*` returns a typed collection or pagination structure;
- `add` inserts one domain object;
- `add_many` inserts a collection in one efficient operation where supported;
- `update` updates an existing domain object;
- `remove` deletes one record;
- `remove_all` is reserved for explicit test or seed maintenance.

Do not use ambiguous `save` methods. Do not encode business actions such as
`complete_objective` in a repository. Atomic compare-and-set, locking, uniqueness, and
pagination are valid persistence concerns when declared by the core port.

Queries use SQLAlchemy expressions and parameter binding. Do not concatenate SQL from
request values or expose query objects to callers.

## Migrations are the schema history

Alembic owns schema changes. Generate a migration, review it, and test both upgrade and
applicable downgrade behavior. Do not use `metadata.create_all` as an application
migration strategy.

Migration revisions must:

- contain only the intended schema/data transition;
- use stable, descriptive names;
- preserve existing data or document the approved destructive behavior;
- add constraints and indexes deliberately;
- avoid importing application runtime code whose behavior can drift later.

Tests may use `metadata.create_all` only for a narrowly scoped fixture while migration
coverage is being established. The production-like integration path runs Alembic.

## Seeders use application adapters

Each persisted module may expose a `<Module>Seeder` that receives repository and
provider ports. Seeders create valid domain objects through domain factories/fakers and
write through repositories. They do not duplicate SQLAlchemy insert statements.

A shared seed entrypoint coordinates module seeders in dependency order and uses one
explicit session boundary. Seeding is an explicit command, never application startup.
Destructive reset is allowed only in the approved `local` environment and must be
guarded before deleting data.

The current shared entrypoint is
`apps/server/src/shifu/shared/database/seed.py`, with seed data construction in
`shared/database/seed_data.py`. The `db:seed` command invokes that module explicitly;
the seed modules must not run as an import side effect.

Because this entrypoint intentionally coordinates feature-owned seeders, the server's
Tach command excludes only `shared/database/seed.py` and `shared/database/seed_data.py`.
Keep this narrow, documented exception instead of adding feature dependencies to the
general shared-database boundary or creating a dependency cycle.

Never embed production credentials or real user data in seeders.

## Persistence is tested through behavior

Use-case unit tests mock repository protocols. Controller and job integration tests
exercise concrete SQLAlchemy repositories against PostgreSQL. Add a repository-focused
integration test outside `apps/server/tests/core` only for complex persistence
semantics that cannot be observed clearly through an application boundary, such as a
concurrency primitive or database-specific query.

Integration fixtures isolate tests, clean tables in reverse dependency order, and do
not leak sessions or containers.

The shared REST fixture uses a session-scoped PostgreSQL Testcontainer, runs the
current Alembic head against its mapped connection URL, and injects its engine into
the application factory. A function-scoped fixture clears application tables before
and after each test while preserving migration metadata. REST tests must not silently
fall back to the developer's Compose database. Controlled doubles are reserved for a
deliberate infrastructure-failure seam or an external service that cannot run
reliably; they do not replace repository coverage.
