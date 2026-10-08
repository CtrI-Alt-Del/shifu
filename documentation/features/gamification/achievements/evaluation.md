---
title: Gamification achievements evaluation
status: completed
spec: ./spec.md
spec_revision: 1
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-79
prd_content_id: "82903042"
prd_version_note: Retrieved 2026-10-05; re-verify before conclude-spec.
last_updated_at: 2026-10-07
---

# Evaluation status

Implementation kicked off against `spec.md` revision 1 (`ready`) and
`plan.md` (`draft` → `in_progress` as of this kickoff). Pre-implementation
baseline: `apps/server/src/shifu/gamification` contains only empty
`__init__.py` skeletons plus an empty `rest/router.py`;
`apps/web/src/ui/gamification/widgets/pages/gamification-page/index.tsx` is
the static mock page; no Gamification tables exist (`alembic heads` →
`c9e4f6a7b8c1`, no Gamification revision). No pre-existing failures or
unrelated warnings recorded in this baseline beyond this absence of code.

Builder assignments across this implementation:

- `gamification-server-core-builder` — Plan phases F1 (domain/interfaces/
  database/migration) and F2 (use cases), Spec revision 1.
- `gamification-web-builder` — Plan phases F3 (web implementation) and F5
  (Playwright integration + manual evidence), Spec revision 1.
- `gamification-server-core-builder-fix` — Plan phase F4 (REST endpoint,
  Inngest jobs), resumed/continued the first Builder's F4 work and debugged
  `ACH-2`.

All assignments recorded before their respective feature-source edits, per
`implement-spec-prompt.md`'s fail-closed invariants.

**All five implementation phases (F1–F5) are complete and independently
verified by the Orchestrator** (not merely accepted from Builder reports),
including real-infrastructure evidence: the full server job suite, the
controller suite against a real Postgres Testcontainer, and the real browser
integration suite. The single Implementation Reviewer (Plan F6) ran against
the complete integrated candidate and found two genuine high-severity gaps
(`ACH-4`, `ACH-5`), both now fixed and re-verified against real
infrastructure. Five findings resolved in total (`ACH-1` through `ACH-5`);
none remain open.

# Acceptance coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01 | `test_create_gamification_profile_use_case.py`, `test_create_profile_on_account_activated_job.py` | fully proven, unit + real Inngest job | `passed` |
| CA-02 | RF-01 | `test_create_gamification_profile_use_case.py` | fully proven by unit test alone | `passed` |
| CA-03 | RF-02 | `test_recognize_diagnostic_completed_use_case.py`, `test_recognize_diagnostic_completed_job.py` | fully proven, unit + real Inngest job | `passed` |
| CA-04 | RF-02 | `test_recognize_diagnostic_completed_use_case.py` | fully proven by unit test alone | `passed` |
| CA-05 | RF-03 | `test_recognize_competency_mastered_use_case.py` | fully proven by unit test alone | `passed` |
| CA-06 | RF-03 | `test_recognize_competency_mastered_use_case.py` | fully proven by unit test alone | `passed` |
| CA-07 | RF-04 | `test_recognize_skill_completed_use_case.py` | fully proven by unit test alone | `passed` |
| CA-08 | RF-05 | `test_grant_xp_use_case.py` | fully proven by unit test alone | `passed` |
| CA-09 | RF-07 | `test_grant_xp_use_case.py` | fully proven by unit test alone | `passed` |
| CA-10 | RF-07 | `test_grant_xp_use_case.py` | fully proven by unit test alone | `passed` |
| CA-11 | RF-08 | `test_grant_xp_use_case.py` (cascade mechanism) plus, after `ACH-4`, the three `test_should_pass_the_fact_date_as_occurred_at_not_the_processing_time` unit tests and `test_recognize_diagnostic_completed_job.py::test_should_date_the_xp_grant_by_the_fact_date_not_the_processing_time` | fully proven end-to-end: mechanism (unit) + real wiring (unit + real Inngest job) | `passed` |
| CA-12 | RF-09 | `test_list_achievements_use_case.py` | fully proven by unit test alone | `passed` |
| CA-13 | RF-10 | `test_recognize_diagnostic_completed_job.py`, `test_recognize_skill_completed_job.py` | fully proven, real Inngest duplicate-delivery case | `passed` |
| CA-14 | RF-11 | `test_delete_gamification_profile_use_case.py`, `test_purge_profile_on_account_deleted_job.py` | fully proven, unit + real Inngest job | `passed` |
| CA-15 | RF-11 | `test_recognize_skill_completed_use_case.py` | fully proven by unit test alone | `passed` |
| CA-16 | RF-12 | `test_list_achievements_use_case.py`, `test_list_achievements_controller.py`, VM-01 | fully proven, unit + controller + manual | `passed` |
| CA-17 | RF-12 | `test_list_achievements_use_case.py` (server) plus, after `ACH-5`, `gamification-page.test.tsx::renders a retired-catalog achievement as historical, keyed by its code, in its own section` (web) | fully proven end-to-end: server unit + web component | `passed` |
| CA-18 | RF-13 | `gamification-page.test.tsx`, `apps/web/tests/gamification/gamification-page.test.ts`, VM-01, VM-02 | fully proven, web unit + Playwright + manual | `passed` |
| CA-19 | RF-13 | `gamification-page.test.tsx` | fully proven by web unit/component test alone | `passed` |

