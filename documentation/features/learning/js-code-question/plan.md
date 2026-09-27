---
title: Learning Activity JavaScript stdin questions implementation plan
status: completed
spec: ./spec.md
spec_revision: 15
evaluation: ./evaluation.md
last_updated_at: 2026-09-27
---

# Execution status

- **Spec:** [spec.md](./spec.md), revision 15, completed after independent
  review. Product behavior and automated acceptance remain unchanged;
  production deployment checks remain outside this feature scope.
- **Why Plan-backed:** this delivery crosses Curriculum, Shared, Learning,
  Intelligence and Web; adds an assessor provider and browser runtime; integrates
  PostgreSQL/outbox/Inngest with five HTTP operations; and requires desktop/mobile
  browser evidence.
- **Plan:** `completed`; F0–F2 focused exits are complete; current Web gates
  pass (EV-078), Server CI-07–13 pass (EV-067/071), and the persisted learner
  journey is recorded in EV-077. Revision 15 makes the selected extra live
  matrices and exact visual comparisons supplemental.
- **Current phase / outcome:** F1-T2 stdin delivery correction and F2-T4
  mobile result-summary correction are complete (EV-077; EV-061/064/069). F3-T1
  composition, F3-T3 REST parity, retained automated/runtime evidence and final
  Implementation Reviewer and revision 15 Spec review are complete (EV-079/081).
  Local artifacts are concluded using retained evidence; the user-waived
  supplemental evidence was not rerun.
- **Builders:** `/root/learning_content_contract_builder` owns F1-T1 and
  `/root/learning_browser_practice_builder` owns F1-T2; their source/test paths
  do not overlap.
- **Shared ownership:** Orchestrator owns this Plan and the eventual Evaluation,
  application composition/settings, package manifests and lockfiles, Vite and
  generated route configuration, cross-Builder integration, final validation,
  screenshots/evidence and the single Implementation Reviewer checkpoint. The
  Plan does not create an Evaluation or claim validation evidence.
- **Traceability:** the Spec's source is the direct user request. SHIFU-75 is
  historical and conflicts with the current PRDs and Spec, so it is not used as
  this Plan's source and will not be updated by this work.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Completed Spec revision 15 retains local Vite isolation and makes the selected manual/visual checks supplemental | Orchestrator | `confirmed — EV-073/081` | No further Spec amendment |
| Product authority | Complete Curriculum PRD 83034113 v12 and Learning PRD 83066881 v22 match the Spec; no Jira mutation | Orchestrator | `confirmed` | Recheck versions at conclusion and report any conflict |
| Delivery traceability | Current Spec names the direct user request; SHIFU-75 is conflicting historical context | Orchestrator | `confirmed` | Keep the direct-request traceability; do not use SHIFU-75 as the source |
| Design references | Four stdin/mixed-result PNGs have visual inventories in the feature handoff; existing choice handoff remains the authority for choice states; 390 × 844 is accepted as the mobile runtime target without a supplemental Pencil frame | Orchestrator | `confirmed` | Use the saved references for implementation |
| Existing result-page evidence | Predecessor VIS-03–06 and VIS-11/12 exact-state choice visuals are freshly captured and reviewed in EV-37; its server-backed runtime evidence is tracked in its own Evaluation | Orchestrator | `confirmed — visual reference` | Existing visual-reference gate for F2-T4 is satisfied |
| Runtime dependencies | Monaco, WebContainers and xterm packages plus direct httpx resolve from owning workspaces and canonical locks; see EV-003 | Orchestrator | `confirmed — F0` | Review transitive lock diff at integration |
| Local browser runtime | Dev and preview HTML carry COOP/COEP; API `/health` is 200 and `/api/inngest` reports seven dev functions; current seeded WebContainer stdin output passes | Orchestrator | `confirmed — EV-077` | Isolated browser evidence remains distinct from CI; user-waived supplemental runtime matrices are non-gating |
| Live provider environment | Deterministic provider tests use a controlled Jev assessor and controlled HTTP responses; no OpenRouter credential is assumed | Orchestrator | `confirmed — deterministic path` | Keep any live OpenRouter smoke check separate and environment-dependent; never place credentials in the repository |

# Execution ledger

The two implementation waves are F1 and F2. At most three Builders run at a
time. F2 starts with Builder Learning Server, Builder Intelligence and Builder
Activity Page; Builder Result Page is a later, separately gated assignment and
does not overlap those three active ownership slots. F0 is Orchestrator setup;
F3 is integration/evidence; F4 is the single read-only review.

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Orchestrator | F0 | Direct runtime dependencies, canonical lockfiles and local WebContainer isolation are ready | Spec scope-path correction complete | — | `complete` | Four Web dependencies and direct httpx resolve from owning manifests/locks; dev and preview HTML headers verified in EV-006; no production-host claim |
| 1 | Builder Content | F1 | Curriculum validates stdin projects/rubrics and exposes immutable mixed snapshots through Shared contracts | F0; corrected ready Spec | Builder Web Practice | `complete — focused` | Focused Shared/Curriculum/legacy checks passed (EV-014); consuming Learning/controller tests remain F2/F3 exits |
| 1 | Builder Web Practice | F1 | Shared editor, terminal and browser runner implement the fixed project practice boundary; revision 13 adds automatic empty-stdin runs | F0; corrected ready Spec | Builder Content | `complete — ACH-019 resolved in EV-077` | Real-WebContainer route asserts pre-input `READY` and program-produced `ECHO:21`; lint/types pass and the seeded browser journey confirms input and edit reruns |
| 2 | Builder Learning Server | F2 | Learning domain, five HTTP operations, REST examples, immutable mixed attempts and official evaluation satisfy the Spec | F1 Builder Content contracts | Builder Intelligence; Builder Activity Page | `complete — integrated gates` | Unit, HTTP/PostgreSQL, Inngest, lint/type/architecture/build gates pass; activities.rest matches all five route declarations |
| 2 | Builder Intelligence | F2 | Intelligence implements the Shared rubric-assessor port using typed Jev Decisions transport | F0; F1 Shared assessor port | Builder Learning Server; Builder Activity Page | `complete — consumer evidence and app composition verified` | Adapter success/failure is covered through controlled Learning/controller/job tests; composed API registers seven functions; no live provider call required |
| 2 | Builder Activity Page | F2 | Web services, mixed Activity route and sequential question flow consume the fixed Learning contract | F1 Builder Web Practice; Spec transport contract | Builder Learning Server; Builder Intelligence | `complete — integrated route E2E` | Page/hook/route suites pass, route supplies the provision runner factory, and generated routes include Activity/Attempt paths |
| 2 | Builder Result Page | F2 | Existing official result surface renders mixed summaries and protected read-only code details | F2 Learning result DTO; Builder Activity Page; refreshed predecessor exact-state visual reference EV-37 | Builder Learning Server; Builder Activity Page | `complete — ACH-013 resolved in EV-069` | Mobile 390px geometry assertions and clean result-main screenshot pass; desktop composition, score/title, keyboard disclosure and read-only details remain verified. Persisted result evidence stays in F3. |
| 3 | Orchestrator | F3 | Integrated application, generated routes and acceptance evidence are recorded | F0–F2 focused exits complete | — | `complete — EV-077–081; revision 15 evidence boundary` | Retained automated gates, persisted learner journey, REST parity and independent reviews are recorded |
| 3 | Implementation Reviewer | F4 | One independent read-only review verifies the integrated candidate and evidence | F3 evidence baseline complete | — | `complete — EV-079` | No actionable implementation finding remains open |

