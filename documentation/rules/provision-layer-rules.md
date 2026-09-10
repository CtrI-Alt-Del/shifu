---
description: Python provider adapters, external SDK boundaries, dependency pipes, and environment rules.
---

# Provider Layer Rules

These rules apply to `apps/server/src/shifu/<module>/providers`, shared providers, and
the dependency pipes that expose them to FastAPI controllers or jobs.

## Core owns provider contracts

Every external capability used by a use case has a narrow `Protocol` in the owning
module's `core/interfaces` package. Examples include clocks, token verification, object
storage, code execution, email delivery, model inference, cache access, and HTTP
gateways.

The contract uses domain structures and primitives. It must not expose vendor clients,
HTTP response classes, environment objects, or SDK exceptions.

## Adapters name technology and capability

Concrete adapters live beneath the module that owns the integration:

```text
identity/providers/auth/jwt/jwks/jwks_jwt_provider.py
intelligence/providers/embeddings/sklearn/tfidf_embeddings_provider.py
learning/providers/code_execution/<sandbox>/sandbox_code_execution_provider.py
shared/providers/cache/redis/redis_cache_provider.py
```

Class names identify the implementation, such as `JwksJwtProvider` or
`RedisCacheProvider`, and implement the matching core protocol. Do not name a concrete
class only `Provider` or place every integration in `shared`.

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

## Time, IDs, and randomness are explicit

Business time, generated identifiers, OTPs, and random selection use provider ports
when determinism or replacement matters. Use-case tests inject deterministic
autospecced mocks rather than patching global functions.

## Provider tests match risk

Use-case tests mock provider protocols. Test a provider adapter directly when its
translation, security, serialization, or failure mapping contains meaningful logic.
Prefer local emulators or Testcontainers for network services. A mock-only adapter test
does not prove compatibility with the real service.

Sandbox and authentication providers require explicit negative-path coverage for
isolation, invalid credentials, timeouts, and secret handling.
