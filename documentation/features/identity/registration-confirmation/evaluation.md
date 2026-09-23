---
title: Identity registration and account confirmation evaluation
status: in_progress
spec: ./spec.md
spec_revision: 11
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-61
prd_content_ids:
  identity: 83001345
  communication: 86114306
prd_version: 1
last_updated_at: 2026-09-21
---

# Evaluation Status

Implementation is in progress under Spec revision `11`. This Evaluation records
the pre-implementation baseline, authority preflight, acceptance coverage, failed
or unavailable validation attempts, and current evidence. It is not a conclusion.

- **Spec:** `ready`, revision `11`.
- **Plan:** `in_progress`; F1-F8 are tracked in [`plan.md`](./plan.md).
- **Authority:** Identity PRD content `83001345`, version `1`, and Communication
  PRD content `86114306`, version `1`, reread on 2026-09-21. Jira `SHIFU-61` was
  reread with status `Fazendo` and updated `2026-09-18T12:21:15.369-0300`.
- **Baseline:** No registration-confirmation implementation, e-mail package,
  Communication delivery use case, confirmation routes, or feature Evaluation
  existed before this pass. Existing Identity sign-in/core and shared messaging
  foundations remain in scope only where the Spec explicitly reconciles them.
- **Worktree:** Pre-existing changes in sign-in artifacts, Rule Packs, tooling,
  `skills-lock.json`, and the untracked SHIFU-61 Spec/design directory were
  preserved. No unrelated change is claimed as SHIFU-61 evidence.

## Acceptance Coverage

| Criterion | RF coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| `CA-01` | `RF-01`, `RF-11` | Widget/route behavior and `VM-01` | Pending implementation | pending |
| `CA-02` | `RF-02` | Widget, use-case and controller validation | Pending implementation | pending |
| `CA-03` | `RF-02`, `RF-04` | Registration persistence, pending context and `VM-02` | Pending implementation | pending |
| `CA-04` | `RF-03` | Duplicate response and no-new-state evidence | Pending implementation | pending |
| `CA-05` | `RF-04`, `RF-05` | Package build, real delivery job and `VM-03` | Pending implementation | pending |
| `CA-06` | `RF-06` | Communication idempotency/concurrency and job evidence | Pending implementation | pending |
| `CA-07` | `RF-06` | Retry/terminal delivery and `VM-04` | Pending implementation | pending |
| `CA-08` | `RF-07`, `RF-08` | One-time activation, session continuation and `VM-05` | Pending implementation | pending |
| `CA-09` | `RF-08` | Distinct recovery states and `VM-06` | Pending implementation | pending |
| `CA-10` | `RF-09` | Cooldown boundary and no-new-state evidence | Pending implementation | pending |
| `CA-11` | `RF-09` | Concurrent replacement, invalidation and `VM-07` | Pending implementation | pending |
| `CA-12` | `RF-10` | Expiry, redaction, reuse and `VM-08` | Pending implementation | pending |
| `CA-13` | `RF-11` | Accessibility, keyboard, focus and state matrix | Pending implementation | pending |

## Automated Gates

| ID | Command/sensor | Baseline result | Current evidence |
| --- | --- | --- | --- |
| `CI-01`-`CI-03` | E-mail package checks/build | Not executable; `packages/email` is absent | Passed: `npm --prefix packages/email run check:code`, `check:types` and `build`; wheel package-data verifier passed. `EV-F3-01` |
| `CI-04`-`CI-10` | Web generation, lint, architecture, types, unit, integration and build | Not executable; `pnpm` is not available in the environment | Static gates passed through installed local binaries: TypeScript, Biome, Dependency Cruiser, Vitest (28 tests) and Vite build. Playwright remains blocked because its declared server command requires unavailable `pnpm`. `EV-F6-01` |
| `CI-11` | `uv run alembic check` from `apps/server` | Pending feature migration; not run at baseline | Pending implementation |
| `CI-12` | `uv run poe check:lint` from `apps/server` | Failed baseline format check on 86 pre-existing files; Ruff check passed | `EV-BASELINE-01` |
| `CI-13` | `uv run poe check:architecture` from `apps/server` | passed | Passed after implementation. `EV-F4-01` |
| `CI-14` | `uv run poe check:types` from `apps/server` | passed | Passed after implementation. `EV-F4-01` |
| `CI-15` | `uv run poe test:unit` from `apps/server` | passed: 8 tests, 2 existing deprecation warnings | Passed: 45 tests, with the same 2 pre-existing deprecation warnings. `EV-F4-01` |
| `CI-16` | `uv run poe test:integration` from `apps/server` | blocked: Docker Desktop daemon unavailable; 6 setup errors | `EV-BASELINE-01` |
| `CI-17` | `uv run poe test:jobs` from `apps/server` | blocked: Docker Desktop daemon unavailable | `EV-BASELINE-01` |
| `CI-18` | Server build and generated package-data verifier | Pending implementation | Pending implementation |

## Manual And Visual Evidence

`VM-01` through `VM-08` are defined in `spec.md`. No manual or Playwright
acceptance evidence has been captured yet. The web runtime and Docker-backed local
services are unavailable in the baseline environment; this limitation must not be
reported as passing evidence.

## Review Findings

No Implementation Reviewer pass has run. Findings will be recorded as `ACH-*`
without removing failed attempts or invalidated evidence.

