---
title: Initial diagnosis implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 9
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-77
last_updated_at: 2026-09-28
---

# 1. Execution status

- **Spec:** `documentation/features/learning/initial-diagnosis/spec.md`, revision
  `9`, status `ready` after the Spec Reviewer's correction pass.
- **Why Plan-backed:** the Spec spans Learning Core, persistence and migration,
  REST and Inngest, Web pages and routing, two HTTP route-group examples, and
  integrated desktop/mobile validation with persisted state.
- **Plan status / phase:** `complete` — the Spec Reviewer accepted revision 9
  after the policy-consumer, revision-token and seed-safety corrections.
- **Next action:** commit and push the Server signer-fixture correction to PR #19, then verify the GitHub Actions rerun.
- **Active blockers:** Web assertions are corrected and its GitHub workflow passes.
  Server signer fixture is corrected; focused and full local integration pass without
  `.env.local`. The next remote rerun is pending. Manual browser validation remains
  waived by the user.
- **External dependencies:** none block execution. Jira records SHIFU-16 and
  SHIFU-18 as complete; the reused activity-question work SHIFU-74 and SHIFU-75
  is complete.
- **Active Builders:** none. F6 corrections and integrated automated validation
  are complete; evidence is recorded in EV-42–EV-46.
- **Completed implementation:** all F1/F2 implementation exits
  passed, including the disposable migration sequence, focused Core coverage,
  aggregate scenario ownership migration, and all Web gates. F2-T2 passed on
  the real Inngest/Testcontainers fixture; F2-T1 controller suites and REST
  parity passed. F3-T1 gates, persisted/mobile journeys and all four captures
  passed. F3-T2 passed review reconciliation at EV-23, then reopened for ACH-10;
  EV-26 visual review passed for entry navigation. ACH-12 continuation and
  refreshed visual review passed at EV-29; the required post-correction VM-01
  remains unavailable because the fresh shared local browser redirects to
  `/login`.
- **Shared and generated ownership:** the Orchestrator owns `plan.md`,
  `evaluation.md`, migration coordination/review, route generation and review
  of `apps/web/src/routeTree.gen.ts`, integrated validation, Evaluation
  evidence, and reviewer reconciliation. `Builder Server` owns the one Learning
  migration within F1-T1. Builder paths do not overlap.

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Current Spec is `ready` at revision `9`; independent Spec Reviewer passed after RF-11 and seed safety corrections | Orchestrator | `satisfied` | Freeze revision for Builders |
| Product authority | `Shifu — PRD — Learning`, content ID `83066881`, version `24`; Curriculum PRD content ID `83034113`, version `12` | Orchestrator | `satisfied` | Re-read if an authority version changes |
| Jira dependencies | SHIFU-16, SHIFU-18, SHIFU-74 and SHIFU-75 are complete | Orchestrator | `satisfied` | None |
| Design inventory | `documentation/features/learning/initial-diagnosis/design/handoff.md` inventories ten supplied 1440 × 900 references and revision-8 copy deviation; revision 9 still requires four fresh happy-path comparisons | Orchestrator | `satisfied` | Use saved references under the feature's `design/references/`; do not add manual scenarios |
| F2 integration environment | Docker/Testcontainers available for PostgreSQL controller tests and real Inngest job tests | Orchestrator | `satisfied` | Disposable PostgreSQL controllers passed; the Testcontainers Dev Server registered and ran all 8 real job tests. The separate shared local Inngest endpoint still reports zero functions. |
| F3 runtime environment | Disposable PostgreSQL/Inngest plus authenticated test account, eligible Goal/Skill and Web/FastAPI services available for VM-01; Playwright CLI available for VM-02 | Orchestrator | `satisfied` | Inngest registered 8 functions; disposable authenticated persisted run and mocked mobile keyboard flow completed with four fresh captures (EV-23) |

