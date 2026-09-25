---
description: Developer tooling for installing, running, validating, and testing the Shifu applications and local infrastructure.
---

# Tooling

This document describes the tooling currently available in the Shifu repository.
For architecture and technology decisions, see
[`architecture.md`](architecture.md). For path-specific engineering constraints,
see [`rules.md`](rules.md).

## Requirements

- **Node.js** `24.20.0`, selected by `.node-version`.
- **pnpm**, used by the web application and the JavaScript workspace.
  The repository does not currently pin a pnpm version in `package.json`.
- **Python** `3.13.5`, selected by `.python-version`.
- **uv**, used for server dependencies, virtual environments, and builds.
- **Docker Engine with Docker Compose**, required for PostgreSQL, Redis, Inngest,
  Mailpit, and the local SonarQube stack.

Check the runtime files before upgrading a local tool. Lockfiles and manifests are
the source of truth for exact dependency versions.

## Repository layout

Shifu is a pnpm workspace with two applications:

```text
apps/
├── web/       TanStack Start / React frontend
└── server/    FastAPI backend

packages/      Reserved for independently reusable packages
documentation/ Project and engineering documentation
```

The web application owns `apps/web/package.json`. The server owns
`apps/server/pyproject.toml` and `apps/server/uv.lock`. Do not copy package names,
scripts, ports, or environment variables from another repository.

## Installation

Install JavaScript dependencies from the repository root:

```bash
corepack enable
pnpm install
```

Install and synchronize Python dependencies from the server directory:

```bash
cd apps/server
uv sync
```

Run repository synchronization scripts from the root:

```bash
pnpm sync:agents
pnpm sync:commands
```

`sync:agents` updates generated agent configuration for supported coding tools.
`sync:commands` synchronizes prompt commands and skills from
`documentation/prompts`.

Add web dependencies with pnpm from the repository root:

```bash
pnpm --filter web add <package>
pnpm --filter web add --save-dev <package>
```

Add server dependencies with uv from `apps/server`:

```bash
uv add <package>
uv add --dev <package>
```

Commit the relevant lockfile whenever dependencies change:

- JavaScript changes update the root `pnpm-lock.yaml`.
- Python changes update `apps/server/uv.lock`.

Do not create an npm, yarn, or pip lockfile for this repository.

## Environment configuration

The root `.env.example` configures Docker Compose. Each application owns its local
environment file and port settings:

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
cp apps/server/.env.example apps/server/.env.local
```

Never commit credentials, tokens, private keys, local database files, or real service
credentials. The `.env.local` files are ignored by Git.

Important local variables include:

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_PORT` | `54344` | PostgreSQL host port |
| `REDIS_PORT` | `6379` | Redis host port |
| `INNGEST_PORT` | `18288` | Inngest UI/API host port |
| `SONAR_PORT` | `19000` | SonarQube web/API host port |
| `MAILPIT_UI_PORT` | `54326` | Mailpit web UI host port |
| `INNGEST_APP_URL` | `http://host.docker.internal:7777/api/inngest` | FastAPI Inngest endpoint discovered by the existing Compose Dev Server |

Only browser-safe variables may be exposed through `VITE_` variables.

## Local infrastructure with Docker Compose

Start the local services from the repository root:

```bash
docker compose up -d
docker compose ps
docker compose logs -f
```

The Compose stack provides:

- PostgreSQL 17 for application data;
- Redis 8 for server cache and rate limiting;
- Inngest development server;
- Mailpit for local mail capture; and
- SonarQube with its PostgreSQL database.

Default endpoints are:

| Service | URL or address |
| --- | --- |
| PostgreSQL | `postgresql://shifu:change-me@localhost:54344/shifu` |
| Redis | `redis://localhost:6379/0` |
| Inngest | `http://localhost:18288` |
| Mailpit UI | `http://localhost:54326` |
| Mailpit SMTP | `localhost:1026` |
| SonarQube | `http://localhost:19000` |
| Web application | `http://localhost:7000` |
| FastAPI application | `http://localhost:7777` (fallback) |

