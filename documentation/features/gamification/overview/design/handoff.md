# Gamification overview design handoff

The authoritative design source named by `SHIFU-82` is `design/shifu.pen`, node
`buFAf` ("Gamificação · Visão geral"). **No Pencil session was available while
authoring this Spec**, so that node was not exported and no screenshot is saved
beside this handoff. This is an explicitly accepted visual assumption, recorded
here as the Spec's required design reference, following the same disposition
[`../../achievements/spec.md`](../../achievements/spec.md) used for its own
missing capture.

The offline authority is therefore textual and already-shipped runtime, applied
in this order:

1. [`documentation/design.md`](../../../../design.md) §6.5 **T31 — Área de
   Progresso** and **T30 — Resumo no shell** own the overview's content and its
   non-negotiable rules: a level treatment carrying accumulated XP and the amount
   missing for the next level, the MVP curve
   `XP necessário = 50 × L × (L − 1)` with no maximum level, current and record
   streak with an encouragement phrase of the
   "7 dias, pratique hoje para manter sua sequência" shape, latão for every
   gamification numeral and never jade, and a screen text that marks the
   difference between learning and gamification — level is **never** presented as
   a level of knowledge.
2. [`documentation/design.md`](../../../../design.md) §3 and
   `apps/web/src/ui/shared/styles/global.css` own tokens, dark-only behavior,
   typography, focus and the responsive shell.
3. Existing primitives under `apps/web/src/ui/shadcn` and
   `apps/web/src/ui/shared/widgets` own interaction, focus and disabled behavior.
4. The already-shipped sibling widgets own the visual vocabulary this tab reuses,
   so the new tab cannot drift from the three tabs beside it.

| Reference | Source / node | Route / surface / state | Viewport | Screenshot | Visible inventory | Interaction / state coverage | Ambiguities / exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop Visão geral tab | `design/shifu.pen` / `buFAf`, applied through `design.md` T30/T31 | `/gamification`, Visão geral tab active (default), account with XP, practice days and obtained achievements | 1440 × 900 | None — accepted visual assumption, see above | Page title `Gamificação` and description; four-tab bar with Visão geral active; level block with level, accumulated XP, current and next thresholds, remaining XP and progress indicator; streak block with current streak, record streak, today's line and the seven-day strip; achievements block with the obtained-versus-catalog total, up to three recent achievements and the Conquistas shortcut; gamification-is-not-knowledge note | Shortcut activates by pointer and keyboard; loading, initial, error-with-retry states; day states identifiable without color | No capture exists for this node; the strip's exact mark shapes, the progress indicator's exact form (ring versus bar) and the mobile frame are unresolved and governed by the deviations below | `CA-18`–`CA-24`; `VM-01`, `VM-02`, `VM-03` |

## Component and token mapping

Map every value to an existing semantic token; raw hex, feature-local radii,
shadows or typography are not permitted.

