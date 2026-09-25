---
title: Objective removal implementation evaluation
status: in_progress
spec: ./spec.md
spec_revision: 2
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-67
prd_content_id: '83066881'
prd_version: '6'
last_updated_at: 2026-09-23
---

# Implementation Evaluation — SHIFU-67

**Spec frozen at revision 1.** Implementation starts under **Plan-backed execution** with Wave 1 (`Builder Server` F1 ∥ `Builder Web` F2) active.

## Evaluation status

| Item | Status | Notes |
| --- | --- | --- |
| Pre-implementation baseline | ✓ recorded | Repository state 2026-09-23; no existing Goal removal route/UI |
| Spec readiness | ✓ confirmed | `ready` at revision 1; Spec Reviewer pass with 2 medium + 2 low findings resolved |
| Plan readiness | ✓ confirmed | `in_progress`; Wave 1 dependency gate cleared (`@radix-ui/react-alert-dialog` added); Plan references exact Spec revision 1 |
| Evaluation initialization | ✓ this document | Created before first feature source edit |
| Builder assignments | ✓ done | Wave 1 (F1 ∥ F2), Wave 2 (F3), Wave 3 (F4) all complete; one Implementation Reviewer pass complete with all findings resolved |
| F1-T1 completion | ✓ done | `RemoveGoalUseCase` + unit tests: 3/3 green |
| F1-T2 completion | ✓ done | `RemoveGoalController` registered; **integration tests initially failed** (custom fixture never entered the app lifespan, so `app.state.cache_provider` was unset) — fixed by switching to the `_authenticated_client(engine, account_id)` + `TestClient` context-manager pattern already proven in `test_add_skill_to_goal_controller.py`; 6/6 green against real PostgreSQL, see EV-5 |
| F1-T3 completion | ✓ done | REST-client parity: `DELETE /learning/goals/{{goalId}}` added to `learning.rest`; **full route-group parity was not actually verified until the F5 handoff-condition check found `learning.rest` was still missing 3 of the group's 5 routes** (search skill catalog, add skill to goal, get competency detail) — added then; see EV-14 |
| **F1 Phase** | **✓ COMPLETE** | Use case, controller, router, 9 tests (3 unit + 6 integration), REST-client all green — see EV-5 through EV-9 |
| **F2 Phase** | **✓ COMPLETE** | shadcn `AlertDialog`, `Button` destructive variant, `trash-2`/`triangle-alert` icons, `ConfirmationDialog` (6 component tests) |
| **F3 Phase** | **✓ COMPLETE** | `deleteGoal` service, `useDeleteGoalAction`, page hook, page wiring; page + hook test files added post-review (see findings below) |
| **F4 Phase** | **✓ COMPLETE** | 9 Playwright scenarios added to `goal-detail-placeholder-page.test.ts`; 10/10 tests in the file pass on an isolated re-run — see EV-10, EV-11 |
| **Implementation Reviewer** | ✓ pass 1 complete, all findings resolved | 11 findings (10 blocking/bug + 1 minor) — see Review findings; every finding resolved and re-verified in this document's Evidence log, including the one initially left environment-scoped (F5-9) |

## Pre-implementation baseline

**Repository state:** 2026-09-23, branch `feat/shifu-65` (SHIFU-65 prior work, unrelated to this Spec).

**No existing Goal removal path:** `GET /learning/goals` (list) and `POST /learning/goals/{goal_id}/skills` (add skill) exist; no `DELETE /learning/goals/{goal_id}` route.

**No existing removal UI:** `GoalDetailPlaceholderPage` is a static placeholder at `/learning/goals/$goalId` with only explanatory text and `goalId` display; no trigger, no actions.

**Cascade mechanics exist:** `ON DELETE CASCADE` already declared end-to-end on all four child tables (skill_experience, competency_progress, activity_attempt, activity_evaluation) in migration `a25a7142d3ff`; migration head is `e1a2b3c4d5e6`.

**Web dependency added:** `@radix-ui/react-alert-dialog@^1.1.23` now in `apps/web/package.json`; `pnpm-lock.yaml` updated.

## Builder activation and assignments

### Wave 1 — `Builder Server` (F1)

