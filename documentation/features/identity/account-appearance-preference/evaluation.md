---
title: Preferência de aparência da conta evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-11-21
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01..CA-15 on the uncommitted candidate |
| Automated checks | 15/15 contracted checks passed (EV-01..EV-15) |
| Type / lint / complexity | Types passed web and server (EV-11); lint and complexity lint passed on changed paths (EV-12); no metrics gate required |
| Manual checks | 2/2 passed (EV-16) |
| Visual checks | VM-05 passed (EV-17); VM-03, VM-04 Blocked: no Penpot, assumption accepted by the user |
| Independent review | Spec Reviewer completed. Implementation Reviewer completed: PASS, 2 medium and 5 low findings, all resolved or recorded (ACH-05..ACH-11). Visual Reviewer not run: it requires Penpot exports, which do not exist for this delivery |
| Blockers | VM-03, VM-04 (no Penpot) |
| Candidate | `feat/shifu-119` at d34bf5b3 (commits eab707d5, b8be2593, 1b9df13d and the merge of `origin/main` 7f83855a), published as PR #59; Spec revision 2 |

Penpot gate deviation: `implement-spec` stops UI work while Penpot is unreachable.
The user stated that no Penpot exists for this delivery and accepted the Spec's
visual assumption, so UI work proceeded from `design.md` §3.2 and the existing
Perfil field pattern. No visual match with Penpot is claimed.

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-03 / EV-01 | — |
| CA-02 | RF-01 | Complete | Passed | CI-06 / EV-05 | — |
| CA-03 | RF-02, RF-03, RF-04 | Complete | Passed | CI-01, CI-04 / EV-01, EV-02 | — |
| CA-04 | RF-03 | Complete | Passed | CI-01, CI-04 / EV-01, EV-02 | — |
| CA-05 | RF-02 | Complete | Passed | CI-01, CI-02, CI-04 / EV-01, EV-02 | — |
| CA-06 | RF-04 | Complete | Passed | CI-02, CI-05 / EV-01, EV-02 | — |
| CA-07 | RF-03, RF-04 | Complete | Passed | CI-12 / EV-08 | — |
| CA-08 | RF-05 | Complete | Partial | CI-07, CI-10, VM-01 / EV-06, EV-07, EV-16; VM-03, VM-04 Blocked | Visual match with Penpot not provable |
| CA-09 | RF-05, RF-06 | Complete | Passed | CI-07, CI-10, VM-01, VM-02 / EV-06, EV-07, EV-16 | — |
| CA-10 | RF-06 | Complete | Passed | CI-07, CI-10 / EV-06, EV-07 | — |
| CA-11 | RF-07 | Complete | Passed | CI-08, CI-11, VM-01 / EV-06, EV-07, EV-16 | — |
| CA-12 | RF-08 | Complete | Passed | CI-11, VM-01 / EV-07, EV-16 | — |
| CA-13 | RF-09 | Complete | Passed | CI-08, CI-11 / EV-06, EV-07 | — |
| CA-14 | RF-10 | Complete | Partial | CI-08, VM-05 / EV-06, EV-17; VM-03, VM-04 Blocked | Visual match with Penpot not provable |
| CA-15 | RF-10 | Complete | Passed | CI-14, VM-05 / EV-12, EV-17 | — |

# Check Results

