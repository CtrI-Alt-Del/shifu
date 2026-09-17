---
description: Vitest and Testing Library rules for web widgets, layouts, hooks, mocks, and navigation behavior.
---

# Widget Testing Rules

These rules apply to tests under `apps/web/src/ui` and the corresponding browser
integration tests under `apps/web/tests`. They define which UI boundaries receive
tests, how those tests are named, how dependencies are mocked, and the minimum
evidence required before a widget is considered covered.

## Browser integration suites follow module ownership

Playwright integration tests cover routed pages and layouts through the real
application composition. Organize them under `apps/web/tests/<module>/`, where
`<module>` is the module that owns the page or the shared boundary:

```text
apps/web/tests/
├── identity/
│   └── account-page.test.ts
└── shared/
    └── app-layout.test.ts
```

Feature page suites belong under their owning business module, such as
`tests/identity/account-page.test.ts`. Shared application shells and layouts
belong under `tests/shared`, such as `tests/shared/app-layout.test.ts`. Do not
place these suites in a generic `tests/integration/` directory, in a flat test
directory, or under a module that does not own the route or layout.

The Playwright configuration must scan `./tests` so every module directory is
discovered. Browser integration files use `.test.ts` or `.test.tsx`, matching the
repository-wide test naming convention. Their Playwright ownership is determined
by their location under `apps/web/tests`, while colocated Vitest widget and hook
tests remain under the owning widget's `tests/` directory.

Every routed Page and Layout owns one module-scoped browser integration file named
after its widget declaration in kebab-case, such as `identity/account-page.test.ts`
or `shared/app-layout.test.ts`. Use `.test.ts` even when the production widget is
`.tsx`; do not name the integration after the route source file or URL segment.

Each page or layout integration suite must exercise the actual route and assert
the user-visible boundary it owns. For navigation and responsive layout flows,
assert the final URL, visible destination content, active accessibility state,
and the relevant keyboard or pointer interaction. Do not replace the owning
widget's colocated Vitest tests with a browser suite, and do not count a test that
only renders a mocked component or intercepts a request as route integration.

## Test public behavior at the owning widget boundary

Tests exercise the smallest public widget or layout that owns a user-visible
behavior. Assert what the user can render, identify, click, and observe rather
than internal JSX structure or implementation details.

An internal widget does not receive a separate test file when it exists only as a
structural part of its owner. For example, `AppLayout` owns its internal `Sidebar`
and `Navbar`; render them through `app-layout.test.tsx` instead of creating
`sidebar.test.tsx` and `navbar.test.tsx`.

Do not mock internal child widgets merely to make the owning widget test smaller.
Rendering the internal composition protects event wiring and accessibility across
the boundary. The owning widget's colocated behavior hook is the one permitted
component-test seam: component tests mock that hook and render the real widget
composition below it. The hook's state, effects and transitions are covered by a
dedicated hook test when they are substantial; query hooks and action hooks do not
receive dedicated tests.

A dedicated widget test becomes appropriate only when the widget has its own
public reuse contract or substantial behavior independent of its current owner.
Do not create tests solely to mirror the file tree.

## Infrastructure providers and plugins never own tests

Do not create test files beneath `apps/web/src/provision` or
`apps/web/tests/unit/provision`, and do not create a suite that directly targets or
imports a concrete infrastructure provider or application plugin. Authentication
provider behavior is tested by sending HTTP requests through the registered API
handler and by exercising routed pages/layouts through real application composition.

React context provider hooks are UI behavior boundaries, not infrastructure
providers. A context-owned `use-<context-name>-provider.ts` may therefore have the
colocated `tests/use-<context-name>-provider.test.ts` required by the context rules.
That test mocks the provision adapter and verifies the context value, state, effects,
subscriptions, or derived behavior; it must not become a back door for directly
testing the infrastructure provider.

An API-handler integration suite targets the public HTTP route, not the provider
method behind it. Send requests through the registered route and assert status,
headers, cookies, persistence, rollback, throttling, and safe failures as applicable.

## Do not confuse structural coverage with behavioral coverage

An isolated test that renders a widget with its owning hook mocked is intentionally
component-boundary coverage. It proves that the widget maps controller state to
markup and delegates callbacks, but it does not prove that the hook, query, dialog,
URL state, or mutation is wired correctly. Those behaviors require the hook and
route layers described below.

