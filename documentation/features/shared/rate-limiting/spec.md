---
feature: Redis-backed rate limiting
module: shared (cross-cutting infrastructure — not a business module)
jira: SHIFU-58
status: implemented
version: 1
last_reviewed: 2026-09-16
---

# Spec: Redis-backed rate limiting for the Shifu Server

## Traceability

This is infrastructure hardening for the whole FastAPI application, not a change to a
business module's product behavior. `modules.md` divides Shifu into six business
modules (Identity, Communication, Curriculum, Learning, Gamification, Intelligence);
none of them owns request-level rate limiting, and no module's canonical Confluence PRD
addresses it. Accordingly:

- **No `RP-*` or `JN-*` applies.** There is no canonical Confluence PRD requirement to
  cite for this ticket, and inventing one would violate the "never invent PRD IDs" rule.
  This is a documented exception to the normal "every `RF-*` maps to an `RP-*`" rule in
  `sdd.md`, made because the work is genuinely outside product-module scope.
- The controlling authority is **Jira SHIFU-58** (retrieved 2026-09-16, status
  "Fazendo", updated 2026-09-15T23:26:02.171-03:00) plus the repository Rule Packs
  listed below, read in full on 2026-09-16:
  - `documentation/rules/provision-layer-rules.md`
  - `documentation/rules/server-app-layer-rules.md`
  - `documentation/rules/core-package-rules.md`
  - `documentation/rules/python-code-conventions-rules.md`
  - `documentation/modules.md`, `documentation/architecture.md`
- No `documentation/templates/sdd/` template exists in this repository yet, and no
  other `spec.md` exists to follow as precedent — this is the first SDD feature
  artifact created here. Its structure follows `documentation/sdd.md` directly.

Because there is no `RP-*` traceability, this Spec substitutes the repository Rule
Packs and this document's own **Decisions and assumptions** as the technical
authority. Those decisions were presented to the assignee and went unchallenged before
planning began, which is the acceptance this Spec was waiting on to move to `ready`.

## Scope

### In scope

- A framework-independent cache-provider contract exposing an atomic rate-limit
  operation, plus a Redis-backed implementation.
- A FastAPI middleware that applies a per-client-IP token-bucket rate limit to every
  route except `/health`.
- Trusted-proxy-gated client-IP resolution (`X-Forwarded-For`/`X-Real-IP` honored only
  when the immediate connection peer is a configured trusted proxy).
- A centralized, `pydantic-settings`-based settings boundary holding `REDIS_URL` and
  the trusted-proxy allowlist, consumed by composition/providers (required because
  `provision-layer-rules.md` forbids new direct `os.getenv` reads and none of that
  boundary exists in the repository yet).
- A FastAPI lifespan check that verifies Redis is reachable at startup and prevents the
  application from starting if it is not.
- `apps/server/.env.example` documenting `REDIS_URL=redis://localhost:6379/0`.

### Out of scope

- Provisioning a Redis instance or Docker Compose service (ticket explicitly excludes
  this; `docker-compose.yaml` has no `redis` service today and none is added here).
- Automated test files (ticket explicitly excludes this deliverable). Acceptance is
  validated manually for this slice (see **Manual validation**); a follow-up ticket
  should add adapter/middleware coverage per `provision-layer-rules.md`'s testing
  guidance.
- Per-account, per-route, or per-API-key rate limits — the ticket scope is per-client-IP
  only.
- Creating `documentation/infrastructure.md` — it does not exist yet. This Spec's
  **Dependencies and follow-ups** section is the interim record of the Redis
  dependency until that document exists.
- Any business-module domain logic, persistence model, or public product-facing
  contract change. `RateLimitError` and `ServiceUnavailableError` already exist under
  `shifu/shared/core/domain/errors/` from prior work and are reused, not redefined.

## Decisions and assumptions

The ticket fixes the policy (60 req/min, burst 10, 429 + `Retry-After`, IP-based,
trusted-proxy-gated, fail-fast on Redis outage) but leaves these implementation-shaping
choices open. They are resolved here so `RF-*`/`CA-*` are unambiguous:

1. **Settings boundary location**: `apps/server/src/shifu/shared/settings.py`, a single
   `pydantic-settings` class consumed by composition and providers. `REDIS_URL` is
   required (fails fast if missing); the trusted-proxy allowlist defaults to empty
   (trust nothing) because Shifu's documented architecture has no reverse proxy in
   front of FastAPI today (`architecture.md`'s system diagram goes browser → BFF →
   FastAPI directly) — an empty allowlist keeps current behavior safe by default.
