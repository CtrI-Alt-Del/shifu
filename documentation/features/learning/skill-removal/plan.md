---
title: SHIFU-68 skill removal implementation plan
status: completed
spec: ./spec.md
spec_revision: 2
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-68
last_updated_at: 2026-09-26
---

## 1. Execution status

| Field | Current value |
| --- | --- |
| Contract | [`spec.md`](spec.md), revision 2, `ready`; independent Reviewer recheck completed without findings |
| Why a Plan | Server + Web, a generated lockfile, shared primitives, a cross-transaction lock-order change, Inngest evidence and three design-backed surfaces require coordinated ownership and recovery state |
| Plan state | `completed`; F0–F4 completed |
| Current phase | Local delivery concluded |
| Next action | Commit the validated delivery; publication remains separately authorized |
| Blockers | None |
| External dependencies | SHIFU-66 is fulfilled: Jira is `Concluído` and its full Skill experience is merged on `main`; no placeholder or deferred UI integration remains |
| Active Builders | None; Server and Web builders completed their bounded implementation streams |
| Shared/generated ownership | Orchestrator owns `apps/web/package.json`, `pnpm-lock.yaml`, SDD artifacts, final integration and reviewer coordination |

## 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Revision 2 reconciles PRD v21 and completed SHIFU-66; Reviewer recheck passed | Orchestrator | `completed` | Freeze revision at implementation kickoff |
| Visual authority | Four inspected PNGs and handoff; SHIFU-64 Lista/Grafo refs linked | Orchestrator | `completed` | Builders consume saved bundle, not live Pencil |
| Current integration surfaces | Final SHIFU-66 SkillPage/SkillExperience/SkillOverview, GoalDetail Lista/Grafo and EvaluateChoiceActivityJob exist on main `fa89380` | Orchestrator | `completed` | Recheck only if main advances before kickoff |
| Web dependency | Radix DropdownMenu installed; generated package/lockfile diff reviewed | Orchestrator | `completed` | None |
| Database/runtime | PostgreSQL and disposable Inngest Testcontainers verified by full suites | Orchestrator | `completed` | None |
| Browser runtime | Playwright CLI focused routes verified with managed webServer | Orchestrator | `completed` | User performs requested interface acceptance |

## 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Orchestrator | F0 | DropdownMenu dependency and generated lockfile are reproducible | Spec r2 | F1 | `completed` | package diff reviewed; web types/build pass |
| 1 | `Builder Server` | F1 | Atomic authorized DELETE and late-event safety, with one global lock order | Spec r2 | F0 | `completed` | focused and full server gates pass |
| 2 | `Builder Web` | F2 | Shared menu and confirmation foundations match saved design and accessibility contract | F0 | F1 | `completed` | component tests and web static gates pass |
| 3 | `Builder Web` | F3 | SkillPage, Lista and Grafo remove one Habilidade with correct post-success state | F2; stable DELETE contract from Spec | — | `completed` | unit and focused 21-test Playwright route suite pass |
| 4 | Orchestrator | F4 | Integrated candidate, runtime/visual evidence and one implementation review are complete | F1, F3 | — | `completed` | automated gates, reviewer corrections and user acceptance complete |

### F0 — Shared dependency coordination

#### F0-T1 — Install the accessible menu primitive dependency

- **Status/owner:** `completed` — Orchestrator.
- **Depends/parallel:** Spec r2; parallel with F1.
- **Paths:** `apps/web/package.json`, `pnpm-lock.yaml` only.
- **Traceability:** RF-07, RF-10; CA-08, CA-09, CA-13.
- **Outcome:** `@radix-ui/react-dropdown-menu` is added from repository root via
  `pnpm --filter web add @radix-ui/react-dropdown-menu`; the generated lockfile
  contains no unrelated dependency churn.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `documentation/rules/ui-layer-rules.md`.
- **Risks/controls:** preserve current pnpm resolver and never hand-edit the
  lockfile; review package and lock diffs before F2.
- **Exit:** `pnpm --filter web check:types`; scoped diff review for both paths.

### F1 — Server removal and concurrency contract

