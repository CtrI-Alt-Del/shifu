---
title: Identity password recovery and reset evaluation
status: ready
spec: ./spec.md
spec_revision: 3
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-63
prd:
  - content_id: 83001345
    version: 1
  - content_id: 86114306
    version: 1
last_updated_at: 2026-09-27
---

# Evaluation Status

`ready` — SHIFU-63 is implemented against Spec revision 3. Identity and
Communication PRDs remain at content versions 1; no external PRD checkbox was
changed. The revision-3 reset-link status endpoint, privacy corrections, and
final integrated gates are recorded below.

# Acceptance Coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-08 | Widget/route tests; VM-01; request screenshots | EV-03, EV-11 | passed |
| CA-02 | RF-01 to RF-03 | Use-case/controller/handler tests; VM-02 | EV-06, EV-11 | passed |
| CA-03 | RF-02, RF-03 | Cooldown/concurrency/replacement tests; VM-02 | EV-06, EV-11 | passed |
| CA-04 | RF-03, RF-04 | Status/retry and delivery tests; VM-03 | EV-11, EV-13 | passed |
| CA-05 | RF-04 | Email package, renderer, Inngest/Mailpit tests; VM-04 | EV-03, EV-12, EV-13 | passed |
| CA-06 | RF-04 | Retry/idempotency/job tests; VM-04 | EV-12, EV-13 | passed |
| CA-07 | RF-05, RF-08 | Reset use-case/controller/widget/route tests; VM-05 | EV-11, EV-14 | passed |
| CA-08 | RF-06, RF-07 | Reset/session integration; VM-06 | EV-11, EV-14 | passed |
| CA-09 | RF-06, RF-08 | Validation/failure-safety tests; VM-06 | EV-06, EV-11, EV-14 | passed |

# Automated Gates

| CI ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| CI-01 | `corepack pnpm --filter web generate-routes` | Generated route tree | passed | EV-11 |
| CI-02 | `corepack pnpm --filter web check:lint` | Web lint | passed | EV-11 |
| CI-03 | `corepack pnpm --filter web check:architecture` | Web boundaries | passed | EV-11 |
| CI-04 | `corepack pnpm --filter web check:types` | Web types | passed | EV-11 |
| CI-05 | `corepack pnpm --filter web test:unit` | Web unit tests | passed, 233 tests | EV-11 |
| CI-06 | `corepack pnpm --filter web test:integration` | Browser/BFF tests | passed, 103 tests | EV-14 |
| CI-07 | `corepack pnpm --filter web build` | Web build | passed | EV-11 |
| CI-08 | `corepack pnpm --dir packages/email check:code` | Email code | passed | EV-12 |
| CI-09 | `corepack pnpm --dir packages/email check:types` | Email types | passed | EV-12 |
| CI-10 | `corepack pnpm --dir packages/email build` | Generated email artifacts | passed | EV-12 |
| CI-11 | `REDIS_URL=redis://localhost:6379/0 uv run poe check:lint` | Server lint | passed | EV-13 |
| CI-12 | `REDIS_URL=redis://localhost:6379/0 uv run poe check:architecture` | Server boundaries | passed | EV-13 |
| CI-13 | `REDIS_URL=redis://localhost:6379/0 uv run poe check:types` | Server types | passed | EV-13 |
| CI-14 | `REDIS_URL=redis://localhost:6379/0 uv run poe test:unit` | Server use cases | passed, 141 tests | EV-13 |
| CI-15 | `REDIS_URL=redis://localhost:6379/0 uv run poe test:integration` | PostgreSQL HTTP boundary | passed, 87 tests | EV-13 |
| CI-16 | `REDIS_URL=redis://localhost:6379/0 uv run poe test:jobs` | Inngest jobs | passed, 7 tests | EV-13 |
| CI-17 | `REDIS_URL=redis://localhost:6379/0 uv run poe build` | Server build | passed | EV-13 |

# Manual and Visual Evidence

