---
title: Add Skill with Suggested Foundations implementation plan
status: draft
spec: ./spec.md
spec_revision: 2
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-65
last_updated_at: 2026-09-22
---

# 1. Execution status

- **Spec**: `documentation/features/learning/add-skill/spec.md`, revision `2`, status `ready`.
- **Why Plan-backed**: `complete`-mode Spec spanning two applications, a
  brand-new cross-module contract (`CurriculumCatalogReader`), a Curriculum
  persistence adapter and database wiring that don't exist yet, a schema
  migration with a concurrency backstop, and multiple design-backed UI states
  across a stateful catalog list and a four-mode confirmation dialog.
- **Plan status**: `draft` — implementation has not started.
- **Next action**: kick off `F1` (`Builder Server`) and `F3` (`Builder Web`)
  together through `implement-spec`; both are dependency-ready now.
- **Active blockers**: none.
- **External dependencies**: none block this Plan. SHIFU-35 (the real
  `/learning/goals/$goalId` page) is referenced by the Spec as later, unrelated
  work — not a gate for any phase here.
- **Active Builders**: none yet.
- **Next dependency-ready Builders**: `Builder Server` (`F1`), `Builder Web`
  (`F3`) — both startable immediately and in parallel.
- **Shared/root ownership**: `apps/server/src/shifu/app.py` (composition
  wiring) and `apps/server/src/shifu/rest/handlers/app_error_handler.py`
  (shared error mapping) are edited only by `Builder Server`, only within `F1`
  — no concurrent-edit risk since `Builder Web` never touches `apps/server/**`.
  The one new Alembic migration is generated and applied by `Builder Server`
  inside `F2`; the Orchestrator reviews its generated content (columns,
  constraint, `down_revision`) before `F4` integration rather than authoring it
  separately.

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` is `ready` at revision `2` | Orchestrator | `done` | None |
| Design Contract | `design/handoff.md` complete with all 7 screenshots inspected | Orchestrator | `done` | None |
| Environment | `docker compose` Postgres (and Redis, required by `apps/server/src/shifu/app.py`'s lifespan) available for `uv run poe test:integration` and the Playwright suite | Builder Server, Builder Web | `pending` | Start required Compose services before running any integration/Playwright command |
| Environment | `apps/server` and `apps/web` dev servers running for `F4`'s manual `VM-*` scenarios | Orchestrator | `pending` | Start `uv run uvicorn main:app --app-dir src --reload` and the web `dev` script before `F4` |

No product dependency from `documentation/modules.md` is treated as an
execution phase; the only real technical dependency sequenced below is
`F2` on `F1` (Learning's use cases need the Curriculum foundation and the
generalized error handler to exist first).

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Server` | F1 | Curriculum foundation (Shared contract + structures, Curriculum search/batch methods, `SqlalchemyCurriculumDatabase`, `CurriculumCatalogReaderProvider`, `app.py` wiring) plus the generalized `AppErrorHandler` | — | F3 | `pending` | `uv run poe check:lint/check:architecture/check:types` pass; `uv run poe test:unit` green including the new `test_app_error_handler.py`; app boots locally without a startup error |
| 1 | `Builder Web` | F3 | Web route, widgets, hooks and REST-service built against the Spec's pinned contract | — | F1, F2 | `pending` | `pnpm --filter web check:lint/check:architecture/check:types` pass; `pnpm --filter web test:unit` green (all component tests, mocked hooks) |
| 2 | `Builder Server` | F2 | Learning server slice: domain errors/structures, 3 use cases, 3 controllers + router, pipe additions, migration, repository `IntegrityError` translation, REST-client file | F1 | F3 (if still running) | `pending` | `uv run poe test:unit` and `uv run poe test:integration` green; migration applies and downgrades cleanly against a local Postgres |
| 3 | Orchestrator | F4 | Integration: real server + web wired together, Playwright suite executed, every `VM-*` performed, REST-client parity verified, migration reviewed, one Implementation Reviewer pass, evidence recorded | F2, F3 | — | `pending` | Every `CA-*`/`VM-*` has accepted evidence in `evaluation.md`; Reviewer findings resolved; all commands in the Spec's Commands section pass |

