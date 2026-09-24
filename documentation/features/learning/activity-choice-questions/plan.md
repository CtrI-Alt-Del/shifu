---
title: Learning Activity choice questions implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 3
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-74
last_updated_at: 2026-09-23
---

# Execution status

- **Spec:** [spec.md](./spec.md), revision 3, `completed` after implementation and
  independent Implementation Reviewer verification.
- **Why Plan-backed:** this slice crosses Curriculum and Learning, server and web,
  a PostgreSQL migration, outbox/Inngest, four HTTP operations, responsive browser
  states, and seven manual scenarios.
- **Plan:** `in_progress`; F2-T2 is complete again; F3-T1 remains open for ACH-10 visual
  recapture.
- **Next action:** refresh the remaining exact visual states currently marked stale in
  Evaluation before local feature conclusion.
- **Active blockers:** none. ACH-01–ACH-12 are resolved. Remaining Activity/result visual
  rows are explicitly marked stale until their matching states are refreshed.
- **Builders:** Builder Server — F2-T1 and Builder Web — F2-T2 completed their scoped
  assignments under Spec revision 3; ACH-06/07/08/09 are verified. Builder Web completed
  ACH-10 with focused Page checks and typecheck; Orchestrator recorded EV-34.
- **Shared ownership:** Orchestrator owns SDD artifacts, generated route metadata,
  package/lockfile changes if any, cross-Builder integration, Evaluation evidence,
  final validation, and the single Implementation Reviewer checkpoint.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Current Spec is `ready`, revision 3; RF-01–RF-11, CA-01–CA-12 and all three contracts are present; module-owned Page suites added to the route-file suite contract | Orchestrator | `confirmed` | Recheck exact revision at conclusion |
| Product authority | Learning PRD 83066881 v13, Curriculum PRD 83034113 v6, and SHIFU-74 read and match Spec traceability | Orchestrator | `confirmed` | Recheck PRD versions at conclusion; report any conflict |
| Design references | Nine saved PNGs have source viewport, visible inventory, state coverage and acceptance mapping in `design/handoff.md` | Orchestrator | `confirmed` | Use saved references; capture each current runtime state in F3 |
| Route-test parity | Spec revision 3 maps each of the three route files and both routed Page widgets to their dedicated Playwright suites | Builder Web | `confirmed` | Implement all five suites in F2 |
| API example | `apps/server/rest-client/learning/activities.rest` has four labeled requests matching the Learning route declarations | Builder Server / Orchestrator | `confirmed` | Verified in EV-14; no route changes after parity check |
| Runtime and fixture | Isolated PostgreSQL, Redis, Inngest, FastAPI/Web process, signed-in browser and registered Learning evaluation job were verified | Orchestrator | `confirmed` | EV-24/EV-26; all disposable processes/containers stopped after each run |
| Migration test boundary | Upgrade, downgrade and re-upgrade ran against disposable PostgreSQL with legacy rows/index assertions | Builder Server / Orchestrator | `confirmed` | VM-07 and CI-14/15 passed in EV-13 |

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Builder Server | F1 | Curriculum choice projection, Learning domain/use cases, persistence mapping and migration support the Spec contract | — | Builder Web F1 | `complete` | Focused/full use-case tests, lint/type/architecture checks and disposable migration lifecycle passed; EV-12–EV-13 |
| 1 | Builder Web | F1 | Safe question/result DTOs, shared choice controls, and question/result widgets cover the approved visual hierarchy | — | Builder Server F1 | `complete` | Orchestrator verified six focused suites (18 tests), typecheck and scoped Biome after the retry-guard correction; component states map to CA-02, CA-05–CA-08 and CA-10 |
| 2 | Builder Server | F2 | Four authenticated Learning routes and registered evaluation job persist and expose the required behavior | Builder Server F1 | Builder Web F2 | `complete` | HTTP/PostgreSQL and real Inngest job boundaries pass; `activities.rest` covers all four routes |
| 2 | Builder Web | F2 | Web service, nested Activity/attempt routes and dedicated route/Page suites exercise the fixed HTTP contract | Builder Web F1; Server F1 transport contract; Spec rev3 ready | Builder Server F2 | `complete` | Original route/Page suites passed; ACH-10 outer-container correction integrated and focused Page suites/typecheck pass in EV-34 |
| 3 | Orchestrator | F3 | Integrated candidate has current evidence, one independent review, resolved findings and a complete handoff | Both F1 and F2 tasks | — | `in_progress` | Spec revision 3 is reconciled; affected VM/VIS captures are refreshed, Web gates pass, and final evidence is current |

