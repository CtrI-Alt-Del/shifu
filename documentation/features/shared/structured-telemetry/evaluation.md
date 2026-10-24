---
title: Structured JSON telemetry for Web/BFF and API evaluation
status: in_progress
spec: ./spec.md
last_updated_at: 2026-10-24
---

# Current State

| Field | State |
| --- | --- |
| Implementation | Review revision applied for CA-01–CA-07; no product behavior, persistence, route collection, IAC or dependency changes |
| Automated checks | Integrated Web type, architecture, focused test and full coverage gates passed; API type/lint gates passed; Docker-backed API tests remain environment-limited |
| Type / lint / complexity | API Ruff, format, compileall, targeted basedpyright and architecture passed; Web direct TypeScript, Vitest and dependency-cruiser passed; Web Biome/pnpm wrapper and full API basedpyright were environment-limited |
| Manual checks | Browser companion integrity passed; feature VM-01–VM-03 require healthy composed services and are not claimed from static checks; VM-04 is externally blocked |
| Visual checks | Not applicable by Spec; the browser companion was exercised only as documentation-integrity validation |
| Independent review | PR review feedback is implemented; redundant Web telemetry tests were removed and the integrated candidate is ready for publication |
| Blockers | VM-01–VM-03 require healthy composed Web/API services and are not claimed from isolated checks; VM-04 requires SHIFU-83/85 staging deployments, CloudWatch groups, awslogs/IAM and exact 14-day retention |
| Candidate | Working tree at implementation time; unrelated pre-existing changes in `AGENTS.md`, prompt/SDD files, `iac/` and `documentation/reports/armazenamento-v1.docx` were preserved |

# Progress

| CA | RF coverage | Implementation | Verification | Checks / evidence | Remaining work |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-06 | Complete locally | Passed for provider/middleware/lifecycle boundaries | API focused telemetry suite, direct Web TypeScript, Vitest, schema/allowlist inspection, app import and browser companion | CI/build execution in hosted environment |
| CA-02 | RF-02 | Complete locally | Boundary/static proof passed; composed Web→API Playwright run not available locally | Axios request-ID tests, API middleware tests, browser companion keyboard/interaction gate | Run CI-03/VM-01 with healthy Web/API services |
| CA-03 | RF-03 | Complete locally | Shared wrapper and registry proof passed; real Inngest/provider runs not available locally | Lifecycle wrapper tests, explicit 15-job catalog/registrar wiring, no raw job logging, targeted static checks | Run CI-04/VM-02 with Docker/Testcontainers and real-runtime flags |
| CA-04 | RF-04 | Complete locally | Provider/error-boundary privacy assertions passed | API focused handlers/middleware suite, Web provider allowlist, no raw job logger scan, targeted static checks | Run CI-05/VM-03 with controlled synthetic forbidden values |
| CA-05 | RF-05 | Complete locally | Unexpected-error and telemetry-failure assertions passed | API error handler suite and best-effort provider/pipe/lifecycle paths | Run VM-03 in a composed runtime |
| CA-06 | RF-07, RF-08 | Complete locally; staging disposition pending | Local lifecycle/dependency composition passed; staging evidence unavailable | App import, lifecycle tests, single-provider composition review | Run VM-04 after SHIFU-83/85 staging gate is available |
| CA-07 | RF-07 | Complete locally at consumer boundaries | Synthetic business-event/controller assertions passed; composed DB-backed tests unavailable | Auth/Learning controller tests, event matrix wiring, retry/evaluation ownership review | Run CI-08/VM-02 with database and Inngest fixtures |

# Check Results

