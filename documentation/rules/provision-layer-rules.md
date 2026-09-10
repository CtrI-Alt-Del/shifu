---
description: Rules for infrastructure providers and external adapters used by server and web modules.
---

# Provision Layer Rules

These rules apply to shared providers under
`apps/server/src/shared/provision` and external adapters under
`apps/web/src/provision`.

## Shared providers have one server implementation

A technical capability used by more than one module must have a single
implementation under:

```text
apps/server/src/shared/provision/<concern>/
```

For example, date and time access belongs in:

```text
apps/server/src/shared/provision/datetime/datetime-provider.ts
```

Do not create one copy of the same provider inside each feature module.
Module-specific gateways and integrations remain owned by their module unless the
capability is intentionally shared.

## Core declares the contract

The infrastructure-independent contract belongs in
`packages/core/src/shared/interfaces`. The server provider implements that
contract.

```ts
@Injectable()
export class DatetimeProvider implements DatetimeProviderContract {
  now(): Date {
    return new Date()
  }
}
```

Core code must depend on the contract, never on NestJS, configuration services, or
the concrete server provider.

Provider methods must expose the smallest capability the domain needs. For date
and time, use `now(): Date`; do not expose an entire third-party date library.

## ProvisionModule owns registration

The shared `ProvisionModule` must register and export shared provider
implementations. Feature modules import `ProvisionModule` to make them available
to controllers and other server adapters.

Do not register duplicate provider implementations in feature modules and do not
instantiate providers manually in controllers.

## Business time comes from DatetimeProvider

Use cases that create or change business timestamps must receive a datetime
provider through their constructor and call `now()`. Do not call `new Date()` or
`Date.now()` inside a use case.

This rule makes time explicit, deterministic in unit tests, and replaceable
without changing domain behavior.

## Providers contain infrastructure concerns only

Provision-layer classes may wrap framework or environment APIs, normalize their
outputs, and expose them through core contracts. They must not implement business
rules or orchestrate module use cases.

Environment access must be wrapped by the shared environment provider instead of
reading `process.env` throughout feature modules.

## Web integrations use a client plus a factory

Web integrations with third-party services use this shape:

```text
apps/web/src/provision/<concern>/<provider>/
├── <provider>-client.ts
└── <provider>-provider.ts
```

The client file creates the configured singleton client. The provider file is a
factory that receives an optional client dependency, defaulting to that singleton,
and returns the application or core contract implemented by the integration:

```ts
export const CookieAuthProvider = (
  client: AuthClient = authClient,
): AuthProvider => {
  return {
    // adapter operations
  }
}
```

This keeps the provider replaceable in tests and keeps third-party calls out of
contexts, widgets, route middleware, and services. Web authentication uses
credentialed requests and an `HttpOnly` cookie issued by the server; browser
code must not read, persist, or synthesize session tokens. Better Auth secrets
and email-provider credentials belong to server infrastructure and must never be
bundled into the web app.

Transactional email adapters belong to Communication provision. A
Communication-owned `EmailProvider` contract may have a Resend implementation
for staging/production and an SMTP implementation for local Mailpit. Identity
publishes its facts through domain events and must not depend on either adapter.

The provider should map third-party responses to core structures and preserve the
core provider contract. The shared auth context consumes the factory result and
owns only React state and subscription lifecycle.

## Provider tests use mocks, not fakers

Use-case unit tests must mock provider contracts with
`vitest-mock-extended`. Do not create faker factories for datetime, environment,
storage, or other providers.

Configure mocked provider methods with explicit deterministic values:

```ts
const datetimeProvider = mock<DatetimeProviderContract>()
const now = new Date('2026-07-24T12:00:00.000Z')

datetimeProvider.now.mockReturnValue(now)
```

Domain fakers are reserved for entities and structures.
