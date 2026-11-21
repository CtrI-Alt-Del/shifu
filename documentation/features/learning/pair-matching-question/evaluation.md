---
title: Learning Activity word-translation pair matching questions evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-20
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for server and web code. Open: seed applied nowhere, no browser journey run |
| Automated checks | 10/10 passed; CI-10 has two Blocked gates (metrics tooling, Node version) |
| Type / lint / complexity | Server types 0 errors, Ruff 0 errors including C90 complexity, format clean (EV-10). Web types 0 errors, Biome clean on the feature paths (EV-11). Quantitative complexity metrics: Blocked, no tool configured. Web architecture gate (`depcruise`): Blocked, Node 25.2.1 unsupported |
| Manual checks | 0/1. VM-01 not run: the API and web were not running and the journey needs the new seed Activity in a database; applying the seed to the shared database is not authorized |
| Visual checks | 0/2. Blocked: the Penpot boards do not exist and the Penpot MCP was not connected (Q1 = B) |
| Independent review | Pending. The Implementation Reviewer was not launched in this session. The independent Spec review was waived by the user's order to implement |
| Blockers | VM-01: shared database seeding not authorized. VM-02, VM-03: Penpot boards missing. Web architecture gate: unsupported Node version |
| Candidate | Branch `feat/shifu-124` from `feat/shifu-122` at `def50ee1`; all work uncommitted |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 / EV-01 | None |
| CA-02 | RF-01, RF-09 | Complete | Passed | CI-01 / CI-02 / EV-01, EV-02 | None |
| CA-03 | RF-01, RF-06 | Complete | Partial | CI-02 / EV-02 passed; VM-01 not run | VM-01 |
| CA-04 | RF-02 | Complete | Partial | CI-08 / EV-08 passed; VM-01 not run | VM-01 |
| CA-05 | RF-02 | Complete | Partial | CI-08 / EV-08 passed; VM-01 not run | VM-01 |
| CA-06 | RF-03, RF-06 | Complete | Passed | CI-03 / CI-04 / EV-03, EV-04 | None |
| CA-07 | RF-03 | Complete | Partial | CI-08 / EV-08 passed; VM-01 not run | VM-01 |
| CA-08 | RF-03, RF-04 | Complete | Passed | CI-03 / CI-05 / EV-03, EV-05 | None |
| CA-09 | RF-04 | Complete | Passed | CI-05 / EV-05 | None |
| CA-10 | RF-04, RF-05 | Complete | Passed | CI-06 / CI-07 / EV-06, EV-07 | None |
| CA-11 | RF-05 | Complete | Passed | CI-06 / EV-06: pair plus translation proven at the use-case and workflow boundaries | None |
| CA-12 | RF-05 | Complete | Passed | CI-06 / EV-06 | None |
| CA-13 | RF-06 | Complete | Partial | CI-09 / EV-09 passed; VM-03 Blocked | VM-03 |
| CA-14 | RF-07 | Complete | Passed | CI-07 / EV-07 duplicate run; EV-06 review attempt after completion changes no progress or evidence | None |
| CA-15 | RF-08 | Complete | Partial | Component tests assert names, announcements and text states (EV-08); VM-01, VM-02 not run | VM-01, VM-02 |
| CA-16 | RF-06, RF-09 | Complete | Partial | CI-03 passed (no AI field, no key); VM-02, VM-03 Blocked | VM-02, VM-03 |

# Check Results

