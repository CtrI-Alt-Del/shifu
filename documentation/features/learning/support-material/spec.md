---
title: Learning Support Material
status: implemented
revision: 2
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-73
scope:
  - apps/server
  - apps/web
  - documentation/features/learning/support-material
last_updated_at: 2026-09-23
---

# 1. Context and scope

## Objective and source

Deliver `SHIFU-73` so an authenticated learner can read one support Material that
belongs to a released Competency inside their own Goal and Skill experience. The
page presents the official Markdown authored by Curriculum, keeps the Competency
that was used to reach the Material, offers a clear way back to it, and surfaces
the Competency's current recommended Activity without computing one of its own.

This is a **complete** Spec: the slice crosses TanStack Start/Query/Router, the
authentication BFF, FastAPI, the Learning and Curriculum modules and PostgreSQL.
It adds no persistence and no migration.

Canonical product authority:

| PRD | Content ID | Version | Retrieved | URL |
| --- | --- | --- | --- | --- |
| Learning | `83066881` | current at retrieval | 2026-09-23 | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning |
| Curriculum | `83034113` | current at retrieval | 2026-09-23 | https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum |

Selected requirements: Learning `RP-08`, `RP-17`, `RP-25`; journey `JN-06`.
Complementary authority: Curriculum `RP-02`.

The delivery source is [SHIFU-73](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-73).
Its traceability cites Learning version `6` and Curriculum version `2`; both pages
were re-read in full on 2026-09-23 and the selected requirements are unchanged in
substance. SHIFU-73 is blocked by [SHIFU-71](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-71)
and [SHIFU-72](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-72), both
`Concluído` and merged into `main` at `05d36a2`.

## Current behavior and product gap

`GetCompetencyDetailUseCase` already resolves ownership, Skill experience,
Competency availability, curricular order and the adaptive recommendation, and the
Competency page already links each Material row to
`/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/materials/$materialId`.

That route existed only as a contract stub whose loader threw `notFound()`, so
every Material link led to the generic not-found boundary. `CurriculumContentProvider`
exposed only `get_skill_content`, and `CurriculumMaterialSnapshot` carries `id`,
`title`, `material_type` and `position` — never the Markdown body. Learning had no
way to obtain the content of a Material.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Route | Authenticated Material route rendering a real page | The Activity route it recommends (SHIFU-74/75) |
| Content | Paragraphs, fenced code blocks and inline code, rendered as React elements | Headings, lists, tables, images or any block the ticket does not require |
| Safety | Embedded HTML shown as literal text | A Markdown or sanitiser dependency |
| Authorization | Owner-only, Competency must be released | Any new persistence or migration |
| Recommendation | Reuse the source Competency's current recommendation | Computing or persisting a Material-specific recommendation |
| Reading state | None | Read marking, read percentage, reading history, global Material library |

## Product decisions and assumptions

- **D1 — An unreleased Competency answers `200` with an `unavailable` payload, not
  `404`.** Learning RP-08 requires that locked content "deixe claro qual Competência
  está indisponível", which a generic 404 cannot do. This mirrors the accepted
  `UnavailableCompetencyDetail` contract from SHIFU-72. The payload carries no
  Material title and no content.
- **D2 — A Material that is not in the requested Competency's sequence answers a
  generic `404`.** Curriculum RP-02 makes the sequence the only link between a
  Material and a Competency, so this is an absence, not a lock.
- **D3 — The recommendation is delegated, never recomputed.** `GetMaterialDetailUseCase`
  composes `GetCompetencyDetailUseCase` and reuses its `recommendation` field. RP-17
  binds the recommendation to the Competency in focus, so a non-focus Competency
  yields `null` and the block is hidden entirely.
- **D4 — Markdown is rendered by a local subset parser, not a library.** The ticket
  requires paragraphs and code blocks and forbids interpreting embedded HTML.
  Building React elements makes HTML inert by construction and avoids adding a
  runtime dependency plus a sanitiser for two block types.

# 2. Implementation Contract

## Functional requirements

| ID | Requirement | Maps to |
| --- | --- | --- |
| `RF-01` | Expose `GET /learning/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/materials/{material_id}` for the authenticated owner. | `RP-08` |
| `RF-02` | Resolve the Material only through the Competency named in the route, so the Competency of origin is preserved when a Material is shared. | `RP-08`, Curriculum `RP-02` |
| `RF-03` | Return the official Markdown authored by Curriculum, unmodified. | `RP-08`, Curriculum `RP-02` |
| `RF-04` | Restrict the content when the Competency is not released, naming the blocked Competency. | `RP-08` |
| `RF-05` | Read a Material without writing progress, domain, status, events or any other state. | `RP-08` |
| `RF-06` | Present the source Competency's current recommended Activity, or hide the block entirely. | `RP-17` |
| `RF-07` | Navigate to the recommended Activity route, keeping the Material visible and offering a retry if that navigation fails. | `RP-17` |
| `RF-08` | Offer a labelled way back to the Competency of origin. | `RP-08` |
| `RF-09` | Render paragraphs, fenced code blocks and inline code; never interpret embedded HTML. | `RP-08` |
| `RF-10` | Provide loading, recoverable error, private absence and unavailable states in pt-BR, on desktop and mobile, operable by keyboard and never by colour alone. | `RP-25` |

