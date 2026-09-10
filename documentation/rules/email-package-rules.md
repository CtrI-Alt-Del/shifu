---
description: Rules for the standalone Communication-owned React Email package.
---

# Email Package Rules

These rules apply to `packages/email` and to imports from
`@scoops/email/templates`. The package composes transactional email messages; it
does not deliver them.

## Ownership and dependencies

- Keep reusable email markup and HTML render helpers in `packages/email`.
- Keep provider selection, credentials, retries, idempotency keys, delivery
  logging, and failure handling in the Server Communication module.
- The package may depend on React and React Email packages only. It must not
  import NestJS, Inngest, Drizzle, PostgreSQL, Better Auth, Server modules,
  provider SDKs, database contracts, environment access, or application
  feature modules.
- Templates must receive all dynamic values through typed props. They must not
  read the database, call an API, generate auth tokens, read environment
  variables, send messages, or encode provider-specific payloads.

## Package layout and public API

Use this structure for new templates:

```text
packages/email/
├── package.json
├── tsconfig.json
└── templates/
    ├── index.ts
    └── <module>/<template-name>.tsx
```

- Use kebab-case file and directory names.
- Place templates under the owning module directory, such as
  `templates/identity/`.
- Export public templates, render helpers, and their props types from
  `templates/index.ts`.
- Server consumers must import from `@scoops/email/templates`, never from an
  internal template file.

## Declaration and rendering conventions

- Export React components as PascalCase arrow-function constants using this
  exact shape:

  ```tsx
  export const EmailLayout = ({ preview, children }: EmailLayoutProps) => {
    // ...
  };
  ```

- Export render helpers as arrow-function constants as well. Keep the props type
  explicit at the public boundary.
- Define one exported props type per template file, named
  `<TemplateName>Props`.
- Keep rendering separate from delivery. A render helper may return stable
  message data such as `{ subject, html }`, but it must not call an email
  provider.
- Keep subjects and template copy deterministic for the same props. Do not add
  timestamps, random identifiers, or request-specific state during rendering.

## Markup and accessibility

- Reuse `EmailLayout` for transactional messages so preview text, document
  language, direction, spacing, and the footer remain consistent.
- Set the document language to `pt-BR` and direction to `ltr` unless a future
  localization contract explicitly changes them.
- Provide meaningful heading structure, visible button labels, and action URLs
  through real links or buttons.
- Pass user-provided values as React children or typed component props so React
  performs escaping; never concatenate untrusted values into raw HTML.
- Keep transactional copy in Portuguese and use inline-compatible styles from
  the existing templates. Avoid external CSS, client-side JavaScript, and
  layout assumptions unsupported by email clients.

## Validation

Before handing off changes to this package, run:

```bash
pnpm --dir packages/email check:code
pnpm --dir packages/email check:types
```

When a template is consumed by Server jobs, also run the Server type check and
the focused Communication job tests. Provider delivery behavior belongs in the
owning Server Communication boundary; do not add direct provider or transport
tests to the email package.
