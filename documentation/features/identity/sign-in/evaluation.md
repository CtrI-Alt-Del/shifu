---
title: Identity sign-in evaluation
status: completed
spec: ./spec.md
spec_revision: 20
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-62
prd_content_id: 83001345
prd_version: 1
last_updated_at: 2026-09-17
---

# Evaluation status

Implementation and final validation are complete under Spec revision `20`,
which is ready after the independence, port-standardization, and shared-provider
amendments. This Evaluation contains the pre-implementation baseline, the
correction history, and current evidence for the complete sign-in slice.

- **Spec:** `ready`, revision `20`, after the independence, port-standardization,
  shared-provider, Inngest-boundary, provider-folder, fixture-naming, and
  Testcontainers amendments.
- **Plan:** `completed`, F1–F8 implementation and validation are recorded;
  final correction evidence is recorded in `EV-CONCLUDE-01`.
  SHIFU-61 and SHIFU-63 remain parallel authorities and are not prerequisites.
- **Authority:** Identity PRD content `83001345`, version `1`, reread on
  2026-09-16; Jira `SHIFU-62`.
- **Baseline:** Existing repository has no sign-in implementation, Better Auth
  runtime, Identity sign-in routes, REST-client artifact, outbox relay, or
  sign-in UI. Docker Compose PostgreSQL, Inngest, and Mailpit are running;
  application processes are not started for baseline inspection.

# Acceptance coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| `AC-01` | `FR-01`, `FR-07` | Widget/page integration plus `MV-01` and desktop/mobile visual evidence | `EV-F6-F7-01`, `EV-CONCLUDE-01` | passed |
| `AC-02` | `FR-01`, `FR-07` | Widget/route tests plus `MV-02` keyboard, focus, and assistive evidence | `EV-F6-F7-01`, `EV-MV-02`, `EV-CONCLUDE-01` | passed |
| `AC-03` | `FR-02`, `FR-06` | Use-case/controller/auth-handler/widget tests plus `MV-03` | `EV-F3-01`, `EV-F5-01`, `EV-MV-03` | passed |
| `AC-04` | `FR-03`, `FR-05` | Controller/auth-handler/protected-page integration plus `MV-04` | `EV-F3-01`, `EV-F5-01`, `EV-MV-04-08` | passed |
| `AC-05` | `FR-04`, `FR-05` | Use-case/auth-handler integration plus `MV-05` redirect/opaque-cookie evidence | `EV-F5-01`, `EV-MV-04-08` | passed |
| `AC-06` | `FR-06` | Widget/page integration, duplicate-request trace, and `MV-02` | `EV-F6-F7-01`, `EV-MV-02`, `EV-CONCLUDE-01` | passed |
| `AC-07` | `FR-06`, `FR-07` | Auth-handler/widget/page integration plus `MV-03` recovery evidence | `EV-F5-01`, `EV-MV-03`, `EV-CONCLUDE-01` | passed |
| `AC-08` | `FR-06` | Auth-handler integration, `429`/retry-header evidence, and `MV-06` | `EV-F5-01`, `EV-MV-04-08` | passed |
| `AC-09` | `FR-05` | Current-session/protected-route integration and `MV-07` | `EV-F3-01`, `EV-MV-04-08` | passed |
| `AC-10` | `FR-02`–`FR-05` | Negative secret/storage/log/database assertions and `MV-07` | `EV-F5-01`, `EV-MV-04-08` | passed |
| `AC-11` | `FR-08` | Event use-case/controller, outbox/listener, real Inngest job, Dashboard integration, and `MV-08` | `EV-F4-01`, `EV-F8-01`, `EV-MV-04-08` | passed |

# Automated gates

| ID | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| `CI-01` | Focused Identity use-case pytest selections from the Plan | Core sign-in/event contracts | passed | `EV-F1-01` |
| `CI-02` | `cd apps/server && uv run poe db:upgrade` plus migration/database review | Better Auth/outbox persistence | passed | `EV-F2-01` |
| `CI-03` | `cd apps/server && uv run pytest tests/rest/controllers/identity` | FastAPI HTTP/auth boundary | passed: 5 tests | `EV-F3-01`, `EV-REST-DB-01` |
| `CI-04` | `docker compose up -d inngest`; `cd apps/server && uv run poe test:jobs` | Real relay/job runtime | passed: 1 real Docker-backed Inngest job test on FastAPI port 7777 | `EV-F4-01` |
| `CI-05` | Web lint, architecture, types, and unit commands | Web context/REST/UI contracts | passed | `EV-F5-01`, `EV-F6-F7-01` |
| `CI-06` | Web unit command plus design-state review | Sign-in widget and visual state mapping | passed: 10 files/24 tests | `EV-F6-F7-01`, `EV-CONCLUDE-01` |
| `CI-07` | Web route generation, integration, and build commands | Route/middleware/browser composition | passed: 18 browser tests | `EV-F6-F7-01`, `EV-CONCLUDE-01` |
| `CI-08` | Full applicable web/server command set | Integrated delivery gates | passed | `EV-F8-01`, `EV-CONCLUDE-01` |
| `CI-09` | `cd apps/server && uv run poe check:lint && uv run poe check:architecture && uv run poe check:types && uv run poe test:unit && uv run poe test:integration && SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=17777 uv run poe test:jobs && uv run poe build` | Final server candidate after fixture correction | passed: 8 core, 6 REST, 1 real Inngest job, build | `EV-CONCLUDE-01` |

