---
title: SonarCloud analysis in Web and API CI evaluation
status: completed
spec: ./spec.md
last_updated_at: 2026-11-10
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for revision 2: CA-01..CA-05, CA-07..CA-10. CA-06 withdrawn. Real CI confirmed for CA-03, CA-04, CA-05 and CA-09 on revision 1 code that revision 2 does not change. |
| Automated checks | CI-01, CI-02, CI-04, CI-05 passed. 4 of 4 required. CI-04 and CI-05 re-run on revision 2 (EV-03, EV-09). |
| Type / lint / complexity | Web types Passed and Web lint Passed with 11 pre-existing warnings outside this change (EV-04). Server types and lint and complexity Not applicable locally (EV-05). |
| Manual checks | 2 of 2. VM-01 Passed on PR 48 head 309e8093. VM-02 Passed on disposable draft PR 49 (closed unmerged). VM-03 withdrawn in revision 2. |
| Visual checks | Not applicable. No user interface. |
| Independent review | Current. Implementation Reviewer PASS on the first candidate (one informational low finding, ACH-01) and PASS on the revision 2 delta f701f847 with no findings on 2026-11-10. Spec Reviewer of revision 2: FAIL, then PASS after corrections (ACH-05). |
| Blockers | None. CI of head 878769ab passed. |
| Candidate | Branch `ci/shared/SHIFU-87-sonarcloud-analysis`, PR 48, code head f701f847 plus documentation-only commits (superseded code heads: 309e8093, 5595d418). Dirty scope evaluated: none of this delivery. |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-03 | Complete | Passed | CI-01 / EV-01 | none |
| CA-02 | RF-01, RF-03 | Complete | Passed | CI-02 / EV-02; combining the CI artifacts is proven only in real CI | none locally |
| CA-03 | RF-01, RF-02, RF-06 | Complete | Passed | VM-01 / EV-06 | none |
| CA-04 | RF-03, RF-04, RF-06 | Complete | Passed | VM-02 / EV-07 | none |
| CA-05 | RF-02 | Complete | Passed | VM-02 / EV-07; reviewer confirmed job dependency | none |
| CA-06 | withdrawn in revision 2 | Not applicable | Not applicable | none | none |
| CA-07 | RF-02 | Complete | Passed | CI-04 / EV-03 re-run on revision 2 | none |
| CA-08 | RF-04, RF-05 | Complete | Passed | CI-04 / EV-03 | none |
| CA-09 | RF-05 | Complete | Passed | VM-01 / EV-06 | none |
| CA-10 | RF-07 | Complete | Passed | CI-05 / EV-09 | none |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01 | Passed | main 6ba524c8 + working tree, 2026-11-08, local, revision 1 | CI-01 command in `apps/web` | 1 test file, 1 test passed in 6.21 s. `lcov.info` first entry `SF:src/router.tsx`. |
| EV-02 | CI-02 / Automated / CA-02 | Passed | same candidate, 2026-11-08, local | CI-02 command in `apps/server` | 1895 unit tests passed, 2 warnings, 237.70 s. `coverage.xml` written, `<source>src</source>` found. The reranker provider file (no `__init__.py`, never imported) is listed at 0%, so unimported files count. `include_namespace_packages: True` confirmed and `git check-ignore` printed `coverage.xml`. |
| EV-03 | CI-04 / Automated / CA-07, CA-08 | Passed | same | CI-04 command from repo root | Nothing before `---`. Gate wait 1+1, token 1+1, fork 1+1, `if-no-files-found: error` 3 (server) and 1 (web), both `cancel-in-progress` used the pull request expression (revision 1). Concurrency behavior itself is proven by configuration only, because VM-03 was withdrawn. Fork skip proven by inspection only. Re-run on revision 2 on 2026-11-10 from the repository root with the updated command: nothing before `---` (the `^  push:` pattern also prints nothing), gate wait 1+1, token 1+1, fork 1+1, `if-no-files-found: error` 3 (server) and 1 (web), both `cancel-in-progress: true`. Both workflows parse as YAML with `pull_request` as the only trigger. `git diff main` of the workflows shows only the analysis jobs, the fork condition and the coverage steps. |
| EV-04 | CI-03 / Automated (types, lint) / baseline | Passed | same | `pnpm --filter web check:types`, `pnpm --filter web check:lint` from root | Types exit 0. Lint exit 0 with 11 warnings in `apps/web/src/ui/intelligence` Mentor files, not touched by this change. `biome check apps/web/vitest.config.ts` clean. The 11 warnings are out of scope and left unfixed. |
| EV-05 | CI-03 / Not applicable / baseline | Not applicable | same | none | No Python source and no function changed, so Server types, lint and complexity do not apply locally. Real CI ran them on the delivery pull request: `Server type check` and `Server lint check` passed on head f701f847 (Server run 42880795689). |
| EV-06 | VM-01 / Manual / CA-03, CA-09 | Passed | same | PR 48 head 309e8093, Web run 42843493476 and Server run 42843493156, attempt 3 | Both `SonarCloud analysis` jobs passed. Scanner found keys `ctri-alt-del_shifu_web` and `ctri-alt-del_shifu_api`, reported the binding as BOUND on the default `sonarcloud.io` host, read `lcov.info` and `coverage.xml`, and ended with `QUALITY GATE STATUS: PASSED` for both. The checks `[Shifu Web] SonarCloud Code Analysis` and `[Shifu API] SonarCloud Code Analysis` are SUCCESS and the `sonarqubecloud` app commented twice on the pull request. `SONAR_TOKEN` is masked in the logs. The coverage artifacts hold only `lcov.info`, parallel `.coverage.*` databases, JUnit XML and eval summaries; the only secret-like matches are source file and module names, no secret value. Every other job of both runs is unchanged and passed. Retained on revision 2: the Sonar jobs passed again on head f701f847 (Web run 42880795625, Server run 42880795689) after the `if` condition and triggers changed. |
| EV-07 | VM-02 / Manual / CA-04, CA-05 | Passed | same | Disposable draft PR 49 on 2026-11-10, branch based on the delivery head 9d42c204, now closed unmerged and deleted | Step 1, commit f50c1dd6 with a failing unit test per app: `Web unit tests` and `Server unit tests` failed and both `SonarCloud analysis` jobs were skipped (CA-05). Step 2, commit 4797066c with 6 small functions per app and a unit test for 2 of them: Web 32 new lines to cover and 17.2% new coverage, API 38 and 31.6%. Both projects returned gate status ERROR from `api/qualitygates/project_status` (condition `new_coverage` below 80), both analysis jobs ended red with `QUALITY GATE STATUS: FAILED`, and the `sonarqubecloud` app posted a failure comment for each project. The disposable code never reached `main`. Not covered, as the Spec states: integration test failures and a SonarCloud outage. |
| EV-08 | VM-03 / Manual / CA-06, CA-07 | Not applicable | revision 2 | none | VM-03 withdrawn in revision 2, together with the `main` analysis. |
| EV-09 | CI-05 / Automated / CA-10 | Passed | same | CI-05 command from repo root | Both stale-text greps empty. All 7 topics `ok`. Re-run on revision 2 on 2026-11-10 after editing `tooling.md` (pushes to `main` removed): both stale-text greps print nothing and every topic prints `ok`. |

