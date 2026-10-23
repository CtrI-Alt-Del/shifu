---
title: Mentor — progress overview without page context
status: completed
revision: 4
source:
  type: direct-request
  ref: User conversation on branch feat/shifu-101, 2026-10-21 ("the mentor should be able to fetch skill data regardless the current active page", "it should be able to return a better message"); parent Spec ../../spec.md revision 18
scope:
  - intelligence/mentor
  - learning/mentor-context-provider
last_updated_at: 2026-10-22
---

# Objective

A learner who asks the Mentor about progress or Habilidades gets a useful local answer from their own Learning data, whichever page is open. Today a question such as "Qual é meu progresso no Objetivo?" returns only "Essas informações estão indisponíveis no momento." unless a Habilidade is selected by the page or named in the message.

Baseline (current source): `LearningMentorContextProvider` always loads the learner's Objetivos and completed Habilidades, but it builds a `progress_summary` fact only for one selected Habilidade, and it prints completed Habilidades as raw IDs. `LocalMentorRouteProvider` answers the progress intent from `progress_summary` and `completed_skills` only, so an account with Objetivos but no completed Habilidade and no selected Habilidade gets the fixed unavailable text. Resolving an Objetivo (by title, explicit ID, page hint or conversation continuity) still yields no progress fact.

Mode: **compact**. The change reads data Learning already owns inside the existing context contract. It adds no persistence, REST, event or web surface.

This change refines the bounded local-only delivery of [Mentor context revision 18](../../spec.md). Amendment 16 stays in force: local deterministic answers and an empty generation request. The base Spec is not edited.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Learner asks about progress | Overview of all own Objetivos with counts per status when no Objetivo and no Habilidade is resolved; list of Habilidades with status when an Objetivo is resolved without a Habilidade; completed Habilidades shown by name; distinct messages for no Objetivos and for an Objetivo without Habilidades; bounded answer size | Materials, activities, assessments and Gamification facts without a Habilidade context; links to open an Objetivo; a phrase to force the overview once an Objetivo is resolved; any AI-generated wording |
| Learning (owner of the data) | The context provider adds read-only fact values from reads it already performs | New Learning use cases, endpoints, persistence or events; changing progress, status or recommendations |
| Intelligence | The local route provider renders headings, bullets, the closing line and the no-Objetivos text from facts | Changing intent classification, FAQ retrieval, indexes, thresholds, clarification rules, the abstention or Core preparation |
| Failure handling | A failed read keeps the existing failed attempt with Retry | A local "could not verify" completed message |

Canonical outcomes (PRD Intelligence, content 83099649, version 9):

- **RP-04 — partial.** Included: the Mentor consults the learner's own Objetivos, Habilidades and progress without confirmation, the current screen being only a hint, and says plainly when information is missing. Still deferred: generated explanations, materials, activities, assessments and Gamification without a Habilidade context.
- **RP-05, JN-02 — unchanged.** Pedagogical limits and the page-hint journey keep the parent contract.
- **RP-11/RP-13 — unchanged.** Only the authenticated account's data is read; nothing is stored beyond the existing answer block.

# Behavior Contract

"Resolved Objetivo" means an Objetivo identified by any existing source: its title in the message, an explicit identifier, the validated page hint, or conversation continuity (the references of the previous completed answer of the conversation). "Selected Habilidade" means a Habilidade identified the same way. The overview applies only when no Objetivo is resolved.

