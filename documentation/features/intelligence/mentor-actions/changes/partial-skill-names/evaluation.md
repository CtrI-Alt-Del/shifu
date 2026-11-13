---
title: Mentor — partial Skill names in confirmed actions evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-11-12
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete; CA-01 to CA-07 (revision 1) |
| Automated checks | 4/4 passed (CI-01 to CI-04), rerun after the review corrections (EV-06) |
| Type / lint / complexity | Passed: basedpyright 0 errors, 0 warnings, 0 notes (EV-04); Ruff lint and format clean on both files; complexity is the configured Ruff `C90` lint with no findings, no metrics tool required (EV-04) |
| Manual checks | 1/1 passed (VM-01, EV-05); the review corrections touch only the word lists and tests, so the manual result stays valid |
| Visual checks | Not applicable: the card, copy, layout and states are unchanged and the Spec names no Penpot board |
| Independent review | Passed: Implementation Reviewer found no blocking issue; one medium and four low findings, all dispositioned (ACH-01 to ACH-05) |
| Blockers | None |
| Candidate | Branch `feat/shifu-118` at `4815e753`, uncommitted (includes the review corrections): `apps/server/src/shifu/intelligence/core/use_cases/mentor_action_planner.py`, `apps/server/tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py`, this Spec and this Evaluation. Unrelated dirty paths are preserved |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 / EV-01, VM-01 / EV-05 | Review |
| CA-02 | RF-01 | Complete | Passed | CI-01 / EV-01 | Review |
| CA-03 | RF-02 | Complete | Passed | CI-02 / EV-02 | Review |
| CA-04 | RF-03 | Complete | Passed | CI-02 / EV-02 | Review |
| CA-05 | RF-04 | Complete | Passed | CI-03 / EV-03 | Review |
| CA-06 | RF-05 | Complete | Passed | CI-03 / EV-03 | Review |
| CA-07 | RF-01, RF-06 | Complete | Passed | CI-01 / EV-01 | Review |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-02, CA-07 | Passed | `4815e753` plus uncommitted change, 2026-11-12, mocked ports (use-case boundary) | `uv run --no-sync pytest tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py -v -p no:cacheprovider`, `apps/server` | Whole file 136 passed, 0 skipped, 21.6 s. The six CI-01 scenarios ran and passed: `..._removal_for_a_skill_named_by_one_word_of_its_title`, `..._addition_for_a_skill_named_by_one_word_of_its_title`, `..._not_match_a_skill_through_command_words`, `..._not_match_a_skill_through_a_named_objective_title`, `..._resolve_the_skill_word_that_stays_next_to_an_objective_title`, `..._keep_the_objective_title_when_no_skill_word_is_left`. The last two assert one destination read, so a command word kept as a candidate cannot hide behind the removal tie-break. History: before the implementation the same file gave 127 passed and 9 failed, the nine behavior scenarios |
| EV-02 | CI-02 / Automated / CA-03, CA-04 | Passed | Same candidate, date, command and file | Same run as EV-01 | The six CI-02 scenarios passed: only held skill, several held, none held, five candidates with exactly six reads (five tie-break plus the final), more than five with no reads, and addition with no tie-break reads |
| EV-03 | CI-03 / Automated / CA-05, CA-06 | Passed | Same candidate, date, command and file | Same run as EV-01 | Existing scenarios for an unknown Skill, the longest full title, non-Skill entries and the Skill page full name and the named-another-Skill cases pass unchanged. The new ones passed: no shared content word, access failure stops the tie-break after one read, and a partial name is not resolved on a Skill page. The helper `_use_real_like_search` now sets `skill_id` as the Learning provider does |
| EV-04 | CI-04 / Automated / baseline | Passed | Same candidate and date | `uv run --no-sync ruff check --no-fix <the two files>` and `uv run --no-sync ruff format --check <the two files>`; `uv run poe check:types`; `uv run poe check:architecture` (all in `apps/server`); `pnpm check:test-integrity` (repository root) | Ruff check: all checks passed (includes `C90`). Ruff format: 2 files already formatted. basedpyright: 0 errors, 0 warnings, 0 notes in 59 s, with no pre-change diagnostics to baseline. Tach: all modules validated. Test integrity: 434 files passed. The pytest run prints 2 existing warnings (a pytest assertion-rewrite notice for `tests.fixtures.postgres_fixture` and a Starlette deprecation), none from this change |
| EV-05 | VM-01 / Manual / CA-01 | Passed | Same candidate, 2026-11-12, real stack: PostgreSQL, Redis, Inngest, API on 7777 restarted on the new code, web on 7000; Mentor index prepared earlier; seed learner; Playwright CLI session `shifu-118` | Signed in through the form, opened the Mentor page and the seeded conversation "Organização dos estudos", sent "Remova a habilidade JavaScript", pressed "Recusar"; read-only queries from the repository root | The conversation answered "Preparei uma proposta para você confirmar." with the card "Remover JavaScript essencial?", "Objetivo: Aprender a programar" and the buttons "Recusar" and "Remover habilidade"; not "Não encontrei…". "Recusar" moved it to "Remoção recusada"; the proposal row is `declined` of kind `remove_skill`. Console: 47 messages, 0 errors, 0 warnings. The charge row for the attempt shows `charged_units` 0 and `refunded` false, so the turn made no model charge. The Skill experience still exists (1 row). Capture: `apps/web/.playwright-cli/screenshots/vm01-partial-skill-card.png`. Limit: the first sign-in attempt submitted before the page hydrated and was repeated; "Organização dos estudos" now holds this exchange until the next reseed |
| EV-06 | CI-01 to CI-04 rerun / Automated / CA-01 to CA-07 | Passed | Same base plus the review corrections, 2026-11-12 | Same pytest, Ruff, basedpyright, Tach and test-integrity commands as EV-01 and EV-04 | Whole file 139 passed, 0 skipped, 2 existing warnings. Ruff check and format clean, basedpyright 0/0/0, Tach validated, test integrity 434 files. Mutation checks: removing the action-verb filter fails 2 scenarios, removing the new function words fails 1, and dropping accent folding of the Objective title fails 1. The corrections added 3 scenarios (function words, action verb in a title, accented Objective title). VM-01 is not rerun: the change touches only word lists and tests, and the VM-01 request resolves exactly as before |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Function words ("uma", "por", "como", "que", "favor"...) still counted as Skill words, so "Remova uma habilidade do meu Objetivo" resolved to "Como avaliar uma condição" where the old rule said not found. RF-01, RF-06 | Medium | CI-01 | Fixed: the words were added to the command-word list, which the Spec lets the implementation extend. New scenario for function words fails without them. EV-06 |
| ACH-02 | No scenario proved the action-verb filter. RF-06 | Low | CI-01 | Fixed: scenario with a Skill titled "Insira dados em tabelas"; it fails when the filter is removed. EV-06 |
| ACH-03 | Accent folding and longest-first removal of Objective titles had no test. RF-06, CA-07 | Low | CI-01 | Partly fixed: an accented-title scenario now fails without folding. Longest-first is not reachable through the use case, because two overlapping titles in one request make the use case ask which Objective is meant before the planner runs. The sort stays as a defensive rule and is covered by review only |
| ACH-04 | The verb pattern filters real words such as "delete" as a Skill word. RF-06 | Low | none | Accepted limit: it follows the Spec, which says to ignore the verbs the planner already knows. A Skill distinguished only by such a word is reachable by another word of its title |
| ACH-05 | New test constants lacked `ClassVar` annotations and `zip` was not strict. Python Conventions | Low | none | Fixed: constants annotated, and the helper builds Objective ids from the index instead of zipping |

