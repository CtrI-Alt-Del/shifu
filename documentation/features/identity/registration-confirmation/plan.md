---
title: Identity registration and account confirmation implementation plan
status: in_progress
spec: ./spec.md
spec_revision: 12
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-61
last_updated_at: 2026-09-23
---

# Execution status

- **Spec:** [`spec.md`](./spec.md), revision `12`, status `draft` during PR #9
  correction reconciliation; source is
  `SHIFU-61`, Identity PRD `83001345` v1 and Communication PRD `86114306` v1.
- **Why Plan-backed:** This delivery crosses Identity and Communication cores,
  composition, PostgreSQL/Alembic, Inngest jobs, a generated React Email package,
  FastAPI/BFF routes, responsive UI, lockfiles, CI and real runtime validation.
- **Plan:** `in_progress`; Evaluation baseline `EV-BASELINE-01` is recorded and
  implementation waves are active.
- **Next action:** Validate PR #9 corrections, restore the Spec to `ready` after
  contract reconciliation, then rerun the independent F8 review.
- **Active blockers/dependencies:** Docker PostgreSQL, Inngest and Mailpit are
  required for integration and job validation. No product or contract blocker
  remains; SHIFU-62 is a reconciled Identity dependency for sign-in e-mail
  normalization and existing session/BFF boundaries.
- **Builders:** `Builder Identity Core`, `Builder Communication Core`, and
  `Builder Email Package` are the initial parallel assignments. The Orchestrator
  owns SDD artifacts, package installation, lockfiles, migrations, generated
  artifacts, root/CI configuration, cross-Builder integration and final gates.
- **Shared ownership:** `apps/server/src/shifu/composition`, `apps/server/src/shifu/app.py`,
  `apps/server/uv.lock`, `pnpm-lock.yaml`, generated route metadata, the Alembic
  migration, generated e-mail output and `.github/workflows` remain Orchestrator
  integration paths.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` is `ready` at revision `11`; independent Spec review passed. | Orchestrator | `passed` | Preserve revision 11 through every phase boundary. |
| Canonical authorities | Identity PRD `83001345` v1 and Communication PRD `86114306` v1 are recorded and reread in the Spec. | Orchestrator | `passed` | Do not mutate Jira or Confluence as an implementation side effect. |
| Infrastructure | PostgreSQL, Inngest Dev Server, Mailpit and Docker-capable test runtime are available. | Orchestrator / Validation | `pending` | Verify health before server integration and real-job phases. |
| Package/runtime dependencies | Existing pnpm/uv manifests and lockfiles accept the approved React Email, provider and encryption dependencies. | Orchestrator | `pending` | Install through declared repository tooling and review generated lockfile diffs. |
| Design and route references | `design/handoff.md`, `documentation/design.md`, route ledger and REST-client paths are available. | Builder Web / Orchestrator | `passed` | Preserve exact viewport/state coverage during implementation. |

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Identity Core` | F1 | Registration, confirmation, resend, expiry, pending-context, delivery-state and cancellation contracts are implemented in the Identity core. | — | F2, F3 | `in_progress` | Identity unit tests and core architecture checks pass; no adapter or Communication imports cross core. |
| 1 | `Builder Communication Core` | F2 | Communication request, delivery, cancellation, persistence ports and internal cancellation state are implemented. | — | F1, F3 | `in_progress` | Communication unit tests pass; encrypted data, idempotency and `cancelled` redaction semantics are covered. |
| 1 | `Builder Email Package` | F3 | React Email source, deterministic HTML/manifest generation and server package-data verifier are implemented. | — | F1, F2 | `in_progress` | Package code/types/build checks pass and generated artifacts match the renderer contract. |
| 2 | `Builder Server Integration` | F4 | Identity/Communication persistence, migration, providers, REST controllers, composition gateway and app wiring are integrated. | F1, F2, F3 | F5 | `pending` | Alembic drift, server lint/types/architecture and PostgreSQL REST integration pass. |
| 2 | `Builder Messaging` | F5 | Outbox-backed delivery, expiry fan-out, cancellation and delivery-state jobs are registered on the single Inngest endpoint. | F1, F2, F4 | F6 | `pending` | Real Inngest job tests prove registration, retries, duplicate safety, cancellation/redaction and bounded fan-out. |
| 2 | `Builder Web` | F6 | Same-origin BFF operations, auth-context actions, public routes and registration/pending/confirmation widgets are implemented. | F4 | F5 | `pending` | Web lint/architecture/types/unit/integration/build and route generation pass; route paths remain thin. |
| 3 | `Builder Validation` | F7 | Real local-service, browser, Mailpit, privacy, retry/recovery and expiry/reuse validation is executed. | F4, F5, F6 | — | `pending` | Every applicable `CA-*`, `VM-*`, REST artifact and fresh visual state has evidence. |
| 3 | `Orchestrator / Implementation Reviewer` | F8 | Complete integrated candidate is independently reviewed and all verified findings are resolved. | F1–F7 and evidence baseline | — | `pending` | Evaluation is ready for `conclude-spec`; no stale evidence or unowned path remains. |