### Scoped Builder Fix — ACH-11 outbox notification wake-up

- **Status/owner:** `complete` — Orchestrator; in-contract infrastructure fix.
- **Spec:** revision 3; the durable outbox contract already requires prompt notification
  wake-up plus bounded polling recovery.
- **Finding:** the dedicated PostgreSQL listener executes `LISTEN` without committing
  the command, so PostgreSQL does not activate the subscription until the relay's
  30-second idle sweep.
- **Allowed paths:** `apps/server/src/shifu/shared/database/sqlalchemy/repositories/listeners/events_repository_listener.py`;
  `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`.
- **Prohibited paths:** Web, unrelated server paths, migrations, shared local data,
  generated artifacts, external systems, and unrelated SDD/design files.
- **Traceability:** RF-03, RF-09; CA-03, CA-05, CA-09; CI-12 and durable outbox
  delivery behavior.
- **Exit:** commit the LISTEN registration and add a real Inngest/PostgreSQL regression
  that requires an outbox-triggered evaluation to arrive well before the 30-second
  fallback; run the focused disposable job test and Server lint/type checks. All exits
  passed in EV-35.

### Scoped UI Fix — ACH-12 pending evaluation motion

- **Status/owner:** `complete` — Orchestrator; visual-only refinement.
- **Spec:** revision 3; preserves the existing pending state and approved status copy.
- **Focal motion:** three muted dots pulse beside “Avaliação em andamento” to show
  that evaluation is still active. The dots remain static when reduced motion is on.
- **Allowed paths:** `apps/web/src/ui/learning/widgets/pages/choice-result-page/index.tsx`;
  `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/choice-result-page.test.tsx`;
  `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx`.
- **Prohibited paths:** Server, unrelated Web paths, generated route metadata, shared
  styles, external systems, and unrelated SDD/design files.
- **Traceability:** RF-06; CA-05, CA-10, CA-12; pending result Page state.
- **Exit:** focused Page and attempt-route suites and Web typecheck pass; inspect the
  pending state at desktop and mobile with standard and reduced motion in Playwright,
  then run the Impeccable motion detector. Screenshots and results are recorded in
  EV-36.

## F1 — Domain, persistence and widget foundations

### F1-T1 — Establish Curriculum/Learning contracts and durable attempt state

- **Status/owner:** `complete` — Builder Server, assignment refreshed for Spec revision 3
- **Depends/parallel:** No implementation dependency; parallel with F1-T2. Preserve the
  Spec's fixed Curriculum → Learning snapshot and public result contracts.
- **Paths:**
  `apps/server/src/shifu/curriculum/core/domain/structures/{single_choice_question.py,multiple_selection_question.py}`;
  `apps/server/src/shifu/shared/core/domain/structures/{curriculum_choice_activity_snapshot.py,curriculum_choice_question_snapshot.py,curriculum_choice_option_snapshot.py,curriculum_choice_part_snapshot.py,__init__.py}`;
  `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py`;
  `apps/server/src/shifu/learning/core/domain/{entities/{activity_attempt.py,activity_evaluation.py,competency_progress.py},structures/{choice_activity_detail.py,choice_question_detail.py,choice_option_detail.py,choice_attempt_detail.py,choice_result_detail.py,__init__.py},events/activity_submission_requested_event.py,interfaces/{activity_attempts_repository.py,activity_evaluations_repository.py,skill_experiences_repository.py},use_cases/{get_choice_activity_use_case.py,submit_choice_activity_use_case.py,evaluate_choice_activity_use_case.py,get_choice_attempt_use_case.py,retry_choice_evaluation_use_case.py,__init__.py}}`;
  `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py`;
  `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`;
  `apps/server/src/shifu/fakers/curriculum/entities/activity_faker.py`;
  `apps/server/src/shifu/learning/database/sqlalchemy/{models/{activity_attempt_model.py,activity_evaluation_model.py},mappers/{activity_attempt_mapper.py,activity_evaluation_mapper.py},repositories/{activity_attempts_repository.py,activity_evaluations_repository.py,skill_experiences_repository.py}}`;
  `apps/server/migrations/versions/f64a8c3d7e21_add_choice_attempt_handoff.py`;
  `apps/server/tests/learning/core/use_cases/test_{get_choice_activity,submit_choice_activity,evaluate_choice_activity,get_choice_attempt,retry_choice_evaluation}_use_case.py`.
