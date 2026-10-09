# Mentor sessions management design handoff

Canonical editable design: [design/shifu.pen](../../../../../design/shifu.pen).
The eight PNG references below were exported through Pencil MCP at scale 1 and
visually inspected on 2026-10-08. They are design references, not runtime evidence.
This task did not edit the Pencil document; its pre-existing dirty state is preserved.
The Spec's approved behavior and repository UI Rules govern the adaptations below.

| Reference / Pencil node | Surface / required state | Reference dimensions | Saved image | Criteria / checks |
| --- | --- | --- | --- | --- |
| O6cds — 15.4 Mentor · nova conversa | /intelligence, unsaved draft, sidebar and composer | 1440×1058 | [O6cds.png](references/O6cds.png) | CA-01/10/11; VM-01/02 |
| XOwCJ — 15 Mentor · conversa | /intelligence?session=<id>, selected persisted conversation | 1440×1180 | [XOwCJ.png](references/XOwCJ.png) | CA-05/10/11; VM-01/02 |
| yXJ3I — 15.6 Mentor · modal pelo FAB | Existing protected route, FAB new-conversation panel | 1440×900; panel 566×800 | [yXJ3I.png](references/yXJ3I.png) | CA-01/10/11; VM-01/02 |
| tMGjt — 15.7 Mentor · histórico no FAB | FAB history/search, selected conversation indication | 1440×900; panel 566×800 | [tMGjt.png](references/tMGjt.png) | CA-04/10/11; VM-01/02 |
| PdJCw — 15.8 Mentor · conversa pelo FAB | FAB selected conversation, expansion and composer | 1440×900; panel 566×800 | [PdJCw.png](references/PdJCw.png) | CA-05/10/11; VM-01/02 |
| Oodia — Diálogo · renomear conversa | Selected persisted conversation, rename dialog | 480×280 | [Oodia.png](references/Oodia.png) | CA-06/10/11; VM-01/02 |
| oTjig — Diálogo · excluir conversa do Mentor | Selected persisted conversation, destructive confirmation | 480×347 | [oTjig.png](references/oTjig.png) | CA-07/10/11; VM-01/02 |
| EmQFg — 15.29 Mentor · remoção · mobile | Mobile fullscreen shell/style only; its action-card content is excluded | 390×1100 | [EmQFg.png](references/EmQFg.png) | CA-10/11; VM-01/02; accepted mobile assumption |

Capture desktop full pages at the first two reference viewports and FAB states at
1440×900. Dialogs use the same desktop surface with a fitted 480 px reference width
and may be inspected as crops. Mobile runtime uses 390×844, adapting the 390 px shell
to the available viewport with independently scrolling history/content and a reachable
composer. Actual messages/titles, wrapping and disabled-state explanations can change
content height; reference artboard height is not a fixed runtime height.

## Approved adaptations and scope

- Per user direction on 2026-10-09, the dedicated `/intelligence` page omits
  redundant floating Mentor access. Other protected routes (including Planner)
  retain the FAB; the shared provider preserves page/panel continuity.
- Desktop panel width is 566 px, explicitly selected over the earlier 400 px design
  document value. Preserve viewport gutters and constrain height to the viewport.
  Mobile opens fullscreen; never squeeze the desktop sidebar beside the conversation.
- There are no specific mobile session-management frames for new/history/pending/
  rename/delete. The user explicitly accepted adapting these from the fullscreen
  EmQFg shell plus desktop component hierarchy and shared primitives. EmQFg does not
  establish a Remove Habilidade workflow for this slice.
- New drafts have no rename/delete action or persisted history entry. The reference's
  active-looking Renomear on Nova conversa must be unavailable.
- Canonical page header orders the mono IA usage affordance, pencil + Renomear,
  then brain + Memórias. Use `IA · indisponível` without sample usage/renewal data;
  keep normal-weight compact labels and wrap mobile actions within the viewport.
- Keep attachment, audio, Memories and quota affordances visible but disabled, as
  explicitly requested. Use disabled semantics, no active destination/handler and
  accessible Indisponível no momento text. Do not show the reference's sample 42%,
  renewal dates or fabricated usage. Disabled controls need not be sequential tab
  stops, but their purpose/unavailability must be available to assistive technology.
- References show generated answers, attachments, tool traces and action cards.
  Preserve only the relevant message/composer layout; render actual stored messages.
  The initial accepted message shows Mensagem salva. A resposta ainda não está
  disponível. Do not display a fake answer, processing animation or queued job.
  Subsequent-send controls remain unavailable until their delivery exists.
- Do not invite unavailable attachment upload in helper/placeholder text. Page
  context may identify the current route visually; it does not claim consultation
  or send page/account content to title inference.
- Starter prompts in O6cds/PdJCw rely on activity-context consultation and suggested
  actions outside this slice (RF-12 exclusions). Omit those cards rather than imply
  access to the illustrated Learning context.
- Dialogs preserve the current shared primitive: 512 px maximum desktop width and
  UI-font titles. The 480 px frames remain visual references; shared primitive
  consistency governs this adaptation. Rename keeps a visible field label.
- Rename Oodia lacks the mandatory icon tile, separate close action and separator.
  Apply the shared dialog header. Its jade field border is replaced by the existing
  shared Input focus treatment. Delete oTjig already supplies that header hierarchy.
- Use control-border for interactive boundaries, rather than copying divider-only
  search/input borders. Preserve at least 44 px mobile hit targets where references
  contain smaller controls. Long titles/text wrap or truncate accessibly without
  horizontal page overflow.
- Selected conversation indication uses more than color. Search and timeline load
  automatically; provide an accessible load/retry action for keyboard/recovery.
  Draft, selection and loading outcomes follow the Spec; no fictitious history data.
