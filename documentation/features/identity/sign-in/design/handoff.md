# Sign-in design handoff

The authoritative source is `design/shifu.pen`. Exports use Pencil scale `1`; all
eight listed nodes were opened and visually inspected on 2026-09-16. Every PNG is
non-empty and matches its declared viewport dimensions.

This artifact follows the repository-wide SDD `design/handoff.md` convention. It
supersedes the earlier feature-local `manifest.md` filename while preserving the
required reference inventory, node, state, viewport, implementation surface and
AC/MV mappings below and adding the offline implementation contract.

| Reference | Pencil file/node | State | Viewport | Screenshot | Implementation surface | Tokens/components | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Desktop default | `design/shifu.pen` / `a9R0Yh` | Ready for input | 1440 × 900 | [a9R0Yh.png](./a9R0Yh.png) | `/login`; sign-in form | `V2/GridBackground`, `V2/Input`, `V2/Button/Primary`, `V2/Button/Ghost`; `page`, `surface`, `raised`, `selo-*`, `text-*`, `radius-*` | `AC-01`, `MV-01`: compare the complete desktop route at 1440 × 900. |
| Pending confirmation destination | `design/shifu.pen` / `Dr6Wk` | Pending account after valid credentials | 1440 × 900 | [Dr6Wk.png](./Dr6Wk.png) | `/pending-confirmation`; adjacent SHIFU-61 surface | `V2/GridBackground`, outline and ghost actions; `jade-*`, `surface`, `text-*` | `AC-05`, `MV-05`: verify redirect and pending-flow handoff only; SHIFU-62 does not implement this page. |
| Mobile default | `design/shifu.pen` / `Yzifg` | Ready for input | 375 × 812 | [Yzifg.png](./Yzifg.png) | `/login`; responsive sign-in form | Desktop primitives retained; 335 px card, 24 px card padding, 20 px viewport gutters | `AC-01`, `MV-01`: compare the complete mobile route at 375 × 812. |
| Invalid credentials | `design/shifu.pen` / `K4sy9p` | Authentication rejected | 1440 × 900 | [K4sy9p.png](./K4sy9p.png) | `/login`; form-level credential error | V2 form primitives plus `circle-alert`; `selo-tint`, `selo-fill`, `selo-text` | `AC-03`, `MV-03`: email remains populated, password is empty, alert copy and placement match. |
| Infrastructure failure | `design/shifu.pen` / `JGwvz` | FastAPI or persistence unavailable | 1440 × 900 | [JGwvz.png](./JGwvz.png) | `/login`; recoverable form-level error | Same alert treatment as invalid credentials; both field values remain present | `AC-07`, `MV-03`: wrapped failure copy, retained fields, and recovery-ready form match. |
| Submitting | `design/shifu.pen` / `i7xhg` | Request in flight | 1440 × 900 | [i7xhg.png](./i7xhg.png) | `/login`; disabled form submission state | Dimmed V2 inputs; primary loading variant with `loader-circle` and `Entrando...` | `AC-06`, `MV-02`: fields and action are disabled, progress is visible, navigation links remain available. |
| Keyboard focus | `design/shifu.pen` / `IxLms` | Email field focused | 1440 × 900 | [IxLms.png](./IxLms.png) | `/login`; keyboard focus treatment | `V2/Input`; 2 px `selo-text` border and `selo-tint` outer focus treatment | `AC-02`, `MV-02`: keyboard traversal produces the visible ring without shifting layout. |
| Mobile invalid credentials | `design/shifu.pen` / `U0Meh0` | Authentication rejected | 375 × 812 | [U0Meh0.png](./U0Meh0.png) | `/login`; responsive form-level credential error | Mobile card and desktop error primitives; message remains single-line at 375 px | `AC-03`, `MV-03`: compare complete mobile error state and verify no clipping or horizontal overflow. |

## Offline implementation authority

This file is the implementation handoff for agents that cannot open Pencil. Apply
sources in this order:

