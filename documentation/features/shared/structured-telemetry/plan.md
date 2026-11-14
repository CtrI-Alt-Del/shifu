---
title: structured telemetry implementation plan
status: ready
spec: ./spec.md
spec_revision: 5
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-94
last_updated_at: 2026-10-21
---

# 1. Execution status

- **Spec:** `documentation/features/shared/structured-telemetry/spec.md`, revision
  5, `ready`.
- **Why Plan-backed:** the delivery crosses Web/BFF and FastAPI application
  composition, shared REST plumbing, Identity/Learning business boundaries, 15
  async registrars/jobs, three external integrations, generated workflow files
  and local/staging validation. The three Builder scopes below are disjoint.
- **Plan status/phase:** `ready` / local implementation complete with external and
  composed-runtime validation gates explicitly pending.
- **Next action:** restore Docker-backed fixtures, run VM-01–VM-03 and CI-06,
  then run VM-04 when SHIFU-83/85 staging evidence exists; use `conclude-spec`
  for final SDD closure.
- **External dependency:** VM-04 and final conclusion require SHIFU-83/85 staging
  deployments, both CloudWatch groups, awslogs/IAM access, one non-sensitive
  synthetic operation and exact 14-day retention. This does not block local
  implementation or VM-01–03.
- **Builders:** `Builder Web Telemetry`, `Builder Server Foundation` and
  `Builder Server Async`; the Orchestrator owns SDD artifacts, root integration,
  CI workflow selections, generated outputs, package/lockfile state and final
  validation.