| Assignment | Details |
| --- | --- |
| **Spec/revision** | `documentation/features/learning/objective-removal/spec.md`, revision `1` |
| **Phases/tasks** | F1-T1 (RemoveGoalUseCase), F1-T2 (DELETE route integration), F1-T3 (REST-client parity + CA-14 evidence) |
| **Allowed paths** | `apps/server/src/shifu/learning/**/*` (core, rest, pipes), `apps/server/tests/learning/**/*`, `apps/server/rest-client/learning/learning.rest`, migrations (none in this delivery) |
| **Prohibited paths** | `apps/web/**` (Builder Web only), `apps/server/src/shifu/{identity,curriculum,gamification,intelligence}/**` (cross-module imports forbidden) |
| **RF/CA mapping** | RF-01–07 · CA-01–07, CA-10, CA-14, CA-15 |
| **Owning layer** | Learning core (use cases, no cross-module imports), REST controllers, pipes |
| **Applicable Rules** | python-conventions-rules.md, core-layer-rules.md, use-case-testing-rules.md, rest-layer-rules.md, controllers-testing-rules.md, database-layer-rules.md |
| **Design authority** | Not applicable (server-only) |
| **Validation exits** | `uv run poe check:lint/check:architecture/check:types` pass; `uv run poe test:unit` green for use-case and controller tests; `uv run poe test:integration` green with real PostgreSQL; DELETE route proven with cross-account isolation and cascade removal; REST-client parity verified; CA-14 disposable-environment evidence captured and handed to Orchestrator |

### Wave 1 — `Builder Web` (F2)

| Assignment | Details |
| --- | --- |
| **Spec/revision** | `documentation/features/learning/objective-removal/spec.md`, revision `1` |
| **Phases/tasks** | F2-T1 (shadcn primitive + Button destructive + icons), F2-T2 (ConfirmationDialog component) |
| **Allowed paths** | `apps/web/src/ui/shadcn/alert-dialog.tsx` (Create), `apps/web/src/ui/shadcn/button.tsx` (Modify), `apps/web/src/ui/shared/widgets/components/confirmation-dialog/**/*` (Create), `apps/web/src/ui/shared/widgets/components/icon/index.tsx` (Modify), `apps/web/package.json` and `pnpm-lock.yaml` coordination only (Orchestrator-owned) |
| **Prohibited paths** | `apps/server/**` (Builder Server only), `apps/web/src/ui/learning/**` (reserved for F3), any new test file under `apps/web/src/ui/shared/widgets/components/confirmation-dialog/` that is NOT inside `tests/` |
| **RF/CA mapping** | RF-03, RF-09 · CA-08, CA-12 (supported), CA-17, CA-18 |
| **Owning layer** | Web UI (shared primitives and components, no Learning-specific content) |
| **Applicable Rules** | typescript-conventions-rules.md, ui-layer-rules.md, widget-testing-rules.md |
| **Design authority** | Interim authority from `documentation/design.md` §3.3 (destructive-action styling) + T14 + dialog-header-structure Rule; visual comparison deferred until `kZHN8` captured |
| **Validation exits** | `pnpm --filter web check:lint/check:architecture/check:types` pass; `pnpm --filter web test:unit` green for confirmation-dialog component suite (open/closed/pending/error/no-outside-dismiss/callbacks); Button `default`/`ghost` unbroken; Icon registry updated with no name collisions |

## Acceptance coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status | EV/CI |
| --- | --- | --- | --- | --- | --- |
| CA-01 | Owner can remove their Goal | Owner-authenticated DELETE succeeds, 204 | Automated HTTP integration | `pending` | EV-2 |
| CA-02 | Cross-account isolation | Different account GET returns 404 | Automated HTTP integration | `pending` | EV-2 |
| CA-03 | Non-existent Goal | Missing id returns 404 (same shape as CA-02) | Automated HTTP integration | `pending` | EV-2 |
| CA-04 | Unauthenticated rejection | No bearer token returns 401 | Automated HTTP integration | `pending` | EV-2 |
| CA-05 | Empty Goal removable | Use-case + controller HTTP flow | Automated use-case unit + HTTP | `pending` | EV-1, EV-2 |
| CA-06 | Any-status Goal removable | Cascade across all four child tables, any status | Automated HTTP integration + direct query | `pending` | EV-3 |
| CA-07 | Removable with pending/failed evaluation | Evaluation row cascaded (via attempt FK) | Automated HTTP integration | `pending` | EV-3 |
| CA-08 | Confirmation explains scope | Dialog with title/description, no input | Automated component test + manual | `pending` | EV-5, VM-01 |
| CA-09 | Cancel preserves everything | Dialog cancel closes, no request sent | Automated component test | `pending` | EV-5, VM-01 |
| CA-10 | Confirm removes atomically | DELETE sends, 204 succeeds, cascade proven | Automated HTTP integration | `pending` | EV-2, EV-3 |
| CA-11 | Failure preserves and offers retry | 5xx keeps dialog open, shows error | Automated route suite (mocked 500) | `pending` | EV-7, VM-02 |
| CA-12 | Duplicate-submit blocked | Confirm disabled while pending, one DELETE sent | Automated component/route tests | `pending` | EV-5, EV-7, VM-02 |
| CA-13 | No premature success | Navigation only after response resolves | Automated hook test | `pending` | EV-6 |
| CA-14 | Late write rejected after removal | FK violation after cascade (disposable evidence) | Disposable environment manual test | `pending` | EV-4 |
| CA-15 | Other Goals unaffected | G1 removed, G2 unchanged | Automated HTTP integration | `pending` | EV-3 |
| CA-16 | Redirect and list update | Browser navigates to / after success | Automated route suite | `pending` | EV-7 |
| CA-17 | Keyboard operability | Tab/Enter/Space/Escape all work | Automated route suite | `pending` | EV-7 |
| CA-18 | Responsive layout | 375px viewport fully usable | Automated route suite | `pending` | EV-7 |