1. `documentation/design.md` and
   `apps/web/src/ui/shared/styles/global.css` own Shifu semantic tokens, dark-only
   behavior, typography and focus language.
2. Existing widgets under `apps/web/src/ui/shared/widgets` and the shared shadcn
   primitives contracted by this Spec under `apps/web/src/ui/shadcn` own
   interaction, disabled, keyboard and motion behavior.
3. This handoff owns component selection, variants, layout recipes and the
   Pencil-to-Shifu mapping for sign-in.
4. The saved PNGs own visual comparison, content hierarchy and relative
   composition.
5. Raw Pencil values and measurements are evidence, not permission to add
   arbitrary Tailwind values, inline styles or parallel design tokens.

If an exact Pencil value has no implemented CSS token, use the semantic fallback
declared below or expose the already-authoritative token from
`documentation/design.md` through `global.css`. Do not invent a feature-local color.
Record any remaining mismatch in `evaluation.md`.

## Extracted token crosswalk

The following bindings were read from the referenced Pencil states and reconciled
with Shifu's canonical design system. Implementation uses the semantic Shifu column;
resolved values are included only for audit and screenshot comparison.

| Pencil binding/role | Resolved evidence | Shifu CSS token | Tailwind/component usage | Required role |
| --- | --- | --- | --- | --- |
| `$page` | `#0A0A0C` | `--background` | `bg-background` | Full viewport canvas. |
| `$surface` | `#161513` | `--card` | `bg-card` | Sign-in card surface. |
| `$raised` | `#1E1C18` | `--muted` | `bg-muted` | Input and subdued/loading surfaces. |
| `$divider` | `#FFFFFF14` | `--border` | `border-border` | Decorative card separation only. |
| `$control-border` | `#FFFFFF54` | `--control-border` | `border-control-border` through the shared input primitive | Active control boundary; do not substitute the decorative divider. |
| `$grid-line` | `#FFFFFF24` | Shared `SquareBackground` CSS | Existing `.square-background__cell` treatment | Decorative structural grid; `aria-hidden`. |
| `$text-primary` | `#F4F2EC` | `--foreground` | `text-foreground` | Heading, labels, entered values and primary copy. |
| `$text-muted` | `#9A958D` | `--muted-foreground` | `text-muted-foreground` | Supporting copy and placeholders. |
| `$text-secondary` | `#C4BFB6` | `--foreground` with existing subdued text treatment | Shared component typography | Secondary form copy and non-primary link context. |
| `$selo-tint` | `#3D1414` | `--accent` | `bg-accent` | Error alert surface and focus contrast support. |
| `$selo-fill` | `#DC2F2F` | `--primary` | `Button` default / `bg-primary` | The single primary action and Shifu seal mark. |
| `$selo-text` | `#F28B8B` | `--selo-text` | `text-selo-text`, `border-selo-text`, focus ring | Error copy/icon and keyboard focus; expose the canonical design token in `global.css`. |
| `$on-selo` | `#FFFFFF` | `--primary-foreground` | `text-primary-foreground` | Content on the primary action. |
| `$jade-text` | `#7BD3B6` | `--success` | `text-success` | Pending-confirmation destination only; adjacent `SHIFU-61` ownership. |
| `$font-serif` | Instrument Serif | `--font-serif` | `font-serif` | Wordmark and `Entrar` heading. |
| `$font-sans` | DM Sans | `--font-sans` | `font-sans` | Labels, inputs, actions, alerts and links. |

The product is dark-only. Do not derive or add a light theme from the PNGs.

## Typography recipe

