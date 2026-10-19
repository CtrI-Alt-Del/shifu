---
title: Practice calendar and streak calculation evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-10-15
---

# Current State

| Field | State |
| --- | --- |
| Implementation | **Complete.** Gamification core/persistence/messaging/REST, the Learning producer enrichment, the Alembic revision `f01033e9cd81` and the full Web surface are implemented |
| Automated checks | **15 / 15 Passed.** 74 gamification core + 115 Learning core + 8 controller (200 in one selection), 11 real-Inngest job tests (non-skipped), 33 web vitest, 3 Playwright route tests |
| Type / lint / complexity | Server: basedpyright 0 errors, Ruff check + format clean on 45 changed paths, Tach validated. Web: `tsc --noEmit` clean, Biome clean. Complexity: configured lint rules only — no quantitative runner exists in this repository |
| Manual checks | **1 / 1 Passed** (`VM-01`, re-run after the visual corrections) |
| Visual checks | **2 / 2 Passed** (`VM-02` at 1440×900 with a practice day selected, and 390×844; both re-captured after ACH-07…ACH-10 and inspected) |
| Independent review | **Complete.** Implementation Reviewer and Visual Reviewer both ran on the integrated candidate; all verified findings resolved (ACH-03…ACH-12) and affected checks re-run |
| Blockers | None for this Spec. **Pre-existing environment defect surfaced:** `uv run poe db:upgrade` fails against the shared dev database because the running `shifu-postgres` container is `postgres:17-alpine` while `docker-compose` declares `pgvector/pgvector:0.8.1-pg17`; an unrelated pending Mentor revision needs `CREATE EXTENSION vector`. The upgrade rolled back cleanly and the dev database is unchanged at `a2f91c6d8e47`. Recreating that container would realign it with the declared image but risks the existing dev data, so it was not done |
| Candidate | `feat/shifu-80`, base `b07cb50`, uncommitted working tree |

