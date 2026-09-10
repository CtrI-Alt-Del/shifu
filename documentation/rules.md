---
description: Dynamic context discovery router for selecting the repository rules required by each task.
---

# Repository Rules

This document is the entry point for the rules under `documentation/rules`. Read
it before starting repository work, then load only the rule documents that match
the task's paths and architectural impact.

For feature SDD, also read [`sdd.md`](sdd.md). It defines the canonical PRD
requirement contract and Implemented-checkbox lifecycle, artifact ownership, statuses,
workflow transitions and the mandatory SDD authority preflight; this router still owns
selection of the task-specific Rule Pack.

## Use dynamic context discovery

Rule selection follows **dynamic context discovery**. Do not load every rule for
every task and do not select rules from the user's wording alone.

Before changing files:

1. Identify the requested outcome and the files or layers likely to change.
2. Inspect the relevant repository paths when the request does not name them.
3. Match both the paths and the behavior being changed against the routing table
   below.
4. Read every matched rule document in full before implementing the change.
5. Re-run discovery whenever the task expands into another layer.

Path matching is only the first signal. Follow dependencies across boundaries. A
new REST operation, for example, may require core contracts, a server controller,
a web adapter, and tests; each affected layer activates its own rules.

Rules are additive. When several rows match, read all of them. A more specific
rule refines a broader rule within its scope; it does not cancel repository-level
instructions from `AGENTS.md`, `AGENTS.local.md`, or the required architecture,
design, infrastructure, and tooling documents.

If implementation and documentation disagree, treat the documentation as intent
and surface the discrepancy before silently copying the implementation.

## Rule routing table

| Rule | Read when | Common path signals |
| --- | --- | --- |
| [`code-conventions-rules.md`](rules/code-conventions-rules.md) | Creating, changing, or reviewing TypeScript/JavaScript source code and its naming, function declaration, or declaration-order conventions. | `apps/**`, `packages/**`, repository tooling |
| [`ui-layer-rules.md`](rules/ui-layer-rules.md) | Creating or changing web UI, widgets, layouts, hooks, contexts, routes, route middleware, sidebar configuration, icons, browser environment values, or web REST adapters. | `apps/web/src/ui/**`, `apps/web/src/constants/**`, `apps/web/src/middlewares/**`, `apps/web/src/rest/**`, `apps/web/src/routes/**` |
| [`web-app-routing-rules.md`](rules/web-app-routing-rules.md) | Creating, changing, renaming, or reviewing web application routes, route constants, route middleware, search validation, navigation paths, or generated route metadata. | `apps/web/src/routes/**`, `apps/web/src/constants/routes.ts`, `apps/web/src/middlewares/**`, `apps/web/src/routeTree.gen.ts` |
| [`widget-testing-rules.md`](rules/widget-testing-rules.md) | Creating, changing, or reviewing tests for React widgets, layouts, pages, behavior-owning widget hooks, navigation behavior, or their mocks. Query/action hooks are covered through consumers rather than dedicated hook tests. | Colocated `apps/web/src/**/*.test.ts`, `apps/web/src/**/*.test.tsx` and browser tests under `apps/web/tests/**` |
| [`core-package-rules.md`](rules/core-package-rules.md) | Changing shared domain entities, structures, errors, events, interfaces, constants, or use cases. Also read it when an app change requires a new or changed core contract. | `packages/core/src/**`, `packages/core/package.json` exports |
| [`email-package-rules.md`](rules/email-package-rules.md) | Creating, changing, exporting, or consuming the standalone Communication-owned React Email package, templates, or HTML render helpers. | `packages/email/**`, `@scoops/email/templates` |
| [`validation-package-rules.md`](rules/validation-package-rules.md) | Creating, changing, exporting, or consuming reusable Zod schemas for forms, REST input, route search, environment configuration, or event payloads. | `packages/validation/**`, Zod schema definitions in `apps/**`, `@scoops/validation` imports |
| [`use-case-testing-rules.md`](rules/use-case-testing-rules.md) | Creating or changing core use cases, their unit tests, domain fakers used by those tests, or mocked use-case dependencies. | `packages/core/src/**/use-cases/**`, `packages/core/src/**/domain/**/fakers/**` |
| [`rest-layer-rules.md`](rules/rest-layer-rules.md) | Adding or changing HTTP routes, NestJS controllers, route decorators, request-body mapping, global REST errors, `.rest` examples, core REST contracts, or web module services that consume those routes. | `apps/server/src/**/rest/**`, `apps/server/src/**/decorators/**`, `apps/server/rest-client/**`, `apps/web/src/rest/services/**`, REST interfaces in `packages/core` |
| [`controllers-testing-rules.md`](rules/controllers-testing-rules.md) | Creating or changing server controller tests, REST fixtures, HTTP assertions, or test application wiring for database-backed routes. | `apps/server/src/**/rest/controllers/tests/**`, `apps/server/src/**/fixtures/**`, `apps/server/src/shared/rest/tests/**` |
| [`database-layer-rules.md`](rules/database-layer-rules.md) | Changing Drizzle models, persistence types, mappers, repositories, repository tokens, database modules, migrations, or seeders. Also read it when a controller or use case change requires persistence work. | `apps/server/src/**/database/**`, `apps/server/src/shared/database/**`, `apps/server/drizzle.config.ts` |
| [`provision-layer-rules.md`](rules/provision-layer-rules.md) | Creating or changing server providers, web provision adapters, provider contracts, environment access, time access, provider registration, or provider mocks in use-case tests. | `apps/server/src/shared/provision/**`, `apps/web/src/provision/**`, shared provider interfaces in `packages/core`, tests mocking those providers |
| [`messaging-layer-rules.md`](rules/messaging-layer-rules.md) | Creating or changing messaging clients, Inngest modules or endpoints, event schemas, background jobs, function registries, messaging environment variables, or messaging tests. | `apps/server/src/shared/messaging/**`, `apps/server/src/**/messaging/**`, Inngest registration in `apps/server/src/app.module.ts` |
| [`commit-rules.md`](rules/commit-rules.md) | Writing, validating, or creating a commit; changing commitlint or commit hooks; or preparing a commit message for the user. | `.husky/**`, `commitlint.config.mjs`, commit operations or commit-message requests |

