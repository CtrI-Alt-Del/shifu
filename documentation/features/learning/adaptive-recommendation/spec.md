---
title: Learning adaptive recommendation
status: completed
revision: 1
source:
  type: prd
  ref: https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB
scope:
  - apps/server/src/shifu/curriculum
  - apps/server/src/shifu/learning
  - apps/server/src/shifu/shared/core/domain/structures
  - apps/server/migrations
  - apps/server/tests
  - apps/web/src/core/learning
  - apps/web/src/rest
  - apps/web/src/ui/learning
  - apps/web/src/routes/learning
  - apps/web/tests
  - apps/server/src/shifu/shared/database/seed_data.py
  - documentation/features/learning/adaptive-recommendation
last_updated_at: 2026-09-24
---

# Adaptive recommendation contract

The canonical [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB), content ID `83066881`, version 17, and [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB), content ID `83034113`, version 9, were read in full on 2026-09-24 UTC. This distinct change follows concluded choice-question Spec revision 3, which records Learning PRD version 13. Its choice grading and existing historical results remain valid, while new pedagogical state uses versioned policy. This delivery activates the policy for new experiences with valid Curriculum coverage and a completed choice-question diagnostic. Code and qualitative evaluators remain separate dependencies.

## Scope and authority

Learning owns learner-specific observations, progress, coverage, mastery, focus and recommendation. Curriculum owns Concepts, prerequisites, question mappings, criteria and content coverage. The shared layer carries immutable, module-neutral Curriculum snapshots. Intelligence may supply constrained interpretation, but cannot decide official state. Choice questions support both diagnostic and learning attempts when their official evaluator produces valid per-Concept observations; code and qualitative paths become eligible only when they offer the same trusted evidence. No score is projected onto every Concept merely because its Activity passed. New experiences must pass Curriculum coverage validation, pin policy v2, complete the diagnostic baseline and then enter learning. Existing v1 experiences continue their recorded policy. User-facing work includes the creation/start/diagnostic journey and the Competency detail and choice result surfaces.

| Requirement | Source | Observable outcome |
| --- | --- | --- |
| RF-01 | Curriculum RP-05/06 | Curriculum defines ordered Concepts, acyclic Concept prerequisites and Activity execution prerequisites within the Skill, material/Activity/Question mappings and per-Concept criteria. Activity prerequisites cannot include a Concept that the Activity evaluates. Only Activities with a trusted executable per-Concept evaluator count toward v2 coverage. Invalid or insufficient curricula cannot activate policy v2. |
| RF-02 | Learning RP-07/27, JN-18/21 | Valid question observations aggregate once per Concept/Activity only when all mapped observations are valid; inconclusive results preserve prior contribution and open verification; no observation stays unknown. |
| RF-03 | Learning RP-15/28, JN-09/20 | Recompute from fixed diagnostic baseline and latest valid contribution per Activity/Concept in first-submission order using policy 70/30; replacement may raise or lower progress; review after Skill completion leaves official state frozen. Existing experiences retain their creation policy. |
| RF-04 | Learning RP-16, JN-10/19 | Complete Competency progress is the mean of all Concept estimates with difficulty coverage; mastery requires mean 85, each Concept 70, two distinct Activities, all three difficulties, hard evidence 80 per Concept, and no verification. Regression requires the same cause in two relevant distinct Activities; released content never relocks. |
| RF-05 | Learning RP-17/28, JN-18/19/20/21 | Choose target by verification, missing evidence/coverage, low progress, hard confirmation and mean recovery. Resolve inadequate prerequisites recursively and deterministically; rank usable Activities by gap reduction and stable ties. Report curriculum/assessment gaps instead of inventing content. |
| RF-06 | Learning RP-08/17 and v17 first-contact amendment | On a Concept with no valid observation, offer an official Material as optional introduction together with a valid easy Activity when a suitable Material exists; otherwise keep the Activity as the next step. Direct practice stays available. Below 40 or two distinct recent failures below 40 also offer suitable optional Material; reading never changes progress. |
| RF-07 | Learning RP-18/25, JN-07/21 | Competency detail/result surfaces explain target, reason, recommended Material and Activity, incomplete coverage and verification separately from score. Pending/failed evaluation suspends new recommendation. |
| RF-08 | Learning RP-28 | Every new experience records policy identity; reconstruction never silently changes old experiences. Decisions and their input evidence remain auditable. |
| RF-09 | Learning RP-03/04/05/06/07, JN-02/03/04 | A learner can create a goal with selected Skills, start an eligible v2 Skill experience, complete every Competency's ordered diagnostic once per Activity, and establish one fixed baseline per Concept before entering learning. During diagnosis, individual scores, corrections and results are hidden, and Material/Mentor help is unavailable. Only consolidated diagnostic output is exposed at completion. Missing or invalid Curriculum coverage blocks start with an explainable gap. |

## Acceptance

| Criterion | RF | Required evidence |
| --- | --- | --- |
| CA-01 | RF-01 | Curriculum domain unit tests and consuming controller/job integration reject Concept/Activity prerequisite cycles, future prerequisites, self-dependencies, Activities requiring Concepts they evaluate, missing criteria, unsupported Activity types counted as v2 coverage, and content unable to provide required difficulty/diversity. |
| CA-02 | RF-02/03 | Unit and job tests cover unknown, zero, partial/inconclusive, same Activity retake, worse retake and stable ordering. |
| CA-03 | RF-04 | Unit/integration tests cover every mastery gate, two-step same-cause regression, recovery and preserved release. |
| CA-04 | RF-05/06 | Unit tests cover first contact with optional Material, known prerequisite, chained prerequisite, missing difficulty, promotions, consolidation, exhausted curriculum and deterministic ranking. |
| CA-05 | RF-07 | Real HTTP and browser evidence shows distinct score/evidence/progress/coverage, reasoned next action and permitted direct practice; mobile and keyboard behavior remain usable. |
| CA-06 | RF-08 | Migration/integration proves existing attempts and v1 experiences retained; new v2 experiences use only valid enriched curriculum; retry/replay idempotency and frozen Concept criteria preserved. |
| CA-07 | RF-09 | Authenticated end-to-end creation/start/diagnostic flow completes every Competency in order, permits one valid submission per diagnostic Activity, persists a pinned v2 experience and fixed Concept baseline, transitions to learning, and exposes only consolidated diagnostic output and a policy-backed next action. Attempt-result routes cannot leak diagnostic scores/corrections; no Material/Mentor help is shown during diagnosis. Invalid coverage is rejected without partial state. |

