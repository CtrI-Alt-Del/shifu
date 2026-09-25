# Add Skill design handoff

The authoritative source is `design/shifu.pen`. Inspected via `pen interactive`
(headless, `--in design/shifu.pen`) on 2026-09-22. Export scale `1`. All seven
screenshots are non-empty, match their declared 1440-wide desktop viewport (the
five dialog frames render at their intrinsic `520`-wide modal size within that
canvas), and were visually inspected, not just OCR'd.

| Reference | Pencil file/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Catalog · collapsed | `design/shifu.pen` / `yR0iN` ("06.1 Adicionar Habilidade") | `/learning/goals/$goalId/skills/add`, first-page/populated, bases-preview collapsed | 1440 × 900 | [yR0iN.png](./yR0iN.png) | "Voltar ao Objetivo" back link; "Adicionar Habilidade" title; guidance banner "Ao adicionar, você pode incluir bases sugeridas. Elas continuam opcionais."; search field "Buscar no Currículo"; 5 example rows | Rows: (1) already-in-goal row with "Já está neste objetivo" + "Abrir" button, no bases shown; (2)/(3)/(5) rows with exactly 1 suggested base shown directly inline ("Base sugerida: X" + status pill "Já no objetivo"/"Ainda não adicionada") + "Adicionar" button; (4) row with 3 suggested bases shown as a summary "3 bases sugeridas · 1 no objetivo · 2 ainda não adicionadas" + "Ver bases" toggle + "Adicionar" button | No loading/empty/search-error/"carregar mais" state designed — falls back to `documentation/design.md` §7 generic states | CA-01, CA-03, CA-25, CA-26, VM-01, VM-02 |
| Catalog · row expanded | `design/shifu.pen` / `SVHqP` ("06.1.1 Adicionar Habilidade · bases abertas") | Same route/state as `yR0iN`, row 4's bases preview expanded | 1440 × 1031 | [SVHqP.png](./SVHqP.png) | Same page; row 4's toggle now reads "Ocultar bases" and reveals a breakdown: "Já no objetivo" heading + check-icon item "Lógica de programação"; "Ainda não adicionadas" heading + circle-icon items "Estruturas de dados básicas", "Funções e modularização" | Toggle is per-row local state; expanding one row doesn't collapse others (not contradicted by the frames, but not proven either — treated as independent per-row state) | CA-26, VM-02 |
| Confirm with selectable bases | `design/shifu.pen` / `o663ai` ("06.1.2 Adicionar Habilidade · confirmar bases") | Dialog opened from a catalog row with a foundation currently selected | 520 (modal) | [o663ai.png](./o663ai.png) | Title "Adicionar Arquivos e planilhas com Python?"; guidance "Você também pode incluir as bases sugeridas. Elas ajudam a formar o caminho no grafo, mas continuam opcionais."; read-only "Habilidade escolhida" chip; "Bases sugeridas" header + "2 selecionadas" + "Desmarcar todas" bulk toggle; 3 rows (1 read-only "Já no objetivo", 2 checked "Será adicionada"); atomic note; footer **"Somente habilidade"** (outline) + **"Adicionar habilidade e 2 bases"** (primary, live count in label) | Two distinct footer actions when ≥1 base is selected | CA-08, CA-09, CA-10, CA-13, CA-27, VM-03, VM-04, VM-05 |
| No suggested bases | `design/shifu.pen` / `xzwuv` ("06.1.2 Adicionar Habilidade · sem bases sugeridas") | Dialog for a Skill with zero Curriculum foundations | 520 (modal) | [xzwuv.png](./xzwuv.png) | Title "Adicionar Depuração e testes?"; guidance "Esta Habilidade não possui bases sugeridas no Currículo."; no "Bases sugeridas" section at all; atomic note "Nenhuma base adicional será incluída."; footer **"Cancelar"** + **"Adicionar habilidade"** (single primary) | Single-button footer (no bases to choose from) | CA-14, VM-06 |
| All bases already present | `design/shifu.pen` / `w3glK` ("06.1.2 Adicionar Habilidade · bases já presentes") | Dialog where every direct foundation already has an experience in the Goal | 520 (modal) | [w3glK.png](./w3glK.png) | Title "Adicionar Estruturas de dados básicas?"; guidance "Todas as bases sugeridas para esta Habilidade já estão neste Objetivo."; "Bases sugeridas" + "1 base já no objetivo" (no bulk toggle — nothing to select); 1 read-only row; note "Somente a Habilidade escolhida será adicionada como não iniciada."; footer **"Cancelar"** + **"Adicionar habilidade"** (single primary) | Single-button footer; no "Selecionar/Desmarcar todas" control when nothing is selectable | CA-15, VM-06 |
| No optional base selected | `design/shifu.pen` / `UXNLJ` ("06.1.2 Adicionar Habilidade · nenhuma base selecionada") | Dialog with selectable bases, current selection count 0 | 520 (modal) | [UXNLJ.png](./UXNLJ.png) | Same layout as `o663ai` but "0 selecionadas", bulk toggle reads **"Selecionar todas"**, both non-present rows unchecked ("Não será adicionada"); footer **"Cancelar"** + **"Adicionar habilidade"** (single primary, no count suffix) | Confirms the footer collapses to one button whenever the selected count is 0, not only when nothing is selectable | CA-16, CA-27, VM-04 |
| Failure with selection preserved | `design/shifu.pen` / `iQP0U` ("06.1.2 Adicionar Habilidade · erro ao adicionar") | Dialog after a failed submit with 2 bases selected | 520 (modal) | [iQP0U.png](./iQP0U.png) | Same selection state as `o663ai` (2 selecionadas, "Desmarcar todas") plus a warning `DS/Alert` "Não foi possível adicionar as Habilidades" / "Sua seleção foi preservada. Verifique sua conexão e tente novamente."; footer reverts to **"Cancelar"** + **"Tentar novamente"** (not the two-button choice) | On failure the footer always shows exactly one retry action that resubmits the last attempted payload (skill-only or skill+bases), never re-prompts the choice | CA-19, VM-08 |