Candidate for all rows: `feat/shifu-124` working tree, 2026-11-19. Server commands run from `apps/server` with `AWS_PROFILE` unset, because the configured profile does not exist in this environment. Web commands run from `apps/web`. PostgreSQL and Redis were the already-running local containers, and each controller test owns its disposable data.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-02 | Passed | Working tree, in-process | `uv run pytest tests/curriculum/core/domain/test_pair_matching_question.py` | 32 passed. Covers 2 and 8 pairs, 1 and 9 rejected, repeated keys and texts, key defects, identity-aligned order, empty explanations, repeated Concepts, score bounds, absent scores, diagnostic rejection |
| EV-02 | CI-02 / Automated / CA-02, CA-03 | Passed | Working tree, real app and disposable PostgreSQL | `uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | Pair cases included and green. The response matches the exact public shape and contains no key or explanation text |
| EV-03 | CI-03 / Automated / CA-06, CA-08, CA-16 | Passed | Working tree | `uv run pytest tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py` | 92 and 22 tests passed. Every permutation of 2 and 3 pairs, five 8-pair cases, invalid classes, stale revision, no writes. Invalid shape returns 422 and pairs that do not fit return 400 |
| EV-04 | CI-04 / Automated / CA-06 | Passed | Working tree | Same files as EV-03 | The response field set is asserted exactly and has no key. Limit: the Spec's 2 to 4 pair enumeration is covered for 3 pairs |
| EV-05 | CI-05 / Automated / CA-08, CA-09 | Passed | Working tree, real app and PostgreSQL | `uv run pytest tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | 115 use-case tests and the controller file passed. One attempt, one evaluation, one outbox event, no Concept rows. Identical replay 200, conflicting replay 409, invalid pairs 422 or 400, stale revision 409. The outbox destination is `inngest` |
| EV-06 | CI-06 / Automated / CA-10, CA-11, CA-12, CA-14 | Passed | Working tree, 2026-11-20 | `uv run pytest tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/ai/workflows` | 89 and 13 passed. Grades, mixed with choice and with translation (assessor called for translation only), Concept scores for full, partial, incorrect and each absent score, invalid saved answer, repeated run once, and a REVIEW attempt after completion that updates no progress and records no Concept evidence. The new workflow case seeds a pair question next to the translation question through `seed_translation_activity_attempt(pair_matching=True)` and shows one assessor call |
| EV-07 | CI-07 / Automated / CA-10, CA-14 | Passed | Working tree, real Inngest Testcontainers | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | 5 passed, including the new pair job test run on the final refactored code. The pair-only Activity routed to `inngest`, completed once, the duplicate event changed nothing, no AI request was sent. Limit: no pair-specific injected-failure job case; the failure path is shared with choice and covered by the existing job tests |
| EV-08 | CI-08 / Automated / CA-04, CA-05, CA-07, CA-15 | Passed | Working tree, jsdom | `pnpm exec vitest run src/ui/learning src/core/learning src/rest` | 565 passed in 60 files. New: hook 8 tests, widget 6, page hook 4. Covers word-then-translation, translation first, replace, remove, Escape, disabled, complete wrong set, incomplete set, repeated or unknown keys, read-only after verify, retry after failure |
| EV-09 | CI-09 / Automated / CA-13 | Passed | Working tree, real app and PostgreSQL | `uv run pytest tests/learning/server/controllers/test_get_choice_attempt_controller.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py`; `pnpm exec vitest run src/ui/learning/widgets/pages/choice-result-page` | Outcomes full, partial, incorrect. The key stays hidden until the current answer is full, a later attempt is full, or the Competency is mastered, and a later partial attempt does not release it. Web detail renders label, counts, pairs and the released key |
| EV-10 | CI-10 / Server types, lint, format, architecture / all | Passed | Working tree | `uv run poe check:types`; `uv run ruff check --no-fix src tests`; `uv run ruff format --check src tests`; `uv run poe check:architecture` | 0 errors and 0 warnings; Ruff passes including C90 after extracting helpers; 1602 files formatted; tach validated. Regression on the final candidate: `uv run pytest tests/curriculum tests/learning tests/shared` gave 921 passed. The 39 warnings are third-party deprecations that existed before this change |
| EV-11 | CI-10 / Web types and lint | Passed | Working tree | `pnpm check:types`; `pnpm exec biome check src/core/learning src/rest/services src/ui/learning` | 0 type errors; Biome clean on the feature paths. The repository-wide `pnpm check:lint` reports 11 existing warnings only in Intelligence files that this change does not touch |
| EV-12 | CI-10 / Complexity metrics | Blocked | n/a | n/a | No quantitative complexity tool is configured. Configured complexity lint passed (EV-10, EV-11) and does not replace it |
| EV-13 | CI-10 / Web architecture | Blocked | Node 25.2.1 | `pnpm check:architecture` | `depcruise` rejects Node 25. Needs Node 22, 24 or 26+ |
| EV-14 | VM-01 / Manual / CA-03 to CA-07, CA-15 | Pending | n/a | n/a | Not run. See Current State |
| EV-15 | VM-02 / Visual / CA-03, CA-04, CA-06, CA-15, CA-16 | Blocked | n/a | n/a | The Penpot boards do not exist and the MCP was not connected |
| EV-16 | VM-03 / Visual / CA-13, CA-16 | Blocked | n/a | n/a | Same as EV-15 |

