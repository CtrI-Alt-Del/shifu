---
title: Identity password recovery and reset implementation plan
status: completed
spec: ./spec.md
spec_revision: 4
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-63
last_updated_at: 2026-09-25
---

> Historical execution record. This archived Plan is read-only history, not active delivery authority. Resume work from [Spec](../spec.md) and [Evaluation](../evaluation.md); its phase/status requirements do not gate implementation or closure.


# Execution status

| Item | State |
| --- | --- |
| Governing contract | [`spec.md`](.././spec.md), revision `4`, status `ready` |
| Plan status / phase | `completed` / revision-4 validation amendment reconciled and ready for publication |
| Why a Plan | Cross-module Identity/Communication contract migration, PostgreSQL forward migration, generated e-mail artifacts, Better Auth BFF work, Inngest integration, and real browser/runtime validation require coordinated ownership. |
| Next action | Complete the revision-4 Spec review, reconcile evidence without visual comparisons, and run the remaining applicable gates. |
| Active blockers | None. Local Docker, Mailpit, Inngest, FastAPI, web, and disposable Testcontainers availability remain validation gates. |
| Active Builders | `identity-password-recovery-server-builder`, `identity-password-recovery-web-builder`, and `identity-password-recovery-email-builder` own the non-overlapping F1, F2, and F3 paths. |
| Shared ownership | The Orchestrator owns this Plan and Evaluation, generated `apps/web/src/routeTree.gen.ts`, generated server e-mail assets, migration coordination, any lockfile change, cross-Builder integration, and final validation. |

The pre-existing modification to `documentation/features/identity/registration-confirmation/spec.md` and the untracked password-recovery feature directory are preserved. Reconcile confirmation compatibility against its current revision before integrated validation; do not overwrite unrelated work.

# Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | `spec.md` remains `ready` at revision `2`; Confluence Identity `83001345` and Communication `86114306` remain version `1` | Orchestrator | `pending` | Recheck source versions and Spec revision at implementation kickoff. |
| Confirmation compatibility | Current `registration-confirmation/spec.md` amendment remains compatible with the neutral `identity_action_token_id` contract | Builder Server | `pending` | Reconcile its existing confirmation flows during F1 and retain regression coverage. |
| E-mail generation | `packages/email` build can generate the recovery HTML and manifest consumed by Communication | Builder Email | `pending` | Complete F3 before F4 uses the generated catalog. |
| Local runtime | PostgreSQL, Mailpit, and Inngest services from `docker-compose.yaml`; healthy FastAPI and web applications | Orchestrator | `pending` | Verify services and health endpoints before VM-01 through VM-06. |
| Disposable integration runtime | Docker-capable environment for PostgreSQL and Inngest Testcontainers | Orchestrator | `pending` | Run `uv run poe test:integration` and `uv run poe test:jobs`; record any unavailable runtime as a limitation, not passing evidence. |

# Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Server` | F1 | Neutral action-token correlation, recovery Identity API, persistence, and server tests are implemented without breaking confirmation. | — | F2, F3 | `in_progress` | Revision-3 reset-link status controller/use case and focused unit/controller integration tests pass. |
| 1 | `Builder Web` | F2 | Public BFF, routes, widgets, and local browser/unit coverage implement the specified recovery experience against the fixed wire contract. | — | F1, F3 | `in_progress` | Revision-3 BFF/widget resolution, expiry-aware polling, automatic success navigation, and handler failure coverage pass. |
| 1 | `Builder Email` | F3 | Controlled recovery e-mail source and multi-template generator are ready. | — | F1, F2 | `completed` | E-mail code/type/build checks pass; generated artifacts are available for F6 review. |
| 2 | `Builder Server` | F4 | Composition, renderer catalog, expiry-aware delivery, cancellation/status jobs, and real server boundaries integrate F1 and F3. | F1, F3 | F5 | `pending` | Communication/controller/job exits pass, including generated-template catalog and registration-confirmation regression. |
| 2 | `Builder Web` | F5 | The BFF handler is verified against the completed Identity boundary, including opaque context and session cleanup behavior. | F1, F2 | F4 | `pending` | Handler integration and focused browser exits pass against required local services. |
| 3 | Orchestrator | F6 | Generated outputs, migration preservation, REST-client parity, complete candidate validation, and Evaluation baseline are reconciled. | F4, F5 | — | `pending` | All applicable CI and VM evidence is current in `evaluation.md`; every CA is mapped to accepted evidence. |
| 4 | `Implementation Reviewer` | F7 | One independent read-only review covers the integrated candidate and evidence. | F6 | — | `pending` | Reviewer report is recorded; verified findings are resolved and affected evidence is rerun. |

