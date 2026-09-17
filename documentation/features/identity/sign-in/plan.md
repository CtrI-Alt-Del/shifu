---
title: Identity sign-in implementation plan
status: completed
spec: ./spec.md
spec_revision: 20
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-62
last_updated_at: 2026-09-17
---

# Execution status

- **Spec:** [`spec.md`](./spec.md), revision `20`, status `completed` after the shared-provider, Inngest-boundary, provider-folder, fixture-naming, and Testcontainers amendments.
- **Why Plan-backed:** This delivery crosses the web BFF, FastAPI Identity,
  PostgreSQL/Alembic, Better Auth, JWT/JWKS, shared outbox/listener/Inngest
  infrastructure, generated routes, responsive UI, and real browser/runtime
  validation. It also has shared package, lockfile, migration, Compose, and
  generated-artifact ownership that cannot safely be represented by one task.
- **Plan:** `completed`; implementation corrections, validation, review findings,
  and local SDD conclusion are complete.
- **Next action:** No further local SDD action is required. Publication or Jira/
  Confluence mutation was not requested.
- **Active blockers/dependencies:** SHIFU-61 and SHIFU-63 are parallel
  integration authorities, not SHIFU-62 execution blockers. SHIFU-62 must not
  create sibling route files or duplicate confirmation, recovery or reset
  behavior; later integration verifies URL/hash compatibility at the boundary.
- **Builders:** `Builder Core` completed F1; `Builder Database` completed F2;
  `Builder Server` completed F3; `Builder Messaging` completed F4; `Builder
  Web` completed F5; and the Orchestrator integrated F6/F7.
- **Shared ownership:** The Orchestrator owns this Plan, `spec.md`, the later
  `evaluation.md`, package installation, `pnpm-lock.yaml`, `apps/server/uv.lock`,
  root configuration, generated route metadata, migration coordination,
  cross-Builder integration, and final validation. Builders may not overlap
  these paths or edit SDD artifacts.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `documentation/features/identity/sign-in/spec.md` is `ready` at revision `19`; source is Identity PRD content `83001345`, version `1`, and Jira `SHIFU-62`. | Orchestrator | `passed` | Recheck the exact revision at each implementation phase boundary. |
| Contract integrity | Functional, technical, design, validation, REST-client, independence, and supplemental-screenshot contracts are reconciled in Spec revision 20 and `design/handoff.md`. | Orchestrator | `passed` | Preserve revision 20 during execution; route any new material change through SDD amendment. |
| SHIFU-61 relationship | Registration, hash creation, confirmation and pending-page behavior remain sibling-owned; Jira completion is not required for SHIFU-62 build/test. | Orchestrator / Identity delivery owner | `not_required` | Validate the stable hash/URL integration contract later; do not wait or duplicate sibling behavior. |
| SHIFU-63 relationship | Recovery/reset behavior remains sibling-owned; Jira completion is not required for SHIFU-62 build/test. | Orchestrator / Identity delivery owner | `not_required` | Validate the stable recovery URL contract later; do not wait or create a recovery page. |
| REST-client boundary | `apps/server/rest-client/identity/identity.rest` covers `POST /identity/sign-in`, `GET /identity/session`, and `POST /identity/main-page-entries`. | Builder Server, reviewed by Orchestrator | `passed` | Preserve parity during final integration. |
| Local services | Docker Compose PostgreSQL, Inngest, and Mailpit were healthy during validation; web/FastAPI were started for browser/runtime checks. | Orchestrator | `passed` | Stop only processes started for validation; leave shared Compose services intact. |
| Design inventory | Eight supplied screenshots have complete inventories in `design/handoff.md`; four derived states are scheduled below, and tablet/protected rejection require no supplemental frame. | Builder UI / Builder Routing | `passed` | Use saved references; capture all scheduled runtime states during evaluation. |

