---
title: Mentor — conversation summary and continuity evaluation
status: ready
spec: ./spec.md
last_updated_at: 2026-10-18
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01..CA-14 (Spec revision 1). Corrections after integrated testing and review: ACH-01, ACH-02, ACH-05..ACH-07 |
| Automated checks | CI-01..CI-17 passed on the final candidate (EV-01..EV-17, see Check Results); CI-18 is publication-only (not applicable locally) |
| Type / lint / complexity | Type: server EV-12, web EV-13 passed. Lint/format/complexity-lint: server EV-14, web EV-15 passed (4 pre-existing biome warnings). No quantitative complexity metric required by the Spec (disposition recorded, not a pass) |
| Manual checks | 2/2 passed (VM-01, VM-02) |
| Visual checks | 4/4 passed (VM-03..VM-06); Visual Reviewer PASS after ACH-06 correction |
| Independent review | Implementation Reviewer: FAIL advisory, all findings dispositioned (ACH-07 table); Visual Reviewer: PASS on every required row and the three extra surfaces |
| Blockers | None |
| Candidate | Branch `feat/shifu-102` @ `46ade1fa` + uncommitted working tree (feature scope; unrelated pre-existing dirty: `design/shifu.pen`, `documentation/prompts/create-spec-prompt.md`, `documentation/sdd.md`) |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 (EV-01), CI-05 (EV-05) | — |
| CA-02 | RF-01, RF-11 | Complete | Passed | CI-01, CI-05 (usage/model/telemetry allowlist scenarios) | — |
| CA-03 | RF-02, RF-12 | Complete | Passed | CI-01, CI-05, CI-08 (EV-08) | — |
| CA-04 | RF-03 | Complete | Passed | CI-01, CI-05 (ACH-01 found/fixed), CI-17 (EV-17) | — |
| CA-05 | RF-04, RF-05 | Complete | Passed | CI-02 (EV-02), CI-05 | — |
| CA-06 | RF-04 | Complete | Passed | CI-05, CI-09 (EV-09) | Limitation L-2 |
| CA-07 | RF-06 | Complete | Passed | CI-01, CI-05, CI-10, CI-11 | — |
| CA-08 | RF-06 | Complete | Passed | CI-01, CI-05 | Limitation L-1 |
| CA-09 | RF-07 | Complete | Passed | CI-01, CI-04, CI-05, CI-06 | — |
| CA-10 | RF-08 | Complete | Passed | CI-03, CI-05, CI-06; VM-01 deletion | — |
| CA-11 | RF-08 | Complete | Passed | CI-03, CI-07 (EV-07) | — |
| CA-12 | RF-09 | Complete | Passed | CI-01, CI-04, CI-05, CI-06, CI-10 | — |
| CA-13 | RF-10 | Complete | Passed | CI-10, CI-11, VM-01..VM-06 (Visual Reviewer PASS) | — |
| CA-14 | RF-12 | Complete | Passed | CI-08 | — |

### Manual / visual evidence inventory

Candidate for all rows: working tree after ACH-02 correction (worker-thread summarize step), 2026-10-18. Real local services: API on 7777 (task-started), web on 7000 (task-started), local PostgreSQL, account `student.seed@shifu.com` via saved auth state. Artifacts under `apps/web/.playwright-cli/screenshots/`.