| EV | Check / type / CA coverage | Status | Candidate, date and environment/fixtures | Command / procedure and working directory | Observations, artifacts and limits |
| --- | --- | --- | --- | --- | --- |
| EV-01 | CI-01 / Automated / CA-01, CA-04 | Passed | Working tree; 2026-10-21; API focused fixtures | `apps/server/.venv/Scripts/pytest.exe -q --confcutdir=tests/shared/server/middlewares tests/shared/server/middlewares/test_telemetry_middleware.py tests/shared/server/handlers/test_app_error_telemetry.py tests/shared/server/lifecycle/test_app_lifecycle_telemetry.py tests/shared/server/controllers/test_business_event_telemetry.py tests/shared/server/messaging/test_job_lifecycle_telemetry.py` from `apps/server` | 7 passed; one Starlette deprecation warning. Assertions cover JSON/allowlist/error resilience at API boundaries. |
| EV-02 | CI-02-types / Automated baseline / CA-01–CA-07 | Passed with limits | Working tree; local toolchains | Web direct `cmd /c .\\node_modules\\.bin\\tsc.cmd --noEmit` from `apps/web`; API targeted `basedpyright` over changed source/tests | Web TypeScript passed with `NODE_OPTIONS=--max-old-space-size=4096`; targeted API basedpyright reported 0 errors/warnings/notes. `pnpm --filter web check:types` was blocked by pnpm preflight rejecting ignored `esbuild@0.28.2` build scripts; full API basedpyright OOMed. |
| EV-03 | CI-02-lint / Automated baseline / CA-01–CA-07 | Passed with limits | Working tree; local toolchains | `ruff check src tests`; `ruff format --check src tests`; Web focused Vitest and dependency checks | API Ruff/format passed (`1233 files already formatted`); Web 5 suites/57 tests passed and dependency-cruiser passed. Web Biome was unavailable because the pnpm preflight environment was incomplete. |
| EV-04 | CI-02-architecture / Automated baseline / CA-01–CA-07 | Passed | Working tree; local toolchains | `tach check --dependencies -e ...` from `apps/server`; `cmd /c .\\node_modules\\.bin\\depcruise.cmd --config dependency-cruiser.config.cjs src` from `apps/web` | API architecture reported all modules valid; Web dependency-cruiser reported 477 modules, 1659 dependencies and no violations. |
| EV-05 | CI-03 / Automated / CA-02 | Re-scoped by review | Integrated candidate; 2026-10-24; local Web toolchain | `pnpm --filter web run test:coverage` from repository root | The redundant standalone Web telemetry integration test was removed per PR review. Full Web coverage passed with 141 suites and 1,238 tests; composed Web→API evidence remains service-dependent. |
| EV-06 | CI-04 / Automated / CA-03 | Partial local pass | Working tree; isolated lifecycle fixture and disposable AgentOS fixture | `apps/server/.venv/Scripts/pytest.exe -q tests/shared/server/messaging/test_job_lifecycle_telemetry.py` plus the focused AgentOS workflow regression with `SHIFU_RUN_REAL_AGENTOS_TESTS=1` | Lifecycle wrapper test passed (2 tests); focused AgentOS commit/no-op regression passed (1 passed, 21 deselected); all 15 function IDs are explicitly mapped and registrars pass the same provider. The full composed job/provider gate remains unclaimed. |
| EV-07 | CI-05 / Automated / CA-04, CA-05 | Passed locally at API boundary | Working tree; isolated synthetic error fixture | `test_app_error_telemetry.py` and `test_telemetry_middleware.py` in EV-01 | Raw messages are not serialized, frames are sanitized, and provider failures are swallowed without changing the HTTP/job result. Full Web error integration remains service-dependent. |
| EV-08 | CI-06 / Automated baseline / CA-01–CA-07 | Not run | Working tree; local build toolchains | Spec Web/API build commands | Not run because the Web package-manager preflight/build-script restriction and full API typecheck resource failure made a reliable integrated build unavailable; no build pass is inferred. |
| EV-09 | CI-07 / Automated / CA-01, CA-04, CA-06 | Passed locally | Working tree; app import and isolated lifecycle fixtures | `python -m compileall -q src`; app import with required local env; `test_app_lifecycle_telemetry.py` in EV-01 | App imported with 8 routes; one composed provider is stored in `app.state`, shared with middleware/registrars/workflow registries, and lifecycle/dependency events use the fixed catalog. |
| EV-10 | CI-08 / Automated / CA-07 | Passed at isolated boundary | Working tree; isolated controller fixtures and AgentOS regression fixture | `test_business_event_telemetry.py`, `test_get_current_session_controller.py`, `test_create_goal_controller.py`, and the focused AgentOS workflow regression, plus static matrix review | Business-event tests and the AgentOS completion-after-commit regression passed; DB-backed composed controller/job selections remain unclaimed because the prescribed composed runtime was not completed. |
| EV-11 | VM-01 / Manual / CA-02 | Blocked locally | Working tree; no healthy composed Web/API services | Spec VM-01 Playwright procedure | Requires real Web/BFF and API processes. The companion page proved keyboard/search/navigation integrity only and is not VM-01 evidence. |
| EV-12 | VM-02 / Manual / CA-03, CA-07 | Blocked locally | Working tree; Docker/Testcontainers unavailable | Spec VM-02 procedure | Do not claim exact-once job/provider/controller correlation without the composed fixtures and real runtime flags. |
| EV-13 | VM-03 / Manual / CA-04, CA-05 | Blocked locally | Working tree; controlled API boundary only | Spec VM-03 procedure | Isolated error assertions passed; prescribed stdout/response inspection with a composed service was not available. |
| EV-14 | VM-04 / Manual / CA-06 | Blocked external | Requires SHIFU-83/85 staging deployments, both CloudWatch groups, awslogs/IAM and 14-day retention | Spec staging procedure | No staging account/group/retention access was available. This is the remaining external delivery gate and is not replaced by local evidence. |
| EV-15 | Companion integrity gate / Automated documentation / not a CA | Passed | Working tree; local static server, Playwright CLI, 390×844 viewport | Serve `interactive-spec.html`; click all chapter links, expand all, search `CloudWatch`, press `/`, snapshot and screenshot | Links reached expected hashes, expand/search worked, `/` focused the search input, narrow snapshot and screenshot were captured under `apps/web/.playwright-cli/`, and console reported 0 errors/0 warnings. |