Environment inspected without starting a behavioral suite: `docker compose ps`
shows `shifu-postgres`, `shifu-inngest`, `shifu-redis` and `shifu-mailpit` up.
Single Alembic head `341cb645e630` confirmed.

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01, CI-08 | — |
| CA-02 | RF-01 | Complete | Passed | CI-02, CI-09 | — |
| CA-03 | RF-01, RF-02 | Complete | Passed | CI-01 | — |
| CA-04 | RF-02 | Complete | Passed | CI-03, CI-08 | — |
| CA-05 | RF-03 | Complete | Passed | CI-04 | — |
| CA-06 | RF-03 | Complete | Passed | CI-04 | — |
| CA-07 | RF-03, RF-12 | Complete | Passed | CI-04, CI-08 | — |
| CA-08 | RF-04 | Complete | Passed | CI-05 | — |
| CA-09 | RF-05 | Complete | Passed | CI-06 | — |
| CA-10 | RF-05 | Complete | Passed | CI-06 | — |
| CA-11 | RF-05 | Complete | Passed | CI-05 | — |
| CA-12 | RF-06, RF-07 | Complete | Passed | CI-06 | — |
| CA-13 | RF-06 | Complete | Passed | CI-07 | — |
| CA-14 | RF-10 | Complete | Passed | CI-07 | — |
| CA-15 | RF-10 | Complete | Passed | CI-07 | — |
| CA-16 | RF-10, RF-09 | Complete | Passed | CI-10 | — |
| CA-17 | RF-09, RF-12 | Complete | Passed | CI-01, CI-08 | — |
| CA-18 | RF-09 | Complete | Passed | CI-08, CI-09 | — |
| CA-19 | RF-09, RF-12 | Complete | Passed | CI-08 | — |
| CA-20 | RF-06, RF-07, RF-08, RF-11 | Complete | Passed | CI-11, CI-13, VM-01, VM-02 | — |
| CA-21 | RF-06, RF-11 | Complete | Passed | CI-11, CI-13, CI-15, VM-01 | — |
| CA-22 | RF-08 | Complete | Passed | CI-11, VM-01 | — |
| CA-23 | RF-11 | Complete | Passed | CI-11, CI-12 | — |
| CA-24 | RF-11 | Complete | Passed | VM-02 | — |
| CA-25 | RF-09 | Complete | Passed | CI-06 | — |
| CA-26 | RF-01, RF-09 | Complete | Passed | CI-09 | — |
| CA-27 | RF-11 | Complete | Passed | CI-12 | — |
| CA-28 | RF-06 | Complete | Passed | CI-15 | — |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-03, CA-17 | Passed | — | `uv run pytest tests/gamification/core/use_cases/test_recognize_practice_day_use_case.py` (`apps/server`) | — |
| EV-02 | CI-02 / Automated / CA-02 | Passed | — | `uv run pytest tests/learning/core/use_cases/test_complete_diagnostic_use_case.py` (`apps/server`) | — |
| EV-03 | CI-03 / Automated / CA-04 | Passed | — | same file as EV-01 | — |
| EV-04 | CI-04 / Automated / CA-05, CA-06, CA-07 | Passed | — | same file as EV-01 | — |
| EV-05 | CI-05 / Automated / CA-08, CA-11 | Passed | — | same file as EV-01 | — |
| EV-06 | CI-06 / Automated / CA-09, CA-10, CA-12, CA-25 | Passed | — | `uv run pytest tests/gamification/core/use_cases/test_get_practice_calendar_use_case.py` (`apps/server`) | — |
| EV-07 | CI-07 / Automated / CA-13, CA-14, CA-15 | Passed | — | `uv run pytest tests/gamification/server/controllers/test_get_practice_calendar_controller.py` (`apps/server`) | Also the sole proof of the new table, model, mapper, repository and migration |
| EV-08 | CI-08 / Automated / CA-01, CA-04, CA-07, CA-17, CA-18, CA-19 | Passed | — | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/gamification/test_recognize_practice_day_on_activity_evaluated_job.py` (`apps/server`) | A skip is Blocked, not passing |
| EV-09 | CI-09 / Automated / CA-02, CA-18, CA-26 | Passed | — | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest <practice-day + existing diagnostic job tests>` (`apps/server`) | — |
| EV-10 | CI-10 / Automated / CA-16 | Passed | — | `uv run pytest tests/gamification/core/use_cases/test_delete_gamification_profile_use_case.py` (`apps/server`) | — |
| EV-11 | CI-11 / Automated / CA-20, CA-21, CA-22, CA-23 | Passed | — | `pnpm --filter web exec vitest run <calendar-tab-panel tests>` (root) | — |
| EV-12 | CI-12 / Automated / CA-23, CA-27 | Passed | — | `pnpm --filter web exec vitest run <gamification-page tests>` (root) | — |
| EV-13 | CI-13 / Automated / CA-20, CA-21 | Passed | — | `pnpm --filter web exec playwright test tests/gamification/gamification-page.test.ts` (root) | Mocked transport; does not prove real persistence |
| EV-14 | CI-15 / Automated / CA-21, CA-28 | Passed | — | `pnpm --filter web exec vitest run <use-calendar-tab-panel test>` (root) | — |
| EV-15 | CI-14 types / Static / all | Passed | — | `uv run poe check:types` (`apps/server`); `pnpm --filter web check:types` (root) | — |
| EV-16 | CI-14 lint+format / Static / all | Passed | — | `uv run ruff check --no-fix <paths>`, `uv run ruff format --check <paths>` (`apps/server`); `pnpm exec biome check <paths>` (root) | — |
| EV-17 | CI-14 architecture / Static / all | Passed | — | `uv run poe check:architecture` (`apps/server`) | Must confirm Gamification still imports only `shifu.shared` |
| EV-18 | CI-14 complexity / Static / all | Passed | — | Ruff `C90` within EV-16; Biome complexity rules within EV-16 | No quantitative metrics runner is configured; a score is not claimed |
| EV-19 | CI-14 mutation / Static / CA-05, CA-07–CA-12 | Passed with justified survivors | — | `uv run poe test:mutation --core --files src/shifu/gamification/core/use_cases/recognize_practice_day_use_case.py src/shifu/gamification/core/use_cases/get_practice_calendar_use_case.py` (`apps/server`) | 2026-10-15. Both targets confirmed in the runner's reported scope. 260 mutants, **250 killed, 8 survived, 2 timeout**, ~55s per run. Three rounds of assertion strengthening took survivors 35 → 22 → 19 → 8. `_state_for` (day-state derivation) has **zero** survivors. Every remaining survivor is individually justified below |
| EV-20 | VM-01 / Manual / CA-20, CA-21, CA-22 | Passed | `feat/shifu-80`, 2026-10-15. Real sign-in as `student.seed@shifu.com` against the real API and an **isolated** pgvector PostgreSQL on port 54399 (migrated to `f01033e9cd81`, seeded with 4 practice days). The shared dev database was left untouched | Real-browser journey driven through the installed Playwright browser API (`playwright-cli` is not installed in this environment); log at `apps/web/.playwright-cli/logs/vm01-journey.log` | URL stayed `/gamification`; h1 `Gamificação`; Calendário `aria-selected=true` by default; month `Outubro 2026`; next-month genuinely disabled; **all five day states rendered from persisted rows** (missed 11, practiced 1, current-streak 2, today-pending 1, neutral 16); keyboard day selection gave `5 de outubro · Houve prática neste dia` with **no XP and no Activity count**; keyboard previous-month moved to `Setembro 2026` issuing 1 new scoped request; Conquistas tab still renders achievements; **0 console errors, 0 failed requests**. Streak read `2 dias seguidos` / `Maior sequência: 4 dias`, matching the seeded rows |
| EV-21 | VM-02 / Visual / CA-20 | Passed | `feat/shifu-80`, 2026-10-15, captured during EV-20 at 1440×900 | `.playwright-cli/screenshots/vm02-desktop-1440x900.png`, opened and compared against `design/J5y1Au.png` | Matches the reference on tab bar, month card, Monday-first header, 64px day cells with mono numeral above the state mark, tinted current-streak cells, outlined today-pending cell with `clock-3`, date-only confirmation line, streak panel hierarchy and the five-state legend. Each state is distinguishable by shape and glyph alone. Accepted deviation: two tabs instead of the reference's four |
| EV-22 | VM-02 / Visual / CA-24 | Passed | `feat/shifu-80`, 2026-10-15, 390×844 | `.playwright-cli/screenshots/vm02-narrow-390x844.png` plus a viewport-only `vm02-narrow-390x844-viewport.png` | 7/7 weekday columns retained with reduced cells per `design.md` §9; `scrollWidth <= innerWidth` so no horizontal overflow. The full-page capture appears to show the fixed bottom navigation crossing the calendar card; a viewport-only capture and a measured check (`nav.top=0`, `overlaps=false`) confirm that is a `fullPage` artifact of a fixed element, not a layout defect. No mobile reference frame exists — accepted deviation recorded in the handoff |

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

