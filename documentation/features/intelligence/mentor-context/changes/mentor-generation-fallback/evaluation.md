---
title: Mentor — generated answer when no local answer exists evaluation
status: completed
spec: ./spec.md
last_updated_at: 2026-10-22
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete; CA-01..CA-10 (Spec revision 2) |
| Automated checks | 4/4 passed: CI-01 70 tests; CI-02 evals (synthetic 9/9, real general 5/5); CI-03 workflow test 14/14 (revision 5); CI-04 gates |
| Type / lint / complexity | Passed on the final tree: basedpyright 0 errors and web `tsc` clean (EV-04); ruff check and format clean on 28 changed paths, configured `C90` rule included, no quantitative complexity metric is configured (EV-05); tach, build and web architecture passed (EV-06) |
| Manual checks | 1/1 passed (VM-01, real OpenRouter provider) |
| Visual checks | Not applicable: no UI change |
| Independent review | Current: Implementation Reviewer PASS on the code, 8 findings all corrected or accepted (Findings). No re-review: the corrections are small |
| Blockers | None; see Handoff for limitations |
| Candidate | Branch `feat/shifu-101`, base `52b52d71`, uncommitted. Mine: the generation change files and this folder, on top of the uncommitted progress change. Not mine and preserved: the removed changed-file coverage jobs, scripts and Tooling text, `documentation/prompts/review-code-prompt.md` |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-07 | Complete | Passed | CI-01, CI-02, VM-01; EV-01, EV-02, EV-07 | None |
| CA-02 | RF-02 | Complete | Passed | CI-01; EV-01 | None |
| CA-03 | RF-03 | Complete | Complete | CI-03; EV-03 | Second version after one rejection and abstention after two, with exactly two writer and two reviewer calls (revision 4) |
| CA-04 | RF-04 | Complete | Passed | CI-01, VM-01; EV-01, EV-07 | None |
| CA-05 | RF-05 | Complete | Complete | CI-01 (decision, store failure); CI-03 (eight limit cases); VM-01 (slots in Redis); EV-01, EV-03, EV-07 | Every Given of the criterion has an automated case since revision 5 |
| CA-06 | RF-05 | Complete | Passed | CI-01; EV-01 | None |
| CA-07 | RF-06 | Complete | Passed | CI-01; EV-01 | None |
| CA-08 | RF-07 | Complete | Complete | CI-02 (projection shape); CI-03 (two accounts, per-account limit); EV-02, EV-03 | No AgentOS table or log exists in the test runtime, so there is nothing to scan (revision 4) |
| CA-09 | RF-08, RF-09 | Complete | Complete | CI-03 (writer failure and retry, cancel and delete during review, per-version usage keys); VM-01 (usage receipts); EV-03, EV-07 | Every Given of the criterion has an automated case since revision 5 |
| CA-10 | RF-10 | Complete | Passed | CI-02, VM-01; EV-02, EV-07 | None |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-02, CA-06, CA-07 | Passed | Spec rev 2, uncommitted candidate, 2026-10-22; mocked ports | `cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py` | 70 tests passed, none skipped. The existing tests are unchanged except `test_should_keep_general_generation_local`, rewritten as `test_should_keep_a_generation_request_local_when_every_part_has_a_curated_answer`. The new `TestPrepareMentorGeneration` group has 21 scenarios (allowed, denied, store failure, claim check before the slot, generated block already published, pedagogical refusals, clarification, statement-only, statement with another answer, three unusable attachment statuses, file question without attachment, usable but unmentioned attachment, attachment-backed request, pure statement without receipt, missing abstention). Rerun pending on the final tree |
| EV-02 | CI-02 / Automated (evals) / CA-01, CA-08, CA-10 | Passed | Spec rev 2, 2026-10-22; synthetic double model, then real configured models with the key from `apps/server/.env.local` and `OPENROUTER_PROMPT_LOGGING_DISABLED=true` | `cd apps/server && uv run python -m evals.run --workflow process-mentor-response` and `OPENROUTER_PROMPT_LOGGING_DISABLED=true SHIFU_RUN_REAL_AI_EVALS=1 uv run --env-file .env.local python -m evals.run --workflow process-mentor-response --tag general` | Double mode 9/9 (4 existing attachment cases plus 5 new `general_*` cases), real mode 5/5 `general_*` cases (greeting, unrelated question oriented to learning without answering it, file question without a reading claim, context not verified, reviewer accepts the orientation). Reports under the session scratchpad only. Limit: the real reviewer case covers only the approving orientation; there is no real rejection case |
| EV-03 | CI-03 / Automated / CA-03, CA-05, CA-08, CA-09 | Passed | Spec rev 5, 2026-10-22; disposable PostgreSQL and Redis (Testcontainers), real use cases and repositories, `Mock` agents, `arun` | `cd apps/server && uv run pytest tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py -q` | 14 passed, none skipped, 42 s. The earlier AgentOS runtime suites that ran on this candidate were removed by user decision (revision 3) |
| EV-04 | CI-04 / Type | Passed | Final tree, 2026-10-22 | `cd apps/server && uv run poe check:types`; `cd apps/web && pnpm check:types` | Server 0 errors, 0 warnings, 0 notes; web `tsc --noEmit` clean |
| EV-05 | CI-04 / Lint, format, C90 | Passed | Final tree | `cd apps/server && uv run ruff check --no-fix <28 changed paths>` and `uv run ruff format --check <28 changed paths>` | Clean. Complexity is the configured `C90` lint rule only; no quantitative metric tool is configured, so none is claimed. `node scripts/check-test-integrity.mjs` also passes (316 test files) |
| EV-06 | CI-04 / Architecture, build | Passed | Final tree | `cd apps/server && uv run poe check:architecture` and `uv run poe build`; `cd apps/web && pnpm check:architecture` | tach "All modules validated"; sdist and wheel built (ignored `dist/`); web depcruise 514 modules, no violation. The registry composition suite was removed by user decision |
| EV-07 | VM-01 / Manual / CA-01, CA-04, CA-10 | Passed | Spec rev 1 behavior (revision 2 changed no behavior), 2026-10-22; disposable `pgvector/pgvector:0.8.1-pg17` (55601) and `redis:7-alpine` (55602), API 17777, web 17000, `playwright-cli` session `vm01g`, seed account, real OpenRouter key | Alembic head, role script, seed, `shifu.mentor_indexes`, sign-in through the visible form, then three new conversations; API restarted once with an empty key | (1) "Olá": generated reply "Olá! Posso ajudar você a entender conceitos, dar dicas sobre habilidades e encontrar materiais de estudo. O que você gostaria de aprender?", no abstention; usage calls `generated-0:writer:0` (1034 tokens) and `generated-0:review:0` (1516). (2) "Qual é meu progresso no Objetivo?": the local overview, no usage calls. (3) "Qual é a capital da França?": a brief learning-focused orientation, approved on the first version, usage recorded. (4) API without the key, "Olá": the abstention, `usage_calls = []`. Redis held 2 slots. Console 0 errors, 0 warnings; no 4xx/5xx. Artifact: `apps/web/.playwright-cli/screenshots/vm01gen-greeting.png`. Cleanup: API and web stopped, both containers removed; the user's 7777 and 7000 were not running. The code changes made after VM-01 (restart recovery, Redis timeouts) do not touch these paths |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | Observation: three selected-skill progress tests carry a generative label on a part that has a local fact answer. Their replies already ended with "Essas informações estão indisponíveis no momento." fragments and the abstention before this change. With the model on the unanswered part gets a generated block instead of the abstention. CA-02 | low-medium | EV-03 | Accepted by Spec RF-02. Tests run with the model off. Out of scope: intent labelling. Reported to the user as a quality follow-up |
| ACH-02 | Implementation Reviewer 1: a restarted run (crash in the final step) re-ran the model although the fallback or `generated-0` was already published, and could add `generated-0` after a published abstention. RF-03, RF-08 | medium | EV-03 | Resolved: `_ExecutionState.resumed`; `_resume_published` applies at preparation and at recovery, and a resumed state skips the write loop. Proof: reading plus the existing recovery suites; the unit tests I wrote for it were removed by the user rule on test boundaries |
| ACH-03 | Reviewer 2: attachment answers share the two-version loop and per-version keys with no proof | medium | EV-03 | Accepted as a limit: no new test (revision 2). The attachment recovery and boundary suites passed before their removal (revision 3) |
| ACH-04 | Reviewer 3: evidence not recorded | — | — | Resolved: this Evaluation |
| ACH-05 | Reviewer 4: Redis client had no socket timeouts, so a blackholed store could hang preparation | low-medium | — | Resolved: `socket_timeout=2` and `socket_connect_timeout=2` in the registry. No test (removed) |
| ACH-06 | Reviewer 5 and 6: window boundary and registry composition not proven | low | — | Accepted: tests removed by the test-boundary decision. The window logic was read and exercised in VM-01 only at the hour scale |
| ACH-07 | Reviewer 7 and 8: degraded index with the model on, mixed message, Langfuse spans | low | — | Accepted as limits: no runtime test (revision 2) |
| ACH-09 | Unrelated flake: `test_registered_attachment_removal_during_vision_inference_does_not_resurrect_data` failed once in the long sequential run ("late inference result resurrected removed attachment data") and passed alone. It exercises attachment preparation, which this change does not touch | low | EV-03 | Accepted as a timing-dependent flake; reported, not corrected here. The file no longer exists (revision 3) |
| ACH-08 | Reviewer ambiguity: RF-07 "inconclusive is accepted" wording | low | — | Resolved: Spec clarification (Revision History, 1 clarification) |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| The AgentOS fixture transport client must not retry like the OpenAI SDK default, or an injected failure is retried away | Test run where a writer 500 completed the answer | Fixed in the fixture (`max_retries=0`) |
| Never stack long AgentOS suites, and never `pkill -f` a pattern that matches the shell | Earlier sessions and this one | Local practice |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-101`, base `52b52d71`, uncommitted |
| Completed | Production code (limit port with Redis and unavailable providers, route `unanswered_requests`, preparation decision, two-version workflow with fallback and restart recovery, closed projection, writer and reviewer instructions, registry with Redis timeouts, settings, docs); eval cases; CI-01, CI-02 (evals), VM-01; types |
| Unfinished | Conclusion: Jira key for the commits, pointers from the base, memory, summary and progress Specs, PRD recheck, local scoped commits. every criterion is Complete since Spec revision 5 |
| Uncommitted work | See Candidate. Also in the working tree, to be committed separately: the registry provider-property rename, the `GenerateMentorTitleProvider` port rename, and the Intelligence provider-layout refactor (`ai/generative` and empty `messaging/{brokers,jobs}` removed; providers moved to `<capability>/<technology>/`; the unused `UnavailableAnswerMentorMessageWorkflow` removed); the Mentor base agent with per-agent model configs and parameterless constructors (model providers and `ai/eval_factories.py` deleted, `evals/dependencies.py` deleted and each eval class building its own target, `ai-layer-rules.md` amended); the removal of every AgentOS runtime test file, the six AgentOS-backed Mentor job tests, the `agentos_fixture.py` and `mentor_job_fixture.py` fixtures and three middleware and pipe tests, with `scripts/check-test-integrity.mjs` now accepting only `*_controller.py` under `tests/<module>/server/` and `test_*_workflow.py` under `tests/<module>/ai/workflows/`; the evals rewritten on one `Eval` base (`evals/eval.py`, Agno `Case`s for agents, local cases for providers, code-activity eval removed); the new in-process workflow tests under `tests/intelligence/ai/workflows/` (process response, generate title, prepare attachment, purge attachments) and `tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py` with its seeding support `tests/fixtures/learning_fixture.py` (registered in `tests/conftest.py`). The untracked copies of the controller tests under `tests/intelligence/server/agentos/` were removed with that folder on the second "remove all agentos tests" request; the tracked originals under `tests/intelligence/server/controllers/` are deleted in the working tree. The progress change (`progress-overview-without-context`) is also uncommitted. Test files removed by user decision, 2026-10-22: server `tests/core/domain/test_domain_rules.py`, `tests/core/shared/domain/test_code_rubric_contracts.py`, `tests/evals/test_run.py`, `tests/evals/test_synthetic_cases.py`, `tests/intelligence/adapters/test_mentor_persistence_adapters.py`, `tests/intelligence/ai/agno/agents/test_mentor_agent_contract_coverage.py`, `tests/intelligence/ai/agno/workflows/test_mentor_workflow_branches.py`, `tests/intelligence/ai/generative/agno/workflows/test_agno_generate_mentor_title_workflow.py`, `tests/intelligence/ai/test_eval_factories.py`, `tests/intelligence/ai/test_intelligence_workflows_registry.py`, `tests/intelligence/providers/test_local_mentor_attachment_extractor_provider.py`, `tests/intelligence/rest/test_attachment_request_boundaries.py`, `tests/learning/messaging/test_learning_inngest_messaging.py`, `tests/rest/handlers/test_app_error_handler.py`, `tests/shared/database/sqlalchemy/repositories/test_events_repository.py`, `tests/shared/messaging/agentos/test_agentos_{client,handoff_store,runtime}.py`, `tests/shared/messaging/test_outbox_brokers.py`, `tests/shared/providers/test_s3_file_storage_provider.py`, `tests/shared/test_settings.py`; web `src/constants/tests/routes.test.ts`, `src/rest/axios/tests/axios-rest-client.test.ts`, `src/rest/services/tests/intelligence-service.test.ts`. Older Evaluations that cite them keep their historical records |
| Active processes | None |
| Blockers | None. Synchronized on 2026-10-22: `origin/main` `0bc77d56` merged with no rebase into the branch (merge commit `1c394530`). Conflicts: the two CI workflows (kept the retired coverage-gate side), the removed AgentOS React evaluation test and the removed coverage-gate test, and the moved React controller fixture (main's file kept, imports updated). Reused: every Intelligence result, because the merge touched no Intelligence path. Refreshed on the merged candidate: `tests/learning` and `tests/curriculum` 467 passed, types 0 errors, ruff clean, architecture valid. Limitations: (1) the AgentOS React evaluation cases that main added (routing to the Learning runtime and a persisted React attempt with replay) were dropped with the AgentOS suite and have no in-process equivalent yet; (2) `scripts/check-test-integrity.mjs` flags two test files that main added, `apps/server/tests/curriculum/core/domain/test_react_question.py` and `apps/web/src/rest/services/tests/gamification-service.test.ts`, which are kinds the repository policy does not allow; they were kept untouched |
| Next action | None. Later review feedback follows `resolve-pr-feedback` |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-04 | RF-01..RF-03, RF-10 / CA-01..CA-03, CA-10 | EV-01, EV-02, EV-07 | partially_implemented by Spec; the consulted-information mark and materials without a Habilidade stay deferred |
| RP-05 | RF-03, RF-06, RF-10 / CA-03, CA-07, CA-10 | EV-01, EV-02, EV-07 | partially_implemented by Spec; the double-rejection path has no automated runtime proof |
| RP-01 | RF-04, RF-05, RF-08 / CA-04, CA-05, CA-09 | EV-01, EV-03, EV-07 | partially_implemented (unavailability message deferred, Q20) |
| RP-02 | RF-05 / CA-05 | EV-01, EV-07 | deferred (monthly quota, Q20); the hourly limit is a technical control |
| RP-06, RP-11 | RF-07, RF-08 / CA-08, CA-09 | EV-02, EV-03 | partially_implemented; isolation and cancel/delete during generation have no new automated runtime proof |
| RP-13 | RF-07 / CA-01, CA-08 | EV-02, EV-07 | partially_implemented |

| Field | Result |
| --- | --- |
| Publication | Pull request [#42](https://github.com/CtrI-Alt-Del/shifu/pull/42), base `main`, head `feat/shifu-101` at `52494baf`. Current-head CI on 2026-10-22: 23 of 23 checks SUCCESS (type, lint, architecture, build, unit, integration shards 1 to 4, web, email contract, real AI evals). Runs: [39964668088](https://github.com/CtrI-Alt-Del/shifu/actions/runs/39964668088), [39964668231](https://github.com/CtrI-Alt-Del/shifu/actions/runs/39964668231), [39964668299](https://github.com/CtrI-Alt-Del/shifu/actions/runs/39964668299). Review: no threads, no review decision yet. Commits: `a5d2f791` server source, `57798ab8` server tests, `18284fc0` evals, `b51a0a67` CI and tooling, `f005ec4f` Specs and rules, `1c394530` merge of main, `52494baf` Evaluation record. Left out as unrelated: `.vscode/settings.json` (only reformatted by biome so the lint hook passes) and `documentation/prompts/review-code-prompt.md` |
| Source verification | PRD Intelligence content 83099649, version 9 (2026-10-13T16:12:19Z), read in full 2026-10-22. Recheck at conclusion |
| Documentation Alignment | Done: architecture.md and tooling.md, and a pointer row in the base Mentor context Spec. The memory and summary Specs need no pointer because their contracts are unchanged |
| Revision History | Revision 2 changes the verification contract only (evals replace the registered generation tests; invalid test files removed); behavior unchanged |
| Limitations | Replay after handoff loss with different token counts already fails today. The Redis adapter's error translation and the registry composition are untested |
