---
title: Mentor — confirmed actions evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-10-23
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for all 15 criteria (Learning, Intelligence, Web and composition integrated; review corrections ACH-07..ACH-14 applied) |
| Automated checks | CI-01–CI-10, CI-13 Passed on the final tree (EV-01–EV-15, EV-19); CI-12: migration Passed (EV-17), test integrity Failed on 2 pre-existing files (EV-18); CI-11 Not applicable (EV-16) |
| Type / lint / complexity | Server types, Ruff lint incl. C90, format, Tach: Passed (EV-09–EV-12). Web types, Biome incl. complexity lint, dependency-cruiser: Passed (EV-13–EV-15). Dedicated metrics: Not applicable (EV-16) |
| Manual checks | 2/2 Passed against real services (VM-01 EV-22, VM-02 EV-23) with local Curriculum Skills instead of "Funções em Python" |
| Visual checks | 2/2 Passed (VM-03, VM-04): V-01..V-05 "Pass with approved adaptation" |
| Independent review | Implementation Review: FAIL → corrections → targeted recheck Resolved (one new finding N1/ACH-14 fixed afterwards, covered by a new test; not rechecked by the reviewer). Visual Review: PASS. |
| Blockers | None. EV-18 `check:test-integrity` still fails on 2 tracked files not touched by this delivery; the user explicitly waived it (2026-10-23) and it is recorded as a limitation, not a pass. |
| Candidate | Branch `feat/shifu-104` on base `1488c943`; delivery committed locally (5 code commits `87551942`, `e2453592`, `a225afe9`, `d6e3a34f`, `6ddfd7cb` plus the documentation commit); not pushed yet; unrelated work: none |

Baseline facts (Spec revision 1, 2026-10-23): branch equals `main`; no feature source existed; Docker Compose services up; `.codegraph/` present; local database was at Alembic head `e862236a33c8` (now `847da98f9bb2`, additive migration applied for the manual journeys).

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-04 | Complete | Passed | CI-03 EV-03, CI-06 EV-06, CI-13 EV-19, VM-01 EV-22 |
| CA-02 | RF-02, RF-14 | Complete | Passed | CI-03, CI-07 EV-07, CI-08 EV-08, VM-01 |
| CA-03 | RF-01, RF-02 | Complete | Passed | CI-03, CI-06, CI-13 |
| CA-04 | RF-04 | Complete | Passed | CI-03, CI-04 EV-04, CI-06, CI-07 |
| CA-05 | RF-05, RF-11 | Complete | Passed | CI-03, CI-04, CI-07 |
| CA-06 | RF-03, RF-14 | Complete | Passed | CI-03, CI-06, CI-07, CI-13, VM-02 EV-23 |
| CA-07 | RF-06 | Complete | Passed | CI-01 EV-01, CI-02 EV-02 |
| CA-08 | RF-07 | Complete | Passed | CI-01, CI-02 |
| CA-09 | RF-08 | Complete | Passed | CI-01, CI-02 |
| CA-10 | RF-09 | Complete | Passed | CI-03, CI-05 EV-05 |
| CA-11 | RF-10 | Complete | Passed | CI-07, CI-08 |
| CA-12 | RF-11 | Complete | Passed | CI-03, CI-04, CI-07, CI-08 |
| CA-13 | RF-12 | Complete | Passed | CI-07, CI-08, VM-01 |
| CA-14 | RF-13 | Complete | Passed | CI-03, CI-04, CI-05; conversation deletion also observed in the real database during cleanup |
| CA-15 | RF-14 | Complete | Passed | CI-07, CI-08 (EV-08), VM-01–VM-04 (EV-22, EV-23), visual review PASS | None. Keyboard focus ring on picker options not evidenced in a capture (ACH-15, accepted). |

# Check Results

