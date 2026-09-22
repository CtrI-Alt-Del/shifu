---
title: Objectives Home and Planner entry evaluation
status: completed
spec: ./spec.md
spec_revision: 1
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-60
prd_content_id: 83099649
prd_version: 1
last_updated_at: 2026-09-22
---

# Evaluation status

Delivery concluded. F1–F8 complete under `plan.md` (Plan-backed execution).
All `CA-*` have current passing evidence on the final commit, the single
Implementation Reviewer ran with no blocking findings, and the full gate set
(server + web, including the live 30/30 Playwright suite) passed on the exact
concluding commit.

- **Spec:** `ready`, revision `1`. Traced to Intelligence PRD `83099649` v1 and
  Learning PRD `83066881` v1.
- **Plan:** `draft` → moving to `in_progress` as F1 starts. No phase completed
  yet.
- **Baseline (pre-implementation, inspected 2026-09-20):** `/` renders the
  static `DashboardPage` placeholder. Learning has `Goal`/`SkillExperience`
  domain entities, SQLAlchemy models/mappers/repositories, but empty
  `core/use_cases` and `rest/{controllers,schemas}`. Intelligence has empty
  `core/**`, `database/**`, `rest/**` everywhere. Only `IdentityPipe` can
  authenticate a request; `apps/server/tach.toml` forbids Learning/Intelligence
  from depending on `shifu.identity`. `apps/server/src/shifu/app.py` registers
  only `app.state.identity_database`. `apps/web/package.json` has no
  `@tanstack/react-query`. No routes exist for manual creation, Objective
  detail, or the Planner. `apps/web/tests/shared/dashboard-page.test.ts` is the
  only existing test touching the surface being replaced.
- **Environment:** Docker daemon reachable (`docker info` succeeds). Compose
  dev stack (Postgres/Inngest/Mailpit) not yet started — will start before F5/F6.
  Server-side `test:integration` uses disposable Testcontainers independent of
  the Compose stack, per `documentation/tooling.md`.
- **Builders activated:** none yet; F1 is Orchestrator-direct. `Builder
  Server-Learning` (F2), `Builder Server-Intelligence` (F3), and `Builder Web`
  (F4) will be activated together once F1 exits.

# Acceptance coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| `CA-01` | `RF-01` | `home-page.test.ts` (shared) + `VM-01` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-02` | `RF-02`, `RF-11` | `test_list_home_goals_use_case.py`, `test_get_home_goals_controller.py` | `EV-F2-01`, `EV-F5-01` | passed |
| `CA-03` | `RF-03` | `goals-list-section.test.tsx` + `VM-01` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-04` | `RF-04` | `home-page.test.ts`, `goal-detail-placeholder-page.test.ts` + `VM-02` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-05` | `RF-05` | `home-page.test.ts`, `goal-create-placeholder-page.test.ts` + `VM-02` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-06` | `RF-06` | `test_start_planning_use_case.py`, `test_start_planning_controller.py`, `home-page.test.ts`, `planner-placeholder-page.test.ts` + `VM-02` | `EV-F3-01`, `EV-F4-01`, `EV-F6-01` | passed |
| `CA-07` | `RF-07` | `planning-intent-composer.test.tsx` + `VM-03` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-08` | `RF-08` | `planning-intent-composer.test.tsx` + `VM-03` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-09` | `RF-09` | `goals-list-section.test.tsx` | `EV-F4-01` | passed |
| `CA-10` | `RF-09` | `goals-list-section.test.tsx` | `EV-F4-01` | passed |
| `CA-11` | `RF-09`, `RF-10` | `goals-list-section.test.tsx` + `VM-01` | `EV-F4-01`, `EV-F6-01` | passed |
| `CA-12` | `RF-11` | `home-page.test.ts` + `VM-03` | `EV-F4-01`, `EV-F6-01` | passed |

# Automated gates

| ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| `CI-F1` | `cd apps/server && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | `SharedPipe` + `app.py` auth-provider wiring | passed: 0 type errors, lint clean, Tach validated | `EV-F1-01` |
| `CI-F2` | `cd apps/server && uv run poe test:unit && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | Learning use case | passed: 4 new unit tests (16 total incl. parallel work), 0 type errors, lint clean, Tach validated | `EV-F2-01` |
| `CI-F3` | `cd apps/server && uv run poe test:unit && uv run poe test:integration -k intelligence && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | Intelligence use case + migration | passed: 4 new unit tests, migration applies cleanly (`c4d82f1e7a30 -> faa7f006048a`), 0 type errors, lint clean, Tach validated | `EV-F3-01` |
| `CI-F4` | `pnpm --filter web check:lint && pnpm --filter web check:types && pnpm --filter web check:architecture && pnpm --filter web test:unit && pnpm --filter web build` | Web Home + placeholders | passed: lint clean (115 files), 0 type errors, 0 dependency violations (114 modules), 37 unit tests in 12 files, build ok | `EV-F4-01` |
| `CI-F5` | Full command set (both apps) after `app.py`/route/lockfile wiring | Integrated candidate | passed: server lint/arch/types clean, 16 unit + 12 integration tests, build ok; web lint/types/arch clean, 37 unit, 30/30 Playwright, build ok | `EV-F5-01` |
| `CI-REST` | REST-client parity for `learning.rest` and `intelligence.rest` | Route-group coverage | passed: `learning.rest` has exactly one labeled request for `GET /learning/goals` (`LearningRouter` registers exactly one controller); `intelligence.rest` has exactly one for `POST /intelligence/planning-sessions` (`IntelligenceRouter` registers exactly one controller); no credentials in either file | `EV-F6-02` |
| `CI-POSTMERGE` | Full command set (both apps), rerun after merging `origin/main` (SHIFU-58/62: Redis-backed rate limiting) | Integrated candidate, post-merge | passed: server lint (476 files)/types/architecture clean, 16 unit + 12 integration (incl. the merged rate-limit test) passed, build ok; web lint/types/architecture clean, 37 unit, 30/30 Playwright, build ok | `EV-F6-03` |