## Evidence Log

### `EV-BASELINE-01` — Pre-implementation repository and environment baseline

- **Date:** 2026-09-21.
- **Scope:** Repository state before SHIFU-61 implementation, including current
  manifests, existing Identity/Communication foundations, and available local
  services/tooling.
- **Authority:** Complete Identity PRD `83001345` v1 and Communication PRD
  `86114306` v1 were read through Atlassian Shifu MCP. Jira `SHIFU-61` was read
  and matches the recorded source metadata. No external object was mutated.
- **Server static checks:** `uv run poe check:architecture` passed and
  `uv run poe check:types` passed. `uv run poe check:lint` reported Ruff checks
  passed but the repository format check failed on 86 existing files; no unrelated
  formatting changes were made.
- **Server unit tests:** `uv run poe test:unit` passed 8 tests with 2 existing
  Starlette/AnyIO deprecation warnings.
- **Server integration:** `uv run poe test:integration` reached fixture setup but
  failed with 6 Docker/Testcontainers setup errors because the Docker Desktop
  Linux engine named pipe was unavailable. This is an environment limitation, not
  acceptance evidence.
- **Web checks:** `pnpm --filter web check:lint`, `check:architecture`,
  `check:types`, and `test:unit` were not executable because `pnpm` is not
  installed or available on PATH. No web criterion is promoted from this result.
- **Runtime:** `docker compose ps` could not connect to the Docker Desktop Linux
  engine. PostgreSQL, Inngest, Mailpit, and browser/runtime validation are not
  available in this baseline.
- **Worktree:** Existing unrelated modifications were preserved and excluded from
  feature claims. The SHIFU-61 feature directory contained `spec.md`, `plan.md`,
  design references, and handoff material but no `evaluation.md` or implementation.

Failed attempts and unavailable services remain part of the evidence history. They
must be superseded only by fresh, current validation after implementation.

### `EV-F3-01` — Generated e-mail package and wheel content

- **Date:** 2026-09-21.
- **Commands:** `npm --prefix packages/email run check:code`, `check:types`, and
  `build`; `uv run poe build`; and `uv run python
  scripts/verify_email_package_data.py dist\\shifu-1.38.1-py3-none-any.whl` from
  `apps/server`.
- **Result:** Passed. The deterministic e-mail package checks/build and server-wheel
  inspection include the generated confirmation HTML and placeholder manifest.

### `EV-F4-01` — Server static and core validation

- **Date:** 2026-09-21.
- **Commands:** `uv lock --check`, `uv run poe check:architecture`, `uv run poe
  check:types`, and `uv run poe test:unit` from `apps/server`.
- **Result:** Passed. The lock resolved, architecture and strict typing passed, and
  45 core use-case tests passed. The suite retains two existing Starlette/AnyIO
  deprecation warnings.
- **Limitation:** `uv run poe check:lint` still fails only at its format stage on
  84 unrelated pre-existing files; Ruff checks passed. `uv run alembic check` and
  real database integration are blocked because the Docker Desktop engine is absent.

### `EV-F5-01` — Bounded expiry child processing

- **Date:** 2026-09-21.
- **Change:** `ExpireUnconfirmedAccountJob` now declares an Inngest concurrency
  limit of 25, preserving per-account durable execution while allowing a claimed
  batch of 100 events to complete without serial starvation.
- **Static checks:** Ruff and BasedPyright passed for the changed job.
- **Limitation:** The Docker-backed fan-out test was selected with
  `SHIFU_RUN_REAL_INNGEST_TESTS=1` but skipped precisely because Testcontainers
  cannot reach the Docker Desktop engine. The previous 300-second failure must be
  rerun on a Docker-capable host before this evidence is accepted for `CA-12`.

### `EV-F6-01` — Public route and web static validation

- **Date:** 2026-09-21.
- **Coverage added:** Playwright route suites for registration, pending
  confirmation, and e-mail confirmation model same-origin BFF transport, client
  validation, public-shell responsiveness, recovery, and URL token cleanup.
- **Commands:** local TypeScript compiler, `npm exec -- biome check src tests
  vitest.config.ts playwright.config.ts dependency-cruiser.config.cjs`, local
  Dependency Cruiser, `npm exec -- vitest run`, and local Vite build.
- **Result:** Passed: TypeScript, Biome, Dependency Cruiser (108 modules), Vitest
  (28 tests), and Vite production build. The build retains the pre-existing large
  client chunk warning.
- **Limitation:** Browser suites cannot start because the repository-declared
  Playwright web-server command requires `pnpm`, which is unavailable on PATH;
  real BFF handler integration also requires Docker-backed PostgreSQL.

## Traceability

| Authority | Local contract | Evidence status |
| --- | --- | --- |
| Identity `RP-01`, `RP-02`, `RP-08`, `RP-10`; `JN-01`, `JN-02`, `JN-08` | `RF-01`-`RF-04`, `RF-07`-`RF-11`; `CA-01`-`CA-04`, `CA-08`-`CA-13` | Pending implementation |
| Communication `RP-01`-`RP-07`; `JN-01`, `JN-03`-`JN-06` | `RF-03`-`RF-06`, `RF-09`, `RF-10`; `CA-03`-`CA-07`, `CA-10`-`CA-12` | Pending implementation |
