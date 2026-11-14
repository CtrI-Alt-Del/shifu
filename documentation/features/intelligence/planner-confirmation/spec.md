---
title: Goal Planner confirmation that creates the planned Goal in Learning
status: draft
revision: 1
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-95
scope:
  - apps/server (shared port, learning creation, intelligence confirm route)
  - apps/web (intelligence planner review states)
  - documentation/features/intelligence/planner-confirmation
last_updated_at: 2026-10-20
---

# Objective

Turn the proposal the learner explicitly confirmed on the Planner review (`SHIFU-93`)
into a real Learning Goal with one Skill experience per proposed Skill and its inclusion
rationale, created as one result and never duplicated when the same confirmation is
repeated. The review shows the creation in progress, a confirmed failure that keeps the
proposal, and an uncertain result that is verified instead of reported as a failure; a
success leads to the Goal page, where the justifications are read-only. Compact mode:
one route and one review surface already covered by browser suites; four frames.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Confirm route (learner) | `POST /intelligence/planning-sessions/{planning_id}/confirm` with the confirmation key and the title/description edits; Skills and justifications come from the stored proposal | Any client-provided Skill list |
| Learning creation (system) | Validation of Learning's own rules, Goal + Skill experiences (`inclusion_reason`) + competency progresses in one transaction, confirmation record keyed by account + confirmation key, replay of the same key, recovery after the temporary planning expired | Automatic diagnosis start, progress, rewards |
| Shared boundary (system) | Port `PlannedGoalProvider` and its structures in Shared, implemented by Learning and bound in `app.py` | Outbox event between the modules |
| Review states (learner) | Creating (frozen review, busy action), confirmed failure with retry, uncertain result with verification, success navigation to the Goal page and Home list refresh | Changes to the interview, outcomes or restart of `SHIFU-92`/`SHIFU-93` |
| Goal page (learner) | Already renders `inclusionReason` read-only in the List (`SHIFU-64`); planned Goals now carry it | New Goal page layouts |