| Role | Pencil evidence | Required implementation |
| --- | --- | --- |
| Shifu wordmark | Instrument Serif with red seal mark | `font-serif`, normal case and weight; the red mark uses `text-primary`. |
| Page title | Instrument Serif, short editorial heading | Semantic `h1` with `font-serif text-3xl font-normal text-foreground`. |
| Labels and values | DM Sans, compact but readable | Shared `Label`/`Input`; retain repository 15 px body baseline and visible labels. |
| Supporting copy and placeholders | DM Sans, subdued | `text-sm text-muted-foreground`; never reduce contrast to imitate a disabled state. |
| Primary action | DM Sans, semibold | Shared `Button`; preserve its accessible height and disabled semantics. |
| Navigation links | DM Sans, small/medium emphasis | Existing `Anchor`; textual label remains authoritative and focus-visible. |
| Alert copy | DM Sans, readable error emphasis | `text-sm text-selo-text`; icon is supplementary and the container uses `role="alert"`. |

Repository text sizing and accessibility take precedence over any smaller logical
Pencil label. Preserve hierarchy through family, role, weight and spacing rather
than undersized text.

## Reusable component mapping

| Pencil source/component | Extracted construction | Shifu implementation | Required configuration |
| --- | --- | --- | --- |
| `V2/GridBackground` | Full-viewport square grid with red proximity wash | Shared `SquareBackground` promoted from `AppLayout` | Fixed, `aria-hidden`, behind the card; preserve reduced-motion and non-pointer fallback. |
| Sign-in surface | 440 px dark card, 32 px desktop padding | Semantic `SignInPage` form container using Shifu surface tokens | `w-full max-w-[440px] bg-card`; 24 px mobile and 32 px desktop padding; no shadow. |
| `V2/Input` | Raised fill, visible border, label and focus treatment | Shared shadcn `Input` plus `Label` | `border-control-border bg-muted`; invalid authentication remains form-level rather than field-level. |
| Password input | Input plus trailing visibility action | `Input`, shared `Button` ghost/icon treatment and `Icon` | Toggle has an accessible name; password stays masked by default; `eye`/`eye-off` are decorative. |
| `V2/Button/Primary` | Red filled full-width action | Shared shadcn `Button` default variant | Full width; exact `Entrar`/`Entrando...` copy; native disabled state; one primary action. |
| `V2/Button/Ghost` | Text navigation action | Existing `Anchor` | Resolve `RouteName` through `ROUTES`; preserve visible focus and 44 px mobile target. |
| Form-level error | Red-tinted outlined callout with icon and copy | Local semantic alert inside `SignInPage` plus shared `Icon` | Between password and submit; `role="alert"`, programmatically focusable, exact copy, no toast. |
| Pending indicator | Circular progress icon and changed action label | Shared `Icon` using `loader-circle` inside `Button` | Spin only while pending; respect reduced motion; text remains authoritative. |
| Form behavior | Email/password validation and request lifecycle | TanStack Form in `useSignInPage`, `useSignInAction` and auth context | Rendering stays in the page; values, focus, duplicate-submit protection and navigation stay in hooks. |

The 440 px card width and 20 px viewport gutters are the only feature-specific
arbitrary layout values required by the approved frames. Colors, radii, focus,
spacing and feedback remain semantic.

## Surface implementation recipes

| Surface | Structure and components | Tokens/layout | States and accessibility |
| --- | --- | --- | --- |
| Sign-in page | `SquareBackground` → centered main region → `SignInPage` card → wordmark, `h1`, form and adjacent links | `min-h-dvh bg-background`; `max-w-[440px]`; 20 px viewport gutters; no authenticated chrome | Public route; landmark and heading remain available before interaction; short viewports top-align and scroll. |
| Default form | Visible labels, email input, password input/visibility action, primary submit, recovery and registration anchors | Card uses `bg-card`; controls use `bg-muted border-control-border`; vertical rhythm follows the reference | Semantic form order; native autocomplete; malformed transport shape is blocked without implying account existence. |
| Invalid credentials | Retained email, cleared password, focused form alert, enabled retry | `bg-accent border-selo-text text-selo-text`; `circle-alert` | One generic message for unknown, deleted, case-mismatched and wrong-password cases; alert is announced and focused. |
| Infrastructure/throttle failure | Form alert with preserved values and enabled retry | Same alert family; exact failure-specific text distinguishes state without a new visual language | Infrastructure preserves both values; throttling preserves both values and waits for provider window reset. |
| Submitting | Disabled fields/action, `loader-circle`, `Entrando...`; links remain active | Subdued shared disabled styles; no feature-specific opacity values | Exactly one request; progress remains textual; motion respects reduced motion. |
| Pending handoff | Successful pending result navigates to `/pending-confirmation` | Destination frame uses the same background/card family and jade confirmation status | `SHIFU-62` validates only redirect and context isolation; page/resend implementation belongs to `SHIFU-61`. |