### F1 — Establish Identity core

#### F1-T1 — Implement Identity registration and lifecycle use cases

- **Status/owner:** `pending` — Builder Identity Core
- **Depends/parallel:** No dependency; parallel with F2 and F3.
- **Paths:** `apps/server/src/shifu/identity/core/domain`, `apps/server/src/shifu/identity/core/interfaces`, `apps/server/src/shifu/identity/core/use_cases`, Identity unit tests in `apps/server/tests/core/identity/use_cases/`.
- **Traceability:** `RF-01`–`RF-04`, `RF-07`, `RF-09`, `RF-10`; `CA-02`–`CA-12`; Identity `RP-01`, `RP-02`, `RP-08`, `JN-01`, `JN-02`, `JN-08`.
- **Outcome:** Pending account creation, one-use confirmation, generic resend, immutable expiry and normalized e-mail identity are implemented behind framework-independent ports.
- **Rules:** `documentation/rules/core-layer-rules.md`, `documentation/rules/python-conventions-rules.md`, `documentation/rules/use-case-testing-rules.md`.
- **Risks/controls:** Cross-module coupling and privacy leaks are controlled by Identity-owned ports, ID-only events and safe projections from the Spec.
- **Exit:** Focused Identity unit tests, `uv run poe check:architecture` from `apps/server`, and Orchestrator path/contract review pass.

### F2 — Establish Communication core and persistence contract

#### F2-T1 — Implement queue, delivery, cancellation and redaction behavior

- **Status/owner:** `pending` — Builder Communication Core
- **Depends/parallel:** No dependency; parallel with F1 and F3.
- **Paths:** `apps/server/src/shifu/communication/core`, Communication unit tests, Communication database models/mappers/repositories listed in the Spec.
- **Traceability:** `RF-03`–`RF-06`; `CA-03`–`CA-07`, `CA-10`–`CA-12`; Communication `RP-01`–`RP-07`, `JN-01`, `JN-03`–`JN-06`.
- **Outcome:** Stable Communication IDs, encrypted retry data, provider-safe terminal state, internal `cancelled` supersession/redaction and idempotent persistence are implemented.
- **Rules:** `documentation/rules/core-layer-rules.md`, `documentation/rules/database-layer-rules.md`, `documentation/rules/messaging-layer-rules.md`, `documentation/rules/python-conventions-rules.md`.
- **Risks/controls:** Partial failure and duplicate delivery are controlled by transaction ownership, unique keys, compare-and-set transitions and retained operational metadata only.
- **Exit:** Queue/delivery/cancellation unit tests and persistence contract review pass without importing Identity core.

### F3 — Build generated e-mail package

#### F3-T1 — Generate the deterministic confirmation template contract

- **Status/owner:** `pending` — Builder Email Package
- **Depends/parallel:** No dependency; parallel with F1 and F2.
- **Paths:** `packages/email`, `apps/server/scripts/verify_email_package_data.py`, generated server template artifacts, `packages/email/package.json`, root `pnpm-lock.yaml`, and the e-mail CI workflow.
- **Traceability:** `RF-05`; `CA-05`, `CA-06`, `CA-12`; Communication `RP-02`, `RP-03`, `RP-07`.
- **Outcome:** React Email source builds stable HTML and a strict placeholder manifest consumed by Python without a runtime Node process.
- **Rules:** `documentation/rules/email-package-rules.md`, `documentation/rules/typescript-conventions-rules.md`, `documentation/rules/python-conventions-rules.md`.
- **Risks/controls:** Artifact drift is controlled by deterministic generation, manifest validation, wheel inspection and `.github/workflows/email-package-ci.yaml`.
- **Exit:** `pnpm --dir packages/email check:code`, `pnpm --dir packages/email check:types`, `pnpm --dir packages/email build`, and server wheel package-data verification pass.