PRD coverage. Intelligence (v4): `RP-10` **implemented** (confirmation, idempotent repeat,
uncertain result, failure keeps the proposal, success navigates, justifications preserved,
temporary planning discarded), `RP-11` **implemented** (ownership on every call), `RP-12`
**implemented** (states with text and roles, keyboard, 44 px targets); `JN-13` **implemented**.
Learning (v24): `RP-02` **implemented**, `RP-03` **implemented** for independent
experiences with the original justification, `RP-05` **implemented** (no diagnosis starts),
`RP-25` **implemented** for the review states.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | Intelligence RP-10; JN-13 | `Criar objetivo` on the review posts `{ confirmation_key, title, description }` to `/intelligence/planning-sessions/{planning_id}/confirm`. The backend builds the confirmed plan from its stored proposal (Skills and justifications), never from the client. Success answers `200 { goal_id, replayed }`. |
| RF-02 | Learning RP-02 | Before creating, Learning verifies title and description present (240 / 4000 limits), at least one Skill, no duplicated Skill, a non-blank justification for every Skill and that every Skill exists and can start (`v2_eligible`). An invalid plan answers `400`; a Skill that cannot start answers `409` (`curriculum_gap` message); nothing is written. |
| RF-03 | Learning RP-02, RP-03, RP-05 | The Goal, one `not-started` Skill experience per Skill with `inclusion_reason = justification`, and the competency progresses are written in one Learning transaction; any failure rolls back everything. No diagnosis starts. |
| RF-04 | Intelligence RP-10 | The pair (account, confirmation key) identifies one confirmation. Repeating it returns the same `goal_id` with `replayed: true`; a repeat with another content answers `409`; concurrent repeats are serialized by a transaction-scoped advisory lock. The record (`learning_goal_confirmations`) outlives the Redis planning. |
| RF-05 | Intelligence RP-10; JN-13 | A successful confirmation removes the temporary planning. A later confirm with the same key, with or without the planning, returns the stored Goal; without a stored confirmation and without the planning it answers `404`. |
| RF-06 | Intelligence RP-07, RP-10 | Confirm requires status `proposal` and no running operation (`409` otherwise). `Cancelar` keeps deleting the planning and returning to the Home. |
| RF-07 | Intelligence RP-10, RP-12 | While the request runs the review is frozen: fields disabled, `Cancelar` and `Reiniciar planejamento` disabled, the primary action reads `Criando objetivo…` with a spinner and the notice `Criando seu objetivo…` / `Estamos salvando o objetivo e as habilidades que você confirmou.` is announced. Double clicks send one request. |
| RF-08 | Intelligence RP-10; Learning RP-02 | A confirmed failure (`400`, `409`) keeps the proposal and the edits, shows `Não foi possível criar o objetivo` with the backend reason followed by `Sua proposta foi mantida.` (or the generic `Sua proposta foi mantida. Tente criar o objetivo novamente.`), unfreezes the review and offers `Tentar criar objetivo`, which replays the same key. |
| RF-09 | Intelligence RP-10 | A lost response or an unavailable backend leaves the review frozen with `Não conseguimos confirmar a criação do objetivo` and `Verificar resultado`, which replays the same key; the copy never states that no Goal was created. A `404` on confirm refreshes the planning state instead. |
| RF-10 | Learning RP-02; Intelligence RP-10 | On success the Home goals list is invalidated, the planning query is dropped and the learner lands on `/learning/goals/{goalId}`, whose List shows each justification read-only. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-03 | A `proposal` planning with two eligible Skills | `POST …/confirm` with a key and edited title | `200`, `replayed: false`; the Goal has the edited title, one experience per Skill with the proposal justification, competency progresses, and the Redis planning is gone | CI-01 / CI-02 |
| CA-02 | RF-01 | The same request carrying a `skills` field | `POST …/confirm` | `422` and nothing changes | CI-02 |
| CA-03 | RF-02 | A proposal whose Skill cannot start (graph-only seed Skill) | `POST …/confirm` | `409` `conflict`, no Goal row, the planning keeps its proposal | CI-01 / CI-02 |
| CA-04 | RF-02 | Blank title, blank description, empty Skills, duplicated Skill or blank justification | Learning use case | `InvalidGoalError`; no transaction opened | CI-01 |
| CA-05 | RF-04, RF-05 | A confirmation already completed | The same key again (with or without the planning) | `200`, same `goal_id`, `replayed: true`, no new Goal | CI-01 / CI-02 |
| CA-06 | RF-04 | A completed key | The same key with another title | `409`, no new Goal | CI-01 / CI-02 |
| CA-07 | RF-05, RF-06 | Unknown planning without a stored confirmation; interviewing or processing planning | `POST …/confirm` | `404`; `409` | CI-01 / CI-02 |
| CA-08 | RF-07, RF-10 | The review with an edited title | `Criar objetivo` | Frozen review and busy action while the request runs; then the Goal page with the edited title and the justifications in the List; the Home list is invalidated; one request with a UUID key | CI-03 / CI-04 / VM-02 |
| CA-09 | RF-08 | The backend answers `409` with a reason | `Criar objetivo`, then `Tentar criar objetivo` twice quickly | Failure notice with the reason, fields enabled and edits kept; the retry sends one request per click cycle and every request repeats the same key | CI-03 / CI-04 / VM-02 |
| CA-10 | RF-09 | The transport fails | `Criar objetivo`, then `Verificar resultado` once the backend answers | Uncertain notice (status, not alert), review frozen except the verification; the replay with the same key lands on the Goal | CI-03 / CI-04 |
| CA-11 | RF-09 | The backend answers `404` on confirm | `Criar objetivo` | The planning is refetched and the page shows its real state; no failure copy | CI-03 |
| CA-12 | RF-07, RF-08 | 390 × 844 | Creating and failed states | No horizontal scroll; the stacked actions keep the busy / retry labels | CI-04 / VM-02 |

# Technical Contract

## Architecture Mapping

