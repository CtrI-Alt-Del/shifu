---
title: Objective removal implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 2
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-67
last_updated_at: 2026-09-25
---

> **Superseded by `evaluation.md`'s "Revision 2" section.** This plan's body
> below (Waves 1–4, task statuses, path references) documents execution as it
> happened against `feat/shifu-65`, before that branch merged into `main` and
> `SHIFU-64` (merged separately) replaced `GoalDetailPlaceholderPage` with the
> real `GoalDetailPage`. All `goal-detail-placeholder-page` paths below are
> stale. See `evaluation.md`'s "Revision 2 — integration-point pivot and PR
> preparation" section and `spec.md` revision 2 for the corrected integration
> point, final gate results, and the reasoning for the pivot. This file was
> not rewritten line-by-line given the size of that change.

# 1. Execution status

- **Spec:** `documentation/features/learning/objective-removal/spec.md`,
  revision `2`, status `ready`.
- **Why Plan-backed:** the Spec's own handoff recommended direct
  `implement-spec`; Plan-backed execution was subsequently requested and is
  recorded here as the chosen strategy. The real coordination value it buys:
  two applications with fully disjoint path sets that support one genuine
  parallel wave; an Orchestrator-owned dependency/lockfile step that gates all
  web work; a strict internal web ordering (shadcn primitive → shared
  `ConfirmationDialog` → page wiring → browser suite) that a single
  undifferentiated task would blur; three shared-boundary web files
  (`ui/shadcn/button.tsx`, `ui/shared/.../icon/index.tsx`, and the new
  `ui/shared/.../confirmation-dialog/`) being changed for a Learning feature;
  and an outstanding external design-capture gate (`kZHN8`) that must stay
  visible from now through handoff.
- **Plan status:** `in_progress` — Wave 1 activation begun; dependency gate
  cleared (`@radix-ui/react-alert-dialog` added); `evaluation.md` initialized.
- **Next action:** `Builder Server` (F1-T1, F1-T2, F1-T3) and `Builder Web`
  (F2-T1, F2-T2) proceed in parallel. Both report focused exits (lint, types,
  unit tests) when complete; Orchestrator integrates and runs F1/F2 integration
  gates, then activates F3.
- **Active blockers:** none block Wave 1. The `kZHN8` design capture is
  an open gate that blocks only the visual-comparison evidence row (Visual rows
  in Validation and handoff) and final handoff, exactly as the Spec recorded it
  (accepted assumption for `ready`, required before shipping).
- **External dependencies:** none. Jira `SHIFU-36` (individual Habilidade
  removal) is *blocked by* this ticket and is not a gate for any phase here;
  the Spec's `ConfirmationDialog` is built to be reused by it later.
- **Active Builders:** `Builder Server` (F1), `Builder Web` (F2) — both
  dependency-ready and proceeding in parallel.
- **Next dependency-ready after F1/F2:** `Builder Web` (F3) — startable as soon
  as F2 exits pass.
- **Shared/root ownership:** `apps/web/package.json` and the root
  `pnpm-lock.yaml` are installed and committed by the **Orchestrator only**
  (never a Builder), per the create-plan ownership rule. The shared web files
  `apps/web/src/ui/shadcn/button.tsx`,
  `apps/web/src/ui/shared/widgets/components/icon/index.tsx` and the new
  `apps/web/src/ui/shared/widgets/components/confirmation-dialog/` are edited
  only by `Builder Web`, only within `F2`; `Builder Server` never touches
  `apps/web/**`, so there is no concurrent-edit risk in Wave 1. **No Alembic
  migration exists in this delivery** — Spec §3 establishes the
  `ON DELETE CASCADE` chain already present since `a25a7142d3ff`; migration
  head `e1a2b3c4d5e6` must be unchanged at handoff.