Current dependency order is F4 Curriculum/private revision and Web traversal,
then F5 Learning batch integration, then F6 validation. The historical F1/F2
work remains as a baseline; F3 evidence is stale for the changed journey.
`implement-spec` creates or reconciles `evaluation.md` at kickoff; no validation
evidence is asserted here.

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Server` | F1 | Learning Core and persistence support for isolated diagnostic runs, provisional evaluation, explicit confirmation, and nullable summaries | — | F1 `Builder Web` | `complete` | F1-T1 and F1-T2 exits pass; migration is reviewed and verified only against a disposable database |
| 1 | `Builder Web` | F1 | Activity, Skill and result pages consume the Spec contracts; result route and required Page suites are present | Spec revision 6 | F1 `Builder Server` | `complete` | F1-T3 exit passes; generated route tree is synchronized and reviewed by the Orchestrator |
| 2 | `Builder Server` | F2 | Authenticated Learning HTTP operations, route-complete REST examples and stale-job protection are integrated | F1 | — | `complete` | F2-T1 exit passes through PostgreSQL HTTP tests, real Inngest job tests and REST parity |
| 3 | `learning-web-continuation-builder` + `Orchestrator` | F3 | Historical ACH-12 Activity continuation, revision 6; authenticated VM-01 evidence moves to F6 | F1, F2 | — | `complete` | Web behavior and automated checks passed at EV-29; current persisted VM-01 was waived by the user at EV-42 |
| 4 | `learning-curriculum-snapshot-builder` | F4 | Existing readiness gate, mixed diagnostic snapshot and private revision token | F1/F2 | Web contract work | `implemented` | Ready Skills remain eligible; server-only HMAC token and mixed code snapshot available; integration review pending |
| 4 | `learning-web-single-submit-builder` | F4 | Revision-9 DTO, session answers, Activity traversal and final-submit UI | F1/F2 and fixed Spec REST contract | Curriculum work | `implemented` | No intermediate POST; one final request; learning Activity flow preserved; integration review pending |
| 5 | `learning-server-batch-builder` | F5 | Global policy and atomic diagnostic batch with REST/job parity | F4 Curriculum port and revision token | — | `implemented` | All-or-none attempts/evaluations/events and replay; route group examples current; integrated behavioral evidence pending |
| 6 | `Orchestrator` | F6 | Integrated validation, evidence and CI follow-up | F4/F5 | Implementation Reviewer passed; visual comparison waived; CI rerun pending | `in_progress` | Resolve GitHub checks and retain manual waiver |
| 6 | `initial-diagnosis-web-fix` | F6 | Correct stale or failing Web component, hook and route assertions against revision-9 single-submit behavior; fix MaterialContent width required by Design System T23 | EV-38 baseline | F6 server fixes | `complete` | CI-05 and CI-06 pass; MaterialContent uses the approved 68ch reading width; fresh affected UI evidence is captured after correction |
| 6 | `initial-diagnosis-core-fix` | F6 | Correct Learning Core behavior and unit fixtures exposed by revision-9 execution | EV-38 baseline | F6 Web/server-boundary fixes | `complete` | CI-11 passes; only Learning Core and its unit-test paths listed in EV-39 change |
| 6 | `initial-diagnosis-server-boundary-fix` | F6 | Correct Learning controller integration fixtures/contracts and establish CI-15 disposable migration cycle | EV-38 baseline | F6 Web/Core fixes | `complete` | CI-12 passes and CI-15 upgrade/downgrade/re-upgrade is verified; only Server REST/test/fixture paths listed in EV-39 change |
| 6 | `initial-diagnosis-job-fix` | F6 | Correct the two real Learning evaluation-job failures on the isolated Inngest runtime | EV-40 baseline | F6 Web/Core/controller fixes | `complete` | CI-13 passes with all 8 tests executing; only the named job/test/fixture paths listed in EV-39 change |

### F1 — Core, persistence and Web implementation

#### F1-T1 — Learning diagnostic state and persistence

- **Status/owner:** `complete` — `learning-server-builder` implementation;
  Orchestrator reviewed the migration and verified the disposable-DB sequence
- **Depends/parallel:** First server task; parallel with F1-T3. F1-T2 follows this
  task. Migration coordination and generated migration review remain with the
  Orchestrator.
- **Paths:** `apps/server/src/shifu/learning/core/domain/entities/{skill_experience.py,activity_attempt.py}`;
  `apps/server/src/shifu/learning/core/domain/structures/{diagnostic_overview.py,diagnostic_competency_summary.py,skill_experience_detail.py,skill_competency_summary.py,skill_recommendation.py,concept_completion_summary.py,competency_completion_summary.py,skill_completion_summary.py,__init__.py}`;
  `apps/server/src/shifu/learning/core/interfaces/activity_attempts_repository.py`;
  `apps/server/src/shifu/learning/database/sqlalchemy/models/{skill_experience_model.py,activity_attempt_model.py}`;
  `apps/server/src/shifu/learning/database/sqlalchemy/mappers/{skill_experience_mapper.py,activity_attempt_mapper.py}`;
  `apps/server/src/shifu/learning/database/sqlalchemy/repositories/activity_attempts_repository.py`;
  `apps/server/migrations/versions/e7d45a1b9c02_isolate_learning_diagnostic_runs.py`.
- **Traceability:** RP-05, RP-06, RP-07, RP-15, RP-16, RP-17, RP-19, RP-28;
  JN-04, JN-05, JN-18; RF-01, RF-05, RF-06, RF-07, RF-08; CA-01, CA-02,
  CA-08–CA-14.
- **Outcome:** domain and SQLAlchemy contracts represent the active diagnostic
  run, provisional attempts, coverage-aware nullable summaries, and persisted
  completion snapshots as specified; the migration adds only the nullable run
  identifiers and declared index.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/core-layer-rules.md`,
  `documentation/rules/database-layer-rules.md`. These packs have no
  `Antipatterns to Avoid` subsection.