No mobile-specific frame exists for any of the eight states above. Narrow-viewport
layout follows `documentation/design.md` §3.6/§9 (single-column stacking, dialog
becomes a near-full-width sheet) and the repository's existing responsive pattern,
same accepted gap as `objectives-home`'s handoff.

## Offline implementation authority

1. `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css` own
   Shifu semantic tokens, dark-only behavior, typography and focus language.
2. Existing widgets under `apps/web/src/ui/shared/widgets` and shadcn primitives
   under `apps/web/src/ui/shadcn` own interaction, disabled, keyboard and motion
   behavior.
3. This handoff owns component selection and the Pencil-to-Shifu mapping below.
4. The saved PNGs own visual comparison and exact pt-BR copy.

## Extracted node inventory

| Pencil node | Role | Extracted content |
| --- | --- | --- |
| `h7fGzC` (`V2/Header`) | Shared `AppLayout` header | Already implemented; out of scope. |
| `NP15O` | Page title | "Adicionar Habilidade". |
| `X3KjTx` (guidance banner) | Page-level guidance | Icon + "Ao adicionar, você pode incluir bases sugeridas. Elas continuam opcionais." |
| `JXldj` (`fill_container` × 48, `$raised`, `search` icon) | Search field | Placeholder "Buscar no Currículo"; no separate label node. |
| `FmpY8`/`c5yug` (`list`) | Catalog results list | 5 example rows in the frame (real data is server-driven; not a literal page size). |
| Row "already in goal" (e.g. `eiOeV`) | Already-added row | Name + "Já está neste objetivo" caption, no bases block, trailing ref `CZw0W` (`V2/Button/Ghost`) labeled **"Abrir"**. |
| Row "single base" (e.g. `sZWCZ`) | Row with exactly 1 direct foundation | Name + description; inline "Base sugerida: {name}" + status pill ("Já no objetivo" / "Ainda não adicionada"); trailing ref `RaoIi` (`V2/Button/Outline`) labeled **"Adicionar"**. |
| Row "many bases" (`oO41F`/`hImRW`) | Row with >1 direct foundations | Name + description; "Suggested bases summary" = "{N} bases sugeridas · {present} no objetivo · {missing} ainda não adicionadas" + toggle ("Ver bases"/"Ocultar bases", icon flips expand/collapse); when expanded, "Suggested bases expanded" frame lists present (check icon, "Já no objetivo" heading) then missing (circle icon, "Ainda não adicionadas" heading) foundations by name only, no per-item action; trailing ref `RaoIi` labeled "Adicionar". |
| `VlDl1`/etc. (`Branch icon`) | Dialog header icon | Decorative branch/tree icon in a jade-tinted circle, identical across all 5 dialog states. |
| `T0iw24`/etc. (Dialog title) | Dialog title | Dynamic: "Adicionar {Habilidade escolhida}?". |
| `TqHTj`/etc. (Dialog guidance) | Dialog guidance | Dynamic per state — see the state-inventory table above for exact copy of each of the 5 variants. |
| `w68Bw`/etc. ("Selected skill") | Read-only chosen-skill chip | Check icon + "Habilidade escolhida" label + skill name; identical shape in all 5 dialog states. |
| `g7VgD`/etc. ("Suggested bases header") | Foundations header (only when ≥1 foundation exists) | "Bases sugeridas" + dynamic count line ("N selecionadas" / "N base(s) já no objetivo"); trailing ref `CZw0W` bulk toggle **only present when ≥1 base is actually selectable** (absent in `w3glK`, absent in `xzwuv` since the whole section is absent there), labeled **"Selecionar todas"** when the selected count is 0, **"Desmarcar todas"** when every selectable base is selected. |
| Foundation row, present (e.g. `zNb2R`) | Read-only present foundation | Check-in-circle "Already included" icon + name + "Já no objetivo" status; no checkbox, never resubmitted. |
| Foundation row, missing (e.g. `dJC2r`) | Selectable foundation | Checkbox icon (checked/unchecked) + name + status text **"Será adicionada"** (checked) / **"Não será adicionada"** (unchecked). |
| `ORxGz`/etc. ("Atomic addition note") | Reassurance copy | Dynamic per state — see state-inventory table; always mentions "não iniciada(s)". |
| `zxuxp` (ref `VnXFK`, `DS/Alert`) | Failure banner (only in `iQP0U`) | Warning-styled alert, icon + "Não foi possível adicionar as Habilidades" + "Sua seleção foi preservada. Verifique sua conexão e tente novamente." |
| Dialog footer (e.g. `wEDQ3`) | Action row | **Two refs when ≥1 base is selected and no prior failure**: `RaoIi` outline "Somente habilidade" + `ygtpy` primary "Adicionar habilidade e N base(s)" (count in label, singular/plural). **One ref otherwise**: `RaoIi` outline "Cancelar" + `ygtpy` primary "Adicionar habilidade" (0 selected/nothing selectable) or "Tentar novamente" (after a failed submit, regardless of what was submitted). |

