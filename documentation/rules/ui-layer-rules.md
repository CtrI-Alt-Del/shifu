---
description: Architecture and implementation rules for the web UI, shared widgets, routing, icons, hooks, REST adapters, and environment configuration.
---

# UI Layer Rules

These rules apply to `apps/web/src` and define how application UI, shared widgets,
hooks, routes, environment configuration, and REST adapters are organized.

Read and apply [`documentation/design.md`](../design.md) before every UI implementation or
review. It is the authority for design tokens, typography, visual hierarchy, responsive
behavior, focus treatment and accessibility expectations; this Rule defines the source and
composition boundaries that implement it.

## UI code follows feature and shared boundaries

Feature-owned UI belongs under:

```text
apps/web/src/ui/<module>/
```

Shared application UI belongs under:

```text
apps/web/src/ui/shared/
```

Use these shared directories consistently:

- `contexts` for application composition and dependency contexts;
- `hooks` for reusable application hooks;
- `styles` for global styles and theme integration;
- `widgets/components` for reusable application components;
- `widgets/layouts` for composed application shells and layouts.

Generated or installed shadcn primitives belong under `apps/web/src/ui/shadcn`.
Application widgets may compose those primitives, but feature code must not copy
or fork a primitive into a feature directory merely to change its presentation.

Business decisions and use-case orchestration do not belong in widgets, pages, or
hooks. The UI consumes core contracts through application adapters.

## Application imports use the `@/` alias

Imports that cross directories inside `apps/web/src` must use `@/`:

```ts
import { ROUTES } from '@/constants/routes'
import { Anchor } from '@/ui/shared/widgets/components/anchor'
```

Do not introduce `#/` or another application alias. Keep package imports such as
`@tanstack/react-router` and `@hms/core/...` unchanged. Relative imports are
appropriate for colocated files within the same widget, hook, context, or test
unit.

File and directory names use kebab-case. React components remain in `.tsx` files;
non-React hooks, types, constants, and utilities remain in `.ts` files.

### Stateful widgets use an index and a colocated hook

The default file boundary for every stateful or composed page, layout, dialog,
form, table, and nested widget is a directory:

```text
user-invite-dialog/
├── index.tsx
└── use-user-invite-dialog.ts
```

This structure is mandatory even when the widget is currently used by only one
page. The `index.tsx` file is the widget's rendering and composition entry point;
the colocated `use-<widget-name>.ts` file is the single owner of local state,
effects, form behavior, derived state, async orchestration, and interaction
handlers. Consumers import the widget from the directory path, which resolves to
`index.tsx`.

Do not create a monolithic `<widget-name>.tsx` file for a behavior-owning widget,
and do not keep its hook in a separate generic hooks directory. A single `.tsx`
file is acceptable only for a genuinely pure prop-to-markup renderer with no
state, effects, refs, form behavior, derived state, or event logic. Nested widgets
follow the same rule and receive their own directory, `index.tsx`, and hook when
they own behavior.

## UI implementation conventions

### Prefer shadcn components for UI elements

When a matching shadcn component exists, use it instead of rendering the
equivalent native interactive or form element directly in feature UI. This
includes controls such as buttons, inputs, selects, textareas, labels, badges,
dialogs and tables. Compose the shared component with its public props and
`className` rather than duplicating its markup in a feature directory.

If no suitable shadcn component exists, add or extend the shared primitive
under `apps/web/src/ui/shadcn` before introducing a feature-local equivalent.
Native elements remain appropriate for document structure, text content,
layout, external links and other cases where no shadcn abstraction exists or
native semantics are required. Preserve accessibility semantics and keyboard
behavior in either case.

### User-visible values use pt-BR labels

The product interface is presented in Brazilian Portuguese (`pt-BR`). Keep
domain discriminators, enum members, URL search values, form payloads and REST
values in their canonical technical representation, but map them to explicit
pt-BR labels before rendering them anywhere a user can read or hear them.