## F1 — Curriculum foundation and error-handler generalization

### F1-T1 — Shared cross-module contract

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** No dependency within F1 (first task); parallel with all of F3
- **Paths:** `apps/server/src/shifu/shared/core/domain/structures/{skill_catalog_entry.py,skill_catalog_page.py,skill_foundation_entry.py,__init__.py}`, `apps/server/src/shifu/shared/core/interfaces/{curriculum_catalog_reader.py,__init__.py}`
- **Traceability:** RF-05; Spec Technical Contract "Domain (Shared)"/"Interfaces (Shared)" rows
- **Outcome:** `CurriculumCatalogReader` Protocol and its three structures created and exported, mirroring `AuthenticationProvider`'s shape
- **Rules:** `documentation/rules/python-conventions-rules.md`, `documentation/rules/core-layer-rules.md`
- **Risks/controls:** None material — pure new-file addition, no existing behavior touched
- **Exit:** `uv run poe check:lint`, `check:types`, `check:architecture` pass

### F1-T2 — Curriculum repository search and batch foundations lookup

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1-T1 (uses its structures' shapes conceptually, though the DB layer itself only needs the domain `Skill`/`SkillFoundation` types); parallel with F3
- **Paths:** `apps/server/src/shifu/curriculum/core/interfaces/{skills_repository.py,skill_foundations_repository.py}`, `apps/server/src/shifu/curriculum/database/sqlalchemy/repositories/{skills_repository.py,skill_foundations_repository.py}`
- **Traceability:** RF-05, RF-07; Spec Technical Contract "Interfaces (Curriculum)" rows
- **Outcome:** `SkillsRepository.search` (keyset-paginated, case-insensitive `ILIKE`) and `SkillFoundationsRepository.find_many_by_skill_ids` (batched `IN` lookup) implemented
- **Rules:** `documentation/rules/database-layer-rules.md`, `documentation/rules/core-layer-rules.md`
- **Risks/controls:** No dedicated repository test per the Spec's accepted rationale (exercised end-to-end by F2's controller tests); confirm this remains true once F2 lands — if the controller tests end up not exercising a code path, flag it rather than silently accepting the gap
- **Exit:** `check:lint`/`check:types`/`check:architecture` pass

### F1-T3 — `SqlalchemyCurriculumDatabase`, reader provider and `app.py` wiring

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1-T1, F1-T2; parallel with F3
- **Paths:** `apps/server/src/shifu/curriculum/database/sqlalchemy/{curriculum_database.py,__init__.py}`, `apps/server/src/shifu/curriculum/providers/curriculum_catalog_reader_provider.py`, `apps/server/src/shifu/app.py`
- **Traceability:** Spec Technical Contract "Provision / Composition" rows
- **Outcome:** `app.state.curriculum_database`/`curriculum_catalog_reader` wired exactly like `authentication_provider`
- **Rules:** `documentation/rules/provision-layer-rules.md` (no dedicated provider test), `documentation/rules/server-app-layer-rules.md`
- **Risks/controls:** `app.py` is the single shared composition file in this Plan — only `Builder Server` edits it, and only in this task, so no concurrent-edit risk
- **Exit:** `check:lint`/`check:types`/`check:architecture` pass; `uv run uvicorn main:app --app-dir src` boots without a startup error

### F1-T4 — Generalize `AppErrorHandler`

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** Independent of F1-T1..T3; parallel with F3
- **Paths:** `apps/server/src/shifu/rest/handlers/app_error_handler.py`
- **Traceability:** Spec Technical Contract "REST (Shared)" row
- **Outcome:** `NotFoundError`→404, `ConflictError`→409, `ValidationError`→400 registered before the generic `AppError`→500 fallback; `InvalidCredentialsError` and the identity-path 503 special case untouched
- **Rules:** `documentation/rules/rest-layer-rules.md`
- **Risks/controls:** This handler is shared by every module — verify no existing test asserts the old blanket-500 behavior for a currently-raised `NotFoundError`/`ConflictError`/`ValidationError` subclass elsewhere in the codebase before merging; if one exists, it means a status code is intentionally changing for existing behavior and must be flagged, not silently accepted
- **Exit:** `apps/server/tests/rest/handlers/test_app_error_handler.py` (Create) green; `uv run poe test:unit` passes with no regression elsewhere

