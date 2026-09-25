# Objective removal design handoff

The authoritative source is `design/shifu.pen`, node `kZHN8` ("confirmação da
remoção do Objetivo" per the Jira `SHIFU-67` traceability section). **No Pencil
MCP tool was available in the session that authored `spec.md` revision 1**, so
`kZHN8` has not been opened, screenshotted, or visually inspected. This is a
recorded gap accepted explicitly by the product owner during Spec
clarification, not a silent omission — see `spec.md` §1 ("Product decisions
and assumptions") and §3 ("Design Contract").

## Interim authority (until `kZHN8` is captured)

1. `documentation/design.md` §3.3 "Como resolver ação destrutiva" — the
   destructive control is never filled/solid: neutral surface, `--selo-text`
   label and border, always paired with an icon, and always lives inside a
   confirmation.
2. `documentation/design.md` §6.2 T14 "Remover Habilidade / Remover Objetivo"
   — two distinct destructive modals; the Objetivo variant "deixa claro que
   **todas** as experiências de Habilidade dele serão removidas." No typed
   confirmation is described for this modal (unlike T09's password-gated
   account-deletion modal), matching `RP-22`'s "a confirmação não exige
   digitação do nome do Objetivo."
3. `documentation/rules/ui-layer-rules.md` "Dialog header structure" — every
   application dialog, including destructive confirmations, uses a semantic
   icon tile at the left of the title/description block, an isolated
   top-right close action, and a header separator dividing header from body.

## Required before shipping this feature

1. Obtain Pencil access (MCP or the Pencil design skill), open
   `design/shifu.pen`, and load `kZHN8`'s editor state with schema.
2. Save one shared-workspace screenshot per required state (default,
   pending/loading if designed, error/failure if designed) under
   `design/references/`.
3. Visually inspect each screenshot (not only filename/OCR); record the exact
   visible copy, icon, button labels, and layout.
4. Reconcile against `ConfirmationDialog`'s implementation
   (`apps/web/src/ui/shared/widgets/components/confirmation-dialog`) and the
   copy used by `GoalDetailPlaceholderPage`. If the real node's copy, layout,
   or interaction differs materially from the interim authority above, update
   this handoff and amend `spec.md` (Section 8 of `create-spec-prompt.md`:
   material amendment) before treating those criteria as visually validated.
5. Replace this section's "not yet captured" status with the completed
   inventory table (see the format used by `../add-skill/design/handoff.md`)
   once screenshots exist.

## Status

`kZHN8`: **not yet captured**. No PNG references exist in `design/references/`
yet. `VM-01`/`VM-02` in `spec.md` §4 instruct comparing the implementation
against `kZHN8` once this capture is complete; until then, manual validation
compares against the interim authority listed above.