### F4 — Integrate server, persistence and composition

#### F4-T1 — Wire PostgreSQL, REST controllers and composition gateway

- **Status/owner:** `pending` — Builder Server Integration
- **Depends/parallel:** F1, F2 and F3; parallel with F5 after stable event contracts.
- **Paths:** Identity/Communication database models, mappers, repositories, migrations, providers, REST controllers/routers, `apps/server/src/shifu/composition`, `apps/server/src/shifu/app.py`, `apps/server/tach.toml`, settings, `.env.example`, and `apps/server/rest-client/identity/identity.rest`.
- **Traceability:** `RF-01`–`RF-10`; `CA-02`–`CA-12`; all REST and persistence rows in the Spec.
- **Outcome:** Real FastAPI/PostgreSQL route boundaries, output-port composition, cookie-safe pending context and persistence migration are integrated with no cross-core imports.
- **Rules:** `documentation/rules/rest-layer-rules.md`, `documentation/rules/server-app-layer-rules.md`, `documentation/rules/database-layer-rules.md`, `documentation/rules/provision-layer-rules.md`, `documentation/rules/controllers-testing-rules.md`.
- **Risks/controls:** Migration drift, route leakage and incomplete REST parity are controlled by Alembic checks, real PostgreSQL controller tests and one labeled `.rest` request per route.
- **Exit:** `uv run alembic check`, `uv run poe check:lint`, `uv run poe check:architecture`, `uv run poe check:types`, `uv run poe test:integration`, and REST-client parity review pass from `apps/server`.

### F5 — Register durable messaging jobs

#### F5-T1 — Implement delivery, expiry and cross-module consumers

- **Status/owner:** `pending` — Builder Messaging
- **Depends/parallel:** F1/F2 and F4 composition; parallel with F6.
- **Paths:** Identity and Communication Inngest jobs/registrars, shared registration wiring, `apps/server/tests/messaging/`, and `apps/server/tests/fixtures/inngest_fixture.py`.
- **Traceability:** `RF-05`, `RF-06`, `RF-10`; `CA-05`–`CA-07`, `CA-10`–`CA-12`; `JN-03`–`JN-06`, `JN-08`.
- **Outcome:** One shared Inngest endpoint hosts bounded expiry fan-out, durable delivery retries, local strict cross-module transport schemas, cancellation/redaction and safe delivery-state consumers.
- **Rules:** `documentation/rules/messaging-layer-rules.md`, `documentation/rules/jobs-testing-rules.md`, `documentation/rules/provision-layer-rules.md`.
- **Risks/controls:** Duplicate events and missed notifications are controlled by persisted idempotency, stable event IDs, independent child jobs and the canonical disposable runtime fixture.
- **Exit:** `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run poe test:jobs` from `apps/server` passes with Mailpit/provider assertions, bounded fan-out and duplicate/redaction coverage.

### F6 — Implement BFF and public web experience

