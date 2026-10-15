# Mentor attachment design handoff

Canonical editable design: `design/shifu.pen`. Its staged user change is preserved.
Pencil MCP was unavailable during research; the user explicitly approved adapting
missing attachment states from saved references and existing primitives (Q7).
The following PNGs were visually inspected on 2026-10-14; they are source design
references, not runtime screenshots or proof of behavior.

| Reference | Required surface/state | Viewport | Saved reference | Criteria/check |
| --- | --- | --- | --- | --- |
| XOwCJ | Page, historical image preview, filename and source hierarchy; adapted ready-draft preview |1440 × 1180 | [XOwCJ](../../mentor-sessions-management/design/references/XOwCJ.png) | CA-09/13; VM-02/03 |
| PdJCw | FAB conversation, ready composer and historical preview adapted from page |1440 × 900;566 × 800 panel with24 px gutters | [PdJCw](../../mentor-sessions-management/design/references/PdJCw.png) | CA-09/13; VM-02/03 |
| EmQFg | Mobile fullscreen shell, ready draft and reopened attachment history |390 × 844 runtime,390 × 1100 reference | [EmQFg](../../mentor-sessions-management/design/references/EmQFg.png) | CA-09/13; VM-02/04 |

## Approved adaptations

- Enable attachment selection; keep text mandatory. No fabricated quota/memories,
  contextual suggestions, tool transcript or action card from reference artwork.
- Inline image preview in draft and historical message, bounded by message width
  with preserved aspect ratio, filename/alt and loading/error text. Non-images use
  readable file rows. PDF does not acquire an inline viewer.
- Ready/partial metadata and file/page/chunk sources use actual server values.
  Partial reading is stated explicitly. Preparation/failure/removal are per-file.
- Mobile uses fullscreen page/FAB and independently scrolling content; no desktop
  sidebar squeezing messages. Source/file text wraps, controls remain reachable.
- Composer retains 56 px baseline and max-h-44 textarea growth; attachment area
  adds height outside textarea. Bottom-aligned44 px controls retain composite focus.
- Only Button default/ghost/danger variants exist in current source. The older
  handoff's outline variant is not an available primitive; do not introduce it
  merely to reproduce that historical table.

## Token and widget ownership

| Role | Existing mapping | Owner |
| --- | --- | --- |
| Page/card/raised surfaces | bg-background, bg-card, bg-muted, bg-surface-alt | Existing page/FAB and message composition |
| Foreground/secondary/muted text | text-foreground, text-secondary-foreground, text-muted-foreground | Filename, status, sources |
| Controls/borders | shared Button default/ghost/danger, border-control-border; border-border for separators | Composer/remove/read actions |
| Typography | font-sans DM Sans; font-serif Instrument Serif headings; font-mono JetBrains Mono code/metadata | Existing hierarchy retained |
| Focus/spacing/radius | Shared Input/Textarea focus; existing semantic utilities and 4/8/12/16/24 rhythm, existing control/card radii | No parallel literal styling |

MentorContext owns shared preparation state and temporary object URLs. Composer
owns picker/keyboard interaction; AttachmentList is pure. Reused module-level
MentorAttachmentPreview renders images; MessageItem owns authorized read/error
state and cleanup; Sources is a pure child. Pure children have no invented hooks
or test suites. Status conveys text/semantics rather than color alone; removal
returns focus predictably and announces results in pt-BR.

Preserve application navigation/header/account menu, page/FAB continuity, history
management, dictation and pending-response controls outside the attachment change.
Dedicated Mentor page continues without redundant FAB.

Implementation captures belong only under
`apps/web/.playwright-cli/{screenshots,snapshots,logs}/`; record fresh paths and
comparisons in Evaluation. Required captures: desktop page ready/history, desktop
FAB ready/history, mobile ready/history. Negative states use automated checks.