If `spec.md`'s revision changes before conclusion, record the mismatch as a
blocker here, stop dependent execution, invalidate affected task assignments
and evidence, and reconcile every phase, path, criterion and validation target
before resuming.

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` is `ready` at revision `1` with the Spec Reviewer pass resolved | Orchestrator | `done` | None |
| Web dependency | `@radix-ui/react-alert-dialog` present in `apps/web/package.json` and root `pnpm-lock.yaml` | Orchestrator | `pending` | Run `pnpm --filter web add @radix-ui/react-alert-dialog` from the repository root; review the lockfile diff. **Blocks `F2`.** |
| Environment — server | Docker Compose PostgreSQL **and Redis** available (`apps/server/src/shifu/app.py`'s lifespan aborts startup with "O Redis está indisponível" when Redis is down, so `test:integration` and any local run need both) | Builder Server | `pending` | `docker compose up -d` and `docker compose ps` before any `F1` integration command. **Blocks `F1` exit.** |
| Environment — browser | Playwright Chromium installed for `apps/web` | Builder Web | `pending` | `pnpm --filter web exec playwright install chromium`. **Blocks `F4` exit.** The suite's `webServer` config auto-starts the web dev server, and route tests use mocked transport, so no API is required for `F4`. |
| Environment — manual validation | `apps/server` + `apps/web` running, and a seeded account owning a Goal that has Habilidade experiences | Orchestrator | `pending` | Start both apps and `uv run poe db:seed` (seed account `student.seed@shifu.com` / `ShifuSeed123!`) before `F5`'s `VM-01`/`VM-02`. **Blocks `F5`.** |
| Design capture — `kZHN8` | One saved, visually-inspected screenshot of `design/shifu.pen` node `kZHN8` under `design/references/`, reconciled into `design/handoff.md` | User (only holder of Pencil access; no Pencil MCP was reachable when the Spec was authored) | `pending` | Capture and save the reference, then reconcile the handoff inventory. **Does not block `F2`–`F4`** (the Spec accepted the documented visual assumption for `ready`); **blocks the Visual row in §4 and final handoff.** If the captured frame contradicts the interim authority, stop and route it through the Spec amendment workflow — do not absorb the difference here. |

No product dependency from `documentation/modules.md` is turned into an
execution phase. The only technical dependencies sequenced below are the web
dependency gate → `F2`, `F2` → `F3`, and `F3` → `F4`.

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Server` | F1 | Complete server slice: `RemoveGoalUseCase`, `RemoveGoalController` + router registration, REST-client parity, unit + HTTP integration coverage, and the `CA-14` constraint evidence | — | F2 | `pending` | `uv run poe check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration` all pass from `apps/server`; `DELETE /learning/goals/{goal_id}` proven against real PostgreSQL |
| 1 | `Builder Web` | F2 | Shared web primitives: `ui/shadcn/alert-dialog.tsx`, `Button` `destructive` variant, two new `IconName` entries, and the reusable `ConfirmationDialog` with its component test | Web dependency gate (§2) | F1 | `pending` | `pnpm --filter web check:lint`, `check:architecture`, `check:types`, `test:unit` pass; `confirmation-dialog.test.tsx` green across open/closed/pending/error/no-outside-dismiss |
| 2 | `Builder Web` | F3 | Learning feature surface: `deleteGoal` REST operation, `useDeleteGoalAction`, page hook, page wiring, plus component and hook tests | F2 | — | `pending` | `pnpm --filter web check:lint`, `check:types`, `test:unit` pass; page component + page-hook suites green including invalidate-then-navigate ordering and the failure path |
| 3 | `Builder Web` | F4 | Browser route coverage for the removal flow on `/learning/goals/$goalId` | F3, browser gate (§2) | — | `pending` | `pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts` green, covering CA-11, CA-12, CA-16, CA-17, CA-18 with asserted request + visible-state pairs |
| 4 | Orchestrator | F5 | Integrated candidate: real server + web exercised together, `VM-01`/`VM-02` performed, REST-client parity verified, one Implementation Reviewer pass, all evidence recorded in `evaluation.md` | F1, F3, F4 | — | `pending` | Every `CA-*`/`VM-*` has current accepted evidence; Reviewer findings resolved; all commands in §4 pass; handoff condition in §4 satisfied |