| VM | Type | Surface / state | Viewport | Reference | Artifact | Observed result | — |
| --- | --- | --- | --- | --- | --- | --- | --- |
| VM-01 | Manual | Page journey (conversation marked `[SHIFU-102 VM 2026-10-18T21:30]`; 96 messages, 4 summaries v1→v4; fresh conversation S2 for the live capture) | 1440×900 | — | `shifu-102-vm01-originals.png`, `shifu-102-vm01-originals-older-pages.png` | Summarizing shown live; composer disabled; ready marker; "Ver resumo" opened by keyboard, focus inside and trapped (Tab ×6), Escape and "Fechar resumo" return focus to "Ver resumo"; "Ver mensagens originais" closed dialog, loaded older messages (first message unloaded before, focused after) and focused the first message `[SHIFU-102 VM …]`; summary GET server function 200; URL stayed `/intelligence?session=<id>`; console errors 0 (non-vite). Both conversations deleted via UI; DB shows 0 summary rows and 0 messages left | PASS (Orchestrator) |
| VM-02 | Manual | FAB (1440×900 on `/gamification`) and page at 390×844 | 1440 FAB; 390 page | — | `shifu-102-vm02-fab-marker.png`, `shifu-102-vm02-fab-dialog.png`, `shifu-102-vm02-mobile-marker.png` | FAB: dialog opens above panel, focus inside, originals reveal focuses first message with panel still open, Escape closes only the dialog, focus returns to "Ver resumo". 390: no horizontal overflow, "Ver resumo" 44 px, dialog 16 px margins (x=16, right 16), action buttons 324×44 stacked | Visual Reviewer: FAB marker, FAB dialog and mobile marker PASS |
| VM-03 | Visual | Page summarizing | 1440×900 | KVnFQ.png | `shifu-102-vm03-summarizing.png` | `loader-circle` + "Resumindo contexto…" in jade after the pending message; composer disabled, placeholder "Aguarde enquanto o contexto é resumido"; "Cancelar resposta" kept (approved adaptation); controls disabled (approved) | Visual Reviewer PASS |
| VM-04 | Visual | Page ready marker | 1440×900 | RDiWy.png (+ ySE0r) | `shifu-102-vm04-ready-marker.png` | `scroll-text` icon, muted 13 px "Contexto resumido", ghost "Ver resumo"; placed after boundary message (approved adaptation) | Visual Reviewer PASS |
| VM-05 | Visual | Dialog desktop | 1440×900 | T4Edi.png | `shifu-102-vm05-dialog-desktop.png` | Centered `max-w-lg` dialog with overlay; icon tile + title + preservation line, top-right close with visible focus ring, separator, runtime template paragraph, two bordered buttons. Real-stack capture predates ACH-06: action-button border was dim; after the fix the button border matches the reference (≈ rgb 103,104,106) — recaptured from the repo Playwright run (mocked stream fixture): `shifu-102-page-1440-dialog.png` | Visual Reviewer FAIL (ACH-06) → re-review PASS on the recapture |
| VM-06 | Visual | Dialog mobile | 390×844 | ov9QQ.png | `shifu-102-vm06-dialog-mobile.png` | Same header hierarchy; near-full-screen with 16 px margins; stacked full-width 44 px actions (spec text) vs content-width in the reference image; no overflow; recapture after ACH-06 from the repo Playwright run: `shifu-102-page-390-dialog.png`. Focus visibility and keyboard behavior are evidenced by the manual journeys and tests, not by the image | Visual Reviewer FAIL (ACH-06) → re-review PASS on the recapture |

# Check Results

Candidate for all rows unless stated: working tree on `feat/shifu-102` @ `46ade1fa` (Spec revision 1), 2026-10-18.

