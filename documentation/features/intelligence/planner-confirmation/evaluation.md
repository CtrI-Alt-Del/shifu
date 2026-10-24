---
title: Goal Planner confirmation evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-20
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01 … CA-12 (spec revision 1) |
| Automated checks | 7 / 7 passed: server use cases and confirm route (25 tests over Postgres + Redis), server changed-file coverage, Vitest scope (61 files, 407 tests), web CI coverage run (29 files, 296 + 8 tests) with the changed-file gate green for 11 / 11 files, browser suites (51 scenarios, 6 of them for the confirmation), server and web baseline checks |
| Type / lint / complexity | Server: `ruff format --check`, `ruff check`, `basedpyright` (whole tree) and `poe check:architecture` clean. Web: `tsc --noEmit` clean, `biome check` clean on the delivery (7 pre-existing Mentor warnings), `depcruise` 508 modules without violations |
| Manual checks | 0 / 1: VM-01 not run against the real model (`OPENROUTER_API_KEY` absent); the confirm route itself runs against the real Learning tables in CI-02 (EV-08) |
| Visual checks | 4 / 4 frames compared (EV-09) |
| Independent review | Pending (pull request review) |
| Blockers | None for the delivery; the inherited SHIFU-91 CI finding on `test_should_discard_a_late_result_of_a_restarted_generation` stays open in `../planner-goal-flow/evaluation.md` (ACH-06) |
| Candidate | Branch `feat/shifu-95` on top of `feat/shifu-93` (PR #35, `e26cc61`): `98fcac2` feature, `d891e89` docs; PR #36 |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-03 | Complete | Passed | CI-01 (EV-01 use cases), CI-02 (EV-02 rows asserted in Postgres, Redis planning removed) | None |
| CA-02 | RF-01 | Complete | Passed | CI-02 (EV-02 `422` for a tampered body) | None |
| CA-03 | RF-02 | Complete | Passed | CI-01 (EV-01 gap and unknown Skill), CI-02 (EV-02 graph-only seed Skill) | None |
| CA-04 | RF-02 | Complete | Passed | CI-01 (EV-01 six invalid shapes, no transaction) | None |
| CA-05 | RF-04, RF-05 | Complete | Passed | CI-01 (EV-01 replay), CI-02 (EV-02 same key after the planning is gone) | None |
| CA-06 | RF-04 | Complete | Passed | CI-01, CI-02 (`409` with another title) | None |
| CA-07 | RF-05, RF-06 | Complete | Passed | CI-01 (EV-01 recovery, not found, conflicts), CI-02 (`404`, `409`) | None |
| CA-08 | RF-07, RF-10 | Complete | Passed | CI-03 (EV-03 page hook success path, review frozen state), CI-04 (EV-05 scenario 1 with the held response and the Goal page), VM-02 | None |
| CA-09 | RF-08 | Complete | Passed | CI-03 (EV-03 refusal with reason, labels), CI-04 (EV-05 scenario 2: three requests, one key), VM-02 | None |
| CA-10 | RF-09 | Complete | Passed | CI-03 (EV-03 uncertain then replay), CI-04 (EV-05 scenario 3) | None |
| CA-11 | RF-09 | Complete | Passed | CI-03 (EV-03 `404` refetches the planning) | None |
| CA-12 | RF-07, RF-08 | Complete | Passed | CI-04 (EV-05 mobile frame walk), VM-02 (`FxmF8`, `n8OPLr`) | None |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated (pytest, autospec) / CA-01, CA-03 … CA-07 | Passed | `feat/shifu-95` working tree, 2026-10-20 | `apps/server`: `uv run pytest -p no:tach -q tests/learning/core/use_cases/test_create_planned_goal_use_case.py tests/intelligence/core/use_cases/test_confirm_planning_use_case.py` | 18 passed. Learning: creation with justifications inside one transaction, replay, divergent key, six invalid shapes, curriculum gap, unknown Skill. Intelligence: stored Skills handed over with the edits, planning removed, recovery by key, not found, other account, running operation, no proposal, Learning refusal keeps the planning |
| EV-02 | CI-02 / Automated (HTTP over Testcontainers Postgres + Redis, seeded curriculum) / CA-01 … CA-03, CA-05 … CA-07 | Passed | Same candidate, `TESTCONTAINERS_RYUK_DISABLED=true` | `apps/server`: `uv run pytest -p no:tach -q tests/intelligence/server/controllers/test_confirm_planning_controller.py` | 7 passed. First run failed three cases with `curriculum_gap` because the suite seeded the curriculum without concepts (ACH-01); fixed by seeding `seed.concepts` as the adaptive journey suite does |
| EV-03 | CI-03 / Automated (Vitest) / CA-08 … CA-11 | Passed | Same candidate, jsdom | `apps/web`: `pnpm exec vitest run src/ui/intelligence src/rest src/ui/shared src/ui/learning/widgets/pages/goal-detail-page src/ui/learning/widgets/pages/goal-create-page src/routes/intelligence src/constants` | 61 files, 407 passed. New or extended: `use-planner-page.test.ts` (success navigation and Home invalidation, refusal with reason, uncertain then replay, `404` refetch, no creation outside the proposal), `planner-page.test.tsx` (frozen review, failure retry), `use-planning-proposal-review.test.ts` (stable key, labels and notices per state), `planning-proposal-review.test.tsx` (creating, failed, uncertain), `planning-server-functions.test.ts` (`confirmPlanningServer` validation, mapping and the real service call), `use-home-goals-query.test.ts` (new) |
| EV-04 | CI-03 / Coverage / all | Passed | Same candidate | `apps/web`: `vitest run --coverage` over the 29 files listed in `web-app-ci.yaml` (296 passed) then `node --experimental-strip-types apps/web/scripts/check-changed-coverage.ts --files <11 changed web files>` | Every changed production file passes 85 / 85 / 85 / 80: `use-planner-page.ts` 187 / 191 lines, `use-planning-proposal-review.ts` 49 / 49, `intelligence-service.ts` 80 / 84. The first run failed `use-home-goals-query.ts` (0 / 8) because the hook had no test in the CI list after gaining the shared key import (ACH-02); a dedicated test was added and listed |
| EV-05 | CI-04 / Automated (Playwright, mocked `_serverFn`) / CA-08 … CA-10, CA-12 | Passed | Same candidate, local FastAPI 7777 + Vite 7000 reused, Chromium 1440 × 900 and 390 × 844 | `apps/web`: `pnpm test:integration tests/intelligence/planner-page.test.ts tests/shared/home-page.test.ts tests/learning/goal-detail-page.test.ts` (`PLANNER_CAPTURE_DIR` set for the captures) | 51 passed in 1.6 min (planner 33 incl. 6 confirmation scenarios, Home 8, goal detail 10). The creating state is observed by holding the mocked response; the retry and the recovery assert that every request repeats the same confirmation key |
| EV-06 | CI-05 / Types, lint, architecture (server) / all | Passed | Same candidate | `apps/server`: `uv run ruff format --check src tests migrations`, `uv run ruff check src tests migrations`, `uv run basedpyright`, `uv run poe check:architecture` | All clean; `tach` keeps Intelligence and Learning on Shared only |
| EV-07 | CI-05 / Coverage (server) / all | Passed | Same candidate | `apps/server`: `uv run coverage run --branch --source=src/shifu -m pytest <the three new modules + tests/intelligence/server/controllers + the Mentor routes coverage suite>` (138 passed), `uv run coverage json`, `uv run python scripts/check_changed_coverage.py --files <18 changed server files>` | Every changed file passes: the new modules at 100 % statements, functions and branches (`create_planned_goal_use_case.py` 56 / 56 statements, 12 / 12 branches); `intelligence_pipe.py` 39 / 39 statements and 10 / 10 functions once the controller suites run, as in the CI selection (a run with only the three new modules reported 3 / 10 functions for that file) |
| EV-08 | VM-01 / Manual / CA-08 | Not run | Local FastAPI without `OPENROUTER_API_KEY` | Reach a real proposal, confirm, verify the Goal page | Without the key the backend cannot produce a proposal; the confirm route and the Learning rows are proven by EV-02, the UI by EV-03 and EV-05. Limitation recorded in Delivery |
| EV-09 | VM-02 / Visual / CA-08, CA-09, CA-12 | Passed | Same candidate, captures from EV-05 | Pencil `Export` at scale 1 (4 PNG in `design/`), `Get` with `ctx.problems` (0 problems), captures in `design/captures/`, side-by-side images in `design/comparisons/` built with Pillow | Notice, dimmed review, busy action, failure copy and the mobile retry-first order match the frames; deviations listed in `design/handoff.md` (guidance kept on failure, backend reason prefixed, shared disabled styles, single Skill icon, shell extras) |
| EV-10 | CI-05 / Types, lint, architecture, routes (web) / all | Passed | Same candidate | `apps/web`: `pnpm check:types`, `pnpm check:lint`, `pnpm check:architecture`, `pnpm generate-routes` | Clean; 7 pre-existing Mentor warnings; no route change |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | The confirm controller suite seeded the curriculum without concepts, so the adaptive seed Skills reported `skill:no_concepts` and every creation answered `curriculum_gap` | Low | EV-02 | Resolved: `seed.concepts` added to the suite's seeding, as the adaptive journey suite does |
| ACH-02 | `use-home-goals-query.ts` entered the changed-file gate (shared query key import) without a test in the CI list | Low | EV-04 | Resolved: `use-home-goals-query.test.ts` added and listed; the key lives in `home-goals-query-key.ts` so the planner hook does not import the Home server function |
| ACH-03 | The mobile failure frame leads with `Tentar criar objetivo` while the creating frame keeps `Reiniciar planejamento` first | Low | EV-09 | Resolved visually with `order-first` below `sm` in the failed state; the DOM order stays stable (handoff) |
| ACH-04 | The default conflict copy of `PlanningRequestError` (`Já existe uma operação em andamento…`) would mislead a creation refusal without a backend reason | Low | EV-05 | Mitigated: every refusal of the confirm route carries its own message (`curriculum_gap`, divergent confirmation, state conflicts); the frame walk uses a realistic reason |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Seed helpers are suite-specific: check which curriculum tables a scenario needs (`concepts` decide `v2_eligible`) | ACH-01 | Local to the suite |
| A change in an import graph can pull an untested file into the coverage gate; keep shared constants in small modules | ACH-02 | Applied (`home-goals-query-key.ts`) |
| Pencil frames of the same surface can disagree on action order between states; follow each frame visually and keep one DOM order | ACH-03 | Recorded in the handoff |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-95` on top of `feat/shifu-93` (`e26cc61`): `98fcac2` feature, `d891e89` docs, then this delivery-state commit |
| Completed | CA-01 … CA-12 implemented; EV-01 … EV-07, EV-09, EV-10 passed |
| Unfinished | VM-01 with the real model (needs `OPENROUTER_API_KEY`) |
| Uncommitted work | None after the delivery commits |
| Active processes | Local FastAPI (7777) and Vite (7000) started for EV-05 may still be running; stop them when done |
| Blockers | None |
| Next action | Watch CI of #36; address review; rebase when #31, #32, #34 and #35 merge |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Intelligence RP-10; JN-13 | RF-01, RF-04 … RF-10 / CA-01 … CA-12 | EV-01 … EV-05, EV-09 | implemented; live model run pending the OpenRouter key |
| Intelligence RP-11, RP-12 | RF-01, RF-07 … RF-09 / CA-07 … CA-12 | EV-02, EV-03, EV-05 | implemented |
| Learning RP-02, RP-03, RP-05 | RF-02, RF-03, RF-10 / CA-01, CA-03 … CA-06 | EV-01, EV-02 | implemented (one transaction, justifications preserved, no diagnosis started) |
| Learning RP-25 | RF-07 … RF-09 / CA-08 … CA-12 | EV-03, EV-05 | implemented |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/36 | `d891e89` (the docs commit that records this state follows) | Pending: CI queued; review pending | https://github.com/CtrI-Alt-Del/shifu/pull/36/checks |

| Field | Result |
| --- | --- |
| Publication | published: PR #36 opened against `main` on 2026-10-20 (stacked on #35, #34, #32 and #31); SHIFU-95 moved to Code Review |
| Source verification | SHIFU-95 description (Jira), PRD Intelligence v4 (Confluence 83099649) and PRD Learning v24 (Confluence 83066881) read on 2026-10-20; frames read and measured from `design/shifu.pen` through Pencil |
| Documentation Alignment | `spec.md` revision 1; `../planner-review/spec.md` revision 3; `../planner-goal-flow/spec.md` revision 4; `design/handoff.md` manifest with 4 pairs; `design.md` T16 label mismatch recorded, no rule change |
| Revision History | Spec revision 1; no contract change during implementation |
| Limitations | Real-model confirmation not run locally (no `OPENROUTER_API_KEY`); the uncertain state has no approved frame and reuses the processing notice |