## Technical contract

The rollout is additive and fail-closed. Introduce Curriculum-owned persisted Concepts, Concept prerequisites and Activity execution prerequisites, plus mappings from existing Materials and Activity questions to Concepts. Extend the Curriculum provider snapshots with only the official data Learning needs, including Activity prerequisites and their validity. Introduce Learning-owned per-Concept observations and state, policy identity on a Skill experience, and a deterministic policy service. Keep existing learning-activity scores and historical attempt/result APIs intact. Evaluate choice questions deterministically, but map answer outcomes to Concept evidence only through explicit Curriculum criteria. Freeze mapping and criteria in the immutable attempt grading snapshot at submission so retry/replay never reinterprets old answers against changed live content. Legacy experiences remain v1. New v2 experiences are accepted only after Curriculum coverage validation; otherwise report a curriculum gap instead of fabricating Concept results. The creation/start boundary pins v2. Diagnostic choice attempts establish the fixed Concept baseline before learning attempts can update progress. Diagnostic attempts use isolated result authorization/projection that never exposes individual scores or corrections; only the consolidated completed diagnostic is public to the learner. Code and qualitative paths without trusted evaluators cannot contribute to v2.

The work follows separate Curriculum catalog, Learning policy/persistence, and delivery/API/UI phases, with one integrated validation pass. Migration is additive and must preserve existing data. No shared rule engine, dynamic question generation, new user preference, automatic reading requirement, or global recommendation across Skills is allowed. The UI maps server decisions without recomputing pedagogy in the browser.

| Boundary | Existing path and required change |
| --- | --- |
| Curriculum domain/persistence | `apps/server/src/shifu/curriculum/core/domain/**`, `database/sqlalchemy/**`, `providers/curriculum_content_provider/**`: add Concepts, mappings, coverage validator and snapshot production. |
| Shared read contract | `apps/server/src/shifu/shared/core/domain/structures/curriculum_*`: add typed immutable Concept/catalog snapshots without Learning decisions. |
| Learning policy | `apps/server/src/shifu/learning/core/domain/**`, `core/use_cases/submit_choice_activity_use_case.py`, `core/use_cases/evaluate_choice_activity_use_case.py`, `core/use_cases/get_competency_detail_use_case.py`: freeze criteria, aggregate observations, recompute policy state, recommend and explain. |
| Experience activation | `apps/server/src/shifu/learning/core/use_cases/**`, `rest/**`, `apps/web/src/routes/learning/goals/**`: create Goal and selected Skill experiences, validate Curriculum before pinning v2, start and complete diagnostic choice attempts, establish baseline and enable learning. |
| Learning persistence | `apps/server/src/shifu/learning/database/sqlalchemy/**`: persist policy identity, Concept state/observations, and recommendation evidence in the account-owned Skill experience. |
| Migration | `apps/server/migrations/versions/**`: additive revision after current heads, with existing v1 data preserved. |
| Server delivery | `apps/server/src/shifu/learning/rest/**`, `apps/server/rest-client/learning/activities.rest`: project new fields; maintain parity for changed routes. |
| Web delivery | `apps/web/src/core/learning/**`, `src/rest/**`, `src/ui/learning/**`: display returned recommendation/coverage/verification on existing pages. Preserve existing routes and design tokens. |

## Validation contract

| ID | Check | Coverage |
| --- | --- | --- |
| CI-01 | `uv run poe check:lint`, `uv run poe check:architecture`, `uv run poe check:types` from `apps/server` | Server source contract |
| CI-02 | `uv run poe test:unit`, `uv run poe test:integration`, `uv run poe test:jobs` from `apps/server` | Policy, HTTP/DB and async effect |
| CI-03 | `uv run poe build` from `apps/server` | Package build |
| CI-04 | `pnpm --filter web check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, `build` from repository root | Web contract and runtime |
| VM-01 | Disposable DB with pre-migration legacy experience, upgrade to new head, evaluate old attempt and inspect account-owned history | CA-06 |
| VM-02 | Authenticated new-goal and diagnostic journey with real valid Curriculum content, complete diagnostic and a three-question learning Activity, inspect HTTP/result/recommendation and persisted Concept evidence | CA-02/04/05/07 |
| VM-03 | At 1440×900 and 390×844, inspect existing Competency detail and result routes for first contact, material+activity, incomplete evidence and inconclusive state using Playwright CLI; inspect focus, DOM, console and failed requests | CA-05 |

The canonical product decision for no-evidence Material was explicitly chosen by the user in this task and written to Learning PRD v17. Existing unrelated workspace changes in choice UI, tests, design and repository rules must be preserved and reviewed before integration. No Confluence or Jira status is changed as an implementation side effect.

Revision 1 is implemented and locally validated. The [Evaluation](evaluation.md) records acceptance, runtime and visual evidence, resolved findings, and remaining validation limits; the [Plan](plan.md) records completed delivery phases.