| Element | Runtime owner | Tokens / primitives |
| --- | --- | --- |
| Page title + description | `gamification-page/index.tsx` (unchanged) | Already shipped by `SHIFU-80`; this delivery does not touch the header |
| Tab bar | `gamification-tabs/index.tsx` | `apps/web/src/ui/shadcn/tabs.tsx`; the new trigger reuses the existing active treatment — latão tint surface, latão text label, control radius, 44px height — and the bar keeps its divider bottom border |
| Level numeral and XP values | `overview-tab-panel/level-progress-card/index.tsx` | Serif numeric display in latão, matching the existing `profile-summary-card/index.tsx` and `streak-panel/index.tsx` treatment; XP values rendered with `toLocaleString('pt-BR')` |
| Level progress indicator | `level-progress-card/index.tsx` | Latão fill over a muted track, using existing surface and border tokens. T31 describes an "anel de nível"; see deviation 2 |
| Remaining-XP line | `level-progress-card/index.tsx` | Muted text, phrased as the already-shipped `profile-summary-card` line (`N XP para o próximo nível`) so the two surfaces stay consistent |
| Gamification-is-not-knowledge note | `overview-tab-panel/index.tsx` | Muted small text; required by T31 and `CA-20` |
| Streak numerals and record line | `streak-summary-card/index.tsx` | Reuses the shipped `calendar-tab-panel/streak-panel/index.tsx` vocabulary: large serif latão current streak, `trophy` icon plus `Maior sequência: N dias`, and today's line with `clock-3` when pending or `circle-check` when practiced |
| Today's encouragement | `streak-summary-card/index.tsx` | The shipped wording `Pratique hoje para manter sua sequência.` / `Você já praticou hoje.`, keeping one phrasing across the area |
| Seven-day strip | `streak-summary-card/practice-week-strip/index.tsx` | Reuses the five `CalendarDayState` values and the shape-plus-icon treatment of `calendar-tab-panel/practice-calendar-grid/calendar-day-cell/index.tsx`; never color alone |
| Achievements total | `achievements-summary-card/index.tsx` | Muted label with latão numerals, phrased as a coherent `X de Y` ratio |
| Recent achievement row | `achievements-summary-card/recent-achievement-row/index.tsx` | Reuses the shipped `achievement-card/index.tsx` vocabulary for name, criterion and `+N XP`, in a compact row; date through the existing `useFormatDate` hooks |
| Conquistas shortcut | `achievements-summary-card/index.tsx` | `apps/web/src/ui/shadcn/button`; selects the Conquistas tab and performs no navigation and no request |

## Accessibility

- The seven-day strip is a list structure whose items each carry an accessible
  name containing the date and its pt-BR state, so a day is never identified by
  mark or color alone (RP-13, `CA-23`).
- The progress indicator exposes its value accessibly; the percentage and the
  remaining XP are also present as text, so the visual fill is never the only
  carrier of that information.
- Each recent-achievement row's accessible name contains the achievement name,
  its criterion, its reward and its date.
- The Conquistas shortcut is a real button with a descriptive accessible name and
  is operable by keyboard.
- Loading uses an `output` with `aria-busy`; the error state is `role='alert'`
  with a focusable heading and a working retry, matching the sibling panels.

## Accepted deviations

1. **No capture for node `buFAf`.** No Pencil session was available, so no image
   is saved and no pixel comparison is possible. `VM-02` compares the rendered
   tab against this handoff's mapping and `design.md` T30/T31 instead. If a
   Pencil export becomes available before conclusion, add it here and reconcile
   any difference as a contract amendment.
2. **Progress indicator form is not fixed to a ring.** T31 says "anel de nível",
   but no shipped Shifu primitive renders a progress ring, and introducing one
   would add a feature-local visual primitive outside the design system. The
   contract fixes the *information* — level, accumulated XP, both thresholds,
   remaining XP and the percentage — and leaves ring-versus-bar to the
   implementation, provided it uses existing tokens and exposes its value
   accessibly. Recorded as a deviation rather than silently implemented.
3. **Four tabs, with Visão geral first and default.** The references behind
   `SHIFU-80` (`J5y1Au`) and `SHIFU-81` (`u8vl4`) both show the four-tab bar in
   the order `Visão geral`, `Calendário`, `Conquistas`, `Histórico de XP`. This
   delivery adds the missing first tab and makes it the area's default, which
   changes the current landing tab from `Calendário`. No reference states the
   default explicitly; RP-01's "resumo … deve permitir abrir a área completa"
   and the reference order are the basis for the choice.
4. **Recent achievements are capped at three.** Neither the PRD nor the
   references state a count for "conquistas recentes". Three keeps the block
   readable beside the other two blocks and stacks cleanly on mobile; the cap is
   contracted in the Spec so the server, the UI and the checks agree.
5. **Mobile layout.** No reference has a mobile frame.
   [`documentation/design.md`](../../../../design.md) §9 requires the area to work
   on mobile; at narrow viewports the three blocks stack in the same reading
   order and the seven-day strip keeps seven items with reduced cells, as
   validated by `VM-03`.
6. **Retired achievements in the ratio.** A retired-catalog holding can appear in
   the recent list but is excluded from the `X de Y` total, so the ratio stays
   coherent. The Conquistas tab remains the surface where retired holdings are
   presented as historical, per RP-07.