| ID | RP / JN / source | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-04; user request | With no resolved Objetivo and no selected Habilidade, the local answer to a progress question is an overview. A heading "Progresso:" is followed by one bullet per Objetivo of the learner, ordered by most recent update (ties by identifier): `- <Título>: <n> Habilidade(s) — <contagens>.` Example: `- Estudar frações: 3 Habilidades — 1 não iniciada, 1 em aprendizado, 1 concluída.` Counts show only non-zero statuses, in this order: "não iniciada(s)", "em diagnóstico", "em aprendizado", "concluída(s)", with singular and plural agreeing with each number. An Objetivo without Habilidades reads `- <Título>: nenhuma Habilidade ainda.` When completed Habilidades exist, the section of RF-04 follows. The answer ends with "Diga o nome de um Objetivo para ver as Habilidades dele." |
| RF-02 | RP-04; user request | With a resolved Objetivo and no selected Habilidade, the local answer is the heading "Progresso no Objetivo <Título>:" followed by one bullet per Habilidade of that Objetivo, ordered by creation time (ties by identifier): `- <Nome da Habilidade>: <estado>`. The state is the existing label of the status ("não iniciada", "diagnóstico em andamento", "em aprendizado", "concluída"). The completed-Habilidades section is not added. When several Objetivos match the title in the message, the existing clarification stays and no list is shown. |
| RF-03 | RP-04 | A resolved Objetivo with no Habilidades is answered with the heading of RF-02 followed by `- Este Objetivo ainda não tem Habilidades.` |
| RF-04 | RP-04 | Every answer that lists completed Habilidades renders each entry as `<Nome da Habilidade> (Objetivo <Título>)` in the existing "Habilidades concluídas:" section. No raw identifier is shown. A Habilidade without a catalog name is shown as "Habilidade sem título". |
| RF-05 | RP-04 | Each list of an answer (Objetivos, Habilidades, completed Habilidades) shows at most 20 items. When more exist, one extra last line `e mais <n>.` gives the exact remaining count (as a bullet in bulleted lists). |
| RF-06 | RP-04 | When the learner has no Objetivos, a progress question is answered with "Você ainda não tem Objetivos. Crie um na tela inicial para acompanhar seu progresso." The fixed text "Essas informações estão indisponíveis no momento." remains for the other fact intents that lack their facts, except that it is not added when another matched fact intent with a higher similarity has facts to render (a weaker, probably false second match such as gamification on "qual o meu atual progresso?"). |
| RF-07 | RP-04, parent RF-05/06/07/08 | Everything with a selected Habilidade (the `progress_summary` rendering, validated hints, explicit references, the ambiguity clarification, the diagnostic boundary and the pedagogical limits) is unchanged, except for the names required by RF-04. A Habilidade in diagnostic shows only its status label: no activity, answer or evaluation is read or shown. Facts of the larger lists also travel in the generation context of attachment-backed requests as before, bounded by RF-05. |
| RF-08 | RP-04/11/13, parent RF-05/07/12/14 | Only the authenticated account's own Objetivos and Habilidades are read, from current state at every message; history proves nothing. The route still returns an empty generation request and calls no model. If Learning cannot be read, the answer attempt fails recoverably and Retry works as today; no completed block reports the failure. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-08 | An account with Objetivos covering all four statuses, one Objetivo with no Habilidades, and completed Habilidades; no page hint; a new conversation | "Qual é meu progresso no Objetivo?" | One local block: the "Progresso:" bullets in most recently updated order with correct counts and plural/singular, then "Habilidades concluídas:", then the closing line; no model request | CI-01 / VM-01 |
| CA-02 | RF-02, RF-07 | The same account, a new conversation | A message naming one Objetivo by title; a message matching two Objetivos with the same title | First: the heading with that title and the Habilidades with names and states, no completed section. Second: the existing clarification question, no list | CI-01 / VM-01 |
| CA-03 | RF-02, RF-07 | The same account | A progress question with a page hint carrying only `goal_id`; then in a conversation where an Objetivo was named, a later "meu progresso"; then the same question in a new conversation | The first two give the Habilidade list of that Objetivo; the new conversation gives the overview | CI-01 |
| CA-04 | RF-03 | An Objetivo without Habilidades | The learner names it | The heading and `- Este Objetivo ainda não tem Habilidades.` | CI-01 |
| CA-05 | RF-04, RF-07 | An account with completed Habilidades in two Objetivos, one Habilidade without catalog name | "Quais Habilidades já concluí?" and a selected-Habilidade progress question | Entries read `<nome> (Objetivo <título>)`, "Habilidade sem título" for the unnamed one, no identifier; the selected-Habilidade summary line is byte-identical to today | CI-01 |
| CA-06 | RF-05 | More than 20 Objetivos; one Objetivo with more than 20 Habilidades; more than 20 completed Habilidades | The three corresponding questions | At most 20 items per list plus `e mais <n>.` with the right remainder | CI-01 |
| CA-07 | RF-06 | An account without Objetivos; a gamification question whose facts are absent | A progress question; the gamification question | The no-Objetivos message; the gamification question keeps "Essas informações estão indisponíveis no momento." | CI-01 |
| CA-10 | RF-06 | A progress question the classifier also matches, more weakly, to gamification, with no gamification facts | The question runs through the real local route | Only the progress answer is published, without the unavailable line; when the missing-fact intent is the stronger match, the line stays | CI-04 |
| CA-08 | RF-07, RF-08 | A Habilidade in diagnostic with an active Atividade diagnóstica; a second account whose Objetivos are seeded directly | The first account asks a progress question | Only the status "diagnóstico em andamento" appears, no activity detail; no title or Habilidade of the second account appears | CI-01 |
| CA-09 | RF-08 | The Learning context read fails once for a progress question | The attempt runs, then the learner retries | The attempt fails recoverably, Retry produces the answer, no completed error-like block exists | CI-01 |