### F1 — Server contract and recovery API

#### F1-T1 — Neutral action-token contract and Identity recovery operations

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** No dependency; parallel with F2 and F3. F4 cannot begin until this task completes.
- **Paths:** `apps/server/src/shifu/identity/**`; `apps/server/src/shifu/communication/core/domain/**`; `apps/server/src/shifu/communication/database/**`; `apps/server/src/shifu/communication/messaging/**`; `apps/server/migrations/versions/<new>_generalize_identity_action_token_delivery.py`; `apps/server/rest-client/identity/identity.rest`; `apps/server/tests/identity/**`; `apps/server/tests/communication/**`; `apps/server/tests/messaging/inngest/jobs/{identity,communication}/**`.
- **Traceability:** Identity `RP-04`, `RP-10`, `JN-04`; Communication `RP-01` to `RP-07`, `JN-02` to `JN-05`; `RF-02` to `RF-07`; `CA-02` to `CA-09`.
- **Outcome:** Identity issues, queries, retries, and consumes recovery tokens through safe opaque handles; the generic correlation, status, cancellation, expiry, and persistence contracts preserve confirmation behavior; all four Identity recovery routes and non-secret REST-client examples exist.
- **Rules:** `documentation/rules/python-conventions-rules.md`; `core-layer-rules.md`; `use-case-testing-rules.md`; `rest-layer-rules.md`; `controllers-testing-rules.md`; `database-layer-rules.md`; `messaging-layer-rules.md`; `jobs-testing-rules.md`. Apply each relevant `Antipatterns to Avoid` subsection and preserve module boundaries.
- **Risks/controls:** The forward migration and broad confirmation rename can lose deployed correlation or break SHIFU-61. Preserve `d7f4e9a1c2b3`, update every producer/consumer atomically, and prove an upgrade with an inserted confirmation row in VM-07.
- **Exit:** Run focused use-case and controller suites, then `uv run poe test:unit`, `uv run poe test:integration`, `uv run poe check:lint`, `uv run poe check:architecture`, and `uv run poe check:types` from `apps/server`. Review one labeled non-secret request for each of `POST /identity/password-recovery-requests`, `/identity/password-recoveries/status`, `/identity/password-recoveries/retry`, and `/identity/password-resets` in `identity.rest`; record that REST examples do not replace real HTTP evidence.

### F2 — Web recovery experience