- **Traceability:** RF-01, RF-03–RF-09, RF-11; CA-01, CA-03–CA-09, CA-11–CA-12; RP-03/RP-04, RP-09/RP-10, RP-13–RP-18, RP-26, JN-07.
- **Outcome:** framework-independent contracts, eligibility and scoring use cases,
  immutable/idempotent attempt state, progress recomputation, repositories and nullable
  legacy-compatible migration exist under the specified ownership boundaries.
- **Rules:** `documentation/rules/python-conventions-rules.md`,
  `core-layer-rules.md`, `use-case-testing-rules.md`, `database-layer-rules.md`,
  `provision-layer-rules.md`.
- **Risks/controls:** migration classification and uniqueness affect existing records;
  preserve answers and legacy completed rows, use the specified archival failure
  classification, and validate upgrade/downgrade only with disposable PostgreSQL data.
  Keep answer keys in private snapshots and enforce exact-set scoring.
- **Exit:** focused use-case tests; `uv run poe check:lint`, `check:architecture`,
  `check:types`, `test:unit`; CI-14/CI-15 commands against disposable data; VM-07
  runs `uv run poe db:upgrade f64a8c3d7e21`, then
  `uv run poe db:downgrade e1a2b3c4d5e6` and re-upgrade, and records preflight counts,
  index/column checks and row comparison. No shared database reset or seed operation.

### F1-T2 — Build accessible question and result widgets

- **Status/owner:** `complete` — Builder Web, assignment refreshed for Spec revision 3
- **Depends/parallel:** No implementation dependency; parallel with F1-T1. Use the
  Spec's safe DTO shape and `design/handoff.md` as the fixed UI contract.
- **Paths:**
  `apps/web/src/core/learning/choice-activity.ts`;
  `apps/web/src/ui/shadcn/{radio-group.tsx,checkbox.tsx}`;
  `apps/web/src/ui/learning/widgets/pages/choice-activity-page/{index.tsx,use-choice-activity-page.ts,choice-question/{index.tsx,tests/choice-question.test.tsx},tests/{choice-activity-page.test.tsx,use-choice-activity-page.test.ts}}`;
  `apps/web/src/ui/learning/widgets/pages/choice-result-page/{index.tsx,use-choice-result-page.ts,choice-result-detail/{index.tsx,tests/choice-result-detail.test.tsx},tests/{choice-result-page.test.tsx,use-choice-result-page.test.ts}}`.
- **Traceability:** RF-02, RF-05–RF-07, RF-10; CA-02, CA-05–CA-08, CA-10; RP-09,
  RP-10, RP-14, RP-18, RP-25, RP-26, SHIFU-74.
- **Outcome:** sequential selection/validation UI and complete pending/failure/result
  presentations render safe server contracts, with visible focus, semantic controls,
  keyboard support and mobile target sizes. Freeze answers once submission starts so
  same-key transport retries keep the submitted payload immutable; expose unsent state
  for the Activity route's in-app navigation warning.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`,
  `ui-layer-rules.md` (including **Antipatterns to Avoid**), `widget-testing-rules.md`;
  apply `documentation/design.md` and the nine-state inventory in `design/handoff.md`.
- **Risks/controls:** never imply pending is zero or expose protected correct options;
  preserve only in-memory unsent answers and one submission key for transport retry;
  follow existing tokens and shell.
- **Exit:** colocated Vitest component/hook suites cover selection, forward-only flow,
  loading/empty/error where applicable, immutable same-key retry payload, pending, failure/retry, completed and
  protected/released detail behavior, including semantic keyboard/focus states. Save
  transient screenshots only as validation evidence; fresh reference comparisons occur
  in F3.

## F2 — HTTP, job, routes and browser integration

### F2-T1 — Expose Activity/attempt operations and register evaluation

- **Status/owner:** `complete` — Builder Server
- **Depends/parallel:** F1-T1 complete; parallel with F2-T2 against the exact four-route
  contract in Spec §3.
