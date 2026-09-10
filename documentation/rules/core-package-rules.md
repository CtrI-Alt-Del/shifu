---
description: Source organization rules for the shared core domain package.
---

# Core Package Rules

These rules apply to TypeScript source files under `packages/core`.

## One exported type per file

Every declaration written with `export type` must live in its own source file.
The filename must describe that exported type using kebab-case.

Do not declare two or more exported types in the same file:

```ts
// legal-catalog.ts — invalid
export type LegalArea = {
  id: string
  name: string
}

export type LegalTopic = {
  id: string
  name: string
}
```

Create one file for each exported type instead:

```ts
// legal-area.ts
export type LegalArea = {
  id: string
  name: string
}
```

```ts
// legal-topic.ts
export type LegalTopic = {
  id: string
  name: string
}
```

Non-exported helper types may remain in the file where they are used. Barrel files named
`index.ts` must only re-export declarations and must not declare types of their own.

## Domain faker conventions

Test fakers for core entities belong under the owning module's
`domain/entities/fakers` directory. Keep one faker class per entity and name it
`<EntityName>Faker`:

```ts
import { faker } from '@faker-js/faker'

import type { Account } from '../account'
import { UserProfile } from '../../structures/user-profile'

export class AccountFaker {
  static fake(overrides: Partial<Account> = {}): Account {
    return {
      id: faker.string.uuid(),
      establishmentId: faker.string.uuid(),
      name: faker.person.fullName(),
      email: faker.internet.email(),
      profile: UserProfile.Manager,
      ...overrides,
    }
  }

  static fakeMany(count = 10): Account[] {
    return Array.from({ length: count }, () => AccountFaker.fake())
  }
}
```

Every core faker must expose both methods:

- `static fake(overrides: Partial<Entity> = {})` returns one valid entity;
- `static fakeMany(count = 10)` returns exactly `count` independently generated
  entities by delegating to `fake()`.

Use `@faker-js/faker` for generated identity fields and realistic values. Keep
defaults valid for the entity and stable where time-sensitive assertions depend
on them. Apply overrides last so tests can express the state under examination
without rebuilding unrelated entity fields. When a scenario contains related
entities, override their IDs explicitly so the relationship remains coherent.

Do not export free functions such as `fakeAccount()` or place faker logic in
production entities, structures, use cases, interfaces, or application layers.
Faker classes are test data builders only and must not add business behavior.
Export every faker class from the module's `fakers/index.ts` barrel, and import
it by class name in tests:

```ts
import { AccountFaker } from '#identity/domain/entities/fakers/index.ts'

const manager = AccountFaker.fake({ profile: UserProfile.Manager })
const operators = AccountFaker.fakeMany(3)
```

Do not scatter hand-written complete entities through tests when a core faker
exists. Keep only the behavior-specific overrides in the test, and add or
update the faker when a new valid default or entity state is needed.

## Business rules belong to use cases

Every business rule in `packages/core` must be implemented exclusively inside a
use case class under the owning module's `use-cases` directory.

Entities and structures describe domain state and valid data shapes. They must not
implement business decisions through methods, exported functions, computed getters,
validators, policies, specifications, or rule objects.

Do not create `domain/rules`, `domain/policies`, or `domain/services` directories to
hold business rules. For example, whether a document package can be confirmed must
be checked by a `ConfirmDocumentPackage` use case class, not by a
`canConfirmDocumentPackage` function.

Use cases may coordinate entities, structures, interfaces, errors, and events while
enforcing the rules required by one application action. Keep one exported use case
class per file and use a verb-led name that describes the action.

## Contracts belong to interfaces directories

Every contract exposed by `packages/core` must live in an `interfaces` directory
under the module that owns it. Never create a directory named `providers` inside
`packages/core`.

This rule applies to provider, repository, gateway, storage, and other contracts
implemented outside the core. Their declaration names must continue to describe
their specific roles, such as `ClientLookupProvider`, `DocumentBatchRepository`, or
`FileStorageProvider`; `interfaces` is the name of the organizational directory,
not a required suffix for each contract.

Place a contract in `shared/interfaces` only when it is intentionally shared by
multiple modules. An `interfaces/index.ts` barrel must only re-export declarations.
Implementations and infrastructure-specific details must remain outside
`packages/core`.

Identity authentication follows the same separation:

- `AuthProvider` is the behavioral contract and belongs in
  `packages/core/src/identity/interfaces`;
- `AuthCredentials`, `AuthSession`, `AuthStateChange`,
  `AuthStateChangeListener`, and `AuthUser` are shared data structures and belong
  in `packages/core/src/identity/domain/structures`;
- authentication-provider implementations belong in an application provision
  layer, not in the core package.

Consumers must import auth data structures from the structures barrel and the
provider contract from the interfaces barrel. Do not place provider-specific
types or Better Auth imports in `packages/core`.

Transactional email is owned by Communication. Its provider-neutral
`EmailProvider` contract belongs under
`packages/core/src/communication/interfaces`; Identity publishes authoritative
domain events and must not import that interface or a Resend, SMTP, or Mailpit
implementation.

When an approved atomic-delivery requirement applies, Core use cases call
`scope.eventsRepository.add(event)` while the owning database transaction is
active. The `EventsRepository` contract accepts only a typed domain `Event`; it
must not expose SQL rows, transaction objects, polling, Inngest, or provider
types. Shared server infrastructure implements transaction-aware event
persistence and the post-commit `InngestBroker` relay.

## Only entities have identity

Only declarations inside an `entities` directory may own a local domain identity
field named `id`. A structure represents a value, state, configuration, or
relationship without an identity of its own and therefore normally must not
declare an `id` property.

If a domain concept needs an `id` so it can be referenced, edited, removed, or tracked
independently, model it as an entity instead of a structure. Do not remove a necessary
identity merely to keep the declaration in `structures`.

Structures may contain explicitly named references to entities, such as
`consultationId` or `legalAreaId`. External identity projections are the narrow
exception: `AuthUser` may expose the provider's subject `id` because it represents
an external authentication identity, not a core aggregate entity. No other
structure should add a bare `id` field without documenting the same external
identity rationale.