# Technical Contract

## Architecture Mapping

**Owner:** Intelligence for rendering and copy of headings, bullets, closing line and no-Objetivos text; Learning for the fact values (titles, counts, status labels, names, remainders). Identity contributes only the existing access guards. Rules ([router](../../../../../rules.md)): Python Conventions, Provision Layer (both providers), AI Layer (routing provider), Job Testing (registered AgentOS boundary). Add Controllers Testing and Database rules if the test fixtures under `tests/fixtures/**` change. Re-run discovery if the scope expands.

**Selected approach and rationale:** extend the two existing providers behind the existing `MentorContextSnapshot.facts` contract. Learning already iterates the learner's Objetivos and Habilidade experiences to build `completed_skills`, so counts and per-Habilidade status come from the same reads. Intelligence only renders facts. Rejected: a new Learning use case or REST read (no consumer needs it), changing Core preparation (it needs no new input), a local "could not verify" block (it would turn a failed answer into a completed one and conflict with parent RF-12), a phrase rule that forces the overview (deferred, Q7), and AI-written summaries (excluded by Amendment 16).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Modify | Learning provider | `LearningMentorContextProvider.read` in `apps/server/src/shifu/learning/providers/learning_mentor_context_provider.py` | Emit the facts of the fact contract below; sort Objetivos by (`updated_at` desc, `id`) and Habilidades by (`created_at`, `id`); render completed Habilidades with catalog names and the Objetivo title; apply the 20-item bound; keep the selected-Habilidade facts byte-identical. The selected-Habilidade path emits none of `progress_overview`, `goal_progress_title` and `goal_skill_status`; that is what keeps its rendering unchanged. |
| Modify | Intelligence provider | `LocalMentorRouteProvider._local_blocks` in `apps/server/src/shifu/intelligence/providers/routing/local_mentor_route_provider.py` | Render the new keys as in RF-01 to RF-03, add the closing line, choose the no-Objetivos text when the learner has no `goals` facts for a progress intent, keep the existing rendering for `progress_summary` and the unavailable text for the other fact intents. |
| Modify | In-process workflow tests | `apps/server/tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py`, class `TestAgnoProcessMentorResponseWorkflowProgress` | Scenarios of CI-01 over the real Learning context provider and the real local route on a stubbed intent index. |

Unchanged on purpose: `MentorContextSnapshot` and its `facts` pair type, `PrepareMentorResponseUseCase`, intent resources and indexes, the web, REST, persistence and events.

```text
apps/server/
├── src/shifu/learning/providers/learning_mentor_context_provider.py          [M]
├── src/shifu/intelligence/providers/routing/local_mentor_route_provider.py   [M]
└── tests/intelligence/ai/workflows/
    └── test_agno_process_mentor_response_workflow.py                         [M]
documentation/features/intelligence/mentor-context/changes/
└── progress-overview-without-context/spec.md                                 [N]
```