# Manual and visual evidence

Manual scenarios `MV-01` through `MV-08` are defined in `spec.md` and are not
duplicated here. The public UI, keyboard/submitting states, failure privacy,
active/pending session behavior, throttling, invalidation, dashboard event
continuity, and the Docker-backed Inngest job are implemented and exercised by
the evidence below. A dedicated dashboard-outage browser trace remains an
evidence limitation, not unimplemented product behavior.

The supplied visual references and scheduled runtime states were reviewed during
the final Playwright CLI pass. `EV-CONCLUDE-01` records the corrected grid,
empty default fields, centered card, exact 1440×900 and 375×812 viewports,
700 decorative cells, no horizontal overflow, and zero console errors beyond
the expected React DevTools informational message. Tablet interpolation and
protected-route rejection require no supplemental frame according to
`design/handoff.md`; the pending destination itself remains sibling-owned and
is not implemented here.

# Review findings

The single read-only Implementation Reviewer checkpoint completed on
2026-09-16. The three conclusion findings below were corrected through the
Plan-backed Builders and revalidated on 2026-09-17.

### `ACH-REVIEW-01` — Integrated reviewer findings resolved

- Browser `/api/auth/token` is blocked with `404`; internal server-side
  `auth.api.getToken()` remains available for protected API calls.
- Better Auth now accepts forwarded client IPs only through configured proxy
  CIDRs (`SHIFU_TRUSTED_PROXY_IPS`); production with no configured ingress
  fails closed instead of accepting browser-supplied IP headers. Local tests
  use loopback proxy configuration and `x-forwarded-for`.
- Active-session persistence clears a partially created session/user and
  expires the session cookie on failure; pending-cookie clearing occurs before
  the authenticated cookie is emitted.
- Dashboard entry reuses the access already validated by the route guard and
  suppresses all observability failures, preserving protected navigation.
- FastAPI owns one SQLAlchemy engine/database instance per app lifecycle;
  request dependencies create sessions, not engines. The default API port is
  aligned to `7777`.
- The sign-in page now uses TanStack Form, and middleware/BFF redirects use
  canonical `ROUTES` values.
- Pre-existing workspace changes outside SHIFU-62 were preserved; no sibling
  registration/confirmation or recovery/reset route behavior was added.

### `ACH-CONCLUDE-01` — Public sign-in background is visually occluded

- **Date:** 2026-09-17
- **Classification:** In-contract implementation correction; severity high for
  visual conformance.
- **Evidence:** Fresh Playwright CLI screenshots at 1440×900 and 375×812
  (`.playwright-cli/conclude-sign-in-desktop-1440x900.png` and
  `.playwright-cli/conclude-sign-in-mobile-375x812.png`) show a solid
  `#0a0a0c` background. The approved `design/a9R0Yh.png` and
  `design/Yzifg.png` references require the visible square grid. The grid is
  mounted by `RootLayout`, but the public sign-in surface's opaque
  `bg-background` stacking context covers it.
- **Affected contract:** `AC-01`, `AC-02`, `AC-06`, `AC-07`, `MV-01`, `MV-02`,
  `MV-03`, and the Design Contract's shared grid-background obligation.
- **Status:** resolved by removing the opaque `bg-background` wrapper class
  from `SignInPage`; `EV-CONCLUDE-01` confirms the visible grid at both exact
  viewports.

### `ACH-CONCLUDE-02` — Sign-in hierarchy and mobile alignment differ from handoff

- **Date:** 2026-09-17
- **Classification:** In-contract implementation correction; severity medium
  for visual conformance.
- **Evidence:** Inspection of the Builder's fresh screenshots
  (`.playwright-cli/sign-in-fix-desktop-1440x900.png` and
  `.playwright-cli/sign-in-fix-mobile-375x812.png`) confirms the grid fix but
  also shows the runtime-only subtitle `Continue sua jornada de aprendizagem.`
  and a top-aligned mobile card. The approved default references
  `design/a9R0Yh.png` and `design/Yzifg.png` omit that subtitle and center the
  card at their declared viewports.
- **Affected contract:** `AC-01`, `MV-01`, and the Design Contract's hierarchy,
  vertical-fit, and exact responsive composition obligations.
- **Status:** resolved by removing the uncontracted subtitle and centering the
  responsive public surface; `EV-CONCLUDE-01` confirms the corrected hierarchy
  and mobile geometry.

### `ACH-CONCLUDE-03` — Public form exposes local seed credentials by default

- **Date:** 2026-09-17
- **Classification:** In-contract implementation correction; severity high for
  privacy and default-state conformance.
- **Evidence:** Fresh `/login` snapshots and screenshots show
  `student.seed@shifu.com` and a populated password on the anonymous default
  form. `use-sign-in-page.ts` declares those values as default form state, and
  the current browser test asserts them. The handoff's default state is empty,
  with an e-mail placeholder and a masked password placeholder.
- **Affected contract:** `AC-01`, `AC-10`, `MV-01`, and the Design Contract's
  empty/default-state and browser-secret restrictions.