- **Risks/controls:** deletion cascades and downgrade affect diagnostic data;
  preserve existing null-valued records and use only the Spec’s disposable-database
  migration sequence. Do not downgrade a shared database.
- **Exit:** focused Core/persistence checks declared in F1-T2 pass; Orchestrator
  reviews migration revision and `down_revision`, then verifies upgrade,
  downgrade and re-upgrade on a disposable PostgreSQL database using CI-15.

#### F1-T2 — Diagnostic use cases and Core unit coverage

- **Status/owner:** `complete` — implementation, focused Core tests, and the
  F2-T2 review-job scenario migration passed
- **Depends/parallel:** After F1-T1; parallel with F1-T3. This remains the same
  Server ownership boundary.
- **Paths:**
  `apps/server/src/shifu/learning/core/use_cases/{start_skill_use_case.py,abandon_diagnostic_use_case.py,complete_diagnostic_use_case.py,get_diagnostic_use_case.py,diagnostic_sequence.py,get_choice_activity_use_case.py,submit_choice_activity_use_case.py,retry_choice_evaluation_use_case.py,evaluate_choice_activity_use_case.py,preview_activity_question_feedback_use_case.py,get_skill_experience_detail_use_case.py,__init__.py}`;
  `apps/server/tests/learning/core/use_cases/{test_start_skill_use_case.py,test_abandon_diagnostic_use_case.py,test_complete_diagnostic_use_case.py,test_get_diagnostic_use_case.py,test_create_goal_use_case.py,test_get_competency_detail_use_case.py,test_submit_choice_activity_use_case.py,test_evaluate_choice_activity_use_case.py,test_retry_choice_evaluation_use_case.py,test_get_choice_activity_use_case.py,test_preview_activity_question_feedback_use_case.py,test_get_skill_experience_detail_use_case.py,test_adaptive_diagnostic_flow.py}`.
- **Traceability:** RP-05–RP-07, RP-10–RP-17, RP-19, RP-26–RP-28; JN-04,
  JN-05, JN-18, JN-21; RF-01–RF-08; CA-01–CA-12 and CA-14.