For a stateful page or widget, use these layers when the behavior crosses the
boundary:

1. A component test that mocks the owning hook and renders the real internal
   composition. Mock the nearest application boundary needed to make the test
   deterministic, such as an Anchor or domain service, and provide the required
   providers.
2. A hook test of the widget's own colocated hook with `renderHook` when it
   owns substantial derived values, URL/state transitions, effects or guards
   that are not adequately observable through the component. This does not
   apply to query/action hooks.
3. A route integration test when the behavior crosses URL, authentication or
   REST boundaries; this is the evidence for the real owning-hook composition.

Every `.test.tsx` for a widget with a colocated owning hook must mock that hook,
including loading, success, empty, error, pending and recovery state cases. Name
the typed mock with the hook name plus `Mock`, and configure a fresh return value
in `beforeEach`. A component test must not invoke the real owning hook merely to
exercise its queries or mutations; cover those through the hook and route layers.
Widgets without a colocated behavior-owning hook remain direct prop/state
component tests and do not need a fabricated hook solely to satisfy this rule.

A green suite made only of mocked controller snapshots, callback assertions, or
route handlers is structural coverage and must not be reported as complete
behavioral coverage.

## Minimum behavior matrix for stateful widgets

The cases below are the default minimum. Omit a case only when the behavior is
impossible for the widget, and state the reason in the test or evaluation.

- loading/skeleton state;
- successful data state with the primary user-visible content;
- empty state without filters and empty state with filters, when both differ;
- request or mutation error with a visible recovery action;
- pending mutation state, including disabled confirmation controls;
- success outcome after the mutation, including refreshed or closed UI;
- every status or role that changes available actions;
- filter, sort, pagination, and URL synchronization when present;
- dialog/drawer open, cancel/close, confirm, and validation behavior when present;
- protected access and redirect behavior at the route integration boundary.

For tables, test the action availability matrix explicitly. For example, an
invited record may expose resend/cancel, an active record may expose deactivate,
and a disabled record may expose reactivate while forbidding removal. Testing one
row and one action does not cover the table.

## Page suites cover the complete widget ownership tree

A page test suite is complete only when every public page behavior and every
owned nested widget boundary has focused coverage. A parent-page test does not
replace the tests for a form, card, editor, or other nested widget with its own
public controls. Keep each test in the `tests/` directory of the boundary it
owns, and cover the real composition at the parent boundary.

For a stateful registration page, the suite should include, when those
boundaries exist:

- the page component and its owning hook, including every returned value and
  callable handler;
- the registration form, including field, unit, category, validation, and
  submit behavior;
- the stock-control card, including each stock mode, stock fields, pending or
  disabled controls, and error state;
- nested brand editors, including every editable field, primary-brand choice,
  removal availability, and field errors.

Apply the same rule to every page: enumerate the page hook's public contract and
the nested widgets' public actions before declaring the suite covered. A passing
parent test or a high file-level coverage percentage is insufficient when one of
those boundaries or returned behaviors is untested.

## File names, locations and test text follow one convention

Place every widget test inside a `tests/` directory under the corresponding
widget directory. This is a mandatory placement rule for both component tests
and behavior-hook tests, not merely a naming preference:

```text
widgets/layouts/app-layout/tests/app-layout.test.tsx
widgets/layouts/app-layout/tests/use-app-layout.test.ts
widgets/pages/products-page/product-filters/tests/product-filters.test.tsx
```

For example, a test for
`widgets/slots/product-stock-slot/stock-transaction-history-card/use-stock-transaction-history-card.ts`
must be located at
`widgets/slots/product-stock-slot/stock-transaction-history-card/tests/use-stock-transaction-history-card.test.ts`.
Do not colocate `.test.ts` or `.test.tsx` files beside the widget entrypoint or
hook implementation. Passing the test-integrity ownership check does not waive
this directory-placement rule; ownership and test placement are separate
requirements.

Do not place Vitest widget tests in a parent page's `tests/` directory, a
feature-level test directory, or a generic shared test folder. If a nested widget
warrants its own test, place it in that nested widget's `tests/` directory. Tests
for a widget's own behavior hook use the same directory. Query/action hooks do
not receive test files.

Use `.test.tsx` for React component tests and `.test.ts` for hook or non-React
Vitest tests. Playwright browser integration tests use the same `.test.ts` or
`.test.tsx` convention and are identified by their module-owned location under
`apps/web/tests`.

