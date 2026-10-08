---
title: Gamification achievements implementation plan
status: completed
spec: ./spec.md
spec_revision: 1
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-79
last_updated_at: 2026-10-07
---

# 1. Execution status

- **Spec:** [`spec.md`](./spec.md), revision 1, status `ready`.
- **Why Plan-backed:** two applications (server + web), a new persisted module
  spanning five server layers, one Alembic migration, cross-module Inngest
  messaging with cascade/idempotency risk, and a concrete, low-cost
  parallelism opportunity between server-core and web work.
- **Plan status:** `in_progress` — all six phases (F1–F6) complete. The
  Implementation Reviewer (F6) ran against the complete integrated candidate
  and found two genuine high-severity gaps — `ACH-4` (RF-08/CA-11: the three
  Learning-fact jobs discarded the event's own fact timestamp and always
  dated grants by processing time, defeating retroactive/late-arriving-fact
  backdating) and `ACH-5` (RF-12/CA-17: a retired-catalog "historical"
  achievement was silently dropped from the web UI and the `Achievement`
  type didn't match the server's real response shape for that state) — both
  fixed and re-verified against real infrastructure. Five findings resolved
  in total (`ACH-1` through `ACH-5`); none remain open.
- **Next action:** route to `conclude-spec`. Implementation is complete, all
  automated/runtime/manual evidence is current, and no blocking finding
  remains.
- **Active blockers/external dependencies:** `identity/account.deleted` has no
  current Identity producer (accepted Spec assumption — F4's consumer was
  validated by directly publishing the event in its job-integration test, not
  by a real deletion flow). Not a blocker for this Plan's own exits.
