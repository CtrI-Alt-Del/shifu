---
title: Preferência de aparência da conta
status: ready
revision: 2
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-119
scope:
  - identity
  - web shared theme
last_updated_at: 2026-11-21
---

# Objective

The account gains an appearance preference with three values: Escuro, Claro and
Sistema, starting as Sistema. Identity owns and exposes the value beside the time
zone. Minha conta > Perfil lets an active account change it, saved by the same
button as name and time zone and without the current password. Every protected
page renders the account's theme on first paint, applies a saved change without a
page reload, and with Sistema follows the device preference, including changes
during the session.

Current behavior: the web application renders only the dark theme. `global.css`
declares `color-scheme: dark` and dark token values, several widgets use fixed
white/black translucent colors, and Identity has no appearance concept.

Mode: `complete`. The delivery adds a migration, changes public REST contracts and
the trusted session, and introduces an application-wide theme.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Identity persistence (active account) | `appearance` on the account, default `system`, existing rows backfilled to `system`; validation; read/write only by the active account with a valid access | Appearance per device/session, schedules, extra themes |
| Identity exposure | `appearance` in `GET/PATCH /identity/accounts/me` and `GET /identity/session` | A new cross-module provider port: no other module consumes appearance yet |
| Perfil form | "Aparência" field after "Fuso horário", Escuro/Claro/Sistema, saved with the form, no current password | Any other Minha conta tab |
| Theme application, protected routes | Account theme on first server render, immediate after save, Sistema follows the device live | Theme on public routes: sign-in, registration, password recovery and reset, e-mail confirmation, pending confirmation and privacy remain dark (decision Q1). No public landing route exists today: `/` is the protected dashboard and redirects visitors to sign-in |
| Light token values | `documentation/design.md` §3.2 "Modo claro", same roles as dark | Redesign of screens beyond Perfil |
| Fixed colors | Every reachable fixed white/black translucent or fixed dark color that breaks in light becomes a token (decision Q3) | Monaco editor and xterm terminal stay dark code surfaces; HTML/React preview frames stay white; dialog scrims and white text on filled danger/primary stay fixed; unreachable `add-skill-catalog-section` tree |
| Product authority | Read-only use of PRD v6 | Any Jira or Confluence write |

RP coverage: RP-06 partial (appearance full; name, e-mail and time zone already
delivered and unchanged). RP-07 and RP-10 support the slice. No JN covers
appearance; JN-06 (Minha conta) supplies journey context.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-06, RP-07 | Every account has exactly one appearance in {`dark`, `light`, `system`}. New accounts start as `system`; existing accounts read as `system` after migration. Identity is the only source of truth. |
| RF-02 | RP-06, RP-07 | Only an active account with a valid access reads or changes its own appearance through the existing profile endpoints. Pending, deleted or stale-access sessions are rejected as today, with no write. |
| RF-03 | RP-06 | The profile update requires `appearance` together with `display_name` and `time_zone`. An unknown value is rejected with `invalid_appearance`, nothing is persisted. Changing appearance never requires the current password and never changes e-mail, ownership or other fields beyond the submitted profile values. |
| RF-04 | RP-06, RP-07 | `GET /identity/accounts/me`, `PATCH /identity/accounts/me` and `GET /identity/session` return the current `appearance`. |
| RF-05 | RP-06, RP-10, JN-06 | Perfil shows "Aparência" immediately after "Fuso horário" with options Escuro, Claro and Sistema in pt-BR, preselected with the saved value; it is keyboard-operable, labeled, disabled while saving, and its help text states the meaning of the selection in words (Sistema: follows the device). |
| RF-06 | RP-06 | After a successful save the new theme applies without a page reload. A failed save keeps the current theme and the draft values and shows an accessible recoverable error. |
| RF-07 | RP-06 | Every protected page is rendered by the server with the account's theme, so a new access on any device shows the saved theme on first paint. If Identity is unavailable while resolving the session, the theme falls back to `system`. |
| RF-08 | RP-06 | With `system`, the theme follows the device's `prefers-color-scheme`, including a change during the session, without reload or extra requests. |
| RF-09 | Q1 decision; RP-12 "identidade visual segue o sistema de design" | Public routes always render dark, store nothing about the visitor and ignore the device preference. |
| RF-10 | RP-10; design.md §3.2, §8 | In light, every active text token keeps AA contrast, `--control-border` keeps 3:1, the three hues keep their roles, and `selo-fill`, `danger`, `jade-fill` and `latao-fill` keep their dark values. Toasts follow the active theme. Reachable shared primitives, the app shell and widgets with fixed translucent white/black or fixed dark backgrounds render with tokens in both themes. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | A new registration | The account is created | Its appearance is `system` | CI-03 |
| CA-02 | RF-01 | An account row existing before the migration | Alembic upgrades to head | The row reads `system`; the column rejects values outside the three; downgrade removes the column | CI-06 |
| CA-03 | RF-02, RF-03, RF-04 | An active account with a valid access | It PATCHes name, time zone and `appearance: light` | 200 with `appearance: light`; the value is persisted; e-mail and status unchanged; no password asked | CI-01, CI-04 |
| CA-04 | RF-03 | An active account | It PATCHes `appearance: sepia`, or omits `appearance` | 400 `invalid_appearance` for the unknown value and a request-validation error for the missing field; nothing persisted | CI-01, CI-04 |
| CA-05 | RF-02 | A pending, deleted or stale-access session | It reads or PATCHes the profile | Rejected as today; no write | CI-01, CI-02, CI-04 |
| CA-06 | RF-04 | An account with `dark` | It calls `GET /identity/accounts/me` and `GET /identity/session` | Both return `appearance: dark` | CI-02, CI-05 |
| CA-07 | RF-03, RF-04 | The BFF profile handler with real services | A signed-in account posts a profile with an appearance, then an unknown or missing one | The valid value persists and returns in camelCase; the unknown or missing value is rejected with 400 by the BFF's strict body validation before reaching Identity, with nothing persisted (Identity's own `invalid_appearance` is proved by CI-04) | CI-12 |
| CA-08 | RF-05 | Perfil loaded with `dark` | The form renders | "Aparência" follows "Fuso horário", shows "Escuro" in the closed control, lists Escuro, Claro and Sistema, and its help text describes the selection | CI-07, CI-10, VM-01, VM-03, VM-04 |
| CA-09 | RF-05, RF-06 | Perfil in each of the three values | The user selects another value by keyboard and saves | The PATCH body carries the canonical value; the field is disabled while pending; success is announced as status; `<html data-theme>` changes without reload | CI-07, CI-10, VM-01, VM-02 |
| CA-10 | RF-06 | Perfil with a changed appearance | The save fails (server error or `invalid_appearance`) | An alert explains the failure, the field keeps the draft, the field error is shown for `invalid_appearance`, `data-theme` is unchanged; a retry can succeed | CI-07, CI-10 |
| CA-11 | RF-07 | The dashboard `/` and a `requireAuthMiddleware` route for an account with `light` | The server renders each page, and the browser loads each route | The HTML response already carries `data-theme="light"` (VM-01); client route loads apply the middleware result (CI-11); without an appearance in the account context the theme is `system` (CI-08) | CI-08, CI-11, VM-01 |
| CA-12 | RF-08 | An account with `system` | The device preference is light, then switches to dark during the session | The light tokens apply, then the dark tokens apply, without reload or request | CI-11, VM-01 |
| CA-13 | RF-09 | An account with `light` or a device preferring light | A public route renders | `data-theme="dark"` and dark tokens | CI-08, CI-11 |
| CA-14 | RF-10 | Light theme on Perfil and the shell | Text, control borders and toasts are measured | Text pairs ≥ 4.5:1, control border ≥ 3:1, fills unchanged, toast follows the theme | CI-08, VM-05 |
| CA-15 | RF-10 | Light theme | Each widget in the fixed-color inventory (Technical Contract) renders hover/border/background states | No fixed white/black translucent class or fixed dark hex remains in the listed files except the accepted exceptions | CI-14, VM-05 |

