---
title: Learning Competency detail implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 3
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-72
last_updated_at: 2026-09-22
---

# Execution status

- **Spec:** [`spec.md`](./spec.md), revision `3`, status `completed`.
- **Why Plan-backed execution:** This slice crosses Shared, Learning, Curriculum,
  Identity, FastAPI composition, PostgreSQL/Alembic, the web BFF/RPC/REST layers,
  TanStack routing, responsive widgets, generated artifacts, and real browser
  validation. It also has migration/backfill risk and multiple non-overlapping
  ownership boundaries.
- **Plan:** `in_progress`; reopened at `F5` migration validation for ACH-022.
- **Outcome:** The migration backfill correction and fresh CA-10 evidence are
  complete; conclusion is the remaining handoff step.
- **Active blockers/dependencies:** Three pre-existing web identity handler
  integration tests still return `503` in the local auth fixture; all new
  Learning feature gates and server integration gates pass. No shared volume or
  database reset is authorized.
- **Builders:** Builder Core, Builder Web, and Builder Server assignments are
  complete after the canonical authority gate was cleared against current PRD
  content `83066881` version `13`.
- **Shared ownership:** The Orchestrator owns package installation and lockfiles,
  `FastAPIApp` composition, root web composition, Alembic migration generation and
  review, generated route metadata, cross-Builder integration, SDD artifacts, and
  final validation. Builder paths below do not overlap those shared/generated
  boundaries.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `documentation/features/learning/competency-detail/spec.md` is `completed` at revision `3` | Orchestrator | `completed` | Exact revision and current PRD authority reconciled |
