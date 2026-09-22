---
title: Objectives Home and Planner entry implementation plan
status: draft
spec: ./spec.md
spec_revision: 1
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-60
last_updated_at: 2026-09-22
---

# 1. Execution status

- **Spec:** [`spec.md`](./spec.md), revision `1`, status `ready`.
- **Why Plan-backed:** crosses `apps/web` and `apps/server`, three modules
  (Learning, Intelligence, Identity via the new shared auth composition),
  introduces a migration and a new web dependency, and has genuine
  non-overlapping parallelism across three implementation lanes.
- **Plan status:** `in_progress`. F1–F6 completed.
- **Next action:** F7 — activate the single Implementation Reviewer.
- **Active blockers/external dependencies:** none. `SHIFU-54` and `SHIFU-34` are
  cited in the Spec as context only; this Spec does not depend on either being
  implemented (quota gating is deferred; the manual-creation destination is a
  placeholder).
- **Active Builders:** none yet. Next dependency-ready Builders after `F1`:
  `Builder Server-Learning` (`F2`), `Builder Server-Intelligence` (`F3`),
  `Builder Web` (`F4`) — all three become ready simultaneously once `F1` exits.
- **Shared/root ownership (never delegated to a Builder):**
  `apps/server/src/shifu/app.py`, `apps/server/src/shifu/shared/pipes/shared_pipe.py`,
  `apps/web/src/routeTree.gen.ts` (generated), `apps/web/package.json` /
  `pnpm-lock.yaml`, and applying the new Alembic migration to the local dev
  database. These are Orchestrator-owned in `F1` and `F5` specifically to avoid
  two Builders writing the same file (`app.py` would otherwise need both
  `Builder Server-Learning` and `Builder Server-Intelligence` to add a line to
  it in the same wave).

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` `status: ready`, `revision: 1` | Orchestrator | `done` | none |
| Local infrastructure | `docker compose up -d` (Postgres, Inngest, Mailpit) running per `documentation/tooling.md` | Orchestrator | `done` | all services healthy; migrations applied through `faa7f006048a` |
| Playwright browser | `pnpm --filter web exec playwright install chromium` | Orchestrator | `done` | chromium available; 30/30 browser tests pass |
| `SHIFU-54` (AI quota) | not required — quota gating is explicitly deferred in the Spec | — | `not applicable` | none |
| `SHIFU-34` (manual Objective creation) | not required — this Spec only creates a placeholder route | — | `not applicable` | none |

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Orchestrator | F1 | Shared `AuthenticationProvider` composition available to every module | — | — | `completed` | `check:types`/`check:lint`/`check:architecture` pass; existing Identity tests unaffected |
| 2 | Builder Server-Learning | F2 | Learning Objectives-list slice complete | F1 | F3, F4 | `completed` (unit-scope; integration test deferred to F5 as designed) | unit test green now; controller integration test green after F5 |
| 2 | Builder Server-Intelligence | F3 | Intelligence start-planning slice complete | F1 | F2, F4 | `completed` (unit-scope; integration test deferred to F5 as designed) | unit test green now; controller integration test green after F5 |
| 2 | Builder Web | F4 | Home UI, composition, and three placeholder pages complete | — (contract-only; no runtime dependency on F2/F3) | F2, F3 | `completed` | component tests + build green now; Playwright suites green after F5 |
| 3 | Orchestrator | F5 | Post-wave integration: `app.state` wiring, route generation, dependency install, migration applied | F2, F3, F4 | — | `completed` | full `pnpm`/`uv` command set green across both apps |
| 4 | Orchestrator | F6 | Manual/runtime validation (`VM-01`..`VM-03`) via Playwright CLI | F5 | — | `completed` | `evaluation.md` records `EV-*` for each VM with fresh screenshots |
| 5 | Implementation Reviewer | F7 | Independent review of the fully integrated candidate | F5, F6 | — | `pending` | every verified finding resolved or explicitly rejected with evidence |
| 6 | Orchestrator | F8 | Final handoff | F7 | — | `pending` | every `CA-*`/`VM-*` has accepted evidence; ready for `conclude-spec` |

### F1 — Shared authentication composition

#### F1-T1 — Give Learning and Intelligence a way to authenticate a request

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** none; must complete before any Wave 2 Builder starts
- **Paths:** `apps/server/src/shifu/shared/pipes/shared_pipe.py` (Create);
  `apps/server/src/shifu/app.py` (Modify — add `app.state.authentication_provider`
  only; the two database registrations are deferred to `F5`)
- **Traceability:** prerequisite for RF-01/RF-02/RF-06 (every authenticated
  read/write in this Spec); see spec.md §3 "Authentication composition" and the
  `SharedPipe` row under REST
- **Outcome:** `SharedPipe.get_authenticated_user` returns an `AuthenticatedUser`
  for a valid bearer token and `401`s otherwise, without Learning or Intelligence
  importing `shifu.identity`
- **Rules:** `documentation/rules/provision-layer-rules.md`,
  `documentation/rules/server-app-layer-rules.md`,
  `documentation/rules/python-conventions-rules.md`
- **Risks/controls:** `app.py` is shared root configuration — keep this diff to
  exactly the one new `app.state` assignment so `F5`'s later additions apply
  cleanly
- **Exit:** `cd apps/server && uv run poe check:types && uv run poe check:lint && uv run poe check:architecture`;
  `uv run poe test:integration` (existing Identity suite) still passes unchanged

### F2 — Learning Objectives-list slice

#### F2-T1 — Query and project the authenticated account's Objectives

- **Status/owner:** `completed` (unit-scope) — Builder Server-Learning
- **Depends/parallel:** depends on F1; parallel with F3, F4; non-overlapping
  paths with both
- **Paths:** every Learning-owned row in spec.md §3 under "Domain (Learning)",
  "Interfaces (Learning)", the Learning row under "Use cases", the Learning rows
  under "Database", and the Learning rows under "REST" (`LearningPipe`,
  `GetHomeGoalsController`, `LearningRouter` registration,
  `apps/server/rest-client/learning/learning.rest`); plus
  `apps/server/tests/core/learning/use_cases/test_list_home_goals_use_case.py`
  and `apps/server/tests/rest/controllers/learning/test_get_home_goals_controller.py`
- **Traceability:** RF-02, RF-03, RF-09 (server projection/ordering), RF-11
  (isolation); CA-02, CA-03
- **Outcome:** `GET /learning/goals` returns only the caller's Objectives,
  ordered by most-recent update, projected to id/title/description/skill_count/
  updated_at
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/core-layer-rules.md`,
  `documentation/rules/use-case-testing-rules.md`,
  `documentation/rules/rest-layer-rules.md`,
  `documentation/rules/controllers-testing-rules.md`,
  `documentation/rules/database-layer-rules.md`
