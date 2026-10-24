# Mentor learner memories — design handoff

Canonical design: [`design/shifu.pen`](../../../../../design/shifu.pen), inspected and
exported through Pencil MCP at scale 1 on 2026-10-20 (active editor
`design/shifu.pen`). The PNGs below are durable references, not runtime evidence.
The `.pen` file was not modified. The [Spec](../spec.md) and the UI Rules govern;
this handoff supersedes the "memories" exclusion in
[`mentor-context/design/handoff.md`](../../mentor-context/design/handoff.md) for the
surfaces listed here only.

## Required frames

| Reference / Pencil node | Surface / required state | Reference dimensions | Saved image | Criteria / checks |
| --- | --- | --- | --- | --- |
| f3v5R — 15.14 Mentor · Memórias · mapa | Memories page, Map view, a memory selected, details panel at the right | 1440×1058 | [f3v5R.png](references/f3v5R.png) | CA-14, CA-15; VM-01, VM-03 |
| Z9YWg9 — 15.22 Mentor · Memórias · lista | Memories page, List view, same memory selected, same details panel | 1440×1180 | [Z9YWg9.png](references/Z9YWg9.png) | CA-14; VM-01, VM-04 |
| pdFGc — 15.23 Mentor · editar memória | Edit form in the details panel (content only; category read-only) | 1440×1180 | [pdFGc.png](references/pdFGc.png) | CA-11, CA-14; VM-01, VM-05 |
| eXEBk — 15.24 Mentor · memória excluída | Panel after deletion: "Memória excluída", explanation, "Voltar ao Mentor" | 1440×1058 | [eXEBk.png](references/eXEBk.png) | CA-12, CA-14; VM-01, VM-05 |
| ik6EW — 15.32 Mentor · memória com origem excluída | Details with one origin shown as locked "Conversa excluída" | 1440×1058 | [ik6EW.png](references/ik6EW.png) | CA-13, CA-14; VM-03 |
| jesf3 — 15.15 Mentor · memória criada | Page conversation: "Memória criada · Ver memória" + category and text after the turn's answer | 1440×1058 | [jesf3.png](references/jesf3.png) | CA-06, CA-16; VM-01, VM-06 |
| Kp8Ou — 15.16 Mentor · memória atualizada | Page conversation: "Memória atualizada · Ver memória" + "Antes" / "Agora" | 1440×1058 | [Kp8Ou.png](references/Kp8Ou.png) | CA-06, CA-16; VM-01, VM-06 |
| F9LDz — 15.30 Mentor · Memórias · lista · mobile | 390 px List: search, "Categoria: Todas", "Ver Mapa" | 390×1180 | [F9LDz.png](references/F9LDz.png) | CA-14; VM-02, VM-07 |
| TAQwm — 15.33 Mentor · Memórias · mapa e detalhes · mobile | 390 px Map (radial, hub links only) with details below | 390×1280 | [TAQwm.png](references/TAQwm.png) | CA-14, CA-15; VM-02, VM-07 |
| yRKMv — 15.35 Mentor · memória atualizada · mobile | 390 px conversation with the updated marker; "Conversas" / "Memórias" buttons | 390×900 | [yRKMv.png](references/yRKMv.png) | CA-16; VM-02, VM-08 |

Runtime viewports: page 1440×900; mobile 390×844. Artboard height is not runtime
height. Reusable components inspected by name: `Mentor/MemoryEvent` (TPF9P, marker) and
`Mentor/MemoryGraphNode` (RqCoQ, map node).

Out of scope frames: `wO8HH — 15.17 Mentor · confirmar dificuldade recorrente` (inferred
difficulty and its confirmation card are deferred by the Spec) and the action-card frames
owned by SHIFU-104.

## Approved adaptations and scope

- **First-person text (user decision Q7).** Frames show third-person titles
  ("Prefere exemplos curtos em JavaScript"), a separate "O que o Mentor lembra" paragraph
  and a condensed marker line. Runtime stores one text: the learner's cleaned sentence. It
  is the item/details title and the content of "O que o Mentor lembra"; the marker shows
  "<categoria>: <texto>" and, for updates, "Antes: <texto anterior>" / "Agora: <texto>".
- **Provenance label is fixed.** Every memory is declared in this delivery, so lists and
  details render "Declarada por você · <data>" and "criada em … · atualizada em …".
  "Confirmada por você" from the frames is not used.
- **Origins (Q34).** One row per source message with the conversation title and a link to
  `/intelligence?session=<id>&message=<id>` that opens the conversation focused on that
  message (Spec RF-21); a deleted conversation is
  a locked row "Conversa excluída" without link, as in ik6EW.