- **Paths:**
  `apps/server/src/shifu/learning/core/domain/structures/{choice_answer_submission.py,choice_submission_outcome.py,__init__.py}`;
  `apps/server/src/shifu/learning/core/use_cases/submit_choice_activity_use_case.py`;
  `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py`;
  `apps/server/src/shifu/shared/rest/middlewares/rate_limit_middleware.py`;
  `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py`;
  `apps/server/tests/fixtures/inngest_fixture.py`;
  `apps/server/src/shifu/learning/rest/controllers/{get_choice_activity_controller.py,submit_choice_activity_controller.py,get_choice_attempt_controller.py,retry_choice_evaluation_controller.py,__init__.py}`;
  `apps/server/src/shifu/learning/rest/router.py`;
  `apps/server/src/shifu/learning/pipes/learning_pipe.py`;
  `apps/server/src/shifu/rest/handlers/app_error_handler.py`;
  `apps/server/src/shifu/learning/messaging/inngest/{jobs/evaluate_choice_activity_job.py,jobs/__init__.py,learning_inngest_messaging.py,__init__.py}`;
  `apps/server/src/shifu/app.py`;
  `apps/server/rest-client/learning/activities.rest`;
  `apps/server/tests/learning/server/controllers/test_{get_choice_activity,submit_choice_activity,get_choice_attempt,retry_choice_evaluation}_controller.py`;
  `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`.
- **Traceability:** RF-01, RF-03–RF-09, RF-11; CA-01, CA-03–CA-09, CA-11–CA-12;
  RP-09/RP-10, RP-13–RP-18, RP-26, JN-07.
- **Outcome:** owner-authorized safe reads, idempotent submission, result/retry transport,
  explicit error mapping, outbox-backed registered Learning job and retry-safe official
  effects operate through the composed application. The use case classifies the fixed
  `{question_key, selected_option_keys}` input using its current Curriculum snapshot and
  reports replay status to the controller without exposing that flag in HTTP.
- **Rules:** `documentation/rules/python-conventions-rules.md`, `rest-layer-rules.md`,
  `controllers-testing-rules.md`, `database-layer-rules.md`, `provision-layer-rules.md`,
  `messaging-layer-rules.md`, `jobs-testing-rules.md`, `server-app-layer-rules.md`.
- **Risks/controls:** enforce server-side ownership and disclosure; do not infer answer
  kind in the controller or add a transport discriminator; job accepts only the current
  run ID and performs transactional effects once. Zero evaluation retries is
  the accepted Spec decision; retain independent durable outbox redelivery. Keep the
  existing shared Inngest endpoint and Identity registration.
- **Exit:** real TestClient/PostgreSQL controller tests assert response/error contracts,
  persistence, authorization and side effects; real Inngest Testcontainers job test
  asserts registration, strict event parsing, stale/duplicate/failure/deletion behavior.
  Add exactly four labeled `.rest` requests (GET Activity, POST attempts, GET attempt,
  POST retry) with current paths/parameters/headers/bodies, reusable non-secret
  variables, and no credentials. Record REST parity; examples do not replace integration
  tests.

### F2-T2 — Connect the web contract to nested Activity and attempt routes

- **Status/owner:** `complete` — Builder Web; ACH-10 correction verified in EV-34
- **Depends/parallel:** F1-T2 complete; parallel with F2-T1 because Spec fixes methods,
  paths, DTOs, errors and status codes. Generated route metadata is Orchestrator-owned.
- **Paths:**
  `apps/web/src/rest/services/learning-service.ts`;
  `apps/web/src/constants/routes.ts`;
  `apps/web/src/ui/learning/widgets/pages/choice-activity-page/{index.tsx,use-choice-activity-page.ts,tests/{choice-activity-page.test.tsx,use-choice-activity-page.test.ts}}`;
  `apps/web/src/ui/learning/widgets/pages/choice-result-page/{index.tsx,use-choice-result-page.ts,tests/{choice-result-page.test.tsx,use-choice-result-page.test.ts}}`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId.tsx` (remove);
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/{route.tsx,index.tsx,attempts/$attemptId/index.tsx}`;
  `apps/web/tests/routes/learning/{activities.$activityId.route.test.tsx,activities.$activityId.index.test.tsx,activities.$activityId.attempts.$attemptId.index.test.tsx}`;
  `apps/web/tests/learning/{choice-activity-page.test.ts,choice-result-page.test.ts,competency-detail-page.test.ts}`.
- **Traceability:** RF-01–RF-03, RF-05–RF-07, RF-10; CA-01–CA-03, CA-05–CA-08,
  CA-10–CA-12; RP-09/RP-10, RP-14, RP-18, RP-25/RP-26, JN-07.
