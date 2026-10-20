# Planner proposal review design handoff

The authoritative design source is `design/shifu.pen`. The eight frames referenced by
SHIFU-93 were exported with Pencil `Export` at scale `1` on 2026-10-20 into this directory
(`<nodeId>.png`, same pixel size as the frame). The implementation captures in `captures/`
come from the browser suite `apps/web/tests/intelligence/planner-page.test.ts` (review
scenarios) run with `PLANNER_CAPTURE_DIR` set, mocked transport, same copy as the frames.
Graph and list captures use a viewport as tall as the document (1440 and 390 wide), the
dialog and processing captures use 1440 × 900 and 390 × 844; CSS animations are
fast-forwarded (`animations: 'disabled'`) so the dialog is captured in its final state.
`comparisons/<nodeId>.png` places the export on the left and the capture on the right.

Structural inspection in Pencil (`Get` with `ctx.problems`) reported zero clipped or
overflowing descendants in the eight frames. Every PNG was opened after export and is
non-empty.

## Manifest

| Reference | Source / node | Route / surface / state | Viewport | Export | Capture | Visible inventory | Implementation notes | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Review, graph | `design/shifu.pen` / `bzItW` | `/intelligence/planner/$planningId`, status `proposal`, `Grafo` tab | 1440 × 1506 | [bzItW.png](./bzItW.png) | [captures/bzItW.png](./captures/bzItW.png) | Shell header, `Revise seu objetivo` (serif 36), guidance, `Título` (52 px input), `Descrição` (88 px area), `Habilidades sugeridas` + `Grafo`/`Lista` segmented control (44 px triggers), relation summary, graph box 1170 × 640 with the helper icon, root node 400 px (`--accent`, `--selo-text` border, target tile), three Skill nodes 360 px, zoom controls `− 100% +`, restart guidance, `Cancelar` ghost, `Reiniciar planejamento` outline, `Criar objetivo` primary | `PlanningProposalReview` inside `PlannerPage` with the 1170 px column (`max-w-[1170px]` only for the `proposal` view; the other states keep 760 px). `ProposalSkillGraph` lays the tree out with ELK (vertical spacing and order) and centers every layer on the widest one; the tree hangs 24 px from the top at zoom 1 when it fits, as drawn | `CA-01`, `CA-03`, `VM-02` |
| Review, list | `design/shifu.pen` / `zX9Ow` | Same, `Lista` tab | 1440 × 1077 | [zX9Ow.png](./zX9Ow.png) | [captures/zX9Ow.png](./captures/zX9Ow.png) | Same header and fields; list box with three rows (34 px jade tile, name 15/500, justification 13), dividers between rows | `ProposalSkillList` (`ul` labelled `Habilidades sugeridas`), same edits preserved across the switch | `CA-02`, `VM-02` |
| Restart dialog | `design/shifu.pen` / `eSaNL` | Same, `Reiniciar planejamento` open | 1440 × 1077 | [eSaNL.png](./eSaNL.png) | [captures/eSaNL.png](./captures/eSaNL.png) | Dimmed page, modal 600 px (`--surface-alt`, radius 14, padding 24, gap 24), serif title 30 + close `X`, label `O que você quer aprender?`, 144 px text area prefilled with the active intention, replacement warning, single `Iniciar planejamento` | `RestartPlanningDialog` on the shared `AlertDialog`; focus lands in the text area, so the selo focus ring is visible in the capture (not drawn in the frame) | `CA-06`, `CA-07`, `VM-02` |
| Restart, analyzing | `design/shifu.pen` / `SU4H8` | After `Iniciar planejamento`: status `processing`, operation `restart` | 1440 × 1180 | [SU4H8.png](./SU4H8.png) | [captures/SU4H8.png](./captures/SU4H8.png) | `Planeje seu objetivo`, intention card, jade spinner notice `Analisando seu objetivo…`, `Cancelar`, busy `Analisando…` | SHIFU-92 processing surface reused unchanged; the page returns to the 760 px column | `CA-08`, `VM-02` |
| Review, graph, mobile | `design/shifu.pen` / `gXrEP` | Status `proposal`, `Grafo` tab | 390 × 1621 | [gXrEP.png](./gXrEP.png) | [captures/gXrEP.png](./captures/gXrEP.png) | Title 30, fields full width, tabs under the heading, graph box 350 × 800, root 318 px, two Skill nodes 151 px side by side (icon above the name), third node 318 px, zoom controls bottom right, `Reiniciar planejamento` and `Criar objetivo` full width, `Cancelar` centered | Compact geometry below 800 px of container width: the Skills of a layer share the row (16 px gaps, 16 px inset), the root spans the row; zoom 100 % | `CA-11`, `VM-02` |
| Review, list, mobile | `design/shifu.pen` / `zCbC0` | `Lista` tab | 390 × 1160 | [zCbC0.png](./zCbC0.png) | [captures/zCbC0.png](./captures/zCbC0.png) | Same inventory stacked; list rows with wrapped justifications | Same widgets | `CA-11`, `VM-02` |
| Restart dialog, mobile | `design/shifu.pen` / `NxoN7` | Dialog open | 390 × 1096 | [NxoN7.png](./NxoN7.png) | [captures/NxoN7.png](./captures/NxoN7.png) | Modal 350 px (padding 20, gap 20), title 26, close 44 px, text area, warning, full-width action | `p-5`/`gap-5` below `sm`, `size-11` close target | `CA-06`, `CA-11`, `VM-02` |
| Restart, analyzing, mobile | `design/shifu.pen` / `lPCGg` | Processing after restart | 390 × 844 | [lPCGg.png](./lPCGg.png) | [captures/lPCGg.png](./captures/lPCGg.png) | Title, intention card, notice, `Cancelar` and busy action in one row | SHIFU-92 surface | `CA-08`, `VM-02` |