2. **Middleware location**: `apps/server/src/shifu/shared/rest/middlewares/rate_limit_middleware.py`,
   mirroring the web app's existing `middlewares/*-middleware.ts` naming
   (`apps/web/src/middlewares/require-auth-middleware.ts`).
3. **Cache provider contract**: `CacheProvider` Protocol in
   `shifu/shared/core/interfaces/cache_provider.py`, with a single atomic operation
   (e.g. `consume(key, capacity, refill_per_second) -> RateLimitDecision`) so the
   token-bucket policy is a middleware/pipe concern, not baked into the adapter.
   Adapter: `shifu/shared/providers/cache/redis/redis_cache_provider.py`
   (`RedisCacheProvider`), per the exact path `provision-layer-rules.md` names for this
   ticket. The adapter must perform the check-and-decrement as one atomic Redis
   operation (e.g. a server-side script) — this is a ticket-mandated constraint, not a
   prescribed algorithm.
4. **429 response body**: a JSON body via the existing `RateLimitError` →
   HTTP-error-mapping convention (no new schema), plus a `Retry-After` header carrying
   the whole-second wait time.
5. **Startup failure body**: Redis unavailability at startup raises during the FastAPI
   `lifespan` context (using `ServiceUnavailableError` semantics) so the process exits
   instead of serving traffic; this is the first fail-fast-on-dependency pattern in the
   codebase and sets precedent for future providers.

These are recommendations, not settled product decisions — flag any of them for change
before implementation starts.

## Functional requirements

- **RF-1**: The rate-limiting middleware applies to every registered route except
  `/health`.
- **RF-2**: Each client IP is limited by a token bucket with capacity 10 and a refill
  rate of 60 tokens per minute (1 per second).
- **RF-3**: A request that exceeds the bucket receives HTTP 429 with a `Retry-After`
  header stating the whole-second wait until a token is available.
- **RF-4**: The client IP used as the bucket key is the raw transport-layer peer
  address, unless that peer is present in the configured trusted-proxy allowlist, in
  which case the forwarded client IP from `X-Forwarded-For`/`X-Real-IP` is used
  instead.
- **RF-5**: The rate-limit check-and-decrement is atomic under concurrent requests
  against the same key — no interleaving of concurrent requests may admit more than
  `capacity` requests before the refill schedule allows it.
- **RF-6**: `REDIS_URL` and the trusted-proxy allowlist are read through one
  centralized settings boundary; no other module reads these values via `os.getenv`.
- **RF-7**: FastAPI startup verifies Redis connectivity and aborts startup (the process
  does not begin serving requests) if Redis is unreachable.
- **RF-8**: `apps/server/.env.example` documents `REDIS_URL=redis://localhost:6379/0`.

*(Traceability: RF-1 through RF-8 derive directly from the SHIFU-58 description; no
`RP-*` applies — see **Traceability**.)*

## Acceptance criteria

- **CA-1** (RF-1): `GET /health` succeeds regardless of how many prior requests were
  made from the same client in the current window; a request to any other registered
  route is subject to the limiter.
- **CA-2** (RF-2, RF-3): From a fresh bucket, up to 10 rapid requests from the same
  client IP succeed; the next request in the same sub-second window returns 429. A
  client sending at a sustained rate of 1 request/second never receives 429 from the
  limiter.
- **CA-3** (RF-3): Every 429 response includes a `Retry-After` header with a positive
  integer value.
- **CA-4** (RF-4): A forwarded IP header from a peer that is *not* in the trusted-proxy
  allowlist is ignored; the bucket key uses the real connection IP. A forwarded IP
  header from a peer that *is* in the allowlist is honored as the bucket key.
- **CA-5** (RF-5): Firing concurrent requests against the same client IP does not allow
  more than `capacity` requests to succeed before the refill schedule would allow it
  (no race condition admits extra requests).
- **CA-6** (RF-6, RF-8): Starting the server with `REDIS_URL` unset or pointing at an
  unreachable instance fails startup with a clear, non-silent error. Starting with a
  reachable `REDIS_URL` succeeds and `/health` responds normally afterward.
  `apps/server/.env.example` contains the `REDIS_URL` line verbatim.

## Manual validation

Automated tests are explicitly excluded from this ticket's deliverables, so acceptance
relies on manual validation. A follow-up ticket should add automated adapter/middleware
coverage per `provision-layer-rules.md`.