All `describe` labels and test-case descriptions are written in English. Use the
exported widget or hook name for the top-level `describe`:

```ts
describe('AppLayout', () => {
  it('delegates navigation when a sidebar item is clicked', () => {
    // ...
  })
})
```

Descriptions state behavior and outcome. Avoid labels such as `works`, `test 1`,
or method-name-only descriptions.

## Use Vitest and Testing Library

Use Vitest for the runner, assertions, spies, and mocks. Use Testing Library to
render components and hooks and to interact with them.

Prefer accessible queries in this order:

- role and accessible name;
- label or placeholder when appropriate for a form control;
- visible text;
- `data-testid` only when no semantic query can express the behavior.

Use `fireEvent` for the current interaction level. Assertions should focus on
rendered content and accessible state such as `aria-current`, `role`, `name`,
`aria-disabled`, and `disabled`. Prefer assertions that describe the user-visible
outcome (`toHaveTextContent`, `toBeDisabled`, `toHaveAttribute`, `toBeVisible`)
over implementation calls. Callback assertions are appropriate only when the
callback is the owning widget's public boundary, and must be paired with an
assertion that the resulting UI state is correct when the result is observable.

Do not use `toBeTruthy()` as the primary assertion for a rendered element. Use an
accessible query and assert the property that matters. Avoid snapshots and
class-name assertions for behavior already expressed semantically.

Clean up rendered components and reset mutable mocks between tests. Configure a
fresh return value in `beforeEach` when a mocked hook drives the widget state.

Each test must be independent: do not rely on test order, shared mutable
fixtures, a previous URL, or a previous mock call count. When a test uses a
factory for a controller or service mock, create a fresh factory result per
test and override only the behavior under examination.

## Widget-hook tests cover hook-owned behavior

Use `renderHook` only for a page/widget's colocated behavior-owning hook when a
separate hook test materially clarifies state, derived values, effects, guards or
handlers that cannot be covered cleanly through rendered behavior. Use `act`
when an operation updates React state.

Do not create dedicated tests for domain query hooks or action hooks. Their
request inputs, pending/error/success behavior, invalidation and recovery must be
asserted through the consuming widget/page, with route integration coverage when
URL or HTTP behavior is involved. Web REST services do not receive dedicated
tests; the consuming widget and route suite own their observable transport
mapping and outcome assertions.

Mock the nearest application abstraction rather than the third-party hook beneath
it. For example, `useAppLayout` tests mock `useUrlPathname`, not TanStack Router's
`useLocation`.

When a widget hook consumes a domain-specific query/action hook, its focused hook
test may mock that domain hook. Do not test the lower query/action hook
separately and do not reconstruct or test React Query itself.

Component tests always replace the owning hook with the typed mock described
above. A consumer hook test should verify its complete state and action matrix,
not only one happy-path mutation. The complete contract includes every public
returned data, state, derived value, and callable handler or integration
function. Each returned item must be exercised through an observable assertion
or an explicit state-transition assertion. Cover every branch that selects a
mutation, maps an error, changes pending state, resets state, or emits a success
effect.

For example,
`stock-transaction-history-card/tests/use-stock-transaction-history-card.test.ts`
must cover all of the hook's returned filters, query/status values, selected
brand information, transaction-page data, pagination handler, filter handlers,
clear action, and refetch function. A test that only checks one filter handler
is incomplete even when the hook's file-level coverage threshold passes.

For realtime hooks, the hook that owns a provider subscription must cover event
mapping and cleanup. A higher-level hook consuming it mocks that application hook
instead of mocking the provider directly.

## Hook mock names mirror the hook

Create the typed mock with `vi.mocked` and name it by appending `Mock` to the hook
name:

```ts
vi.mock('../use-app-layout', () => ({
  useAppLayout: vi.fn(),
}))

const useAppLayoutMock = vi.mocked(useAppLayout)
```

Use `useUrlPathnameMock`, `useIntakesQueryMock`, and equivalent names. Do not use
generic names such as `hookMock`, `mockedHook`, or `mockUseAppLayout`.

Interaction spies follow the same subject-first convention, for example
`anchorOnClickMock` or `handleSidebarToggleMock`.

## Widget mocks reuse the widget's own prop type