## Common multi-rule combinations

Use these combinations as starting points, then add rules discovered from the
actual scope:

| Task | Rules to load |
| --- | --- |
| Build or change a widget | UI Layer; add Widget Testing when tests change |
| Add or change a web application route | UI Layer + Web App Routing; add Widget Testing when navigation behavior is tested |
| Change an internal layout widget | UI Layer + Widget Testing, because behavior is tested at the owning layout boundary |
| Add a domain-specific query/action hook | UI Layer; add Widget Testing for the consuming widget/page or route behavior, not for a dedicated query/action-hook test |
| Add a realtime or behavior-owning widget hook | UI Layer + Widget Testing |
| Add a web REST service for an existing endpoint | UI Layer + REST Layer; cover transport behavior through consuming widget/page and route integration tests rather than a dedicated service test; add Core Package when the service contract changes |
| Add or change a reusable Zod schema | Validation Package; add the consuming UI, REST, Provision or Messaging rules for each affected boundary |
| Create or change an email template | Email Package + Code Conventions; add Messaging or Provision when changing the consuming job or delivery adapter |
| Add a complete REST operation | Core Package + REST Layer; add Validation Package when reusable input schemas change; add Database Layer when persistence changes; add Controller Testing and Use Case Testing for their respective tests |
| Change a use case only | Core Package + Use Case Testing |
| Add or change a shared provider | Provision Layer + Core Package; add Use Case Testing when use-case tests consume it |
| Add or change an Inngest job | Messaging Layer; add Core Package when the trigger uses a new or changed domain event; add Provision Layer when the handler needs a new external adapter |
| Change a database-backed controller test | REST Layer + Controller Testing + Database Layer |
| Create a commit | Commit Rules, plus the implementation rules already selected for validating the changed scope |

## Re-evaluate when scope changes

Discovery is continuous during a task. Stop and load additional rules before
working in a newly discovered layer. Examples:

- a widget change needs a new route: add UI Layer if it was not already loaded;
- a controller change requires a repository method: add Core Package and Database
  Layer;
- a web service exposes a new response contract: add Core Package and REST Layer;
- a form, route, controller, provider or job needs a reusable Zod schema: add
  Validation Package and the Rule for every consuming boundary;
- a use case starts depending on time or environment: add Provision Layer;
- a domain event starts or changes an asynchronous job: add Messaging Layer and
  Core Package;
- implementation adds tests: add the testing rule for that test boundary.

Do not continue under an incomplete rule set merely because the additional work
was discovered after implementation started.