- **Status:** resolved by using empty form defaults, the approved placeholders,
  and updated hook/browser assertions; `EV-CONCLUDE-01` confirms no credential
  appears in the anonymous default DOM state.

### Reviewer evidence limitations

- The normal FastAPI REST tests use a disposable, migrated PostgreSQL
  Testcontainer and production SQLAlchemy repositories. The infrastructure
  failure regression case retains a controlled database double because it
  deliberately injects an unavailable dependency rather than destabilizing the
  shared test database.
- `CI-04` now passes with the Testcontainers fixture using isolated host port
  `17777` for the FastAPI callback because the shared local application already
  occupied the default `7777`; the production/local contract remains `7777`.
  The runtime fixture waits for the registered app, publishes through
  `/e/dev_key`, and uses a fresh ULID per run so persisted local Dev Server
  history cannot suppress the test event.
- The dashboard browser test now asserts one persisted event row per
  navigation. A dedicated browser trace with the event endpoint forced to
  `503` was not run; the provider's best-effort catch boundary is covered by
  the implementation and the normal dashboard continuity test.
- The connected Atlassian reader rejected the configured Cloud ID during this
  conclusion pass. Local Spec revision 20 and the prior authority evidence
  still record Identity PRD content `83001345`, version `1`, and Jira
  `SHIFU-62`; no external content was mutated. This source reread limitation
  is non-blocking because the local contract and recorded source metadata are
  unchanged.

# Candidate conformance snapshot

- **Contract:** `documentation/features/identity/sign-in/spec.md`, revision
  `20`, completed; source Jira `SHIFU-62`; canonical Identity PRD content
  `83001345`, version `1`. The PRD and Jira remain unchanged.
- **Scope match:** The integrated diff covers the assigned F1–F8 Plan scope:
  Identity core/server/database/messaging, Better Auth BFF, public sign-in and
  protected route composition, generated routes, REST-client parity, Compose
  callback configuration, tests, and SDD evidence. Unrelated pre-existing
  workspace changes were preserved and excluded from SHIFU-62 claims.
- **Allowed/prohibited paths:** Delivery-owned paths are the `apps/server`
  Identity/shared infrastructure and tests, `apps/web` sign-in/auth/routing/UI
  and tests, REST client, Compose/environment/tooling configuration, generated
  route metadata, migrations, and this feature artifact set. No registration,
  confirmation, recovery, reset, sibling page, or sibling business-state
  implementation was added for SHIFU-61 or SHIFU-63.
- **Tree/generated treatment:** The required Identity controller, pipe,
  provider, core use-case/event, outbox/listener, Inngest job/fixture, BFF,
  route, widget, colocated tests, REST example, migrations, and generated route
  tree are present. Generated route metadata was regenerated and reviewed.
- **Builder/Plan conformance:** Builder Core, Database, Server, Messaging, Web,
  UI, and Routing completed F1–F7; the Orchestrator completed F8 and resumed
  the UI and Messaging Builder Fixes for `ACH-CONCLUDE-01` through
  `ACH-CONCLUDE-03`. The final allowed scope is Identity/shared auth,
  persistence/outbox/messaging, BFF/routes/UI, REST parity, migrations,
  generated metadata, configuration, tests, and this feature's SDD/design
  artifacts. Prohibited sibling registration, confirmation, pending-page,
  recovery/reset, or unrelated business-state behavior is absent.
- **Behavior/state coverage:** Active, pending, invalid, throttled,
  infrastructure-failure, submitting, keyboard-focus, protected rejection,
  secret-boundary, responsive, and main-page event states are covered by the
  `AC-*`, `MV-*`, `EV-*`, and resolved `ACH-*` records above. SHIFU-61/63
  destination behavior remains explicitly excluded.
- **Runtime/REST/visual:** The FastAPI/Inngest callback contract remains
  `7777`; the final isolated Testcontainers job gate used `17777` because the
  shared local application already occupied `7777`. CI-04 and CI-09 pass 1/1
  using the registered job and current event contract.
  The three Identity operations have one current credential-free request each
  in `apps/server/rest-client/identity/identity.rest`. Fresh 1440×900 and
  375×812 screenshots and inspected design references are recorded in
  `EV-CONCLUDE-01`; derived states follow the approved handoff contract.
- **Limitations/findings:** The dedicated forced-dashboard-503 browser trace
  remains unexecuted; the normal best-effort continuity path and provider catch
  boundary are evidenced. The prior persistent Dev Server event-ID collision
  was resolved with explicit registration readiness and fresh test ULIDs. The
  Atlassian reread limitation is recorded above. No blocking finding remains.

