# Competency detail design handoff

The authoritative design source is `design/shifu.pen`. Pencil exports use scale `1`.
All ten references below were exported, opened, and visually inspected on 2026-09-21;
every PNG is non-empty, matches its declared viewport, and passed Pencil structural
inspection with no clipping or overflow findings.

This handoff is the offline implementation authority for SHIFU-72. It records the
accepted design assumption for a released Competency that is not the current focus;
that state has no dedicated Pencil frame and must be captured during runtime validation.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop available focus | `design/shifu.pen` / `xsNI4` | Competency detail; released, current focus, recommendation available | 1440 × 900 | [xsNI4.png](./xsNI4.png) | Desktop application shell, Skill return action, Competency title, focus/status/progress badges, orientation copy, ordered material/activity timeline, latest scores, highlighted recommendation and `Praticar` action | Open any released item; recommendation is emphasized but does not auto-start | This composition and `A61TJ` differ in card treatment; use existing Shifu tokens and the hierarchy common to both rather than copying raw values | `CA-02`–`CA-04`, `CA-07`, `VM-01` |
| Mobile available focus | `design/shifu.pen` / `R7GgrF` | Competency detail; released, current focus, recommendation available | 390 × 844 | [R7GgrF.png](./R7GgrF.png) | Mobile header/menu, Skill return action, title, focus/status/progress, stacked content cards, recommendation action and bottom navigation | Touch and keyboard-equivalent item navigation; content scrolls above persistent bottom navigation | The desktop orientation sentence is omitted at this width; semantics remain available through heading, badges and item labels | `CA-02`–`CA-04`, `CA-07`, `CA-09`, `VM-01` |
| Desktop loading | `design/shifu.pen` / `DF05W` | Initial unresolved query | 1440 × 900 | [DF05W.png](./DF05W.png) | Centered surface with four skeleton regions and `Carregando Competência e seu progresso...` | Non-interactive progress state announced to assistive technology | Skeleton motion is optional and must respect reduced motion; text carries meaning | `CA-08`, `CA-09`, `VM-02` |
| Mobile loading | `design/shifu.pen` / `IqpIe` | Initial unresolved query | 390 × 844 | [IqpIe.png](./IqpIe.png) | Mobile shell and centered fluid loading surface with the same status copy | Same announcement contract without clipping or horizontal overflow | Bottom navigation remains visible; no interaction is enabled in the loading card | `CA-08`, `CA-09`, `VM-02` |
| Desktop recoverable error | `design/shifu.pen` / `m4Swx` | Transport/server failure | 1440 × 900 | [m4Swx.png](./m4Swx.png) | Application shell, alert icon, `Não foi possível carregar esta Competência`, saved-progress reassurance and `Tentar novamente` | Retry refetches the same canonical query once; focus moves to the error heading/action region | The message must not expose identifiers, ownership or infrastructure details | `CA-01`, `CA-08`, `VM-03` |
| Mobile recoverable error | `design/shifu.pen` / `pYLj5` | Transport/server failure | 390 × 844 | [pYLj5.png](./pYLj5.png) | Mobile shell, wrapped error heading/copy and full-width-safe retry action | Keyboard/touch retry, alert announcement and retained route | No toast substitutes for the in-page recovery surface | `CA-01`, `CA-08`, `CA-09`, `VM-03` |
| Desktop unavailable | `design/shifu.pen` / `VrlNG` | Owned Skill experience; requested Competency exists but is not released | 1440 × 900 | [VrlNG.png](./VrlNG.png) | Application shell, lock icon, `Competência ainda indisponível`, prerequisite/focus explanation and `Voltar para a Habilidade` | Safe navigation only; no materials, Activities, progress or recommendation are exposed | The exact prerequisite name comes from the restricted server projection, not a browser-side lookup | `CA-01`, `CA-06`, `CA-07`, `VM-04` |
| Mobile unavailable | `design/shifu.pen` / `B0DSt` | Owned Skill experience; requested Competency exists but is not released | 390 × 844 | [B0DSt.png](./B0DSt.png) | Mobile shell, compact lock surface, wrapped prerequisite copy and Skill return action | Touch/keyboard return without leaked detail content | Copy adapts grammatically to the server-provided focus Competency name | `CA-01`, `CA-06`, `CA-07`, `CA-09`, `VM-04` |
| Desktop focus returned | `design/shifu.pen` / `A61TJ` | Released Competency became current focus again after progress regression | 1440 × 900 | [A61TJ.png](./A61TJ.png) | Breadcrumb context, title, focus/status badges, progress bar, `Esta Competência voltou a ser seu foco...`, ordered content table and recommendation | Reinforcement explanation precedes the same manual-choice and recommendation behavior | The server may assert this reason only when a later Competency remains released while this earlier Competency is again the first non-mastered item | `CA-02`, `CA-04`, `VM-05` |
| Mobile focus returned | `design/shifu.pen` / `u301ZL` | Released Competency became current focus again after progress regression | 390 × 844 | [u301ZL.png](./u301ZL.png) | Mobile shell, Skill return action, focus/status/progress, wrapped reinforcement notice, ordered cards and recommendation | Notice and recommendation remain distinguishable without color alone | Use the same derivation and copy as desktop; no separate mobile rule | `CA-02`, `CA-04`, `CA-09`, `VM-05` |