This applies to text content, badges, table cells, menu items, placeholders,
accessible names and every state of a form control. Select controls must render
the localized selected label in the closed trigger as well as in the popup; do
not assume that a primitive will derive the visible label from `SelectItem`
children. Use a typed label map or an explicit localized value child when the
control stores values such as `all`, `active`, `inactive`, `portion` or `resale`.
Tests must assert the visible or accessible pt-BR label for representative
default and selected states while preserving the canonical value passed to
handlers, URLs and services.

### Shared code conventions

Apply [`code-conventions-rules.md`](code-conventions-rules.md) for function
declarations, naming, handler prefixes, and the order of values and functions in
hook-result destructuring. The UI-specific rules below refine those shared
conventions where necessary.

### Action hooks

Hooks that encapsulate an application action use the
`use<Name>Action` naming pattern and are declared as exported arrow functions:

```ts
export const useForgotPasswordAction = () => {
  const { requestPasswordReset } = useAuthContext()
  const { mutate, isPending, error } = useMutation({
    mutationFn: (email: string) => requestPasswordReset(email),
  })

  return {
    error,
    forgotPassword: mutate,
    isPending,
  }
}
```

Action hooks should follow this structure:

1. obtain dependencies from application contexts or providers;
2. configure the underlying mutation/query and destructure its status values;
3. expose the operation through a domain-specific name instead of leaking a
   generic `mutate` function;
4. return the operation together with its `error` and loading/status values.

The action hook owns request orchestration and lifecycle callbacks. Page or
widget hooks consume the action hook and own local form state, UI state, and
interaction handlers.

Query and action hooks do not receive dedicated test files. Their observable
request, lifecycle, invalidation, recovery and rendering behavior is covered by
the consuming page/widget test and, when applicable, the route integration
suite. Web REST services also do not receive dedicated tests: exercise their
observable method/path/query/body, response mapping and failure behavior through
those consuming boundaries. Do not test React Query itself or duplicate consumer
behavior in a `use-<query-or-action>.test.ts` file.

### Catch blocks provide user-visible feedback

In Web UI code, a catch block must not use a comment as the only explanation
for a swallowed or recovered failure. When a comment inside a catch block
describes why execution continues, replace that comment with a user-visible
toast notification implemented through Sonner:

~~~ts
import { showErrorToast } from '@/ui/shared/notifications'

try {
  await submitForm()
} catch {
  showErrorToast('Não foi possível concluir agora. Tente novamente.')
}
~~~

The shared notification wrapper at apps/web/src/ui/shared/notifications is
the application boundary for Sonner calls, and the root layout owns the single
Toaster mount. Use an error, warning or neutral informational toast according
to the failure and keep the existing recovery behavior, field state and
navigation semantics intact. A toast must not disclose authentication,
account-existence, tenant or provider details that the existing flow
intentionally keeps neutral.

This rule applies to catches in page hooks, feature hooks, contexts, layouts,
storage helpers and client route middleware. Do not add a second Toaster, call
Sonner directly from feature widgets, or leave a comment-only catch after the
change. Server-side code outside the Web UI uses its existing application error
and logging contracts rather than importing Sonner.

### Mirror widget structure for nested components

Every nested component is a widget and follows the same directory convention as
its parent widget. A parent and each nested widget use an `index.tsx` entry point;
the widget may also have a colocated `use-<widget-name>.ts` hook when it owns UI
logic:

```text
client-register-dialog/
├── index.tsx
├── use-client-register-dialog.ts
└── steps/
    └── client-identification/
        ├── index.tsx
        └── use-client-identification.ts
```

This is mandatory: do not define a nested component as a local component inside
its parent's `index.tsx`. Every internal component must be promoted to an
internal widget with its own widget directory and `index.tsx` entry point. Give
it an exported widget-specific prop type and a colocated hook when it owns
behavior, even when the widget is not reused outside its parent.

### Keep UI logic inside the owning widget hook