**Fact contract (closed set).** `facts` stays a tuple of `(key, value)` pairs. Learning emits these keys:

- `progress_overview`: one value per Objetivo, the text after the bullet in RF-01 (the last value may be `e mais <n>.`).
- `goal_progress_title`: exactly one value, the title of the resolved Objetivo, present when RF-02 or RF-03 applies.
- `goal_skill_status`: one value per Habilidade (`<Nome>: <estado>`), or the single value `Este Objetivo ainda não tem Habilidades.`; the last value may be `e mais <n>.`.
- `completed_skills`: values `<Nome> (Objetivo <Título>)`, the last value possibly `e mais <n>.`.
- `progress_summary`: unchanged (selected Habilidade and the existing per-competency lines).
- `goals`: unchanged, one value per Objetivo; its absence means the learner has no Objetivos.

Learning still emits `completed_skills` for every goal, so the renderer must ignore it in the Objetivo list. Intelligence renders, in order: first, for a progress intent with no `goals` fact, the no-Objetivos text; else if `goal_skill_status` exists, the heading `Progresso no Objetivo <goal_progress_title>:` with bullets and no completed section; else if `progress_overview` exists, the heading `Progresso:` with bullets, then the existing "Habilidades concluídas:" rendering of `completed_skills` when present, then the closing line; else the existing rendering of `progress_summary` and `completed_skills`, which is byte-identical to today apart from names. The completed section keeps today's unbulleted form (the label, then one entry per line). Sections are separated by a blank line, as today.

**Observable copy** (fixed pt-BR text). Intelligence emits: the headings above, the closing line "Diga o nome de um Objetivo para ver as Habilidades dele." and "Você ainda não tem Objetivos. Crie um na tela inicial para acompanhar seu progresso." Learning emits inside fact values: "Este Objetivo ainda não tem Habilidades.", "e mais <n>.", "Habilidade sem título" and "nenhuma Habilidade ainda".

## Runtime Flow

1. A learner message arrives. The existing preparation step reads the Learning context with the page hint and the conversation's continuity references, and resolves a named Objetivo or Habilidade as today.
2. The Learning provider returns the facts for the resolved scope: the overview facts when no Objetivo is resolved, the Habilidade facts when an Objetivo is resolved without a Habilidade, the unchanged facts when a Habilidade is selected.
3. The local route provider classifies the question, renders one local block under RF-01 to RF-06, and the existing flow saves and publishes it. `generation_requests` stays empty.
4. If any Learning read raises, the existing failure handling applies: the attempt fails recoverably and Retry re-reads current state.
5. Continuity is existing behavior: once an Objetivo is resolved in a conversation, later vague questions keep resolving to it until a new conversation starts (Q7 = A).
6. Isolation and the access guards are unchanged: state is read per message, scoped to the authenticated account.

# Verification Contract

## Shared setup

Server automated checks run the response workflow in process (`tests/intelligence/ai/workflows`), over the disposable PostgreSQL at Alembic head, with the agents replaced by `unittest.mock.Mock`. The Learning context is the real `LearningMentorContextProvider` over the Learning and Curriculum rows, with the real Curriculum catalog projection for names. The route is the real local route provider over a stubbed intent index whose similarities select the intent: classification and thresholds are out of scope and need no pgvector index. Rows use the existing fakers and repositories because `skill_experiences.skill_id` has no foreign key, but names need the catalog. A Learning read failure is injected once by wrapping `read` on the mocked context provider. The second account of CA-08 is seeded directly in the database while the fixture account asks. Accounts come from the Intelligence fixture (`tests/fixtures/intelligence_fixture.py`).

Manual checks run on a disposable stack, never the shared development database:

