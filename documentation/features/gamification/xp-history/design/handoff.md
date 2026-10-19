# XP history design handoff

The authoritative design source is `design/shifu.pen`, node `u8vl4`
("14.3 Gamificação · Histórico de XP · Redesign"). The export below was produced
at scale `1` through the Pencil CLI on 2026-10-18, opened and visually
inspected; the PNG is non-empty and matches its declared 1440 × 1100 viewport.

This handoff is the offline implementation authority for `SHIFU-81`. It records
six accepted deviations — the tab bar, the Atividade row and its descriptor, the
achievement criterion wording, the mobile layout, the fact-date line and legacy
rows — none of which the reference frame resolves on its own.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop Histórico de XP tab | `design/shifu.pen` / `u8vl4` | `/gamification`, Histórico de XP tab active, account with five grants | 1440 × 1100 | [u8vl4.png](./u8vl4.png) | Global header; page title `Gamificação` and description; four-tab bar with Histórico de XP active; section title `Histórico de XP` with description; `XP acumulado` label and total; record card with `Origem` / `Concedido em` / `XP recebido` column headers and five record rows, each with an origin mark, origin name, type-and-context line, grant date and `+N XP`; preservation note | Rows are static text — no links, no row actions, no pagination control | The reference shows four tabs, only one example per source, an Atividade row that this delivery cannot produce, no row whose fact date differs from its concession date, and no mobile frame | `CA-15`–`CA-20`; `VM-01`, `VM-02` |

## Offline implementation authority

Apply sources in this order:

1. [`documentation/design.md`](../../../../design.md) and
   `apps/web/src/ui/shared/styles/global.css` own Shifu tokens, dark-only
   behavior, typography, focus and responsive shell rules.
2. Existing primitives under `apps/web/src/ui/shared/widgets` and
   `apps/web/src/ui/shadcn` own interaction, focus and disabled behavior.
3. This handoff owns the Histórico de XP hierarchy, row vocabulary and
   Pencil-to-runtime interpretation.
4. The saved PNG owns visual comparison, content hierarchy and relative
   composition.
5. Raw Pencil measurements are evidence, not permission to add feature-local
   colors, typography, radii or shadows.

## Row vocabulary

Every row renders a **subject title** and a **type-and-context descriptor**, so
the origin is identifiable without relying on color or icon alone (RP-13). The
title is the grant's stored `XpOrigin.label`; the descriptor is derived from
`XpOrigin.source` by the server, as fixed in the Spec's Technical Contract.

| `XpSource` | Origin mark (lucide) | Title in the reference | Descriptor | Delivered here |
| --- | --- | --- | --- | --- |
| `activity` | `target` | `Somar os números pares` | `Atividade` — the reference's `Atividade · <Habilidade>` needs more than a name, see deviation 2 | No |
| `diagnosis` | `clipboard-check` | `Lógica de programação` | `Diagnóstico concluído` | Yes |
| `competency-mastery` | `badge-check` | `Condicionais` | `Primeiro domínio de Competência` | Yes |
| `skill-completion` | `graduation-cap` | — (absent from the reference) | `Habilidade concluída` | Yes |
| `achievement` | `award` | `Consistência II` | `Conquista · <critério>` | Yes |

`graduation-cap` already exists in the Icon map; `award`, `badge-check` and
`clipboard-check` are added to both the Lucide map and the `IconName` union.
`target` already exists and is mapped now so that the mark is settled once
`SHIFU-84` extends the descriptor derivation — see deviation 2.

## Component and token mapping

Token names below are read from the reference node; map them to the existing
semantic tokens rather than to raw hex.

