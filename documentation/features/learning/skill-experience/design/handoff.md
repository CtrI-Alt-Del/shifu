# Skill experience design handoff

The authoritative design source is `design/shifu.pen`. Pencil exports use scale `1`.
All twelve references below were exported, opened and compared node by node against the
implementation on 2026-09-25; every PNG is non-empty, matches its declared viewport, and
Pencil structural inspection reported zero clipped or overflowing descendants.

This handoff covers the **settled** branch of the Skill route only. The `not-started`
and `diagnosing` states of the same route belong to the diagnostic slice already on
`main` and are untouched by SHIFU-66.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop base | `design/shifu.pen` / `uyfWq` | Skill in learning, recommendation available | 1440 × 900 | [uyfWq.png](./uyfWq.png) | Return to the Objective, title at 40, `Em aprendizado` pill, `Resultado geral` chip, actions trigger, recommendation card with difficulty and type badges, Activity title and two actions, and the ordered Competency list | The frame is the *menu aberto* variant; its menu items belong to SHIFU-36 and only the trigger is rendered | `CA-03`, `CA-04`, `CA-11`–`CA-15` |
| Mobile base | `design/shifu.pen` / `wXPwI` | Skill in learning, recommendation available | 390 × 844 | [wXPwI.png](./wXPwI.png) | Same sequence stacked, actions full width, rows without the progress bar column | The 360 px bar is hidden below `lg`; the percentage and the pills carry the same information | `CA-20`, `CA-21` |
| Desktop loading | `design/shifu.pen` / `XBet9` | Unresolved query | 1440 × 900 | [XBet9.png](./XBet9.png) | Centered `Carregando habilidade` with the supporting sentence | Owned by the existing page shell, which already renders a loading surface for this route | `CA-19` |
| Mobile loading | `design/shifu.pen` / `JNazF` | Unresolved query | 390 × 844 | [JNazF.png](./JNazF.png) | Same surface at mobile width | Same as desktop | `CA-19` |
| Desktop unavailable | `design/shifu.pen` / `f500p` | Absent Skill, or one owned by another account | 1440 × 900 | [f500p.png](./f500p.png) | Lock, `Habilidade indisponível`, the neutral explanation and the return to the Objective | Rendered from the generic `404` by decision `D8`; no payload describes it | `CA-02`, `CA-19` |
| Mobile unavailable | `design/shifu.pen` / `gMddp` | Absent Skill | 390 × 844 | [gMddp.png](./gMddp.png) | Same surface at mobile width | Same as desktop | `CA-02` |
| Desktop error | `design/shifu.pen` / `lcS3z` | Transport or server failure | 1440 × 900 | [lcS3z.png](./lcS3z.png) | `Não foi possível carregar a Habilidade`, the reassurance and `Tentar novamente` | Owned by the existing page shell | `CA-19` |
| Mobile error | `design/shifu.pen` / `JXyUe` | Transport or server failure | 390 × 844 | [JXyUe.png](./JXyUe.png) | Same surface at mobile width | Same as desktop | `CA-19` |
| Desktop evaluation running | `design/shifu.pen` / `uyhA7` | An evaluation of this Skill is pending | 1440 × 900 | [uyhA7.png](./uyhA7.png) | Three jade dots, `Avaliando sua resposta`, the paused-attempts sentence, and the full Competency list below | The recommendation card is absent, which the payload enforces | `CA-16`, `CA-17` |
| Mobile evaluation running | `design/shifu.pen` / `fYHyi` | An evaluation is pending | 390 × 844 | [fYHyi.png](./fYHyi.png) | Same notice wrapped | Same as desktop | `CA-16`, `CA-20` |
| Desktop evaluation failed | `design/shifu.pen` / `XxLQ1` | The evaluation could not finish | 1440 × 900 | [XxLQ1.png](./XxLQ1.png) | Alert chip, `A avaliação não pôde terminar`, the preserved-answer sentence and `Tentar novamente` | The retry calls the endpoint SHIFU-74 delivered | `CA-18` |
| Mobile evaluation failed | `design/shifu.pen` / `vlvkI` | The evaluation could not finish | 390 × 844 | [vlvkI.png](./vlvkI.png) | Same notice wrapped, action full width | Same as desktop | `CA-18`, `CA-20` |

## Token mapping