Widgets with non-trivial interface behavior must have a colocated
`use-<widget-name>.ts` hook. Non-trivial behavior includes local state, effects,
refs, form state or validation, field arrays, request/action orchestration,
derived UI state, transitions, and user-interaction handlers. A widget may omit
the hook only when it is a pure prop-to-markup renderer with no behavior of its
own.

The widget `index.tsx` is a composition and rendering boundary. Its component
must be declared as an exported `const` using the widget-specific props type:

```tsx
export const CollaboratorRegisterDialog = (
  props: CollaboratorRegisterDialogProps,
) => {
  const { state, error, handleClose, handleSubmit } =
    useCollaboratorRegisterDialog(props)

  return <DialogContent>{/* markup and hook wiring */}</DialogContent>
}
```

Do not declare behavior-owning widget entry points with `export function`, and do
not keep their state, effects, form setup, derived state, request orchestration,
or handler implementations in `index.tsx`. The entry point may render markup,
compose nested widgets, and use trivial inline callbacks only to adapt a prop
or provide an item index; the behavior itself belongs in the hook. Do not add
standalone helper or formatter functions outside the component and its owning
hook in a `.tsx` file.

Reusable display formatting is an application concern, not a widget-local
implementation detail. Currency, decimal, quantity, percentage and date
formatting shared by more than one widget belongs in the shared UI hooks
boundary, using the existing formatter hooks and locale/precision conventions.
Widget-local formatters are permitted only for genuinely private presentation
rules that are not reusable and do not duplicate a shared formatter contract.

Each shared formatter hook must have its own kebab-case file under
`apps/web/src/ui/shared/hooks`. For example, `useFormatCurrency` belongs in
`use-format-currency.ts`, `useFormatDecimal` in `use-format-decimal.ts`,
`useFormatQuantity` in `use-format-quantity.ts`, and `useFormatDate` in
`use-format-date.ts`. Do not group multiple formatter hooks in a
`use-formatters.ts` module or add a formatter barrel; consumers import each
hook directly from its own file.

Functions declared inside a widget hook must use the `function` form, including
helpers, interaction handlers, lifecycle callbacks, and async submit handlers:

```ts
export function useCollaboratorRegisterDialog(props: CollaboratorRegisterDialogProps) {
  function handleClose() {
    // interface behavior
  }

  async function handleSubmit() {
    // submit behavior
  }

  return { handleClose, handleSubmit }
}
```

Do not declare widget-hook behavior as arrow-function variables. This rule
applies to widget and page hooks; the exported-arrow convention for
`use<Name>Action` hooks remains the explicit exception described above.

All UI logic belongs in the owning widget's hook. This includes local state,
effects, subscriptions, form state and validation, request orchestration,
derived state, transitions, and user-interaction handlers. The component entry
point is responsible for rendering markup, passing props, and wiring DOM events
to handlers exposed by the hook; it must not contain the logic behind those
handlers.

Consume every page and widget hook through direct named destructuring. Do not
assign a hook result to `controller`, `viewModel`, or another aggregate variable
and then dereference it throughout the component. The hook's returned object is
the public UI contract, so its values and handlers must be visible at the call
site and kept in the shared value-before-handler order:

```ts
const { state, error, onboarding, handleRestart } =
  useOnboardingConfirmationPage(confirmationToken)
```

This rule applies to all hooks consumed by UI widgets, including hooks that
return a single state value or action contract. A `controller` variable is not a
UI hook convention.

The hook must remain the single owner of the widget's behavior. Nested widgets
apply the same rule in their own hooks and must not reach into a parent's local
state except through explicit props or callbacks.

Page-owned hooks live beside the page widget under its feature directory, for
example `widgets/pages/<page>/use-<page>.ts`. Query hooks, action hooks and query
keys that exist only for that page stay within the same page boundary. Every
named function in a page hook—including helpers and interaction handlers—must be
declared with the `function` form; do not use arrow-function declarations for
page-hook behavior.