Concurrency: at most **two** concurrent implementation Builders (Wave 1 only),
well inside the default limit. `Builder Server` owns `apps/server/**`
exclusively; `Builder Web` owns `apps/web/src/**` and `apps/web/tests/**`
exclusively; the Orchestrator owns `apps/web/package.json`, the root
`pnpm-lock.yaml` and every SDD artifact. No path is owned by two active
Builders.

### F1 — Server slice

#### F1-T1 — `RemoveGoalUseCase` with ownership enforcement

- **Status/owner:** `pending` — `Builder Server`
- **Depends/parallel:** no dependency; runs in parallel with all of `F2`
- **Paths:** `apps/server/src/shifu/learning/core/use_cases/remove_goal_use_case.py` (Create); `apps/server/src/shifu/learning/core/use_cases/__init__.py` (Modify); `apps/server/tests/learning/core/use_cases/test_remove_goal_use_case.py` (Create)
- **Traceability:** RP-22, JN-15 · RF-01, RF-02, RF-04 · CA-05
- **Outcome:** a single-action use case that opens one
  `learning_database.transaction()`, raises `GoalNotFoundError` when the Goal
  is absent or owned by another account, and otherwise calls
  `repos.goals.remove(goal)` — no other repository call.
- **Rules:** `documentation/rules/python-conventions-rules.md`;
  `documentation/rules/core-layer-rules.md`;
  `documentation/rules/use-case-testing-rules.md`
- **Risks/controls:** the tempting-but-wrong path is hand-deleting child rows.
  Spec §3 "Technical decisions" pins cascade-only; any explicit child delete is
  a contract deviation and must be reported, not improvised. Mocks use
  `create_autospec` against the `Protocol`, never handwritten doubles.
- **Exit:** `cd apps/server && uv run poe check:lint && uv run poe check:types && uv run poe test:unit`; all three `test_should_*` cases green, with the rejection cases asserting `remove` was never called.

#### F1-T2 — `DELETE /learning/goals/{goal_id}` end to end

- **Status/owner:** `pending` — `Builder Server`
- **Depends/parallel:** depends on `F1-T1`
- **Paths:** `apps/server/src/shifu/learning/rest/controllers/remove_goal_controller.py` (Create); `apps/server/src/shifu/learning/rest/router.py` (Modify); `apps/server/tests/learning/server/controllers/test_remove_goal_controller.py` (Create)
- **Traceability:** RP-22, JN-15 · RF-01, RF-02, RF-04, RF-07 · CA-01, CA-02, CA-03, CA-04, CA-06, CA-07, CA-10, CA-15
- **Outcome:** a registered route returning `204` with no body on success and
  `404` for missing-or-not-owned, proven against real PostgreSQL to cascade
  every `learning_skill_experiences`, `learning_competency_progresses`,
  `learning_activity_attempts` and `learning_activity_evaluations` row.
- **Rules:** `documentation/rules/rest-layer-rules.md`;
  `documentation/rules/controllers-testing-rules.md`;
  `documentation/rules/database-layer-rules.md`;
  `documentation/rules/python-conventions-rules.md`
- **Risks/controls:** the controller must declare `response_model=None`
  explicitly and return `Response(status_code=204)` (Spec §3 pins
  `MainPageEnteredController` as the precedent); it must contain **no**
  `try`/`except` error mapping — `GoalNotFoundError` propagates to the global
  `AppErrorHandler`. Repositories must not be mocked in the HTTP integration
  test.
- **Exit:** `cd apps/server && uv run poe check:architecture && uv run poe test:integration` with Compose PostgreSQL + Redis up; the cross-account case asserts the Goal and its rows survive; the success case asserts zero rows across all four child tables.

#### F1-T3 — REST-client parity and the `CA-14` constraint evidence