| Acceptance | RF coverage | Automated evidence | Runtime/manual evidence | Visual evidence | Status |
| --- | --- | --- | --- | --- | --- |
| `AC-01` | `FR-01`, `FR-07` | `EV-F6-F7-01` | `EV-CONCLUDE-01` | `EV-CONCLUDE-01` | passed |
| `AC-02` | `FR-01`, `FR-07` | `EV-F6-F7-01` | `EV-MV-02`, `EV-CONCLUDE-01` | `EV-CONCLUDE-01` | passed |
| `AC-03` | `FR-02`, `FR-06` | `EV-F3-01`, `EV-F5-01` | `EV-MV-03` | `EV-MV-01-03` | passed |
| `AC-04` | `FR-03`, `FR-05` | `EV-F3-01`, `EV-F5-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |
| `AC-05` | `FR-04`, `FR-05` | `EV-F5-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |
| `AC-06` | `FR-06` | `EV-F6-F7-01` | `EV-MV-02`, `EV-CONCLUDE-01` | `EV-CONCLUDE-01` | passed |
| `AC-07` | `FR-06`, `FR-07` | `EV-F5-01` | `EV-MV-03`, `EV-CONCLUDE-01` | `EV-CONCLUDE-01` | passed |
| `AC-08` | `FR-06` | `EV-F5-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |
| `AC-09` | `FR-05` | `EV-F3-01`, `EV-F6-F7-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |
| `AC-10` | `FR-02`–`FR-05` | `EV-F5-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |
| `AC-11` | `FR-08` | `EV-F1-01`, `EV-F3-01`, `EV-F4-01`, `EV-F6-F7-01`, `EV-REF-16-01` | `EV-MV-04-08` | `EV-MV-04-08` | passed |

## Traceability and lessons

| RP/JN | RF/AC coverage | Evidence | Delivery disposition | PRD checkbox |
| --- | --- | --- | --- | --- |
| `RP-03` / `JN-03` | `FR-01`–`FR-06`, `AC-01`–`AC-08`, `AC-11` | `EV-F1-01`, `EV-F3-01`, `EV-F4-01`, `EV-F5-01`, `EV-F6-F7-01`, `EV-CONCLUDE-01`, `EV-MV-01-08` | implemented | unchanged |
| `RP-07` | `FR-03`, `FR-05`, `AC-04`, `AC-09`, `AC-10` | `EV-F3-01`, `EV-F5-01`, `EV-MV-04-08` | implemented for sign-in | unchanged |
| `RP-10` | `FR-01`, `FR-06`, `FR-07`, `AC-01`, `AC-02`, `AC-06`, `AC-07` | `EV-F6-F7-01`, `EV-CONCLUDE-01`, `EV-MV-01-03` | implemented | unchanged |

- **Lesson / authority disposition:** Persistent local Inngest runtimes require
  explicit app-registration readiness and unique event IDs for repeatable test
  runs. This is feature-local runtime evidence already captured in the Spec,
  Plan, Evaluation, and `documentation/tooling.md`; no global Rule Pack change
  is needed.
- **Lesson / authority disposition:** The local server callback must use the
  documented `7777` port and Compose host-gateway mapping. `spec.md` and
  `documentation/tooling.md` already contain this factual alignment; no further
  architecture or product-authority change is required.

# Evidence log

### `EV-BASELINE-01` — Pre-implementation repository baseline

- **Date:** 2026-09-16
- **Scope:** Existing web/server repository before F1 changes.
- **Result:** Web `check:lint`, `check:architecture`, `check:types`, and
  `test:unit` passed; `test:unit` reported no test files. Server
  `check:lint`, `check:architecture`, `check:types`, `test:unit`, and
  `test:integration` passed; the server integration suite had one existing
  health-controller test pass.
- **Finding:** Web lint reported four existing `noImportantStyles` warnings
  in `apps/web/src/ui/shared/styles/global.css` lines 122–125. No fixes were
  applied during baseline. The existing pnpm configuration warning about
  `onlyBuiltDependencies` was also observed.
- **Runtime:** Docker Compose PostgreSQL, Inngest, and Mailpit containers were
  running; web and FastAPI processes were not started for baseline inspection.
- **Acceptance mapping:** Baseline only; it is not acceptance evidence for
  `AC-01`–`AC-11`.

Failed attempts, unavailable services, stale evidence, and corrections must be
appended here with their exact command or sensor result and linked acceptance
criteria.

### `EV-F1-01` — Identity core implementation and focused validation

- **Date:** 2026-09-16
- **Scope:** `Authentication`, canonical `MainPageEnteredEvent`,
  `SignInUseCase`, `PublishMainPageEnteredUseCase`, and removal of the obsolete
  FastAPI token-issuance port.
- **Result:** `cd apps/server && uv run pytest tests/core/identity/use_cases/test_sign_in_use_case.py tests/core/identity/use_cases/test_publish_main_page_entered_use_case.py` passed 8 tests.
- **Static validation:** `cd apps/server && uv run poe check:lint`,
  `check:architecture`, and `check:types` passed after the implementation.
- **Evidence:** Active and pending accounts return only the contracted safe
  projection; invalid, deleted, exact-case-mismatched, unknown, and
  wrong-password credentials raise the generic domain error; event identity,
  account, and UTC timestamp are injected and persisted through one transaction
  collaboration. No acceptance criterion is promoted to passed from this
  unit-level evidence alone.

### `EV-F2-01` — Technical persistence and transaction boundary

- **Date:** 2026-09-16
- **Scope:** Six Better Auth metadata tables, the durable `events` outbox,
  SQLAlchemy event repository, Identity transaction owner, Alembic revisions
  `b8f67e3c9a21` and `c4d82f1e7a30`, and metadata registration.
- **Result:** `cd apps/server && uv run poe db:upgrade` applied both revisions;
  `uv run alembic check` reported no new upgrade operations. PostgreSQL is at
  head `c4d82f1e7a30` and contains all six `better_auth_*` tables plus `events`;
  named constraints and `trg_events_notify_after_insert` were verified.
- **Static/runtime validation:** Server `check:lint`, `check:types`,
  `check:architecture`, `test:unit`, and `test:integration` passed. The unit
  suite has 8 Identity core tests; the existing integration suite has 1 health
  test. The two existing Starlette/anyio deprecation warnings remain.
- **Safety disposition:** A downgrade was not run against the shared database
  because it would remove the newly added schema. Isolated-database downgrade
  coverage remains required before final acceptance.

### `EV-RESUME-01` — Resumed implementation dependency gate

- **Date:** 2026-09-16
- **Scope:** F3/F5–F7 resume check against SHIFU-61 and SHIFU-63.
- **Result:** Both Jira issues remain `A fazer`. The local repository contains
  no concrete password-hashing adapter, pending-confirmation route/context, or
  recovery route from those deliveries; only the existing core ports and
  pre-existing recovery event declarations are present.
- **Disposition at revision 13:** F3/F5–F7 remained pending. No substitute hash
  adapter, pending route, recovery route, or placeholder UI was created. This
  historical gate is superseded by the revision-14 independence amendment.
- **Acceptance mapping:** This is a dependency/blocker record, not evidence
  for `AC-01`–`AC-11`.

### `EV-SPEC-14-01` — Independent delivery contract amendment

- **Date:** 2026-09-16
- **Scope:** Revision 14 reconciliation of SHIFU-62 against the canonical
  Identity PRD and the current SHIFU-61/SHIFU-63 Jira state.
- **Result:** SHIFU-61 and SHIFU-63 remain parallel product authorities for
  registration/confirmation and recovery/reset behavior, respectively. Their
  unfinished Jira status is not a SHIFU-62 build or test prerequisite. The
  amended contract adds a replaceable SHIFU-62 Argon2id verifier composition and
  exact canonical URL/redirect assertions, while prohibiting sibling route files
  and sibling product-flow duplication.
- **Authority check:** Identity PRD content `83001345`, version `1`, was reread
  on 2026-09-16. No Confluence or Jira mutation was made.
- **Disposition:** Prior F1/F2 evidence remains valid for the amended contract;
  F3 onward remains pending until implementation evidence is complete.
- **Acceptance mapping:** Amendment/traceability evidence only; it does not pass
  `AC-01`–`AC-11`.

### `EV-F3-SETUP-01` — Independent server-boundary prerequisites

- **Date:** 2026-09-16
- **Scope:** SHIFU-62-owned Argon2id verifier composition and server auth settings.
- **Result:** `argon2-cffi` and `PyJWT[crypto]` are resolved in `apps/server/uv.lock`;
  `EnvironmentSettings` exposes local issuer, audience and JWKS URL values; and
  `Argon2idHashProvider` implements the revision-14 parameters and false-on-invalid
  verification behavior.
- **Validation:** Ruff and strict Pyright pass for the adapter. This setup evidence
  does not pass the controller, JWT/JWKS, persistence, or acceptance criteria.
- **Disposition at capture time:** This setup record was captured before the
  controller composition and consuming REST tests; the later `EV-F3-01` record
  supersedes its implementation-status note.

### `EV-BUILDERS-14-01` — Revision-14 Builder assignments

- **Date:** 2026-09-16
- **Scope:** Plan-backed implementation ownership for revision 14.
- **Assignments:** `identity-api-builder` owns the F3 Identity REST/provider/pipe
  source and consuming controller tests; the Orchestrator owns app composition,
  shared/generated paths, dependency/config integration and SDD artifacts.
  F4/F5/F6/F7 builders will be activated only after their declared dependencies
  are stable, with disjoint paths and no SHIFU-61/SHIFU-63 implementation scope.
- **Validation exits:** F3 focused controller tests plus server lint, types,
  architecture and REST-client parity; all Builder reports require Orchestrator
  diff inspection before evidence is promoted.
- **Disposition:** Assignment evidence only; no acceptance criterion is passed.

### `EV-F3-01` — Integrated FastAPI Identity boundary

- **Date:** 2026-09-16
- **Scope:** Argon2id composition, sign-in, current-session/JWKS, main-page-entry
  controllers, Identity pipe, REST artifact, and application registration.
- **Result:** `cd apps/server && uv run pytest tests/rest/controllers/identity`
  passed 5 tests against the PostgreSQL Testcontainer fixture; server Ruff,
  basedpyright, Tach architecture, Alembic check,
  full pytest, and `uv build` passed. The REST artifact contains exactly one
  labeled credential-free request for each of the three Identity routes.
- **Error boundary:** Controllers contain no `try`/`except` blocks. Invalid
  credentials and unexpected Identity failures are mapped by the global
  FastAPI handlers registered in `create_app`; the infrastructure-failure
  regression test verifies the safe `503 identity_unavailable` contract.
- **Runtime/privacy:** Real local HTTP checks returned the safe active/pending/
  invalid contracts; valid EdDSA projection succeeded, stale access versions
  were rejected, and no password/hash/JWT/private key appeared in response
  bodies or the browser-facing route contract.

### `EV-REF-16-01` — Shared identifier provider boundary

- **Date:** 2026-09-16
- **Scope:** Core `IdentifierProvider`, shared `SystemIdentifierProvider`, and
  `IdentityPipe` composition.
- **Result:** The private `_SystemIdentifierProvider` and its timestamp/base32
  implementation were removed from `IdentityPipe`. The pipe now returns the
  shared provider through the provider-neutral core interface; the core event
  use case remains framework-independent.
- **Validation:** Server strict types, architecture, lint, and the 13 focused
  Identity core/controller tests passed. No provider-owned test file was added.

### `EV-REF-17-01` — Shared Inngest broker boundary

- **Date:** 2026-09-16
- **Scope:** `InngestBroker` module location, shared Inngest package exports,
  and FastAPI application composition.
- **Result:** The broker now lives at
  `apps/server/src/shifu/shared/messaging/inngest/inngest_broker.py`; the
  package exports it alongside `InngestMessaging`, and `FastAPIApp` imports the
  broker from that shared Inngest package. The former generic broker export no
  longer exposes the implementation.
- **Validation:** Server lint, strict types, architecture, focused pytest
  (`13 passed, 1 skipped`), and the real Inngest job on port `7777` (`1 passed`)
  pass after the move; this remains an open implementation record.

### `EV-REF-18-01` — Shared provider folder boundary

- **Date:** 2026-09-16
- **Scope:** `SystemClockProvider` and `SystemIdentifierProvider` package
  layout and all server composition imports.
- **Result:** Each provider now has a provider-named folder containing its
  implementation and `__init__.py` export. No provider remains directly under
  `apps/server/src/shifu/shared/providers`.
- **Validation:** Provider-folder Ruff checks, direct package imports,
  architecture, the full server strict type gate, and the full server pytest
  suite pass after the SQLAlchemy model rename was completed.

### `EV-REF-19` — Shared SQLAlchemy utility class boundaries

- **Date:** 2026-09-16
- **Scope:** Shared SQLAlchemy serialization and session infrastructure.
- **Result:** `serialization.py` now exposes the `Serialization` class with
  static recursive encode/decode methods, and `session.py` now exposes the
  `Session` class with static engine creation and transaction context methods.
  All mappers, repositories, application composition, seed composition, and
  the Inngest broker use the class APIs; transaction commit/rollback and value
  conversion behavior are unchanged.
- **Validation:** Focused Ruff and basedpyright checks pass, no legacy function
  imports or call sites remain, and the full server pytest suite validates the
  class-based SQLAlchemy utilities through real imports and REST execution.

### `EV-REF-20-01` — Testcontainers job-test isolation

- **Date:** 2026-09-16
- **Scope:** Real Inngest job fixture infrastructure and dependency isolation.
- **Result:** The fixture now uses disposable `PostgresContainer` and
  `DockerContainer('inngest/inngest:v1.41.1')` instances, random-maps the
  Inngest port, injects the container database URL into FastAPI, waits for
  endpoint/function registration, and cleans up both containers after the
  session. Compose remains available for ordinary local development.
- **Validation:** Testcontainers imports and fixture-local Ruff checks pass;
  the PostgreSQL fixture is exercised by the full REST suite. The optional
  Docker-backed job selection remains independently gated by
  `SHIFU_RUN_REAL_INNGEST_TESTS=1`.

### `EV-REST-DB-01` — Real PostgreSQL REST fixture and repository coverage

- **Date:** 2026-09-16
- **Scope:** Session-scoped PostgreSQL Testcontainers lifecycle, Alembic
  migration setup, function-scoped table cleanup, injected FastAPI engine,
  Identity REST tests, and PostgreSQL LISTEN shutdown behavior.
- **Result:** `tests/fixtures/postgres.py` starts `postgres:17-alpine` with a
  random host port, applies `alembic upgrade head` using the container URL,
  and truncates application tables before and after each test while preserving
  `alembic_version`. `FastAPIApp.register` receives that engine through the
  shared `client` fixture. Active sign-in persists an `Account` through
  `SqlalchemyIdentityDatabase` and verifies the submitted password with the
  production `Argon2idHashProvider`; invalid credentials query the real
  repository.
- **Validation:** `TESTCONTAINERS_RYUK_DISABLED=true uv run pytest -p no:tach -q
  tests/rest` passed 6 tests; the full server suite passed 14 tests with 1
  intentionally skipped Docker-backed job selection. Ruff, formatting, and
  basedpyright passed across `src` and `tests`.
- **Correction:** The shared event listener now opens a dedicated psycopg
  connection rather than closing a SQLAlchemy pooled wrapper from the LISTEN
  thread. This prevents `TestClient` teardown from blocking while preserving
  the production outbox relay boundary.
- **Disposition:** Real PostgreSQL is now the default REST-test path. Only the
  deterministic infrastructure-failure regression keeps a controlled double;
  it does not replace repository coverage.

### `EV-F4-01` — Durable relay and Inngest composition

- **Date:** 2026-09-16
- **Scope:** Shared broker, outbox reservation/acknowledgement lifecycle,
  logging-only Identity job, Compose discovery, and Docker-capable test fixture.
- **Result:** Compose was recreated with the pinned Inngest image, one
  `-u http://host.docker.internal:7777/api/inngest` callback, and the Linux
  `host-gateway` mapping. The broker was exercised against the live local
  PostgreSQL/Inngest stack: a committed main-page event moved from pending to
  published, the Dev Server received the stable event ID, and Dashboard
  continuity remained intact. `SHIFU_RUN_REAL_INNGEST_TESTS=1
  SHIFU_INNGEST_FASTAPI_PORT=7777 uv run poe test:jobs` passed the real
  registered-job test, including the structured `identity.main_page_entered`
  log and canonical payload fields.

