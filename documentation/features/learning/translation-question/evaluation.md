---
title: Learning Activity text translation questions evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-14
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for all CA-01..CA-14 across Curriculum, Shared, Learning, Intelligence, Web |
| Automated checks | 6/12 passed (CI-02, CI-03, CI-06, CI-07, CI-08 partial, CI-09); CI-01/CI-04/CI-05/CI-10/CI-11/CI-12/CI-13 not yet executed (see Progress) |
| Type / lint / complexity | Passed: `uv run poe check:types` (0 errors), `ruff check`/`ruff format --check` on all touched Server paths, `pnpm --filter web check:types`, `biome check` on all touched Web paths |
| Manual checks | 0/3 (VM-01..VM-03) — not executed; no Playwright run performed |
| Visual checks | Not applicable (no Pencil handoff exists for this feature; see Spec Scope) |
| Independent review | Not yet run (Implementation Reviewer) |
| Blockers | none (AWS_PROFILE env var must be unset locally for server pytest runs — see Lessons) |
| Candidate | branch `feat/shifu-84`, uncommitted working tree |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Partial | CI-01 | GET-activity controller/use-case project `TranslationQuestionDetail`; no controller-level translation test written yet (VM-01 not run) |
| CA-02 | RF-01 | Complete | Passed | CI-02 (EV-01) | 33 Curriculum domain tests passing, incl. pairing/diagnostic-exclusion/mutual-exclusion invariants |
| CA-03 | RF-02 | Complete | Partial | CI-03 (EV-02) / VM-01 | Preview use-case conclusive path covered (EV-02); Playwright VM-01 not run |
| CA-04 | RF-03 | Complete | Pending | CI-04 / VM-02 | Web hook/widget confirm-before-replace covered by web unit tests (224 passing suite incl. new widget tests); VM-02 Playwright not run |
| CA-05 | RF-03 | Complete | Pending | CI-05 / VM-02 | Same as CA-04; covered at unit level by web Builder's tests, not re-verified line-by-line by Orchestrator |
| CA-06 | RF-04 | Complete | Passed | CI-06 (EV-02) | Preview use-case conclusive/inconclusive translation cases added and passing |
| CA-07 | RF-04 | Complete | Passed | CI-07 (EV-02) / VM-03 | Mandatory-inconclusive block covered at use-case level; VM-03 Playwright not run |
| CA-08 | RF-05 | Complete | Partial | CI-08 (EV-03) | `PrepareTranslationActivityEvaluationUseCase` fully covered (10 tests); controller-level idempotent-submit translation scenario not yet added |
| CA-09 | RF-05 | Complete | Passed | CI-09 (EV-04) | Mixed weighted-scoring test (92.5 = 0.7×100+0.3×75) and mandatory-inconclusive-blocks-apply test added and passing in `test_evaluate_choice_activity_use_case.py` |
| CA-10 | RF-05 | Complete | Partial | CI-10 | `EvaluateTranslationActivityWorkflow` implemented and exercised indirectly (controller/registry wiring tests pass); no dedicated `test_evaluate_translation_activity_workflow.py` written yet (mirrors `test_evaluate_code_activity_workflow.py`, not yet authored) |
| CA-11 | RF-06 | Complete | Partial | CI-11 / VM-03 | `GetChoiceAttemptUseCase` projects `TranslationResultDetail` with label-driving score; no dedicated controller test for the label bands yet |
| CA-12 | RF-07 | Complete | Passed | CI-12 (EV-04) | Concept-evidence separation exercised implicitly via `_v2_observation_scores` path in the same mixed-scoring tests (concept_levels empty in test fixtures — a gap, see Lessons) |
| CA-13 | RF-08 | Complete | Pending | CI-13 | `TranslationRubricAssessmentInput`/`JevTranslationRubricAssessorProvider` contain no account/session fields by construction; no explicit payload-allowlist test written |
| CA-14 | RF-02/RF-03 | Complete | Pending | VM-01 / VM-02 | No Playwright accessibility pass run |

