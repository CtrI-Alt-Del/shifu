---
title: Learning Activity fill-in-the-blank questions evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-17
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01..CA-17, CA-19, CA-20. CA-18 (visual) not started: blocked on Penpot |
| Automated checks | 16/17 passed. CI-16 Failed (pre-existing, outside this delivery) |
| Type / lint / complexity | Passed for the affected scope: CI-13 (EV-13), CI-14 (EV-14), CI-15 (EV-15; configured lint only, no metrics tool) |
| Manual checks | 0/2. VM-01 and VM-02 Blocked: API cannot start locally and `db:seed` is not authorized |
| Visual checks | 0/4. VM-03..VM-06 Blocked: Penpot MCP not connected |
| Independent review | Implementation Reviewer: PASS, low findings only (ACH-05..ACH-12). Visual Reviewer not applicable until captures exist |
| Blockers | Penpot MCP (VM-03..06); local API startup and `db:seed` authorization (VM-01, VM-02); pre-existing test-integrity failure (CI-16) |
| Candidate | `feat/shifu-123` on `main` 9b606f4b, uncommitted working tree (see Handoff) |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 / EV-01 | none |
| CA-02 | RF-01, RF-02 | Complete | Passed | CI-01 / EV-01 | none |
| CA-03 | RF-02, RF-03, RF-13 | Complete | Passed | CI-02, CI-03, CI-07 / EV-02, EV-03, EV-07 | none |
| CA-04 | RF-04, RF-05 | Complete | Passed | CI-09 / EV-09; CI-12 keyboard and mouse drag / EV-12 | touch drag only in VM-02 (Blocked) |
| CA-05 | RF-05 | Complete | Partial | CI-09 / EV-09; VM-03..06 Blocked | visual comparison |
| CA-06 | RF-06, RF-08, RF-09 | Complete | Passed | CI-10 / EV-10 | none |
| CA-07 | RF-07, RF-08 | Complete | Passed | CI-02 / EV-02 | none |
| CA-08 | RF-06, RF-13 | Complete | Passed | CI-02, CI-04 / EV-02, EV-04 | none |
| CA-09 | RF-06, RF-09 | Complete | Passed | CI-03, CI-05 / EV-03, EV-05 | none |
| CA-10 | RF-07, RF-10 | Complete | Passed | CI-02 / EV-02 | none |
| CA-11 | RF-10, RF-11 | Complete | Passed | CI-02, CI-08 / EV-02, EV-08 | none |
| CA-12 | RF-11 | Complete | Passed | CI-02 / EV-02 | none |
| CA-13 | RF-09, RF-10, RF-11 | Complete | Passed | CI-08 / EV-08 | none |
| CA-14 | RF-12 | Complete | Passed | CI-02, CI-06 / EV-02, EV-06 | none |
| CA-15 | RF-12 | Complete | Passed | CI-02 / EV-02 | none |
| CA-16 | RF-08, RF-12, RF-05 | Complete | Passed | CI-10, CI-11, CI-12 / EV-10, EV-11, EV-12 | none |
| CA-17 | RF-03..RF-12, RF-14 | Complete | Blocked | VM-01, VM-02 Blocked; CI-12 covers browser composition only | real-service journeys |
| CA-18 | RF-05 | Pending | Blocked | VM-03..VM-06 | Penpot MCP |
| CA-19 | RF-01, RF-03 | Complete | Passed | CI-07 / EV-07 | none |
| CA-20 | RF-02 | Complete | Passed | CI-17 / EV-17 | none |

# Check Results