### `EV-F4-02` — Animus-aligned Shifu Inngest messaging composition

- **Date:** 2026-09-16
- **Scope:** Shared `InngestMessaging` composition,
  `IdentityInngestMessaging` job declaration, and application lifecycle
  registration.
- **Result:** `InngestMessaging.register(app)` creates the configured
  process-wide Shifu client, consumes the Identity job group through
  `IdentityInngestMessaging.register_jobs`, and serves the single
  `/api/inngest` endpoint. `FastAPIApp` consumes the returned client for the
  durable broker, so the relay and registered jobs share one client and no job
  is registered at import time. The client uses the `uvicorn` logger
  consistently with the Animus composition pattern.
- **Validation:** `cd apps/server && uv run basedpyright`, focused Ruff checks,
  and `SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=7777 uv run poe
  test:jobs` passed; the real Docker-backed test observed the registered
  Identity job and its structured log. The job payload boundary now uses a
  strict Pydantic model with forbidden extra fields, non-empty identifiers, and
  UTC timestamp validation; targeted basedpyright and direct valid/invalid model
  checks passed.
- **Current validation limitation:** A fresh pytest import was not repeatable
  after an unrelated in-progress worktree rename removed
  `shared/database/sqlalchemy/base.py` while existing model imports still
  reference it. No unrelated database files were changed for this job update;
  the earlier real Docker-backed job result remains recorded above.