## Icon mapping

Use the shared Shifu `Icon` widget and registered `IconName` values. Feature
widgets must not import `lucide-react`, author SVGs or use font icons.

| Intent | Pencil icon | Shifu `IconName` | Size/semantic contract |
| --- | --- | --- | --- |
| Show password | Eye | `eye` | 16–18 px; decorative inside a button named `Mostrar senha`. |
| Hide password | Eye-off | `eye-off` | 16–18 px; decorative inside a button named `Ocultar senha`. |
| Failure | Circle alert | `circle-alert` | 16 px; alert copy and `role="alert"` carry meaning. |
| Submitting | Loader circle | `loader-circle` | 16 px; pending text carries meaning; reduced motion disables rotation. |

## Responsive and state contract

| Concern | Wide reference | Required narrow/runtime behavior |
| --- | --- | --- |
| Page | 1440 × 900 centered card on structural grid | At 375 × 812 use 20 px gutters and a 335 px fluid card; no horizontal overflow. |
| Card | 440 px width and 32 px padding | `width: 100%`, maximum 440 px; 24 px padding on mobile. |
| Vertical fit | Complete card centered | When the card does not fit, top-align within a scrollable main region; never clip form controls or links. |
| Error copy | Desktop one/two-line variants | Wrap naturally; mobile invalid copy remains unclipped and all actions remain visible. |
| Focus | Email-focused frame at desktop | Apply the same focus language to password, visibility action, submit and links without layout shift. |
| Motion | Spinner/proximity enhancement implied | Respect `prefers-reduced-motion`; status remains understandable without animation. |
| Tablet interpolation | No dedicated Pencil frame | Interpolate using fixed max card width and viewport gutters; do not introduce a second layout. |

## Visual inventory and interpretation

| Reference | Route/surface/state | Viewport | Required visible inventory | Interaction/state coverage | Ambiguities or exclusions | Validation target |
| --- | --- | --- | --- | --- | --- | --- |
| Desktop default | `/login`, ready | 1440 × 900 | Full-page dark grid; centered 440 px surface card; Shifu wordmark; `Entrar` heading; labeled email and password fields; red primary action; recovery and registration links. | Default, empty, enabled form with masked password placeholder. | No remember-me control, social sign-in, account-lock notice, or authenticated navigation. | `AC-01`, `MV-01` |
| Pending confirmation destination | `/pending-confirmation`, pending | 1440 × 900 | Centered surface card; jade mail icon; confirmation heading and explanatory copy; resend cooldown action; `Sair` action. | Destination reached after valid pending-account credentials using the opaque pending-flow context. | Page behavior and resend lifecycle belong to SHIFU-61; this frame defines only SHIFU-62's redirect boundary. | `AC-05`, `MV-05` |
| Mobile default | `/login`, ready | 375 × 812 | Dark grid continues behind a single centered card; controls fill the card width; two navigation links remain on one row with touch-friendly padding. | Responsive default form and usable link/action layout. | No separate tablet frame is required; widths from 376 px through desktop interpolate by fixed maximum card width and viewport gutters. | `AC-01`, `MV-01` |
| Invalid credentials | `/login`, rejected | 1440 × 900 | Email value retained; empty password control; red-tinted outlined alert between password and action; `circle-alert` icon; exact generic copy. | Form-level `role="alert"`; focus moves to the alert in runtime; next password entry remains available. | The alert does not identify whether the email exists, is deleted, or has a wrong password. | `AC-03`, `MV-03` |
| Infrastructure failure | `/login`, recoverable failure | 1440 × 900 | Both submitted values retained; two-line red-tinted alert; enabled `Entrar` retry action and navigation links. | Form-level `role="alert"`; retry uses the preserved values. | The visual must not imply invalid credentials or account state. | `AC-07`, `MV-03` |
| Submitting | `/login`, submitting | 1440 × 900 | Email and password controls visibly dimmed; subdued primary action; progress indicator; `Entrando...`; recovery and registration links unchanged. | Duplicate submission is prevented while navigation links remain usable. | The static frame represents an indeterminate progress indicator; runtime motion must respect reduced-motion preferences. | `AC-06`, `MV-02` |
| Keyboard focus | `/login`, email focused | 1440 × 900 | Email control has a clearly visible pink-red 2 px focus boundary and outer contrast treatment; remaining controls retain default styling. | Representative keyboard-focus state; the same focus language applies to password, primary action, and links. | This frame does not prescribe browser caret appearance or focus order beyond the semantic form sequence. | `AC-02`, `MV-02` |
| Mobile invalid credentials | `/login`, rejected | 375 × 812 | Mobile card, retained email, empty password, single-line credential alert, full-width action, and both navigation links all remain visible without clipping. | Responsive error announcement and recovery at the narrow validation viewport. | Infrastructure and submitting mobile states derive from the same responsive card and their approved desktop treatments; they remain runtime validation targets rather than additional required frames. | `AC-03`, `MV-03` |

