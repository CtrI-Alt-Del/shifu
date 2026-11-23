---
title: Public landing page evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-23
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Implemented locally; CA-01 through CA-06 have code and focused coverage. |
| Automated checks | CI-01 passed: landing/root-layout 11/11 and affected confirmation API 3/3. CI-02 passed 30/30. CI-03 type, lint/complexity, architecture and build checks passed. |
| Type / lint / complexity | TypeScript and Biome passed. Biome includes configured complexity rules; no quantitative complexity runner is configured. |
| Manual checks | User approved the landing page. The separate authenticated entry remains covered by CI-01. |
| Visual checks | VM-02 passed from current desktop, full-page, mobile and 320 px browser captures. No matching Penpot board exists. |
| Independent review | Spec review passed revision 1. Implementation review confirms the pending-context fix and proxy isolation; it still flags the existing TanStack Start CSRF warning. Visual review passed. |
| Blockers | The dev runtime reports TanStack Start's existing server-function CSRF middleware warning. Resolving it would expand the approved auth/security contract. GitHub CLI authentication is currently invalid. |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; implementation and requested manual landing review approved. |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Done | Passed | CI-01; visitor route, `private, no-store`, public shell and no private requests. | None. |
| CA-02 | RF-01/RF-05 | Done | Passed | CI-01; active root/HomePage and root-layout navigation. | None. |
| CA-03 | RF-01 | Done | Passed | CI-01; valid, invalid/expired, rejected-session and unavailable-Identity paths. | None. |
| CA-04 | RF-02/RF-03 | Done | Passed | CI-01, CI-02, VM-01/VM-02; pt-BR copy, destinations, MVP/future labels and illustrative preview. | None. |
| CA-05 | RF-04 | Done | Passed | CI-01, CI-02, VM-01/VM-02; 320 px overflow, CTA visibility, reduced motion, focus and touch targets. | None. |
| CA-06 | RF-05 | Done | Passed | CI-01; no private calls or external origins; root response cache is private. | None. |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | Spec review / all | Passed | Spec revision 1; 2026-11-22 | Read-only `public_landing_spec_reviewer`; repository root | No blocking findings after focused contract updates. |
| EV-02 | CI-01 / Automated / CA-01–CA-06 | Passed | Current branch; 2026-11-23; local Chrome, Vite, Identity API, controlled proxy and PostgreSQL; browser origin matches `.env.local` (`localhost`) | `playwright.cmd test --config=playwright.local.config.ts tests/identity/landing-page.test.ts tests/shared/root-layout.test.ts`; `apps/web` | 11/11 passed in 26.2s. A temporary local config supplied existing services because the repository's POSIX `exec` web-server commands cannot launch under Windows PowerShell; the temp file was removed after testing. |
| EV-02a | Confirmation BFF regression / Automated / CA-03 | Passed | Current branch; 2026-11-23; same local services | `playwright.cmd test --config=playwright.local.config.ts tests/identity/register-confirmation-auth-api.test.ts`; `apps/web` | 3/3 passed, including sign-out of pending verification context. |
| EV-03 | CI-02 / Automated / CA-04–CA-05 and root-layout | Passed | Current branch; 2026-11-23; Vitest 4.1.6 | `.\node_modules\.bin\vitest.cmd run src\ui\identity\widgets\pages\landing-page\tests\landing-page.test.tsx src\ui\identity\widgets\pages\landing-page\tests\use-landing-page.test.ts src\ui\shared\widgets\layouts\root-layout\tests\root-layout.test.tsx src\ui\shared\widgets\layouts\root-layout\tests\use-root-layout.test.ts`; `apps/web` | 4 files, 30 tests passed. |
| EV-04 | CI-03 types / static / all | Passed | Current branch; 2026-11-23; Web | `.\node_modules\.bin\tsc.cmd --noEmit`; `apps/web` | Exit 0 after the latest changes. |
| EV-05 | CI-03 lint and configured complexity / static / all | Passed | Current branch; 2026-11-23; repository | `.\node_modules\.bin\biome.cmd check apps/web/src apps/web/tests apps/web/vitest.config.ts apps/web/playwright.config.ts apps/web/dependency-cruiser.config.cjs`; repository root | 879 files checked with no findings. Complexity rules run through Biome; no separate numeric complexity checker is configured. |
| EV-06 | CI-03 architecture / static / changed Web | Passed | Current branch; 2026-11-22; Web | `depcruise --config dependency-cruiser.config.cjs src`; `apps/web` | 869 modules and 3519 dependencies; no architecture violations. |
| EV-07 | CI-03 production build / static / all | Passed | Current branch; 2026-11-22; Web | `vite build`; `apps/web` | Build succeeded. Rolldown plugin timing output was informational. |
| EV-08 | VM-01 / Manual / CA-01–CA-04, CA-06 | Passed for the requested landing review | Current landing; 2026-11-23 | User reviewed the desktop landing capture and approved the page; local route is `http://localhost:7000/` | Manual approval covers the landing presentation only. Authenticated and pending account paths are covered by CI-01. |
| EV-09 | VM-02 / Visual / CA-04–CA-05 | Passed | Current branch; 2026-11-23; fresh Playwright captures | Visual review of `landing-desktop-fold.png`, `landing-desktop.png`, `landing-mobile.png`, `landing-320.png`; `apps/web/.playwright-cli/screenshots/` | Independent visual reviewer passed. Desktop hierarchy and responsive 390/320 px compositions have no material findings. No matching Penpot board; no Penpot comparison claimed. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | `delivery_issue` previously did not distinguish absent pending context from an Identity outage. CA-01/CA-03. | High | CI-01, CI-03 | Resolved: check for cookie-name presence only, validate signed/stored context server-side, return unavailable on Identity failure. CI-01 11/11 passed. |
| ACH-02 | A proxy outage scenario was global, and the first local browser harness used `127.0.0.1` while Better Auth was configured for `localhost`; concurrent tests could be affected and cross-origin login was rejected. | Medium | CI-01 | Resolved: scope outage scenario to the pending handle and use the configured `localhost` origin. CI-01 11/11 and confirmation BFF 3/3 passed. |
| ACH-03 | TanStack Start dev runtime reports that server functions lack CSRF middleware. It is an existing app-wide warning outside the approved landing Spec. | Medium | Runtime warning review | Unresolved. Not disabled or hidden. Adding middleware would affect server-function security globally and requires a Spec amendment. |
| ACH-04 | Removing user-authorized `SHIFU-129-diagnostico.md` left two references in the ready Learning ordering Spec. | Low | Documentation | Resolved: references now point to the existing ordering Spec; no product contract changed. |
| ACH-05 | Unscoped outage test scenario could leak across concurrent account tests. | Medium | CI-01 | Resolved: proxy matches the pending handle in the request body; the request body is replayed unchanged to the upstream when no fault applies. CI-01 11/11 passed. |

