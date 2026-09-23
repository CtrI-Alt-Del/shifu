---
feature: Redis-backed rate limiting
module: shared (cross-cutting infrastructure)
jira: SHIFU-58
status: completed
spec_version: 2
---

# Plan: Redis-backed rate limiting for the Shifu Server

Execution ledger for `spec.md` (v2, `ready`). This is a single-agent, sequential build
— every layer depends on the one before it, so no parallel subagents are used. All
paths are under `apps/server/src/shifu` unless noted; all commands run from
`apps/server`.

## Sequence

### Step 1 — Cache-provider contract (core)

- **Traces**: RF-5.
- **Files**: `shared/core/interfaces/cache_provider.py` (new, `CacheProvider`
  Protocol with one atomic operation, e.g. `consume(key, capacity,
  refill_per_second) -> RateLimitDecision`); `shared/core/domain/structures/
  rate_limit_decision.py` (new, decorated with the existing shared `structure`
  decorator — `allowed: bool`, `retry_after_seconds: int`).
- **Rule Pack**: `core-package-rules.md`, `python-code-conventions-rules.md`.
- **Depends on**: nothing.
- **Risk**: keeping the Protocol domain-oriented — it must not leak `redis`-specific
  types, keys formats, or SDK exceptions (core-package-rules.md's "Interfaces are
  structural ports").
- **Validation**: CI-1, CI-3 (`tach check --dependencies` must show no `redis` import
  from `core`).

### Step 2 — Settings boundary, dependency, and env file

- **Traces**: RF-6, RF-8.
- **Files**: `shared/settings.py` (new — single `pydantic-settings` class holding
  `redis_url: str` (required) and `trusted_proxy_ips: list[str]` (default empty));
  `apps/server/pyproject.toml` (add `redis` and `pydantic-settings` via `uv add
  redis pydantic-settings`, regenerating `uv.lock`); `apps/server/.env.example` (add
  `REDIS_URL=redis://localhost:6379/0`).
- **Rule Pack**: `provision-layer-rules.md`, `python-code-conventions-rules.md`.
- **Depends on**: nothing (safe to do alongside Step 1).
- **Risk**: `pydantic-settings` v2 API specifics (`BaseSettings`/`SettingsConfigDict`
  vs. v1 `Config` class) — check Context7 for the installed `pydantic` major version
  before writing this, per `AGENTS.md`'s guidance on Pydantic.
- **Validation**: CI-1, CI-2.

### Step 3 — Redis adapter

- **Traces**: RF-2, RF-5.
- **Files**: `shared/providers/cache/redis/redis_cache_provider.py` (new,
  `RedisCacheProvider` implementing `CacheProvider`; takes a constructed
  `redis.asyncio.Redis` client via its constructor — it does not read settings
  itself, per provision-layer-rules.md's "providers translate infrastructure").
  Perform the token-bucket check-and-decrement as one atomic server-side operation
  (e.g. `EVAL` of a small Lua script) so RF-5/CA-5 hold under concurrency; set a TTL
  on the bucket key so idle clients don't accumulate state forever (Constraints →
  Persistence).
- **Rule Pack**: `provision-layer-rules.md`, `python-code-conventions-rules.md`.
- **Depends on**: Step 1 (protocol/structure to implement), Step 2 (`redis` package
  installed).
- **Risk**: this is the highest-risk step — an incorrect Lua script or a non-atomic
  read-then-write allows the race CA-5 forbids. Reason through the script's
  correctness explicitly (single `EVAL` covering read, refill computation, and
  decrement) before moving on; do not split it into multiple round trips.
- **Validation**: CI-1, CI-3; exercised end-to-end later by VM-1/VM-3.

### Step 4 — Trusted-proxy IP resolution + rate-limit middleware

- **Traces**: RF-1, RF-2, RF-3, RF-4.
- **Files**: `shared/rest/middlewares/rate_limit_middleware.py` (new). Depends only
  on the `CacheProvider` Protocol (constructor-injected), not the concrete adapter.
  Logic: resolve client IP (raw peer unless peer ∈ trusted-proxy allowlist, then use
  `X-Forwarded-For`/`X-Real-IP`); skip entirely for `request.url.path` in
  `{'/health', '/identity/session'}`;
  call `CacheProvider.consume(...)` with capacity 10 / refill 1-per-second; on
  `allowed=False`, short-circuit with a 429 response carrying `Retry-After` and the
  existing `RateLimitError` JSON shape; otherwise call `call_next`.
- **Rule Pack**: `server-app-layer-rules.md`, `python-code-conventions-rules.md`.
- **Depends on**: Step 1 (types), Step 3 (needs a real adapter to be meaningfully
  testable end-to-end, even though the class itself only imports the Protocol).
- **Risk**: path matching must exclude exactly `/health` (confirm no other
  health/monitoring route exists before hardcoding — `shared/rest/router.py`
  registers only `/health` today, but re-check at implementation time in case
  Step 2's changes or concurrent work added another route); trusted-proxy allowlist
  parsing must handle both bare IPs and CIDRs without silently trusting everything on
  a parse error (fail closed, not open).
- **Validation**: CI-1, CI-2; VM-1, VM-3, VM-4.

### Step 5 — Composition: lifespan startup check + middleware registration

- **Traces**: RF-1, RF-7.
- **Files**: `app.py` (add a FastAPI `lifespan` async context manager that builds the
  `redis.asyncio.Redis` client from `Settings.redis_url`, `PING`s it, raises before
  yielding if unreachable — using `ServiceUnavailableError` semantics — stores the
  client/`RedisCacheProvider` on `app.state`, and closes the client on shutdown; wire
  `RateLimitMiddleware` via `app.add_middleware(...)`, constructed with the
  `RedisCacheProvider` from `app.state`).
- **Rule Pack**: `server-app-layer-rules.md`.
- **Depends on**: Steps 1–4 all complete.
- **Risk**: `create_app()` must remain safe to call repeatedly in tests
  (`server-app-layer-rules.md`) — the Redis client must be scoped per-app-instance via
  `app.state`/the lifespan closure, never a module-level global, so multiple
  `create_app()` calls in the same test process don't share or leak connections.
  This step also activates the CI-4 precondition already recorded in `spec.md`: once
  this lands, `uv run poe test` requires a reachable `REDIS_URL` because
  `tests/conftest.py:11` drives `TestClient` as a context manager, which runs this
  lifespan. Start a local Redis (`docker run --rm -p 6379:6379 redis:alpine`) before
  running the suite from this step onward.
- **Validation**: CI-1, CI-2, CI-3, CI-4 (with local Redis running); VM-2 exercises
  the failure path specifically (stop Redis, confirm startup aborts).

## Cross-cutting validation pass

After Step 5, run the full manual validation set from `spec.md` against the
integrated result: VM-1 through VM-4, in that order (VM-1/VM-4 need the server up
with Redis reachable; VM-2 needs it stopped; VM-3 needs the allowlist toggled).
Then run CI-1 through CI-4 once more on the integrated tree.

## Ownership and parallelism

Single Builder, sequential (Step 1 and Step 2 may be done in either order or
interleaved since neither depends on the other, but Steps 3–5 are strictly
sequential). Not delegated to parallel subagents — the layers are too interdependent
for independent ownership to reduce risk here.

## Execution notes

All 5 steps completed as sequenced. One deviation discovered during Step 4/5
manual validation: Uvicorn's own default `proxy_headers=True` behavior (trusting
`X-Forwarded-For` from peer `127.0.0.1` regardless of our app-level config) was
silently overriding RF-4 for local/dev connections. Fixed by adding
`proxy_headers=False` to `uvicorn.run(...)` in `apps/server/src/main.py`, which
was not an anticipated file in the original plan. Full detail and evidence in
`evaluation.md` (ACH-1).

## Out of scope reminders (from spec.md)

Do not provision Redis in Docker Compose, do not add automated test files, and do not
create `documentation/infrastructure.md` as part of this Plan — these remain explicit
exclusions carried over from the Spec.