#### F1-T1 — Implement the Core action and global lock order

- **Status/owner:** `completed` — Builder Server.
- **Depends/parallel:** Spec r2; parallel with F0.
- **Paths:**
  `apps/server/src/shifu/learning/core/interfaces/skill_experiences_repository.py`,
  `apps/server/src/shifu/learning/core/use_cases/remove_skill_from_goal_use_case.py`,
  `apps/server/src/shifu/learning/core/use_cases/evaluate_choice_activity_use_case.py`,
  `apps/server/src/shifu/learning/core/use_cases/__init__.py`,
  `apps/server/src/shifu/learning/database/sqlalchemy/repositories/skill_experiences_repository.py`,
  `apps/server/tests/learning/core/use_cases/test_remove_skill_from_goal_use_case.py`,
  `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py`.
- **Traceability:** RP-03, RP-21; RF-01–RF-06; CA-01, CA-02, CA-05, CA-06.
- **Outcome:** one Learning transaction authorizes and removes the experience;
  evaluation and removal both acquire experience before evaluation locks.
- **Rules:** `python-conventions-rules.md`, `core-layer-rules.md`,
  `use-case-testing-rules.md`, `database-layer-rules.md`.
- **Risks/controls:** changing the evaluation lock order must preserve all
  stale/missing guards; unit tests assert both no-op behavior and collaboration
  order without importing infrastructure into Core.
- **Exit:** focused pytest for both use cases; `uv run poe check:lint`,
  `check:architecture`, `check:types`, `test:unit` from `apps/server`.

#### F1-T2 — Expose and prove the real DELETE boundary

- **Status/owner:** `completed` — Builder Server.
- **Depends/parallel:** F1-T1; parallel with F2 after its dependency is ready.
- **Paths:**
  `apps/server/src/shifu/learning/rest/controllers/remove_skill_from_goal_controller.py`,
  `apps/server/src/shifu/learning/rest/controllers/__init__.py`,
  `apps/server/src/shifu/learning/rest/router.py`,
  `apps/server/rest-client/learning/learning.rest`,
  `apps/server/tests/learning/server/controllers/test_remove_skill_from_goal_controller.py`,
  `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`.
- **Traceability:** RF-01–RF-06; CA-01–CA-07.
- **Outcome:** authenticated nested DELETE returns 204 only after commit; real
  PostgreSQL proves all cascades/isolation/rollback/concurrency, and real Inngest
  proves a late canonical event is a no-op after the domain action.
- **Rules:** `rest-layer-rules.md`, `controllers-testing-rules.md`,
  `database-layer-rules.md`, `messaging-layer-rules.md`,
  `jobs-testing-rules.md`.
- **Risks/controls:** coordinate concurrent transactions with events/barriers and
  bounded timeouts, never sleeps; test concept observations/states as well as
  legacy rows; retain the immutable outbox history.
- **Exit:** focused controller integration and job integration pass; full
  `uv run poe test:integration`, `uv run poe test:jobs`, and server build pass;
  `learning.rest` has one labeled, current, secret-free request for every
  registered Learning route.

### F2 — Shared web interaction foundations

#### F2-T1 — Build the reusable menu and extend confirmation content

- **Status/owner:** `completed` — Builder Web.
- **Depends/parallel:** F0; parallel with F1.
- **Paths:**
  `apps/web/src/ui/shadcn/dropdown-menu.tsx`,
  `apps/web/src/ui/shared/widgets/components/confirmation-dialog/index.tsx`,
  `apps/web/src/ui/shared/widgets/components/confirmation-dialog/tests/confirmation-dialog.test.tsx`,
  `apps/web/src/ui/learning/widgets/components/skill-actions-menu/index.tsx`,
  `apps/web/src/ui/learning/widgets/components/skill-actions-menu/tests/skill-actions-menu.test.tsx`.
- **Traceability:** RF-07, RF-08, RF-10; CA-08–CA-10, CA-13.
- **Outcome:** one pure feature menu supplies “Remover habilidade” to every
  surface; shared confirmation renders the loss list without regressing
  SHIFU-67.