- **Status/owner:** `pending` — `Builder Server`
- **Depends/parallel:** depends on `F1-T2`
- **Paths:** `apps/server/rest-client/learning/learning.rest` (Modify)
- **Traceability:** RP-22 · RF-06 · CA-14 (plus route-group parity for the whole `learning` group)
- **Outcome:** the `learning` route group's `.rest` artifact covers every
  controller route in the group — the existing `GET /learning/goals` plus a new
  labeled `DELETE {{baseUrl}}/learning/goals/{{goalId}}` with a reusable
  `@goalId` variable and the `Authorization` header — and the `CA-14`
  disposable-environment evidence is captured.
- **Rules:** `documentation/rules/rest-layer-rules.md`;
  `documentation/rules/database-layer-rules.md`
- **Risks/controls:** no credentials or real tokens in the `.rest` file
  (`@accessToken` stays a placeholder). `CA-14` is **not** a pytest case — Spec
  §4 reclassified it after the Spec Reviewer flagged the non-HTTP assertion;
  producing it as a committed test is a contract deviation.
- **Exit:** every route in the `learning` group has one labeled request with current method/path/parameters/headers and no secrets; and, using the same PostgreSQL Testcontainer fixture already up for `F1-T2`, a direct `SqlalchemyActivityAttemptsRepository.add()` against a removed Goal's `skill_experience_id` raises `sqlalchemy.exc.IntegrityError` — traceback captured and handed to the Orchestrator for `evaluation.md` as the `CA-14`/`RF-06` evidence.

### F2 — Shared web primitives

#### F2-T1 — shadcn `AlertDialog` primitive, destructive `Button`, new icons

- **Status/owner:** `pending` — `Builder Web`
- **Depends/parallel:** depends on the web dependency gate (§2); parallel with all of `F1`
- **Paths:** `apps/web/src/ui/shadcn/alert-dialog.tsx` (Create); `apps/web/src/ui/shadcn/button.tsx` (Modify); `apps/web/src/ui/shared/widgets/components/icon/index.tsx` (Modify)
- **Traceability:** RP-22 · RF-03, RF-09 · supports CA-08, CA-17, CA-18
- **Outcome:** a Shifu-tokenized `AlertDialog` primitive (controlled
  `open`/`onOpenChange`, no overlay dismissal, `Escape` → Cancel), a `Button`
  `destructive` variant, and `'trash-2'` / `'triangle-alert'` registered in
  `IconName` + `ICON_COMPONENTS`.
- **Rules:** `documentation/rules/ui-layer-rules.md` (including its
  "Antipatterns to Avoid"); `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** the generated shadcn default palette must be replaced
  with Shifu CSS variables — no `bg-white`/`text-gray-*`/`bg-blue-*` literals
  (that is exactly how `AddSkillFoundationsDialog` diverged, per Spec §3). The
  `destructive` variant follows `documentation/design.md` §3.3: neutral
  surface, `--selo-text` label and border, never filled. Existing
  `default`/`ghost` behavior must not change.
- **Exit:** `pnpm --filter web check:lint && pnpm --filter web check:architecture && pnpm --filter web check:types` pass; `pnpm --filter web test:unit` still green (no regression in widgets already consuming `Button`/`Icon`).

#### F2-T2 — reusable `ConfirmationDialog`

- **Status/owner:** `pending` — `Builder Web`
- **Depends/parallel:** depends on `F2-T1`
- **Paths:** `apps/web/src/ui/shared/widgets/components/confirmation-dialog/index.tsx` (Create); `apps/web/src/ui/shared/widgets/components/confirmation-dialog/tests/confirmation-dialog.test.tsx` (Create)
- **Traceability:** RP-22, JN-15 · RF-03, RF-04, RF-05, RF-09 · CA-08, CA-12
- **Outcome:** a module-neutral, pure prop-to-markup confirmation dialog
  implementing the mandatory dialog header structure (semantic icon tile left
  of title+description, isolated top-right close wired to `onCancel`, header
  separator), disabling both actions while `isSubmitting` and rendering
  `error` inline.
- **Rules:** `documentation/rules/ui-layer-rules.md` ("Dialog header
  structure", "One widget per entrypoint", "Antipatterns to Avoid");
  `documentation/rules/widget-testing-rules.md`;
  `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** it owns **no** state — `isOpen`/`isSubmitting`/`error`
  arrive as props, so it correctly has no colocated hook; adding local state
  would break that classification. It must stay free of any Learning-specific
  copy (all strings are props) or it no longer belongs under `ui/shared`. Test
  file goes in `tests/`, never beside `index.tsx`.
