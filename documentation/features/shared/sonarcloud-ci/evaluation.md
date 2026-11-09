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
| Blockers | VM-01..VM-03: `SONAR_TOKEN` secret, Automatic Analysis off, monorepo binding, GitHub App, then publication authorization. |
| Candidate | Branch `main` at 6ba524c8, uncommitted working tree. Dirty scope listed in Handoff. |

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
| none yet | none | Pending | none |

| Field | Result |
| --- | --- |
| Publication | Not requested |
| Source verification | Jira SHIFU-87 read on 2026-11-08, status "A fazer". Sprint 2 report conflict reported, left as history. |
| Documentation Alignment | `tooling.md`, `architecture.md`, `README.md` updated. Rules and `modules.md` confirmed, no change. |
| Revision History | No contract change since revision 1. |
| Limitations | Real SonarCloud behavior and combined API coverage are unproven until VM-01..VM-03. |

Follow [SDD](../../../sdd.md) and [Conclude Spec](../../../prompts/conclude-spec-prompt.md).