- **Risks/controls:** the controller integration test needs
  `app.state.learning_database`, which does not exist until `F5` — write the
  test now against the real route and let it fail/skip for the right reason
  (missing `app.state` attribute), not by mocking around the gap
- **Exit:** `uv run poe test:unit` passes for the new use-case test now;
  `uv run poe check:types`/`check:lint`/`check:architecture` pass; the `.rest`
  file has one labeled request for `GET /learning/goals`; the controller
  integration test is not required to pass until `F5`

### F3 — Intelligence start-planning slice

#### F3-T1 — Start and persist a temporary planning session

- **Status/owner:** `completed` (unit-scope) — Builder Server-Intelligence
- **Depends/parallel:** depends on F1; parallel with F2, F4; non-overlapping
  paths with both
- **Paths:** every Intelligence-owned row in spec.md §3 under "Domain
  (Intelligence)", "Interfaces (Intelligence)", the Intelligence row under "Use
  cases", the Intelligence rows under "Database" (including the migration file),
  and the Intelligence rows under "REST" (`IntelligencePipe`,
  `StartPlanningController`, `IntelligenceRouter` registration,
  `apps/server/rest-client/intelligence/intelligence.rest`); plus
  `apps/server/tests/core/intelligence/use_cases/test_start_planning_use_case.py`
  and `apps/server/tests/rest/controllers/intelligence/test_start_planning_controller.py`
