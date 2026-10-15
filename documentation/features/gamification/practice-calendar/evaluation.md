---
title: Practice calendar and streak calculation evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-14
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Pending — kickoff; no source edited yet. All 28 criteria outstanding |
| Automated checks | 0 / 15 passed; none run |
| Type / lint / complexity | Types Pending; lint/format Pending; complexity Pending (configured lint rules only — no quantitative metrics runner exists in this repository) |
| Manual checks | 0 / 1 passed (`VM-01`) |
| Visual checks | 0 / 2 passed (`VM-02` desktop 1440×900 and narrow 390×844 — scheduled as separate obligations) |
| Independent review | Pending — Implementation Reviewer and Visual Reviewer launch in parallel on the integrated candidate |
| Blockers | None |
| Candidate | `feat/shifu-80`, clean at `e7b2097`; dirty scope limited to `documentation/features/gamification/practice-calendar/**` |

Environment inspected without starting a behavioral suite: `docker compose ps`
shows `shifu-postgres`, `shifu-inngest`, `shifu-redis` and `shifu-mailpit` up.
Single Alembic head `341cb645e630` confirmed.

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Pending | Pending | CI-01, CI-08 | Recognize use case and activity-evaluated job |
| CA-02 | RF-01 | Pending | Pending | CI-02, CI-09 | Diagnostic event dating from the last required attempt |
| CA-03 | RF-01, RF-02 | Pending | Pending | CI-01 | Score-0 / no-XP practice still recognized |
| CA-04 | RF-02 | Pending | Pending | CI-03, CI-08 | Single-day collapse via the unique index |
| CA-05 | RF-03 | Pending | Pending | CI-04 | Local-date resolution across the zone boundary |
| CA-06 | RF-03 | Pending | Pending | CI-04 | Stored date frozen against later zone change |
| CA-07 | RF-03, RF-12 | Pending | Pending | CI-04, CI-08 | UTC fallback for absent/null/empty/unresolvable zone |
| CA-08 | RF-04 | Pending | Pending | CI-05 | Late evaluation joins two runs |
| CA-09 | RF-05 | Pending | Pending | CI-06 | Run ending yesterday stays active today |
| CA-10 | RF-05 | Pending | Pending | CI-06 | Derived current decays to 0; longest preserved |
| CA-11 | RF-05 | Pending | Pending | CI-05 | Restart at 1 after a break |
| CA-12 | RF-06, RF-07 | Pending | Pending | CI-06 | Five day states across a month |
| CA-13 | RF-06 | Pending | Pending | CI-07 | Future month rejected with 400 |
| CA-14 | RF-10 | Pending | Pending | CI-07 | Account isolation |
| CA-15 | RF-10 | Pending | Pending | CI-07 | 404 without a profile |
| CA-16 | RF-10, RF-09 | Pending | Pending | CI-10 | Practice days purged on deletion |
| CA-17 | RF-09, RF-12 | Pending | Pending | CI-01, CI-08 | No-profile delivery writes nothing |
| CA-18 | RF-09 | Pending | Pending | CI-08, CI-09 | Duplicate delivery adds nothing |
| CA-19 | RF-09, RF-12 | Pending | Pending | CI-08 | Malformed payload is non-retriable, writes nothing |
| CA-20 | RF-06, RF-07, RF-08, RF-11 | Pending | Pending | CI-11, CI-13, VM-01, VM-02 | Calendar renders real data |
| CA-21 | RF-06, RF-11 | Pending | Pending | CI-11, CI-13, CI-15, VM-01 | Keyboard month navigation; future disabled |
| CA-22 | RF-08 | Pending | Pending | CI-11, VM-01 | Date-only selection confirmation |
| CA-23 | RF-11 | Pending | Pending | CI-11, CI-12 | Loading and error with working retry |
| CA-24 | RF-11 | Pending | Pending | VM-02 | Narrow viewport keeps 7 columns |
| CA-25 | RF-09 | Pending | Pending | CI-06 | Goal/Skill removal preserves days |
| CA-26 | RF-01, RF-09 | Pending | Pending | CI-09 | Existing XP consumer survives the enriched payload |
| CA-27 | RF-11 | Pending | Pending | CI-12 | Tab shell; achievements preserved |
| CA-28 | RF-06 | Pending | Pending | CI-15 | Earliest-practice floor on navigation |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-03, CA-17 | Pending | — | `uv run pytest tests/gamification/core/use_cases/test_recognize_practice_day_use_case.py` (`apps/server`) | — |
| EV-02 | CI-02 / Automated / CA-02 | Pending | — | `uv run pytest tests/learning/core/use_cases/test_complete_diagnostic_use_case.py` (`apps/server`) | — |
| EV-03 | CI-03 / Automated / CA-04 | Pending | — | same file as EV-01 | — |
| EV-04 | CI-04 / Automated / CA-05, CA-06, CA-07 | Pending | — | same file as EV-01 | — |
| EV-05 | CI-05 / Automated / CA-08, CA-11 | Pending | — | same file as EV-01 | — |
| EV-06 | CI-06 / Automated / CA-09, CA-10, CA-12, CA-25 | Pending | — | `uv run pytest tests/gamification/core/use_cases/test_get_practice_calendar_use_case.py` (`apps/server`) | — |
| EV-07 | CI-07 / Automated / CA-13, CA-14, CA-15 | Pending | — | `uv run pytest tests/gamification/server/controllers/test_get_practice_calendar_controller.py` (`apps/server`) | Also the sole proof of the new table, model, mapper, repository and migration |
| EV-08 | CI-08 / Automated / CA-01, CA-04, CA-07, CA-17, CA-18, CA-19 | Pending | — | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/gamification/test_recognize_practice_day_on_activity_evaluated_job.py` (`apps/server`) | A skip is Blocked, not passing |
| EV-09 | CI-09 / Automated / CA-02, CA-18, CA-26 | Pending | — | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest <practice-day + existing diagnostic job tests>` (`apps/server`) | — |
| EV-10 | CI-10 / Automated / CA-16 | Pending | — | `uv run pytest tests/gamification/core/use_cases/test_delete_gamification_profile_use_case.py` (`apps/server`) | — |
| EV-11 | CI-11 / Automated / CA-20, CA-21, CA-22, CA-23 | Pending | — | `pnpm --filter web exec vitest run <calendar-tab-panel tests>` (root) | — |
| EV-12 | CI-12 / Automated / CA-23, CA-27 | Pending | — | `pnpm --filter web exec vitest run <gamification-page tests>` (root) | — |
| EV-13 | CI-13 / Automated / CA-20, CA-21 | Pending | — | `pnpm --filter web exec playwright test tests/gamification/gamification-page.test.ts` (root) | Mocked transport; does not prove real persistence |
| EV-14 | CI-15 / Automated / CA-21, CA-28 | Pending | — | `pnpm --filter web exec vitest run <use-calendar-tab-panel test>` (root) | — |
| EV-15 | CI-14 types / Static / all | Pending | — | `uv run poe check:types` (`apps/server`); `pnpm --filter web check:types` (root) | — |
| EV-16 | CI-14 lint+format / Static / all | Pending | — | `uv run ruff check --no-fix <paths>`, `uv run ruff format --check <paths>` (`apps/server`); `pnpm exec biome check <paths>` (root) | — |
| EV-17 | CI-14 architecture / Static / all | Pending | — | `uv run poe check:architecture` (`apps/server`) | Must confirm Gamification still imports only `shifu.shared` |
| EV-18 | CI-14 complexity / Static / all | Pending | — | Ruff `C90` within EV-16; Biome complexity rules within EV-16 | No quantitative metrics runner is configured; a score is not claimed |
| EV-19 | CI-14 mutation / Static / CA-05, CA-07–CA-12 | Pending | — | `uv run poe test:mutation --core --files <both use-case paths on one flag>` (`apps/server`) | Record targets, elapsed time and mutant outcomes; runner success alone is not proof |
| EV-20 | VM-01 / Manual / CA-20, CA-21, CA-22 | Pending | — | Playwright CLI real authenticated journey (`apps/web`) | — |
| EV-21 | VM-02 / Visual / CA-20 | Pending | — | Capture during EV-20 at 1440×900 | — |
| EV-22 | VM-02 / Visual / CA-24 | Pending | — | Capture during EV-20 at 390×844 | — |