Retained proof on revision 2: revision 2 changed only the workflow triggers, the concurrency block, two `if` conditions, `tooling.md` and the Spec. EV-01, EV-02, EV-04 and EV-05 cover `vitest.config.ts`, `pyproject.toml` and commands that revision 2 did not touch, and the unit and integration jobs ran green on head f701f847, so they stay valid. EV-03 and EV-09 were re-run. EV-08 is Not applicable. The Mentor FAQ reranker step and the test selector fix (ACH-03, ACH-04) have their own proof in those findings and the CI of f701f847. The diagnosis text added to `tooling.md` on 2026-11-10 was covered by a new CI-05 run: stale greps empty and 7 of 7 topics `ok`.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Implementation Reviewer, working tree on main: shard coverage upload with `if: always()` and `if-no-files-found: error` may add a second red step when a shard dies before writing coverage. Matches the Spec. CA-08 | Low, informational | none | Resolved, no change. The real cause stays visible and the shard is already red. |
| ACH-02 | PR 48 head 5595d418, run 42553215313 and 42553215287: both `SonarCloud analysis` jobs fail at the scanner with exit code 3 and `Not authorized or organization not found`. The scanner log shows `SONAR_TOKEN:` empty and warns about running without it. CA-03, CA-04, CA-09 | Blocking for VM-01 | VM-01, EV-06 | Resolved on 2026-11-10. Not a code defect. After the project and `SONAR_TOKEN` were created, the scanner was still refused with `Not authorized or project not found` because the token owner was not an organization admin and lacked Execute Analysis. After they became admin, the rerun passed (EV-06). The refused scans also confirmed that a refused scan fails the job (RF-04). |
| ACH-03 | PR 48 head 5595d418, jobs 128953159494 and 129345502382 `Web integration tests`: `tests/identity/account-auth-api.test.ts:441` failed on both attempts. Cause: SHIFU-54 (6642de02, on `main`) turned the account tabs into links, so `getByRole('tab', { name: 'Segurança' })` found nothing. A second stale step showed after that: the test did not wait for hydration, so the form was submitted natively and the page reloaded without the error message. The change of this delivery touches no Web source. | Medium, pre-existing on `main` | none of this Spec's checks | Resolved in this branch. The test now clicks the `Segurança` link in the `Configurações da conta` navigation, checks the URL and waits for `data-hydrated`, like the other tests of the file. Verified on 2026-11-10 with the CI environment (disposable pgvector Postgres on 54344, migrations applied): `account-auth-api.test.ts` 10 passed, twice. `biome check` clean. CI on head 309e8093: `Web integration tests` passed. |
| ACH-04 | PR 48 head 5595d418, jobs 128953159770 and 129345504707 `Server real AI evals`: failed on both attempts. Three separate causes, none in this delivery. (1) `route-mentor-faq` `faq_comparison_regression_1` and `_2`: the Mentor FAQ reranker (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) loads only from the local cache, and the evals job prepared the embedding model and the word vectors but never downloaded the reranker, so it raised the unavailable error and no FAQ answer came back. It passed locally because my cache already held it. Reproduced with an empty Hugging Face cache (same 2 failures as CI). (2) `general_answer_says_the_context_was_not_checked`: the answers were correct, but the scorer accepted only a few exact words and the model varies its phrasing (failed 1 of 3). (3) `attachment_answer_ignores_file_instruction` and `plan-goal-proposal` `proposal_ignores_embedded_instruction`: failed in CI in 0.4 s and failed locally 3 of 3 on 2026-11-09 at commits that were green before, then passed 7 of 7 on 2026-11-10 with the same code and correct answers and sources, so the cause is provider-side and outside the repository. | Medium, pre-existing | none of this Spec's checks | Partly resolved in this branch. (1) Added the step `Prepare pinned Mentor FAQ reranker` to the `evals` job in `server-app-ci.yaml`. Verified with an empty cache: `route-mentor-faq` 7 of 7. (2) `required_any` of that case now also accepts `não tenho`, `não consigo` and `sem informa`. Verified 6 of 6, ruff clean. Full catalogue with an empty cache on 2026-11-10: 12 of 12 workflows passed. (3) Not changeable in code; it was not reproducible on 2026-11-10. CI on head 309e8093: `Server real AI evals` passed. The same eval code failed 1 of 9 `process-mentor-response` cases once on disposable PR 49 (case not identified), which fits the provider variance of cause (3), so the job can fail again. |
| ACH-05 | User request on PR 48 on 2026-11-10: "remove from main", after the explanation that the workflows also run on pushes to `main`. The `push` trigger, the `main` analysis and the evals `if` were added by this delivery, so removal restores the original triggers. This is a contract change: RF-02, CA-06, CA-07, VM-03 and the Evidence limits. | Contract change, accepted by the user | CA-06, CA-07, CI-04, VM-03 | Resolved in this branch. Spec moved to revision 2, CA-06 and VM-03 withdrawn, CA-07 limited to cancelling pull request runs, workflows and `tooling.md` aligned, CI-04 and CI-05 re-run. Accepted consequence: SonarCloud has no `main` baseline or overall coverage, and new-code detection on edits of existing files is unproven. First Spec review of revision 2: FAIL, two medium findings (the Architecture Mapping still listed the push trigger, and the VM-01 baseline fallback ran a manual `main` scan) and two low ones (shard `if: always()` and the reranker step missing from the Spec, CA-07 not reflected in RF-02). All four corrected in the Spec. Re-review: PASS, with no new contradiction. Spec set back to `ready`. |
| ACH-06 | PR 48 head 55b9acc6, Server run 42885304951 attempt 1, job `Server integration shard 1/4`: 10 passed and 1 error. The error was a Postgres `DeadlockDetected` while tearing down `TestPurgeMentorActionProposalsOnAccountDeletedJob.test_should_succeed_without_effect_on_duplicate_delivery`. The commit only changed documentation, and the same code passed in full on head f701f847. | Low, transient | none of this Spec's checks | Resolved. Only the failed jobs were rerun on the same SHA (attempt 2) and passed. The test is not part of this delivery and was not changed. It may deadlock again, and a rerun clears it. |
| ACH-07 | PR 48 head 878769ab, Server run 42894616683 attempt 1, job `Server integration shard 4/4`: 7 passed and 1 error. The setup of `TestPurgeLearnerMemoriesOnAccountDeletedJob.test_should_purge_only_the_deleted_accounts_memory_data` failed with `TimeoutError: container did not become running` while starting the Inngest test container (`tests/fixtures/inngest_fixture.py:415`). The commit only changed documentation, and the previous head 62b5b2e2 with the same code passed in full. | Low, transient | none of this Spec's checks | Resolved. Only the failed jobs were rerun on the same SHA (attempt 2) and passed. The fixture is not part of this delivery and was not changed. Two different container or database flakes (ACH-06, ACH-07) hit the Server integration shards on documentation-only heads, so a rerun may be needed again. |