- **Map (Q19/Q39).** Hub "Suas memórias" linked to every visible memory; on desktop,
  memories sharing a concept get an extra link; on mobile only hub links (TAQwm). Node
  positions are computed on a circle around the hub; the frame's fan layout is a sample,
  not a positional contract. Concepts render as the "Relacionada a" chips.
- **Delete confirmation.** Frames show only the result (eXEBk). Runtime opens the shared
  `ConfirmationDialog` first, as the design system requires for destructive actions
  (design.md §3.3); the commit button uses the destructive variant.
- **Marker placement (Q22).** After the answer of the turn that produced it; when that
  answer is absent (cancelled or failed), right after the learner message. A memory deleted
  later renders "Memória excluída" without text or link.
- **Statement-only answer (Q21).** jesf3 shows a personalized Mentor reply; runtime uses
  the fixed local block "Anotado. Vou considerar isso nas próximas explicações."
- **No toast.** Failures render inline in the details panel or confirmation dialog; the
  project has no toast library.
- **Mobile filters.** "Categoria: Todas" opens a single-choice menu (existing
  `ui/shadcn/dropdown-menu.tsx`); "Ver Mapa"/"Ver Lista" toggles the view.
- Touch targets stay ≥ 44 px; focus rings follow the shared Input/Button rules.

## Token and primitive mapping

No parallel literal palette, font, radius or shadow. Values come from design.md §3, the existing Tailwind theme and the reusable components
TPF9P and RqCoQ, inspected through Pencil on 2026-10-21; the implementer re-inspects the
frames before building and records any token mismatch as a finding instead of adding
literals.

| Pencil value / component | Existing Shifu mapping | Owning widget |
| --- | --- | --- |
| Page title Instrument Serif 30/36 | existing page title classes (`ModulePageHeader` typography) | memories-page |
| `$surface` cards / list rows | `bg-card` + `border-border`, card radius 10 | memory-list-item, memory-details |
| Selected row / chip (jade fill) | `bg-jade-tint` + `border-jade-solid` + `text-jade-text` | memory-list-item, memory-filters |
| Category label in details (selo text, mono caption) | `text-selo-text` + `font-mono text-xs uppercase` | memory-details |
| `$text-muted` metadata | `text-muted-foreground` | list, details, marker |
| Concept chips | outline pill `border-jade-solid text-jade-text`, control radius | memory-details |
| Search field | existing `Input` with the `SessionHistory` search pattern (sr-only label + `search` icon) | memory-filters |
| Lista/Mapa toggle | `ui/shadcn/tabs.tsx` as segmented control (precedent `goal-view-switcher`) | memory-filters |
| Category chips (desktop) | `Button variant="ghost"` + `border border-control-border`, selected = jade mapping above; `aria-pressed` | memory-filters |
| Edit button (outline) | `Button variant="ghost"` + `border border-control-border text-foreground` | memory-details |
| Excluir trigger | neutral surface, `text-selo-text` + `border-selo-text`, with `trash-2` icon (design.md §3.3) | memory-details |
| Salvar memória (primary) | `Button` default (selo fill) | memory-edit-form |
| Map canvas / nodes / hub (RqCoQ: halo and ring stroked `$selo-text`, ring fill `$surface-alt`, icon `$text-primary`) | `@xyflow/react` custom nodes; ring and halo `border-selo-text` on `bg-surface-alt`, icon `text-foreground`; selected node uses the existing `primary` token family (`bg-primary/20`, ring `border-primary`) since no selo tint token exists; hub `brain` icon, `border-foreground` | memory-map |
| Category icons | shared `Icon`: preference `sliders-horizontal`, knowledge `book-open` (exists), interest `compass`, difficulty `puzzle`, deleted origin `lock` (new names added to `IconName` and the Lucide map) | `ui/intelligence/constants/learner-memory-categories.ts` |
| Marker (TPF9P: icon `$text-muted`; label `$text-secondary` `$font-ui` 13; detail line `$text-muted` 13; gaps `$space-1`/`$space-2`, padding `$space-2` `$space-1`) | `brain` icon `text-muted-foreground`; label `text-secondary-foreground text-[13px]`; ghost "Ver memória" link; detail lines `text-muted-foreground text-[13px]`; `gap-1`/`gap-2`, `px-1 py-2` | memory-change-marker |

## Preserved surroundings and evidence

App navigation, Mentor sidebar, conversation header (only the "Memórias" button becomes
active), context bar, bubbles and composer are unchanged. The "IA 42% · renova 1 nov" text
in frames is quota UI outside this change and is not introduced. Runtime captures belong
under `apps/web/.playwright-cli/{screenshots,snapshots,logs}/` and are recorded in
`evaluation.md`; no feature-local evidence folder.
