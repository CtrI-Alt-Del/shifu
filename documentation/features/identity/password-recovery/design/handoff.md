# Password-recovery design handoff

The authoritative source is `design/shifu.pen`. The three nodes below were
opened, structurally inspected and exported at Pencil scale `1` on 2026-09-25.
All supplied frames are `1440 x 900`; Pencil reported no clipping or overflow.

| Reference | Pencil file/node | State | Viewport | Screenshot | Implementation surface | Visible inventory | Scope |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Recovery request | `design/shifu.pen` / `CGmXc` | Default request form | 1440 x 900 | [CGmXc.png](./CGmXc.png) | `/forgot-password` | Dark structural grid, centered public card, Shifu mark, e-mail field, primary action and entry navigation | Implementation reference only |
| Password reset | `design/shifu.pen` / `VcFmX` | Valid reset form and success | 1440 x 900 | [VcFmX.png](./VcFmX.png) | `/reset-password` | Dark structural grid, centered public card, password and confirmation fields, primary action and sign-in continuation | Implementation reference only |
| Reset-link outcomes | `design/shifu.pen` / `lfk5T` | Expired, used and invalid overview | 1440 x 900 | [lfk5T.png](./lfk5T.png) | `/reset-password` | Textual outcome cards, icon reinforcement and one recovery action for each state | Implementation reference only |

## Derived states

The following states are approved derived states. They use the supplied card,
grid, typography and status language; they do not authorize feature-local

| Surface/state | Required behavior | Runtime coverage |
| --- | --- | --- |
| Recovery request validation, submitting, accepted, cooldown, delivery issue and retry | Preserve valid e-mail input on validation failure, announce generic feedback, prevent duplicate submission and never reveal eligibility. | Widget and route suites. |
| Reset validation, submitting, success and pending-confirmation explanation | Capture the token before URL cleanup, preserve recoverable fields, announce feedback and route to sign-in only after successful reset. | Widget and route suites. |
| Reset expired, used, invalid and unavailable outcomes | Keep the outcome generic, focus the textual explanation and provide the approved sign-in or new-request action. | Widget and route suites. |
| Short mobile viewport | Top-align and scroll instead of clipping inputs, actions or recovery paths. | Narrow-viewport route coverage. |

Implementation uses existing Shifu tokens, Instrument Serif headings, DM Sans
controls, the dark-only grid background, 44 px mobile targets and the two-pixel
focus language from `documentation/design.md`. Status meaning remains textual
and icon-supported; motion respects `prefers-reduced-motion`.