## Token mapping

Every value comes from `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css`;
no new token was needed.

| Pencil variable / value | Web token | Utility used |
| --- | --- | --- |
| `$page` `#0A0A0C` | `--background` | app shell |
| `$surface` `#161513` | `--card` | `bg-card` (selected tab, tooltip) |
| `$surface-alt` `#1D1E22` | `--surface-alt` | `bg-surface-alt` (graph and list boxes, Skill nodes, dialog, notice) |
| `$raised` `#1E1C18` | `--muted` | `bg-muted` (inputs, text areas, tab list, zoom controls) |
| `$divider` `#FFFFFF14` | `--border` | `border-border` (boxes, nodes, list dividers, dialog) |
| `$control-border` `#FFFFFF54` | `--control-border` | `border-control-border` (inputs, outline button, zoom controls, edges) |
| `$text-primary` `#F4F2EC` | `--foreground` | `text-foreground` |
| `$text-secondary` `#C4BFB6` | `--text-secondary` | `text-secondary-foreground` (guidance, justifications, labels, zoom icons) |
| `$text-muted` `#9A958D` | `--muted-foreground` | `text-muted-foreground` (unselected tab, helper icon) |
| `$selo-fill` `#DC2F2F` | `--primary` | `bg-primary` (primary actions, root icon tile) |
| `$selo-text` `#F28B8B` | `--selo-text` | `text-selo-text`, `border-selo-text` (root node, field errors, focus ring) |
| `$selo-tint` `#3D1414` | `--accent` | `bg-accent` (root node) |
| `$jade-tint` `#0E2E26` / `$jade-text` `#7BD3B6` | `--jade-tint` / `--jade-text` | Skill icon tiles, processing spinner |
| Instrument Serif 36 / 30 / 26 | `font-serif` | page title, dialog title (desktop / mobile) |
| Radii 6 / 10 / 14 | `rounded-md` / `rounded-[10px]` / `rounded-[14px]` | controls, boxes and nodes, dialog |

## Deviations from the frames

| Frame element | Implementation | Reason |
| --- | --- | --- |
| Skill node icons `code`, `terminal`, `table` | One `graduation-cap` tile for every Skill (graph and list) | The proposal payload carries no icon (spec decision D3) |
| Progress track and `…` actions menu inside each Skill node | Not rendered; nodes are shorter (about 130 px on desktop, 250 px for the narrow mobile nodes) | A proposal has no progress and no actions (D2); the frames reuse Learning's node |
| Tree drawn on the left 800 px of the 1170 px box | Tree centered horizontally in the box, 24 px from the top (16 px on mobile) | Centering keeps the same look for any number of Skills; the mobile frame is matched exactly |
| Orthogonal 1.5 px edges | ReactFlow `smoothstep` edges, 2 px `--control-border` | Shared edge style with the Learning graph |
| Static `git-fork` helper icon at 20 × 20 | The same icon is the `Restaurar posição inicial do grafo` button (44 px ghost target, tooltip) | Keyboard users need a way back after panning or zooming |
| Zoom buttons 32 × 32 | 32 px visual buttons with an invisible 44 px hit area | `design.md` requires 44 px touch targets on mobile |
| Text area without focus ring | Selo focus ring visible on the dialog text area in the capture | Focus lands in the field when the dialog opens (CA-06) |
| Dialog 310 px from the top (desktop) / 220 px (mobile) | Dialog centered in the viewport | Shared `AlertDialog` placement |
| Header `Objetivos ▾` and no mobile bottom navigation | Current shell: top navigation on desktop, bottom navigation and floating Mentor button on mobile | Shell belongs to earlier deliveries; captured at the bottom of the tall viewport |
| Root title wraps after `com` at 390 px | Wraps after `a` | Browser font metrics |