| Canonical product authority | Complete Learning PRD, content ID `83066881`, current version `13`, read through Atlassian Shifu MCP | Orchestrator | `ready` — full page reread completed 2026-09-22 | Freeze Spec revision `3`; no contract drift found |
| Delivery source | Jira `SHIFU-72` is available and matches the Spec's objective, scope, validation, and exclusions | Orchestrator | `ready` | Preserve the external issue as read-only authority |
| Design authority | `design/handoff.md`, ten PNG references, and the accepted released-non-focus assumption are inventoried | Orchestrator | `ready` | Use saved references; do not mutate Pencil |
| Web dependency | `@tanstack/react-query` `^5.103.2` is added through pnpm and the lockfile is regenerated | Orchestrator | `ready` | F1-T1 complete; validate again with consuming code |
| Disposable persistence | PostgreSQL/Testcontainers fixture can run Alembic from `c4d82f1e7a30` to the new head | Builder Server / Orchestrator | `completed` | Corrected upgrade, safe-abort regression, seed, and controller integration passed |
| Browser validation | Playwright Chromium and the repository's shared fixture are available | Builder Web / Orchestrator | `completed` | VM-01 real seeded desktop/mobile run passed; owning page/layout integration suites passed |

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Orchestrator` | F1 | Required Query dependency is installed through the owning manifest and lockfile | Canonical PRD gate | — | `completed` | `pnpm --filter web check:types` resolves the dependency and `pnpm-lock.yaml` contains only the generated dependency change |
| 2 | `Builder Core` | F2 | Shared Curriculum snapshots and the Learning competency-detail use case/projection contract are implemented with the unit matrix | F1; current Spec revision `3` | Builder Web | `completed` | Focused Core matrix passes; aggregate typing is closed by F4 adapter implementation |
| 2 | `Builder Web` | F3 | BFF/RPC/REST contracts, detail widgets, route sources, and web tests cover the declared UI contract | F1; Core DTO/transport contract in Spec | Builder Core | `completed` | Focused Web suites, lint, architecture, build, and generated-route type check pass |
| 3 | `Builder Server` | F4 | Learning/Curriculum adapters, persistence integrity, protected HTTP route, REST artifact, seed scenarios, and controller integration are complete | F2; F1 | Builder Web | `completed` | Server lint/architecture/types and 11-case feature controller suite pass; full collection 17/17 after ACH-022 correction |
| 4 | `Orchestrator` | F5 | Composition, migration, generated metadata, integrated application gates, and runtime evidence are reconciled | F3 and F4 | — | `completed` | Corrected migration activity identity predicate and refreshed disposable persistence evidence |
| 5 | `Implementation Reviewer` | F6 | One read-only audit checks the integrated candidate, cross-Builder contracts, REST parity, evidence freshness, and UI/server surfaces | F5 automated/evidence baseline | Orchestrator integrated sensors may run in parallel | `completed` | Final advisory audit completed; conditional GO issued with ACH-018 as the sole accepted limitation |
| 6 | `Orchestrator` | F7 | Final handoff is complete | F6 and any correction exits | — | `in_progress` | Conclude the corrected candidate with current evidence |

### F1 — Shared dependency preparation

#### F1-T1 — Install the declared web server-state dependency

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** Starts only after the canonical PRD gate is cleared; blocks F2 and F3.
- **Paths:** `apps/web/package.json`; `pnpm-lock.yaml`.
- **Traceability:** Spec Technical Contract server-state decision; supports `RF-08`, `RF-09`, `CA-08`, and `CA-09`.
- **Outcome:** `@tanstack/react-query` is added as `^5.103.2` through pnpm with no unrelated manifest or lockfile changes.
- **Rules:** `documentation/tooling.md`; `documentation/rules.md`; `documentation/rules/typescript-conventions-rules.md`.
- **Risks/controls:** The current worktree contains unrelated user edits; inspect the dependency diff and preserve all unrelated changes. Do not hand-edit the lockfile.
- **Exit:** Run `pnpm --filter web add @tanstack/react-query@^5.103.2`, review `git diff -- apps/web/package.json pnpm-lock.yaml`, and run `pnpm --filter web check:types` after the consuming code exists.

### F2 — Core contracts and deterministic detail projection

#### F2-T1 — Add Shared Curriculum snapshots and Learning projection contracts

- **Status/owner:** `completed` — Builder Core
- **Depends/parallel:** F1; may run in parallel with F3 after the Spec contract is frozen.
- **Paths:** `apps/server/src/shifu/shared/core/domain/structures/curriculum_content.py`; `apps/server/src/shifu/shared/core/domain/structures/__init__.py`; `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py`; `apps/server/src/shifu/shared/core/interfaces/__init__.py`; `apps/server/src/shifu/learning/core/domain/enums/competency_availability.py`; `apps/server/src/shifu/learning/core/domain/enums/__init__.py`; `apps/server/src/shifu/learning/core/domain/structures/official_activity_result.py`; `apps/server/src/shifu/learning/core/domain/structures/competency_material_detail.py`; `apps/server/src/shifu/learning/core/domain/structures/competency_activity_detail.py`; `apps/server/src/shifu/learning/core/domain/structures/available_competency_detail.py`; `apps/server/src/shifu/learning/core/domain/structures/unavailable_competency_detail.py`; `apps/server/src/shifu/learning/core/domain/structures/competency_detail.py`; `apps/server/src/shifu/learning/core/domain/structures/__init__.py`; `apps/server/src/shifu/learning/core/domain/errors/competency_detail_not_found_error.py`; `apps/server/src/shifu/learning/core/domain/errors/__init__.py`; `apps/server/src/shifu/learning/core/interfaces/activity_evaluations_repository.py`; `apps/server/src/shifu/learning/core/use_cases/get_competency_detail_use_case.py`; `apps/server/src/shifu/learning/core/use_cases/__init__.py`.
- **Traceability:** `RP-08`, `RP-15`, `RP-16`, `RP-17`, `RP-25`, `JN-06`, `JN-10`; `RF-01`–`RF-06`, `RF-10`; `CA-01`–`CA-06`, `CA-10`.
- **Outcome:** Framework-independent immutable snapshots, discriminated detail projections, safe not-found error, and the ownership-first deterministic projection contract exist exactly as specified.
- **Rules:** `documentation/rules/core-layer-rules.md` (framework independence, immutable structures, ports, module direction, transport-neutral errors); `documentation/rules/python-conventions-rules.md`.
- **Risks/controls:** Do not move Learning decisions into Shared or Curriculum, expose ORM types, or add undocumented behavior. Keep recommendation/focus logic in the Learning use case and preserve the no-write contract.
- **Exit:** `cd apps/server && uv run poe check:types && uv run poe check:architecture`; inspect exports and confirm no Core import reaches FastAPI, SQLAlchemy, or another business module.

#### F2-T2 — Prove use-case behavior and side-effect absence

- **Status/owner:** `completed` — Builder Core
- **Depends/parallel:** F2-T1; sequential within Builder Core.
- **Paths:** `apps/server/tests/learning/core/use_cases/test_get_competency_detail_use_case.py`.
- **Traceability:** All use-case cases in the Spec Validation Contract; `CA-01`–`CA-06`, `CA-10`.
- **Outcome:** Autospecced Learning/provider matrix proves ownership-first rejection, availability, order, latest official scores, focus-returned derivation, recommendation thresholds/ties/repeat avoidance, and zero writes/events.
- **Rules:** `documentation/rules/use-case-testing-rules.md` (module-first path, `Test<GetUseCase>` class, autospecced ports, `test_should_` names, no infrastructure); `documentation/rules/core-layer-rules.md`.
- **Risks/controls:** Keep repository/provider mocks typed and fresh per case; do not duplicate controller or database behavior in unit tests.
- **Exit:** `cd apps/server && uv run pytest tests/learning/core/use_cases/test_get_competency_detail_use_case.py`; then run `uv run poe test:unit` after integration.

### F3 — Web BFF, query, UI, and typed route contracts

#### F3-T1 — Build validated REST/RPC contracts and context composition values

- **Status/owner:** `completed` — Builder Web
- **Depends/parallel:** F1 and the exact transport contract in Spec; may run in parallel with F2.
- **Paths:** `apps/web/src/core/learning/competency-detail.ts`; `apps/web/src/rest/services/learning-service.ts`; `apps/web/src/rpc/actions/learning/get-competency-detail-action.ts`; `apps/web/src/rpc/services/learning-service.ts`; `apps/web/src/ui/shared/contexts/rpc-context/index.tsx`; `apps/web/src/ui/shared/contexts/rpc-context/types/rpc-context-value.ts`; `apps/web/src/ui/shared/contexts/rpc-context/types/index.ts`; `apps/web/src/ui/shared/contexts/rpc-context/use-rpc-context-provider.ts`; `apps/web/src/ui/shared/hooks/use-rpc-context.ts`.
- **Traceability:** `RF-01`–`RF-08`, `RF-10`; `CA-01`–`CA-08`, `CA-10`; browser-credential and query-lifecycle restrictions.
- **Outcome:** The server-only action obtains the session/token, the REST service maps the exact GET contract, the UI service validates/maps the safe union, and the root-facing context exposes only the typed UI service.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`; `documentation/rules/ui-layer-rules.md` (service factories, context shape, query/action ownership, credential boundary); `documentation/rules/rest-layer-rules.md`.
- **Risks/controls:** Never expose the bearer token through context, route params, query data, browser storage, logs, or client errors. Do not add dedicated tests for REST/action/query hooks; cover them through consumers and routes.
- **Exit:** `pnpm --filter web check:types && pnpm --filter web check:architecture`; consumer tests must verify the exact method/path/IDs and safe response/error mapping.