- **Outcome:** authenticated nested routes consume the server operations, while Page
  hooks preserve saved-attempt return, visible-only result polling, retry, and unsent
  navigation-warning behavior. Each route file's final URL, rendered state and outgoing
  method/path/body are tested at its dedicated boundary.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`, `ui-layer-rules.md`
  (including **Antipatterns to Avoid**), `rest-layer-rules.md`,
  `web-app-routing-rules.md`, `widget-testing-rules.md`; use `documentation/design.md`
  and `design/handoff.md`.
- **Risks/controls:** keep access tokens server-side; use `ROUTES` for runtime
  navigation; keep routes thin by putting polling, saved-attempt recovery and selection
  guards in Page hooks; do not hand-edit `routeTree.gen.ts`. Mocked route transport
  proves only the browser boundary, not server persistence.
- **Exit:** parent-route suite asserts auth middleware, `Outlet` and child navigation;
  Activity-index suite asserts loading, error/recovery, question flow, final URL and
  requests; attempt-index suite asserts pending/failure/retry/completed states, return
  URL and requests; module-owned Activity and result Page suites exercise actual route
  composition and their visible page contracts. Activity integration also verifies the
  unsent-answer blocker for in-app navigation. Orchestrator runs the route generator
  after these files land, reviews parent/child output, then runs web gates. Visual screenshots and live
  persisted flow are F3 evidence.

## F3 — Integrated validation and handoff

### F3-T1 — Reconcile, validate, review once and prepare conclusion

- **Status/owner:** `in_progress` — Orchestrator
- **Depends/parallel:** F2-T1 and F2-T2 complete. This is the integrated phase; keep it
  `in_progress` while gates, runtime evidence, review findings or corrections remain.
- **Paths:** `apps/web/src/routeTree.gen.ts` (generated by
  `pnpm --filter web generate-routes`); `documentation/features/learning/activity-choice-questions/evaluation.md`;
  Plan status updates in this file. Review all changed application paths from F1/F2.
- **Traceability:** RF-01–RF-11; CA-01–CA-12; VM-01–VM-07; CI-01–CI-15; RP-03/RP-04,
  RP-09/RP-10, RP-13–RP-18, RP-25/RP-26, JN-07.
- **Outcome:** complete integrated diff is reconciled to the current Spec revision, all applicable
  evidence is current and accepted, one read-only Implementation Reviewer has completed,
  verified findings are resolved, and Evaluation is ready for `conclude-spec`.
- **Rules:** all selected Rule Packs in the adjacent task cards; repository SDD lifecycle
  in `documentation/sdd.md`; browser validation follows applicable Agent Guide rules.
- **Risks/controls:** verify migration and browser fixture only on disposable data;
  distinguish mocked route tests from real HTTP/DB and job evidence. If Spec revision or
  authority changes, stop, invalidate affected assignments/evidence and reconcile before
  resuming.
- **Exit:** generated artifacts reviewed; all commands CI-01–CI-15 pass without lowering
  floors; VM-01–VM-07 and every design-state comparison have current evidence at the
  listed viewport and state. Verify keyboard/focus/accessibility and narrow viewport
  behavior; exercise loading, error and recovery states where applicable; inspect
  console errors, failed requests and HTTP 4xx/5xx responses; capture a fresh Playwright
  CLI screenshot for every listed state. REST parity is recorded; exactly one
  Implementation Reviewer completes after automated gates and evidence baseline.
  Resolve findings through `implement-spec`, invalidate stale evidence, rerun affected
  exits and resume the same Reviewer. Evaluation is ready for `conclude-spec`.

#### Scoped Builder Fix — ACH-06 result wire mapping

- **Status/owner:** `complete` — Builder Web (`/root/learning_activity_web_builder`)
- **Spec:** revision 3; in-contract correction, no Spec or product behavior change.
- **Finding:** API serializes result fields as `question_key`, `selected_option_keys`,
  and `disclosed_correct_option_keys`, while Web `AttemptWire` expected different names.
- **Allowed path:** `apps/web/src/rest/services/learning-service.ts` only.
- **Prohibited paths:** Server, all other Web paths, generated route metadata, SDD/design/
  authority artifacts and external systems.
- **Traceability:** RF-06–RF-08; CA-06–CA-08; RP-09/RP-10 and `rest-layer-rules.md`.
- **Outcome/exits:** map the exact response contract; Orchestrator reruns Web static/unit/
  build gates and authenticated persisted live flow, checks question detail and protected/
  released disclosures, then recaptures affected result screenshots. No dedicated REST
  service test is added because the selected test Rule assigns observable behavior to the
  consuming Page/browser boundary.

#### Scoped Builder Fix — ACH-07 completed result HTTP contract

- **Status/owner:** `complete` — Builder Server (`/root/learning_activity_server_builder`)
- **Spec:** revision 3; in-contract correction, no Spec or product behavior change.
- **Finding:** isolated full-stack submission persisted three answers and three result
  parts, and the evaluation completed, but the live Result Page rendered zero question
  details. ACH-06 Web mapping is corrected; verify whether the API response actually
  includes those details before choosing a layer correction.
- **Allowed paths:** `apps/server/tests/learning/server/controllers/test_get_choice_attempt_controller.py`;
  conditionally `apps/server/src/shifu/learning/rest/controllers/get_choice_attempt_controller.py`,
  `apps/server/src/shifu/learning/core/use_cases/get_choice_attempt_use_case.py`,
  `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py`,
  `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_evaluation_mapper.py`.
- **Prohibited paths:** every other path, Web, generated metadata, SDD/design/authority
  files and external systems.
- **Traceability:** RF-06–RF-08; CA-06–CA-08; RP-09/RP-10 and Server Rules in F2-T1.
- **Outcome/exits:** verify completed GET attempt status/body with details and disclosure;
  add real controller integration regression coverage; correct only a confirmed server
  defect. Orchestrator reruns affected server gates and live authenticated result flow.

#### Scoped Builder Fix — ACH-08 compact score display

- **Status/owner:** `complete` — Builder Web (`/root/learning_activity_web_builder`) and Orchestrator integrated verification
- **Spec:** revision 3; in-contract visual correction, no score calculation or API change.
- **Finding:** live persisted score values contain decimal scale from PostgreSQL and render
  trailing zeroes (`100.00`); saved result designs show compact values such as `70 / 100`.
- **Allowed paths:** `apps/web/src/ui/learning/widgets/pages/choice-result-page/index.tsx`,
  `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx`,
  and their colocated test files only.
- **Prohibited paths:** Server, REST mapping, domain scoring, route/generated metadata,
  other Web paths, SDD/design/authority artifacts and external systems.
- **Traceability:** RF-06; CA-04/CA-06; saved complete-result and outcome-detail design
  references; Widget Testing Rule.
- **Outcome/exits:** format displayed values without altering exact domain values; assert
  integer and fractional display behavior at page/detail boundaries. Builder focused
  tests, scoped Biome and typecheck passed; Orchestrator reran the Web gates and full
  Playwright suite and recaptured result states, including authenticated persisted
  desktop/mobile plus five-question mobile scroll evidence (EV-24–EV-30).

#### Scoped Builder Fix — ACH-09 shared navigation wrapper compliance

- **Status/owner:** `complete` — Builder Web (`/root/learning_activity_web_builder`)
- **Spec:** revision 3; in-contract correction, no Spec or product behavior change.
- **Finding:** the Activity and attempt route wrappers call TanStack `useNavigate`
  directly and hardcode `/login`, bypassing the shared `useNavigation` abstraction
  required by `ui-layer-rules.md`.
- **Allowed paths:** `apps/web/src/ui/shared/hooks/use-navigation.ts`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx`;
  `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/index.tsx`;
  and only existing route test files needed to verify the wrapper behavior.