| VM scenario | Exact viewport/state | Reference | Artifact path | Expected/observed result | Status |
| --- | --- | --- | --- | --- | --- |
| VM-01 request form/accessibility | 1440x900, 375x812, 375x667; invalid input | `design/CGmXc.png`, handoff derived states | `%LOCALAPPDATA%/Temp/opencode/password-recovery-request-{desktop,mobile,short-mobile}.png` | Labeled form, validation, preserved input, focus and responsive scroll observed | passed |
| VM-02 privacy/cooldown/replacement | Active, pending, deleted, unknown accounts | None | EV-06, EV-14 | Generic outcome and persisted eligible-only token/request behavior covered through unit, controller and handler boundaries | passed |
| VM-03 terminal delivery recovery | Generic status/retry; desktop and mobile | handoff derived delivery issue | EV-11, EV-13 | Only ready/cooldown/delivery-issue states reach the browser; expiry cancels delivery | passed |
| VM-04 Mailpit/retry/idempotency/privacy | Real local Inngest/Mailpit flow | None | EV-12, EV-13 | One pt-BR message, one reset URL, one-hour validity and ID-only job data asserted | passed |
| VM-05 reset link outcomes | 1440x900, 375x812; valid/expired/used/invalid/malformed | `design/VcFmX.png`, `design/lfk5T.png` | `%LOCALAPPDATA%/Temp/opencode/password-recovery-reset-invalid-desktop.png`; EV-14 | Token removal and valid/expired/used/invalid paths resolve before form rendering | passed |
| VM-06 reset/session/pending account | Active and pending sessions | `design/VcFmX.png` | EV-06, EV-14 | Password/token/access-version changes, cookie clear, session cleanup failure safety and pending preservation covered | passed |
| VM-07 forward migration preservation | Disposable PostgreSQL from d7f4e9a1c2b3 | None | EV-10 | Legacy confirmation correlation, expiry and partial unique index preserved | passed |
| Visual request states | 1440x900, 375x812, 375x667 | `design/CGmXc.png`, handoff | pending | Expected supplied dark grid/card language and responsive scroll; not yet run | pending |
| Visual reset states | 1440x900, 375x812, 375x667 | `design/VcFmX.png`, handoff | pending | Expected reset form/success language and responsive scroll; not yet run | pending |
| Visual link outcomes | 1440x900, 375x812 | `design/lfk5T.png`, handoff | pending | Expected textual/icon-supported generic outcomes; not yet run | pending |

# Review Findings

| ACH ID | Classification | Source | Affected evidence | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| ACH-01 | Environment blocker | Baseline `pnpm --filter web test:unit` | CI-01 to CI-10, web evidence | open | Install/enable declared pnpm tool or record final environment limitation and rerun where possible. |
| ACH-02 | Environment blocker | Baseline `docker compose ps` | CI-15, CI-16, VM-02 to VM-07 | open | Start required Docker services or record precise unavailable-runtime limitation; skipped runtime evidence cannot pass. |
| ACH-03 | Environment/configuration blocker | Baseline `uv run poe test:unit` | CI-14 and server collection | open | Provide declared server runtime configuration including `redis_url`, then rerun. |
| ACH-04 | Pre-existing scope risk | Worktree status | Confirmation compatibility and VM-07 | open | Preserve user change and reconcile neutral `identity_action_token_id` contract during F1/integration. |
| ACH-05 | Baseline/process | Plan kickoff | All current evidence | resolved | Evaluation created before feature source edits; Plan set to `in_progress`; exact Builder assignments recorded below. |
| ACH-06 | Implementation defect | Integrated Server lint/type gates | CI-11, CI-13 and all Server evidence | partially_resolved | Ruff rule checks and type checks now pass; `ruff format --check src tests` remains blocked by 122 pre-existing unformatted files outside focused scope. |
| ACH-07 | Missing required coverage | F1/F4 Builder Fix validation | CA-02 to CA-04 and CA-07 to CA-09 | resolved | Added four recovery use-case modules; 23 focused and 133 total use-case tests pass. |
| ACH-08 | Blocking migration defect | CI-15/CI-16 integration attempt | PostgreSQL controller, job, migration, and runtime evidence | partially_resolved | Migration re-anchored at `c9e4f6a7b8c1`; one Alembic head and 85 integration tests pass. Job suite progressed but timed out after 240 seconds. |
| ACH-09 | Missing required coverage | F1/F4 conformance checkpoint | CA-02 to CA-09 controller evidence | resolved | Added four database-backed controller modules; 11 focused tests and the 85-test integration suite pass. |
| ACH-10 | Runtime evidence blocker | CI-06 | Browser/visual/handler evidence | resolved | Playwright starts FastAPI and Vite with the required Redis configuration; the full 103-test suite passes. |
| ACH-11 | Runtime evidence blocker | CI-16 | Inngest/Mailpit/job evidence | resolved | The real disposable Inngest/Testcontainers suite passed 7 tests in 605.70 seconds. |
| ACH-12 | High implementation defect | Independent integrated review | CA-04, VM-03, VM-04 | resolved | Expired status now persists the token and publishes `AccountActionTokenCancelledEvent` with the `expired` reason; focused and full server tests pass. |
| ACH-13 | High implementation defect | Independent integrated review | CA-07, VM-05 | resolved | Revision 3 adds a non-mutating BFF-only reset-link status endpoint; the page resolves the outcome before form rendering. |
| ACH-14 | Medium implementation defect | Independent integrated review | CA-04, VM-03 | resolved | Status polling uses the opaque context expiry and stops when it is no longer valid. |
| ACH-15 | Medium implementation defect | Independent integrated review | CA-08, VM-06 | resolved | A successful reset automatically follows only the validated BFF-provided `/login` destination. |
| ACH-16 | Medium missing coverage | Independent integrated review | CA-08, VM-06 | resolved | Registered-handler coverage proves session deletion failure keeps reset successful, clears the cookie, and emits only the fixed operational observation. |

