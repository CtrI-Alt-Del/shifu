---
description: How to write commit messages in this repository — Conventional Commits, enforced by commitlint + husky.
---

# Commit Rules

This repository uses **[Conventional Commits](https://www.conventionalcommits.org/)**,
enforced automatically by **commitlint** + **husky**. Every commit message is
validated by the `commit-msg` git hook; a message that violates the rules is
rejected and the commit does not happen.

The configuration lives in [`commitlint.config.mjs`](../../commitlint.config.mjs)
(extends `@commitlint/config-conventional`).

---

## Format

```
<type>(<scope>): SHIFU-<number> <subject>

<body>

<footer>
```

Only the **first line** (`type` + optional `scope` + `subject`) is required.

Example:

```
feat(web): SHIFU-138 add sign-up form validation
```

---

## Type (required)

The type must be one of the following (this is the exact `type-enum` enforced by
commitlint):

| Type       | Use for                                                        |
| ---------- | ------------------------------------------------------------- |
| `feat`     | a new feature                                                 |
| `fix`      | a bug fix                                                     |
| `refactor` | a code change that neither fixes a bug nor adds a feature     |
| `perf`     | a change that improves performance                            |
| `docs`     | documentation only                                            |
| `test`     | adding or correcting tests                                    |
| `style`    | formatting, whitespace, semicolons — no logic change          |
| `build`    | build system, dependencies, bundling                         |
| `ci`       | CI configuration and scripts                                  |
| `chore`    | tooling, config, housekeeping that doesn't fit the above      |
| `revert`   | reverts a previous commit                                     |

The type must be **lowercase**.

---

## Scope (optional, recommended)

The scope is the area of the codebase affected. In this monorepo prefer:

- `web` — the TanStack Start frontend (`apps/web`)
- `server` — the FastAPI backend (`apps/server`)
- `core` — framework-independent domain code inside the server modules

You may use a more specific scope when it adds clarity, but keep it short and
lowercase. Omit the scope only when the change is genuinely cross-cutting
(e.g. root tooling: `chore: ...`).

---

## Subject (required)

- begin with a Jira key matching `SHIFU-<number>`;
- **imperative mood**: "add", "fix", "remove" — not "added", "adds", "adding"
- **lowercase first word**: commitlint's `subject-case` rule rejects
  sentence-case, Start-Case, PascalCase and UPPER-CASE — so write
  `fix(web): correct image loading`, not `fix(web): Correct image loading`
- **no trailing period**
- **describe the *why*, not the *what*** when the diff alone isn't obvious
- the whole header (type + scope + subject) must be **≤ 100 characters**; aim for
  ≤ 50 on the subject itself

---

## Body (optional)

- separated from the subject by a **blank line**
- wrap lines at ~72–100 characters
- use it to explain motivation, tradeoffs, or non-obvious context
- use `-` for bullet points, not `*`
- skip it entirely when the subject is self-explanatory

Always include a body for: breaking changes, security fixes, data migrations, and
reverts.

---

## Footer (optional)

- separated from the body by a **blank line**
- reference issues: `Closes #123`, `Refs #45`
- declare breaking changes (see below)

---

## Breaking changes

Either append `!` after the type/scope, or add a `BREAKING CHANGE:` footer (or both):

```
feat(core)!: rename Person.documentId to Person.taxId

BREAKING CHANGE: consumers reading `documentId` must switch to `taxId`.
```

---

## Examples

Good:

```
feat(web): SHIFU-138 add product listing page
fix(server): SHIFU-138 correct health check version
refactor(core): SHIFU-138 extract consent validation into use case
docs: SHIFU-138 add commit rules
test(web): SHIFU-138 cover sign-up page with integration tests
chore: SHIFU-138 configure commitlint and husky commit hooks
```

Rejected by the hook:

```
added new stuff                              # no type or Jira key
Feat: SHIFU-138 Add Page                      # type and subject case are invalid
feature(web): SHIFU-138 add page              # "feature" is not in type-enum
fix(web): correct image loading               # missing Jira key
fix(web): SHIFU-138 correct image loading.    # trailing period
```

---

## Hooks & enforcement

- The `commit-msg` hook ([`.husky/commit-msg`](../../.husky/commit-msg)) runs
  `commitlint --edit` on every commit.
- **Do not bypass the hook** with `git commit --no-verify` (`-n`). If a message is
  being rejected, fix the message — the rule is the same for everyone.
- The hooks are installed automatically after `pnpm install` via the `prepare`
  script in the root `package.json`.

To test a message manually without committing:

```
echo "feat(web): SHIFU-138 add sign-up form" | pnpm exec commitlint
```

---

## Relationship to PR titles

Commit messages follow Conventional Commits (this document). **PR titles do not** —
they are plain noun phrases without a type prefix. See
[`documentation/prompts/create-pr-prompt.md`](../prompts/create-pr-prompt.md).