When a hook is consumed by more than one widget, it is a feature-level shared
hook and must live under `apps/web/src/ui/<module>/hooks/`. It must not remain
inside the first widget that used it. A hook that is exclusive to one component
widget remains colocated with that widget. The placement follows actual
consumers: do not promote a hook merely because it might be reused later.

Tests for a page, layout, dialog, form, table or other widget live directly in
that widget's directory beside `index.tsx` and its owning hook. A nested widget's
test belongs in the nested widget directory, not in a parent-level or shared
`tests/` directory. Query/action hooks remain covered through these consuming
widget tests and do not add their own test files.

### Use shared HTTP status constants

Web UI code must use `HTTP_STATUS_CODE` from
`@hms/core/shared/constants` when interpreting REST status
codes. Do not compare a response status with a numeric literal:

```ts
import { HTTP_STATUS_CODE } from '@hms/core/shared/constants/http-status-code'

if (response.statusCode === HTTP_STATUS_CODE.conflict) {
  // recover from a concurrent registration
}
```

This applies to every status-code branch, including `notFound`, `conflict`, and
`unprocessableEntity`. Keep transport-to-domain mapping in the REST adapter or
owning widget hook as appropriate, but always use the shared constant for the
comparison.

## Widgets expose widget-specific prop types

Every widget with props must export a type named after the widget:

```ts
export type SidebarProps = {
  isCollapsed: boolean
  onToggle: (isCollapsed: boolean) => void
}

export const Sidebar = ({ isCollapsed, onToggle }: SidebarProps) => {
  // ...
}
```

Use `<WidgetName>Props`; do not export a generic `Props` type from a widget. A
children-only widget may alias `PropsWithChildren`, but the alias must still carry
the widget name, such as `AppLayoutProps`.

The exported prop type is part of the widget contract and must also be reused by
tests and mocks. Do not reconstruct an approximate prop shape elsewhere.

## Shared wrappers own third-party UI boundaries

Application code must consume shared wrappers for third-party primitives when the
wrapper establishes an HMS contract. Consumers depend on the wrapper, not on the
library's implementation details.

### Navigation uses `Anchor`

Internal application links use
`apps/web/src/ui/shared/widgets/components/anchor`. `Anchor` owns the TanStack
Router `Link` integration and accepts a typed `route` name instead of an arbitrary
`href` or `to` value:

```tsx
<Anchor route='intakes'>Intakes</Anchor>
```

Do not reproduce TanStack Router link casts or adapters in each widget. External
URLs may still use a native anchor because they are not application routes.

### Application icons use `Icon`

Application widgets use the shared `Icon` component instead of importing Lucide
components or `LucideIcon` types directly. The Lucide mapping remains an internal
implementation detail of the icon widget.

Every public icon is registered in the icon map and represented by `IconName`.
`IconName` values use kebab-case:

```ts
type IconName = 'arrow-right' | 'layout-dashboard' | 'file-text'
```

If a widget needs a new icon, add it to `IconName` and the internal map before
using it. Do not pass icon components through sidebar configuration; pass an
`IconName` instead.

## Route constants are canonical paths

All application paths are declared in `apps/web/src/constants/routes.ts` as
string values:

```ts
export const ROUTES = {
  root: '/',
  home: '/home',
  intakes: '/intakes',
} as const
```

Do not wrap routes in objects such as `{ path: string }`. No path may end in `/`,
except the root path `/`. Route files, widgets, sidebar configuration, and tests
must reuse `ROUTES` rather than duplicate path literals.

`RouteName` identifies a key of `ROUTES`; `RoutePath` identifies one of its path
values. Configuration such as sidebar items stores a `RouteName`, allowing the
consumer to resolve the canonical path through `ROUTES[item.route]`.

`ROUTES` must describe the route tree that actually exists in the web app. Remove
stale paths instead of keeping placeholders for future screens. When a route is
renamed, update the route file, route constants, sidebar configuration, and
navigation consumers together.

## Route protection uses one middleware

Protected routes use the shared middleware from:

