# Mentor contextual responses — design handoff

Editable authority: [shifu.pen](../../../../../design/shifu.pen), inspected through Pencil MCP on2026-10-10. No design edit is part of this Spec. Its existing dirty state is preserved. User approved the Mentor frame selection before requesting the written Spec.

Durable PNGs below come from the concluded [session-management handoff](../../mentor-sessions-management/design/handoff.md), exported at scale1 on2026-10-08 and visually inspected. They are source references, not fresh runtime evidence. Fresh export attempted during this drafting session failed because the MCP editor no longer resolved the Shifu nodes; no new image was saved. Existing images remain available. Error frame IDs/text were inspected live on2026-10-10; they are supplemental, not required happy-path capture references.

| Pencil node / frame | Included surface/state | Durable image | Dimensions / capture | Criteria/checks |
| --- | --- | --- | --- | --- |
| O6cds —15.4 nova conversa | Page draft/composer, no empty persisted conversation | [O6cds.png](../../mentor-sessions-management/design/references/O6cds.png) |1440×1058 |CA-01/12; VM-01/03 |
| XOwCJ —15 conversa | Page persisted messages and approved response | [XOwCJ.png](../../mentor-sessions-management/design/references/XOwCJ.png) |1440×1180 |CA-07/12; VM-01/03 |
| yXJ3I —15.6 modal FAB | FAB draft and composer | [yXJ3I.png](../../mentor-sessions-management/design/references/yXJ3I.png) |1440×900, panel566×800 |CA-03/12; VM-01/03 |
| PdJCw —15.8 conversa FAB | Selected FAB conversation, expand/close | [PdJCw.png](../../mentor-sessions-management/design/references/PdJCw.png) |1440×900, panel566×800 |CA-07/12; VM-01/03 |
| tMGjt —15.7 histórico FAB | Preserved navigation/history | [tMGjt.png](../../mentor-sessions-management/design/references/tMGjt.png) |1440×900 |CA-07/12; CI-08 |
| EmQFg —15.29 mobile | Fullscreen mobile shell only, action card excluded | [EmQFg.png](../../mentor-sessions-management/design/references/EmQFg.png) |source390×1100; runtime390×844 |CA-12; VM-01/03 |
| yfOZm —15.9 falha | Message preserved, “Aguardando resposta”, “Tentar novamente”; pending composer | Live Pencil node; no durable export in this feature |1440×1058 |CA-08/12; CI-08 |
| x2HsU —15.10 IA indisponível | Temporary generator failure; conversations remain accessible | Live Pencil node; no durable export in this feature |1440×1058 |CA-06/12; CI-08 |
| upndz —15.11 falha FAB | Same failed/pending recovery in dock | Live Pencil node; no durable export in this feature |1440×900 |CA-08/12; CI-08 |

## Approved adaptations

- This slice replaces earlier “mensagem salva/resposta indisponível” placeholders with real queued/processing/partial/completed/failed/cancelled states. Multiple independent requests form ordered blocks in one reply. Generic consultation indicators describe actual authorized calls, without raw transcripts or private context.
- Typing is presentation of an already approved complete block. Historic/catch-up/reopened blocks appear complete; reduced motion removes typing. Screen readers receive full approved text without per-character announcements. Markdown/code preserve the conversation hierarchy.
- Mobile adapts EmQFg fullscreen shell and desktop hierarchy at390×844, an explicitly accepted visual assumption. No Skill removal/addition card is implied. Desktop FAB keeps566px width, viewport gutters/height and44px targets. No sidebar squeezed into mobile.
- Failure frames preserve the learner message and offer retry without resend. Pending composer asks the user to resolve the response. x2HsU must not disable adequate local answers merely because the conversational generator is unavailable. Later-block failure marks the reply partial/failed, never completed.
- Preserve delivered rename/delete/search/sidebar, multiline composer growth with max-h-44 cap, skeletons and focus behavior from the previous handoff. Exclusion invalidates ongoing processing; no new management flow is introduced.
- Page omits redundant FAB; other protected routes retain FAB. Page/FAB share provider and presentation registry. Context hint from the current recognized Learning route is captured on send; visual context alone is not proof that a query ran.
- No action cards, summaries, memories, attachments or dictation workflows. Preserve existing disabled affordances: page quota/memories disabled with unavailable copy, FAB omits them. Never show sample42%, renewal dates or fake data. Do not resurrect starter cards requiring unapproved actions.
- Runtime text, titles and code lengths vary from reference samples; artboard height is not fixed runtime height. Approved blocks must wrap/scroll without global overflow.

## Token and primitive mapping

Existing Dojo tokens and shared primitives govern. No parallel literal palette, font, radius or shadow.

| Design role / reusable node | Shifu mapping / owner |
| --- | --- |
| Background/card/raised/alternate | bg-background/bg-card/bg-muted/bg-surface-alt, existing page/panel |
| Primary/secondary/muted text | text-foreground/text-secondary-foreground/text-muted-foreground |
| Primary and other buttons | Shared Button default/outline/ghost/danger; Icon wrapper |
| Divider versus interactive border | border-border versus border-control-border, primitive focus treatment |
| UI/display/mono | font-sans DM Sans / font-serif Instrument Serif / font-mono JetBrains Mono |
| Code block | font-mono, existing muted surface/border/radius, local overflow-x-auto and keyboard focus when needed |
| Composer L1j2DY | Existing Input/Textarea/Label, composite focus outline; controls bottom aligned; growth capped176px |
| Header iNUby, context VSZka, sidebar jn28o, FAB ycX9o | Existing Intelligence widgets/shared primitives; ToolCall HOxqy supplies generic query marker layout only |
| Spacing/radius | Existing semantic utilities;4/8/12/16/24/32/48 rhythm and current control/card/modal roles |
| Pending/loading/failure | Shared reduced-motion Skeleton, aria-busy/status, readable error copy; no animation as sole signal |

The feature's MessageItem owns typing hook; nested AnswerBlock/ResponseStatus are pure renderers. Root MentorContext owns session/stream/presentation continuity. Keep authenticated shell, underlying Learning navigation and current account UI.

Frames for quota, actions, memories, summaries, attachment analysis and dictation are excluded. Runtime captures belong under `apps/web/.playwright-cli/{screenshots,snapshots,logs}/`, recorded in Evaluation at implementation. Saving an image does not establish a visual pass; inspect captures against these references and adaptations.