## F0 — Dependency and local runtime preparation

### F0-T1 — Prepare runtime dependencies and local WebContainer headers

- **Status/owner:** `complete — EV-003–006` — Orchestrator
- **Depends/parallel:** Spec scope-path readiness gate is resolved. Complete F0
  before either implementation wave.
- **Paths:** `apps/web/package.json`; root `pnpm-lock.yaml` (canonical workspace
  lock); `apps/server/pyproject.toml`; `apps/server/uv.lock`;
  `apps/web/vite.config.ts`.
- **Traceability:** Spec Dependencies and Unsupported Runtime; RF-03/04; CA-03/04;
  CI-01–CI-03, CI-07–CI-09.
- **Outcome:** Add `@monaco-editor/react`, `@webcontainer/api`, `@xterm/xterm`,
  `@xterm/addon-fit`, and direct `httpx` using the current pnpm/uv workspaces.
  Configure the Spec's local Vite isolation requirement without implying that a
  production host is configured.
- **Rules:** `documentation/rules/provision-layer-rules.md`,
  `documentation/rules/ai-layer-rules.md`, and `documentation/tooling.md`.
- **Risks/controls:** Select versions against current Shifu manifests and lock
  files; do not edit the stale nested `apps/web/pnpm-lock.yaml`; do not add TypeSafe
  SDK or Agno; do not add secrets or invent a production deployment configuration.
- **Exit:** Manifest/lock consistency and package resolution are verified using
  declared workspace tooling. Local Vite response headers are inspected. Record
  selected versions and resulting paths in Evaluation at implementation kickoff.

## F1 — Content contracts and browser practice foundations

### F1-T1 — Establish immutable Shared snapshots and Curriculum content support

- **Status/owner:** `complete — focused` — `/root/learning_content_contract_builder`
- **Depends/parallel:** F0 complete. Parallel with F1-T2. Keep the Shared snapshots
  provider-neutral and use the exact F1 types fixed by Spec revision 10; revision
  11 only clarifies the later public DTO.
- **Paths:** Shared structures and port:
  `apps/server/src/shifu/shared/core/domain/structures/{curriculum_learning_activity_snapshot.py,curriculum_javascript_stdin_question_snapshot.py,curriculum_code_rubric_criterion_snapshot.py,curriculum_code_concept_criterion_snapshot.py,curriculum_code_rubric_part_snapshot.py,code_rubric_assessment_input.py,code_rubric_decisions.py,__init__.py}`;
  `apps/server/src/shifu/shared/core/interfaces/{curriculum_content_provider.py,code_rubric_assessor_provider.py,__init__.py}`.
  Curriculum domain, mapping and projection:
  `apps/server/src/shifu/curriculum/core/domain/structures/{javascript_stdin_question.py,code_rubric_criterion.py,code_concept_criterion.py,code_rubric_evaluation_part.py,activity_question.py,evaluation_part.py,__init__.py}`;
  `apps/server/src/shifu/curriculum/core/domain/entities/activity.py`;
  `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py`;
  `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`;
  focused Shared tests under `apps/server/tests/core/shared/domain/` and
  Curriculum domain tests under `apps/server/tests/curriculum/core/domain/`;
  provider traversal belongs to consuming F2 real controller tests under the
  selected provision/testing Rules.
- **Traceability:** Curriculum RP-03/JN-03; RF-01/02; CA-01/02/08; CI-10/11;
  VM-01/06.
- **Outcome:** Released 3–5 question mixed Activities produce complete immutable
  private snapshots; public projections omit answer keys and private rubric data;
  invalid/unsupported content fails closed; old choice rows and consumers remain
  readable.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `core-layer-rules.md`, `use-case-testing-rules.md`, `database-layer-rules.md`,
  `provision-layer-rules.md`, and `documentation/modules.md`.
- **Risks/controls:** Keep Curriculum as content owner and Shared as neutral
  contracts. Preserve legacy JSON hydration and choice-provider consumers; make no
  migration. Validate path/key/weight invariants at the owning boundary.
- **Exit:** Focused Shared/Curriculum domain tests prove mixed
  projection, private-field safety, eligibility, malformed-content rejection and
  legacy compatibility. The Spec's consuming GET/use-case and real controller
  evidence, including concrete provider traversal, is completed when F2/F3 owns
  those paths. Record no schema migration;
  do not modify Alembic files.

### F1-T2 — Build shared editor, terminal and browser practice runner

- **Status/owner:** `complete — EV-077` — `/root/learning_stdin_delivery_fix`; previous pre-input correction EV-050 and resize slice EV-045 remain supporting evidence
- **Depends/parallel:** F0 complete. Parallel with F1-T1. Use the existing Design
  Contract and tokens; the Activity Page integration consumes these components in
  F2.
- **Paths:** `apps/web/src/core/learning/code-practice-runner.ts`;
  `apps/web/src/provision/learning/webcontainer-code-practice-runner.ts`;
  regression coverage in `apps/web/tests/routes/learning/activities.$activityId.index.test.tsx` uses mocked transport and the real WebContainer; no live-backend test is added to the route suite.
  `apps/web/src/ui/learning/widgets/components/code-editor/{index.tsx,use-code-editor.ts,tests/code-editor.test.tsx,tests/use-code-editor.test.ts}`;
  `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/{index.tsx,use-code-question.ts,code-question.css,panel-resize-handle/index.tsx,tests/code-question.test.tsx,tests/use-code-question.test.ts}`;
  `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/{index.tsx,use-code-terminal.ts,tests/code-terminal.test.tsx,tests/use-code-terminal.test.ts}`.
