---
title: Progresso panel — learning panorama and engagement dashboard evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-11-22
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for server, shared charts, Learning and Engajamento widgets, route and browser tests, including the revision-2 reconciliation (Q19-Q23). |
| Automated checks | 13/13 selections executed and passing on the merged candidate (see Check Results). The whole-script exit code of `pnpm check:test-integrity` is a pre-existing failure on two base files; its Spec passing condition (no new test file flagged) holds. |
| Type / lint / complexity | Types passed (server 0/0, web `tsc` clean). Ruff and Biome clean on changed paths and on all 883 web files. Complexity-metrics tooling Not applicable per the Spec. |
| Manual checks | VM-01 Passed: real-service desktop journey and keyboard path, plus keyboard at 390 px on the final candidate. |
| Visual checks | VM-02 and VM-03 Passed in the second independent review (rows V-1 and V-2), after the corrections for the first review and the mobile recapture. |
| Independent review | Implementation review (revision 1 and the revision-2 delta): no blocking finding; items ACH-05..ACH-13 resolved or accepted. Visual review: first FAIL (ACH-04), second PASS. |
| Blockers | None. ACH-02 (two Alembic heads on the base) was resolved on `main` by the SHIFU-130 migration that merges both heads; the merged candidate migrates to the single head `e48385bfd6fe`. |
| Candidate | Branch `claude/shifu-133-spec-5249fe`: seven scoped delivery commits on base `c0567b49`, then `origin/main` `98b2aec8` merged (merge commit `ceb5c72f`). Publication in progress. |

Contract evaluated: Spec revision 2 (revision 1 evidence for the server remains valid because revision 2 changed only web presentation and the evolution card rule). Environment: the worktree had no installed dependencies, so
`pnpm install --frozen-lockfile` and `uv sync` ran first. Verification used a disposable stack
(Postgres `pgvector/pgvector:0.8.1-pg17` on 54399, Redis on 63799, API 7788, web 7100, proxies 7789/7790),
never the shared dev services. No `.codegraph/` index exists.

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-09, CI-10, VM-01| None |
| CA-02 | RF-02, RF-03 | Complete | Passed | CI-01, CI-03 | None |
| CA-03 | RF-03, RF-09 | Complete | Passed | CI-01 | None |
| CA-04 | RF-02 | Complete | Passed | CI-01, CI-03 | None |
| CA-05 | RF-04 | Complete | Passed | CI-01, CI-03 | None |
| CA-06 | RF-05 | Complete | Passed | CI-01 | None |
| CA-07 | RF-05 | Complete | Passed | CI-01 | None |
| CA-08 | RF-05 | Complete | Passed | CI-07, VM-01| None |
| CA-09 | RF-06 | Complete | Passed | CI-01, CI-03 | None |
| CA-10 | RF-06 | Complete | Passed | CI-01 | None |
| CA-11 | RF-06, RF-14 | Complete | Passed | CI-01, CI-04 | None |
| CA-12 | RF-07 | Complete | Passed | CI-02, CI-03 | None |
| CA-13 | RF-07 | Complete | Passed | CI-02 | None |
| CA-14 | RF-07 | Complete | Passed | CI-02 | None |
| CA-15 | RF-07 | Complete | Passed | CI-02 | None |
| CA-16 | RF-07, RF-17 | Complete | Passed | CI-03 | None |
| CA-17 | RF-07 | Complete | Passed | CI-01 | None |
| CA-18 | RF-07, RF-16 | Complete | Passed | CI-07 | None |
| CA-19 | RF-08 | Complete | Passed | CI-01, CI-07, VM-02| None |
| CA-20 | RF-09 | Complete | Passed | CI-01 | None |
| CA-21 | RF-10 | Complete | Passed | CI-07 | None |
| CA-22 | RF-10 | Complete | Passed | CI-07| None |
| CA-23 | RF-11 | Complete | Passed | CI-04, CI-05, CI-08, VM-02| None |
| CA-24 | RF-12 | Complete | Passed | CI-04, CI-08, VM-02| None |
| CA-25 | RF-13 | Complete | Passed | CI-04 | None |
| CA-26 | RF-13 | Complete | Passed | CI-04, CI-08 | None |
| CA-27 | RF-13 | Complete | Passed | CI-04 | None |
| CA-28 | RF-14 | Complete | Passed | CI-04, CI-05 | None |
| CA-29 | RF-14 | Complete | Passed | CI-08, VM-01, VM-02| None |
| CA-30 | RF-15 | Complete | Passed | CI-06, CI-07, CI-08, CI-09 | None |
| CA-31 | RF-16 | Complete | Passed | CI-06, CI-09, VM-01| None |
| CA-32 | RF-17 | Complete | Passed | CI-03, CI-05 | None |
| CA-33 | RF-17 | Complete | Passed | CI-03, CI-05 | None |
| CA-34 | RF-18 | Complete | Passed | CI-01, CI-03, CI-05 | None |
| CA-35 | RF-19 | Complete | Passed | CI-09, VM-01, VM-03| None |
| CA-36 | RF-01, RF-15 | Complete | Passed | CI-06, CI-07, CI-08, VM-02| None |
| CA-37 | RF-13 | Complete | Passed | CI-04 | None |