Stop containers without deleting named volumes:

```bash
docker compose down
```

Do not delete Docker volumes or reset local databases unless explicitly requested.

The existing Compose Inngest service is the development Dev Server. It starts with
`-u ${INNGEST_APP_URL}` and reaches the host FastAPI process through the Linux
`host-gateway` mapping. Job integration tests use disposable Testcontainers
instead, so they do not reuse this persistent development instance. For local
development, start FastAPI first, then verify that the application is discovered
at `http://localhost:18288`:

```bash
docker compose up -d inngest
curl http://localhost:18288/e/health
```

The server registers the logging-only Identity job at `/api/inngest`; no second
Inngest process or obsolete `pubsub` task is required.

From `apps/server`, configure `DATABASE_URL` in `.env.local` and run:

```bash
uv run poe db:current
uv run poe db:upgrade
uv run poe db:seed
```

The seed command executes `shifu.shared.database.seed` and is the only supported
entrypoint for local seed composition. Its two operational composition modules are
the explicit Tach exclusions in `check:architecture`; do not widen that exclusion.

`db:seed` is destructive for the application tables and is guarded to `local` mode.
It checks that the database is at the current Alembic head before deleting any
data; if it reports an older revision, run `db:upgrade` first. All `db:*` Poe
commands load the same `.env.local` file. Seeding is never run during FastAPI
startup.

The local development seed creates the active account
`student.seed@shifu.com` with the fixed password `ShifuSeed123!`.
It also provides a ready-to-start adaptive Learning laboratory. See the
[seed scenario guide](features/learning/adaptive-recommendation/seed-scenarios.md)
for its curriculum, learner path, and expected progress. A local reseed clears
pending outbox events along with the previous application data.

## Running the applications

Set each application port in its ignored app-local `.env.local` file:

```dotenv filename="apps/web/.env.local"
SHIFU_WEB_APP_PORT=7000
VITE_SHIFU_SERVER_URL=http://localhost:7777
```

```dotenv filename="apps/server/.env.local"
SHIFU_SERVER_APP_PORT=7777
```

Vite reads the web values from `apps/web/.env.local`. The server launcher reads
`SHIFU_SERVER_APP_PORT` from `apps/server/.env.local`.

Start the web application from the repository root:

```bash
pnpm --filter web dev
```

The web port is `7000` by default and can be changed with `SHIFU_WEB_APP_PORT`.
Regenerate TanStack route metadata when route files change:

```bash
pnpm --filter web generate-routes
```

The generated `apps/web/src/routeTree.gen.ts` file is tool-owned and must not be
edited manually.

Start the FastAPI application from `apps/server`:

```bash
uv run --env-file .env.local python src/main.py
```

The application exposes the shared health endpoint at `GET /health`.

## Web tooling

The web stack uses TypeScript, React, TanStack Start/Router, Vite, Tailwind CSS,
Axios, Zod, and Biome. The test stack uses Vitest, Testing Library, jsdom, and
Playwright.

| Command | Purpose |
| --- | --- |
| `pnpm --filter web dev` | Start the development server |
| `pnpm --filter web generate-routes` | Generate TanStack route metadata |
| `pnpm --filter web check:types` | Run TypeScript strict no-emit checking |
| `pnpm --filter web check:lint` | Run Biome checks |
| `pnpm --filter web check:architecture` | Check TypeScript dependency boundaries |
| `pnpm --filter web test:unit` | Run Vitest unit tests |
| `pnpm --filter web test:integration` | Run Playwright browser tests |
| `pnpm --filter web build` | Build the TanStack Start application |
| `pnpm --filter web preview` | Preview the Vite production build |

Biome is configured centrally in the root `biome.json`. Formatting uses two spaces,
a 90-character line width,
single quotes, JSX single quotes, and semicolons only when required. Biome does
not own generated route metadata.

