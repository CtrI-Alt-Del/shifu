---
title: Goal Planner backend flow evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-20
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01 to CA-18 against spec revision 2 |
| Automated checks | 5/5 defined checks passed locally: CI-01 (EV-01, 46 passed), CI-02 (EV-02, 45 passed), CI-03 (EV-03, 19 passed), CI-04 (EV-04, 9 passed), CI-05 (EV-05, EV-06, EV-07); the CI coverage gate runs on the PR (EV-09) |
| Type / lint / complexity | Lint passed (EV-05, `ruff check` + `ruff format --check`, 1307 files); types passed (EV-05, `basedpyright` strict, 0 errors); architecture passed (EV-05, `tach`); complexity covered only by the configured Ruff `C90` rule (no quantitative tooling configured) |
| Manual checks | VM-01 blocked: the real DeepSeek run needs `OPENROUTER_API_KEY`, absent on this machine |
| Visual checks | Not applicable: no user interface |
| Independent review | Pending: PR review by the team |
| Blockers | None for the deterministic delivery; VM-01 waits for a key |
| Candidate | branch `feat/shifu-91` on top of `feat/shifu-89` (`6a4bdcb`), commits `0f0be27` and `4481df0`; the evaluated scope is those commits |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-07 | Complete | Passed | CI-03 (EV-03) | None |
| CA-02 | RF-01 | Complete | Passed | CI-04 (EV-04) | None |
| CA-03 | RF-01, RF-09 | Complete | Passed | CI-01 (EV-01), CI-04 (EV-04: Jev 503 ×3 → `failed`, retry → `proposal`) | None |
| CA-04 | RF-02, RF-03 | Complete | Passed | CI-04 (EV-04: batch with `Não sei`, `Outro` filtered, payload keys restricted) | Real-model question quality (VM-01) |
| CA-05 | RF-03 | Complete | Passed | CI-01 (EV-01), CI-02 (EV-02), CI-03 (EV-03: `400 validation_error`, no event) | None |
| CA-06 | RF-03 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03) | None |
| CA-07 | RF-03, RF-04 | Complete | Passed | CI-02 (EV-02 batch limits), workflow constant `MAX_BATCHES = 3` exercised by the interview step guard | Scenario with three answered batches is covered by the guard, not by a dedicated registered run |
| CA-08 | RF-04 | Complete | Passed | CI-04 (EV-04: proposal with relations among proposed Skills, `consulted_curriculum`) | Real-model proposal quality (VM-01) |
| CA-09 | RF-05 | Complete | Passed | CI-02 (EV-02 draft problems), CI-04 (EV-04 invalid then corrected) | None |
| CA-10 | RF-05 | Complete | Passed | CI-04 (EV-04 four invalid drafts → `validation-failed`) | None |
| CA-11 | RF-06 | Complete | Passed | CI-04 (EV-04 composer declines) | None |
| CA-12 | RF-07 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03 `409`) | None |
| CA-13 | RF-07 | Complete | Passed | CI-03 (EV-03 concurrent submissions → one `202`, one `409`, one event) | None |
| CA-14 | RF-08 | Complete | Passed | CI-01 (EV-01), CI-04 (EV-04 cancel during a blocked run → `404`, no key) | None |
| CA-15 | RF-08, RF-10 | Complete | Passed | CI-01 (EV-01), CI-04 (EV-04 timeout → restart → late result discarded, generation 2 completes) | None |
| CA-16 | RF-09 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03 `operation_timeout`) | None |
| CA-17 | RF-11 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-03 `404` for foreign plannings on every route) | None |
| CA-18 | RF-11, RF-12 | Complete | Passed | CI-03 (EV-03 TTL and body keys), CI-04 (EV-04 payload keys), migration drops the only Planner table (EV-06) | None |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-03, CA-05, CA-06, CA-12, CA-14, CA-15, CA-16, CA-17 | Passed | `feat/shifu-91` dirty tree, 2026-10-20, Windows 11, Python 3.13 venv; `TESTCONTAINERS_RYUK_DISABLED=true` | `cd apps/server && uv run pytest tests/intelligence/core/use_cases -k planning -q -p no:tach` | 46 passed in 3.53 s across eight use-case modules (start, get, answer, restart, retry, cancel, prepare, complete) |
| EV-02 | CI-02 / Automated / CA-05, CA-07, CA-09, CA-10 | Passed | Same candidate | `cd apps/server && uv run pytest tests/intelligence/core/domain/test_planning_session_domain.py -q -p no:tach` | 45 passed in 2.73 s: transitions, answer validation (missing, unknown, two on single, exclusive combined, repeated), fences, timeout, outcomes, structure invariants, draft problems |
| EV-03 | CI-03 / Automated / CA-01, CA-05, CA-06, CA-12, CA-13, CA-16, CA-17, CA-18 | Passed | Same candidate; Testcontainers PostgreSQL (pgvector, migrated to head) and Redis; AgentOS relay neutralized by `planning_client` | `cd apps/server && uv run pytest tests/intelligence/server/controllers -k planning -q -p no:tach` | 19 passed in 59.51 s across six controller modules: `201`/`422`/`401` on start with the Redis hash, its TTL and the unrouted outbox row; `200` detail with batch, proposal and relations; `operation_timeout` on a stale operation; `404` for foreign, unknown and malformed ids; `202`/`400`/`409` on answers with one `202` and one `409` for concurrent submissions and exactly one event; restart generation 2; retry from `failed`; `204` idempotent cancel |
| EV-04 | CI-04 / Automated / CA-02, CA-03, CA-04, CA-08, CA-09, CA-10, CA-11, CA-14, CA-15, CA-18 | Passed | Same candidate; registered AgentOS runtime with disposable PostgreSQL and Redis, real local NLP models and Planner index, `ControlledDecisionsTransport` and planner model transport | `cd apps/server && SHIFU_RUN_REAL_AGENTOS_TESTS=1 uv run pytest tests/intelligence/server/agentos/test_plan_goal_workflow.py -q -p no:tach` | 9 passed in 214.37 s: direct proposal with relations among proposed Skills and model payloads restricted to intent/answers/candidates; interview batch (`Outro` filtered, `Não sei` exclusive) then proposal with the answers in the next payload; out-of-scope with zero model calls; unsupported; invalid draft corrected on the second call with the pt-BR problems; four invalid drafts → `validation-failed`; Jev 503 ×3 → `failed` then retry → `proposal`; cancel during a blocked run → `404` and no hash; timeout → restart → late result of generation 1 discarded and generation 2 completes. A first run failed on all nine scenarios because `AgentOSClient` rejected the ticket fields (ACH-04) |
| EV-05 | CI-05 / Lint, types, architecture | Passed | Same candidate | `cd apps/server && uv run poe check:lint && uv run poe check:types && uv run poe check:architecture` | `ruff`: "All checks passed!", "1307 files already formatted"; `basedpyright`: "0 errors, 0 warnings, 0 notes"; `tach`: "[OK] All modules validated!" |
| EV-06 | CI-05 / Migration / CA-18 | Passed | Local Compose PostgreSQL | `cd apps/server && uv run poe db:upgrade && uv run --env-file .env.local alembic check && uv run poe db:downgrade && uv run poe db:upgrade` | "Running upgrade a7c9e2f4b1d3 -> b8d1f3a2c4e6, drop intelligence planning sessions"; `alembic check`: "No new upgrade operations detected."; downgrade recreates the table and re-upgrade drops it |
| EV-07 | CI-05 / Unit selection and registry | Passed | Same candidate | `cd apps/server && uv run poe test:unit` and `uv run pytest tests/intelligence/ai/test_intelligence_workflows_registry.py -q -p no:tach` | `test:unit`: 938 passed in 61.59 s (907 before this delivery + 31 Planner use-case cases that the selection collects; the legacy stub tests were removed); registry module: 15 passed, 7 skipped (AgentOS-flagged), including the planning event projection and the Redis repository ownership |
| EV-08 | VM-01 / Manual (opt-in real DeepSeek) / CA-04, CA-08 | Blocked | Not run: `OPENROUTER_API_KEY` is not configured on this machine | Procedure in the spec | The registered-boundary proof uses controlled transports; question and proposal quality with the real model remains a limitation until the key is available |
| EV-09 | Changed-file coverage (CI gate) | Pending | GitHub Actions `changed-file-coverage` job | Selection extended with the sixteen new test modules | Recorded in Delivery once the PR CI finishes |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Revision 1 of CA-15 assumed a restart during a running operation, which RF-07 forbids (`409`); the generation fence is only reachable after a timeout reported the run as `failed` | Low | CI-04 | Resolved: spec revision 2 restates CA-15 and EV-04 proves it through the timeout path with `PLANNING_OPERATION_TIMEOUT_SECONDS=10` in the fixture |
| ACH-02 | A single-choice question answered with `Não sei` plus another option is rejected by the single-choice rule first, so the exclusive-option message appears only on multiple choice | Low | CI-02, CI-03 | Resolved: EV-02 covers the exclusive message on multiple choice; EV-03 asserts the single-choice message for the HTTP path |
| ACH-03 | The AgentOS runtime starts its queue workers in every controller test even with the relay neutralized (log noise, ~2 s per test) | Low | CI-03 | Open, inherited from the Mentor controller tests; no functional effect |
| ACH-04 | The first registered run ended every scenario as `failed` / `operation_timeout`: `AgentOSClient._serialize_fields` allowlists ticket field names and `planning_id` / `operation_id` were missing, so the relay rejected the envelope silently and the run never started (EV-04, first attempt, 9 failed in 259 s) | High | CI-04 | Resolved: the two ID-only names were added to the Shared allowlist with a positive and a negative case in `tests/shared/messaging/agentos/test_agentos_client.py` (10 passed); EV-04 rerun 9 passed |
| ACH-05 | The fixture commit `1be84ce` (cherry-picked from the SHIFU-92 branch) also deleted `planner-placeholder-page/index.tsx` and its browser test, so PR #32 failed the web type check, build and integration jobs with `Cannot find module '@/ui/intelligence/widgets/pages/planner-placeholder-page'` | High | PR #32 web jobs | Resolved: both files restored from `1be84ce~1`; `tsc` clean and the placeholder suite passes (2) again |
| ACH-06 | `test_should_discard_a_late_result_of_a_restarted_generation` failed in the CI shard and coverage jobs (`timed_out is None`) while passing locally, also when the shard order was replayed; the logs show Agno keeping the first test's Redis cancellation manager and event stream for the whole process (`Cancellation check unavailable (Redis fault, failing open): Event loop is closed`) | Medium | CI-04 (shard 2/4, coverage job) | Open: the fixture resets Agno's process-wide manager and event stream before and after every registered app (the `Event loop is closed` warnings are gone), the planner gate waits 90 s and the scenario observes the 10 s timeout for up to 80 s, yet the first CI run after that still failed in shard 2/4 and in the coverage job (`timed_out is None` after 80 s) while the same order passes locally; the scenario now reports the statuses and stages it observed so the next CI run names the state the API kept answering |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| A new AgentOS workflow needs its ticket field names in the Shared envelope allowlist, and a rejected envelope surfaces only as a timed-out operation; check the allowlist before the first registered run | ACH-04 | Proposed note for the Messaging Layer Rules (admission envelope section); no change made here |
| Prove a fence with the state transition that can actually reach it; a rule that forbids the trigger (restart while processing) cannot be the scenario | ACH-01 | Spec revision 2 |
| When several validation rules can reject one input, assert the message of the rule that fires first or assert the code only | ACH-02 | Test adjusted; no rule change |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-91`, commit `0f0be27`, pull request #32 |
| Completed | CA-01 to CA-18 implemented; EV-01 to EV-07 passed |
| Unfinished | EV-08 (real DeepSeek run, needs a key); EV-09 (runs on the PR) |
| Uncommitted work | None after delivery |
| Active processes | None; Compose services stay up for development |
| Blockers | `OPENROUTER_API_KEY` for EV-08 |
| Next action | Open the PR on top of `feat/shifu-89` (rebase onto `main` after #31 merges), watch EV-09 |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-07 | RF-01, RF-02, RF-07, RF-09, RF-11; CA-01 to CA-03, CA-12 to CA-17 | EV-01, EV-03, EV-04 | implemented (backend); quota belongs to SHIFU-54 |
| RP-08 | RF-03; CA-04 to CA-07 | EV-02, EV-03, EV-04 | implemented (backend); real-model question quality pending EV-08 |
| RP-09 | RF-04, RF-05, RF-06, RF-12; CA-08 to CA-11, CA-18 | EV-02, EV-04 | implemented (backend); real-model proposal quality pending EV-08 |
| RP-10 | RF-10; CA-15 | EV-01, EV-04 | partially_implemented: restart; confirmation is SHIFU-95 |
| RP-11 | RF-11; CA-17 | EV-01, EV-03 | partially_implemented: ownership, revision check and TTL |
| RP-12 | RF-11; CA-18 | EV-03, EV-04 | partially_implemented: pt-BR payloads; UI is SHIFU-92/93 |
| JN-07, JN-08, JN-09, JN-10, JN-11, JN-12, JN-15 | RF-01 to RF-10 | EV-04 | implemented up to the API state |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/32 (targets `main`; includes the SHIFU-89 commits until #31 merges) | `0f0be27` (feature), `4481df0` (documentation), `1be84ce` (fixture seam), then the ACH-05/ACH-06 fix commit | Pending: CI running on the PR head; review not started | GitHub Actions `Server application CI` on the PR; the changed-file coverage job (EV-09) is the gate still open |

| Field | Result |
| --- | --- |
| Publication | Published: branch `feat/shifu-91` pushed to `CtrI-Alt-Del/shifu`, pull request #32 open against `main` (stacked on #31); Jira SHIFU-91 moved to Code Review |
| Source verification | SHIFU-91 (Jira, read 2026-10-20) and PRD Intelligence content `83099649` version 4 |
| Documentation Alignment | Confirmed as listed in the spec; no Confluence write; `documentation/modules.md` unchanged |
| Revision History | Spec revision 2 (see spec) |
| Limitations | EV-08 blocked without a key; the web client keeps the `id`/`created_at` contract of the start response and consumes the new states only in SHIFU-92 |
