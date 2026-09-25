---
title: Identity account menu and current-session logout evaluation
status: completed
spec: ./spec.md
spec_revision: 3
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-69
prd_content_id: 83001345
prd_version: 1
last_updated_at: 2026-09-24
---

# Evaluation Status

Implementation is complete for Spec revision `3`. The canonical Identity PRD was
reread at content ID `83001345`, version `1`; no Jira or Confluence state was
mutated. All applicable web gates and real Better Auth/PostgreSQL handler coverage
pass against the final candidate.

## Acceptance Coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Account-menu/layout suites; VM-01; header/menu/desktop visual references | Current account summary contains only display name/e-mail | passed |
| CA-02 | RF-01, RF-02 | Account-menu hook/component and shared browser suite; VM-01 | Keyboard, Escape, outside dismissal and focus restoration | passed |
| CA-03 | RF-03 | Account-menu component and shared browser suite; VM-01 | Disabled non-focusable `Sua conta`; only `Sair` enabled | passed |
| CA-04 | RF-04, RF-05 | Registered Better Auth handler; PostgreSQL; VM-02 | Only initiating session row/cookie ends and second session remains authorized | passed |
| CA-05 | RF-05, RF-06 | Widget/hook/route suites; VM-01 and VM-02 | Pending, success, recoverable failure and retry | passed |
| CA-06 | RF-07 | Pending BFF handler/page/route suites; VM-03 | Pending verification/cookie cleanup with no authenticated-session effect | passed |
| CA-07 | RF-04 to RF-07 | Negative handler assertions; VM-02 and VM-03 | No tokens, identifiers, provider details or prohibited browser persistence | passed |

## Automated Gates

| CI ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| CI-01 | `corepack pnpm --filter web generate-routes` | Generated pending-confirmation route metadata | passed; generator warning only | EV-013 |
| CI-02 | `corepack pnpm --filter web check:lint` | Web source and tests | passed | EV-013 |
| CI-03 | `corepack pnpm --filter web check:architecture` | Web dependency direction | passed | EV-013 |
| CI-04 | `corepack pnpm --filter web check:types` | Strict TypeScript | passed | EV-013 |
| CI-05 | `corepack pnpm --filter web test:unit` | Widget, hook and context suites | passed: 26 files / 77 tests | EV-013 |
| CI-06 | Playwright CLI `test` | Browser and registered-handler integration | passed: 48/48 | EV-014 |
| CI-07 | `corepack pnpm --filter web build` | TanStack Start production build | passed | EV-013 |
| CI-08 | Orchestrator path-map review against Spec, Plan, Evaluation, status, generated route metadata and final tree | Structural implementation conformance | passed; repository rules define no executable `check:spec-implementation` command | EV-011 |

## Manual and Visual Evidence

| VM scenario details | Exact viewport/state | Reference | Artifact path | Observed result | Status |
| --- | --- | --- | --- | --- | --- |
| VM-01 account-menu interaction, keyboard, focus and outside dismissal | `1440 x 900`, authenticated protected shell; `390 x 844`, mobile shell | `h7fGzC.png`, `x9zS2.png`, `sFInu.png` | `apps/web/test-results/shifu-69-vm-01-desktop.png`; `shifu-69-vm-01-mobile.png` | Inspected: identity, disabled row, enabled exit and mobile coexistence are visible; full-page fixture retains public SSR markup above the composed shell | passed with fixture-layout limitation |
| VM-02 current-session logout isolation and protected-history denial | Two persisted sessions for one account | Spec VM-02 | EV-014 handler/browser scenarios | Cookie-selected sign-out deletes one session; remaining session stays authorized | passed |
| VM-03 pending-context exit and failure/retry | `390 x 844`, pending failure/retry state | `design/handoff.md` derived states | `apps/web/test-results/shifu-69-vm-03-retry.png` | Inspected: safe pt-BR alert and retry control visible; handler proves verification/cookie cleanup on success | passed |

## Review Findings

