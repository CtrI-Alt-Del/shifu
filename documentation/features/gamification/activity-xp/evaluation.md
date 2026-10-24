---
title: Activity XP grants and the Activity result reward band evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-23
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for RF-01..RF-09. Server (core, database, migration, messaging, REST) and web (types, service, reward band widget/hooks, result-page slot, route) all implemented per the Technical Contract |
| Automated checks | CI-01 through CI-08 passed. CI-09 written but unexecuted (webServer boot blocked, see Blockers). CI-10/CI-11 passed for all server/web unit, controller, job and static checks reachable in this environment |
| Type / lint / complexity | Server: `ruff check`, `ruff format --check`, `basedpyright` all pass repo-wide. Web: `tsc --noEmit` and `biome check` pass on every touched file. No dedicated complexity command exists on either side (per CI-10 disposition); Ruff C90 / Biome complexity rules raised nothing |
| Manual checks | Not started (VM-01 requires a real Playwright/browser journey against a running stack) |
| Visual checks | Not started (VM-02 depends on VM-01's captures) |
| Independent review | Not performed in this session |
| Blockers | Web `check:architecture` Blocked — local Node is v25.2.1, dependency-cruiser requires ^22\|\|^24\|\|>=26 (pre-existing environment mismatch, not caused by this change). CI-09/VM-01/VM-02 Blocked — the Playwright `webServer` (uvicorn) fails to boot locally: `EnvironmentSettings` requires `communication_encryption_keys`, not supplied by the current shell/`.env.local` combination used by `playwright.config.ts`'s spawned process |
| Candidate | Branch `feat/shifu-84`, working tree (uncommitted); diff spans `apps/server` and `apps/web` per the Spec's expected file tree |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01, CI-05 | None |
| CA-02 | RF-01 | Complete | Passed | CI-03, CI-04 | None |
| CA-03 | RF-02 | Complete | Passed | CI-01 | None |
| CA-04 | RF-02 | Complete | Passed | CI-01 | None |
| CA-05 | RF-02 | Complete | Passed | CI-01 | None |
| CA-06 | RF-02, RF-03 | Complete | Passed | CI-01 | None |
| CA-07 | RF-03 | Complete | Passed | CI-01, CI-06 | None |
| CA-08 | RF-03 | Complete | Passed | CI-01 | Covered implicitly: the balance is keyed only by `(account_id, activity_id)`, never by Objetivo/Habilidade, so removal of either is a no-op by construction. No dedicated test asserts removal explicitly |
| CA-09 | RF-03 | Complete | Passed | CI-01 | None |
| CA-10 | RF-04 | Complete | Passed | CI-01, CI-11 | Full Gamification use-case suite (182 tests) passes unedited, including achievement/level cascade tests |
| CA-11 | RF-01, RF-05 | Complete | Passed | CI-05, CI-06 | `test_recognize_practice_day_on_activity_evaluated_job.py` passes unedited; fan-out test confirms both consumers fire independently from one event |
| CA-12 | RF-04, RF-05 | Complete | Passed | CI-01, CI-06 | None |
| CA-13 | RF-05 | Complete | Passed | CI-01, CI-05 | None |
| CA-14 | RF-05 | Complete | Passed | CI-06 | Concurrency test exercises the no-balance-yet race (abort + Inngest retry) and confirms the final `granted_xp` sums correctly and never exceeds the maximum |
| CA-15 | RF-06 | Complete | Passed | CI-03, CI-04, CI-07, CI-09, VM-01 | CI-09 written, not executed (Blocked); VM-01 not started |
| CA-16 | RF-06, RF-08 | Complete | Passed | CI-04 | None |
| CA-17 | RF-07 | Complete | Passed | CI-03, CI-07, CI-08, CI-09, VM-01 | CI-09/VM-01 Blocked as above |
| CA-18 | RF-08 | Complete | Passed | CI-04, CI-07 | None |
| CA-19 | RF-08 | Complete | Passed | CI-02, CI-06 | None |
| CA-20 | RF-09 | Complete | Partial | CI-07, VM-01, VM-02 | Automated keyboard/structure assertions not written as a dedicated case beyond the component test's role/text queries; narrow-viewport and real keyboard-tab-order proof needs VM-01/VM-02, Blocked |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01,03,04,05,06,07,08,09,10,12,13 | Passed | `feat/shifu-84` working tree, 2026-10-23, mocked ports | `cd apps/server && uv run pytest tests/gamification/core/use_cases/test_recognize_activity_evaluated_use_case.py` | 19 tests passed |
| EV-02 | CI-02 / Automated / CA-19 | Passed | same | `cd apps/server && uv run pytest tests/gamification/core/use_cases/test_delete_gamification_profile_use_case.py` plus `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/gamification/test_purge_profile_on_account_deleted_job.py` | Use-case test extended (2 tests); real-Inngest purge test extended and passed (1 test), real Postgres via Testcontainers |
| EV-03 | CI-03 / Automated / CA-02,15,17 | Passed | same | `cd apps/server && uv run pytest tests/gamification/core/use_cases/test_get_activity_xp_reward_use_case.py` | 7 tests passed |
| EV-04 | CI-04 / Automated / CA-02,15,16,18 | Passed | same, real PostgreSQL via Testcontainers, real Alembic migrations | `cd apps/server && uv run pytest tests/gamification/server/controllers/test_get_activity_xp_reward_controller.py` | 6 tests passed; migration `fdae74f2bef2` applied cleanly on top of head `23653c3a7833` |
| EV-05 | CI-05 / Automated / CA-01,11,13 | Passed | same, disposable Inngest+Postgres via Testcontainers | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/gamification/test_recognize_activity_xp_on_activity_evaluated_job.py` | 6 tests passed, incl. duplicate-delivery idempotency and non-retriable invalid-payload cases |
| EV-06 | CI-06 / Automated / CA-07,11,12,14 | Passed | same | Same file as EV-05, fan-out and concurrency cases; plus `test_recognize_practice_day_on_activity_evaluated_job.py` run alongside (4 tests, unedited) | Concurrency test confirms the no-balance race settles at `granted_xp=24` via commit-abort-and-retry, matching the deterministic total regardless of delivery order |
| EV-07 | CI-10 / Automated baseline / — | Passed | same | `cd apps/server && uv run poe check:lint` (ruff check + format), `uv run poe check:types` (basedpyright), `uv run poe check:architecture` (tach) | All pass repo-wide; Tach confirms Gamification still imports only `shifu.shared` |
| EV-08 | CI-11 / Automated / CA-10 | Passed | same | `cd apps/server && uv run pytest tests/gamification` | 182 tests passed (full Gamification use-case, controller and page-adjacent suite) |
| EV-09 | CI-07 / Automated / CA-15,17,18,20 | Passed | web, jsdom via Vitest | `pnpm exec vitest run src/ui/gamification/widgets/components/activity-xp-reward-band src/ui/learning/widgets/pages/choice-result-page` | 39 tests passed across band component test (new), band hook test (new) and extended `choice-result-page.test.tsx` |
| EV-10 | CI-08 / Automated / CA-17 | Passed | web, jsdom via Vitest | Same command as EV-09 | Covered by `use-activity-xp-reward-band.test.ts`'s 7 cases, included in EV-09's 39 |
| EV-11 | Web types/lint baseline / — | Passed | web | `pnpm check:types` (tsc), `pnpm exec biome check <changed files>` | Both pass on every touched/created file |
| EV-12 | Web architecture baseline / — | Blocked | web, Node v25.2.1 | `pnpm --filter web check:architecture` | dependency-cruiser requires Node ^22\|\|^24\|\|>=26; local Node is v25.2.1. Pre-existing environment mismatch, not caused by this change. Not re-attempted with a different Node version |
| EV-13 | CI-09 / Automated / CA-15,17 | Blocked | web, Playwright | `pnpm exec playwright test tests/learning/choice-result-page.test.ts -g "Activity XP reward band integration"` | Test cases written (2, mirroring `serverFnExport` pattern). Playwright's `webServer` spawn of the server app fails: `pydantic_core.ValidationError: Communication encryption keys are required`. The spawned uvicorn process does not inherit `.env.local`; requires local secrets/config this session does not have authority to fabricate |
| EV-14 | VM-01, VM-02 / Manual, Visual / CA-15,17,20 | Blocked | — | Playwright CLI manual journey per the Spec | Not started; depends on the same local stack boot as EV-13 |

# Findings

None recorded. No independent Implementation Reviewer or Visual Reviewer pass has run yet.

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| None | — | No reusable lesson beyond this feature's own scope |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | Branch `feat/shifu-84`, uncommitted working tree. 49 changed/created paths spanning `apps/server` and `apps/web`, matching the Spec's Expected file tree exactly |
| Completed | All server and web production code and all automated unit/component/controller/job tests (CI-01 through CI-08, CI-10, CI-11). Server static checks (lint, types, architecture) and web static checks (types, lint) pass |
| Unfinished | CI-09 (Playwright integration), VM-01 (manual journey), VM-02 (narrow-viewport visual) — all Blocked by local environment, not by missing code. Web `check:architecture` Blocked by local Node version. Independent Implementation/Visual review not yet run |
| Uncommitted work | Everything listed above is uncommitted on `feat/shifu-84`; no other unrelated uncommitted work exists on this branch to preserve |
| Active processes | None left running. The Playwright webServer attempt failed at boot and did not leave a process behind |
| Blockers | (1) Local Node v25.2.1 vs dependency-cruiser's required range for `check:architecture`. (2) Local `.env.local`/shell does not supply `communication_encryption_keys` (and possibly other secrets) to the process Playwright's `webServer` config spawns, so the real stack cannot boot for CI-09/VM-01/VM-02 in this environment |
| Next action | Resolve the two environment blockers (Node version for dependency-cruiser; communication encryption keys for the Playwright-spawned server app), then run CI-09, VM-01, VM-02, and the independent Implementation/Visual review before setting Spec to `implemented` |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-02 | RF-01..RF-09; CA-01..CA-19 | EV-01..EV-11 | implemented |
| RP-09, RP-13 | RF-06, RF-07, RF-09; CA-15, CA-17, CA-20 | EV-09, EV-10 | partially_implemented — automated coverage complete; manual/visual narrow-viewport and keyboard-journey proof (VM-01, VM-02) outstanding, Blocked by local environment |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| Not opened | — | — | — |

| Field | Result |
| --- | --- |
| Publication | Not requested; local-only |
| Source verification | Not re-checked this session; Spec's own Documentation Alignment table was accepted as current at kickoff |
| Documentation Alignment | No sibling Spec (`achievements`, `practice-calendar`, `xp-history`) required edits; their non-regression is proven by EV-08's unedited 182-test pass |
| Revision History | No contract change; Spec stays at revision 1 |
| Limitations | CI-09, VM-01, VM-02 and the web architecture baseline are Blocked by local environment configuration, not by code defects. No PR opened; nothing pushed; nothing committed per standing instruction not to commit without explicit request |
