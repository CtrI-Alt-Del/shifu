---
description: FastAPI TestClient integration rules for controllers, SQLAlchemy persistence, and external boundaries.
---

# Controller Testing Rules

These rules apply to controller integration tests under
`apps/server/tests/rest/controllers/<module>` and their shared pytest fixtures.

## Test through HTTP

Every controller has one mirrored test module:

```text
src/shifu/identity/rest/controllers/create_account_controller.py
tests/rest/controllers/identity/test_create_account_controller.py
```

All pytest cases are methods on a `Test<Controller>` class. Group related route
scenarios in that class; do not define top-level `test_*` functions.

Use FastAPI `TestClient` to exercise the registered route. Do not call the controller
callback or use case directly. The test must cover the applicable path through routing,
Pydantic parsing, dependency wiring, use-case construction, repository adapter,
transaction middleware, error handler, and response serialization.

## Use the real database boundary

Database-backed controller tests use PostgreSQL through Testcontainers, run migrations,
and construct the same SQLAlchemy repositories as production. Do not mock the
repository in a normal HTTP integration test. A dedicated infrastructure-failure
regression may replace the dependency at the composition seam to force a deterministic
safe-error response, but it must still construct the real application against the
fixture database and must not replace repository coverage for successful paths.

Session-scoped fixtures own container and engine lifecycle. Function-scoped fixtures
own sessions and database cleanup. Reset application tables before each test and close
every session, engine, client, container, and overridden environment value during
teardown.

The shared `TestClient` fixture must receive the Testcontainer engine through the
application factory (for example, `FastAPIApp.register(database_engine=...)`) so HTTP
tests exercise production repository composition. Do not let an imported application
singleton or the developer's `DATABASE_URL` select the database for these tests.

Seed prerequisites through domain fakers, seeders, or small fixture helpers. Avoid raw
SQL except when testing malformed legacy persistence intentionally.

## Replace only impractical external systems

Use the production adapter against a local emulator or Testcontainer when practical.
Use a controlled fake only when an external service cannot run reliably in CI or when
the test is observing an event sent to another boundary.

Fakes expose recorded interactions with typed fields. Monkeypatch the composition seam,
not internal use-case behavior. A fake Inngest client may record emitted events in a
controller test; full Inngest execution belongs in job integration tests.

## Assert transport and effects

For every meaningful path, assert:

- HTTP method and complete route;
- status code;
- exact response body or relevant headers;
- persisted state for writes;
- filtering, ordering, and serialization for reads;
- emitted event name and payload when publication is part of the action;
- absence of protected effects on failure.

Cover successful behavior plus expected validation, authentication, authorization,
not-found, conflict, and invalid-transition responses that the controller can expose.
Do not duplicate the exhaustive use-case matrix at the HTTP boundary; select cases that
prove wiring and error mapping.

## Fixtures are reusable and explicit

Register common fixtures through `apps/server/tests/conftest.py` and place reusable
infrastructure under `apps/server/tests/fixtures`. Module fixtures may expose helpers
such as `create_account` or `create_objective`, but they must not hide the assertion or
perform the action under test.

Use `monkeypatch` for temporary environment or composition overrides. Never mutate a
shared global client without restoring it.

## Docker requirements are visible

Integration tests that require Docker may skip locally with a precise reason when the
runtime is unavailable, but CI must execute them on a Docker-capable runner. A skipped
suite is not evidence of a passing integration boundary.

Run focused controller tests through `uv run pytest tests/rest/controllers/<module>`.
Before delivery, run Ruff, strict typing, and all applicable controller tests.