## Required manual and visual evidence inventory

| Row | VM / CA | Surface / route | State | Viewport | Reference | Candidate | Artifact path | Observed | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | VM-01 / CA-20, CA-21, CA-22 | `/gamification`, Calendário tab | Real authenticated journey: current month, keyboard month navigation, disabled future control, keyboard day selection, tab switch | 1440×900 | — (behavioral) | — | — | — | Pending |
| V1 | VM-02 / CA-20 | `/gamification`, Calendário tab | Current month with a current-streak day, a non-streak practice day, a missed day and today-pending | 1440×900 | `design/J5y1Au.png` (node `J5y1Au`, 1440×1100, scale 1) | — | — | — | Pending |
| V2 | VM-02 / CA-24 | `/gamification`, Calendário tab | Same month state at a narrow viewport | 390×844 | No reference frame — `design.md` §9 ("7 colunas, célula reduzida"), accepted deviation recorded in `design/handoff.md` | — | — | — | Pending |

Behavioral and visual results are separate: a working journey does not establish
a design match, and a matching image does not establish real authentication or
persistence. A captured state stays Pending until inspected against its own
reference. The `neutral` day state does not occur in the reference month and is
verified against the legend entry (handoff deviation 3).

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| — | No findings recorded yet | — | — | — |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| — | None yet | — |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-80`, base `e7b2097`, clean working tree at kickoff |
| Completed | None |
| Unfinished | All 28 criteria; all 15 automated checks; `VM-01`, `VM-02` (both viewports) |
| Uncommitted work | `documentation/features/gamification/practice-calendar/{spec.md,evaluation.md,design/}` — SDD artifacts, Orchestrator-owned. Unrelated untracked file to preserve: `documentation/prompts/create-plan-prompt.md` |
| Active processes | None task-started. Shared Docker services (`shifu-postgres`, `shifu-inngest`, `shifu-redis`, `shifu-mailpit`) were already running and must be left running |
| Blockers | None |
| Next action | Implement Gamification core + persistence, Learning producer enrichment and the Web tab as disjoint streams; then the Alembic revision, jobs and REST endpoint in the main task |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-01 | RF-10; CA-14, CA-15 | — | Pending |
| RP-05 | RF-01–RF-05, RF-09; CA-01–CA-11, CA-17, CA-18, CA-25, CA-26 | — | Pending |
| RP-06 | RF-06–RF-08; CA-12, CA-13, CA-20–CA-22, CA-28 | — | Pending |
| RP-08 | RF-09; CA-25 | — | Pending |
| RP-11 | RF-01, RF-09, RF-12; CA-17, CA-19, CA-26 | — | Pending |
| RP-12 | RF-10; CA-15, CA-16 | — | Pending |
| RP-13 | RF-11; CA-20, CA-21, CA-23, CA-24, CA-27 | — | Pending |

| Field | Result |
| --- | --- |
| Publication | Not requested — local only |
| Source verification | PRD — Gamification, content ID `82903042`, version 3, last edited 2026-10-04, complete page read 2026-10-14. Reported conflict: SHIFU-80 cites "versão 2"; the canonical page is version 3 |
| Documentation Alignment | Pending — reconcile `../achievements/spec.md` RP-05/RP-06 deferral notes at conclusion |
| Revision History | No contract change since revision 1 |
| Limitations | `Sequência` achievements remain unreachable by contract (achievement processing is excluded from SHIFU-80); no mobile design reference frame exists for node 14.1 |