## Design Contract

Visual source: the Shifu file in Penpot, read only through the Penpot MCP. The
task cites `shifu.fig`; `AGENTS.md` makes Penpot the current source and
`shifu.fig` historical, so `shifu.fig` is not used for validation.

**Visual assumption (accepted by the user on 2026-11-21).** No Penpot file or
Penpot MCP is available to this delivery, so the boards below were not inspected. Until they are, the
contract assumes: the Aparência field reuses the Perfil time-zone `Select`
composition (label, 52 px control, help text below, `text-xs` muted help, field
error in `text-selo-text`); light values come from `design.md` §3.2. The user
accepted this assumption explicitly; VM-03 and VM-04 stay Blocked and no visual
match with the design is claimed.

| Surface / route | State / viewport | Penpot page / board / components | CA / Visual check | Allowed deviations |
| --- | --- | --- | --- | --- |
| Perfil `/account/profile` | Dark, saved value, 1440 × 900 | "Sua conta / Perfil" desktop (to verify); Select, Button | CA-08 / VM-03 | Reminder and privacy cards outside this change render as today |
| Perfil `/account/profile` | Light, after save, 1440 × 900 | "Sua conta / Perfil" desktop with the "Modo claro" values (to verify) | CA-09, CA-14 / VM-03 | Same |
| Perfil `/account/profile` | Dark and light, 390 × 844 | "Sua conta / Perfil" mobile (to verify) | CA-08, CA-14 / VM-04 | Same |
| App shell on Perfil | Light, desktop and mobile | Design System page, "Modo claro" section (to verify) | CA-14, CA-15 / VM-05 | Code editor and terminal stay dark |

Token mapping for touched widgets (source: `apps/web/src/ui/shared/styles/global.css`):

- surfaces: `bg-background` (`--background` = page), `bg-card` (surface), `bg-muted` (raised, also the hover state per design.md §3.2), `bg-surface-alt`;
- text: `text-foreground`, `text-secondary-foreground`, `text-muted-foreground`, `text-selo-text`, `text-jade-text`;
- borders: `border-border` (divider), `border-control-border` (controls), new `border-glass-border`;
- focus: the existing 2 px `--selo-text` ring with 2 px offset, unchanged;
- primitives: `Select` and `Button` (`primary`, `ghost`, `outline`) variants, unchanged API.

Preserved UI: Perfil reminders card, privacy card, security, deletion and AI-usage
tabs, and all public pages, beyond receiving token values.

# Technical Contract

## Architecture Mapping