## Offline implementation authority

Apply sources in this order:

1. `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css` own
   Shifu tokens, dark-only behavior, typography, focus and responsive shell rules.
2. Existing primitives under `apps/web/src/ui/shared/widgets` and
   `apps/web/src/ui/shadcn` own interaction, focus, disabled and reduced-motion behavior.
3. This handoff owns the Competency-detail hierarchy, state inventory and
   Pencil-to-runtime interpretation.
4. The saved PNGs own visual comparison, content hierarchy and relative composition.
5. Raw Pencil measurements are evidence, not permission to add feature-local colors,
   typography, radii, shadows or parallel tokens.

## Component and token mapping

| Pencil role | Shifu implementation | Required contract |
| --- | --- | --- |
| Application shell | Existing `RootLayout` / `AppLayout` and mobile navigation | Do not recreate headers, navigation or grid background inside Learning widgets. |
| Editorial heading, Skill return, focus/status and progress | `CompetencyDetailHeader` widget using semantic `h1`, shared link/icon/badge primitives and `ProgressMeter` | Preserve heading hierarchy and pt-BR capitalization; text/icon identify state; label progress with accessible numeric semantics. |
| Ordered content | `CompetencyContentList` widget containing only `CompetencyContentRow` widgets | Curriculum position controls DOM and visual order; every item appears once inside a semantic list. |
| Material item | `CompetencyContentRow` Material variant using typed TanStack `Link` and shared icon treatment | Label `Material de apoio`; omit score/recommendation; opening it never changes progress. |
| Activity item | `CompetencyContentRow` Activity variant using typed TanStack `Link`, shared icon and tags | Expose Activity type, localized difficulty and latest official score when present. |
| Recommendation | Recommended `CompetencyContentRow` Activity variant with explicit `Recomendada` copy and primary `Praticar` action | Present only for the current focus; emphasis never removes manual access to other released items. |
| Loading/error/unavailable | `CompetencyDetailFeedback` widget using shared surface/button/icon primitives | Announced status/alert semantics, visible recovery/navigation, safe detail omission and no color-only meaning. |

Use only icons registered by the shared `Icon` widget. Feature widgets must not import
`lucide-react`, author inline SVGs or use font icons.

## Responsive contract

| Concern | 1440 × 900 | 390 × 844 and runtime interpolation |
| --- | --- | --- |
| Shell | Existing desktop application navigation and full content width | Existing compact header and bottom navigation; detail content scrolls without being obscured. |
| Header | Return/breadcrumb context, title, badges and progress occupy the content column | Return action, title and badges wrap vertically; no horizontal scroll. |
| Content sequence | Horizontal rows/timeline with metadata and trailing action | Stacked cards; labels wrap; minimum interactive target remains 44 px. |
| Recommendation | Highlighted final row with a trailing action | Highlighted card with metadata above/beside a reachable `Praticar` action. |
| Feedback surfaces | Centered fixed-maximum surface | Fluid within 20 px viewport gutters; copy wraps and all actions remain visible. |
| Focus | Visible on links, cards and actions without layout shift | Same focus language; bottom navigation does not trap focus. |

Tablet widths interpolate between these layouts using existing breakpoints. No separate
tablet design frame is required.

## Accepted supplemental-state assumption

The Jira Contract requires a released Competency that is not the current focus, but
the supplied `A61TJ` / `u301ZL` frames depict a Competency that has become the focus
again. The user explicitly accepted this implementation assumption:

- reuse the available-detail hierarchy and released content list;
- omit the local recommendation badge and `Praticar` recommendation treatment;
- replace the focus/reinforcement notice with a neutral explanatory notice stating
  that recommendations follow the current focus;
- expose a typed action labelled `Ir para a Competência em foco` using the focus
  Competency identifiers returned by the server; and
- keep every released content item manually accessible.

This assumption is required behavior under `CA-05`. Capture fresh desktop and mobile
runtime screenshots in `VM-06`; no Pencil mutation or additional pre-implementation
frame is required.

## Allowed deviations and exclusions

- Runtime text may wrap according to localized content while preserving hierarchy,
  readable measure and interactive targets.
- Native caret, browser focus internals, query timing and optional skeleton animation
  need not be pixel-identical; their visible states and accessibility semantics must
  match this handoff.
- Material contents, Activity questions/evaluation, Skill-detail contents, diagnosis,
  history, Gamification and Mentor behavior are not defined by these references.
- URL targets owned by SHIFU-66, SHIFU-73, SHIFU-74 and SHIFU-75 are validated as
  typed destination contracts; this feature does not fabricate placeholder pages.

## Layout inspection

Pencil structural inspection reported zero clipped or overflowing descendants for
`xsNI4`, `R7GgrF`, `DF05W`, `IqpIe`, `m4Swx`, `pYLj5`, `VrlNG`, `B0DSt`,
`A61TJ` and `u301ZL`. Visual inspection confirmed that all desktop states fit
1440 × 900, all mobile states fit 390 × 844, content cards remain inside their
containers, and every feedback action remains visible. Runtime implementation must
preserve those properties and avoid fixed-height content clipping.