- **Scope disposition:** No additional product jobs were invented. The registry
  exposes the domain grouping pattern for future contracted Shifu jobs while
  preserving the SHIFU-62 logging-only behavior and SHIFU-61/SHIFU-63 boundary.

### `EV-F5-01` — Better Auth BFF and handler integration

- **Date:** 2026-09-16
- **Scope:** Server-only Better Auth provider, Identity REST service, technical
  projection/session persistence, pending verification handoff, limiter, safe
  failures, and browser-safe auth provider.
- **Result:** Playwright handler requests passed active and pending scenarios;
  active responses set a 30-day HttpOnly same-origin session cookie, pending
  responses set only an opaque 15-minute signed handoff cookie, invalid
  credentials returned the generic 401 contract, and no secret-bearing value
  appeared in the response body/cookie. The browser-facing `/api/auth/token`
  endpoint returned 404 while server-side token generation remained internal.
  Runtime throttle evidence produced ten 401s followed by a 429 with
  `x-retry-after: 300` for one configured client IP.
- **Cleanup:** PostgreSQL inspection after the suite reported zero temporary
  identity accounts, technical users, sessions, verification rows, outbox rows,
  or test limiter rows.

### `EV-F6-F7-01` — UI, routing, and integrated browser validation

- **Date:** 2026-09-16
- **Scope:** Public `/login`, shared responsive primitives, auth-context hook,
  protected module routes, Dashboard entry middleware, route generation, and
  production build.