Candidate for every row: working tree on `feat/shifu-123`, 2026-11-17. Server commands run from `apps/server` with `env -u AWS_PROFILE` (the shell's `AWS_PROFILE` names a profile that does not exist and breaks the test bootstrap) and `-p no:tach`. Web commands run from the repository root. PostgreSQL and Redis come from disposable Testcontainers.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-02 | Passed | unit, no infrastructure | `uv run pytest tests/curriculum/core/domain/test_fill_blanks_question.py` | 45 passed |
| EV-02 | CI-02 / Automated / CA-07, 08, 10, 11, 12, 14, 15 | Passed | autospecced ports | `uv run pytest tests/learning/core/use_cases/test_{preview_activity_question_feedback,submit_choice_activity,evaluate_choice_activity,get_choice_activity,get_choice_attempt,retry_choice_evaluation}_use_case.py` | 87 + 117 + 82 + 24 + 16 + 6 passed (existing and new). Core selection `tests/curriculum/core tests/learning/core`: 596 passed |
| EV-03 | CI-03 / Automated / CA-03, CA-09 | Passed | same files as EV-02 | covered by the EV-02 command | fill-blanks projection and normalization scenarios ran |
| EV-04 | CI-04 / Automated / CA-07, CA-08 | Passed | real app, Testcontainers | `uv run pytest tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py` | 22 passed (11 new). Invalid fill is HTTP 400, body shape is 422 |
| EV-05 | CI-05 / Automated / CA-09 | Passed | real app, Testcontainers | `uv run pytest tests/learning/server/controllers/test_submit_choice_activity_controller.py` | 25 passed (new: persistence, replay 200, conflict 409, shapes, stale and pending) |
| EV-06 | CI-06 / Automated / CA-14 | Passed | real app, evaluation use case, advancing clock | `uv run pytest tests/learning/server/controllers/test_get_choice_attempt_controller.py` | 10 passed (disclosure hidden, released after a later correct attempt, 404 for another goal) |
| EV-07 | CI-07 / Automated / CA-03, CA-19 | Passed | real app | `uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py -k fill_blanks` | 3 passed. The negative search covers hidden field names and explanation texts |
| EV-08 | CI-08 / Automated / CA-11, CA-13 | Passed | real Inngest runtime and disposable PostgreSQL | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | 5 passed, none skipped. Destination `inngest`, completion once, duplicate delivery wrote nothing |
| EV-09 | CI-09 / Automated / CA-04, CA-05 | Passed | Vitest | `pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/fill-blanks-question/tests` | 21 passed (12 hook, 9 component) |
| EV-10 | CI-10 / Automated / CA-06, CA-16 | Passed | Vitest | `pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page` | 19 files, 304 passed |
| EV-11 | CI-11 / Automated / CA-16 | Passed | Vitest | `pnpm --filter web exec vitest run src/ui/learning/widgets/pages/choice-result-page` | 4 files, 41 passed |
| EV-12 | CI-12 / Automated / CA-04, CA-16, CA-17 | Passed with limitation | Playwright against a health-only stub on port 7777; server functions mocked | `pnpm exec playwright test tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts -g "fill-in-the-blank\|drops a bank word"` from `apps/web` | 4 Activity scenarios (desktop and mobile keyboard journeys, narrow-screen sizes, mouse drop) and 4 result scenarios passed. Limit: the real API was not running, so this proves browser composition only |
| EV-13 | CI-13 / Types | Passed | | `uv run poe check:types` (0 errors, 0 warnings); `pnpm --filter web check:types` (exit 0) | affected projects and consumers |
| EV-14 | CI-14 / Lint and format | Passed | | `uv run ruff check --no-fix <65 changed paths>` and `ruff format --check`; `pnpm exec biome check <29 changed paths>` | zero diagnostics after correcting 7 Ruff and 8 Biome findings |
| EV-15 | CI-15 / Complexity | Passed (configured lint) | | the EV-14 commands | `C901` raised three times and fixed by extraction, with no new suppression. No metrics tool is configured, so no score exists |
| EV-16 | CI-16 / Architecture, build, integrity | Failed (pre-existing) | | `uv run poe check:architecture`, `uv run poe build`, `pnpm --filter web build` passed; `pnpm exec depcruise ...` passed under Node 24 (732 modules; the default Node 25 is unsupported by the tool); `pnpm check:test-integrity` **failed** | Only violation: `apps/server/tests/curriculum/database/test_roadmap_skills_seed.py`, from another delivery. Every file added or changed here is allowed. Not reported as a pass |
| EV-17 | CI-17 / Automated / CA-20 | Passed | real app | `uv run pytest tests/learning/server/controllers/test_submit_diagnostic_batch_controller.py` | 2 passed. The valid-batch success path is covered by the legacy consumer file below |
| EV-18 | Consumer regression / seed and shared unions | Passed | disposable PostgreSQL | `uv run pytest tests/learning/server/controllers tests/learning/rest/controllers tests/intelligence/server/controllers/test_confirm_planning_controller.py tests/intelligence/preparation/test_prepare_planning_indexes.py tests/curriculum` | 359 passed in 6m39s. Run before the later refactors, then the affected files were rerun |
| EV-19 | VM-01 / Manual / CA-17 | Blocked | | real desktop journey | The API fails at startup (`AGENTOS_DATABASE_URL is required`) and the seeded English experience needs `db:seed`, which resets shared local data and is not authorized |
| EV-20 | VM-02 / Manual / CA-17 | Blocked | | real mobile journey incl. touch drag | same cause as EV-19 |
| EV-21 | VM-03..VM-06 / Visual / CA-18 | Blocked | | fresh Penpot export vs Playwright capture | Penpot MCP not connected in this session. No visual pass is claimed |

Warnings observed in the test runs, all pre-existing and outside the delivery: `PytestAssertRewriteWarning` for a plugin imported early, Starlette `DeprecationWarning`s, and a `PytestCollectionWarning` for the `Test`-prefixed structure `TestCasesEvaluationPart`. The suites report no new warning from the changed code.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Spec said an invalid fill returns 422. The existing error handler maps the domain `ValidationError` to 400. Found while writing CI-04 | Medium | CI-04, CI-05 | Resolved: Spec revision 2 and the tests state 400 (invalid fill) and 422 (body shape) |
| ACH-02 | Accessible name of a filled blank lost its space before the period in Chrome | Low | CI-09, CI-12 | Resolved: browser locators tolerate it; unit tests assert the exact name |
| ACH-03 | `pnpm add` re-resolved unrelated TanStack Devtools packages in the lockfile | Low | CI-16 | Resolved: lockfile restored and only the three `@dnd-kit` entries added (37 lines); `pnpm install --frozen-lockfile` passes |
| ACH-05 | Reviewer: current-attempt disclosure releases the expected words when that attempt is fully correct (choice precedent) while RF-12 said "later" | Low | CI-06 | Resolved: RF-12 reworded to match |
| ACH-06 | Reviewer: blanks not required in segment order; disclosed list would follow `blanks` order | Low | CI-01 | Resolved: Curriculum question and snapshot now require segment order; new CI-01 case |
| ACH-07 | Reviewer: `ROUND_HALF_UP` tie untested; singular count text untested; `PlacementRequest` limits missing on submit; leftover `satisfies` | Low | CI-02, CI-11 | Resolved: 32-blank tie test (3.13), singular-text test, `Field(min_length, max_length)`, leftover removed; affected tests and gates rerun (EV-02 88 passed, web 545 passed, types 0 errors) |
| ACH-08 | Reviewer: the feedback region is mounted with its text, so some screen readers may not announce the outcome; dnd-kit drop announcement says "Palavra solta." even outside a target | Low | CI-09, VM-01 | Open: improve with the always-mounted output and verify with assistive technology in VM-01 |
| ACH-09 | Reviewer: touch drag with `touch-action: manipulation` and a 200 ms delay is unverified against page scroll | Low | VM-02 | Open: blocked with VM-02 |
| ACH-10 | Reviewer: `fill_answer: object` plus a `type: ignore` in an evaluate test; new `mixed_question_snapshots.py` and prop names not listed in the Spec tree | Low | CI-13 | Open: cosmetic, to fold into the next Spec revision |
| ACH-04 | `pnpm check:test-integrity` fails on `test_roadmap_skills_seed.py` | Medium | CI-16 | Open, pre-existing and outside scope: needs a separate maintenance fix or the user's explicit acceptance |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| A Spec naming an HTTP status for a domain error must be checked against `AppErrorHandler` | ACH-01 | No change: the REST Rule already says the handler maps errors |
| `pnpm add` can rewrite unrelated lockfile entries with this pnpm version | ACH-03 | Pending proposal: none; handled locally |
| Playwright's accessible-name computation inserts spaces between inline-flex items that Testing Library does not | ACH-02 | No change: feature-specific |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-123` at `9b606f4b`, uncommitted. Nothing is staged or committed |
| Completed | Server, API, persistence, job routing, seed, web widgets and all automated checks above |
| Unfinished | VM-01, VM-02, VM-03..VM-06, the independent review disposition, and the CI-16 pre-existing failure |
| Uncommitted work | `apps/server/src/shifu/{curriculum,shared,learning,fakers}`, `apps/server/tests`, `apps/server/rest-client/learning/activities.rest`, `apps/web/src`, `apps/web/tests/learning`, `apps/web/package.json`, `pnpm-lock.yaml`, this feature folder. Other stashes in the repository belong to the user and were left untouched |
| Active processes | none (the health-only stub on port 7777 was stopped) |
| Blockers | Penpot MCP; `AGENTOS_DATABASE_URL` and `db:seed` authorization; ACH-04 |
| Next action | Reconcile the reviewer report, then ask the user to connect Penpot and to authorize the seed so VM-01..VM-06 can run |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03, RP-04; JN-03, JN-04 | RF-01, RF-02, RF-03 / CA-01..CA-03, CA-19 | EV-01, EV-02, EV-03, EV-07 | implemented |
| Learning RP-09, RP-13, RP-14, RP-15, RP-18, RP-20, RP-27; JN-07, JN-08, JN-13 | RF-04..RF-13 / CA-04..CA-16, CA-20 | EV-02, EV-04..EV-12, EV-17, EV-18 | implemented for automated proof; real-service journeys not run |
| Learning RP-25 | RF-05 / CA-05, CA-18 | EV-09, EV-12 | partially_implemented: accessibility behavior proven in unit and browser composition; visual match and touch drag not verified |
| SHIFU-123 example content | RF-14 / CA-17 | seed builds and loads (EV-18) | partially_implemented: the real journeys over the seed are not run |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| none | none | not applicable | not applicable |

| Field | Result |
| --- | --- |
| Publication | not requested; local only |
| Source verification | Learning PRD 83066881 (modified 2026-11-12) and Curriculum PRD 83034113 (modified 2026-11-02) read in full on 2026-11-17. The API gives no version number; SHIFU-123 cites 28 and 15 |
| Documentation Alignment | No external write made. Penpot boards unverified |
| Revision History | Spec revision 2 records implementation corrections, no product behavior change |
| Limitations | VM-01..VM-06 Blocked; CI-12 ran against a stub API; CI-16 failing on a pre-existing file |