- **Outcome:** entry, abandonment, sequence, retry, provisional evaluation and
  one-time confirmation follow revision 6, including no stale side effects,
  evidence partiality, event uniqueness and preservation of the existing
  adaptive policy. Retire the aggregate Core suite only after its valid scenarios
  are migrated to their owning suites as listed in the Spec.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/core-layer-rules.md`,
  `documentation/rules/use-case-testing-rules.md`. These packs have no
  `Antipatterns to Avoid` subsection.
- **Risks/controls:** run/attempt identifiers can be confused and the former
  aggregate suite contains valid scenarios. Keep evaluation `run_id` distinct
  from diagnostic run ID, and retain the Spec’s explicit scenario migration map.
- **Exit:** focused use-case suites pass and all valid aggregate scenarios are
  migrated to their owning Core/job suites; then `cd apps/server && uv run poe
  check:lint`, `check:architecture`, and `test:unit` pass. The full-app type
  check is verified in F2-T1 after the controller passes the required
  `entry_key`; this avoids making the Core API optional to satisfy an adapter
  that is intentionally owned by F2. No tests call infrastructure from Core
  unit suites.

#### F1-T3 — Web services, pages, routes and browser suites

- **Status/owner:** `complete` — `learning-web-builder`; Orchestrator reran
  the scoped gates and reviewed retired-suite scenario migration
- **Depends/parallel:** Starts in Wave 1 alongside F1-T1; consumes the fixed
  Spec contract. Orchestrator generates/reviews the route tree after route files
  are ready; F3 owns integrated browser and visual evidence.
- **Paths:**
  `apps/web/src/core/learning/{goal-detail.ts,skill-experience.ts}`;
  `apps/web/src/constants/routes.ts`;
  `apps/web/src/rest/services/learning-service.ts`;
  `apps/web/src/ui/learning/{diagnostic-run-session.ts,hooks/use-diagnostic-leave-guard.ts}`;
  `apps/web/src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts,code-question/index.tsx,tests/activity-page.test.tsx,tests/use-activity-page.test.ts,code-question/tests/code-question.test.tsx}`;
  `apps/web/src/ui/learning/widgets/pages/skill-page/{index.tsx,use-skill-page.ts,skill-experience/index.tsx,skill-experience/tests/skill-experience.test.tsx,skill-overview/index.tsx,skill-competency-list/skill-competency-row/index.tsx,tests/skill-page.test.tsx}`;
  `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/{index.tsx,use-diagnostic-result-page.ts,tests/diagnostic-result-page.test.tsx}`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/index.tsx`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/diagnostic/result/index.tsx`;
  `apps/web/tests/learning/{activity-page.test.ts,skill-page.test.ts,diagnostic-result-page.test.ts,skill-experience-page.test.ts,choice-activity-page.test.ts}`.
- **Generated path:** `apps/web/src/routeTree.gen.ts` is generated by the
  Orchestrator with `pnpm --filter web generate-routes`; never hand-edit it.
- **Traceability:** RP-05–RP-07, RP-10–RP-17, RP-19, RP-25–RP-28; JN-04,
  JN-05, JN-18, JN-21; RF-01–RF-09; CA-01–CA-06 and CA-10–CA-15.
- **Outcome:** Skill, Activity and result pages implement the run/session and
  privacy contract, including accessible pt-BR states, route protection,
  required recovery states and completion/result navigation. Retire the two
  superseded browser suites after useful scenarios have moved to the Page-owned
  suites.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `ui-layer-rules.md`, `web-app-routing-rules.md`,
  `widget-testing-rules.md`, `rest-layer-rules.md`; for `ui-layer-rules.md`, also
  apply its `Antipatterns to Avoid` subsection.
- **Risks/controls:** browser memory is per-tab and must not leak into persistent
  storage or URLs. Keep page hooks as behavior owners, route files thin, use
  canonical dynamic route params, and preserve mocked-browser evidence as distinct
  from server-backed VM-01 evidence.
- **Exit:** `pnpm --filter web generate-routes` is run by the Orchestrator and
  its route-tree diff reviewed; `pnpm --filter web check:lint`,
  `check:architecture`, `check:types`, `test:unit`, the focused CI-06 Playwright
  Page suites, and `build` pass. Review loading/empty/error/recovery, keyboard,
  focus, accessibility, narrow viewport, console and failed-request assertions
  against the Design Contract; fresh required screenshots are captured in F3.

### F2 — REST, composition, route examples and Inngest job

#### F2-T1 — HTTP contracts, composition and route-complete REST examples

- **Status/owner:** `complete` — `learning-server-builder`; integrated
  controller gates and both route-group parity audits passed
- **Depends/parallel:** After F1; requires the F2 Testcontainers environment for
  HTTP integration exits. F3 follows this task.
- **Paths:**
  `apps/server/src/shifu/learning/rest/controllers/{start_skill_controller.py,abandon_diagnostic_controller.py,complete_diagnostic_controller.py,get_diagnostic_controller.py,get_choice_activity_controller.py,submit_choice_activity_controller.py,retry_choice_evaluation_controller.py,get_skill_experience_detail_controller.py,__init__.py}`;
  `apps/server/src/shifu/learning/rest/router.py`;
  `apps/server/src/shifu/learning/pipes/learning_pipe.py`;
  `apps/server/rest-client/learning/{learning.rest,activities.rest}`;
  `apps/server/tests/learning/server/controllers/{test_start_skill_controller.py,test_abandon_diagnostic_controller.py,test_complete_diagnostic_controller.py,test_get_diagnostic_controller.py,test_adaptive_journey_controller.py,test_get_competency_detail_controller.py,test_get_choice_activity_controller.py,test_submit_choice_activity_controller.py,test_retry_choice_evaluation_controller.py,test_get_skill_experience_detail_controller.py}`.
- **Traceability:** RP-05–RP-07, RP-10–RP-17, RP-19, RP-25–RP-28; JN-04,
  JN-05, JN-18, JN-21; RF-01–RF-08; CA-01–CA-04, CA-06–CA-14.
- **Outcome:** Learning controllers expose the Spec’s explicit request/response,
  auth, status and error contracts. `learning.rest` and `activities.rest` each
  contain one labeled request for every route in their respective current route
  groups, including unaffected existing routes.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/rest-layer-rules.md`,
  `documentation/rules/server-app-layer-rules.md`,
  `documentation/rules/controllers-testing-rules.md`. These packs have no
  `Antipatterns to Avoid` subsection.
