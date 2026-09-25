# SHIFU-74 design handoff

The editable source is `design/shifu.pen`. Pencil MCP inspection and screenshots were
captured on 2026-09-22. The six Jira frames are references for individual question
and question-result states. `PCnZO`, `rf857`, and `k3bUS8` are the three approved
supplemental frames for the complete result and mobile layouts. The incorrect
single-choice frame `YDgNz` no longer contains the misleading protected-answer row.

Pencil `TakeScreenshot` returns a uniformly scaled PNG: desktop exports are
400 × 250 for a 1440 × 900 frame (scale `0.27778`), and mobile exports are
185 × 400 for a 390 × 844 frame (scale about `0.474`). The editable frame
dimensions, not these preview dimensions, are the implementation viewports.
Each PNG was opened and inspected after saving. All nine frames reported zero
clipped or overflowing descendants in Pencil's resolved-bounds inspection.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single question | `design/shifu.pen` / `o2q7H` | Activity, question 2 of 3 | 1440 × 900 | [o2q7H.png](./o2q7H.png) | Shifu shell, position, prompt/code, radio options, selected state, next action | One answer; sequential advance | Reference has a selected example, not every disabled/invalid state | `CA-01`, `CA-02`, `VM-01` |
| Multiple question | `design/shifu.pen` / `Cj8R7` | Activity, question 1 of 3 | 1440 × 900 | [Cj8R7.png](./Cj8R7.png) | Prompt/code, four checkbox options, two selected states, next action | Add/remove selections, advance | Selected red treatment is visual; checkbox state and text remain explicit | `CA-01`, `CA-02`, `VM-01` |
| Incorrect single | `design/shifu.pen` / `YDgNz` | Individual question detail within result | 1440 × 900 | [YDgNz.png](./YDgNz.png) | Zero score, chosen answer, conceptual explanation, progress, next action | Incorrect and protected answer | The protected-answer placeholder row was removed; correct option is absent | `CA-06`, `CA-07`, `VM-03` |
| Correct single | `design/shifu.pen` / `gftrs` | Individual question detail within result | 1440 × 900 | [gftrs.png](./gftrs.png) | Full question score, selected correct option, explanation, progress | Correct answer may be shown | Example progress numbers are illustrative, never the scoring rule | `CA-06`, `CA-08`, `VM-03` |
| Incorrect multiple | `design/shifu.pen` / `ad7p6` | Individual question detail within result | 1440 × 900 | [ad7p6.png](./ad7p6.png) | Zero score, selected/unselected states, conceptual explanation | Incorrect set with no unselected correct-option disclosure | Render only selected options and safe feedback when disclosure is barred | `CA-06`, `CA-07`, `VM-03` |
| Correct multiple | `design/shifu.pen` / `ntBNV` | Individual question detail within result | 1440 × 900 | [ntBNV.png](./ntBNV.png) | Full score, selected correct set, explanation | Exact-set success | Example progress numbers are illustrative | `CA-06`, `CA-08`, `VM-03` |
| Complete desktop result | `design/shifu.pen` / `PCnZO` | One Activity result containing three question details | 1440 × 900 | [PCnZO.png](./PCnZO.png) | Final weighted score, progress change, three detailed cards, feedback, next action | Mixed correct/incorrect result on one page | Example weights 40/30/30 and score 70 are illustrative; actual values come from Curriculum | `CA-05`–`CA-08`, `VM-03` |
| Mobile multiple question | `design/shifu.pen` / `rf857` | Activity, multiple selection | 390 × 844 | [rf857.png](./rf857.png) | Compact shell, prompt/code, four 44 px choice rows, 44 px next action, bottom navigation | Multi-select, mobile touch and keyboard states | No separate mobile single-choice frame; reuse this hierarchy with radio behavior | `CA-01`, `CA-02`, `CA-10`, `VM-02` |
| Complete mobile result | `design/shifu.pen` / `k3bUS8` | One Activity result containing three question details | 390 × 844 | [k3bUS8.png](./k3bUS8.png) | Final score, progress, three detail cards, explanation, next action, bottom navigation | Full result in one vertical flow | Four or five questions extend the scroll; never clip or split into separate detail routes | `CA-05`–`CA-10`, `VM-04` |

## Implementation authority

1. `documentation/design.md` and existing `apps/web/src/ui/shared/styles/global.css`
   own Shifu colors, typography, spacing, surfaces, radii, focus and dark-only shell.
2. Existing shared widgets/primitives own buttons, progress semantics and icons.
   The Spec adds shared radio-group and checkbox primitives under
   `apps/web/src/ui/shadcn`; they own selection, labels, focus and keyboard behavior.
3. This handoff owns the Activity/question/result hierarchy and the approved
   interpretation of the Pencil frames. The saved PNGs are visual comparison
   references; raw Pencil values do not authorize parallel CSS tokens.

| Pencil role | Runtime mapping | Required behavior |
| --- | --- | --- |
| Shared desktop/mobile shell | Existing `AppLayout`, header, bottom navigation and shared `Icon` | Do not recreate the shell inside the Activity widget. |
| Question stage | Learning Activity page widget with one question child | Show position and total, difficulty, prompt and optional code; follow Curriculum order. |
| Single/multiple choice rows | New shared radio/checkbox primitives inside Learning question widget | One selection for single choice; one or more removable selections for multiple choice; visible focus and 44 px mobile targets. |
| Submit/advance action | Shared `Button` | Advance only after a valid response; after the last question, submit one complete attempt. |
| Final score and progress | Learning result page widget | Distinguish Activity score, Competency progress and status; use unrounded values for domain decisions. |
| Per-question cards | Result detail widgets | Show submitted selection, score and outcome; use the safe outcome-specific explanation; do not infer or render hidden correct options. |
| Pending/failure | Existing Pencil Skill states `obhHC`, `fYHyi`, `vlvkI` as adjacent state references | Keep pending, failed/manual retry, and same-Skill pause understandable with text and live status. |

## Responsive, access and allowed variation

At 1440 × 900, keep the question/result column centered inside the existing shell.
At 390 × 844, stack it above bottom navigation with no horizontal overflow or
obstructed action. Longer prompts and four or five result cards scroll naturally;
the frame height is a viewport, not a maximum document height. Interactive mobile
targets are at least 44 px. Status, correction, score and progress cannot rely on
color alone. Use semantic groups and labels, visible focus, keyboard selection,
announced pending/failure/result changes, and reduced-motion-safe loading.

The displayed 70-point complete-result example has two correct question results
weighted 40% and 30%. Its `68 → 69` progress example is illustrative; RP-15
recomputation can also lower progress. Runtime copy may wrap with real Curriculum
content. Static Pencil screenshots do not specify server timing, polling, focus
placement, or a history page. Fresh Playwright CLI screenshots at both viewports
must compare the implemented states to this bundle.