## Acceptance criteria

| ID | Criterion | RF |
| --- | --- | --- |
| `CA-01` | Only the authenticated owner reads the Material inside the Goal, Skill and Competency of the route. | `RF-01` |
| `CA-02` | A Goal, Skill, Competency or Material that is absent or owned by another account returns the same generic not-found body. | `RF-01`, `RF-02` |
| `CA-03` | A Material outside the requested Competency's curricular sequence is a generic absence. | `RF-02` |
| `CA-04` | A Material of another Skill is a generic absence. | `RF-02` |
| `CA-05` | The rendered content equals the Markdown stored by Curriculum. | `RF-03` |
| `CA-06` | Paragraphs, fenced code blocks and inline code are readable and preserve indentation. | `RF-09` |
| `CA-07` | HTML inside the Markdown is displayed as text and never executed or mounted as interface. | `RF-09` |
| `CA-08` | The same Material reached from a different Competency keeps that Competency in the header and in the back action. | `RF-02`, `RF-08` |
| `CA-09` | Opening a Material changes no progress, domain, status, completion or event row. | `RF-05` |
| `CA-10` | The page offers no read marking, read percentage, reading history or global library. | `RF-05` |
| `CA-11` | An unreleased Competency hides the content and names the blocked Competency without telling the reader to advance in that same Competency. | `RF-04` |
| `CA-12` | The recommendation shown equals the source Competency's current recommendation. | `RF-06` |
| `CA-13` | No recommendation is computed or persisted by the Material. | `RF-06` |
| `CA-14` | When no recommendation exists, no recommendation block or action is rendered. | `RF-06` |
| `CA-15` | Selecting the recommendation navigates to the Activity route with all four identifiers. | `RF-07` |
| `CA-16` | A failure to open the Activity keeps the content visible, reports the problem and allows a retry. | `RF-07` |
| `CA-17` | A duplicate selection is blocked while the Activity is opening. | `RF-07` |
| `CA-18` | Loading, recoverable error and unavailable states give comprehensible feedback and an action. | `RF-10` |
| `CA-19` | Long content keeps a 68-character reading column and can be scrolled completely, including a wide code block, by keyboard. | `RF-10` |
| `CA-20` | The page works on desktop and mobile with visible focus and accessible names, and no state depends on colour alone. | `RF-10` |

## Cross-cutting restrictions

- Learning stays authoritative for availability; Curriculum stays authoritative for
  content. Neither module imports the other: the contract crosses through
  `shared/core/interfaces/CurriculumContentProvider`.
- No new table, column, migration or seed row. Development seed **content** was
  enriched so the local stack exercises real Markdown, which changes no schema.
- No new runtime dependency in `apps/web` or `apps/server`.

## Design Contract

Authority: [`documentation/design.md`](../../../design.md), section T23 —
"Leitura confortável, largura máxima de 68 caracteres. Caminho de volta claro para
a Competência de origem", and section 3.4 — "Material de apoio é exceção: DM Sans
16 / 28".

Pencil references from the ticket: design `RTwfu`, mobile `HQKUj`; desktop states
`qImzG`, `t7C2XU`, `j50Z0g`, `A1rzZ4`, `tLLeI`, `kpGXW`; mobile states `FCMbg`,
`x69MV`, `Pu6sO`, `mumyI`, `iFkAY`, `ClGcY`.

All fourteen frames were opened in Pencil on 2026-09-23, exported at scale `1` to
[`design/`](design/) and compared node by node against the implementation. That
comparison, the component and token mapping it produced, and the nine deltas it
found are recorded in [`design/handoff.md`](design/handoff.md).
No structural divergence was found: every frame's hierarchy, state inventory and
responsive behavior is present in the implementation, and Pencil structural inspection
reported no clipped or overflowing descendant in any of the fourteen frames.

The implementation also remains verified against `design.md`, which `ui-layer-rules.md`
declares the authority for tokens and typography, and measured in the running browser.
`ACH-02` in `evaluation.md` is closed by this comparison. Of the four copy and
iconography deltas it found, three were corrected in the runtime and one is accepted,
all recorded there as `ACH-05`.

# 3. Technical Contract

## Resulting contracts

```python
# shifu/shared/core/domain/structures/curriculum_material_content_snapshot.py
@structure
class CurriculumMaterialContentSnapshot:
    id: str
    skill_id: str
    title: str
    material_type: str
    content: str

# shifu/shared/core/interfaces/curriculum_content_provider.py
class CurriculumContentProvider(Protocol):
    def get_skill_content(self, skill_id: str) -> CurriculumSkillSnapshot | None: ...
    def get_material_content(
        self, material_id: str
    ) -> CurriculumMaterialContentSnapshot | None: ...
```

