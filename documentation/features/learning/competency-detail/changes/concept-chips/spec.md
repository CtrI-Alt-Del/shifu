---
title: Concept chips in Competency content
status: completed
revision: 1
source:
  type: direct-request
  ref: Codex conversation, 2026-09-28, "they should be shown as chips" and "do it"
scope:
  - apps/server/src/shifu/learning/core
  - apps/server/src/shifu/learning/rest/controllers/get_competency_detail_controller.py
  - apps/server/tests/learning
  - apps/web/src/core/learning/competency-detail.ts
  - apps/web/src/ui/learning/widgets/pages/competency-detail-page
  - apps/web/tests/learning
last_updated_at: 2026-09-28
---

# 1. Context and scope

Learning owns the Competency detail page. Its ordered Material and Activity rows currently show titles and type/difficulty, but not the Curriculum Concepts they address. The user requested visible chips on those rows after reviewing the current screenshot. This is a compact additive presentation change. The complete Learning PRD `83066881` v24 and Curriculum PRD `83034113` v12 were read on 2026-09-28; Learning RP-08/17/25/27 and JN-06 and Curriculum RP-05 govern the existing content, recommendation and Concept meanings.

| Area | In scope | Out of scope |
| --- | --- | --- |
| Sequence rows | Static named Concept chips for every officially mapped Material and Activity; target chip identified on a recommended row | Concept progress, filtering, navigation or editable tags |
| Data | Add item Concept IDs and names to the owned Competency detail projection | Curriculum mapping, recommendations, grading or persistence changes |
| Availability | Chips only in already authorized released content; unmapped legacy items remain usable | Exposing unreleased content or diagnostic answers |

| Source requirement | Delivery | Notes |
| --- | --- | --- |
| User request and Learning RP-08/17/25/27, JN-06 | partial | Shows mapped Concepts in this list; existing recommendation reason remains in the separate recommendation surface. |
| Curriculum RP-05 | partial | Uses official Concept names and associations already present in the Curriculum snapshot. |

# 2. Implementation Contract

| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | User request, Curriculum RP-05, Learning RP-08/27, JN-06 | Every released sequence row displays one noninteractive chip for each distinct officially associated Concept, in stable Curriculum order. Activity chips describe assessed Concepts; Material chips describe covered Concepts. Unmapped items remain readable without fabricated chips. |
| RF-02 | User request, Learning RP-17/25 | On a recommended row, visually and textually identify the chip for the current target Concept when that Concept is associated with the item. Preserve recommendation, action and item ordering. |
| RF-03 | Learning RP-08/25 | Preserve account authorization and restricted unreleased projection. Long names and multiple chips wrap without horizontal overflow at desktop and mobile widths; each row link's accessible name or description includes the mapped Concept names, despite any explicit `aria-label`. |

| ID | RF coverage | Given | When | Then | Evidence |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | A released Competency with multi-Concept Material and Activity mappings | The detail is fetched and rendered | Each item shows its own distinct official Concept names in stable order; no extra association is inferred from the title | Server use-case/controller and widget assertions |
| CA-02 | RF-01/02 | An Activity or Material is recommended for an associated Concept | The sequence is rendered | The target chip says `Foco atual` in text and is visually distinct; other chips stay neutral and the existing action remains available | Widget assertion and desktop/mobile capture |
| CA-03 | RF-01/03 | An existing item has no Concept mapping | The detail is rendered | The row and destination still work, with no empty chip or invented name | Use-case/widget assertion |
| CA-04 | RF-03 | An owned but unreleased Competency or a private absence | The route is requested | No item Concept names are disclosed | Controller test |
| CA-05 | RF-03 | Several or long Concept names at a narrow viewport | The user views and tabs through the page | Chips wrap, no horizontal page overflow, link focus remains usable, and each link's accessible name or description announces its Concept names | Widget assertion; Playwright CLI, 390×844 screenshot and keyboard check |

The accepted visual reference is the screenshot attached in this conversation, showing the ordered dark timeline and highlighted `Entrada por idade` row. The prior desktop/mobile competency handoff remains the layout and token reference. Chips are the user-approved addition to that reference, not a new Pencil behavior or interaction. Use existing Shifu surface, border, text and focus colors; do not make chips buttons. Required happy-path captures: released focus at 1440×900 and 390×844 with mapped Material and Activity, including a recommended target chip.

# 3. Technical Contract

| Boundary | Change |
| --- | --- |
| Learning projection | Map `CurriculumActivitySnapshot.concept_ids` and `CurriculumMaterialSnapshot.concept_ids` to `id`/`name` pairs from the Skill's official Concept snapshots; preserve item sequence and empty mappings. |
| REST | Add `concepts: [{id, name}]` to each available Material/Activity item, with no field on unavailable detail. |
| Web contract | Parse and type the Concept pairs; accept absent `concepts` as an empty list during compatible rollout. |
| UI | Render a row of static chip labels below existing metadata; highlight only the matching adaptive target on a recommended row. |

No new endpoint, database operation, Curriculum mutation or recommendation policy is required. The current Concept-to-item associations are authoritative; Activity prerequisites are not presented as assessed Concepts.

# 4. Validation Contract

| ID | Check | Coverage |
| --- | --- | --- |
| CI-01 | `uv run poe check:lint`, `uv run poe check:types`, `uv run poe check:architecture` in `apps/server` | Python and module contracts |
| CI-02 | Focused Learning use-case and controller pytest files | CA-01/03/04 |
| CI-03 | `pnpm check:lint`, `pnpm check:types`, `pnpm check:architecture` in `apps/web` | Web contracts |
| CI-04 | Focused Competency content row/list Vitest suites | CA-01/02/03 |
| VM-01 | Playwright CLI released Competency page at 1440×900 and 390×844; inspect fresh screenshots, links, focus and overflow | CA-02/05 |

Selected Rule Pack: Python Conventions, Core, REST, Controller Testing, TypeScript Conventions, UI, Widget Testing, plus `documentation/design.md`. UI captures verify the happy path only; automated tests cover empty mappings and private/restricted outcomes.

# 5. Documentation alignment and revision history

| Revision | Date | Change |
| --- | --- | --- |
| 1 | 2026-09-28 | Additive Concept-chip contract for the existing Competency sequence, sourced from the user's explicit request and current PRDs. |

No Confluence or Jira mutation is part of this delivery. This change leaves the concluded parent Spec intact.