| ACH ID | Classification | Source | Affected evidence | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| ACH-001 | environment blocker | Baseline preflight | CI-02 to CI-06; VM-01 to VM-03 | resolved | Corepack executes the declared pnpm tooling; Docker remains unavailable for registered-handler and manual persistence evidence. |
| ACH-002 | contract/integration | Auth fixture and server-function RPC boundary | CA-01 to CA-05; VM-01; CI-06 | resolved | Fixture returns the TanStack Start RPC envelope `{ result: LayoutAccount }`; focused browser coverage passes. |
| ACH-003 | test determinism | Pending and logout browser state transitions | CA-05, CA-06; VM-01, VM-03; CI-06 | resolved | Controlled response release retains pending/error assertions; focused browser coverage passes. |
| ACH-004 | runtime/UI integration | Account-menu stacking context and public-route hydration timing | CA-01, CA-02, CA-05, CA-06; VM-01, VM-03; CI-06 | resolved | Shared header stacking, exact menu controls, and router readiness correction pass focused browser coverage. |
| ACH-005 | test determinism | SSR-visible pending route success scenario | CA-06; VM-03; CI-06 | resolved | The success path waits for completed browser load after router readiness before interaction; focused browser coverage passes. |
| ACH-006 | review finding | Pending verification persistence failure could erase retry context | CA-06, CA-07 | resolved | `pendingSignOut` now retains the signed pending cookie on persistence failure and clears it only after successful/idempotent deletion. |
| ACH-007 | environment blocker | Local integration startup and database migration state | CA-04, CA-06; CI-06; VM-02, VM-03 | resolved | Process-only `REDIS_URL` allowed FastAPI health and handler execution; the historic Alembic stamp did not block the covered Better Auth tables. No configuration or shared database mutation was performed. |
| ACH-008 | worktree scope | Unrelated `pnpm-lock.yaml` drift | CI-01 to CI-07 | accepted exclusion | The lockfile changed concurrently and remains outside the delivery scope; it is preserved unstaged for its owner. |

## Evidence Log