## F3 — Web surface

### F3-T1 — REST service and shared hooks

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** None; parallel with all of F1/F2
- **Paths:** `apps/web/src/rest/services/learning-service.ts` (Modify), `apps/web/src/ui/shared/hooks/use-navigation.ts` (Modify), `apps/web/src/ui/shared/hooks/use-debounced-value.ts` (Create)
- **Traceability:** Spec Technical Contract "UI (Learning + Shared)" rows
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** None material
- **Exit:** `pnpm --filter web check:lint`, `check:types`, `check:architecture` pass

### F3-T2 — Route and `AddSkillPage`

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** After F3-T1; parallel with F1/F2
- **Paths:** `apps/web/src/routes/learning/goals/$goalId/skills/add/index.tsx` (Create), `apps/web/src/ui/learning/widgets/pages/add-skill-page/{index.tsx,use-add-skill-page.ts}` (Create)
- **Traceability:** RF-04, RF-12, RF-14
- **Rules:** `documentation/rules/web-app-routing-rules.md`, `documentation/rules/ui-layer-rules.md`
- **Exit:** `check:lint`/`check:types`/`check:architecture` pass

### F3-T3 — Catalog section, catalog item and its query hook

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** After F3-T1, F3-T2; parallel with F1/F2
- **Paths:** `apps/web/src/ui/learning/widgets/layouts/add-skill-catalog-section/**` (Create), `apps/web/src/ui/learning/widgets/components/skill-catalog-item/**` (Create)
- **Traceability:** RF-02, RF-03, RF-04, RF-07, RF-13 (search/list keyboard and non-color states), RF-14; CA-01, CA-02 (client shape only — server 404 behavior is F2/F4), CA-03, CA-04, CA-05, CA-06, CA-07, CA-08, CA-13, CA-25, CA-26
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** `use-skill-catalog-item.ts` is a genuinely trivial local-state hook per the Spec's rationale for no dedicated test file — if implementation reveals it growing real logic beyond the expand/collapse boolean, stop and add a dedicated hook test rather than silently exceeding that rationale
- **Exit:** `pnpm --filter web test:unit` green for `add-skill-catalog-section.test.tsx`; `check:lint`/`check:types`/`check:architecture` pass

### F3-T4 — Foundations dialog, foundation row and its preview query hook

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** After F3-T1, F3-T2; parallel with F1/F2 and with F3-T3
- **Paths:** `apps/web/src/ui/learning/widgets/layouts/add-skill-foundations-dialog/**` (Create), `apps/web/src/ui/learning/widgets/components/skill-foundation-row/**` (Create)
- **Traceability:** RF-06, RF-08, RF-09, RF-11 (duplicate-submit guard), RF-13 (dialog keyboard and non-color states), RF-15, RF-16; CA-09, CA-10, CA-11, CA-12, CA-14, CA-15, CA-16, CA-17, CA-18, CA-19, CA-20, CA-21, CA-27, CA-28, CA-29, CA-30, CA-31
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** This is the highest-logic widget in the feature (footer-mode derivation, bulk toggle, retry-payload memory, duplicate-submit guard) — keep it in the colocated hook, not the render component, so the required component test can mock the hook cleanly
- **Exit:** `pnpm --filter web test:unit` green for `add-skill-foundations-dialog.test.tsx` and `skill-foundation-row.test.tsx`; `check:lint`/`check:types`/`check:architecture` pass