Owner: Identity (server and web Perfil) plus the web shared theme. Rules:
[Python Conventions](../../../rules/python-conventions-rules.md),
[Core Domain](../../../rules/core-layer-rules.md),
[Use Case Testing](../../../rules/use-case-testing-rules.md),
[REST](../../../rules/rest-layer-rules.md),
[Controller Testing](../../../rules/controllers-testing-rules.md),
[Database](../../../rules/database-layer-rules.md),
[Provider Layer](../../../rules/provision-layer-rules.md),
[TypeScript Conventions](../../../rules/typescript-conventions-rules.md),
[UI Layer](../../../rules/ui-layer-rules.md),
[Web App Routing](../../../rules/web-app-routing-rules.md),
[Widget Testing](../../../rules/widget-testing-rules.md),
[Server Application](../../../rules/server-app-layer-rules.md) (shared error boundary),
[Commit](../../../rules/commit-rules.md) at commit time.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Core enum | `AccountAppearance` in `apps/server/src/shifu/identity/core/domain/enums/account_appearance.py` | `StrEnum` with `DARK='dark'`, `LIGHT='light'`, `SYSTEM='system'`; re-exported from `enums/__init__.py` |
| Create | Core errors | `InvalidAppearanceError` in `identity/core/domain/errors/invalid_appearance_error.py`, re-exported from `errors/__init__.py` | `ValidationError` subclass like `InvalidTimeZoneError`, `message: str = 'Selecione uma aparência válida.'` |
| Modify | Core entity | `Account` in `identity/core/domain/entities/account.py` | Field `appearance: AccountAppearance = AccountAppearance.SYSTEM` and the same keyword in `create`; registration keeps the default |
| Modify | Core structures | `AccountProfile`, `AccountProfileUpdate` | `AccountProfile.appearance: AccountAppearance`; `AccountProfileUpdate.appearance: str`, checked in `__post_init__` against `AccountAppearance` values and raising `InvalidAppearanceError`, never retyped (same pattern as `time_zone`) |
| Modify | Core use cases | `GetAccountProfileUseCase`, `UpdateAccountProfileUseCase` | Return `appearance`; update assigns `AccountAppearance(update.appearance)` in the same transaction as name and time zone, after the unchanged access check |
| Keep | Shared structure / provider | `AuthenticatedUser`, `JwksJwtAuthenticationProvider` | Unchanged. Appearance is an Identity preference no other module consumes, so it stays out of the cross-module auth contract |
| Modify | Database model / mapper | `AccountModel`, `AccountMapper` | `appearance: Mapped[str] = mapped_column(String(16), nullable=False, server_default='system')` with `CheckConstraint("appearance IN ('dark', 'light', 'system')", name='ck_identity_accounts_appearance')`; mapper converts with `AccountAppearance(...)` / `.value` |
| Create | Migration | `apps/server/migrations/versions/<revision>_add_account_appearance.py` | Generated with `DATABASE_URL=<disposable database at the current head, prepared as in CI-06> uv run alembic revision --autogenerate -m "add account appearance"` (never against the shared development database), then reviewed: add column NOT NULL with server default `'system'` (backfills existing rows). Autogenerate does not emit a CHECK constraint on an existing table, so `ck_identity_accounts_appearance` is added by hand in `upgrade` and dropped before the column in `downgrade`. File name and revision come from Alembic |
| Modify | REST controllers | `get_account_profile_controller.py`, `update_account_profile_controller.py`, `get_current_session_controller.py` | Profile responses add `appearance: AccountAppearance` (same typing as `status: AccountStatus`); PATCH `Request` adds required `appearance: str` (strict, extra forbidden) passed to `AccountProfileUpdate`. The session controller additionally depends on `IdentityPipe.get_database` and builds its response (`account_id`, `display_name`, `time_zone`, `appearance: AccountAppearance`) from `GetAccountProfileUseCase(database).execute(user)`, which applies the same active-access check the authentication provider already passed; cost is one extra primary-key read per session call |
| Modify | Error handler | `AppErrorHandler.handle_validation_error` in `rest/handlers/app_error_handler.py` | Maps `InvalidAppearanceError` to code `invalid_appearance` on account paths; registration unchanged |
| Modify | API example | `apps/server/rest-client/identity/identity.rest` | PATCH example body includes `"appearance": "system"` |
| Modify | Faker | `AccountFaker` | Accepts `appearance` override, default `AccountAppearance.SYSTEM` |
| Create | Web core contract | `apps/web/src/core/identity/account-appearance.ts` | `ACCOUNT_APPEARANCES` and `AccountAppearance` |
| Modify | Web core error | `AuthErrorOptions.field` in `core/errors/auth-error.ts` | Adds `'appearance'` |
| Modify | Web REST service | `IdentityService` in `rest/services/identity-service.ts` | `IdentityProfile.appearance`, `CurrentIdentitySession.appearance`, `updateAccountProfile` input `appearance` sent as `appearance` |
| Modify | Web provision (server) | `better-auth-provider.ts` | `ServerAuthenticatedAccess.appearance` (fallback `'system'` on Identity unavailability); `LayoutAccount.appearance`; `/account/profile` body `appearance: z.enum(ACCOUNT_APPEARANCES)`; `toAccountProfile` parses and returns `appearance`; `invalid_appearance` handled like other field codes |
| Modify | Web provision (browser) | `cookie-session-auth-provider.ts` | `AccountProfile.appearance`, `UpdateAccountProfileInput.appearance`, response validation, `invalid_appearance → 'appearance'` field mapping |
| Modify | Route middleware | `middlewares/require-auth-middleware.ts`, `middlewares/enter-main-page-middleware.ts` | Both return `appearance` in `LayoutAccount` (the second serves the protected dashboard `/`) |
| Modify | Root layout | `ui/shared/widgets/layouts/root-layout/{index.tsx,use-root-layout.ts}` | Hook returns `theme: AccountAppearance` (`'dark'` on public routes, `account.appearance` on protected routes, `'system'` when absent); `<html lang='pt-BR' data-theme={theme}>`; `<Toaster theme={theme} />` |
| Modify | Toaster primitive | `ui/shadcn/sonner.tsx` | Removes the fixed `theme='dark'`; takes `theme` from props (Sonner accepts `dark`, `light`, `system`) |
| Modify | Global styles | `ui/shared/styles/global.css` | Each themed token holds its light and dark values (CSS `light-dark()`); `color-scheme` is `dark` by default, `light` for `data-theme='light'` and `light dark` for `data-theme='system'`, so Sistema follows `prefers-color-scheme`; new `--glass-border` token exposed as `--color-glass-border`; `--success` and `--accent` get light values (jade-text and selo-tint light) |
| Modify | Profile form | `profile-form/{index.tsx,use-profile-form.ts}` | Appearance field, schema, error and reset; see UI composition |
| Modify | Shared primitives and shell | `ui/shadcn/button.tsx`; `app-layout/{navigation,mobile-bottom-navigation,desktop-header,account-menu}/index.tsx`; `ui/shared/widgets/components/confirmation-dialog/index.tsx` | `hover:bg-white/5 → hover:bg-muted`; active-state `bg-white/5 → bg-muted`; `border-white/10 → border-glass-border` |
| Modify | Feature widgets | Gamification: `streak-reminder-invite`, `gamification-overview-page/achievements-summary-card`. Intelligence: `mentor-action-card`, `mentor-chat/{conversation/composer, conversation/memory-change-marker, conversation/summary-marker/summary-dialog, header, rename-session-dialog}`, `layouts/planning-intent-composer`, `memories-page/{memory-details/memory-origin-list, memory-removed-notice}`, `planner-page/planning-proposal-review` and its `restart-planning-dialog` | `bg-white/5` and `hover:bg-white/5 → *bg-muted`; `border-white/16! bg-[#0f0f10]! → border-control-border! bg-background!` |
| Modify | Feature stylesheet | `ui/intelligence/widgets/pages/planner-page/planner-page.css` | `#ffffff → var(--primary-foreground)` (same value, token-owned) |
| Keep (accepted) | Learning / scrims | `code-editor` Monaco theme, `code-terminal` xterm theme, preview `bg-white` in `react-question`, `html-css-js-question`, `react-fastify-question/preview-panel`, `bg-black/50` in `shadcn/dialog.tsx` and `alert-dialog.tsx`, `sm:bg-black/55` in `mentor-fab`, `text-white` on `bg-danger` | Decision Q3: code surfaces stay dark; previews imitate a browser; scrims and text on fills are valid in both themes |
| Keep (out of reach) | Learning | `add-skill-catalog-section`, `skill-catalog-view`, `add-skill-foundations-dialog`, `skill-foundation-row` | Not rendered by any route; recorded as a known deviation, not changed |