```text
apps/web/src/middlewares/require-auth-middleware.ts
```

Attach it through `beforeLoad: requireAuthMiddleware`. Do not create a separate
`requireAuth` helper for individual routes or duplicate provider session checks
inside route files. The middleware must consult the provisioned auth provider,
redirect unauthenticated users to `ROUTES.login`, and return the authenticated
session in the before-load result.

Authentication is a route concern, not a widget concern. Widgets may still use
the shared auth context to render and perform actions after the route is loaded.

## Imperative navigation uses the application hook

Components and application hooks must use
`apps/web/src/ui/shared/hooks/use-navigation.ts` for imperative navigation. The
hook maps a typed `RouteName` to the TanStack Router path through `ROUTES`.
Import `useNavigate` directly only inside this wrapper or in infrastructure code
that is not a UI interaction. Declarative internal links use `Anchor`.

## Sidebar configuration is profile-driven

Sidebar entries belong in `apps/web/src/constants/sidebar-items.ts`, not inside
the layout. Every item contains a label, a `RouteName`, and an `IconName`.

`SIDEBAR_ITEMS` must define an entry for every current `UserProfile`. Reuse shared
item collections where Manager and Operator have the same destinations instead of
duplicating arrays, and add profile-specific destinations only to the profile that
is authorized to reach them. Communication is not a sidebar item.

`useAppLayout` must select the collection from the authenticated account's
`UserProfile`. Do not infer a profile from the route, local storage, or placeholder
user data. While the account is loading or unavailable, do not render a
profile-dependent sidebar collection.

The active item matches either its exact path or a nested path. Normalize a
trailing slash before matching. The Home item is exact-only and must not become
active for arbitrary nested paths.

## Internal layout widgets stay owned by their layout

Structural widgets such as an app layout's `Sidebar` and `Navbar` are internal to
that layout while they have no independent reuse contract. Keep them colocated
under the layout directory and exercise their user-visible behavior through the
owning layout.

An internal widget may have a colocated hook when state, subscriptions, or
coordination would otherwise make rendering code difficult to follow. Extracted
hooks own behavior and effects; widgets remain responsible for markup and event
wiring. The existence of a hook does not make the internal widget a public shared
component.

## Hooks wrap application semantics, not libraries generically

Create an application hook around a library hook when it provides a stable HMS
concept, centralizes mapping or lifecycle behavior, or shields consumers from a
third-party API. For example, `useUrlPathname` exposes the pathname required by
application layouts without spreading TanStack Router selection details.

Do not create transparent generic wrappers such as an HMS-wide `useQuery` that
merely forwards options. Prefer domain-specific hooks such as `useIntakesQuery`,
where query keys, service calls, response handling, and domain naming can remain
consistent.

Query hooks must also hide TanStack Query's generic result names from their
consumers. Destructure and rename `data`, `error`, and loading state inside the
owning hook, then return names that describe the domain value and operation:

```ts
export const useLegalAreasQuery = () => {
  const { legalCatalogService } = useRestContext()
  const {
    data: legalAreas = [],
    error: legalAreasError,
    isLoading: isLoadingLegalAreas,
  } = useQuery({
    queryKey: ['legal-catalog', 'areas'],
    queryFn: async () => {
      const response = await legalCatalogService.listLegalAreas()

      if (response.isFailure) response.throwError()

      return response.body
    },
  })

  return { legalAreas, legalAreasError, isLoadingLegalAreas }
}
```

The consuming widget hook should use the semantic result directly rather than
repeating aliases such as `data: legalAreas` or `error: legalAreasError`. A query
that depends on a selected identifier must expose the dependency in its query
key and disable the request until that identifier is available.

The same rule applies to realtime APIs. A provider-backed realtime subscription may be
encapsulated by a domain-specific hook that owns subscribe, unsubscribe, event
mapping, and cleanup. It does not need to be forced through TanStack Query when
the concern is a live subscription rather than request caching.

