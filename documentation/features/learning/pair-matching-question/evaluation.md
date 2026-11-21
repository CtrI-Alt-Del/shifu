---
title: Learning Activity word-translation pair matching questions evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-21
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for server and web code. Open: the real authenticated browser journey (VM-01) and the Penpot comparisons (VM-02, VM-03) |
| Automated checks | 10/10 passed on the final candidate (EV-18, EV-19) |
| Type / lint / complexity | Server types 0 errors, Ruff 0 errors including C90 complexity, format clean (EV-18). Web types 0 errors, Biome clean on the feature paths, `depcruise` clean on Node 24 (EV-18). Quantitative complexity metrics: Blocked, no tool configured (EV-12). The 2 Biome warnings of the whole web app are old Intelligence files this change does not touch |
| Manual checks | 0/1. VM-01 Blocked: the journey needs a signed-in session (JWT from the web's Better Auth) whose account owns the seeded Learning data. There is no saved login state, and the seed belongs to a fixed seed account in the shared development database, which this task may not seed or reset. EV-19 runs the pair flow in a real browser with the Start server functions stubbed, which does not replace VM-01 |
| Visual checks | 0/2. Blocked: the Penpot boards do not exist and the Penpot MCP was not connected (Q1 = B) |
| Independent review | Current for the code: one Implementation Reviewer pass (ACH-07 to ACH-16) and the review comments on PR 58 (ACH-17 to ACH-26), all corrected or recorded. The independent Spec review was waived by the user's order to implement |
| Blockers | VM-01: no authenticated identity for an isolated database. VM-02, VM-03: Penpot boards missing |
| Candidate | Branch `feat/shifu-124`, evaluated at `5e90d4fb`. It contains the SHIFU-122 and SHIFU-123 work through the merge `fdb0cba0` of `origin/main` at `fbc7cd30`. The commit that records this Evaluation follows it |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 / EV-01 | None |
| CA-02 | RF-01, RF-09 | Complete | Passed | CI-01 / CI-02 / EV-01, EV-02 | None |
| CA-03 | RF-01, RF-06 | Complete | Partial | CI-02 / EV-02 passed; VM-01 not run | VM-01 |
| CA-04 | RF-02 | Complete | Partial | CI-08 / EV-08 and the browser run EV-19 passed; VM-01 not run | VM-01 |
| CA-05 | RF-02 | Complete | Partial | CI-08 / EV-08 and EV-19 passed; VM-01 not run | VM-01 |
| CA-06 | RF-03, RF-06 | Complete | Passed | CI-03 / CI-04 / EV-03, EV-04 | None |
| CA-07 | RF-03 | Complete | Partial | CI-08 / EV-08 and EV-19 passed; VM-01 not run | VM-01 |
| CA-08 | RF-03, RF-04 | Complete | Passed | CI-03 / CI-05 / EV-03, EV-05 | None |
| CA-09 | RF-04 | Complete | Passed | CI-05 / EV-05 | None |
| CA-10 | RF-04, RF-05 | Complete | Passed | CI-06 / CI-07 / EV-06, EV-07 | None |
| CA-11 | RF-05 | Complete | Passed | CI-06 / EV-06: pair with translation and pair with code, at the use-case and workflow boundaries | None |
| CA-12 | RF-05 | Complete | Passed | CI-06 / EV-06 | None |
| CA-13 | RF-06 | Complete | Partial | CI-09 / EV-09 passed; VM-03 Blocked | VM-03 |
| CA-14 | RF-07 | Complete | Passed | CI-07 / EV-07 duplicate run, EV-20 failed evaluation then retry, EV-06 review attempt | None |
| CA-15 | RF-08 | Complete | Partial | Component and hook tests assert names, announcements, focus and text states (EV-08); EV-19 drives it by keyboard on desktop and mobile; VM-01, VM-02 not run | VM-01, VM-02 |
| CA-16 | RF-06, RF-09 | Complete | Partial | CI-03 passed (no AI field, no key); VM-02, VM-03 Blocked | VM-02, VM-03 |

# Check Results

Server commands run from `apps/server` with `AWS_PROFILE` unset, because the configured profile does not exist in this environment. Web commands run from `apps/web`. Rows EV-01 to EV-16 were first run on the working tree before the merge, on 2026-11-19 and 2026-11-20. The merged and final candidates re-ran their selections in EV-17 and EV-18, and those rows are the current proof. Controller tests own disposable PostgreSQL data, and the already-running local PostgreSQL and Redis containers were used for them.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-02 | Passed | Pre-merge tree, in-process | `uv run pytest tests/curriculum/core/domain/test_pair_matching_question.py` | 32 passed. 2 and 8 pairs accepted, 1 and 9 rejected, repeated keys and texts, key defects, identity-aligned order, empty explanations, repeated Concepts, score bounds, absent scores, diagnostic rejection. Test data comes from `PairMatchingQuestionFaker` |
| EV-02 | CI-02 / Automated / CA-02, CA-03 | Passed | Pre-merge tree, real app and disposable PostgreSQL | `uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | The response matches the exact public shape and has no key or explanation text. A seed test asserts the seeded item keys are opaque (ACH-07) |
| EV-03 | CI-03 / Automated / CA-06, CA-08, CA-16 | Passed | Pre-merge tree | `uv run pytest tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py` | Every permutation of 2 and 3 pairs, five 8-pair cases, invalid classes, stale revision, no writes, seven invalid-snapshot cases. Invalid shape returns 422 and pairs that do not fit return 400. Grades are rounded half up to two decimals (33.33, 66.67) |
| EV-04 | CI-04 / Automated / CA-06 | Passed | Pre-merge tree | Same files as EV-03 | The response field set is asserted exactly and has no key. Limit: the Spec's 2 to 4 pair enumeration is covered for 3 pairs |
| EV-05 | CI-05 / Automated / CA-08, CA-09 | Passed | Pre-merge tree, real app and PostgreSQL | `uv run pytest tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | One attempt, one evaluation, one outbox event, no Concept rows. Identical replay 200, the same pairs in another order replay the same attempt, conflicting replay 409, invalid pairs 422 or 400, stale revision 409. The outbox destination is `inngest` |
| EV-06 | CI-06 / Automated / CA-10, CA-11, CA-12, CA-14 | Passed | Pre-merge tree | `uv run pytest tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/ai/workflows` | Grades, mixed with choice, translation and code (assessor called only for the AI question), Concept scores for each outcome and each absent score, invalid saved answer, repeated run once, and a review attempt after completion that updates no progress and records no Concept evidence. The workflow case seeds a pair question through `seed_translation_activity_attempt(pair_matching=True)` |
| EV-07 | CI-07 / Automated / CA-10, CA-14 | Passed | Pre-merge tree, real Inngest Testcontainers | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | The pair-only Activity routed to `inngest`, completed once, the duplicate event changed nothing, no AI request was sent. Re-run in EV-18. The failure then retry proof is EV-20 |
| EV-08 | CI-08 / Automated / CA-04, CA-05, CA-07, CA-15 | Passed | Pre-merge tree, jsdom | `pnpm exec vitest run src/ui/learning src/core/learning src/rest` | Re-run in EV-18 with the review changes. Hook, widget, page hook, page route and feedback tests cover selection, replace, remove with focus, Escape, ordered pairs, pt-BR language labels, read-only after verify and retry after failure |
| EV-09 | CI-09 / Automated / CA-13 | Passed | Pre-merge tree, real app and PostgreSQL | `uv run pytest tests/learning/server/controllers/test_get_choice_attempt_controller.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py`; `pnpm exec vitest run src/ui/learning/widgets/pages/choice-result-page` | The key stays hidden until the current answer is full, a later attempt is full, or the Competency is mastered. A later partial attempt does not release it. The web result widget and its hook have their own tests |
| EV-10 | CI-10 / Server static gates | Passed | Pre-merge tree | `uv run poe check:types`; `uv run ruff check --no-fix src tests`; `uv run ruff format --check src tests`; `uv run poe check:architecture` | Superseded by EV-18 |
| EV-11 | CI-10 / Web types and lint | Passed | Pre-merge tree | `pnpm check:types`; `pnpm exec biome check` on the feature paths | Superseded by EV-18 |
| EV-12 | CI-10 / Complexity metrics | Blocked | n/a | n/a | No quantitative complexity tool is configured. Configured complexity lint passed (EV-18) and does not replace it |
| EV-13 | CI-10 / Web architecture | Passed | Node 24.20.0 | `PATH=~/.nvm/versions/node/v24.20.0/bin:$PATH pnpm check:architecture` | Re-run in EV-18. Node 25.2.1, the default here, is rejected by `depcruise` |
| EV-14 | VM-01 / Manual / CA-03 to CA-07, CA-15 | Blocked | n/a | n/a | Not run. See Current State. The behaviors are proven at the real-app, real-PostgreSQL, jsdom and stubbed-browser boundaries (EV-02, EV-03, EV-05, EV-08, EV-09, EV-19), which do not replace the required real journey |
| EV-15 | VM-02 / Visual / CA-03, CA-04, CA-06, CA-15, CA-16 | Blocked | n/a | n/a | The Penpot boards do not exist and the MCP was not connected |
| EV-16 | VM-03 / Visual / CA-13, CA-16 | Blocked | n/a | n/a | Same as EV-15 |
| EV-17 | CI-01 to CI-10 / Merged candidate | Passed | `fdb0cba0`, 2026-11-20 | The EV-18 commands | After merging the SHIFU-123 fill-in-the-blank work: server regression 1045 passed and 5 failed in a field-set assertion that was corrected (117 passed in that file afterwards); job file 6 passed; static gates clean; web 618 passed. Conflicts were resolved by keeping both formats and reapplying the pair changes on the refactored use cases |
| EV-18 | CI-01 to CI-10 / Final candidate | Passed | `5e90d4fb`, 2026-11-21 | `uv run pytest tests/curriculum tests/learning tests/shared`; `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`; `uv run poe check:types`; `uv run ruff check --no-fix src tests`; `uv run ruff format --check src tests`; `uv run poe check:architecture`; from `apps/web`: `pnpm exec vitest run src/ui/learning src/core/learning src/rest`, `pnpm check:types`, `pnpm exec biome check src tests`, and `pnpm check:architecture` on Node 24 | Server regression 1051 passed (the 46 warnings are third-party deprecations from before this change); job file 6 passed; types 0 errors; Ruff, format and tach clean. Web 632 passed in 65 files; types clean; Biome reports 2 warnings in Intelligence files this change does not touch; `depcruise` found no violations |
| EV-19 | CI-08 / Automated browser / CA-04, CA-05, CA-07, CA-15 | Passed | `5e90d4fb`, 2026-11-21, disposable PostgreSQL (migrated to Alembic head with the AgentOS runtime role) and Redis on spare ports, removed afterwards; Start server functions stubbed | `pnpm exec playwright test tests/learning/activity-page.test.ts` from `apps/web`, with the disposable `DATABASE_URL`, `AGENTOS_DATABASE_URL`, `REDIS_URL`, the placeholder `SHIFU_COMMUNICATION_ENCRYPTION_KEYS` from the repository test support, the three `AI_QUOTA_*` example values and `AWS_PROFILE` unset | 20 passed, including the new pair test on desktop and mobile: keyboard pairing, replacement, Verify disabled until complete, partial result with text, read-only after verify, Next question, final submit. The test asserts the browser-to-server payload carries `pair_matching`, the revision and the verified pair keys. Limit: the mapping in the web REST service to the Python API body is not observed here, because the server functions are stubbed. The shared development database and Redis were not used |
| EV-20 | CI-07 / Automated / CA-14 | Passed | `5e90d4fb`, 2026-11-21, real app and PostgreSQL | `uv run pytest tests/learning/rest/controllers/test_retry_choice_evaluation_controller.py` | A pair attempt whose evaluation failed is retried with a new run and one outbox event. The evaluation then completes once, the saved pairs are unchanged, the attempt count grows by one and there is one evaluated event. A repeated run is a no-op |
| EV-21 | Source verification | Passed | 2026-11-21, Atlassian Shifu MCP | `fetch` of the Learning PRD page 83066881 compared line by line with the version 33 text read on 2026-11-19 | Version 34 adds one appended addendum, "Aditivo aprovado em 2026-11-20 — SHIFU-98" (server-side deletion within 24 hours and offline drafts). The pair-matching rules in RP-09, RP-13, RP-14, RP-18, RP-20, RP-25 and RP-27 are unchanged, so the Spec is valid against version 34. Curriculum PRD version 19 was not reread |

Earlier failed attempts, kept: the first run of the preview controller tests failed 4 cases because domain validation returns 400, not 422 (Spec clarified in revision 2); the first job run failed on destination routing timing and a score rounding assertion (test fixed); the first release-history controller test failed because the application clock is fixed (test corrected); the first merged server regression failed 5 cases in a field-set assertion (EV-17); the first Playwright runs failed to start the server because of unset settings and an unavailable AWS profile (environment, not product).

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Ruff C901 complexity in four use-case methods after adding the pair branches | Medium | CI-10 | Resolved: extracted helper methods without `noqa` |
| ACH-02 | The preview response would have carried an empty `submitted_pairs` for choice questions, breaking an exact-shape test | Medium | CI-03 | Resolved: the pair fields are optional and absent for other kinds |
| ACH-03 | The Spec said an absent Concept score gives no observation, but the choice format records an inconclusive observation | Low | CA-12 | Resolved: Spec revision 2 and tests |
| ACH-04 | The seed Activity exists in source only and was not applied | Low | VM-01 | Open |
| ACH-05 | No independent code review had been run | Medium | all | Resolved on 2026-11-20 |
| ACH-06 | The workflow-file and review-attempt pair cases were missing | Low | CI-06 | Resolved (EV-06) |
| ACH-07 | Seed item keys followed the pairing index, so the answer key leaked through the responses (blocking) | High | CI-02 | Resolved: seed keys are hashes of the item text; a seed test asserts it |
| ACH-08 | The widget test ran the real hook | Medium | CI-08 | Resolved: the component test mocks the hook |
| ACH-09 | No page-level test of the pair route and none for the feedback component | Medium | CA-04 to CA-07, CA-15 | Resolved |
| ACH-10 | The Shared snapshot checked less than the Curriculum rules and had no test | Medium | CA-02 | Resolved |
| ACH-11 | Removing a pair dropped keyboard focus | Medium | CA-15 | Resolved: focus moves to the word button; the hook test asserts it |
| ACH-12 | Two structures shared one file | Low | Rules | Resolved |
| ACH-13 | The preview count is an oracle for the key | Low | CA-06 | Accepted: RP-18 requires the count; recorded in the Spec |
| ACH-14 | A replay with the same pairs in another order returned 409 | Low | CA-09 | Resolved: pairs are stored sorted by word key |
| ACH-15 | Duplicate state announcement and an `undefined` text fallback | Low | CA-15 | Resolved |
| ACH-16 | No test mixed a pair question with a code question | Medium | CA-11 | Resolved |
| ACH-17 | Pair test data was hand built in five places (review comment on `pair_matching_fixture.py`) | Medium | Rules | Resolved: `PairMatchingQuestionFaker` (Curriculum) and `CurriculumPairMatchingQuestionSnapshotFaker` (Shared) with overridable arguments; the old fixture is deleted and every copy uses a faker |
| ACH-18 | Interaction logic lived in the widget `index.tsx`: refs, pair order, Escape, focus on remove (review comment) | Medium | UI Rules, CA-15 | Resolved: all of it moved into `usePairMatchingQuestion`, covered by hook tests |
| ACH-19 | The items were native buttons with their own CSS (review comment) | Low | UI Rules | Resolved: the shadcn `Button` with `data-*` state; the CSS keeps only the selected and paired colors |
| ACH-20 | The pair result card sat inside `ChoiceResultDetail` with local helpers, and the text lookup and outcome line were repeated (review comment) | Medium | UI Rules | Resolved: `pair-matching-result/` widget with its own hook; one shared outcome hook and one text helper serve the feedback and the result |
| ACH-21 | The item languages were shown as raw codes such as `en-US` (review comment) | Medium | CA-15, UI Rules | Resolved: `languageLabel` gives pt-BR names, authored names stay as they are, and the translation question uses it too; Spec revision 4 |
| ACH-22 | The REST examples mixed the pair and fill-in-the-blank requests and had invalid JSON (review comment) | Medium | Rules | Resolved: the file is main's plus four complete pair examples (GET, preview, submit, result); every body parses as JSON |
| ACH-23 | The pair grade was not rounded, for example 33.33333333333333333333333333 (review comment) | Medium | CA-06, CA-10 | Resolved: half up to two decimals like fill-in-the-blank; Spec revision 4; tests assert 33.33 and 66.67 |
| ACH-24 | This Evaluation was stale about commits, revision, review, PR and PRD version (review comment) | Medium | Process | Resolved: rewritten from Git and the PR; the PRD reread is EV-21 |
| ACH-25 | CA-14 was Passed without a pair failure then retry proof (review comment) | Medium | CA-14, CI-07 | Resolved: EV-20 adds the retry test; the Spec's CI-07 now names its proofs |
| ACH-26 | No web test of the pair request and result mapping (review comment) | Medium | CA-04 to CA-07 | Partly resolved: EV-19 asserts the browser-to-server payload. The web REST service mapping itself is not covered by a transport test, which the UI rules assign to consumer and route tests, and the server controller tests assert the exact response shape. Risk recorded |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Item keys that follow the order of the pairing leak the answer key even when the key field is private; derive opaque keys | ACH-07 | Spec revision 3 records the authoring rule; a seed test enforces it |
| Test files end with module-level helpers, so appending methods at the end of a file can attach them to the wrong scope | The first preview controller pair tests were not collected | No change warranted |
| A response model that excludes only `None` values makes new default-empty fields visible to unrelated question kinds | ACH-02 | No change warranted |
| When a format is added next to a sibling that was merged meanwhile, merge `main` early and rebuild the shared use cases from its version instead of stitching hunks | The SHIFU-123 conflicts in 29 files | No change warranted |
| Valid domain objects in tests belong in fakers from the first test, not in per-file builders | ACH-17 | No change warranted |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-124` at `5e90d4fb` plus the commit that records this Evaluation; PR 58 is open against `main` |
| Completed | All server and web code; every CA verified at its automated boundary (EV-18 to EV-20); the independent review and the PR review comments corrected; the PRD reread |
| Unfinished | VM-01 manual journey, VM-02 and VM-03 visual checks |
| Uncommitted work | None |
| Active processes | None. The disposable PostgreSQL and Redis used by EV-19 were removed |
| Blockers | No authenticated identity for an isolated database; Penpot boards missing |
| Next action | Wait for the CI on the current head of PR 58, answer the review conversations, and run VM-01 and the visual checks when an authenticated isolated environment and the Penpot boards exist |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03, RP-04; Learning RP-09, RP-13, RP-18, RP-25, RP-27 | RF-01 to RF-09 / CA-01 to CA-16 | EV-01 to EV-11, EV-17 to EV-19 | partially_implemented: automated and stubbed-browser proof is accepted; the real journey and the visual comparisons are outstanding |
| Learning RP-14, RP-20 | RF-07 / CA-14 | EV-06, EV-07, EV-20 | implemented: duplicate run, failed evaluation then retry and the review attempt are each proven for pair questions |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| [CtrI-Alt-Del/shifu#58](https://github.com/CtrI-Alt-Del/shifu/pull/58) | `5e90d4fb` plus the Evaluation commit | SonarQube Cloud quality gates passed for Shifu Web and Shifu API on the earlier head; CI for the current head and the ten review conversations are pending | Review by JohnPetros, 2026-11-20 |

| Field | Result |
| --- | --- |
| Publication | Published: PR 58 is open against `main` |
| Source verification | Learning PRD 83066881: version 33 at authoring, version 34 reread on 2026-11-21 (EV-21). Curriculum PRD 83034113 version 19 at authoring, not reread |
| Documentation Alignment | No external writes. The Penpot boards remain a dependency |
| Revision History | Spec revision 4: grade rounding, pt-BR language names, result widget, fakers, retry proof and the PRD version 34 reconciliation |
| Limitations | Spec review waived by the user; VM-01, VM-02 and VM-03 not run; the Spec status stays `ready`, not `implemented`, until they are |