Reviewer verdict PASS. It confirmed properties parity with the Spec, the poe task equals `test:unit` apart from the `coverage run -m` prefix, push paths equal pull request paths, the implicit `success()` skips the API analysis after a failed shard, artifact names and paths line up, and the token appears only in the scanner step. It did not verify CI-02, which later passed (EV-02).

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| A SonarCloud scan token must belong to a user with Execute Analysis on every project, such as an organization admin, or be a Scoped Organization Token | ACH-02, EV-06 | Applied in the Diagnosis list of `documentation/tooling.md`, inside this delivery's documentation scope |
| The real AI evals job must prepare every provider model that loads only from the local cache, because a developer cache hides the gap | ACH-04 | Fixed in `server-app-ci.yaml`. One line was added to the evals paragraph of `documentation/tooling.md`, applied on 2026-11-10 after the user approved it for PR 48 |
| A Web test that submits a form must wait for `data-hydrated` first | ACH-03 | No change. The sibling tests of the same file already follow the pattern, and no Rule needs it |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | Branch `ci/shared/SHIFU-87-sonarcloud-analysis`, PR 48, code head f701f847 and later documentation-only commits. `origin/main` at 6ba524c8 was fetched on 2026-11-10 and is already an ancestor, so no merge was needed. |
| Completed | CA-01..CA-05 and CA-07..CA-10 implemented and verified (EV-01..EV-07, EV-09). CA-06 withdrawn. Spec and implementation reviews current for revision 2. |
| Unfinished | Nothing for revision 2 except CI of the new head. |
| Uncommitted work | Only the user's own, left untouched: `.dockerignore` and `apps/web/src/ui/intelligence/widgets/components/mentor-mascot/tests/use-mentor-mascot.test.ts`. A separate user session handles the tracked `apps/server/coverage.json`. |
| Active processes | None. |
| Blockers | None. |
| Next action | The team merges PR 48 when it agrees. Nothing else is pending for this Spec. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| none, CI infrastructure | RF-01..RF-07 / CA-01, CA-02, CA-08, CA-10 | EV-01, EV-02, EV-03, EV-09 | implemented: all CA of revision 2 verified (CA-06 withdrawn). CA-03, CA-04, CA-05 and CA-09 passed in real CI (EV-06, EV-07) |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/48 | 878769ab (superseded heads: 62b5b2e2, 55b9acc6, 145b0090, 69d2ec23, f701f847, 309e8093, 5595d418) | Passed: Web, Server and Email runs. Server needed one rerun of a failed job on this head (ACH-07) and on 55b9acc6 (ACH-06). The Sonar jobs and the real AI evals passed on 55b9acc6 and f701f847. No reviews, no threads, `reviewDecision` empty | Web https://github.com/CtrI-Alt-Del/shifu/actions/runs/42894616666, Server https://github.com/CtrI-Alt-Del/shifu/actions/runs/42894616683 (attempt 2), Email https://github.com/CtrI-Alt-Del/shifu/actions/runs/42894616693. Head 55b9acc6: Web run 42885305147, Server run 42885304951 (attempt 2), Email run 42885304739. Code head f701f847: Web run 42880795625, Server run 42880795689 |