#### F2-T1 — BFF, routes, and accessible public recovery pages

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** Uses the fixed Spec wire contract; parallel with F1 and F3. F5 awaits F1 completion.
- **Paths:** `apps/web/src/constants/routes.ts`; `apps/web/src/rest/services/identity-service.ts`; `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`; `apps/web/src/routes/forgot-password/index.tsx`; `apps/web/src/routes/reset-password/index.tsx`; `apps/web/src/ui/identity/hooks/use-request-password-recovery-action.ts`; `apps/web/src/ui/identity/hooks/use-password-recovery-status-query.ts`; `apps/web/src/ui/identity/hooks/use-reset-password-action.ts`; `apps/web/src/ui/identity/widgets/pages/forgot-password-page/**`; `apps/web/src/ui/identity/widgets/pages/reset-password-page/**`; `apps/web/tests/routes/identity/forgot-password.index.test.tsx`; `apps/web/tests/routes/identity/reset-password.index.test.tsx`; `apps/web/tests/identity/password-recovery-auth-handler.test.ts`.
- **Traceability:** Identity `RP-04`, `RP-10`, `JN-04`; `RF-01`, `RF-03`, `RF-05` to `RF-08`; `CA-01` to `CA-04`, `CA-07` to `CA-09`.
- **Outcome:** Public request and reset routes honor the opaque BFF context, URL cleanup, generic disclosure, access invalidation handling, and the specified pt-BR accessible states.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`; `ui-layer-rules.md` including `Antipatterns to Avoid`; `web-app-routing-rules.md`; `widget-testing-rules.md`; `rest-layer-rules.md`; `provision-layer-rules.md`; `documentation/design.md`.
- **Risks/controls:** Browser-visible values or a route/widget shortcut could expose account/token data or bypass BFF ownership. Keep route files thin, validate search in the route, use only same-origin BFF operations, and test malformed, unavailable, pending, error, and recovery states through the owning boundaries.
- **Exit:** Run focused Vitest and mocked Playwright route suites with the shared fixture, then `pnpm --filter web check:lint`, `pnpm --filter web check:architecture`, `pnpm --filter web check:types`, and `pnpm --filter web test:unit`. Verify keyboard, focus, accessible names and narrow viewport behavior through the declared suites; the user waived screenshot capture and visual comparison for this delivery. Defer `routeTree.gen.ts` generation to F6.

### F3 — Controlled recovery e-mail source

#### F3-T1 — Recovery template and multi-template generation

- **Status/owner:** `pending` — Builder Email
- **Depends/parallel:** No dependency; parallel with F1 and F2. F4 awaits this task.
- **Paths:** `packages/email/templates/identity/password-recovery-email.tsx`; `packages/email/templates/index.ts`; `packages/email/scripts/build-templates.ts`.
- **Traceability:** Communication `RP-01`, `RP-02`, `RP-07`, `JN-02`; `RF-04`; `CA-05`, `CA-06`.
- **Outcome:** The package exposes deterministic pt-BR recovery content with only `actionUrl` and `expiresAt`, while the generator produces both controlled template artifacts.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`; `email-package-rules.md`.
- **Risks/controls:** A template change can weaken the controlled catalog or leak unsupported values. Keep the public props explicit, use `EmailLayout`, reject manifest drift, and leave generated server files to the Orchestrator.
- **Exit:** Run `pnpm --dir packages/email check:code`, `pnpm --dir packages/email check:types`, and `pnpm --dir packages/email build`. Report generated `password-recovery.html` and `.manifest.json` for F6 review; do not hand-edit them.

### F4 — Server delivery and composition integration

#### F4-T1 — Recovery workflow, generated renderer, and durable delivery behavior

- **Status/owner:** `pending` — Builder Server
- **Depends/parallel:** F1 and F3; parallel with F5.
- **Paths:** `apps/server/src/shifu/composition/registration_confirmation_workflow.py`; `apps/server/src/shifu/composition/password_recovery_workflow.py`; `apps/server/src/shifu/composition/__init__.py`; `apps/server/src/shifu/communication/providers/email/template/generated_email_message_renderer.py`; `apps/server/src/shifu/app.py`; the F1-owned Communication delivery/cancellation/status job paths and focused test paths when correction is required.
- **Traceability:** Communication `RP-01` to `RP-07`, `JN-02` to `JN-05`; Identity `RP-04`, `JN-04`; `RF-02` to `RF-04`, `RF-06`; `CA-03` to `CA-06`, `CA-08`.
- **Outcome:** Composition binds both delivery gateways without module-core imports; the renderer selects validated generated artifacts; delivery/retry/cancellation publishes ID-only states and stops expired recovery links.
- **Rules:** `documentation/rules/python-conventions-rules.md`; `server-app-layer-rules.md`; `core-layer-rules.md`; `database-layer-rules.md`; `messaging-layer-rules.md`; `jobs-testing-rules.md`; `provision-layer-rules.md`.
- **Risks/controls:** Queue/delivery and session-cleanup partial failures must not restore unsafe access or roll back committed Identity state. Keep queue reconciliation and operational reporting non-secret, then prove persisted effects through controller and real-job tests.
- **Exit:** Regenerate package artifacts only through the e-mail build, run focused Communication and Inngest job tests, then `uv run poe test:jobs`, `uv run poe check:architecture`, and `uv run poe check:types` from `apps/server`. Verify the registered application exposes one Inngest endpoint and confirmation delivery remains operational.