Dependency Cruiser uses `apps/web/dependency-cruiser.config.cjs` to reject circular
dependencies and invalid web layer direction. Keep routes, UI, core contracts, and
REST adapters within the boundaries described in `architecture.md` and the selected
rules under `documentation/rules`.

Install the Playwright browser on a new machine when browser tests are required:

```bash
pnpm --filter web exec playwright install chromium
```

Use the repository's Playwright configuration for committed browser tests. For
manual browser inspection, use the Playwright CLI workflow described by the local
agent instructions. Browser output and screenshots are temporary validation artifacts
and must not be committed.

## Server tooling

The server uses Python 3.13, FastAPI, Pydantic, uv, Poe the Poet, Ruff,
basedpyright, pytest, and Tach.

Run commands from `apps/server` through uv:

| Command | Purpose |
| --- | --- |
| `uv run poe check:types` | Run strict basedpyright checking |
| `uv run poe check:lint` | Run non-mutating Ruff lint and format checks |
| `uv run poe check:architecture` | Validate Tach module dependencies |
| `uv run poe test:unit` | Run module-first use-case tests under `tests/<module>/core/use_cases` plus legacy `tests/core/**/use_cases` during migration |
| `uv run poe test:integration` | Run module-first server integration tests under `tests/<module>/server` plus legacy `tests/rest` during migration, against disposable PostgreSQL Testcontainers |
| `uv run poe test:jobs` | Run real Inngest job tests with disposable Testcontainers under `tests/messaging/inngest/jobs` |
| `uv run poe test` | Run the complete pytest suite with verbose output |
| `uv run poe build` | Build source and wheel distributions with uv |
| `uv run --env-file .env.local python src/main.py` | Start the API locally |

The server's module boundaries are declared in `apps/server/tach.toml`. The current
module policy keeps business modules dependent on shared code while application
composition may assemble the module routers. `check:architecture` intentionally
excludes only the shared seed composition files because they coordinate feature seeders
for an explicit local command.

Ruff is intentionally invoked with `--no-fix` in the CI-facing `check:lint` task.
Validation must not rewrite source files. Use an explicit formatter command when a
formatting change is intended:

```bash
uv run ruff format src tests
```

FastAPI controller integration tests use `TestClient` through the shared fixture in
`apps/server/tests/conftest.py`. Test HTTP behavior through the application boundary;
do not call nested controller handlers directly. All server pytest cases are methods
on a `Test<Subject>` class; top-level `test_*` functions are not used.

## Architecture and quality checks

Run the affected application gates before handing off a change:

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web test:unit
pnpm --filter web build

cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe test:unit
uv run poe test:integration
uv run poe build
```

The web `check:code`/SonarQube gate is intentionally not part of the current local
contract. SonarQube is present in Docker Compose, but CI integration and scanner
configuration are deferred.

There is currently no committed `.github/workflows` directory. When CI workflows are
added, they must call these application-owned commands, use the repository runtime
files, and preserve the web/server path separation.

## Database and asynchronous tooling status

The server provides an explicit Alembic migration workflow and registers its
module-owned Inngest functions through one `/api/inngest` endpoint. REST integration
tests use disposable PostgreSQL Testcontainers and do not reuse the developer's
Compose database. Docker-backed job tests use disposable PostgreSQL and Inngest
containers; they may skip locally when Docker or the configured callback port is
unavailable, but CI must run them on a Docker-capable runner.

## Recommended handoff checklist

Before handing off a change:

1. Inspect `git status` and preserve unrelated user changes.
2. Run the gates for every changed application or package.
3. Run focused tests first, then the broader application test command.
4. Run a real browser check for changed web routes or interaction behavior when the
   required application services are available.
5. Confirm generated output, caches, credentials, test reports, and build artifacts
   are ignored and not staged.
6. Report unavailable infrastructure or pre-existing failures explicitly instead of
   treating skipped checks as passing.