1. Start a disposable `pgvector/pgvector:0.8.1-pg17` container and a disposable Redis container, each on a free port, and run `apps/server/scripts/create_agentos_runtime_role.sql` against the database.
2. Export `DATABASE_URL`, `AGENTOS_DATABASE_URL`, the web `BETTER_AUTH_DATABASE_URL` and the Redis URL for those containers, with `SHIFU_SERVER_APP_MODE=local` (see [Tooling](../../../../../tooling.md) for the variables). Before starting, confirm that `apps/server/.env.local` and the web env file do not override them, and record how the effective values were checked.
3. From `apps/server` run `uv run alembic upgrade head`, then, after checking that `DATABASE_URL` points at the disposable host and port, `uv run python -m shifu.shared.database.seed` (destructive: never run it against the shared database), then `uv run python -m shifu.mentor_indexes`.
4. Start the API on 7777 and the web on 7000 with the same variables and sign in as the documented seed account.
5. Before the journey, query the disposable database for the expected counts per Objetivo and status; the expected answer is derived from that query, not hard-coded.
6. Afterwards delete only the conversations the journey created, stop the task-started processes and remove both containers.

## Automated

### CI-01 — Local progress answers from the learner's own data

**Criteria:** CA-01, CA-02, CA-03, CA-04, CA-05, CA-06, CA-07, CA-08, CA-09

**Expected result:** every scenario of CA-01 to CA-09 through the registered runtime, each in its own conversation where continuity would otherwise interfere: overview with all statuses, counts, plural and singular, order, completed section and closing line; named list; ambiguous title clarification unchanged; hint and continuity cases; empty Objetivo; names and "Habilidade sem título", selected-Habilidade summary byte-identical; 20-item bound with the exact remainder in all three lists; no-Objetivos message; gamification absence keeps the unavailable text; diagnostic status only; no foreign account data; one failing Learning read gives a recoverable failure and Retry succeeds; zero requests to the model endpoint (`model_transport.requests`) in every scenario.

**Proof:** `apps/server/tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py`, class `TestAgnoProcessMentorResponseWorkflowProgress`, in-process workflow boundary (providers get no dedicated tests under the AI and Provider Rules).

```bash
cd apps/server && uv run pytest tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py
```

**Passing condition:** every listed scenario asserted, including absent effects; the tests run (not skipped).

### CI-02 — Routing regression

**Criteria:** CA-05, CA-07

**Expected result:** the existing local FAQ, abstention and fact behavior is unchanged where this change does not apply.

**Proof:** the other cases of `apps/server/tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py` and `apps/server/tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py`, unchanged in behavior. The first exercises local publishing, abstention and limits through the workflow; the second consumes the same context contract.

```bash
cd apps/server && uv run pytest tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py
cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py
```

**Passing condition:** pass unchanged, not skipped.

### CI-04 — Weaker second fact intent adds no unavailable line

**Criteria:** CA-10

**Expected result:** with the real local route over a stubbed intent index, a progress question that also matches gamification more weakly publishes only the progress answer; a gamification question without facts keeps the unavailable text; when the missing-fact intent is the stronger match, the line stays after the progress answer.

**Proof:** `apps/server/tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py`, three cases whose names contain `unavailable_line`, in-process workflow test with mocked agents.

```bash
cd apps/server && uv run pytest tests/intelligence/ai/workflows/test_agno_process_mentor_response_workflow.py
```

**Passing condition:** pass, not skipped.

### CI-03 — Static gates

**Scope:** the two modified server files, the new test file and their consumers.

**Checks:**

- types: `cd apps/server && uv run poe check:types`;
- lint and format on exact changed paths: `uv run ruff check --no-fix <paths>` and `uv run ruff format --check <paths>`, which include the configured `C90` complexity rule (no quantitative complexity metric is configured or required; that disposition is recorded);
- architecture: `uv run poe check:architecture`;
- build: `uv run poe build`;