### F5 — BFF-to-server integration

#### F5-T1 — Opaque context and all-session reset verification

- **Status/owner:** `pending` — Builder Web
- **Depends/parallel:** F1 and F2; parallel with F4.
- **Paths:** `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`; `apps/web/tests/identity/password-recovery-auth-handler.test.ts`; F2-owned web paths only when an in-Contract integration correction is required.
- **Traceability:** Identity `RP-03`, `RP-04`, `JN-04`; `RF-02`, `RF-03`, `RF-06`, `RF-07`; `CA-02`, `CA-04`, `CA-08`, `CA-09`.
- **Outcome:** Registered Better Auth HTTP handlers retain opaque real/decoy context only server-side, delete account sessions by trusted ID after a committed reset, clear the current cookie, and expose only approved generic browser results.
- **Rules:** `documentation/rules/typescript-conventions-rules.md`; `ui-layer-rules.md`; `widget-testing-rules.md`; `rest-layer-rules.md`; `provision-layer-rules.md`; `web-app-routing-rules.md`.
- **Risks/controls:** Mocked route coverage cannot prove cookie/session persistence or FastAPI authorization. Use the canonical handler integration fixture and local FastAPI/PostgreSQL; assert HTTP, cookie, persistence, old-session rejection, and safe cleanup-failure observation.
- **Exit:** Run the focused handler integration suite with services available, inspect final URLs, responses, cookies, and persisted session effects, then rerun the affected web checks. Record an explicit limitation if the real runtime cannot be started.

### F6 — Integrated validation and evidence

#### F6-T1 — Generated artifacts, migration, parity, and acceptance baseline

- **Status/owner:** `pending` — Orchestrator
- **Depends/parallel:** F4 and F5; no parallel Builder work.
- **Paths:** `apps/web/src/routeTree.gen.ts` (generated); `apps/server/src/shifu/communication/providers/email/template/generated/password-recovery.html`; `apps/server/src/shifu/communication/providers/email/template/generated/password-recovery.manifest.json`; `documentation/features/identity/password-recovery/evaluation.md`.
- **Traceability:** All selected `RP-*`/`JN-*`; `RF-01` to `RF-08`; `CA-01` to `CA-09`; `VM-01` to `VM-07`; `CI-01` to `CI-17`.
- **Outcome:** Generated files are current and reviewed, migration preservation and REST-client parity are demonstrated, and Evaluation contains current evidence rather than assumptions.
- **Rules:** `documentation/sdd.md`; `documentation/tooling.md`; all Rules listed in the governing Spec section 5 for the changed paths.
- **Risks/controls:** Generated files and migration state can become stale after integration. Generate only with declared commands and rerun affected exits after any correction. The user waived screenshot capture and visual comparison for this delivery.
- **Exit:** Run CI-01 through CI-17 as applicable, execute VM-01 through VM-07, inspect the full diff against the Spec affected-path map, and record each accepted evidence item in `evaluation.md`.

### F7 — Integrated implementation review

#### F7-T1 — Independent cross-boundary review