Candidate for all rows: branch `feat/shifu-104` on `1488c943` plus the uncommitted delivery diff, Spec revision 1, 2026-10-23, unless noted. "Compose DB" is the shared local PostgreSQL; server test suites use disposable Testcontainers.

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-07–09 | Passed | 2026-10-23; no external services | `cd apps/server && uv run pytest -p no:tach tests/learning/core/use_cases/test_add_skill_to_goal_from_mentor_use_case.py tests/learning/core/use_cases/test_remove_skill_experience_from_mentor_use_case.py` | 34 passed (18 add, 16 remove) in 3.7 s. Every outcome of CI-01 covered. |
| EV-02 | CI-02 / Automated / CA-07–09 | Passed | 2026-10-23; PostgreSQL Testcontainer at Alembic head `847da98f9bb2` | `cd apps/server && uv run pytest tests/learning/server/controllers/test_add_skill_to_goal_from_mentor_controller.py tests/learning/server/controllers/test_remove_skill_experience_from_mentor_controller.py` | 44 passed in 117 s. Includes outbox row assertions, 422, 401 without receipt, foreign Objective, cascade removal, stale removal after re-add and two concurrent identical requests. |
| EV-03 | CI-03 / Automated / CA-01–06, 10, 12, 14 | Passed | 2026-10-23, final tree after the N1 fix | `cd apps/server && uv run pytest -p no:tach <the 11 Intelligence files of CI-03 + the 2 Learning use-case files>` | 302 passed in 28 s (34 Learning + 268 Intelligence): two-action split, skill resolution, question veto in the planner. |
| EV-04 | CI-04 / Automated / CA-04, 05, 12, 14 | Passed | 2026-10-23, final tree; PostgreSQL Testcontainer | `cd apps/server && uv run pytest -p no:tach <3 controller files of CI-04>` (run together with EV-02 and EV-06) | 23 passed, including 2 new DB-backed negative tests (cancel/fail removal filter; event hydration with current state). |
| EV-05 | CI-05 / Automated / CA-10, 14 | Passed | 2026-10-23 (rerun on the final tree: 16 passed, 0 skipped); disposable Inngest + PostgreSQL | `cd apps/server && SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest -p no:tach tests/messaging/inngest/jobs/intelligence/test_record_mentor_action_outcome_job.py tests/messaging/inngest/jobs/intelligence/test_purge_mentor_action_proposals_on_account_deleted_job.py -rs` | 16 passed, 0 skipped, 75 s. Registered functions exercised. |
| EV-06 | CI-06 / Automated / CA-01, 03, 04, 06 | Passed | 2026-10-23, final tree after the N1 fix; real local route provider and spaCy, stubbed index similarities | `cd apps/server && uv run pytest -p no:tach tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py` | 38 passed in 118 s. Combined controller run on the final tree before N1: EV-02 44 + EV-04 23 + workflow 38 = 105 passed in 228 s. N1 touches only the planner, which none of the controllers reach; EV-02 and EV-04 retained. |
| EV-07 | CI-07 / Automated / CA-02, 04, 05, 11–13, 15 | Passed | 2026-10-23, rerun after styling corrections | `pnpm --filter web exec vitest run <11 files of CI-07>` (repo root) | 11 files, 306 tests passed in 8.5 s. Full web unit suite (builder run, before corrections): 138 files, 1222 tests passed. |
| EV-08 | CI-08 / Automated / CA-02, 11–13, 15 | Passed | 2026-10-23, final web tree; real FastAPI process on 7777 for the readiness probe; all BFF transport mocked | `pnpm --filter web exec playwright test tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts tests/learning/goal-detail-page.test.ts --workers=2` (repo root) | 55 passed (16 new) twice (2.2 min, then 1.6 min after the styling and swap-link corrections). With the default 6 workers two earlier runs failed 1 then 2 different tests with 30 s timeouts under load (including a pre-existing memory test); each passed three times alone. Limit: mocked transport does not prove persistence (VM-01/VM-02 do). |
| EV-09 | CI-09 / Server types | Passed | 2026-10-23 | `cd apps/server && uv run poe check:types` | 0 errors, 0 warnings, 0 notes (basedpyright strict). |
| EV-10 | CI-09 / Server lint incl. C90 complexity | Passed | 2026-10-23 | `uv run ruff check --no-fix <130 changed Python paths>` | All checks passed after fixing UP035/E-format in the new migration. Complexity: configured C90 only. |
| EV-11 | CI-09 / Server format | Passed | 2026-10-23 | `uv run ruff format --check <130 changed paths>` | 130 files already formatted (after formatting `app.py` and the migration). |
| EV-12 | CI-09 / Server architecture | Passed | 2026-10-23 | `uv run poe check:architecture` | "All modules validated" (no Learning ↔ Intelligence import). |
| EV-13 | CI-10 / Web types | Passed | 2026-10-23 | `pnpm --filter web check:types` | tsc --noEmit: no errors. |
| EV-14 | CI-10 / Web lint incl. complexity lint | Passed | 2026-10-23 | `pnpm exec biome check <41 changed web paths>` | 0 errors; 8 warnings `useSemanticElements` for `role='status'`/`role='group'`, same pattern as the existing composer. Complexity: configured Biome rules only. |
| EV-15 | CI-10 / Web architecture | Passed | 2026-10-23 | `pnpm --filter web check:architecture` | 582 modules, no dependency violations. |
| EV-16 | CI-11 / Complexity metrics | Not applicable | 2026-10-23 | none | No configured metrics runner (Tooling); Spec records it as unavailable and not required. EV-10 and EV-14 are the configured gates. |
| EV-17 | CI-12 / Migration up/down/up + data preflight + drift | Passed | 2026-10-23; disposable databases created inside the Compose server (`shifu_mig_104`, `shifu_mig_104b` = copy of the local database), both dropped afterwards | `cd apps/server && DATABASE_URL=<disposable> uv run alembic upgrade head`; `downgrade -1`; `upgrade head`; `alembic check` | Upgrade, downgrade and re-upgrade succeeded; `alembic check`: "No new upgrade operations detected". Preflight on the copy: event kinds before and after upgrade identical (block 25, completed 21, status 54). Constraints present: `uq_learning_mentor_action_receipt_confirmation`, `ck_mentor_action_proposal_resolution`, `ck_mentor_event_kind` (widened), `ck_mentor_event_action_shape`. Autogenerate did not emit CHECK changes or the FK name; both written by hand. |
| EV-18 | CI-12 / Test integrity | Failed (pre-existing); waived by the user 2026-10-23 | 2026-10-23 | `pnpm check:test-integrity` (root) | Fails on `apps/server/tests/curriculum/core/domain/test_react_question.py` and `apps/web/src/rest/services/tests/gamification-service.test.ts`: both tracked, unmodified by this delivery and outside its scope. No file of this delivery is flagged (confirmed by the Implementation Reviewer's own run). This is a waiver, not a pass: the check remains Failed for the repository baseline, and the user explicitly accepted proceeding to readiness and conclusion with it recorded as a limitation. |
| EV-19 | CI-13 / Intent calibration eval | Passed | 2026-10-23; local E5 model, in-memory index, double mode | `cd apps/server && uv run python evals/run.py --workflow classify-mentor-intent` | 13/13 cases passed in ~15 s (final tree, dataset `mentor-intents-synthetic-50a76cb4b829`). After the F2 data additions: add_skill precision 1.0 / recall 0.923 (24/26); remove_skill precision 1.0 / recall 0.96 (24/25); hard-negative false-positive rate 0.0 (0 of 62, including 20 question/conditional sentences); out-of-domain FP 0/2; no corpus leakage. Three polite requests with "?" fall below the embedding threshold (recall stays above the 0.70 gate). Earlier run before F2: recall 1.0/1.0 over 45 hard negatives. Thresholds: add_skill 0.8888, remove_skill 0.90044 (lowest calibration positive − 0.005). Report: `apps/server/test-results/evals/classify-mentor-intent.json` (ignored). Limit: embedding thresholds alone admit many hard negatives; see ACH-01 (lexical request gate). In-memory repository compared to pgvector `find_nearest`: same ordering, max similarity difference 1.6e-7. |
| EV-20 | Baseline / Web build | Passed | 2026-10-23 | `pnpm --filter web build` | Built in 2.3 s. Web types, Biome and dependency-cruiser also rerun green on the final tree. |
| EV-21 | Baseline / Full server unit-integration regression of untouched modules | Not applicable | — | — | Selection policy: only scoped tests and direct consumers (Tooling). Direct consumers run: Learning use cases (346), Intelligence use cases (886 by the builder), session/submit controllers. |
| EV-22 | VM-01 / Manual / CA-01, 02, 13, 15 | Passed (fixture adapted) | 2026-10-23 21:29–21:38 UTC-3; web `pnpm --filter web dev` on 7000, API on 7777 with Inngest Dev Server (both new functions registered), account `student.seed@shifu.com`, Compose DB migrated to head, 1440×900 | Playwright CLI session `shifu`: created Objective A (contains "Decisões em algoritmos") and B ("Lógica de programação") through the UI; `/intelligence` → new message "Adicione Decisões em algoritmos ao meu Objetivo" → keyboard: focus Objective B, Enter, "Trocar Objetivo" visible, focus "Adicionar habilidade", Enter → success → composer enabled → "Ver Objetivo" via keyboard → Objective page list view | Picker listed the account's Objectives with A disabled "Já contém esta Habilidade". After confirmation: proposal `completed/added` (Inngest job), Learning receipt `add_skill/added`, experience with justification "Você pediu ao Mentor para adicionar esta Habilidade. Prática de condições…", composer enabled, 0 console errors. Objective page: justification visible read-only in the list view (the default graph view does not render it; the Spec names `GoalSkillRow`, which is the list view). Fixture adaptation: the local Curriculum has no "Funções em Python"; Skills used: "Decisões em algoritmos" and "Lógica de programação". Reload persistence of the card was observed in the second run (reload re-rendered the pending proposal). Screenshots: `apps/web/.playwright-cli/screenshots/shifu-104-vm01-*.png`. Cleanup: Objectives and conversations removed through the UI. |
| EV-23 | VM-02 / Manual / CA-06, 15 | Passed (fixture adapted) | Same environment, 390×844, FAB on `/learning/goals/<B>` | Playwright CLI: open FAB, send "Remova Decisões em algoritmos deste Objetivo", read consequences, keyboard Enter on "Remover habilidade", "Ver Objetivo" | Consequences visible above the button, no modal, buttons stacked full width, proposal `completed/removed`, receipt `remove_skill/removed`, Objective B kept with 1 remaining Skill and the Skill node gone, composer enabled, 0 console errors. Run twice (second to retake captures). Screenshots: `shifu-104-vm02-*`, `shifu-104-vm04-*`. |
| EV-24 | Delivery / migration applied to the Compose database | Passed | 2026-10-23 | `uv run --env-file .env.local alembic upgrade head` (apps/server) | Required by the manual journeys; additive migration only, no reset/reseed. The Mentor index was rebuilt by `python -m shifu.mentor_indexes` (authorized, Q50): version `dd88bd0d…`, 247 vectors, previous version deactivated, no rows deleted. |

## Required Manual and Visual inventory

Reference column uses the saved images under `design/references/`. Artifact paths are under `apps/web/.playwright-cli/screenshots/`.

| Row | VM / CA | Surface / route | State | Viewport | Reference | Candidate | Artifact path | Observed result | Review disposition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M-01 | VM-01 / CA-01, 02, 13, 15 | Page `/intelligence` | Add journey (request → picker → pick → "Trocar Objetivo" → confirm → success → composer enabled → "Ver Objetivo" → Objective page) | 1440×900 | — | Working tree after card width and outline corrections for V-captures; journey itself run twice | `shifu-104-vm01-*.png` | Passed (EV-22) | Reviewed in this record; no separate reviewer role |
| M-02 | VM-02 / CA-06, 15 | FAB on `/learning/goals/<id>` | Remove journey (request → consequences → keyboard confirm → removed → composer unblocked → "Ver Objetivo") | 390×844 | — | Same | `shifu-104-vm02-*.png` | Passed (EV-23) | Reviewed in this record; no separate reviewer role |
| V-01 | VM-03 / CA-02, 15 | Page | Picker step | 1440×900 | AyIMM | Final styling, then improved on user request (ACH-16; new title row, wrapped options): `shifu-104-picker-improved-1440.png`, mobile `shifu-104-picker-improved-390.png` | `shifu-104-vm03-picker-1440.png` | Anatomy matches: "Objetivo" label, outline option buttons, disabled option with "Já contém esta Habilidade", hint, 640 px card. Deviations: extra "Recusar" button (needed to unblock the composer; recorded ACH-02); option text and border now use `text-foreground!`/`border-control-border!`. | Visual Reviewer: Pass with approved adaptation |
| V-02 | VM-03 / CA-01, 15 | Page | Add proposal | 1440×900 | XOwCJ, Zel1j | Final styling (re-captured after the swap-link fix: `shifu-104-vm03-proposal-final-1440.png`) | `shifu-104-vm03-proposal-1440.png`, `shifu-104-vm03-proposal-final-1440.png` | Matches: jade icon box, title, "Objetivo:" line, reason, outline "Recusar" and primary "Adicionar habilidade", 640 px. Adaptations: "Trocar Objetivo" link (approved Q7/Q44); reason uses the explicit-request sentence + Curriculum description. | Visual Reviewer: Pass with approved adaptation |
| V-03 | VM-03 / CA-11, 15 | Page | Add success | 1440×900 | Fbn2b (add completed) | Final styling | `shifu-104-vm03-success-1440.png` | Matches: jade icon, title "<Habilidade> adicionada", Objective line, result text, status line, outline "Ver Objetivo". Focus ring visible on the status region after the move. | Visual Reviewer: Pass with approved adaptation |
| V-04 | VM-04 / CA-06, 15 | FAB | Removal proposal | 390×844 | EmQFg, BbWyG | Final styling | `shifu-104-vm04-proposal-390.png` | Matches: full-width card, danger icon box, consequences copy before the buttons, stacked full-width outline "Recusar" and danger "Remover habilidade". | Visual Reviewer: Pass with approved adaptation |
| V-05 | VM-04 / CA-06, 15 | FAB | Removal success | 390×844 | Fbn2b (success) | Final styling | `shifu-104-vm04-success-390.png` | Matches: muted trash icon box, "<Habilidade> removida", result "A experiência e seu histórico foram removidos. O Objetivo permanece disponível.", status line "Remoção concluída", full-width outline "Ver Objetivo" (stacked below 480 px, approved). | Visual Reviewer: Pass with approved adaptation |

# Findings

Independent Implementation Review (report 1, FAIL: 2 major) and Visual Review (PASS, no blocking) ran on the same integrated candidate on 2026-10-23. A targeted recheck of the corrected scope followed.

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Embedding similarity alone cannot isolate action requests (29 of 45 hard negatives would classify as actions). The AI builder added a deterministic `LexicalMentorActionRequestProvider` (matching-direction verb + "Objetivo"/"Habilidade", no wh-/question/conditional opener, no negation) that must agree with the embedding verdict; `EmbeddingsMentorIntentClassifierProvider.classify(query, text)` gained the `text` argument. Observable consequence: a request without the word Objetivo/Habilidade gets no card. Reviewer (F3) accepts it as in-contract provided it is documented; the Spec's mapping and file tree do not list it. | Medium (documentation) | CI-13, CI-06, VM-01 | Resolved as an accepted, recorded implementation note; no Spec amendment made (RF-01 already requires an explicit request). The lists live only in the lexical provider and do not change the intents resource version. Open question for the user: add the note to the Spec's AI-routing row (revision 2). |
| ACH-02 | The picker step has a "Recusar" button that AyIMM does not draw (needed so a learner can unblock the composer when every Objective is disabled). | Low | CI-07, VM-03 | Accepted deviation; visual reviewer: Pass with approved adaptation. Not yet listed in the handoff. |
| ACH-03 | Manual capture showed the card at full conversation width (reference 640 px) and muted outline text/border (Button `ghost` + appended `text-foreground`, no class merging). | Low | VM-03, VM-04, CI-08 | Resolved: `max-w-[640px]`, `border-control-border!`/`text-foreground!`; captures retaken; CI-07 306 and CI-08 55 passed on the final tree (EV-07, EV-08). |
| ACH-04 | One sentence "Adicione X … e remova Y …" was resolved over the whole clause (CA-04). | Medium | CA-04, CI-03, CI-06 | Resolved: planner splits before a plain "e"/"e também" followed by an add/remove verb; tests added. |
| ACH-05 | Planner copy and eligibility narrowing (Spec silent): Skill page restricts resolution to the hinted Skill; new pt-BR texts "<S> não está no Objetivo <O>.", "<S> não está em nenhum dos seus Objetivos.", "<S> já está em todos os seus Objetivos.". | Low | CA-03 | Accepted (follows the Spec's "existing eligibility filter"). |
| ACH-06 | `check:test-integrity` fails on two unrelated tracked files (EV-18). | Low (process) | CI-12 | Waived by the user (2026-10-23); recorded as a limitation. Not caused by this delivery; fix belongs to a separate maintenance change. |
| ACH-07 (F1) | Planner accepted a single search result even when the message named a different Skill (search matches any token in title or description), e.g. on the "Funções em Python" page "Remova React em Python do meu Objetivo" produced a removal card for "Funções em Python"; arbitrary Skills in the ambiguity list. | Major | CA-01, CA-03, CA-06, CI-03 | Resolved: title must occur in the part, or every content word of the single candidate's title must be a token of the part; ambiguity list filtered to related Skills; `TestPrepareMentorActionSkillResolution` (stub mimicking real `search` with Skill-page eligibility). Reviewer recheck: Resolved. |
| ACH-08 (F2) | Questions and purpose/conditional sentences ("Posso adicionar Habilidades ao meu Objetivo?", "Se eu remover X do Objetivo, perco o progresso?") passed the lexical gate. | Major | CA-01, CA-03, CI-13 | Resolved: question-mark veto (except polite "pode/poderia/consegue…"), openers vetoed, 20 gated hard negatives and 5 polite positives added to `mentor-evaluation.json`; eval 13/13, add recall 0.923, remove recall 0.96, hard-negative FP 0/62. Three polite requests with "?" fall below the embedding threshold (recall still above the 0.70 gate). Reviewer recheck: Resolved. |
| ACH-09 (F4a/F4b) | Cancel/fail removal filter and event hydration with current state were asserted only through mocked calls. | Minor | CA-14, CA-05, CI-04 | Resolved: DB-backed tests `test_should_remove_only_the_pending_proposals_of_a_cancelled_attempt` and `test_should_replay_the_action_event_with_the_current_state_of_the_proposal`. Reviewer recheck: Resolved. |
| ACH-10 (F5) | Only a 503 maps to `failed`; other statuses (401/403/404/422/500) map to `uncertain` (only "Verificar resultado"), so deterministic errors leave the composer blocked until the outcome arrives or the learner reloads; the locked Objective is lost on reload. | Minor | CA-11 | Accepted limitation: matches the Spec's classification (503 with body → failed; network, timeout, missing body, 409 → uncertain); Spec is silent on other statuses. |
| ACH-11 (F6/F7) | Differences from Spec text: card uses `renderLink` instead of `href` (typed Link); stream+detail merge lives in the context provider, discriminator is `kind`; `DEFAULT_ADD_JUSTIFICATION` duplicates the server literal and is unreachable; `MentorActionPlanner` (two public classes, plain dataclass) and `MentorActionReceiptRecorder` are helpers, not `*UseCase`. | Minor | RF-14 | Accepted; behavior equivalent and tested. |
| ACH-12 (F8) | `intelligence.rest` pending-409 example reused a submission key. | Minor | REST examples | Resolved (fresh `pendingSubmissionKey`, labels corrected). |
| ACH-13 (F9/F10) | Goal row lock is taken before the ownership check (response identical for missing/foreign Objective); the intents resource version changed, so any environment (including CI evals) needs `python -m shifu.mentor_indexes` before release. | Note | RF-08, CI-13 | Recorded. EV-24 covers the local database only. |
| ACH-14 (N1) | After the F2 fix the planner re-routes message parts without their "?", so a question part could pass the gate there. | Minor–medium | CA-04, CI-03 | Correction requested from the core builder; verification below. |
| ACH-15 (visual) | Visual review (PASS, V-01..V-05 "Pass with approved adaptation"): unlisted small differences — "Trocar Objetivo" inset and low contrast; 44 px / 15 px buttons and options vs 38 px / 13 px reference (44 px required by CA-15); option gap 10 px vs 12; no keyboard focus ring evidenced on picker options. No required visual state is missing for VM-03/VM-04. | Low | VM-03, VM-04 | "Trocar Objetivo" fixed (now brighter, ~8 px inset) and recaptured (`shifu-104-vm03-proposal-final-1440.png`); the rest recorded as accepted (44 px from CA-15; font size cosmetic). |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| `Button` appends `className` without merging, so conflicting `text-*`/`border-*` utilities depend on CSS order; use the Tailwind 4 `!` suffix for outline mappings over `ghost`. | ACH-03 | The handoff's mapping row ("`Button variant=ghost` + `border border-control-border text-foreground`") is incomplete; no repository-wide rule change proposed. |
| Playwright route suites with the default worker count are load-sensitive against the Vite dev server; `--workers=2` is stable here. | EV-08 | Recorded locally; no documentation change proposed. |
| Autogenerate does not emit CHECK changes and leaves unnamed FKs unnamed; migrations that widen CHECKs must be written by hand. | EV-17 | Already covered by the Database Rule ("review"); no change. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-104` on base `1488c943`; commits `87551942` (Learning routes + shared port), `e2453592` (migration), `a225afe9` (local intent routing), `d6e3a34f` (Intelligence proposals/decline/jobs/composition), `6ddfd7cb` (web), then the documentation commit |
| Completed | All implementation scopes; CI-01–CI-10, CI-13; CI-12 migration part; VM-01–VM-04 with review dispositions; ACH-07..ACH-15 resolved or accepted |
| Unfinished | Conclusion steps (PRD version recheck); optional Spec note for the lexical request gate (ACH-01); `modules.md` wording reviewed and left unchanged ("Intelligence forwards the confirmed action" stays accurate: the Intelligence web card forwards to Learning's routes) |
| Uncommitted work | None after the documentation commit. Delivery paths (for reference): `apps/server` (shared, learning, intelligence, fakers, migration `847da98f9bb2`, evals, tests, rest-client), `apps/web` (core, rest, ui/intelligence, tests, `tests/support/mentor-actions-backend.ts`), `documentation/features/intelligence/mentor-actions/` (spec, design, this file). Browser captures are ignored files under `apps/web/.playwright-cli/`. |
| Active processes | None (API, web dev server and Playwright session stopped; disposable databases dropped; the shared Compose services were left running) |
| Blockers | None (EV-18 waived by the user) |
| Next action | `create-pr` pushes the branch and opens or updates the delivery PR; then record the head SHA, current-head CI and review conversations, and set both artifacts `completed` only after they pass |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| Intelligence RP-17, JN-21, JN-22 | RF-01–RF-05, RF-09–RF-14 / CA-01–CA-06, CA-10–CA-15 | EV-03–EV-08, EV-19, EV-22, EV-23 | implemented (inferred-difficulty variant deferred by the Spec) |
| Intelligence RP-06 (v10 partial), RP-03, RP-11, RP-12, RP-13, RP-14 (partial) | RF-04, RF-05, RF-11, RF-13, RF-14 | EV-03–EV-05, EV-07, EV-08 | Implemented; independent review resolved |
| Learning RP-03, RP-21, RP-23, JN-14 (Mentor path), JN-23, RP-29 (partial) | RF-06–RF-09 / CA-07–CA-09 | EV-01, EV-02, EV-17 | Implemented; receipts await Learning's account purge (recorded gap) |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| Not applicable | — | — | — |

| Field | Result |
| --- | --- |
| Publication | Authorized by the explicit conclude-spec request (2026-10-23). Commits created (see Handoff); `create-pr` pending: branch not pushed, no PR yet |
| Synchronization | `git fetch origin main` at 2026-10-23: `origin/main` = `1488c943` = merge base of the branch; nothing to merge, no evidence invalidated |
| Source verification | 2026-10-23 (conclusion): Intelligence PRD 83099649 still v10 (2026-10-23T21:57:11Z) and Learning PRD 83066881 still v26 (2026-10-05T02:11:45Z); no reread needed. Jira SHIFU-104 unchanged, no Jira/Confluence write made. |
| Documentation Alignment | `modules.md` wording confirmed, no change; PRD versions to recheck at conclusion; handoff list should gain the picker "Recusar" adaptation (ACH-02) |
| Revision History | Spec revision 1, no contract change |
| Limitations | EV-18 `check:test-integrity` waived by the user for 2 pre-existing offenders (waiver, not a pass); manual journeys used local Curriculum Skills (no "Funções em Python"); the Objective page shows the justification in the list view only (default graph view does not render it); BFF transport mocked in Playwright suites; EV-18 pre-existing failure; the mentor index version changed, so every other environment (including CI evals) needs `python -m shifu.mentor_indexes`; Learning receipts remain until Learning's account purge (recorded gap) |