# Lessons Learned

None. The review corrections are small, and the existing Spec wording already allowed extending the command-word list.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-118` at `4815e753`; uncommitted paths listed in Current State |
| Completed | CA-01 to CA-07 implemented, verified (EV-01 to EV-06) and independently reviewed |
| Unfinished | Nothing; publication was not requested |
| Uncommitted work | The two source and test files plus this Spec and Evaluation belong to this task. `scripts/open-penpot.mjs`, `apps/server/coverage.xml` and the SHIFU-118 Evaluation edit are unrelated and preserved |
| Active processes | API on 7777 (`uv run poe dev`, log `/tmp/claude-1000/api-user11.log`), Redis and Compose services, the user's web app on 7000. The Playwright session `shifu-118` is closed. The API was started earlier in this session and restarted for VM-01; leave it running unless asked |
| Blockers | None |
| Next action | Conclude locally. Commit and branch choice are the user's call, as the change is outside PR 51 |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-17, JN-21, JN-22 | RF-01 to RF-06 / CA-01 to CA-07 | EV-01 to EV-06 | implemented and reviewed; limits: the manual-check data note in EV-05 and the longest-first note in ACH-03 |

| PR | Current head SHA | Review state |
| --- | --- | --- |
| Not requested | n/a | n/a |

| Field | Result |
| --- | --- |
| Publication | Not requested; the change is outside PR 51 and nothing is committed or published |
| Source verification | Intelligence PRD 83099649 version 10, read in full on 2026-11-12; unchanged intent |
| Documentation Alignment | The parent Spec stays unedited and `architecture.md` needs no update, as the Spec records |
| Revision History | Revision 1, initial contract; no amendment during implementation |
| Limitations | Longest-first Objective title removal is defensive and not reachable through the use case (ACH-03) |

Follow [SDD](../../../../../sdd.md) and [Conclude Spec](../../../../../prompts/conclude-spec-prompt.md).