- **Risks/controls:** keep Learning rules in Core, not controllers or pipes;
  cover persisted state and authorization through the FastAPI app boundary, not
  mocked transports. Keep route registration explicit and preserve existing
  learning/review requests without diagnostic headers.
- **Exit:** controller integration suites pass through the real TestClient,
  composed repositories and disposable PostgreSQL; assert route methods, status,
  body, auth/authorization, persistence, outbox and forbidden side effects.
  Verify both `.rest` files against every controller in each route group:
  current methods, full paths, params, headers, representative bodies, reusable
  non-secret variables, no credentials. Exercise each labeled request once
  against the local server when available and record parity separately from
  integration evidence in `evaluation.md`.

#### F2-T2 — Stale diagnostic evaluation job protection

- **Status/owner:** `complete` — `learning_diagnostic_job_builder`; real job suite
  passed and the valid aggregate job scenario moved to its job-owner suite
- **Depends/parallel:** After F1; can proceed alongside F2-T1 only if ownership
  remains limited to the paths below. Both tasks belong to `Builder Server` and
  may be sequenced by that Builder. F2 completion requires both.
- **Paths:**
  `apps/server/src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py`;
  `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`;
  `apps/server/tests/learning/core/use_cases/test_adaptive_diagnostic_flow.py`
  (retire only its review-job scenario after the equivalent job-owner test
  passes; preserve its Core-owned scenarios).
- **Traceability:** RP-05, RP-06, RP-07, RP-11–RP-14, RP-27; JN-04, JN-05,
  JN-21; RF-03–RF-05; CA-05, CA-07–CA-09.
- **Outcome:** current diagnostic evaluation failures and successes remain
  provisional; stale, abandoned or replaced work has no progress, completion or
  event effect, including in the failure callback.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `documentation/rules/messaging-layer-rules.md`,
  `documentation/rules/jobs-testing-rules.md`. These packs have no
  `Antipatterns to Avoid` subsection.
- **Risks/controls:** a mocked job call is not runtime evidence. Preserve the
  existing registered event and exercise the real Inngest Dev Server,
  application callback, durable steps and disposable PostgreSQL fixture.
- **Exit:** `cd apps/server && uv run poe test:jobs` passes without a Docker
  skip; assert current/stale runs, retry/failure callback behavior, persisted
  effects and absence of premature events.

### F3 — Integrated validation and handoff

#### F3-T1 — Integrated quality gates, migration, runtime journey and captures

- **Status/owner:** `in_progress` — the bounded ACH-12 Web correction, integrated
  Web gates, and desktop/mobile pending-state captures passed at EV-29.
  Orchestrator owns the remaining authenticated persisted VM-01 replay.
  Earlier migration and runtime evidence remains historical for paths affected
  by ACH-12.
- **Depends/parallel:** After F1 and F2. Run all contract-required automated
  gates, then VM-01/VM-02 and capture the four required images before review.
