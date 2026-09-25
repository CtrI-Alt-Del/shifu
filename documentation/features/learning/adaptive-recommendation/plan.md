---
title: Learning adaptive recommendation implementation plan
status: completed
spec: ./spec.md
spec_revision: 1
evaluation: ./evaluation.md
last_updated_at: 2026-09-24
---

# Execution status

Spec revision 1 is implemented and validated. Curriculum catalog, Learning persistence/policy, activation, diagnostic, web routes and additive migrations integrate without changing legacy experiences. All phases are complete. Existing workspace changes outside this feature were preserved. The Orchestrator owns SDD artifacts, migration coordination, shared integration and final validation.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Revision 1 ready; independent Spec review accepted | Orchestrator | passed | Freeze revision |
| Canonical PRDs | Learning 83066881 v17 and Curriculum 83034113 v9 read in full | Orchestrator | passed | Recheck versions at conclusion |
| Existing code | Legacy choice paths and pre-existing changes inventoried | Orchestrator | passed | Preserve diffs |
| Curriculum content | Valid v2 choice diagnostic and two learning Activities per difficulty/Concept | Curriculum Builder | passed | Dedicated development Skill validated without shared seed/reset |
| Runtime validation | Disposable DB, authenticated account and local applications | Orchestrator | passed | HTTP/Testcontainers, real Inngest, Playwright route tests and visual inspection passed; browser transport mocks are recorded separately |

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Curriculum Builder | F1 | Concept catalog, criteria, validated snapshots and v2 development content | Spec ready | Learning policy pure domain | completed | Curriculum domain tests, snapshot consumption and eligible development Skill pass |
| 1 | Learning Builder | F2 | Versioned Concept policy and state | Spec ready | Curriculum catalog | completed | Policy domain tests pass |
| 2 | Learning Builder | F3 | Choice evaluation, diagnostic and activation | F1, F2, migration | F1-T2 seed fixture | completed | Job/controller integration passes |
| 3 | Web Builder | F4 | Creation/diagnostic and recommendation UI | F3 API contract | F3 server delivery | completed | Widget/route tests and browser checks pass |
| 4 | Orchestrator | F5 | Migration, integration and evidence | F1–F4 | — | completed | Server/Web gates, disposable HTTP/job and visual evidence pass |

### F1 — Curriculum catalog

#### F1-T1 — Validated Concept content

- **Status/owner:** completed — Curriculum Builder; Material content and Skill catalog provider follow-ups passed; consuming DB integration remains in F3/F5.
- **Depends/parallel:** Spec ready; parallel with F2 pure policy.
- **Paths:** `apps/server/src/shifu/curriculum/**`, `apps/server/src/shifu/shared/core/domain/structures/curriculum_*`, `apps/server/src/shifu/shared/database/seed_data.py`, focused Curriculum domain and consuming controller/job test fixtures. Excludes Learning, Web, migrations, and SDD artifacts.
- **Traceability:** Curriculum RP-05/06; RF-01/02/05/06; CA-01/04.
- **Outcome:** validated, executable per-Concept catalog with frozen choice criteria and Activity prerequisites.
- **Rules:** `documentation/rules.md` selected Curriculum/core/database/provider/testing packs; architecture and modules.
- **Risks/controls:** existing catalog cannot satisfy v2 coverage; keep legacy content valid for v1 and create explicit v2 fixtures.
- **Exit:** focused domain tests and consuming integration tests, type/lint checks; report exact schema requirements to Orchestrator.

#### F1-T2 — Isolated v2 development Skill

- **Status/owner:** completed — Curriculum Builder.
- **Depends/parallel:** F1-T1 catalog; parallel with F3 Learning server integration.
- **Paths:** `apps/server/src/shifu/curriculum/database/curriculum_seeder.py`, `apps/server/src/shifu/shared/database/seed.py`, `apps/server/src/shifu/shared/database/seed_data.py`, focused existing boundary tests. Excludes migrations, Learning, Web and SDD artifacts.
- **Traceability:** Curriculum RP-05/06 and Learning RP-06/07; RF-01/09; CA-01/07.
- **Outcome:** new dedicated one-Competency Skill with one Concept, official Material, three ordered diagnostic Activities and two executable choice learning Activities per difficulty; legacy seed rows remain unchanged.
- **Rules:** `documentation/rules.md` selected Python/database/messaging/testing packs, architecture and modules.
- **Risks/controls:** seed is an explicit command and may reset local data; change seed construction only, never execute reset against shared services.
- **Exit:** pure build/snapshot validation and real disposable seeded application scenario; report exact results without running shared seed.