- **Traceability:** RF-02/03/06/11; CA-02/03/04/06/14/15; CI-01–CI-05; VM-02/03.
- **Outcome:** Monaco editor and initial-file tree support only Curriculum-declared
  paths. One browser-tab WebContainer runner handles the fixed project, stdin,
  permitted commands, automatic reruns, output bounds and disposal. xterm.js is
  usable with keyboard and an accessible fallback transcript; practice failure
  leaves editing and assessment available.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `ui-layer-rules.md` including **Antipatterns to Avoid**,
  `widget-testing-rules.md`, `provision-layer-rules.md`, and
  `documentation/design.md`.
- **Risks/controls:** Browser practice is not official grading. Do not add a new
  file control, unrestricted shell, server execution endpoint, Execute action or
  unsupported CPU/memory guarantee. Dispose superseded processes/listeners and
  keep source/terminal contents out of logs.
- **Exit:** Focused component/hook/runner suites cover editable/read-only paths,
  focus, tabs, empty-stdin output, exact-command rejection, last-input rerun,
  current-run output, cleanup and boot failure. The consuming route regression
  asserts a unique output produced from stdin and waits for pre-input `READY`.
  EV-077 also reruns the seeded Activity on disposable services, including
  latest-input edits; EV-059 remains user confirmation, not runtime evidence.

## F2 — Learning assessment, provider and routed Web integration

### F2-T1 — Implement Learning mixed feedback, attempts, persistence and job

- **Status/owner:** `complete — integrated gates` — `/root/learning_server_resume`
- **Depends/parallel:** F1-T1 contracts complete. Parallel with F2-T2 and F2-T3;
  controller, provider composition and Web route generation remain separate.
- **Paths:** Learning core domain structures, entities and use cases listed in the
  Spec, including `apps/server/src/shifu/learning/core/domain/structures/{code_answer.py,activity_answer.py,code_rubric_result.py,evaluation_part_result.py,choice_activity_detail.py,code_question_detail.py,choice_attempt_detail.py,code_result_detail.py,__init__.py}`;
  `apps/server/src/shifu/learning/core/domain/entities/{activity_attempt.py,activity_evaluation.py}`;
  `apps/server/src/shifu/learning/core/use_cases/{preview_activity_question_feedback_use_case.py,get_choice_activity_use_case.py,submit_choice_activity_use_case.py,evaluate_choice_activity_use_case.py,get_choice_attempt_use_case.py,retry_choice_evaluation_use_case.py,__init__.py}`;
  `apps/server/src/shifu/learning/database/sqlalchemy/mappers/{activity_attempt_mapper.py,activity_evaluation_mapper.py}`;
  `apps/server/src/shifu/learning/rest/controllers/{preview_activity_question_feedback_controller.py,get_choice_activity_controller.py,submit_choice_activity_controller.py,get_choice_attempt_controller.py,retry_choice_evaluation_controller.py,__init__.py}`;
  `apps/server/src/shifu/learning/rest/router.py`;
  `apps/server/src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py`;
  `apps/server/src/shifu/learning/messaging/inngest/learning_inngest_messaging.py`;
  `apps/server/rest-client/learning/activities.rest`;
  `apps/server/tests/learning/core/use_cases/test_{get_choice_activity,preview_activity_question_feedback,submit_choice_activity,evaluate_choice_activity,get_choice_attempt,retry_choice_evaluation}_use_case.py`;
  `apps/server/tests/learning/server/controllers/test_{preview_activity_question_feedback,get_choice_activity,submit_choice_activity,get_choice_attempt,retry_choice_evaluation}_controller.py`;
  `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`.
- **Traceability:** Learning RP-09/11–14/18/25/27 and JN-07/08; RF-01/02,
  RF-04–10; CA-01/02, CA-05–13; CI-10/11/12; VM-04–07.
- **Outcome:** Preliminary choice/code feedback is stateless. Final submission
  stores one immutable mixed attempt and saved snapshot; Learning validates fixed
  assessor decisions, computes official scores and Concept evidence, and applies a
  single guarded progress effect. Legacy code answers/results still hydrate.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `core-layer-rules.md`, `use-case-testing-rules.md`, `rest-layer-rules.md`,
  `controllers-testing-rules.md`, `database-layer-rules.md`,
  `messaging-layer-rules.md`, and `jobs-testing-rules.md`.
- **Risks/controls:** Keep AI calls outside database transactions; recheck the
  active run before commit. Preview writes no attempt, evaluation, outbox or
  progress. Treat missing/invalid decisions and provider failure as inconclusive or
  typed failure, never zero. Preserve idempotent replay and once-only effects. No
  partial attempt or migration.
- **Exit:** Spec's named use-case tests cover no-write preview, exact saved project
  normalization, immutable replay after content change, weighted scoring, retry,
  stale run and duplicate effect. Real TestClient/PostgreSQL controller tests assert
  status/error, authorization, persistence and no-write preview; the real Inngest
  job test asserts registered evaluation and once-only effect. Preserve diagnostic
  examples and provide five labeled requests in activities.rest (GET Activity,
  POST preliminary feedback, POST mixed attempts, GET attempt, POST retry) with
  current methods/paths/parameters/headers/bodies, reusable non-secret variables
  and no credentials. Record route parity; examples do not substitute for the real
  integration boundaries.

### F2-T2 — Implement Intelligence Jev rubric assessor

- **Status/owner:** `complete — consumer evidence and app composition verified` — `/root/learning_intelligence_resume`
- **Depends/parallel:** F0 direct httpx dependency and F1 Shared assessor port
  complete. Parallel with F2-T1 and F2-T3; Orchestrator owns settings and app
  injection.
- **Paths:** `apps/server/src/shifu/intelligence/providers/code_rubric_assessor_provider/jev_code_rubric_assessor_provider.py`.
  Provider behavior is exercised through F2-T1's consuming Learning controller/job
  integration tests; no provider-owned test file is permitted by the Rule Pack.
- **Traceability:** Learning RP-12/13/27 and JN-07/08; RF-04/05/08/09;
  CA-05/06/09/10; CI-10/12; VM-04/05/07.
- **Outcome:** Intelligence implements the Shared port with typed Pydantic
  Decisions transport, pinned Jev model selection from typed settings and closed
  criterion/Concept option sets. Learning retains scoring, comments, authorization
  and progress ownership.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `core-layer-rules.md`, `provision-layer-rules.md`, `ai-layer-rules.md`,
  `server-app-layer-rules.md`, and `documentation/modules.md`.
- **Risks/controls:** No Learning/Curriculum imports, free-form feedback, raw
  provider payload leakage, browser key, TypeSafe SDK or Agno. Use controlled HTTP
  responses and failure cases; do not call OpenRouter live in deterministic gates.
