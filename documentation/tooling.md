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
  MinIO, Mailpit, and the local SonarQube stack.

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
| `MENTOR_ATTACHMENT_STORAGE_PORT` | `9000` | Private Mentor MinIO API host port |
| `MENTOR_ATTACHMENT_STORAGE_BUCKET` | `shifu-mentor-attachments` | Local private attachment bucket |
| `LANGFUSE_PORT` | `7003` | Local agent monitoring UI/API host port |
| `LANGFUSE_BASE_URL` | `http://localhost:7003` | Server telemetry destination |
| `MENTOR_TELEMETRY_ENABLED` | `false` | Opt in to sanitized Intelligence and Learning agent monitoring |
| `MENTOR_GENERATION_LIMIT_PER_HOUR` | `30` | Server setting: generated Mentor answers per account per rolling hour for questions without a local answer; `0` turns them off and the Mentor shows its local abstention |
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
- private S3-compatible MinIO storage for Mentor attachments;
- Mailpit for local mail capture; and
- SonarQube with its PostgreSQL database.

Default endpoints are:

| Service | URL or address |
| --- | --- |
| PostgreSQL | `postgresql://shifu:change-me@localhost:54344/shifu` |
| Redis | `redis://localhost:6379/0` |
| Inngest | `http://localhost:18288` |
| Private MinIO | `http://localhost:9000` (API; local credentials only) |
| Mailpit UI | `http://localhost:54326` |
| Mailpit SMTP | `localhost:1026` |
| SonarQube | `http://localhost:19000` |
| Langfuse (profile `langfuse`) | `http://localhost:7003` |
| Web application | `http://localhost:7000` |
| FastAPI application | `http://localhost:7777` (fallback) |

Stop containers without deleting named volumes:

```bash
docker compose down
```

Do not delete Docker volumes or reset local databases unless explicitly requested.

Compose starts the private `minio` service and one-shot `minio-init` service; the latter
creates the configured attachment bucket after MinIO is healthy. This storage has its
own named volume and credentials, separate from the optional Langfuse MinIO. The
server's `MENTOR_ATTACHMENT_STORAGE_*` values in `apps/server/.env.local` must match
the root Compose values copied from `.env.example`. Values in the environment examples
are local placeholders only. The typed server limits default to 20,000,000 decoded
image pixels, 40 PDF pages, 200,000 extracted characters, a 10-second PDF processing
deadline and 20,000,000 total rendered PDF bytes per attachment. PDF parsing and raster
rendering run in deadline-bounded workers; pages that exceed the render-byte budget or
deadline remain uninterpreted. The upload boundary also enforces at most five files
and 10,000,000 bytes per file. These bounds apply before content is sent to model
inference.

Compose also runs the idempotent `agentos-role-init` service to provision the
`shifu_agentos_runtime` login. `DATABASE_URL` remains the migration and application
database connection; `AGENTOS_DATABASE_URL` in `apps/server/.env.local` must use the
restricted runtime login. Alembic grants that role schema usage and table DML on the
two AgentOS schemas, but no schema ownership or DDL permission. Start
`docker compose up -d agentos-role-init` when bringing up only selected services;
never point the AgentOS runtime URL at the migration owner.

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

The server registers non-AI Inngest functions at `/api/inngest`; registered AI
workflows use the owning module's AgentOS queue. Do not add a second Inngest process or
obsolete `pubsub` task.

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

The seed also provides three short Mentor conversations and one long conversation,
"Listas e laços em Python", with 30 messages (15 answered pairs). It is one learner
message short of the conversation-summary threshold: sending any message in it makes
the answer run summarize the older messages first ("Resumindo contexto…") and then
show the "Contexto resumido" marker. Reseeding restores it; the summary itself is
derived data, so it is created by the first message and removed by the next reseed.

## Test integrity