Expected file tree:

```text
apps/server/
├── migrations/versions/<alembic revision>_add_account_appearance.py           [N] generated
├── rest-client/identity/identity.rest                                         [M]
├── src/shifu/
│   ├── fakers/identity/entities/account_faker.py                              [M]
│   ├── identity/
│   │   ├── core/domain/
│   │   │   ├── entities/account.py                                            [M]
│   │   │   ├── enums/{__init__.py [M], account_appearance.py [N]}
│   │   │   ├── errors/{__init__.py [M], invalid_appearance_error.py [N]}
│   │   │   └── structures/{account_profile.py, account_profile_update.py}     [M]
│   │   ├── core/use_cases/{get_account_profile_use_case.py, update_account_profile_use_case.py} [M]
│   │   ├── database/sqlalchemy/{models/account_model.py, mappers/account_mapper.py} [M]
│   │   └── rest/controllers/
│   │       ├── get_account_profile_controller.py                              [M]
│   │       ├── get_current_session_controller.py                              [M]
│   │       └── update_account_profile_controller.py                           [M]
│   └── rest/handlers/app_error_handler.py                                     [M]
└── tests/identity/
    ├── core/use_cases/
    │   ├── test_get_account_profile_use_case.py                               [M]
    │   ├── test_register_account_use_case.py                                  [M]
    │   └── test_update_account_profile_use_case.py                            [M]
    └── server/controllers/
        ├── test_get_account_profile_controller.py                             [M]
        ├── test_get_current_session_controller.py                             [M]
        └── test_update_account_profile_controller.py                          [M]
apps/web/
├── src/
│   ├── core/errors/auth-error.ts                                              [M]
│   ├── core/identity/account-appearance.ts                                    [N]
│   ├── middlewares/{require-auth-middleware.ts, enter-main-page-middleware.ts} [M]
│   ├── provision/auth/
│   │   ├── better-auth/better-auth-provider.ts                                [M]
│   │   └── cookie-session-auth-provider.ts                                    [M]
│   ├── rest/services/identity-service.ts                                      [M]
│   └── ui/
│       ├── shadcn/{button.tsx, sonner.tsx}                                    [M]
│       ├── shared/styles/global.css                                           [M]
│       ├── shared/widgets/components/confirmation-dialog/index.tsx            [M]
│       ├── shared/widgets/layouts/
│       │   ├── root-layout/
│       │   │   ├── index.tsx                                                  [M]
│       │   │   ├── use-root-layout.ts                                         [M]
│       │   │   └── tests/{root-layout.test.tsx, use-root-layout.test.ts}      [M]
│       │   └── app-layout/{navigation, mobile-bottom-navigation, desktop-header, account-menu}/index.tsx [M]
│       ├── identity/widgets/pages/account-profile-page/profile-form/
│       │   ├── index.tsx                                                      [M]
│       │   ├── use-profile-form.ts                                            [M]
│       │   ├── use-update-account-profile-action.ts                           [M] refresh warning copy only
│       │   └── tests/{profile-form.test.tsx, use-profile-form.test.ts}        [M]
│       ├── shared/contexts/auth-context/tests/use-auth-context-provider.test.ts [M] conditional: only if fixtures need appearance
│       ├── gamification/widgets/
│       │   ├── components/streak-reminder-invite/index.tsx                    [M]
│       │   └── pages/gamification-overview-page/achievements-summary-card/index.tsx [M]
│       └── intelligence/widgets/
│           ├── components/mentor-action-card/index.tsx                        [M]
│           ├── components/mentor-chat/conversation/composer/index.tsx         [M]
│           ├── components/mentor-chat/conversation/memory-change-marker/index.tsx [M]
│           ├── components/mentor-chat/conversation/summary-marker/summary-dialog/index.tsx [M]
│           ├── components/mentor-chat/header/index.tsx                        [M]
│           ├── components/mentor-chat/rename-session-dialog/index.tsx         [M]
│           ├── layouts/planning-intent-composer/index.tsx                     [M]
│           ├── pages/memories-page/memory-details/memory-origin-list/index.tsx [M]
│           ├── pages/memories-page/memory-removed-notice/index.tsx            [M]
│           └── pages/planner-page/
│               ├── planner-page.css                                           [M]
│               └── planning-proposal-review/{index.tsx, restart-planning-dialog/index.tsx} [M]
└── tests/
    ├── fixtures/identity-module-fixture.ts                                    [M] session/profile mocks gain appearance
    ├── support/account-backend.ts                                             [M] mocked profile gains appearance
    ├── identity/{account-profile-page.test.ts, account-auth-api.test.ts}      [M]
    └── shared/root-layout.test.ts                                             [M]
```