F1 and F2 are complete. The revision-14 amendment removes sibling Jira delivery
state from the SHIFU-62 critical path, and the amended contract is ready for F3.
Sibling flows remain integration contracts, not implementation work in this delivery.

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Core` | F1 | Framework-independent sign-in, authentication, and canonical event/outbox contracts exist. | Spec revision 14; existing Identity ports and account structures. | — | `completed` | Focused use-case tests pass and no adapter/framework types cross core. |
| 2 | `Builder Database` | F2 | Better Auth technical schema and transactional events outbox are migration-managed. | F1; existing Alembic history and PostgreSQL. | — | `completed` | Upgrade and metadata review pass; shared-database downgrade is deferred because it would remove the additive schema from the user database. |
| 3 | `Builder Server` / Orchestrator | F3 | FastAPI sign-in, current-session, main-page-entry, JWT/JWKS, and composition boundaries are registered with the SHIFU-62-owned verifier. | F1/F2; validated settings; revision-14 Spec review. | — | `completed` | Focused REST suites, server gates, and route-complete REST artifact pass. |
| 4 | `Builder Messaging` | F4 | Committed outbox rows relay durably to one Inngest endpoint and logging-only job. | F1/F2/F3 composition; local Inngest. | F5 | `completed` | Broker, Compose sync, real-runtime fixture, and live relay evidence are integrated. |
| 4 | `Builder Web` | F5 | Server-only Better Auth/BFF provider, Identity service, auth context, and safe error boundary are composed. | F2/F3; canonical URL assertions. | F4 | `completed` | Web lint, architecture, types, unit, handler, persistence, cookie, and secret-boundary checks pass. |
| 5 | `Builder UI` | F6 | Public sign-in page and shared visual primitives render all contracted states. | F5; `documentation/design.md`; `design/handoff.md`. | — | `completed` | Colocated component/hook tests and fresh responsive/state evidence pass. |
| 6 | `Builder Routing` | F7 | Public/protected routes, middleware, generated tree, and module-owned browser suites are integrated. | F4/F5/F6; canonical URL assertions. | — | `completed` | Route generation, 18 browser tests, build, and protected-route evidence pass. |
| 7 | `Orchestrator / Implementation Reviewer` | F8 | Integrated candidate is reconciled against every criterion and independently reviewed. | F1–F7; evaluation baseline; all applicable automated gates. | — | `completed` | `evaluation.md` is complete at Spec revision 20 with resolved findings and final evidence. |

## F1 — Establish Identity core and shared event contracts

#### F1-T1 — Create framework-independent authentication and event contracts

- **Status/owner:** `completed` — Builder Core.
- **Depends/parallel:** After readiness confirmation; no parallel implementation
  path because shared core contracts are consumed by later server/database work.
- **Paths:**
  `apps/server/src/shifu/identity/core/domain/structures/authentication.py`;
  `apps/server/src/shifu/identity/core/domain/structures/issued_access_token.py`
  (remove);
  `apps/server/src/shifu/identity/core/domain/structures/__init__.py`;
  `apps/server/src/shifu/identity/core/domain/events/main_page_entered_event.py`;
  `apps/server/src/shifu/identity/core/domain/events/__init__.py`;
  `apps/server/src/shifu/identity/core/use_cases/sign_in_use_case.py`;
  `apps/server/src/shifu/identity/core/use_cases/publish_main_page_entered_use_case.py`;
  `apps/server/src/shifu/identity/core/interfaces/access_token_provider.py`
  (remove);
  `apps/server/src/shifu/identity/core/interfaces/__init__.py`;
  `apps/server/src/shifu/shared/core/interfaces/events_repository.py`;
  `apps/server/src/shifu/shared/core/interfaces/events_repository_listener.py`;
  `apps/server/src/shifu/shared/core/interfaces/outbox_event.py`;
  `apps/server/src/shifu/shared/core/interfaces/__init__.py`;
  `apps/server/tests/core/identity/use_cases/test_sign_in_use_case.py`;
  `apps/server/tests/core/identity/use_cases/test_publish_main_page_entered_use_case.py`.
- **Traceability:** `RP-03`, `RP-07`; `JN-03`; `FR-02`–`FR-05`, `FR-08`;
  `AC-03`–`AC-05`, `AC-09`, `AC-11`.
- **Outcome:** Sign-in returns only safe `Authentication`; invalid, missing,
  deleted, case-mismatched, and wrong-password inputs remain indistinguishable;
  main-page events are server-derived and enqueue only through the typed
  transactional `EventsRepository` port.
- **Rules:** `documentation/rules/python-conventions-rules.md`;
  `core-layer-rules.md` (core framework-independence, typed ports, domain errors,
  event ownership); `use-case-testing-rules.md` (autospecced ports,
  infrastructure-free tests); `messaging-layer-rules.md` (repository enqueue,
  no direct Inngest dependency). Antipattern controls: no FastAPI/SQLAlchemy/
  Inngest imports, no token issuer, no browser-supplied event fields, and no
  dedicated tests for declarations or providers.
- **Risks/controls:** Keep the `PasswordHashingProvider` port framework-free and
  use the SHIFU-62-owned Argon2id adapter only through composition; no provider-
  owned test file. Do not change account schema, e-mail policy, status, lockout
  behavior, or event privacy. A hash-format discrepancy is recorded for later
  sibling integration and does not block the independent sign-in build.
- **Exit:** Run `cd apps/server && uv run pytest tests/core/identity/use_cases/test_sign_in_use_case.py`
  and `cd apps/server && uv run pytest tests/core/identity/use_cases/test_publish_main_page_entered_use_case.py`.
  Record normalization, rejection, no-side-effect, deterministic event, and
  transaction-collaboration evidence in `evaluation.md`.

**F1 evidence:** `EV-F1-01` records 8 focused tests passing; server lint,
architecture, and strict type gates also pass after the core changes.

## F2 — Add technical persistence and transaction boundaries

#### F2-T1 — Add Better Auth metadata, events outbox, and migration lifecycle

- **Status/owner:** `completed` — Builder Database (`Hypatia`).
- **Depends/parallel:** After F1; serial because the repository implements the
  F1 outbox port. No active path overlaps migration/shared database ownership.
- **Paths:**
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_user_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_session_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_account_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_verification_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_jwks_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/better_auth_rate_limit_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/event_model.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/models/__init__.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/repositories/events_repository.py`;
  `apps/server/src/shifu/shared/database/sqlalchemy/repositories/__init__.py`;
  `apps/server/src/shifu/identity/database/sqlalchemy/identity_database.py`;
  `apps/server/src/shifu/identity/database/sqlalchemy/__init__.py`;
  `apps/server/migrations/env.py`;
  `apps/server/migrations/versions/b8f67e3c9a21_add_better_auth_schema.py`;
  `apps/server/migrations/versions/c4d82f1e7a30_add_event_outbox.py`;
  `apps/server/tests/conftest.py`.
- **Traceability:** `RP-03`, `RP-07`; `JN-03`; `FR-03`–`FR-05`, `FR-08`;
  `AC-04`, `AC-05`, `AC-08`–`AC-11`.
- **Outcome:** Six metadata-only Better Auth tables, the `events` outbox,
  one Identity transaction owner, guarded reservation/completion, committed
  `pg_notify`, expiry/retry indexes, and safe delivery metadata are migration-
  managed without changing `identity_accounts`.
- **Rules:** `documentation/rules/python-conventions-rules.md`;
  `database-layer-rules.md` (one transaction owner, SQLAlchemy models,
  migrations, concrete repositories); `server-app-layer-rules.md` (explicit
  lifecycle/composition); `controllers-testing-rules.md` (real PostgreSQL
  fixtures); `messaging-layer-rules.md` (outbox durability and no broker calls).
  Antipattern controls: no `metadata.create_all` production migration, no
  repository commits, no ORM leakage, no event delivery from persistence.
- **Risks/controls:** Review every Spec column, constraint, index, trigger,
  upgrade, and destructive downgrade precondition. Keep Better Auth tables
  technical-only, preserve password/hash/e-mail rules, and isolate fixtures.
- **Exit:** Run `cd apps/server && uv run poe db:upgrade`; review migration
  SQL and generated metadata; run the focused F3 controller suites when
  available; and record upgrade/downgrade and persistence evidence in
  `evaluation.md`. Do not mark complete from schema generation alone.

**F2 evidence:** `EV-F2-01` records the additive migration, PostgreSQL schema
inspection, metadata drift check, and current server gates. Downgrade was not
run against the shared database because it would remove the additive schema;
isolated-database downgrade coverage remains part of final delivery validation.