`pnpm check:test-integrity` (`node scripts/check-test-integrity.mjs`) fails when a
test file is not for a use case, controller, job or API handler on the server, or a
hook, widget, page, layout or API handler on the web. `--list` prints the allowed
files with their kind. Run it after adding, moving or deleting test files.

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
| `pnpm --filter web test:coverage` | Run Vitest unit tests with V8 coverage |
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

Use the repository's Playwright configuration for committed browser tests.
Browser output and screenshots are temporary validation artifacts and must not
be committed.

### Manual browser checks with Playwright CLI

Use Playwright CLI for concise, required happy paths. Check service health first,
then start a named session from `apps/web`:

```bash
cd apps/web
playwright-cli -s=shifu open http://127.0.0.1:7000/login
```

For protected routes, load `.playwright-cli/states/shifu-auth-state.json`. If it
is missing, sign in with the local seeded account described above and save the
state. Use fresh snapshots and accessible locators. Check the final URL, visible
result, relevant requests, console errors, and keyboard path; inspect only
required screenshots.

Keep captures under `apps/web/.playwright-cli/{screenshots,snapshots,logs}/`.
Storage state contains credentials: do not print, stage, or commit it. Close only
the session and app processes started for the check; leave shared Docker services
running.

## Server tooling

The server uses Python 3.13, FastAPI, Pydantic, uv, Poe the Poet, Ruff,
basedpyright, pytest, and Tach.

Run commands from `apps/server` through uv:

| Command | Purpose |
| --- | --- |
| `uv run poe check:types` | Run strict basedpyright checking |
| `uv run poe check:lint` | Run non-mutating Ruff lint and format checks |
| `uv run poe check:architecture` | Validate Tach module dependencies |
| `uv run poe test:unit` | Run module-first use-case tests, permitted focused domain conformance under `tests/<module>/core/domain`, and legacy `tests/core/**/use_cases` during migration |
| `uv run poe test:integration` | Run module-first server/handler integration plus the explicit Planning preparation/capability boundaries and legacy `tests/rest`, against disposable PostgreSQL Testcontainers |
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

### Automated check execution

Select local tests only for the scoped changes: the Verification Contract's
behavior, changed production boundaries and directly affected consumers. Determine
impact from the diff and actual dependencies, rather than similarly named files
or the fact that an application was touched. A Web-only presentation change does
not require Server tests; a Server change without observable browser impact does
not require Web browser tests. Shared contracts add tests for the consumers whose
behavior is actually affected, not every module automatically.

| Check | During implementation | Integrated verification | After correction |
| --- | --- | --- | --- |
| Unit/component | Run exact affected test files as coherent behavior is implemented. | Confirm current results for scoped behavior and affected consumers. | Rerun failed and invalidated files/scenarios. |
| Server REST/persistence | Implement boundary assertions; use unit/static feedback during building. | Batch affected controller/migration boundary tests after integration using disposable fixtures. | Rerun affected boundary selections sequentially. |
| Inngest jobs | Implement job assertions; use focused unit/static feedback during building. | Run affected real-job tests with their required environment and disposable services. | Rerun affected jobs and directly impacted consumers. |
| Web browser | Implement affected route/journey tests; use component/static feedback during building. | Run only affected Playwright scenario files after integration. | Rerun affected scenarios. |
| Types | Check after public types, schemas, signatures or consumers change. | Run type checks for affected apps and affected consumer projects with their actual configuration. | Rerun impacted producer/consumer projects. |
| Lint/format | Check exact changed source/test/configuration paths without writing. | Confirm current lint/format results for the scoped paths; apply broader configured gates only when required. | Recheck edited paths and affected lint configuration. |
| Complexity | Inspect changed logic and execute available configured complexity checks for that scope. | Record complexity results and the checker limits; a required unavailable quantitative gate is Blocked. | Recheck changed logic; never relax rules or update a baseline merely to pass. |
| Architecture/build | Check affected dependencies, exports, composition and build inputs. | Run required gates for affected apps and dependent consumers. | Rerun gates whose claims/inputs changed. |

