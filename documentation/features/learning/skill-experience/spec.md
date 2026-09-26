---
title: Learning Skill Experience
status: implemented
revision: 2
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-66
scope:
  - apps/server
  - apps/web
  - documentation/features/learning/skill-experience
last_updated_at: 2026-09-25
---

# 1. Context and scope

## Objective and source

Deliver `SHIFU-66` so an authenticated learner opens one Skill of their own Goal and
understands, in a single page, how far they are, which Competency is in focus, what the
system recommends next, and which Competencies they may already open. The page stays
honest while an evaluation of that Skill is running or has failed: it shows the
situation, keeps released content reachable, and offers recovery.

This is a **complete** Spec: the slice crosses TanStack Start/Query/Router, the
authentication BFF, FastAPI, the Learning and Curriculum modules and PostgreSQL. It
adds no table, no migration and no write operation.

Canonical product authority:

| PRD | Content ID | Version | Retrieved | URL |
| --- | --- | --- | --- | --- |
| Learning | `83066881` | 6 at retrieval | 2026-09-23 | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning |

Selected requirements: Learning `RP-05`, `RP-08`, `RP-13`, `RP-14`, `RP-15`, `RP-16`,
`RP-17` and `RP-25`; journeys `JN-06`, `JN-07`, `JN-08`, `JN-09` and `JN-10`.

The delivery source is [SHIFU-66](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-66).
It blocks `SHIFU-21`, `SHIFU-37`, `SHIFU-38` and `SHIFU-39`.

## Current behavior and product gap

The route `/learning/goals/$goalId/skills/$skillId/` already renders a `SkillPage`
delivered by the diagnostic slice: it starts a Skill, follows a running diagnostic and,
once the diagnostic settles, shows a bare consolidated summary with a link per
Competency. Diagnosis is explicitly out of `SHIFU-66`, so this delivery **replaces only
the settled branch** of that page — `status` `learning` or `completed` — and leaves the
`not-started` and `diagnosing` branches untouched.

On the server, `GetCompetencyDetailUseCase` already resolves ownership, Skill
experience, curricular order, release, focus and the adaptive recommendation, but only
for one Competency: it discards the rest of the walk, so no caller could obtain the
Skill's overall result or the list of its Competencies. It also hides the progress of a
blocked Competency, which the design requires the Skill page to show.

`CompetencyProgress` already owns the arithmetic the ticket restates: `record_result`
applies `0.7 × previous + 0.3 × score`, keeps the best hard score, and derives
`learning` / `developing` / `proficient` / `mastered` with the 85 average and 80
hard-activity thresholds. This delivery reads and presents that state.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Route | The settled branch of the Skill route | Starting or following a diagnostic |
| Reading | Skill name, situation, overall result, focus, ordered Competencies with progress, status and availability | Competency contents, owned by SHIFU-72 |
| Progress | Presenting the progress, status and mastery the domain already computes | Recomputing or persisting progress |
| Recommendation | Presenting the focus Competency's current recommendation and opening it | Computing a Skill-specific recommendation |
| Evaluation | Pending and failed states, and recovering through the existing retry endpoint | Producing the evaluation, owned by SHIFU-74 and SHIFU-75 |
| Removal | None | Removing the Skill and the `C51Tjy` states, owned by SHIFU-36 |

## Product decisions and assumptions

- **D1 — Progress is presented per Competency, not per Concept.** `RP-15` and `RP-16`
  define progress, coverage, diversity and regression verification over *Conceitos*.
  The Learning domain has no Concept entity: `CompetencyProgress` is the finest grain
  that exists, and both the ticket's acceptance criteria and every Pencil frame state
  the rules in Competency terms — a percentage, a status and a lock per row. This
  delivery implements that projection and claims no coverage of the Concept-level parts
  of `RP-15` and `RP-16`.
- **D2 — The overall result averages every Competency, including the blocked ones.**
  `RP-15` and the ticket agree. A Competency with no progress row contributes `0`.
- **D3 — Focus and displayed progress have one definition, shared by composition.** The
  repository's core layer has no domain-service concept, and its rules prefer composing
  use cases over new layers. `GetCompetencyDetailUseCase.find_focus` and
  `display_progress` were promoted from private to public statics, and
  `GetSkillExperienceDetailUseCase` calls them and composes the whole use case to obtain
  the focus recommendation. The Skill page and the Competency page therefore cannot
  disagree about who is in focus or what is recommended.
