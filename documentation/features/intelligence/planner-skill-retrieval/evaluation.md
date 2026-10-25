---
title: Planner intent classification and Skill retrieval with NLP evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-20
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Complete for CA-01 to CA-14 against spec revision 2 |
| Automated checks | 4/4 defined checks passed locally (CI-01, CI-02, CI-03 deterministic suite, CI-04); the opt-in real-model part of CI-03 is blocked (no `OPENROUTER_API_KEY` on this machine, EV-08); the CI coverage gate runs on the PR (EV-09) |
| Type / lint / complexity | Lint passed (EV-03, `ruff check` + `ruff format --check`, 1253 files); types passed (EV-03, `basedpyright` strict, 0 errors); architecture passed (EV-03, `tach`); no quantitative complexity tooling is configured, so complexity is covered only by the configured Ruff `C90` rule |
| Manual checks | VM-01 1/1 passed (EV-07) |
| Visual checks | Not applicable: no user interface |
| Independent review | Pending: PR review by the team |
| Blockers | None for the deterministic delivery; the quality confusion matrix of CA-12 needs the opt-in real run (EV-08) |
| Candidate | branch `feat/shifu-89` on `origin/main` `f8a6158`, commit `bffe732`; the evaluated scope is that commit (server code, tests, migration, CI selection, this documentation) |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-04) | Real-model matrix (EV-08) when a key is available |
| CA-02 | RF-01 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-04) | Same as CA-01 |
| CA-03 | RF-01 | Complete | Passed | CI-01 (EV-01), CI-03 (EV-04: 503×3, transport error ×3, 400, non-JSON, missing answer, choice and probabilities outside the closed set, probabilities not summing to one) | None |
| CA-04 | RF-01 | Complete | Passed | CI-03 (EV-04: no key → typed error, zero requests) | None |
| CA-05 | RF-02, RF-03 | Complete | Passed | CI-01 (EV-01: catalog double receives only `list_skills` and `find_direct_foundations_for_many`), CI-03 (EV-04: decision payload carries only `intent` and `answers`) | None |
| CA-06 | RF-04 | Complete | Passed | CI-03 (EV-04: `não`, `nunca`, `nem` kept; `bancos`→`banco`, `dados`→`dado`; stop words removed; `normalize` keeps the sentence) | None |
| CA-07 | RF-05 | Complete | Passed | CI-02 (EV-02), CI-03 (EV-04: provider, lazy provider and use case fail closed without an active version) | None |
| CA-08 | RF-05 | Complete | Passed | CI-02 (EV-02), CI-03 (EV-04: one 384-d normalized vector per Skill, single active version, active version immutable, CLI subprocess activates the bound version), EV-06 migration | None |
| CA-09 | RF-06 | Complete | Passed | CI-01 (EV-01 structure invariants), CI-03 (EV-04: fused score equals the RRF sum, ranks match the source rankings, limits 10/10/20, no duplicates) | None |
| CA-10 | RF-07 | Complete | Passed | CI-03 (EV-04: the same intent with two answer sets yields different rankings; React rises with the "interatividade e componentes" answers) | None |
| CA-11 | RF-08 | Complete | Passed | CI-04 (EV-03: `tach` validates Intelligence → `shared` only; Learning consumers of the catalog contract pass in EV-05) | None |
| CA-12 | RF-09 | Complete | Partial | CI-03 (EV-04: confusion matrix over 42 labeled requests through the transport double, zero undue refusals, mapping and thresholds proven); real-model matrix blocked (EV-08) | Run EV-08 with `SHIFU_RUN_REAL_OPENROUTER_TESTS=1` and a key |
| CA-13 | RF-09 | Complete | Passed | CI-03 (EV-04: Recall@5 / Recall@10 / MRR for lexical, semantic and hybrid; no-coverage queries) | None |
| CA-14 | RF-10 | Complete | Passed | CI-02 (EV-02) and CI-03 (EV-04) write only the two versioned embedding tables; no Learning or Curriculum write exists in the delivery (`git diff` scope) | None |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-02, CA-03, CA-05, CA-09 | Passed | `feat/shifu-89` dirty tree, 2026-10-20, Windows 11, Python 3.13 venv; Testcontainers Redis autouse (reaper disabled, see ACH-02) | `cd apps/server && uv run pytest tests/intelligence/core/domain/test_planning_domain.py tests/intelligence/core/use_cases/test_classify_planning_intent_use_case.py tests/intelligence/core/use_cases/test_retrieve_planning_skills_use_case.py -q -p no:tach` | 50 passed in 3.12 s (39 domain conformance cases, 5 classify, 6 retrieve) |
| EV-02 | CI-02 / Automated / CA-07, CA-08, CA-14 | Passed | Same candidate; Testcontainers PostgreSQL `pgvector/pgvector:0.8.1-pg17` migrated to head | `cd apps/server && uv run pytest tests/intelligence/adapters/test_planning_embeddings_repository.py "tests/intelligence/ai/test_intelligence_workflows_registry.py::test_registry_exposes_planning_ports_and_fails_closed_without_a_catalog" -q -p no:tach -x` | 4 passed in 8.06 s (3 repository scenarios + the registry planner-ports test): eligibility, limit, ordering by similarity then Skill id, activation swap, immutability of the active version, invalid vectors and versions; the registry exposes the Jev classifier and fails closed on retrieval without a Curriculum catalog |
| EV-03 | CI-04 / Lint, types, architecture / CA-11 | Passed | Same candidate | `cd apps/server && uv run poe check:lint && uv run poe check:types && uv run poe check:architecture` | `ruff`: "All checks passed!", "1253 files already formatted"; `basedpyright`: "0 errors, 0 warnings, 0 notes"; `tach`: "[OK] All modules validated!"; the two scikit-learn member accesses carry targeted `reportUnknownMemberType` suppressions with reasons |
| EV-04 | CI-03 / Automated / CA-01 to CA-10, CA-12, CA-13, CA-14 | Passed | Same candidate; real `pt_core_news_sm` 3.8.0, real `intfloat/multilingual-e5-small` at the pinned revision from the Hugging Face cache, Testcontainers PostgreSQL + pgvector, Jev through `httpx.MockTransport`; `TESTCONTAINERS_RYUK_DISABLED=true` on this machine | `cd apps/server && uv run pytest tests/intelligence/ai/test_planning_nlp_evaluation.py -q -p no:tach -s` | 37 passed, 1 skipped (EV-08 opt-in) in 71.77 s. Retrieval over the 15 labeled queries (13 with relevant Skills, 2 no-coverage): lexical MRR 0.6538 / Recall@5 0.5769 / Recall@10 0.5769; semantic MRR 0.9231 / 1.0000 / 1.0000; hybrid MRR 0.8269 / 1.0000 / 1.0000; top-1 cosine clear min 0.8671 > no-coverage max 0.8389, and both no-coverage queries have an empty lexical ranking. Classification through the transport double over 42 labeled requests: learning 20/20, out-of-scope 12/12, ambiguous 10/10, 0 undue refusals (the double answers the label, so this matrix proves the decision contract, the thresholds and the mapping, not model quality). Negation: q08 ranks `APIs web` first and above `HTML e CSS`; q21 keeps `Lógica de programação` in the top 5 but behind `React`, `APIs web` and `JavaScript essencial` (see ACH-03). Refresh: q09 and q10 rankings differ and `React` rises from 4th to 2nd with the "interatividade e componentes" answers. Offline entry point as a subprocess: "Planner index activated: <bound version>" and the lazy provider then serves `React` first for "Quero aprender React". With seven Skills and 10 + 10 source limits, Recall@10 saturates; MRR is the discriminating metric |
| EV-05 | CI-04 / Unit selection / CA-11 | Passed | Same candidate | `cd apps/server && uv run poe test:unit` | 907 passed in 55.15 s; includes the Learning suites that mock `CurriculumCatalogProvider` |
| EV-06 | CI-02 / Migration upgrade, drift and downgrade / CA-08 | Passed | Local Compose PostgreSQL (`shifu-postgres`, pgvector) | `cd apps/server && uv run poe db:upgrade && uv run --env-file .env.local alembic check && uv run poe db:downgrade && uv run poe db:upgrade` | "Running upgrade f01033e9cd81 -> a7c9e2f4b1d3", `alembic check`: "No new upgrade operations detected.", downgrade and re-upgrade clean |
| EV-07 | VM-01 / Manual / CA-08, CA-09, CA-10 | Passed | Local Compose services, database re-seeded with `poe db:seed` (seven retained Skills), models cached | `cd apps/server && uv run --env-file .env.local python -m shifu.planning_indexes`, then the preview script over the labeled queries (scratchpad `planner_smoke.py`) | Printed `Planner index activated: e60a8f544d2f03bee5bffac6d86a26197aed7b1c8a465ac23d1a30e8aa457d6b` and the lazy provider confirmed `active version matches: True` for the seven-Skill catalog. "Quero aprender a programar do zero, sem nunca ter escrito código": no lexical candidate, semantic and hybrid rank `Lógica de programação` first. "Não quero front-end nem páginas, prefiro APIs e regras de negócio no servidor": hybrid `APIs web` (lexical 1, semantic 1) above `HTML e CSS` (lexical 2, semantic 3). "Quero aprender a fazer sites" with the answers "Quero começar pela estrutura e pela aparência das páginas" + "Ainda não sei programar": `HTML e CSS`, `Lógica de programação`, `APIs web`, `React`; with "Já sei HTML e CSS" + "Quero interatividade e componentes": `HTML e CSS`, `React`, `APIs web`, `Lógica de programação`, so the order changes with the answer set. Only seeded Skills appear in every ranking |
| EV-08 | CI-03 / Real OpenRouter decisions (opt-in) / CA-12 | Blocked | Not run: `OPENROUTER_API_KEY` is not configured on this machine | `cd apps/server && SHIFU_RUN_REAL_OPENROUTER_TESTS=1 uv run pytest tests/intelligence/ai/test_planning_nlp_evaluation.py -k real_model -q -p no:tach -s` | The test is collected and reported as skipped with the opt-in reason; the quality matrix of CA-12 therefore remains a limitation, never a pass |
| EV-09 | Changed-file coverage (CI gate) / Automated | Pending | Runs only in GitHub Actions (`changed-file-coverage` job) | Workflow selection extended with the five new test modules | Expected to run on the PR; result recorded in Delivery once the PR CI finishes |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | The revision 1 target "no-coverage queries put none of the expected-absent Skills in the top 3" was unverifiable: a rank-only fusion always ranks some Skill first (smoke over the seeded catalog, 2026-10-20). Affected CA-13 | Medium | CI-03 | Resolved: spec revision 2 restates CA-13 as an empty lexical ranking plus a top-1 cosine below every clear query; EV-04 asserts it |
| ACH-02 | On this machine the Testcontainers reaper fails intermittently ("Port mapping ... port 8080 is not available") and, because the Redis fixture is autouse, a whole pytest session is reported as skipped with exit code 0 | Medium | EV-01, EV-02, EV-04, EV-05 | Resolved for this evaluation by `TESTCONTAINERS_RYUK_DISABLED=true`; every recorded run shows an explicit "N passed" count. Not a repository change; CI (ubuntu) is unaffected |
| ACH-03 | `pt_core_news_sm` lemmatizes weakly (`programei` → `programeir`, `definir` → `definar`, `quero` dropped as a stop word), so TF-IDF alone misses vague requests and adds noise to the fusion (lexical MRR 0.6538 against semantic 0.9231 in EV-04); negation is preserved only as tokens, so q21 ("Não quero começar por web nem por interfaces, quero primeiro a base de lógica") still ranks web Skills above `Lógica de programação` (4th) | Low | CI-03 | Open, documented limitation of the model and of token-level negation prescribed by the ticket; the hybrid ranking keeps the semantic side, the spec target for the hybrid is defined relative to lexical plus an absolute floor, and the interview of SHIFU-91 is the place to resolve such requests with the learner |
| ACH-04 | The development seed retains only seven Skills (those with ready Competencies), so the labeled retrieval set cannot reference the other six Skills declared in `seed_data.py`; an earlier draft of the set did and failed with `KeyError` | Low | CI-03 | Resolved: the retrieval set references only retained Skills and resolves ids through `list_skills()` |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| Define retrieval targets as properties of the fusion that is actually used; RRF is rank-based, so "nothing in the top k" needs a score-based gate, not a rank gate | ACH-01 | Spec revision 2; no rule change needed |
| Always read the pytest count, never only the exit code, when Testcontainers fixtures are autouse | ACH-02 | Local memory note; no repository change |
| When a labeled set references seeded data, resolve references through the application contract and assert their presence up front | ACH-04 | Evaluation test resolves names through `list_skills()` |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | `feat/shifu-89`, commit `bffe732`, pull request #31 |
| Completed | CA-01 to CA-14 implemented; EV-01 to EV-07 passed |
| Unfinished | EV-08 real-model matrix (needs an OpenRouter key); EV-09 CI coverage gate (runs on the PR) |
| Uncommitted work | None after delivery |
| Active processes | None; Compose services (`shifu-postgres`, `shifu-redis` on 6380, `shifu-inngest`, `shifu-mailpit`, `shifu-minio`) stay up for development |
| Blockers | `OPENROUTER_API_KEY` for EV-08 |
| Next action | Open the PR, watch EV-09, then run EV-08 once a key is provided |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| RP-07 | RF-01, RF-02, RF-03, RF-04, RF-05; CA-01 to CA-08, CA-12 | EV-01, EV-02, EV-04, EV-06, EV-07 | partially_implemented: classification and retrieval foundations; the temporary session and cancel/retry belong to SHIFU-91; real-model quality matrix pending (EV-08) |
| RP-08 | RF-06, RF-07; CA-09, CA-10 | EV-04, EV-07 | partially_implemented: refreshed query over the full answer set; question generation belongs to SHIFU-91 |
| RP-09 | RF-06, RF-10; CA-09, CA-14 | EV-01, EV-04 | partially_implemented: only existing Skills are candidates; proposal composition belongs to SHIFU-91 |
| RP-10 | RF-10; CA-14 | EV-02, EV-04 | not_implemented by design: nothing is confirmed or created |
| JN-07, JN-08, JN-11, JN-15 | RF-01, RF-02, RF-07 | EV-04 | partially_implemented up to the decision and candidate set |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| https://github.com/CtrI-Alt-Del/shifu/pull/31 | `bffe732` (feature and documentation; this delivery-state note follows as a docs commit) | Pending: CI running on the PR head; review not started | GitHub Actions `Server application CI` on the PR; the changed-file coverage job (EV-09) is the gate still open |

| Field | Result |
| --- | --- |
| Publication | Published: branch `feat/shifu-89` pushed to `CtrI-Alt-Del/shifu`, pull request #31 open against `main`; Jira SHIFU-89 moved to Code Review |
| Source verification | SHIFU-89 (Jira, read 2026-10-20) and PRD Intelligence content `83099649` version 4; no change since the spec was written |
| Documentation Alignment | Confirmed as listed in the spec; no Confluence write; `documentation/modules.md` unchanged |
| Revision History | Spec revision 2 (see spec) |
| Limitations | EV-08 blocked without a key; ACH-03 lemmatizer quality; the development seed exposes seven Skills, so Recall@10 over a ≤ 10 + 10 candidate set is close to saturation and MRR is the discriminating metric |
