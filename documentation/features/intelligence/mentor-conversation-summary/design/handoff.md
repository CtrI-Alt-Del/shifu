# Mentor conversation summary — design handoff

Canonical design: [`design/shifu.pen`](../../../../../design/shifu.pen), inspected and
exported through Pencil MCP at scale 1 on 2026-10-18 (active editor
`design/shifu.pen`). The PNGs below are durable references, not runtime evidence.
The `.pen` file was not modified. The [Spec](../spec.md) and the UI Rules govern;
this handoff supersedes the "summaries" exclusion in
[`mentor-context/design/handoff.md`](../../mentor-context/design/handoff.md) for the
surfaces listed here only.

## Required frames

| Reference / Pencil node | Surface / required state | Reference dimensions | Saved image | Criteria / checks |
| --- | --- | --- | --- | --- |
| KVnFQ — 15.13 Mentor · resumindo contexto | Page; response in progress with `progress = summarize-context`: processing marker after the pending learner message; composer disabled with "Aguarde enquanto o contexto é resumido" | 1440×1058 | [KVnFQ.png](references/KVnFQ.png) | CA-13; VM-01, VM-03 |
| RDiWy — 15.12 Mentor · conversa resumida | Page; ready marker "Contexto resumido · Ver resumo" at the boundary; answer below | 1440×1058 | [RDiWy.png](references/RDiWy.png) | CA-13; VM-01, VM-04 |
| T4Edi — 15.20 Mentor · consultar resumo de contexto | Page; summary content (title "Resumo desta conversa", paragraph, preservation line, two actions) — runtime shows it inside a dialog | 1440×1058 | [T4Edi.png](references/T4Edi.png) | CA-13; VM-01, VM-05 |
| ov9QQ — 15.34 Mentor · consultar resumo · mobile | 390 px; same content stacked, buttons full row — runtime shows it in a near full-screen dialog | 390×1000 | [ov9QQ.png](references/ov9QQ.png) | CA-13; VM-02, VM-06 |
| ySE0r — Mentor/CompactionMarker (reusable) | Marker component: icon, label, ghost "Ver resumo" | 640×44 | [ySE0r.png](references/ySE0r.png) | CA-13 |

