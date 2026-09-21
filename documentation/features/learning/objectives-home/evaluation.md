---
title: Objectives Home and Planner entry evaluation
status: in_progress
spec: ./spec.md
spec_revision: 1
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-60
prd_content_id: 83099649
prd_version: 1
last_updated_at: 2026-09-20
---

# Evaluation status

Implementation kickoff for `spec.md` revision `1` (`ready`) under `plan.md`
(Plan-backed execution, waves F1–F8).

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
| `CA-01` | `RF-01` | `home-page.test.ts` (shared) + `VM-01` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-02` | `RF-02`, `RF-11` | `test_list_home_goals_use_case.py`, `test_get_home_goals_controller.py` | `EV-F2-01`, `EV-F5-01` | pending |
| `CA-03` | `RF-03` | `goals-list-section.test.tsx` + `VM-01` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-04` | `RF-04` | `home-page.test.ts`, `goal-detail-placeholder-page.test.ts` + `VM-02` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-05` | `RF-05` | `home-page.test.ts`, `goal-create-placeholder-page.test.ts` + `VM-02` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-06` | `RF-06` | `test_start_planning_use_case.py`, `test_start_planning_controller.py`, `home-page.test.ts`, `planner-placeholder-page.test.ts` + `VM-02` | `EV-F3-01`, `EV-F4-01`, `EV-F6-01` | pending |
| `CA-07` | `RF-07` | `planning-intent-composer.test.tsx` + `VM-03` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-08` | `RF-08` | `planning-intent-composer.test.tsx` + `VM-03` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-09` | `RF-09` | `goals-list-section.test.tsx` | `EV-F4-01` | pending |
| `CA-10` | `RF-09` | `goals-list-section.test.tsx` | `EV-F4-01` | pending |
| `CA-11` | `RF-09`, `RF-10` | `goals-list-section.test.tsx` + `VM-01` | `EV-F4-01`, `EV-F6-01` | pending |
| `CA-12` | `RF-11` | `home-page.test.ts` + `VM-03` | `EV-F4-01`, `EV-F6-01` | pending |

# Automated gates

| ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| `CI-F1` | `cd apps/server && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | `SharedPipe` + `app.py` auth-provider wiring | passed: 0 type errors, lint clean, Tach validated | `EV-F1-01` |
| `CI-F2` | `cd apps/server && uv run poe test:unit && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | Learning use case | passed: 4 new unit tests (16 total incl. parallel work), 0 type errors, lint clean, Tach validated | `EV-F2-01` |
| `CI-F3` | `cd apps/server && uv run poe test:unit && uv run poe test:integration -k intelligence && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture` | Intelligence use case + migration | passed: 4 new unit tests, migration applies cleanly (`c4d82f1e7a30 -> faa7f006048a`), 0 type errors, lint clean, Tach validated | `EV-F3-01` |
| `CI-F4` | `pnpm --filter web check:lint && pnpm --filter web check:types && pnpm --filter web check:architecture && pnpm --filter web test:unit && pnpm --filter web build` | Web Home + placeholders | passed: lint clean (115 files), 0 type errors, 0 dependency violations (114 modules), 37 unit tests in 12 files, build ok | `EV-F4-01` |
| `CI-F5` | Full command set (both apps) after `app.py`/route/lockfile wiring | Integrated candidate | passed: server lint/arch/types clean, 16 unit + 12 integration tests, build ok; web lint/types/arch clean, 37 unit, 30/30 Playwright, build ok | `EV-F5-01` |
| `CI-REST` | REST-client parity for `learning.rest` and `intelligence.rest` | Route-group coverage | pending (F6) | — |

# Manual and visual evidence

`VM-01`, `VM-02`, `VM-03` are defined in `spec.md` and not duplicated here.
Scheduled for F6, after F5's integration passes.

# Review findings

None yet. The single Implementation Reviewer runs at F7.

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
