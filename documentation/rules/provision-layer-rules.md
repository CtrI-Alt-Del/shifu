---
description: Server and web provider adapters, external SDK boundaries, dependency composition, and environment rules.
---

# Provider Layer Rules

These rules apply to `apps/server/src/shifu/<module>/providers`, shared providers,
the dependency pipes that expose them to FastAPI controllers or jobs, and web
infrastructure adapters under `apps/web/src/provision`.

## Core owns provider contracts

Every external capability used by a use case has a narrow `Protocol` in the owning
module's `core/interfaces` package. Examples include clocks, token verification, object
storage, code execution, email delivery, model inference, cache access, and HTTP
gateways.

The contract uses domain structures and primitives. It must not expose vendor clients,
HTTP response classes, environment objects, or SDK exceptions.

Cross-module provider contracts that are genuinely technical and shared belong under
`apps/server/src/shifu/shared/core/interfaces`. Their concrete implementations belong
under `apps/server/src/shifu/shared/providers`.

## Adapters name technology and capability

Concrete adapters live beneath the module that owns the integration:

```text
identity/providers/auth/jwt/jwks/jwks_jwt_provider.py
intelligence/providers/embeddings/sklearn/tfidf_embeddings_provider.py
learning/providers/code_execution/<sandbox>/sandbox_code_execution_provider.py
shared/providers/system_clock_provider/system_clock_provider.py
shared/providers/system_identifier_provider/system_identifier_provider.py
```

Class names identify the implementation, such as `JwksJwtProvider` or
`RedisCacheProvider`, and implement the matching core protocol. Do not name a concrete
class only `Provider` or place every integration in `shared`.

Every concrete provider directly under `apps/server/src/shifu/shared/providers` has its
own folder named after the provider. The folder contains the provider module and may
contain a local `__init__.py` that explicitly exports its public class:

```text
shared/providers/
├── system_clock_provider/
│   ├── __init__.py
│   └── system_clock_provider.py
└── system_identifier_provider/
    ├── __init__.py
    └── system_identifier_provider.py
```

Do not add flat shared provider modules or generic technology buckets such as
`shared/providers/cache/redis`. Package exports must not perform registration, I/O, or
environment loading.

## Providers translate infrastructure

A provider may configure an SDK, perform external I/O, normalize vendor responses, map
known vendor failures, and return domain values. It must not decide learning progress,
award XP, authorize another module's data, or orchestrate unrelated use cases.

Contain untyped SDK behavior, retries, pagination tokens, headers, and transport details
inside the adapter. Raise a typed application/infrastructure error without leaking
credentials or raw vendor payloads.

## Pipes construct replaceable dependencies

FastAPI dependency factories live in the owning module's `pipes` package or
`shifu/shared/pipes`. They construct a concrete provider and return the core protocol:

```python
class ProvidersPipe:
    @staticmethod
    def get_clock() -> ClockProvider:
        return SystemClockProvider()
```

Controllers use `Annotated[ClockProvider, Depends(ProvidersPipe.get_clock)]`. Do not
instantiate a concrete external provider in a core use case. Jobs may construct an
adapter at their outer boundary when no request dependency graph exists, but the use
case still receives only its protocol.

Long-lived clients should be created once through FastAPI lifespan and returned by a
dependency; do not create a new connection pool or expensive SDK client per request.

## Environment settings are centralized

Read and validate environment values through one settings boundary based on
`pydantic-settings` or an equivalent typed mechanism. Application composition and
providers consume that object. Core code never reads environment variables.

Required production configuration fails fast with a safe message. Local defaults are
allowed only for explicitly local services. Secrets never receive committed defaults,
appear in logs, or cross into browser bundles.

## Web auth provision uses a compact technology boundary

Web authentication infrastructure belongs under `apps/web/src/provision/auth`.
Better Auth-specific server configuration and runtime composition use this tree:

```text
apps/web/src/provision/auth/
├── better-auth/
│   ├── better-auth-config.ts
│   └── better-auth-provider.ts
└── cookie-session-auth-provider.ts
```

`better-auth-config.ts` owns validated server-only settings and Better Auth policy.
`better-auth-provider.ts` owns the configured Better Auth instance, persistence
lifecycle, registered auth endpoints, and server session operations. Do not split
those responsibilities into generic `auth.ts`, `environment.ts`, `session.ts`,
`types.ts`, or one file per Better Auth plugin. Browser-safe sign-in contracts stay
colocated with `cookie-session-auth-provider.ts` unless another consumer establishes
a real shared contract.

Providers consume module REST services for HTTP operations. They must not create an
ad hoc API client inside `provision`, call Axios directly, or move business authority
out of the owning server module.

## Time, IDs, and randomness are explicit

Business time, generated identifiers, OTPs, and random selection use provider ports
when determinism or replacement matters. Use-case tests inject deterministic
autospecced mocks rather than patching global functions.

Use `ClockProvider` for current time in application orchestration, brokers, jobs, and
use cases. `SystemClockProvider` is the infrastructure implementation and may read the
system clock at that boundary; consumers receive the protocol through injection. Do
not define local `_utc_now()` helpers or call `datetime.now()` directly in those
consumers.

## Providers never own test files

Do not create a dedicated test file for a provider, provision adapter, dependency
pipe, or application plugin. This prohibition applies to both
`apps/server/tests/providers` and tests beneath `apps/web/src/provision` or
`apps/web/tests/unit/provision`. Test filenames, suite targets, and fixtures must not
name or import the concrete provider or plugin solely to exercise its internals.

Exercise provider behavior through its consuming boundary: use-case tests mock the
provider protocol; FastAPI controller integration tests traverse composed pipes;
web auth/API integration tests send requests through the registered HTTP handler;
and routed page/layout tests exercise browser-visible behavior. Use controlled real
services, local emulators, or Testcontainers at those consuming integration
boundaries when compatibility or persistence must be proved. Sandbox and
authentication behavior still requires negative-path coverage for isolation,
invalid credentials, timeouts, rollback, and secret handling, but that evidence
must not be implemented as a provider-owned test.