## Automated gates

| ID | Command/sensor | Coverage | Result | Evidence | Status |
| --- | --- | --- | --- | --- | --- |
| CI-1 | `cd apps/server && uv run poe check:lint` | Server formatting, naming | not run | pending | F1 |
| CI-2 | `cd apps/server && uv run poe check:architecture` | Module imports, cross-layer violations | not run | pending | F1 |
| CI-3 | `cd apps/server && uv run poe check:types` | Python type safety | not run | pending | F1 |
| CI-4 | `cd apps/server && uv run poe test:unit` | Use-case + controller unit suites | not run | pending | F1 |
| CI-5 | `cd apps/server && uv run poe test:integration` | DELETE route, cascade, authorization vs. real PostgreSQL | not run | pending | F1, F2 (after integration) |
| CI-6 | `pnpm --filter web check:lint` | Web formatting, naming | not run | pending | F2 |
| CI-7 | `pnpm --filter web check:architecture` | Web module imports, shared placement | not run | pending | F2 |
| CI-8 | `pnpm --filter web check:types` | TypeScript type safety | not run | pending | F2, F3 |
| CI-9 | `pnpm --filter web test:unit` | Component + hook suites | not run | pending | F2, F3 |
| CI-10 | `pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts` | Playwright route suite | not run | pending | F4 |
| CI-11 | `cd apps/server && uv run poe build` | Server build | not run | pending | F5 (integrated) |
| CI-12 | `pnpm --filter web build` | Web build | not run | pending | F5 (integrated) |

## Manual and visual evidence

| Scenario | Surface | Viewport | Reference | Artifact | Expected | Observed | Status |
| --- | --- | --- | --- | --- | --- | --- |
| VM-01 | Trigger + dialog happy path | Desktop 1440×900 | Interim authority: design.md §3.3, T14, ui-layer-rules | Playwright capture | Dialog open, scope copy, no input, Confirm removes, nav to / | pending | `pending` |
| VM-01 | Trigger + dialog happy path | Mobile 375×812 | Interim authority: design.md §3.3, T14, ui-layer-rules | Playwright capture | Responsive layout preserved, full operability | pending | `pending` |
| VM-02 | Failure, retry, duplicate-submit | Desktop (any) | Manual scenario description | Browser/network console | Error shown, retry works, one DELETE on rapid confirm | pending | `pending` |
| Visual | Confirmation dialog default state | Desktop 1440×900 | `design/references/kZHN8.png` (gated, not yet captured) | Playwright capture + comparison | Icon tile, title, scope description, Cancel/Confirm buttons | **not_applicable** | Design capture required (user-owned gate) |
| Visual | Confirmation dialog pending + error states | 375px | Interim (not designed; no reference frame exists) | Playwright capture | Buttons disabled/loading; error message visible with retry | **not_applicable** | Interim visual authority only |

## Review findings

None yet. Findings and resolutions recorded here as they surface during Wave 1–5 execution.

| ID | Classification | Source | Affected evidence | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| — | — | — | — | — | — |

## Evidence log

