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
| Manual checks | VM-01 partially passed in an authenticated disposable-database journey; final Activity submission was rate-limited and its result page was not reached |
| Visual checks | VM-02 captures exist at required desktop/mobile viewports; desktop Pencil references are unavailable, so visual comparison remains blocked |
| Independent review | Spec review passed and user approved Spec revision 1; implementation review verified the fixture guardrail and local-draft description; visual review found the mobile CTA/FAB collision, with source spacing corrected and a post-fix capture still pending |
| Blockers | Official submission/result-page confirmation and Pencil reference comparison remain unavailable |
| Candidate | `feat/server/SHIFU-86-html-css-js`; implementation commit `0d8fd36`, based on `1488c9437c81016f328fcdff0397b427bbb92f0d` |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Implemented | Passed | CI-01 | 316 integrated Server tests passed, including Curriculum, mixed activity and legacy snapshot paths |
| CA-02 | RF-01 | Implemented | Passed | CI-01 | Project validation and editable-file normalization covered in the same 316-test Server selection |
| CA-03 | RF-02, RF-05 | Implemented | Automated passed; manual partial | CI-02, VM-01 | Final integrated Web selection passed 66 tests; the 10-test HTML widget/hook selection also passed after the runner entrypoint correction. Authenticated Activity and question navigation observed. WebContainer preview remained unavailable in headless Chromium. |
| CA-04 | RF-02 | Implemented | Automated passed; manual passed | CI-03, VM-01 | Draft, cross-tab and consumer regression tests passed. Browser logout/login restored edited HTML and JavaScript from the browser-local draft. |
| CA-05 | RF-02, RF-04 | Implemented | Passed | CI-03 | Tombstone invalidation and frozen-response tests passed in the focused Web selection. |
| CA-06 | RF-03 | Implemented | Passed | CI-04 | Server preview/use-case/controller and Web feedback selections passed. |
| CA-07 | RF-03, RF-04 | Implemented | Automated passed; manual partial | CI-05, VM-01 | Immutable submission, retry and workflow selections passed in the integrated Server run. Browser reached final submission UI, but API rate limiting prevented confirmation. |
| CA-08 | RF-04 | Implemented | Automated passed; manual partial | CI-06, VM-01 | Historical read-only Web/Server tests passed; browser proved draft recovery, but no persisted official result was reached. |
| CA-09 | RF-03, RF-04 | Implemented | Passed | CI-07 | Privacy, invalidation and delayed-work workflow/use-case tests passed in the integrated Server selection. |
| CA-10 | RF-05 | Implemented | Manual partial | VM-02 | Keyboard interaction tests passed. Screenshots at 1440×900 and 390×844 exposed a mobile FAB/CTA overlap; the HTML assessment button now reserves 4rem on the right below `lg`. Mobile document width matched the viewport. Fresh post-fix capture and Pencil comparison remain unavailable. |

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
| EV-09 | VM-01 / Manual / CA-03–09 | Partial | Local Web `http://localhost:7001`, API `http://localhost:7778`, disposable PostgreSQL `127.0.0.1:15448` and Redis `127.0.0.1:16379`; 2026-10-24 | Playwright CLI signed in with the documented seed account; opened the mixed Activity; evaluated choice and HTML responses; edited all three files; logged out/in; inspected restored draft; captured final desktop/mobile views; attempted final submit | Activity GET, choice preliminary, HTML preliminary (75%), and third choice preliminary returned 200. Draft recovery restored edited HTML/JS from browser-local storage after reauthentication. No browser or console errors were recorded in the successful run. WebContainer preview stayed unavailable despite cross-origin isolation and SharedArrayBuffer support. Final submission returned 429 from the API limiter, so persisted official result is unverified. Screenshots: `apps/web/.playwright-cli/screenshots/shifu-86-desktop.png` and `apps/web/.playwright-cli/screenshots/shifu-86-mobile.png`. |
| EV-10 | VM-02 / Visual / CA-10 | Partial | Candidate working tree; 2026-10-24 | Captured authenticated Activity at desktop and mobile viewports; measured document width at mobile; reviewed overlap and added mobile CTA spacing | Screenshots exist at 1440×900 and 390×844; mobile document/body width was 390px, with no horizontal overflow. Mobile capture showed the Mentor FAB touching the assessment button; the button now reserves 4rem at right below `lg`, and the 10 focused HTML widget/hook tests pass. A post-fix browser capture is still needed. Pencil references Veyl9/EzCt3 have no exported image paths, so visual comparison cannot be completed. |
| EV-11 | Baseline regression / Automated / existing React and Activity consumers | Passed | Feature branch, 2026-10-23; local Web dependencies | `apps/web/node_modules/.bin/vitest.cmd run` with five Activity/React/result test files from `apps/web`; `TEMP` and `TMP` used an ignored task-local directory | 80 tests passed in 5 files. `pnpm` could not resolve its package-manager version because registry DNS was unavailable; direct installed Vitest binary was used. |
| EV-12 | Baseline regression / Automated / existing Curriculum and Learning consumers | Passed | Feature branch, 2026-10-23; local Server venv and disposable Testcontainers | `.venv/Scripts/python.exe -m pytest -q` with `test_react_question.py` and six named Learning use-case files from `apps/server`, with Docker access | 240 tests passed with 1 warning in 13.56s. An earlier unelevated attempt failed during fixture setup because Docker named-pipe access was denied; rerun with local Docker access passed. |
| EV-13 | VM-01 readiness / Manual / CA-03–09 | Partial | Disposable local environment, 2026-10-24 | Guarded fixture prepared an isolated PostgreSQL database; isolated Redis, API, decision stub and Web served the authenticated Playwright journey | Authenticated Activity and preliminary evaluation worked. A later retry after restarting the API had an issuer/JWKS configuration mismatch; this did not invalidate the earlier successful journey. Task-started disposable services are stopped before handoff; shared Compose services remain untouched. |

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
| ACH-03 | Final official browser submission returned 429; EV-09/EV-13 | Blocking for final manual evidence | VM-01 | Authenticated Activity, preliminary evaluation and draft recovery passed in the disposable fixture. The official result page was not reached after API throttling. |
| ACH-04 | Pencil references Veyl9/EzCt3 are not exported; EV-10 | Blocking for visual comparison | VM-02 | Desktop/mobile Activity screenshots and overflow measurement now exist. The mobile FAB/CTA overlap was corrected in source, but a post-fix capture and reference comparison need fresh authenticated access and exported images. |

