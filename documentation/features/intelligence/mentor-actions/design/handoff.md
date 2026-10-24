# Mentor confirmed actions — design handoff

Canonical design: [`design/shifu.pen`](../../../../../design/shifu.pen), inspected and
exported through Pencil MCP at scale 1 on 2026-10-23 (active editor
`design/shifu.pen`). The PNGs below are durable references, not runtime evidence.
The `.pen` file was not modified. The [Spec](../spec.md) and the UI Rules govern;
this handoff supersedes the "action-card frames owned by SHIFU-104" exclusion in
[`mentor-memory/design/handoff.md`](../../mentor-memory/design/handoff.md) for the
surfaces listed here only.

## Required frames

| Reference / Pencil node | Surface / required state | Reference dimensions | Saved image | Criteria / checks |
| --- | --- | --- | --- | --- |
| Zel1j — `Mentor/ActionCard` (component) | Card anatomy: icon box, title, "Objetivo: …" line, reason, consequences slot, result slot, button row | 640×177 | [Zel1j.png](references/Zel1j.png) | CA-15; VM-03 |
| XOwCJ — 15 Mentor · conversa | Page conversation with an add proposal ("Adicionar Funções em Python?", "Recusar" / "Adicionar habilidade") | 1440×1180 | [XOwCJ.png](references/XOwCJ.png) | CA-01, CA-15; VM-01, VM-03 |
| AyIMM — 15.19 Mentor · escolher Objetivo da adição | Page conversation: Objective picker step before the proposal | 1440×1058 | [AyIMM.png](references/AyIMM.png) | CA-02, CA-15; VM-01, VM-03 |
| lHJ6r — 15.3 Mentor · adicionando habilidade | Add processing (layout only; the status line follows Fbn2b, Q46) | 1440×1180 | [lHJ6r.png](references/lHJ6r.png) | CA-11, CA-15; VM-03 |
| BbWyG — 15.18 Mentor · confirmar remoção de Habilidade | Page conversation with a removal proposal, consequences and "Remover habilidade" | 1440×1058 | [BbWyG.png](references/BbWyG.png) | CA-06, CA-15; VM-02, VM-04 |
| EmQFg — 15.29 Mentor · remoção · mobile | 390 px removal proposal, full-width card, stacked full-width buttons | 390×1100 | [EmQFg.png](references/EmQFg.png) | CA-06, CA-15; VM-02, VM-04 |
| Fbn2b — 15.21 Mentor · estados do card de ação | State board: processing, uncertain, success, recoverable failure, declined, add completed, already present | 1440×1680 | [Fbn2b.png](references/Fbn2b.png) | CA-11, CA-15; VM-03, VM-04 |
| wO8HH — 15.17 Mentor · confirmar dificuldade recorrente | Future memory variant (reference only, not built; Spec Q1) | 1440×1058 | [wO8HH.png](references/wO8HH.png) | — |

Runtime viewports: page 1440×900; mobile 390×844 (Mentor FAB sheet and page). Artboard
height is not runtime height. Reusable components inspected: `Mentor/ActionCard`
(Zel1j), `V2/Button/Primary` (ygtpy), `V2/Button/Outline` (RaoIi).

## Approved adaptations and scope

- **Proposal trigger (Q3, Q43).** XOwCJ and AyIMM show proposals after "Quero praticar
  funções em Python". Runtime proposes an addition only after an explicit request to add
  ("adicione Funções em Python ao meu Objetivo"); the frames are visual references only.
- **Objective picker (Q7, Q44).** As in AyIMM, the card starts on a picker step: label
  "Objetivo", one outline button per candidate, hint "Escolha um Objetivo para revisar a
  proposta de adição." Candidates that already contain the Skill render disabled with
  "Já contém esta Habilidade". Choosing a candidate shows the full proposal with that
  Objective and a "Trocar Objetivo" link until confirmation. Removal uses the same step
  with "Escolha um Objetivo para revisar a proposta de remoção."
- **Missing surfaces (Q45).** No FAB or mobile add frame exists. The FAB and the mobile
  page render the same card at the available width; below 480 px the buttons stack at full
  width as in EmQFg and picker options take the full width.
- **Missing add states (Q45).** Add uncertain, recoverable failure and declined reuse the
  Fbn2b copy with the add wording and the jade icon box: "Verificando adição de <Habilidade>",
  "Não foi possível adicionar <Habilidade>" / "A adição não foi concluída. Sua proposta foi
  preservada.", "Adição recusada" / "<Habilidade> não foi adicionada ao Objetivo.".