- **Result:** Web Biome, TypeScript, dependency-cruiser, unit, route-generation,
  and build checks passed. Unit coverage is 10 files/22 tests. The complete
  Playwright suite passed 18 tests across sign-in handler/page, Dashboard,
  Account, Curriculum, Learning, Gamification, Intelligence, root layout, and
  responsive AppLayout suites. Anonymous and rejected protected access redirected
  to `/login` before protected content rendered.

### `EV-MV-01-03` — Fresh public visual and failure-state inspection

- **Date:** 2026-09-16
- **Evidence:** Playwright CLI inspected the public `/login` accessibility tree
  and captured `/home/petros/projects/shifu/.playwright-cli/sign-in-desktop-1440x900.png`
  at 1440×900 and `/home/petros/projects/shifu/.playwright-cli/sign-in-mobile-final.png`
  at 375×812. The mobile document `scrollWidth` was 375, with no clipping; the
  public shell omitted application navigation; canonical `/register` and
  `/forgot-password` links were present. A delayed controlled 503 trace showed
  `Entrando...` with submit/email/password disabled, followed by the safe
  infrastructure message with both fields preserved. Clean page inspection
  reported zero console errors; the only error in the delayed trace was the
  intentionally returned 503 request.

### `EV-MV-02` — Keyboard and submitting behavior

- **Date:** 2026-09-16
- **Result:** The semantic form exposed labeled e-mail/password controls, a
  keyboard-accessible password visibility action, a submit button and canonical
  links. During the delayed request, the submit and both fields were disabled,
  the button text changed to `Entrando...`, and the e-mail value remained
  visible. The hook guard and integration suite prevent duplicate submission;
  recovery preserved both values.

### `EV-MV-03` — Failure privacy and recovery

