---
title: Learning Support Material — Evaluation
status: ready
revision: 2
spec: ./spec.md
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-73
last_updated_at: 2026-09-23
---

# 1. Delivery disposition

| PRD requirement | Disposition | Note |
| --- | --- | --- |
| Learning `RP-08` | `implemented` | Curricular access, shared Material keeping its Competency of origin, reading without progress, locked content naming the blocked Competency. |
| Learning `RP-17` | `implemented` | The Material reuses the source Competency's current recommendation and never computes one. |
| Learning `RP-25` | `implemented` | pt-BR, desktop and mobile, keyboard, visible focus, no colour-only state. |
| Curriculum `RP-02` | `implemented` | The curricular sequence is the only link between Material and Competency; a Material belongs to one Skill. |

# 2. Quality gates

| ID | Command | Result |
| --- | --- | --- |
| `CI-01` | `uv run poe check:lint` (`apps/server`) | `ruff check` clean. `ruff format --check` reports 75 pre-existing files, all untouched empty `__init__.py` modules holding CRLF from a checkout older than `.gitattributes`. Every file changed by this delivery is clean. See `ACH-01`. |
| `CI-02` | `uv run poe check:types` | 0 errors, 0 warnings, 0 notes. |
| `CI-03` | `uv run poe check:architecture` | All modules validated. |
| `CI-04` | `uv run poe test:unit` | 10 new use-case tests pass. |
| `CI-05` | `uv run poe test:integration` | 20 passed against real PostgreSQL via Testcontainers, 9 of them new. |
| `CI-06` | `pnpm --dir apps/web check:types` | Clean. |
| `CI-07` | `pnpm --dir apps/web check:lint` | Clean over every path changed by this delivery. The repository-wide run reports the same pre-existing CRLF files described in `ACH-01`. |
| `CI-08` | `pnpm --dir apps/web check:architecture` | No dependency violations, 151 modules cruised. |
| `CI-09` | `pnpm --dir apps/web test:unit` | 28 files, 112 tests pass; 46 of them belong to this feature. |
| `CI-10` | `pnpm --dir apps/web test:integration` | `tests/learning` 25 passed, 11 of them new. |

# 3. Acceptance matrix

| CA | Evidence |
| --- | --- |
| `CA-01` | `CI-05` `test_missing_bearer_is_unauthorized`; `VM-01` signed in as the seeded account. |
| `CA-02` | `CI-05` `test_goal_of_another_account_is_a_private_absence` returns `{"code":"not_found","message":"Recurso não encontrado."}`. |
| `CA-03` | `CI-05` `test_material_of_another_competency_is_a_private_absence`; `VM-03`. |
| `CA-04` | `CI-05` `test_material_of_another_skill_is_a_private_absence`; `CI-04` rejects content whose `skill_id` differs. |
| `CA-05` | `CI-05` asserts the body starts with the seeded sentence and contains the fence; `VM-01` renders it from PostgreSQL. |
| `CA-06` | `CI-09` `material-content` asserts language label and preserved indentation; `VM-01` screenshot. |
| `CA-07` | `CI-09` asserts no `img`, `b` or `script` element is created; `CI-10` asserts `'__xss' in window` is `false` after rendering an `onerror` payload. |
| `CA-08` | `CI-09` `material-header` with two different Competency names; `VM-04`. |
| `CA-09` | `CI-05` `test_released_material_serializes_official_markdown_without_events` compares the event count before and after. |
| `CA-10` | The page renders no such control; `CI-09` asserts the rendered tree. |
| `CA-11` | `CI-05` `test_unreleased_competency_restricts_the_material_content` asserts `content` and `materialTitle` are absent; `CI-09` covers both phrasings; `VM-02`. |
| `CA-12` | `CI-05` `test_released_material_exposes_the_recommendation_of_its_competency` compares the Material payload with the Competency payload field by field; `VM-04`. |
| `CA-13` | The use case has no recommendation logic; `CI-04` asserts the value is the delegated object. |
| `CA-14` | `CI-09` and `CI-10` assert the block and its button are absent. |
| `CA-15` | `CI-10` asserts the resulting URL; `VM-04` observed the real navigation. |
| `CA-16` | `CI-09` `use-material-page` rejects the navigation and asserts the recoverable state. |
| `CA-17` | `CI-09` asserts the disabled pending control and that a duplicate click does not call the handler. |
| `CA-18` | `CI-09` covers loading, error with retry, private absence and unavailable; `CI-10` covers retry against transport. |
| `CA-19` | `CI-10` asserts no horizontal page scroll at 375×812; `VM-05` measured a 68-character column. |
| `CA-20` | `CI-10` focuses the code block and the recommendation; `VM-05` measured typography and mobile layout. |