### Server declarations

```python
# identity/core/domain/enums/account_appearance.py
from enum import StrEnum


class AccountAppearance(StrEnum):
    DARK = 'dark'
    LIGHT = 'light'
    SYSTEM = 'system'
```

```python
# identity/core/domain/structures/account_profile_update.py (result)
@structure
class AccountProfileUpdate:
    display_name: str
    time_zone: str
    appearance: str  # __post_init__ raises InvalidAppearanceError unless the
    # value is one of AccountAppearance's values, after the unchanged
    # display-name and time-zone checks; the use case converts it.
```

`AccountProfile` adds `appearance: AccountAppearance` after `time_zone`; other
members unchanged. `UpdateAccountProfileUseCase.execute(user, update) ->
AccountProfile` and `GetAccountProfileUseCase.execute(user) -> AccountProfile`
keep their signatures.

REST contracts (prefix `/identity`, BFF secret and bearer token as today):

- `PATCH /accounts/me` request `{"display_name": str, "time_zone": str, "appearance": str}`,
  strict, no extra keys. 200 body adds `"appearance": "dark" | "light" | "system"`.
  400 `invalid_appearance` (pt-BR message) for an unknown value; a missing key is a
  request-validation failure; 401/403 unchanged.
- `GET /accounts/me` 200 body adds `appearance`.
- `GET /session` 200 body becomes `{account_id, display_name, time_zone, appearance}`.

Persistence guarantee: the migration is additive; a server default backfills every
existing row in the same DDL statement, so no separate data step is needed and no
row can be NULL. The check constraint guards the closed set at the database level
in addition to domain validation.

### Web declarations

```ts
// apps/web/src/core/identity/account-appearance.ts
export const ACCOUNT_APPEARANCES = ['dark', 'light', 'system'] as const

export type AccountAppearance = (typeof ACCOUNT_APPEARANCES)[number]
```

```ts
// provision/auth/cookie-session-auth-provider.ts (scoped excerpt)
export type AccountProfile = {
  accountId: string
  displayName: string
  email: string
  timeZone: string | null
  appearance: AccountAppearance
}
export type UpdateAccountProfileInput = {
  displayName: string
  timeZone: string
  appearance: AccountAppearance
}

// provision/auth/better-auth/better-auth-provider.ts (scoped excerpt)
export type LayoutAccount = {
  displayName: string
  email: string
  appearance: AccountAppearance
}
```

**Theme concept.** The theme is the value written to `<html data-theme>`. The
server-side route middleware is its only input on protected routes: it resolves the
session through Identity and returns `LayoutAccount.appearance`. The root layout
derives `theme` from the route match context (`dark` on public routes). CSS owns
the visual result: dark values are the default, light values apply to
`data-theme='light'`, and to `data-theme='system'` only while the device prefers
light. No browser storage, script or React state holds the theme, so there is
exactly one source of truth (Identity) and no hydration mismatch. The Toaster
receives the same value and resolves `system` itself.

**UI composition.** No new widget directory is created:

```text
account-profile-page/                       (unchanged page and query)
└── profile-form/
    ├── index.tsx                           renders the new Aparência Select after Fuso horário
    ├── use-profile-form.ts                 owns appearance value, options, validation, errors, reset
    ├── use-update-account-profile-action.ts  unchanged mutation and route refresh
    └── tests/{profile-form.test.tsx, use-profile-form.test.ts}
shared/widgets/layouts/root-layout/
├── index.tsx                               writes data-theme and passes theme to Toaster
├── use-root-layout.ts                      derives theme from route context
└── tests/{root-layout.test.tsx, use-root-layout.test.ts}
```

`useProfileForm` returns, in addition to its current contract, `appearance`
(`AccountAppearance`), `appearanceOptions` (`{ value, label }[]` with labels
Escuro, Claro, Sistema from a typed label map), `appearanceHelp` (pt-BR sentence
describing the current selection) and `handleAppearanceChange`. Form default and
reset values include `appearance: profile.appearance`; the schema validates it with
`z.enum(ACCOUNT_APPEARANCES)`; `errors.appearance` is shown below the field and an
`AuthError` with `field === 'appearance'` sets it. The action hook keeps its
mutation, cache write and `refreshCurrentRoute()`; only its refresh-warning copy
changes to mention the appearance. The route refresh re-runs
`requireAuthMiddleware`, which is what applies the new theme without a reload.

## Runtime Flow

```mermaid
sequenceDiagram
    participant U as Browser (Perfil)
    participant B as BFF /api/auth/account/profile
    participant I as FastAPI PATCH /identity/accounts/me
    participant D as identity_accounts
    participant R as Router + requireAuthMiddleware
    participant L as RootLayout
    U->>B: POST {displayName, timeZone, appearance}
    B->>B: zod enum validation, session required
    B->>I: PATCH {display_name, time_zone, appearance}
    I->>I: AccountProfileUpdate validation (InvalidAppearanceError → 400)
    I->>D: same transaction: access check, update name, zone, appearance
    I-->>B: 200 profile with appearance
    B-->>U: 200 camelCase profile
    U->>R: refreshCurrentRoute()
    R->>I: GET /identity/session
    I-->>R: {..., appearance}
    R-->>L: LayoutAccount.appearance
    L->>U: <html data-theme> updated, CSS applies tokens
```

- Trusted context: the bearer token and BFF secret identify the account; the body
  never names an account. The unchanged access check rejects pending, deleted and
  stale sessions before any write.
- Transaction: one Identity transaction updates name, time zone and appearance;
  any validation failure happens before it opens, so nothing is written.
