# Account menu and current-session logout design handoff

The canonical editable authority is `design/shifu.pen`. The three references below
were exported at Pencil scale `1` and visually inspected on 2026-09-24. The
Pencil layout inspection reported no clipping or overflow for the referenced
nodes.

| Reference | Pencil source/node | Route/surface/state | Viewport | Saved screenshot | Visible inventory | Interaction/state coverage | Ambiguities/exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Header component | `design/shifu.pen` / `h7fGzC` — `V2/Header` | Authenticated desktop header | 1440 x 64 | [h7fGzC.png](./references/h7fGzC.png) | Wordmark, primary navigation and 32 px account trigger | Account trigger opens the menu | The header component itself does not prescribe mobile composition | `CA-01`, `CA-02`, `VM-01` |
| Account menu component | `design/shifu.pen` / `x9zS2` — `V2/Menu/Conta` | Open authenticated account menu | 304 x 192 | [x9zS2.png](./references/x9zS2.png) | Display name, e-mail, divider, `Sua conta`, divider and `Sair` | Account summary and logout action | Jira requires `Sua conta` to be disabled and absent from sequential focus; remove its active affordance and chevron rather than treating the Pencil row as actionable | `CA-01` to `CA-05`, `VM-01`, `VM-02` |
| Complete desktop state | `design/shifu.pen` / `sFInu` — `10.5 Habilidade · menu da conta aberto` | Authenticated content with account menu open | 1440 x 900 | [sFInu.png](./references/sFInu.png) | Header trigger anchors the menu over the current protected screen; account menu keeps a compact 304 px surface | Open-state placement and visual hierarchy | The reference has placeholder identity values and no pending/error state; runtime data and derived states remain validation targets | `CA-01` to `CA-05`, `VM-01`, `VM-02` |

## Offline implementation authority

Apply `documentation/design.md` first for the dark-only Dojo editorial tokens,
typography, focus treatment, responsive breakpoints and accessibility. Reuse the
existing shared `Icon`, shadcn `Button`, `Anchor`, application shell, semantic
Tailwind tokens and `V2/Header`/`V2/Menu/Conta` hierarchy. Do not recreate a
Pencil component as a parallel token system.

The account menu uses `bg-card`, `border-border`, `text-foreground`,
`text-muted-foreground`, `text-selo-text`, `bg-muted`, `rounded-lg`/existing
control radii, and the existing visible focus language. The destructive-looking
`Sair` row remains textual and icon-supported rather than becoming a filled
primary action. `Sua conta` has disabled semantics, `aria-disabled='true'`, no
navigation target and no tab stop.

## Responsive and runtime states

| Concern | Required contract |
| --- | --- |
| Desktop | At 1440 x 900, the menu is right-aligned to the account trigger and overlays the protected content without clipping. |
| Mobile | At 390 x 844, the same trigger and menu remain reachable from the mobile header without colliding with its navigation control or the bottom navigation. The menu fits within viewport gutters and remains usable without horizontal scrolling. |
| Open/close | The trigger exposes expanded state. Escape and pointer interaction outside the menu close it and return focus to the trigger for Escape. |
| Logout pending | `Sair` changes to `Saindo...`, exposes progress, and prevents a concurrent sign-out request. |
| Logout failure | The menu remains available, the active session remains intact, and an announced, non-color-only recoverable message offers a retry. |
| Motion | Opening and progress motion must remain understandable with `prefers-reduced-motion`; motion is supplementary. |

## Supplemental coverage decision

No Pencil amendment is required. The approved Jira acceptance criteria override the
actionable-looking `Sua conta` row in `x9zS2`. Mobile, keyboard-focus, pending and
recoverable-failure variants are derived states and require fresh runtime screenshots
and Playwright inspection in evaluation rather than new static Pencil frames.