- **Prohibited paths:** Server, unrelated Web paths, generated route metadata, SDD/design/
  authority files and external systems.
- **Traceability:** RF-01–RF-03, RF-05–RF-08; CA-01–CA-03, CA-05–CA-08, CA-10, CA-12;
  `ui-layer-rules.md` imperative-navigation and `ROUTES` requirements.
- **Outcome/exits:** both routes use the shared wrapper for dynamic Activity/attempt
  navigation and login redirection. Existing route suites pass; Orchestrator reran Web
  lint, architecture, types, unit, integration, build and `git diff --check` (EV-32).

#### Scoped Builder Fix — ACH-10 outer page container width

- **Status/owner:** `complete` — Builder Web (`/root/learning_activity_web_builder`)
- **Spec:** revision 3; visual-only correction, no product behavior change.
- **Finding:** user-directed layout convention requires outer Activity and result page
  containers to use Tailwind `max-w-7xl`.
- **Allowed paths:** `apps/web/src/ui/learning/widgets/pages/choice-activity-page/index.tsx`;
  `apps/web/src/ui/learning/widgets/pages/choice-result-page/index.tsx`.
- **Prohibited paths:** Server, unrelated Web paths, generated route metadata, all
  SDD/design/authority files and external systems.
- **Traceability:** RF-02, RF-06, RF-10; CA-02, CA-06, CA-10; affected VIS-01–VIS-12
  and VM-01–VM-04/VM-06 page captures.
