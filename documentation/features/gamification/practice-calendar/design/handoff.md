# Practice calendar design handoff

The authoritative design source is `design/shifu.pen`, node `J5y1Au`
("14.1 Gamificação · Calendário · Redesign"). The export below was produced at
scale `1` through the Pencil CLI on 2026-10-14, opened and visually inspected;
the PNG is non-empty and matches its declared 1440 × 1100 viewport.

This handoff is the offline implementation authority for `SHIFU-80`. It records
the accepted deviations for the tab bar, the mobile layout and the `neutral`
day state, none of which the reference frame resolves on its own.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop Calendário tab | `design/shifu.pen` / `J5y1Au` | `/gamification`, Calendário tab active, current month with an active streak and a selected practice day | 1440 × 1100 | [J5y1Au.png](./J5y1Au.png) | Global header; page title `Gamificação` and description; four-tab bar with Calendário active; month card with month label, previous/next controls, Monday-first weekday header, 5 week rows, selected-day confirmation line; streak panel with current value, record line, today card and guidance; five-state legend | Previous month enabled, next month disabled on the current month, day selection confirms a date only | The reference shows four tabs and no mobile frame; the `neutral` day state does not occur in this example month | `CA-20`–`CA-24`; `VM-01`, `VM-02` |

## Offline implementation authority

Apply sources in this order:

1. [`documentation/design.md`](../../../../design.md) and
   `apps/web/src/ui/shared/styles/global.css` own Shifu tokens, dark-only
   behavior, typography, focus and responsive shell rules.
2. Existing primitives under `apps/web/src/ui/shared/widgets` and
   `apps/web/src/ui/shadcn` own interaction, focus, disabled and
   reduced-motion behavior.
3. This handoff owns the Calendário hierarchy, state inventory and
   Pencil-to-runtime interpretation.
4. The saved PNG owns visual comparison, content hierarchy and relative
   composition.
5. Raw Pencil measurements are evidence, not permission to add feature-local
   colors, typography, radii or shadows.

## Day-state vocabulary

Each state is distinguished by shape **and** icon, never by color alone, which
is what satisfies RP-13 and `RF-07`. Values below are read from the reference
node; map them to the existing semantic tokens rather than to raw hex.

| State | `CalendarDayState` | Cell fill | Cell stroke | Day number | Mark |
| --- | --- | --- | --- | --- | --- |
| Neutro | `neutral` | none | none | `$text-secondary` | 4 × 4 ellipse, `$text-muted` (legend only — see deviation 3) |
| Dia de prática | `practiced` | none | none | `$text-secondary` | 20 × 20 `$radius-pill` ring, `$latao-solid` 1px, lucide `check` 12 `$latao-text` |
| Sequência atual | `current-streak` | `$latao-tint` | none | `$latao-text` | lucide `check` 14 `$latao-solid` |
| Sem prática | `missed` | none | none | `$text-secondary` | lucide `minus` 14 `$text-muted` |
| Hoje pendente | `today-pending` | none | `$latao-solid` 1px | `$latao-text` | lucide `clock-3` 14 `$latao-solid` |
| Fora do mês | — | none | none | — | empty cell, height preserved |

Selection is rendered as an **added** 1px `$latao-solid` stroke on the cell,
composed over whatever state the day already has; it never replaces the state
mark. In the reference, day 29 is `current-streak` plus that stroke.

## Component and token mapping

| Reference element | Runtime owner | Tokens / primitives |
| --- | --- | --- |
| Page title + description | `gamification-page/index.tsx` | Serif display heading, `$text-primary`; description `$text-secondary`. Replaces the current `ModulePageHeader`; the `mx-auto w-full max-w-7xl` shell is preserved on every branch |
| Tab bar | `gamification-tabs/index.tsx` | `apps/web/src/ui/shadcn/tabs.tsx`; active tab `$latao-tint` surface with `$latao-text` label, inactive `$text-secondary`; bottom divider `$divider` |
| Month card | `calendar-tab-panel/index.tsx` | `bg-card` surface, `$radius-card`, `$space-6` padding |
| Month label + navigation | `month-navigator/index.tsx` | Serif display label; two 44 × 44 controls. Previous: `$raised` fill, `$control-border` stroke, `chevron-left` `$text-secondary`. Next on the current month: no fill, no stroke, `chevron-right` `$text-disabled`, and genuinely `disabled` — not merely styled |
| Weekday header | `practice-calendar-grid/index.tsx` | Monday-first `Seg Ter Qua Qui Sex Sáb Dom`, 13px `$text-muted`, centered |
| Day cell | `calendar-day-cell/index.tsx` | 64px tall, `$radius-control`, day number in `$font-mono` 14 above the state mark |
| Selected-day line | `selected-day-confirmation/index.tsx` | Top divider `$divider`; `circle-check` 18 `$latao-solid` + date text `$text-secondary` 14. Shows a date only — no XP, no Activity count |
| Streak panel | `streak-panel/index.tsx` | Serif "Sua constância"; current value `$font-display` 64 `$latao-text`; `trophy` 18 + record line; today card on `$raised` with `$radius-card` |
| Legend | `calendar-legend/index.tsx` | Top divider; five entries using the shape/icon vocabulary above |

Required icon additions to the shared allowlist
(`apps/web/src/ui/shared/widgets/components/icon/index.tsx`, both the Lucide map
and the `IconName` union): `calendar`, `chevron-left`, `check`, `clock-3`.
Already registered: `circle-check`, `minus`, `trophy`, `chevron-right`.

## Accepted deviations

1. **Two tabs, not four.** The reference shows `Visão geral`, `Calendário`,
   `Conquistas` and `Histórico de XP`. Only Calendário and Conquistas have
   content in any delivered ticket; `Visão geral` and `Histórico de XP` belong
   to `SHIFU-81`/`SHIFU-84`. A disabled tab is a dead control that assistive
   technology still announces, which conflicts with RP-13, so this delivery
   ships two tabs and each later ticket appends its own.
2. **No mobile reference frame.** Other features have `· Mobile` variants;
   gamification node 14.1 has none. The narrow viewport follows
   [`documentation/design.md`](../../../../design.md) §9 — "Calendário mantém 7
   colunas, com célula reduzida" — and is verified at 390 × 844 in `VM-02`
   rather than against a saved reference.
3. **`neutral` is legend-only in the reference.** The example month (September
   2026) has no day before the learner's first practice and no future day
   inside the month, so no grid cell renders `neutral`. The legend entry is the
   authority for that state.
4. **Copy is illustrative.** Dates, the streak value of 12 and the record of 21
   are mock data. The runtime renders real values; only the sentence structure
   and hierarchy are authoritative.

## Preserved UI outside this change

The achievements composition — `profile-summary-card`,
`achievement-family-section`, `historical-achievements-section` and
`achievement-card` — moves inside the Conquistas tab panel unchanged. No
achievement visual, copy or behavior is modified by this delivery; `CI-12`
asserts that every previously passing achievements expectation still holds.
