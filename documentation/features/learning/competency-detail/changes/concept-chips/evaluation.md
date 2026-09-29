---
title: Concept chips in Competency content evaluation
status: completed
spec: ./spec.md
spec_revision: 1
last_updated_at: 2026-09-28
---

# Evaluation status

Spec revision 1 is implemented. The complete Learning PRD `83066881` v24 and Curriculum PRD `83034113` v12 were read before implementation. No Confluence or Jira content was changed. The existing user edits outside this scope were preserved.

# Acceptance coverage

| Criterion | Evidence | Status |
| --- | --- | --- |
| CA-01 | Use-case mapping test covers multiple official Concepts, Skill-wide lookup, stable order, deduplication, and unknown IDs; controller test asserts exact nonempty `{id, name}` serialization; web tests render names | passed |
| CA-02 | Web tests assert only the matching recommended Concept says `Foco atual`; final desktop and mobile captures show distinct target chips and intact actions | passed |
| CA-03 | Use-case/controller and web tests cover empty or absent mappings without empty chips | passed |
| CA-04 | Controller test covers restricted detail with no item or Concept disclosure | passed |
| CA-05 | Web accessibility assertion and Playwright CLI keyboard check confirm link names announce Concepts; at 390 px, document scroll width is 390 px and Tab advances between row links | passed |

# Assignments and reviews

| Assignment | Result |
| --- | --- |
| `concept-chips-server-builder` | Learning DTO, use case, REST projection and focused tests completed in owned server paths |
| `concept-chips-web-builder` | Web contract, content rows/list and focused tests completed in owned web paths |
| Independent Spec reviewer | Found premature ready status and missing accessible-name requirement; both corrected before implementation |
| Integrated implementation reviewer | Found missing positive REST test and chip placement on Activity rows; both corrected |
| Integrated visual reviewer | Found Activity chips above metadata; corrected and recaptured desktop/mobile |

# Automated gates

| Check | Result |
| --- | --- |
| Server `uv run poe check:lint`, `check:types`, `check:architecture` | passed |
| Server focused use-case/controller pytest | 24 passed, 3 upstream deprecation warnings |
| Web `pnpm check:lint`, `check:types`, `check:architecture` | passed |
| Web focused Competency detail/list Vitest | 2 files, 7 tests passed |
| `git diff --check` | passed |

# Manual and visual evidence

Playwright CLI exercised the already running local application with an authenticated released Competency. The real detail request returned HTTP 200. The recommended Material `Condições, limites e combinações` and Activity `Entrada por idade` each showed the official `Condições e limites · Foco atual` chip; subsequent Activities and the final Material showed their own mapped Concepts. At 390×844, chips wrapped within the cards and no horizontal overflow occurred. Keyboard focus advanced from the recommended Activity link to the next Activity link, and each accessible name announced its Concept. The browser reported zero console errors. Final captures inspected against the user reference:

- Desktop 1440×900: `/home/petros/.codex/visualizations/2026/09/28/01a0e77e-ee47-7cb3-9e2c-2639aa95c9e3/concept-chips-desktop-final.png`
- Mobile 390×844: `/home/petros/.codex/visualizations/2026/09/28/01a0e77e-ee47-7cb3-9e2c-2639aa95c9e3/concept-chips-mobile-final.png`

Manual validation covers the released happy path; automated tests cover empty mappings and restricted access. The pre-existing local web/API and shared Docker services were left running; the Playwright CLI session was closed.
