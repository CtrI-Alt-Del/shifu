---
title: Questão HTML, CSS e JavaScript em Atividades de aprendizagem evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-24
---

# Current State

| Field | State |
| --- | --- |
| Implementation | CA-01–CA-10 implemented; nested preview entrypoint correction and REST examples integrated |
| Automated checks | CI-01–CI-08 passed on the integrated working tree; current-head CI pending publication |
| Type / lint / complexity | Web and Server type, lint, architecture and build gates passed; dedicated quantitative complexity tooling unavailable |
| Manual checks | VM-01 blocked; login stays at `/login` and no local HTML Activity is available to prove the real journey |
| Visual checks | VM-02 blocked; Activity screenshots and exported desktop references are unavailable |
| Independent review | Spec review passed and user approved Spec revision 1; implementation review corrections integrated; final evidence refresh pending |
| Blockers | VM-01 authenticated scenario and VM-02 capture/reference evidence unavailable in current local environment |
| Candidate | `feat/server/SHIFU-86-html-css-js`, based on `1488c9437c81016f328fcdff0397b427bbb92f0d`; feature changes uncommitted at this evaluation revision |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Implemented | Passed | CI-01 | 316 integrated Server tests passed, including Curriculum, mixed activity and legacy snapshot paths |
| CA-02 | RF-01 | Implemented | Passed | CI-01 | Project validation and editable-file normalization covered in the same 316-test Server selection |
| CA-03 | RF-02, RF-05 | Implemented | Automated passed; manual blocked | CI-02, VM-01 | Final integrated Web selection passed 66 tests; the 10-test HTML widget/hook selection also passed after the runner entrypoint correction. Real authenticated journey unavailable. |
| CA-04 | RF-02 | Implemented | Automated passed; manual blocked | CI-03, VM-01 | Draft, cross-tab and consumer regression tests passed. Real account/session recovery not observed in browser. |
| CA-05 | RF-02, RF-04 | Implemented | Passed | CI-03 | Tombstone invalidation and frozen-response tests passed in the focused Web selection. |
| CA-06 | RF-03 | Implemented | Passed | CI-04 | Server preview/use-case/controller and Web feedback selections passed. |
| CA-07 | RF-03, RF-04 | Implemented | Passed | CI-05 | Immutable submission, retry and workflow selections passed in the integrated Server run. |
| CA-08 | RF-04 | Implemented | Automated passed; manual blocked | CI-06, VM-01 | Historical read-only Web/Server tests passed; browser persistence and recovery journey unavailable. |
| CA-09 | RF-03, RF-04 | Implemented | Passed | CI-07 | Privacy, invalidation and delayed-work workflow/use-case tests passed in the integrated Server selection. |
| CA-10 | RF-05 | Implemented | Blocked | VM-02 | Keyboard interaction tests passed. Desktop/mobile captures, overflow inspection and Pencil comparison are unavailable. |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01–02 | Passed | Integrated working tree on `feat/server/SHIFU-86-html-css-js`, 2026-10-24; disposable Testcontainers | Combined focused pytest selection in `apps/server`; exact command recorded below | **316 passed**, 11 deprecation/collection warnings, 142.22s. Includes HTML domain, Curriculum, mixed activity, snapshots and legacy question types. |
| EV-02 | CI-02 / Automated / CA-03 | Passed | Integrated working tree, 2026-10-24; local Vitest/jsdom | HTML widget/hook tests in `apps/web` after nested-entrypoint correction | **10 passed** in 2 files. Includes the actual WebContainer runner resolving a nested curricular entrypoint to the isolated preview URL. |
| EV-03 | CI-03 / Automated / CA-04–05 | Passed | Integrated working tree, 2026-10-24; local Vitest/jsdom | Focused HTML/draft/activity Web selection in `apps/web` | Final integrated selection: **66 passed** in 5 files. The focused 10-test runner/widget selection also passed. Builder reported **63 shared-consumer tests passed** in 9 files. |
| EV-04 | CI-04 / Automated / CA-06 | Passed | Integrated working tree, 2026-10-24; disposable Testcontainers and local Vitest | Server preview/use-case/controller and Web feedback tests in the combined selections | Covered by the 316 Server passes and 65 Web passes. |
| EV-05 | CI-05 / Automated / CA-07 | Passed | Integrated working tree, 2026-10-24; disposable Testcontainers | Submission, evaluation and in-process workflow tests in the combined `apps/server` selection | Covered by the 316 Server passes. Retry after evaluator failure emitted the expected warning and passed. |
| EV-06 | CI-06 / Automated / CA-08 | Passed | Integrated working tree, 2026-10-24; disposable Testcontainers and local Vitest | Attempt/history Server and read-only result Web tests in the combined selections | Covered by the 316 Server passes and 65 Web passes. |
| EV-07 | CI-07 / Automated / CA-09 | Passed | Integrated working tree, 2026-10-24; disposable Testcontainers | Evaluation workflow and submit/evaluate use-case tests in the combined `apps/server` selection | Covered by the 316 Server passes; no registered AgentOS runtime suite exists per supplied context. |
| EV-08 | CI-08 / Automated / types, lint, complexity, architecture and build | Passed with stated limit | Integrated working tree, 2026-10-24; local toolchain | Web TypeScript, Biome on changed files, Dependency Cruiser and Vite build; Server basedpyright, Ruff check/format, Tach, compileall and `uv build` | All configured gates passed. Dedicated quantitative complexity metrics are unavailable and remain unmeasured. Corepack/pnpm could not resolve pnpm because registry DNS failed; installed local binaries ran the declared checks. Server build passed after granting local cache/Docker access. |
| EV-09 | VM-01 / Manual / CA-03–09 | Blocked | Local Web at `http://127.0.0.1:7000`; API health `http://127.0.0.1:7777/health` returned 200; 2026-10-24 | Playwright CLI opened `/login`, submitted the documented seed account, and inspected page, requests and console | Sign-in POST returned 200 but the page stayed at `/login`; no authenticated Activity was reached. No database seed/reset was run. Preview, draft-recovery, submission and persisted-result browser behavior remain unobserved. |
| EV-10 | VM-02 / Visual / CA-10 | Blocked | Candidate working tree; 2026-10-24 | Visual Reviewer inspected the handoff and available Playwright evidence | Activity captures at 1440×900 and 390×844 are absent. Handoff names Pencil references Veyl9/EzCt3 but provides no exported image paths. Visual Reviewer returned BLOCKED; only a `/login` snapshot is available. |
| EV-11 | Baseline regression / Automated / existing React and Activity consumers | Passed | Feature branch, 2026-10-23; local Web dependencies | `apps/web/node_modules/.bin/vitest.cmd run` with five Activity/React/result test files from `apps/web`; `TEMP` and `TMP` used an ignored task-local directory | 80 tests passed in 5 files. `pnpm` could not resolve its package-manager version because registry DNS was unavailable; direct installed Vitest binary was used. |
| EV-12 | Baseline regression / Automated / existing Curriculum and Learning consumers | Passed | Feature branch, 2026-10-23; local Server venv and disposable Testcontainers | `.venv/Scripts/python.exe -m pytest -q` with `test_react_question.py` and six named Learning use-case files from `apps/server`, with Docker access | 240 tests passed with 1 warning in 13.56s. An earlier unelevated attempt failed during fixture setup because Docker named-pipe access was denied; rerun with local Docker access passed. |
| EV-13 | VM-01 readiness / Manual / CA-03–09 | Blocked | Local environment, 2026-10-24 | `docker compose ps`; HTTP health requests; Web startup; Playwright login | PostgreSQL, Inngest and Mailpit were already running; API health returned 200 and task-started Web served `/login`. The documented seed login did not establish an authenticated browser route. Shared Compose services and the pre-existing API process were left running. Task-started Web process is stopped before handoff. |