When a widget must be mocked, import and use its exported prop type:

```tsx
import type { AnchorProps } from '@/ui/shared/widgets/components/anchor'

vi.mock('@/ui/shared/widgets/components/anchor', () => ({
  Anchor: ({ children, route, ...props }: AnchorProps) => (
    <a href={ROUTES[route]} {...props}>
      {children}
    </a>
  ),
}))
```

Never recreate the prop shape with React utility types, inline object types, or
`any`. A mock must fail to compile when the real widget contract changes.

If a mock factory needs a spy before imports are evaluated, declare it with
`vi.hoisted`. Keep mocks behaviorally minimal while preserving the public contract
needed by the test.

## Mock application wrappers, not third-party libraries

Consumer tests mock the HMS wrapper around a third-party primitive. For navigation,
mock `Anchor`; do not mock TanStack Router's `Link` and do not create an inline
replacement for the router library in every test.

The same rule applies to other established boundaries:

- mock `Icon` rather than Lucide when icon rendering is irrelevant;
- mock `useUrlPathname` rather than `useLocation`;
- mock a domain query hook rather than a generic `useQuery` result;
- mock a domain realtime hook rather than the provider client.

Mock the library directly only when the unit under test is the application wrapper
itself.

Do not mock the owning widget's internal children merely to bypass difficult
setup. If a dialog, menu, table, or form is part of the widget's public behavior,
render it and interact through its accessible interface. Mock a child only when it
has an independent public contract covered elsewhere and its behavior is outside
the current test's scope; use the child's exported prop type for the mock.

## Reuse canonical constants in tests

Tests import `ROUTES` and other canonical constants. Do not repeat route strings,
sidebar item arrays, or production mapping objects in fixtures.

Use route constants when configuring mocks and asserting navigation:

```ts
useAppLayoutMock.mockReturnValue({
  pathname: ROUTES.curriculum,
  primaryItems: expectedPrimaryItems,
  secondaryItems: expectedSecondaryItems,
  // ...
})
```

Literal strings remain appropriate when the string itself is the behavior under
test, such as visible copy or an intentionally invalid value.

## Navigation has unit and integration boundaries

A layout unit test must cover the user's click and verify that navigation is
delegated to the application navigation wrapper with the canonical route. It does
not need to boot a real TanStack Router.

Actual URL transitions, route loading, history behavior, and rendered destination
pages belong to integration tests with the router configured.

Route integration tests live under `apps/web/tests`, use the configured Playwright
fixture with mocked transport, and must assert more than a successful HTTP stub.
For each critical route flow, assert the final URL, visible destination state,
protected redirect, and the outgoing request method/path/query/body that proves
the UI-to-API contract. This mocked route coverage must not be confused with the
explicit HTTP-handler integration suites outside `apps/web/tests/routes/`, which may
use the local FastAPI service and real database state to verify a registered handler's
HTTP, cookie, and persistence boundary. Neither suite replaces the widget tests'
real composition coverage. Do not count a test as end-to-end if it never exercises
the route's actual loader, middleware, or rendered destination.

## Completion criteria for a widget test suite

Before marking a widget complete, review the suite against this checklist:

- the primary component test mocks the owning hook and renders the real internal
  widget composition;
- a dedicated hook test or linked route integration test covers the real owning
  hook behavior when the widget has one;
- each meaningful state and action branch has a user-observable assertion;
- error and pending paths are tested, not only successful callbacks;
- URL/API contracts are asserted where the widget owns filters, pagination, or
  mutations;
- no test passes solely because a mocked handler was called;
- typecheck and the focused Vitest suite pass, with Playwright used for route,
  authentication, form, and REST integration changes.

Active-item logic belongs to the layout behavior and must be covered at the owning
layout boundary. Include at least:

- an exact active path;
- a nested path that keeps its parent item active;
- normalization of a trailing slash from the observed pathname;
- the exact-only Home exception.

Assert active navigation through `aria-current='page'`, not through CSS classes.

## Test the fixed profile constraint in the layout hook

While the application profile is intentionally fixed, `useAppLayout` tests must
assert that it returns the canonical primary and secondary navigation entries.
They must also protect the removal of Communication from the current navigation
model.

When authenticated profiles replace the temporary fixed value, update the hook
test to cover profile selection rather than deleting the assertion without a
replacement.
