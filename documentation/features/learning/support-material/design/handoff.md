# Support Material design handoff

The authoritative design source is `design/shifu.pen`. Pencil exports use scale `1`.
All fourteen references below were exported, opened, and visually inspected on
2026-09-23; every PNG is non-empty, matches its declared viewport, and passed Pencil
structural inspection with no clipping or overflow findings.

This handoff is written **after** the SHIFU-73 implementation, not before it. The
Pencil application was unavailable during the delivery, so the implementation was
built against `documentation/design.md` and measured in the browser, and `ACH-02`
recorded that the node-by-node comparison was still owed. This document is that
comparison. It keeps the same authority order as the Competency-detail handoff and
adds, in "Design-to-runtime deltas", every difference the comparison found.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop available | `design/shifu.pen` / `RTwfu` | Material; released Competency, recommendation available | 1440 × 900 | [RTwfu.png](./RTwfu.png) | Desktop application shell, `← Estruturas de repetição` return action, `Repetição com for` title, two body paragraphs, a fenced Python block, and a recommendation card with `Recomendação atual`, the Competency name and a primary action | Return to the Competency of origin; open the recommended Activity; reading changes no state | The card shows the Competency name where the runtime shows the Activity metadata; see the deltas table | `CA-05`, `CA-06`, `CA-08`, `CA-12`, `CA-15`, `VM-01`, `VM-04` |
| Mobile available | `design/shifu.pen` / `HQKUj` | Material; released Competency, recommendation available | 390 × 844 | [HQKUj.png](./HQKUj.png) | Mobile header with menu, return action carrying only the Competency name, title at 30, same content sequence, full-width recommendation action and bottom navigation | Touch and keyboard return; content scrolls above persistent bottom navigation | The desktop `Voltar para` prefix is dropped at this width; the runtime does the same | `CA-06`, `CA-08`, `CA-19`, `CA-20`, `VM-05` |
| Desktop loading | `design/shifu.pen` / `qImzG` | Initial unresolved query | 1440 × 900 | [qImzG.png](./qImzG.png) | Application shell and a centered card holding four skeleton regions above `Carregando Material de apoio…` | Non-interactive progress state announced to assistive technology | Skeleton motion is optional and must respect reduced motion; the caption carries the meaning | `CA-18`, `VM-01` |
| Mobile loading | `design/shifu.pen` / `FCMbg` | Initial unresolved query | 390 × 844 | [FCMbg.png](./FCMbg.png) | Mobile shell, fluid skeleton card with the same caption, bottom navigation visible | Same announcement contract without clipping or horizontal overflow | No interaction is enabled in the loading card | `CA-18`, `CA-20` |
| Desktop error | `design/shifu.pen` / `t7C2XU` | Transport or server failure | 1440 × 900 | [t7C2XU.png](./t7C2XU.png) | Application shell, alert icon, `Não foi possível carregar este Material`, `O conteúdo não foi alterado. Tente carregar a página novamente.` and `Tentar novamente` | Retry refetches the same canonical query; focus moves to the error heading | Only the icon shape differs from the runtime; see the deltas table | `CA-18`, `VM-01` |
| Mobile error | `design/shifu.pen` / `x69MV` | Transport or server failure | 390 × 844 | [x69MV.png](./x69MV.png) | Mobile shell, wrapped heading and copy, full-width-safe retry action | Keyboard and touch retry, alert announcement, route retained | No toast substitutes for the in-page recovery surface | `CA-18`, `CA-20` |
| Desktop unavailable | `design/shifu.pen` / `j50Z0g` | Owned experience; the Competency of the route is not released | 1440 × 900 | [j50Z0g.png](./j50Z0g.png) | Application shell, lock icon, `Material ainda indisponível`, an orientation sentence and `Voltar para a Competência` | Safe navigation only; no Material title, content or recommendation is exposed | The frame's sentence names no Competency, which `CA-11` requires; the runtime names it | `CA-11`, `VM-02` |
| Mobile unavailable | `design/shifu.pen` / `Pu6sO` | Owned experience; the Competency of the route is not released | 390 × 844 | [Pu6sO.png](./Pu6sO.png) | Mobile shell, compact lock surface, wrapped copy and the Competency return action | Touch and keyboard return without leaked detail content | Same naming delta as the desktop frame | `CA-11`, `CA-20` |
| Desktop long content | `design/shifu.pen` / `A1rzZ4` | Released Material whose Markdown exceeds one screen | 1440 × 1100 | [A1rzZ4.png](./A1rzZ4.png) | The available composition extended with additional paragraphs and a wide code block, recommendation card still last | Whole page scrolls; the code block is reachable by keyboard | The frame is 200 px taller than the viewport on purpose, to show the scrolled extent | `CA-19`, `VM-05` |
| Mobile long content | `design/shifu.pen` / `mumyI` | Released Material whose Markdown exceeds one screen | 390 × 1260 | [mumyI.png](./mumyI.png) | Same extended sequence stacked, bottom navigation pinned | Vertical scroll only; no horizontal page scroll at 390 | The reading column stays at the 68-character measure while the code block scrolls inside its own box | `CA-19`, `CA-20`, `VM-05` |
| Desktop without recommendation | `design/shifu.pen` / `tLLeI` | Released Material whose source Competency has no current recommendation | 1440 × 900 | [tLLeI.png](./tLLeI.png) | The available composition with the recommendation card absent entirely | Nothing replaces the card: no empty state, no disabled action | Absence is the design; a placeholder would contradict `CA-14` | `CA-14` |
| Mobile without recommendation | `design/shifu.pen` / `iFkAY` | Released Material whose source Competency has no current recommendation | 390 × 844 | [iFkAY.png](./iFkAY.png) | Same absence on the mobile composition | Content ends above the bottom navigation with no trailing action | Same as desktop | `CA-14`, `CA-20` |
| Desktop Activity failure | `design/shifu.pen` / `kpGXW` | Opening the recommended Activity failed | 1440 × 900 | [kpGXW.png](./kpGXW.png) | The available composition plus an inline alert inside the recommendation card and a retry-labelled primary action | The Material stays fully visible and readable; the retry repeats the same navigation | The runtime matches both the alert and the relabelled action since 2026-09-23 | `CA-16`, `CA-17` |
| Mobile Activity failure | `design/shifu.pen` / `ClGcY` | Opening the recommended Activity failed | 390 × 844 | [ClGcY.png](./ClGcY.png) | Same inline alert stacked above the full-width retry action | Touch and keyboard retry; the alert is announced and the content is retained | The frame's alert sentence is shorter than the desktop one; the runtime uses the desktop sentence at both widths | `CA-16`, `CA-17`, `CA-20` |