## Component mapping

| Pencil source | Shifu implementation | Required configuration |
| --- | --- | --- |
| `V2/Button/Ghost` ("Voltar ao Objetivo") | Shared `Anchor`/`Link` styled ghost with a leading `arrow-left` icon | Navigates to `/learning/goals/$goalId` (`useNavigation().navigateToGoalDetail`). |
| Guidance banner | New inline banner in `AddSkillCatalogSection`, reusing the shared inline-alert pattern (info tone) | Static copy, not dismissible per the design. |
| Search field | Shared shadcn `Input` with a leading `search` icon | Placeholder "Buscar no Currículo"; debounced per the Spec's Technical Contract. |
| Catalog row | New `SkillCatalogItem` (now a small stateful component: local `expanded` toggle for the "Ver/Ocultar bases" affordance) | Renders the three row variants (already-added, single-base, many-bases-summary) from one typed prop shape; "Abrir"/"Adicionar" as shared shadcn `Button` (ghost/outline respectively). |
| `V2/Button/Outline` ("Somente habilidade" / "Cancelar") | Shared shadcn `Button` outline variant | Label switches on dialog state (see inventory). |
| `V2/Button/Primary` ("Adicionar habilidade e N bases" / "Adicionar habilidade" / "Tentar novamente") | Shared shadcn `Button` default variant | Label and submitted payload switch on dialog state; disabled while a submit is in flight (duplicate-submit guard). |
| `V2/Button/Ghost` ("Selecionar todas"/"Desmarcar todas") | Shared shadcn `Button` ghost, small size | Toggles every selectable (not-already-present) foundation's checkbox in one action; label reflects current all-selected state. |
| Checkbox foundation rows | Shared shadcn `Checkbox` + label, one `SkillFoundationRow` per foundation | Present foundations render the read-only variant (no `Checkbox`, check-in-circle icon instead). |
| `DS/Alert` (warning) | Shared inline alert/banner component (warning tone) | Rendered only in the post-failure state, above the footer. |