## F3 — Implement FastAPI Identity operations and protected authentication

#### F3-T1 — Register Identity HTTP, JWT/JWKS, settings, and REST parity

- **Status/owner:** `completed` — Builder Server / Orchestrator.
- **Depends/parallel:** After F1/F2, validated environment settings, and the
  revision-14 Spec review. F4 and F5 may start after the composed server
  contracts are stable; neither waits for SHIFU-61 or SHIFU-63.
- **Paths:**
  `apps/server/src/shifu/identity/rest/controllers/sign_in_controller.py`;
  `apps/server/src/shifu/identity/rest/controllers/get_current_session_controller.py`;
  `apps/server/src/shifu/identity/rest/controllers/main_page_entered_controller.py`;
  `apps/server/src/shifu/identity/rest/router.py`;
  `apps/server/rest-client/identity/identity.rest`;
  `apps/server/src/shifu/identity/providers/auth/password_hashing/argon2id_hash_provider.py`;
  `apps/server/src/shifu/identity/providers/auth/jwt/jwks/jwks_jwt_authentication_provider.py`;
  `apps/server/src/shifu/identity/pipes/identity_pipe.py`;
  `apps/server/src/shifu/identity/pipes/__init__.py`;
  `apps/server/src/shifu/shared/constants/environment.py`;
  `apps/server/src/shifu/app.py`; `apps/server/.env.example`;
  `apps/server/pyproject.toml`; `apps/server/uv.lock`;
  `apps/server/tests/rest/controllers/identity/test_sign_in_controller.py`;
  `apps/server/tests/rest/controllers/identity/test_get_current_session_controller.py`;
  `apps/server/tests/rest/controllers/identity/test_main_page_entered_controller.py`.
- **Traceability:** `RP-03`, `RP-07`; `JN-03`; `FR-02`–`FR-05`, `FR-08`;
  `AC-03`–`AC-05`, `AC-08`–`AC-11`.
- **Outcome:** `POST /identity/sign-in`, `GET /identity/session`, and
  `POST /identity/main-page-entries` are composed through FastAPI with safe
  status/body contracts, active-account/version enforcement, EdDSA/JWKS
  validation, and no browser JWT issuance.
- **Rules:** `python-conventions-rules.md`; `rest-layer-rules.md` (explicit
  controllers, response models, status/error mapping and synchronized examples);
  `server-app-layer-rules.md`; `provision-layer-rules.md`; `database-layer-rules.md`;
  `controllers-testing-rules.md`; `core-layer-rules.md`. Antipattern controls:
  no provider-owned test files, no raw exception/credential/token responses,
  no async event-loop blocking, and no mutable module-level application state.
- **Risks/controls:** Reject unknown/retired keys, invalid claims, pending,
  deleted, missing, and stale accounts uniformly. Resolve client IP only at the
  trusted boundary; never log request bodies or authorization headers. Keep
  `identity.rest` credential-free and include exactly one labeled request for
  every route, with current headers, bodies, and reusable local variables.
- **Exit:** Run `cd apps/server && uv run pytest tests/rest/controllers/identity`;
  run `uv run poe check:lint`, `check:architecture`, and `check:types` as
  applicable; inspect the OpenAPI/HTTP responses; and verify the REST artifact
  has one labeled request each for all three routes. Record real HTTP,
  persistence, authorization, and negative-secret evidence in `evaluation.md`.

**F3 setup evidence:** The SHIFU-62-owned `Argon2idHashProvider` is now present
with the revision-14 parameters, `argon2-cffi` and `PyJWT[crypto]` are resolved in
`uv.lock`, and `EnvironmentSettings` exposes the issuer, audience and JWKS URL.
The adapter's Ruff and strict Pyright checks pass; HTTP/JWT/controller composition
and its consuming tests are now complete.

**F3 completion evidence:** The three Identity routes are registered, the REST
artifact has one labeled credential-free request per route, focused consuming
REST tests pass (`5 passed`) against the session-scoped PostgreSQL
Testcontainers fixture, controllers contain no `try`/`except` blocks, global
FastAPI error handlers own safe Identity failure mapping, and server lint,
strict type, and architecture gates pass. PostgreSQL/JWKS, BFF, browser, and live outbox relay evidence is
recorded in the Evaluation ledger; the Docker job selection remains explicitly
skipped when its owned port is unavailable.

**F3 database-fixture correction:** `tests/fixtures/postgres.py` now owns a
session-scoped disposable PostgreSQL container, applies the current Alembic
head, and gives each REST test a clean function-scoped database boundary.
`tests/conftest.py` injects that engine into `FastAPIApp`, so normal REST
requests use production repositories and the production password verifier. The
intentional infrastructure-failure regression remains the only controlled
database double. The shared PostgreSQL LISTEN connection uses a dedicated
psycopg connection so application teardown cannot block on a pooled SQLAlchemy
rollback.

## F4 — Implement durable outbox relay and logging-only Inngest job

#### F4-T1 — Start one shared listener and register the Identity logging job

- **Status/owner:** `completed` — Builder Messaging / Orchestrator.
- **Depends/parallel:** Wave 4, parallel with F5 after F3 composition and local
  Inngest availability. Paths are restricted to shared messaging, Identity job
  integration fixtures, and root/runtime documentation listed below.
- **Paths:**
  `apps/server/src/shifu/shared/messaging/inngest/client.py`;
  `apps/server/src/shifu/shared/messaging/inngest/inngest_messaging.py`;
  `apps/server/src/shifu/shared/messaging/inngest/__init__.py`;
  `apps/server/src/shifu/shared/messaging/inngest/inngest_broker.py`;
  `apps/server/src/shifu/identity/messaging/inngest/jobs/log_main_page_entered_job.py`;
  `apps/server/src/shifu/identity/messaging/inngest/jobs/__init__.py`;
  `apps/server/src/shifu/identity/messaging/inngest/identity_inngest_messaging.py`;
  `apps/server/src/shifu/app.py`;
  `apps/server/src/main.py`;
  `apps/server/tests/fixtures/inngest_fixture.py`;
  `apps/server/tests/messaging/inngest/jobs/identity/test_log_main_page_entered_job.py`;
  `docker-compose.yaml`; `.env.example`; `documentation/tooling.md`.