## Offline implementation authority

Apply sources in this order:

1. `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css` own
   Shifu tokens, dark-only behavior, typography, focus and responsive shell rules.
2. Existing primitives under `apps/web/src/ui/shared/widgets` and
   `apps/web/src/ui/shadcn` own interaction, focus, disabled and reduced-motion behavior.
3. This handoff owns the Material hierarchy, state inventory and Pencil-to-runtime
   interpretation.
4. The saved PNGs own visual comparison, content hierarchy and relative composition.
5. Raw Pencil measurements are evidence, not permission to add feature-local colors,
   typography, radii, shadows or parallel tokens.

## Component and token mapping

| Pencil role | Shifu implementation | Required contract |
| --- | --- | --- |
| Application shell | Existing `RootLayout` / `AppLayout` and mobile bottom navigation | Do not recreate headers, navigation or grid background inside Learning widgets. |
| Return action and editorial title | `MaterialHeader` using a typed TanStack `Link` and a semantic `h1` | The return action always carries the Competency of the route, never the focus Competency; its accessible name names that Competency. |
| Markdown body | `MaterialContent` rendering paragraphs, fenced blocks and inline code as React elements | Embedded HTML stays literal text; the reading column stays at 68 characters; the code block is focusable. |
| Recommendation | `MaterialRecommendation` with a single primary action | Rendered only when the source Competency has a recommendation; the label and metadata come from that delegated recommendation, never from a local computation. |
| Loading, error, unavailable and private absence | `MaterialFeedback` using shared surface, button and icon primitives | Announced status and alert semantics, visible recovery or navigation, no colour-only meaning, and no Material title inside the restricted states. |

Use only icons registered by the shared `Icon` widget. Feature widgets must not import
`lucide-react`, author inline SVGs or use font icons.

## Responsive contract

| Concern | 1440 × 900 | 390 × 844 and runtime interpolation |
| --- | --- | --- |
| Shell | Desktop application navigation and full content width | Compact header and bottom navigation; content scrolls without being obscured. |
| Header | Return action above the title, both inside the reading column | Return action carries the Competency name alone; the title wraps without horizontal scroll. |
| Body | 68-character reading column, code block full column width | Same measure; the code block scrolls horizontally inside its own box, never the page. |
| Recommendation | Metadata and action side by side in one card | Metadata above a full-width-safe action, minimum interactive target 44 px. |
| Feedback surfaces | Centered fixed-maximum surface | Fluid within the viewport gutters; copy wraps and every action stays visible. |
| Focus | Visible on the return link, the code block and the action without layout shift | Same focus language; bottom navigation does not trap focus. |

Tablet widths interpolate between these layouts using existing breakpoints. No separate
tablet frame is required.

## Design-to-runtime deltas

The comparison of 2026-09-23 found no structural divergence: every frame's hierarchy,
state inventory and responsive behavior are present in the implementation, and Pencil
structural inspection reported zero clipped or overflowing descendants. The deltas
below are copy and iconography, and each one is recorded rather than silently accepted.

