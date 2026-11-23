---
title: Public landing page evaluation
status: completed
spec: ./spec.md
last_updated_at: 2026-11-23
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Implemented; CA-01 through CA-06 have code and focused coverage. |
| Automated checks | PR #65 HEAD `ae52f4af`; Web CI run `45105489196` completed with all seven jobs passing after the failed integration job was rerun. Playwright integration rerun: 426/426. Vitest full suite passed; coverage: 81.89% lines. Sonar Quality Gate passed with 81.6% new-code coverage against an 80% threshold. |
| Type / lint / complexity | TypeScript and Web Biome gates passed. Biome includes configured complexity rules; no quantitative complexity runner is configured. |
| Manual checks | User approved the landing page presentation. Authenticated entry is covered by CI-01. |
| Visual checks | VM-02 passed from current desktop, full-page, mobile and 320 px captures. No matching Penpot board exists. |
| Independent review | Spec review passed revision 1. Visual review passed. Implementation review confirms the auth fix and proxy isolation, and flags the existing TanStack Start CSRF warning. |
| Blockers | None for this delivery. The existing app-wide TanStack Start CSRF warning remains documented in ACH-03 because changing server-function security is outside this feature contract. |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; HEAD `ae52f4af`, including task commits `7513dda2`, `81bf8a10`, `467d83c2`, `88fa92ea`, `2a050acf`, `ae52f4af` and merge of `origin/main` at `eaaaf5fe`. PR [#65](https://github.com/CtrI-Alt-Del/shifu/pull/65). |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Done | Passed | CI-01; visitor route, `private, no-store`, public shell, no private calls. | None. |
| CA-02 | RF-01/RF-05 | Done | Passed | CI-01; active root/HomePage and root-layout navigation. | None. |
| CA-03 | RF-01 | Done | Passed | CI-01; valid, invalid/expired, rejected-session and unavailable-Identity paths. | None. |
| CA-04 | RF-02/RF-03 | Done | Passed | CI-01, CI-02, VM-01/VM-02; pt-BR copy, destinations, MVP/future labels and illustrative preview. | None. |
| CA-05 | RF-04 | Done | Passed | CI-01, CI-02, VM-01/VM-02; 320 px overflow, CTA visibility, reduced motion, focus and touch targets. | None. |
| CA-06 | RF-05 | Done | Passed | CI-01; no private calls or external origins; root response cache is private. | None. |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | Spec review / all | Passed | Spec revision 1; 2026-11-22 | Read-only `public_landing_spec_reviewer`; repository root | No blocking findings after focused contract updates. |
| EV-02 | CI-01 / Automated / CA-01–CA-06 | Passed | Merged head; 2026-11-23; local Chrome, Vite, Identity API, controlled proxy and PostgreSQL; origin matches `.env.local` (`localhost`) | `playwright.cmd test --config=playwright.local.config.ts tests/identity/landing-page.test.ts tests/shared/root-layout.test.ts tests/identity/register-confirmation-auth-api.test.ts`; `apps/web` | 14/14 passed in 56.1s. A temporary local config supplied existing services because repository Playwright web-server commands use POSIX `exec`, unavailable in Windows PowerShell. The temporary config was removed after testing. Earlier runs used `127.0.0.1` while Better Auth expected `localhost`; the corrected origin passes all auth flows. |
| EV-03 | CI-02 / Automated / CA-04–CA-05 and root-layout | Passed | Merged head; 2026-11-23; Vitest 4.1.6 | `.\node_modules\.bin\vitest.cmd run src\ui\identity\widgets\pages\landing-page\tests\landing-page.test.tsx src\ui\identity\widgets\pages\landing-page\tests\use-landing-page.test.ts src\ui\shared\widgets\layouts\root-layout\tests\root-layout.test.tsx src\ui\shared\widgets\layouts\root-layout\tests\use-root-layout.test.ts`; `apps/web` | 4 files, 30 tests passed. |
| EV-04 | CI-03 types / static / all | Passed | Merged head; 2026-11-23; Web | `pnpm --filter web check:types`; repository root | Exit 0 after `pnpm install --frozen-lockfile` synchronized Recharts from the merged lockfile. |
| EV-05 | CI-03 lint and configured complexity / static / all | Passed | Merged head; 2026-11-23; repository | `pnpm --filter web check:lint`; repository root | 917 files checked with no findings. Complexity rules run through Biome; no separate numeric complexity checker is configured. |
| EV-06 | CI-03 architecture / static / changed Web | Passed | Merged head; 2026-11-23; Web | `pnpm --filter web check:architecture`; repository root | 907 modules and 3702 dependencies; no architecture violations. |
| EV-07 | CI-03 production build / static / all | Passed | Merged head; 2026-11-23; Web | `pnpm --filter web build`; repository root | Build succeeded with Recharts installed. Rolldown plugin timing output was informational. |
| EV-08 | VM-01 / Manual / CA-01–CA-04, CA-06 | Passed for requested page review | Current landing; 2026-11-23 | User reviewed the landing presentation and approved it; local route is `http://localhost:7000/` | User's manual approval covers the page presentation. Authenticated and pending account paths are covered by CI-01. |
| EV-09 | VM-02 / Visual / CA-04–CA-05 | Passed | Current branch; 2026-11-23; fresh Playwright captures | `landing-desktop-fold.png`, `landing-desktop.png`, `landing-mobile.png`, `landing-320.png`; `apps/web/.playwright-cli/screenshots/` | Independent visual reviewer passed. Desktop hierarchy and responsive 390/320 px compositions have no material findings. No matching Penpot board; no Penpot comparison claimed. |
| EV-10 | Web application CI / Automated / CA-01–CA-06 | Passed | PR #65 HEAD `ae52f4af`; 2026-11-23; GitHub Actions run `45105489196` | `Web application CI`; GitHub Actions | All seven jobs passed after rerunning the failed integration job. The first attempt had 425/426 because the existing lost-password-response test received 401 instead of 200; rerun passed 426/426 in 8.0 min. Unit tests, type check, lint, architecture, build and SonarCloud also passed. Overall Vitest line coverage was 81.89%. |
| EV-11 | SonarCloud Quality Gate / Automated / all changed production paths | Passed | PR #65 HEAD `ae52f4af`; 2026-11-23; SonarCloud | Quality Gate status API for project `ctri-alt-del_shifu_web`, pull request 65 | New-code coverage 81.6% (threshold 80%); reliability, security, maintainability, duplication and hotspot conditions all passed. |
| EV-12 | Pending confirmation status unit suite / Automated / CA-01, CA-03 | Passed | HEAD `ae52f4af`; 2026-11-23; Vitest 4.1.6 | `vitest run src/provision/auth/better-auth/tests/pending-confirmation-status.test.ts`; `apps/web` | 13/13 passed. Covers missing/malformed cookies, accepted statuses, Identity failure and malformed payloads; also asserts forwarding the cookie header. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | `delivery_issue` did not distinguish absent pending context from an Identity outage. CA-01/CA-03. | High | CI-01, CI-03 | Resolved: check for cookie-name presence only, validate signed/stored context server-side, return unavailable on Identity failure. CI-01 14/14 passed on merged head. |
| ACH-02 | A global proxy outage scenario could affect concurrent tests. Initial browser harness also used `127.0.0.1` while Better Auth expected `localhost`, rejecting auth requests. | Medium | CI-01 | Resolved: scope outage by pending handle and use the configured origin. CI-01 14/14 passed. |
| ACH-03 | TanStack Start dev runtime reports that server functions lack CSRF middleware. It is an existing app-wide warning outside the approved landing Spec. | Medium | Runtime warning review | Unresolved. Not disabled or hidden. Adding middleware changes server-function security globally and requires a Spec amendment. |
| ACH-04 | Removing user-authorized `SHIFU-129-diagnostico.md` left two references in the ready Learning ordering Spec. | Low | Documentation | Resolved: references now point to the existing ordering Spec; no product contract changed. |
| ACH-05 | The proxy's pending-outage scenario could leak across parallel account tests. | Medium | CI-01 | Resolved: proxy matches the pending handle in the request body and forwards that body unchanged when no fault applies. CI-01 14/14 passed. |
| ACH-06 | The repository-wide commit hook reported warnings in unrelated Studio files: two non-null assertions and two `!important` uses. It also reported a 3.7 MiB generated coverage file as informational. | Low | Commit hook | Unresolved; paths are outside SHIFU-121. The scoped Web lint gate passes without findings. |
| ACH-07 | The existing anonymous Home integration test still expected `/` to redirect to login after the public landing was introduced. | Medium | Web integration CI | Resolved in `467d83c2`: the test now asserts the public landing and absence of Home. Full CI passed 426/426 on `ae52f4af`. |
| ACH-08 | SonarCloud initially measured 53.6% new-code coverage, below its 80% Quality Gate. | High | SonarCloud Quality Gate | Resolved in `88fa92ea`: extracted the pending-confirmation response validation into a focused helper with 13 unit cases. Current Quality Gate passes at 81.6%. |
| ACH-09 | An unrelated existing lost-password-response integration test returned 401 instead of 200 on one full-suite attempt. | Low | Web integration CI | Rerunning only the failed CI job passed all 426/426 tests on the same HEAD. No task code or fixtures were implicated. Recorded as an intermittent CI failure. |

# Lessons Learned

- Windows PowerShell cannot launch the repository Playwright config's POSIX `exec` web-server commands. A temporary local config used already-running services and was removed after testing.
- The browser origin must match the Web app's configured `SHIFU_WEB_APP_URL` for Better Auth's same-origin checks.
- A screenshot proves visual composition only; it does not prove server behavior or auth persistence.
- A Sonar Quality Gate can fail on new-code coverage even when the general unit suite passes; query its per-file measures, add behavioral tests, and verify the next PR head.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; HEAD `ae52f4af`, PR [#65](https://github.com/CtrI-Alt-Del/shifu/pull/65). |
| Completed | Approved Spec revision 1, landing implementation, all scoped local checks, full PR CI with 426/426 integration tests on rerun, Sonar Quality Gate at 81.6%, user landing approval, visual review, and authorized diagnostic-file cleanup with repaired Learning Spec links. |
| Unfinished | PR merge and any separate decision about the pre-existing app-wide CSRF warning. |
| Uncommitted work | Keep the user-provided `?? SHIFU-121-plano-de-implementacao.md` uncommitted. All task files and the authorized Markdown cleanup are committed. |
| Active processes | Local Identity API, Vite and proxy remain running for review. Stop only confirmed task-owned processes after delivery. Shared Docker services remain running. |
| Blockers | None for this PR. The existing TanStack CSRF warning and unrelated Studio hook warnings remain documented and outside this feature's scope. |
| Next action | Review and merge PR #65 when ready. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Identity RP-12 / JN-12 | RF-01–RF-05 / CA-01–CA-06 | EV-02–EV-12; user approved the landing presentation; PR #65 CI passed on HEAD `ae52f4af` | implemented; PR is open and all required checks pass. Remote `main` is incorporated. Merge remains pending. |

| Field | Result |
| --- | --- |
| Publication | PR [#65](https://github.com/CtrI-Alt-Del/shifu/pull/65) is open. CI on HEAD `ae52f4af` passed after rerunning the failed integration job. Merge is pending. |
| Source verification | Identity PRD content `83001345`, version 6; retrieved 2026-11-22. |
| Documentation Alignment | No Jira or Confluence writes authorized or made. |
| Revision History | Spec revision 1 approved; no contract amendment. |
| Limitations | The pre-existing TanStack Start CSRF middleware warning remains unresolved because it is app-wide and outside the approved feature scope. The repository-wide commit hook reports unrelated Studio warnings; scoped Web lint and all PR checks pass. The user manually approved the landing presentation. |