Feature-owned realtime hooks must expose application-level domain values and actions,
not transport controls or event-source details. For example,
`apps/web/src/ui/communication/hooks/use-notification-realtime.ts` owns the
notification stream's `EventSource` lifecycle, event parsing and validation, domain
mapping, retry schedule, fan-out and cleanup. Its public contract is limited to the
notification scope, such as eligibility and a notification-created callback; consumers
must not manage `EventSource`, reconnect timers, raw event names or serialized payloads.
Keep the browser transport construction seam under `apps/web/src/provision`, while
keeping lifecycle and transport error handling inside the feature-owned realtime hook.

Realtime hooks, realtime providers and their transport adapters are verified through
the consumer boundary that observes their behavior. Do not add dedicated test files
for `useNotificationRealtime` or the native `EventSource` adapter. Cover notification
delivery, validation, retry, cleanup, eligibility and no-replay behavior through the
notification context consumer, owning widgets and the browser route suite. A context
provider hook that owns broader UI state, such as notification queue, selection or
dropdown pinning, remains tested at its context boundary; that test must not duplicate
the transport implementation.

## React contexts follow one composition pattern

Use React Context for dependencies or state that must be shared by distant
branches of a stable application subtree. Prefer props for explicit parent-child
data flow and local state for behavior owned by one widget. Do not introduce a
context merely to avoid passing one or two props through a shallow tree.

A shared context belongs under:

```text
apps/web/src/ui/shared/contexts/<context-name>/
```

A context owned by one feature belongs under that feature's `contexts` directory.
Use this structure:

```text
<context-name>/
├── index.tsx
├── types/
│   └── <context-name>-value.ts
├── use-<context-name>-provider.ts
└── tests/
    └── use-<context-name>-provider.test.ts
```

This structure is mandatory for every new or relocated context. Do not keep a
flat `<context-name>.ts` or `<context-name>.tsx` file inside a widget, layout,
page, or generic hooks directory. The context directory is the single ownership
boundary:

- `index.tsx` owns the `createContext` call and the named provider component;
  it may accept a typed `value` prop when the owning layout assembles the value,
  but it must not contain consumer behavior or business rules.
- `types/<context-name>-value.ts` owns the complete `<ContextName>Value` type;
  export it through `types/index.ts` when the context has a types barrel.
- `use-<context-name>-provider.ts` owns provider construction, state, effects,
  and derived values when the context itself owns that behavior.
- `tests/use-<context-name>-provider.test.ts` owns the provider hook's behavior
  matrix when the provider hook owns state, effects, subscriptions, or derived
  context values. Keep this test inside the context directory rather than in a
  widget or generic hooks directory.
- Consumer hooks belong under `ui/shared/hooks` for shared contexts or the
  feature's `hooks` directory for feature contexts. A consumer hook is the only
  boundary allowed to call `useContext` and import the raw context object;
  components, layouts, and other consumers must import the named hook instead.

When a context provider owns state, subscriptions, effects, or derived values,
keep that behavior in the context directory's `use-<context-name>-provider.ts`
hook and render the context directory's provider component at the narrowest
stable layout boundary. A layout may assemble an already-owned context value,
but it must not become the provider hook's ownership boundary. The consumer-hook
boundary still applies; this does not justify placing the context declaration or
provider hook back under a layout.

Feature-specific realtime context belongs under the feature's context boundary. The
notification shell context therefore lives under:

```text
apps/web/src/ui/communication/contexts/notification-shell-context/
```

Keep `useNotificationShellProvider` in that directory as the provider-value builder,
and expose a named consumer hook such as `useNotificationShellContext` from the
feature hooks boundary. The consumer hook is the only UI boundary that reads the raw
context object; components use its named, high-level notification state and actions.
Compose `NotificationShellContextProvider`, `useNotificationShellProvider` and
`useNotificationRealtime` directly in `AppLayout`, which is the stable authenticated
notification scope. Do not add or retain a notification-specific layout wrapper just
to mount the context or realtime hook.