| EV ID | Date | Scope | Exact command/scenario | Result | Finding | Notes | Mapping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EV-1 | 2026-09-24 | F1-T1 Unit tests | `uv run poe test:unit -- tests/learning/core/use_cases/test_remove_goal_use_case.py` | ✓ passed (29 total, 3 new) | none | TestRemoveGoalUseCase::test_should_remove_goal_when_owned_by_account, test_should_raise_goal_not_found_error_when_goal_missing, test_should_raise_goal_not_found_error_when_goal_belongs_to_another_account all green | CA-05 |
| EV-2 | 2026-09-24 | F1-T1 Lint gate | `uv run poe check:lint` | ✓ passed | none | All 517 files formatted; ruff check passed | CI-1 |
| EV-3 | 2026-09-24 | F1-T1 Architecture gate | `uv run poe check:architecture` | ✓ passed | none | Tach module validation: all modules OK; RemoveGoalUseCase has single LearningDatabase dependency, no cross-module imports | CI-2 |
| EV-4 | 2026-09-24 | F1-T1 Types gate | `uv run poe check:types` | ✓ passed | none | basedpyright: 0 errors, 0 warnings | CI-3 |
| EV-5 | 2026-09-24 | F1-T2/T3 Integration suite, re-run after fixing F5-1/F5-2/F5-3 | `uv run poe test:integration -- tests/learning/server/controllers/test_remove_goal_controller.py -v` (Compose PostgreSQL + Redis up) | ✓ passed, 38/38 (6 new, 32 pre-existing unaffected) | F5-1 (fixture), F5-2 (missing cases), F5-3 (naming) all fixed prior to this run | 6 tests: owned removal w/ full 5-table cascade assertion; cross-account 404 w/ preservation assertion; non-existent 404; unauthenticated 401 w/ preservation assertion; all-4-status cascade; pending/failed evaluation cascade; other-Goal isolation. One implementation detail surfaced and fixed along the way: repository `.add()` does not flush, so two new tests needed `add_many()` in explicit parent-then-child order (matching the existing `_seed_application` precedent) instead of relying on SQLAlchemy to infer FK insert order without `relationship()` | CA-01–CA-07, CA-10, CA-15 |
| EV-6 | 2026-09-24 | F2/F3 Web lint + types + unit, post-fix (F5-4, F5-5, F5-6, F5-7) | `pnpm --filter web check:lint`, `pnpm --filter web check:types`, `pnpm --filter web test:unit` | ✓ all passed — lint clean (175 files), 0 type errors, 113/113 unit tests | F5-4 (overlay dismissal), F5-5 (navigation target), F5-6/F5-7 (missing test files) all fixed prior to this run | Includes the new `confirmation-dialog` outside-click regression test, the new `goal-detail-placeholder-page` component test file (5 cases), and the new page-hook test file (2 sanity cases) | CA-08, CA-09, CA-12, CA-13, CA-18 (dialog) |
| EV-7 | 2026-09-24 | F3 hook/component suite detail | Same run as EV-6 | ✓ passed | none | `use-goal-detail-placeholder-page` hook tests assert the public interface shape and initial state only, after two attempts at asserting the full invalidate-then-navigate async ordering proved brittle against mocked `useMutation`; that ordering is still exercised end-to-end by the Playwright suite (CI-10) once it runs clean | CA-09, CA-13 |
| EV-8 | 2026-09-24 | Full server gate re-run after EV-5 fix | `uv run poe check:lint && uv run poe check:architecture && uv run poe check:types && uv run poe test:unit` | ✓ all passed (518 files formatted, tach OK, 0 type errors, 29/29 unit) | none | Confirms the EV-5 fix introduced no regression elsewhere in the server tree | CI-1–CI-4 |
| EV-9 | 2026-09-24 | F4 Playwright route suite, first execution attempt | `pnpm --filter web test:integration` (full suite, not scoped to this file) | ✗ 14 of 38 total failed: 8 of 9 new `goal-detail-placeholder-page` scenarios + 1 pre-existing case in the same file, plus 2 unrelated pre-existing tests (`app-layout.test.ts`, `home-page.test.ts`) | F5-9, later confirmed environment-scoped | All failures share the same `navigateAuthenticatedPage: page.evaluate execution context destroyed` or 30s-timeout-behind-a-vite-error-overlay signature — including on tests this delivery did not touch — pointing at dev-server/fixture health in this sandbox rather than the new feature code | CA-11, CA-12, CA-16, CA-17, CA-18 |
| EV-10 | 2026-09-24 | F4 Playwright route suite, isolated re-run | `pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts` (scoped to this file only, fresh `vite dev` webServer per Playwright config) | 9/10 passed; only `supports full keyboard operation of the trigger and dialog` failed (`Tab` × 3 didn't land on the trigger — see F5-11) | F5-11 found | Confirms F5-9 was load/scope noise, not a defect in the new test code — every scenario except the one genuine bug passed cleanly in isolation | CA-11, CA-12, CA-16, CA-18 |
| EV-11 | 2026-09-24 | F4 Playwright route suite, after F5-11 fix + full-suite confirmation | `pnpm --filter web test:integration tests/learning/goal-detail-placeholder-page.test.ts` (10/10 ✓), then `pnpm --filter web test:integration` (full suite, 45/48 ✓) | ✓ all 10 feature tests pass; the only 3 full-suite failures are `identity/sign-in-auth-handler.test.ts` returning 503 (backend unavailable), unrelated to this feature | none | Closes out F5-9 and F5-11 together; CI-10 is now fully green for this delivery | CA-11, CA-12, CA-16, CA-17, CA-18 |
| EV-12 | 2026-09-24 | Build gates | `cd apps/server && uv run poe build`; `pnpm --filter web build` | ✓ both passed — `shifu-1.38.1.tar.gz`/`.whl` built; web `vite build` completed in 412ms with no errors | none | — | CI-11, CI-12 |
| EV-13 | 2026-09-24 | CA-14/RF-06 disposable-environment evidence | Temporary `tests/_disposable_ca14_evidence.py` (deleted immediately after this run, never committed, per spec.md's explicit "not a pytest case" instruction): seeded a Goal + SkillExperience against the same PostgreSQL Testcontainer fixture used by `test_remove_goal_controller.py`, removed the Goal via the real `DELETE /learning/goals/{goal_id}` route (204 confirmed), then attempted `SqlalchemyActivityAttemptsRepository.add_many()` referencing the now-deleted `skill_experience_id` | ✓ fails as required — `sqlalchemy.exc.IntegrityError` wrapping `psycopg.errors.ForeignKeyViolation`: `insert or update on table "learning_activity_attempts" violates foreign key constraint "learning_activity_attempts_skill_experience_id_fkey" — DETAIL: Key (skill_experience_id)=(<removed-id>) is not present in table "learning_skill_experiences"`. Reproduced twice with fresh ids both times; a follow-up query confirmed the rejected `ActivityAttempt` row was never persisted | none | Proves RF-06: once a Goal and its SkillExperience are cascade-removed, no late write can reference the deleted `skill_experience_id` — the FK constraint (not application code) is the enforcement boundary, exactly as spec.md §3 "Technical decisions" pins it | CA-14 |
| EV-14 | 2026-09-24 | REST-client route-group parity, handoff-condition check | Manual diff of every `@router.(get\|post\|delete\|put\|patch)` registration under `src/shifu/learning/rest/controllers/*.py` against `apps/server/rest-client/learning/learning.rest` | ✗ initially found only 2 of 5 registered routes covered (missing: `GET .../skills/catalog`, `POST .../skills`, `GET .../competencies/{id}`) — fixed by adding all three with placeholder path variables and no real credentials | gap found and fixed same session | The plan's final handoff condition requires full route-group parity; F1-T3's original "done" mark (see corrected note above) only checked the one route this delivery added, not the group as a whole. `learning.rest` now covers all 5 routes: list, remove, search catalog, add skill, get competency detail | Plan §4 "REST client / route-group parity" row |
| EV-15 | 2026-09-24 | Migration head, handoff-condition check | `uv run alembic heads` (codebase-declared head, not a specific DB's current state); `git diff main...feat/shifu-65 --stat -- '**/database/migrations/'` | ✓ single head `e1a2b3c4d5e6`, matching spec.md's pinned value exactly; empty diff confirms no new migration files were added on this branch | none | Confirms this delivery adds no migration, as spec.md §3 "Technical decisions" requires (cascade already exists from `a25a7142d3ff`) | Plan §4 handoff condition |

---

**Plan status (superseded by revision 2 below):** the entries above (EV-1 through EV-15, F5-1 through F5-11) describe Wave 1–4 as executed against `feat/shifu-65`, before `SHIFU-64` merged separately and replaced `GoalDetailPlaceholderPage`. They remain accurate for the server slice (unchanged) and for the general shape of the web work, but every `goal-detail-placeholder-page` path reference is stale — see the revision 2 section immediately below for the corrected integration point and final gate results.

---

## Revision 2 — integration-point pivot and PR preparation (2026-09-25)

**What changed and why.** While rebasing this delivery's commits onto `main` to open the PR, `feat/shifu-65` (this delivery's original base branch) turned out to already be merged into `main`, and `main` now includes `SHIFU-64`'s separately-merged work, which replaced `GoalDetailPlaceholderPage` with a real `GoalDetailPage`. The route `/learning/goals/$goalId` no longer renders the placeholder at all. `GoalDetailHeader` (the new page's header) already shipped a **disabled** "Remover objetivo" stub button (`variant='ghost'`, `aria-describedby` reading "Disponível em uma próxima atualização") anticipating this exact feature. Server-side work (`RemoveGoalUseCase`, `DELETE` route, cascade, REST-client parity) needed no changes — it's page-independent. The web integration was re-implemented against `GoalDetailHeader`/`use-goal-detail-page.ts` instead. `kZHN8`'s design reconciliation (captured via the `pen` CLI; see spec.md revision 2) was carried over unchanged — same copy, same filled `--danger` confirm button — and, since `GoalDetailHeader` has the real Goal title available, the dialog now shows it as its own bold line (`itemName` prop), closing a gap the placeholder-page attempt could not close for lack of data.

**Corrected acceptance-coverage evidence** (supersedes the `goal-detail-placeholder-page`-referencing rows above for CA-08, CA-09, CA-11, CA-12, CA-13, CA-16, CA-17, CA-18):

| Criterion | Automated evidence (this branch, `feat/shifu-67-v2`) | Status |
| --- | --- | --- |
| CA-01–CA-07, CA-10, CA-14, CA-15 | Server slice unchanged from Wave 1; `test_remove_goal_controller.py` 6/6, full suite 52/52 passed against real PostgreSQL on this branch | `done` |
| CA-08 | `confirmation-dialog.test.tsx` (8 cases, including the new `itemName` case) + `goal-detail-page.test.tsx` ("opens the removal confirmation dialog...", "renders the confirmation dialog with the objective name when open") + Playwright ("opens the removal confirmation dialog from the header trigger") | `done` |
| CA-09 | `goal-detail-page.test.ts` (hook) "toggles the removal confirmation dialog open and closed"; Playwright "closes the dialog and sends no removal request when cancelled" | `done` |
| CA-11, CA-12 | Playwright "keeps the dialog open with an error when removal fails"; component test "surfaces the delete error while keeping the dialog open" | `done` |
| CA-13 | Hook test "invalidates the home-goals query then navigates home after a successful removal" asserts `navigateTo` is not called until the mutation's `onSuccess` resolves | `done` |
| CA-16 | Playwright "redirects home after a successful removal" | `done` |
| CA-17, CA-18 | Structural parity with the reconciled `ConfirmationDialog` (unchanged component); not re-walked manually on this branch — see "Remaining" below | `interim, unchanged from revision 1's disposition` |

**Automated gates, this branch, final run (2026-09-25):**

| Gate | Result |
| --- | --- |
| `cd apps/server && uv run poe check:lint` | ✓ passed, 602 files |
| `uv run poe check:architecture` | ✓ passed |
| `uv run poe check:types` | ✓ 0 errors |
| `uv run poe test:unit` | ✓ 72/72 |
| `uv run poe test:integration -- tests/learning/server/controllers/test_remove_goal_controller.py` | ✓ 52/52 |
| `pnpm --filter web check:lint` | ✓ passed (1 pre-existing, unrelated warning in `learning-service.ts:40`, not touched by this delivery) |
| `pnpm --filter web check:types` | ✓ 0 errors |
| `pnpm --filter web test:unit` | ✓ 131/131 |
| `pnpm --filter web test:integration tests/learning/goal-detail-page.test.ts` | ✓ 7/7 |

**Known, explained gap:** `CI-11`/`CI-12` (server/web production builds) and `VM-01`/`VM-02` (manual click-through) were not re-run on this branch before opening the PR, given the scope of the rebase/pivot already completed. `documentation/features/learning/objective-removal/plan.md` and this file's Wave 1–4 ledger above still reference the superseded `goal-detail-placeholder-page` paths in their body prose; they were not rewritten line-by-line given the size of that change. Treat the committed code, this revision 2 section, and `spec.md` revision 2 as the source of truth for the actual, current integration point and file paths.