Integration remains an integrated checkpoint, not a per-edit ritual. Run related
Server selections together to reuse fixture setup, and serialize container-backed
commands so independent pytest processes do not compete for ports/services.
Independent read-only checks may run concurrently when resources do not compete;
generation, dependent builds and validation of their outputs remain sequential.

Do not run full local workspace suites as a default or add them to a Spec merely
because work reaches integration. Broaden a selection only for demonstrated
shared behavior, affected consumers or a concrete gap in proof of the scoped
changes; record that dependency and reason. A whole-suite run is appropriate only
when the scoped impact actually spans that suite or the user explicitly requests
such a measurement. Keep unrelated tests outside routine local validation.

Record exact files/scenarios, boundaries, test counts, outcomes, command wall time,
candidate/environment and artifacts in Evaluation. Keep Web Vitest, Web Playwright,
Server use-case, REST/persistence and real-job results separate. A skipped or empty
selection cannot pass because a command exits successfully. Review, continuation
and conclusion reuse unchanged evidence; a new commit or ledger edit alone does
not justify another run. Preserve original failed/full-run and coverage outcomes;
focused corrections establish only the current scope they execute.

### Selecting unit and integration tests

Use these command forms with source-verified exact file paths substituted for the
placeholders. List those paths in the Spec and actual executed commands in
Evaluation. Test-name filters require names verified in source; avoid broad globs
or keyword searches that silently include unrelated tests.

| Boundary | Working directory | Focused command form |
| --- | --- | --- |
| Web unit/component | Repository root | `pnpm --filter web exec vitest run <test-files...>` |
| Web browser integration | Repository root | `pnpm --filter web exec playwright test <scenario-files...>` |
| Server use case | `apps/server` | `uv run pytest <use-case-test-files...>` |
| Server controller/persistence | `apps/server` | `uv run pytest <controller-or-migration-test-files...>` |
| Real Inngest job | `apps/server` | `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest <job-test-files...>` |

Paths passed to Web runners are relative to `apps/web`; paths passed to pytest
are relative to `apps/server`. Choose test files within the owning Rules' allowed
boundaries. Use-case tests mock ports; controller tests exercise the real app and
persistence; job tests exercise registered durable execution. Mocked browser
transport proves isolated browser behavior, not required real Auth/REST effects.
Manual Playwright CLI checks cover the concise real-service journeys in the Spec.

The unfiltered `test:unit`, `test:integration` and `test:jobs` scripts in the
catalogues above select complete categories. Server Poe unit/integration tasks
use shell discovery and do not define positional file selectors; use pytest
directly for scoped files instead of assuming appended arguments narrow them.
The real-job selection must retain `SHIFU_RUN_REAL_INNGEST_TESTS=1`; otherwise a
skip does not prove execution. Inspect the applicable fixtures for additional
readiness/configuration and verify actual test counts and results.

Whole-suite impact must be demonstrated: for example, global Server composition,
auth/error boundaries or shared transaction/fixture behavior may affect many
controllers; shared routing/session/root-layout behavior may affect many browser
journeys. Select their actual consumers and identify remaining coverage gaps
before expanding further. CI independently runs its configured suites for
applicable current PR heads; these local scope rules do not change CI discovery.

### Scoped type, lint and complexity checks

Include type, lint and complexity as explicit Automated check obligations in the
Spec and separate result/disposition entries in Evaluation. They supplement the
scoped behavioral tests; a test pass does not establish static conformance.
Documentation-only deliveries may mark source checks Not applicable with a reason.