#### F6-T1 — Add handlers, contexts, routes and widgets

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** F4 server contracts; parallel with F5.
- **Paths:** `apps/web/src/routes/register`, `pending-confirmation`, `confirm-email`, `apps/web/src/rest/services/identity-service.ts`, Better Auth/cookie-session providers, auth context, Identity hooks/widgets/tests, root-layout paths, route tests and BFF handler integration tests listed in the Spec.
- **Traceability:** `RF-01`, `RF-08`, `RF-09`, `RF-11`; `CA-01`–`CA-04`, `CA-08`–`CA-13`; `RP-10`.
- **Outcome:** Thin public routes and accessible pt-BR pages expose only the opaque pending flow, preserve input/focus, classify confirmation outcomes and keep authenticated chrome out of public states.
- **Rules:** `documentation/rules/ui-layer-rules.md`, `documentation/rules/web-app-routing-rules.md`, `documentation/rules/widget-testing-rules.md`, `documentation/rules/typescript-conventions-rules.md`, `documentation/rules/validation-package-rules.md`.
- **Risks/controls:** Token/session disclosure and route drift are controlled by same-origin BFF operations, server-only providers, generated route metadata and exact REST schemas.
- **Exit:** `pnpm --filter web generate-routes`, `check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, and `build` pass from the repository root.

### F7 — Validate integrated runtime and visual contract

#### F7-T1 — Execute real service, browser and privacy validation

- **Status/owner:** `pending` — Builder Validation
- **Depends/parallel:** F4, F5 and F6 complete; no parallel implementation work.
- **Paths:** `apps/web/tests/routes/identity/*.test.tsx`, BFF handler integration suite, real-job fixtures, `documentation/features/identity/registration-confirmation/evaluation.md`, and transient Playwright evidence outside tracked source.
- **Traceability:** Every `CA-01`–`CA-13`, `VM-01`–`VM-08`, `CI-01`–`CI-18`.
- **Outcome:** Real PostgreSQL, Inngest, Mailpit, FastAPI and web behavior is validated for registration, delivery, failure/recovery, confirmation, resend, expiry/reuse, privacy and responsive accessibility.
- **Rules:** `documentation/rules/widget-testing-rules.md`, `documentation/rules/web-app-routing-rules.md`, `documentation/rules/jobs-testing-rules.md`, `documentation/tooling.md`.
- **Risks/controls:** Mocked transport is not accepted as server evidence; inspect final URLs, requests, console, HTTP responses, persistence, provider effects and fresh screenshots at each required viewport/state.
- **Exit:** Record current `EV-*` evidence for every criterion, all applicable CI gates and all visual/manual scenarios in `evaluation.md`; classify any unavailable service explicitly.

### F8 — Independent implementation review and handoff

#### F8-T1 — Reconcile the complete candidate

- **Status/owner:** `pending` — Orchestrator / Implementation Reviewer
- **Depends/parallel:** F1–F7 and the complete evidence baseline; no parallel work.
- **Paths:** Full integrated diff, generated routes/migration/lockfiles, REST artifact, evaluation, and all affected source/test paths.
- **Traceability:** Complete Spec contract and every `CA-*`/`VM-*`.
- **Outcome:** One read-only Implementation Reviewer checks cross-Builder contracts, generated artifacts, REST parity, evidence freshness, server/browser behavior and Rule Pack conformance.
- **Rules:** `documentation/sdd.md`, `documentation/rules.md`, every Rule Pack selected by the Spec.
- **Risks/controls:** Findings invalidate affected evidence and return to the responsible Builder; the same Reviewer is resumed after correction.
- **Exit:** All verified findings are resolved, Evaluation is ready for `conclude-spec`, and no unowned path or stale evidence remains.

# Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | E-mail package | `CA-05`, `CA-12` | `CI-01`–`CI-03`, `CI-18` | `evaluation.md` `EV-F3-*` | `pending` |
| Automated | Server core and REST | `CA-02`–`CA-04`, `CA-08`–`CA-12` | `CI-11`–`CI-16` | `evaluation.md` `EV-F4-*` | `pending` |
| Runtime | Inngest delivery, expiry and cancellation | `CA-05`–`CA-07`, `CA-10`–`CA-12` | `CI-17`, `VM-03`, `VM-04`, `VM-08` | `evaluation.md` `EV-F5-*` | `pending` |
| Automated | Web routes and widgets | `CA-01`–`CA-04`, `CA-08`–`CA-13` | `CI-04`–`CI-10` | `evaluation.md` `EV-F6-*` | `pending` |
| REST client | Identity route group | `CA-03`, `CA-04`, `CA-08`, `CA-09`, `CA-11` | `apps/server/rest-client/identity/identity.rest` | Route parity result + `EV-F4-*` | `pending` |
| Manual | Registration, delivery, confirmation, resend and expiry | `CA-01`–`CA-12` | `VM-01`–`VM-08` | `evaluation.md` `EV-VM-*` | `pending` |
| Visual | Desktop/mobile public registration flow | `CA-01`, `CA-08`, `CA-13` | `design/handoff.md`, `VM-01`, `VM-05`, `VM-06` | Fresh Playwright screenshots + `EV-V-*` | `pending` |

Final handoff requires every phase and task to be completed at Spec revision 11,
all applicable pnpm/uv commands to pass, generated artifacts and REST examples to
be reviewed, every `CA-*` and `VM-*` to have current accepted evidence, the single
Implementation Reviewer checkpoint to be resolved, and the Evaluation to be ready
for `conclude-spec`.