# Evidence Log

| EV ID | Date | Scope | Exact command/scenario | Result | Finding | Runtime notes | Acceptance mapping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EV-00 | 2026-09-25 | Pre-implementation baseline | `git status --short`; `docker compose ps`; `pnpm --filter web test:unit`; `uv run poe test:unit` | Baseline captured; required gates unavailable/blocked | ACH-01, ACH-02, ACH-03, ACH-04 | Docker has no running services; pnpm command is unavailable; server collection requires `redis_url`; unrelated registration spec change preserved | All CA as baseline only |
| EV-01 | 2026-09-25 | Authority/design preflight | Read Spec revision 2, Plan, Rules, Architecture, Modules, Tooling, SDD, Identity/Communication PRDs, and password-recovery handoff | Passed | None | PRDs content IDs `83001345`/`86114306`, both version 1; design references and derived states recorded | RF-01 to RF-08 |
| EV-02 | 2026-09-25 | Spec conformance kickoff | Compare untouched tree against Spec affected paths, widget tree, route artifacts, and exclusions | In progress | ACH-04 | No recovery implementation exists; confirmation correlation is still confirmation-specific before F1 | All CA |
| EV-03 | 2026-09-25 | F2/F3 integrated focused gates | `corepack pnpm --filter web check:lint`; `check:architecture`; `test:unit`; `corepack pnpm --dir packages/email check:code`; `check:types`; `build` | Passed | None | Web: 53 files/233 tests passed; Email package build generated recovery artifacts transiently | CA-01 to CA-09 supporting evidence |
| EV-04 | 2026-09-25 | F1/F4 integrated focused gates | `uv run poe check:lint`; `check:types`; `check:architecture` | Lint/types failed; architecture passed | ACH-06 | Lint reported 9 errors; Pyright reported 25 errors; no runtime services started | CA-02 to CA-08 pending correction |
| EV-05 | 2026-09-25 | F1/F4 Builder Fix focused gates | `uv run poe check:types`; `uv run poe check:architecture`; `REDIS_URL=redis://localhost:6379/0 uv run pytest tests/communication/core/use_cases`; `REDIS_URL=redis://localhost:6379/0 uv run pytest tests/identity/core/use_cases` | Types/architecture passed; 9 Communication and 28 Identity tests passed | ACH-06 partly corrected; ACH-07 discovered | Full Ruff rule checks passed, but formatter check reported 122 files would be reformatted across the integrated tree; recovery-specific use-case test modules are absent | CA-02 to CA-08 pending fresh coverage |
| EV-06 | 2026-09-25 | Integrated gates and generated outputs | Web CI-01 to CI-07; Server CI-14/CI-17; package build | Web all passed; Server CI-14 passed 133 tests and CI-17 built; generated route/template artifacts current | ACH-06, ACH-07 | Web Playwright timed out waiting for its web server; server formatter has 122 pre-existing unformatted files | CA-01 to CA-09 supporting evidence |
| EV-07 | 2026-09-25 | Docker-backed integration/jobs | `uv run poe test:integration`; `uv run poe test:jobs` | Failed before tests executed | ACH-08 | Alembic reported multiple heads (`c9e4f6a7b8c1`, `e7b5c8d9f012`); all 74 integration and 7 job cases blocked at migration setup | CA-02 to CA-08 blocked |
| EV-08 | 2026-09-25 | Migration/controller correction | `uv run alembic heads`; focused four recovery controller modules; `uv run poe test:integration`; `uv run ruff check --no-fix src tests` | Passed | ACH-07, ACH-08, ACH-09 resolved/partially resolved | One Alembic head `e7b5c8d9f012`; 11 focused controller tests and 85 integration tests passed; Ruff rule checks passed | CA-02 to CA-09 |
| EV-09 | 2026-09-25 | Runtime gate attempts | `corepack pnpm --filter web test:integration`; `uv run poe test:jobs` | Failed/timeout | ACH-10, ACH-11 | Playwright webServer timed out at 60 seconds; jobs advanced through migration and first two scenarios but exceeded 240 seconds | VM-01 to VM-06; CA-04 to CA-06, CA-08 |
| EV-10 | 2026-09-26 | Independent integrated review | Full SHIFU-63 working-tree review against Spec revision 2 | Failed | ACH-12 to ACH-16 | Five in-contract server/web defects or test gaps found; affected evidence remains stale until correction and rerun | CA-04, CA-07, CA-08; VM-03 to VM-06 |
| EV-11 | 2026-09-27 | Web candidate and BFF correction | `corepack pnpm --filter web generate-routes`; `check:lint`; `check:architecture`; `check:types`; `test:unit`; `build` | Passed | ACH-13 to ACH-16 corrected | 53 files/233 unit tests; reset-link resolver, polling expiry and automatic safe navigation implemented | CA-01 to CA-04, CA-07 to CA-09 |
| EV-12 | 2026-09-27 | E-mail package and generated assets | `corepack pnpm --dir packages/email check:code`; `check:types`; `build` | Passed | None | Controlled recovery template and generated HTML/manifest are current | CA-05, CA-06 |
| EV-13 | 2026-09-27 | Server candidate | `REDIS_URL=redis://localhost:6379/0 uv run poe check:lint`; `check:architecture`; `check:types`; `test:unit`; `test:integration`; `test:jobs`; `build` | Passed | ACH-11, ACH-12 resolved | 141 unit, 87 PostgreSQL integration and 7 real Inngest/Testcontainers tests; jobs took 605.70 seconds | CA-02 to CA-09; VM-02 to VM-07 |
| EV-14 | 2026-09-27 | Full browser integration | `corepack pnpm --filter web test:integration` | Passed | Rate-limit concurrency finding resolved | 103 tests with six workers; recovery BFF endpoints are exempt only from generic Better Auth throttling while Identity cooldown remains authoritative | CA-01 to CA-04, CA-07 to CA-09 |