- **Preserved unrelated paths:** `iac/` and
  `documentation/reports/armazenamento-v1.docx` remain outside this delivery.

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Revision 5 is `ready`, with current authority metadata, compatibility review and synchronized companion | Orchestrator | `passed` | Preserve the exact revision through implementation kickoff |
| Jira authority | Complete reread of SHIFU-94, status `Fazendo`, updated `2026-10-20T15:07:02.289-0300`, retrieved `2026-10-21T20:26:54-03:00` | Orchestrator | `passed` | Reuse unless Jira version changes |
| Privacy authority | Complete reread of Confluence content `100106241`, version 4, retrieved `2026-10-21T20:26:54-03:00` | Orchestrator | `passed` | Reconcile if the page version changes |
| Rule/architecture compatibility | Independent revision-5 Spec review; selected packs include `widget-testing-rules.md` | Spec Reviewer / Orchestrator | `passed` | Reopen affected contract if a new blocking finding appears |
| Companion integrity | Edge Playwright interaction checks, narrow viewport and no page/console errors | Orchestrator | `passed` | Preserve ignored artifacts under `apps/web/.playwright-cli/` |
| Generated workflow artifacts | Canonical prompt sources synchronized to ignored skills/commands/agent outputs | Orchestrator | `passed with pnpm wrapper limitation` | Re-run the direct generators during implementation if prompt sources change |
| Local services/fixtures | Web/API test dependencies, disposable Inngest fixture, database/Redis and AgentOS test prerequisites | Orchestrator | `blocked: Docker named pipe` | Re-run composed checks when Docker Desktop access is restored |
| Staging evidence for VM-04 | SHIFU-83/85 deployments, CloudWatch groups, awslogs/IAM, synthetic operation and exact retention | Infrastructure/Delivery | `blocked: external gate` | Run VM-04 when the real dependencies are available |

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Builder Web Telemetry` | F1 | Typed Web provider, request context, configuration and propagation contracts are in place | Spec rev 5 | F2, F3 | `complete` | Web contract/type checks and focused provider/request tests pass |
| 1 | `Builder Server Foundation` | F2 | Typed API provider, `TelemetryPipe`, middleware, errors, lifecycle and business-owner contracts are in place | Spec rev 5 | F1, F3 | `complete` | API focused boundary tests prove app-state composition, safe errors and matrix ownership |
| 1 | `Builder Server Async` | F3 | Shared lifecycle wrapper, registrar contract and integration adapter boundaries are defined | Spec rev 5; F2 public provider contract | F1, F2 | `complete` | Registrar and adapter tests observe fixed lifecycle fields without payload data |
| 2 | `Builder Web Telemetry` | F4 | All listed server-function consumers and Better Auth request/session paths forward or emit safe telemetry | F1 | F5, F6 | `complete` | Web focused tests and changed-file coverage selection are integrated |
| 2 | `Builder Server Foundation` | F5 | Root-independent API middleware/controllers/lifecycle/business-event consumers are adapted | F2 | F4, F6 | `complete` | Isolated controller, error, lifecycle and business-event checks pass; composed checks await Docker |
| 2 | `Builder Server Async` | F6 | All 15 registrars/jobs plus Resend/OpenRouter/Jev consumers use explicit provider passing and safe lifecycle telemetry | F2, F3 | F4, F5 | `complete` | Static/isolated lifecycle proof passes; real-runtime selections await Docker |
| 3 | `Orchestrator` | F7 | Root API logging/Uvicorn composition, CI coverage selections and generated outputs are integrated | F4, F5, F6 | — | `complete` | Single-provider composition and workflow selections reviewed |
| 4 | `Orchestrator` | F8 | Focused Web/API/job/runtime checks and companion integrity are complete; composed VM-01–03 are blocked | F7 | — | `complete with limits` | Current local evidence and external limitations are recorded in `evaluation.md` |
| 5 | `Implementation Reviewer` | F9 | One integrated read-only review validates the complete candidate and evidence | F8 | — | `complete` | Reviewer report reconciled with no blocking finding |
| 6 | `Orchestrator` | F10 | VM-04 is performed when staging dependencies exist and conclusion is prepared | F9; VM-04 gate | — | `pending external gate` | Run VM-04 or preserve the exact external limitation, then use `conclude-spec` |

### F1 — Web telemetry and request propagation

#### F1-T1 — Establish Web contracts and configuration

- **Status/owner:** `complete` — Builder Web Telemetry
- **Depends/parallel:** Spec revision 5; parallel with F2 and F3.
- **Paths:** `apps/web/src/core/shared/interfaces/telemetry-provider.ts`,
  `apps/web/src/core/shared/interfaces/request-telemetry-context.ts`,
  `apps/web/src/provision/telemetry/console-telemetry-provider.ts`,
  `apps/web/src/constants/server-env.ts`, `apps/web/.env.example`.
- **Traceability:** RF-01, RF-04, RF-05, RF-06; CA-01, CA-04, CA-05.
- **Outcome:** Web provider and typed context enforce the fixed event,
  `TelemetryErrorCode`, level, environment and safe-field catalogs.
- **Rules:** `documentation/rules.md` routed TypeScript, core, provision and
  web-app-routing packs, including their antipattern sections.
- **Risks/controls:** Keep browser clients context-free and avoid global mutable
  state; use the existing server-function context boundary.
- **Exit:** Web type/lint/architecture checks and focused provider/request tests
  pass; no dependency or lockfile changes.

#### F1-T2 — Adapt BFF and server-function consumers

- **Status/owner:** `complete` — Builder Web Telemetry
- **Depends/parallel:** F1-T1; parallel with F5 and F6.
- **Paths:** `apps/web/src/start.ts`, `apps/web/src/rest/axios/axios-rest-client.ts`,
  `apps/web/src/rest/axios/server-request-client.ts`,
  `apps/web/src/rest/axios/utils/request.ts`, all production `createServerFn`
  consumers listed in Spec, `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`.
- **Traceability:** RF-02, RF-04, RF-07; CA-02, CA-04, CA-07; VM-01.
- **Outcome:** Request IDs propagate BFF→API, response IDs are observed, and
  Better Auth emits only the fixed session event without secrets or session data.
- **Rules:** TypeScript, core, provision, UI, web-app-routing and widget-testing
  packs; preserve existing Axios and auth behavior.
- **Risks/controls:** Do not instrument browser-only calls or log raw paths;
  exercise a registered API handler in the integration test.
- **Exit:** `apps/web/tests/shared/structured-telemetry-api.test.ts`, Axios tests,
  Web static checks and changed-file coverage are current.

### F2 — Server Foundation

#### F2-T1 — Establish provider, pipe and application-boundary contracts

- **Status/owner:** `complete` — Builder Server Foundation
- **Depends/parallel:** Spec revision 5; parallel with F1 and F3.
- **Paths:** `apps/server/src/shifu/shared/core/interfaces/telemetry_provider.py`,
  `apps/server/src/shifu/shared/providers/console_telemetry_provider/`,
  `apps/server/src/shifu/shared/rest/pipes/telemetry_pipe.py`,
  `apps/server/src/shifu/shared/constants/environment.py`,
  `apps/server/.env.example`.
- **Traceability:** RF-01, RF-04, RF-05, RF-06; CA-01, CA-04, CA-05.
- **Outcome:** One typed provider contract, bounded error catalog and one
  `TelemetryPipe` dependency are available for explicit composition.
- **Rules:** Python, core, provision/provider, server-app and REST packs; no
  provider-only test file and no raw framework logger bypass.
- **Risks/controls:** Keep provider independent of FastAPI and ensure failed
  serialization cannot alter business outcomes.
- **Exit:** Python lint/architecture/types and focused provider-consuming tests
  pass at the application boundaries.

#### F2-T2 — Adapt middleware, error and business-event consumers

- **Status/owner:** `complete` — Builder Server Foundation
- **Depends/parallel:** F2-T1; parallel with F4 and F6.
- **Paths:** `apps/server/src/shifu/shared/rest/middlewares/telemetry_middleware.py`,
  `apps/server/src/shifu/rest/handlers/app_error_handler.py`, the Identity and
  Learning business-owner controllers listed in Spec, and their module-first
  tests including `test_business_event_telemetry.py`.
- **Traceability:** RF-02, RF-04, RF-05, RF-07; CA-02, CA-04, CA-05, CA-07;
  CI-01, CI-03, CI-05, CI-08; VM-01–03.
- **Outcome:** Request/error telemetry is safe and each matrix row is emitted
  once after the owning outcome; retry dispatch is not an evaluation completion.
- **Rules:** REST, controllers-testing, core and server-app packs; preserve
  module ownership and existing response codes.
- **Risks/controls:** Reuse existing safe API error codes, map unexpected errors
  to `internal_error`, and never transform exception text into a code.
- **Exit:** Composed controller/error/middleware tests cover every matrix row,
  forbidden fields and telemetry-failure resilience.

### F3 — Server Async

#### F3-T1 — Establish lifecycle and registrar contracts

- **Status/owner:** `complete` — Builder Server Async
- **Depends/parallel:** F2-T1 provider contract; parallel with F1-T1 and F2-T2.
- **Paths:** `apps/server/src/shifu/shared/messaging/inngest/job_lifecycle_telemetry.py`
  and every module `*_inngest_messaging.py` registrar.
- **Traceability:** RF-03, RF-04, RF-07; CA-03, CA-04; CI-04, VM-02.
- **Outcome:** All 15 registered jobs have stable IDs and shared start,
  completion, retry and failure lifecycle behavior with explicit provider input.
- **Rules:** Messaging and jobs-testing packs; no event payload content used as
  a job identifier.
- **Risks/controls:** Keep retry lifecycle separate from business completion;
  use the SDK run/event identifiers only when exposed by the SDK.
- **Exit:** Registry proof and representative module-first job tests observe all
  lifecycle states with safe fields.

#### F3-T2 — Adapt jobs and external integrations

- **Status/owner:** `complete` — Builder Server Async
- **Depends/parallel:** F3-T1 and F2-T1; parallel with F4 and F5.
- **Paths:** all 15 registered job handlers, Resend delivery/confirmation
  consumers, OpenRouter providers, the Jev mentor-review consumer and the
  composed Learning/AgentOS evaluation workflow.
- **Traceability:** RF-03, RF-04, RF-07; CA-03, CA-04, CA-07; CI-04, CI-08;
  VM-02.
- **Outcome:** Integrations use `inngest.dispatch`, `resend.send` or
  `openrouter.generate`; evaluation completion belongs only to the completed
  evaluation job.
- **Rules:** Messaging, jobs-testing, AI and controllers-testing packs; use the
  composed Mentor controller boundary with `SHIFU_RUN_REAL_AGENTOS_TESTS=1`.
- **Risks/controls:** Do not modify the legacy dedicated Mentor workflow test;
  replace its CI/coverage target with the composed controller/registered runtime
  boundary, and do not emit account/content/provider payloads or false completion events.
- **Exit:** Inngest fixture and existing integration consumers pass success,
  retry and failure assertions; the legacy dedicated workflow test is not a
  changed-file coverage target.

### F4 — Web consumer adaptation

#### F4-T1 — Prove Web propagation and session telemetry

- **Status/owner:** `complete` — Builder Web Telemetry
- **Depends/parallel:** F1-T1 and F2-T1; parallel with F5-T1 and F6-T1.
- **Paths:** Web server-function consumers, Better Auth provider and Web tests;
  the Orchestrator owns the root workflow selection.
- **Traceability:** RF-02, RF-04, RF-07; CA-02, CA-04, CA-07; CI-03, CI-08; VM-01.
- **Outcome:** Registered Web/BFF requests forward the typed ID and session
  invalidation produces the fixed event without credentials or content.
- **Rules:** TypeScript, UI, web-app-routing and widget-testing packs.
- **Risks/controls:** Keep browser-only requests unchanged; assert through a
  registered API handler rather than a mocked transport.
- **Exit:** Focused Vitest/Playwright checks, lint/architecture/types and changed
  file coverage pass with no empty selection.

### F5 — Server Foundation consumer adaptation

#### F5-T1 — Prove API boundaries and business matrix

- **Status/owner:** `complete` — Builder Server Foundation
- **Depends/parallel:** F2-T1; parallel with F4-T1 and F6-T1.
- **Paths:** API middleware/error/lifecycle consumers, Identity/Learning
  controllers, `test_business_event_telemetry.py` and related module-first tests.
- **Traceability:** RF-02, RF-04, RF-05, RF-07; CA-02, CA-04, CA-05, CA-07;
  CI-01, CI-03, CI-05, CI-07, CI-08; VM-01–03.
- **Outcome:** Composed API boundaries emit safe request/error/lifecycle and
  Auth/Learning events after the owning outcome.
- **Rules:** Python, REST, controllers-testing, server-app and core packs.
- **Risks/controls:** Preserve response semantics and existing safe error codes;
  inject the one provider instance rather than constructing providers per request.
- **Exit:** Focused pytest selections and changed-file coverage meet repository
  thresholds; no provider-only test is introduced.

### F6 — Server Async consumer adaptation

#### F6-T1 — Prove all async and integration consumers

- **Status/owner:** `complete` — Builder Server Async
- **Depends/parallel:** F3-T1 and F2-T1; parallel with F4-T1 and F5-T1.
- **Paths:** 15 job handlers/registrars, Resend/OpenRouter/Jev consumers and
  their existing representative tests.
- **Traceability:** RF-03, RF-04, RF-07; CA-03, CA-04, CA-07; CI-04, CI-08; VM-02.
- **Outcome:** Every async consumer receives the provider explicitly and emits
  only generic lifecycle or owning integration/business events.
- **Rules:** Messaging, jobs-testing, AI and controllers-testing packs.
- **Risks/controls:** Keep retry dispatch distinct from completion and set
  `SHIFU_RUN_REAL_INNGEST_TESTS=1`/`SHIFU_RUN_REAL_AGENTOS_TESTS=1` where required.
- **Exit:** Inngest fixture and integration consumer checks pass success,
  retry/failure and privacy assertions; no legacy dedicated Mentor target is
  selected.

### F7 — Orchestrator integration

The Orchestrator owns `apps/server/src/shifu/app.py` and `apps/server/src/main.py`
composition, the root API/Uvicorn handler installation, `.github/workflows/web-app-ci.yaml`
and `.github/workflows/server-app-ci.yaml` changed-file selections, generated
ignored outputs, package/lockfile state and cross-Builder integration. No Builder
may edit these shared paths or any SDD artifact. The Orchestrator also preserves
the unrelated `iac/` and `documentation/reports/` paths.

#### F7-T1 — Integrate root composition and coverage workflows

- **Status/owner:** `complete` — Orchestrator
- **Depends/parallel:** F4-T1, F5-T1 and F6-T1; no parallel shared-path edits.
- **Paths:** `apps/server/src/shifu/app.py`, `apps/server/src/main.py`,
  `.github/workflows/web-app-ci.yaml`, `.github/workflows/server-app-ci.yaml`,
  generated ignored outputs and any root configuration needed for composition.
- **Traceability:** RF-01, RF-03, RF-06; CA-01, CA-03, CA-06, CA-07; CI-02, CI-06, CI-07.
- **Outcome:** Application composition creates one provider, installs root/Uvicorn
  formatting and selects every changed production file for coverage; the legacy
  dedicated Mentor workflow target is replaced by the composed boundary.
- **Rules:** Architecture, server-app, CI/tooling and AI packs; no dependency,
  lockfile, migration, IAC, route or REST-collection changes.
- **Risks/controls:** Review the integrated diff for cross-Builder overlap and
  keep all generated artifacts derived from canonical prompt sources.
- **Exit:** Root runtime tests, Web/API changed-file coverage workflow checks and
  `git diff --check` pass.

### F8 — Local integrated validation

#### F8-T1 — Run focused checks and VM-01–03

- **Status/owner:** `complete with limits` — Orchestrator
- **Depends/parallel:** F7-T1.
- **Paths:** No new production ownership; evidence in `evaluation.md` and ignored
  `.playwright-cli` directories only.
- **Traceability:** All applicable CA-01–CA-07; CI-01–CI-08; VM-01–VM-03.
- **Outcome:** Focused Web/API/job/runtime checks and configured changed-file
  coverage pass without lowering thresholds.
- **Rules:** `documentation/tooling.md`, selected Rule Packs and Playwright CLI
  rules from `AGENTS.md`.
- **Risks/controls:** Start only required services, preserve shared Docker state,
  and record unavailable staging proof as pending rather than as a pass.
- **Exit:** Current command output and VM observations are recorded in Evaluation.

### F9 — Integrated implementation review

#### F9-T1 — Review the integrated candidate once

- **Status/owner:** `complete` — Implementation Reviewer (read-only)
- **Depends/parallel:** F8-T1; no parallel review streams.
- **Paths:** Complete integrated diff, generated outputs, workflow selections and
  all affected Web/API/job/runtime surfaces.
- **Traceability:** All affected RF/CA/checkers; reviewer evidence as `ACH-*`.
- **Outcome:** One coherent cross-Builder review identifies no unresolved
  blocking contract, architecture, privacy or coverage finding.
- **Rules:** `documentation/agents/implementation-reviewer-agent.md`.
- **Risks/controls:** Resume the responsible Builder and rerun only affected
  checks when a finding invalidates evidence; do not replace the Reviewer.
- **Exit:** Reviewer report is reconciled in Evaluation and all blocking findings
  are resolved.

### F10 — Staging gate and conclusion

#### F10-T1 — Complete VM-04 and conclude

- **Status/owner:** `pending external gate` — Orchestrator
- **Depends/parallel:** F9-T1 and the staging dependency gate.
- **Paths:** Evaluation, this Plan, staging observation artifacts and no deployed
  infrastructure files.
- **Traceability:** CA-06; VM-04; `conclude-spec` completion contract.
- **Outcome:** VM-04 is run only when SHIFU-83/85 and CloudWatch/IAM/awslogs
  dependencies are available; otherwise the exact external limitation is kept.
- **Rules:** SDD conclusion workflow, privacy policy and staging safety rules.
- **Risks/controls:** Never emit deployed events or mutate Jira/Confluence/IAC as
  a side effect; preserve exact 14-day retention evidence.
- **Exit:** `conclude-spec` verifies Evaluation, marks this Plan `completed` only
  after all required evidence or justified external disposition is current.

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Web provider, Axios and BFF/API propagation | CA-01, CA-02, CA-04, CA-05 | Spec CI-01, CI-03, CI-05 | `evaluation.md` `EV-01` | `passed with runtime limits` |
| Automated | API provider, middleware, error and lifecycle boundaries | CA-01, CA-04, CA-05, CA-06 | Spec CI-01, CI-05, CI-07 | `evaluation.md` `EV-02` | `passed with runtime limits` |
| Automated | Auth/Learning business-event matrix and completed evaluation job | CA-07 | Spec CI-08 | `evaluation.md` `EV-03` | `passed at isolated boundaries` |
| Automated | 15-job registry, representative Inngest jobs and integrations | CA-03, CA-04 | Spec CI-04 | `evaluation.md` `EV-04` | `passed with Docker/runtime limits` |
| Automated | Web/API changed-file coverage selections | CA-01, CA-03, CA-04, CA-07 | Spec Architecture Mapping and CI workflow files | `evaluation.md` `EV-05` | `reviewed` |
| Runtime | Root API/Uvicorn and composed Web/API boundary | CA-01, CA-02, CA-06 | Spec Technical Contract | `evaluation.md` `EV-06` | `passed locally; composed boundary pending` |
| Manual | VM-01 — Web/BFF to API correlation | CA-02 | Spec VM-01 | `evaluation.md` `VM-01` | `blocked: local services` |
| Manual | VM-02 — business, job and provider correlation | CA-03, CA-07 | Spec VM-02 | `evaluation.md` `VM-02` | `blocked: Docker fixtures` |
| Manual | VM-03 — safe unexpected-error handling | CA-04, CA-05 | Spec VM-03 | `evaluation.md` `VM-03` | `blocked: composed runtime` |
| Manual | VM-04 — staging CloudWatch validation | CA-06 | Spec VM-04 | `evaluation.md` `VM-04` | `blocked: external gate` |
| Review | One integrated Implementation Reviewer | All affected criteria and paths | `documentation/agents/implementation-reviewer-agent.md` | `evaluation.md` `ACH-*` | `complete; no blocking finding` |

The implementation checkpoint is one integrated read-only Reviewer after F8 and
before VM-04/conclusion. The Orchestrator resumes the responsible Builder for any
verified finding, invalidates affected evidence and reuses the same Reviewer
after correction. `conclude-spec` completes this Plan only after all local proof,
the Reviewer and any applicable staging disposition are current.

# 5. Execution log

- **2026-10-21 — Workflow and artifact synchronization preflight**
  - **Finding/result:** `pnpm sync:agents` and `pnpm sync:commands` were attempted;
    the pnpm wrapper stopped during its automatic workspace install because of
    sandbox symlink/ignored `esbuild` build-script restrictions. The canonical
    generators `node scripts/sync-agents.mjs` and `node scripts/sync-commands.mjs`
    completed successfully and their ignored outputs were inspected.
  - **Next action:** Re-run the generators if prompt sources change during
    implementation; do not edit generated outputs directly.

- **2026-10-21 — Implementation and local evidence**
  - **Finding/result:** F1–F9 were implemented and reconciled. Web/API
    telemetry providers, request propagation, API error/lifecycle/business
    boundaries, all 15 Inngest registrars/jobs, Resend/OpenRouter/Jev adapters,
    root composition, CI selections and telemetry documentation are present.
    Focused API checks, direct Web type/Vitest/architecture checks, app import,
    and the companion integrity gate passed. The implementation reviewer found
    no blocking finding.
  - **Limitation:** Docker-backed composed checks are blocked by local Docker
    Desktop named-pipe access; VM-04 remains dependent on SHIFU-83/85 staging,
    CloudWatch, awslogs/IAM and exact 14-day retention. The Plan is ready for
    `conclude-spec` after those external gates are resolved or formally
    dispositioned.
- **2026-10-21 — Final review corrections**
  - **Finding/result:** The AgentOS evaluation path and Inngest choice path were
    corrected to emit `learning.evaluation.completed` only after a committed
    evaluation. The focused AgentOS regression passed. The final reviewer also
    identified three duplicate server CI selections; the lower duplicates were
    removed and each affected path now occurs once. The recheck found no
    unresolved implementation or evidence finding.
  - **Disposition:** F9 is complete. F10 remains pending the external VM-04
    gate and the unavailable composed-runtime observations; no completion or
    staging pass is inferred from local evidence.