- **Traceability:** `RP-03`, `RP-07`; `JN-03`; `FR-08`; `AC-11`.
- **Outcome:** One FastAPI Inngest endpoint is composed by shared
  `InngestMessaging`, which consumes the Identity-owned
  `IdentityInngestMessaging` job group and registers it with one client; the
  long-lived
  broker drains committed rows on startup/reconnect, wakes on notifications or
  due retry deadlines, reserves safely, sends stable IDs, acknowledges before
  publishing, retries boundedly, and leaves terminal rows visible. The Identity
  job emits one structured safe log with zero retries and no business mutation.
- **Rules:** `python-conventions-rules.md`; `messaging-layer-rules.md` (one
  endpoint, persisted-before-publication, idempotent relay, bounded retry);
  `jobs-testing-rules.md` (real runtime, bounded polling, observable effects);
  `server-app-layer-rules.md`; `database-layer-rules.md`;
  `provision-layer-rules.md`. Antipattern controls: no direct use-case broker
  calls, no import-time registration, no notification-only durability, no
  infinite polling, and no blocking async-loop work.
- **Risks/controls:** PostgreSQL notification is latency-only; startup/reconnect
  drain and deadline wakeups are mandatory. Do not create a second dev server
  or endpoint. Keep payloads to `event_id`, `account_id`, and UTC time, and use
  stable redacted error codes.
- **Exit:** The declared Docker-capable `cd apps/server && uv run poe
  test:jobs` path now publishes through the Inngest Dev Server and waits for the
  registered FastAPI job. It is explicitly skipped when its owned port 7777 is
  unavailable; live relay/persistence/job evidence is recorded separately in
  `evaluation.md`.

## F5 — Build the web BFF, auth adapters, and shared auth context

#### F5-T1 — Compose Better Auth, Identity REST, and browser-safe auth context

- **Status/owner:** `completed` — Builder Web / Orchestrator.
- **Depends/parallel:** Wave 4, parallel with F4 after F3; exact canonical URL
  assertions cover sibling destinations. No path overlaps F4 and no sibling
  Jira delivery is required.
- **Paths:**
  `apps/web/src/core/shared/interfaces/rest-client.ts`;
  `apps/web/src/rest/axios/axios-rest-client.ts`;
  `apps/web/src/rest/services/identity-service.ts`;
  `apps/web/src/core/errors/app-error.ts`;
  `apps/web/src/core/errors/rest-error.ts`;
  `apps/web/src/core/errors/auth-error.ts`;
  `apps/web/src/rest/errors/rest-error.ts` (remove);
  `apps/web/src/core/shared/responses/rest-response.ts`;
  `apps/web/src/ui/shared/hooks/use-rest-context.ts`;
  `apps/web/src/provision/auth/better-auth/better-auth-config.ts`;
  `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`;
  `apps/web/src/provision/auth/cookie-session-auth-provider.ts`;
  `apps/web/src/ui/shared/contexts/auth-context/index.tsx`;
  `apps/web/src/ui/shared/contexts/auth-context/use-auth-context-provider.ts`;
  `apps/web/src/ui/shared/contexts/auth-context/use-auth-context.ts`;
  `apps/web/src/ui/shared/contexts/auth-context/types/auth-context-value.ts`;
  `apps/web/src/ui/shared/contexts/auth-context/types/index.ts`;
  `apps/web/src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts`;
  `apps/web/package.json`; `apps/web/vitest.config.ts`;
  `apps/web/.env.example`; `pnpm-lock.yaml` (Orchestrator-generated).
- **Traceability:** `RP-03`, `RP-07`, `RP-10`; `JN-03`; `FR-01`–`FR-06`;
  `AC-01`–`AC-10`.
- **Outcome:** Server-only Better Auth owns the technical projection, fixed
  session, pending record, limiter, rollback, cookies, and BFF handler; the
  browser receives only the typed sign-in/context surface and never receives
  credentials, JWTs, pending values, account IDs, or session tokens.
- **Rules:** `typescript-conventions-rules.md`; `ui-layer-rules.md`;
  `rest-layer-rules.md`; `provision-layer-rules.md`; `widget-testing-rules.md`.
  Antipattern controls: no provider/plugin test file, no direct Axios in
  provision, no browser-readable secret storage, no feature error class, no
  second Toaster/provider, and no native status literals in UI branches.
- **Risks/controls:** Keep server-only imports out of Vite bundles; apply the
  host-only cookie policy and safe error mapping; test persistence and rollback
  through the registered handler. The context-provider hook test may mock the
  provision adapter, but must not become a Better Auth provider test.
- **Exit:** Web lint, architecture, strict types, 10 unit files/22 tests, and
  registered-handler HTTP coverage pass. Active/pending cookies and persisted
  technical session state were also verified against PostgreSQL; no temporary
  identity, session, verification, event, or limiter rows remain.

## F6 — Implement the sign-in page and shared visual primitives

#### F6-T1 — Render the public sign-in state and responsive design contract

- **Status/owner:** `completed` — Builder UI / Orchestrator.
- **Depends/parallel:** After F5 and the saved design handoff; serial with F7
  because F7 consumes the complete page/context surface.
- **Paths:**
  `apps/web/src/ui/identity/widgets/pages/sign-in-page/index.tsx`;
  `apps/web/src/ui/identity/widgets/pages/sign-in-page/use-sign-in-page.ts`;
  `apps/web/src/ui/identity/widgets/pages/sign-in-page/tests/sign-in-page.test.tsx`;
  `apps/web/src/ui/identity/widgets/pages/sign-in-page/tests/use-sign-in-page.test.ts`;
  `apps/web/src/ui/identity/hooks/use-sign-in-action.ts`;
  `apps/web/src/ui/shared/hooks/use-navigation.ts`;
  `apps/web/src/ui/shared/styles/global.css`;
  `apps/web/src/ui/shadcn/button.tsx`;
  `apps/web/src/ui/shadcn/input.tsx`;
  `apps/web/src/ui/shadcn/label.tsx`;
  `apps/web/src/ui/shared/widgets/components/icon/index.tsx`;
  `apps/web/src/ui/shared/widgets/components/square-background/index.tsx`;
  `apps/web/src/ui/shared/widgets/components/square-background/use-square-background.ts`;
  `apps/web/src/ui/shared/widgets/components/square-background/tests/square-background.test.tsx`;
  `apps/web/src/ui/shared/widgets/components/square-background/tests/use-square-background.test.ts`;
  `apps/web/src/ui/shared/widgets/layouts/app-layout/square-background/index.tsx`
  (remove);
  `apps/web/src/ui/shared/widgets/layouts/app-layout/square-background/use-square-background.ts`
  (remove);
  `apps/web/src/ui/shared/widgets/layouts/app-layout/index.tsx`;
  `apps/web/src/ui/shared/widgets/layouts/app-layout/tests/app-layout.test.tsx`;
  `apps/web/src/ui/shared/widgets/layouts/root-layout/index.tsx`;
  `apps/web/src/ui/shared/widgets/layouts/root-layout/use-root-layout.ts`;
  `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx`;
  `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts`.