- **Processing (Q46).** Both flows use the Fbn2b status line ("Adicionando habilidade…" /
  "Removendo habilidade…") as a live status region, without the animated dots of lHJ6r and
  without buttons.
- **Buttons (Q47).** Variants map to the existing `Button` primitive (see the table); the
  primary restyled as outline in Fbn2b success is implemented as the outline mapping.
- **Rejection and composer copy (Q48).** Not drawn. Rejection: title "Não foi possível
  adicionar <Habilidade>" / "Não foi possível remover <Habilidade>", reason "Este Objetivo não
  está mais disponível." / "Esta Habilidade não está mais disponível no Currículo." / "Esta
  experiência já não está no Objetivo.", result "Nenhuma alteração foi executada.", no
  buttons. Composer: "Confirme ou recuse a ação proposta para continuar." and, while
  refreshing, "Atualizando a conversa…" with "Tentar novamente" after the limit.
- **Add reason (Q3, Q48).** The card reason and the stored justification are the same text:
  "Você pediu ao Mentor para adicionar esta Habilidade." followed by the Skill's Curriculum
  description. The frame sample sentence is not used.
- **Removal reason.** "Você pediu para retirar esta Habilidade do Objetivo." and the BbWyG
  consequences text, verbatim.
- **Quota text.** "IA 42% · renova 1 nov" in frames is quota UI outside this change.

## Token and primitive mapping

No parallel literal palette, font, radius or shadow. Values come from design.md §3, the
existing Tailwind theme (`apps/web/src/ui/shared/styles`) and the components above; the
implementer re-inspects the frames before building and records any token mismatch as a
finding instead of adding literals.

| Pencil value / component | Existing Shifu mapping | Owning widget |
| --- | --- | --- |
| Card container `$surface-alt`, 1 px `$divider`, `$radius-card` 10, padding 16/18, gap 12 | `bg-surface-alt border border-border rounded-[10px] px-[18px] py-4 gap-3` | mentor-action-card |
| Title `$font-ui` 16/600 `$text-primary` | `text-base font-semibold text-foreground` | mentor-action-card |
| Destination line 13/1.5 `$text-primary` | `text-[13px] leading-normal text-foreground` | mentor-action-card |
| Reason 14 `$text-secondary`; consequences/result 13 `$text-secondary` | `text-sm text-secondary-foreground`; `text-[13px] text-secondary-foreground` | mentor-action-card |
| Add icon box `$jade-tint` 30×30, `graduation-cap` 17 `$jade-text`, `$radius-control` 6 | `bg-jade-tint text-jade-text rounded-md size-[30px]`, shared `Icon name="graduation-cap"` (tone `jade`) | skill-action-card chooses; mentor-action-card renders |
| Removal icon box `$selo-tint` + `trash-2` `$selo-text` | `bg-danger/15 text-selo-text` (no selo tint token exists), `Icon name="trash-2"` (tone `danger`) | skill-action-card chooses; mentor-action-card renders |
| Removal state boxes `$raised` + `trash-2` `$text-muted` | `bg-muted text-muted-foreground` (tone `muted`) | skill-action-card chooses; mentor-action-card renders |
| "Adicionar habilidade", "Tentar novamente", "Verificar resultado" (`V2/Button/Primary`, `$selo-fill`) | `Button` default variant | skill-action-card |
| "Remover habilidade" (confirm fill `$danger`) | `Button variant="danger"` | skill-action-card |
| "Recusar" and picker options (`V2/Button/Outline`, `$control-border`) | `Button variant="ghost"` + `border border-control-border text-foreground` (outline precedent from mentor-memory) | skill-action-card, objective-picker |
| "Ver Objetivo" / "Ver Habilidade" | TanStack `Link` with `ROUTES.learningGoal` / `ROUTES.learningSkill` and typed params, styled with the outline mapping above | skill-action-card |
| Button row gap 10, right-aligned; stacked below 480 px | `flex justify-end gap-2.5`; `max-[480px]:flex-col max-[480px]:[&>*]:w-full` | mentor-action-card |

## Preserved surroundings and evidence

App navigation, Mentor sidebar, conversation header, context bar, bubbles and the rest of
the composer are unchanged; only the composer's blocked reason line is added. Runtime
captures belong under `apps/web/.playwright-cli/{screenshots,snapshots,logs}/` and are
recorded in `evaluation.md`; no feature-local evidence folder.