- **Rules:** `typescript-conventions-rules.md`, `ui-layer-rules.md`,
  `widget-testing-rules.md`; `documentation/design.md` §3.3/T14.
- **Risks/controls:** use the shadcn wrapper instead of direct feature imports
  from Radix; keep Goal removal defaults stable; test accessible names,
  focus/Escape and pending/error states.
- **Exit:** focused Vitest suites pass; `pnpm --filter web check:lint`,
  `check:architecture`, and `check:types` pass for the integrated F0/F2 diff.

### F3 — Web page integration

#### F3-T1 — Add the shared action and SkillPage flow

- **Status/owner:** `completed` — Builder Web.
- **Depends/parallel:** F2; can proceed against the frozen HTTP contract while
  F1-T2 finishes, but runtime success evidence waits for F1.
- **Paths:**
  `apps/web/src/rest/services/learning-service.ts`,
  `apps/web/src/ui/learning/hooks/use-remove-skill-action.ts`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/use-skill-page.ts`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/tests/skill-experience.test.tsx`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/skill-overview/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/skill-page/tests/skill-page.test.tsx`,
  `apps/web/tests/learning/skill-experience-page.test.ts`.
- **Traceability:** RF-07–RF-10; CA-08–CA-10, CA-12, CA-13.
- **Outcome:** SkillPage authenticates through the existing BFF boundary,
  exposes the action in diagnostic and settled states, replaces the inert
  SHIFU-66 overview trigger without regressing its content, prevents duplicate
  submission, recovers in-place and navigates to the same Goal's graph after
  success.
- **Rules:** `rest-layer-rules.md`, `typescript-conventions-rules.md`,
  `ui-layer-rules.md`, `widget-testing-rules.md`.
- **Risks/controls:** action/query hooks receive no direct test; consumer page
  and route tests prove method/path/lifecycle. Closing/canceling resets stale
  mutation errors.
- **Exit:** focused SkillPage/SkillExperience component suites and the existing
  `skill-experience-page` route suite pass; request is one BFF POST that maps to
  exactly one backend DELETE; URL and visible destination are asserted.

#### F3-T2 — Replace Lista/Grafo stubs without changing view behavior

- **Status/owner:** `completed` — Builder Web.
- **Depends/parallel:** F3-T1 action contract; sequential ownership avoids
  overlapping changes in the shared GoalDetail page.
- **Paths:**
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/use-goal-detail-page.ts`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/goal-detail-page.test.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/tests/use-goal-detail-page.test.ts`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-list/goal-skill-row/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/use-goal-skill-graph.ts`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-node/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/tests/goal-skill-graph.test.tsx`,
  `apps/web/tests/learning/goal-detail-page.test.ts`.
- **Traceability:** RF-04, RF-07–RF-10; CA-05, CA-08–CA-11, CA-13.
- **Outcome:** both stubs become the same menu; GoalDetail owns one selected
  skill/dialog/mutation, refreshes matching query caches, removes the node/row
  and preserves its local `view`.
- **Rules:** `typescript-conventions-rules.md`, `ui-layer-rules.md`,
  `widget-testing-rules.md`; SHIFU-64 design manifest.
- **Risks/controls:** callbacks travel through explicit props/node data; do not
  remount the page, enable node dragging or regress edge highlighting; update
  the graph's existing colocalized test contract.
- **Exit:** focused GoalDetail component/hook/graph/route suites pass; list and
  graph requests, same-view result and sibling preservation are asserted.

#### F3-T3 — Close the complete web gate

- **Status/owner:** `completed` — Builder Web.
- **Depends/parallel:** F3-T1 and F3-T2.
- **Paths:** no new paths; fixes remain inside the F2/F3 ownership fences.
- **Traceability:** RF-07–RF-10; CA-08–CA-13.
- **Outcome:** the complete web candidate is type-safe, architecture-safe and
  builds with generated routes unchanged except normal Vite output.
- **Rules:** all Web Rules selected in the Spec.
- **Risks/controls:** do not classify mocked route transport as real backend
  evidence; preserve unrelated tests and existing warning baseline.
- **Exit:** web lint, architecture, types, unit, integration and build commands
  all pass; failures are classified in Evaluation rather than hidden.

### F4 — Integrated validation and review

#### F4-T1 — Reconcile candidate, collect runtime evidence and review once

- **Status/owner:** `completed` — Orchestrator; automated evidence, reviewer
  corrections and user acceptance complete.
- **Depends/parallel:** F1 and F3 complete; no parallel code edits.
- **Paths:** `documentation/features/learning/skill-removal/evaluation.md` only
  for evidence; implementation corrections return to their owning Builder.
- **Traceability:** every RP/JN/RF/CA/VM/CI in Spec revision 2.
- **Outcome:** real API/PostgreSQL/Inngest behavior and all three UI surfaces
  are observed; one Implementation Reviewer audits the integrated diff.
- **Rules:** AGENTS browser workflow, SDD implement/conclude prompts and every
  Rule selected in the Spec.
- **Risks/controls:** fresh screenshots at exact viewports; inspect final URL,
  DELETE, persisted rows, console, failed requests, focus and layout; stop only
  processes started for validation.
- **Exit:** all acceptance/evidence rows current; Reviewer completed; verified
  findings resolved by the original Builder and affected gates rerun; candidate
  is ready for `conclude-spec`.

## 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Core removal + lock ordering | CA-01, CA-02, CA-05, CA-06 | Spec Technical Contract | Evaluation EV | `completed` |
| Runtime | DELETE + PostgreSQL cascade/isolation/rollback/concurrency | CA-01–CA-06 | Spec CA matrix | Evaluation EV | `completed` |
| Runtime | Late Inngest event after domain removal | CA-07 | Existing canonical job path | Evaluation EV | `completed` |
| REST client | Complete Learning route group | Technical Contract | `apps/server/rest-client/learning/learning.rest` | Parity result + EV | `completed` |
| Automated | Web components/hooks/routes | CA-08–CA-13 | Spec test boundaries | Evaluation EV | `completed` |
| Manual | VM-01 SkillPage desktop success/error/retry | CA-08–CA-10, CA-12, CA-13 | `design/references/uyfWq.png`, `wr9RG.png`, `C51Tjy.png` | Playwright assertions + user acceptance | `completed` |
| Visual | SkillPage desktop menu | CA-08, CA-13 | `uyfWq.png`, 1440 × 900 | Fresh screenshot + comparison | `pending` |
| Visual | Confirmation default | CA-08–CA-10 | `C51Tjy.png`, component 440 px | Fresh screenshot + comparison | `pending` |
| Visual | Confirmation pending/error supplemental states | CA-10, CA-13 | Handoff conventions | Fresh screenshots + comparison | `pending` |
| Manual/visual | VM-02 SkillPage mobile | CA-08, CA-10, CA-13 | `wXPwI.png`, 390 × 844 | Playwright DOM/layout assertions; user accepted behavior | `completed` |
| Manual/visual | VM-03 GoalDetail Lista | CA-08, CA-11, CA-13 | SHIFU-64 Lista + `wr9RG.png` | Playwright request/view evidence; user accepted behavior | `completed` |
| Manual/visual | VM-03 GoalDetail Grafo | CA-08, CA-11, CA-13 | SHIFU-64 Grafo + `wr9RG.png` | User screenshot + Playwright request/view evidence | `completed` |
| Review | One integrated Implementation Reviewer | all | Spec r2 + complete diff | ACH ledger | `completed`; findings resolved/accepted |

The implementation handoff is complete only when every task and phase is
`completed`; Spec revision 2 and the complete diff are reconciled; all declared
uv/pnpm gates pass without relaxed configuration; package/lockfile, route
registration and REST-client parity are reviewed; every CA and VM has current
accepted evidence; all required visual comparisons are fresh; Docker/browser
limitations are resolved or explicitly classified; the single Implementation
Reviewer has rechecked any corrections; and `evaluation.md` is ready for
`conclude-spec`. No phase, command, review or runtime result in this Plan is
claimed as already executed.