- **Traceability:** `RP-03`, `RP-10`; `JN-03`; `FR-01`, `FR-06`, `FR-07`;
  `AC-01`–`AC-03`, `AC-06`, `AC-07`.
- **Outcome:** `/login` renders the pt-BR semantic form, exact idle,
  submitting, invalid, throttle, and infrastructure states, alert focus and
  field preservation, shared background, visible focus, 44 px targets, and
  reduced-motion-safe progress without authenticated chrome.
- **Rules:** `typescript-conventions-rules.md`; `ui-layer-rules.md`;
  `widget-testing-rules.md`; `rest-layer-rules.md`; `documentation/design.md`;
  `design/handoff.md`. Antipattern controls: one widget per entrypoint,
  behavior in colocated hooks, shared `Anchor`/`Icon`/shadcn primitives,
  no feature-local tokens, no color-only state, and no action/REST dedicated
  tests.
- **Risks/controls:** Use the exact eight file-backed references and semantic
  token crosswalk. Keep links pointed at canonical URL contracts and assert them
  without requiring sibling pages, but do not create sibling route files;
  derive the four supplemental states in evaluation. Verify compact/mobile
  scrolling rather than fixed-height clipping.
- **Exit:** The page, hook, shared primitives, auth-context hook, and responsive
  states are covered by the 22-test unit suite and Playwright state checks.
  Fresh 1440×900 and 375×812 screenshots, overflow inspection, and expected
  failure/submitting evidence are recorded in `evaluation.md`.

## F7 — Add public/protected routes, middleware, and browser integration suites

#### F7-T1 — Integrate route guards, main-page entry, generated metadata, and browser suites

- **Status/owner:** `completed` — Builder Routing / Orchestrator.
- **Depends/parallel:** After F4, F5, F6, and canonical URL assertions. No
  route tree or browser-test path is shared with F6; sibling route implementation
  is validated later as an integration concern.
- **Paths:**
  `apps/web/src/middlewares/require-auth-middleware.ts`;
  `apps/web/src/middlewares/enter-main-page-middleware.ts`;
  `apps/web/src/routes/api/auth/$.ts`;
  `apps/web/src/routes/login/index.tsx`;
  `apps/web/src/routes/index.tsx`;
  `apps/web/src/routes/account/index.tsx`;
  `apps/web/src/routes/curriculum/index.tsx`;
  `apps/web/src/routes/learning/index.tsx`;
  `apps/web/src/routes/gamification/index.tsx`;
  `apps/web/src/routes/intelligence/index.tsx`;
  `apps/web/src/constants/routes.ts`;
  `apps/web/src/routeTree.gen.ts` (generate only);
  `apps/web/tests/playwright.ts`;
  `apps/web/tests/fixtures/identity-module-fixture.ts`;
  `apps/web/tests/identity/sign-in-auth-handler.test.ts`;
  `apps/web/tests/identity/sign-in-page.test.ts`;
  `apps/web/tests/shared/dashboard-page.test.ts`;
  `apps/web/tests/identity/account-page.test.ts`;
  `apps/web/tests/curriculum/curriculum-page.test.ts`;
  `apps/web/tests/learning/learning-page.test.ts`;
  `apps/web/tests/gamification/gamification-page.test.ts`;
  `apps/web/tests/intelligence/intelligence-page.test.ts`;
  `apps/web/tests/shared/root-layout.test.ts`;
  `apps/web/tests/shared/app-layout.test.ts`.
- **Traceability:** `RP-03`, `RP-07`, `RP-10`; `JN-03`; `FR-01`, `FR-03`–`FR-08`;
  `AC-01`–`AC-11`.
- **Outcome:** The same-origin auth handler and `/login` are public; all
  existing protected routes reject anonymous/pending/stale/deleted access
  before rendering; `/` records one server-only entry signal; generated route
  metadata and module-owned browser suites are synchronized.
- **Rules:** `ui-layer-rules.md`; `web-app-routing-rules.md`;
  `widget-testing-rules.md`; `typescript-conventions-rules.md`;
  `provision-layer-rules.md`; `rest-layer-rules.md`. Antipattern controls:
  one canonical `ROUTES` map, one auth middleware, no hand-edited generated
  tree, shared Playwright factory only, mocked transport explicitly labeled,
  and no `/register`, `/forgot-password`, or `/pending-confirmation` files.
- **Risks/controls:** Browser suites prove UI-to-REST and route behavior only;
  server persistence/authorization comes from F2/F3/F4 and manual runtime
  evidence. Assert final URL, visible state, request method/path/body/status,
  console, failed requests, keyboard path, focus, narrow viewport, and all
  eight manual scenarios plus derived screenshot states.
- **Exit:** Route generation and `git diff --check` pass; the complete 18-test
  Playwright suite and production build pass. Public/protected URL boundaries,
  active/pending handler outcomes, and Dashboard event continuity are recorded
  in `evaluation.md`.

## F8 — Integrated review and delivery evidence

#### F8-T1 — Reconcile the integrated candidate and complete evidence

- **Status/owner:** `completed` — Orchestrator; then exactly one read-only
  `Implementation Reviewer`.
- **Depends/parallel:** After F1–F7, all applicable automated gates, and the
  initial Evaluation evidence baseline. No implementation work runs in parallel.
