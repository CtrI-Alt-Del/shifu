---
feature: Redis-backed rate limiting
module: shared (cross-cutting infrastructure)
jira: SHIFU-58
status: ready
spec_version: 1
---

# Evaluation: Redis-backed rate limiting for the Shifu Server

Acceptance matrix and evidence for `spec.md` (v1) / `plan.md` (v1), executed and
validated in the same session. All commands ran from `apps/server`. Manual
validation used a temporary, non-persistent Redis container
(`docker run --rm -p 16379:6379 redis:7-alpine`) started and torn down for this
purpose; no shared Compose service was added or modified, per the Spec's exclusion.

## Acceptance matrix

| CA | Result | Evidence |
| --- | --- | --- |
| CA-1 (`/health` exempt) | ✅ Pass | VM-4: `/health` returned 200 while the same client's rate-limit bucket was exhausted on `/curriculum`. |
| CA-2 (burst 10, sustained 1/s) | ✅ Pass | VM-1: 10 rapid requests returned their normal (404, unmapped-route) status; the 11th returned 429. A single request issued ~1s after exhaustion succeeded (404, not 429), confirming the 1-token/s refill. |
| CA-3 (`Retry-After` header) | ✅ Pass | Observed `retry-after: 1` on every 429 response during VM-1/VM-3 testing. |
| CA-4 (trusted-proxy-gated IP resolution) | ✅ Pass, after one fix | See **ACH-1** below. After the fix: forged `X-Forwarded-For` from an untrusted peer produced key `rate-limit:127.0.0.1` (header ignored); the same header from a peer added to `TRUSTED_PROXY_IPS` produced key `rate-limit:5.5.5.5` (header honored). Verified directly against Redis keys (`redis-cli KEYS '*'`), not just HTTP status. |
| CA-5 (atomic consume, no race) | ✅ Pass by construction | The Lua script (`redis_cache_provider.py`) performs read, refill computation, and decrement in one `EVAL`, so Redis's single-threaded command execution makes the operation atomic. Not separately load-tested for concurrency in this pass (see **Follow-ups**). |
| CA-6 (fail-fast startup, `.env.example`) | ✅ Pass | VM-2: with Redis stopped, startup raised `ServiceUnavailableError` and logged `ERROR: Application startup failed. Exiting.`; `/health` returned no response (`curl` exit 7 / status `000`). With Redis restored, startup succeeded and `/health` returned 200. `apps/server/.env.example` contains `REDIS_URL=redis://localhost:6379/0` verbatim. |

## Automated quality gates

| Gate | Command | Result |
| --- | --- | --- |
| CI-1 | `uv run poe check:types` | ✅ 0 errors, 0 warnings |
| CI-2 | `uv run poe check:lint` | ✅ All checks passed, all files formatted |
| CI-3 | `uv run poe check:architecture` | ✅ All modules validated |
| CI-4 | `uv run poe test` | ✅ 1 passed (existing suite; ran against a reachable local Redis per the CI-4 precondition already recorded in `spec.md`) |

## Findings

- **ACH-1** (severity: high, status: fixed) — During VM-3, manual testing revealed
  that Uvicorn's own built-in proxy-header trust (`proxy_headers`, enabled by
  default with `forwarded_allow_ips` defaulting to `127.0.0.1`) was rewriting
  `request.client` from a forged `X-Forwarded-For` header *before* our middleware
  ever ran, because the test client connected from `127.0.0.1` — which happens to
  be Uvicorn's own default trusted value, entirely independent of our
  `TRUSTED_PROXY_IPS` setting. This silently defeated RF-4/CA-4 for exactly the
  most common local/dev connection path. Fixed by adding `proxy_headers=False` to
  `uvicorn.run(...)` in `apps/server/src/main.py`, making `RateLimitMiddleware` the
  single source of truth for proxy trust, as RF-4 requires. Confirmed fixed by
  re-running VM-3 (forged header from an untrusted peer now correctly ignored).
  This is exactly the kind of defect the Spec's manual-validation requirement
  (VM-3) exists to catch, and it would not have been caught by CI-1/2/3 alone.

## Delivery disposition

- RF-1 through RF-8: **implemented**, evidence above.
- No `RP-*`/`JN-*` applies (see `spec.md` → Traceability); no product-PRD
  disposition to record.

## Follow-ups (carried from spec.md, unchanged)

- Add automated adapter/middleware test coverage (explicitly out of scope for
  SHIFU-58).
- Load-test CA-5's atomicity claim under real concurrency once test infrastructure
  exists.
- Record Redis as an operational dependency in `documentation/infrastructure.md`
  once that document exists.
- Revisit the trusted-proxy allowlist default if a reverse proxy is introduced in
  front of FastAPI.

## Revision history

- v1 (2026-09-16): Initial evaluation. All CA-*/CI-* pass. One finding (ACH-1)
  raised and fixed during validation.