- **Paths:** Orchestrator owns `documentation/features/learning/initial-diagnosis/evaluation.md`
  and transient validation evidence only; screenshots and browser artifacts are
  not committed. For ACH-07, Builder Server owns
  `apps/server/src/shifu/learning/core/use_cases/get_diagnostic_use_case.py`,
  `apps/server/src/shifu/learning/core/domain/structures/diagnostic_overview.py`,
  `apps/server/src/shifu/learning/rest/controllers/get_diagnostic_controller.py`,
  `apps/server/tests/learning/core/use_cases/test_get_diagnostic_use_case.py`,
  `apps/server/tests/learning/server/controllers/test_adaptive_journey_controller.py`,
  and `apps/server/tests/learning/core/use_cases/test_adaptive_diagnostic_flow.py`
  for assertions and fixtures affected by the immutable settled result contract.
  For ACH-08 and the Web side of ACH-07, Builder Web owns
  `apps/web/src/core/learning/goal-detail.ts`,
  `apps/web/src/rest/services/learning-service.ts`,
  `apps/web/src/ui/learning/widgets/pages/activity-page/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/activity-page/choice-question/choice-question.css`,
  `apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx`,
  `apps/web/src/ui/learning/widgets/pages/diagnostic-result-page/index.tsx`,
  `apps/web/tests/learning/diagnostic-result-page.test.ts`,
  `apps/web/src/ui/shared/widgets/layouts/app-layout/index.tsx`, and
  `apps/web/src/ui/shared/widgets/layouts/app-layout/tests/app-layout.test.tsx`.
  All remaining feature behavior, route and ownership boundaries stay unchanged.
  ACH-12 Builder Web owns only the Activity Page hook, component and their
  colocated tests; the Skill Page hook, component and colocated test; the
  Activity route composition; the Activity and Skill Page browser suites; and
  `apps/web/src/ui/learning/diagnostic-actions.ts` only if sharing the existing
  diagnostic action requires extraction. The exact path fence is recorded in
  Evaluation. Server, seed, generated routes and SDD artifacts are prohibited.
  Review generated `apps/web/src/routeTree.gen.ts` and the migration diff as
  integration artifacts.
- **Traceability:** CA-01–CA-15; VM-01, VM-02; CI-01–CI-15; all inherited RP/JN
  traceability in Spec revision 6.
- **Outcome:** fresh evidence identifies the candidate, commands, persisted
  result, route parity, migration behavior, and each required desktop/mobile
  capture without extending the two approved happy-path manual journeys.
- **Rules:** `documentation/rules.md`, `documentation/tooling.md`,
  `documentation/architecture.md`, `documentation/design.md`, `AGENTS.md`, and
  the Rule Packs named in F1/F2.
- **Risks/controls:** VM-01 requires an authenticated, persisted run and stable
  local services; VM-02 uses mocked transport and must not be reported as server
  persistence evidence. Use only disposable databases for CI-15 and VM-01.
- **Exit:** pass all applicable commands in the Spec’s CI-01–CI-15 table,
  including migration upgrade/downgrade/re-upgrade on a disposable database.
  Complete VM-01 and VM-02 as specified. Inspect URL, requests, status, console
  and failed requests. Capture and inspect four distinct images: selection at
  1440 × 900 against `XhhBc` or `S4YpF1`; normal result at 1440 × 900 against
  `Yn7tE`; selection at 390 × 844; normal result at 390 × 844. Save paths and
  results in Evaluation; do not commit captures. Confirm REST parity for both
  route groups before activating reviewers.

#### F3-T2 — Parallel integrated code and visual review; evidence reconciliation

- **Status/owner:** `in_progress` — both parallel reviewers passed the ACH-12
  integrated candidate and corrected visual captures at EV-29. Orchestrator
  still owns VM-01 evidence reconciliation before final Spec conclusion.
- **Depends/parallel:** F3-T1 passed; the automatic-navigation correction has
  focused checks and fresh selection captures in EV-24. The existing two
  reviewers inspect this same candidate and captures in parallel. If a further
  correction is made, resume the affected reviewer after rerunning its exits.
- **Paths:** reviewers read the full integrated diff, Spec, Plan, Evaluation,
  route examples and captures; they do not edit candidate paths. Orchestrator
  owns all Evaluation/reconciliation edits.
- **Traceability:** CA-01–CA-15, VM-01, VM-02, all affected REST groups and all
  Spec visual states required for acceptance.
- **Outcome:** code findings and concrete desktop/mobile visual comparisons are
  reconciled; verified findings are resolved and accepted ACH entries/evidence
  are recorded by the Orchestrator.
- **Rules:** `documentation/agents/implementation-reviewer-agent.md`,
  `documentation/agents/visual-reviewer-agent.md`, `documentation/rules.md`,
  and all task-applicable Rule Packs.
- **Risks/controls:** reports are advisory. The Orchestrator verifies findings,
  marks affected evidence stale, resumes the responsible Builder through
  `implement-spec`, and reruns affected exits; no third serial reviewer is
  scheduled.