- New access: every protected route's `beforeLoad` runs the middleware on the
  server for the first request, so the HTML response already carries the theme.
- Sistema: the `light dark` color scheme resolves from `prefers-color-scheme` and
  re-evaluates on device change; no JavaScript, request or reload.
- Failure: a rejected save leaves the route context untouched, so `data-theme`
  keeps the saved value; the form keeps the draft and shows the alert and field
  error. If the route refresh fails after a successful save, the existing warning
  asks to reload. If Identity is unavailable while resolving the session, the BFF's
  existing fallback access uses `appearance: 'system'`.
- Concurrency: last write wins, as for name and time zone; another device sees the
  new value on its next route load.

# Verification Contract

## Shared setup

- **Server tests.** From `apps/server`, with `AWS_PROFILE` unset in the shell.
  Use-case tests use autospecced ports. Controller tests use the shared
  PostgreSQL Testcontainer fixture from `apps/server/tests/conftest.py`, which runs
  Alembic head and cleans tables per test. Docker must be available; a skip is not
  a pass.
- **Web unit tests.** From the repository root with Node 24 (`nvm use 24`; Node 25
  breaks dependency-cruiser). Profile-form and root-layout component tests mock
  their owning hooks; hook tests mock the action hook and the router-matches source.
- **Web browser suites with mocked transport.** `account-profile-page.test.ts` and
  `root-layout.test.ts` use the shared factory `apps/web/tests/playwright.ts` and
  the Identity module fixture `apps/web/tests/fixtures/identity-module-fixture.ts`
  (`authenticatedPage`, server-function routing). The fixture's session and profile
  responses gain `appearance`; theme cases use `page.emulateMedia({ colorScheme })`.
- **Web auth API suite with real services.** `account-auth-api.test.ts` needs the
  Playwright web server environment: disposable PostgreSQL and Redis, the FastAPI
  service at Alembic head, `SHIFU_COMMUNICATION_ENCRYPTION_KEYS` placeholder and
  `AI_QUOTA_*` values as configured in `apps/web/playwright.config.ts`. It creates
  its own accounts; it never seeds or resets the shared development database.
- **Manual and visual checks.** Docker Compose services healthy (`docker compose
  ps`, API and web health). Sign in with the local seeded account
  `student.seed@shifu.com` (see `documentation/tooling.md`), storage state in
  `apps/web/.playwright-cli/states/shifu-auth-state.json`. Record the account's
  appearance before the journey and restore it afterwards. Captures go under
  `apps/web/.playwright-cli/screenshots/`. Close only the task-started session.