- **VM-1** (CA-2, CA-3): Run the server locally against a manually started local Redis
  instance (e.g. `docker run --rm -p 6379:6379 redis:alpine`, started outside this
  Spec's scope). Send 11 rapid requests to a non-health route with `curl`; confirm the
  first 10 return their normal status and the 11th returns 429 with a `Retry-After`
  header.
- **VM-2** (CA-6): Stop Redis (or point `REDIS_URL` at an unreachable host) and start
  the server; confirm it exits/fails to start rather than serving traffic. Restore
  Redis and confirm the server starts and `/health` returns 200.
- **VM-3** (CA-4): With the trusted-proxy allowlist empty (default), send a request
  with a forged `X-Forwarded-For` header and confirm it is ignored (rate limiting
  tracks the real peer IP). Add the test client's peer address to the allowlist,
  resend with a different `X-Forwarded-For` value, and confirm that value is now used
  as the bucket key (e.g. by exhausting its bucket independently of the real peer's).
- **VM-4** (CA-1): While a client's bucket is exhausted from VM-1, confirm `GET
  /health` still returns 200 for the same client.

## Automated quality gates

No new automated tests are added in this slice, but all existing gates must stay
green for the changed code (run from `apps/server`):

- **CI-1**: `uv run poe check:types` — strict Pyright/basedpyright typing for the new
  Protocol, provider, middleware, and settings code.
- **CI-2**: `uv run poe check:lint` — Ruff lint and format check.
- **CI-3**: `uv run poe check:architecture` — `tach check --dependencies`, verifying
  the new `core/interfaces` Protocol stays framework-independent and the Redis adapter
  stays confined to the providers layer.
- **CI-4**: `uv run poe test` — full existing suite must still pass (no regression),
  even though this ticket adds no new test files. **Precondition**: `tests/conftest.py`
  drives `TestClient` as a context manager, which runs the FastAPI lifespan — once
  RF-7's startup check is wired in, a reachable Redis instance becomes a precondition
  for running this suite at all, the same way integration tests already assume the
  Compose-provided services are reachable. This does not conflict with "no Redis
  provisioning in this task" (that excludes adding infrastructure-as-code, not running
  tests against a manually started instance).

## Constraints

- **Module**: Shared/cross-cutting; must not absorb business-module logic and must not
  be imported by a business module's `core` (per `core-package-rules.md`).
- **Contract**: Adds a new possible `429` response with a `Retry-After` header to every
  existing and future route except `/health`. This is a cross-cutting HTTP contract
  addition, not a schema change to any existing 2xx response.
- **Persistence**: None in PostgreSQL. State is ephemeral in Redis only, keyed by
  client IP, and should carry a TTL so idle buckets do not accumulate indefinitely.
- **Security**: Forwarded-IP headers must never be trusted from an unconfigured peer
  (spoofing risk — CA-4). `REDIS_URL` is infrastructure configuration and must flow
  only through the settings boundary; it must never be logged.
- **Privacy**: Client IP addresses are processed only transiently for rate-limiting
  and are not persisted beyond the ephemeral, TTL-bound Redis keys.
- **Accessibility**: Not applicable — no user-facing UI in this ticket.
- **Observability**: No new metrics/monitoring endpoint is introduced in this ticket
  (none exists yet to exclude besides `/health`). Startup failures must surface a
  clear, actionable error rather than an ambiguous crash.
- **Design**: Not applicable — backend-only infrastructure change, no Pencil reference.

## Dependencies and follow-ups

- Redis becomes a required runtime dependency of the Shifu Server. `documentation/
  infrastructure.md` does not exist yet; when it is created, it must record Redis
  (connection via `REDIS_URL`, no committed provisioning) as an operational
  dependency. Until then, this Spec is the authoritative record of that dependency.
- Follow-up: add automated coverage (adapter contract test for `RedisCacheProvider`,
  middleware behavior test) once this ticket's "no test files" exclusion is lifted by a
  later ticket.
- Follow-up: if Shifu later introduces a reverse proxy/load balancer in front of
  FastAPI, the trusted-proxy allowlist default and deployment configuration must be
  revisited.

## Revision history

- v1 (2026-09-16): Initial draft from Jira SHIFU-58. No `RP-*`/`JN-*` applies (see
  **Traceability**). Awaiting review of **Decisions and assumptions** before moving to
  `ready`.
- v1 (2026-09-16): Marked `ready` — assumptions presented and unchallenged before the
  execution Plan was requested. Added the CI-4 precondition about Redis reachability
  for the test suite once RF-7 lands.
- v1 (2026-09-16): Marked `implemented` after executing `plan.md`. All RF-*/CA-* hold;
  see `evaluation.md` for the acceptance matrix, gate results, and one fixed finding
  (ACH-1: Uvicorn's default proxy-header trust was overriding RF-4 for local
  connections; fixed in `apps/server/src/main.py`).
