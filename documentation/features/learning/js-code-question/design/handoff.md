# JavaScript stdin question design handoff

The editable source is `design/shifu.pen`. Pencil nodes were inspected on
2026-09-26. Three 1440 × 900 frames are captured at 400 × 250; the expanded
1440 × 1400 full-page frame is captured at 400 × 389 (scale 0.27778). All four
PNGs were opened and inspected; none reported clipped descendants. The result
frames focus on the official result and omit the existing recommendation block;
runtime guidance stays available where Learning already supplies it. The existing
[choice Activity handoff](../../activity-choice-questions/design/handoff.md)
remains the visual authority for choice questions in a mixed Activity.

| Reference | Source/node | Route/surface/state | Viewport | Screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| JavaScript program | `design/shifu.pen` / `lZDH7`; 2026-09-26 user browser screenshot for adjustable panel layout | Activity question, editing and practice | 1440 × 900 default and resized; 390 × 844 mobile | [lZDH7.png](./references/lZDH7.png) | Progress, enunciado/arquivos tabs, fixed file tree, code editor, Terminal tab, xterm.js practice output, evaluation action; subtle keyboard accessible splitters on desktop | Edit initial files, supply stdin, automatic rerun, inspect stdout/stderr, resize desktop panels, request provisional evaluation | Example source/output are illustrative; saved Pencil frame defines default widths; resized and mobile states need fresh runtime screenshots; no Execute button and no additional-file creation | CA-01–CA-04/15, VM-01–VM-03 |
| Preliminary stdin result | `design/shifu.pen` / `O070h` | Question feedback, read-only stdin source and next action | 1440 × 900 | [O070h.png](./references/O070h.png) | Provisional question score, criterion weights/levels/fixed comments, file tree and read-only `main.js` | Advance after conclusive assessment; final question offers Activity submission | New frame copies the approved `MQVcK` hierarchy with stdin sample content. Score/comments are illustrative; runtime uses Curriculum rubric and Learning result | CA-05–CA-06, VM-04 |
| Completed mixed result, default | `design/shifu.pen` / `oPNtH` | Official Activity result after completion | 1440 × 900 | [oPNtH.png](./references/oPNtH.png) | Official score and Competency progress first; three ordered collapsed question summaries, including JavaScript stdin, each with position/type/score | Summaries start collapsed; each expands independently, so several may remain open; no terminal or practice output in official detail | Sample score and titles are illustrative; new recommendation design is deferred, while existing runtime guidance is preserved | CA-13/14, VM-05 |
| Completed mixed result, all questions open | `design/shifu.pen` / `Qxidv` | Expanded official Activity result; full-page scroll specimen | 1440 × 1400 | [Qxidv.png](./references/Qxidv.png) | Official summary followed by two choice answers/explanations and JavaScript rubric, read-only sent files and separate Concept evidence | All three independent disclosures open simultaneously; at 1440 × 900 the page scrolls to code details | Choice disclosure and scores are illustrative; new recommendation design is deferred, while existing runtime guidance is preserved. `PCnZO` governs choice-detail treatment | CA-09–CA-14, VM-05/07 |

## Implementation mapping

| Pencil role | Runtime mapping | Required behavior |
| --- | --- | --- |
| Shifu shell and progress | Existing Learning Activity route and shared layout | One question at a time; difficulty, position, total and progress remain visible in mixed Activities. |
| Enunciado/Arquivos sidebar | Learning question widget | Tabs form one contiguous panel with the editor; the file tree opens without creating or renaming files in this slice. |
| Editor | Learning code editor widget | Only Curriculum-declared initial files are editable. The selected file and unsent source stay in client state until final submission. |
| Terminal | xterm.js wrapper and browser WebContainer adapter | The Terminal tab is a real interactive terminal. The allowlisted JavaScript entrypoint runs with empty stdin on load and edits until input is supplied, so `console.log` output appears before first input while guidance still invites stdin. Later edits reuse the last input. Practice is optional for submission; there is no Execute button or unrestricted command line. |
| Assess/question result | Learning evaluation action and result widget | Freeze the assessed source for provisional feedback, display rubric decisions supplied by Learning, and advance sequentially. No provisional result becomes an official attempt. |
| Historical source | Learning attempt result widget | The sent files remain in a read-only tree/editor inside the expanded code question; the terminal is absent. |
| Question summaries | Learning attempt result widget | Official score/progress precede ordered question rows. All rows start collapsed, toggle independently with keyboard and announce their expanded state. Existing recommendation presentation remains outside this design slice. |

At 390 × 844, the same controls must be reachable by keyboard/touch in a
single-column flow: enunciado and file tree are collapsible, the editor remains
usable without horizontal page overflow, and the Terminal occupies its own
tab/panel rather than shrinking beside the editor. The desktop frames do not
define a separate mobile visual composition. A supplemental mobile Pencil frame
is recommended before implementation polish; the documented single-column rule
and a fresh 390 × 844 Playwright screenshot are the current validation target.
Use existing `documentation/design.md` tokens, shared controls, visible focus,
status text/announcements and pt-BR copy. The result screenshot is a layout
reference: Curriculum content and real Learning scores replace its sample
comments and values.