Owners: `shared` (port), `learning` (creation), `intelligence` (confirm route, review).
Rules: [core layer](../../../rules/core-layer-rules.md) (module-neutral contracts in
Shared), [provision layer](../../../rules/provision-layer-rules.md) (a module implements a
Shared port under its `providers`), [REST layer](../../../rules/rest-layer-rules.md),
[UI layer](../../../rules/ui-layer-rules.md), [widget testing](../../../rules/widget-testing-rules.md).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | shared core | `PlannedGoalSkill`, `PlannedGoalConfirmation`, `PlannedGoalCreation` — `apps/server/src/shifu/shared/core/domain/structures/planned_goal_*.py` | Module-neutral structures of the confirmed plan and its result |
| Create | shared core | `PlannedGoalProvider` — `apps/server/src/shifu/shared/core/interfaces/planned_goal_provider.py` | `create(confirmation) -> PlannedGoalCreation`, `find(account_id, confirmation_key) -> PlannedGoalCreation \| None` |
| Create | learning core | `GoalConfirmation` structure, `GoalConfirmationsRepository` (`lock`, `find`, `add`), `GoalConfirmationConflictError`, `CreatePlannedGoalUseCase` | Validation, one transaction, replay by key, divergent content conflict |
| Modify | learning core | `LearningDatabaseRepositories.goal_confirmations` | New repository in the unit of work |
| Create | learning database | `GoalConfirmationModel` (`learning_goal_confirmations`), mapper, `SqlalchemyGoalConfirmationsRepository`, migration `c3e7a9d2f5b1` | PK (`account_id`, `confirmation_key`), `goal_id` FK with cascade, `fingerprint`, advisory lock |
| Create | learning providers | `LearningPlannedGoalProvider` | Implements the Shared port over the use case and the repository |
| Create | intelligence core | `ConfirmPlanningUseCase` | Ownership, state guards, hand-over with the stored Skills, removal of the planning, recovery by key |
| Create | intelligence REST | `ConfirmPlanningController` (`POST …/confirm`), `IntelligencePipe.get_planned_goal_provider` | Request `{ confirmation_key (UUID), title ≤ 240, description ≤ 4000 }` → `{ goal_id, replayed }` |
| Modify | app | `apps/server/src/shifu/app.py` | Binds `LearningPlannedGoalProvider` to `app.state.planned_goal_provider` |
| Modify | server docs | `apps/server/rest-client/intelligence/intelligence.rest` | Confirm example |
| Modify | web core | `PlanningGoalCreationRequest.confirmationKey`, `PlanningGoalCreation`, length constants, `CONFIRMATION_KEY_PATTERN` | `apps/web/src/core/intelligence/planning-session.ts` |
| Modify | web REST | `IntelligenceService.confirmPlanning` | `POST …/confirm` mapped to `{ goalId, replayed }` |
| Create | web hooks | `useConfirmPlanningAction`, `confirmPlanningServer` — `apps/web/src/ui/intelligence/hooks/use-confirm-planning-action.ts`; `home-goals-query-key.ts` | Zod input, `withPlanningService`, shared Home key |
| Modify | web UI | `usePlannerPage` (`goalCreation` state, `handleCreateGoal`, `leaveToGoal`), `PlanningProposalReview` (`goalCreation` prop, frozen review, labels, notice), `usePlanningProposalReview` (confirmation key, labels, notice), `PlanningProcessingNotice` (`uncertain` tone) | States of RF-07 … RF-10; the provisional `onCreateGoal` prop and notice of SHIFU-93 are removed |
| Modify | web tests | planner page, review and hook suites, `planning-server-functions.test.ts`, `tests/intelligence/planner-page.test.ts` | Creation states, replay, recovery, four frame captures |
| Modify | CI | `.github/workflows/server-app-ci.yaml` | New server test modules in the coverage selection |

Contracts:

```python
class PlannedGoalProvider(Protocol):
    def create(self, confirmation: PlannedGoalConfirmation) -> PlannedGoalCreation: ...
    def find(self, account_id: str, confirmation_key: str) -> PlannedGoalCreation | None: ...

# PlannedGoalConfirmation(account_id, confirmation_key, planning_id, title, description, skills: tuple[PlannedGoalSkill, ...])
# PlannedGoalSkill(skill_id, inclusion_reason); PlannedGoalCreation(goal_id, confirmation_key, replayed)
# ConfirmPlanningUseCase(sessions, planned_goals).execute(account_id, planning_id, confirmation_key, title, description)
# CreatePlannedGoalUseCase(database, curriculum, clock, identifiers).execute(confirmation)
```