- **Paths:** All changed paths assigned above plus
  `documentation/features/identity/sign-in/evaluation.md` (created by
  `implement-spec` at kickoff). The Orchestrator owns any shared/generated,
  package, lockfile, migration, Compose, and route-tree reconciliation.
- **Traceability:** All `FR-01`–`FR-08`, `AC-01`–`AC-11`, `RP-03`, `RP-07`,
  `RP-10`, and `JN-03`.
- **Outcome:** The exact Spec revision, integrated diff, route parity, generated
  artifacts, persistence boundaries, server/web contracts, UI states, manual
  scenarios, and evidence are reconciled. Reviewer findings become `ACH-*`
  entries and are resolved by resuming the responsible Builder when needed.
- **Rules:** Every Rule Pack named in the Spec and this Plan;
  `documentation/agents/implementation-reviewer-agent.md`; add
  `commit-rules.md` only if a commit is separately requested. Antipattern
  controls: no reviewer per Builder, no stale evidence acceptance, no claim
  from mocked transport or HTTP 200 alone, and no skipped required runtime gate
  presented as passed.
- **Risks/controls:** Stop and invalidate affected evidence if the Spec revision,
  route contract, design inventory, sibling dependency, or generated artifact
  changes. Keep Docker services running unless teardown is requested; stop only
  application processes started for validation.
- **Exit:** Run all applicable commands listed in the Validation and handoff
  table, complete every `MV-*`, verify every `CA-*` has current accepted
  evidence, complete the single Implementation Reviewer checkpoint, resolve
  verified findings, and route the ready Evaluation directly to `conclude-spec`.

# Validation and handoff

The following rows schedule evidence; they do not claim that any command,
runtime, screenshot, review, or criterion has passed. Actual results belong in
`evaluation.md`.

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Server Identity core use cases | `AC-03`–`AC-05`, `AC-11` | Spec Validation Contract / `CI-01` | `evaluation.md` `EV-F1-01` | `passed` |
| Automated | Server migration and persistence boundary | `AC-04`, `AC-05`, `AC-08`, `AC-11` | Technical Contract / `CI-02` | `evaluation.md` `EV-F2-01` | `passed` |
| Automated | FastAPI Identity controller suite | `AC-03`–`AC-05`, `AC-09`–`AC-11` | Technical Contract / `CI-03` | `evaluation.md` `EV-F3-01` | `passed` |
| Automated | Real Inngest job selection | `AC-11` | Messaging Contract / `CI-04` | `evaluation.md` `EV-F4-01` | `passed` |
| Automated | Web unit/component/context suites | `AC-01`–`AC-08`, `AC-10` | UI/Widget Rules / `CI-05`, `CI-06` | `evaluation.md` `EV-F5-01`, `EV-F6-F7-01` | `passed` |
| Automated | Web route integration and production build | `AC-01`–`AC-11` | Routing Contract / `CI-07` | `evaluation.md` `EV-F6-F7-01`, `EV-CONCLUDE-01` | `passed` |
| Automated | Final web/server quality gates | All applicable criteria | Spec Validation Contract / `CI-08` | `evaluation.md` `EV-F8-01` | `passed` |
| Runtime | `POST /identity/sign-in` through FastAPI/PostgreSQL | `AC-03`–`AC-05`, `AC-10` | REST Contract | `evaluation.md` `EV-F3-01`, `EV-F5-01` | `passed` |
| Runtime | `GET /identity/session` with EdDSA/JWKS and current account | `AC-09`, `AC-10` | JWT/JWKS Contract | `evaluation.md` `EV-F3-01`, `EV-MV-04-08` | `passed` |
| Runtime | `POST /identity/main-page-entries` transaction boundary | `AC-11` | Event Contract | `evaluation.md` `EV-F4-01`, `EV-MV-04-08` | `passed` |
| Runtime | Committed outbox → listener → Inngest job | `AC-11` | Messaging Contract | `evaluation.md` `EV-F4-01` | `passed` |
| REST client | Identity route group: sign-in, session, main-page entry | `AC-03`–`AC-05`, `AC-09`, `AC-11` | `apps/server/rest-client/identity/identity.rest` | Three labeled requests; parity and no secrets in `evaluation.md` `EV-F3-01` | `passed` |
| Manual | `MV-01` responsive visual fidelity | `AC-01` | `design/a9R0Yh.png`, `design/Yzifg.png` | Exact 1440×900 and 375×812 screenshots, URLs, console/network inspection | `passed` |
| Manual | `MV-02` keyboard, focus, and submitting | `AC-02`, `AC-06` | `design/IxLms.png`, `design/i7xhg.png` | Keyboard trace, focus/submitting screenshots, duplicate-request evidence | `passed` |
| Manual | `MV-03` failure privacy and recovery | `AC-03`, `AC-07` | `design/K4sy9p.png`, `design/U0Meh0.png`, `design/JGwvz.png` | Desktop/mobile failure screenshots, redacted network/log/DB evidence | `passed` |
| Manual | `MV-04` active persisted and concurrent sessions | `AC-04` | Spec `MV-04` | Two isolated contexts, cookie metadata, reload, session/projection evidence | `passed` |
| Manual | `MV-05` pending-flow isolation | `AC-05` | `design/Dr6Wk.png` | Redirect, opaque-cookie, verification/session-table, expiry evidence | `passed` |
| Manual | `MV-06` built-in database throttling | `AC-08` | Spec `MV-06` | Eleventh-request `429`, retry header, no FastAPI call, limiter evidence | `passed` |
| Manual | `MV-07` protected invalidation and secret audit | `AC-09`, `AC-10` | Spec `MV-07` | Redirect/session deletion, storage/log/table inspection, console state | `passed` |
| Manual | `MV-08` event publication and outage tolerance | `AC-11` | Spec `MV-08` | Pending/published rows, notification/relay/run/log, outage recovery, page continuity | `passed` |
| Visual | `/login` desktop default, 1440×900 | `AC-01`, `MV-01` | `design/a9R0Yh.png` | Fresh Playwright screenshot + visual inventory comparison | `passed` |
| Visual | Pending handoff (no destination page) | `AC-05`, `MV-05` | `design/Dr6Wk.png` | Canonical redirect/opaque-cookie evidence; destination screenshot is owned by SHIFU-61 and is not required by SHIFU-62 | `not_required` |
| Visual | `/login` mobile default, 375×812 | `AC-01`, `MV-01` | `design/Yzifg.png` | Fresh Playwright screenshot + overflow/focus inspection | `passed` |
| Visual | `/login` desktop invalid credentials, 1440×900 | `AC-03`, `MV-03` | `design/K4sy9p.png` | Fresh screenshot + retained/cleared field and alert evidence | `passed` |
| Visual | `/login` desktop infrastructure failure, 1440×900 | `AC-07`, `MV-03` | `design/JGwvz.png` | Fresh screenshot + recovery evidence | `passed` |
| Visual | `/login` desktop submitting, 1440×900 | `AC-06`, `MV-02` | `design/i7xhg.png` | Fresh screenshot + disabled/progress/link evidence | `passed` |
| Visual | `/login` desktop keyboard focus, 1440×900 | `AC-02`, `MV-02` | `design/IxLms.png` | Fresh screenshot + focus-ring/accessibility evidence | `passed` |
| Visual | `/login` mobile invalid credentials, 375×812 | `AC-03`, `MV-03` | `design/U0Meh0.png` | Fresh screenshot + no-clipping evidence | `passed` |
| Visual | `/login` mobile submitting, 375×812 | `AC-06`, `MV-02` | Handoff supplemental decision | Derived state covered by the approved mobile card/state contract | `not_required` |
| Visual | `/login` mobile infrastructure failure, 375×812 | `AC-07`, `MV-03` | Handoff supplemental decision | Derived state covered by the approved responsive alert/card contract | `not_required` |
| Visual | `/login` throttled form, 1440×900 | `AC-08`, `MV-06` | Handoff supplemental decision | Runtime-only alert-family state covered by `EV-F5-01` | `not_required` |
| Visual | `/login` short mobile viewport, 375×667 | `AC-01`, `AC-02`, `MV-01` | Handoff supplemental decision | Runtime-only viewport behavior covered by `EV-MV-01-03` | `not_required` |