| Reference element | Runtime owner | Tokens / primitives |
| --- | --- | --- |
| Page title + description | `gamification-page/index.tsx` (unchanged) | Already shipped by `SHIFU-80`; this delivery does not touch the header |
| Tab bar | `gamification-tabs/index.tsx` | `apps/web/src/ui/shadcn/tabs.tsx`; the new trigger reuses the existing active treatment — `$latao-tint` surface, `$latao-text` label, `$radius-control`, 44px height — and the bar keeps its `$divider` bottom border |
| Section title + description | `xp-history-summary/index.tsx` | Title 24px `$text-primary`; description 14px `$text-secondary`; `$space-2` gap |
| `XP acumulado` block | `xp-history-summary/index.tsx` | Label 13px `$text-muted`; value 28px `$latao-text`, rendered as `<total> XP` with `toLocaleString('pt-BR')` |
| Record card | `xp-history-table/index.tsx` | `$surface` fill, `$divider` border, `$radius-card`, full width |
| Column header row | `xp-history-table/index.tsx` | 12px `$text-muted`, `$divider` bottom border, 16px/24px padding, `$space-6` gap |
| Record row | `xp-history-row/index.tsx` | `$divider` bottom border, 20px/24px padding, `$space-6` gap |
| Origin mark | `xp-history-row/index.tsx` | 36 × 36 `$latao-tint` square, `$radius-control`, 18px icon `$latao-text` |
| Origin name | `xp-history-row/index.tsx` | 15px `$text-primary` |
| Type and context | `xp-history-row/index.tsx` | 13px `$text-muted` |
| Grant date | `xp-history-row/index.tsx` | 14px `$text-primary`, fixed 164px column |
| Fact date when different | `xp-history-row/index.tsx` | 12px `$text-muted`, directly under the grant date; rendered only when the two formatted dates differ |
| XP amount | `xp-history-row/index.tsx` | 17px `$latao-text`, `+<amount> XP` |
| Preservation note | `xp-history-tab-panel/index.tsx` | 13px `$text-muted`: "O XP recebido permanece no histórico mesmo se você remover um objetivo ou uma habilidade." |

Dates are formatted in the **viewer's own time zone** through a new
`formatShortDate` in `apps/web/src/ui/shared/hooks/use-format-date.ts`,
composing `Intl` parts into the reference's `13 set 2026` shape. The existing
formatters in that file pin `timeZone: 'UTC'` because they format plain
`YYYY-MM-DD` calendar dates; a grant is an instant, so it is formatted locally
and the fact-date comparison uses those same locally formatted strings.

## Accessibility

- The record list is a `<ul>`/`<li>` structure, not a `<table>`: the design has
  no row or column interactions, and a list stacks on narrow viewports without
  losing its reading order. The column header row is `aria-hidden` decoration;
  every value is announced from the row itself.
- Each row's accessible name contains the origin title, the descriptor, the
  grant date and the amount, so the origin never depends on the mark alone.
- The amount uses `+18 XP` text, not color, to communicate a gain.
- Loading uses an `output` with `aria-busy`; the error state is `role='alert'`
  with a focusable heading and a working retry, matching the sibling panels.

## Accepted deviations

1. **Three tabs, not four.** The reference shows `Visão geral`, `Calendário`,
   `Conquistas` and `Histórico de XP`. This delivery adds the third
   (`Histórico de XP`) to the two tabs `SHIFU-80` shipped. `Visão geral` has no
   content in any delivered ticket, and a disabled tab is a dead control that
   assistive technology still announces, against RP-13. Adding it later is one
   entry in the tab array.
2. **No Atividade row, and its descriptor is narrower than the reference.** XP
   for evaluated Activities is RP-02, owned by `SHIFU-84`; no `activity` grant
   can exist yet, so the row cannot appear in any capture taken for this Spec.
   The reference writes `Atividade · Lógica de programação`, naming the
   Habilidade, but the Spec derives every descriptor from `XpOrigin.source`
   alone — which cannot carry a Habilidade name. `SHIFU-84` must therefore
   extend the derivation, not merely populate a name, to reach the reference's
   row. The mark and the base descriptor are fixed above so the rest of the row
   renders correctly the moment that delivery lands.
3. **Achievement criterion wording.** The reference writes
   `Conquista · Primeiro diagnóstico concluído` and
   `Conquista · 7 dias consecutivos de prática`. The runtime reuses the
   criterion vocabulary already shipped for the Conquistas tab
   (`1 diagnóstico concluído`, `7 dias consecutivos`) rather than introducing a
   second phrasing for the same catalogue criteria. The structure, order and
   hierarchy are unchanged.
4. **Mobile layout.** The reference has no mobile frame.
   [`documentation/design.md`](../../../../design.md) §9 requires the histórico
   to work on mobile; at narrow viewports the row stacks the grant date and the
   amount under the origin block, keeping the same reading order and the same
   accessible names.
5. **Fact date line.** Every row in the reference shows a single date, because
   no example grant has a fact date differing from its concession date. RF-06
   requires the fact date to be shown when the two differ, so a second
   12px `$text-muted` line can appear under the concession date in states the
   reference never exercises. `design.md` T34 governs that line's content.
6. **Legacy rows.** Grants stored before this delivery keep their old sentence
   in `label` (for example `Diagnóstico concluído: Lógica de programação`) and
   therefore render a longer title above their descriptor. They remain readable
   and correctly ordered; no backfill is performed.