- **Status/owner:** `pending` — Implementation Reviewer
- **Depends/parallel:** F6; no parallel work.
- **Paths:** Read-only review of the complete integrated candidate, generated artifacts, REST client, and `documentation/features/identity/password-recovery/evaluation.md`.
- **Traceability:** All `CA-*`, `VM-*`, `CI-*`, cross-module boundaries, and F1 through F6 exits.
- **Outcome:** One advisory report checks the full candidate, not isolated Builder diffs, including confirmation compatibility, artifact freshness, REST parity, persistence, BFF/session behavior, and functional responsive/accessibility evidence.
- **Rules:** `documentation/agents/implementation-reviewer-agent.md`; governing Rule Pack references in `spec.md`.
- **Risks/controls:** A Builder report is not acceptance evidence. The Orchestrator verifies each finding, records verified items as `ACH-*` in `evaluation.md`, resumes the responsible Builder when necessary, invalidates stale evidence, and resumes this same Reviewer after correction.
- **Exit:** Reviewer report is complete and every verified finding has a resolved or explicitly accepted Evaluation disposition.

# Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Identity recovery use cases and Communication delivery use case | CA-02 to CA-09 | Spec Validation Contract | `evaluation.md` `EV-01` | `pending` |
| Automated | Identity PostgreSQL recovery controllers | CA-02 to CA-09 | Spec Validation Contract | `evaluation.md` `EV-02` | `pending` |
| Automated | Real Inngest delivery, cancellation, and status jobs | CA-03 to CA-06 | Spec Validation Contract | `evaluation.md` `EV-03` | `pending` |
| Automated | E-mail package checks and generated-template build | CA-05, CA-06 | CI-08 to CI-10 | `evaluation.md` `EV-04` | `pending` |
| Automated | Recovery page widget suites | CA-01 to CA-04, CA-07 to CA-09 | Spec Validation Contract | `evaluation.md` `EV-05` | `pending` |
| Automated | Mocked browser route suites, one per recovery route | CA-01 to CA-09 | `apps/web/tests/routes/identity/*.test.tsx` | `evaluation.md` `EV-06` | `pending` |
| Runtime | Registered BFF handler with FastAPI/PostgreSQL and Better Auth sessions | CA-02, CA-04, CA-08 | Spec Technical Contract | `evaluation.md` `EV-07` | `pending` |
| REST client | Identity recovery route group | CA-02 to CA-09 | `apps/server/rest-client/identity/identity.rest` | parity result + `EV-08` | `pending` |
| Manual | VM-01 request form and accessibility | CA-01 | Spec `VM-01` | `evaluation.md` `EV-09` | `pending` |
| Manual | VM-02 privacy, cooldown, and replacement persistence | CA-02, CA-03 | Spec `VM-02` | `evaluation.md` `EV-10` | `pending` |
| Manual | VM-03 terminal delivery recovery | CA-04 | Spec `VM-03` | `evaluation.md` `EV-11` | `pending` |
| Manual | VM-04 Mailpit, retry, idempotency, and event privacy | CA-05, CA-06 | Spec `VM-04` | `evaluation.md` `EV-12` | `pending` |
| Manual | VM-05 reset-link outcomes and URL cleanup | CA-07 | Spec `VM-05` | `evaluation.md` `EV-13` | `pending` |
| Manual | VM-06 reset, session invalidation, and pending-account preservation | CA-08, CA-09 | Spec `VM-06` | `evaluation.md` `EV-14` | `pending` |
| Manual | VM-07 disposable forward-migration preservation | CA-03, CA-05, CA-06 | Spec `VM-07` | `evaluation.md` `EV-15` | `pending` |

The Orchestrator must run the applicable declared commands: `pnpm --filter web generate-routes`, `check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, and `build`; `pnpm --dir packages/email check:code`, `check:types`, and `build`; then, from `apps/server`, `uv run poe check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration`, `test:jobs`, and `build`.

Final handoff requires every task and phase completed; the exact Spec revision and integrated diff reconciled; applicable commands passed without lowering configured floors; generated routes, migration, e-mail artifacts, and REST-client examples reviewed; every `CA-*` and `VM-*` backed by current accepted evidence; all affected REST-client routes complete; the Implementation Reviewer completed with verified findings resolved; runtime limitations explicitly recorded; and `evaluation.md` ready for `conclude-spec`.
