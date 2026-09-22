# Objectives Home design handoff

The authoritative source is `design/shifu.pen`. Inspected via `pen interactive`
(headless, `--in design/shifu.pen`) on 2026-09-20. Export scale `1`. The screenshot
is non-empty and matches its declared viewport.

| Reference | Pencil file/node | Route/state | Viewport | Screenshot | Visible inventory | Validation |
| --- | --- | --- | --- | --- | --- | --- |
| Home | `design/shifu.pen` / `AMF1e` ("03 Home") | `/`, populated | 1440 × 900 | [AMF1e.png](./AMF1e.png) | Shared `AppLayout` header (out of scope); intro heading "O que você quer aprender?" + subcopy; textarea (placeholder "Ex.: quero conseguir automatizar tarefas repetitivas com Python"); ghost "Criar manualmente" action; primary "Planejar com IA" button; "Seus Objetivos" title + live count; responsive grid of `ObjectiveCard` (title, description, "N Habilidades", trailing arrow icon) | CA-01, CA-03, CA-04 |

A second frame, `LO4Z3` ("03.1 Home · menu aberto"), shows the same page with the
shared header's `V2/Menu/Objetivos` dropdown open. That is shared `AppLayout`
navigation behavior, not Home-content behavior, and is excluded from this Spec.

No mobile-specific Home frame exists in `design/shifu.pen`. Narrow-viewport layout
is resolved from `documentation/design.md` §3.6 breakpoints (`mobile < 640`) and the
existing repository pattern of stacking a multi-column grid to one column below
`sm`/`md`, as already used by `apps/web/src/ui/intelligence/widgets/pages/intelligence-page`.

## Offline implementation authority

1. `documentation/design.md` and `apps/web/src/ui/shared/styles/global.css` own
   Shifu semantic tokens, dark-only behavior, typography and focus language.
2. Existing widgets under `apps/web/src/ui/shared/widgets` and shadcn primitives
   under `apps/web/src/ui/shadcn` own interaction, disabled, keyboard and motion
   behavior.
3. This handoff owns component selection and the Pencil-to-Shifu mapping below.
4. The saved PNG owns visual comparison and content hierarchy.

## Extracted node inventory

| Pencil node | Role | Extracted content |
| --- | --- | --- |
| `h7fGzC` (`V2/Header`) | Shared `AppLayout` header | Already implemented; out of scope. |
| `JOVQv` / `L0TmE` | Intro heading + subcopy | "O que você quer aprender?" / "Descreva com suas palavras. O Shifu monta uma proposta com Habilidades reais e você confirma antes de criar." |
| `CHEGv` (textarea) | Free-form intent field | Placeholder: "Ex.: quero conseguir automatizar tarefas repetitivas com Python". |
| `RpBtN` (ref `CZw0W`, `V2/Button/Ghost`) | Manual-creation action | Label "Criar manualmente". |
| `QeCXy` (ref `ygtpy`, `V2/Button/Primary`) | Start-planning action | Label "Planejar com IA". |
| `F5WEwL` (`goals-header`) | Section header | "Seus Objetivos" + live count text (e.g. "6 objetivos"). |
| `G4Jk27` (`V2/ObjectiveCard`) | Goal card | Title, description, "N Habilidades" text, trailing `arrow-right` icon (`lucide`). All six real instances in the frame override the component's generic placeholder text (which shows a skill-status breakdown) with the plain "N Habilidades" count only — confirms no per-skill status belongs on this card. |

## Component mapping

| Pencil source | Shifu implementation | Required configuration |
| --- | --- | --- |
| `V2/Button/Ghost` ("Criar manualmente") | Shared shadcn `Button` ghost variant or existing `Anchor` styled as ghost | Navigates to the manual-creation placeholder route; 44px min touch target on mobile. |
| `V2/Button/Primary` ("Planejar com IA") | Shared shadcn `Button` default variant | Disabled while the intent is empty or the start-planning request is pending; loading state uses `loader-circle` per existing `Icon` widget. |
| Textarea | Shared shadcn `Textarea` (or existing form primitive) | Multi-line, visible label, non-color-only invalid state on empty submit. |
| `V2/ObjectiveCard` | New `apps/web/src/ui/learning/widgets/components/objective-card` | Renders title, description (2-line clamp), skill count with correct pt-BR singular/plural, `arrow-right` icon via the shared `Icon` widget; whole card is a keyboard-operable link to the goal-detail placeholder route. |
| Section header + count | New `goals-list-section` layout | "Seus Objetivos" heading + live count derived from the query result length (singular/plural). |