Test selection follows
[Tooling](../../../tooling.md#selecting-unit-and-integration-tests): only the files
below, because they own the changed contracts or are their direct consumers.

## Automated

### CI-01 — Profile update persists appearance and rejects invalid input

**Criteria:** CA-03, CA-04, CA-05

**Expected result:** each of `dark`, `light`, `system` is assigned and returned;
an unknown value raises `InvalidAppearanceError` with no repository update; the
unchanged access-denied cases raise `AuthorizationError` with no update.

**Proof:** `apps/server/tests/identity/core/use_cases/test_update_account_profile_use_case.py`

```bash
cd apps/server && uv run pytest tests/identity/core/use_cases/test_update_account_profile_use_case.py
```

**Passing condition:** new scenarios for the three values (parametrized), the
invalid value and existing denial cases pass; no skipped tests.

### CI-02 — Profile read returns appearance

**Criteria:** CA-05, CA-06

**Proof:** `apps/server/tests/identity/core/use_cases/test_get_account_profile_use_case.py`

```bash
cd apps/server && uv run pytest tests/identity/core/use_cases/test_get_account_profile_use_case.py
```

**Passing condition:** the returned `AccountProfile.appearance` equals the
account's value; denial cases unchanged and passing.

### CI-03 — New account starts as Sistema

**Criteria:** CA-01

**Proof:** `apps/server/tests/identity/core/use_cases/test_register_account_use_case.py`

```bash
cd apps/server && uv run pytest tests/identity/core/use_cases/test_register_account_use_case.py
```

**Passing condition:** the account passed to the repository has
`AccountAppearance.SYSTEM`.

### CI-04 — PATCH /identity/accounts/me contract and persistence

**Criteria:** CA-03, CA-04, CA-05

**Expected result:** 200 with `appearance` and persisted value read in a fresh
session; 400 `invalid_appearance` and unchanged row for `sepia`; request-validation
failure and unchanged row when `appearance` is missing; existing 401/403 cases.

**Proof:** `apps/server/tests/identity/server/controllers/test_update_account_profile_controller.py`

```bash
cd apps/server && uv run pytest tests/identity/server/controllers/test_update_account_profile_controller.py
```

**Passing condition:** all scenarios execute against the Testcontainer database.

### CI-05 — Read endpoints expose appearance

**Criteria:** CA-06

**Expected result:** `GET /identity/accounts/me` and `GET /identity/session` return
the stored appearance for each of the three values; an account created with the
entity default (faker without override) reads `system`. This proves the entity
default only; the migrated column default and backfill are proved by CI-06.

**Proof:** `apps/server/tests/identity/server/controllers/test_get_account_profile_controller.py`,
`apps/server/tests/identity/server/controllers/test_get_current_session_controller.py`

```bash
cd apps/server && uv run pytest tests/identity/server/controllers/test_get_account_profile_controller.py tests/identity/server/controllers/test_get_current_session_controller.py
```

**Passing condition:** exact response bodies include `appearance`; tests run.

### CI-06 — Migration upgrade, backfill and downgrade

**Criteria:** CA-02

**Expected result:** on a disposable PostgreSQL at the previous head with one
inserted account row, `upgrade head` yields `appearance = 'system'` for that row,
an `UPDATE ... SET appearance = 'sepia'` fails on `ck_identity_accounts_appearance`,
and `downgrade -1` removes the column and constraint.

**Proof:** disposable-environment delivery evidence (Database Rules forbid a
migration test module). The environment mirrors the test fixture
(`apps/server/tests/fixtures/postgres_fixture.py`) and CI
(`.github/workflows/server-app-ci.yaml`): the migration history needs the
pgvector extension and the AgentOS runtime role. From `apps/server`:

```bash
docker run --rm -d --name shifu-119-pg -e POSTGRES_PASSWORD=postgres -p 55432:5432 pgvector/pgvector:0.8.1-pg17
psql postgresql://postgres:postgres@127.0.0.1:55432/postgres -v runtime_password=disposable-runtime -v database_name=postgres -f scripts/create_agentos_runtime_role.sql
export DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:55432/postgres
uv run alembic upgrade <previous head>
# insert one identity_accounts row with psql, then:
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
uv run alembic check
docker stop shifu-119-pg
```

`DATABASE_URL` is the variable read by `DatabaseSettings` through
`apps/server/migrations/env.py`. The role script requires the psql variables
`runtime_password` (a disposable placeholder here) and `database_name` (the
disposable database, `postgres`), as the CI step passes them.

**Passing condition:** each command exits 0, `alembic check` reports no drift,
and the psql observations match; the shared development database is never
touched.

### CI-07 — Perfil form appearance behavior

**Criteria:** CA-08, CA-09, CA-10

**Expected result:** the component renders "Aparência" after "Fuso horário" with
the pt-BR selected label in the closed control and the help text, disabled while
pending, field error when present. The hook covers default from profile, change
handler, submit payload with the canonical value, `AuthError` field
`appearance`, generic failure, success reset and profile refresh reset.

**Proof:** `apps/web/src/ui/identity/widgets/pages/account-profile-page/profile-form/tests/profile-form.test.tsx`,
`.../profile-form/tests/use-profile-form.test.ts`

```bash
pnpm --filter web exec vitest run src/ui/identity/widgets/pages/account-profile-page/profile-form/tests/profile-form.test.tsx src/ui/identity/widgets/pages/account-profile-page/profile-form/tests/use-profile-form.test.ts
```

**Passing condition:** new cases pass with the component mocking
`useProfileForm` (`useProfileFormMock`) and the hook test mocking
`useUpdateAccountProfileAction`.

### CI-08 — Root layout resolves and writes the theme

**Criteria:** CA-11, CA-13, CA-14

**Expected result:** the hook returns `dark` on every public path, the account's
appearance on protected paths and `system` when the account context lacks it; the
component writes `data-theme` on `<html>` and passes the same theme to `Toaster`.

**Proof:** `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts`,
`.../root-layout/tests/root-layout.test.tsx`

```bash
pnpm --filter web exec vitest run src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx
```

**Passing condition:** the three values and the public override are each asserted.

### CI-09 — Auth context value keeps its contract

**Criteria:** CA-09 (consumer of the changed `AccountProfile` type)

**Proof:** `apps/web/src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts`
(update fixtures only if the changed type requires it)

```bash
pnpm --filter web exec vitest run src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts
```

**Passing condition:** passes with profile fixtures that include `appearance`.

### CI-10 — Perfil route saves each appearance and applies it

**Criteria:** CA-08, CA-09, CA-10

**Expected result (mocked transport):** for each target value, keyboard selection
and save send `POST /api/auth/account/profile` with the canonical `appearance`; the
success status is visible; `document.documentElement.dataset.theme` equals the new
value without a navigation event. A 503 and an `invalid_appearance` response keep
the previous `data-theme`, show the alert (and field error), and a retry succeeds.

**Proof:** `apps/web/tests/identity/account-profile-page.test.ts` (new tests)

```bash
pnpm --filter web exec playwright test tests/identity/account-profile-page.test.ts
```

**Passing condition:** new and existing scenarios pass in Chromium; the stateful
mock returns the saved appearance on the subsequent session read.

### CI-11 — Theme from the route middlewares, Sistema live change and public routes

**Criteria:** CA-11 (client route loads), CA-12, CA-13

**Expected result (mocked transport):** when each protected route producer returns
a `light` account, `/` (`enterMainPageMiddleware`) and `/account/profile`
(`requireAuthMiddleware`) render `data-theme="light"` and the light page
background; a `system` account renders light tokens under `colorScheme: 'light'`,
dark tokens after `emulateMedia({ colorScheme: 'dark' })` and light again, without
reload or additional middleware request (computed `background-color` of `body`);
the sign-in route renders `data-theme="dark"` and the dark background under
`colorScheme: 'light'`.

**Limits:** mocked browser transport answers server functions only for client-side
route loads; it cannot intercept the server render of the first document request.
The server-rendered first paint (CA-11) is proved by VM-01 with real services.

**Proof:** `apps/web/tests/shared/root-layout.test.ts` (new tests)

```bash
pnpm --filter web exec playwright test tests/shared/root-layout.test.ts
```

**Passing condition:** all scenarios pass; the existing public-shell test passes.

### CI-12 — BFF profile handler persists appearance with real services

**Criteria:** CA-07

**Expected result:** a signed-in account posting `appearance: 'light'` gets 200
with `appearance: 'light'`, a subsequent `GET /api/auth/account` returns it, and
the canonical row reflects it; bodies with `appearance: 'sepia'` or without
`appearance` are rejected with 400 and the account's appearance stays unchanged.

**Proof:** `apps/web/tests/identity/account-auth-api.test.ts` (extended)

```bash
pnpm --filter web exec playwright test tests/identity/account-auth-api.test.ts
```

**Passing condition:** runs against the disposable services described in Shared
setup; skipped runs are not a pass.

### CI-13 — Types

**Scope:** web project and server project (changed contracts and their consumers).

```bash
pnpm --filter web check:types
cd apps/server && uv run poe check:types
```

**Passing condition:** zero errors and zero warnings.

### CI-14 — Lint, format and complexity lint

**Scope:** every changed web and server path.

```bash
pnpm exec biome check <changed web paths...>
cd apps/server && uv run ruff check --no-fix <changed python paths...> && uv run ruff format --check <changed python paths...>
```

Additionally, a source search confirms CA-15: no `bg-white/`, `hover:bg-white/`,
`border-white/` or `bg-[#0f0f10]` remains in the modified widget files listed in
Architecture Mapping, and only the accepted exceptions keep fixed colors.

**Passing condition:** zero diagnostics. Biome's configured complexity rules and
Ruff `C90` are the complexity-lint dispositions. No dedicated complexity-metrics
gate is required or configured; that is recorded as not applicable, not as a pass.

### CI-15 — Project gates

**Scope:** affected apps.

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web build
pnpm check:test-integrity
cd apps/server && uv run poe check:lint && uv run poe check:architecture && uv run poe build
```

**Passing condition:** every gate passes with zero warnings; test integrity
accepts every modified test file.

## Manual

### VM-01 — Real authenticated journey, desktop

**Type:** Manual

**Criteria:** CA-08, CA-09, CA-11, CA-12

**Tool / setup:** Playwright CLI from `apps/web`, session `shifu`, 1440 × 900,
real services (Shared setup).

**Procedure:** open `/account/profile`; note the current appearance; select Claro
by keyboard and save; observe the status message and `data-theme="light"` with no
reload; reload and confirm light on first paint, and read the raw HTML of a document
request for `/` and for `/account/profile` with the session cookie (Playwright
request context) to confirm both carry `data-theme="light"` before hydration; open a second browser context,
sign in again and confirm light (new device); select Sistema and save; switch the
emulated color scheme dark/light and observe the theme follow; restore the noted
value.

**Passing condition:** final URL `/account/profile`; PATCH 200 seen in requests;
no new console errors; focus visible throughout; original value restored.

### VM-02 — Real journey, mobile and keyboard

**Type:** Manual

**Criteria:** CA-09

**Tool / setup:** as VM-01 at 390 × 844.

**Procedure:** reach the Aparência field and the save button by Tab only, change
to Escuro, save, then restore the original value.

**Passing condition:** no horizontal overflow, touch targets ≥ 44 px, status
announced, theme applied, no new console errors.

## Visual

### VM-03 — Perfil desktop in both themes

**Type:** Visual

**Criteria:** CA-08, CA-09, CA-14

**Reference / setup:** Penpot "Sua conta / Perfil" desktop board and the Design
System "Modo claro" section; captures from VM-01 at 1440 × 900 in dark and light.

**Capture / comparison:** fresh Penpot MCP exports vs the Playwright captures:
field order, control size, label/help typography, token colors per theme.

**Passing condition:** matches with no unaccepted deviation. Blocked while the
Penpot MCP is unavailable (Design Contract assumption).

### VM-04 — Perfil mobile in both themes

**Type:** Visual

**Criteria:** CA-08, CA-14

**Reference / setup:** Penpot "Sua conta / Perfil" mobile board; captures from
VM-02 at 390 × 844 in dark and light.

**Passing condition:** as VM-03. Blocked while the Penpot MCP is unavailable.

### VM-05 — Light contrast and shell token audit

**Type:** Visual

**Criteria:** CA-14, CA-15

**Reference / setup:** design.md §3.2 light values; Perfil, the desktop shell and
the mobile bottom navigation in light, with one hover state per changed shared
primitive.

**Capture / comparison:** read computed colors with Playwright CLI and compute
contrast ratios for every visible text pair and the control border; inspect the
captures for invisible hovers or borders.

**Passing condition:** text pairs ≥ 4.5:1, control border ≥ 3:1 against
`--muted`, fills equal to the dark values, toast in light. Run across every page of
the Penpot file is additionally required by `AGENTS.md` for Penpot work; this
delivery does not edit Penpot, so that sweep is not applicable.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Identity](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345/Shifu+PRD+Identity), content ID 83001345, version 6, last modified 2026-11-20, retrieved 2026-11-21 | RP-06 (partial), RP-07, RP-10; JN-06 context | Aligned; no amendment. Jira SHIFU-119 cites version 3: the conflict is reported, version 6 is used | Recheck version at conclusion; no external write |
| Jira SHIFU-119 (Epic SHIFU-24) | Delivery scope and criteria | Cites `shifu.fig`; `AGENTS.md` makes Penpot current. Conflict reported, Penpot used | No Jira write |
| Shifu Penpot file | Perfil and "Modo claro" boards | Not inspected: no Penpot available to the delivery | Visual assumption accepted by the user on 2026-11-21; VM-03/VM-04 Blocked |
| `documentation/design.md` §3, §6.1 T07, §8 | Tokens, Perfil field, accessibility | Confirmed as the light-value source; unchanged | — |
| `documentation/modules.md`, `architecture.md` | Identity authority, web composition | Unchanged; Identity stays the source of the value | — |
| Rule Pack listed in Architecture Mapping | Server and web boundaries | Confirmed; no rule change | Recheck if scope expands |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-11-21 | Initial contract, corrected after the independent Spec review (migration environment, structure typing, session appearance kept inside Identity, dashboard middleware, exact widget and fixture paths) | SHIFU-119 and PRD Identity v6 RP-06. Decisions: public routes stay dark (Q1), Penpot is the design source (Q2), revisited: no Penpot is available, so the visual assumption was accepted and VM-03/VM-04 stay Blocked, fixed colors become tokens except code surfaces, previews and scrims (Q3), server-rendered `data-theme` with CSS media query (Q4), required `appearance` in the strict profile contract with a NOT NULL default column (Q5) |
| 2 | 2026-11-21 | CI-11 limited to client route loads; server-rendered first paint for CA-11 moved to VM-01. CA-07/CI-12 state that the BFF's strict body validation rejects unknown or missing appearance before Identity | Mocked browser transport cannot intercept the server render of the first document request, found while running CI-11 |