# Automated gates

| CI ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| CI-01 | `uv run poe check:lint` (server) | All new Python paths | `passed` | EV-1 |
| CI-02 | `uv run poe check:types` (server) | All new Python paths | `passed` | EV-1 |
| CI-03 | `uv run poe check:architecture` (server) | Module boundary (Gamification → Shared only) | `passed` | EV-1 |
| CI-04 | `uv run poe test:unit` (Gamification subset: 25 tests) + full server suite (125 passed, no regressions) | F2 use cases | `passed` | EV-2 |
| CI-05 | `uv run pytest tests/gamification/server/controllers -v` | F4 controller | `passed` | EV-6 |
| CI-06 | `uv run poe test:jobs` (full server job suite) | F4 jobs | `passed` — 12/12 | EV-8 |
| CI-07 | `pnpm --filter web check:lint` | All new web paths | `passed` | EV-3 |
| CI-08 | `pnpm --filter web check:types` | All new web paths | `passed` | EV-3 |
| CI-09 | `pnpm --filter web check:architecture` | Web layer boundaries | `passed` | EV-3 |
| CI-10 | `pnpm exec vitest run` (Gamification subset: 10 tests) + full web suite (177 passed, no regressions) | F3 widgets/hooks | `passed` | EV-4 |
| CI-11 | `pnpm --filter web test:integration` (Gamification suite) | F5 Playwright | `passed` — 2/2 | EV-9 |
| CI-12 | `uv run alembic upgrade head` / `downgrade -1` / `upgrade head` | F1 migration | `passed` | EV-5 |

# Manual and visual evidence

| VM | Scenario | Viewport/state | Reference | Artifact path | Observed result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| VM-01 | Achievements tab, desktop, obtained/locked states | `1280×800` | `documentation/design.md` §6.5 T33 | `/tmp/gamification-vm-evidence/vm-01-desktop.png` (original capture), `vm-01-desktop-recapture.png` (post-`ACH-3` fix, Orchestrator-verified) | Real level "02", "290 XP", "10 XP para o próximo nível"; 5 family headings; 3 obtained cards with unlock dates; locked cards with criterion + numeric progress; zero console/network errors; keyboard tab order clean. Post-fix recapture confirms Latão gold (not Selo red) on the level card and obtained-achievement icons/labels, matching `design.md` P1 | `passed` |
| VM-02 | Achievements tab, mobile viewport | `375×812` | `documentation/design.md` §6.5 T33 | `/tmp/gamification-vm-evidence/vm-02-mobile.png`, `vm-02-mobile-viewport-scrolled.png`, `vm-02-mobile-viewport-top.png` | Single-column reflow, shared `max-w-7xl` page shell retained, no horizontal scroll (`scrollWidth === clientWidth` confirmed programmatically) | `passed` |

# Review findings

The Spec-authoring-stage Spec Reviewer findings (6 total: 1 blocking, 4
medium, 1 low) were already resolved before the Spec became `ready` and are
recorded in `spec.md`'s revision history, not here. The implementation
Builders surfaced `ACH-1` through `ACH-3` below; the Implementation Reviewer
(Plan F6, see its full result after this table) surfaced `ACH-4` and `ACH-5`.

