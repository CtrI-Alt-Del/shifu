---
description: TypeScript and JavaScript conventions for the Shifu web application and tooling.
---

# Code Conventions

Code conventions are the rules and practices used to keep the Shifu codebase
consistent, readable, and maintainable by everyone on the project.

These conventions apply to TypeScript and JavaScript source code in `apps/web/`, future
TypeScript packages, and repository tooling unless a more specific rule refines them.
Python code follows [`python-conventions-rules.md`](python-conventions-rules.md).

## Language

All code is written in English, including variable names, functions, types,
comments, and exported contracts. User-facing copy may use the product's
language.

## Naming variables, types, objects, and functions

### `camelCase`

Local variables, object properties, function parameters, and regular
functions/methods use [camelCase](https://developer.mozilla.org/en-US/docs/Glossary/Camel_case).

### `PascalCase`

Classes, interfaces, types, React components, and factory functions use
`PascalCase`.

React hooks use the `use<Name>` form, such as `useSignInPage` or
`useClientRegisterDialog`.

### Descriptive and clear names

Choose names that clearly communicate the purpose of the value. Prefer
`productsList` over `pl` or `items` when the context does not make the meaning
obvious.

Avoid redundant names when the surrounding context already provides the
meaning:

```ts
const controller = new FetchLastWeekRankingWinnersController();
```

is preferred over:

```ts
const fetchLastWeekRankingWinnersController =
  new FetchLastWeekRankingWinnersController();
```

### Boolean variables

Use prefixes such as `is`, `has`, `can`, and `should` for boolean values:

```ts
const isActive = true;
const hasPermission = false;
const canEdit = true;
const shouldRetry = false;
```

Use `should` when the value indicates whether an action ought to be performed.
Use `can` when it represents capability or permission.

### Collection variables

Use plural names for arrays and lists:

```ts
const users = [];
const achievements = [];
const unlockedStars = [];
```

### Number variables

Use the `count` suffix when a number represents a quantity:

```ts
const upvotesCount = 0;
const completedChallengesCount = 0;
const unlockedStarsCount = 0;
```

The suffix is not required for nouns that are inherently numeric, such as
`height`, `level`, and `margin`.

### Constants

Module-level constants use uppercase [snake_case](https://www.theserverside.com/definition/Snake-case):

```ts
const BETTER_AUTH_URL = "https://api.example.com";
const HEADER_HEIGHT = 64;
const EVENT_KEY = "intake.created";
```

Constants scoped inside a function may use a local name when their lifetime and
meaning are limited to that render or invocation.

### Interfaces

When an imported interface has the same name as a class or factory function,
alias the interface with an `I` prefix:

```ts
import { ProfileService as IProfileService } from "./profile-service";
```

### Functions and handlers

Regular functions should start with an imperative verb, such as `unlockStar`,
`earnCoins`, or `acquireAvatar`. Factory functions are the exception and use a
noun in `PascalCase`.

User-interaction handlers use the `handle` prefix and describe the action, such
as `handleSubmit`, `handleClose`, or `handleTogglePasswordVisibility`.
`on*` names are reserved for callback props and external contracts, not for
implementation functions.

## Function declarations

Use function declarations for helpers, page/controller hooks, event handlers,
service utilities, and other named functions:

```ts
function handleSubmit(values: FormValues) {
  // ...
}
```

React component definitions may use the established component form:

```tsx
export const SignInPage = () => {
  // ...
};
```

Factory functions follow the dedicated factory convention below and are declared
as PascalCase arrow functions assigned to constants.

## Class-owned functions stay inside the class

Do not declare a loose module-level function when it exists only to support one
class in the same file. Serialization, mapping, normalization, validation, and
other behavior owned exclusively by that class must be implemented as a private
method of the class.

```ts
export class DocumentTool {
  execute() {
    return this.serializeDocument();
  }

  private serializeDocument() {
    // ...
  }
}
```

Do not place the helper after or before the class as an unexported standalone
function:

```ts
export class DocumentTool {
  execute() {
    return serializeDocument();
  }
}

function serializeDocument() {
  // Invalid: this behavior belongs only to DocumentTool.
}
```

A module-level function is allowed only when it is genuinely independent of a
class, is shared by multiple declarations, or is intentionally exposed as the
module's functional API. Do not move class-owned behavior out of a class merely
to shorten the class body.

## Known application failures use AppError

Do not throw the native `Error` class directly from application, domain,
infrastructure, provider, repository, controller, job, tool, agent, or workflow
code when the failure is known and can be described by the application.

Use `AppError` or a specific subclass owned by the appropriate module:

```ts
throw new AppError(
  "A credencial do provedor é obrigatória.",
  "Erro de Configuração",
);
```

Prefer a named `AppError` subclass when the same failure can occur in more than
one location, participates in control flow, needs distinct REST mapping, or is a
business error. Do not use a generic native error merely because the failure is
technical rather than business-related.

Errors received from third-party libraries may remain native while being caught,
but application code must translate a known failure before exposing or throwing
it across an HMS boundary. Test assertions and fixture guards are outside this
rule because they do not represent runtime application failures.

## Declaration and destructuring order

Keep values and state before functions in declaration lists and destructured
controller results. Use this order when a hook returns a widget controller:

1. data, state, status, and derived values;
2. event handlers and other named functions;
3. library integration helpers such as `register`.

For example:

```tsx
const {
  error,
  showPassword,
  isLoading,
  handleSubmit,
  handleTogglePasswordVisibility,
  register,
} = useSignInPage();
```

Keep the returned object in the same order as the public controller contract so
the hook and its consumer communicate the same shape consistently.

## File naming

File and directory names use `kebab-case` throughout the repository:

```text
app-error.ts
profile-page-view.tsx
use-pagination.ts
special-characters.ts
user-schema.ts
```

React widgets use `index.tsx` as their directory entrypoint. This is an
application widget entrypoint, not a barrel file.

## Barrel files

A barrel file, usually named `index.ts`, re-exports multiple modules from a
directory so consumers can import them from one stable location.

Use barrels only where the module boundary benefits from a centralized public
export. Do not add an `index.ts` barrel solely for a hooks or widgets directory,
or solely to make an internal mock import shorter. Widget directories may still
use their required `index.tsx` entrypoint.

Example:

```ts
// controllers/index.ts
export { Controller1 } from "./controller-1";
export { Controller2 } from "./controller-2";
```

## Factory functions

Factory functions are preferred for creating modules that manage dependencies or
state in the functional application architecture.

They follow these conventions:

- declaration as a PascalCase arrow function assigned to a `const`;
- explicit return type when implementing an interface;
- return of an object containing the exposed methods and properties;
- arguments limited to dependencies such as services and HTTP clients;
- construction by function call, without `new`.

```ts
interface SpaceService {
  fetchPlanets(): Promise<Planet[]>;
}

export const SpaceService = (restClient: RestClient): SpaceService => {
  return {
    fetchPlanets() {
      return restClient.get<Planet[]>("/space/planets");
    },
  };
};
```

Private helper functions may be declared inside the factory and can use the
factory's dependency closure without becoming part of its public contract.

## Tooling

The HMS tooling conventions are documented in
[`documentation/tooling.md`](../tooling.md). The current standard is:

- package manager: `pnpm`, run from the owning app or package directory;
- linting and formatting: BiomeJS;
- type checking: TypeScript with `tsc`;
- tests: Vitest;
- commit hooks and message validation: Husky and commitlint.

Use the owning app or package's local commands described in the tooling
documentation instead of introducing alternative runners or formatters.