One row per criterion. Implementation: Pending, Partial, Complete. Verification:
Pending, Partial, Passed, Failed, Blocked, Stale.

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-02..11,17,19,20,34 | Passed | Merged candidate (`ceb5c72f` plus one added test case), 2026-11-22, mocked repositories | `uv run pytest -p no:tach tests/learning/core/use_cases/test_get_learning_panorama_use_case.py` in `apps/server` with the stack environment | 34 passed. Reran after the sync with `main` because Learning domain files changed there. |
| EV-02 | CI-02 / Automated / CA-12..15 | Passed | same | `uv run pytest -p no:tach tests/learning/core/use_cases/test_get_skill_evolution_use_case.py` | 22 passed. The pending/failed/effectless case now also covers `closed_without_grade` (ACH-14). |
| EV-03 | CI-03 / Automated / CA-02,04,05,09,12,16,32,33,34 | Passed | Testcontainer Postgres+Redis on the merged candidate, 2026-11-22; no temporary migration (single Alembic head `e48385bfd6fe`) | `uv run pytest -p no:tach` on both Learning controller files | 15 passed (8 panorama including a `closed_without_grade` attempt that is not counted, 7 evolution). Reproducible on `main` now that ACH-02 is resolved. |
| EV-04 | CI-04 / Automated / CA-11,23..28,37 | Passed | mocked repositories, merged candidate | overview, list-achievements and practice-calendar use-case files | 74 passed (45 + 4 + 25); the two regression files have no diff. Total of the five use-case files: 130 passed. |
| EV-05 | CI-05 / Automated / CA-23,28,32,33,34 | Passed | Testcontainer on the merged candidate, no temporary migration | overview controller file | 13 passed (28 controller tests in the three files together, 192 s). |
| EV-06 | CI-06 / Automated / CA-30,31,36 | Passed | jsdom, merged candidate | `pnpm exec vitest run src/ui/shared/widgets src/ui/learning src/ui/gamification src/routes src/rest` in `apps/web` | 136 files / 1326 tests passed together, including the shared layout, chart-frame (`headerAction`, `footnote`), bar-chart, line-chart, tooltip and value-label tests; the six new directories emit zero console warnings. The jsdom "navigation to another Document" message comes from older unmodified widget tests. |
| EV-07 | CI-07 / Automated / CA-08,18,19,21,22,30,36 | Passed | jsdom, merged candidate | included in the EV-06 run | All Learning widget suites pass, including the two-point evolution rule (0, 1, 2 points), the weekly footnote in both views and the jade markers. Zero warnings. |
| EV-08 | CI-08 / Automated / CA-23,24,26,29,30,36 | Passed | jsdom, merged candidate | included in the EV-06 run | All Gamification suites pass, including the compact month grid and legend, the regular grid unchanged, the XP link in the title row and the engagement error cards. Calendar-page and XP-history tests are unedited and pass. |
| EV-09 | CI-09 / Automated / CA-01,30,31,35 | Passed | Playwright on the merged candidate, real Better Auth/Identity on the disposable stack (Postgres 54399, Redis 63799, API 7788, web 7100), controlled upstream for the three paths | `pnpm exec playwright test tests/shared/progress-panel-layout.test.ts` with the stack environment | 7/7 passed after the sync with `main` (which changed `vite.config.ts` and the route tree). Earlier runs: one cold-start timeout on the first test, then green. |
| EV-10 | CI-10 / Automated / CA-01 | Passed | same | `pnpm exec playwright test tests/gamification/gamification-layout.test.ts` | 13/13 passed on the merged candidate; `tests/shared/app-layout.test.ts` and the Mentor page scenarios also passed (30 selected tests). |
| EV-11 | CI-11 / Type | Passed | merged candidate | `uv run poe check:types` in `apps/server`; `pnpm exec tsc --noEmit` in `apps/web` | Server 0 errors, 0 warnings, 0 notes; web clean. |
| EV-12 | CI-12 / Lint, format, complexity lint | Passed | merged candidate | `uv run ruff check --no-fix src tests` and `uv run ruff format --check src tests` in `apps/server`; `pnpm exec biome check src tests vitest.config.ts playwright.config.ts dependency-cruiser.config.cjs` in `apps/web` | Zero diagnostics on 1932 server and 905 web files. The pre-commit root `biome check .` also reports 4 warnings, all in `packages/studio` (non-null assertions and `!important`), which this change does not touch (ACH-15). Ruff `C90` and Biome complexity rules are the gate; no metrics tool exists (Not applicable). |
| EV-13 | CI-13 / Architecture, test integrity, build | Passed | merged candidate | `uv run poe check:architecture` and `uv run poe build` in `apps/server`; `pnpm exec depcruise --config dependency-cruiser.config.cjs src` and `pnpm build` in `apps/web`; `pnpm check:test-integrity` at the root | Tach OK; Dependency Cruiser no violation (896 modules); both builds succeed. The test-integrity script still exits 1 only for `apps/server/tests/curriculum/providers/test_curriculum_content_provider.py` and `apps/server/tests/learning/server/controllers/test_ordering_response_models.py`, which this change does not touch and which exist on `origin/main` (ACH-03). No file of this change is flagged, which is the Spec's passing condition. |
| EV-14 | VM-01 / Manual / CA-01,08,29,31,35 | Passed | Playwright CLI session `shifu`, seeded learner on a seeded disposable DB (desktop), 2026-11-22; Playwright run with real auth and controlled upstream for the final candidate (390 px) | open `/gamification` → panel; requests; console; keyboard desktop and 390 px | Desktop: `/gamification` → `/gamification/overview`, h1 "Progresso", four tabs, both sections; API log 200 for `/learning/panorama`, its evolution and `/gamification/overview`; console 0 errors/0 warnings; the seed has no completed evaluations so the charts showed their explanation (filled values came from the controlled upstream). Keyboard: Tab reaches the chart, arrows change the tooltip, Tabela and back, Continuar opens the skill page. 390 px on the final candidate: Tab from the switch lands on the XP chart, ArrowRight fills the live tooltip, Tabela opens and the "XP mede engajamento, não conhecimento" text stays; no horizontal overflow. The desktop real-service run predates the revision-2 presentation edits; the journey they touch (switch, header link, month card, legend) is covered by CI-09 and the keyboard scenarios on the final candidate. Artifact: `apps/web/.playwright-cli/screenshots/overview-desktop-real-seed.png`. |
| EV-15 | VM-02 / Visual / desktop | Passed | Fresh Penpot export of board da96f6a1-…6000fe vs `overview-desktop-fixture.png` and `month-card-desktop.png` (controlled bodies mirroring the board, dark appearance, 2026-11-22 final candidate) | second independent visual review | First review FAILED (ACH-04). Corrections: border tokens for missed/today/legend/Não iniciadas, evolution last-value label (capture timing), then reviewed again: all five findings resolved, no remaining difference outside the accepted deviations. |
| EV-16 | VM-03 / Visual / mobile | Passed | board da96f6a1-…688d25 vs `overview-mobile-fixture.png` (fixed elements hidden for the image) | second independent visual review plus orchestrator inspection of the recapture | Second review PASS with one capture defect (the fixed bottom navigation overlaid the Continue card); recaptured with `display: none` on the fixed elements, and the Continue card now renders with title, Objetivo and Foco line, stage and full-width "Continuar". Resolved findings: "resultado final" caption, XP link in the title row with the switch below, outlines. |

