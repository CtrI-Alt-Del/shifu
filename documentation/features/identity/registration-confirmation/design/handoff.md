# Registration-confirmation design handoff

The authoritative source is `design/shifu.pen`. The three nodes below were
opened, structurally inspected and exported at Pencil scale `1` on 2026-09-20.
All supplied frames are `1440 x 900`; Pencil reported no clipping or overflow.

| Reference | Pencil file/node | State | Viewport | Screenshot | Implementation surface | Visible inventory | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Registration | `design/shifu.pen` / `s4zUz` | Ready/default | 1440 x 900 | [s4zUz.png](./s4zUz.png) | `/register` | Dark structural grid, centered 440 px surface card, Shifu mark, name/e-mail/password fields, eight-character guidance, primary action and sign-in link | `CA-01` to `CA-04`, `VM-01`, `VM-02` |
| Pending confirmation | `design/shifu.pen` / `Dr6Wk` | Cooldown | 1440 x 900 | [Dr6Wk.png](./Dr6Wk.png) | `/pending-confirmation` | Dark grid, centered surface card, jade mail status, restriction copy, countdown action and sign-out action | `CA-03`, `CA-07`, `CA-10`, `CA-11`, `VM-04`, `VM-07` |
| Confirmation outcomes | `design/shifu.pen` / `lfk5T` | Activated, expired, used and invalid overview | 1440 x 900 | [lfk5T.png](./lfk5T.png) | `/confirm-email` | Four outcome cards with textual headings, icon reinforcement and one recovery/continuation action each | `CA-08`, `CA-09`, `VM-05`, `VM-06` |

## Derived states

The following states are approved derived states. They use the supplied card,
grid, typography and status language; they do not authorize feature-local
tokens or a light theme.

| Surface/state | Required behavior | Viewport/evidence |
| --- | --- | --- |
| Registration validation, duplicate, submitting, unavailable and focused | Preserve valid values, announce feedback, prevent duplicate submit and retain keyboard-visible focus. | 1440 x 900 and 375 x 812; capture during `VM-01` and `VM-02`. |
| Pending ready, delivery failure and polling refresh | Keep the restriction clear, use a generic 60-second local countdown, expose recoverable delivery state and refresh safely. | 1440 x 900 and 375 x 812; capture during `VM-04` and `VM-07`. |
| Confirmation individual outcomes and same-access continuation | Capture the token before URL cleanup; show the individual approved outcome and use `Continuar` only for a matching pending context. | 1440 x 900 and 375 x 812; capture during `VM-05` and `VM-06`. |
| Short mobile viewport | Top-align and scroll instead of clipping controls or recovery actions. | 375 x 667; capture during `VM-01`. |

Implementation uses existing Shifu tokens, Instrument Serif headings, DM Sans
controls, the dark-only grid background, 44 px mobile targets and the two-pixel
focus language from `documentation/design.md`. Status meaning remains textual
and icon-supported; motion respects `prefers-reduced-motion`.