- **Exit:** Implementation review checks request shape, Pydantic response
  parsing, missing/invalid keys and typed availability failures against the
  Shared port. F2-T1's consuming Learning/controller/job tests use controlled
  HTTP responses to prove the composed module boundary; Orchestrator runs them
  at integration. Any live OpenRouter smoke check is separate, optional and
  dependent on an authorized environment credential.

### F2-T3 — Integrate mixed Activity service, Page and protected route

- **Status/owner:** `complete — integrated route E2E` — `/root/learning_activity_route_injection_fix`
- **Depends/parallel:** F1-T2 and the Spec's fixed mixed transport contract.
  Parallel with F2-T1 and F2-T2. Keep the existing public URL and generated route
  tree ownership.
- **Paths:** `apps/web/src/core/learning/choice-activity.ts`;
  `apps/web/src/rest/services/learning-service.ts`;
  `apps/web/src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts,tests/activity-page.test.tsx,tests/use-activity-page.test.ts,choice-question/index.tsx,choice-question/choice-question.css,choice-question/tests/choice-question.test.tsx,question-feedback/index.tsx}`;
  source move paths `apps/web/src/ui/learning/widgets/pages/choice-activity-page/{index.tsx,use-choice-activity-page.ts,tests/choice-activity-page.test.tsx,tests/use-choice-activity-page.test.ts,choice-question/index.tsx,choice-question/choice-question.css,choice-question/tests/choice-question.test.tsx}`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx`;
  `apps/web/tests/routes/learning/activities.$activityId.index.test.tsx`;
  `apps/web/tests/learning/activity-page.test.ts`.
- **Traceability:** RF-01–07; CA-01–08/14; CI-01–06; VM-01–04/06.
- **Outcome:** The neutral Activity Page preserves choice behavior and adds the
  ordered code question, stateless feedback, frozen source, stale-response guard,
  final submission and unsent-work leave warning. The browser sends the Spec's
  revision, mixed answers and stable submission key through the existing route.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `ui-layer-rules.md` including **Antipatterns to Avoid**,
  `web-app-routing-rules.md`, `rest-layer-rules.md`, `widget-testing-rules.md`, and
  `documentation/design.md`.
- **Risks/controls:** Preserve choice controls, protected route and URL; do not
  expose private keys/rubric data or rely on browser mocks as persistence evidence.
  Generated route metadata is Orchestrator-owned. Route output must be generated,
  never hand-edited.
- **Exit:** Page, hook and route suites cover loading/error/recovery, choice and
  code sequence, frozen answers, request method/path/body, resulting URL, auth,
  keyboard/focus and navigation warning. Compare choice state against its existing
  handoff and code state against lZDH7 at 1440 × 900 and the accepted 390 × 844
  layout. Capture fresh Playwright screenshots; inspect console, failed requests and
  HTTP statuses.

### F2-T4 — Integrate mixed official result details

- **Status/owner:** `complete — ACH-013 resolved in EV-069` — scoped Builder Fix `/root/learning_result_mobile_summary_fix`
- **Depends/parallel:** F2-T1 result DTO and F2-T3 Activity contract inspected in
  the current revision 11 worktree; predecessor exact-state choice/result visual
  references were refreshed in EV-37. The predecessor visual gate is satisfied.
  This path is separate from the Activity Page task and can run while
  Server/Intelligence work remains active.
- **Paths:** `apps/web/src/ui/learning/widgets/pages/choice-result-page/{index.tsx,use-choice-result-page.ts,choice-result-detail/index.tsx,choice-result-detail/tests/choice-result-detail.test.tsx,tests/choice-result-page.test.tsx,tests/use-choice-result-page.test.ts}`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/index.tsx`;
  `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx`;
  `apps/web/tests/learning/choice-result-page.test.ts`.
- **Traceability:** RF-09/10; CA-09–14; CI-01–06; VM-05/07.
- **Outcome:** Official score/progress lead the result. Ordered question summaries
  begin collapsed and expand independently; code details show rubric and saved
  files read-only without a terminal; choice disclosure and existing next-step
  behavior remain protected/preserved.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `ui-layer-rules.md` including **Antipatterns to Avoid**,
  `web-app-routing-rules.md`, `rest-layer-rules.md`, `widget-testing-rules.md`, and
  `documentation/design.md`.
- **Risks/controls:** Do not change recommendation behavior, expose another
  account's source, or boot WebContainer on the result route. Reuse existing result
  components and responsive shell.
- **Exit:** Page/hook/route suites verify pending/failure/retry/completed states,
  multiple independent disclosure state, keyboard/ARIA, private source and result
  URL. Compare O070h, oPNtH and Qxidv (including full-page scroll at 1440 × 900)
  and existing choice references. At 390 × 844 verify single-column flow,
  collapsible enunciado/file tree, terminal tab layout on Activity, no horizontal
  overflow and reachable actions. Capture fresh Playwright screenshots and inspect
  console, failed requests and HTTP statuses.

## F3 — Orchestrator integration and final evidence

### F3-T1 — Compose the application and reconcile generated routes

- **Status/owner:** `complete — integrated composition and generated routes verified` — Orchestrator
- **Depends/parallel:** F0–F2 focused implementation exits complete. No active
  Builder overlaps these shared paths.
- **Paths:** `apps/server/src/shifu/app.py`;
  `apps/server/src/shifu/learning/pipes/learning_pipe.py`;
  `apps/server/src/shifu/shared/settings.py`;
  generated `apps/web/src/routeTree.gen.ts` via the declared web route generator.
- **Traceability:** Spec Runtime Decisions and affected paths; RF-03/04/08/09;
  CA-03–13; CI-01–CI-13; VM-01–07.
- **Outcome:** Construct one Intelligence provider and inject it through the Shared
  port into Learning HTTP and Inngest; close its HTTP client on application
  shutdown; inject the browser runner at the route boundary; register the new
  controller and produce reviewed route metadata without import-time I/O.
- **Rules:** `documentation/rules/server-app-layer-rules.md`,
  `provision-layer-rules.md`, `web-app-routing-rules.md`, and
  `documentation/modules.md`.
- **Risks/controls:** Keep module ownership intact and keep external I/O out of
  import-time composition. Do not hand-edit route metadata or infer production
  hosting configuration from local Vite settings.
- **Exit:** Run the declared `pnpm --filter web generate-routes`, review the
  generated diff, then run the full commands listed in Validation and handoff.
  Inspect application startup/shutdown, provider injection, registered Learning
  function, HTTP route and Web route behavior.

### F3-T2 — Complete integrated validation and Evaluation evidence

- **Status/owner:** `complete — EV-077–081; revision 15 evidence boundary` — Orchestrator
- **Depends/parallel:** F3-T1. Run only after all integrated code is stable; refresh
  affected evidence after any correction.