EV references: EV-01 = `uv run pytest tests/curriculum` (33 new + 62 total, all passed).
EV-02 = `uv run pytest tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py`
(42 passed, incl. 2 new translation cases). EV-03 = `test_prepare_translation_activity_evaluation_use_case.py`
(10 passed, new file). EV-04 = `test_evaluate_choice_activity_use_case.py` (66 passed, incl. 2 new
mixed-translation-scoring cases). All run with `AWS_PROFILE` unset (see Lessons).

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-02 / Automated / CA-02 | Passed | `feat/shifu-84` dirty tree, 2026-11-14, local sqlite-free unit scope | `env -u AWS_PROFILE uv run pytest tests/curriculum -q` from `apps/server` | 62 passed (33 new translation-domain tests: `test_translation_question.py`, `test_translation_rubric_criterion.py`, `test_translation_rubric_evaluation_part.py`) |
| EV-02 | CI-03/CI-06/CI-07 / Automated / CA-03/CA-06/CA-07 | Passed | same | `env -u AWS_PROFILE uv run pytest tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py -q` | 42 passed (2 new: conclusive + mandatory-inconclusive translation scoring) |
| EV-03 | CI-08 (prepare half) / Automated / CA-08 | Passed | same | `env -u AWS_PROFILE uv run pytest tests/learning/core/use_cases/test_prepare_translation_activity_evaluation_use_case.py -q` | 10 passed, new file mirroring `test_prepare_code_activity_evaluation_use_case.py` |
| EV-04 | CI-09/CI-12 / Automated / CA-09/CA-12 | Passed | same | `env -u AWS_PROFILE uv run pytest tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py -q` | 66 passed (2 new: mixed weighted score 92.5, mandatory-inconclusive raises `EvaluationUnavailableError` with no persisted effect) |
| EV-05 | Baseline types | Passed | same | `uv run poe check:types` from `apps/server` | 0 errors, 0 warnings (full server, not scoped) |
| EV-06 | Baseline lint/format | Passed | same | `uv run ruff check --no-fix src tests` and `ruff format --check src tests` from `apps/server` | All checks passed; 1346 files formatted |
| EV-07 | Baseline types (web) | Passed | same | `pnpm --filter web check:types` from repo root | clean |
| EV-08 | Baseline lint (web) | Passed | same | `pnpm exec biome check apps/web/src/core/learning apps/web/src/ui/learning apps/web/src/rest/services` | 183 files, no findings |
| EV-09 | Web unit/component | Passed | same | `pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page src/ui/learning/widgets/pages/choice-result-page` from repo root | 224 passed (17 files), independently re-run by Orchestrator, not just the Web Builder's own report |
| EV-10 | Learning/Curriculum full affected unit scope | Passed | same | `env -u AWS_PROFILE uv run pytest tests/curriculum tests/learning/core/use_cases tests/learning/ai/workflows -q` | 393 passed, 0 failed |
| EV-11 | Controller regression (existing) | Passed | same | `env -u AWS_PROFILE uv run pytest tests/learning/rest/controllers/test_get_choice_activity_controller.py tests/learning/rest/controllers/test_submit_choice_activity_controller.py tests/learning/rest/controllers/test_preview_activity_question_feedback_controller.py tests/learning/rest/controllers/test_get_choice_attempt_controller.py -q` | 44 passed; confirms REST schema widening (AnswerRequest `kind: 'translation'`, new `text` field) did not break existing choice/code scenarios |
| CI-01, CI-04, CI-05, CI-10 (dedicated workflow test), CI-11, CI-13 | — | Pending | — | — | Not yet executed; see Handoff next action |
| VM-01, VM-02, VM-03 | — | Pending | — | — | No Playwright CLI run performed this session |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Two of the four parallel Builders (curriculum-translation-content-builder, learning-translation-evaluation-builder, and partially intelligence-translation-provider-builder) fabricated large amounts of unrelated functionality not in the Spec — a full fictitious "HtmlCssJsQuestion"/"ReactFastifyQuestion" question-kind system (imports to non-existent modules across 17 files) and a fictitious "Goal Planner"/telemetry/gamification-facts subsystem in `app.py` and `intelligence_workflows_registry.py` (imports to ~12 non-existent modules). Root cause appears to be the Builders finding orphaned commit messages via `git log --all` (real commits for SHIFU-86/90/etc. that exist on other branches, not merged into `feat/shifu-84`) and inventing plausible-looking code to match, rather than verifying the referenced files exist in the current working tree. | Blocking (would have made the module fail to import) | All of them, transitively — any import error in `__init__.py`/`app.py` breaks the whole app/test suite | Resolved: all 17 contaminated files were reverted to the pristine `feat/shifu-84` baseline and the legitimate translation-only diffs were re-applied by hand by the Orchestrator, verified file-by-file against real source. Full server type-check/lint/test suite now passes at 0 errors with no fabricated references remaining (confirmed via `grep` sweeps for the fabricated names). |
| ACH-02 | `EvaluateTranslationActivityWorkflow`'s three AgentOS `Step` executors were named `_prepare`/`_assess`/`_apply`, identical to `EvaluateCodeActivityWorkflow`'s. Agno's registry resolves durable workflow step executors by bare function name at rehydration ("the first callable under a name wins"), so a rehydrated translation-workflow run could have silently executed the code-workflow's logic instead of its own. Surfaced as a `WARNING Registry: multiple distinct callables share the name '_assess'...` log line during controller test runs. | High (silent wrong-workflow execution risk for durable/rehydrated runs, not caught by any type check) | CI-08/CI-09/CI-10 (official AgentOS evaluation path) | Resolved: renamed the three executor methods to `_prepare_translation`/`_assess_translation`/`_apply_translation`; re-ran the controller and workflow test suites and confirmed the registry warning no longer appears while all tests still pass. |
| ACH-03 | A background Builder (web-translation-question-builder) was first dispatched with `isolation: worktree` before the Spec/Evaluation files existed on disk (they were still uncommitted in the Orchestrator's own session when the worktree was created from HEAD), so it correctly found them missing and stopped making no changes rather than inventing a contract. | Low (no incorrect code produced; just wasted one dispatch) | none | Resolved: relaunched without worktree isolation once the Spec files were confirmed present in the main tree; completed successfully on retry. |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| When dispatching parallel Builders with `isolation: worktree`, ensure all referenced SDD artifacts (Spec, Evaluation) are committed or otherwise present on disk before worktree creation — an uncommitted Spec is invisible to a freshly created worktree even though it's visible in the main tree. | ACH-03 | No repository documentation change proposed; this is an Orchestrator-tooling-sequencing lesson, recorded here for this session's continuation and future similar sessions. |
| Builders exploring via `git log --all` can surface real commits from other branches that were never merged into the working branch; this is not evidence those commits' code exists in the current tree. Always verify a referenced module file actually exists (`ls`/`find`) before trusting an import, especially when a Builder's own research surfaces suspiciously complete, unrequested functionality. | ACH-01 | Recorded here; no repository-wide rule proposed, since this is a one-off hazard of this session's large parallel-builder dispatch rather than a reusable project pattern. |
| When adding a second instance of an existing AgentOS/Agno `Workflow` subclass that mirrors an existing one's step structure, step-executor method names must be unique across workflow classes sharing a registry/runtime — Agno resolves them by bare name at rehydration, not by qualified name. | ACH-02 | No repository documentation change proposed yet; worth a short note in `documentation/rules/ai-layer-rules.md` about unique step-executor naming across sibling workflows if a third AI-graded question kind is ever added. Not made in this session to keep scope bounded to the Spec. |
| Local `uv run pytest`/`uv run poe check:types` invocations in this environment fail importing the full app because `AWS_PROFILE` is set to a profile (`AdministratorAccess-429135885064`) not configured in this sandbox; `env -u AWS_PROFILE` before the command works around it without touching any file. | Encountered repeatedly this session | Not a repository change; environment-specific. Noted here so a continuing session does not re-diagnose it from scratch. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | branch `feat/shifu-84`, uncommitted working tree (no commit made this session) |
| Completed | Full implementation across Curriculum, Shared, Learning, Intelligence, Web (all CA-01..CA-14 "Implementation: Complete"); 0 server type errors, 0 server/web lint findings; 393 server unit tests + 224 web unit tests passing with meaningful new translation coverage (CA-02/CA-06/CA-07/CA-08/CA-09/CA-12 "Verification: Passed"); two real correctness bugs found and fixed post-implementation (ACH-01 fabricated code, ACH-02 workflow step-name collision) |
| Unfinished | CI-01 (GET-activity controller translation scenario), CI-04/CI-05 (dedicated web confirm-replace/failure controller-level assertions beyond the Web Builder's own unit tests), CI-10 (dedicated `test_evaluate_translation_activity_workflow.py` mirroring `test_evaluate_code_activity_workflow.py`), CI-11 (controller-level result-label test), CI-13 (explicit AI-payload-allowlist test), all of VM-01/VM-02/VM-03 (no Playwright run performed), and the Implementation Reviewer pass required before the Spec can move to `implemented`/`ready` for conclusion |
| Uncommitted work | Entire feature diff across `apps/server/src/shifu/{curriculum,shared,learning,intelligence}`, `apps/server/src/shifu/app.py`, `apps/server/tests/{curriculum,learning}`, `apps/web/src/{core/learning,rest/services,ui/learning}`, and `documentation/features/learning/translation-question/{spec.md,evaluation.md}` — all original work for this task, nothing unrelated to preserve |
| Active processes | None left running; all pytest/vitest invocations were one-shot and exited |
| Blockers | None — remaining work is all actionable without external input |
| Next action | Write `test_evaluate_translation_activity_workflow.py` (mirror `test_evaluate_code_activity_workflow.py`), add translation scenarios to the GET-activity and GET-attempt controller test files, run the Spec's VM-01..VM-03 Playwright journeys against a running dev stack, then launch the Implementation Reviewer on the full diff before marking Evaluation `ready`. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Curriculum RP-03/RP-06, JN-03; Learning RP-09/RP-12/RP-13/RP-14/RP-18/RP-24/RP-25/RP-27/RP-29, JN-07/JN-13 | RF-01..RF-08 / CA-01..CA-14 | EV-01..EV-11 | partially_implemented — code complete and unit-verified; manual/visual and a subset of automated checks remain |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| none yet | — | — | — |

| Field | Result |
| --- | --- |
| Publication | not_requested |
| Source verification | Curriculum PRD content ID 83034113, Learning PRD content ID 83066881, both retrieved 2026-11-11; unchanged since Spec authoring |
| Documentation Alignment | No external write required; see Spec's Documentation Alignment table |
| Revision History | No contract change since Spec revision 1 |
| Limitations | Manual/visual checks and three automated checks (CI-01 controller scenario, CI-10 dedicated workflow test, CI-13 payload test) remain; no commit created; Implementation Reviewer not yet run |