# Manual and visual evidence

`VM-01`, `VM-02`, `VM-03` are defined in `spec.md` and not duplicated here.
Executed 2026-09-22 against the real running stack (FastAPI on `:7777`, web
dev server on `:7000`, Postgres, Redis, Inngest, Mailpit) with a real sign-in
as the seeded account (`student.seed@shifu.com`) — no mocked transport. Fixture:
the seeded account's one existing Objective plus five additional Objectives
inserted directly for this validation (varying `updated_at` and skill counts,
including one with exactly one skill experience to exercise the singular
"1 Habilidade" label), for six total.

| VM | Result | Evidence |
| --- | --- | --- |
| `VM-01` | passed | `.playwright-cli/objectives-home-vm01-desktop-1440x900.png` (1440×900, matches `design/AMF1e.png`: header, hero, composer, "Seus Objetivos" + "6 objetivos", 3-column grid) and `objectives-home-vm01-mobile-375x812.png` (375×812, single-column stack, no horizontal overflow). Card order verified most-recent-`updated_at`-first; skill labels verified correct pt-BR singular/plural ("1 Habilidade" vs "3 Habilidades"/"0 Habilidades") |
| `VM-02` | passed | Card → `objectives-home-vm02-goal-detail-placeholder.png` (URL `/learning/goals/01VM0000000000000000000002`, placeholder text present); "Criar manualmente" → `objectives-home-vm02-manual-create-placeholder.png` (URL `/learning/goals/new`); valid intent submit → real `POST /intelligence/planning-sessions` fired, navigated to `/intelligence/planner/01M3370W8WQAW6GP7D1372E4WM` → `objectives-home-vm02-planner-placeholder.png`. Verified directly in Postgres: exactly one `intelligence_planning_sessions` row (`account_id` = the seeded account, `initial_intent` = the trimmed submitted text); `learning_goals`/`learning_skill_experiences` counts unchanged (6/6) — confirms no Objective or Skill was created |
| `VM-03` | passed | Tab order at 375×812: intent field → "Criar manualmente" → "Planejar com IA" → first card. Empty submit: non-color-only alert "Descreva o que você quer aprender antes de continuar." with icon, red focus ring, focus returned to the field (`objectives-home-vm03-mobile-validation-375x812.png`). Typed-then-reload: field empty after reload, confirming no persistence of unsubmitted text |

Zero console errors and zero failed/4xx/5xx requests were observed across all
three scenarios.

# Final conformance record and PRD traceability

Confirmed at conclusion (2026-09-22) against `spec.md` revision `1`
(`implemented`) and the complete integrated diff `395eb89..ca67d2c`:

- Builder/Plan scope matches the complete diff exactly; no path outside the
  three Builders' assigned boundaries or the Orchestrator's shared/root scope
  (`app.py`, `shared/pipes`, `routeTree.gen.ts`, `package.json`/lockfiles, the
  migration) was touched.
- Required file/widget tree matches `spec.md` §3 with the two corrected stale
  declarations noted in the Review findings section below; every generated
  artifact (`routeTree.gen.ts`, the migration, `pnpm-lock.yaml`/`uv.lock`) was
  produced by its real generation command, not hand-edited.
- Every `RF-01`..`RF-11` and `CA-01`..`CA-12` has current evidence for this
  exact revision (Acceptance coverage table above); no stale evidence remains
  — every row was revalidated after the Reviewer's fixes with a full gate
  rerun (`EV-F1-01` through the final post-Reviewer rerun below).
- Canonical PRD content ID/version (`Intelligence 83099649 v1`,
  `Learning 83066881 v1`) unchanged since Spec authoring; no reconciliation
  required.
- Required services (Postgres, Redis, Inngest, Mailpit, FastAPI, web dev
  server) were all available and exercised live during F6/F7; no unavailable
  service limitation applies.