- **Paths:** Evaluation evidence in the eventual
  `documentation/features/learning/js-code-question/evaluation.md` and the local
  fixture `apps/server/src/shifu/shared/database/seed_data.py`; transient
  browser captures stored outside tracked repository paths. Do not commit
  screenshots, browser storage, credentials, or runtime artifacts.
- **Traceability:** All RF-01–RF-11, CA-01–CA-15, CI-01–CI-13, VM-01–VM-07 and
  route-client parity.
- **Outcome:** Evaluation records actual commands, app/DB/job boundaries, HTTP and
  persisted state, screenshots, limitations and traceability disposition. Mocked
  transport and mocked WebContainer evidence
  remain labeled as boundary evidence only.
- **Rules:** `documentation/rules.md`, `documentation/tooling.md`, all selected
  Rule Packs in the Spec, and the Playwright CLI workflow in `AGENTS.md`.
- **Risks/controls:** Verify Compose services and health before browser scenarios;
  use disposable fixtures and accounts; do not reset shared data, stop shared
  Docker services, emit deployed events, or use production credentials. Stop only
  app processes started for validation. Keep controlled Jev and controlled HTTP
  responses deterministic; no live OpenRouter call is required.
- **Exit:** Automated gates are recorded in EV-031/032/035/037 and current
  candidate Web/Server results in EV-067/078. EV-077 records the seeded persisted
  result, WebContainer input, fallback and preview no-write counts. EV-080/081
  document the user-authorized supplemental-evidence disposition and independent
  Spec review. REST parity and structural mapping remain recorded in EV-028/034.
  No Alembic migration is expected.

### F3-T3 — Verify REST artifact parity and structural path map

- **Status/owner:** `complete` — Orchestrator
- **Depends/parallel:** F3-T2's integrated route contract; record with final
  evidence baseline.
- **Paths:** `apps/server/rest-client/learning/activities.rest` and Evaluation.
- **Traceability:** CA-01–08/12; CI-11; VM-01/04–07.
- **Outcome:** The REST artifact preserves existing diagnostic examples and
  contains one labeled request for each current route: GET Activity, POST
  preliminary question feedback, POST final attempts with a representative mixed
  body, GET attempt, and POST retry.
- **Rules:** `documentation/rules/rest-layer-rules.md` and
  `documentation/tooling.md`.
- **Risks/controls:** Keep methods, paths, parameters, headers and bodies aligned
  with route declarations; use reusable non-secret variables and no credentials.
  REST examples do not replace real HTTP/PostgreSQL evidence.
- **Exit:** Manually compare all five labeled requests to the route declarations,
  verify reusable local variables and credential absence, then record parity in
  Evaluation. Complete the Orchestrator's manual Spec-to-path structural review
  there; do not invent or claim a `check:spec-implementation` command.

## F4 — Independent review and conclusion handoff

### F4-T1 — Review one integrated candidate

- **Status/owner:** `complete — EV-079` — one Implementation Reviewer, read-only
- **Depends/parallel:** F3-T1–T3 and all baseline evidence complete; no ongoing
  Builder changes during the initial review.
- **Paths:** Review the integrated implementation, Spec, Plan and Evaluation;
  the reviewer edits no files.
- **Traceability:** All RF/CA/VM/CI plus module ownership, route parity, visual
  evidence and contract/path map.
- **Outcome:** One independent findings pass covers the exact integrated
  candidate. Findings are returned to the owning Builder or Orchestrator through
  `implement-spec`; the reviewer does not amend the Spec or Plan.
- **Rules:** `documentation/agents/implementation-reviewer-agent.md`,
  `documentation/rules.md`, and the selected Rule Packs.
- **Risks/controls:** Evidence is invalidated for affected gates after a fix; the
  Orchestrator verifies fresh results before conclusion. Preserve the single
  reviewer checkpoint and use a manual structural path-map Evaluation row rather
  than fabricating an unavailable command.
- **Exit:** EV-079 found no actionable implementation or Contract finding; its
  documentation evidence request was resolved in EV-078. EV-081 independently
  approved the revision 15 evidence-scope amendment after one wording correction.
  No further checks were run per the user's direction.

# Validation and handoff

## Evidence coverage

| Type | Scenario/surface | Criteria | Evidence target | Status |
| --- | --- | --- | --- | --- |
| Automated | Web lint, architecture, types, unit, integration and build: CI-01–CI-06 | CA-01–14 | EV-078; all six current Web gates pass, including serial integration 92/92 | `complete — CI-01–06` |
| Automated | Server lint, architecture, types, unit, integration, jobs and build: CI-07–CI-13 | CA-01–13 | EV-031/067/071; all seven gates pass; Testcontainers own PostgreSQL/Inngest fixtures | `complete` |
| Manual/runtime | Retained VM-01/02/03/05 and automated substitutes for VM-04/06/07 | CA-01–CA-15 | EV-077 persisted journey; EV-067/078 automated Server and route evidence. Remaining live matrices are supplemental under Spec revision 15 (EV-080/081). | `complete — retained evidence and approved scope disposition` |
| REST parity | Five current Activity route patterns in activities.rest | CA-01–08/12 | EV-028 confirms all five requests, methods, paths, params, headers and representative bodies; no credentials | `complete` |
| Visual | Retained responsive/runtime states and supplied references | CA-01–06/10/13/14 | EV-045/061/064/068/069/077; exact VIS-02/05 comparisons are supplemental under Spec revision 15 (EV-080/081) | `complete — retained visual evidence and approved scope disposition` |
| Structural review | Manual Spec-to-path ownership map; no declared command exists | All RF/CA and module boundaries | Evaluation contains the Orchestrator's ownership map and evidence boundary | `complete — EV-034` |
| Independent review | Read-only Spec and Implementation Reviewer passes | All RF/CA/VM/CI | EV-079 found no actionable implementation/Contract defect; EV-081 approved the revision 15 evidence-scope disposition after one visual wording correction | `complete — EV-079/081` |

## Handoff rules

- Keep this Plan `in_progress` during implementation. The Spec scope-path gate
  is resolved at revision 10 and Evaluation was opened at kickoff. Only
  `conclude-spec` marks the Plan completed.
- Builders report task outcomes, paths, checks and evidence to the Orchestrator;
  they do not edit the Spec, Plan, Evaluation or shared paths unless assigned by
  the Orchestrator. Active Builder paths must not overlap.
- Run two implementation waves, with no more than three concurrent Builders.
  The result-page task alone waits for the existing Choice Activity visual
  evidence gate; F1 and the other F2 work do not wait on it.