- Independent Memories are not copied/deleted. Destructive copy can preserve the
  design's explanation of inaccessible history/source links; it must not imply this
  slice has created attachments, summaries or Memories.

## Token and primitive mapping

The existing Dojo dark theme and shared primitives are the implementation authority.
Do not introduce parallel literal colors, typography, radii, spacing or shadows.

| Pencil value / component | Existing Shifu mapping | Owning application |
| --- | --- | --- |
| page; surface; raised; surface-alt | bg-background; bg-card; bg-muted; bg-surface-alt | Page, sidebar, panel, message surfaces |
| text-primary; text-secondary; text-muted | text-foreground; text-secondary-foreground; text-muted-foreground | Titles, message content, supporting copy |
| selo-fill / on-selo | bg-primary / text-primary-foreground | Shared Button default; send/new/save |
| destructive fill | Shared Button danger and existing danger semantic token | Delete confirmation |
| divider / control-border | border-border / border-control-border | Separators versus interactive boundaries |
| font-ui / font-display / font-mono | font-sans (DM Sans) / font-serif (Instrument Serif) / font-mono (JetBrains Mono) | Body and controls / headings / code and supporting metadata |
| control/card/modal radii; spacing variables | Existing semantic radius and spacing utilities, preserving 6/10/14 px design roles and 4/8/12/16/24/32/48 spacing rhythm | Controls, message/history cards, dialogs and panel |
| Input UzvM7; composer b96Jv4 (O6cds child, 1024×56) | Shared Input/Textarea/Label; existing primitive focus ring/border | Search, rename, composer |
| DS primary/outline/ghost/destructive | Existing Button default/outline/ghost/danger variants | Main, secondary, icon and destructive actions |
| ConversationSidebar jn28o; ConversationHeader iNUby | Intelligence-owned composition of existing primitives | History/title/actions, shared by page and panel |
| FAB ycX9o | Intelligence MentorFab trigger using existing Button and Icon | Protected AppLayout |
| Dialogs Oodia/oTjig | Shared dialog/AlertDialog, mandated header, shared Button/Input | Rename/delete |

Use the actual existing Icon wrapper and extend its icon map only when needed.
The composer has 88×44 attachment and 44×44 dictation/send controls, with one
composite focus outline. The inner textarea delegates focus styling; page ancestors
must not clip that outline. Preserve shared input focus behavior elsewhere.
Pending controls expose disabled/busy semantics; errors use accessible text and
existing application feedback conventions. Skeletons/status text use existing
semantic surfaces. Reduced motion does not remove status information.

## Preserved surroundings and evidence

Keep the existing authenticated header, account menu, primary navigation, bottom
navigation and underlying Learning page behavior. FAB visibility does not authorize
changes to those business flows. The page remains IntelligencePage at /intelligence.

Runtime captures belong under apps/web/.playwright-cli/screenshots/, snapshots/,
and logs/; record observations and actual paths in evaluation.md during implementation.
This directory contains only durable source design references. Visual review must
inspect captures against the appropriate row and these approved adaptations.

### Composer multiline adaptation (2026-10-09)

The user requested automatic growth as lines are added. Preserve the 56px initial composite; grow with draft content and narrower wrapping, cap the textarea at the existing `max-h-44` (176px) token, then scroll internally. Clear drafts shrink the field. Attachment, dictation and Send remain bottom aligned. Fresh desktop/mobile captures: `apps/web/.playwright-cli/screenshots/mentor-growing-{1440,390}.png`.

## JhtFv sidebar correction — 2026-10-09

Pencil MCP inspection confirmed the300px sidebar,12pxpadding,10pxgaps,
searchicon and readable title/date rows. Runtime now uses compact44px rename/delete
icon buttons with explicit pt-BR names, preserving the delivery's management
operations while avoiding the former text actions squeezing titles into two-letter
lines. Dates come from actual lastActivityAt; activity-context text, group labels
and a new desktopcollapse interaction are not fabricated. Desktop1440×900 and
mobile390×844 captures were inspected and independently passed (EV-23).

### Loading skeleton adaptation (2026-10-09)

User requested skeleton loading for the Mentor page, consistent with design §7. Scope validation reserves the existing desktop sidebar/header/welcome/composer composition; mobile omits the desktop sidebar. History loading uses three conversation-shaped placeholders beneath search and retains loaded rows during paging. Conversation loading replaces the empty welcome with message-shaped placeholders; loaded messages remain visible during older-page requests. All placeholders use the shared reduced-motion-aware Skeleton primitive, are decorative/hidden from assistive technology, and have one pt-BR loading announcement. Scope placeholders contain no private data. Captures `mentor-skeleton-{scope,history,conversation}-{desktop,mobile}.png` are local evidence under `apps/web/.playwright-cli/screenshots/`.

### FAB fidelity correction — 2026-10-09

Reinspected `yXJ3I`, `tMGjt`, and `PdJCw` through Pencil MCP. FAB uses the
566×800 desktop dock with 24px gutters, charcoal surface, separate draft/history/
selected headers, labeled desktop actions, full-width history creation, icon-only
attachment and compact conversation typography. Mobile retains back/expand/close
controls with title truncation and a reachable composer. Targets remain 44px;
reference contextual suggestions and grouping are omitted until their underlying
contracts exist. VM-02 fresh desktop/mobile comparisons passed (EV-24).

Final local conclusion (rev8): disabled Memories/quota placeholders remain on the dedicated page and are omitted in the FAB as requested. Panel entrance respects reduced motion. Fresh desktop/mobile FAB and settled dialog comparisons passed EV-33; the initial mobile delete frame was captured during entrance and superseded by the settled frame.