### F3-T5 — Playwright suite (authored here, executed in F4)

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** After F3-T2..T4; parallel with F1/F2
- **Paths:** `apps/web/tests/learning/add-skill-page.test.ts` (Create)
- **Traceability:** CA-01, CA-03, CA-08, CA-17, CA-21, CA-22, CA-23, CA-24, CA-25
- **Rules:** `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** This suite needs the real server (F2) and a real running web app to pass — it is written and lint-clean by the end of F3, but its **passing execution** is an F4 exit condition, not an F3 one; do not report F3 complete on the strength of this file existing alone
- **Exit (F3):** File created, `pnpm --filter web check:lint` passes on it. **Not executed here.**

## F2 — Learning server slice

### F2-T1 — Domain errors and structures

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1 (needs `CurriculumCatalogReader`'s shapes to reference); not parallel with anything in F1/F2 (same Builder, sequential)
- **Paths:** `apps/server/src/shifu/learning/core/domain/errors/{curriculum_skill_not_found_error.py,invalid_foundation_selection_error.py,__init__.py}`, `apps/server/src/shifu/learning/core/domain/structures/{suggested_foundation.py,skill_addition_preview.py,skill_catalog_row.py,__init__.py}`
- **Traceability:** Spec Technical Contract "Domain (Learning)" rows
- **Rules:** `documentation/rules/core-layer-rules.md`
- **Exit:** `check:lint`/`check:types`/`check:architecture` pass

### F2-T2 — Use cases

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1, F2-T1
- **Paths:** `apps/server/src/shifu/learning/core/use_cases/{search_skill_catalog_use_case.py,preview_skill_addition_use_case.py,add_skill_to_goal_use_case.py,__init__.py}`
- **Traceability:** RF-01, RF-02, RF-03, RF-04, RF-05, RF-06, RF-07, RF-08, RF-09, RF-10, RF-11 (server-side idempotency backstop), RF-12, RF-16; CA-01, CA-02, CA-08, CA-09, CA-12, CA-14, CA-15, CA-16, CA-17, CA-19, CA-20
- **Rules:** `documentation/rules/core-layer-rules.md`, `documentation/rules/use-case-testing-rules.md`
- **Risks/controls:** `SearchSkillCatalogUseCase` is the one place batching must actually happen (one `find_direct_foundations_for_many` call and one `find_many_by_goal_id` call per page, not per row) — the exit test must assert call counts, not just output shape, to catch an accidental N+1 regression
- **Exit:** `apps/server/tests/core/learning/use_cases/test_{search_skill_catalog,preview_skill_addition,add_skill_to_goal}_use_case.py` (Create) green, including the batching-call-count assertion

### F2-T3 — Migration and repository `IntegrityError` translation

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1 (needs the app to boot with the Curriculum wiring for a clean local `db:upgrade` run); can run before or after F2-T1/T2 within F2
- **Paths:** `apps/server/src/shifu/learning/database/sqlalchemy/repositories/skill_experiences_repository.py` (Modify), `apps/server/migrations/versions/<generated>_add_skill_experience_goal_skill_unique_constraint.py` (Generate)
- **Traceability:** Spec Technical Contract "Database (Learning)" rows
- **Rules:** `documentation/rules/database-layer-rules.md`
- **Risks/controls:** Generate with `uv run poe db:migrate "add skill experience goal skill unique constraint"`, review the diff before applying (only the intended constraint, correct `down_revision = faa7f006048a`), then apply with `uv run poe db:upgrade` and prove the downgrade with `uv run poe db:downgrade`
- **Exit:** Migration reviewed and applies/downgrades cleanly against a local Postgres; `test_add_skill_to_goal_use_case.py`'s duplicate-add scenario and a controller-level concurrent-submit assertion both pass

### F2-T4 — Controllers, router and pipe

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F1, F2-T1, F2-T2, F2-T3
- **Paths:** `apps/server/src/shifu/learning/rest/controllers/{search_skill_catalog_controller.py,preview_skill_addition_controller.py,add_skill_to_goal_controller.py,__init__.py}`, `apps/server/src/shifu/learning/rest/router.py` (Modify), `apps/server/src/shifu/learning/pipes/learning_pipe.py` (Modify)
- **Traceability:** All RF/CA the three endpoints serve; see Spec §2 in full
- **Rules:** `documentation/rules/rest-layer-rules.md`, `documentation/rules/controllers-testing-rules.md`, `documentation/rules/server-app-layer-rules.md`
- **Exit:** `apps/server/tests/rest/controllers/learning/test_{search_skill_catalog,preview_skill_addition,add_skill_to_goal}_controller.py` (Create) green against the real Testcontainers Postgres fixture, including 404/409/400 status assertions through the generalized `AppErrorHandler`

### F2-T5 — REST-client parity

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** After F2-T4
- **Paths:** `apps/server/rest-client/learning/goal-skills.rest` (Create)
- **Traceability:** Spec §4 Commands note
- **Rules:** `documentation/rules/rest-layer-rules.md`
- **Exit:** One labeled request per controller route (catalog search, addition preview, add), current methods/paths/parameters/headers, representative bodies, reusable non-secret variables (`{{baseUrl}}`, `{{goalId}}`, `{{skillId}}`, placeholder `{{accessToken}}`), no credentials; manually exercised once against the running local server

## F4 — Integration, review and handoff

- **Status/owner:** `pending` — Orchestrator
- **Depends on:** F2, F3
- Wire the real `apps/server` and `apps/web` dev servers together; run the
  complete `uv run poe test:unit`/`test:integration` and `pnpm --filter web
  test:unit`/`test:integration` suites; execute `apps/web/tests/learning/add-skill-page.test.ts`
  via Playwright CLI against the real stack; perform every `VM-01`..`VM-09`
  manual scenario from the Spec; exercise `goal-skills.rest` for REST-client
  parity evidence; review the applied migration; schedule exactly one
  Implementation Reviewer over the complete integrated diff; verify every
  finding, resume the responsible Builder for any accepted correction, rerun
  the affected exits; record all evidence in `evaluation.md`; then route to
  `conclude-spec`.

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | `apps/server/tests/core/learning/use_cases/*` | CA-01, CA-02, CA-08, CA-09, CA-12, CA-14, CA-15, CA-16, CA-17, CA-19, CA-20 | Spec Validation Contract | `evaluation.md` `EV-1` | `pending` |
| Automated | `apps/server/tests/rest/controllers/learning/*` | CA-01, CA-02, CA-17 | Spec Validation Contract | `evaluation.md` `EV-2` | `pending` |
| Automated | `apps/server/tests/rest/handlers/test_app_error_handler.py` | Cross-cutting error-status mapping | Spec Technical Contract "REST (Shared)" | `evaluation.md` `EV-3` | `pending` |
| Automated | `add-skill-catalog-section.test.tsx` | CA-04..CA-07, CA-13, CA-26 | Spec Validation Contract | `evaluation.md` `EV-4` | `pending` |
| Automated | `add-skill-foundations-dialog.test.tsx` | CA-10, CA-11, CA-16, CA-18, CA-19, CA-21, CA-27..CA-31 | Spec Validation Contract | `evaluation.md` `EV-5` | `pending` |
| Automated | `skill-foundation-row.test.tsx` | CA-11 (both render modes) | Spec Validation Contract | `evaluation.md` `EV-6` | `pending` |
| Runtime | Real server: ownership, atomicity, concurrency, error-status mapping | CA-01, CA-02, CA-12, CA-17, CA-20 | Spec Technical Contract "Solution and runtime flow" | `evaluation.md` `EV-7` | `pending` |
| Manual | VM-01 | CA-01, CA-03, CA-23, CA-24, CA-25 | Spec `VM-01` | `evaluation.md` `EV-8` | `pending` |
| Manual | VM-02 | CA-04..CA-07 | Spec `VM-02` | `evaluation.md` `EV-9` | `pending` |
| Manual | VM-03 | CA-08, CA-17, CA-21, CA-22 | Spec `VM-03` | `evaluation.md` `EV-10` | `pending` |
| Manual | VM-04 | CA-09..CA-11, CA-16, CA-27..CA-30 | Spec `VM-04` | `evaluation.md` `EV-11` | `pending` |
| Manual | VM-05 | CA-13, CA-26 | Spec `VM-05` | `evaluation.md` `EV-12` | `pending` |
| Manual | VM-06 | CA-14, CA-15, CA-30 | Spec `VM-06` | `evaluation.md` `EV-13` | `pending` |
| Manual | VM-07 | CA-18 | Spec `VM-07` | `evaluation.md` `EV-14` | `pending` |
| Manual | VM-08 | CA-19, CA-31 | Spec `VM-08` | `evaluation.md` `EV-15` | `pending` |
| Manual | VM-09 | CA-23, CA-24 | Spec `VM-09` | `evaluation.md` `EV-16` | `pending` |
| Visual | Catalog, collapsed, desktop | CA-01, CA-03, CA-25, CA-26 | `design/yR0iN.png` | Playwright artifact path + `evaluation.md` `EV-17` | `pending` |
| Visual | Catalog, one row expanded | CA-13 | `design/SVHqP.png` | Playwright artifact path + `evaluation.md` `EV-18` | `pending` |
| Visual | Dialog, ≥1 foundation selected | CA-09, CA-10, CA-27, CA-28, CA-29 | `design/o663ai.png` | Playwright artifact path + `evaluation.md` `EV-19` | `pending` |
| Visual | Dialog, no suggested foundations | CA-14 | `design/xzwuv.png` | Playwright artifact path + `evaluation.md` `EV-20` | `pending` |
| Visual | Dialog, all foundations already present | CA-15 | `design/w3glK.png` | Playwright artifact path + `evaluation.md` `EV-21` | `pending` |
| Visual | Dialog, 0 foundations selected | CA-16, CA-27, CA-30 | `design/UXNLJ.png` | Playwright artifact path + `evaluation.md` `EV-22` | `pending` |
| Visual | Dialog, failed submit, selection preserved | CA-19, CA-31 | `design/iQP0U.png` | Playwright artifact path + `evaluation.md` `EV-23` | `pending` |
| Visual | Mobile viewport (no dedicated frame — `design.md` §3.6/§9 fallback) | CA-24 | `documentation/design.md` | Playwright artifact path + `evaluation.md` `EV-24` | `pending` |
| REST client | `learning/skills` route group | Spec Technical Contract REST rows | `apps/server/rest-client/learning/goal-skills.rest` | Parity result + `evaluation.md` `EV-25` | `pending` |

Applicable commands (subset used depends on which paths a given task touches):

```bash
cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe db:migrate "add skill experience goal skill unique constraint"
uv run poe db:upgrade
uv run poe db:downgrade
```

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web test:integration
```

Schedule exactly one read-only Implementation Reviewer in `F4`, after F2 and F3
are both integrated and the automated gates above pass. It checks the complete
candidate diff, cross-Builder contracts, changed paths, generated artifacts
(migration, route registration), REST-client parity, evidence freshness and
both affected UI/server surfaces. The Orchestrator verifies every finding,
records accepted results as `ACH-*` entries in `evaluation.md`, resumes the
responsible Builder for any correction, invalidates stale evidence, and reruns
the affected exits — resuming the same Reviewer rather than replacing it.

**Final handoff condition** — all of the following before routing to
`conclude-spec`:

- F1, F2, F3 and F4 all `completed`;
- Spec revision `2` reconciled against the complete integrated diff;
- every command above passes without lowering a configured floor;
- the generated migration, route registrations and REST-client file reviewed;
- every `CA-01`..`CA-31` and `VM-01`..`VM-09` has current accepted evidence in
  `evaluation.md`;
- every visual row above has a fresh Playwright screenshot compared against its
  design reference, including the mobile fallback;
- `goal-skills.rest` covers all three routes with no credentials;
- the Implementation Reviewer has run once and every verified finding is
  resolved;
- required services (Postgres, Redis, both dev servers) were available or
  their limitation is explicitly recorded; and
- `evaluation.md` is ready for `conclude-spec`.