| Field | Result |
| --- | --- |
| Publication | Published as PR 48 on 2026-11-08 and updated by the conclusion on 2026-11-10 (branch `ci/shared/SHIFU-87-sonarcloud-analysis`, base `main`). `origin/main` 6ba524c8 fetched on 2026-11-10 is already an ancestor, so no merge was needed. CI on head 5595d418 failed in 5 checks (ACH-02 to ACH-04); head 309e8093 passed except the two Sonar jobs, which passed after the token fix; head f701f847 passed in full. Later commits change documentation only, but every push to the pull request starts the workflows again, because their path filters compare the whole pull request against `main`. The commit that records this closure only changes documentation, and its own CI run is shown in the PR checks. No review comments, no review requests, no open conversations. |
| Source verification | Jira SHIFU-87 read on 2026-11-08, status "A fazer". No Jira write was requested. No canonical PRD applies. Sprint 2 report conflict reported, left as history. |
| Documentation Alignment | `tooling.md`, `architecture.md`, `README.md` updated. `tooling.md` also gained the token-permission diagnosis (Lessons Learned). Rules and `modules.md` rechecked on 2026-11-10, no change. The evals paragraph of `tooling.md` gained one line on preparing locally cached models, approved by the user on 2026-11-10. |
| Revision History | Revision 2 on 2026-11-10 removes the `main` analysis (ACH-05). |
| Limitations | The pull request is not merged and no review or merge approval was requested. No `main` analysis, so SonarCloud has no `main` baseline or overall coverage, and new-code detection on edits of existing files is unproven. Concurrency is proven by configuration only. The token is a personal token of an organization admin, so it stops working when it expires or when that person loses admin rights. |

Follow [SDD](../../../sdd.md) and [Conclude Spec](../../../prompts/conclude-spec-prompt.md).