## Executable validation commands

Run only commands present in the current manifests or added by the task that
owns the command, and record unavailable commands explicitly:

- Web: `pnpm --filter web generate-routes`, `check:lint`,
  `check:architecture`, `check:types`, `test:unit`, `test:integration`, and
  `build`.
- Server: `cd apps/server && uv run poe db:upgrade`, focused core/controller
  pytest selections, `check:lint`, `check:architecture`, `check:types`,
  `test:unit`, `test:integration`, and `build`.
- Messaging: `docker compose up -d inngest`, followed after F4 adds the
  manifest task by `cd apps/server && uv run poe test:jobs`.
- Runtime: documented local PostgreSQL, FastAPI, web, and Inngest health
  checks; Playwright CLI through the single shared factory. No real-service
  browser suite is claimed for the web application.

## Final handoff condition

The delivery was routed to `conclude-spec` after every task and phase was complete;
Spec revision 20 and the integrated diff reconcile; all applicable pnpm/uv
gates pass; generated routes, migrations, lockfiles, REST examples, and Compose
changes are reviewed; every `CA-*` and `MV-*` has current accepted evidence;
all supplied and scheduled visual states are compared; the REST artifact is
route-complete; the single Implementation Reviewer has completed and verified
findings are resolved; required services/fixtures are available or limitations
are recorded; and `evaluation.md` is ready. This Plan is now `completed`; no
external publication or Atlassian mutation was performed.

# Execution log

- **2026-09-16 — F1 kickoff and baseline**
  - **Finding/result:** `EV-BASELINE-01`; existing web/server quality checks
    pass, web has no unit test files yet, and four pre-existing web lint
    warnings remain. PostgreSQL, Inngest, and Mailpit are available.
  - **Next action:** Begin F1/F2 implementation; at that baseline, F3/F5–F7
    were still described as waiting on SHIFU-61/SHIFU-63.

- **2026-09-16 — F1/F2 complete, integration paused**
  - **Finding/result:** F1 focused core tests and F2 migration/static gates
    passed; evidence is recorded as `EV-F1-01` and `EV-F2-01`. The additive
    migration is applied to the local PostgreSQL service at head
    `c4d82f1e7a30`.
  - **Next action at the time:** Await the real SHIFU-61/SHIFU-63 contracts;
    this historical disposition is superseded by revision 14. No substitute
    sibling routes or placeholder pages were introduced.

- **2026-09-16 — Revision 14 independence amendment**
  - **Finding/result:** SHIFU-61 and SHIFU-63 remain `A fazer`, but their Jira
    delivery state is not a SHIFU-62 build/test dependency. The Spec now keeps
    sibling page/flow ownership intact while defining canonical URL/redirect
    assertions and a replaceable SHIFU-62 Argon2id verifier composition.
  - **Next action:** Complete the revision-14 Spec review, then start F3. Keep
    sibling compatibility checks as later integration evidence; do not wait or
    implement sibling behavior.

- **2026-09-16 — Revision 14 review passed**
  - **Finding/result:** The independent Spec reviewer confirmed the Argon2id
    contract, canonical URL/redirect evidence, sibling ownership boundaries,
    and absence of active revision-13 gates. Spec revision 14 is `ready`.
  - **Next action:** Start F3 with the SHIFU-62-owned verifier; continue F4/F5
    from the composed boundary without waiting for SHIFU-61 or SHIFU-63.

- **2026-09-16 — F3 server builder activated**
  - **Finding/result:** Revision 14 is ready. F3 owns the FastAPI Identity
    boundary, local Argon2id verifier composition, JWT/JWKS adapter and REST
    parity; SHIFU-61/63 remain outside its build/test dependency set.
  - **Next action:** Builder Server implements only its assigned server source
    and consuming REST tests. The Orchestrator retains package/config/shared
    artifact ownership and will integrate the result before F4/F5.

- **2026-09-16 — F3 bounded continuation**
  - **Finding/result:** The delegated builder stopped because the orchestrator-
    owned dependency/config paths were initially excluded. Those prerequisites
    are now resolved, and the Argon2id adapter passes focused Ruff/Pyright checks.
  - **Next action:** Continue the remaining Identity controllers, JWT/JWKS
  composition and consuming REST tests; F3 stays `in_progress` until those
  boundaries and the REST artifact are validated.