```ts
export type PlanningGoalCreationRequest = { planningId; confirmationKey; title; description; proposal }
export type PlanningGoalCreation = { goalId: string; replayed: boolean }
export type GoalCreationState = { status: 'idle' | 'creating' | 'failed' | 'uncertain'; message: string | null }
// usePlannerPage → goalCreation, isCreatingGoal, handleCreateGoal(request)
// usePlanningProposalReview → isFrozen, createGoalLabel, goalCreationNotice, handleCreateGoal (adds the key)
```

Expected file tree:

```text
apps/server/
├── migrations/versions/c3e7a9d2f5b1_add_learning_goal_confirmations.py             [N]
├── rest-client/intelligence/intelligence.rest                                       [M]
└── src/shifu/
    ├── app.py                                                                       [M]
    ├── shared/core/domain/structures/planned_goal_{skill,confirmation,creation}.py  [N]
    ├── shared/core/interfaces/planned_goal_provider.py                              [N]
    ├── learning/core/domain/structures/goal_confirmation.py                         [N]
    ├── learning/core/domain/errors/goal_confirmation_conflict_error.py              [N]
    ├── learning/core/interfaces/{goal_confirmations_repository,learning_database}.py [N,M]
    ├── learning/core/use_cases/create_planned_goal_use_case.py                      [N]
    ├── learning/database/sqlalchemy/{models,mappers,repositories}/goal_confirmation* [N]
    ├── learning/providers/learning_planned_goal_provider.py                         [N]
    ├── intelligence/core/use_cases/confirm_planning_use_case.py                     [N]
    ├── intelligence/rest/controllers/confirm_planning_controller.py                 [N]
    └── intelligence/pipes/intelligence_pipe.py                                      [M]
apps/web/src/
├── core/intelligence/planning-session.ts                                            [M]
├── rest/services/intelligence-service.ts                                            [M]
├── ui/intelligence/hooks/{use-confirm-planning-action,home-goals-query-key}.ts      [N]
└── ui/intelligence/widgets/pages/planner-page/
    ├── use-planner-page.ts, index.tsx, planning-processing-notice/index.tsx         [M]
    └── planning-proposal-review/{index.tsx,use-planning-proposal-review.ts}         [M]
documentation/features/intelligence/planner-confirmation/{spec.md,evaluation.md,design/} [N]
```

Dependency direction: `IntelligenceRouter` → `ConfirmPlanningController` → `ConfirmPlanningUseCase`
→ `PlannedGoalProvider` (Shared port) ← `LearningPlannedGoalProvider` → `CreatePlannedGoalUseCase`
→ `LearningDatabase`. Only `app.py` knows both modules (`tach` keeps Intelligence and Learning on
Shared alone). On the web, `PlannerPage` → `PlanningProposalReview`; the page owns the mutation
and the navigation, the review owns the key, the labels and the frozen state.

## Runtime Flow

Review → `Criar objetivo` → review validation → `handleCreateGoal({ confirmationKey, title,
description })` → `goalCreation = creating` (review frozen) → `confirmPlanningServer` →
`POST …/confirm` → `ConfirmPlanningUseCase` (owner, `proposal`, idle) →
`LearningPlannedGoalProvider.create` → one Learning transaction (lock → replay check →
catalogs → Goal + experiences + progresses + confirmation row) → planning removed → `200`
→ Home goals invalidated, planning query dropped, navigation to the Goal page. `409`/`400`
→ `failed` with the reason, review unfrozen, `Tentar criar objetivo` replays the key.
Transport failure → `uncertain`, review frozen, `Verificar resultado` replays the key; the
backend answers the stored Goal (`replayed: true`) even after the planning expired.

# Verification Contract

## Shared setup

Server: Testcontainers Postgres + Redis (`TESTCONTAINERS_RYUK_DISABLED=true` locally,
`-p no:tach`), curriculum seed (`build_development_seed`) for the HTTP scenarios. Web: jsdom
Vitest with the owning hooks mocked for widgets; Playwright with the shared `authenticatedPage`
and `bff` fixtures, local FastAPI 7777 and Vite 7000 reused.

## Automated

### CI-01 — Learning and Intelligence use cases under pytest

**Criteria:** CA-01, CA-03 … CA-07