- **D4 — A blocked Competency is not a destination.** Selecting it keeps the reader on
  the page and explains the release requirement, naming the focus Competency. It is
  rendered as a button, never a link, so keyboard and pointer users meet the same wall.
- **D5 — A pending or failed evaluation pauses only new attempts of that Skill.** The
  Competency list and released content stay reachable, and the recommendation block is
  suppressed while an evaluation holds the Skill, which the payload enforces as an
  invariant.
- **D6 — Recovery reuses the endpoint SHIFU-74 delivered.** An earlier draft of this
  Spec added a reprocess endpoint. `RetryChoiceEvaluationUseCase` already reopens a
  failed evaluation on the same attempt and republishes the submission event, so this
  delivery calls it from the page instead of duplicating a domain action. No write
  operation is added here.
- **D7 — `Escolher outra` opens the focus Competency and starts nothing.**
- **D8 — An absent or foreign Skill answers the generic `404`.** Unlike a locked
  Competency, there is nothing the learner owns to describe, so no `unavailable`
  payload exists. The `f500p` and `gMddp` frames are the client rendering of that
  absence, consistent with what SHIFU-73 established.
- **D9 — The missing palette entries were added centrally.** `jade-fill`, `jade-solid`,
  `jade-text`, `on-jade` and `text-secondary` are defined in `design.md` but had never
  been needed by the web app. They were added to `global.css` as shared tokens rather
  than authored as feature-local colors, which `ui-layer-rules.md` forbids.

# 2. Implementation Contract

## Functional requirements

| ID | Requirement | Maps to |
| --- | --- | --- |
| `RF-01` | Expose `GET /learning/goals/{goal_id}/skills/{skill_id}` for the authenticated owner. | `RP-05` |
| `RF-02` | Return the Skill's name, situation, overall result and focus Competency. | `RP-05`, `RP-15` |
| `RF-03` | Return every curricular Competency in order with its progress, status, focus condition and availability, including the blocked ones. | `RP-15`, `RP-16` |
| `RF-04` | Compute the overall result as the average of the progress of all Competencies. | `RP-15` |
| `RF-05` | Present the current recommendation of the focus Competency, with the Activity title, reusing the rules of the Competency detail. | `RP-17` |
| `RF-06` | Open the recommended Activity, and open the focus Competency without starting anything when the reader asks for another. | `RP-17` |
| `RF-07` | Navigate a released Competency to its detail route; keep a blocked one on the page and explain its requirement. | `RP-08`, `RP-16` |
| `RF-08` | Show a running evaluation without any final result and without recommending a new submission. | `RP-13`, `RP-17` |
| `RF-09` | Show a failed evaluation and allow processing it again through the existing retry endpoint. | `RP-14` |
| `RF-10` | Keep released content reachable while an evaluation is pending or failed. | `RP-14`, `RP-16` |
| `RF-11` | Never block content that was released before. | `RP-16` |
| `RF-12` | Work in pt-BR on desktop and mobile, operable by keyboard, never by colour alone. | `RP-25` |

## Acceptance criteria