The public context file owns the context object, its named provider props, and the
provider component. Contexts start with `null`; do not cast an empty object into
the value type:

```tsx
import { createContext, type PropsWithChildren } from 'react'

import type { RestContextValue } from './types/rest-context-value'
import { useRestContextProvider } from './use-rest-context-provider'

export type RestContextProviderProps = PropsWithChildren

export const RestContext = createContext<RestContextValue | null>(null)

export const RestContextProvider = ({ children }: RestContextProviderProps) => {
  const value = useRestContextProvider()

  return <RestContext.Provider value={value}>{children}</RestContext.Provider>
}
```

The value type uses the `<ContextName>Value` suffix and describes only values
available to consumers. Derive service factory values with `ReturnType` instead
of duplicating their contracts:

```ts
export type RestContextValue = {
  intakeService: ReturnType<typeof IntakeService>
}
```

The application auth context is a shared composition boundary and belongs at:

```text
apps/web/src/ui/shared/contexts/auth-context/
```

Keep its provider hook, consumer hook, and value type colocated there. Identity
widgets consume `useAuthContext`; they do not own or recreate the context.

The auth context must delegate authentication operations to the concrete
cookie-session provider under `apps/web/src/provision/auth/`. It may own React state,
subscription lifecycle, and the value exposed to consumers, but it must not call
Better Auth directly, read the `HttpOnly` cookie, or persist session tokens.

There is one application sidebar:

```text
apps/web/src/ui/shared/widgets/layouts/app-layout/sidebar/
```

Do not create feature-specific duplicate sidebars. Sidebar actions, including
sign-out, belong to that widget and consume shared application contexts.

The provider hook owns dependency construction, state, effects, and derived
values needed to assemble the context. It returns the complete context value and
must not contain business rules. Keep the provider component declarative; it only
calls the provider hook and renders the React provider.

Do not add `useMemo` to provider values by default. Introduce memoization only
when referential stability is required by behavior or demonstrated by a relevant
rendering problem.

Consumers use a named application hook rather than calling `useContext` directly.
The hook validates the provider boundary and throws `AppError` when the context is
missing:

```ts
export function useRestContext() {
  const context = useContext(RestContext)

  if (!context) {
    throw new AppError('useRestContext must be used inside RestContextProvider')
  }

  return context
}
```

Place a shared consumer hook under `ui/shared/hooks`; place a feature-owned hook
under that feature's `hooks` directory. Components import the consumer hook, not
the raw context object.

Mount each provider at the narrowest stable layout or application boundary that
contains all intended consumers. When adding or removing a context value, update
the value type, provider hook, provider composition, and affected consumers as one
change.

### Feature notification presentation constants

When multiple notification widgets need the same kind-to-icon, tint or semantic
presentation, define one typed, exhaustive mapping under:

```text
apps/web/src/ui/communication/constants/
```

Keep distinct semantic constant groups in their own kebab-case files, such as
`notification-presentation.ts` and `notification-semantic-styles.ts`. Key mappings
by the canonical `NotificationKind`, use existing `IconName` and design-system
tokens, and compose the mapping in `NotificationRow` and `NotificationToast`. Do
not duplicate kind conditionals or introduce widget-local presentation literals when
the shared notification constant applies.

## REST adapters are factories

The web REST layer lives outside `ui`, under `apps/web/src/rest`, and is composed
at the UI application boundary.

Transport and module services use the shared PascalCase factory convention and
return objects. Do not implement them as classes. Returned operations use method
shorthand:

```ts
export const IntakeService = (restClient: RestClient): IntakeRestService => {
  return {
    getIntake(intakeId) {
      return restClient.get<Intake>(`/intakes/${intakeId}`)
    },
  }
}
```

Allow the declared return interface to contextually type method parameters when
TypeScript supports it. Generic transport methods may retain the annotations
required to avoid implicit `any`.

Module services receive `RestClient`, implement the corresponding core service
interface, and only map operations to HTTP methods and paths. They contain no
business rules, caching, authentication state, or direct Axios calls.

