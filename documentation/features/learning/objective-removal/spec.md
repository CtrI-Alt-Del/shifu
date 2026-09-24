---
title: Remoção atômica de Objetivo e suas experiências
status: ready
revision: 1
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-67
scope:
  - apps/server/src/shifu/learning
  - apps/server/rest-client/learning
  - apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page
  - apps/web/src/ui/shared/widgets/components/confirmation-dialog
  - apps/web/src/ui/shadcn
  - apps/web/src/ui/shared/widgets/components/icon
  - apps/web/src/rest/services/learning-service.ts
  - apps/web/tests/learning/goal-detail-placeholder-page.test.ts
last_updated_at: 2026-09-23
---

# 1. Context and scope

## Objective and source

Deliver SHIFU-67: let the authenticated owner permanently and atomically remove
one Objetivo (Goal) and every Habilidade experience it contains, in one
explicit action, with no partial result possible. Owning module: **Learning**.
Source: Jira `SHIFU-67` ("Implementar remoção atômica de Objetivo e suas
experiências"), tracing to the canonical PRD requirement `RP-22` and journey
`JN-15` in [Shifu — PRD — Learning](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning)
(content ID `83066881`; Jira records page version `6`; re-read at authoring
time on 2026-09-23, page `lastModified` "cerca de 2 horas atrás" relative to
that read — the retrieval tool used for this Spec does not expose a numeric
page-version field, so freshness is evidenced by direct full-page re-read
rather than a cited version number. `RP-22`/`JN-15` content was re-verified
against this fresh read and is unchanged in substance from Jira's traceability
section). Delivery mode: **complete** — the change spans REST, a new use case,
a new cross-feature-reusable UI primitive (`ConfirmationDialog`), a new shadcn
dependency, concurrency/duplicate-submit guarding, and an explicit persistence
race-protection guarantee, so the independent Spec Reviewer (Section 6) is
mandatory.

## Current behavior and product gap

`GET /learning/goals` (`ListHomeGoalsUseCase`) lists a user's Goals and
`POST /learning/goals/{goal_id}/skills` (`AddSkillToGoalUseCase`) adds a
Habilidade, but no use case, route, or UI exists to remove a Goal today.
`/learning/goals/$goalId` renders `GoalDetailPlaceholderPage`
(`apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx`),
a static placeholder with no data-fetching, no actions, and no colocated
behavior hook. The persistence mechanics for atomic cascade removal already
exist (`GoalsRepository.remove()`, and `ON DELETE CASCADE` declared end-to-end
on every child table — see Section 3), but nothing in the application layers
calls them for a user-initiated Goal deletion.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Trigger | A "Remover Objetivo" destructive action added to the existing `GoalDetailPlaceholderPage` at `/learning/goals/$goalId` | Building the real Objetivo detail page (Habilidade list/graph, editing, T12) — a separate, already-excluded delivery; the Home grid `ObjectiveCard` gains no menu |
| Removal | Goal + every associated Habilidade experience (diagnostic, progress/domain, released content, attempts, evaluations, inclusion justification, final summary) removed as one atomic result, in any Goal/experience state, including with a pending or failed evaluation | Individual Habilidade removal (`RP-21`/`JN-14`, Jira `SHIFU-36`, currently blocked by this ticket); Goal creation or editing; restoring a removed Goal (PRD explicitly excludes restoration) |
| Confirmation | A destructive confirmation dialog that explains scope and irreversibility, requires no typed Goal name | A password-gated "modal destrutivo" like account deletion (T09) — `RP-22` and Jira both state no name/typing requirement |
| Race protection | A persistence-level guarantee (existing `ON DELETE CASCADE`) plus one test proving a late write against removed data fails instead of recreating it | Building or altering the (currently nonexistent) asynchronous evaluation pipeline itself |
| Navigation | Redirect to `/` and an updated Goal list after success | Any other post-removal screen |

| Source requirement | Delivery | Notes |
| --- | --- | --- |
| `RP-22` — Remover um Objetivo e Todas as suas Experiências | full | Every business rule in `RP-22` is covered by `RF-01`–`RF-07` below |
| `JN-15` — Remover um Objetivo Inteiro | full | The journey's four steps (request → explain scope → confirm → atomic removal, others intact) map to `RF-03`, `RF-04`, `RF-07` |

## Product decisions and assumptions

- The trigger lives on the existing placeholder page rather than the Home
  grid card, matching the route Jira names and `documentation/design.md` T12's
  stated menu location, without building the rest of that page (user-accepted
  during clarification).
- No Pencil MCP tool was available in this session to inspect design node
  `kZHN8` (`design/shifu.pen`). Per explicit user acceptance, this Spec relies
  on `documentation/design.md` §3.3 (destructive-action styling) and T14's
  textual description instead of a captured screenshot; capturing and visually
  verifying `kZHN8` is recorded as a required, deferred step before this
  ships (Section 3, Design Contract) rather than a blocker for `ready`.
- No asynchronous evaluation/diagnostic pipeline exists anywhere in the
  repository yet (`learning/messaging/{jobs,brokers}` are empty stubs; no use
  case publishes `ActivitySubmissionRequestedEvent`/`ActivityEvaluatedEvent`).
  `RP-22`'s "resultados que chegarem depois não podem recriar dados removidos"
  is therefore validated as a structural persistence guarantee (existing
  `ON DELETE CASCADE` FK constraints reject a write against a removed parent)
  rather than against a live pipeline (user-accepted during clarification).
  Building that pipeline is explicitly out of scope.
- "Outros Objetivos e o Currículo permanecem intactos" (`RP-22`) is enforced
  by construction for Curriculum: `RemoveGoalUseCase` never imports a
  Curriculum repository or model (Learning does not import another business
  module per `documentation/modules.md`), so no Curriculum-side test is
  needed. The Learning-side half (other Goals untouched) is covered by
  `CA-15`.
- Removing a Goal's last Habilidade must not remove the Goal automatically
  (`RP-22`); since individual Habilidade removal is not implemented by any
  ticket yet, this is a design constraint on `RemoveGoalUseCase`'s
  surface (it only ever removes a whole Goal, never a single experience) and
  is not a separately testable scenario in this delivery.

# 2. Implementation Contract

| ID | RP/JN coverage | Required behavior |
| --- | --- | --- |
| RF-01 | RP-22 | Only the authenticated account that owns the Goal may remove it. A Goal that does not exist, or belongs to another account, is rejected without revealing which case occurred. |
| RF-02 | RP-22 | Removal is permitted for an empty Goal and for a Goal containing Habilidade experiences in any status (`NOT_STARTED`, `DIAGNOSING`, `LEARNING`, `COMPLETED`), including when an experience has a pending or failed evaluation. |
| RF-03 | RP-22, JN-15 | Before removal, the user sees a confirmation that explicitly states every Habilidade experience of that Goal will be removed and that the action is permanent. The confirmation never requires typing the Goal's title. |
| RF-04 | RP-22, JN-15 | Confirming removes the Goal and every associated Habilidade experience (diagnostic, progress/domain, released content, attempts, evaluations, inclusion justification, final summary) as one atomic result. A failure leaves the Goal and all experiences fully intact, and the confirmation stays open with a retry path. |
| RF-05 | RP-22 | While removal is in progress, a duplicate confirmation is blocked, and success is never communicated before the atomic operation actually completes. |
| RF-06 | RP-22 | A result that completes after the Goal was removed cannot recreate the Goal or any of its experiences. |
| RF-07 | RP-22 | Other Goals belonging to the same account, Curriculum content, and Gamification reward history remain unaffected by the removal. |
| RF-08 | RP-22, JN-15 | After success, the user is taken to `/`, and the removed Goal no longer appears in the user's Goal list. |
| RF-09 | RP-22 (regressão de acessibilidade transversal, `documentation/design.md` §8–9) | The trigger and confirmation work on desktop and mobile viewports, with visible keyboard focus and complete keyboard operability. |

| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Owner can remove their Goal | An authenticated account owns Goal `G` | It requests removal of `G` | `G` and its experiences are deleted; `204 No Content` | `test_remove_goal_controller.py::test_should_remove_goal_when_owned_by_account` |
| CA-02 | RF-01 | Cross-account isolation | Goal `G` belongs to account `A` | Account `B` requests removal of `G` | `404`; `G` and its rows remain fully intact | `test_remove_goal_controller.py::test_should_return_404_and_preserve_goal_when_requested_by_another_account` |
| CA-03 | RF-01 | Non-existent Goal | Goal id does not exist | Removal is requested | `404`, same response shape as CA-02 (no existence disclosure) | `test_remove_goal_controller.py::test_should_return_404_when_goal_does_not_exist` |
| CA-04 | RF-01 | Unauthenticated rejection | No valid session | Removal is requested | `401`; no deletion occurs | `test_remove_goal_controller.py::test_should_return_401_when_unauthenticated` |
| CA-05 | RF-02 | Empty Goal removable | Goal `G` has zero Habilidade experiences | Owner confirms removal | `G` is deleted | `test_remove_goal_use_case.py::test_should_remove_goal_when_owned_by_account`; `test_remove_goal_controller.py::test_should_remove_goal_when_owned_by_account` |
| CA-06 | RF-02 | Any-status Goal removable | Goal `G` has experiences in `NOT_STARTED`, `DIAGNOSING`, `LEARNING`, and `COMPLETED` | Owner confirms removal | `G` and every `learning_skill_experiences`/`learning_competency_progresses`/`learning_activity_attempts`/`learning_activity_evaluations` row scoped to `G` are gone | `test_remove_goal_controller.py::test_should_cascade_remove_every_skill_experience_and_learning_data_regardless_of_status` |
| CA-07 | RF-02 | Removable with pending/failed evaluation | A skill experience under `G` has an `ActivityEvaluation` with `status=PENDING` or `FAILED` | Owner confirms removal | Removal still succeeds; the evaluation row is gone (cascaded through its attempt) | `test_remove_goal_controller.py::test_should_remove_goal_with_pending_or_failed_evaluation` |
| CA-08 | RF-03 | Confirmation explains scope | The Goal-detail placeholder page is open | User activates "Remover Objetivo" | A dialog opens stating every Habilidade experience of the Goal will be permanently removed; no name/text input is present | `confirmation-dialog.test.tsx::renders the destructive scope copy without a confirmation input`; `goal-detail-placeholder-page.test.tsx::opens the confirmation dialog when the trigger is activated` |
| CA-09 | RF-04 | Cancel preserves everything | The confirmation dialog is open | User cancels | Dialog closes; no HTTP request was sent; Goal and experiences remain | `goal-detail-placeholder-page.test.tsx::closes the dialog and sends no request when cancelled`; `use-goal-detail-placeholder-page.test.ts` |
| CA-10 | RF-04 | Confirm removes atomically | The confirmation dialog is open for Goal `G` with experiences | User confirms | `DELETE /learning/goals/{G}` succeeds; `G` and every child row are gone in one transaction | `test_remove_goal_controller.py::test_should_remove_goal_when_owned_by_account` (asserts zero rows across all four child tables after) |
| CA-11 | RF-04 | Failure preserves and offers retry | The confirmation dialog is open; the DELETE request will fail | User confirms | Goal and every experience remain unchanged; dialog stays open showing an error and a retry action | `goal-detail-placeholder-page.test.tsx::keeps the dialog open with a retry action when removal fails`; `goal-detail-placeholder-page.test.ts` (route suite, mocked 500) |
| CA-12 | RF-05 | Duplicate-submit blocked | A removal request is in flight | User activates confirm again | The confirm control is disabled; only one `DELETE` request is observed | `goal-detail-placeholder-page.test.tsx::disables the confirm control while removal is pending`; route suite |
| CA-13 | RF-05 | No premature success | A removal request is in flight | — | No success/redirect happens until the response resolves | `use-goal-detail-placeholder-page.test.ts::navigates only after the delete mutation resolves` |
| CA-14 | RF-06 | Late write rejected after removal | Goal `G` (with a skill experience `S`) was already removed | A direct repository write is attempted against `S`'s id (e.g. a new `ActivityAttempt`) | The write fails with a foreign-key violation; no row referencing `S` or `G` is recreated | Disposable-environment evidence (see note below the acceptance-coverage table) |
| CA-15 | RF-07 | Other Goals unaffected | Account has Goals `G1` (removed) and `G2` | `G1` is removed | `G2` and its experiences are byte-for-byte unchanged | `test_remove_goal_controller.py::test_should_leave_other_goals_of_the_same_account_untouched` |
| CA-16 | RF-08 | Redirect and list update | Removal of `G` succeeds | — | Browser navigates to `/`; a subsequent Goal-list fetch no longer includes `G` | `goal-detail-placeholder-page.test.ts::redirects to the dashboard and removes the goal from the list after success` (route suite) |
| CA-17 | RF-09 | Keyboard operability | The placeholder page is focused | User tabs to the trigger, activates it with Enter/Space, tabs through the dialog, activates Cancel/Confirm with the keyboard | Every control is reachable and operable by keyboard with a visible focus ring | `goal-detail-placeholder-page.test.ts::supports full keyboard operation of the trigger and dialog` (route suite) |
| CA-18 | RF-09 | Responsive layout | Trigger and dialog rendered at a 375px viewport | — | Trigger and dialog remain fully visible and usable, matching `documentation/design.md` §3.6/§9 | `goal-detail-placeholder-page.test.ts::renders the trigger and dialog usably at a narrow viewport` (route suite) |

## Design Contract

Design authority: `documentation/features/learning/objective-removal/design/handoff.md`
(this delivery's first design artifact; no PNG references exist yet — see
below). Canonical Pencil node: `design/shifu.pen` / `kZHN8` ("confirmação da
remoção do Objetivo" per Jira traceability).

No Pencil MCP tool was reachable in this authoring session, so `kZHN8` was
**not** visually inspected — this is a recorded, user-accepted gap, not a
silent omission. The interim implementation authority is:

1. `documentation/design.md` §3.3 ("Como resolver ação destrutiva"): the
   destructive control is never filled/solid, uses a neutral surface with a
   `--selo-text` label and border plus an icon, and always lives inside a
   confirmation.
2. `documentation/design.md` §6.2 T14: "Remover Objetivo: deixa claro que
   **todas** as experiências de Habilidade dele serão removidas"; no typed
   confirmation is described (unlike T09's password-gated destructive modal).
3. `documentation/rules/ui-layer-rules.md` "Dialog header structure": every
   application dialog, including destructive confirmations, uses a semantic
   icon tile at the left of the title/description block, an isolated
   top-right close action, and a header separator.

Before this ships, `kZHN8` must be opened in Pencil, one shared-workspace
screenshot saved under `design/references/`, visually inspected (not only
OCR'd), and reconciled against the inventory below; any divergence updates
`design/handoff.md` and, if it changes observable behavior, this Spec.

| Reference | Route/surface/state | Viewport | Implementation surface | Criteria mapping | Validation target |
| --- | --- | --- | --- | --- | --- |
| Remover Objetivo — trigger | `/learning/goals/$goalId`, default state | 1440×900 (desktop), 375×812 (mobile) | `GoalDetailPlaceholderPage` | CA-08, CA-17, CA-18 | VM-01 |
| Remover Objetivo — confirmation | Dialog opened from the trigger | 520 (modal), both viewports | `ConfirmationDialog` (`ui/shared/widgets/components/confirmation-dialog`) | CA-08, CA-09, CA-17, CA-18 | VM-01, VM-02 |
| Remover Objetivo — pending/error | Dialog after Confirm, in flight / after a failed attempt | 520 (modal) | `ConfirmationDialog` | CA-11, CA-12 | VM-02 |

# 3. Technical Contract

## Current technical state

| Evidence | Current responsibility | Gap |
| --- | --- | --- |
| `apps/server/src/shifu/learning/core/interfaces/goals_repository.py:GoalsRepository.remove` | Deletes one `Goal` row by id | None — reusable as-is |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/goals_repository.py:SqlalchemyGoalsRepository.remove` | Executes `DELETE FROM learning_goals WHERE id = :id` | None — reusable as-is |
| `apps/server/src/shifu/learning/database/sqlalchemy/models/{skill_experience,competency_progress,activity_attempt,activity_evaluation}_model.py` | Each declares `ForeignKey(..., ondelete='CASCADE')` to its parent, enforced by PostgreSQL (confirmed in the same models and in migration `a25a7142d3ff`) | None — a single `DELETE` on `learning_goals` already cascades through all four child tables |
| `apps/server/src/shifu/learning/core/interfaces/learning_database.py:LearningDatabase.transaction` | Sole transaction owner: commits only on normal exit, rolls back on any exception, shared session across all five repositories | None — reusable as-is for atomicity |
| `apps/server/src/shifu/learning/core/use_cases/*` (4 files) | No Goal-removal use case exists | Missing: `RemoveGoalUseCase` |
| `apps/server/src/shifu/learning/rest/{router.py,controllers/*}` | No `DELETE /goals/{goal_id}` route | Missing: `RemoveGoalController` + router registration |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx` | Static placeholder, no hook, no actions | Missing: trigger, colocated behavior hook, dialog wiring |
| `apps/web/src/ui/shadcn/` (`button.tsx`, `input.tsx`, `label.tsx`, `textarea.tsx`) | No dialog primitive; `Button` has only `default`/`ghost` variants | Missing: `alert-dialog.tsx` primitive; `destructive` `Button` variant per `documentation/design.md` §3.3 |
| `apps/web/src/rest/services/learning-service.ts` | `getGoals`, `getCompetencyDetail`, `searchSkillCatalog`, `addSkillToGoal` | Missing: `deleteGoal` |
| `apps/server/rest-client/learning/learning.rest` | One `GET /learning/goals` request | Missing: a `DELETE /learning/goals/{goalId}` request |

## Solution and runtime flow

The Goal-detail page renders a destructive "Remover Objetivo" trigger. Its
colocated hook opens `ConfirmationDialog`; Confirm invokes the
`useDeleteGoalAction` mutation, which calls `LearningService.deleteGoal`
through the BFF `createServerFn`/Better Auth token pattern already used by
`useAddSkillToGoalAction`. The web layer never decides ownership; it only
surfaces the server's `404`/`401`/`5xx` outcome.

`RemoveGoalController` resolves the authenticated account and the module
database, then calls `RemoveGoalUseCase.execute(account_id, goal_id)` and
returns `Response(status_code=204)`, mirroring `MainPageEnteredController`'s
explicit `response_model=None` shape rather than a bare-`None` return.
Inside `learning_database.transaction()`, the use case loads the Goal,
raises `GoalNotFoundError` when it is missing or owned by another account
(mirroring `AddSkillToGoalUseCase`'s identical check), and otherwise calls
`repos.goals.remove(goal)`. The transaction commits exactly once; PostgreSQL's
`ON DELETE CASCADE` chain removes every `learning_skill_experiences`,
`learning_competency_progresses`, `learning_activity_attempts`, and
`learning_activity_evaluations` row scoped to that Goal as part of the same
statement's cascade, inside the same commit — this is the atomicity and
all-or-nothing guarantee `RF-04` requires. `GoalNotFoundError` is already
registered with `AppErrorHandler` as a `NotFoundError` → `404` mapping, so no
new error-handler wiring is needed.

On the client, a successful `204` invalidates the `['learning', 'home-goals']`
query key using `useQueryClient().invalidateQueries()`. No other mutation in
the repository currently performs cache invalidation (`useQueryClient` has no
prior call site), so this is the first concrete application of
`architecture.md`'s "action hooks invalidate the smallest stable query-key
prefix" guidance rather than a reused pattern. It then navigates to `/` via
`useNavigation().navigateTo('root')`. A failure leaves the dialog open,
surfaces the error, and re-enables Confirm for retry — no client-side
optimistic removal occurs, satisfying `RF-05`'s "no premature success".

`RF-06` (late results cannot recreate removed data) is a structural guarantee
rather than a new code path: because every child table's foreign key is
`ON DELETE CASCADE` and there is no orphan-tolerant insert path anywhere in
the module, any write that references an id that no longer exists fails with
a PostgreSQL foreign-key violation, surfaced as an unhandled `IntegrityError`
at whatever (currently nonexistent) boundary attempts it. `CA-14` proves this
directly against the real database as disposable-environment evidence during
Evaluation (Section 4) rather than asserting it only by inspection, since no
HTTP boundary in this delivery can observe it.

## Affected layer contracts

### Use cases

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/core/use_cases/remove_goal_use_case.py` | Create | `class RemoveGoalUseCase: def __init__(self, learning_database: LearningDatabase); def execute(self, account_id: str, goal_id: str) -> None` | Opens one `learning_database.transaction()`; raises `GoalNotFoundError` when the Goal is missing or `goal.account_id != account_id`; otherwise calls `repos.goals.remove(goal)`. No other repository call — cascade handles child rows. | Consumed by `RemoveGoalController` | `apps/server/tests/learning/core/use_cases/test_remove_goal_use_case.py` |
| `apps/server/src/shifu/learning/core/use_cases/__init__.py` | Modify | Re-export `RemoveGoalUseCase` | Barrel re-export only, no new behavior | — | Covered by the use-case's own test import |

### REST

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/learning/rest/controllers/remove_goal_controller.py` | Create | `class RemoveGoalController: @staticmethod def handle(router: APIRouter) -> None` registering `router.delete('/goals/{goal_id}', response_model=None, status_code=status.HTTP_204_NO_CONTENT)`, handler returns `Response(status_code=status.HTTP_204_NO_CONTENT)` | Mirrors the repository's only existing body-less-response precedent, `MainPageEnteredController` (`response_model=None` declared explicitly, `fastapi.Response` return type, not a bare `None`); depends on `SharedPipe.get_authenticated_user` and `LearningPipe.get_database`; constructs `RemoveGoalUseCase` and calls `.execute(user.account_id, goal_id)`; expected failures (`GoalNotFoundError`) propagate to the global `AppErrorHandler`, already mapped to `404` | Registered by `LearningRouter` | `apps/server/tests/learning/server/controllers/test_remove_goal_controller.py` |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | Add `RemoveGoalController.handle(router)` inside `LearningRouter.register()` | Registration only | — | Exercised by the controller test above via `FastAPIApp.register()` |
| `apps/server/rest-client/learning/learning.rest` | Modify | Add `@goalId` variable and a `### Remove goal` / `DELETE {{baseUrl}}/learning/goals/{{goalId}}` labeled request with the `Authorization` header | REST-client parity for the new route group member | — | Manual artifact, no automated test |

### UI

Widget hierarchy for the changed surface:

| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| `GoalDetailPlaceholderPage` | Page | `/learning/goals/$goalId` route | `ConfirmationDialog` | `GoalDetailPlaceholderPageProps { goalId: string }` (unchanged) | Colocated `use-goal-detail-placeholder-page.ts` |
| `ConfirmationDialog` | Component (shared) | `GoalDetailPlaceholderPage` (this delivery); reusable by future destructive flows (e.g. SHIFU-36) | shadcn `AlertDialog*` primitives | `ConfirmationDialogProps { title, description, confirmLabel, cancelLabel, icon: IconName, isOpen, isSubmitting, error?, onConfirm, onCancel }` | None — pure prop-to-markup renderer, no local state |
| `AlertDialog` / `AlertDialogContent` / `AlertDialogHeader` / `AlertDialogTitle` / `AlertDialogDescription` / `AlertDialogFooter` / `AlertDialogAction` / `AlertDialogCancel` | shadcn primitives | `ui/shadcn` | Radix `@radix-ui/react-alert-dialog` | Standard shadcn generated-primitive contract, Shifu token-mapped | Radix (controlled `open`/`onOpenChange`) |

Expected file tree for the changed UI surface:

```text
apps/web/package.json                                    Modify
pnpm-lock.yaml                                            Modify

apps/web/src/ui/shadcn/
├── alert-dialog.tsx                                    Create
└── button.tsx                                           Modify

apps/web/src/ui/shared/widgets/components/
├── icon/index.tsx                                       Modify
└── confirmation-dialog/
    ├── index.tsx                                        Create
    └── tests/
        └── confirmation-dialog.test.tsx                 Create

apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/
├── index.tsx                                             Modify
├── use-goal-detail-placeholder-page.ts                   Create
├── use-delete-goal-action.ts                             Create
└── tests/
    ├── goal-detail-placeholder-page.test.tsx              Create
    └── use-goal-detail-placeholder-page.test.ts           Create
```

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/web/package.json`, `pnpm-lock.yaml` | Modify | Add `@radix-ui/react-alert-dialog` (`pnpm --filter web add @radix-ui/react-alert-dialog`, run from the repository root) | New runtime dependency for the shadcn `AlertDialog` primitive | Consumed by `ui/shadcn/alert-dialog.tsx` | Generated lockfile diff, committed alongside the source change |
| `apps/web/src/ui/shadcn/alert-dialog.tsx` | Create | Generated shadcn `AlertDialog` primitive wrapping `@radix-ui/react-alert-dialog`, re-tokenized to Shifu's `--surface`/`--raised`/`--control-border`/`--selo-*` CSS variables instead of default shadcn colors | Controlled via `open`/`onOpenChange`; blocks outside-click/overlay dismissal (destructive-dialog semantics); `Escape` triggers Cancel | Consumed by `ConfirmationDialog` only | Covered indirectly through `confirmation-dialog.test.tsx` |
| `apps/web/src/ui/shadcn/button.tsx` | Modify | Add `'destructive'` to `ButtonProps['variant']` union; neutral surface, `--selo-text` label and border, per §3.3 | No breaking change to `'default'`/`'ghost'` | Consumed by the new trigger | Covered through `goal-detail-placeholder-page.test.tsx` |
| `apps/web/src/ui/shared/widgets/components/icon/index.tsx` | Modify | Add `'trash-2'` (`Trash2`) and `'triangle-alert'` (`TriangleAlert`) to `IconName`/`ICON_COMPONENTS` | No change to existing icon names | Consumed by the trigger and `ConfirmationDialog` | Covered through consuming widget tests |
| `apps/web/src/ui/shared/widgets/components/confirmation-dialog/index.tsx` | Create | `export type ConfirmationDialogProps = { title: string; description: string; confirmLabel: string; cancelLabel: string; icon: IconName; isOpen: boolean; isSubmitting: boolean; error?: string \| null; onConfirm: () => void; onCancel: () => void }`; `export const ConfirmationDialog = (props: ConfirmationDialogProps) => ReactNode` | Implements the mandatory "Dialog header structure" (icon tile, title+description, isolated top-right close mapped to `onCancel`, separator); disables both actions while `isSubmitting`; renders `error` inline when present | Consumed by `GoalDetailPlaceholderPage` now; intended reuse by a future Habilidade-removal dialog | `apps/web/src/ui/shared/widgets/components/confirmation-dialog/tests/confirmation-dialog.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/index.tsx` | Modify | Add the destructive trigger `Button` and `ConfirmationDialog`, consuming `useGoalDetailPlaceholderPage` | Existing placeholder copy/markup unchanged; component stays an exported `const` | Route `learning/goals/$goalId/index.tsx` (unchanged — still passes only `goalId`) | `tests/goal-detail-placeholder-page.test.tsx` |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/use-goal-detail-placeholder-page.ts` | Create | `export function useGoalDetailPlaceholderPage(goalId: string)` returning `{ isConfirmDialogOpen, isDeletingGoal, deleteGoalError, handleOpenConfirmDialog, handleCancelRemoval, handleConfirmRemoval }` | Owns dialog-open state; on confirm success, invalidates `['learning', 'home-goals']` via `useQueryClient()` and calls `navigateTo('root')`; on failure, dialog stays open with the surfaced error | Consumes `useDeleteGoalAction`, `useNavigation`, `useQueryClient` | `tests/use-goal-detail-placeholder-page.test.ts` |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/use-delete-goal-action.ts` | Create | `export const useDeleteGoalAction = (goalId: string) => { deleteGoal, isDeletingGoal, deleteGoalError, resetDeleteGoal }`, `createServerFn`-backed exactly like `use-add-skill-to-goal-action.ts` | Duplicate-submit guard via TanStack Query `isPending`; no dedicated test file (query/action-hook exemption) | `LearningService.deleteGoal` | Covered through the page hook and route suite |
| `apps/web/src/rest/services/learning-service.ts` | Modify | Add `deleteGoal(accessToken: string, goalId: string): Promise<void>` calling `restClient.delete<void>('/learning/goals/' + goalId, undefined, { headers: { Authorization: 'Bearer ' + accessToken } })`, checking `response.isFailure` | No new response DTO — `204` has no body | `useDeleteGoalAction` | Covered through consuming widget/route tests (REST services are untested directly per Rule) |
| `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` | Modify | Extend the existing Playwright suite (currently only the anonymous-redirect and static-render cases) with the removal flow | Add cases per CA-08–CA-18 | — | Playwright, mocked transport |

## Technical decisions

| Decision | Chosen approach | Alternative considered | Reason | Accepted trade-off |
| --- | --- | --- | --- | --- |
| Cascade mechanism | Rely on the existing `ON DELETE CASCADE` chain; the use case only calls `repos.goals.remove(goal)` | Explicitly delete each child table from the use case before removing the Goal | The constraint already guarantees atomicity and completeness at the database level; explicit deletes would duplicate that guarantee with more code and more failure surface for no added correctness | Child-row deletion is not independently observable from the use case's own unit test; proven instead through the controller integration test (real Postgres) |
| Delete response shape | `204 No Content`, no response body, `response_model=None` declared explicitly, handler returns `fastapi.Response(status_code=204)` | Return a body echoing removed-experience counts | `RP-22`/Jira do not require reporting counts; `MainPageEnteredController` is the repository's one existing body-less-response precedent and uses this exact explicit-`response_model=None`-plus-`Response`-return shape, so this Spec reuses it instead of inventing a new idiom | A future feature that wants to show "N Habilidades removidas" after the fact would need a new endpoint or response shape |
| Confirmation dialog primitive | Add `ui/shadcn/alert-dialog.tsx` (`@radix-ui/react-alert-dialog`) and compose `ConfirmationDialog` on top of it | Hand-rolled raw-`div` dialog matching the existing `AddSkillFoundationsDialog` pattern | `documentation/rules/ui-layer-rules.md` requires extending the shared `ui/shadcn` primitive before a feature-local equivalent when no shadcn component exists; `AddSkillFoundationsDialog` predates/diverges from that rule (uses `bg-white`/gray literals, not Shifu tokens) and is not a pattern to extend | New dependency (`@radix-ui/react-alert-dialog`) added to `apps/web/package.json`/`pnpm-lock.yaml`; `AddSkillFoundationsDialog` itself is left as-is (out of scope to refactor) |
| Action-hook placement | Colocate `use-delete-goal-action.ts` inside `goal-detail-placeholder-page/`, not under `ui/learning/hooks/` | Mirror `use-add-skill-to-goal-action.ts`'s placement under `ui/learning/hooks/` | `documentation/rules/ui-layer-rules.md`: "Query hooks, action hooks and query keys that exist only for that page stay within the same page boundary"; this action hook has exactly one consumer today | If a second page later needs Goal deletion, the hook is promoted to `ui/learning/hooks/` per the same Rule's promotion clause |
| `ConfirmationDialog` ownership boundary | `ui/shared/widgets/components/confirmation-dialog` (module-neutral) | `ui/learning/widgets/components/confirmation-dialog` (Learning-owned) | The widget has no Learning-specific content (all copy passed as props) and is explicitly intended for reuse by SHIFU-36's Habilidade-removal confirmation; `architecture.md`'s Shared UI boundary test is "a stable, module-neutral responsibility" — a content-based test independent of how many features currently consume it, which is deliberately a different test from the *hook*-placement decision above (hooks follow the Rule's explicit "stays within the same page boundary until a second consumer exists" wording, which is about behavior/orchestration ownership, not component reusability). SHIFU-36 does not exist yet, so this placement is confirmed as the Orchestrator's judgment call, not a fact already proven by a second consumer. | None — first consumer is still a Learning page |

# 4. Validation Contract

| Test file | Test type | Target | Coverage goal |
| --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_remove_goal_use_case.py` | unit | `RemoveGoalUseCase` | Ownership check, not-found, repository call shape, no side effects on rejection |
| `apps/server/tests/learning/server/controllers/test_remove_goal_controller.py` | integration (FastAPI `TestClient` + PostgreSQL Testcontainer) | `DELETE /learning/goals/{goal_id}` | Full HTTP contract, real cascade deletion, isolation |
| `apps/web/src/ui/shared/widgets/components/confirmation-dialog/tests/confirmation-dialog.test.tsx` | component | `ConfirmationDialog` | Open/closed rendering, scope copy, pending/error/disabled states, no outside-dismiss |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/tests/goal-detail-placeholder-page.test.tsx` | component | `GoalDetailPlaceholderPage` | Trigger → dialog wiring, mocked hook's full state matrix |
| `apps/web/src/ui/learning/widgets/pages/goal-detail-placeholder-page/tests/use-goal-detail-placeholder-page.test.ts` | hook | `useGoalDetailPlaceholderPage` | Open/cancel/confirm orchestration, invalidate-then-navigate ordering, failure path |
| `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` | manual/Playwright route integration | `/learning/goals/$goalId` | Real route composition, REST contract, redirect, list update, keyboard, responsive |

| Test file | Test case | Description | Assertions |
| --- | --- | --- | --- |
| `test_remove_goal_use_case.py` | `test_should_remove_goal_when_owned_by_account` | Owner removes an owned Goal | `repos.goals.remove` called once with the loaded `Goal` |
| `test_remove_goal_use_case.py` | `test_should_raise_goal_not_found_error_when_goal_missing` | Goal id has no row | `pytest.raises(GoalNotFoundError)`; `remove` never called |
| `test_remove_goal_use_case.py` | `test_should_raise_goal_not_found_error_when_goal_belongs_to_another_account` | Goal exists, different `account_id` | `pytest.raises(GoalNotFoundError)`; `remove` never called |
| `test_remove_goal_controller.py` | `test_should_remove_goal_when_owned_by_account` | Seeded Goal + skill experience + progress + attempt + evaluation | `204`; all five tables' scoped rows are gone via a direct follow-up query |
| `test_remove_goal_controller.py` | `test_should_return_404_and_preserve_goal_when_requested_by_another_account` | Goal seeded for account `A`; request authenticated as `B` | `404`; a follow-up `GET` (or direct repository read) shows the Goal and its rows unchanged |
| `test_remove_goal_controller.py` | `test_should_return_404_when_goal_does_not_exist` | Random id | `404`, same response shape as the cross-account case |
| `test_remove_goal_controller.py` | `test_should_return_401_when_unauthenticated` | No bearer token | `401`; no deletion attempted |
| `test_remove_goal_controller.py` | `test_should_cascade_remove_every_skill_experience_and_learning_data_regardless_of_status` | Skill experiences seeded in all four `SkillExperienceStatus` values | `204`; zero rows remain in all four child tables for that Goal |
| `test_remove_goal_controller.py` | `test_should_remove_goal_with_pending_or_failed_evaluation` | A seeded `ActivityEvaluation` with `status=PENDING`/`FAILED` | `204`; the evaluation row is gone |
| `test_remove_goal_controller.py` | `test_should_leave_other_goals_of_the_same_account_untouched` | Account has `G1` and `G2`, both with experiences | `G1` removed | `G2` and its rows are byte-for-byte unchanged after |
| `confirmation-dialog.test.tsx` | `renders nothing when isOpen is false` | `isOpen=false` | Dialog content not in the document |
| `confirmation-dialog.test.tsx` | `renders the destructive scope copy without a confirmation input` | `isOpen=true` | Title/description visible; no text input rendered; `role='alertdialog'` |
| `confirmation-dialog.test.tsx` | `disables both actions while isSubmitting` | `isSubmitting=true` | Confirm and Cancel both `aria-disabled`/`disabled` |
| `confirmation-dialog.test.tsx` | `renders the error message when provided` | `error='...'` | Error text visible, `role='alert'` |
| `confirmation-dialog.test.tsx` | `calls onConfirm and onCancel from the respective actions` | Default props | Clicking Confirm/Cancel calls the matching prop once |
| `confirmation-dialog.test.tsx` | `does not close on overlay interaction` | `isOpen=true` | Simulated outside click does not invoke `onCancel` |
| `goal-detail-placeholder-page.test.tsx` | `opens the confirmation dialog when the trigger is activated` | Mocked hook, `isConfirmDialogOpen=false` initially | Clicking the trigger calls `handleOpenConfirmDialog` |
| `goal-detail-placeholder-page.test.tsx` | `renders the dialog open, pending, and error states from the hook` | Mocked hook returns each state | `ConfirmationDialog` receives the matching props |
| `goal-detail-placeholder-page.test.tsx` | `wires Cancel and Confirm to the hook handlers` | Mocked hook | Dialog callbacks invoke `handleCancelRemoval`/`handleConfirmRemoval` |
| `use-goal-detail-placeholder-page.test.ts` | `opens and closes the dialog` | — | `isConfirmDialogOpen` toggles via the exposed handlers |
| `use-goal-detail-placeholder-page.test.ts` | `invalidates the home-goals query and navigates to root on success` | Mocked `useDeleteGoalAction` resolving | `queryClient.invalidateQueries` called with `['learning', 'home-goals']`; `navigateTo('root')` called after |
| `use-goal-detail-placeholder-page.test.ts` | `keeps the dialog open and surfaces the error on failure` | Mocked `useDeleteGoalAction` rejecting | `isConfirmDialogOpen` stays `true`; `deleteGoalError` reflects the failure; navigation not called |
| `use-goal-detail-placeholder-page.test.ts` | `navigates only after the delete mutation resolves` | Mocked pending → resolved transition | No navigation call while pending; exactly one call after resolution |

| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01 | `test_remove_goal_controller.py::test_should_remove_goal_when_owned_by_account` | — | evaluation.md |
| CA-02 | `test_remove_goal_controller.py::test_should_return_404_and_preserve_goal_when_requested_by_another_account` | — | evaluation.md |
| CA-03 | `test_remove_goal_controller.py::test_should_return_404_when_goal_does_not_exist` | — | evaluation.md |
| CA-04 | `test_remove_goal_controller.py::test_should_return_401_when_unauthenticated` | — | evaluation.md |
| CA-05 | `test_remove_goal_use_case.py::test_should_remove_goal_when_owned_by_account`, controller equivalent | — | evaluation.md |
| CA-06 | `test_remove_goal_controller.py::test_should_cascade_remove_every_skill_experience_and_learning_data_regardless_of_status` | — | evaluation.md |
| CA-07 | `test_remove_goal_controller.py::test_should_remove_goal_with_pending_or_failed_evaluation` | — | evaluation.md |
| CA-08 | `confirmation-dialog.test.tsx`, `goal-detail-placeholder-page.test.tsx` | VM-01 | evaluation.md |
| CA-09 | `goal-detail-placeholder-page.test.tsx`, `use-goal-detail-placeholder-page.test.ts` | VM-01 | evaluation.md |
| CA-10 | `test_remove_goal_controller.py::test_should_remove_goal_when_owned_by_account` | VM-01 | evaluation.md |
| CA-11 | `goal-detail-placeholder-page.test.ts` (route suite, mocked 500) | VM-02 | evaluation.md |
| CA-12 | `goal-detail-placeholder-page.test.tsx`, route suite | VM-02 | evaluation.md |
| CA-13 | `use-goal-detail-placeholder-page.test.ts::navigates only after the delete mutation resolves` | — | evaluation.md |
| CA-14 | none (see disposable-environment note below) | — | evaluation.md |
| CA-15 | `test_remove_goal_controller.py::test_should_leave_other_goals_of_the_same_account_untouched` | — | evaluation.md |
| CA-16 | route suite (`redirects to the dashboard and removes the goal from the list after success`) | VM-01 | evaluation.md |
| CA-17 | route suite (`supports full keyboard operation...`) | VM-01, VM-02 | evaluation.md |
| CA-18 | route suite (`renders the trigger and dialog usably at a narrow viewport`) | VM-01, VM-02 | evaluation.md |

**CA-14 disposable-environment evidence (not a pytest case).** The Spec
Reviewer flagged that `should_prevent_late_write_from_recreating_data_after_goal_removal`,
as originally drafted, asserted a raw repository write and its resulting
`IntegrityError` from inside `test_remove_goal_controller.py` — a boundary
`controllers-testing-rules.md` reserves for exercising the SUT through
`TestClient`/HTTP, not for a direct non-HTTP repository call. No HTTP endpoint
in this delivery (or the repository as a whole) performs the kind of write
CA-14 needs to disprove, so there is no HTTP boundary through which RF-06 can
be observed. Per `database-layer-rules.md` ("If a complex database primitive
cannot be observed adequately through that boundary ... record focused
disposable-environment validation evidence instead of creating a
database-layer test suite" — the same treatment that document already gives
migration/constraint/index checks), CA-14 is proven as **disposable-environment
evidence during Evaluation**, not as an automated pytest case: using the same
PostgreSQL Testcontainer fixture already started for the controller suite,
after removing a Goal with a skill experience via the real `DELETE` route,
attempt a direct `SqlalchemyActivityAttemptsRepository.add()` (or equivalent)
referencing the removed `skill_experience_id` and record the resulting
`sqlalchemy.exc.IntegrityError` (with traceback) as `evaluation.md` evidence
for CA-14/RF-06.

For every `VM-*`:

**VM-01 — Trigger and confirmation happy path (desktop 1440×900 and mobile 375×812).**

Preconditions: local stack up (`docker compose up -d`), FastAPI and web dev
servers running, a seeded account with at least one Goal that has Habilidade
experiences (`student.seed@shifu.com` or an equivalent fixture Goal).

1. Sign in and navigate to `/learning/goals/{goalId}` for a Goal with
   experiences.
2. Confirm the "Remover Objetivo" trigger is visible, uses the destructive
   style (neutral surface, `--selo-text` label/border, icon), and is reachable
   by Tab with a visible focus ring.
3. Activate the trigger; confirm the dialog opens with the icon tile, title,
   full-scope/irreversibility description, no text input, and Cancel/Confirm
   actions, matching the `kZHN8` screenshot once captured (Section 3, Design
   Contract note).
4. Click Cancel; confirm the dialog closes, the page is unchanged, and no
   network request was sent (inspect the network panel).
5. Reopen the dialog and click Confirm; confirm exactly one
   `DELETE /learning/goals/{goalId}` request is sent, the button shows a
   pending state, and on completion the browser navigates to `/`.
6. On `/`, confirm the removed Goal's card no longer appears in the grid.
7. Inspect console for errors and confirm no failed requests remain.

Cleanup: none required (the Goal is intentionally deleted); reseed if the
fixture account is reused by other manual scenarios.

**VM-02 — Failure, retry, and duplicate-submit guard.**

Preconditions: same as VM-01, plus the ability to force a `5xx` (e.g. stop the
API mid-request or use a network-throttling/mocked-failure browser tool).

1. Open the confirmation dialog for a Goal with experiences.
2. Force the `DELETE` request to fail; confirm the dialog stays open, shows
   an error message, and offers a retry action; confirm the Goal and its
   experiences are unchanged (reload the page or query the API).
3. Rapidly double-activate Confirm on a normal (non-forced-failure) attempt;
   confirm only one `DELETE` request is observed (network panel) and the
   button is disabled after the first activation.
4. Retry after the earlier forced failure; confirm success now redirects to
   `/` as in VM-01.

Cleanup: none beyond reseeding the affected Goal if manual scenarios continue.

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
pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts
pnpm --filter web build
```

# 5. Documentation alignment and revision history

| Document | Authority for | State | Required change/confirmation |
| --- | --- | --- | --- |
| Shifu — PRD — Learning (content ID `83066881`) | `RP-22`, `JN-15` product intent | confirmed | Full page re-read on 2026-09-23; `RP-22`/`JN-15` text matches Jira's cited traceability; no PRD change required |
| `documentation/modules.md` | Learning module ownership | confirmed | No cross-module boundary change; Learning does not import Curriculum |
| `documentation/architecture.md` | Web/server layering, Shared UI boundary | confirmed | `ConfirmationDialog` placed under `ui/shared/widgets/components` per its "module-neutral responsibility" definition |
| `documentation/design.md` | Visual/design-token authority | confirmed (partial — `kZHN8` not visually inspected) | Screenshot capture and reconciliation required before this ships (Section 3 Design Contract) |
| `documentation/rules/ui-layer-rules.md` | shadcn-first UI primitives, dialog header structure, hook placement | confirmed | Governs the `alert-dialog.tsx`/`ConfirmationDialog` and action-hook-placement decisions above |
| `documentation/rules/web-app-routing-rules.md` | Playwright route-suite location | discrepancy noted, not resolved by this Spec | The Rule's "Route integration tests" section names `apps/web/tests/routes/<module>/<route-file>.test.tsx`, but no `apps/web/tests/routes/` directory exists anywhere in the repository; every module (`identity`, `curriculum`, `gamification`, `learning`, `intelligence`, `shared`) and `documentation/rules/widget-testing-rules.md` instead use `apps/web/tests/<module>/<page>.test.ts` — the pre-existing, pre-classified-`Modify` `apps/web/tests/learning/goal-detail-placeholder-page.test.ts` follows that actual convention. This Spec follows the real, universal repository practice per `AGENTS.md`'s "treat the documentation as intent and surface the discrepancy" precedence rule, flagged here for a separate maintenance correction to the stale Rule text rather than blocking this delivery. |

| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| `documentation/rules/python-conventions-rules.md` | `apps/server/src/shifu/learning/**`, tests | 2026-09-23 repository state |
| `documentation/rules/core-layer-rules.md` | `RemoveGoalUseCase` | 2026-09-23 repository state |
| `documentation/rules/use-case-testing-rules.md` | `test_remove_goal_use_case.py` | 2026-09-23 repository state |
| `documentation/rules/rest-layer-rules.md` | `RemoveGoalController`, `learning-service.ts` | 2026-09-23 repository state |
| `documentation/rules/controllers-testing-rules.md` | `test_remove_goal_controller.py` | 2026-09-23 repository state |
| `documentation/rules/database-layer-rules.md` | Cascade/`remove()` reuse, persistence test boundary | 2026-09-23 repository state |
| `documentation/rules/typescript-conventions-rules.md` | All changed `apps/web` files | 2026-09-23 repository state |
| `documentation/rules/ui-layer-rules.md` | `ConfirmationDialog`, `alert-dialog.tsx`, page hook, action hook | 2026-09-23 repository state |
| `documentation/rules/web-app-routing-rules.md` | Route/navigation behavior (no route file change) | 2026-09-23 repository state |
| `documentation/rules/widget-testing-rules.md` | All new/modified web tests | 2026-09-23 repository state |

| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | 2026-09-23 | Created Spec for SHIFU-67 | Jira Dev Task requesting atomic Objetivo removal, tracing to `RP-22`/`JN-15` |