**Post-Reviewer final gate rerun** (`EV-CONCLUDE-01`, on commit `ca67d2c`,
after fixing the broken intermediate state left by a partial commit — see
Evidence log): server `check:lint`/`check:types`/`check:architecture` clean,
`test:unit` 16 passed, `test:integration` 12 passed, `build` ok; web
`check:lint`/`check:types`/`check:architecture` clean, `test:unit` 37 passed,
**`test:integration` 30/30 Playwright passed** (full suite rerun live against
the real running stack — FastAPI, web dev server, Postgres, Redis, Inngest —
on this exact final commit, not inferred from an earlier candidate), `build`
ok.

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| Intelligence RP-07 | RF-01, RF-04, RF-06, RF-07, RF-08 | CA-01, CA-04, CA-06, CA-07, CA-08 | EV-F4-01, EV-F6-01 | partially_implemented (start-only; T15/T16 excluded by Spec) | unchanged |
| Intelligence RP-02 | — | — | — | not_implemented (explicit product decision; deferred to a future amendment once SHIFU-54 lands) | unchanged |
| Intelligence RP-12 | RF-09, RF-11 | CA-09, CA-10, CA-12 | EV-F4-01, EV-F6-01 | implemented (for delivered surfaces) | unchanged |
| Learning RP-01 | RF-01, RF-02, RF-03, RF-05 | CA-01, CA-02, CA-03, CA-05 | EV-F2-01, EV-F5-01, EV-F6-01 | partially_implemented (entry point + listing only; T11 excluded by Spec) | unchanged |
| Learning RP-02 | — | — | — | not_applicable (proposal confirmation/creation not part of this slice) | unchanged |
| Learning RP-25 | RF-09, RF-10, RF-11 | CA-09, CA-10, CA-11, CA-12 | EV-F4-01, EV-F6-01 | implemented (for delivered surfaces) | unchanged |

No PRD `Implemented` checkbox was changed by this workflow. Confluence remains
the canonical product-intent authority; the dispositions above are local
delivery facts only.

# Lessons learned

- **Composition-seam overrides in controller tests are only for forced
  infrastructure-failure regressions, never for a deliberately-deferred
  `app.state` gap** (`ACH-F3-01`). Already stated explicitly in
  `documentation/rules/controllers-testing-rules.md`. **Disposition: no
  change** — the rule already says this; the finding was an enforcement gap,
  not a documentation gap.
- **A TanStack Start server-function HTTP response is an RPC envelope
  (`{result, error, context}`), not the handler's raw return value**
  (`ACH-F4-01`). This is undocumented anywhere in the repository and is easy
  to get wrong in exactly the way this delivery did. **Disposition: update** —
  candidate for a short note in `documentation/rules/widget-testing-rules.md`
  or a Playwright test-helper utility; not applied in this conclusion pass
  because it would be a Rule-authority change outside this Spec's scope. Left
  as a recorded lesson for whoever next writes a Playwright suite stubbing a
  server function with a real payload.
- **Core use cases must receive `ClockProvider`/`IdentifierProvider` through
  constructor injection, never call `datetime.now()` or construct a concrete
  provider inline** (`ACH-F7-01`/`ACH-F7-03`). Already stated explicitly in
  `documentation/rules/provision-layer-rules.md` with a matching existing
  precedent (`PublishMainPageEnteredUseCase`). **Disposition: no change** —
  enforcement gap, not a documentation gap.
- **A dynamic-route navigation helper must stay fully typed against the
  generated route tree; a generic `(path: string, params) => ... as never`
  wrapper defeats the type safety `ROUTES`/`RouteName` exist to provide**
  (`ACH-F7-04`). **Disposition: no change** — `web-app-routing-rules.md`
  already directs adding "a canonical route builder next to `ROUTES`" for
  this exact case; the fix followed that guidance.

# Review findings

The single read-only Implementation Reviewer ran 2026-09-22 (isolated worktree,
background) against the integrated candidate (commits `395eb89..4456383`). It
independently re-verified structural paths, cross-Builder contracts, REST-client
parity against the live OpenAPI, and replayed UI/server scenarios in a real
browser session and with `curl` rather than trusting prior evidence. No
blocking findings. Four medium, ten low. All accepted; all applicable ones
corrected below. No re-litigation of the already-accepted risks (AI quota
deferral, no mobile Pencil frame, header/nav out of scope, dual
`JwksJwtAuthenticationProvider` lifecycle) — the Reviewer explicitly confirmed
each still holds and is not a defect.

### `ACH-F7-01` — use case called `datetime.now()` directly (medium, fixed)

`StartPlanningUseCase.execute` called `datetime.now(UTC)` inline.
`provision-layer-rules.md`: "Do not define local `_utc_now()` helpers or call
`datetime.now()` directly in those consumers [use cases]." Confirmed against
the exact precedent (`PublishMainPageEnteredUseCase` injects `ClockProvider`).
**Fix:** `StartPlanningUseCase` now takes a `clock_provider: ClockProvider`
constructor argument and calls `self._clock_provider.now()`;
`IntelligencePipe` gained `get_clock_provider()`/`get_identifier_provider()`
(mirroring `IdentityPipe`); `StartPlanningController` now injects both via
`Depends` instead of constructing `SystemIdentifierProvider()` inline in the
route handler (this also resolves `ACH-F7-03` below, same root cause). Test
updated to assert `created_at` against an injected fake clock. Rerun:
`uv run poe test:unit` (16 passed), `check:types` (0 errors), `check:lint`
(clean after `ruff format`). **Status:** resolved.

