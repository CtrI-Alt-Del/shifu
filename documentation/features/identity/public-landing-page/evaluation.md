---
title: Public landing page evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-23
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Implemented; CA-01 through CA-06 have code and focused coverage. |
| Automated checks | On the merged head, CI-01 passed 14/14. CI-02 passed 30/30. CI-03 type, lint/complexity, architecture and build passed. |
| Type / lint / complexity | TypeScript and Web Biome gates passed. Biome includes configured complexity rules; no quantitative complexity runner is configured. |
| Manual checks | User approved the landing page presentation. Authenticated entry is covered by CI-01. |
| Visual checks | VM-02 passed from current desktop, full-page, mobile and 320 px captures. No matching Penpot board exists. |
| Independent review | Spec review passed revision 1. Visual review passed. Implementation review confirms the auth fix and proxy isolation, and flags the existing TanStack Start CSRF warning. |
| Blockers | Existing app-wide CSRF warning needs a scope decision. `gh auth status` reports an invalid GitHub token. |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; task commit `7513dda2`, plus merge of `origin/main` at `eaaaf5fe`. |

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

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | `delivery_issue` did not distinguish absent pending context from an Identity outage. CA-01/CA-03. | High | CI-01, CI-03 | Resolved: check for cookie-name presence only, validate signed/stored context server-side, return unavailable on Identity failure. CI-01 14/14 passed on merged head. |
| ACH-02 | A global proxy outage scenario could affect concurrent tests. Initial browser harness also used `127.0.0.1` while Better Auth expected `localhost`, rejecting auth requests. | Medium | CI-01 | Resolved: scope outage by pending handle and use the configured origin. CI-01 14/14 passed. |
| ACH-03 | TanStack Start dev runtime reports that server functions lack CSRF middleware. It is an existing app-wide warning outside the approved landing Spec. | Medium | Runtime warning review | Unresolved. Not disabled or hidden. Adding middleware changes server-function security globally and requires a Spec amendment. |
| ACH-04 | Removing user-authorized `SHIFU-129-diagnostico.md` left two references in the ready Learning ordering Spec. | Low | Documentation | Resolved: references now point to the existing ordering Spec; no product contract changed. |
| ACH-05 | The proxy's pending-outage scenario could leak across parallel account tests. | Medium | CI-01 | Resolved: proxy matches the pending handle in the request body and forwards that body unchanged when no fault applies. CI-01 14/14 passed. |
| ACH-06 | The repository-wide commit hook reported warnings in unrelated Studio files: two non-null assertions and two `!important` uses. It also reported a 3.7 MiB generated coverage file as informational. | Low | Commit hook | Unresolved; paths are outside SHIFU-121. The scoped Web lint gate passes without findings. |

# Lessons Learned

- Windows PowerShell cannot launch the repository Playwright config's POSIX `exec` web-server commands. A temporary local config used already-running services and was removed after testing.
- The browser origin must match the Web app's configured `SHIFU_WEB_APP_URL` for Better Auth's same-origin checks.
- A screenshot proves visual composition only; it does not prove server behavior or auth persistence.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; task commit `7513dda2` plus merge of `origin/main` at `eaaaf5fe`. |
| Completed | Approved Spec revision 1, landing implementation, 14 focused browser tests, 30 focused unit tests, static/build/architecture checks, user landing approval, visual review, and the authorized diagnostic-file cleanup with repaired Learning Spec links. |
| Unfinished | Decide how to handle the app-wide CSRF warning, reauthenticate GitHub CLI, then push and create the PR. |
| Uncommitted work | Keep the user-provided `?? SHIFU-121-plano-de-implementacao.md` uncommitted. All task files and the authorized Markdown cleanup are committed. |
| Active processes | Local Identity API, Vite and proxy remain running for review. Stop only confirmed task-owned processes after delivery. Shared Docker services remain running. |
| Blockers | Existing TanStack CSRF warning and invalid GitHub CLI token. The commit hook also reported unrelated Studio warnings. |
| Next action | Get a scope decision for app-wide CSRF hardening, restore `gh` authentication, push the branch and publish the PR. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Identity RP-12 / JN-12 | RF-01–RF-05 / CA-01–CA-06 | EV-02–EV-09; user approved the landing presentation | implemented_locally; publication pending warning disposition and valid GitHub CLI authentication. Remote `main` is incorporated. |

| Field | Result |
| --- | --- |
| Publication | User approved the landing and authorized the PR. It has not been published. |
| Source verification | Identity PRD content `83001345`, version 6; retrieved 2026-11-22. |
| Documentation Alignment | No Jira or Confluence writes authorized or made. |
| Revision History | Spec revision 1 approved; no contract amendment. |
| Limitations | CI-01, CI-02 and CI-03 passed locally on the merged head. The TanStack Start CSRF middleware warning remains unresolved because it is app-wide and outside the approved feature scope. The commit hook also reported unrelated Studio warnings. Authenticated paths passed automated validation; the user manually approved the landing presentation. |