| ACH | Classification | Source | Affected evidence | Status | Resolution |
| --- | --- | --- | --- | --- | --- |
| ACH-1 | in-Contract correction, medium | `gamification-web-builder` (F3), flagged rather than guessed | F3's `use-gamification-page.ts` (interim XP/level approximation, now superseded), spec.md REST/Use-case/Domain/Web-supporting-paths rows | `resolved` | The original Technical Contract's `GET /gamification/achievements` returned only the achievement list, leaving `ProfileSummaryCard` (Design Contract) with no sanctioned source for `level`/`totalXp`/`xpForNextLevel`, even though RF-13 already required real level/XP on this page. Classified in-Contract (RF-13 already mandated the behavior; this only completes how the Technical Contract delivers it — no new product behavior, module boundary or architecture). Fix: `ListAchievementsUseCase` now returns `AchievementsOverview` (`level, total_xp, xp_for_next_level, achievements`); the controller's `Response` carries all four; `leveling.py` gained `xp_required_for_level`. Web's `Achievement`-adjacent contract gained `AchievementsOverview`; `gamification-service.ts`/`achievements-provider.ts`/`get-achievements.ts` return it instead of a bare achievement array. Spec revision unchanged (1) per the in-Contract-correction rule. Both Builders notified to implement the corrected shape. |
| ACH-2 | test defect (not a Contract or production-code issue), low | Orchestrator's independent F4-T2 verification run | `test_recognize_competency_mastered_job.py`, `test_recognize_diagnostic_completed_job.py`, `test_recognize_skill_completed_job.py` | `resolved` | 3/12 real-Inngest job tests failed on first run (`wait_for_database` timeout). Root cause A (all three): each test's event was the account's first-ever milestone of its type, so `GrantXpUseCase`'s cascade correctly also unlocked the matching threshold-1 "first X" catalog achievement in the same transaction — the tests' expected `total_xp`/grant-count values predated this and were simply wrong (competency 50→75, skill 100→150, diagnostic 60→85, matching `dominio-primeiro-dominio`=25/`conclusao-primeira-jornada`=50/`diagnostico-primeiro-passo`=25 exactly). Root cause B (diagnostic only): its curriculum seed was missing `CurriculumSequence` rows, so `DatabaseCurriculumContentProvider.get_skill_content` correctly returned `None` and the use case correctly no-op'd. Both confirmed by manual reproduction against the real Postgres, bypassing Inngest. Fix touched only the three test files (expected values + seed data) — zero production-code changes. Full regression (`uv run poe test:jobs`, unscoped): 12/12 passed. |
| ACH-3 | design-system nonconformance, medium | Orchestrator's independent VM-01 visual re-verification | `apps/web/src/ui/shared/styles/global.css`, `profile-summary-card/index.tsx`, `achievement-card/index.tsx` | `resolved` | The F5 Builder's original VM-01 screenshot rendered the level card and obtained-achievement icons/labels in Selo red (`bg-primary`/`text-primary`), not the Latão gold/brass `documentation/design.md` §3.1 reserves exclusively for Gamification content (P1: "Latão nunca toca em nada pedagógico... [e Selo não toca em recompensa]"). Root cause: the five `--latao-*`/`--on-latao` CSS variables were simply never added to `apps/web/src/ui/shared/styles/global.css` (only `--jade-tint`/`--selo-text` exist so far) — not a case of ignoring an existing token, since none existed to use. Fix: added the five variables with the exact hex values from `design.md` §3.2, and switched `ProfileSummaryCard`'s card background/text and `AchievementCard`'s obtained-state icon background/icon color/state-label color to the new `latao-*`/`on-latao` Tailwind utilities (locked/historical states correctly stay neutral `muted-foreground`, matching design.md's "estados que não sejam sucesso ou erro usam neutro"). Re-verified: lint/types clean, Gamification Vitest (10/10) and Playwright (2/2) still green, VM-01 recaptured and visually confirmed correct. |
| ACH-4 | in-Contract defect, high | Implementation Reviewer (F6) | `gamification/messaging/inngest/jobs/recognize_{diagnostic_completed,competency_mastered,skill_completed}_job.py`, `core/use_cases/recognize_{diagnostic_completed,competency_mastered,skill_completed}_use_case.py`, their unit tests, `test_recognize_diagnostic_completed_job.py` | `resolved` | RF-08 requires "An achievement's recorded unlock date is the date its criterion was first satisfied, even when recognized later (retroactive evaluation, late-arriving fact...)". `GrantXpUseCase` correctly supports this via its `occurred_at`-vs-`now` split (unit-tested in isolation), but every job's `_normalize_payload` validated the Learning event's own fact timestamp (`completed_at`/`mastered_at`) and then discarded it — every `Recognize*UseCase.execute` took only `now` and passed it as both `occurred_at` and `now` to the cascade. A real late-arriving fact (exactly RP-11/RF-10's own downtime-recovery scenario) would always be dated to processing time, never its actual fact date. No existing test caught this because none exercised a real `occurred_at ≠ now` scenario through the actual job wiring. Fix: all three jobs now thread the event's own timestamp field through `_normalize_payload` into `_recognize`, parsed via the existing `_parse_utc_iso` helper; all three use cases now take an explicit `occurred_at: datetime` parameter (separate from `now`) and pass it through to `GrantXpUseCase.apply_within_transaction`. Added `test_should_pass_the_fact_date_as_occurred_at_not_the_processing_time` to each of the three use-case unit test files, and `test_should_date_the_xp_grant_by_the_fact_date_not_the_processing_time` to the real-Inngest diagnostic job test (publishes an event with a historical `completed_at` and asserts the resulting `XpGrantModel.occurred_at` equals that historical date, not the processing timestamp) — closing exactly the coverage gap the Reviewer identified. Re-verified: 28/28 use-case+controller unit tests, 13/13 real-Inngest Gamification job tests (new backdating test included), full server unit suite 128/128, lint/types/architecture clean. |
| ACH-5 | in-Contract defect (cross-Builder contract mismatch), high | Implementation Reviewer (F6) | `apps/web/src/core/gamification/achievement.ts`, `use-gamification-page.ts` (`groupByFamily`), `achievement-card/index.tsx`, new `historical-achievements-section/` | `resolved` | The server's `ListAchievementsUseCase._historical_view` correctly returns a `historical` `AchievementView` with `family=None` (plus `name`/`description`/`criterion_label`/`xp_reward=None`) for a retired-but-held achievement code, per CA-17 ("no catalog metadata beyond the stored code"), and this is proven server-side by `test_should_mark_unknown_catalog_code_as_historical_only_for_holder`. On the web side, `groupByFamily` grouped strictly by the 5 known `AchievementFamily` values; a historical entry's `family=null` matched none of them and was silently dropped — never rendered anywhere, with no historical-state test anywhere in the web suite. The `Achievement` TypeScript type was also non-nullable for those 5 fields, a type-contract mismatch with the real server response for `state === 'historical'`. Fix: `Achievement.family`/`name`/`description`/`criterionLabel`/`xpReward` are now `| null`; `useGamificationPage` now also returns `historicalAchievements` (filtered separately from the family grouping); a new `HistoricalAchievementsSection` widget renders them in their own "Histórico" section on the page; `AchievementCard` falls back to `achievement.code` as its heading when `name` is null and conditionally omits `description`/`criterionLabel` when absent. Added `test_should_mark_unknown_catalog_code_as_historical_only_for_holder`'s web-side counterpart (`renders a retired-catalog achievement as historical, keyed by its code, in its own section`) to `gamification-page.test.tsx`. Re-verified: 11/11 Gamification Vitest, 178/178 full web suite, 2/2 Playwright, lint/types/architecture clean. |

## Implementation Reviewer Result (Plan F6)

- **Reviewer:** Implementation Reviewer
- **Status:** completed
- **Spec revision:** `documentation/features/gamification/achievements/spec.md`, revision 1
- **Candidate scope:** complete integrated SHIFU-79 diff (server Gamification core/database/rest/messaging + migration + `app.py` composition + rest-client; web `gamification-page` widget tree + `core/gamification` + `provision/gamification` + `rest/services/gamification-service.ts` + `global.css` Latão tokens + Playwright suite)
- **Review commands:** independently reran every automated gate (server `check:lint`/`check:types`/`check:architecture`, `pytest tests/gamification` 28/28, real-Inngest `test:jobs` 12/12, web `vitest run` full suite 177/177, `check:types`/`check:lint`/`check:architecture`, Playwright `tests/gamification` 2/2) — all matched or exceeded the Orchestrator's own evidence log. Attempted a live-stack VM re-drive; blocked by a pre-existing local Compose-Postgres schema/seed gap unrelated to this delivery, so visual conformance was established via direct code/token inspection plus the passing mocked Playwright suite as the permitted fallback proxy.
- **Findings:** 2 high (`ACH-4` backdating wiring gap, `ACH-5` historical-achievement cross-Builder contract mismatch), 1 low informational (CA-19's empty state is structurally present and tested but not reachable through any real server response, since the catalog is never empty in practice — no action taken, accepted as-is), plus explicit `none` findings confirming structural conformance, REST-client parity, the shared-transaction/cascade mechanism, the Latão fix, and `AchievementFamily` casing consistency.
- **Disposition:** both high findings verified as real by the Orchestrator and fixed (see `ACH-4`/`ACH-5` above); all affected automated gates rerun and passing on the corrected candidate. The Reviewer was not re-invoked after the fix (both corrections were narrow, mechanically verified by rerunning the exact gates the Reviewer itself used, and well within the already-reviewed Rule Pack/architecture boundaries) — the Orchestrator owns this closing verification per the Implementation Reviewer's own "advisory, not official evidence" contract.

# Evidence log

| EV | Date | Scope | Exact command/scenario | Result | Finding | Runtime notes | Acceptance mapping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EV-0 | 2026-10-05 | Baseline | `find apps/server/src/shifu/gamification -type f`; `cd apps/server && uv run alembic heads` | Confirmed empty skeletons; single head `c9e4f6a7b8c1` | none | Docker services already running (`shifu-postgres`, `shifu-inngest`, `shifu-redis`, `shifu-mailpit`) | baseline for all CA-* |
| EV-1 | 2026-10-05 | F1/F2 server structural checks (Orchestrator-independent rerun, not just the Builder's report) | `uv run poe check:lint`; `uv run poe check:types`; `uv run poe check:architecture` from `apps/server` | All three: pass, 0 errors/warnings/notes, no module-boundary violations | none | Re-inspected `gamification_profile.py` (literal `id` field, confirmed against `entity.py`), `grant_xp_use_case.py` (shared-transaction `apply_within_transaction` pattern, confirmed), `rewarded_milestones_repository.py` (`try_add`/`remove_many_by_account_id`, confirmed), migration file (`down_revision='c9e4f6a7b8c1'`, 4 tables, confirmed) before trusting the report | CI-01, CI-02, CI-03 |
| EV-2 | 2026-10-05 | F2 Gamification use-case unit tests | `uv run pytest tests/gamification/core/use_cases -v` (25 tests); `uv run poe test:unit` (full server, 125 tests) | 25/25 and 125/125 passed, no regressions | none | Includes CA-09/CA-10/CA-11's cascade-stabilization and backdating cases (`test_should_unlock_level_and_count_achievements_in_the_same_cascade`, `test_should_backdate_a_directly_triggered_unlock_and_now_date_a_cascaded_one`) | CI-04; CA-02,04,05,06,07,08,09,10,11,12,15,17 |
| EV-3 | 2026-10-05 | F3 web structural checks (Orchestrator-independent rerun) | `pnpm --filter web check:lint`; `pnpm --filter web check:types`; `PATH=".../node-v24.20.0/bin:$PATH" pnpm --filter web check:architecture` from repo root | All three: pass, no dependency violations (250 modules, 829 dependencies cruised) | none | `check:architecture` requires Node 24 (dependency-cruiser incompatible with the shell default Node 25.2.1) — pre-existing environment quirk, not introduced by this delivery | CI-07, CI-08, CI-09 |
| EV-4 | 2026-10-05 | F3 Gamification web unit/component tests | `pnpm exec vitest run src/ui/gamification` (10 tests) and full suite `pnpm exec vitest run` (177 tests) from `apps/web` | 10/10 and 177/177 passed, no regressions | none | Includes the `ACH-1` correction's rewritten `use-gamification-page.test.ts` passing the real `AchievementsOverview` through unchanged | CI-10; CA-19 |
| EV-5 | 2026-10-05 | F1 migration reversibility (Orchestrator-independent rerun) | `uv run --env-file .env.local alembic downgrade -1` then `upgrade head` from `apps/server`, against the already-running Compose Postgres | Both succeed; schema matches the up-front `upgrade head` the Builder already ran | none | — | CI-12 |
| EV-6 | 2026-10-06 | F4-T1 controller integration test, rerun after `app.py` wiring (F4-T3) and after a session restart | `uv run pytest tests/gamification/server/controllers -v` from `apps/server` | 3/3 passed (obtained+locked overview, profile-absent zeroed overview, unauthenticated 401); migration chain applied clean from scratch in the same run | none | Confirms F4-T1 and F4-T3 together, independent of the F4-T2 job runtime | CI-05; CA-16 (unit+controller portion) |
| EV-7 | 2026-10-06 | F4-T2 real Inngest job integration tests, first full run after `app.py` wiring | `uv run poe test:jobs -- tests/messaging/inngest/jobs/gamification -v` from `apps/server`, real Inngest Dev Server + Postgres Testcontainers, ~5 min | 9/12 passed. 3 failed: `test_recognize_competency_mastered_job.py::test_should_grant_fifty_xp_once_on_first_mastery`, `test_recognize_diagnostic_completed_job.py::test_should_grant_xp_once_per_competency_under_duplicate_event_delivery`, `test_recognize_skill_completed_job.py::test_should_grant_xp_once_under_duplicate_event_delivery` — all three `wait_for_database` timeouts despite Inngest logging `function.finished` for each | `ACH-2` opened, see EV-8 for resolution | superseded by EV-8 |
| EV-8 | 2026-10-06 | F4-T2 fix verification and full regression | `gamification-server-core-builder-fix`'s targeted reruns, then Orchestrator-independent `uv run poe test:jobs` (full server job suite, unscoped) from `apps/server`, 29.57s | **12/12 passed** — all 5 Gamification job tests plus 2 Communication + 4 Identity + 1 Learning job tests, no regressions. Confirmed the catalog math by hand: `diagnostico-primeiro-passo`=25, `dominio-primeiro-dominio`=25, `conclusao-primeira-jornada`=50 XP, matching the corrected test expectations exactly (diagnostic 60→85, competency 50→75, skill 100→150) | `ACH-2` resolved: both root causes (achievement-cascade bonus XP not accounted for in 3 tests' expectations; missing `CurriculumSequence` seed rows in the diagnostic test specifically) were test-only bugs. Zero production-code changes were needed or made — `grant_xp_use_case.py`, `database/curriculum_content_provider.py`, and all other core/database files are untouched from their F1/F2 state | CI-06; CA-01, CA-03, CA-05, CA-07, CA-13, CA-14 — all now fully evidenced at both unit and job-integration level |
| EV-9 | 2026-10-06 | F5 real browser integration and VM-01/VM-02, Orchestrator-independent rerun | `pnpm exec playwright test tests/gamification --reporter=line` from `apps/web`, real FastAPI (`uv run uvicorn main:app`) + real web dev server, after `ACH-3`'s color fix | 2/2 passed (`protects gamification and renders it for an active session`; `renders the real level/XP header and the achievement grid grouped by family`) | `ACH-3` opened and resolved in this same entry — see `ACH-3` row for root cause/fix; VM-01 recaptured post-fix via a temporary screenshot line in the already-passing mocked test (reverted immediately after capture, confirmed via `grep` no leftover), visually inspected and confirmed Latão gold rendering correctly | CI-11; CA-16, CA-18; VM-01, VM-02 |
| EV-10 | 2026-10-06 | Post-implementation full regression (web) | `pnpm --filter web check:lint`/`check:types`; `pnpm exec vitest run` (177 tests) from `apps/web` | All pass, no regressions from the `ACH-3` styling change | none | — | CI-07, CI-08, CI-10 (reconfirmed) |
| EV-11 | 2026-10-07 | F6 Implementation Reviewer, first pass against the complete integrated candidate | Full independent rerun of every automated gate plus manual code-path tracing and cross-Builder contract comparison (see the Implementation Reviewer Result block above for the complete command list) | All existing automated gates reconfirmed green; 2 high findings opened from direct code inspection (no existing test caught either) | `ACH-4`, `ACH-5` opened — see their rows and EV-12/EV-13 for resolution | superseded by EV-12/EV-13 |
| EV-12 | 2026-10-07 | `ACH-4` fix and verification (RF-08/CA-11 backdating wiring) | `uv run pytest tests/gamification/core/use_cases -v` (28 tests, 3 new); `uv run poe test:jobs -- tests/messaging/inngest/jobs/gamification -v` (13 tests, 1 new, real Inngest + Postgres); `uv run poe test:unit` (full server, 128 tests); `uv run poe check:lint`/`check:types`/`check:architecture` — all from `apps/server` | All green: 28/28, 13/13 (twice, including a final post-formatting confirmation run), 128/128, lint/types/architecture clean | `ACH-4` resolved | Fix threads each job's own event timestamp (`completed_at`/`mastered_at`) through as `occurred_at`, separate from the processing-time `now`; new tests publish an event with a historical fact date through the real Inngest runtime and assert the resulting `XpGrantModel.occurred_at` equals that date | CA-11 |
| EV-13 | 2026-10-07 | `ACH-5` fix and verification (RF-12/CA-17 historical-achievement web rendering) | `pnpm check:types`; `pnpm check:lint`; `pnpm exec vitest run src/ui/gamification` (11 tests, 1 new); `pnpm exec vitest run` (full, 178 tests); `pnpm exec playwright test tests/gamification --reporter=line` (2 tests) — all from `apps/web` | All green: types/lint clean, 11/11, 178/178, 2/2 | `ACH-5` resolved | `Achievement`'s 5 catalog-metadata fields are now nullable, matching the real server response for `state==='historical'`; a new `HistoricalAchievementsSection` widget renders them separately from the family-grouped sections; `AchievementCard` falls back to `code` as its heading when `name` is null | CA-17, CA-18 |
| EV-14 | 2026-10-07 | Final full-workspace regression after both F6 fixes (`ACH-4` + `ACH-5` together) | `apps/server`: `uv run poe check:lint`, `check:types`, `check:architecture`, `uv run pytest tests/gamification -v` (31/31), `uv run poe test:jobs` (13/13, full server job suite unscoped). `apps/web`: `pnpm check:types`, `pnpm check:lint`, `PATH=.../node-v24.20.0/bin:$PATH pnpm check:architecture`, `pnpm exec vitest run` (178/178), `pnpm exec playwright test tests/gamification` (2/2) | Every gate green on both applications, no regressions from either fix, no stray dev-server processes left running (confirmed via `ps aux`) | none | This is the final integrated-candidate confirmation referenced by the Final conformance record below | all CA-* |

# Documentation and PRD traceability

Canonical PRD: [Shifu — PRD — Gamification](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/82903042/Shifu+PRD+Gamification),
content ID `82903042`, version 3 (last edited 2026-10-04, before this Spec's
2026-10-05 retrieval) — re-fetched and spot-checked unchanged at this
conclude-spec preflight (2026-10-07): RP-04's level formula, RP-07's complete
12-row catalog table, RP-08's required XP-record fields, and RP-12's account
lifecycle rules all match what `spec.md` was authored against. No PRD drift
during implementation. No Confluence checkbox was read, checked or unchecked
by this workflow.

| RP/JN | RF coverage | CA coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- | --- |
| RP-01 | RF-01 | CA-01, CA-02 | EV-2, EV-7, EV-8 | partially_implemented — single global profile with correct initial state (0 XP, level 1) is delivered; the PRD's "resumo no shell" (nav-bar summary) is `SHIFU-82`'s scope, not this delivery | unchanged |
| RP-03 | RF-02, RF-03, RF-04 | CA-03–CA-11 | EV-2, EV-7, EV-8, EV-12 | partially_implemented — diagnostic/mastery/first-completion XP delivered; Activity-score XP (RP-02, not selected for this Spec) remains `SHIFU-84`'s scope | unchanged |
| RP-04 | RF-05 | CA-08 | EV-2 | partially_implemented — level formula and the never-decreases ratchet are delivered; the dedicated "anel de nível" overview UI is `SHIFU-82`'s scope | unchanged |
| RP-05 | — | — | — | not_implemented (explicitly deferred, see `spec.md` scope table) — `max_streak_days` column exists but no producer populates it; owned by `SHIFU-80` | unchanged |
| RP-06 | — | — | — | not_applicable for this delivery slice — calendar UI is `SHIFU-80`'s scope | unchanged |
| RP-07 | RF-06, RF-07, RF-08, RF-09 | CA-06, CA-09, CA-10, CA-11, CA-12, CA-16, CA-17 | EV-2, EV-6, EV-12, EV-13 | partially_implemented — catalog, cascade, retroactive backdating (post-`ACH-4`), retirement/historical handling (post-`ACH-5`) and the Achievements tab are delivered for Diagnóstico/Domínio/Conclusão/Nível; Sequência stays catalogued but unreachable until `SHIFU-80` populates streak data | unchanged |
| RP-08 | RF-08 | CA-11, CA-12 | EV-2, EV-12 | partially_implemented — only the minimal dedup/history facts needed to prevent duplicate recognition; the learner-facing XP History tab is `SHIFU-81`'s scope | unchanged |
| RP-09 | — | — | — | not_applicable — explicitly excluded by Jira SHIFU-79, tracked separately by `SHIFU-115` | unchanged |
| RP-10 | — | — | — | not_applicable — not selected for this delivery | unchanged |
| RP-11 | RF-10 | CA-13 | EV-7, EV-8, EV-14 | implemented — real-Inngest duplicate-delivery idempotency proven for the three Learning-fact consumers | unchanged |
| RP-12 | RF-11 | CA-14, CA-15 | EV-2, EV-7, EV-8 | partially_implemented — consumer-side purge against the stable `identity/account.deleted` contract is implemented and tested directly; a real end-to-end deletion flow is blocked on Identity, which has no current producer for that event (accepted external dependency, recorded in `spec.md`) | unchanged |
| RP-13 | RF-12, RF-13 | CA-16, CA-18, CA-19 | EV-4, EV-9, EV-13 | implemented (for the delivered Achievements-tab surface) — responsive, pt-BR, keyboard-operable, explicit loading/empty/error states | unchanged |
| JN-01 | RF-01 | CA-01, CA-02 | EV-2, EV-7 | partially_implemented — profile starts correctly; full area per JN-01 is `SHIFU-82` | unchanged |
| JN-03 | RF-02–RF-04 | CA-03–CA-11 | EV-2, EV-12 | partially_implemented — milestone recognition delivered; grouped celebration return (RP-09) excluded | unchanged |
| JN-05 | RF-08 | CA-11 | EV-12 | implemented — late-arriving-fact backdating proven end-to-end post-`ACH-4` | unchanged |
| JN-07 | RF-07 | CA-09, CA-10 | EV-2 | implemented — cascade-until-stable proven (two-simultaneous-threshold case) | unchanged |
| JN-08 | RF-07 | CA-12 | EV-2 | implemented — catalog-addition reconciliation against preserved history proven | unchanged |
| JN-11 | RF-10 | CA-13 | EV-7, EV-8 | implemented | unchanged |
| JN-12 | RF-09 | CA-12 | EV-2 | implemented | unchanged |
| JN-13 | RF-11 | CA-14 | EV-2, EV-7 | partially_implemented — same RP-12 external-dependency caveat as above | unchanged |

Not selected for this Spec and therefore not scored above: RP-02 (`SHIFU-84`),
RP-06 (`SHIFU-80`), RP-09 (`SHIFU-115`), RP-10 (not selected); JN-02, JN-04,
JN-06, JN-09, JN-10 (same reasons). This mirrors `spec.md`'s own scope table
and introduces no new exclusion.

# Findings disposition and lessons learned

| ACH | Reusable lesson? | Authority disposition |
| --- | --- | --- |
| ACH-1 | No — feature-specific Technical Contract gap caught during authoring-adjacent implementation, not an ambiguous or missing Rule | No change. `documentation/rules/rest-layer-rules.md`'s "Keep contracts synchronized" already states the general principle; the gap was in this Spec's first draft, not the Rule. |
| ACH-2 | No — feature-specific test-math mistake (achievement cascade bonus XP not accounted for) | No change. `documentation/rules/use-case-testing-rules.md` already requires covering "event publication and complete event payloads"; the lesson is Gamification-catalog-specific, not a generalizable testing pitfall. |
| ACH-3 | No — one-off token-infrastructure gap (Latão variables never added), not a Rule ambiguity | No change. `documentation/design.md` §3.1's three-hue rule is already unambiguous; the gap was an implementation omission the Implementation Reviewer's/Orchestrator's own visual-gate process caught, exactly as `implement-spec-prompt.md`'s design gate is meant to. |
| ACH-4 | Considered — "a job that validates a payload field but never forwards it to its use case" is a real, somewhat generalizable pitfall shape | No change. `documentation/rules/messaging-layer-rules.md` already requires payloads to "contain only the identifiers and immutable data required by consumers" and requires jobs to "normalize a payload" correctly; the defect was an implementation lapse within an already-correct Rule, not evidence the Rule itself is missing or unclear. Recording a narrow addendum here risks overfitting one feature's mistake into global guidance. |
| ACH-5 | Considered — "a TypeScript type mirroring a server DTO must model per-state field nullability, not just the happy-path shape" is a recurring pitfall class | No change. `documentation/rules/ui-layer-rules.md` and `rest-layer-rules.md` already require contract synchronization end-to-end; this was a one-field nullability mismatch the Implementation Reviewer's cross-Builder contract check caught, which is exactly the control the Rule Pack already relies on (the review gate itself), not a sign the Rule Pack needs new text. |

No durable authority file was modified as a result of this delivery's
findings, per the explicit caution against overfitting global guidance with
feature-local details.

# Final conformance record

- **Spec:** `spec.md`, revision 1, status `implemented`.
- **Plan:** `plan.md`, phases F1–F6 all `completed`.
- **Builder/Plan scope vs. complete diff:** matches exactly — independently
  re-verified file-by-file against `spec.md`'s Technical/Design Contract
  tables during the F6 Implementation Reviewer pass (see its result block
  above); no extra, missing or misplaced path.
- **Required file/widget tree:** confirmed complete, including the `ACH-5`
  addition (`historical-achievements-section/`) which extends but does not
  contradict the original Design Contract's widget hierarchy — the Spec's RF-12
  already required historical achievements to be visible; this is the
  completion of that requirement, not a new surface.
- **Generated-file treatment:** migration `50cab7ec9bb5` reviewed, applies and
  reverses cleanly (EV-5); `app.py` diff reviewed for composition correctness
  (EV-1, EV-6); no other generated artifacts affected.
- **Contract obligations/exclusions:** all 19 `CA-*` have current `passed`
  evidence (Acceptance coverage table above); RP-02/RP-05/RP-06/RP-09/RP-10
  remain explicitly out of scope per `spec.md`, unchanged by this conclusion.
- **Current evidence:** every `CA-*` and both `VM-*` have current evidence IDs
  (EV-0 through EV-14); no stale or superseded row remains uncorrected (EV-7
  explicitly marked superseded by EV-8; EV-11 explicitly marked superseded by
  EV-12/EV-13, both carried through to this record).
- **Automated/runtime/REST-client/manual/visual results:** all current and
  passing — see Automated gates and Manual and visual evidence tables above.
- **Limitations:** the Implementation Reviewer's live-stack VM re-drive was
  blocked by a pre-existing local Compose-Postgres schema/seed gap unrelated to
  this delivery (recorded, not a Gamification defect); `identity/account.deleted`
  has no current Identity producer (accepted external dependency, recorded in
  `spec.md` and above).
- **Unresolved findings:** none. All five (`ACH-1`–`ACH-5`) resolved with
  current, re-verified evidence.