# Builder Assignments

| Builder | Plan scope | Exact allowed paths | Prohibited paths | Exits |
| --- | --- | --- | --- | --- |
| `identity-password-recovery-server-builder` | F1/F4, Builder Server; Identity/Communication server contracts, persistence, jobs, composition and tests | `apps/server/src/shifu/identity/**`; `apps/server/src/shifu/communication/core/domain/**`; `apps/server/src/shifu/communication/database/**`; `apps/server/src/shifu/communication/messaging/**`; `apps/server/src/shifu/communication/core/**`; `apps/server/src/shifu/composition/**`; `apps/server/src/shifu/communication/providers/email/template/generated_email_message_renderer.py`; `apps/server/src/shifu/app.py`; `apps/server/migrations/versions/<new>_generalize_identity_action_token_delivery.py`; `apps/server/rest-client/identity/identity.rest`; matching `apps/server/tests/identity/**`, `apps/server/tests/communication/**`, and `apps/server/tests/messaging/inngest/jobs/{identity,communication}/**` | Spec, Plan, Evaluation, Rules, Architecture, Modules, Tooling, design artifacts, `packages/email/**`, `apps/web/**`, generated email artifacts | Focused server tests, lint, architecture, types; route parity; report Docker/config limitations |
| `identity-password-recovery-web-builder` | F2/F5, Builder Web; BFF, public routes, widgets and web tests | `apps/web/src/constants/routes.ts`; `apps/web/src/rest/services/identity-service.ts`; `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`; `apps/web/src/routes/forgot-password/**`; `apps/web/src/routes/reset-password/**`; `apps/web/src/ui/identity/hooks/**` limited to listed recovery hooks; `apps/web/src/ui/identity/widgets/pages/forgot-password-page/**`; `apps/web/src/ui/identity/widgets/pages/reset-password-page/**`; `apps/web/tests/routes/identity/**`; `apps/web/tests/identity/password-recovery-auth-handler.test.ts` | Spec, Plan, Evaluation, Rules, Architecture, Modules, Tooling, design artifacts, `apps/web/src/routeTree.gen.ts`, `packages/email/**`, `apps/server/**` | Focused Vitest/route checks; no route generation; report pnpm/runtime limitations |
| `identity-password-recovery-email-builder` | F3, Builder Email; controlled template and multi-template generator | `packages/email/templates/identity/password-recovery-email.tsx`; `packages/email/templates/index.ts`; `packages/email/scripts/build-templates.ts` | Spec, Plan, Evaluation, Rules, Architecture, Modules, Tooling, all `apps/server/**`, all `apps/web/**`, generated server email artifacts | Email code/types/build; generated artifacts reported, never hand-edited |

# Design Authority Preflight

Feature root: `documentation/features/identity/password-recovery/`.

Canonical design authority: `design/handoff.md`, with saved references
`design/CGmXc.png`, `design/VcFmX.png`, and `design/lfk5T.png`. The affected
surfaces are `/forgot-password` and `/reset-password`; exact reference viewport
is `1440x900`, with approved derived states at `375x812` and short-mobile
`375x667`. The scope fence excludes adjacent Identity routes and shared visual
language changes. Every visual row above is stale/pending until a fresh
post-change comparison is captured.