| # | Surface | Pencil frame | Runtime | Disposition |
| --- | --- | --- | --- | --- |
| 1 | Recommendation card | `Recomendação atual` above the Competency name, action `Abrir atividade recomendada` | `Continuar em <Competency>` above the delegated Activity metadata, action `Praticar` | Runtime is richer and matches the Competency page, where the same recommendation reads `Recomendada` with its type and difficulty. `CA-12` requires parity with that page, so the runtime wording is kept and the frames are the ones behind. |
| 2 | Activity failure | Alert `Não foi possível abrir a atividade recomendada. Tente novamente.` (mobile: `Não foi possível abrir a atividade. Tente novamente.`) and the primary action relabelled `Tentar abrir novamente` | Same alert sentence at both widths, and the action now reads `Tentar abrir novamente` after a failure, still `Abrindo...` while pending | Resolved on 2026-09-23. The runtime was aligned to the frames; `CA-16` and `CA-17` keep their coverage. |
| 3 | Error body | `O conteúdo não foi alterado. Tente carregar a página novamente.` | Same sentence | Resolved on 2026-09-23. The frame's sentence is the accurate one, because reading a Material writes no progress at all (`CA-09`). |
| 4 | Error icon | `triangle-alert` | `circle-alert` | Accepted. `triangle-alert` is not registered in the shared `Icon` widget, and `CompetencyDetailFeedback` renders this same state with `circle-alert`. Matching the frame would mean extending the shared registry and making the Material page differ from its sibling for an identical state, which is a design-system decision, not a Material one. Neither icon carries meaning alone. |
| 5 | Unavailable body | `Volte para a Competência de origem para continuar seu caminho de aprendizagem.` | Names the blocked Competency, and branches when it is itself the focus | Accepted. `CA-11` and `RF-04` require naming the blocked Competency, which the frame does not do. `ACH-03` fixed the branching. The frames are behind. |
| 6 | Header | Return action, then the title | Return action, a `<Skill> · <Competency>` context line, the title, and a `Material de apoio` badge | Accepted. Both additions reuse existing primitives and reinforce `CA-08`; no frame contradicts them. |
| 7 | Return action label | `← Estruturas de repetição` at both widths | `Voltar para <Competency>` from 640 px, the bare Competency name below it | Accepted. The accessible name is `Voltar para a Competência <name>` at every width, and the mobile rendering matches the frame. |
| 8 | Loading caption | `Carregando Material de apoio…` | `Carregando Material de apoio...` | Resolved on 2026-09-23, in the caption and in its accessible name. The ASCII ellipsis is kept, because every other caption in the application uses it. |
| 9 | Screen title size | 36 desktop, 30 mobile | 48 from 640 px, 36 below | Out of scope. `MaterialHeader` uses exactly the classes of `CompetencyDetailHeader`, accepted in SHIFU-72, so this is a system-wide difference between the Pencil frames and the runtime type scale, not a Material regression. `design.md` section 3.4 sizes the screen title at 30 / 36, so a correction belongs to the design system, not to this feature. |

Deltas 2, 3 and 8 were resolved on 2026-09-23 by aligning the runtime strings to the
frames and updating their assertions; `pnpm --dir apps/web test:unit` and
`pnpm --dir apps/web test:integration` pass. Delta 4 is accepted for the reason in its
row. Deltas 1, 5, 6 and 7 stand as recorded: in each of them the frame is the source
that is behind, not the runtime.

## Allowed deviations and exclusions

- Runtime text may wrap according to the real Markdown while preserving hierarchy,
  the 68-character measure and interactive targets. The frames render one seeded
  Material; the page renders whatever Curriculum stored.
- Native caret, browser focus internals, query timing and optional skeleton animation
  need not be pixel-identical; their visible states and accessibility semantics must
  match this handoff.
- The private-absence state has no Pencil frame. It reuses the generic not-found
  surface of the application and is validated by `CA-02` and `CI-09` instead.
- Activity contents, Competency-detail composition, diagnosis, history, Gamification
  and Mentor behavior are not defined by these references.
- The Activity route reached from the recommendation belongs to SHIFU-74 and is still
  a contract stub.

## Layout inspection

Pencil structural inspection reported zero clipped or overflowing descendants for
`RTwfu`, `HQKUj`, `qImzG`, `t7C2XU`, `j50Z0g`, `A1rzZ4`, `tLLeI`, `kpGXW`, `FCMbg`,
`x69MV`, `Pu6sO`, `mumyI`, `iFkAY` and `ClGcY`. Visual inspection confirmed that the
six desktop states fit 1440 × 900 except `A1rzZ4`, which is deliberately 1440 × 1100
to show long content, that the six mobile states fit 390 × 844 except `mumyI` at
390 × 1260 for the same reason, that no frame is a placeholder, and that every
feedback action remains visible. Runtime implementation must preserve those properties
and avoid fixed-height content clipping.
