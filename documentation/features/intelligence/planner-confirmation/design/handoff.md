# Planner confirmation design handoff

The authoritative design source is `design/shifu.pen`. The four frames referenced by
SHIFU-95 were exported with Pencil `Export` at scale `1` on 2026-10-20 into this directory
(`<nodeId>.png`, same pixel size as the frame). The implementation captures in `captures/`
come from the browser suite `apps/web/tests/intelligence/planner-page.test.ts` (confirmation
frame walks) run with `PLANNER_CAPTURE_DIR` set, mocked transport, same copy as the frames,
on a viewport as tall as the document (1440 and 390 wide), with CSS animations
fast-forwarded. `comparisons/<nodeId>.png` places the export on the left and the capture on
the right.

Structural inspection in Pencil (`Get` with `ctx.problems`) reported zero clipped or
overflowing descendants in the four frames. Every PNG was opened after export and is
non-empty.

## Manifest

| Reference | Source / node | Route / surface / state | Viewport | Export | Capture | Visible inventory | Implementation notes | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Creating the Goal | `design/shifu.pen` / `BswO3` | `/intelligence/planner/$planningId`, review in `Lista`, confirmation in flight | 1440 × 1180 | [BswO3.png](./BswO3.png) | [captures/BswO3.png](./captures/BswO3.png) | `Revise seu objetivo`, notice with jade spinner `Criando seu objetivo…` / `Estamos salvando o objetivo e as habilidades que você confirmou.`, guidance, dimmed `Título` and `Descrição`, `Habilidades sugeridas` with `Lista` selected, three rows, restart guidance, dimmed `Cancelar` and `Reiniciar planejamento`, busy primary `Criando objetivo…` with spinner | `PlanningProcessingNotice` (tone `processing`) between the title and the guidance; fields and secondary actions `disabled`; primary `aria-busy` with `loader-circle` | `CA-08`, `VM-02` |
| Creation failed | `design/shifu.pen` / `qJw1C` | Same, after a refused creation | 1440 × 1077 | [qJw1C.png](./qJw1C.png) | [captures/qJw1C.png](./captures/qJw1C.png) | Notice with selo `triangle-alert` `Não foi possível criar o objetivo` / `Sua proposta foi mantida. Tente criar o objetivo novamente.`, fields enabled with the kept edits, list, `Cancelar`, `Reiniciar planejamento`, primary `Tentar criar objetivo` | Tone `failure` (role `alert`); the backend reason precedes `Sua proposta foi mantida.` when present | `CA-09`, `VM-02` |
| Creating, mobile | `design/shifu.pen` / `FxmF8` | Same as `BswO3` | 390 × 1276 | [FxmF8.png](./FxmF8.png) | [captures/FxmF8.png](./captures/FxmF8.png) | Same inventory stacked; `Reiniciar planejamento` dimmed above the busy full-width primary, `Cancelar` centered below | Same widgets; `order` utilities of the review | `CA-12`, `VM-02` |
| Creation failed, mobile | `design/shifu.pen` / `n8OPLr` | Same as `qJw1C` | 390 × 1200 | [n8OPLr.png](./n8OPLr.png) | [captures/n8OPLr.png](./captures/n8OPLr.png) | Notice, fields, list, then `Tentar criar objetivo` full width **above** `Reiniciar planejamento`, `Cancelar` centered | The primary gets `order-first` below `sm` only in the `failed` state; DOM order (and the tab order) stays `Reiniciar planejamento`, primary | `CA-12`, `VM-02` |

The uncertain result (lost response) has no frame: it reuses the same notice with the
`uncertain` tone (`clock-3`, role `status`), copy `Não conseguimos confirmar a criação do
objetivo` / `A resposta não chegou. Verifique o resultado antes de tentar de novo: a mesma
confirmação não cria outro objetivo.`, the review frozen and the primary `Verificar resultado`.

## Token mapping

Every value comes from `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css`;
no new token was needed. The review tokens are listed in `../../planner-review/design/handoff.md`.

| Pencil variable / value | Web token | Utility used |
| --- | --- | --- |
| `$surface-alt` `#1D1E22` + `$divider` `#FFFFFF14` | `--surface-alt`, `--border` | notice card (`bg-surface-alt border-border`, radius 10, padding 16, gap 12) |
| `$jade-text` `#7BD3B6` | `--jade-text` | spinner of the creating notice and of the busy primary |
| `$selo-text` `#F28B8B` | `--selo-text` | `triangle-alert` of the failure notice |
| `$text-primary` `#F4F2EC` 15 / 600 | `--foreground` | notice title |
| `$text-secondary` `#C4BFB6` 13 | `--text-secondary` | notice support |
| Fields at opacity 0.6, actions at 0.4 / 0.65 | shared `disabled:` styles of `Input`, `Textarea`, `Button` | frozen review |

## Deviations from the frames

| Frame element | Implementation | Reason |
| --- | --- | --- |
| Failure frames omit the guidance paragraph `Esta proposta considera…` | The paragraph stays in every state | The creating and idle frames keep it; dropping it only on failure would shift the whole page on each retry |
| Failure support copy is the generic sentence | `<backend reason> Sua proposta foi mantida.` when the backend gives a reason (`curriculum_gap`, divergent confirmation, state conflicts); the generic sentence otherwise | PRD RP-10 asks for understandable validation and technical errors |
| Dimmed fields and actions at opacity 0.6 / 0.4 / 0.65 | Shared disabled styles (opacity 0.5) | One disabled style across the product; the state is also conveyed by `disabled`, `aria-busy` and the live notice |
| Skill rows with `code`, `terminal`, `table` icons | One `graduation-cap` tile | Review decision D3 (the payload carries no icon) |
| Mobile failure frame leads with `Tentar criar objetivo` | Visual order only (`order-first` below `sm`); the DOM keeps `Reiniciar planejamento` first | Keeps one tab order across states |
| Header `Objetivos ▾`, no bottom navigation | Current shell (top navigation on desktop, bottom navigation and floating Mentor button on mobile) | Shell belongs to earlier deliveries |
