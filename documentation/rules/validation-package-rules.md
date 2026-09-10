---
description: Rules for owning, composing, exporting, and consuming reusable Zod schemas through @scoops/validation.
---

# Validation Package Rules

These rules apply to `packages/validation` and to any application code that
defines or consumes a reusable Zod schema.

`@scoops/validation` is the shared runtime-validation boundary for browser
forms, REST input, route-search parameters, environment configuration, and
event payloads. It standardizes the shape and syntactic validity of data; it
does not own authorization or business decisions.

## Ownership and dependency direction

- Reusable Zod schemas belong in `packages/validation`, not in `apps/web`,
  `apps/server`, or `packages/core`.
- `@scoops/validation` may depend on `zod` and `@scoops/core`. It must not
  import either application, React, NestJS, Drizzle, Inngest, provider SDKs,
  browser globals, or `process.env`.
- `@scoops/core` must never import `@scoops/validation`. Core owns domain
  meaning and remains framework- and validation-library-independent.
- The web and server applications may import `@scoops/validation` from its
  package root. Do not use deep imports into `packages/validation/src`.
- A server compatibility module may re-export a shared schema from its existing
  local path while callers are migrated. It must contain no duplicate schema
  definition and should not become a second public contract.

## Schema placement and naming

Keep every schema in its own kebab-case file under the appropriate concern:

```text
packages/validation/src/
├── identity/       identity inputs and reusable identity primitives
├── mrp/            catalog, stock, and production inputs
├── web/            browser-form and route-search schemas
├── environment/    browser, server, and seed configuration schemas
└── communication/  message and event payload schemas
```

- A schema file exports one primary `camelCase` schema whose name ends in
  `Schema`; for example, `register-product-schema.ts` exports
  `registerProductSchema`.
- Keep shared primitive schemas in their own files. Compose them in higher-level
  schemas instead of repeating string, UUID, email, password, or enum rules.
- A module may contain private constants or refinements required by its primary
  schema, but it must not define a second reusable schema.
- Add every public schema to `src/index.ts`. The root barrel is the package's
  stable consumer API; do not add directory barrels only to shorten internal
  imports.
- Internal relative imports and re-exports use explicit `.ts` extensions, as
  required by the package's source-backed TypeScript setup.

## Core structures and enums

When the domain already exposes a runtime structure, derive the Zod enum from
that structure:

```ts
import { UserProfile } from "@scoops/core/identity/domain/structures";
import { z } from "zod";

export const userProfileSchema = z.enum(UserProfile);
```

Do not reproduce core-owned enum members as literal arrays. Literal Zod enums
are acceptable only when the values are not represented by a core runtime
structure, such as a package-local configuration mode.

## Consumer boundaries

- Web forms use React Hook Form with `zodResolver` and a schema imported from
  `@scoops/validation`. Form state, submit orchestration, field registration,
  pending state, and toast feedback remain in the web application.
- Route declarations use shared route-search schemas rather than declaring a
  second local schema.
- Server controllers, messaging jobs, and environment providers parse their
  framework input with the shared schema at their respective boundary.
- Infer request and form types from the schema when useful; do not hand-maintain
  a duplicate structural type for the same payload.
- Schemas may improve feedback and reject malformed input, but they must not
  encode authorization, tenant ownership, persistence checks, or business
  invariants. The server and core use case remain authoritative.

## Change and validation workflow

When adding or changing a reusable schema:

1. Check whether an existing primitive or composed schema can be reused.
2. Confirm that any enum has a core runtime structure before introducing a
   literal enum.
3. Add or update exactly one schema module and its root-barrel export.
4. Update every affected web and server consumer together; add
   `@scoops/validation` as a local package dependency only in packages that
   import it.
5. Run `pnpm --dir packages/validation check:code` and
   `pnpm --dir packages/validation check:types`, followed by the relevant
   consumer checks and tests.

If a schema change changes product-visible validation or an authoritative
business rule, also follow the owning module's PRD and layer rules. A shared
schema alone does not authorize changing the product contract.