### EV-19 surviving-mutant disposition

Each survivor was extracted from the generated mutant source and classified; none
is a live defect.

| Mutant | Change | Disposition |
| --- | --- | --- |
| `_streak_from_dates__mutmut_39` | `while index >= 0` instead of `> 0` | Equivalent. At index 0 the guard compares `ordered[0] - ordered[-1]`, which on an ascending list is never +1 day, so the loop exits identically and the index never goes negative |
| `_current_run__mutmut_13` | same `index >= 0` change | Equivalent, same reasoning |
| `_longest_run__mutmut_2` | `return 1` instead of `0` for an empty list | Unreachable: `_longest_run` is only called from `_streak_for`'s non-empty branch |
| `_streak_for__mutmut_5` | drops the explicit `current=0` | Equivalent: 0 is already the `PracticeStreak` field default |
| `GetPracticeCalendarUseCase.execute__mutmut_7` | `year <= 1` | Differs only at year 1, which is not a meaningful calendar input; asserting it would encode nonsense as contract |
| `GetPracticeCalendarUseCase.execute__mutmut_8` | `year < 2` | Same as above |
| `RecognizePracticeDayUseCase.execute__mutmut_22` | `now.astimezone(None)` (system local zone) | Only distinguishable by pinning the test machine's timezone, which would make the suite machine-dependent. Accepted rather than introducing an environment-coupled test |
| `GetPracticeCalendarUseCase.execute__mutmut_12` | same `astimezone(None)` change | Same as above |