| EV ID | Date | Scope | Exact command/scenario | Result | Finding | Runtime notes | Acceptance mapping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EV-001 | 2026-09-24 | Pre-implementation baseline | `git status --short`; `docker compose ps`; web gates with `pnpm`; saved reference inspection | Baseline recorded; web commands blocked because `pnpm` is unavailable; Docker services absent | ACH-001 | Pre-existing untracked `uv.lock` and feature artifact directory preserved; no feature source changed | All CA; CI-01 to CI-07; VM-01 to VM-03 |
| EV-002 | 2026-09-24 | Authority and design preflight | Read Spec rev 3, Plan rev 3, Identity PRD `83001345` v1, selected Rules, `design/handoff.md`, and saved PNG references | Passed | None | PRD and local Spec agree for this slice; no external mutation | All CA; VM-01 to VM-03 |
| EV-003 | 2026-09-24 | Untouched implementation conformance | Compare required paths and current source tree before edits | Passed with required Create/Modify gaps | Pending implementation work is assigned to Wave 1 Builders | Existing pending-confirmation route/page/tests and account-menu paths are absent; route constant already exists | RF-01 to RF-07; CA-01 to CA-07 |
| EV-004 | 2026-09-24 | Integrated Web quality gates before browser correction | `corepack pnpm --filter web generate-routes`; `check:lint`; `check:architecture`; `check:types`; `test:unit`; `build` | Passed: route generation, lint, architecture, types, 26 unit files/77 tests and build | Generator emitted a circular-dependency warning; no gate failure | Generated route tree includes only the new public route; temporary validation shim is not delivery scope | All CA; CI-01 to CI-05; CI-07 |
| EV-005 | 2026-09-24 | Focused browser integration first attempt | `corepack pnpm --filter web test:integration tests/shared/app-layout.test.ts tests/routes/identity/pending-confirmation.index.test.tsx` | Blocked initially by bare `pnpm` webServer command; Corepack shim workaround allowed execution | ACH-001 resolved for local command execution; Docker-backed handler evidence remains unavailable | Browser ran with Vite and Chromium; 2 existing navigation tests passed | CI-06; CA-01 to CA-07 |
| EV-006 | 2026-09-24 | Focused browser correction discovery | Same focused browser command with 8 tests | Failed: 6 tests; authenticated account menu absent and immediate mocked responses skipped pending/error assertions | Auth fixture used raw server-function body; action mocks need controlled response release | ACH-002, ACH-003 | CA-01 to CA-06; VM-01, VM-03 |
| EV-007 | 2026-09-24 | Focused browser correction discovery after RPC/timing fix | `corepack pnpm --dir apps/web exec playwright test tests/shared/app-layout.test.ts tests/routes/identity/pending-confirmation.index.test.tsx` | Failed: account data now renders; 2 tests passed, 6 failed due header/main pointer interception, broad accessible-name matching, and pending route hydration timing | ACH-003, ACH-004 | No persistence/handler evidence; browser transport remains mocked | CA-01, CA-02, CA-05, CA-06; VM-01, VM-03 |
| EV-008 | 2026-09-24 | Isolated post-ACH-004 browser rerun | Playwright CLI `tests/shared/app-layout.test.ts` and `tests/routes/identity/pending-confirmation.index.test.tsx` | `AppLayout`: 6/6 passed; pending route: 1/2 passed, success path still missed hydrated click handler | ACH-005 | Route failure/retry path passed with held response; no real persistence evidence | CA-01, CA-02, CA-05, CA-06; VM-01, VM-03 |
| EV-009 | 2026-09-24 | Focused post-ACH-005 browser integration | Playwright CLI `tests/shared/app-layout.test.ts tests/routes/identity/pending-confirmation.index.test.tsx` | Passed: 8/8 | None | Uses mocked BFF transport; verifies desktop/mobile interaction, pending, retry, redirect, keyboard and focus states | CA-01, CA-02, CA-03, CA-05, CA-06, CA-07; CI-06 |
| EV-010 | 2026-09-24 | Full browser integration | Playwright CLI `test` | 43/48 passed; five registered Auth-handler tests returned safe 503 | ACH-007 | UI/layout/route tests pass; server-backed Auth handler is unavailable because local API cannot start | CA-01 to CA-07; CI-06 |
| EV-011 | 2026-09-24 | Integrated structural review | `git status --short`; `git diff --check`; Spec/Plan/Evaluation/path-map review; one read-only Implementation Reviewer | Passed for feature paths; no executable `check:spec-implementation` exists or was invented | ACH-006, ACH-008 | Reviewer finding ACH-006 corrected in source; lockfile preserved because it changed concurrently | All CA; CI-08 |
| EV-012 | 2026-09-24 | Time-bounded local runtime retry | FastAPI with process-only `REDIS_URL`; direct Vite startup and `/login` wait, each capped at one minute | FastAPI reached `Application startup complete`; Vite reported ready but `/login` did not respond before timeout | ACH-007 | Temporary processes were stopped; no `.env.local`, migration, database or lockfile mutation | CA-04, CA-06, CA-07; CI-06; VM-02, VM-03 |
| EV-013 | 2026-09-24 | Final web quality gates | `corepack pnpm --filter web generate-routes`; `check:lint`; `check:architecture`; `check:types`; `test:unit`; `build` | All passed; unit suite: 26 files / 77 tests | None | Route generator emitted its existing circular-dependency warning only | CI-01 to CI-05, CI-07; all CA |
| EV-014 | 2026-09-24 | Final browser and handler integration | FastAPI with process-only `REDIS_URL`; Playwright CLI `test` | Passed: 48/48 | None | Real PostgreSQL handler tests prove current-session isolation, cookie expiry and pending verification cleanup; API process was stopped afterwards | CA-01 to CA-07; CI-06; VM-02, VM-03 |
| EV-015 | 2026-09-24 | Visual inspection | Focused Playwright 8/8 with temporary screenshots at `1440x900` and `390x844` | Passed: menu desktop/mobile and pending retry state captured and inspected | None | Screenshot files are ignored validation artifacts, not delivery files; fixture SSR layout limits viewport-level comparison to rendered shell/menu surfaces | CA-01 to CA-03, CA-05, CA-06; VM-01, VM-03 |

## Execution Assignments