| ID | Criterion | RF |
| --- | --- | --- |
| `CA-01` | Only the authenticated owner reads the Skill experience of the Goal in the route. | `RF-01` |
| `CA-02` | A Goal or Skill that is absent, or owned by another account, returns the same generic not-found body. | `RF-01` |
| `CA-03` | The page presents the Skill's name, situation, overall result and focus Competency. | `RF-02` |
| `CA-04` | Every Competency presents percentage progress, status, focus condition and availability. | `RF-03` |
| `CA-05` | Progress is the value the domain recomputed with `0.7 × previous + 0.3 × score`. | `RF-03` |
| `CA-06` | The overall result equals the average of every Competency's progress, blocked ones included. | `RF-04` |
| `CA-07` | The status bands respect the PRD limits. | `RF-03` |
| `CA-08` | Mastery requires at least 85 overall and at least 80 on a hard Activity. | `RF-03` |
| `CA-09` | The focus is the first Competency in curricular order that is not mastered. | `RF-02` |
| `CA-10` | Content released before is not blocked again when progress falls. | `RF-11` |
| `CA-11` | The recommendation is the one the focus Competency currently holds. | `RF-05` |
| `CA-12` | The continue action opens the current recommendation with all four identifiers. | `RF-06` |
| `CA-13` | Asking for another Activity opens the focus Competency and starts no Activity. | `RF-06` |
| `CA-14` | Selecting a released Competency navigates to its detail route. | `RF-07` |
| `CA-15` | Selecting a blocked Competency keeps the current page and explains the release requirement. | `RF-07` |
| `CA-16` | During a pending evaluation no final result and no recommendation are shown. | `RF-08` |
| `CA-17` | A pending or failed evaluation blocks only new attempts; released content stays reachable. | `RF-10` |
| `CA-18` | A failed evaluation preserves attempt and answer and allows reprocessing without duplicating the attempt. | `RF-09` |
| `CA-19` | Loading, absence and failure states give comprehensible feedback and recovery. | `RF-12` |
| `CA-20` | The page works on desktop and mobile with visible focus and accessible names. | `RF-12` |
| `CA-21` | No state or progress information depends on colour alone. | `RF-12` |

## Cross-cutting restrictions

- Learning stays authoritative for the learner's state; Curriculum stays authoritative
  for the curricular sequence. The contract crosses through `CurriculumContentProvider`.
- No new table, column, migration, seed row or write operation.
- No new runtime dependency in `apps/web` or `apps/server`.
- The removal item of the `uyfWq` menu belongs to SHIFU-36 and is not rendered.

## Design Contract

Authority: [`documentation/design.md`](../../../design.md) for tokens, dark-only
behavior, typography, focus and the responsive shell.

Pencil references: base `uyfWq`, mobile `wXPwI`; loading `XBet9`, `JNazF`; unavailable
`f500p`, `gMddp`; recoverable error `lcS3z`, `JXyUe`; evaluation running `uyhA7`,
`fYHyi`; evaluation failed `XxLQ1`, `vlvkI`.

All twelve frames were opened in Pencil on 2026-09-25, exported at scale `1` into
[`design/`](design/) and compared node by node against the implementation. The
comparison, the token mapping it produced and the deltas it found are recorded in
[`design/handoff.md`](design/handoff.md).

# 3. Technical Contract

## Resulting contracts

```python
# shifu/learning/core/domain/structures/skill_competency_summary.py
@structure
class SkillCompetencySummary:
    competency_id: str
    competency_name: str
    position: int
    progress: Decimal
    status: CompetencyProgressStatus
    availability: CompetencyAvailability
    is_focus: bool

# shifu/learning/core/domain/structures/skill_recommendation.py
@structure
class SkillRecommendation:
    competency_id: str
    competency_name: str
    activity_id: str
    activity_title: str
    difficulty: ActivityDifficulty
    type: ActivityRecommendationType

# shifu/learning/core/domain/structures/skill_evaluation_state.py
@structure
class SkillEvaluationState:
    evaluation_id: str
    attempt_id: str
    activity_id: str
    competency_id: str
    status: ActivityEvaluationStatus  # pending or failed only
```

`SkillExperienceDetail` carries `goal_id`, `skill_id`, `skill_name`, `skill_status`,
`overall_result`, `focus_competency_id`, `focus_competency_name`, `competencies`,
`recommendation` and `evaluation`. Its `__post_init__` refuses a list out of curricular
order, more than one focus, a recommendation that does not belong to the declared focus,
and a recommendation offered while an evaluation holds the Skill.

## Runtime flow

1. The route renders `SkillPage`, which keeps the diagnostic branches and delegates the
   settled branch to `SkillExperience`.
2. `useSkillExperience` runs `getSkillExperienceAction`, a TanStack server function that
   validates the two ULIDs, resolves the session and calls
   `LearningService.getSkillExperienceDetail`. It polls every three seconds while an
   evaluation is pending.
3. `GetSkillExperienceDetailController` builds `GetSkillExperienceDetailUseCase` over
   the Learning database, the Curriculum provider and `GetCompetencyDetailUseCase`.
4. The use case validates ownership and the experience, reads the curricular order,
   loads every progress row, derives focus and the per-Competency summaries, reads the
   unresolved evaluation of the experience, and — when nothing holds the Skill — composes
   the Competency detail of the focus to obtain its recommendation, enriching it with
   the Activity title resolved from the curricular snapshot.