Every value below comes from `documentation/design.md`. Five entries existed in the
design authority but not yet in `global.css` and were added there as shared tokens
(decision `D9`); none of them is feature-local.

| Pencil variable | Web token | Utility used |
| --- | --- | --- |
| `$page` | `--background` | `bg-background` (app shell) |
| `$surface-alt` | `--surface-alt` | `bg-surface-alt` |
| `$raised` | `--muted` | `bg-muted` |
| `$text-primary` | `--foreground` | `text-foreground` |
| `$text-secondary` | `--text-secondary` **added** | `text-secondary-foreground` |
| `$text-muted` | `--muted-foreground` | `text-muted-foreground` |
| `$jade-tint` | `--jade-tint` | `bg-jade-tint` |
| `$jade-fill` | `--jade-fill` **added** | `bg-jade-fill` |
| `$jade-solid` | `--jade-solid` **added** | `bg-jade-solid` |
| `$jade-text` | `--jade-text` **added** | `text-jade-text` |
| `$on-jade` | `--on-jade` **added** | `text-on-jade` |
| `$selo-tint` | `--accent` | `bg-accent` |
| `$selo-fill` | `--primary` | `bg-primary` |
| `$selo-text` | `--selo-text` | `text-selo-text` |
| `$on-selo` | `--primary-foreground` | `text-primary-foreground` |
| `$control-border` | `--control-border` | `border-control-border`, `bg-control-border` |
| `$radius-control` = 6 | — | `rounded-md` |
| `$radius-card` = 10 | — | `rounded-[10px]` |

## Component and token mapping

| Pencil role | Shifu implementation | Required contract |
| --- | --- | --- |
| Application shell and grid background | Existing `RootLayout` / `AppLayout` | Never recreated inside Learning widgets. |
| Return, title, status and result | `SkillOverview` with a semantic `h1` | The status pill pairs an icon with its label; the result is `tabular-nums`. |
| Recommendation | `SkillRecommendationCard` | Rendered only when the payload carries one; both actions are typed links, and nothing starts automatically. |
| Competency list | `SkillCompetencyList` and `SkillCompetencyRow` | A released row is a link, a blocked row is a button that explains the requirement in an `alert`. |
| Evaluation notices | `SkillEvaluationNotice` | The pending notice is a polite `output`, the failed one an `alert` with the retry action. |

Use only icons registered by the shared `Icon` widget. Feature widgets must not import
`lucide-react` or author inline SVGs.

## Measurements carried from the frames

- Content column: vertical stack, gap 24, horizontal gutter 80 at `lg`.
- Title 40 in the display face; status pill 12/600; result label 11/500 with the value
  at 16/700.
- Recommendation card: padding 18, radius 10, badges 11/500, Activity title 17/500,
  actions 38 tall with 18 of horizontal padding.
- Competency card: padding 6, radius 10; each row 50 tall, gap 16, padding 14 by 16,
  radius 6, and the focus row filled with `$raised`.
- Progress bar: 360 × 8, radius 3, with three 1 px marks at 40, 70 and 85 in
  `$text-primary`. The marks are the reason no state depends on colour alone.

## Design-to-runtime deltas

| # | Surface | Pencil frame | Runtime | Disposition |
| --- | --- | --- | --- | --- |
| 1 | Blocked badge icon | `lock` | `lock-keyhole` | Accepted. `lock` is not in the shared registry; see `ACH-02`. |
| 2 | Failed evaluation chip | `alert-triangle` | `circle-alert` | Accepted. Not registered, and the sibling feedback widgets already use `circle-alert` for this meaning; see `ACH-03`. |
| 3 | Skill actions menu | Expanded, with its items | Trigger only | Accepted. Every item belongs to SHIFU-36; see `ACH-04`. |
| 4 | Progress bar at mobile | Present | Hidden below `lg` | Accepted. At 390 the 360 px bar cannot coexist with the name, the percentage and two pills; the numeric value and the pills carry the same information, and the frame itself drops it. |
| 5 | Row trailing space | Fixed columns leave empty space at the right | Same at `lg`; the name stretches below it | Accepted. The fixed 280 px name and 360 px bar are reproduced from `lg` up, where the frame's width applies. |

No structural divergence was found: every frame's hierarchy, state inventory and
responsive behavior is present in the implementation.