## Supplemental coverage decisions

| Proposed route/surface/state | Role/fixture and viewport | Why the supplied references are insufficient | Coverage | Decision |
| --- | --- | --- | --- | --- |
| Mobile submitting | Anonymous learner; 375 × 812 | The submitting reference is desktop-only. | `AC-02`, `AC-06`; `MV-02` | Recommended runtime screenshot; deferred to `evaluation.md` because the approved mobile card and desktop pending treatment fully define the derived state. |
| Mobile infrastructure failure | Anonymous learner; 375 × 812 | Only invalid credentials has a mobile error frame. | `AC-07`; `MV-03` | Recommended runtime screenshot; deferred to `evaluation.md` using the same responsive alert/card contract. |
| Throttled form | Anonymous learner after the eleventh request; 1440 × 900 | No Pencil frame has the throttle-specific copy. | `AC-08`; `MV-06` | Recommended runtime screenshot; approved assumption reuses the form-alert family with exact Spec copy. |
| Short mobile viewport | Anonymous learner; 375 × 667 | The supplied mobile frame is 812 px tall and does not prove vertical overflow behavior. | `AC-01`, `AC-02`; `MV-01` | Recommended runtime screenshot; deferred to `evaluation.md`; top alignment and scrolling are fixed by this handoff. |
| Tablet interpolation | Anonymous learner; 768 × 1024 | No tablet frame exists. | `AC-01`; `MV-01` | No additional design frame required; fixed maximum card width and viewport gutters define interpolation. |
| Protected-route rejection | Anonymous or stale authenticated session; 1440 × 900 | Static sign-in references cannot show server redirect timing or session deletion. | `AC-09`; `MV-07` | Network/URL/manual evidence only; no supplemental design frame required. |

No additional screenshot is required before implementation. Runtime-only caret
rendering, progress rotation, focus movement and assistive semantics are allowed
deviations when they preserve the captured geometry and honor reduced-motion
preferences.

## Layout inspection

Pencil structural inspection reported no clipping or overflow problems for
`a9R0Yh`, `Dr6Wk`, `Yzifg`, `K4sy9p`, `JGwvz`, `i7xhg`, `IxLms` or `U0Meh0`.
Visual inspection confirmed that all desktop cards fit 1440 × 900, both mobile
cards fit 375 × 812 without horizontal overflow, and the focus/error treatments
remain inside their control/card bounds. Implementation must not introduce page-
level clipping, horizontal overflow or a fixed-height card.