The 2 timeouts are infinite-loop mutants of the streak walk; mutmut counts a
timeout as detected, and they are not survivors.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Spec contracted `__tablename__ = 'practice_days'`, but every sibling Gamification table is `gamification_*` | low | — | **Resolved.** Used `gamification_practice_days` for convention consistency; Spec Architecture Mapping reconciled |
| ACH-02 | `_streak_for` returned `longest=0` beside a non-null `latest_practice_date` when a profile snapshot was never written, violating `PracticeStreak`'s `(longest == 0) != (latest is None)` invariant and 400-ing a valid read. Found by the controller test | high | CI-06, CI-07 | **Resolved.** `longest = max(stored.longest, _longest_run(ordered))`; covered by `test_should_derive_longest_from_the_days_when_the_snapshot_lags` |
| ACH-03 | Implementation Reviewer: `test_complete_diagnostic_use_case.py` was marked `[M]` but never extended; every attempt fixture shared `submitted_at=NOW`, so the "last required attempt" selection was asserted nowhere. EV-02 was recorded Passed without support | **blocking** | CI-02 | **Resolved.** Attempts now submit on distinct days with a zone; the test asserts the emitted `submitted_at`/`time_zone` match the latest attempt and that `completed_at` still differs. EV-02 re-run |
| ACH-04 | Implementation Reviewer: `use-gamification-page.test.ts` marked `[M]` but never extended — `activeTab`/`handleTabChange` unasserted below Playwright | high | CI-12 | **Resolved.** Added a default-tab and tab-change case |
| ACH-05 | Implementation Reviewer: `test_evaluate_choice_activity_use_case.py` marked `[M]` but never extended — the new producer emission unasserted | high | CI-01 | **Resolved.** Asserts `submitted_at`/`time_zone` from the attempt and that they differ from `evaluated_at` |
| ACH-06 | Implementation Reviewer: `Query(ge=1, le=12)` made FastAPI answer **422** for an out-of-range month where `spec.md` contracts **400**, leaving the use-case guard unreachable over HTTP | medium | CI-07, CA-13 | **Resolved.** Bounds removed so `InvalidGamificationError` surfaces as 400; controller test now asserts 400 |
| ACH-07 | Visual Reviewer: `* { border-color: var(--border) }` is **unlayered** at `apps/web/src/ui/shared/styles/global.css:133-136`, so it outranks every layered Tailwind `border-*` utility. The latão rings never rendered — `practiced` and `current-streak` collapsed to "has a check", breaking non-colour differentiation (RF-07, RP-13) | **blocking** | VM-02, CA-20 | **Resolved locally** with the Tailwind `!` modifier on this feature's rings. **Not fixed globally:** the same reset also silently disables `border-selo-text` (19 uses), `border-primary` (9) and `border-success` (2) elsewhere; correcting it app-wide would change surfaces with no visual evidence and is out of this Spec's scope — see Lessons Learned |
| ACH-08 | Visual Reviewer: active tab rendered with shadcn's `data-[state=active]:bg-card` defaults instead of the latão tab and hairline divider the handoff specifies | medium | VM-02 | **Resolved.** TabsList/TabsTrigger overridden with `!` (the primitive's variant selector outranks a plain utility). `activeTab` prop became redundant and was removed |
| ACH-09 | Visual Reviewer: streak numeral was `text-5xl` (48px) where the handoff specifies 64px | low | VM-02 | **Resolved.** Now `text-[64px] leading-none` |
| ACH-10 | Self-found during recapture: the selection indicator used `outline`, which the `:focus-visible` outline (`--selo-text`, red) replaced — a keyboard-selected day showed a red ring instead of the latão selection stroke | medium | VM-01, VM-02 | **Resolved.** Selection is now `ring-1 ring-latao-solid`, which composes with the focus outline. Re-captured with focus blurred so the selection ring is evidenced on its own |
| ACH-11 | Visual Reviewer: RP-06's selected-day state was not visually evidenced — no day was selected in the original captures | medium | VM-02 | **Resolved.** The journey now selects a practice day before capturing; `vm02-desktop-1440x900.png` shows "5 de outubro · Houve prática neste dia" with no XP and no Activity count |
| ACH-12 | `VM-01` was driven through the installed Playwright browser API rather than `playwright-cli`, which `AGENTS.md` and `spec.md:650` name. `playwright-cli` is **not installed** in this environment and `implement-spec` forbids installing a runner incidentally | low | VM-01 | **Accepted deviation.** The journey still exercised the real browser, real sign-in, real API and real persistence — no mocks. Recorded rather than silently substituted |

