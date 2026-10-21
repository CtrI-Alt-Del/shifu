# SHIFU-88 React activity design handoff

## Approved references

| Frame | Reference | Viewport | Required states and content |
| --- | --- | --- | --- |
| `ZWAmr` | [ZWAmr.png](./references/ZWAmr.png) | 1440×900 | Activity question 2 of 3, statement and public rubric, React editor with initial/additional files, locally saved status, preview and terminal. |
| `ZQZkP` | [ZQZkP.png](./references/ZQZkP.png) | 1440×900 | Authorized file creation affordance, curricular directory/extensions/count information, editor, preview and terminal. |

## Implementation guidance

- Preserve the existing Shifu Dojo dark theme and map colors, spacing, type, borders and controls to repository tokens and primitives. Do not invent a parallel system.
- Reuse existing activity shell, code editor/file tree, practice panel, question feedback and result patterns. The design shows a three-panel work surface and existing activity progression.
- Treat example question text, file names, 30/40/30 weights, and “1 de 3” file counts in frames as illustrative. Render all content and policy limits from the active curriculum question.
- The approved frames are desktop only. For mobile, adapt using existing Learning navigation and responsive panel patterns; keep statement/files, editor and preview reachable without page-level horizontal overflow. Do not represent this adaptation as a Pencil-approved mobile frame.
- Preliminary assessment and historical results follow current Learning components; the frames do not define a separate result visual treatment.

## Visual review states

1. `ZWAmr`: activity loaded, React editor, saved locally indicator, rubric, preview/terminal; compare panel hierarchy, token usage, text density and action hierarchy.
2. `ZQZkP`: authorized additional file creation and file explorer limits; compare permission affordance, directory/extensions/count, selected and newly created file states.
3. 390×844 adaptation: activity/editor controls remain reachable, panels reflow or switch using existing responsive patterns, keyboard focus is visible, and no horizontal page overflow appears.

Pencil source: `design/shifu.pen`; inspected through Pencil MCP only and left unchanged.