Statuses: Pending, Passed, Failed, Blocked, Stale, Not applicable.

## Required manual and visual inventory

| Row | VM / CA | Surface / route | State / viewport | Penpot board | Artifact path | Observed result | Review disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| M-1 | VM-01 / CA-01 | `/gamification` → `/gamification/overview` | Desktop, real seeded session | n/a | `overview-desktop-real-seed.png` | Passed (EV-14) | n/a |
| M-2 | VM-01 / CA-08, CA-31 | Continuar link and chart keyboard path | Desktop | n/a | none (observations in EV-14) | Passed | n/a |
| M-3 | VM-01 / CA-29 | XP por semana text and Histórico de XP link | Desktop and 390 px | n/a | `overview-desktop-fixture.png` | Passed (text, header link, keyboard path in CI-09) | n/a |
| M-4 | VM-01 / CA-35 | Stacking, no horizontal overflow, keyboard | 390 × 844 | n/a | `overview-mobile-fixture.png` | Passed (overflow 0 px, keyboard path on the final candidate) | n/a |
| V-1 | VM-02 / CA-01, CA-19, CA-23, CA-24, CA-29, CA-36 | `/gamification/overview` | Filled, 1440 px | 🖥️ Desktop / "Progresso / Painel — Visão geral / Desktop" | `apps/web/.playwright-cli/screenshots/overview-desktop-fixture.png`, `month-card-desktop.png` | Passed | PASS (second visual review) |
| V-2 | VM-03 / CA-35 | `/gamification/overview` | Filled, 390 px | 📱 Mobile / "Progresso / Painel — Visão geral / Mobile" | `apps/web/.playwright-cli/screenshots/overview-mobile-fixture.png` | Passed | PASS (second visual review; Continue card confirmed in the recapture) |