# Findings

| ACH | Problem / evidence / affected CA | Severity | Affected checks | Status / correction / verification |
| --- | --- | --- | --- | --- |
| ACH-01 | `TelemetryPipe` imported FastAPI `Request` only under `TYPE_CHECKING`, causing FastAPI to treat the dependency as a query parameter and return 422. | high | CI-01, CI-03, CI-05, CI-08 | Resolved by making `Request` a runtime import with a narrow lint exemption. EV-01 then passed 7 tests. |
| ACH-02 | Web changed-file coverage initially selected a Playwright test in the Vitest command. | medium | CI-02, CI-03 | Resolved by removing `tests/shared/structured-telemetry-api.test.ts` from the Vitest selection; the existing Web integration job runs it through `playwright test`. |
| ACH-03 | Local package preflight rejects ignored `esbuild@0.28.2` build scripts; sandboxed Node/Vitest runs also hit Windows EPERM and memory failures. | medium | CI-02, CI-06 | Direct TypeScript and unsandboxed focused Vitest passed; pnpm/Biome/build claims remain limited rather than inferred. |
| ACH-04 | Docker-backed fixtures cannot open the Docker Desktop named pipe (`pywintypes.error: (5, CreateFile, Acesso negado.)`). | medium | CI-04, CI-08, VM-01–VM-03 | External environment limitation; isolated boundary checks were run and composed checks remain explicitly blocked. |
| ACH-05 | Full API basedpyright exceeded the local Node memory zone; targeted changed-scope basedpyright passed. | low | CI-02 | Full-repository gate remains unclaimed; targeted type evidence is current. |
| ACH-06 | The AgentOS evaluation workflow could bypass the shared completion event, and the Inngest path could report completion after a no-op evaluation. | high | CI-04, CI-08, CA-03, CA-07 | Resolved by gating both paths on a committed evaluation and adding the direct workflow regression; the focused AgentOS test passed. |
| ACH-07 | The changed-file server CI command selected three controller/job test files twice. | medium | CI-02, CI-04, CI-08 | Resolved by removing the lower duplicate entries; each affected filename now occurs once and `git diff --check` passes. |
| ACH-08 | Final independent review initially reported the CI duplicate selections above. | informational | F9 / affected workflow coverage | Rechecked after correction; no unresolved contract, architecture, privacy, runtime-correlation or coverage finding remains. |
| ACH-09 | PR review identified redundant standalone Web telemetry tests, including the fetch stream client test; these tests no longer represented required product behavior after the current `main` test composition. | medium | Review feedback / Web test scope | Resolved by removing the ten newly added standalone Web tests while retaining the existing route-handler adaptations and updating the server-function mock for both current `createServerFn` chaining forms. Web typecheck, lint, architecture, focused test and full coverage passed. |