- **Outcome/exits:** all 10 outer page branches use `max-w-7xl`; focused Page suites,
  scoped Biome and Web typecheck pass. Representative live desktop/mobile Activity and
  pending/completed result captures are inspected in EV-34. Exact-state captures for
  other VIS rows remain stale and are part of the open F3 exit.

# Validation and handoff

## Evidence coverage

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Server use-case suite: five Activity/attempt actions | CA-01, CA-03–CA-09, CA-11–CA-12 | Spec Validation Contract; F1-T1 | `evaluation.md` focused server unit evidence | `complete` |
| Automated | Real HTTP/PostgreSQL controller suite: four routes | CA-01, CA-03, CA-05–CA-09, CA-11–CA-12 | Spec Validation Contract; F2-T1 | `evaluation.md` HTTP, auth, serialized body and persisted side effects | `complete` |
| Automated | Registered Learning Inngest job with disposable Testcontainers | CA-04, CA-05, CA-09, CA-12 | Spec Validation Contract; F2-T1 | `evaluation.md` run trace, current run/effect and outbox evidence | `complete` |
| Automated | Web widget/hook suites | CA-02, CA-05–CA-08, CA-10 | Spec Validation Contract; F1-T2 | `evaluation.md` interaction and accessibility evidence | `complete` |
| Automated | Activity parent route suite: auth, outlet and nested navigation | CA-01, CA-12 | `activities.$activityId.route.test.tsx`; F2-T2 | `evaluation.md` redirect, URL and child-render assertions | `complete` |
| Automated | Activity index route suite: question, submit and recovery | CA-01–CA-03, CA-10–CA-11 | `activities.$activityId.index.test.tsx`; F2-T2 | `evaluation.md` URL, visible state and request assertions | `complete` |
| Automated | Attempt index route suite: pending, failure/retry and result | CA-05–CA-08, CA-10, CA-12 | `activities.$activityId.attempts.$attemptId.index.test.tsx`; F2-T2 | `evaluation.md` URL, rendered states and request assertions | `complete` |
| Automated | Module-owned Activity Page suite through actual route composition | CA-01–CA-03, CA-10–CA-11 | `apps/web/tests/learning/choice-activity-page.test.ts`; F2-T2 | `evaluation.md` Page URL, interaction, request and visible outcome assertions | `complete` |
| Automated | Module-owned result Page suite through actual attempt route composition | CA-05–CA-08, CA-10, CA-12 | `apps/web/tests/learning/choice-result-page.test.ts`; F2-T2 | `evaluation.md` Page URL, status, retry, disclosure and return assertions | `complete` |
| Automated | Web gates: `pnpm --filter web check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, `build` | CA-01–CA-03, CA-05–CA-08, CA-10–CA-12 | CI-01–CI-06 | `evaluation.md` command outputs and route-tree diff | `complete` |
| Automated | Server gates: `uv run poe check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, `test:jobs`, `build` from `apps/server` | CA-01, CA-03–CA-09, CA-11–CA-12 | CI-07–CI-13 | `evaluation.md` command outputs and runtime boundary results | `complete` |
| Manual/migration | VM-07 — legacy row preflight, upgrade, downgrade/re-upgrade and data preservation on disposable PostgreSQL | CA-03, CA-05, CA-09 | Spec VM-07; CI-14–CI-15 | `evaluation.md` counts, SQL/index checks, migration output and row comparison | `complete` |
| Manual/runtime | VM-01 — desktop owner flow, sequential answer and idempotent submit, 1440 × 900 | CA-01–CA-03, CA-10 | Spec VM-01; `o2q7H.png`, `Cj8R7.png` | `evaluation.md` URL/HTTP/DB evidence and fresh screenshots | `complete` |
| Manual/runtime | VM-02 — mobile selection and unsent leave warning, 390 × 844 | CA-02, CA-10 | Spec VM-02; `rf857.png` | `evaluation.md` focus, target/overflow measurements and fresh screenshots | `open — stale; exact-state recapture required` |
| Manual/runtime | VM-03 — desktop pending, completed result, disclosure and progress, 1440 × 900 | CA-04–CA-08, CA-10, CA-12 | Spec VM-03; `PCnZO.png`, `YDgNz.png`, `gftrs.png`, `ad7p6.png`, `ntBNV.png` | `evaluation.md` response/DOM/job/progress evidence and fresh state screenshots | `complete` |
| Manual/runtime | VM-04 — mobile full three/five-question result, 390 × 844 | CA-06, CA-10 | Spec VM-04; `k3bUS8.png` | `evaluation.md` scrolling/overflow/keyboard evidence and fresh screenshots | `complete` |
| Manual/runtime | VM-05 — anonymous/other-account/private absence and legacy content eligibility, 1440 × 900 | CA-01, CA-08, CA-11 | Spec VM-05; Activity question references | `evaluation.md` access matrix, safe response and eligibility evidence | `complete` |
| Manual/runtime | VM-06 — fail/retry, stale pending, duplicate/late event and deleted Skill, 1440 × 900 | CA-03, CA-05, CA-09, CA-12 | Spec VM-06; handoff adjacent state references | `evaluation.md` disposable DB/Inngest trace and fresh pending/failure/recovery screenshots | `open — stale; exact-state recapture required` |
| Visual | Desktop question 2 of 3, single choice, 1440 × 900 | CA-01, CA-02 | `design/o2q7H.png`; VM-01 | Fresh Playwright screenshot + comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Desktop question 1 of 3, multiple selection, 1440 × 900 | CA-01, CA-02 | `design/Cj8R7.png`; VM-01 | Fresh Playwright screenshot + comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Desktop incorrect single-choice detail with protected answer, 1440 × 900 | CA-06, CA-07 | `design/YDgNz.png`; VM-03 | Fresh Playwright screenshot + disclosure comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Desktop correct single-choice detail, 1440 × 900 | CA-06, CA-08 | `design/gftrs.png`; VM-03 | Fresh Playwright screenshot + comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Desktop incorrect multiple-selection detail, 1440 × 900 | CA-06, CA-07 | `design/ad7p6.png`; VM-03 | Fresh Playwright screenshot + disclosure comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Desktop correct multiple-selection detail, 1440 × 900 | CA-06, CA-08 | `design/ntBNV.png`; VM-03 | Fresh Playwright screenshot + comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Complete desktop three-question result, 1440 × 900 | CA-05–CA-08 | `design/PCnZO.png`; VM-03 | Fresh Playwright screenshot + full-page/scroll comparison in Evaluation | `complete` |
| Visual | Mobile multiple-selection question, 390 × 844 | CA-01, CA-02, CA-10 | `design/rf857.png`; VM-02 | Fresh Playwright screenshot + target/overflow comparison in Evaluation | `open — stale; exact-state recapture required` |
| Visual | Complete mobile three-question result, 390 × 844 | CA-05–CA-10 | `design/k3bUS8.png`; VM-04 | Fresh Playwright screenshot + long-result comparison in Evaluation | `complete` |
| Visual | Desktop pending evaluation state, 1440 × 900 | CA-05, CA-10, CA-12 | Handoff adjacent pending state; VM-03/VM-06 | Fresh Playwright screenshot and announced status evidence | `complete` |
| Visual | Desktop failed evaluation with retry action, 1440 × 900 | CA-05, CA-10 | Handoff adjacent failure state; VM-06 | Fresh Playwright screenshot, focus and retry evidence | `open — stale; exact-state recapture required` |
| Visual | Desktop recovered evaluation after retry, 1440 × 900 | CA-05, CA-09, CA-10 | Handoff adjacent recovery state; VM-06 | Fresh Playwright screenshot and same-attempt/new-run evidence | `open — stale; exact-state recapture required` |
| REST client | Learning `/activities` route group: Activity GET, attempts POST, attempt GET, retry POST | CA-01, CA-03, CA-05–CA-07, CA-12 | `apps/server/rest-client/learning/activities.rest` | Four labeled current requests, reusable non-secret vars, no credentials; parity recorded in Evaluation | `complete` |
| Review | One read-only Implementation Reviewer over integrated candidate and all evidence | CA-01–CA-12; all RF/VM/CI | `documentation/agents/implementation-reviewer-agent.md` | Initial pass EV-31; resumed passes EV-33/EV-36 confirm code findings resolved; stale visual rows remain open | `complete` |
## Final handoff condition

Route to `conclude-spec` only when every task/phase is complete; current Spec revision and
the integrated diff are reconciled; CI-01–CI-15 pass; generated route metadata,
migration and REST-client examples are reviewed; each CA/VM and each listed visual
state has current accepted evidence; all four REST examples are route-complete; the
single Implementation Reviewer has completed and verified findings are resolved;
required services/accounts/fixtures are available or their limits are recorded; and
Evaluation is ready. Do not infer evidence from Builder reports or mocked transports.