| ACH-13 | CI browser suite failed on three assertions outside the gamification tests: `intelligence-page.test.ts` and `app-layout.test.ts` asserted the replaced h1 "Cada passo merece ser visto.", and `app-layout.test.ts` queried `getByRole('alert')` unscoped — the Calendário tab is now the default, so an unmocked calendar request adds a second alert | high | CI-13 and the shared/intelligence browser suites | **Resolved** in `434559c`. h1 assertions updated; the logout alert scoped to the account menu. Root cause was under-selecting locally: only the gamification suite was run, though the page header has consumers in two other suites. The full browser suite is now the selection |
| ACH-14 | CI new-code mutation gate failed on **Learning**, not Gamification (which scored 88.7%). The gate scores whole changed files, so ~10 lines of Learning edits pulled in 1,224 pre-existing mutants at 59.9% against a 70% minimum. No subset of the touched files reaches 70%, and RP-05 cannot be met without editing at least `evaluate_choice_activity` and `complete_diagnostic` | **blocking** | CI mutation gate | **Resolved** by raising coverage on the three files in a separate PR (#29) merged into this branch: 58.1% → 70.3% standalone, **71.0% here** (869/1224, 12-mutant margin). The threshold file was **not** weakened |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| An unscoped `getByRole('alert')` in a shared suite is fragile: adding a legitimate error region anywhere on the landed route breaks it with a strict-mode violation. Equally, changing a page header silently breaks suites that use that page only as a shell fixture | ACH-13 | Select the full browser suite when changing a shared page's header or adding a new alert region, not just the feature's own file |
| The CI mutation gate scores whole changed files, so touching one line of an under-covered file inherits all of its debt. 10 of Learning's 21 use-case files sit below the 70% minimum, which effectively blocks edits to them | ACH-14 | Raised as PR #29's "Limitações conhecidas": score changed lines, or add per-file baselines as `module_baselines` already does for regression. Not fixed here — altering the gate to go green would weaken it |
| An unlayered `*` rule beats every layered Tailwind utility regardless of specificity, so `global.css`'s `border-color` reset silently disables all border-colour utilities app-wide. Any surface that uses a coloured border to carry *meaning* will fail accessibility review without anyone noticing | ACH-07; measured by the Visual Reviewer at ~1.1:1 contrast | **Proposed, not applied.** Scoping the reset into `@layer base` is a one-line fix but changes ~33 call sites (`border-selo-text`, `border-primary`, `border-success`) with no visual evidence. Warrants its own ticket with its own visual pass |
| Marking a test file `[M]` in a Spec's file tree does not make it modified. Three files were listed as extended, ran green, and were recorded as passing while asserting none of the new behaviour | ACH-03, ACH-04, ACH-05 | Before recording an EV as Passed, confirm the proving file actually appears in `git status`. Applied here; worth repeating at conclusion time |
| Framework-level input validation can silently pre-empt a contracted domain error — FastAPI's `Query(le=12)` answered 422 where the Spec contracted 400 | ACH-06 | Contract the status code at the boundary that owns the rule, and assert it in the controller test |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-80`, base `b07cb50`, uncommitted working tree (59 paths: 22 new, 37 modified) |
| Completed | All 28 criteria implemented and verified. 15/15 automated checks, `VM-01`, both `VM-02` viewports, all static gates, and the scoped mutation run |
| Unfinished | None for this Spec |
| Uncommitted work | The feature diff plus `documentation/features/gamification/practice-calendar/{spec.md,evaluation.md,design/}`. Unrelated untracked file to preserve: `documentation/prompts/create-plan-prompt.md` |
| Active processes | None. The task-started API (:7777) and Vite (:7000) were stopped; the disposable `shifu-vm-postgres` container was removed. Shared Docker services were left running and the shared dev database is untouched at `a2f91c6d8e47` |
| Blockers | None. Two environment issues recorded, neither caused by this Spec: the dev Postgres container runs `postgres:17-alpine` while compose declares `pgvector/pgvector:0.8.1-pg17`, so `db:upgrade` fails on an unrelated Mentor revision needing `CREATE EXTENSION vector`; and `playwright-cli` is not installed (ACH-12) |
| Next action | `conclude-spec` |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-01 | RF-10; CA-14, CA-15| EV-01…EV-22 | implemented |
| RP-05 | RF-01–RF-05, RF-09; CA-01–CA-11, CA-17, CA-18, CA-25, CA-26| EV-01…EV-22 | implemented |
| RP-06 | RF-06–RF-08; CA-12, CA-13, CA-20–CA-22, CA-28| EV-01…EV-22 | implemented |
| RP-08 | RF-09; CA-25| EV-01…EV-22 | implemented |
| RP-11 | RF-01, RF-09, RF-12; CA-17, CA-19, CA-26| EV-01…EV-22 | implemented |
| RP-12 | RF-10; CA-15, CA-16| EV-01…EV-22 | implemented |
| RP-13 | RF-11; CA-20, CA-21, CA-23, CA-24, CA-27| EV-01…EV-22 | implemented |

| Field | Result |
| --- | --- |
| Publication | Not requested — local only; nothing committed |
| Source verification | PRD — Gamification, content ID `82903042`, version 3, last edited 2026-10-04, complete page read 2026-10-14. Reported conflict: SHIFU-80 cites "versão 2"; the canonical page is version 3 |
| Documentation Alignment | `../achievements/spec.md` records RP-05/RP-06 as deferred; those are now delivered and the note should be reconciled at conclusion. Its `Sequência`-unreachable note remains accurate |
| Revision History | No contract change since revision 1 |
| Limitations | `Sequência` achievements remain unreachable by contract (achievement processing is excluded from SHIFU-80); no mobile design reference frame exists for node 14.1 |