# Lessons Learned

| Lesson | Supporting finding / evidence | Documentation action or disposition |
| --- | --- | --- |
| FastAPI dependency annotations must remain runtime-resolvable when used by a shared pipe. | ACH-01 and the initial 422 response | Keep the runtime import and focused composed boundary test. |
| Integration test runners must remain separated by framework. | ACH-02 | Keep Playwright selections in `test:integration` and Vitest selections in changed-file coverage. |
| Local evidence must distinguish isolated contract proof from composed service proof. | ACH-03/ACH-04 and EV-05/EV-12 | Preserve explicit blocked dispositions until Docker and staging gates are available. |
| Completion telemetry must be owned by the committed evaluation boundary in every runtime path. | ACH-06 and EV-06/EV-10 | Keep the no-op/commit regression for both Inngest and AgentOS workflow paths. |

# Handoff

| Field | Detail |
| --- | --- |
| Candidate | Isolated merge candidate implementing Spec revision 5 for SHIFU-94; no external Jira/Confluence mutation was made. |
| Completed | F1–F9 implementation and local validation; final F9 review; Web/API providers, request propagation, error/lifecycle/business boundaries, all 15 job registrars, Resend/OpenRouter/Jev adapters, root composition, CI selections and `documentation/telemetry.md`. |
| Unfinished | VM-01–VM-03 composed-runtime observations, CI-06 hosted builds, and VM-04 staging CloudWatch retention proof; hosted PR checks remain to be observed after publication. |
| Uncommitted work | Task-owned production/tests/docs/workflow paths shown by `git status`; preserve unrelated pre-existing `AGENTS.md`, prompt/SDD edits, `iac/` and `documentation/reports/armazenamento-v1.docx`. |
| Active processes | None; the temporary documentation HTTP server and Playwright browser were closed after validation. |
| Blockers | VM-01–VM-03 composed Web/API observations were not completed; pnpm/esbuild preflight and full typecheck resource limits remain; external SHIFU-83/85 staging/CloudWatch/IAM gate remains required for VM-04. |
| Next action | Publish the corrected PR and observe hosted checks; run the blocked composed checks when Docker access is restored, then execute VM-04 after staging deployment and use `conclude-spec` to close the SDD artifacts. |

# Delivery

| RP/JN | RF / CA coverage | Accepted evidence | Disposition and limitations |
| --- | --- | --- | --- |
| No canonical module RP/JN; SHIFU-94 and privacy policy v4 govern this shared infrastructure delivery. | RF-01–RF-08 / CA-01–CA-07 | Local implementation, focused API/Web checks, architecture/static checks, browser companion integrity and independent review | Local candidate is ready; composed-runtime and staging gates remain explicitly pending/blocked. |

| PR | Current head SHA | CI / review state | Run / artifacts |
| --- | --- | --- | --- |
| #40 | Pending publication | Review feedback implemented; hosted checks pending | Evaluation, telemetry documentation and current focused Web/API validation |

| Field | Result |
| --- | --- |
| Publication | Pending push of the corrected merge candidate; no merge or deploy |
| Source verification | SHIFU-94, privacy policy v4 and Spec revision 5 were preserved from the kickoff preflight; no external source was mutated |
| Documentation Alignment | Added `documentation/telemetry.md`; no Confluence/Jira mutation authorized |
| Revision History | No Spec contract change; implementation and evidence recorded in this Evaluation |
| Limitations | VM-04 requires external staging/CloudWatch/IAM evidence; VM-01–VM-03 require healthy composed services; visual feature evidence is not applicable by contract |