`AvailableMaterialDetail` carries `goal_id`, `skill_id`, `skill_name`,
`competency_id`, `competency_name`, `material_id`, `material_title`, `availability`,
`content` and `recommendation`. `UnavailableMaterialDetail` carries the same
context minus `material_title` and `content`, plus `focus_competency_id` and
`focus_competency_name`. Both reuse the existing `CompetencyAvailability` enum; no
new enum was introduced.

## Runtime flow

1. The route attaches `requireAuthMiddleware` and renders `MaterialPage`.
2. `useMaterialPage` runs `getMaterialDetailAction`, a TanStack server function that
   validates the four ULIDs, resolves the session through Better Auth and calls
   `LearningService.getMaterialDetail`.
3. `GetMaterialDetailController` builds `GetMaterialDetailUseCase` over
   `GetCompetencyDetailUseCase` and the Curriculum provider.
4. The use case delegates ownership, experience, availability, curricular order and
   recommendation to `GetCompetencyDetailUseCase`, then locates the Material among
   that Competency's items and fetches its content.
5. A `TypeAdapter` validates the returned structure against the discriminated
   response union.

Failures escape to the shared `AppErrorHandler`: `MaterialDetailNotFoundError` and
`CompetencyDetailNotFoundError` both derive from `NotFoundError` and map to a
generic `404`.

## Affected paths

```text
apps/server/src/shifu/shared/core/domain/structures/curriculum_material_content_snapshot.py   new
apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py                   port
apps/server/src/shifu/curriculum/providers/curriculum_content_provider/…                      adapter
apps/server/src/shifu/learning/core/domain/errors/material_detail_not_found_error.py           new
apps/server/src/shifu/learning/core/domain/structures/{available,unavailable,}material_detail.py new
apps/server/src/shifu/learning/core/use_cases/get_material_detail_use_case.py                  new
apps/server/src/shifu/learning/rest/controllers/get_material_detail_controller.py              new
apps/server/src/shifu/learning/rest/router.py                                                  registration
apps/server/src/shifu/shared/database/seed_data.py                                             richer Markdown
apps/web/src/core/learning/material-detail.ts                                                  new
apps/web/src/rest/services/learning-service.ts                                                 operation
apps/web/src/ui/shared/hooks/use-navigation.ts                                                 navigateToActivity
apps/web/src/ui/shared/styles/global.css                                                       --font-mono
apps/web/src/ui/learning/widgets/pages/material-page/**                                        new
apps/web/src/routes/learning/.../materials/$materialId.tsx                                     stub replaced
```

`apps/web/src/routeTree.gen.ts` is unchanged: the route file already existed, so the
generated tree already declared it.

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
| `tests/learning/core/use_cases/test_get_material_detail_use_case.py` | Use case, mocked ports | `CA-01`–`CA-05`, `CA-12`–`CA-14` |
| `tests/learning/server/controllers/test_get_material_detail_controller.py` | HTTP + real PostgreSQL | `CA-01`–`CA-05`, `CA-09`, `CA-11`, `CA-12` |
| `material-page/tests/material-page.test.tsx` | Page composition, hook mocked | `CA-08`, `CA-11`, `CA-14`, `CA-16`–`CA-18` |
| `material-page/tests/use-material-page.test.ts` | Page hook | `CA-15`–`CA-17` |
| `material-content/tests/material-content.test.tsx` | Markdown renderer | `CA-06`, `CA-07`, `CA-19` |
| `material-header/tests/material-header.test.tsx` | Header and back path | `CA-08` |
| `material-recommendation/tests/material-recommendation.test.tsx` | Recommendation block | `CA-12`, `CA-14`, `CA-16`, `CA-17` |
| `apps/web/tests/learning/material-page.test.ts` | Route, mocked transport | `CA-02`, `CA-05`–`CA-08`, `CA-11`, `CA-14`–`CA-20` |

`material-feedback` has no dedicated suite: all four of its states are rendered
through the real composition in `material-page.test.tsx`, where only the owning hook
is mocked. Adding an isolated suite would duplicate that coverage, which
`widget-testing-rules.md` discourages for an internal widget with no independent
reuse contract.

## Manual scenarios

Recorded with evidence in [`evaluation.md`](evaluation.md): `VM-01` released Material
against real persistence, `VM-02` restricted Competency, `VM-03` Material of another
Competency, `VM-04` back navigation and recommendation parity, `VM-05` mobile,
typography and keyboard.

# 5. Documentation alignment and revision history

## Evaluated Rule Pack

`rules.md` routing selected, and this delivery followed: Python Conventions, Core
Domain, REST, Use Case Testing, Controller Testing, Provider Layer, TypeScript
Conventions, UI Layer, Web App Routing, Widget Testing and Commit Rules. No rule
document was modified by this delivery.

## Revision history

| Revision | Date | Change |
| --- | --- | --- |
| 1 | 2026-09-23 | Initial Spec, implemented and validated locally. |
| 2 | 2026-09-23 | Pencil reached; the fourteen frames were exported and compared node by node, three copy deltas were corrected in the runtime, and the Design Contract now cites `design/handoff.md`. |