# Lessons Learned

None.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/server/SHIFU-86-html-css-js`; implementation commit `0d8fd36`, based on `1488c9437c81016f328fcdff0397b427bbb92f0d` |
| Completed | CA-01–CA-09 implementation and automated proof; CA-10 UI/keyboard implementation and automated checks; all configured local static/build gates; Spec revision 1 approved; implementation-review corrections integrated and checked |
| Unfinished | Confirm official submission/result in browser; compare screenshots to exported Pencil references; current-head CI |
| Uncommitted work | `apps/server/devtools/html_css_js_browser_fixture/{README.md,activity.py,prepare.py}`, the HTML question mobile spacing in `apps/web/src/ui/learning/widgets/pages/activity-page/html-css-js-question/index.tsx`, and this Evaluation update will be committed. The two user-provided root task documents remain untracked and excluded. |
| Active processes | Shared Docker Compose services PostgreSQL, Inngest and Mailpit were already running and remain untouched; pre-existing API process not managed by this task; task-started Web was stopped after browser validation |
| Blockers | Official browser submit returned 429 before producing a result page; Pencil references have no exported image paths; `gh auth status` reports invalid GitHub token although git push credentials work |
| Next action | Review current-head CI on PR #44; repeat only the final submit after the rate-limit window, and compare captures if references are exported |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03/JN-03 | RF-01, CA-01–02 | EV-01, EV-08 | Implemented and locally verified; current-head CI pending |
| Learning RP-09, RP-11–14, RP-18, RP-21–22, RP-25, RP-29 | RF-01–05, CA-01–10 | EV-01–EV-10 | Implementation and automated checks pass. Browser verified sign-in, editing, autosave/recovery and preliminary evaluation. Final submission confirmation and visual reference comparison remain unverified. |

| Field | Result |
| --- | --- |
| Publication | Branch published; PR #44 opened and attached: https://github.com/CtrI-Alt-Del/shifu/pull/44 |
| Source verification | Learning content 83066881 v26 and Curriculum content 83034113 v13 per supplied context document; no Jira/Confluence refresh requested |
| Documentation Alignment | Spec and Evaluation created; no external writes |
| Revision History | Spec revision 1 |
| Limitations | Local automated checks pass; VM-01/VM-02 are partial as recorded. The headless browser could not start the WebContainer preview; official submit was rate-limited. Quantitative complexity metrics have no configured tool. GitHub CLI token is invalid; branch push and PR creation succeeded through configured integrations. Current-head CI is pending. |