See [Tooling](../../../../../tooling.md#scoped-type-lint-and-complexity-checks).

**Passing condition:** zero errors and diagnostics. The repository no longer enforces changed-file coverage thresholds (see [Tooling](../../../../../tooling.md)), so none is required; the new tests still prove every criterion through CI-01.

## Manual

### VM-01 — Progress answers on a real stack

**Type:** Manual

**Criteria:** CA-01, CA-02

**Tool / setup:** `playwright-cli` from `apps/web` against the disposable stack of Shared setup, 1440×900.

**Procedure:** open `/intelligence` with no page context and start a conversation with "Qual é meu progresso no Objetivo?"; read the answer. Start a second conversation, name one seeded Objetivo by its title and read the list. In a third conversation send a message that matches nothing local.

**Passing condition:** the overview lines equal the counts queried before the journey, the named list shows the Habilidade names and states, the third message keeps the abstention; no console errors (warnings classified); cleanup done. No visual comparison applies because no UI changes.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Intelligence](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649/Shifu+PRD+Intelligence), content 83099649, **version 9** (2026-10-13T16:12:19Z, "Remover elegibilidade ZDR do escopo do ditado browser-managed"), space 82509828, retrieved 2026-10-21 | RP-04, RP-05, JN-02 | No PRD change. The page was read in full through RP-05 and the journeys (RP-04 text read directly from Confluence); the lifecycle, quota, memory and action sections were skimmed as unaffected. Recheck the version at conclusion. | External write not authorized; none required |
| [Mentor context Spec revision 18](../../spec.md) | Local-only delivery, RF-03/05/06/07/12 | Remains the base contract; this change refines the progress answer only. Add a one-line pointer to this change at conclusion. | Confirm at conclusion |
| [Mentor context Evaluation](../../evaluation.md) | Historical evidence | Preserved untouched | — |
| [modules.md](../../../../../modules.md), [architecture.md](../../../../../architecture.md) | Ownership and runtime boundaries | Unchanged: Learning supplies read-only facts through the existing neutral snapshot, Intelligence owns the rendering | Confirm at conclusion |
| Rules and [Tooling](../../../../../tooling.md) | Boundaries and commands | Confirmed: providers get no dedicated tests; proof is through the in-process workflow boundary with mocked agents; no changed-file coverage list exists to extend | Recheck if scope expands |
| Jira | Delivery tracking | No ticket exists for this change; the user decides the key before commits (the branch key SHIFU-101 belongs to the learner memories delivery) | Open question for the user |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-21 | Initial contract: progress overview and Habilidade list from the learner's own data without page context, completed Habilidades by name, empty-Objetivo and no-Objetivos messages, 20-item bound, failure handling unchanged | User decisions Q1 = overview of all Objetivos, Q2 = Habilidades with names and status, Q3 = progress and status only, Q4 = distinct messages, Q5 = separate change Spec, Q6 = failed reads keep the existing failure and Retry, Q7 = any Objetivo source gives the list. Confirmed by the user at review of the written contract (2026-10-21): ordering rules and tie-breaks, the 20-item bound with one remainder line, the closing line, "Habilidade sem título" and the empty-Objetivo copy. PRD Intelligence v9 RP-04 |
| 2 | 2026-10-22 | Drop the changed-file coverage gate from CI-03 and the CI workflow row from the Architecture Mapping | The repository retired the changed-file coverage jobs and checker scripts and removed them from Tooling, so the contract item cannot be run or satisfied. No product behavior changed; CA-01 to CA-09 are unchanged. |
| 3 | 2026-10-22 | RF-06: the unavailable line is not added to an answer when a stronger matched fact intent has facts; new CA-10 proved by CI-04 | User report with a screenshot: "qual o meu atual progresso?" returned the overview followed by "Essas informações estão indisponíveis no momento." because gamification matched at 0.887 (threshold 0.871) against progress at 0.927. Rendering only; thresholds and classification are unchanged |
| 4 | 2026-10-22 | The proof of CI-01 and CI-02 moves from registered AgentOS tests to in-process workflow tests with mocked agents, the real Learning context and the real local route over a stubbed intent index | The repository removed every AgentOS runtime test (user request, same day) and the Job Testing rules now accept workflow tests. No product behavior changed; CA-01 to CA-10 are unchanged |