- **Exit:** `pnpm --filter web test:unit` green with the six cases from Spec §4 (closed, scope copy without any text input, pending-disables-both, error visible, callbacks fire, no overlay dismissal); `role='alertdialog'` asserted.

### F3 — Learning feature surface

#### F3-T1 — `deleteGoal` transport and action hook

- **Status/owner:** `pending` — `Builder Web`
- **Depends/parallel:** depends on `F2`; no safe parallel work (same Builder)
- **Paths:** `apps/web/src/rest/services/learning-service.ts` (Modify); `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/use-delete-goal-action.ts` (Create)
- **Traceability:** RP-22 · RF-01, RF-04, RF-05 · supports CA-11, CA-12
- **Outcome:** `LearningService.deleteGoal(accessToken, goalId)` issuing
  `DELETE /learning/goals/{goalId}` with the bearer header and no response
  body, plus a `createServerFn`-backed `useDeleteGoalAction` exposing
  `{ deleteGoal, isDeletingGoal, deleteGoalError, resetDeleteGoal }`.
- **Rules:** `documentation/rules/rest-layer-rules.md` ("Web REST services use
  direct module files"); `documentation/rules/ui-layer-rules.md` ("Action
  hooks"); `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** neither file gets a dedicated test — Spec §3 and both
  Rules place their coverage at the consuming widget/route boundary; adding
  `use-delete-goal-action.test.ts` is a forbidden test path. The action hook is
  colocated under the page directory (Spec §3 "Action-hook placement"), *not*
  under `ui/learning/hooks/`, deliberately diverging from
  `use-add-skill-to-goal-action.ts`. Mirror that file's Better Auth access
  pattern rather than inventing a new one.
- **Exit:** `pnpm --filter web check:types && pnpm --filter web check:architecture` pass; no new test file introduced for either path.

#### F3-T2 — page hook, page wiring and their tests

- **Status/owner:** `pending` — `Builder Web`
- **Depends/parallel:** depends on `F3-T1`
- **Paths:** `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/use-goal-detail-placeholder-page.ts` (Create); `.../goal-detail-placeholder-page/index.tsx` (Modify); `.../goal-detail-placeholder-page/tests/goal-detail-placeholder-page.test.tsx` (Create); `.../goal-detail-placeholder-page/tests/use-goal-detail-placeholder-page.test.ts` (Create)
- **Traceability:** RP-22, JN-15 · RF-03, RF-04, RF-05, RF-08 · CA-08, CA-09, CA-11, CA-12, CA-13
- **Outcome:** the placeholder page gains a destructive "Remover Objetivo"
  trigger and the `ConfirmationDialog`; its colocated hook owns dialog state,
  invalidates `['learning', 'home-goals']` and navigates to `/` on success, and
  keeps the dialog open with the surfaced error on failure.
- **Rules:** `documentation/rules/ui-layer-rules.md` ("Keep UI logic inside the
  owning widget hook", "Imperative navigation uses the application hook",
  "Antipatterns to Avoid"); `documentation/rules/widget-testing-rules.md`;
  `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** the existing placeholder copy/markup must survive intact
  (the two pre-existing browser cases assert it). Hook functions use the
  `function` form; the component stays an exported `const` consuming the hook
  by direct named destructuring — no `controller` aggregate variable. This is
  the repository's **first** `useQueryClient()` call site (Spec §3), so there
  is no prior invalidation pattern to copy. Navigation goes through
  `useNavigation().navigateTo('root')`, never a raw `useNavigate`. The
  component test mocks the owning hook; it must not invoke the real one.
- **Exit:** `pnpm --filter web check:lint && check:types && test:unit` pass; hook suite proves invalidate-then-navigate ordering, no navigation while pending, and the failure path leaving `isConfirmDialogOpen` true.

### F4 — Browser route coverage

#### F4-T1 — extend the goal-detail route suite with the removal flow

- **Status/owner:** `pending` — `Builder Web`
- **Depends/parallel:** depends on `F3` and the browser gate (§2)
- **Paths:** `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` (Modify)
- **Traceability:** RP-22, JN-15 · RF-04, RF-05, RF-08, RF-09 · CA-11, CA-12, CA-16, CA-17, CA-18
- **Outcome:** the existing suite (anonymous redirect + static render) gains the
  removal flow: dialog open/cancel, confirm issuing exactly one
  `DELETE /learning/goals/{goalId}`, redirect to `/` with the Goal absent from
  the refreshed list, mocked-`500` keeping the dialog open with retry,
  duplicate-submit guard, full keyboard path, and a 375px viewport check.
- **Rules:** `documentation/rules/web-app-routing-rules.md` (mandatory route
  coverage matrix, shared Playwright fixtures);
  `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** transport is **mocked** — this suite must not be reported
  as proof of server authorization or persistence (that is `F1-T2`'s job). Use
  a **stateful** route mock so the post-delete Goal-list GET reflects the
  mutation; a single frozen fixture cannot prove CA-16. Import `test`/`expect`
  only from `../playwright`. Each request assertion must be paired with a
  visible-state assertion. The two pre-existing cases must still pass.
- **Exit:** `pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts` green; console errors and failed requests inspected and classified.

### F5 — Integration, manual validation and review

#### F5-T1 — integrated candidate, `VM-*` evidence and Implementation Reviewer

- **Status/owner:** `pending` — Orchestrator
- **Depends/parallel:** depends on `F1`, `F3`, `F4` and the manual-validation gate (§2)
- **Paths:** `documentation/features/learning/objective-removal/evaluation.md` (Create, at implementation kickoff); no source paths — corrections are routed back to the owning Builder
- **Traceability:** all of RF-01–RF-09 · all of CA-01–CA-18 · VM-01, VM-02
- **Outcome:** a reconciled integrated diff with real server + web exercised
  together, both manual scenarios performed, REST-client parity confirmed, one
  Implementation Reviewer pass completed and its verified findings resolved,
  and every criterion carrying current accepted evidence.
- **Rules:** every Rule listed in Spec §5's Rule table, re-checked against the
  integrated diff rather than per-Builder
- **Risks/controls:** a Builder report alone never completes a task — the
  Orchestrator reruns each exit. Any finding keeps the affected task
  `in_progress`, invalidates the stale evidence, and resumes the **responsible**
  Builder through `implement-spec`; a separate Builder Fix is activated only if
  that Builder cannot be resumed. Migration head must still be
  `e1a2b3c4d5e6` (this delivery adds none). If `kZHN8`'s capture contradicts
  the implemented dialog, stop and route it through the Spec amendment
  workflow.
- **Exit:** the full handoff condition in §4 is satisfied, then route directly to `conclude-spec`.

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | `apps/server` use-case unit suite | CA-05 | Spec Validation Contract | `evaluation.md` `EV-1` | `pending` |
| Runtime | `DELETE /learning/goals/{goal_id}` against real PostgreSQL (ownership, isolation, 401/404) | CA-01, CA-02, CA-03, CA-04 | Spec Technical Contract | `evaluation.md` `EV-2` | `pending` |
| Runtime | Real cascade removal across all four child tables, any status, pending/failed evaluation, other Goals intact | CA-06, CA-07, CA-10, CA-15 | Spec Technical Contract | `evaluation.md` `EV-3` | `pending` |
| Runtime | FK-violation constraint proof after removal (disposable environment, not a pytest case) | CA-14 | Spec §4 CA-14 note | `evaluation.md` `EV-4` | `pending` |
| Automated | `ConfirmationDialog` component suite | CA-08, CA-12 | Spec Validation Contract | `evaluation.md` `EV-5` | `pending` |
| Automated | Goal-detail page component + page-hook suites | CA-09, CA-11, CA-12, CA-13 | Spec Validation Contract | `evaluation.md` `EV-6` | `pending` |
| Automated | Playwright route suite, mocked transport | CA-11, CA-12, CA-16, CA-17, CA-18 | Spec Validation Contract | `evaluation.md` `EV-7` | `pending` |
| Manual | `VM-01` — trigger + confirmation happy path, desktop 1440×900 | CA-08, CA-09, CA-10, CA-16, CA-17 | Spec `VM-01` | `evaluation.md` `EV-8` | `pending` |
| Manual | `VM-01` — same flow, mobile 375×812 | CA-17, CA-18 | Spec `VM-01` | `evaluation.md` `EV-9` | `pending` |
| Manual | `VM-02` — failure, retry and duplicate-submit guard | CA-11, CA-12, CA-13 | Spec `VM-02` | `evaluation.md` `EV-10` | `pending` |
| Visual | Confirmation dialog vs. `kZHN8`, desktop | CA-08 | `design/references/kZHN8.png` (gated — not yet captured, §2) | Playwright artifact path + `EV-11` | `pending` |
| Visual | Confirmation dialog pending + error states, 375px | CA-11, CA-12, CA-18 | `documentation/design.md` §3.3/§9 (no designed frame exists for these states) | Playwright artifact path + `EV-12` | `pending` |
| REST client | `learning` route group parity | Spec Technical Contract (route-group parity) | `apps/server/rest-client/learning/learning.rest` | parity result + `EV-13` | `pending` |

Commands (all present in current manifests and `documentation/tooling.md`):

```bash
cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe build

pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web test:integration
pnpm --filter web build
```

Structural conformance against the Spec's affected-path map is an Orchestrator
review recorded in `evaluation.md`, not a command — there is no repository-wide
spec-implementation checker, and the web `check:code`/SonarQube gate is
explicitly outside the current local contract per `documentation/tooling.md`.

**Implementation Reviewer.** Schedule exactly one read-only
[`Implementation Reviewer`](../../../agents/implementation-reviewer-agent.md)
in `F5`, after every Builder diff is integrated and the automated gates plus
the evidence baseline pass. It reviews the complete candidate: the
server slice and its HTTP/persistence contract, the shared web primitives, the
Learning feature surface, the browser suite, REST-client parity, evidence
freshness, and every affected UI/server surface. Do not create reviewers per
Builder, phase or application. Its report is advisory — the Orchestrator
verifies each finding, records accepted `ACH-*` entries in `evaluation.md`,
resumes the responsible Builder, invalidates stale evidence and reruns the
affected exits, then resumes the **same** Reviewer.

**Final handoff condition.** All of the following must hold before routing to
`conclude-spec`:

- every task and phase is `completed`;
- the integrated diff is reconciled against `spec.md` revision `1`, with no
  path outside the Spec's affected-path map and no forbidden test path;
- every command above passes without lowering a configured floor;
- the lockfile diff for `@radix-ui/react-alert-dialog` is reviewed, and
  migration head is still `e1a2b3c4d5e6` (this delivery adds no migration);
- every `CA-01`–`CA-18` and both `VM-*` carry current accepted evidence;
- the `kZHN8` capture is complete, its visual comparison recorded, and the
  supplemental-state decision for the pending/error frames explicitly resolved;
- `apps/server/rest-client/learning/learning.rest` is present and covers every
  route in the group;
- the Implementation Reviewer completed and every verified finding is resolved;
- required services, accounts and fixtures were available, or each limitation
  is explicitly recorded in `evaluation.md`; and
- `evaluation.md` is ready for `conclude-spec`.