- **Date:** 2026-09-16
- **Result:** Controlled 401 UI integration displayed only `E-mail ou senha
  inválidos.` and cleared the password while retaining e-mail. Controlled 503
  displayed only the safe retry message and retained both fields. The real
  handler returned the same generic 401 body and no session cookie.

### `EV-MV-04-08` — Runtime state matrix

- **Date:** 2026-09-16
- **Result:** Temporary active-account runtime checks proved persisted technical
  user/session creation, fixed approximately 30-day expiry, two concurrent
  sessions, current-session projection through EdDSA/JWKS, stale-version
  rejection and deletion of the rejected session. Pending-account checks proved
  the activation-only response, canonical `/pending-confirmation` redirect,
  opaque 15-minute verification handoff, and absence of technical user/session.
  Ten same-IP attempts followed by the eleventh 429 proved database limiter
  behavior. Dashboard entry requests created exactly one outbox row per
  navigation and the live relay moved them to published while the page stayed
  available. These checks used
  temporary data only and the cleanup query reported zero temporary rows.

### `EV-F8-01` — Final integrated gates after reviewer corrections

- **Date:** 2026-09-16
- **Scope:** Reviewer-corrected candidate, route generation, builds, database
  migration state, and final integrated validation.
- **Result:** Web TypeScript, Biome, dependency-cruiser, 22 unit tests, route
  generation, production build, and 18 Playwright tests passed. Server Ruff,
  basedpyright, Tach architecture, full pytest (`14 passed, 1 skipped`),
  Alembic upgrade/check, and `uv build` passed. `git diff --check` passed.
- **Review linkage:** `ACH-REVIEW-01` was resolved in the candidate before
  these results were captured. The real job gate is green on FastAPI port
  `7777`.

### `EV-CONCLUDE-01` — Final correction and conformance validation

- **Date:** 2026-09-17
- **Scope:** Resolved `ACH-CONCLUDE-01` through `ACH-CONCLUDE-03`, final
  public sign-in UI, Testcontainers Inngest fixture, and integrated candidate
  at Spec revision `20`.
- **Correction results:** `SignInPage` no longer covers the shared grid,
  removes the uncontracted subtitle, and centers the public card. The hook now
  starts with empty e-mail/password values; the page exposes the approved
  `voce@exemplo.com` and `••••••••` placeholders. The Inngest fixture now
  starts the image with `inngest dev ...`, matching Compose.
- **Automated results:**
  `pnpm --filter web check:lint`, `check:architecture`, `check:types`,
  `test:unit` (10 files/24 tests), `test:integration` (18 passed), and
  `build` passed. Server `uv run poe check:lint`, `check:architecture`,
  `check:types`, `test:unit` (8 passed), `test:integration` (6 passed),
  `SHIFU_RUN_REAL_INNGEST_TESTS=1 SHIFU_INNGEST_FASTAPI_PORT=17777 uv run poe
  test:jobs` (1 passed), and `build` passed. Route generation and
  `git diff --check` passed.
- **REST/runtime results:** FastAPI health and the persistent local Inngest app
  were healthy; the registered `shifu` app reported one function. The
  Testcontainers job emitted the canonical logging event and completed without
  a skip. `apps/server/rest-client/identity/identity.rest` has one current,
  credential-free request for each of the three Identity routes.
- **Fresh visual/manual results:** Playwright CLI captured and visually
  inspected the final default state at
  `/home/petros/projects/shifu/.playwright-cli/conclude-sign-in-final-desktop-1440x900.png`
  and
  `/home/petros/projects/shifu/.playwright-cli/conclude-sign-in-final-mobile-375x812.png`.
  The desktop card is 440 px wide at 1440×900; the mobile card is 335 px wide
  within 20 px gutters at 375×812. Both have 700 grid cells, empty fields,
  correct placeholders, no horizontal overflow, no authenticated chrome, and
  no console errors beyond the expected React DevTools informational message.
  The invalid mobile state is recorded at
  `/home/petros/projects/shifu/.playwright-cli/conclude-sign-in-final-invalid-mobile-375x812.png`
  with retained e-mail, cleared password and generic alert. The recoverable
  desktop failure is recorded at
  `/home/petros/projects/shifu/.playwright-cli/conclude-sign-in-final-unavailable-desktop-1440x900.png`
  with both values retained and alert focus. The submitting desktop state is
  recorded at
  `/home/petros/projects/shifu/.playwright-cli/conclude-sign-in-final-submitting-desktop-1440x900.png`
  with `Entrando...`, disabled controls, and visible progress. Intentional
  mocked 401/503 responses are classified as expected network errors; clean
  default/submitting inspections had no console errors.
- **Acceptance mapping:** Refreshes `AC-01`, `AC-02`, `AC-06`, `AC-07`,
  `AC-10`, `MV-01`, `MV-02`, and `MV-03`; all other acceptance rows retain
  their current evidence from `EV-F1-01` through `EV-F8-01` and
  `EV-MV-04-08`.
- **Limitations:** The dedicated forced-dashboard-503 browser trace remains
  unexecuted; the normal best-effort continuity path and provider catch
  boundary are covered. The connected Atlassian source reread was unavailable
  in this pass and is recorded as a non-blocking external-reader limitation
  above.