| Builder | Spec/Plan scope | Allowed paths | Prohibited paths | Status |
| --- | --- | --- | --- | --- |
| `identity-auth-bff-builder` | Spec rev 3; F1-T1/F1-T2 plus ACH-002 and ACH-006 corrections; RF-01, RF-04 to RF-07; CA-01, CA-04 to CA-07; RP-03, RP-10; JN-07 | Recorded Auth/BFF paths | Shell/UI widgets, routes, generated route tree, Spec, Plan, Evaluation, Rules, Architecture, Modules, Tooling, package manifests and lockfiles | completed; EV-014 supersedes the environment-limited handler evidence |
| `identity-shell-ui-builder` | Spec rev 3; F2-T1/F2-T2 plus ACH-003/ACH-004 corrections; RF-01 to RF-07; CA-01 to CA-07; RP-03, RP-10; JN-07 | Recorded Shell/UI paths | Auth/BFF provision, auth context, middleware, REST-client artifact, generated route tree, Spec, Plan, Evaluation, Rules, Architecture, Modules, Tooling, package manifests and lockfiles | completed; EV-014 and EV-015 supersede correction evidence |

## Conformance Checkpoint

| Check | Required proof | Current result |
| --- | --- | --- |
| File/widget tree | Required Create/Modify/Generate paths match Spec rev 3 | Passed in EV-011; generated route metadata and required feature paths are present |
| Boundary ownership | Changed paths remain inside the active Builder scope | Passed for feature paths in EV-011; `pnpm-lock.yaml` is an unrelated concurrent change (ACH-008) |
| Route artifacts | Affected BFF route group receives route-complete `auth.rest` with no credentials | Passed: both same-origin sign-out paths documented without cookie values |
| Contract | RF/CA, `LayoutAccount`, session isolation, pending cleanup and privacy restrictions match Spec | Passed: EV-014 verifies real handler persistence; EV-009/EV-015 verify UI and browser boundaries |
| UI states | Success, pending, error/retry, disabled, focus, keyboard and responsive states are exercised | Passed: focused 8/8 and full 48/48 browser evidence |
| Design references | Saved references and exact viewports are recorded; fresh comparisons required | EV-015 inspected the required menu/pending states; the fixture SSR layout limitation is recorded |
| Validation | Current-candidate commands, console/network, persistence and cookie results are classified | Passed: EV-013, EV-014 and EV-015 supersede stale attempts |

## Final Acceptance Matrix

| Acceptance | RF coverage | Automated evidence | Runtime/manual evidence | Visual evidence | Status |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | EV-013, EV-014 | Shared protected shell | EV-015 | passed |
| CA-02 | RF-01, RF-02 | EV-014 | Escape, outside click and focus restoration | EV-015 | passed |
| CA-03 | RF-03 | EV-014 | Disabled `Sua conta`; enabled `Sair` | EV-015 | passed |
| CA-04 | RF-04, RF-05 | EV-014 | PostgreSQL current-session isolation and cookie expiry | — | passed |
| CA-05 | RF-05, RF-06 | EV-014 | Pending, error/retry and final login navigation | EV-015 | passed |
| CA-06 | RF-07 | EV-014 | PostgreSQL verification cleanup, idempotency and no session effect | EV-015 | passed |
| CA-07 | RF-04 to RF-07 | EV-014 | Handler assertions and browser request inspection | — | passed |

## Final Conformance Record

Spec `documentation/features/identity/account-menu-logout/spec.md` revision `3`
matches the complete delivery tree: Auth/BFF provision, protected middleware,
shared shell/account-menu, public pending-confirmation route, generated route
metadata, focused integration coverage and `apps/server/rest-client/identity/auth.rest`.
`LayoutAccount` remains the only hydrated identity shape. Tokens, account IDs,
time zones and pending identifiers stay outside the browser contract.

`pnpm-lock.yaml` is an unrelated concurrent worktree change and is excluded from
this delivery; it was not staged or modified by conclusion. The temporary
`pnpm.cmd` shim and screenshot instrumentation were removed. No repository-wide
`check:spec-implementation` command exists, so CI-08 is the required local
path-map conformance review.

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| RP-03 / JN-07 | RF-01, RF-04 to RF-07 | CA-01, CA-04 to CA-07 | EV-013 to EV-015 | partially_implemented: current-device logout only | unchanged |
| RP-10 | RF-01 to RF-07 | CA-01 to CA-07 | EV-014, EV-015 | implemented for this slice | unchanged |

## Lessons Learned

No reusable rule or authority gap has been identified. The missing Evaluation
artifact is recorded as a delivery preflight correction, not a repository rule
change.