- **Exit:** both reviewers report on the same candidate; verified findings are
  resolved; CA-01/CA-03 and the VM-01 persisted-validation limit are reconciled
  in Evaluation before any conclusion.

### F4 — Revision-9 content and web boundaries

#### F4-T1 — Curriculum readiness, seed filter and private diagnostic snapshots

- **Status/owner:** `implemented`, integration evidence pending — `curriculum_revision_builder` owns the
  Curriculum provider/readiness paths; `seed_filter_builder` owns only the
  in-memory seed composition. Orchestrator owns shared snapshot structures,
  settings, app composition, environment example and migration coordination.
- **Depends/parallel:** Spec revision 9; parallel with F4-T2 after the REST and snapshot contracts are fixed.
- **Paths:** `curriculum_revision_builder` owns
  `apps/server/src/shifu/curriculum/core/domain/structures/diagnostic_coverage.py`
  and `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`;
  `seed_filter_builder` owns `apps/server/src/shifu/shared/database/seed_data.py`;
  Orchestrator owns the shared snapshot/configuration/composition and migration
  paths declared in the Spec.
- **Traceability:** PRD Curriculum v12; RF-02, RF-11; CA-05, CA-17–CA-19.
- **Outcome:** preserve the existing gate, provide mixed diagnostic code snapshots and HMAC revision tokens without exposing rubrics; Orchestrator filters only the in-memory seed structure to two ready Skills and unaffected Goals.
- **Rules:** `python-conventions-rules.md`, `core-layer-rules.md`, `provision-layer-rules.md`, `database-layer-rules.md` under `documentation/rules/`.
- **Risks/controls:** missing key or incomplete Skill fails closed; never log or serialize key; `db:seed` calls `SeedOrchestrator.clear()` and must not run on the shared database.
- **Exit:** inspect provider and shared-port parity; server lint, architecture and types; required automated and runtime gates remain pending until authorized.

#### F4-T2 — Web traversal and single final action

- **Status/owner:** `implemented`, integration review pending — `learning-web-single-submit-builder`.
- **Depends/parallel:** REST contract fixed by Spec; parallel with F4-T1.
- **Paths:** `apps/web/src/core/learning/goal-detail.ts`, `apps/web/src/rest/services/learning-service.ts`, `apps/web/src/ui/learning/diagnostic-run-session.ts`, `apps/web/src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts}` and existing route `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx`. Orchestrator owns generated route tree and shared files.
- **Traceability:** RP-06, RP-14; RF-02–RF-05, RF-09; CA-03–CA-07, CA-15, CA-18–CA-20.
- **Outcome:** existing question widgets collect every answer in memory; same-Competency and next-Competency controls advance without POST; final control sends one batch and watches one aggregate wait.
- **Rules:** `typescript-conventions-rules.md`, `ui-layer-rules.md`, `web-app-routing-rules.md`, `widget-testing-rules.md` under `documentation/rules/`.
- **Risks/controls:** avoid leaking rubric/answer or changing learning Activity behavior; preserve keyboard, leave guard and invalidation.
- **Exit:** web lint, architecture, types and build; focused browser and visual gates remain pending until authorized.

### F5 — Atomic Learning server operation

#### F5-T1 — Global policy and diagnostic batch

- **Status/owner:** `implemented`, integration evidence pending — `learning_policy_builder` and `learning-server-batch-builder`.
- **Depends/parallel:** F4-T1 shared snapshot/port and HMAC contract; F4-T2 may continue during integration.
- **Paths:** `apps/server/src/shifu/learning/**` for
  `learning_policy_builder`; `apps/server/rest-client/learning/{learning.rest,activities.rest}`
  for Orchestrator integration; Orchestrator also owns migration and shared
  files. Test paths are not assigned under the current user constraint.
- **Traceability:** RP-06, RP-13, RP-14, RP-28; RF-02, RF-04, RF-05, RF-10; CA-07–CA-09, CA-16, CA-18–CA-20.
- **Outcome:** one authenticated, atomic POST creates one immutable attempt/evaluation/event per Activity, blocks individual diagnostic POST, handles full replay and stale execution, and keeps confirmed results unchanged.
- **Rules:** `python-conventions-rules.md`, `core-layer-rules.md`, `use-case-testing-rules.md`, `rest-layer-rules.md`, `database-layer-rules.md`, `messaging-layer-rules.md` under `documentation/rules/`.
- **Risks/controls:** authorization and row lock before replay/mutation; no partial commit or event; route examples match controller schema.
- **Exit:** server lint, architecture, types and build; required automated/runtime gates remain pending until authorized.

