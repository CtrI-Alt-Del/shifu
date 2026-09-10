---
description: Unit-testing rules for core use cases and domain test-data fakers.
---

# Use Case Testing Rules

These rules apply to use cases and their unit tests under `packages/core/src`.

## Use cases follow one standard shape

Use-case files belong in the owning module's `use-cases` directory and end in
`-use-case.ts`. Classes use a verb-led name ending in `UseCase` and implement the
shared use-case interface:

```ts
type Request = {
  intakeId: string
}

type Response = Intake

export class GetIntakeUseCase implements UseCase<Request, Response> {
  // ...
}
```

Prefer the local name `Request` for the input type. Do not repeat the use-case name
in a private type such as `GetIntakeRequest`. Export a request or response type
only when another domain API genuinely needs that named contract.

Business rules and orchestration belong in `execute`. Use repositories and
providers through core interfaces.

Use business verbs instead of generic CRUD verbs. Registering a new intake is
`RegisterIntakeUseCase`, not `CreateIntakeUseCase`. Distinct business actions such
as transitioning status or closing an intake without a contract remain separate
use cases rather than a generic update use case.

## Only use cases receive unit tests

Unit tests in `packages/core` are written for use cases. Do not create isolated
unit tests for entities, structures, fakers, repository interfaces, providers,
mappers, controllers, or database repositories.

Repository implementations do not receive test files of their own. Do not create
unit or integration tests whose subject is a repository, mapper, Drizzle model, or
database adapter. Persistence is exercised indirectly through the server integration
tests for the controller or application flow that consumes it.

## One test file per use case

Every use case must have its own test file under:

```text
packages/core/src/<module>/use-cases/tests/
```

The filename mirrors the use-case filename and uses the `.test.ts` suffix:

```text
register-intake-use-case.test.ts
```

Do not use `.spec.ts`. A test file may contain several test cases, but it must test
only its corresponding use case.

The top-level `describe` must write every word in the use-case name separately:

```ts
describe('Register Intake Use Case', () => {
  // ...
})
```

Do not copy the class identifier directly:

```ts
// Invalid
describe('RegisterIntakeUseCase', () => {
  // ...
})
```

Cover every meaningful behavior, including:

- the successful result;
- repository and provider interactions;
- required business errors;
- not-found and invalid-transition paths;
- concurrency or version checks when the use case exposes them.

Assert both the returned domain value and the important dependency calls. Avoid
tests that only repeat implementation details.

## Mock dependencies with vitest-mock-extended

Repository, gateway, and provider dependencies must use:

```ts
import { mock, type MockProxy } from 'vitest-mock-extended'
```

Declare dependency fields as `MockProxy<Contract>` and initialize them with
`mock<Contract>()`. Do not write ad hoc objects with `vi.fn()` when a typed contract
mock can be used.

Reset or recreate mocks for every test so call history and configured responses do
not leak between cases.

## Time is deterministic

Use cases that depend on the current time must receive the datetime provider.
Configure its mock to return a fixed `Date` and assert that the persisted or
returned value uses that exact instant.

Never depend on the machine clock, fake timers, or `new Date()` in a use-case unit
test when `DatetimeProvider` is part of the contract.

## Domain test data uses colocated fakers

Entity fakers belong in:

```text
packages/core/src/<module>/domain/entities/fakers/
```

Structure fakers belong in:

```text
packages/core/src/<module>/domain/structures/fakers/
```

Fakers must use `@faker-js/faker`, return valid domain data by default, and accept
partial overrides so a test can express only the fields relevant to its scenario:

```ts
export function fakeIntake(overrides: Partial<Intake> = {}): Intake {
  return {
    id: faker.string.uuid(),
    // valid defaults...
    ...overrides,
  }
}
```

Add a `fakeMany` helper only when tests need collections repeatedly. Export fakers
through the local `fakers/index.ts` barrel.

Do not create fakers for providers or repository implementations. Providers use
typed mocks; fakers are only for domain entities and structures.

## Unit tests stay infrastructure-free

Use-case tests must not bootstrap NestJS, connect to a database, start
Testcontainers, perform HTTP requests, or instantiate server adapters. They must
run with core domain code, domain fakers, and mocked interfaces only.