All results are on the uncommitted candidate over 2e322dc0, Spec revision 2,
2026-11-21. Server commands ran from `apps/server` with `AWS_PROFILE` unset and the
non-secret CI placeholder variables from `server-app-ci.yaml`. Web commands ran
with Node 24.20.0 and pnpm 10 through corepack. Browser suites and manual journeys
used disposable services: PostgreSQL `pgvector/pgvector:0.8.1-pg17` container
`shifu-119-pg` on port 55433 at Alembic head, with the AgentOS role created by
`scripts/create_agentos_runtime_role.sql`, and Redis container `shifu-119-redis`
on 56380. The task servers ran on 7877 (API) and 7100 (web). The shared
development database was never used.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01, CI-02, CI-03 / Automated / CA-01, CA-03..CA-06 | Passed | Use-case tests, autospecced ports | `uv run pytest` on `tests/identity/core/use_cases/{test_update_account_profile_use_case,test_get_account_profile_use_case,test_register_account_use_case,test_sign_in_with_pending_context_use_case}.py` and `tests/core/identity/use_cases/test_sign_in_use_case.py` (with EV-02, one run) | Part of 105 passed. The two sign-in files are affected consumers: `AccountProfile` gained a required field |
| EV-02 | CI-04, CI-05 / Automated / CA-03..CA-06 | Passed | PostgreSQL Testcontainer from `tests/conftest.py` | same run: `tests/identity/server/controllers/{test_update_account_profile_controller,test_get_account_profile_controller,test_get_current_session_controller}.py` | 105 passed in 79.7 s, 0 skipped. 2 warnings, both third-party: Starlette `anyio.abc.BlockingPortal` DeprecationWarning and pytest's note that `tests.fixtures.postgres_fixture` was imported before assertion rewriting |
| EV-03 | Builder regression sweep / Automated | Passed | Builder run, Testcontainer | `uv run pytest tests/identity tests/core/identity` | 258 passed (builder report); retained as supporting evidence only |
| EV-04 | Test integrity / Automated | Passed | Repository root | `node scripts/check-test-integrity.mjs` | 474 test files checked |
| EV-05 | CI-06 / Automated (disposable evidence) / CA-02 | Passed | `shifu-119-pg` | `DATABASE_URL=…55433/shifu uv run alembic upgrade 4316ce01866a`; insert one account; `upgrade head`; `update … set appearance='sepia'`; `downgrade -1`; `upgrade head`; `alembic check` | Existing row read `system`; `sepia` failed on `ck_identity_accounts_appearance`; after downgrade the column and constraint counts were 0; `alembic check`: no new upgrade operations. The migration `14fadc960949_add_account_appearance.py` was written by hand (autogenerate needs a database at head; the constraint must be hand-added anyway) |
| EV-06 | CI-07, CI-08, CI-09 / Automated / CA-08..CA-11, CA-13, CA-14 | Passed | Vitest/jsdom | `pnpm --filter web exec vitest run src/ui/shared/widgets/layouts/root-layout/tests src/ui/shared/widgets/layouts/app-layout src/ui/identity/widgets/pages/account-profile-page src/ui/shared/contexts/auth-context` | 15 files, 97 tests passed. Includes the profile form (24 tests), root layout and the consumers whose fixtures gained `appearance` (account menu, app layout, account profile page, auth context). Two jsdom "navigation to another Document" notices come from existing account-menu sign-out tests |
| EV-07 | CI-10, CI-11 / Automated (browser, mocked transport) / CA-08..CA-13 | Passed | Chromium, task ports | `pnpm exec playwright test tests/shared/root-layout.test.ts tests/identity/account-profile-page.test.ts` from `apps/web` | 26 passed in 1.0 min (5 new). Web-server log noise is pre-existing: TanStack CSRF advisory, route-file warnings for two test files under `src/routes`, `ECONNRESET` on aborted requests |
| EV-08 | CI-12 / Automated (real services) / CA-07 | Passed | Real FastAPI and BFF, disposable DB; `SHIFU_AUTH_JWKS_URL` set to the task web port | `pnpm exec playwright test tests/identity/account-auth-api.test.ts` | 10 passed. First attempt failed 10/10 with 401 because the API's JWKS URL defaulted to port 7000; corrected the environment only |
| EV-09 | Affected consumers of changed sign-in/confirmation use cases / Automated (real services) | Passed | Same environment | `pnpm exec playwright test tests/identity/sign-in-auth-api.test.ts tests/identity/register-confirmation-auth-api.test.ts` | 10 passed |
| EV-10 | Mentor action card consumers / Automated | Passed | Vitest | `vitest run src/ui/intelligence/widgets/components/mentor-action-card src/ui/intelligence/widgets/components/mentor-chat/conversation/message-list/skill-action-card` | 3 files, 58 passed, after replacing the result `div[role=status]` with `<output>` to clear a lint warning in a touched file |
| EV-11 | CI-13 / Automated / types | Passed | — | `pnpm --filter web check:types`; `uv run poe check:types` | Web `tsc` 0 errors; basedpyright 0 errors, 0 warnings, 0 notes |
| EV-12 | CI-14 / Automated / lint, format, complexity lint / CA-15 | Passed | — | `pnpm exec biome check <48 changed web paths>`; `uv run ruff check --no-fix` and `ruff format --check` on 27 changed Python paths; source search for fixed colors | Biome: 0 errors, 0 warnings on changed paths. Ruff: all passed, C90 included. Fixed-color search: only the accepted exceptions remain (previews, scrims, white text on fills, unreachable catalog). No dedicated complexity metrics gate exists or is required |
| EV-13 | CI-15 / Automated / web gates | Passed with pre-existing findings | — | `pnpm --filter web check:lint`, `check:architecture`, `build` | Architecture: no violations (795 modules). Build passed. `check:lint` reports 1 warning in `skill-action-card/objective-picker/index.tsx` (not changed by this delivery). Build warnings about two test files under `src/routes` and chunk size are pre-existing |
| EV-14 | CI-15 / Automated / server gates | Passed | — | `uv run poe check:lint`, `check:architecture`, `build` | All passed |
| EV-15 | Web Vitest for changed fixtures / Automated | Passed | — | covered by EV-06 | — |
| EV-16 | VM-01, VM-02 / Manual / CA-08, CA-09, CA-11, CA-12 | Passed | Production web build (`node server.production.mjs`, `NODE_ENV=production`) on 7100 and the API on 7877 with the disposable DB; task-owned account `manual-119@shifu.local` inserted in the disposable DB | Script `apps/web/.playwright-cli/journey-shifu-119.mjs` (Playwright library; `playwright-cli` is not installed and installing it was out of scope) | 19/19 checks: initial Sistema; Claro saved by keyboard and applied without reload; POST body carried `appearance: light`; light kept after reload; raw server HTML for `/account/profile` and `/` carried `data-theme="light"`; a second browser context saw light; Sistema followed the emulated device scheme both ways; at 390 × 844 keyboard save applied dark, no horizontal overflow, field height 52 px; cleanup restored Sistema (confirmed in the DB). Console errors: 0. Earlier runs against the Vite dev server produced thousands of relayed `Failed to fetch` errors when a second context closed mid-request; that is a TanStack devtools echo in dev mode, absent in the production build |
| EV-17 | VM-05 / Visual / CA-14, CA-15 | Passed | Same run | Computed token colors in light on Perfil; control border composited over `--muted` computed from the same resolved tokens; captures `apps/web/.playwright-cli/screenshots/shifu-119-profile-{desktop-dark,desktop-light,mobile-system-light,mobile-dark}.png` | Contrast on light `--card`: foreground 16.96, muted 5.59, secondary 8.92, selo-text 6.35, jade-text 6.62, latão-text 7.59; on-selo on selo-fill 4.68; `--control-border` over light `--muted` 3.82 (dark 3.00); fills equal to dark values. Toast: no toast was rendered in the journey; the Toaster receiving the active theme is proved by EV-06 (root-layout component test), not by a captured toast. Captures show tokens applied to the tab bar, fields, primary button, cards, header and bottom navigation; no invisible border or hover surface found. The streak-reminder card error in captures is due to push not being configured in the disposable environment |
| EV-18 | VM-03, VM-04 / Visual | Blocked | — | — | No Penpot file or MCP; the user accepted the visual assumption |
| EV-19 | Review corrections / Automated | Passed | Candidate after ACH-05..ACH-09 corrections | `npx tsc --noEmit` (apps/web); `vitest run` on `mentor-action-card`, `skill-action-card`, `account-profile-page` (7 files, 91 passed); `biome check` on 52 changed web paths (0 diagnostics) | Re-runs the checks invalidated by the corrections |
| EV-21 | Post-merge recheck / Automated | Passed | d34bf5b3 after merging `origin/main` 7f83855a (PR #58, no shared surface with this delivery, no migration) | `npx tsc --noEmit` (web); `uv run poe check:types`; `uv run alembic heads`; `node scripts/check-test-integrity.mjs` | Types clean; single head `14fadc960949`; 480 test files checked. Other evidence retained: the merge touched no file of this delivery |
| EV-22 | Pre-existing flaky browser test / Automated | Passed locally | d34bf5b3, disposable services | `pnpm exec playwright test tests/learning/goal-detail-page.test.ts -g "pans the canvas" --repeat-each 3` | 3/3 passed. The same test failed on CI for this PR and earlier for `feat/shifu-124` (run 44934741213) before this delivery existed; classified as pre-existing flakiness (ACH-12) |
| EV-20 | CI-10 and affected consumer / Automated (browser, mocked transport) | Passed | Same candidate, task ports | `pnpm exec playwright test tests/shared/app-layout.test.ts tests/identity/account-profile-page.test.ts` | 47 passed in 1.1 min. `app-layout.test.ts` is a direct consumer of the changed `AccountProfile` body (ACH-05). EV-16 is retained: its journey did not exercise the field-error color or the Mentor card changed afterwards |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Mocked browser transport cannot intercept the first server render, so CI-11 could not prove CA-11's server-rendered theme | Medium (contract) | CI-11, VM-01 | Resolved: Spec revision 2 moved that proof to VM-01; EV-16 confirms raw HTML on `/` and `/account/profile` |
| ACH-02 | The BFF's strict body validation rejects an unknown appearance before Identity, so CA-07's "field error" wording was not reachable through the BFF | Low (contract) | CI-12 | Resolved: Spec revision 2 restates CA-07; EV-08 passes |
| ACH-03 | `mentor-action-card` (touched) carried a Biome `useSemanticElements` warning | Low | CI-14 | Resolved: result region is now `<output>`; EV-10, EV-12 |
| ACH-04 | Pre-existing warnings outside the diff: Biome warning in `objective-picker`, build warnings for test files under `src/routes`, third-party pytest warnings | Low | EV-02, EV-13 | Open, out of scope; recorded, not hidden |
| ACH-05 | Implementation Reviewer: two `GET /api/auth/account` mocks in `apps/web/tests/shared/app-layout.test.ts` returned the old 4-key body, which the browser provider now rejects | Medium | EV-20 | Resolved: mocks include `appearance`; suite run (EV-20) |
| ACH-06 | Implementation Reviewer: EV-17 lacked the control-border ratio and the toast observation | Medium | EV-17 | Resolved: ratio recorded (3.82); toast recorded as proved by EV-06 only, not by a captured toast |
| ACH-07 | Implementation Reviewer: `.border-glow` halo and mesh in `global.css` use fixed white glow on the planning-intent field | Low | EV-12, EV-17 | Classified as an accepted decorative exception: the animated rainbow border and its glow are ornaments that do not delimit the control or carry text, as design.md §3.2/§8 allow for decorative layers. No change |
| ACH-08 | Implementation Reviewer: appearance field error used `text-muted-foreground` instead of the Design Contract's `text-selo-text` | Low | EV-19, EV-20 | Resolved: help text switches to `text-selo-text` while an error is shown |
| ACH-09 | Implementation Reviewer: `<output>` in `mentor-action-card` wrapped `<p>` (invalid phrasing content) | Low | EV-19 | Resolved: children are `<span class="block">` |
| ACH-10 | Implementation Reviewer: the BFF fallback to `appearance: 'system'` when Identity is unavailable has no direct test | Low | — | Recorded: CI-08 proves the layout fallback; provider tests are forbidden by the Rules, and the existing outage suite asserts the menu, not the theme. No change |
| ACH-12 | CI run 44957823779, job 137009739973 (Web integration tests): `tests/learning/goal-detail-page.test.ts:82` expected the restored graph transform `translate(2.97938px, …)` and received `translate(52.9794px, …)` | Low | EV-22 | Pre-existing flaky test outside the diff (same failure on `feat/shifu-124` run 44934741213; passes 3/3 locally). Not fixed in this delivery |
| ACH-11 | Implementation Reviewer: consumer updates outside the Spec tree and the journey script location | Low | — | Resolved: paths listed in Handoff; scripts moved to `apps/web/.playwright-cli/logs/` |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Mocked browser suites prove client route loads only; first server render needs a real request | ACH-01, EV-16 | Proposal: mention it in `widget-testing-rules.md` when a later delivery touches that rule |
| Real-service browser suites on non-default ports also need `SHIFU_AUTH_JWKS_URL` | EV-08 | Proposal for `tooling.md`; not changed in this delivery |
| Manual journeys with several browser contexts should run against the production build | EV-16 | Proposal for `tooling.md`; not changed in this delivery |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-119` published as PR #59 |
| Completed | All CA implemented; EV-01..EV-17 passed |
| Unfinished | VM-03, VM-04 Blocked (no Penpot); Evaluation cannot become `ready` while they are Blocked |
| Uncommitted work | None. Delivery paths are committed; consumer updates outside the Spec tree are listed in ACH-11 and the commits. Ignored local artifacts: `apps/web/.playwright-cli/{logs,screenshots}`, `apps/server/dist`, `apps/web/dist`, `node_modules` |
| Active processes | None. Task API (7877), web (7100) and containers `shifu-119-pg`, `shifu-119-redis` were stopped; ports confirmed free |
| Blockers | VM-03, VM-04 (no Penpot) |
| Next action | Follow CI on the PR head; VM-03/VM-04 stay Blocked unless a Penpot reference appears |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-06 | RF-01..RF-10 / CA-01..CA-15 | EV-01..EV-20 | partially_implemented: appearance behavior implemented and verified; visual match with Penpot not provable (VM-03, VM-04 Blocked) |
| RP-07 | RF-01, RF-02, RF-04, RF-07 | EV-01, EV-02, EV-08, EV-16 | implemented for the appearance slice |
| RP-10 | RF-05, RF-10 | EV-06, EV-07, EV-16, EV-17, EV-20 | implemented for the touched screens; Penpot comparison Blocked |

| PR | Current head SHA | Review state |
| --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/59 | the docs commit that follows d34bf5b3 | No review yet |

| Field | Result |
| --- | --- |
| Publication | Published: https://github.com/CtrI-Alt-Del/shifu/pull/59 (base `main`). Not complete: VM-03/VM-04 Blocked |
| Source verification | PRD Identity 83001345 v6, retrieved 2026-11-21 |
| Documentation Alignment | No external write; no repository authority changed |
| Revision History | Revision 2: verification boundary for CA-11 and CA-07 wording |
| Limitations | No Penpot reference (VM-03, VM-04 Blocked); manual journey used a Playwright script instead of `playwright-cli` |