### F6 — Current-revision integration

#### F6-T1 — Evidence, runtime and review

- **Status/owner:** `complete` — Implementation Reviewer found no actionable code-contract issues; visual comparison was waived by the user.
- **Depends/parallel:** F4-T1/T2 and F5-T1 integrated; Implementation Reviewer inspected the integrated candidate, then parent reconciled evidence and assertion findings.
- **Paths:** `documentation/features/learning/initial-diagnosis/{plan.md,evaluation.md}`, generated routes, migrations, shared/config/seed integration and transient browser evidence.
- **Traceability:** all current RF-01–RF-11 and CA-01–CA-20.
- **Outcome:** automated revision-9 gates pass; manual VM-01–VM-03 and fresh captures are waived by the user and are not claimed as passing.
- **Rules:** Spec Rule Pack, `documentation/tooling.md`, Playwright CLI workflow from `AGENTS.md`.
- **Risks/controls:** historical EV-29 cannot prove batch behavior; do not touch shared database or claim mocked transport as persistence.
- **Exit:** current automated gates and REST parity are recorded; final implementation review findings are resolved; manual/visual evidence is explicitly waived.

# 4. Validation and handoff

The user explicitly waived manual validation and fresh screenshots on
2026-09-28. Automated gates and current route parity evidence are recorded in
Evaluation EV-42–EV-49. Historical screenshots remain audit-only and are not
claimed as current revision-9 visual evidence.

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Web unit, mocked Page integration, lint, architecture, types and build | CA-01–CA-15 | Spec Validation Contract; CI-02–CI-07 | `evaluation.md` EV-43 | `passed` |
| Automated | Server lint, architecture, types, Core unit, controller integration, jobs and build | CA-01–CA-20 | Spec Validation Contract; CI-08–CI-14 | `evaluation.md` EV-43/44 | `passed` |
| Migration | Alembic upgrade, downgrade and re-upgrade on disposable PostgreSQL | CA-02, CA-08, CA-09 | Spec migration contract; CI-15 | `evaluation.md` EV-43 | `passed` within CI-12 integration suite |
| REST client | Learning and Activity route-group parity | CA-01–CA-14 | `apps/server/rest-client/learning/{learning,activities}.rest`; EV-19 | Evaluation historical static parity review; route files unchanged in F6 | `passed; request playback not run` |
| Runtime/manual | Authenticated persisted diagnostic and result reopen (VM-01) | CA-01, CA-03, CA-04, CA-06, CA-08, CA-11, CA-13, CA-15 | Spec VM-01 | `evaluation.md` §4 | `waived by user` |
| Runtime/manual | Mobile keyboard/layout journey (VM-02) | CA-15 | Spec VM-02 | `evaluation.md` §4 | `waived by user` |
| Visual/manual | Current Activity and result captures, desktop/mobile (VM-03) | CA-03, CA-04, CA-10–CA-13, CA-15 | Design handoff references | `evaluation.md` §4 | `waived by user; historical captures only` |
| Review | Integrated Implementation Reviewer | CA-01–CA-20 | `documentation/agents/implementation-reviewer-agent.md` | `evaluation.md` EV-47 | `passed; no actionable code-contract findings` |
| Review | Visual Reviewer comparison | CA-03, CA-04, CA-10–CA-13, CA-15 | `documentation/agents/visual-reviewer-agent.md` | `evaluation.md` EV-46 | `waived by user; no fresh captures` |

Use only the commands declared by the Spec and current manifests:

```bash
pnpm --filter web generate-routes
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web test:integration tests/learning/activity-page.test.ts tests/learning/skill-page.test.ts tests/learning/diagnostic-result-page.test.ts
pnpm --filter web build

cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe test:jobs
uv run poe build
uv run poe db:upgrade head
uv run poe db:downgrade
uv run poe db:upgrade head
```

The final handoff requires every task and phase complete; the exact Spec revision
and integrated diff reconciled; all applicable commands passing without lowered
floors; the route tree, migration and both REST files reviewed; every CA and VM
with current accepted evidence; four visual comparisons complete; every affected
route group complete and credential-free; both reviewers complete with verified
findings resolved; and required services, accounts and fixtures available or
their limits explicitly recorded. The Evaluation must be ready for
`conclude-spec`, which is the next workflow.