`AxiosRestClient` creates the Axios instance and returns the `RestClient` object.
Reusable request execution, header normalization, and error extraction belong in
`apps/web/src/rest/axios/utils`; do not simulate private class methods inside the
factory.

Dynamic identifiers may be interpolated directly when their contract guarantees
a URL-safe format such as ULID. Do not add `encodeURIComponent` mechanically to
ULID path segments.

## REST services are composed by the context provider

`RestContextProvider` is the application composition boundary for REST services.
Its provider hook creates `AxiosRestClient` with the validated browser API URL and
passes that client to each service factory:

```ts
const restClient = AxiosRestClient(BROWSER_ENV.hmsServerAppUrl)

return {
  intakeService: IntakeService(restClient),
}
```

Keep `RestContextValue` aligned with the services returned by the provider and use
`ReturnType<typeof ServiceFactory>` instead of duplicating service interfaces.
The current provider intentionally creates its dependencies directly and does not
use `useMemo`.

## Environment variables are validated at the boundary

Browser-visible variables use Vite's `VITE_` prefix and are read only by the
browser environment constants. Map infrastructure names to application names and
validate them with Zod before exporting `BROWSER_ENV`:

```ts
const BROWSER_ENV_INPUT = {
  hmsServerAppUrl: import.meta.env.VITE_HMS_SERVER_APP_URL,
}
```

Server-only variables must not use the `VITE_` prefix and must not be exposed
through `BROWSER_ENV`. Keep browser and server environment schemas in separate
files.

## Visual implementation follows the design system

Before changing UI or styling, follow
[`documentation/design.md`](../design.md). Use the existing CSS variables and
Tailwind theme tokens for colors, typography, radii, spacing, shadows, focus
states, and light/dark behavior. Do not hardcode a design value when an
appropriate token exists.

Headings use the documented serif family; body copy, controls, and navigation use
the documented sans family. Preserve accessible names, visible keyboard focus,
semantic elements, and non-color indicators for state.

## Composite input focus states

When an input is visually contained by a composite field wrapper, render one
focus treatment on the wrapper with `focus-within`. Remove the inner input's
focus-visible border, outline, ring, and shadow so nested controls do not show
duplicated focus states. The wrapper must remain visibly focused for keyboard
users. When the shared global focus selector would otherwise add an outline,
mark the delegated control with `data-focus-ring='delegated'`. Playwright
validation must verify both the neutral inner styles and the wrapper's visible
focus treatment. Apply this pattern to affixed inputs and to native date inputs
composed with an inline `De`/`Até` label; preserve the browser's active date-segment
highlight as an editing cue, but never use that segment highlight as the only
visible focus indicator.

Shared primitives that already own a complete `focus-visible` border/ring must
set `data-focus-ring='delegated'` by default so the global fallback outline does
not create a doubled halo. Consumers must not remove the primitive's remaining
visible focus treatment. All text-like inputs use the shared Input focus style:
one `ring-2 ring-ring/20` with a `border-ring`, whether it is owned directly by
the input or delegated to a composite wrapper. Do not introduce page-level
focus-color or ring-strength overrides for ordinary inputs.

## Dialog header structure

Every application dialog, including alert and destructive confirmation dialogs,
uses the shared two-column header hierarchy: the semantic icon tile remains to the
left of the title and supporting-description block, the supporting description stays
immediately below the title, the close action remains isolated at the top-right, and
a soft separator divides the header from the body. Preserve the icon and semantic
color that communicate the dialog's purpose; do not stack the icon above the copy or
omit the header separator. Reserve enough right padding that long titles and
descriptions cannot collide with the close action.

## Antipatterns to Avoid

- Do not expose raw technical values such as `all`, `active` or `inactive` in
  user-visible controls. Render `Todos`, `Ativo` or `Inativo` as appropriate,
  verify the closed control displays that pt-BR label, and keep the raw value
  only at the state, URL, form or transport boundary.