- For any contract change, stop the affected task and use the relevant SDD or
  authority amendment workflow. Do not silently widen this Plan.
- Before `conclude-spec`, reconcile each CA, VM, CI, REST request, visual state
  and reviewer finding against current Evaluation evidence.

# Execution log

| Date | Event | Effect on execution |
| --- | --- | --- |
| 2026-09-26 | CodeGraph queries: “Learning Activity mixed choice and javascript stdin question lifecycle: Curriculum snapshots, Learning preliminary and official assessment, web editor/WebContainer/xterm, REST routes, Inngest job, tests and callers” and “Learning Activity HTTP route group: get_choice_activity_controller, submit_choice_activity_controller, get_choice_attempt_controller, retry_choice_evaluation_controller, learning router; Curriculum activity_mapper and curriculum_content_provider callers; Shared CurriculumContentProvider contract and Learning tests”. | Existing call paths are choice-oriented; CurriculumContentProvider has broad reuse, so retain the legacy choice accessor and add the mixed snapshot contract at its owning boundary. |
| 2026-09-26 | Planning preflight found the Spec scope-path mismatch and the predecessor Choice Activity Plan's stale result-page evidence. | Keep Plan `draft`; correct/reconcile the Spec path before any Builder starts, and gate only F2-T4 on predecessor visual recapture. |
| 2026-09-26 | Implementation kickoff opened Evaluation and corrected the Spec's stale scope path and VM table header as typo-only documentation fixes. | Spec stays `ready` revision 10; Plan enters `in_progress`; F0 begins. The predecessor visual gate remains scoped to F2-T4. |
| 2026-09-26 | F0 installed direct dependencies, added Vite isolation middleware and verified dev/preview HTML responses, Web type check and build (EV-003–006). | F0 complete. Preview `/` 500 is tracked as ACH-003 for F3 classification; preview `/login` 200 verifies production-preview headers. |
| 2026-09-26 | Corrected F1 execution exits that had depended on consuming F2 routes/browser scenarios, while preserving every Spec CI/VM criterion (ACH-004). | Activate `/root/learning_content_contract_builder` and `/root/learning_browser_practice_builder` on non-overlapping F1 paths; final consuming evidence stays in F2/F3. |
| 2026-09-26 | Classified preview `/` 500 through CodeGraph root/auth path and Better Auth config: local production-mode auth/BFF secrets are unset (EV-008). | ACH-003 resolved as environment-specific; local F3 browser evidence uses dev, while production auth remains a release configuration concern. |
| 2026-09-26 | Assigned `/root/choice_visual_evidence_runner` to collect predecessor Choice Activity stale visual captures without repository edits (EV-009). | Orchestrator retains predecessor SDD review/closure and F2-T4 gate decision; collection runs alongside non-overlapping F1 Builders. |
| 2026-09-26 | F1 Content Builder found the Plan's provider-owned focused test path conflicts with the selected provision-layer Rule (EV-011). | Removed the forbidden test placement from F1; concrete provider coverage stays assigned to F2 consuming real controller tests, with CI-11 unchanged. |
| 2026-09-26 | Same provision-layer Rule audit found F2-T2's proposed Intelligence provider-owned test path is forbidden (EV-012). | F2-T2 owns only the adapter; controlled HTTP response assertions are integrated through F2-T1's consuming controller/job tests. No CI/VM coverage is removed. |
| 2026-09-26 | First predecessor visual recapture used isolated Vite/Playwright route mocks, but screenshots retained the SSR login form above routed content (EV-013). | Captures are diagnostic only; F2-T4 remains gated. Evidence helper is pursuing a clean isolated authenticated fixture and settled exact-state captures. |
| 2026-09-26 | F1 Content Builder completed Shared/Curriculum source and allowed focused tests; Orchestrator reran lint, type, architecture and 14 focused/legacy tests (EV-014). | F1-T1 focused exit complete; F2 consuming controller/job evidence remains mandatory. |
| 2026-09-26 | Opened scoped Spec revision 11 amendment to state that public CodeQuestionDetail includes Curriculum fixed dependency names/versions (ACH-005). | Spec is draft pending independent Spec Reviewer/integrity; F2 DTO work waits. Revision 10 F1 work remains valid because project snapshots/runner already carry the fixed list. |
| 2026-09-26 | Spec Reviewer found revision 11 transport amendment compatible and rechecked the added GET public/private assertion; Orchestrator structural integrity passed (EV-016). | Spec returned to `ready`; F2 public DTO work is unblocked. F1 output is compatible with revision 11. |
| 2026-09-26 | F1 Web Practice Builder corrected transcript run isolation and the complete-command allowlist control; Orchestrator reran focused Web gates (EV-017). | F1-T2 focused exit complete; integrated WebContainer/browser VM-02/03 remain F3 evidence. |
| 2026-09-26 | Activated three non-overlapping F2 Builders from ready Spec revision 11 (EV-018). | Learning Server, Intelligence adapter and Activity Page work in parallel; Orchestrator retains composition, generated routes, result gate and integrated evidence. |
| 2026-09-26 | Predecessor choice VIS-01–06/08/11/12 were recaptured cleanly with mock-backed transport and reviewed against saved references (EV-019); its VM-02/06 real behavior remains open. | F2-T4 visual prerequisite is satisfied without claiming predecessor F3-T1 completion; this feature still requires its own real persisted result VM-05/07. F2-T4 now waits only on F2 DTO/Page dependencies. |
| 2026-09-26 | Resumed the interrupted F2 assignments from the shared partial worktree; Evaluation EV-020 records active ownership and EV-021 records the Intelligence adapter review. | Preserve prior edits, finish F2-T1/T3 within their assigned paths, verify controlled assessor responses through consuming tests, then start F2-T4 when dependencies are met. |
| 2026-09-26 | CodeGraph readiness query covered the mixed official result page, result route and DTO callers; revision 11 contracts and the current mixed result DTO are present. | Activated Builder Result Page as F2-T4 on its separate Web paths; it must validate integrated evidence after F2-T1/T3 complete. |
| 2026-09-26 | F2-T3 resumed Builder confirmed the existing mixed Activity flow and focused Web gates pass (Evaluation EV-023). | F2-T3 implementation exit is complete; real persistence/auth, generated route metadata, visual VM states, and final integrated gates remain assigned to the Orchestrator. |
| 2026-09-26 | F2-T4 result page focused suites passed; mocked full-page captures retained the initial login shell above client-navigated content (Evaluation EV-024). | Builder implementation is complete; Orchestrator must verify the authenticated result route and fresh exact-state screenshots in F3. |
| 2026-09-26 | F2-T1 completed mixed unit, TestClient/PostgreSQL, Inngest, lint/type/architecture gates; F2-T2 controlled adapter success/failure was covered through the registered Learning job (Evaluation EV-025). | F2 implementation ownership is complete at focused level; F3 composition, route generation, integrated validation and visual evidence are active. |
| 2026-09-26 | Orchestrator found ACH-008: the code question constructed its default WebContainer adapter inside the UI. F1-T2 removed that fallback; Evaluation EV-027 records the scoped fix and stale evidence. | F1-T2 now uses only an injected runner factory; F2-T3 is wiring the provision adapter from the Activity route and will rerun Page/route checks. |
| 2026-09-26 | The route injection assertion reached the terminal waiting state but Chromium could not click the submit button because xterm repeatedly emitted ResizeObserver loop errors (Evaluation EV-029). | Opened ACH-009 and activated a Builder Fix only on F1-T2 code-terminal paths; F2 route ownership retains the Playwright assertion for rerun. |
| 2026-09-26 | F1-T2 coalesced terminal resize notifications and F2-T3 kept route-owned runner injection. The exact Activity route test passed after the correction; integrated Learning browser routes passed (Evaluation EV-030/032). | ACH-008/009 resolved. Focused implementation exits are complete; real persisted desktop/mobile VM and visual evidence remain F3 requirements. |
| 2026-09-26 | Orchestrator reran all Web and Server CI gates. Web lint/architecture/types/unit/build and all Server gates passed; the 92-case Playwright suite completed with 84 passing and 8 Identity auth-handler 503 failures in the local auth configuration (Evaluation EV-031/032). | Keep CI-05 failed with its unrelated local auth configuration limitation; do not claim the full acceptance suite passes. |
| 2026-09-26 | Started the documented FastAPI launcher, verified `/health` 200 and `/api/inngest` `function_count: 7`, then stopped the application with lifespan shutdown complete (Evaluation EV-033). | Shared Compose stayed running; no event was sent. Obtain a disposable authenticated learner and released mixed Activity fixture before persisted VM scenarios; do not seed/reset shared data. |
| 2026-09-26 | Recorded the manual Spec-to-path ownership map for all RF/CA slices, alongside REST artifact parity and CI dispositions (Evaluation EV-028/034). | F3-T3 complete. F3-T2 remains open for authenticated VM/VIS evidence; F4 review follows that evidence baseline. |