### F2 — Learning policy

#### F2-T1 — Deterministic versioned policy

- **Status/owner:** completed — Learning Builder; integrated focused domain/static checks passed.
- **Depends/parallel:** Spec ready; parallel with F1 only for pure policy files.
- **Paths:** `apps/server/src/shifu/learning/core/domain/**` and focused domain tests. Excludes Curriculum, Web, migrations, REST, SDD artifacts and existing changed user paths.
- **Traceability:** Learning RP-07/15/16/17/27/28; RF-02–06/08; CA-02–04/06.
- **Outcome:** valid/inconclusive Concept evidence, stable recomputation, mastery/regression and deterministic reasoned recommendation.
- **Rules:** selected Python/core/unit-testing packs, architecture and modules.
- **Risks/controls:** do not reinterpret v1 scalar progress as Concept evidence; pure policy consumes explicit snapshots and observations.
- **Exit:** focused domain tests for replacement order, coverage, regressions, prerequisites and gaps; report storage contract.

### F3 — Learning delivery

#### F3-T1 — Persisted activation and diagnostic

- **Status/owner:** completed — Learning Builder; 75 Learning tests and full server CI pass, with review fixes integrated.
- **Depends/parallel:** F1, F2, additive migration coordinated by Orchestrator.
- **Paths:** `apps/server/src/shifu/learning/core/use_cases/**`, `database/sqlalchemy/**`, `rest/**`, `messaging/**`, `apps/server/rest-client/learning/**`, focused Learning tests. Excludes Curriculum, Web, migrations, SDD artifacts and unrelated changed files.
- **Traceability:** Learning RP-03–08/15–18/25/27/28; RF-02–09; CA-02–07.
- **Outcome:** authenticated creation, ordered private diagnostic, fixed baseline and v2 recommendation while v1 remains stable.
- **Rules:** selected Python/core/database/provision/REST/controller/messaging/testing packs.
- **Risks/controls:** diagnostic result/event leakage, replay and authorization; assert at server boundary and consuming event handlers.
- **Exit:** focused job/controller integration with persistence, authorization, idempotency and REST-client parity for every changed route.

### F4 — Web journey

#### F4-T1 — Learner journey and recommendation explanation

- **Status/owner:** completed — Web Builder; final route/widget tests and browser inspection passed.
- **Depends/parallel:** F3 API contract.
- **Paths:** `apps/web/src/core/learning/**`, `apps/web/src/rest/**`, `apps/web/src/routes/learning/**`, `apps/web/src/ui/learning/**`, matching `apps/web/tests/**` and colocated widget tests. Excludes pre-existing changed shared UI files, Pencil document and SDD artifacts.
- **Traceability:** Learning RP-03–08/17/18/25; RF-06/07/09; CA-04/05/07.
- **Outcome:** create/start/complete diagnosis, see consolidated output and reasoned Material+Activity recommendation.
- **Rules:** selected UI/routing/widget-testing/TypeScript packs, `documentation/design.md`, architecture and modules.
- **Risks/controls:** preserve current choice screens and design tokens; use Playwright CLI for visible behavior, keyboard and narrow viewport.
- **Exit:** route/widget tests; authenticated browser journey, fresh screenshots, console/network and persistence evidence.

### F5 — Integrated candidate

#### F5-T1 — Migration and validation

- **Status/owner:** completed — Orchestrator; b8 additive migration, disposable HTTP, real Inngest, Web integration and browser checks passed.
- **Depends/parallel:** F1–F4.
- **Paths:** `apps/server/migrations/versions/**`, SDD artifacts, integration fixes only after explicit reassignment.
- **Traceability:** all RF/CA; CI-01–04 and VM-01–03.
- **Outcome:** upgrade-safe integrated candidate with current evidence.
- **Rules:** all selected packs and implementation review process.
- **Risks/controls:** preserve legacy rows and unrelated workspace changes; inspect every diff and use disposable database.
- **Exit:** all applicable gates, manual scenarios, single independent implementation review and accepted Evaluation.

# Validation and handoff

The Orchestrator validates migrations and every integrated boundary, records CI/VM/EV/ACH evidence, checks route-group REST-client parity and preserves pre-existing changes. Web visual changes require fresh Playwright CLI screenshots at 1440×900 and 390×844, keyboard/focus and console/network checks. No design reference was supplied for new screens; existing Shifu tokens and relevant Pencil handoff must be inspected before visual implementation. Final review and conclusion follow the ready Spec.
