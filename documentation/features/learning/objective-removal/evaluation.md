---
title: Objective removal implementation evaluation
status: in_progress
spec: ./spec.md
spec_revision: 1
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
| Builder assignments | ⧖ in_progress | Wave 1 active: `Builder Server` (F1-T1 ✓, F1-T2 pending, F1-T3 pending), `Builder Web` (F2 pending) |
| F1-T1 completion | ✓ done | `RemoveGoalUseCase` + unit tests: CI-4 passed (3/3 tests green); CI-1, CI-2, CI-3 passed |
| F1-T2 status | ⧖ in_progress | `RemoveGoalController` created and registered; integration tests written (fixture setup needs minor correction); HTTP contract test structure ready |

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

---

**Plan status:** `in_progress`, Wave 1 active. Next action: `Builder Server` (F1) and `Builder Web` (F2) proceed in parallel. Both report their focused exits (lint, types, unit tests) to the Orchestrator when complete, then Phase integration begins.