Integrated Server selection, run from `apps/server` with Docker access for
disposable Testcontainers (EV-01, EV-04–EV-07):

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/curriculum/core/domain/test_html_css_js_question.py tests/curriculum/core/domain/test_react_question.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py tests/learning/rest/controllers/test_get_choice_activity_controller.py tests/learning/rest/controllers/test_get_choice_attempt_controller.py tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/rest/controllers/test_preview_activity_question_feedback_controller.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_prepare_code_activity_evaluation_use_case.py tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/rest/controllers/test_submit_choice_activity_controller.py tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py
```

Integrated Web selection (EV-02–EV-03), run from `apps/web` with `TEMP` and
`TMP` pointed at the ignored `.playwright-cli/logs/shifu-86-tmp-20261023-01`:

```powershell
.\node_modules\.bin\vitest.cmd run src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/html-css-js-question.test.tsx src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/use-html-css-js-question.test.ts src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts
```

The post-review runner correction was verified from `apps/web` with the two HTML
widget/hook test paths from EV-02. The 9-file shared-consumer command and its
63-test result were run by the Web Builder before the Orchestrator integrated
candidate; no product code in those consumers changed afterward.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Preview omitted nested curricular `entrypoint`; Implementation Reviewer finding, CA-03 | Medium | CI-02, VM-01 | Corrected URL resolution and added a regression test; 10 focused Web tests passed, then Web type/lint/architecture/build gates passed. |
| ACH-02 | REST examples omitted the `html_css_js` response/request contract; Implementation Reviewer finding, CA-01/06/07 | Low | REST contract review | Added the discriminator/detail documentation plus preliminary-evaluation and mixed-submission examples to `apps/server/rest-client/learning/activities.rest`. |
| ACH-03 | Browser login stayed at `/login`; EV-09/EV-13 | Blocking for manual evidence | VM-01 | Auth POST returned 200, API health returned 200, but an authenticated Activity was not reached. No seed/reset or shared database mutation was performed. |
| ACH-04 | Activity screenshots and exported Pencil desktop references are unavailable; EV-10 | Blocking for visual evidence | VM-02 | Visual Reviewer returned BLOCKED. Smallest next action is to supply the references and an authenticated local HTML Activity, then capture the two required viewports. |

# Lessons Learned

None.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/server/SHIFU-86-html-css-js`, based on `1488c9437c81016f328fcdff0397b427bbb92f0d`; feature changes still uncommitted |
| Completed | CA-01–CA-09 implementation and automated proof; CA-10 UI/keyboard implementation and automated checks; all configured local static/build gates; Spec revision 1 approved; implementation-review corrections integrated |
| Unfinished | VM-01 real authenticated Activity journey; VM-02 captures/reference comparison; current-head CI after PR publication; final implementation-review evidence refresh |
| Uncommitted work | User-provided root task documents remain untracked; pre-existing deletion of `SHIFU-88-IMPLEMENTACAO.md` preserved |
| Active processes | Shared Docker Compose services PostgreSQL, Inngest and Mailpit were already running and remain untouched; pre-existing API process not managed by this task; task-started Web must be stopped before handoff |
| Blockers | Local login remained at `/login`, with no HTML Activity available for the manual journey; Pencil references have no exported image paths; `gh auth status` reports invalid GitHub token although git push credentials work |
| Next action | Finish reviewer evidence update, commit the implementation and separately authorized deletion, push the branch, and create/attach the PR through the connected GitHub integration |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03/JN-03 | RF-01, CA-01–02 | EV-01, EV-08 | Implemented and locally verified; current-head CI pending |
| Learning RP-09, RP-11–14, RP-18, RP-21–22, RP-25, RP-29 | RF-01–05, CA-01–10 | EV-01–EV-08; EV-09/EV-10 blocked | Implementation and automated checks pass. Real browser journey and visual acceptance remain unverified in this local environment. |

| Field | Result |
| --- | --- |
| Publication | Branch published; PR not yet created |
| Source verification | Learning content 83066881 v26 and Curriculum content 83034113 v13 per supplied context document; no Jira/Confluence refresh requested |
| Documentation Alignment | Spec and Evaluation created; no external writes |
| Revision History | Spec revision 1 |
| Limitations | Local automated checks pass; VM-01/VM-02 remain blocked as recorded. Quantitative complexity metrics have no configured tool. GitHub CLI token is invalid; use the connected GitHub integration for PR creation. Current-head CI remains pending until publication. |
