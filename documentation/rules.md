---
description: Dynamic context discovery router for selecting the repository rules required by each task.
---

# Repository Rules

This document is the entry point for the rules under `documentation/rules`. Read
it before starting repository work, then load only the rule documents that match
the task's paths and architectural impact.

For feature SDD, also read [`sdd.md`](sdd.md). It defines the Confluence PRD
source/version contract, local delivery-disposition lifecycle, artifact ownership,
statuses, workflow transitions, and mandatory SDD authority preflight; this router
still owns selection of the task-specific Rule Pack.

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
| [`typescript-conventions-rules.md`](rules/typescript-conventions-rules.md) | Creating, changing, or reviewing TypeScript/JavaScript source and tooling. | `apps/web/**`, `packages/**/*.ts`, repository TypeScript tooling |
| [`python-conventions-rules.md`](rules/python-conventions-rules.md) | Creating, changing, or reviewing Python source, tests, typing, imports, naming, or Python tooling. | `apps/server/**/*.py`, `apps/server/pyproject.toml`, `apps/server/tests/**` |
| [`ui-layer-rules.md`](rules/ui-layer-rules.md) | Creating or changing web UI, widgets, layouts, hooks, contexts, browser environment values, or web REST adapters. | `apps/web/src/ui/**`, `apps/web/src/constants/**`, `apps/web/src/rest/**` |
| [`web-app-routing-rules.md`](rules/web-app-routing-rules.md) | Creating or changing TanStack routes, route constants, middleware, search validation, or generated route metadata. | `apps/web/src/routes/**`, `apps/web/src/constants/routes.ts`, `apps/web/src/routeTree.gen.ts` |
| [`widget-testing-rules.md`](rules/widget-testing-rules.md) | Creating or changing React widget, layout, hook, page, navigation, or browser tests. | `apps/web/src/**/*.test.ts`, `apps/web/src/**/*.test.tsx`, `apps/web/tests/**` |
| [`core-layer-rules.md`](rules/core-layer-rules.md) | Changing Python domain entities, structures, errors, events, interfaces, use cases, or module boundaries. | `apps/server/src/shifu/**/core/**` |
| [`email-package-rules.md`](rules/email-package-rules.md) | Creating, changing, exporting, or consuming the standalone Communication-owned React Email package, templates, or HTML render helpers. | `packages/email/**`, `@scoops/email/templates` |
| [`validation-package-rules.md`](rules/validation-package-rules.md) | Creating or consuming reusable web Zod schemas. Backend HTTP schemas follow the REST rules instead. | `packages/validation/**`, web Zod schemas |
| [`use-case-testing-rules.md`](rules/use-case-testing-rules.md) | Creating or changing Python core use cases, unit tests, domain fakers, or mocked ports. | `apps/server/src/shifu/**/core/use_cases/**`, `apps/server/tests/core/**` |
| [`server-app-layer-rules.md`](rules/server-app-layer-rules.md) | Changing FastAPI creation, application composition, router registration, middleware, lifespan, or dependency pipes. | `apps/server/src/main.py`, `apps/server/src/shifu/app.py`, `apps/server/src/shifu/composition/**`, `apps/server/src/shifu/**/pipes/**` |
| [`rest-layer-rules.md`](rules/rest-layer-rules.md) | Adding or changing FastAPI routers/controllers, Pydantic transport schemas, dependency wiring, error handlers, OpenAPI contracts, or web API adapters. | `apps/server/src/shifu/**/rest/**`, `apps/web/src/rest/**` |
| [`controllers-testing-rules.md`](rules/controllers-testing-rules.md) | Creating or changing FastAPI controller tests, TestClient fixtures, HTTP assertions, or database-backed route setup. | `apps/server/tests/rest/controllers/**`, `apps/server/tests/fixtures/**`, `apps/server/tests/conftest.py` |
| [`database-layer-rules.md`](rules/database-layer-rules.md) | Changing SQLAlchemy sessions, models, mappers, repositories, Alembic migrations, seeders, or database fixtures. | `apps/server/src/shifu/**/database/**`, `apps/server/migrations/**`, database fixtures under `apps/server/tests/**` |
| [`provision-layer-rules.md`](rules/provision-layer-rules.md) | Creating or changing provider ports/adapters, external SDKs, environment settings, clocks, IDs, storage, auth, sandbox, or provider pipes. | `apps/server/src/shifu/**/providers/**`, `apps/server/src/shifu/**/pipes/**`, provider interfaces under `core/interfaces` |
| [`messaging-layer-rules.md`](rules/messaging-layer-rules.md) | Creating or changing domain events, broker adapters, Inngest clients/endpoints, jobs, durable steps, fan-out, retries, or outbox delivery. | `apps/server/src/shifu/**/messaging/**`, domain events, shared Inngest infrastructure |
| [`jobs-testing-rules.md`](rules/jobs-testing-rules.md) | Creating or changing Inngest job integration tests or their Docker/runtime fixtures. | `apps/server/tests/messaging/inngest/jobs/**`, Inngest fixtures under `apps/server/tests/fixtures/**` |
| [`ai-layer-rules.md`](rules/ai-layer-rules.md) | Creating or changing Mentor, Goal Planner, AI/NLP workflows, prompts, model adapters, structured outputs, TF-IDF, or classifiers. | `apps/server/src/shifu/intelligence/ai/**`, AI provider adapters and workflow interfaces |
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
| Add or change a reusable web Zod schema | Validation Package; add the consuming UI or Web Routing rules |
| Create or change an email template | Email Package + Code Conventions; add Messaging or Provider rules when changing delivery |
| Add a complete FastAPI operation | Python Conventions + Core Domain + REST; add Database when persistence changes and Controller Testing + Use Case Testing for their boundaries |
| Change a Python use case | Python Conventions + Core Domain + Use Case Testing |
| Change FastAPI composition or middleware | Python Conventions + Server Application; add Database, Messaging, or Provider rules for each managed lifecycle |
| Add or change a provider | Python Conventions + Provider Layer + Core Domain; add Use Case Testing when a use case consumes it |
| Add or change an Inngest job | Python Conventions + Messaging + Job Testing; add Core Domain for events/use cases and Provider or Database rules for adapters used by the job |
| Add or change an AI workflow | Python Conventions + AI Layer + Core Domain; add Messaging for asynchronous execution and Provider for external model adapters |
| Change a database-backed controller test | Python Conventions + REST + Controller Testing + Database |
| Create a commit | Commit Rules, plus the implementation rules already selected for validating the changed scope |

## Re-evaluate when scope changes

Discovery is continuous during a task. Stop and load additional rules before
working in a newly discovered layer. Examples:

- a widget change needs a new route: add UI Layer if it was not already loaded;
- a FastAPI controller needs a repository method: add Core Domain and Database;
- a controller introduces reusable dependency wiring: add Server Application;
- a use case starts depending on time, randomness, storage, sandboxing, or another
  external capability: add Provider Layer;
- a domain event starts or changes asynchronous work: add Messaging and Job Testing;
- an AI workflow persists official results: add Core Domain and Database, and keep the
  owning module authoritative;
- implementation adds tests: add the testing rule for that test boundary.

Do not continue under an incomplete rule set merely because the additional work
was discovered after implementation started.
