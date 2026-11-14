# Planner interview design handoff

The authoritative design source is `design/shifu.pen`. The twenty-four frames referenced by
SHIFU-92 were exported with Pencil `Export` at scale `1` on 2026-10-20 into this directory
(`<nodeId>.png`, same pixel size as the frame). The implementation captures in `captures/`
come from the browser suite `apps/web/tests/intelligence/planner-page.test.ts` run with
`PLANNER_CAPTURE_DIR` set (1440 × 900 and 390 × 844, mocked transport, same copy as the
frames). `comparisons/<nodeId>.png` places the export on the left and the capture on the
right for a node-by-node inspection.

Structural inspection in Pencil (`Get` with `ctx.problems`) reported zero clipped or
overflowing descendants in the twenty-four frames. Every PNG was opened after export and is
non-empty.

## Manifest

| Reference | Source / node | Route / surface / state | Viewport | Export | Capture | Visible inventory | Implementation notes | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Question, single choice | `design/shifu.pen` / `q8TK6d` | Interview, step 1 of 3, one option selected | 1440 × 898 | [q8TK6d.png](./q8TK6d.png) | [captures/q8TK6d.png](./captures/q8TK6d.png) | Shell header, intention card, `Pergunta 1 de 3 deste conjunto`, three step buttons, serif question, guidance, four radio rows (one selected, `Não sei` last), `Cancelar` and `Próxima` | `PlanningIntentSummary`, `PlanningStepTrail`, `PlanningQuestionCard` with the shared `RadioGroup`; selected row = `--muted` + `--selo-text` border, filled `--primary` indicator | `CA-02`, `CA-03`, `VM-02` |
| Question, multiple choice | `design/shifu.pen` / `R9DLj` | Interview, step 2 of 3, two options checked | 1440 × 1000 | [R9DLj.png](./R9DLj.png) | [captures/R9DLj.png](./captures/R9DLj.png) | `1 · Respondida`, `2 · Atual`, `3 · Pendente`, checkbox rows with white check on `--primary`, `Anterior` outline + `Próxima` | Shared `Checkbox` rows restyled by `planner-page.css`; `Anterior` uses the new `outline` Button variant | `CA-03`, `CA-04`, `VM-02` |
| Last question, submit | `design/shifu.pen` / `L0i7L1` | Interview, step 3 of 3, batch complete | 1440 × 1000 | [L0i7L1.png](./L0i7L1.png) | [captures/L0i7L1.png](./captures/L0i7L1.png) | `1 · Respondida`, `2 · Respondida`, `3 · Atual`, guidance `Todas as perguntas estão respondidas…`, `Enviar respostas` primary | `Enviar respostas` is disabled until every question has a selection | `CA-05`, `CA-06`, `VM-02` |
| Reviewing an answered step | `design/shifu.pen` / `OUE0P` | Interview, step 1 revisited with the batch complete | 1440 × 1000 | [OUE0P.png](./OUE0P.png) | [captures/OUE0P.png](./captures/OUE0P.png) | `Revisando pergunta 1 de 3 · conjunto respondido`, review guidance, selection preserved, `Próxima` | Label and guidance derive from `isBatchComplete && !isLastStep` | `CA-03`, `VM-02` |
| Analyzing the intention | `design/shifu.pen` / `CM4DZ` | Processing, stage `analyzing` | 1440 × 1077 | [CM4DZ.png](./CM4DZ.png) | [captures/CM4DZ.png](./captures/CM4DZ.png) | `Planeje seu objetivo`, intention card, jade spinner notice, `Cancelar`, busy `Analisando…` | Stage from `operation.stage`; before the first report, `start`/`restart` operations default to this copy | `CA-08`, `VM-02` |
| Preparing the next step | `design/shifu.pen` / `NmsmF` | Processing, stage `interviewing` after answers | 1440 × 1077 | [NmsmF.png](./NmsmF.png) | [captures/NmsmF.png](./captures/NmsmF.png) | Notice `Preparando o próximo passo…` with `Suas respostas foram enviadas…`, busy `Processando…` | The answered-batch sentence is shown only for `answer` operations | `CA-06`, `CA-08`, `VM-02` |
| Consulting the Curriculum | `design/shifu.pen` / `AiygN` | Processing, stage `retrieving` | 1440 × 1077 | [AiygN.png](./AiygN.png) | [captures/AiygN.png](./captures/AiygN.png) | Notice `Consultando o Currículo…`, busy `Consultando…` | No internal detail of the retrieval is exposed | `CA-08`, `VM-02` |
| Composing the proposal | `design/shifu.pen` / `nKwq9` | Processing, stage `composing` | 1440 × 1077 | [nKwq9.png](./nKwq9.png) | [captures/nKwq9.png](./captures/nKwq9.png) | Notice `Montando sua proposta…`, busy `Montando proposta…` | Reported before the first proposal draft | `CA-08`, `VM-02` |
| Out of scope | `design/shifu.pen` / `kLZY2` | Outcome `out-of-scope` | 1440 × 900 | [kLZY2.png](./kLZY2.png) | [captures/kLZY2.png](./captures/kLZY2.png) | Compass tile, `Vamos planejar sua aprendizagem`, scope guidance, `Criar manualmente` outline + `Reformular` primary | `PlanningOutcome` neutral tone; both exits abandon the planning | `CA-15`, `CA-18`, `VM-02` |
| Unsupported Goal | `design/shifu.pen` / `B6LwtJ` | Outcome `unsupported` | 1440 × 900 | [B6LwtJ.png](./B6LwtJ.png) | [captures/B6LwtJ.png](./captures/B6LwtJ.png) | Selo tile, `Ainda não temos Habilidades para isso`, Curriculum guidance, `Reformular` outline + `Criar manualmente` primary | Alert tone; no Skill name is rendered | `CA-16`, `CA-18`, `VM-02` |
| Technical failure | `design/shifu.pen` / `gLg9C` | Status `failed` | 1440 × 1077 | [gLg9C.png](./gLg9C.png) | [captures/gLg9C.png](./captures/gLg9C.png) | Page title, intention card, alert notice `Não conseguimos continuar agora`, `Cancelar`, `Tentar novamente` | `PlanningProcessingNotice` failure tone (`triangle-alert`, `--selo-text`); 44 px actions as in the frame | `CA-12`, `VM-02` |
| Proposal not validated | `design/shifu.pen` / `PwKlt` | Outcome `validation-failed` | 1440 × 1077 | [PwKlt.png](./PwKlt.png) | [captures/PwKlt.png](./captures/PwKlt.png) | Shield tile, `Não conseguimos concluir sua proposta`, `Nenhum objetivo foi criado`, `Criar manualmente` ghost, `Reformular` outline, `Tentar novamente` primary | Three exits; retry posts `/retry` | `CA-17`, `VM-02` |
| Question, mobile | `design/shifu.pen` / `veOpx` | Interview, step 1 of 3 | 390 × 844 | [veOpx.png](./veOpx.png) | [captures/veOpx.png](./captures/veOpx.png) | Same inventory stacked; `Próxima` full width above a centered `Cancelar` | Mobile order through flex `order` utilities; DOM order keeps `Cancelar` first for the desktop tab order | `CA-20`, `CA-21`, `VM-02` |
| Multiple choice, mobile | `design/shifu.pen` / `ojjlR` | Interview, step 2 of 3 | 390 × 847 | [ojjlR.png](./ojjlR.png) | [captures/ojjlR.png](./captures/ojjlR.png) | `Anterior` and `Próxima` full width, `Cancelar` below | Same widgets | `CA-20`, `VM-02` |
| Last question, mobile | `design/shifu.pen` / `v6t4v` | Interview, step 3 of 3 | 390 × 886 | [v6t4v.png](./v6t4v.png) | [captures/v6t4v.png](./captures/v6t4v.png) | `Enviar respostas` full width | Same widgets | `CA-20`, `VM-02` |
| Review, mobile | `design/shifu.pen` / `ZmelL` | Interview, step 1 revisited | 390 × 844 | [ZmelL.png](./ZmelL.png) | [captures/ZmelL.png](./captures/ZmelL.png) | Review label and guidance | Same widgets | `CA-20`, `VM-02` |
| Analyzing, mobile | `design/shifu.pen` / `ZlbGK` | Processing `analyzing` | 390 × 844 | [ZlbGK.png](./ZlbGK.png) | [captures/ZlbGK.png](./captures/ZlbGK.png) | Title 30 px, notice, `Cancelar` and busy action in one row | Row kept at mobile width as drawn | `CA-08`, `CA-20` |
| Preparing, mobile | `design/shifu.pen` / `sgL1E` | Processing `interviewing` | 390 × 844 | [sgL1E.png](./sgL1E.png) | [captures/sgL1E.png](./captures/sgL1E.png) | Same | Same | `CA-08`, `CA-20` |
| Consulting, mobile | `design/shifu.pen` / `KPglx` | Processing `retrieving` | 390 × 844 | [KPglx.png](./KPglx.png) | [captures/KPglx.png](./captures/KPglx.png) | Same | Same | `CA-08`, `CA-20` |
| Composing, mobile | `design/shifu.pen` / `FtBY1` | Processing `composing` | 390 × 844 | [FtBY1.png](./FtBY1.png) | [captures/FtBY1.png](./captures/FtBY1.png) | Same | Same | `CA-08`, `CA-20` |
| Out of scope, mobile | `design/shifu.pen` / `AECyy` | Outcome `out-of-scope` | 390 × 844 | [AECyy.png](./AECyy.png) | [captures/AECyy.png](./captures/AECyy.png) | Centered column, two actions side by side | `PlanningOutcome` row layout | `CA-15`, `CA-20` |
| Unsupported, mobile | `design/shifu.pen` / `H1SrH` | Outcome `unsupported` | 390 × 844 | [H1SrH.png](./H1SrH.png) | [captures/H1SrH.png](./captures/H1SrH.png) | Same pattern | Same | `CA-16`, `CA-20` |
| Failure, mobile | `design/shifu.pen` / `Aj406` | Status `failed` | 390 × 1100 | [Aj406.png](./Aj406.png) | [captures/Aj406.png](./captures/Aj406.png) | `Tentar novamente` full width above `Cancelar` full width | Stacked actions | `CA-12`, `CA-20` |
| Not validated, mobile | `design/shifu.pen` / `k4oQiw` | Outcome `validation-failed` | 390 × 1100 | [k4oQiw.png](./k4oQiw.png) | [captures/k4oQiw.png](./captures/k4oQiw.png) | `Tentar novamente`, `Reformular`, `Criar manualmente` stacked | `actionsLayout='stack'` with reversed visual order on desktop | `CA-17`, `CA-20` |

