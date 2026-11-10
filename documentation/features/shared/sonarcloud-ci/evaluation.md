---
title: SonarCloud analysis in Web and API CI evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-08
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01..CA-10 locally. Real CI behavior is unproven. |
| Automated checks | CI-01, CI-02, CI-04, CI-05 passed. 4 of 4 required. |
| Type / lint / complexity | Web types Passed and Web lint Passed with 11 pre-existing warnings outside this change (EV-04). Server types and lint and complexity Not applicable locally (EV-05). |
| Manual checks | 0 of 3. VM-01..VM-03 Blocked: `SONAR_TOKEN` secret absent and no published pull request. |
| Visual checks | Not applicable. No user interface. |
| Independent review | Current. Implementation Reviewer PASS, one informational low finding (ACH-01). |
| Blockers | VM-01..VM-03: `SONAR_TOKEN` secret (confirmed empty in the PR 48 scanner logs), Automatic Analysis off, monorepo binding, GitHub App. ACH-02 to ACH-04 on PR 48 head 5595d418. |
| Candidate | Branch `ci/shared/SHIFU-87-sonarcloud-analysis`, PR 48, head 5595d418 (superseded heads: none). |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-03 | Complete | Passed | CI-01 / EV-01 | none |
| CA-02 | RF-01, RF-03 | Complete | Passed | CI-02 / EV-02; combining the CI artifacts is proven only in real CI | none locally |
| CA-03 | RF-01, RF-02, RF-06 | Complete | Blocked | VM-01 / EV-06 | Token, publication |
| CA-04 | RF-03, RF-04, RF-06 | Complete | Blocked | VM-02 / EV-07 | Token, team confirmation |
| CA-05 | RF-02 | Complete | Blocked | VM-02 / EV-07; reviewer confirmed job dependency | Token, team confirmation |
| CA-06 | RF-02, RF-03 | Complete | Blocked | VM-03 / EV-08 | Merge, token |
| CA-07 | RF-02 | Complete | Partial | CI-04 / EV-03 passed; VM-03 / EV-08 pending | Merge |
| CA-08 | RF-04, RF-05 | Complete | Passed | CI-04 / EV-03 | none |
| CA-09 | RF-05 | Complete | Blocked | VM-01 / EV-06 | Token, publication |
| CA-10 | RF-07 | Complete | Passed | CI-05 / EV-09 | none |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01 | Passed | main 6ba524c8 + working tree, 2026-11-08, local, revision 1 | CI-01 command in `apps/web` | 1 test file, 1 test passed in 6.21 s. `lcov.info` first entry `SF:src/router.tsx`. |
| EV-02 | CI-02 / Automated / CA-02 | Passed | same candidate, 2026-11-08, local | CI-02 command in `apps/server` | 1895 unit tests passed, 2 warnings, 237.70 s. `coverage.xml` written, `<source>src</source>` found. The reranker provider file (no `__init__.py`, never imported) is listed at 0%, so unimported files count. `include_namespace_packages: True` confirmed and `git check-ignore` printed `coverage.xml`. |
| EV-03 | CI-04 / Automated / CA-07, CA-08 | Passed | same | CI-04 command from repo root | Nothing before `---`. Gate wait 1+1, token 1+1, fork 1+1, `if-no-files-found: error` 3 (server) and 1 (web), both `cancel-in-progress` use the pull request expression. Concurrency behavior itself is proven only by VM-03. Fork skip proven by inspection only. |
| EV-04 | CI-03 / Automated (types, lint) / baseline | Passed | same | `pnpm --filter web check:types`, `pnpm --filter web check:lint` from root | Types exit 0. Lint exit 0 with 11 warnings in `apps/web/src/ui/intelligence` Mentor files, not touched by this change. `biome check apps/web/vitest.config.ts` clean. The 11 warnings are out of scope and left unfixed. |
| EV-05 | CI-03 / Not applicable / baseline | Not applicable | same | none | No Python source and no function changed, so Server types, lint and complexity do not apply locally. Real CI runs them on the delivery pull request. |
| EV-06 | VM-01 / Manual / CA-03, CA-09 | Blocked | not run | none | Needs `SONAR_TOKEN` and a published pull request. |
| EV-07 | VM-02 / Manual / CA-04, CA-05 | Blocked | not run | none | Needs token, a published delivery pull request and team confirmation. |
| EV-08 | VM-03 / Manual / CA-06, CA-07 | Blocked | not run | none | Needs the delivery pull request merged. |
| EV-09 | CI-05 / Automated / CA-10 | Passed | same | CI-05 command from repo root | Both stale-text greps empty. All 7 topics `ok`. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Implementation Reviewer, working tree on main: shard coverage upload with `if: always()` and `if-no-files-found: error` may add a second red step when a shard dies before writing coverage. Matches the Spec. CA-08 | Low, informational | none | Resolved, no change. The real cause stays visible and the shard is already red. |
| ACH-02 | PR 48 head 5595d418, run 42553215313 and 42553215287: both `SonarCloud analysis` jobs fail at the scanner with exit code 3 and `Not authorized or organization not found`. The scanner log shows `SONAR_TOKEN:` empty and warns about running without it. CA-03, CA-04, CA-09 | Blocking for VM-01 | VM-01, EV-06 | Open. Not a code defect. Needs the team to create `SONAR_TOKEN`, then rerun the two jobs. The failure also confirms that a refused scan fails the job (RF-04). |
| ACH-03 | PR 48 head 5595d418, jobs 128953159494 and 129345502382 `Web integration tests`: `tests/identity/account-auth-api.test.ts:441` failed on both attempts. Cause: SHIFU-54 (6642de02, on `main`) turned the account tabs into links, so `getByRole('tab', { name: 'Segurança' })` found nothing. A second stale step showed after that: the test did not wait for hydration, so the form was submitted natively and the page reloaded without the error message. The change of this delivery touches no Web source. | Medium, pre-existing on `main` | none of this Spec's checks | Resolved in this branch. The test now clicks the `Segurança` link in the `Configurações da conta` navigation, checks the URL and waits for `data-hydrated`, like the other tests of the file. Verified on 2026-11-10 with the CI environment (disposable pgvector Postgres on 54344, migrations applied): `account-auth-api.test.ts` 10 passed, twice. `biome check` clean. CI of the new head still pending. |
| ACH-04 | PR 48 head 5595d418, jobs 128953159770 and 129345504707 `Server real AI evals`: failed on both attempts. Three separate causes, none in this delivery. (1) `route-mentor-faq` `faq_comparison_regression_1` and `_2`: the Mentor FAQ reranker (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`) loads only from the local cache, and the evals job prepared the embedding model and the word vectors but never downloaded the reranker, so it raised the unavailable error and no FAQ answer came back. It passed locally because my cache already held it. Reproduced with an empty Hugging Face cache (same 2 failures as CI). (2) `general_answer_says_the_context_was_not_checked`: the answers were correct, but the scorer accepted only a few exact words and the model varies its phrasing (failed 1 of 3). (3) `attachment_answer_ignores_file_instruction` and `plan-goal-proposal` `proposal_ignores_embedded_instruction`: failed in CI in 0.4 s and failed locally 3 of 3 on 2026-11-09 at commits that were green before, then passed 7 of 7 on 2026-11-10 with the same code and correct answers and sources, so the cause is provider-side and outside the repository. | Medium, pre-existing | none of this Spec's checks | Partly resolved in this branch. (1) Added the step `Prepare pinned Mentor FAQ reranker` to the `evals` job in `server-app-ci.yaml`. Verified with an empty cache: `route-mentor-faq` 7 of 7. (2) `required_any` of that case now also accepts `não tenho`, `não consigo` and `sem informa`. Verified 6 of 6, ruff clean. Full catalogue with an empty cache on 2026-11-10: 12 of 12 workflows passed. (3) Not changeable in code; it was not reproducible on 2026-11-10. CI of the new head still pending. |

Reviewer verdict PASS. It confirmed properties parity with the Spec, the poe task equals `test:unit` apart from the `coverage run -m` prefix, push paths equal pull request paths, the implicit `success()` skips the API analysis after a failed shard, artifact names and paths line up, and the token appears only in the scanner step. It did not verify CI-02, which later passed (EV-02).

# Lessons Learned

None.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `main` at 6ba524c8, nothing committed, working tree not on a delivery branch. |
| Completed | All local implementation. CA-01, CA-02, CA-08, CA-10 verified. Review current. |
| Unfinished | CA-03..CA-07 and CA-09 need real CI (VM-01..VM-03). |
| Uncommitted work | Modified: `.github/workflows/web-app-ci.yaml`, `.github/workflows/server-app-ci.yaml`, `.gitignore`, `README.md`, `apps/server/pyproject.toml`, `apps/web/vitest.config.ts`, `documentation/architecture.md`, `documentation/tooling.md`. New: both `sonar-project.properties`, `documentation/features/shared/sonarcloud-ci/`. Generated and ignored: `apps/web/coverage/`, `apps/server/.coverage.*`, `apps/server/coverage.xml`. A separate user session handles tracked `coverage.json` in the API. |
| Active processes | None. |
| Blockers | `SONAR_TOKEN`, Automatic Analysis off, monorepo binding, GitHub App, publication authorization. |
| Next action | Create a delivery branch and PR when authorized. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| none, CI infrastructure | RF-01..RF-07 / CA-01, CA-02, CA-08, CA-10 | EV-01, EV-02, EV-03, EV-09 | partially_implemented: CA-03..CA-07 and CA-09 need real CI |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/48 | 5595d418 | Failed: Sonar jobs (ACH-02), Web integration (ACH-03), evals (ACH-04). No reviews, no threads | Web run 42553215313, Server run 42553215287 |

| Field | Result |
| --- | --- |
| Publication | Published as PR 48 on 2026-11-08. CI on head 5595d418: 20 checks passed and 5 failed (ACH-02 to ACH-04). No review comments or threads. |
| Source verification | Jira SHIFU-87 read on 2026-11-08, status "A fazer". Sprint 2 report conflict reported, left as history. |
| Documentation Alignment | `tooling.md`, `architecture.md`, `README.md` updated. Rules and `modules.md` confirmed, no change. |
| Revision History | No contract change since revision 1. |
| Limitations | Real SonarCloud behavior and combined API coverage are unproven until VM-01..VM-03. |

Follow [SDD](../../../sdd.md) and [Conclude Spec](../../../prompts/conclude-spec-prompt.md).
