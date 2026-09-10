---
description: Integration-testing rules for NestJS controllers and database-backed routes.
---

# Controller Testing Rules

These rules apply to controller tests under `apps/server/src`.

## Controller tests are integration tests

Test controllers through their HTTP routes with a NestJS test application and
Supertest. The test must exercise the real path from controller to manually
instantiated use case, repository contract binding, Drizzle repository, mapper,
and database.

Do not call `controller.handle()` directly. Do not replace the repository with a
mock merely to make a controller test resemble a unit test.

## One test file per controller

Every REST controller must have its own test file under:

```text
apps/server/src/<module>/rest/controllers/tests/
```

The filename mirrors the controller and uses `.test.ts`:

```text
register-intakes.controller.test.ts
list-client-intakes.controller.test.ts
```

Do not use `.spec.ts`, combine several controllers into one test file, or leave a
controller without a corresponding integration test.

Each file tests the route owned by that controller, including the HTTP method,
path, request input, status, response body, and persisted effect when applicable.

The top-level `describe` must write the controller name with words separated and
append the HTTP method and complete route between brackets:

```ts
describe('Register Intakes Controller [POST /intakes]', () => {
  // ...
})
```

Do not use the class identifier as the description:

```ts
// Invalid
describe('RegisterIntakesController', () => {
  // ...
})
```

Path parameters must remain visible in the route, such as
`[GET /intakes/:intakeId]`.

The HTTP method and path belong only in the top-level `describe`. Individual
`it` descriptions must describe the behavior under test without repeating the
route:

```ts
describe('Get Intakes Controller [GET /intakes/:intakeId]', () => {
  it('gets an intake', async () => {
    // ...
  })
})
```

## Use real infrastructure and minimize mocks

Use real module providers and repositories wherever practical. External services
must run through Testcontainers or another project-approved test service rather
than being represented by loose mocks.

Mocks are allowed only when no practical test service exists or when the
dependency cannot be placed under test control. Keep the exception local and
document why it is necessary.

Use core entity and structure fakers to create valid domain test data. Do not
recreate domain fixtures as arbitrary inline objects in every controller test.

## DatabaseFixture encapsulates database test infrastructure

All shared PostgreSQL integration-test setup belongs in:

```text
apps/server/src/shared/database/fixtures/database-fixture.ts
```

`DatabaseFixture` is responsible for:

- starting and stopping the PostgreSQL Testcontainer;
- setting a temporary `DATABASE_URL`;
- applying Drizzle migrations;
- exposing the database connection needed by test setup;
- truncating public application tables between tests;
- preserving the Drizzle migrations table;
- restoring environment state during teardown.

Controller tests and module-specific helpers must not duplicate container startup,
migration, cleanup, or environment restoration logic.

`RestFixture`, under `apps/server/src/shared/rest/tests`, must compose
`DatabaseFixture` with the Nest test application. It owns generic REST integration
setup, provider resolution, database reset, and teardown.

Each module must provide its own fixture under
`apps/server/src/<module>/fixtures`. For Intake, this is
`IntakeModuleFixture`. A module fixture composes `RestFixture` and may only own
feature-specific module setup, repository access, seed data, and domain helpers.
Do not create function-based test contexts or duplicate generic REST and database
lifecycle code.

Every fixture must expose a static `register` method as its entry point. Do not
use a static `create` method for fixture initialization.

## Build the test application with real module wiring

The Nest testing module must include the target controller and the actual feature
database and provision modules required by it. Repository tokens must resolve to
the same concrete providers used by the application.

Seed prerequisites through the module seeder or the real repository. Prefer the
module seeder and `addMany` when a scenario needs several records. Do not insert
raw SQL rows that bypass module models and mappers unless the test explicitly
verifies corrupted or legacy persistence data.

## Isolate every test

Clean application tables before every test. Create only the records required by
the current scenario.

Close the Nest application and stop the shared database fixture after all tests,
even when an assertion fails. Do not allow ports, connections, containers, or
environment variables to leak into another test file.

Tests that share one fixture must still be order-independent.

## Assert the HTTP and persistence contracts

For write controllers, assert the response and verify the resulting record through
the real repository or a subsequent HTTP read when appropriate.

For read controllers, seed distinguishable records and assert filtering, ordering,
optional values, and response serialization that are part of the endpoint
contract.

Include error-path assertions when the controller, NestJS integration, or use case
maps a domain error into a defined HTTP response.

## Test files do not ship in production builds

Server build configuration must exclude `**/tests/**` and `**/*.test.ts`.
Integration tests rely on the Vitest alias configuration so internal imports keep
the same `@/` paths used by production server code.

Running controller integration tests requires a working Docker-compatible
container runtime.