## Token mapping

Every value comes from `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css`;
no new token was needed.

| Pencil variable / value | Web token | Utility used |
| --- | --- | --- |
| `$page` `#0A0A0C` | `--background` | app shell |
| `$surface` `#161513` | `--card` | `bg-card` (pending/answered step buttons) |
| `$surface-alt` `#1D1E22` | `--surface-alt` | `bg-surface-alt` (unselected option rows, notices) |
| `$raised` `#1E1C18` | `--muted` | `bg-muted` (intention card, current step, selected option) |
| `$divider` `#FFFFFF14` | `--border` | `border-border` |
| `$control-border` `#FFFFFF54` | `--control-border` | `border-control-border` (step buttons, outline button, option indicators) |
| `$text-primary` `#F4F2EC` | `--foreground` | `text-foreground` |
| `$text-secondary` `#C4BFB6` | `--text-secondary` | `text-secondary-foreground` |
| `$text-muted` `#9A958D` | `--muted-foreground` | `text-muted-foreground` |
| `$selo-fill` `#DC2F2F` | `--primary` | `bg-primary`, selected indicator fill |
| `$selo-text` `#F28B8B` | `--selo-text` | selected option border, alert icon, focus outline |
| `$selo-tint` `#3D1414` | `--accent` | alert icon tile |
| `$jade-text` `#7BD3B6` | `--jade-text` | spinner, `Proposta pronta` eyebrow |
| Instrument Serif 36 / 30 | `--font-serif` | `font-serif text-4xl` / `text-3xl` |
| DM Sans 15 / 13 / 12 | `--font-sans` | `text-[15px]`, `text-[13px]`, `text-xs` with `leading-[1.45]` |
| radius 10 / 6 | — | `rounded-[10px]`, `rounded-md` |