5. Recovering a failed evaluation posts to the retry endpoint SHIFU-74 delivered.

`SkillExperienceDetailNotFoundError` maps to the generic `404`.

## Affected paths

```text
apps/server/src/shifu/learning/core/domain/errors/skill_experience_detail_not_found_error.py  new
apps/server/src/shifu/learning/core/domain/structures/skill_competency_summary.py             new
apps/server/src/shifu/learning/core/domain/structures/skill_evaluation_state.py               new
apps/server/src/shifu/learning/core/domain/structures/skill_experience_detail.py              new
apps/server/src/shifu/learning/core/domain/structures/skill_recommendation.py                 new
apps/server/src/shifu/learning/core/use_cases/get_competency_detail_use_case.py               two statics made public
apps/server/src/shifu/learning/core/use_cases/get_skill_experience_detail_use_case.py         new
apps/server/src/shifu/learning/rest/controllers/get_skill_experience_detail_controller.py     new
apps/server/src/shifu/learning/rest/router.py                                                 registration
apps/web/src/core/learning/skill-experience.ts                                                new
apps/web/src/rest/services/learning-service.ts                                                one operation
apps/web/src/ui/shared/styles/global.css                                                      five shared tokens
apps/web/src/ui/learning/widgets/pages/skill-page/skill-experience/**                         new
apps/web/src/ui/learning/widgets/pages/skill-page/skill-overview/**                           new
apps/web/src/ui/learning/widgets/pages/skill-page/skill-recommendation/**                     new
apps/web/src/ui/learning/widgets/pages/skill-page/skill-competency-list/**                    new
apps/web/src/ui/learning/widgets/pages/skill-page/skill-evaluation-notice/**                  new
apps/web/src/ui/learning/widgets/pages/skill-page/use-skill-experience.ts                     new
apps/web/src/ui/learning/widgets/pages/skill-page/index.tsx                                   settled branch delegated
```

`apps/web/src/routeTree.gen.ts` is unchanged: the route file already existed.

# 4. Validation Contract

## Executable commands

```bash
cd apps/server && uv run poe check:lint
cd apps/server && uv run poe check:types
cd apps/server && uv run poe check:architecture
cd apps/server && uv run poe test:unit
cd apps/server && uv run poe test:integration
pnpm --dir apps/web check:types
pnpm --dir apps/web check:lint
pnpm --dir apps/web check:architecture
pnpm --dir apps/web test:unit
pnpm --dir apps/web test:integration
```

## Automated test cases

| Suite | Boundary | Criteria |
| --- | --- | --- |
| `tests/learning/core/use_cases/test_get_skill_experience_detail_use_case.py` | Use case, mocked ports | `CA-01`–`CA-11`, `CA-16`, `CA-17` |
| `tests/learning/server/controllers/test_get_skill_experience_detail_controller.py` | HTTP + real PostgreSQL | `CA-01`–`CA-06`, `CA-09`, `CA-11` |
| `skill-page/skill-experience/tests/skill-experience.test.tsx` | Page composition | `CA-03`, `CA-04`, `CA-12`–`CA-18` |
| `apps/web/tests/learning/skill-experience-page.test.ts` | Route, mocked transport | `CA-03`, `CA-12`–`CA-18`, `CA-20` |

## Manual scenarios

Recorded with evidence in [`evaluation.md`](evaluation.md).

# 5. Documentation alignment and revision history

## Evaluated Rule Pack

Python Conventions, Core Domain, REST, Use Case Testing, Controller Testing, TypeScript
Conventions, UI Layer, Web App Routing, Widget Testing and Commit Rules. No rule
document was modified.

## Revision history

| Revision | Date | Change |
| --- | --- | --- |
| 1 | 2026-09-23 | Initial Spec, drafted from SHIFU-66 and Learning PRD version 6. |
| 2 | 2026-09-25 | Reconciled with a `main` that gained the diagnostic Skill page, the SHIFU-74 recommendation and its retry endpoint: the reprocess operation was dropped (`D6`), the absence contract became the generic 404 (`D8`), and the shared tokens were recorded (`D9`). Implemented and compared against the twelve frames. |