# 4. Manual validation

Stack: `docker compose up -d postgres` (`localhost:54344`), an existing Redis on
`6379`, `alembic upgrade head`, `python -m shifu.shared.database.seed`, FastAPI on
`127.0.0.1:7777`, web on `127.0.0.1:7000`. Signed in through the real form as
`student.seed@shifu.com`.

### `VM-01` — Released Material against real persistence

`/learning/goals/01SHF000000000000000000012/skills/01SHF000000000000000000002/competencies/01SHF000000000000000000020/materials/01SHF000000000000000000021`
rendered the heading "Por que repetir instruções?", two paragraphs, the Python code
block with preserved indentation and inline `print`. One RPC request carried all
four identifiers. No console errors.

### `VM-02` — Restricted Competency

The Python Skill's "Funções" Competency has no released progress. The page showed
"Material ainda indisponível" with no content and no Material title.

### `VM-03` — Material of another Competency

Requesting `…/competencies/01SHF000000000000000000020/materials/01SHF000000000000000000007`
("Introdução aos algoritmos", which belongs to the Variables Competency) returned the
generic "Recurso não encontrado".

### `VM-04` — Back navigation and recommendation parity

From "Repetição com for", the back action landed on the Competency page. That page
showed "Controle a condição de parada · Média · Recomendada"; the Material page had
shown "Atividade nova · Média" for the same Activity. Selecting "Praticar" navigated
to `…/activities/01SHF000000000000000000024`, which renders the SHIFU-74 contract
stub.

### `VM-05` — Mobile, typography and keyboard

At 375×812 the reading column measured 335px with `max-width: 586.5px` (68ch) and no
horizontal page scroll. Content paragraphs computed to DM Sans `16px / 28px`, matching
`design.md` section 3.4. The code block resolved to the mono stack and exposes
`tabindex="0"`, so it is reachable by keyboard.

# 5. Findings

| ID | Severity | Status | Description |
| --- | --- | --- | --- |
| `ACH-01` | Low | Open, out of scope | `ruff format --check` and `biome check` fail on 75 files this delivery never touched. Their working-tree copies hold CRLF from a checkout made before `.gitattributes` declared `text eol=lf`; the stored blobs are LF. `git add --renormalize .` on a clean tree fixes it. Left out so this branch stays reviewable. |
| `ACH-02` | Low | Closed | Pencil node-by-node comparison was owed because the Pencil application was not running during the delivery. Performed on 2026-09-23: the fourteen frames were opened, exported at scale `1` to `design/` and compared against the implementation. No structural divergence and no clipping; see `design/handoff.md`. The copy deltas it found are tracked as `ACH-05`. |
| `ACH-03` | Medium | Fixed | The first unavailable copy read "A Competência Funções ainda não foi liberada. Avance em Funções para abrir o conteúdo dela." when the blocked Competency was itself the focus. Unit tests missed it because they used different names; `VM-02` exposed it. The widget now branches on `focusCompetencyId === competencyId`, and two regression tests were added. |
| `ACH-04` | Low | Open, out of scope | `pnpm --dir apps/web generate-routes` deletes the `declare module '@tanstack/react-start'` block that `510c987` added deliberately. The generated tree was left untouched because this delivery adds no route file. |
| `ACH-05` | Low | Fixed | Four copy and iconography deltas between the Pencil frames and the runtime, none of which broke a `CA-*`. Three were corrected in the runtime on 2026-09-23: the Activity-failure alert now reads `Não foi possível abrir a atividade recomendada. Tente novamente.` and its action relabels to `Tentar abrir novamente`, the error body now reads `O conteúdo não foi alterado. Tente carregar a página novamente.`, and the loading caption and its accessible name now read `Carregando Material de apoio...`. The fourth, the frame's `triangle-alert` against the runtime's `circle-alert`, is accepted: `triangle-alert` is not in the shared `Icon` registry and `CompetencyDetailFeedback` uses `circle-alert` for the same state, so changing it is a design-system decision. `CI-06`, `CI-09` and `CI-10` were re-run after the change. Recorded in full in `design/handoff.md`. |

# 6. Conclusion

Every `CA-*` has accepted evidence. `ACH-03` and `ACH-05` were fixed and covered.
`ACH-02` was closed by the Pencil comparison of 2026-09-23. `ACH-01` and `ACH-04` are
recorded and left out of this delivery. The Activity route reached by the
recommendation is still SHIFU-74's contract stub, which is the expected state of
`main`.