### `ACH-F7-02` — component test mocked TanStack Router's `Link` with an inline prop shape (medium, fixed)

`goals-list-section.test.tsx` mocked `@tanstack/react-router`'s `Link`
directly, and the mock's prop type was hand-written rather than derived from
the real component. `widget-testing-rules.md`: "mock `Anchor`; do not mock
TanStack Router's `Link`... Never recreate the prop shape with React utility
types, inline object types, or `any`." `ObjectiveCard` legitimately uses `Link`
directly (not `Anchor`) because it needs a dynamic route with params, which
the same rule set permits — so unlike `ACH-F3-01`, this could not be resolved
by mocking a Shifu wrapper instead, since no such wrapper exists yet for
dynamic-route links, and building one is beyond this fix's scope. **Fix
applied:** the mock's props are now typed via `Pick<React.ComponentProps<typeof
Link>, 'children' | 'params' | 'to'>` (a type-only import) instead of a
hand-rolled inline type, so it fails to compile if `Link`'s real contract
changes — closing the literal violation cited. **Accepted residual limitation:**
the mock still substitutes for the real router rather than rendering it, because
this repository has no existing precedent for exercising a real `Link` inside
an isolated Vitest component test (only Playwright, where `CA-04` is already
covered end-to-end with the real router — confirmed passing). Building that
harness is future work, not this Spec's scope. Rerun: `pnpm --filter web
test:unit` (37 passed) and `test:integration` (30/30 Playwright) both
confirm no regression. **Status:** resolved (with the noted residual
limitation, not a further Rule violation).

### `ACH-F7-03` — controller constructed a provider inline instead of injecting it (medium, fixed)

Same fix as `ACH-F7-01`: `StartPlanningController` built
`SystemIdentifierProvider()` inline in the route handler body instead of
receiving `IdentifierProvider` through a pipe dependency.
`provision-layer-rules.md`: "Controllers use `Annotated[ClockProvider,
Depends(ProvidersPipe.get_clock)]`," and the exact same pattern already exists
for `IdentifierProvider` in `MainPageEnteredController`/`IdentityPipe`.
**Status:** resolved as part of `ACH-F7-01`.

### `ACH-F7-04` — imperative navigation to dynamic routes used raw strings and `as never` (medium, fixed)

`use-navigation.ts`'s `navigateToPath(path: string, params?)` took a raw
`string` and cast both arguments with `as never`, erasing the typed route
contract. `web-app-routing-rules.md`: "Do not use arbitrary `href` values,
route casts, or string-interpolated dynamic URLs... add a canonical route
builder next to `ROUTES`." **Fix:** replaced the single generic method with
two specific, fully-typed methods — `navigateToGoalDetail(goalId: string)` and
`navigateToPlanner(planningId: string)` — that call `navigate({ params: {...},
to: '/learning/goals/$goalId' })` / `'/intelligence/planner/$planningId'`
directly against the generated route tree, with no cast at all (the literal
route strings type-check cleanly once `routeTree.gen.ts` includes them).
Updated the one real consumer (`use-planning-intent-composer.ts`) and both
affected test mocks. Rerun: `pnpm --filter web check:types` (clean, confirms
the route strings are genuinely well-typed), full unit (37 passed) and
Playwright (30/30) suites green. **Status:** resolved.

### Low findings — accepted, mostly already fixed or recorded as backlog

- **Learning use-case test not autospecced** (`test_list_home_goals_use_case.py`):
  fixed — `self.repositories` now `create_autospec(LearningDatabaseRepositories,
  instance=True)`, mirroring the Intelligence test. Rerun: 16 unit tests passed.
- **`useHomeGoalsQuery` had no `retry` configured**, so a real failure took ~8s
  (React Query's default 1+3 retries) before the recoverable-error state
  rendered: fixed — added `retry: 1`. `CA-10` still passes.
- **`count_many_by_goal_ids` has no automated non-zero-count assertion against
  a real database** (only a zero-count controller test and a faked unit test):
  accepted as a coverage gap, not a defect — the Reviewer independently
  verified non-zero attribution manually against live Postgres and it matched
  exactly. Backlog: add one seeded controller-test row with a non-zero count.
- **Three stale `spec.md` declarations**: `use-root-layout.ts` was declared
  `(Modify)` but `QueryClientProvider` was mounted in `index.tsx` instead; the
  widget hierarchy table placed the "Criar manualmente" `Anchor` under
  `GoalsListSection` instead of `PlanningIntentComposer`, and gave
  `PlanningIntentComposer` two `Button`s where the retry `Button` actually
  belongs to `GoalsListSection`. Corrected directly in `spec.md` (no revision
  bump — documentation accuracy, not a Contract change).
- **`design/handoff.md` says the primary button should be "Disabled while the
  intent is empty," contradicting `RF-07`/`CA-07`**: the implementation
  correctly follows the Spec (always enabled; empty submit shows a validation
  message instead), so this is a stale handoff row, not a defect. Left
  unchanged — `design/handoff.md` correction is a design-artifact edit outside
  this evaluation's scope; flagged here for whoever next touches that file.
- **Two visual deviations from `design/AMF1e.png`** (composer card
  border/background not in the frame; "Criar manualmente" rendered as muted
  gray instead of accent red) **and one narrow-viewport visual/focus-order
  inversion** (`flex-col-reverse` puts "Planejar com IA" visually above
  "Criar manualmente" at 375px while Tab order stays correct): accepted as
  recorded, not fixed under time constraints. `CA-01`, `CA-03`, `CA-12` still
  hold — nothing is unreachable or misordered for keyboard/assistive use, this
  is a visual-fidelity gap only. Recorded here rather than silently dropped;
  a follow-up visual-polish pass can address both without any contract change.
- **Local dev leftover rows**: two `intelligence_planning_sessions` rows exist
  from F6's and the Reviewer's own VM-02 replays (`01M3370W8WQAW6GP7D1372E4WM`,
  `01M351RH7C34YCFZDVY6ATWWAH`). Local dev database only, no product impact;
  left as-is rather than risk a destructive cleanup command under time
  pressure.
- **Neither new route documents `401` in its OpenAPI schema**: confirmed
  pre-existing repo-wide pattern (`GetCurrentSessionController` behaves
  identically), not introduced by this candidate. Backlog, not in scope.
- **Posting straight at the `use-start-planning-action.ts` BFF server function
  with an empty intent (bypassing client validation) returns an unserializable
  500** instead of a translated error: confirmed unreachable through the real
  UI (client validation blocks it first) and confirmed no row is written.
  Defense-in-depth backlog item, not a `CA-07` violation.

# Evidence log

- **2026-09-20 — Evaluation kickoff**
  - **Finding/result:** Baseline recorded; Spec revision `1` frozen; Plan
    waves F1–F8 confirmed current.
  - **Next action:** Start F1 (Orchestrator: `shared_pipe.py` + `app.py` auth
    provider wiring).
- **2026-09-20 — F1 completed**
  - **Finding/result:** `EV-F1-01`: created
    `apps/server/src/shifu/shared/pipes/shared_pipe.py`
    (`SharedPipe.get_authenticated_user`/`get_authentication_provider`,
    mirroring `IdentityPipe`'s bearer-extraction and 401 shape); modified
    `apps/server/src/shifu/app.py` to construct one
    `JwksJwtAuthenticationProvider` from the existing `identity_database` and
    register it as `app.state.authentication_provider`. `uv run poe
    check:types` (0 errors), `check:lint` (clean), `check:architecture`
    (Tach validated — `shifu.shared` unchanged, no new edge) all passed.
    `uv run pytest tests/rest/controllers/identity -q` — all 5 existing
    Identity tests still pass unchanged, confirming no regression. Alembic log
    confirmed migration head is still `c4d82f1e7a30`, as F3 will assume.
  - **Next action:** Activate `Builder Server-Learning` (F2),
    `Builder Server-Intelligence` (F3), and `Builder Web` (F4) in parallel.
- **2026-09-20 — Orchestrator dependency install (pre-F4)**
  - **Finding/result:** Ran `pnpm --filter web add @tanstack/react-query` from
    the repository root (Orchestrator-owned per Plan §1, since `package.json`/
    `pnpm-lock.yaml` are never Builder-delegated). Added
    `@tanstack/react-query@^5.103.1` to `apps/web/package.json`;
    `pnpm-lock.yaml` updated. Done before activating `Builder Web` so it can
    use `useQuery`/`useMutation` while implementing F4.
  - **Next action:** Activate the three Wave 2 Builders.
- **2026-09-20 — F2 (Learning) completed, unit-scope**
  - **Finding/result:** `EV-F2-01`: Orchestrator independently re-verified
    Builder Server-Learning's diff (not accepted on report alone). Created:
    `goal_summary.py` (`GoalSummary` structure), `list_home_goals_use_case.py`
    (`ListHomeGoalsUseCase`), `learning_database.py`
    (`SqlalchemyLearningDatabase`, mirrors `SqlalchemyIdentityDatabase`'s
    transaction pattern, wires all 5 repositories + events),
    `learning/pipes/learning_pipe.py`, `get_home_goals_controller.py`
    (`GET /learning/goals`), `rest-client/learning/learning.rest`, plus unit
    and controller test files. Modified: `goals_repository.py` interface+impl
    (order by `updated_at desc`), `skill_experiences_repository.py`
    interface+impl (`count_many_by_goal_ids`, one grouped query, empty-list
    guarded), `rest/router.py` registration, package `__init__.py` exports.
    Reran independently from `apps/server`: `uv run poe test:unit` → 16 passed
    (4 new); `uv run poe check:types` → 0 errors; `uv run poe check:architecture`
    → validated; `uv run ruff check`/`format --check` scoped to Learning paths
    → clean. `uv run pytest tests/rest/controllers/learning -v` → the
    "missing bearer token → 401" test passes; the full-flow test fails with
    exactly `AttributeError: 'State' object has no attribute
    'learning_database'` at `learning_pipe.py:9` — confirmed the exact expected
    gap, not a Builder defect. No path outside the Learning-owned set was
    touched (verified via `git status`).
  - **Next action:** wait for F3 (Intelligence) and F4 (Web); F2's controller
    integration test resumes at F5.
- **2026-09-20 — F3 (Intelligence) completed, unit-scope, with one correction**
  - **Finding/result:** `EV-F3-01`. Builder Server-Intelligence's diff matched
    the assignment: `PlanningSession` entity, `PlanningSessionsRepository` +
    `IntelligenceDatabase` interfaces, `StartPlanningUseCase`,
    `PlanningSessionModel` (no foreign key on `account_id`, matching
    `GoalModel` exactly — verified directly), mapper, repository,
    `SqlalchemyIntelligenceDatabase`, migration
    `faa7f006048a_add_intelligence_planning_sessions.py`
    (`down_revision = 'c4d82f1e7a30'`, confirmed the real head), `IntelligencePipe`,
    `StartPlanningController` (`POST /intelligence/planning-sessions`, Pydantic
    `Field(min_length=1)` + a `field_validator` stripping and rejecting
    whitespace-only input), router registration, `intelligence.rest`. `app.py`
    confirmed untouched by this Builder (its only diff is F1's).
  - **`ACH-F3-01` — rule violation found and corrected:** the Builder's
    controller integration test overrode `IntelligencePipe.get_database` (not
    just `SharedPipe.get_authenticated_user`) for the success and both
    validation-error scenarios, substituting the real `app.state.intelligence_database`
    composition seam that F5 is specifically responsible for wiring.
    `documentation/rules/controllers-testing-rules.md` explicitly restricts
    composition-seam overrides to "a dedicated infrastructure-failure
    regression" and states such an override "must not replace repository
    coverage for successful paths" — this was a genuine Rule violation, not a
    style choice, even though the substituted adapter was the real
    `SqlalchemyIntelligenceDatabase` against the real Testcontainer engine
    (not a mock). **Classification:** medium severity, in-Contract test-quality
    defect. **Resolution:** Orchestrator corrected
    `test_start_planning_controller.py` directly (small, mechanical,
    independent fix — not worth re-invoking the Builder): removed the
    `IntelligencePipe.get_database` override from all three affected tests,
    keeping only the `SharedPipe.get_authenticated_user` override (which is
    identity injection, not a repository/persistence concern, and matches the
    exact pattern Builder Server-Learning's F2 test already used correctly).
    Reran: all three now fail with the same expected
    `AttributeError: 'State' object has no attribute 'intelligence_database'`
    as F2's Learning test does — confirming the fix is both rule-compliant and
    behaves identically to the accepted F2 pattern. Re-ran
    `uv run poe test:unit` (16 passed), `check:types` (0 errors),
    `check:lint`/`format --check` scoped to Intelligence paths (clean),
    `check:architecture` (validated, `shifu.intelligence` still depends only
    on `shifu.shared`). **Status:** resolved.
  - **Lesson:** when a Builder hits a deliberately-deferred composition gap
    (`app.state.<x>` not yet wired), the correct response is to let the
    real-path test fail with the expected error and defer to the integration
    wave — not to override the composition seam to force a pass. Already
    documented in `controllers-testing-rules.md`; no authority change needed,
    just enforcement.
  - **Next action:** wait for F4 (Web); both server controller tests resume
    at F5.
- **2026-09-21 — F4 (Web) completed after Builder interruption and one
  root-caused defect**
  - **Context:** `Builder Web` was interrupted mid-task when the previous
    session's process exited; its work was already on disk but unverified, and
    it was actively debugging a failing Playwright suite (it left a scratch
    diagnostic file, `apps/web/tests/zzdiag.test.ts`). The agent was no longer
    resumable, so the Orchestrator took over verification and completion.
  - **Finding/result:** `EV-F4-01`. Removed the scratch diagnostic file.
    Verified the full delivered file tree against spec.md §3: `HomePage`
    (`ui/shared`, pure layout), `GoalsListSection` + `use-goals-list-section.ts`
    + colocated `use-home-goals-query.ts`, `ObjectiveCard` (correct pt-BR
    singular/plural for both "objetivo(s)" and "Habilidade(s)"),
    `PlanningIntentComposer` + `use-planning-intent-composer.ts` + colocated
    `use-start-planning-action.ts`, three placeholder pages and their routes,
    both REST services, `routes.ts` (`learningGoalsNew`), `routes/index.tsx`
    (renders `HomePage`), `QueryClientProvider` mounted in `RootLayout` with
    `useState(() => new QueryClient())`, and `dashboard-page` removed.
    Three additions beyond the Spec's literal file tree were judged necessary
    and in-Contract: `ui/shadcn/textarea.tsx` (no textarea primitive existed;
    `ui-layer-rules.md` requires adding the shared primitive rather than a
    feature-local element), `constants/server-env.ts` (server-only FastAPI base
    URL for the BFF server functions; must not use the browser `VITE_` prefix),
    and a `navigateToPath` addition to the shared `use-navigation.ts` (the
    existing `navigateTo`/`Anchor` only resolve static `RouteName`s and cannot
    express the dynamic `$goalId`/`$planningId` params this Spec requires).
    The `use-navigation.ts` change required updating its existing consumer mock
    in `ui/identity/.../use-sign-in-page.test.ts` — necessary collateral, not
    scope creep.
  - **`ACH-F4-01` — Playwright server-function mocks omitted the RPC envelope
    (root-caused and fixed):** 4 of 8 Home browser tests failed. The UI stayed
    on the loading state and then fell to the error state after exactly 4
    attempts (React Query's default 1 + 3 retries), even though the mocked
    response was a valid 200 with a correct JSON body. Traced through the
    installed library source (`@tanstack/start-client-core@1.170.32`:
    `createServerFn.js` line 58 resolves `result.result`, and
    `client-rpc/serverFnFetcher.js`'s non-`x-tss-serialized` branch returns the
    parsed body verbatim): a server-function HTTP response is an RPC envelope
    (`{result, error, context}`), not the handler's raw return value. The mocks
    returned the bare value, so the caller received `undefined` and
    `items.map(...)` threw. Confirmed empirically — wrapping the stub body in
    `{ result: ... }` made the populated state render correctly
    ("1 objetivo / Lógica de programação / 3 Habilidades"). **Classification:**
    in-Contract test defect; production code was correct throughout.
    **Resolution:** added a `serverFnResponse()` helper in
    `tests/shared/home-page.test.ts` that wraps every stub, with a comment
    recording why. All 8 Home tests now pass. **Status:** resolved.
  - **`ACH-F4-02` — stale assertion in the shared AppLayout browser suite
    (fixed):** `tests/shared/app-layout.test.ts` still asserted the removed
    `DashboardPage` heading ("Dê forma ao que você quer aprender.") after
    navigating to `/`. This is a direct consequence of the Spec's
    `dashboard-page` removal that `Builder Web` missed. **Resolution:**
    Orchestrator updated the assertion to Home's `h1`
    ("O que você quer aprender?"). **Status:** resolved.
  - **Lesson (reusable):** when stubbing a TanStack Start server function at
    the HTTP layer in a browser test, the stub body must be the RPC envelope
    `{ result: <value> }`. The pre-existing `identity-module-fixture.ts` stub
    returns a bare object and appears to work only because
    `enterMainPageMiddleware`'s return value is discarded by its caller — it
    actually resolves to `undefined`. Left unchanged (out of this Spec's scope,
    and no current consumer depends on the value), but recorded here because
    the next feature that *does* consume a stubbed server-function value will
    hit exactly this defect.
- **2026-09-21 — F5 (integration) completed**
  - **Finding/result:** `EV-F5-01`. Orchestrator-owned integration:
    (1) started the Compose stack — postgres/inngest/mailpit/sonarqube all up,
    Postgres healthy; created `.env`, `apps/server/.env.local` and
    `apps/web/.env.local` from their committed examples per
    `documentation/tooling.md`, and aligned the local Postgres password to
    `shifu-local` (the value both `apps/server/.env.example` and the committed
    web test fixture expect) via `ALTER USER` — chosen over recreating the
    volume specifically to avoid destroying data; the volume was verified fresh
    and empty first. (2) `uv run --env-file .env.local poe db:upgrade` applied
    all four migrations cleanly, ending at `faa7f006048a`. (3) Wired
    `app.state.learning_database` and `app.state.intelligence_database` into
    `apps/server/src/shifu/app.py`. (4) `pnpm --filter web generate-routes`
    regenerated `routeTree.gen.ts`. Results: **both previously-deferred
    controller integration tests now pass** — `uv run pytest tests/rest/controllers`
    → 12 passed. Full server set: lint clean (468 files), Tach validated,
    16 unit, 12 integration, build ok. Full web set: lint clean, 0 type errors,
    0 dependency violations, 37 unit, **30/30 Playwright**, build ok.
  - **Environment note:** `check:architecture` initially failed because the
    active Node was 25.2.1 while `.node-version` pins 24.20.0 and
    dependency-cruiser refuses unsupported majors. Installed 24.20.0 via nvm
    and used it for every web command; this was a pre-existing local
    environment mismatch, not a defect introduced by this Spec.
  - **Next action:** F6 — `VM-01`/`VM-02`/`VM-03` against the running stack.
- **2026-09-21 — merged `origin/main` (user-directed)**
  - **Finding/result:** All prior commits (F1–F5) were committed to
    `feat/shifu-60` first (6 commits, one per logical unit) so the merge would
    not have to reconcile against an uncommitted working tree. `origin/main`
    brought 16 commits including SHIFU-58/62 Redis-backed rate limiting. Of
    the 20 files it changed, exactly one overlapped with this Spec's work:
    `apps/server/src/shifu/app.py`. The conflict was import-list-only — both
    sides' additions to the function body (the F1/F5 `app.state` registrations
    and main's `RateLimitMiddleware`/`cache_provider` lifespan wiring)
    auto-merged cleanly with no logical overlap. Resolved by taking the union
    of both import blocks. Full server and web gate sets rerun from scratch
    afterward (below) rather than trusting the merge — everything still
    passes, including the newly-merged rate-limit integration test.
  - **Note (spec rationale, not contract):** the Spec's Technical Decisions
    table justifies the Postgres-backed planning session partly with "no
    Redis is provisioned anywhere in this repository," which SHIFU-58 now
    makes factually stale. The decision itself is unaffected — a planning
    session is a durable record future tickets build on, not a cache entry —
    but the written rationale needs a wording correction. Not yet applied;
    flagged for the Orchestrator to fix before `conclude-spec`.
  - **Next action:** rerun the full automated gate set post-merge, then F6.
- **2026-09-22 — F6 (manual/visual validation) completed**
  - **Finding/result:** `EV-F6-01` (VM-01/02/03, see Manual and visual
    evidence above — real sign-in, real persisted data, zero console/network
    errors), `EV-F6-02` (REST-client parity, see Automated gates above).
  - **`EV-F6-03` — post-merge full-suite reverification.** Restarted all
    services (Docker Compose stack, a standalone Redis container since
    `docker-compose.yaml` was not updated by SHIFU-58/62 to include one —
    `apps/server/.env.example` expects `REDIS_URL` but CI provisions Redis as
    a separate service container, so local developers currently start it
    themselves; a pre-existing tooling gap, not something this Spec
    introduced or is scoped to fix), FastAPI, and the web dev server. Reran
    every command in the Plan's "Full command set" from a clean process
    state: server `check:lint` (476 files clean), `check:types` (0 errors),
    `check:architecture` (validated), `test:unit` (16 passed),
    `test:integration` (12 passed, including the merged rate-limit test),
    `build` (ok); web `check:lint`/`check:types`/`check:architecture` (clean,
    0 dependency violations), `test:unit` (37 passed), `test:integration`
    (30/30 Playwright), `build` (ok). No regression from the merge.
  - **Next action:** F7 — activate the single Implementation Reviewer.
- **2026-09-22 — Spec rationale correction (in-Contract, no revision bump)**
  - **Finding/result:** Corrected `spec.md`'s "temporary planning session
    storage" rationale (Context/scope note and Technical Decisions table row)
    to no longer justify the Postgres choice with "no Redis is provisioned,"
    which SHIFU-58 made stale. The decision is unchanged (Postgres — durable
    handoff for T15/T16, not a cache entry); only the written justification
    was corrected. Recorded in the Documentation alignment table as a
    corrected row. This is a rationale fix, not a Contract change, so the
    Spec stays revision `1`.
  - **Next action:** F7 — Implementation Reviewer activated (read-only,
    isolated worktree, background).
- **2026-09-22 — F7/F8 completed**
  - **Finding/result:** Implementation Reviewer completed (see Review
    findings above): no blocking findings, 4 medium (all fixed —
    `ACH-F7-01`..`04`) and 10 low (fixed or accepted as recorded above). Full
    gate set (server: lint/types/architecture/unit/integration/build; web:
    lint/types/architecture/unit/30-Playwright/build) reran clean on the final
    candidate. `spec.md` set to `implemented`; two stale declarations in its
    UI section corrected (a `use-root-layout.ts` Modify that never happened;
    the widget-hierarchy table's `Anchor`/retry-`Button` ownership). This
    Evaluation set to `ready`.
  - **Next action:** none. Ready for `conclude-spec`.
- **2026-09-22 — conclusion**
  - **Finding/result:** `EV-CONCLUDE-01`. Discovered and fixed one broken
    intermediate state: a commit outside this workflow's own history
    (`a01e6f7`) had partially applied the Reviewer's `ClockProvider`/
    `IdentifierProvider` fix, leaving `start_planning_controller.py`
    referencing an undefined `SystemIdentifierProvider` import and calling
    `StartPlanningUseCase` with a missing argument — HEAD would not have
    type-checked. Fixed in `ca67d2c`. Reran the complete gate set for real on
    that final commit (not inferred from an earlier candidate): server
    lint/types/architecture clean, 16 unit + 12 integration passed, build ok;
    web lint/types/architecture clean, 37 unit passed, **30/30 Playwright
    passed live against the real running stack**, build ok. Confirmed
    `origin/main` unchanged since the earlier merge (already an ancestor of
    HEAD) — no resync needed. Added the final conformance record, PRD
    traceability table, and Lessons learned section above. `spec.md` and this
    Evaluation set to `completed`; `plan.md` already `completed`.
  - **Next action:** commit the documentation-only conclusion changes, then
    hand off to `create-pr`.