| Check | Command / scope | Evidence and limits |
| --- | --- | --- |
| Web types | `pnpm --filter web check:types` from the repository root | Uses the existing TypeScript project configuration and catches affected consumer types. |
| Server types | `uv run poe check:types` from `apps/server` | Uses the existing basedpyright configuration. Run for affected Server contracts/implementation. |
| Web lint/format | `pnpm exec biome check <changed-paths...>` from the repository root | Non-writing checks of source/test/configuration paths supported by Biome and its repository configuration. |
| Server lint | `uv run ruff check --no-fix <changed-paths...>` from `apps/server` | Non-writing lint for affected Python source/test paths. |
| Server format | `uv run ruff format --check <changed-paths...>` from `apps/server` | Format compliance without rewriting files. |
| Web complexity lint | The scoped Biome check above | Evaluates configured complexity rules in `biome.json`; record diagnostics and warning severity. This is not a quantitative complexity/baseline measurement. |
| Server complexity lint | The scoped Ruff check above (`C90` is selected in root `pyproject.toml`) | Enforces configured McCabe complexity diagnostics; this does not establish an independent metrics baseline. |
| Dedicated complexity metrics | No configured script/runner/baseline in current root/Web/Server manifests | Record unavailable tooling explicitly; do not invent `check:complexity`, thresholds or a passing metrics result. |

Replace placeholders with exact affected paths verified in source. Type checks may
need the affected app/project rather than a file list to preserve tsconfig/import
context and consumer correctness; record that scope. Do not pass files to `tsc`
in a way that bypasses the repository project configuration. Keep checks within
affected apps/consumers and use scoped lint for routine feedback instead of root
repository-wide lint or formatting commands. Required configured project gates
still apply to the affected apps.

For complexity, the Spec identifies affected logic, available checker and actual
pass conditions. Web's configured complexity lint can share an executed command
with lint, but must have an explicit result/disposition and evidence limits.
Server Ruff includes the configured C90 complexity lint gate; there is no separate metrics/baseline script. Manual review may
record maintainability findings, but cannot satisfy a required quantitative
measurement. If such a measurement is required, missing tooling is Blocked until
provided or the contract is explicitly reconciled; ordinary lint/type/test success
cannot replace it. Introducing a metrics tool/configuration is separate from this
workflow documentation change. Recheck manifests before naming future commands.

### Applicable project gates

During implementation, use focused checks from the Spec. After integration, run
applicable static/build gates below plus the contracted affected test selections.
The complete test-suite scripts in the command catalogues above are available
commands, not a mandatory local execution checklist. Specify exact test files or
scenarios with verified runner commands. Use full scripts only when scoped impact
actually spans that suite or the user explicitly requests it. Reuse valid results
at later handoffs:

```bash
pnpm --filter web check:lint
pnpm --filter web check:architecture
pnpm --filter web check:types
pnpm --filter web build

cd apps/server
uv run poe check:lint
uv run poe check:architecture
uv run poe check:types
uv run poe build
```

Run affected integration selections on the integrated candidate. Fix failures and
rerun affected checks until they pass. Code, fixture, configuration, or contract
changes reopen affected checks; role or commit changes alone do not. Use explicit
CI-compatible fixture settings instead of relying on ignored local environment
files.

The web `check:code`/SonarQube gate is intentionally not part of the current local
contract. SonarQube is present in Docker Compose, but CI integration and scanner
configuration are deferred. The local SonarQube service is separate from the
planned SonarCloud coverage and quality-gate integration.

Inspect the current `.github/workflows` when selecting delivery gates. CI uses
application-owned commands and repository runtime files. Server CI also runs
`uv run alembic check` after migrating its disposable database to detect schema
migration drift. The Email workflow separately checks package code/types,
generates templates and verifies the server distribution contract when its path
filters match. A remote CI run is evidence for its exact candidate/environment;
do not treat a pending or failed check as passed.