- **2026-09-16 — F3–F7 integrated implementation**
  - **Finding/result:** FastAPI Identity routes, EdDSA/JWKS validation, the
    SHIFU-62 Argon2id verifier, Better Auth BFF persistence/cookies/limiter,
    the browser-safe auth context, public sign-in UI, protected route guards,
    Dashboard event middleware, Compose Inngest sync, shared runtime fixtures,
    and generated routes are implemented. No sibling route or confirmation,
    recovery, or reset behavior was added.
  - **Validation:** Server migration/controller/build/full checks passed;
    web lint/types/architecture/unit/build passed; route generation passed;
    Playwright passed 18 tests; handler active/pending tests passed with
    PostgreSQL cleanup verified at zero temporary rows. The Docker job command
    has a real runtime path but was skipped locally because port 9000 was occupied by
    unrelated MinIO; prior live local-stack evidence covers the relay path.
  - **Next action:** Complete the single read-only Implementation Reviewer and
    resolve any verified findings before routing Evaluation to `conclude-spec`.

- **2026-09-16 — F8 reviewer resolution and final implementation validation**
  - **Finding/result:** The single read-only Implementation Reviewer completed.
    Browser JWT exposure, untrusted client-IP configuration, partial-session
    persistence, duplicate dashboard auth lookup, per-request SQLAlchemy
    engines, missing TanStack Form usage, hard-coded redirects, and the API
    port mismatch were corrected. The dashboard browser test now verifies one
    persisted event row per navigation; the exact desktop screenshot was
    recaptured at 1440×900.
  - **Validation:** Web unit tests pass 22/22 and the complete Playwright suite
    passes 18/18. Web route generation/build, server migration/Alembic check,
    server build, lint, types, architecture and full pytest pass. CI-04 stays
    explicitly partial at that earlier checkpoint because the validation host
    had MinIO on port 9000; that limitation is superseded by the later real
    job validation on the standardized server callback port 7777, and no
    implementation blocker remains.
  - **Next action:** Route the evidence-ready delivery to `conclude-spec`.

- **2026-09-16 — F8 real Inngest validation on port 7777**
  - **Finding/result:** Standardized the FastAPI/Inngest callback and runtime
    fixture on port `7777`. The fixture now waits for app registration,
    submits the current Dev Server event shape, and generates a fresh ULID so
    persisted local history cannot suppress the run.
  - **Validation:** `SHIFU_RUN_REAL_INNGEST_TESTS=1
    SHIFU_INNGEST_FASTAPI_PORT=7777 uv run poe test:jobs` passed `1` test,
    including the structured log fields. CI-04 and the committed outbox to
    listener to Inngest job runtime row are now green.
- **Next action:** Continue the open implementation/evidence pass; do not
    invoke `conclude-spec` until explicitly requested.

- **2026-09-16 — Revision-16 shared identifier provider boundary**
  - **Finding/result:** Moved system ULID generation from the private
    `IdentityPipe` implementation to shared `SystemIdentifierProvider`, which
    implements the core `IdentifierProvider` port. `IdentityPipe` now exposes
    the provider through the core interface while preserving the use-case
    contract.
  - **Validation:** Server strict types, architecture, lint, and 13 focused
    Identity core/controller tests passed. No provider-owned test file was
    added because this is a provider-boundary refactor with existing behavior.
  - **Next action:** Continue the task with the Spec, Plan, and Evaluation
    artifacts open and resumable.

- **2026-09-16 — Revision-17 Inngest broker package boundary**
  - **Finding/result:** Moved `InngestBroker` from the generic `brokers` package
    to `shared/messaging/inngest`, exported it with `InngestMessaging`, and
    updated FastAPI application composition to import the shared Inngest package.
  - **Validation:** The implementation path and package exports match the
    revised Spec; server lint, types, architecture, focused tests (`13 passed,
    1 skipped`), and the real Inngest job on port `7777` (`1 passed`) are green.
  - **Next action:** Continue the open implementation/evidence pass; do not
    invoke `conclude-spec` until explicitly requested.

- **2026-09-16 — Revision-18 shared provider folder boundary**
  - **Finding/result:** Placed `SystemClockProvider` and
    `SystemIdentifierProvider` in provider-named folders with local package
    exports; all existing consumers continue importing through those package
    boundaries.
  - **Validation:** Provider-folder Ruff checks and direct package imports pass;
    architecture validation passes. The shared SQLAlchemy serialization and
    session modules now pass focused formatting/lint checks; types/tests remain
    blocked because the tracked `shared/database/sqlalchemy/base.py` is deleted
    while active imports still reference it.
  - **Next action:** Continue the open implementation/evidence pass; do not
    invoke `conclude-spec` until explicitly requested.

- **2026-09-16 — Revision-19 Inngest fixture naming**
  - **Finding/result:** Renamed the Docker-backed job-test fixture module to
    `inngest_fixture.py`, its pytest fixture to `inngest_fixture`, and its
    runtime type to `InngestFixture`; plugin and job-test references follow.
  - **Validation:** Renamed fixture import and provider-local Ruff checks pass.
    Full server validation remains subject to the existing unrelated database
    worktree limitation.
  - **Next action:** Continue the open implementation/evidence pass; do not
    invoke `conclude-spec` until explicitly requested.

- **2026-09-16 — Revision-20 Testcontainers job-test isolation**
  - **Finding/result:** Replaced the persistent Compose Inngest dependency in
    `inngest_fixture` with disposable PostgreSQL and Inngest Testcontainers;
    Inngest uses a random mapped host port and FastAPI keeps the port `7777`
    callback contract.
  - **Validation:** Testcontainers imports and fixture-local Ruff checks pass.
    Full server validation remains subject to the existing unrelated database
    worktree limitation.
  - **Next action:** Continue the open implementation/evidence pass; do not
    invoke `conclude-spec` until explicitly requested.

- **2026-09-17 — Local SDD conclusion**
  - **Result:** Resolved the three final conformance findings, reran the full
    web/server gates and isolated real Inngest job test, inspected fresh
    responsive/error/submitting browser evidence, and completed the Evaluation.
  - **Next action:** None for this local Spec. `spec.md`, `plan.md`, and
    `evaluation.md` are complete at revision `20`; no external publication or
    Atlassian mutation was requested.