| EV | Check / type / CA coverage | Status | Environment / fixtures | Command / procedure (cwd) | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01,02,03,04,07,08,09,12 | Passed | mocked ports | `uv run pytest --noconftest -p no:tach tests/intelligence/core/use_cases/test_summarize_mentor_session_context_use_case.py` (apps/server) | 95 passed after the ordering assertion added for ACH-01. `--noconftest` because the use-case suite needs no Docker |
| EV-02 | CI-02, CI-03, CI-04 / Automated / CA-05,10,11,09,12 | Passed | mocked ports | `uv run pytest --noconftest -p no:tach tests/intelligence/core/use_cases -q` (apps/server) | 673 passed (101 in the summarize module) on the final tree |
| EV-05 | CI-05 / Automated / CA-01..10,12 | Passed | registered AgentOS runtime, real spaCy/E5, disposable PostgreSQL; AgentOS fixture patched to keep the host clock monotonic (ACH-05) | `SHIFU_RUN_REAL_AGENTOS_TESTS=1 uv run pytest tests/intelligence/server/agentos/test_process_mentor_response_summary.py tests/intelligence/server/agentos/test_process_mentor_response_workflow.py` (apps/server) | **Final run on the final tree: 49 passed (32 summary + 17 workflow), 864.9 s.** History preserved: run 1 pre-fix failed the v1→v2 fold (ACH-01); a combined run after ACH-02 had 2 failures (access-revision test adjusted; reviewer-provider-raises timeout), and a later run had 1 failure of the explicit-reference test — all traced to ACH-05 (host wall clock stepping backwards) and fixed in the fixture; the explicit-reference test then passed 12/12 in a loop |
| EV-06 | CI-06 / Automated / CA-09,10,12 | Passed | disposable PostgreSQL | `uv run pytest tests/intelligence/server/controllers/test_get_mentor_session_summary_controller.py …test_get_mentor_session_controller.py …test_remove_mentor_session_controller.py …test_stream_mentor_response_controller.py …test_submit_mentor_message_controller.py` | 37 passed (final tree, 75.5 s) |
| EV-07 | CI-07 / Automated / CA-11 | Passed | real Inngest dev runner (`SHIFU_RUN_REAL_INNGEST_TESTS=1`) | `uv run pytest tests/messaging/inngest/jobs/intelligence/test_purge_mentor_summaries_on_account_deleted_job.py tests/messaging/inngest/jobs/intelligence/test_mentor_nlp_integrity_job.py` | 6 passed on the final tree (3 purge + 3 NLP integrity), 138.9 s |
| EV-08 | CI-08 / Automated / CA-03,14 | Passed | `double` mode, no model calls | `uv run python evals/run.py --workflow summarize-mentor-session --output-dir test-results/evals`; `uv run pytest tests/evals` | 12/12 cases, exit 0, `nondeterministic`=0 (each case run twice); Dúvida recall 1.0, Orientação 0.8–1.0, Assunto 0.75–1.0, fidelity 100%, leakage 0, fenced 0; `tests/evals` 19 passed incl. failing-case and drifting-summarizer exit 1. Thin Assunto margin (L-3) |
| EV-09 | CI-09 / Automated / CA-06 | Passed | real AgentOS / real Inngest | `…test_process_mentor_response_workflow.py::test_registered_runtime_keeps_indexed_faq_and_abstention_local` (inside the 17-test workflow file of EV-05) and `…test_mentor_nlp_integrity_job.py` (inside EV-07) | Both passed on the final tree |
| EV-10 | CI-10 / Automated / CA-07,13 | Passed | jsdom | exact Vitest command from the Spec (apps/web) | 9 files, 159 tests passed after the reveal-robustness correction (ACH-07 #11) |
| EV-11 | CI-11 / Automated / CA-07,13 | Passed | repo Playwright config; real API on 7777 started as a task-owned process (the config's own API entry cannot start without the server env — prerequisite); mocked stream fixture | `pnpm --filter web exec playwright test tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts` | 20 passed after ACH-06 and again after the reveal correction (web builder run); logs `apps/web/.playwright-cli/logs/shifu-102-ci-11-*.log`. Mocked transport proves the rendered contract only |
| EV-12 | CI-12 / Type / — | Passed | — | `uv run poe check:types` | 0 errors on the final tree |
| EV-13 | CI-13 / Type / — | Passed | — | `pnpm --filter web check:types` | exit 0 on the final tree |
| EV-14 | CI-14 / Lint+format+C90 / — | Passed | — | `uv run ruff check --no-fix` and `ruff format --check` over the 94 changed/created Python paths | All checks passed (final tree) |
| EV-15 | CI-15 / Lint / — | Passed | — | `pnpm exec biome check` over 33 changed web files | 0 errors, 4 pre-existing warnings (untouched lines of `composer/index.tsx`) |
| EV-16 | CI-16 / Architecture+build / — | Passed | — | `uv run poe check:architecture`; `pnpm --filter web check:architecture`; `pnpm --filter web build` | Tach validated; depcruise 0 violations (466 modules); web build OK (final tree) |
| EV-17 | CI-17 / Migration / CA-04 | Passed | disposable `pgvector/pgvector:0.8.1-pg17` on port 54999 with the AgentOS runtime role created from `scripts/create_agentos_runtime_role.sql` | `DATABASE_URL=… uv run alembic upgrade head`, `check`, `downgrade -1`, `upgrade head`, `check` (apps/server) | All succeeded; "No new upgrade operations detected" twice; constraints/indexes match the declaration (verified with `\d`). Container stopped. The same revision was then applied (upgrade only) to the local development database to run the real journeys |
| EV-18 | CI-18 / Delivery wiring / — | Not applicable (local) | — | — | Workflow edits present (`changed-file-coverage` list, `evals` model-prepare step); current-head CI only exists on publication |
| EV-19 | VM-01, VM-02 / Manual | Passed | See inventory (executed after ACH-02; the ordering fix ACH-01 was active; later web/server corrections did not change the rendered journey) | Playwright CLI session `shifu102` + `run-code` | Detail in the inventory; conversations deleted via UI, DB shows 0 residual rows |
| EV-20 | VM-03..VM-06 / Visual | Passed | See inventory | Screenshots inspected against references by the Orchestrator and the Visual Reviewer | PASS on all required rows after ACH-06; limits recorded in the inventory |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Orchestrator, CI-05 run 1: the use case marked the new row `ready` before `remove_superseded`, violating `uq_mentor_summary_ready`; the swallowed `IntegrityError` left v2 `processing` (CA-04) | High | CI-01, CI-05, CI-17 | Resolved: remove superseded rows first, then mark ready; unit ordering assertion added; fold test and the live v1→v4 journey pass |
| ACH-02 | Orchestrator, real journey: agno calls a sync step executor on the event loop, so the ~2 s summarization stalled API/SSE and the marker never painted (CA-13, RF-10) | High | CI-05, VM-01, VM-03 | Resolved: step runs the use case in `asyncio.to_thread`; marker observed at ~1.7 s with the composer disabled; the thread-safety consequence (shared E5 model) is ACH-07 #1 |
| ACH-03 | Builder deviation: `summarize-context` progress is recorded after the processing-row insert commits (Spec: same locked transaction) because the progress use case opens its own session and self-deadlocks on the session lock; failure deletes the row (`discarded`) | Low | CI-01 | Accepted by the Implementation Reviewer as Low; Spec Runtime Flow step 5 wording not amended (no behavior change); recorded here |
| ACH-04 | The NLP builder edited `shared/providers/langfuse_telemetry_provider/…` (Spec: Shared gains nothing) | Low | CI-05 telemetry | Accepted by the Implementation Reviewer: minimal, additive (outcomes, stage, count keys, closed `failure_code`) and unavoidable; Architecture Mapping note recommended |
| ACH-05 | Intermittent CI-05 failures (explicit-reference test; once the reviewer-provider-raises test): the host (WSL2) wall clock steps backwards ~1–2 s about every 28 s, which reverses `created_at`/ULID order of consecutive attempts; the existing "current attempt" ordering then never claims the new attempt (stays `queued`). Reproduced on pre-feature code (2/5 runs) | Medium (test infra); latent design risk | CI-05, CI-09 | Resolved for tests: AgentOS fixture keeps `SystemClockProvider.now` monotonic (`tests/fixtures/agentos_fixture.py`); explicit-reference test 12/12; full AgentOS run 49/49. **Follow-up (out of scope, recommend a ticket):** attempt ordering relies on wall-clock `created_at` + ULID; a robust key would be a DB sequence or per-session event sequence |
| ACH-06 | Visual Reviewer: dialog action buttons rendered with the `--border` colour (≈ #2E2F33) instead of `--control-border` (reference ≈ #67686B); the global unlayered `* { border-color: var(--border) }` overrides the Tailwind utility (CA-13, VM-05, VM-06, FAB dialog) | Medium | VM-05, VM-06, EV-20 | Resolved: `border-control-border!` on the three action buttons; recaptured; reviewer re-review PASS. Not changed: the global rule and the dialog container border (mirrors `alert-dialog`); the same global-rule effect likely dims other existing `border-control-border` users (pre-existing, outside this Spec) |
| ACH-07 | Implementation Reviewer (13 findings) | see below | see below | Dispositions: **#1 E5 not thread-safe — Resolved** (lock in the SentenceTransformers adapter + CI-05 concurrency scenario, peak concurrency 1); **#2 stale evidence — Resolved** (final-tree reruns, EV-02..EV-16); **#3 CA-08 cancel after commit — Resolved** (real-DB test); **#4 determinism — Resolved** (eval runs twice + AgentOS test); **#5 CA-06 — Resolved** (FAQ-hit-through-topics and explicit-reference tests); **#6 CA-01 — Resolved except** exact 20 without a boundary is unreachable through the public path (replies pair with questions ⇒ odd count), covered with a boundary and by unit boundaries; equal-`created_at` tie-break and 16,000 with boundary added; **#7 first-message query — Resolved** (`find_first_message_id`, one `find_range` outside the lock); **#8 candidate cap — Resolved** (`MAX_CANDIDATES`/`MAX_PHRASES` 512, in `algorithm_version`); **#9 silent failures — Accepted** (Core has no logging convention; every outcome and failure code is emitted through the telemetry span; stale-row/close-failure paths unit-tested quiet); **#10 failed-row pruning — Resolved** (`remove_superseded_failures`); **#11 reveal robustness — Resolved** (active-session abort only, 3-attempt cap, 3 s focus-release timeout); **#12 hygiene — Resolved** (single Core `fenced_code_ranges`; gate docstring; `inspect.stack()` sniff replaced); **#13 `tests/evals` in `changed-file-coverage` — Not applicable** (list gates `src/shifu` coverage; `tests/evals` cover `evals/`; no CI job runs `tests/evals` — noted, see Delivery limitations) | Mixed | CI-01..CI-11 | Resolved / accepted as listed |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| A sync Agno step executor blocks the process event loop, which also serves SSE; CPU-bound steps that publish live progress must run off-loop — and any shared model then needs its own lock | ACH-02, ACH-07 #1, EV-05 | Candidate AI Layer rule note (pending proposal; not edited here) |
| Mocked-port unit tests cannot detect database-constraint ordering bugs; lifecycle replacement needs real-database proof | ACH-01, EV-05 | None; CI-05 owns the proof |
| Attempt/message ordering by wall clock makes registered-runtime tests flaky on hosts whose clock steps backwards; keep the clock monotonic in AgentOS fixtures | ACH-05, EV-05 | Candidate Job Testing rule note (pending proposal; not edited here); follow-up ticket for a non-wall-clock ordering key |
| A global unlayered `*{border-color}` rule defeats Tailwind border-colour utilities; use the `!` modifier or fix the global rule deliberately | ACH-06 | None here; follow-up for the global rule outside this Spec |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-102` @ `46ade1fa`; uncommitted working tree |
| Completed | All criteria implemented and verified (CI-01..CI-17, VM-01..VM-06), both independent reviews dispositioned |
| Unfinished | None. CI-18 and PRD recheck happen at publication/conclusion |
| Uncommitted work | Everything under `apps/server`, `apps/web`, `pnpm-lock.yaml`, `.github/workflows/server-app-ci.yaml`, `documentation/architecture.md` and this feature directory; unrelated pre-existing dirty: `design/shifu.pen`, `documentation/prompts/create-spec-prompt.md`, `documentation/sdd.md` |
| Active processes | None (API 7777, web 7000, browser session, disposable containers and worktrees stopped/removed). The local development database has migration `190822048e6a` applied (additive; `alembic downgrade -1` available) |
| Blockers | None |
| Next action | Conclude (`conclude-spec`): reverify PRD Intelligence v9, reconcile Documentation Alignment, then commit/publication only when requested |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-15, JN-19 | RF-01..RF-12 / CA-01..CA-14 | EV-01..EV-20 | implemented (local delivery) |
| RP-03, RP-06, RP-02, RP-04, RP-11, RP-12, RP-13, RP-14, JN-14, JN-16 | partial scopes per Spec Scope | EV-01..EV-20 | implemented for the selected partial scope |
| RP-01 | — | — | not_applicable (no AI provider is used for summarization) |

Limitations: **L-1** cancel/access-change mid-summarization leaves an invisible stale `processing` row until the next attempt, session deletion or account purge removes it (Spec Runtime Flow steps 3 and 8); **L-2** the topic retry cannot help parts containing "isso"/"aquilo" because the unchanged `retrieve()` rejects them, and `expanded` counts attempts; **L-3** thin Assunto recall margin (0.75 vs 0.70) on the synthetic eval; **L-4** the Mentor's local answers in the real journey were mostly abstentions, so Dúvida excerpts were absent from that live summary (CI-05/CI-08 and the mocked captures cover excerpt content); **L-5** CI-11 needs an API on port 7777 started with the server env (the Playwright config cannot start it alone); **L-6** `tests/evals` is not run by any CI job (CI-08 lists it; add a CI step if desired); **L-7** the FAB at 390 px and the failure notice have no real-stack capture (automated tests only); **L-8** the corrected dialog captures VM-05/VM-06/FAB come from the mocked-stream run (real-stack captures predate ACH-06); **L-9** exact 20 unsummarized messages without a previous boundary is unreachable via the public path; **L-10** pre-existing RP-11 gap (account deletion does not purge sessions/messages) remains out of scope per the Spec.

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| Not applicable (local-only) | — | — | — |

| Field | Result |
| --- | --- |
| Publication | Not requested (local-only); CI-18 current-head CI not applicable |
| Source verification | PRD Intelligence 83099649 v9 recorded in the Spec; recheck at conclusion |
| Documentation Alignment | `documentation/architecture.md` sentence added; `documentation/modules.md` confirmed unchanged (already describes summaries); mentor-context spec revision note deferred per the Spec; recommended Spec wording updates (accepted deviations ACH-03, `getMentorSessionSummary(accessToken, …)` signature, `summary-failure` item kind, `MAX_CANDIDATES`/`MAX_PHRASES` constants) recorded here without a revision increment because behavior is unchanged |
| Revision History | Spec revision 1; no contract change |
| Limitations | L-1..L-10 above |