# Lessons Learned

- On Windows, the repository Playwright config's POSIX `exec` web-server command cannot launch. A temporary local-only config was used with existing services, then removed. The supported CI command remains unchanged.
- A passing screenshot is visual evidence only; it does not prove authenticated persistence or server behavior.

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/web/SHIFU-121-public-landing-page`; implemented locally, awaiting user review. |
| Completed | Approved Spec revision 1, landing implementation, focused unit/static/build/architecture checks, fresh visual review, and the authorized diagnostic-file cleanup with repaired Learning Spec links. |
| Unfinished | Resolve or explicitly retain the app-wide CSRF warning, finish warning review, commit the authorized changes, synchronize with remote `main`, then publish the PR. |
| Uncommitted work | User explicitly authorized including the pre-existing deletion of `SHIFU-129-diagnostico.md` in the task commit and describing it as cleanup in the PR. Keep `?? SHIFU-121-plano-de-implementacao.md` uncommitted. |
| Active processes | Local Identity API, Vite and proxy remain running for review; stop only confirmed task-owned processes after delivery. Shared Docker services remain running. |
| Blockers | Existing TanStack CSRF runtime warning remains outside scope. `gh auth status` reports an invalid GitHub token, so PR publication may require reauthentication. |
| Next action | Address the warning scope, commit the approved task paths, fetch/merge remote `main`, rerun checks affected by the merge, then publish the PR with `gh`. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Identity RP-12 / JN-12 | RF-01–RF-05 / CA-01–CA-06 | EV-02–EV-09; visual landing approved by user | implemented_locally; publication remains pending CSRF warning disposition, remote synchronization, and valid GitHub CLI authentication. |

| Field | Result |
| --- | --- |
| Publication | User approved the landing and authorized the PR. Not yet published. |
| Source verification | Identity PRD content `83001345`, version 6; retrieved 2026-11-22. |
| Documentation Alignment | No Jira or Confluence writes authorized or made. |
| Revision History | Spec revision 1 approved; no contract amendment. |
| Limitations | CI-01 and the affected confirmation BFF suite passed locally. The TanStack Start CSRF middleware warning remains unresolved because it is app-wide and outside the approved feature scope. The authenticated CI-01 flow passed automated validation; user manual approval covered the landing presentation. |