## Deviations and decisions

| Item | Frame | Implementation | Reason |
| --- | --- | --- | --- |
| Busy primary action opacity | 0.65 | 0.5 | The shared `Button` applies `disabled:opacity-50`; a page-level override would fight the primitive (spec decision D7) |
| `Cancelar` weight | 500 | 600 | Shared ghost `Button` is semibold; kept for consistency with every other page |
| Desktop action height | 38 px on interview, processing, out-of-scope and unsupported; 44 px on failure and validation frames | Same split: compact 38 px actions at `lg` on the first group, 44 px on the second | Faithful to each frame; mobile is always 44 px |
| Vertical placement | Column centered in the content area on desktop; 24 px top padding on mobile | Column centered inside the app `main` at `lg`; the shared shell gives 32 px top padding on mobile | The shell gutters belong to `AppLayout` |
| Exclusive option text | `--text-secondary` on single-choice frames, `--text-primary` on the multiple frame | `--text-secondary` in both formats | One rule for the same option (spec decision D8) |
| Support copy of `interviewing` | Only drawn after answers | `Suas respostas foram enviadas.` is omitted when the operation is not an `answer` | Honest copy for start/restart/retry operations (D9) |
| Failure icon | Node named `Spinner`, icon `triangle-alert` in `$selo-text` | Static `triangle-alert`, `--selo-text` | A spinning icon on a failure would be misleading |
| Step buttons with four questions at 390 px | Three questions drawn | Labels wrap inside a 44 px minimum height | The trail is driven by the real batch size (1–4) |
| Shell header | Drawn in every frame | Rendered by the existing `AppLayout` | The page never re-implements the shell |
| Mobile shell extras | Frames show only the menu trigger | Captures also show the account trigger, the bottom navigation and the Mentor FAB | Owned by `AppLayout`; the planner column keeps its 20 px gutters above the bottom bar |
| Multiple-choice guidance on the last step | Only drawn mid-batch (`R9DLj`) | The `Não sei` sentence wins over the last-step hint while the batch is incomplete | The exclusivity rule matters wherever the option exists; `Enviar respostas` stays disabled and the trail shows the pending steps |
| Review handoff | No frame (SHIFU-93) | `PlanningProposalHandoff` shows `Proposta pronta`, the proposal title and the Skill count, with `Cancelar` | Typed boundary for the next delivery; never renders an invalid proposal |
| Request error / not found | No frame | `PlanningOutcome` with `triangle-alert` / `circle-alert`, neutral copy, `Voltar à Home` and `Tentar novamente` | Required by the behavior contract (RF-08, CA-23) |