Web CI runs type, lint, architecture, unit, browser integration and build checks
as independent jobs. Playwright uses the development server and
keeps its own database/server setup. Server CI runs type, lint, architecture,
unit, integration and real AI eval checks independently. Controller and registered
workflow tests plus real Inngest job tests run as separate steps in the same
integration job. Distribution build/verification runs in its own build job; architecture-check
only validates dependency boundaries. Server eval CI runs every available eval
class through `apps/server/evals/run.py`, without workflow/name/tag filters, with
`SHIFU_RUN_REAL_AI_EVALS=1`, and uploads reports on failure. The runner writes
per-workflow JSON reports and a summary, and exits nonzero when a workflow or
report write fails. Its model settings use the `OPENROUTER_API_KEY` repository secret and the
`OPENROUTER_PROMPT_LOGGING_DISABLED` / `MENTOR_TITLE_PROMPT_LOGGING_DISABLED`
repository variables. Resolve actual provider privacy attestations before setting
those variables; this local workflow edit does not configure external secrets or
variables. Local eval validation selects only complete changed/affected workflow
classes, while current-head CI requires the full catalogue. Email CI runs package code, type, template build, Server type
and Server distribution checks independently; the package does not define unit or integration
test scripts. Email retains its required aggregate check. Web and Server expose
individual checks directly, without verify aggregate jobs; these local edits do
not change repository branch-protection settings.

## Database and asynchronous tooling status

The server provides an explicit Alembic migration workflow. It registers non-AI
Inngest functions through one `/api/inngest` endpoint and starts separate native
AgentOS registries for Intelligence and Learning. Their PostgreSQL schemas, queues,
clients and lifecycles are module-scoped; Shared supplies only destination-aware
transport and sanitized observability. REST integration tests use disposable
PostgreSQL Testcontainers and do not reuse the developer's Compose database.
Attachment controller tests also use disposable MinIO. Inngest tests use disposable
PostgreSQL and Inngest. There are no AgentOS runtime tests. Workflow tests under
`apps/server/tests/<module>/ai/workflows/` run the Agno workflow in process with mocked
agents; answer quality is proved by the evals under `apps/server/evals`. Local tests may report a precise Docker or callback-port skip, but CI must run
all contracted runtime selections on a Docker-capable runner. Set
`SHIFU_RUN_REAL_INNGEST_TESTS=1` for real Inngest tests; skips or empty selections do
not pass.

### Local agent monitoring with Langfuse

AgentOS runs the Intelligence and Learning workflows. Langfuse supplies their
local monitoring UI at `http://localhost:7003`. Start its existing Compose profile
from the repository root:

```bash
docker compose --profile langfuse up -d langfuse-web langfuse-worker
docker compose --profile langfuse ps
curl --fail http://localhost:7003/api/public/health
```

The profile includes a separate PostgreSQL database, Redis, ClickHouse and MinIO
with persistent named volumes. It does not use the application database or Mentor
attachment bucket. The web UI/API is published only on loopback.

Sign in to the local UI, open the Shifu project's settings, and obtain its API key
pair. Configure the following in the ignored `apps/server/.env.local` and restart
the Server so its settings are reloaded:

```dotenv
MENTOR_TELEMETRY_ENABLED=true
LANGFUSE_BASE_URL=http://localhost:7003
LANGFUSE_PUBLIC_KEY=<project-public-key>
LANGFUSE_SECRET_KEY=<project-secret-key>
MENTOR_TELEMETRY_CONTENT_ENABLED=false
```

Monitoring exports sanitized operational traces for both modules: stage/profile,
timing, outcome, reported usage, and opaque correlation identifiers. Raw prompts,
answers, JEV decisions, attachment content, credentials and exception text are
excluded; `MENTOR_TELEMETRY_CONTENT_ENABLED` remains only as a compatibility
setting and cannot enable content capture. Telemetry is optional and failures do
not interrupt agent execution. AgentOS retains its module-scoped runtime,
persistence and restricted database credentials.

The local stack uses Langfuse v4. With its default `events_only` ingestion mode,
legacy `/api/public/traces` reads return 404 even after successful ingestion.
Use `/api/public/v2/observations` with `traceId` and bounded
`fromStartTime`/`toStartTime` filters to verify persisted monitoring data; the
native UI groups those observations into traces.

## Delivery handoff

- Preserve unrelated changes; confirm generated files, credentials, reports, and
  build artifacts are not staged.
- Record acceptance progress, required captures, and checker evidence in
  Evaluation. Reuse unaffected passing results; report skipped or failed checks.
- Include the Spec revision, candidate, unfinished criteria, blockers, and next
  action so work can continue without repeating valid checks.