**Proof:** `apps/server/tests/learning/core/use_cases/test_create_planned_goal_use_case.py`,
`apps/server/tests/intelligence/core/use_cases/test_confirm_planning_use_case.py`.

### CI-02 — Confirm route against Postgres and Redis

**Criteria:** CA-01 … CA-03, CA-05 … CA-07

**Proof:** `apps/server/tests/intelligence/server/controllers/test_confirm_planning_controller.py`
(seeded curriculum, Learning rows and the Redis planning asserted).

### CI-03 — Review and page states under Vitest

**Criteria:** CA-08 … CA-11

**Proof:** `planner-page/tests/{planner-page.test.tsx,use-planner-page.test.ts}`,
`planning-proposal-review/tests/*`, `hooks/tests/planning-server-functions.test.ts`.

### CI-04 — Browser suite with mocked transport

**Criteria:** CA-08 … CA-10, CA-12

**Proof:** `apps/web/tests/intelligence/planner-page.test.ts` (confirmation scenarios and the
four frame captures).

```bash
cd apps/web && pnpm test:integration tests/intelligence/planner-page.test.ts --grep confirmation
```

### CI-05 — Applicable baseline checks

Server: `uv run ruff format --check`, `uv run ruff check`, `uv run basedpyright`,
`uv run poe check:architecture`. Web: `pnpm check:types`, `check:lint`, `check:architecture`,
scoped coverage run with the changed-file gate.

## Manual

### VM-01 — Confirmation against the real backend

Needs `OPENROUTER_API_KEY` to obtain a real proposal; the confirm route itself is exercised
by CI-02 against the real Learning tables.

## Visual

### VM-02 — Frames versus implementation

Four frames (`BswO3`, `qJw1C`, `FxmF8`, `n8OPLr`) exported at scale 1 and compared with the
captures of CI-04 at 1440 and 390 wide; deviations listed in `design/handoff.md`.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| Shifu PRD Intelligence (Confluence 83099649, v4) | RP-10, RP-11, RP-12; JN-13 | Confirmation, idempotent repeat, uncertain result, failure keeps the proposal, navigation | Unchanged intent |
| Shifu PRD Learning (Confluence 83066881, v24) | RP-02, RP-03, RP-05, RP-25 | Learning validates and creates as one result; justifications read-only | Unchanged intent |
| `documentation/modules.md` (Intelligence → Learning confirmed proposals) | Boundary | Learning validates, executes and returns results for recovery of the same confirmation | Confirmed by the Shared port and the confirmation record |
| `documentation/design.md` T16 | Review actions | T16 still lists `Ajustar / Confirmar / Cancelar`; the implemented labels follow PRD v4 (`Reiniciar planejamento`, `Criar objetivo`) | Deviation recorded; no edit to design.md in this delivery |
| `../planner-review/spec.md` | `onCreateGoal` boundary and the neutral notice | Revision 3: the notice is replaced by the real creation states | Updated |
| `../planner-goal-flow/spec.md` | Planning API | Revision 4: the confirm route and the removal of the planning on success | Updated |
| `../../learning/goal-details/spec.md` | Justification display | Unchanged; planned Goals now carry `inclusion_reason` | Confirmed |

Decisions: `D1` the confirmation key is a UUID generated once per review (per generation)
on the client and persisted by Learning, so retries, double clicks and recoveries are the
same confirmation; `D2` the hand-over is a Shared port implemented by Learning and bound in
`app.py`, keeping Intelligence and Learning apart under `tach`; `D3` the creation runs
synchronously inside the confirm request (the learner waits for the result, the Learning
transaction is local); `D4` success removes the temporary planning, recovery reads Learning's
record; `D5` the uncertain state has its own copy and reuses the processing notice with a
neutral tone, since the frames only draw creating and failure; `D6` the confirm response is
always `200` with `replayed`; `D7` the controller bounds title and description to the Learning
columns (240 / 4000) and Learning validates again; `D8` a `404` on confirm refreshes the
planning instead of showing a failure, because the proposal cannot be kept when the planning
is gone and no Goal exists.

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-20 | Initial contract | SHIFU-95 ticket, PRD Intelligence v4, PRD Learning v24, four approved frames |