- **Active Builders:** none — all phases complete.
- **Shared/root ownership (Orchestrator-only):** `apps/server/src/shifu/app.py`
  composition (F4), the Alembic migration revision/head coordination (F1), and
  all cross-Builder integration and final validation (F6).

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` is `ready` at revision 1 | Orchestrator | `satisfied` | none |
| Alembic head | Single current head, no merge migration needed | Orchestrator | `satisfied` — confirmed `c9e4f6a7b8c1 (head)` via `uv run alembic heads` | Builder Server Core sets `down_revision = 'c9e4f6a7b8c1'` in F1 |
| Docker/Testcontainers | Required for job (F4) and controller (F4) integration tests | Orchestrator | `satisfied` — `docker info` succeeds; Postgres/Inngest/Redis/Mailpit containers already up | none |
| Local dev servers (web `7000`, API `7777`) | Required for F5 Playwright evidence and manual VM-01/VM-02 | Builder Web (F5) | `satisfied` | Started/stopped for F5 and again for F6's live-stack attempt; none left running |
| Identity `account.deleted` producer | Real end-to-end deletion flow | Identity (future ticket) | `accepted gap` — recorded in Spec | None required here; F4's exit validates the consumer directly against the published event contract |

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `gamification-server-core-builder` | F1 | Domain, interfaces, persistence and migration exist and are structurally valid | — | F3 | `completed` | `check:lint`/`check:types`/`check:architecture` pass; migration applies clean |
| 1 | `gamification-web-builder` | F3 | Achievements tab implementation exists against the Spec's pinned contract, covered by Vitest | — | F1, F2 | `completed` | Web unit/component suite + `check:lint`/`check:types`/`check:architecture` pass |
| 2 | `gamification-server-core-builder` | F2 | Use cases implement the recognition/cascade engine, proven by unit tests | F1 | F3 | `completed` | `uv run poe test:unit` (Gamification subset) + `check:types`/`check:lint` pass |
| 3 | `gamification-server-core-builder-fix` | F4 | REST endpoint, Inngest jobs and `app.py` composition wire the engine end-to-end | F2 | — | `completed` | Controller + job integration tests pass against real Postgres/Inngest; rest-client parity confirmed |
| 4 | `gamification-web-builder` | F5 | Achievements tab verified against the real running backend | F3, F4 | — | `completed` | Playwright suite passes; VM-01/VM-02 evidence captured |
| 5 | Orchestrator | F6 | Implementation Reviewer pass, full command suite, Evaluation ready | F4, F5 | — | `completed` | All findings resolved; every `CA-*`/`VM-*` has accepted evidence |

Two Builders run concurrently in Wave 1/2 (`Builder Server Core`, `Builder
Web`) — within the default limit of three. The Spec pins the REST response
shape and the `Achievement`/`AchievementState` contract exactly, so Web has
everything it needs without waiting on server implementation; paths are
fully disjoint (`apps/server/**` vs `apps/web/**`) until F5's integration.

### F1 — Domain, interfaces, persistence and migration

#### F1-T1 — Domain entities, enums, structures and the leveling function

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** none; parallel with F3
- **Paths:** `apps/server/src/shifu/gamification/core/domain/entities/{gamification_profile,xp_grant,achievement_unlock,rewarded_milestone}.py`, `core/domain/enums/{xp_origin,milestone_type,achievement_family,achievement_criterion_type}.py`, `core/domain/structures/{achievement_definition,achievement_view}.py`, `core/domain/achievement_catalog.py`, `core/domain/leveling.py`
- **Traceability:** substrate for RF-01–RF-08, RF-12; no `CA-*` proven at this phase (structural only, no use case exists yet)
- **Outcome:** every domain type compiles, typechecks, and the 12-row catalog matches the Spec's Technical Contract exactly
- **Rules:** `documentation/rules/core-layer-rules.md`, `documentation/rules/python-conventions-rules.md`
- **Risks/controls:** `GamificationProfile` must declare a literal `id` field (not `account_id`) per the Spec Reviewer's correction — verify against `shared/core/domain/entities/entity.py`'s `_entity_equal`/`_set_entity_attribute`
- **Exit:** `uv run poe check:types`, `uv run poe check:lint` pass for the new paths; no dedicated domain unit tests (per `core-layer-rules.md`, exercised through F2's use-case tests)

#### F1-T2 — Interfaces (ports)

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F1-T1
- **Paths:** `apps/server/src/shifu/gamification/core/interfaces/{gamification_database,gamification_profiles_repository,xp_grants_repository,achievement_unlocks_repository,rewarded_milestones_repository}.py`
- **Traceability:** substrate for all `RF-*`
- **Outcome:** `GamificationDatabase`/`GamificationDatabaseRepositories` and the four repository `Protocol`s match the Spec exactly, including the corrected `remove(profile)`/`remove_many_by_account_id` naming
- **Rules:** `documentation/rules/core-layer-rules.md`
- **Risks/controls:** keep ports narrow — no SQLAlchemy/Inngest types leak into `core/interfaces`
- **Exit:** `uv run poe check:types` passes; shape consumed and proven by F1-T3's repository implementations

#### F1-T3 — SQLAlchemy models, mappers, repositories and migration

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F1-T2
- **Paths:** `apps/server/src/shifu/gamification/database/sqlalchemy/models/{gamification_profile,xp_grant,achievement_unlock,rewarded_milestone}_model.py`, `database/sqlalchemy/mappers/*_mapper.py`, `database/sqlalchemy/repositories/*_repository.py`, `database/sqlalchemy/gamification_database.py`, `apps/server/migrations/versions/<new_revision>_create_gamification_tables.py`, `apps/server/src/shifu/fakers/gamification/entities/*.py`
- **Traceability:** substrate for all `RF-*`; database schema for CA-01–CA-19
- **Outcome:** four tables created with the exact Columns/Indexes/Constraints from the Spec's Database rows; `SqlalchemyGamificationDatabase.transaction()` mirrors `SqlalchemyLearningDatabase`
- **Rules:** `documentation/rules/database-layer-rules.md`, `documentation/rules/core-layer-rules.md`
- **Risks/controls:** set `down_revision = 'c9e4f6a7b8c1'` (confirmed single current head — no merge migration needed); re-run `uv run alembic heads` immediately before generating in case another branch landed a migration first
- **Exit:** `uv run alembic upgrade head` then `uv run alembic downgrade -1` then `uv run alembic upgrade head` all succeed against a disposable database; `uv run poe check:architecture` passes (no forbidden cross-module model import)

### F2 — Use cases (recognition and cascade engine)

#### F2-T1 — `GrantXpUseCase` and the profile lifecycle use cases

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F1
- **Paths:** `apps/server/src/shifu/gamification/core/use_cases/{grant_xp_use_case,create_gamification_profile_use_case,delete_gamification_profile_use_case}.py`, `apps/server/tests/gamification/core/use_cases/test_{grant_xp_use_case,create_gamification_profile_use_case,delete_gamification_profile_use_case}.py`
- **Traceability:** RF-01, RF-05, RF-07, RF-08, RF-11 → CA-01, CA-02, CA-08, CA-09, CA-10, CA-11, CA-14
- **Outcome:** the stabilizing cascade loop, level ratchet, and idempotent profile create/delete are proven by unit tests with autospecced repositories
- **Rules:** `documentation/rules/use-case-testing-rules.md`, `documentation/rules/core-layer-rules.md`
- **Risks/controls:** the cascade loop is the highest-complexity unit in this delivery (XP → level → achievement → XP, recursive); cover the two-simultaneous-threshold case (CA-09) and the no-further-pass-grants-nothing termination explicitly, not just a single-level happy path
- **Exit:** `uv run pytest apps/server/tests/gamification/core/use_cases/test_grant_xp_use_case.py apps/server/tests/gamification/core/use_cases/test_create_gamification_profile_use_case.py apps/server/tests/gamification/core/use_cases/test_delete_gamification_profile_use_case.py -v` passes

#### F2-T2 — Learning-fact recognition use cases

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F2-T1
- **Paths:** `apps/server/src/shifu/gamification/core/use_cases/{recognize_diagnostic_completed,recognize_competency_mastered,recognize_skill_completed}_use_case.py`, matching `tests/gamification/core/use_cases/test_*.py`
- **Traceability:** RF-02, RF-03, RF-04, RF-09, RF-10 → CA-03, CA-04, CA-05, CA-06, CA-07, CA-12, CA-15
- **Outcome:** each recognition use case is idempotent via `RewardedMilestonesRepository.try_add`, no-ops without a profile, and delegates to `GrantXpUseCase`
- **Rules:** `documentation/rules/use-case-testing-rules.md`, `documentation/rules/core-layer-rules.md`
- **Risks/controls:** `RecognizeDiagnosticCompletedUseCase` depends on `CurriculumContentProvider.get_skill_content` — mock it via `create_autospec(CurriculumContentProvider, instance=True)`, not a handwritten fake
- **Exit:** `uv run pytest apps/server/tests/gamification/core/use_cases -v` passes (full module); `uv run poe check:lint`, `uv run poe check:types` pass

#### F2-T3 — `ListAchievementsUseCase`

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F2-T1 (reads the same repositories; no hard dependency on F2-T2)
- **Paths:** `apps/server/src/shifu/gamification/core/use_cases/list_achievements_use_case.py`, `tests/gamification/core/use_cases/test_list_achievements_use_case.py`
- **Traceability:** RF-12 → CA-12, CA-16, CA-17
- **Outcome:** merges the code catalog with held-but-retired unlocks and computes locked-item progress
- **Rules:** `documentation/rules/use-case-testing-rules.md`
- **Risks/controls:** CA-17's retired-catalog-code case needs a fixture unlock row whose code is deliberately absent from `ACHIEVEMENT_CATALOG`
- **Exit:** `uv run pytest apps/server/tests/gamification/core/use_cases/test_list_achievements_use_case.py -v` passes

### F3 — Web implementation (parallel with F1/F2)

#### F3-T1 — Core contract, REST service and provision layer

- **Status/owner:** `completed` — `Builder Web`
- **Depends/parallel:** none; parallel with F1, F2
- **Paths:** `apps/web/src/core/gamification/achievement.ts`, `apps/web/src/rest/services/gamification-service.ts`, `apps/web/src/provision/gamification/{achievements-provider,get-achievements}.ts`
- **Traceability:** substrate for RF-12, RF-13
- **Outcome:** `Achievement`/`AchievementState`/`AchievementFamily` types, `GamificationService.listAchievements(accessToken)`, `AchievementsProvider`, and the `getAchievements` server function all exist and typecheck, mirroring `learning-service.ts`/`GoalDetailProvider`/`get-goal-detail.ts` exactly
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/typescript-conventions-rules.md`
- **Risks/controls:** no dedicated test files here (REST services and provision/server-fn layers are exercised only through the consuming widget/route per `widget-testing-rules.md`); do not add one
- **Exit:** `pnpm --filter web check:types`, `pnpm --filter web check:lint`, `pnpm --filter web check:architecture` pass

#### F3-T2 — Page composition, hooks and nested widgets

- **Status/owner:** `completed` — `Builder Web`
- **Depends/parallel:** F3-T1
- **Paths:** `apps/web/src/ui/gamification/widgets/pages/gamification-page/{index.tsx,use-gamification-page.ts,use-achievements-query.ts}`, `.../profile-summary-card/index.tsx`, `.../achievement-family-section/index.tsx`, `.../achievement-card/index.tsx`, `.../tests/{gamification-page.test.tsx,use-gamification-page.test.ts}`
- **Traceability:** RF-12, RF-13 → CA-16 (mocked-hook level), CA-18, CA-19
- **Outcome:** `GamificationPage` keeps its existing `ModulePageHeader` and replaces the mocked body with real composition grouped by family, with explicit loading/empty/error states
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** `gamification-page.test.tsx` must still assert the existing heading (`'Cada passo merece ser visto.'`) alongside the new achievement/profile content — do not drop that assertion while adding new ones
- **Exit:** `pnpm --filter web test:unit` (Gamification subset) passes with the full state matrix from `widget-testing-rules.md` (loading, success, empty, error); `pnpm --filter web check:types`/`check:lint` pass

### F4 — REST, messaging and composition (depends on F2)

#### F4-T1 — REST endpoint

- **Status/owner:** `completed` — `Builder Server Core`
- **Depends/parallel:** F2-T3
- **Paths:** `apps/server/src/shifu/gamification/rest/controllers/list_achievements_controller.py`, `gamification/rest/router.py` (Modify), `gamification/pipes/gamification_pipe.py`, `apps/server/rest-client/gamification/gamification.rest`, `apps/server/tests/gamification/server/controllers/test_list_achievements_controller.py`
- **Traceability:** RF-12 → CA-16
- **Outcome:** `GET /gamification/achievements` returns field-by-field constructed `AchievementResponse` rows, authenticated via `AuthenticationPipe`
- **Rules:** `documentation/rules/rest-layer-rules.md`, `documentation/rules/controllers-testing-rules.md`
- **Risks/controls:** none beyond the Spec's explicit no-`TypeAdapter` decision
- **Exit:** `uv run pytest apps/server/tests/gamification/server/controllers -v` passes against the real Postgres Testcontainer — **verified independently by the Orchestrator 2026-10-06, 3/3 passed**; `gamification.rest` inspected, one labeled request, no secrets — confirmed

#### F4-T2 — Inngest jobs and registrar

- **Status/owner:** `completed` — `gamification-server-core-builder-fix`
- **Depends/parallel:** F2-T1, F2-T2
- **Paths:** `apps/server/src/shifu/gamification/messaging/inngest/gamification_inngest_messaging.py`, `messaging/inngest/jobs/{create_profile_on_account_activated,purge_profile_on_account_deleted,recognize_diagnostic_completed,recognize_competency_mastered,recognize_skill_completed}_job.py`, matching `apps/server/tests/messaging/inngest/jobs/gamification/test_*.py`; **Remove** `gamification/messaging/jobs/__init__.py` and `gamification/messaging/brokers/__init__.py`
- **Traceability:** RF-01, RF-02, RF-03, RF-04, RF-10, RF-11 → CA-01, CA-03, CA-05, CA-07, CA-13, CA-14
- **Outcome:** five real Inngest functions, each with its own module-local, non-imported `_Payload` Pydantic model (per the Spec Reviewer's correction)
- **Rules:** `documentation/rules/messaging-layer-rules.md`, `documentation/rules/jobs-testing-rules.md`
- **Risks/controls:** CA-13's duplicate-delivery case is the idempotency proof. **Resolved finding:** an initial real-runtime run showed 3/12 job tests failing with `wait_for_database` timeouts. Root cause (confirmed via manual reproduction against the real Postgres, bypassing Inngest): the three failing tests' expected `total_xp`/XP-grant-count values didn't account for `GrantXpUseCase`'s cascade — each test's event was the account's first-ever milestone of its type, so the matching threshold-1 "first X" catalog achievement correctly fired too (e.g. diagnostic 60→85 XP including `diagnostico-primeiro-passo`'s 25 XP). A second, independent bug was also found and fixed in the diagnostic test's own curriculum seed data (missing `CurriculumSequence` rows caused `get_skill_content` to legitimately return `None`, which correctly made the use case no-op). Fixed by correcting the three test files' expectations and seed data — zero production-code changes were needed.
- **Exit:** `uv run poe test:jobs` passes — **verified independently by the Orchestrator 2026-10-06: 12/12 passed (all modules, including all 5 Gamification job tests), 29.57s**

#### F4-T3 — Application composition

- **Status/owner:** `completed` — Orchestrator (root composition file, shared ownership)
- **Depends/parallel:** F4-T1, F4-T2
- **Paths:** `apps/server/src/shifu/app.py` (Modify)
- **Traceability:** substrate for every `RF-*` requiring a live route or job
- **Outcome:** `gamification_database` constructed beside the existing module databases; `GamificationInngestMessaging.register_jobs` added to `job_group_registrars`; `app.state.gamification_database` set
- **Rules:** `documentation/rules/server-app-layer-rules.md`, `documentation/rules/python-conventions-rules.md`
- **Risks/controls:** this file is already shared across every module's composition — re-verify no other in-flight branch touched the same `job_group_registrars` list before merging
- **Exit:** `uv run poe check:types`, `check:lint`, `check:architecture` all pass on the modified `app.py` (independently reran 2026-10-06); controller suite (F4-T1) boots the real `FastAPIApp.register()` with this composition and passes 3/3

### F5 — Browser integration (depends on F3, F4)

#### F5-T1 — Playwright route integration and manual evidence

- **Status/owner:** `completed` — `gamification-web-builder`
- **Depends/parallel:** F3-T2, F4-T1, F4-T2, F4-T3
- **Paths:** `apps/web/tests/gamification/gamification-page.test.ts` (Modify — extend, keep existing heading/redirect assertions)
- **Traceability:** RF-12, RF-13 → CA-18; VM-01, VM-02
- **Outcome:** the real route renders real achievement/profile data end-to-end; desktop and mobile viewports both verified
- **Rules:** `documentation/rules/widget-testing-rules.md`
- **Risks/controls:** start the FastAPI app and web dev server for this phase only, with a seeded account that has at least one unlocked achievement (diagnose+master+complete a seeded Habilidade, or seed directly); stop both processes after evidence capture. **Resolved finding (`ACH-3`):** the live VM-01 screenshot revealed the level card and achievement icons rendering in Selo red instead of the design system's reserved Latão (gold/brass) hue — a real violation of `documentation/design.md` P1 ("Latão nunca toca em nada pedagógico... Selo"), caused by the Latão CSS variables never having been added to `apps/web/src/ui/shared/styles/global.css` (not a Rule violation at authoring time — the token didn't exist yet to ignore). Orchestrator added the five `--latao-*`/`--on-latao` variables (exact values from `design.md` §3.2) and switched `ProfileSummaryCard`/`AchievementCard`'s obtained-state styling to use them; re-verified lint/types/the Gamification Vitest+Playwright suites green, and recaptured the visual evidence to confirm.
- **Exit:** `pnpm --filter web test:integration` (Gamification suite) passes — **verified independently, 2/2**; VM-01 (desktop) and VM-02 (mobile) manual steps executed with fresh Playwright CLI screenshots saved as evidence (not committed) — VM-01 recaptured after the Latão fix

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | `gamification/core/use_cases` (unit, 28 tests) | CA-01, CA-02, CA-05–CA-12, CA-14, CA-15, CA-17 | Spec Validation Contract | `evaluation.md` Acceptance coverage table + `EV-2`, `EV-12` | `passed` |
| Runtime | `gamification/server/controllers` (real Postgres Testcontainer, 3 tests) | CA-16 | Technical Contract | `evaluation.md` `EV-6` | `passed` |
| Runtime | `messaging/inngest/jobs/gamification` (real Inngest + Postgres, 13 tests) | CA-01, CA-03, CA-05, CA-07, CA-11, CA-13, CA-14 | Technical Contract | `evaluation.md` `EV-7`, `EV-8`, `EV-12` | `passed` |
| Automated | `ui/gamification/widgets/pages/gamification-page` (Vitest, 11 tests) | CA-16 (mocked), CA-17, CA-18, CA-19 | Spec Validation Contract | `evaluation.md` `EV-4`, `EV-13` | `passed` |
| Automated | `apps/web/tests/gamification` (Playwright, 2 tests) | CA-18 | Spec Validation Contract | `evaluation.md` `EV-9`, `EV-13` | `passed` |
| Manual | VM-01 — desktop achievements tab | CA-16, CA-18 | Spec `VM-01` | `evaluation.md` Manual and visual evidence table | `passed` |
| Manual | VM-02 — mobile achievements tab | CA-18 | Spec `VM-02` | `evaluation.md` Manual and visual evidence table | `passed` |
| REST client | `gamification` route group | CA-16, Technical Contract | `apps/server/rest-client/gamification/gamification.rest` | Confirmed by Implementation Reviewer: one labeled request, current contract, no secrets | `passed` |

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
uv run poe test:jobs
uv run poe build
```

The single read-only [`Implementation Reviewer`](../../../agents/implementation-reviewer-agent.md)
ran in **F6** after F4 and F5 were both `completed` and the commands above
passed. Scope as planned: the complete integrated diff across both
applications, cross-Builder contract consistency, every changed/generated
path, the migration, REST-client parity, and evidence freshness. It found two
genuine high-severity findings (`ACH-4`, `ACH-5` — see `evaluation.md`), both
fixed and re-verified by the Orchestrator rerunning the exact gates the
Reviewer itself used; the Reviewer was not re-invoked for the narrow,
mechanically-verified corrections (see `evaluation.md`'s Implementation
Reviewer Result block for the explicit rationale).

**Final handoff condition — all met:**

- F1–F6 all `completed`;
- the complete diff reconciled against Spec revision 1 (no Contract change —
  both post-review findings were in-Contract defects, not scope changes);
- every command above passes without lowering configured floors;
- the migration applies and reverses cleanly; `app.py`'s diff reviewed for
  composition correctness;
- every `CA-01`…`CA-19` and `VM-01`/`VM-02` has current accepted evidence in
  `evaluation.md`;
- `apps/server/rest-client/gamification/gamification.rest` is present and
  route-complete;
- the Implementation Reviewer completed and every verified finding is
  resolved;
- `evaluation.md` is `ready`.

Ready for `conclude-spec`.

# 5. Execution log

- **2026-10-05 — F1/F3 kicked off in parallel**
  - **Finding/result:** both Builders activated per the Plan's Wave 1
    parallelism rationale; no overlap.
  - **Next action:** integrate once both report.
- **2026-10-05/06 — Session rate-limit interruptions (3 occurrences)**
  - **Finding/result:** `gamification-server-core-builder`,
    `gamification-web-builder` (F5 attempt), and the first Implementation
    Reviewer attempt were each interrupted mid-task by the account's session
    usage limit, not by any code or Contract defect. Each was resumed/relaunched
    after confirming the limit had reset; in every case, work already written
    to disk survived intact (verified via `git status`/file inspection before
    resuming) — only live agent session context was lost.
  - **Next action:** none — a known environment characteristic, not a defect.
- **2026-10-06 — `ACH-1` found during F3 (in-Contract correction)**
  - **Finding/result:** `gamification-web-builder` flagged a real Technical
    Contract gap — the REST response had no profile data for
    `ProfileSummaryCard` despite RF-13 requiring it. Fixed in `spec.md`
    directly (`GET /gamification/achievements` → bundled `AchievementsOverview`),
    revision unchanged at 1.
  - **Next action:** both Builders apply the corrected shape.
- **2026-10-06 — `ACH-2` found during F4-T2 verification (test defect)**
  - **Finding/result:** 3/12 real-Inngest job tests failed; root-caused to the
    achievement cascade's bonus XP not being accounted for in 3 tests'
    expectations, plus a missing curriculum seed row in one. Zero production
    code changed.
  - **Next action:** none — resolved same day, 12/12 confirmed.
- **2026-10-06 — `ACH-3` found during F5 visual re-verification (design nonconformance)**
  - **Finding/result:** Orchestrator's independent VM-01 recapture showed Selo
    red instead of the design system's reserved Latão hue on Gamification
    elements. Added the missing `--latao-*` CSS variables and switched the two
    affected components.
  - **Next action:** none — resolved same day, visually reconfirmed.
- **2026-10-07 — F6 Implementation Reviewer found `ACH-4` and `ACH-5` (in-Contract defects)**
  - **Finding/result:** `ACH-4` — the three Learning-fact jobs discarded the
    event's own fact timestamp, defeating RF-08/CA-11's retroactive-backdating
    requirement for any real late-arriving fact. `ACH-5` — the web UI silently
    dropped retired-catalog "historical" achievements and the `Achievement`
    type didn't match the server's real response shape for that state,
    violating RF-12/CA-17. Both fixed, with new tests closing the exact
    coverage gaps the Reviewer identified (a real-Inngest backdating proof and
    a web historical-rendering test).
  - **Next action:** none — all gates reconfirmed green; routing to
    `conclude-spec`.
