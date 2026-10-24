---
title: XP history persistence and Histórico de XP tab evaluation
status: completed
spec: ./spec.md
last_updated_at: 2026-10-19
---

# Current State

| Field | State |
| --- | --- |
| Implementation | complete; CA-01–CA-20 implemented |
| Automated checks | 9/9 passed (CI-01–CI-09) |
| Type / lint / complexity | types Passed (EV-10); lint + format Passed (EV-11); architecture Passed (EV-12); complexity discharged by configured lint rules only, no quantitative tooling configured (EV-13); mutation Passed 48/48 (EV-14) |
| Manual checks | 1/1 passed (VM-01, EV-15) |
| Visual checks | 1/1 passed (VM-02, EV-16) with the Spec's five accepted deviations |
| Independent review | complete; Implementation Reviewer and Visual Reviewer run in parallel, both passed (ACH-05, ACH-06) |
| Blockers | none |
| Candidate | `feat/shifu-81` (branched from `feat/shifu-80` at `acb2afb`); uncommitted working tree, diff matches the Spec's expected file tree exactly |

Branch note: `SHIFU-81` extends the two-tab Gamification shell that `SHIFU-80`
delivered and which is not yet on `main` (`feat/shifu-80` is 8 commits ahead), so
this candidate stacks on that branch rather than on `main`.

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-08 | Complete | Passed | CI-02 (EV-02), CI-05 (EV-05) | — |
| CA-02 | RF-01 | Complete | Passed | CI-05 (EV-05) | — |
| CA-03 | RF-02 | Complete | Passed | CI-02 (EV-02), CI-01 (EV-01) | — |
| CA-04 | RF-02 | Complete | Passed | CI-02 (EV-02), CI-01 (EV-01) | — |
| CA-05 | RF-02 | Complete | Passed | CI-02 (EV-02), CI-01 (EV-01) | — |
| CA-06 | RF-02 | Complete | Passed | CI-02 (EV-02), CI-01 (EV-01) | — |
| CA-07 | RF-02 | Complete | Passed | CI-02 (EV-02) | — |
| CA-08 | RF-02, RF-09 | Complete | Passed | CI-01 (EV-01) | — |
| CA-09 | RF-03, RF-04 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03) | — |
| CA-10 | RF-03 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03) | — |
| CA-11 | RF-07 | Complete | Passed | CI-03 (EV-03) | — |
| CA-12 | RF-07 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03) | — |
| CA-13 | RF-07 | Complete | Passed | CI-04 (EV-04) | — |
| CA-14 | RF-05, RF-09 | Complete | Passed | CI-01 (EV-01), CI-04 (EV-04) | — |
| CA-15 | RF-03, RF-04, RF-10 | Complete | Passed | CI-06 (EV-06), CI-09 (EV-09), VM-01 (EV-15), VM-02 (EV-16) | — |
| CA-16 | RF-06 | Complete | Passed | CI-06 (EV-06); also observed live in EV-15 | — |
| CA-17 | RF-10 | Complete | Passed | CI-06 (EV-06), CI-08 (EV-08) | — |
| CA-18 | RF-10 | Complete | Passed | CI-06 (EV-06), CI-07 (EV-07), CI-08 (EV-08) | — |
| CA-19 | RF-10 | Complete | Passed | CI-07 (EV-07), VM-01 (EV-15), VM-02 (EV-16) | — |
| CA-20 | RF-05, RF-10 | Complete | Passed | CI-06 (EV-06), VM-02 (EV-16) | — |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-03–CA-06, CA-08–CA-10, CA-12, CA-14 | Passed | `feat/shifu-81`, 2026-10-19; mocked ports only, no Docker | `uv run pytest tests/gamification/core/use_cases/test_get_xp_history_use_case.py` from `apps/server` | **15 passed**, 1.19s. Covers ordering preservation, shared-instant pair, summed total, all four producing descriptors, achievement criterion from the account's own earned row, degraded `Conquista` without one, legacy label unchanged, both dates, 404, no-mutation-on-read, and per-repository account-id filtering. Mocked ports prove projection only; SQL ordering is EV-03. |
| EV-02 | CI-02 / Automated / CA-01, CA-03–CA-07 | Passed | `feat/shifu-81`, 2026-10-19; mocked ports | `uv run pytest` over the five use-case test files named in CI-02, from `apps/server` | **30 passed** (5+7+6+8+4). `test_list_achievements_use_case.py` (4 tests) passed **unedited**, which is the contracted guard that the criterion-helper extraction changed no behavior; `test_delete_gamification_profile_use_case.py` is CI-04's own proof artifact (EV-04), not part of this count. Fallback cases assert a created grant, never a dropped or raised one. Corrected from an earlier "31 passed" bookkeeping slip, found by the independent Implementation Reviewer and re-verified by direct rerun. |
| EV-03 | CI-03 / Automated / CA-09–CA-12 | Passed | `feat/shifu-81`, 2026-10-19; Testcontainers PostgreSQL (`pgvector/pgvector:0.8.1-pg17`) + Redis, real Alembic migrations through head `f01033e9cd81` | `uv run pytest tests/gamification/server/controllers/test_get_xp_history_controller.py` from `apps/server` | **7 passed**, 5.82s. Proves the repository read and its `granted_at DESC, id DESC` SQL ordering, which have no test of their own by rule. `totalXp` asserted equal to both the summed response amounts and the seeded `gamification_profiles.total_xp`. Isolation, empty set, 404 and 401 all asserted. Migration run confirms the Spec's single-head claim. |
| EV-04 | CI-04 / Automated / CA-13, CA-14 | Passed | `feat/shifu-81`, 2026-10-19; mocked ports | `uv run pytest tests/gamification/core/use_cases/test_delete_gamification_profile_use_case.py` | **2 passed**, file **unedited** — the contracted signal that this slice did not touch the deletion path. |
| EV-05 | CI-05 / Automated / CA-01, CA-02 | Passed | `feat/shifu-81`, 2026-10-19; disposable Inngest + PostgreSQL containers, `SHIFU_RUN_REAL_INNGEST_TESTS=1` | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/gamification` from `apps/server` | **11 passed**, 68.23s — the extended competency test plus every pre-existing Gamification job, so the messaging-composition change caused no regression. The competency test now seeds real Curriculum skill/competency/sequence rows so the **real** content provider resolves `Condicionais` end to end, and asserts a redelivery adds no second record. |
| EV-05a | CI-05 / Automated / CA-01, CA-02 | Failed (superseded) | same candidate, 2026-10-19 | same command | First directory run reported **11 skipped** with "FastAPI port 7777 is already occupied; Inngest fixture needs ownership" — the VM-01 isolated API still held the port. Recorded because a skip is never a pass; resolved by tearing down the VM-01 environment and re-running as EV-05. |
| EV-06 | CI-06 / Automated / CA-15–CA-18, CA-20 | Passed | `feat/shifu-81`, 2026-10-19; Vitest + jsdom | `pnpm --filter web exec vitest run src/ui/gamification/widgets/pages/gamification-page/xp-history-tab-panel/tests/xp-history-tab-panel.test.tsx` | **9 passed**. Role-first queries; order asserted on rendered row text, not mock indexes; `queryAllByRole('link')` and `queryAllByRole('button')` empty inside the record region; fact-date line asserted present on the differing row and absent on matching rows; no snapshots or class-name assertions. |
| EV-07 | CI-07 / Automated / CA-18, CA-19 | Passed | `feat/shifu-81`, 2026-10-19; Vitest + jsdom | `pnpm --filter web exec vitest run src/ui/gamification/widgets/pages/gamification-page/tests` | **17 passed** across 2 files. All three tabs asserted by role and `aria-selected`; header plus three tab triggers asserted on the loading and error branches; every pre-existing achievements/calendar assertion still passes. |
| EV-08 | CI-08 / Automated / CA-17, CA-18 | Passed | `feat/shifu-81`, 2026-10-19; Vitest + jsdom | `pnpm --filter web exec vitest run .../xp-history-tab-panel/tests/use-xp-history-tab-panel.test.ts` | **7 passed**. Complete public return contract asserted: all four states, returned entries and total on success, `isRetrying`, and the refetch call. |
| EV-09 | CI-09 / Automated / CA-15 | Passed | `feat/shifu-81`, 2026-10-19; Playwright, mocked `**/_serverFn/**` transport, dev web + API on 7000/7777 | `pnpm exec playwright test tests/gamification/gamification-page.test.ts` from `apps/web` | **4 passed**, 9.9s — the new XP-history case plus the 3 pre-existing cases. Asserts the `getXpHistory_*` server-function export is observed exactly once, keyboard tab activation, rendered order and total, and final URL. **Limit:** this fixture mocks the auth middleware and the transport, so it proves neither real authentication nor the upstream HTTP contract; EV-03 and EV-15 own those. |
| EV-10 | CI-10 / Automated / baseline — types | Passed | `feat/shifu-81`, 2026-10-19 | `uv run poe check:types` (`apps/server`); `pnpm --filter web check:types` | Server basedpyright **0 errors, 0 warnings, 0 notes**; web `tsc --noEmit` clean. Project configuration used, not a file list. |
| EV-11 | CI-10 / Automated / baseline — lint + format | Passed | `feat/shifu-81`, 2026-10-19 | `uv run ruff check --no-fix <changed .py>`; `uv run ruff format --check <changed .py>`; `pnpm exec biome check <changed web paths>` | Ruff: **All checks passed**, 25 files already formatted. Biome: clean after three real fixes (invalid `aria-label` on a non-role `div`, a `valueOf` global shadow, and formatting). An earlier run passed the `.rest` example file to Ruff and produced 17 spurious parse errors — selection error on my part, corrected to Python paths only. No source rewritten by the check commands. |
| EV-12 | CI-10 / Automated / baseline — architecture | Passed | `feat/shifu-81`, 2026-10-19 | `uv run poe check:architecture` (`apps/server`); `./node_modules/.bin/depcruise --config dependency-cruiser.config.cjs src` (`apps/web`, under Node 24) | Tach: **All modules validated** — Gamification still imports only `shifu.shared`. dependency-cruiser: **no dependency violations (462 modules, 1568 dependencies)**. The packaged `pnpm --filter web check:architecture` first failed because dependency-cruiser rejects this machine's default Node 25.2.1 (supports `^22\|\|^24\|\|>=26`); recovered without installing anything by running it under the already-present Node 24.20.0. |
| EV-13 | CI-10 / Automated / baseline — complexity | Passed (qualified) | `feat/shifu-81`, 2026-10-19 | configured complexity lint rules inside EV-11 | No dedicated metrics command, threshold or baseline is configured in this repository, so none was invented. Ruff `C90` and Biome's configured complexity rules reported **no diagnostics** on the changed paths. **No quantitative complexity score is claimed.** |
| EV-14 | CI-10 / Automated / mutation | Passed | `feat/shifu-81`, 2026-10-19; mutmut 3.8, no Docker | `uv run poe test:mutation --core --files src/shifu/gamification/core/use_cases/get_xp_history_use_case.py` from `apps/server` | **48/48 mutants killed (100%)**, 10.7s wall, ~10.5 mutations/second. First run was 45/48 with **3 survivors**; all three were the same real gap — the test never asserted that each repository read receives the authenticated account id, which is exactly how account isolation is enforced. Closed with `test_should_query_every_repository_with_the_owning_account_id`, after which no mutant survives. No equivalent-mutant deferrals. The five other changed core use cases were not locally targeted per the Spec; CI's `--all --core --shard N/12` 70% new-code gate still scores all six. |
| EV-15 | VM-01 / **Manual** / CA-15, CA-19 | Passed | `feat/shifu-81`, 2026-10-19; **isolated task-owned environment** — disposable PostgreSQL (`pgvector/pgvector:0.8.1-pg17`, port 55444) and disposable Redis (port 6399), real API on 7777 and real web on 7000 pointed at them; shared Compose data never touched | Real browser journey driven through the installed Playwright against real services; artifacts under `apps/web/.playwright-cli/` | Real sign-in through the **visible form** as the seeded active account `student.seed@shifu.com`. Histórico de XP reached **by keyboard** (focus confirmed on the tab, activated with Enter, `aria-selected=true`). Real API logged `GET /gamification/xp-history 200`. Rendered total **305 XP**; 5 records newest-concession-first (13 set → 8 set → 5 set → 2 set *Primeiro Passo* → 2 set *Lógica de programação*, the tied pair ordered by the `id` tiebreak); **sum of rendered amounts = 305 = displayed total**; Conquistas `Seu nível` card independently shows **305 XP**. Fact-date line present only on the differing record. 0 links and 0 buttons inside records. Narrow viewport 390×844: no horizontal overflow, 3 tabs reachable. Final URL `/gamification`. **No console errors.** Log: `.playwright-cli/logs/vm01-journey.log`. |
| EV-16 | VM-02 / **Visual** / CA-15, CA-19, CA-20 | Passed | `feat/shifu-81`, 2026-10-19; same isolated environment as EV-15 | Captured during the EV-15 journeys at 1440×900 and 390×844; **both images opened and inspected** against `design/u8vl4.png` | Desktop `.playwright-cli/screenshots/vm01-xp-history-desktop-1440x900.png`: header, tab bar, section title/description, `XP acumulado` + latao total, record card with `Origem`/`Concedido em`/`XP recebido` headers, per-row mark/title/descriptor/date/amount, and the preservation note all match the reference's hierarchy and token usage. Mobile `.playwright-cli/screenshots/vm02-xp-history-mobile-390x844.png`: all 5 records stack with the same reading order, no clipping, no horizontal overflow. **Accepted deviations observed exactly as recorded:** three tabs instead of four; no `Atividade` row; criterion wording reused from the Conquistas tab (`Conquista · 7 dias consecutivos` / `Conquista · 1 diagnóstico concluído` vs the reference's longer phrasings); the RF-06 fact-date second line, absent from the reference month; the mobile layout, which has no reference frame. |
| EV-16a | VM-02 / **Visual** / CA-19 | Failed (superseded) | same candidate, 2026-10-19 | first mobile capture during the EV-15 desktop journey | `.playwright-cli/screenshots/vm01-mobile-SUPERSEDED-429-error-state.png` captured the **error state**, not the record list: the journey's second `GET /gamification/xp-history` was rejected **429** by the shared Redis rate limiter, and the `retry: false` query surfaced the error branch. Caught only by opening the image — the automated overflow probe had reported "no overflow" against the error card. Resolved by moving the isolated API onto a disposable Redis and re-capturing as EV-16. Retained as evidence that a saved screenshot is not a pass. |

# Required manual and visual evidence inventory

| Row | VM / CA | Surface / route | State | Viewport | Reference | Candidate | Artifact path | Observed | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MV-1 | VM-01 / CA-15 | `/gamification` Histórico de XP tab | Populated, real authenticated data | 1440 × 900 | — (behavioral) | `feat/shifu-81` | `.playwright-cli/logs/vm01-journey.log` | Real 200 from the API; 5 ordered records; total 305 XP matching both the summed amounts and the Conquistas card; no console errors | **Passed** |
| MV-2 | VM-01 / CA-19 | `/gamification` Histórico de XP tab | Populated, keyboard-operated | 390 × 844 | — (behavioral) | `feat/shifu-81` | `.playwright-cli/logs/vm02-mobile.log` | Tab reached and activated by keyboard; 3 tabs reachable; 5 records; no horizontal overflow; no console errors | **Passed** |
| MV-3 | VM-02 / CA-15, CA-20 | `/gamification` Histórico de XP tab | Populated | 1440 × 900 | `design/u8vl4.png` node `u8vl4` | `feat/shifu-81` | `.playwright-cli/screenshots/vm01-xp-history-desktop-1440x900.png` | Inspected against the reference; hierarchy, row vocabulary and tokens match; deviations 1–3 and 5 observed as recorded | **Passed** |
| MV-4 | VM-02 / CA-19 | `/gamification` Histórico de XP tab | Populated, stacked rows | 390 × 844 | `design.md` §9 (no reference frame) | `feat/shifu-81` | `.playwright-cli/screenshots/vm02-xp-history-mobile-390x844.png` | Inspected; rows stack preserving reading order; no clipping or horizontal overflow | **Passed** (first attempt failed — see EV-16a) |

No `Atividade` row appears in any row above: `XpSource.ACTIVITY` has no producer
until `SHIFU-84`, as the Spec's Scope records.

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Mutation run left 3 survivors on `get_xp_history_use_case.py`: no test asserted that each repository read receives the authenticated account id, the mechanism behind RF-07 account isolation. Self-found via EV-14. Affects CA-11, CA-12. | medium | CI-01, CI-10 | **Resolved.** Added `test_should_query_every_repository_with_the_owning_account_id`; re-ran EV-14 → 48/48 killed. |
| ACH-02 | `aria-label` applied to a plain `div` in `xp-history-row` — invalid for its role, and it would have overridden the row's own text for assistive technology. Self-found via Biome `lint/a11y/useAriaPropsSupportedByRole` in EV-11. Affects CA-15, CA-20. | medium | CI-06, CI-10 | **Resolved.** Removed the attribute; the row's visible text already carries origin, kind, date and amount. `CI-06` now asserts those four facts on the row's own text content. |
| ACH-03 | First mobile visual capture showed the error state, not the record list, because the shared Redis rate limiter returned 429 on the journey's second history request. Self-found by opening the image. Affects CA-19. | medium | VM-02 | **Resolved.** Moved the isolated API onto a disposable Redis and re-captured (EV-16). The superseded image is retained and renamed to state its status. |
| ACH-04 | First real-Inngest directory run reported 11 skipped because the VM-01 isolated API still owned port 7777. Self-found via `-rs`. Affects CA-01, CA-02. | low | CI-05 | **Resolved.** Tore down the VM-01 environment and re-ran: 11 passed (EV-05). Recorded because a skipped job suite is Blocked, never a pass. |
| ACH-05 | Independent Implementation Reviewer traced CA-01–CA-20 against the diff, read the controller test and ran the cheap suites directly rather than trusting prose; verdict "genuinely satisfies the Spec", no correctness bugs or contract deviations found. Found EV-02's "31 passed" count did not reproduce (`30 passed`, 5+7+6+8+4) and folded in `test_delete_gamification_profile_use_case.py`, which is CI-04's own proof artifact, not CI-02's. | low | CI-02 | **Resolved.** EV-02 corrected to "30 passed" with the per-file breakdown and the file misattribution removed; re-verified by direct rerun. Documentation-only; no code change. |
| ACH-06 | Independent Visual Reviewer compared both passed captures against `u8vl4.png` row-by-row; verdict "matches the reference within the accepted deviations, no undisclosed visual defects". Noted two pre-existing, out-of-scope observations: the shared top-nav label reads "Progresso" rather than "Gamificação" (shipped by `SHIFU-80`), and a pre-existing floating assistant button slightly overlaps a row divider on the mobile capture without obscuring any record text. Also independently confirmed the superseded screenshot genuinely shows the 429 error branch, not mislabeled evidence. | none | VM-02 | **No correction needed** — both observations are pre-existing app chrome outside this Spec's scope, not XP-history defects. |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| A saved screenshot proves nothing until it is opened: the automated overflow probe reported "no horizontal overflow" against an error card that contained no records at all. | ACH-03, EV-16a | No documentation change needed — `AGENTS.md` and the implement prompt already require inspecting captures; this run is a concrete instance of why. |
| Mutation survivors on a read-only use case pointed at a genuine authorization gap rather than noise: the three survivors were all "pass a different account id", the exact mechanism RF-07 relies on. | ACH-01, EV-14 | Feature-local; no authority change warranted. |
| A local manual journey can be run fully isolated — disposable PostgreSQL **and** Redis plus task-owned API/web processes on the standard ports — so shared Compose data never has to be reseeded to obtain Spec-required evidence. | EV-15 | Candidate addition to `documentation/tooling.md` manual-evidence guidance; proposed, not applied, since it changes shared authority. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-81`, branched from `feat/shifu-80` at `acb2afb`; **no commits yet**, all work uncommitted in the working tree |
| Completed | CA-01–CA-20 implemented and verified; CI-01–CI-10, VM-01, VM-02 all passed; independent Implementation and Visual review both run and passed, with one documentation-only correction (ACH-05) |
| Unfinished | Documentation Alignment reconciliation of the two sibling Gamification specs deferred to conclusion |
| Uncommitted work | The 27 modified and 10 new paths listed by `git status`, matching the Spec's expected file tree, plus `documentation/features/gamification/xp-history/` (Spec, handoff, reference export, this Evaluation). No unrelated work in the tree. |
| Active processes | **None.** The task-started API (7777) and web (7000) processes were stopped; the disposable `shifu-vm01-postgres` and `shifu-vm01-redis` containers were removed. Shared Compose services left running, as `AGENTS.md` requires. |
| Blockers | none |
| Next action | Reconcile Documentation Alignment (the RP-08 `partial` notes in `../achievements/spec.md` and `../practice-calendar/spec.md`), then proceed to conclusion/publication per user instruction |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-01 | RF-07; CA-11, CA-12 | EV-01, EV-03 | partially_implemented — the history read is private to the owning account; the profile itself remains `SHIFU-82` |
| RP-04 | RF-09; CA-08, CA-14 | EV-01, EV-04 | partially_implemented — records are never recomputed; levels themselves remain `SHIFU-82` |
| RP-08 | RF-01–RF-06, RF-08, RF-09; CA-01–CA-16, CA-20 | EV-01–EV-06, EV-09, EV-15, EV-16 | implemented |
| RP-11 | RF-01; CA-01, CA-02 | EV-05 | partially_implemented — no duplicate record on redelivery for the sources that exist; activity XP recovery remains `SHIFU-84` |
| RP-12 | RF-07; CA-13 | EV-04 | partially_implemented — records purged inside the existing deletion path |
| RP-13 | RF-10; CA-15–CA-20 | EV-06–EV-09, EV-15, EV-16 | partially_implemented — responsive, pt-BR, keyboard-operable and non-colour-only for this tab |

| Field | Result |
| --- | --- |
| Publication | not requested — no commit, push or PR performed |
| Source verification | PRD — Gamification content ID `82903042` version 3, retrieved 2026-10-18; SHIFU-81. No Atlassian writes performed |
| Documentation Alignment | pending at conclusion: the RP-08 `partial` notes in `../achievements/spec.md` and `../practice-calendar/spec.md` become satisfied by this Spec; their `SHIFU-84` notes for RP-02 remain accurate |
| Revision History | no contract change since revision 1 |
| Limitations | `XpSource.ACTIVITY` has no producer until `SHIFU-84`, so no `Atividade` row could be verified in any state. EV-09 proves neither real authentication nor the upstream HTTP contract (mocked fixture). EV-13 claims no quantitative complexity score. EV-15/EV-16 grants were written by a disposable fixture through the real repositories rather than produced by live Learning facts; EV-05 proves that production path separately with real Inngest. |