Runtime viewports: page 1440×900; FAB 1440×900 with the existing 566×800 panel; mobile
390×844 (adapted from ov9QQ's 390-wide artboard). Artboard height is not runtime height.

## Marker variants (ySE0r)

- **ready:** `scroll-text` icon + "Contexto resumido" in `$text-muted`, `$font-ui` 13 px,
  plus ghost button "Ver resumo" (dialog trigger, `aria-haspopup="dialog"`).
- **processing (KVnFQ override mtXqc):** `loader-circle` icon + "Resumindo contexto…" in
  `$jade-text`; the "Ver resumo" button is disabled/omitted.
- **failed (Spec RF-06, no frame):** `circle-alert` icon + "Não foi possível resumir o
  contexto. O histórico completo continua disponível." in `$text-muted`; no button.
  Visual adaptation of the same component; text carries the meaning.

## Approved adaptations and scope

- **Reading surface is a modal dialog (user decision Q74/Q75, 2026-10-18).** T4Edi and
  ov9QQ show the summary as an inline card below the marker; runtime opens the same
  content (title, paragraph, preservation line, "Ver mensagens originais", "Fechar
  resumo") in a `role="dialog"` from the new `ui/shadcn/dialog.tsx` (Radix Dialog) with
  overlay, close button, focus trap, Escape and focus return to "Ver resumo". Desktop:
  centered `max-w-lg`, reusing `.dialog-overlay`/`.dialog-content` and their
  reduced-motion rules. 390 px: near full-screen with 16 px margins, scrollable content and
  stacked full-width actions as in ov9QQ (Q76). In the FAB the dialog renders above the
  panel. `design/shifu.pen` is not modified; visual checks compare content, tokens and
  spacing against T4Edi/ov9QQ inside the dialog container.
- **Dialog header (UI Layer "Dialog header structure").** Because the content now sits in
  a dialog, the shared header hierarchy applies: a `scroll-text` icon tile (`rounded-full
  bg-accent`, as in `confirmation-dialog`) left of the title and the description (the
  preservation line moves into `DialogDescription`), the close action at the top-right and a
  soft `border-border` separator before the body. T4Edi has no icon tile or close button;
  both are required by the rule, not design deviations of choice.

- The frames place the marker directly above the newest question. Runtime places it after
  the boundary message (the newest message outside the 10-message recent window, Spec
  RF-01). Position follows the boundary, not the frame sample.
- The design's summary paragraph is illustrative prose. Runtime text is the server-rendered
  deterministic template built from verbatim extractive excerpts (Spec RF-02/RF-09), shown
  as plain text.
- The processing marker replaces the existing `ResponseStatus` row while
  `progress = summarize-context`; the existing "Cancelar" action stays reachable inside the
  live area (RP-06). KVnFQ does not show cancel; keeping it is an approved adaptation.
- Outline buttons (`RaoIi`) "Ver mensagens originais" and "Fechar resumo" map to
  `Button variant="ghost"` plus `border border-control-border text-foreground`, following
  the SHIFU-103 handoff rule not to introduce an outline variant.
- KVnFQ hides the composer's "Anexar" control while disabled; runtime keeps the existing
  composer layout with every control disabled.
- Reduced motion: the processing icon does not spin; the label still conveys the state.
- Touch targets stay ≥ 44 px (existing `Button` `min-h-11`).
- No fake data: the context bar's "IA 42% · renova 1 nov" text is preserved UI outside
  this change (quota is out of scope) and is not introduced or altered.

## Token and primitive mapping

No parallel literal palette, font, radius or shadow.

| Pencil value / component | Existing Shifu mapping | Owning widget |
| --- | --- | --- |
| `$text-muted` #9A958D | `text-muted-foreground` | summary-marker label (ready/failed) |
| `$jade-text` #7BD3B6 | `text-jade-text` | summary-marker processing label/icon |
| `$font-ui` DM Sans 13 px | `font-sans text-[13px]` | summary-marker label |
| `$surface-alt` #1D1E22 | `bg-surface-alt` | summary-dialog content surface |
| `$divider` | `border-border` | summary-dialog border |
| `$control-border` | `border-control-border` | dialog action buttons |
| `$radius-card` 10 | existing 10 px card radius used by Mentor surfaces | summary-dialog |
| `$space-3` / `$space-4` (12/16) | `gap-3` / `p-4` | summary-dialog |
| Dialog icon tile (no frame) | `rounded-full bg-accent` tile + `scroll-text` `Icon`, as in `confirmation-dialog` | summary-dialog header |
| Header separator (no frame) | `border-b border-border` | summary-dialog header |
| Overlay / modal container (no frame) | existing `.dialog-overlay` / `.dialog-content`, `bg-card`, `border-control-border` as in `ui/shadcn/alert-dialog.tsx` | `ui/shadcn/dialog.tsx` |
| `CZw0W` V2/Button/Ghost | `Button variant="ghost"` | "Ver resumo" |
| `RaoIi` V2/Button/Outline | `Button variant="ghost"` + `border border-control-border text-foreground` | dialog actions |
| lucide `scroll-text`, `loader-circle`, `circle-alert` | shared `Icon` (`scroll-text` added to the map) | summary-marker |
| Composer L1j2DY disabled placeholder | existing composer, `disabled`, placeholder "Aguarde enquanto o contexto é resumido" | composer |

## Preserved surroundings and evidence

Sidebar (jn28o), header (iNUby), context bar (VSZka), message bubbles and the composer
layout are unchanged apart from the disabled state. Runtime captures belong under
`apps/web/.playwright-cli/{screenshots,snapshots,logs}/` and are recorded in
`evaluation.md`; no feature-local evidence folder.