Earlier failed attempts, kept: an unfixed first run of the preview controller tests failed 4 cases because domain validation returns 400, not 422 (Spec clarified in revision 2); the first job run failed on destination routing timing and a score rounding assertion (test fixed); the first release-history controller test failed because the application clock is fixed (test corrected).

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Ruff C901 complexity in four use-case methods after adding the pair branches | Medium | CI-10 / EV-10 | Resolved: extracted helper methods without `noqa`; Ruff, types and 921 tests green |
| ACH-02 | The preview response would have carried an empty `submitted_pairs` for choice questions, breaking an exact-shape test | Medium | CI-03 / EV-03 | Resolved: the pair fields are optional and absent for other kinds |
| ACH-03 | Spec said an absent Concept score gives no observation, but the choice format records an inconclusive observation | Low | CA-12 / EV-06 | Resolved: Spec revision 2 aligns to choice semantics and tests assert it |
| ACH-04 | The seed Activity exists in source only. It was not applied or exercised | Low | VM-01 | Open |
| ACH-05 | No independent code review was run | Medium | all | Open |
| ACH-06 | The workflow-file and review-attempt pair cases were missing | Low | CI-06 | Resolved on 2026-11-20 (EV-06) |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Test files in this repository end with module-level helper functions. Appending methods at the end of a file can attach them to the wrong scope, so insert before the first module-level function | The first preview controller pair tests were not collected | No change warranted |
| A response model that excludes only `None` values makes new default-empty fields visible to unrelated question kinds | ACH-02 | No change warranted |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-124` from `feat/shifu-122` at `def50ee1`, nothing committed |
| Completed | All server and web code; CA-01, CA-02, CA-06, CA-08, CA-09, CA-10, CA-12 verified; the other criteria verified at the automated boundary |
| Unfinished | VM-01 manual journey, VM-02 and VM-03 visual checks, independent Implementation Reviewer, web architecture gate on a supported Node |
| Uncommitted work | All feature files under `apps/server`, `apps/web` and this directory. The Spec is at revision 2 |
| Active processes | None. All background test runs ended |
| Blockers | Shared database seeding is not authorized; Penpot boards missing; Node version for `depcruise` |
| Next action | Run VM-01 against an isolated database seeded with `SEED_ACTIVITY_PAIR_MATCHING_ID`, launch the Implementation Reviewer, then rerun `pnpm check:architecture` on a supported Node |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03, RP-04; Learning RP-09, RP-13, RP-18, RP-25, RP-27 | RF-01 to RF-09 / CA-01 to CA-16 | EV-01 to EV-11 | partially_implemented: automated proof is accepted; manual, visual and independent review are outstanding |
| Learning RP-14, RP-20 | RF-07 / CA-14 | EV-07 | partially_implemented: duplicate and failure paths proven; review attempt proven only through the shared unchanged branch |

| Field | Result |
| --- | --- |
| Publication | Not requested; no PR |
| Source verification | Learning PRD 83066881 v33 and Curriculum PRD 83034113 v19, retrieved 2026-11-19; recheck before conclusion |
| Documentation Alignment | No external writes. The Penpot boards remain a dependency |
| Revision History | Revision 2: absent Concept score is inconclusive; 400 for pairs that do not fit the question |
| Limitations | Spec review waived by the user; manual and visual checks not run; no independent review; the Spec status stays `ready`, not `implemented` |