| 2026-09-26 | Full Web integration was rerun with isolated local auth/BFF and database configuration; 92 tests passed and the opt-in live test was skipped in the full gate (Evaluation EV-035). | CI-05 is now pass for the configured gate. Preserve EV-032 as the earlier failure under the unconfigured local environment; the dedicated opt-in fixture journey is recorded separately. |
| 2026-09-26 | Provisioned disposable learner and released mixed Activity in isolated PostgreSQL; the authenticated live route, WebContainer, inconclusive/recovery feedback, result, keyboard disclosures and mobile result passed (Evaluation EV-036). | VM-01/02/04/05 and VIS-01–05 are partial. VM-03/06/07, edit-triggered rerun, live preview no-write row count, exact all-open desktop visual state and MCP Inngest/outbox trace remain open. Stopped only task-started apps and disposable DB; shared Compose remains running. |
| 2026-09-26 | Refreshed Web lint/types and whitespace checks after the opt-in browser test was added (Evaluation EV-037). | CI-01 and CI-03 pass with current file set; F3-T2 remains open for the runtime evidence gaps above. |

| 2026-09-26 | Fixed the desktop code-practice workspace overflowing short viewports; the Activity route browser scenario now checks the terminal bounds at 1440 × 800 and passed (Evaluation EV-038). | The terminal and controls fit inside the viewport while the editor, terminal output and prompt can scroll within their panels. Mobile layout remains single-column and naturally sized. |

| 2026-09-26 | Replaced the terminal's exposed command ID with an understandable permitted-command label; the live route assertion and current screenshot pass (Evaluation EV-039). | `run-main` remains an internal dispatch identifier; the learner sees `Executar node src/main.js`. |