All captures live under `apps/web/.playwright-cli/screenshots/` (ignored by Git).

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | `pnpm --filter web add` re-resolved unrelated lockfile entries. Regenerating with pnpm 10 (CI's major) reduced the diff to +337/-139 with only `recharts ^3.11.0` and `react-is ^19.3.1` as importer changes; the rest is pnpm re-resolving `latest`-tagged TanStack devtools and peer variants. | Low | CI-13 | Accepted limitation; frozen install and web build verified. |
| ACH-02 | Base `c0567b49` had two Alembic heads (`14fadc960949`, `46a3cef1cbec`): every Testcontainer test failed at `alembic upgrade head`. Not caused by this change; no migration here. | High (environment) | CI-03, CI-05, published CI | Resolved by `main`: the SHIFU-130 migration `e48385bfd6fe` merges both heads. The merged candidate has the single head and EV-03/EV-05 reran on it without a temporary migration. The separate task started for this is no longer needed. |
| ACH-03 | `pnpm check:test-integrity` fails on two server test files that predate the change. | Medium (pre-existing) | CI-13 | Open, outside scope; still failing on `main` after the sync. No new file flagged. |
| ACH-04 | Independent visual review FAIL: month card, card surface, XP link placement, Conquistas stretch, chart row heights, Domínios/Conquistas copy and dates, peak labels, Habilidades concluídas rhythm and mobile column, spacing, KPI copy; second pass found faint borders (global `border-color` rule overrides utilities, so the repo uses `!`), invisible "Não iniciadas" marker, missing "resultado final" on mobile, XP link placement on mobile, a capture-timing gap for the evolution label. | High | VM-02, VM-03 | Resolved. Contract-level differences settled by Q19-Q23 (Spec revision 2); code fixes for the rest; second review PASS. Accepted deviations are listed in the Design Contract. |
| ACH-05 | Implementation review: shared chart tooltip and value label belonged to `ChartFrame` although used by the two charts. | Medium | CI-06 | Resolved: promoted to `components/chart-tooltip` and `components/chart-value-label`; unused `isTableView` removed; CI-06 selection reran green. |
| ACH-06 | Implementation review: Engajamento summary error rendered one card while Learning renders two (CA-30). | Medium | CA-30, CI-08 | Resolved: two cards each with own retry; test updated. |
| ACH-07 | Implementation review: jade/latão card markers had no automated assertion (CA-36). | Medium | CI-07, CI-08 | Resolved: assertions added in both summary suites. |
| ACH-08 | Implementation review: RF-10 reading for an evolution series holding only the diagnostic base. | Medium (ambiguity) | CA-22, CI-07 | Resolved by Q23 = A: fewer than two points shows the explanation; hook tests cover 0, 1 and 2 points. |
| ACH-09 | Implementation review: private base averaging differs from the policy when a diagnostic Activity is re-observed in learning. The Spec defines the base from diagnostic rows, which the code follows. | Medium | CA-12, CI-02 | Resolved: added a parity test (diagnostic value kept when re-observed); 22 tests pass. |
| ACH-10 | Implementation review: weekly footnote disappears in Tabela view and in the empty state (RF-06). | Low | CI-07 | Resolved by Q21 = A: `ChartFrame.footnote` is visible in both views and the weekly card test asserts it in the table view; hidden in the empty state because no chart exists to qualify. |
| ACH-11 | Implementation review: keyboard at 390 px not automated; CA-34 overview half is synthetic; other low items (local date formatter near-duplicate, `Link` use as in objective-card precedent, no all-zero bar test). | Low | CA-35, CA-34 | Keyboard at 390 px recorded in EV-14; the others accepted or optional. |
| ACH-12 | Implementation review (revision-2 delta): practice-day fill `latao-tint` is nearly the card colour in the light theme (contrast about 1.0:1), so a practiced compact cell and its legend swatch were barely visible without colour cues (RF-12). | Medium | CA-24, CI-08 | Resolved: practice days and the swatch carry a thin latão border; recorded as an accepted deviation; the grid test asserts the border classes. |
| ACH-13 | Implementation review (revision-2 delta): test gaps (missed/neutral compact classes, regular grid unchanged, legend descriptions and aria-hidden swatches, XP link in the title row, weekly footnote in the table view) and the compact presentation map living in the widget entrypoint. | Low | CI-07, CI-08 | Resolved: assertions added; the map moved to `ui/gamification/constants/calendar-day-presentation.ts`. Light-theme VM captures are not required by the Spec and were not taken. |
| ACH-14 | Sync with `main`: the Preparação Prática format (SHIFU-130) now exists and its evaluations can be `closed_without_grade`. Repository queries already count only `COMPLETED` evaluations, so RF-06 and RF-07 hold, but no test covered the new status and the Spec said the format was not implemented. | Low | CA-09, CA-12, CI-01, CI-02, CI-03 | Resolved: the evolution use-case test and the panorama controller test now include a `closed_without_grade` attempt that is not counted; the RF-06 sentence in the Spec states the actual reason (contract unchanged, so no revision change). |
| ACH-15 | The pre-commit hook `npm run lint` (`biome check .`) reports 4 warnings, all in `packages/studio`. | Low (pre-existing) | CI-12 | Open, outside scope: the files are untouched by this change and fixing another package's lint is not part of SHIFU-133. |

# Lessons Learned

| Lesson | Supporting ACH/EV | Documentation action |
| --- | --- | --- |
| In this web app a global `border-color` rule overrides Tailwind border-colour utilities, so a border colour on a new element needs the `!` suffix as the existing calendar and stage markers use. A first compact month card rendered nearly invisible outlines until this was found by the visual review. | ACH-04, EV-15 | None: the pattern already exists in `calendar-day-presentation.ts`; no rule change warranted. |
| Recharts animates labels in after the line is drawn, so a capture taken right after the chart appears can miss the last-value label. Wait for the label (or the animation) and assert it before capturing. | ACH-04, EV-15 | None: a capture-procedure detail, recorded here only. |
| A full-page screenshot draws fixed elements (bottom navigation, Mentor button) mid-page; hide them with `display: none !important` for the image. | EV-16 | None. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | Branch `claude/shifu-133-spec-5249fe`: seven scoped delivery commits on base `c0567b49`, then `origin/main` `98b2aec8` merged (merge commit `ceb5c72f`); Spec, Evaluation and two added test cases are committed next. |
| Completed | All 37 criteria and all 16 checks have current passing proof (EV-01..EV-16); both reviews resolved. |
| Unfinished | None for this change. Local conclusion only; no publication requested. |
| Uncommitted work | None after the final delivery commit; no env file, storage state or screenshot is staged. |
| Active processes | None. The disposable Postgres/Redis containers, API, web and proxy processes and the Playwright CLI session were stopped after the last runs. Ports 7000 and 7777 belong to processes this task did not start and were left alone. |
| Blockers | None for this candidate. ACH-02 (two Alembic heads on `main`) needs its own fix; a separate task was started for it. |
| Next action | Publication through `create-pr`; then the PR checks decide completion. |

# Delivery

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| Learning RP-35, JN-27 | RF-02…RF-10, RF-15…RF-19 | CA-02…CA-22, CA-30…CA-36 | EV-01..EV-03, EV-06..EV-10, EV-14..EV-16 | implemented (full slice per the Spec) | unchanged |
| Learning RP-15, RP-16, RP-17, RP-19, RP-20, RP-21, RP-22, RP-25 | RF-03, RF-05…RF-09, RF-16, RF-18, RF-19 | CA-03, CA-06…CA-09, CA-12…CA-20, CA-32…CA-36 | EV-01..EV-03, EV-07, EV-09 | partially_implemented (only the read-side and presentation guarantees the Spec lists) | unchanged |
| Gamification RP-15, JN-16 | RF-01, RF-11…RF-19 | CA-01, CA-23…CA-37 | EV-04..EV-05, EV-08..EV-10, EV-14..EV-16 | implemented (full slice per the Spec) | unchanged |
| Gamification RP-01 | RF-01, RF-17 | CA-01, CA-32, CA-33 | EV-09, EV-10, EV-14 | partially_implemented (area titled Progresso with both sections; the optional navigation summary is deferred by the Spec) | unchanged |
| Gamification RP-04, RP-05, RP-06, RP-07, RP-08, RP-11, RP-13 | RF-11…RF-15, RF-18, RF-19 | CA-23…CA-31, CA-37 | EV-04, EV-05, EV-08, EV-09 | partially_implemented (presentation, XP by fact date, independent failure and accessibility only) | unchanged |

| Field | Result |
| --- | --- |
| Publication | Authorized by the explicit `conclude-spec` invocation: synchronized with `origin/main` (`98b2aec8`, merge `ceb5c72f`, one conflict in a re-export list resolved by keeping both sides), scoped commits created, PR creation follows. Spec stays `implemented` and Evaluation `ready` until the PR checks and review conversations are resolved. |
| Source verification | Learning PRD content 83066881 is still version 36 and Gamification PRD content 82903042 is still version 5 (read through Atlassian MCP at conclusion, summary and version metadata only; the complete pages were read in the Spec cycle). No authority conflict. |
| Documentation Alignment | Spec Documentation Alignment reconciled: PRD versions confirmed, Penpot boards re-exported fresh for the final visual review, modules and architecture unchanged. No change to Architecture, Modules, Rules, Tooling or Design documents is warranted: the lessons recorded above are feature-level details or already covered by existing code patterns. No Confluence checkbox or Jira status was changed; no Jira or Confluence write was requested. |
| Revision History | Revision 2 (Q19-Q23 reconciliation) on 2026-11-22; no change at conclusion. |
| Limitations | ACH-01 (lockfile re-resolution accepted). ACH-03 (two pre-existing test-integrity files) and ACH-15 (four Biome warnings in `packages/studio`) are base defects outside this change; ACH-02 was resolved by `main` and EV-03/EV-05 reran without a temporary migration. The light-theme month card was reviewed by the implementation reviewer, not captured. Task-owned servers, containers and the Playwright session were stopped. The merge to `main` brought SHIFU-130, whose Learning changes do not alter any panorama or overview contract. |