#### F3-T2 — Implement the competency-detail widget tree and shared primitive extensions

- **Status/owner:** `completed` — Builder Web
- **Depends/parallel:** F3-T1; sequential within Builder Web.
- **Paths:** `apps/web/src/ui/learning/widgets/pages/competency-detail-page/index.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/use-competency-detail-page.ts`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-detail-header/index.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-detail-header/tests/competency-detail-header.test.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-detail-feedback/index.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-detail-feedback/tests/competency-detail-feedback.test.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-content-list/index.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-content-list/tests/competency-content-list.test.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-content-list/competency-content-row/index.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/competency-content-list/competency-content-row/tests/competency-content-row.test.tsx`; `apps/web/src/ui/learning/widgets/pages/competency-detail-page/tests/competency-detail-page.test.tsx`; `apps/web/src/ui/shared/widgets/components/progress-meter/index.tsx`; `apps/web/src/ui/shared/widgets/components/progress-meter/tests/progress-meter.test.tsx`; `apps/web/src/ui/shared/widgets/components/icon/index.tsx`; `apps/web/src/ui/shared/widgets/components/icon/tests/icon.test.tsx`.
- **Traceability:** `RF-02`–`RF-09`; `CA-02`–`CA-09`; `VM-01`–`VM-06`.
- **Outcome:** Available focus, focus-returned, released non-focus, unavailable, loading, private absence, error/recovery, ordered content, accessible recommendation, pt-BR copy, keyboard focus, and mobile layout render through the declared widget boundaries.
- **Rules:** `documentation/design.md`; `documentation/features/learning/competency-detail/design/handoff.md`; `documentation/rules/ui-layer-rules.md` (widget/context/navigation/token boundaries); `documentation/rules/widget-testing-rules.md` (typed hook mocks, real child composition, semantic assertions); `documentation/rules/typescript-conventions-rules.md`.
- **Risks/controls:** Use existing dark-only tokens and shared `Anchor`/`Icon`/`ProgressMeter`; do not import Lucide directly, add feature-local tokens, define local named child components, or use color-only state.
- **Exit:** `pnpm --filter web test:unit`; inspect semantic roles, visible focus, 44px targets, no overflow, and exact route/param assertions in the component suite.

#### F3-T3 — Register protected detail and contract-only destination routes

- **Status/owner:** `completed` — Builder Web
- **Depends/parallel:** F3-T2; generated route metadata remains Orchestrator-owned in F5.
- **Paths:** `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/index.tsx`; `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId.tsx`; `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId.tsx`; `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId.tsx`; `apps/web/tests/learning/learning-page.test.ts`; `apps/web/tests/learning/competency-detail-page.test.ts`.
- **Traceability:** `RF-01`, `RF-07`–`RF-09`; `CA-01`, `CA-04`–`CA-09`; `VM-01`, `VM-04`, `VM-06`.
- **Outcome:** Protected dynamic route reaches the page with explicit IDs; Skill, Material, and Activity contracts authenticate then terminate at generic `notFound()` without placeholder rendering or side effects.
- **Rules:** `documentation/rules/web-app-routing-rules.md` (literal route declarations, middleware and typed params); `documentation/rules/ui-layer-rules.md`; `documentation/rules/widget-testing-rules.md` (route assertions stay in the owning page/layout suite).
- **Risks/controls:** Do not hand-edit `routeTree.gen.ts`, concatenate URLs, cast route types, or let the Skill index intercept Competency descendants. Route suites use the shared Playwright fixture and mocked transport only.
- **Exit:** After F5 generation, run the owning page suites with `pnpm --filter web test:integration -- tests/learning` and verify final URLs, auth redirects, request IDs, generic not-found boundaries, keyboard navigation, and visible outcomes.

### F4 — Server adapters, persistence, REST, and real HTTP boundary

#### F4-T1 — Implement module transactions, provider, integrity metadata, and seed scenarios

- **Status/owner:** `completed` — Builder Server
- **Depends/parallel:** F2; may proceed in parallel with F3 after Core contracts land.
- **Paths:** `apps/server/src/shifu/curriculum/database/sqlalchemy/curriculum_database.py`; `apps/server/src/shifu/curriculum/database/sqlalchemy/__init__.py`; `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`; `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/__init__.py`; `apps/server/src/shifu/learning/database/sqlalchemy/learning_database.py`; `apps/server/src/shifu/learning/database/sqlalchemy/__init__.py`; `apps/server/src/shifu/learning/database/sqlalchemy/models/competency_progress_model.py`; `apps/server/src/shifu/learning/database/sqlalchemy/models/skill_experience_model.py`; `apps/server/src/shifu/learning/database/sqlalchemy/models/goal_model.py`; `apps/server/src/shifu/learning/database/sqlalchemy/models/activity_attempt_model.py`; `apps/server/src/shifu/curriculum/database/sqlalchemy/models/competency_model.py`; `apps/server/src/shifu/curriculum/database/sqlalchemy/models/material_model.py`; `apps/server/src/shifu/curriculum/database/sqlalchemy/models/activity_model.py`; `apps/server/src/shifu/learning/database/sqlalchemy/mappers/competency_progress_mapper.py`; `apps/server/src/shifu/learning/database/sqlalchemy/repositories/activity_evaluations_repository.py`; `apps/server/src/shifu/shared/database/seed_data.py`.
- **Traceability:** `RF-01`–`RF-04`, `RF-06`, `RF-10`; `CA-01`–`CA-06`, `CA-10`; persistence and read-consistency contracts.
- **Outcome:** Learning/Curriculum have separate read-only transaction owners, the provider returns complete ordered Shared snapshots, hard scores round-trip, semantic uniqueness/index metadata is declared, and deterministic local scenarios exist.
- **Rules:** `documentation/rules/database-layer-rules.md` (single transaction owner, models/mappers/repositories, migration/seed ownership, behavior-boundary testing); `documentation/rules/provision-layer-rules.md`; `documentation/rules/core-layer-rules.md`.
- **Risks/controls:** Audit duplicates and legacy mastered rows before applying uniqueness/backfill; never delete/merge or invent scores. Do not import Learning into Curriculum or leak ORM models through Shared.
- **Exit:** `cd apps/server && uv run poe check:architecture && uv run poe check:types`; inspect transaction commit/rollback/close paths and exercise persistence through F4-T2's real controller boundary.

#### F4-T2 — Expose the protected HTTP operation and route-complete REST artifact

- **Status/owner:** `completed` — Builder Server
- **Depends/parallel:** F4-T1 and F2; sequential within Builder Server.
- **Paths:** `apps/server/src/shifu/shared/pipes/authentication_pipe.py`; `apps/server/src/shifu/shared/pipes/__init__.py`; `apps/server/src/shifu/identity/pipes/identity_pipe.py`; `apps/server/src/shifu/learning/pipes/learning_pipe.py`; `apps/server/src/shifu/learning/pipes/__init__.py`; `apps/server/src/shifu/learning/rest/controllers/get_competency_detail_controller.py`; `apps/server/src/shifu/learning/rest/controllers/__init__.py`; `apps/server/src/shifu/learning/rest/router.py`; `apps/server/src/shifu/rest/handlers/app_error_handler.py`; `apps/server/rest-client/learning/competencies.rest`; `apps/server/tests/learning/server/controllers/test_get_competency_detail_controller.py`.
- **Traceability:** `RF-01`–`RF-10`; `CA-01`–`CA-10`; REST contract and controller validation matrix.
- **Outcome:** The protected GET returns the exact available/unavailable union and safe `401`/`404`/`422`/`503` failures; the controller uses Shared auth and Learning/Curriculum protocols; the REST artifact covers the route.
- **Rules:** `documentation/rules/rest-layer-rules.md` (thin controller, explicit response/error mapping, contract synchronization); `documentation/rules/server-app-layer-rules.md`; `documentation/rules/controllers-testing-rules.md`; `documentation/rules/provision-layer-rules.md`.
- **Risks/controls:** Preserve generic private absence and safe unexpected failures; do not catch/map errors inside the controller. The REST artifact must contain one labeled request for this route with reusable non-secret IDs/token variables, current headers, no body, and no real credentials.
- **Exit:** `cd apps/server && uv run pytest tests/learning/server/controllers/test_get_competency_detail_controller.py`; inspect OpenAPI route method/path; verify the `.rest` file's labeled request, reusable variables, no credentials, and parity with the controller. The test must traverse `FastAPIApp.register()` and PostgreSQL rather than calling handlers directly.

### F5 — Orchestrated integration and evidence baseline

#### F5-T1 — Integrate shared composition and generated artifacts

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** F3 and F4; no active Builder may own these shared/generated paths.
- **Paths:** `apps/server/src/shifu/app.py`; `apps/web/src/middlewares/require-auth-middleware.ts`; `apps/web/src/ui/shared/widgets/layouts/root-layout/use-root-layout.ts`; `apps/web/src/ui/shared/widgets/layouts/root-layout/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts`; `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx`; `apps/web/src/routeTree.gen.ts`; `apps/server/migrations/versions/d72c0f4e8a31_add_learning_competency_detail_integrity.py`.
- **Traceability:** Technical Contract composition, auth, query, generation, and migration decisions; `CA-01`, `CA-07`, `CA-08`, `CA-09`, `CA-10`.
- **Outcome:** FastAPI composition binds the adapters once and safely; the root mounts the stable Query/RPC providers; protected auth results do not expose the token; route metadata and Alembic revision are generated/reviewed from source.
- **Rules:** `documentation/rules/server-app-layer-rules.md`; `documentation/rules/database-layer-rules.md`; `documentation/rules/web-app-routing-rules.md`; `documentation/rules/ui-layer-rules.md`; `documentation/rules/widget-testing-rules.md`.
- **Risks/controls:** Generated files are never hand-edited. Migration upgrade/backfill must preserve valid data or abort safely; downgrade is only inspected on a disposable copy because it removes persisted hard-score snapshots.
- **Exit:** Run `pnpm --filter web generate-routes` and review only the generated route-tree diff; from `apps/server`, run `uv run poe db:migrate "add learning competency detail integrity"`, reconcile the generated revision against the Spec's declared migration path, and review migration SQL/preflight before applying `uv run poe db:upgrade head` to the selected disposable database.

#### F5-T2 — Run integrated automated gates and establish Evaluation evidence

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** F5-T1; manual evidence starts only after focused automated gates pass.
- **Paths:** Complete integrated candidate; `documentation/features/learning/competency-detail/evaluation.md` is created by `implement-spec` at implementation kickoff and is not fabricated by this Plan.
- **Traceability:** Every `RF-*`, `CA-*`, and `VM-*`; `CI-*` quality gates declared by the current manifests/tooling.
- **Outcome:** The complete candidate has fresh automated evidence, current generated-artifact parity, and an evidence baseline ready for runtime validation.
- **Rules:** `documentation/sdd.md`; `documentation/tooling.md`; all selected Rule Packs listed in the Spec and referenced by F2–F5.
- **Risks/controls:** Do not claim passing evidence from mocked transport alone. Record skipped infrastructure, pre-existing findings, stale evidence, and the current Spec revision explicitly in `evaluation.md`.
- **Exit:** Run `pnpm --filter web check:lint`, `pnpm --filter web check:architecture`, `pnpm --filter web check:types`, `pnpm --filter web test:unit`, `pnpm --filter web test:integration`, `pnpm --filter web build`; then `cd apps/server && uv run poe check:lint`, `uv run poe check:architecture`, `uv run poe check:types`, `uv run poe test:unit`, `uv run poe test:integration`, and `uv run poe build`.

#### F5-T3 — Capture real seeded full-stack and visual evidence

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** F5-T2 and available Docker/Web/API/Playwright services; no database reset or volume deletion.
- **Paths:** Runtime surfaces only; transient screenshots/traces remain uncommitted validation artifacts. Evidence is recorded in `evaluation.md`.
- **Traceability:** `VM-01`–`VM-07`; `CA-01`–`CA-10`; all ten supplied design states plus the accepted released-non-focus desktop/mobile assumption.
- **Outcome:** Real BFF → FastAPI → PostgreSQL behavior, privacy/isolation, no-write semantics, migration/seed integrity, keyboard/accessibility behavior, responsive layout, network/console health, and visual comparisons are evidenced.
- **Rules:** `documentation/features/learning/competency-detail/design/handoff.md`; `documentation/rules/web-app-routing-rules.md`; `documentation/rules/widget-testing-rules.md`; repository Playwright instructions in `AGENTS.md`.
- **Risks/controls:** Use a clean non-production browser context; never save passwords/tokens; use disposable PostgreSQL for migration checks; stop only processes started for validation and leave shared Docker services unchanged unless explicitly requested.
- **Exit:** Verify `/health`, start only required local applications, execute VM-01–VM-07 with Playwright CLI at `1440×900` and `390×844` where specified, inspect final URLs/requests/DOM/accessibility/console/4xx/5xx responses, and save fresh screenshots for each supplied state and both non-focus supplemental states.

### F6 — Integrated Implementation Reviewer checkpoint

#### F6-T1 — Audit the complete candidate read-only

- **Status/owner:** `completed` — Implementation Reviewer
- **Depends/parallel:** Starts only after F5-T2's automated/evidence baseline and all Builder diffs are integrated; may run alongside Orchestrator's read-only sensors.
- **Paths:** Read-only review of the complete integrated diff, Spec, Plan, Evaluation, affected source/tests/generated artifacts, `apps/server/rest-client/learning/competencies.rest`, and all affected runtime surfaces.
- **Traceability:** All `RF-*`, `CA-*`, `VM-*`, REST contract, design references, and cross-Builder boundaries.
- **Outcome:** One advisory report identifies any conformance, contract, stale-evidence, REST-parity, UI, server, migration, or integration finding with the responsible Builder.
- **Rules:** [`implementation-reviewer-agent.md`](../../../agents/implementation-reviewer-agent.md); all selected Rule Packs and the current Spec revision.
- **Risks/controls:** The Reviewer does not edit files, decide official evidence, mutate Atlassian, or replace the Orchestrator's sensors. If a contracted path changes, invalidate affected evidence and resume the same Reviewer after the responsible Builder's correction exit passes.
- **Exit:** Complete the required read-only structural, REST-client, UI/Playwright, and server-backed audit; record `ACH-*` findings and conformance status in the Evaluation without claiming the advisory report itself is acceptance evidence.

### F7 — Final handoff

#### F7-T1 — Resolve verified findings and route to conclusion

- **Status/owner:** `completed` — Orchestrator
- **Depends/parallel:** F6-T1; responsible Builder corrections may run sequentially through `implement-spec`, then the same Reviewer is resumed.
- **Paths:** Any corrected contracted paths assigned by the finding; `documentation/features/learning/competency-detail/plan.md`; `documentation/features/learning/competency-detail/evaluation.md`; no external Jira/Confluence writes.
- **Traceability:** Every remaining `ACH-*`, `EV-*`, `CA-*`, `VM-*`, and final delivery disposition for selected `RP-*`/`JN-*` coverage.
- **Outcome:** The exact Spec revision, integrated diff, generated artifacts, route parity, quality gates, current visual/runtime evidence, and reviewer findings are reconciled. The final reviewer issued a conditional GO; ACH-018 is explicitly accepted as the sole evidence limitation, and the Evaluation is complete for delivery.
- **Rules:** `documentation/sdd.md`; `documentation/prompts/conclude-spec-prompt.md`; `documentation/rules.md`; all affected Rule Packs.
- **Risks/controls:** The accepted ACH-018 boundary is explicit in the
  Evaluation; VM-02–VM-06 are not represented as real backend evidence. No task
  or phase is marked complete from an unverified Builder report, stale screenshot,
  mocked transport, or unavailable service.
- **Exit:** Confirm every task/phase is `completed`, every `CA-*`/`VM-*` has accepted current evidence, every affected route group has a route-complete `.rest` artifact, the same Reviewer is complete with verified findings resolved, and then route directly to `conclude-spec`.

# Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Learning use-case unit matrix | `CA-01`–`CA-06`, `CA-10` | Spec Validation Contract; F2-T2 | `evaluation.md` `EV-*` plus `CI-*` focused result | `completed` |
| Runtime | FastAPI/PostgreSQL controller integration | `CA-01`–`CA-03`, `CA-06`, `CA-10` | Technical Contract; F4-T2 | HTTP/body/auth/persistence/no-write evidence in `evaluation.md` | `completed` |
| Automated | Web widget/unit suites | `CA-02`–`CA-05`, `CA-08`, `CA-09` | UI and Widget Testing Rules; F3-T2 | `evaluation.md` `EV-*` plus `CI-*` focused result | `completed` |
| Automated | Web mocked route integration | `CA-01`, `CA-04`–`CA-09` | Routing and Widget Testing Rules; F3-T3 | Final URL, mocked method/path/body, visible result, and accessibility evidence | `completed` |
| Automated | Generated route metadata and build | `CA-07`, `CA-09` | F5-T1 | Generated-tree diff review and web build result | `completed` |
| REST client | `learning/competencies` route group | Protected GET technical contract; `CA-01`–`CA-03`, `CA-06` | `apps/server/rest-client/learning/competencies.rest` | One labeled request for the route, exact method/path/path IDs/header/no body, reusable non-secret variables, no credentials, parity result in `evaluation.md` | `completed` |
| Runtime | `VM-01` Available focus, order, recommendation, and navigation | `CA-02`–`CA-04`, `CA-07`, `CA-09` | `design/xsNI4.png`; `design/R7GgrF.png`; Spec `VM-01` | Fresh desktop/mobile screenshots, response/DOM/order, keyboard/URL/network/console evidence | `completed` |
| Visual | Desktop available focus | `CA-02`–`CA-04`, `CA-07`, `CA-09` | `design/xsNI4.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile available focus | `CA-02`–`CA-04`, `CA-07`, `CA-09` | `design/R7GgrF.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-02` Loading | `CA-08`, `CA-09` | `design/DF05W.png`; `design/IqpIe.png`; Spec `VM-02` | Fresh asserted UI-state screenshots, one-request trace, status semantics; backend lineage limitation recorded as ACH-018 | `completed` |
| Visual | Desktop loading | `CA-08`, `CA-09` | `design/DF05W.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile loading | `CA-08`, `CA-09` | `design/IqpIe.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-03` Privacy, recoverable error, and retry | `CA-01`, `CA-08`, `CA-09` | `design/m4Swx.png`; `design/pYLj5.png`; Spec `VM-03` | Fresh asserted UI-state screenshots, sanitized DOM/retry/recovery evidence; backend lineage limitation recorded as ACH-018 | `completed` |
| Visual | Desktop recoverable error | `CA-01`, `CA-08` | `design/m4Swx.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile recoverable error | `CA-01`, `CA-08`, `CA-09` | `design/pYLj5.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-04` Restricted unavailable Competency | `CA-01`, `CA-06`, `CA-07`, `CA-09` | `design/VrlNG.png`; `design/B0DSt.png`; Spec `VM-04` | Fresh asserted UI-state screenshots, unavailable/negative DOM field inspection, safe Skill navigation; backend lineage limitation recorded as ACH-018 | `completed` |
| Visual | Desktop unavailable | `CA-01`, `CA-06`, `CA-07` | `design/VrlNG.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile unavailable | `CA-01`, `CA-06`, `CA-07` | `design/B0DSt.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-05` Focus returned after regression | `CA-02`, `CA-04`, `CA-09` | `design/A61TJ.png`; `design/u301ZL.png`; Spec `VM-05` | Fresh asserted UI-state screenshots plus independent derivation/no-write evidence; backend lineage limitation recorded as ACH-018 | `completed` |
| Visual | Desktop focus returned | `CA-02`, `CA-04` | `design/A61TJ.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile focus returned | `CA-02`, `CA-04`, `CA-09` | `design/u301ZL.png` | Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-06` Released non-focus accepted assumption | `CA-05`, `CA-07`, `CA-09` | `design/handoff.md`; Spec `VM-06` | Fresh asserted UI-state screenshots, no local recommendation, focus-link URL/params; backend lineage limitation recorded as ACH-018 | `completed` |
| Visual | Desktop released non-focus supplemental state | `CA-05`, `CA-07`, `CA-09` | `design/handoff.md` accepted assumption | Fresh Playwright screenshot + comparison `EV-*` | `completed` |
| Visual | Mobile released non-focus supplemental state | `CA-05`, `CA-07`, `CA-09` | `design/handoff.md` accepted assumption | Fresh Playwright screenshot + comparison `EV-*` | `completed` |
| Runtime | `VM-07` Persistence, migration, and Goal isolation | `CA-10` | Spec `VM-07`; migration `d72c0f4e8a31` | Disposable migration preflight/upgrade/downgrade, hard-score round-trip, uniqueness/index inspection, account/Goal isolation, no-write diff | `completed` |

The final handoff completed every phase/task above against Spec
revision `3`; the complete integrated diff and generated route/lockfile/migration
artifacts reconciled; all applicable pnpm and uv commands passed without lowering
configured floors; the route-group REST artifact is present and route-complete;
all `CA-*` and `VM-*` have accepted current evidence; all supplied and supplemental
visual states have fresh comparisons; required services, accounts, fixtures and
limitations are recorded; the single Implementation Reviewer completed with a
conditional GO; ACH-018 is accepted as the sole evidence limitation; all other
verified findings are resolved; and `evaluation.md` is complete for delivery.