| 2026-09-26 | Removed the redundant note below the practice terminal; the Terminal retains its own status and unavailable message, confirmed in Evaluation EV-040. | Focused route, Web unit, lint and type checks pass; refreshed screenshot is retained under `/tmp`. |
| 2026-09-26 | Installed `@reui/c-tree-5` with the requested shadcn CLI, adapted the generated tree to Shifu's fixed project files, and connected sidebar selection to the shared editor (Evaluation EV-041). | Focused tree/editor/widget checks and the 1440 × 800 Activity route pass; F3's persisted and mobile evidence gaps remain open. |
| 2026-09-26 | Orchestrator removed the separate stdin and command-entry forms plus the Execute action from the practice terminal, and removed the now-unused command-button runner API. | EV-043 verifies direct xterm stdin against the allowlisted entrypoint; remaining VM-03/06/07 and resize evidence stay open. |
| 2026-09-26 | Orchestrator made Monaco's language explicit by selected-file extension and added a Shifu-scoped dark theme with clearer JavaScript token roles and bracket guides. | EV-046/047 track focused and route browser evidence; unsupported extensions stay plain text. |
| 2026-09-26 | Corrected the editor canvas after the user reported that Monaco rendered white despite the custom token colors. | EV-048 verifies the explicit dark canvas and gutter colors in the real route browser test. |
| 2026-09-26 | Matched the code-editor syntax palette to the user's pink, lavender, mint and warm-number reference. | EV-049 verifies the token and canvas colors in the real route browser capture. |
| 2026-09-26 | Reconciled Spec/Plan revision 12 for RF-11/CA-15; scoped Builder added desktop resize handles and hook/widget coverage. Orchestrator inspected default/resized/mobile Playwright CLI captures and observed pointer/keyboard, preserved source/transcript and no mobile overflow (Evaluation EV-044). | F1-T2 resize slice complete. F3-T2 remains in progress for the existing VM-02 rerun and VM-03/06/07 gaps; single Implementation Reviewer is active. |
| 2026-09-26 | The single Implementation Reviewer found editor and border-width bounds defects (ACH-010). Scoped Builder corrected both; Orchestrator reran focused tests, Web lint/types/architecture, Activity route and authenticated default/resized/mobile Playwright CLI captures; the same Reviewer found no further issue (Evaluation EV-045). | RF-11/CA-15 resize slice complete and current. F3-T2 stays in progress for the earlier VM-02 edit-triggered rerun and VM-03/06/07 gaps; no release-readiness claim. |
| 2026-09-26 | User approved Learning PRD RP-11/JN-07 version 22 for immediate JavaScript output before stdin. Spec revision 13 independently reviewed ready; F1-T2 scoped runner correction assigned and F3-T2 VM-02 output/edit/allowlist evidence reopened. | Exact Curriculum command must be permitted on every automatic run; historical EV-045 resize evidence remains valid, while pre-input behavior requires fresh browser evidence. |
| 2026-09-27 | Conclusion preflight compared current browser evidence with the later mobile UI candidate. EV-050 records a 36,694px terminal region at 390 × 844; CodeGraph returned the current terminal widget and its Activity Page call chain (Evaluation EV-060). | Reopen only the F1-T2 terminal UI slice under ACH-011. Refresh VM-02 and VIS-01 after the correction, then reconcile all remaining partial VM/VIS evidence before completing this Plan. |
| 2026-09-27 | Fresh current-candidate result capture showed the question type/title colliding with its score at 390 × 844. The full-page screenshot also contains stale login-fixture content and is rejected as evidence (ACH-013). | Reopen only F2-T4's result summary under a scoped Builder Fix; verify no overlap at 390px, capture the result main element without fixture residue, then resume F3-T2. |
| 2026-09-27 | Scoped result Builder Fix stacked mobile summary labels above their scores, retained the desktop row, added mobile geometry assertions, and recaptured the result main at mobile plus collapsed/expanded desktop. | EV-069 passes the focused result widget and route checks; ACH-013 is resolved. F2-T4 is complete; persisted result/job evidence and mobile fallback remain open in F3. |
| 2026-09-27 | Added a fixed mixed JavaScript stdin Activity to the existing development seed learner's Repetition competency. An initial real-backend Playwright test draft was removed from `apps/web/tests` after Spec review because route suites use mocked transport; the journey is manual CLI evidence. | EV-071 records seed construction and earlier workspace gates; EV-073 records the test-integrity correction. The manual journey and VM-03/06/07, VM-04 row-count and VM-05 job/outbox evidence remain open until an isolated seeded API/database with deterministic assessor is available. |
| 2026-09-27 | Reran the full Web integration suite after removing the real-backend test from test discovery. | EV-074 records 92/92 passing with no skipped tests; the persisted journey remains an in-scope manual VM evidence item. |
| 2026-09-27 | Final independent Implementation Reviewer rechecked the integrated Spec, Plan, Evaluation, scope boundary, CI-05 disposition and current ledgers after the EV-072 corrections (Evaluation EV-075). | No review-documentation findings remain. Runtime evidence and some visual states are still open, so F3/F4 and the overall Plan remain `in_progress`. |
| 2026-09-27 | The scoped F1-T2 fix kept stdin writes on the active WebContainer PTY and added a unique program-output route assertion. The isolated seeded Activity then completed practice, preview, official submit and protected result read; a forced module-load failure exercised the mobile practice fallback (Evaluation EV-077). | ACH-019 resolved and F1-T2 complete. VM-01/02/03/05 plus preview no-write counts are verified; VM-04 recovery, VM-06/07 and visual-reference comparisons remain open. |
| 2026-09-27 | Current Web lint, architecture, types, unit, build and serial integration gates passed on the corrected runner candidate; focused Server Learning tests passed 110 with 2 environment skips (Evaluation EV-078). The final independent reviewer reported no implementation/Contract finding and confirmed the remaining gates are partial; the review's CI evidence request was reconciled. | F4 is complete (EV-079). F3 and the Plan remain `in_progress` for VM-04 recovery, the two-account VM-06 matrix, VM-07 persisted failure/retry/stale-duplicate traces, and remaining visual comparisons. The isolated runtime was stopped after evidence capture. |
| 2026-09-27 | Revision 15 retained product behavior and automated acceptance while making the selected live matrices and exact visual comparisons supplemental. The Spec Reviewer approved it after one Design Contract wording correction (Evaluation EV-080/081). | VM-04/06/07 live repetitions and VIS-02/05 exact comparison are explicitly non-gating; their IDs/evidence remain traceable. All retained CI/runtime/REST/review evidence is reconciled. Spec, Plan and Evaluation are concluded without rerunning waived checks. |
| 2026-09-26 | Scoped Builder implemented revision 13 pre-input runner behavior. Orchestrator validated authenticated output before stdin, latest-input rerun, startup output, missing-command rejection and waiting-input fallback in a real WebContainer; focused Web gates and route passed. Independent Implementation Reviewer cleared the final correction (EV-050). | F1-T2 pre-input slice complete; F3-T2 remains partial for PTY EOF-dependent programs, mobile terminal height, VM-03/06/07 and remaining full feature evidence. |
| 2026-09-26 | Removed the resize handle's focus outline while preserving its green keyboard-focus fill and center line. | Recorded as EV-051; browser appearance and interaction have not been revalidated. |
| 2026-09-26 | Added a reusable Activity question header and progress bar, shared by choice and code questions. | Recorded as EV-052; the browser layout has not been revalidated. |
| 2026-09-26 | Aligned the official mixed result page's header, score, progress summary and collapsed/expanded question details with Pencil nodes `oPNtH` and `Qxidv`. | Focused component and route tests pass; current 1440 × 900 collapsed/expanded screenshots are inspected in EV-053. Full persisted, mobile and remaining feature VM/VIS evidence stays open. |
| 2026-09-26 | After the user noted the page became taller, removed the fixed desktop height from the code Activity wrapper while keeping a viewport-based minimum, so feedback and submit content expand the app shell with the document. | EV-054 verifies the shell reaches the submit action at a 520px viewport; focused route/component checks and Web type/lint pass. |
| 2026-09-26 | The user then reported the editor grew with that content. Bounded the code-question panel to the viewport while keeping feedback and submit content in the page flow. | EV-055 verifies the editor panel stays within 520px and the app shell still reaches the submit action. |
| 2026-09-26 | Replaced raw criterion keys with their authored names and restyled feedback cards to match the user's second screenshot. | EV-056 verifies visible title, weight, score and comment on the real Activity route; internal criterion key is absent. |
| 2026-09-26 | Removed the `Aguardando entrada padrão` label from the terminal header while the practice waits for stdin. | EV-057 records 6/6 focused terminal tests, Web type/lint checks and the Activity route browser scenario (1/1). |
| 2026-09-26 | Fixed the blank desktop account avatar by overriding Button sizing/padding that collapsed the icon to zero width; matched the selected Pencil header node `bwFPW/UHFSB`. | EV-058 records the refreshed screenshot and 32×32 button / 16×16 icon DOM measurements. |
| 2026-09-26 | Kept the AppLayout shell at 1600px, constrained choice Activity content to `max-w-7xl`, and let code questions fill the shell. | Recorded as EV-058; browser widths have not been revalidated. |