- **Traceability:** RF-06, RF-07 (server-side non-empty enforcement); CA-06
- **Outcome:** `POST /intelligence/planning-sessions` validates a non-empty
  intent, mints an id, persists exactly one row, and returns it; no Learning
  state is touched
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/core-layer-rules.md`,
  `documentation/rules/use-case-testing-rules.md`,
  `documentation/rules/rest-layer-rules.md`,
  `documentation/rules/controllers-testing-rules.md`,
  `documentation/rules/database-layer-rules.md`
- **Risks/controls:** this is the first Intelligence persistence in the
  repository — confirm `apps/server/tach.toml` still shows `shifu.intelligence`
  depending only on `shifu.shared` after this change; confirm the new
  migration's `down_revision` is still the actual head (`c4d82f1e7a30`) at the
  time this task runs, in case another change landed on `main` since the Spec
  was written; `PlanningSessionModel.account_id` must stay a plain column with
  no foreign key, matching `GoalModel` (the Spec Reviewer flagged and the Spec
  now records this explicitly)
- **Exit:** `uv run poe test:unit` passes for the new use-case test now;
  `uv run poe check:types`/`check:lint`/`check:architecture` pass;
  `uv run poe test:integration` (Testcontainers-backed) passes, proving the
  migration applies cleanly against a disposable database; the `.rest` file has
  one labeled request for `POST /intelligence/planning-sessions`; the controller
  integration test assertions themselves are not blocked on `F5` here because
  Testcontainers-backed `test:integration` builds its own app instance — record
  in `evaluation.md` whether the test fixture already wires `app.state` fully or
  also needs the `F5` change reflected locally before this passes

### F4 — Home UI, composition, and placeholder pages

#### F4-T1 — Build the Home page and its three navigation destinations

- **Status/owner:** `completed` — Builder Web
- **Depends/parallel:** no runtime dependency on F2/F3 (the REST contracts are
  already fully specified in spec.md §3); parallel with F2, F3
- **Paths:** every UI row in spec.md §3's "UI" file tree (`routes/index.tsx`
  Modify; the three new placeholder route files; `constants/routes.ts` Modify;
  `rest/services/learning-service.ts` and `intelligence-service.ts` Create;
  `ui/shared/widgets/pages/home-page` Create and `dashboard-page` Remove;
  `ui/shared/widgets/layouts/root-layout` Modify for `QueryClientProvider`;
  `ui/learning/widgets/layouts/goals-list-section` and
  `ui/learning/widgets/components/objective-card` and the two Learning
  placeholder pages; `ui/intelligence/widgets/layouts/planning-intent-composer`
  and its placeholder page); `package.json`/`pnpm-lock.yaml` Modify (add
  `@tanstack/react-query`); plus every test file listed in spec.md §4 under
  `apps/web/src/ui/**/tests/` and `apps/web/tests/**`
- **Traceability:** RF-01, RF-03 through RF-11 (all client-observable Home
  behavior); CA-01, CA-03 through CA-12
- **Outcome:** `/` renders the intent field, "Criar manualmente", and the
  Objectives list in order, with all required states, and the three
  destinations are reachable
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `documentation/rules/ui-layer-rules.md`,
  `documentation/rules/web-app-routing-rules.md`,
  `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** component tests (Vitest) must mock the owning hook per
  `widget-testing-rules.md` and must not perform real network calls; the four
  Playwright suites are written now but are expected to fail until `F5`
  regenerates `routeTree.gen.ts` and the real backend is reachable — do not
  weaken them to pass early
- **Exit:** `pnpm --filter web check:lint`/`check:types`/`check:architecture`
  pass; `pnpm --filter web test:unit` (component tests) passes now;
  `pnpm --filter web build` passes; the four Playwright suites are not required
  to pass until `F5`/`F6`

### F5 — Post-wave integration

#### F5-T1 — Wire the remaining shared state and regenerate generated artifacts

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** depends on F2, F3, F4 all reaching their non-blocked
  exit; not parallel with anything (single integration point)
- **Paths:** `apps/server/src/shifu/app.py` (Modify — add
  `app.state.learning_database` and `app.state.intelligence_database`, using the
  `SqlalchemyLearningDatabase`/`SqlalchemyIntelligenceDatabase` classes created in
  F2/F3); `apps/web/src/routeTree.gen.ts` (Generate via
  `pnpm --filter web generate-routes`); `pnpm-lock.yaml` (Modify — real
  `pnpm install` after F4's `package.json` change); local Postgres migration
  application
- **Traceability:** unblocks the deferred exits of F2, F3, and F4
- **Outcome:** both new endpoints are reachable through the real running
  application; the web app's generated route tree includes the three new routes
- **Rules:** `documentation/rules/server-app-layer-rules.md`,
  `documentation/rules/provision-layer-rules.md`,
  `documentation/rules/database-layer-rules.md`
- **Risks/controls:** run `docker compose up -d` and confirm Postgres is
  reachable before `uv run poe db:upgrade`; if any Builder's diff needs
  correction to integrate cleanly, keep that Builder's task `in_progress`,
  record the finding here, resume the same Builder, and rerun this phase's exit
  — do not patch around it directly as the Orchestrator
- **Exit:** from `apps/server`: `uv run poe db:upgrade` succeeds;
  `uv run poe check:types && uv run poe check:lint && uv run poe check:architecture && uv run poe test:unit && uv run poe test:integration && uv run poe build`
  all pass, including the two previously-deferred controller integration tests;
  from the repository root: `pnpm --filter web generate-routes` then
  `pnpm --filter web check:lint && pnpm --filter web check:architecture && pnpm --filter web check:types && pnpm --filter web test:unit && pnpm --filter web build`
  all pass; with both apps running locally,
  `pnpm --filter web test:integration` passes, including the four
  previously-deferred Playwright suites

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | `test_list_home_goals_use_case.py` | CA-02 | Spec Validation Contract | `evaluation.md` `EV-1` | `pending` |
| Automated | `test_start_planning_use_case.py` | CA-06 | Spec Validation Contract | `evaluation.md` `EV-2` | `pending` |
| Runtime | `test_get_home_goals_controller.py` | CA-02 | Technical Contract (REST) | `evaluation.md` `EV-3` | `pending` |
| Runtime | `test_start_planning_controller.py` | CA-06 | Technical Contract (REST) | `evaluation.md` `EV-4` | `pending` |
| Automated | `goals-list-section.test.tsx` | CA-03, CA-09, CA-10, CA-11 | Spec Validation Contract | `evaluation.md` `EV-5` | `pending` |
| Automated | `planning-intent-composer.test.tsx` | CA-07, CA-08 | Spec Validation Contract | `evaluation.md` `EV-6` | `pending` |
| Runtime | `apps/web/tests/shared/home-page.test.ts` | CA-01, CA-04, CA-05, CA-06, CA-12 | Spec Validation Contract | `evaluation.md` `EV-7` | `pending` |
| Runtime | `apps/web/tests/learning/goal-create-placeholder-page.test.ts` | CA-05 | Spec Validation Contract | `evaluation.md` `EV-8` | `pending` |
| Runtime | `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` | CA-04 | Spec Validation Contract | `evaluation.md` `EV-9` | `pending` |
| Runtime | `apps/web/tests/intelligence/planner-placeholder-page.test.ts` | CA-06 | Spec Validation Contract | `evaluation.md` `EV-10` | `pending` |
| Manual | `VM-01` (visual, 1440×900 + 375×viewport + empty state) | CA-01, CA-03, CA-11 | Spec `VM-01`; `design/AMF1e.png` | Playwright screenshot path + `evaluation.md` `EV-11` | `pending` |
| Manual | `VM-02` (three navigation destinations, real persistence check) | CA-04, CA-05, CA-06 | Spec `VM-02` | `evaluation.md` `EV-12` | `pending` |
| Manual | `VM-03` (keyboard, narrow viewport, validation) | CA-07, CA-12 | Spec `VM-03` | `evaluation.md` `EV-13` | `pending` |
| REST client | `apps/server/rest-client/learning/learning.rest` | `GET /learning/goals` | Spec §3 REST | parity result + `evaluation.md` `EV-14` | `pending` |
| REST client | `apps/server/rest-client/intelligence/intelligence.rest` | `POST /intelligence/planning-sessions` | Spec §3 REST | parity result + `evaluation.md` `EV-15` | `pending` |

Full command set (both apps), also used as `F5`'s exit and rerun for final
handoff:

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web test:integration
pnpm --filter web build

cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe build
```

Schedule exactly one Implementation Reviewer (`F7`) after `F5` and `F6` both
pass. It checks the complete integrated candidate: cross-Builder contracts
(the two new REST endpoints and the shared `SharedPipe`), every changed path
against spec.md §3, the migration, both `.rest` files' parity, evidence
freshness, and the web UI surfaces against the Design Contract. Its report is
advisory; the Orchestrator verifies each finding, records accepted ones as
`ACH-*` in `evaluation.md`, resumes the responsible Builder for any correction,
invalidates stale evidence, and reruns the affected exits before resuming the
same Reviewer.

**Final handoff (`F8`) requires:**

- F1 through F6 all `completed`, and F7's findings all resolved or explicitly
  rejected with evidence;
- the exact Spec revision (`1`) unchanged throughout execution, or reconciled
  if it changed;
- every command in the full set above passing without lowering any configured
  floor;
- `routeTree.gen.ts`, the new migration, `pnpm-lock.yaml`/`uv.lock`, and both
  `.rest` files reviewed as part of the integrated diff;
- every `CA-01`..`CA-12` and `VM-01`..`VM-03` holding current accepted evidence
  in `evaluation.md`;
- the two accepted Design Contract gaps (no mobile Pencil frame; shared
  header/menu out of scope) still recorded as accepted, not silently dropped;
  and
- `evaluation.md` ready for `conclude-spec`.

Then route directly to `conclude-spec`. No phase below `F8` may be reported as
passed before it is actually observed and recorded.

# 5. Execution log

No execution has started yet; this section will be populated once `F1` begins.
