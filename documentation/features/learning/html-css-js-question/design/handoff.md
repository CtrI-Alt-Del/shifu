# Design handoff — HTML/CSS/JavaScript Activity question

## Authority and references

The supplied `SHIFU-86-CONTEXTO.md` records that `design/shifu.pen` was inspected
through Pencil. This handoff preserves its findings without reading the encrypted
`.pen` file through filesystem tools.

- Canonical desktop frame: `Veyl9`, 1440×900, HTML/CSS/JavaScript editor and preview.
- Supporting files state: `EzCt3`, 1440×900, file list open.
- Reused references: `n7nYU` practice panel; `WFmlv` editor; `u6n3J` prompt/files panel.
- No approved mobile frame or HTML result frame exists. Reuse current responsive
  Activity and result patterns and report that adaptation as unapproved by Pencil.

## Required surfaces and states

1. Protected Activity page with header, difficulty, question position/progress
   and “Avaliar questão”.
2. Prompt/files side panel with curricular prompt and rubric criteria/weights.
3. Monaco editor and curricular file tabs. Read-only initial files remain visible.
   No enabled file-creation control.
4. Practice panel tabs “Prévia” and “Terminal”. Do not show “HTTP” or “Executar”.
5. Practice states: starting, updating, ready, unavailable/error. Text communicates
   state; preview failure leaves editing and evaluation available.
6. Draft states: saving, saved, failed. Unsaved response warns before leaving.
7. Preliminary feedback: exact evaluated snapshot read-only; criteria, weights,
   levels and fixed comments; inconclusive required criterion blocks advancement.
8. Historical result: pending, failed/recoverable and complete; response and rubric
   read-only, with no runtime started.

## Viewports and acceptance

- Desktop: 1440×900; compare the three-column hierarchy and panel proportions to
  `Veyl9`. The file panel should follow `EzCt3`.
- Mobile: 390×844; adapt using existing Web responsive patterns. Prompt, files,
  editor, preview and terminal remain reachable without page-level horizontal scroll.
- Keyboard: all controls reachable in logical order, visible focus, labeled tabs,
  files and actions. No essential status is conveyed only by color.
- Tokens: use current Web tokens and code font JetBrains Mono. Do not add a new
  palette, spacing scale, typography, radius or shadow system.
- Isolated preview: only HTTPS on an approved separate WebContainer origin, inside
  the existing scripts-only iframe sandbox; no app credentials or authenticated
  state.

## Accepted adaptations

- Mobile layout is an implementation adaptation because no Pencil mobile frame is
  available; it is not described as Pencil-approved.
- Result layout reuses existing historical-result patterns because no HTML result
  frame is available.
- Curricular file names, counts, criteria and weights are data-driven. Pencil's
  three-file example and 30/40/30 weights are not product constants.
