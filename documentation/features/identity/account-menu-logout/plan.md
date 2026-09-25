---
title: Identity account menu and current-session logout implementation plan
status: completed
spec: ./spec.md
spec_revision: 3
evaluation: ./evaluation.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-69
last_updated_at: 2026-09-24
---

# 1. Execution status

| Item | Current state |
| --- | --- |
| Spec | [`spec.md`](./spec.md), revision `3`, status `ready` |
| Why Plan-backed execution | The slice crosses Better Auth BFF persistence, protected-route hydration, shared desktop/mobile shell, a new public route, generated route metadata, browser authorization behavior and real PostgreSQL-backed handler validation. The auth and shell boundaries can be built in parallel after one typed contract handshake. |
| Plan status | `in_progress` |
| Current phase | Completed |
| Next action | Delivery handoff through the scoped commit and pull request workflow. |
| Active blockers | None for this delivery. `pnpm-lock.yaml` remains an explicit unstaged exclusion owned by concurrent work. |
| External dependencies | Better Auth `1.6.23` APIs for signed-cookie access and verification cleanup were confirmed; local PostgreSQL, FastAPI and Chromium are required for integration and manual validation. |
| Active Builders | `identity-auth-bff-builder` owns F1 and `identity-shell-ui-builder` owns F2; paths are non-overlapping and use the shared typed contract below. |
| Shared ownership | The Orchestrator owns `evaluation.md`, `apps/web/src/routeTree.gen.ts`, integrated fixture/configuration changes, generated output review, quality gates, evidence freshness and final reconciliation. No package or lockfile change is expected. |

# 2. Readiness and dependencies

| Gate | Required evidence | Owner | Status | Next action |
| --- | --- | --- | --- | --- |
| Spec readiness | Current Spec is `ready` at revision `3` | Orchestrator | `pass` | Preserve revision through all phases. |
| Product authority | Identity PRD `83001345`, version `1`, permits a pending account only to continue confirmation, recovery and exit; it does not require an authenticated account menu | Orchestrator | `pass` | Preserve the Spec's standalone pending-confirmation `Sair`. |
| Canonical authority | Identity PRD content ID `83001345`, version `1`, is current and matches the Spec | Orchestrator | `pass` at planning preflight | Recheck before conclusion. |
| Design authority | [`design/handoff.md`](./design/handoff.md) inventories `h7fGzC`, `x9zS2` and `sFInu`, including accepted mobile, keyboard, pending and failure supplemental states | Orchestrator | `pass` | Use saved references and the Design Contract during UI validation. |
| Better Auth API | Better Auth `1.6.23` supports signed-cookie read/expiry and verification deletion through the endpoint context | Builder Auth/BFF | `pass` | Implement after the typed Builder handshake is recorded. |
| Typed Builder handshake | `LayoutAccount { displayName, email }`, `signOut(): Promise<void>`, and `exitPendingConfirmation(): Promise<void>` are recorded in the implementation handoff | Orchestrator | `pass` | Preserve this contract across F1/F2 and do not hydrate account IDs, tokens or pending identifiers. |
| REST-client artifact | `apps/server/rest-client/identity/auth.rest` covers every affected BFF logout route with reusable non-secret variables | Builder Auth/BFF | `pass` | Both labeled same-origin routes are present without cookie values or credentials. |
| Route generation | Source route exists before generated route metadata is updated | Orchestrator | `pass` | Generated metadata includes the public pending-confirmation route. |
| Integration environment | PostgreSQL at `localhost:54344`, FastAPI at `http://localhost:7777/health`, web at `http://localhost:7000`, and Chromium are available | Orchestrator | `blocked` | Docker dependencies are healthy, but FastAPI cannot load without `REDIS_URL` and the database references absent Alembic revision `f4a2c7d1e9b0`. |

# 3. Execution ledger

| Wave | Builder | Phase | Outcome | Depends on | Parallel with | Status | Exit condition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `identity-auth-bff-builder` | F1 | Safe current-session and pending-context operations plus hydrated account projection | Typed handshake | F2 after the same gate | `complete` | EV-014 verifies handler persistence, cookies and REST parity. |
| 1 | `identity-shell-ui-builder` | F2 | Accessible account menu in desktop/mobile shell and standalone pending-confirmation exit route | Typed handshake | F1 after the same gate | `complete` | Focused browser coverage passes success, pending, failure/retry, focus, keyboard and narrow viewport behavior. |
| 2 | `Orchestrator` | F3 | Integrated generated route tree, complete diff and baseline validation | F1 and F2 | — | `complete` | EV-013 to EV-015 verify generation, quality gates, runtime and visual states. |
| 3 | `Implementation Reviewer` | F4 | One read-only review of the integrated candidate and evidence | F3 | — | `complete` | One reviewer completed; its verified pending-cookie recovery finding was corrected and recorded as ACH-006. |
| 4 | `Orchestrator` | F5 | Corrected candidate and Evaluation ready for conclusion | F4 and any resumed Builder corrections | — | `complete` | All acceptance criteria are accepted; ACH-008 is an explicit unrelated exclusion. |

### F1 — Auth and BFF session boundary

#### F1-T1 — Produce the safe authenticated access projection and BFF operations

- **Status/owner:** `in_progress` — `identity-auth-bff-builder`
- **Depends/parallel:** Starts after the typed handshake; may run in parallel with F2 without touching Shell/UI paths.
- **Paths:** `apps/web/src/provision/auth/better-auth/better-auth-provider.ts`; `apps/web/src/middlewares/require-auth-middleware.ts`; `apps/web/src/middlewares/enter-main-page-middleware.ts`; `apps/web/tests/identity/sign-in-auth-handler.test.ts`; `apps/web/tests/identity/register-confirmation-auth-handler.test.ts`; `apps/server/rest-client/identity/auth.rest`
- **Traceability:** `RF-01`, `RF-04`, `RF-05`, `RF-07`; `CA-01`, `CA-04`, `CA-06`, `CA-07`; `RP-03`, `RP-10`; `JN-07`
- **Outcome:** `LayoutAccount` exposes only display name/e-mail across matched-route hydration; current Better Auth sign-out deletes only the requesting session and clears its cookie; pending exit deletes only its opaque verification record and expires the pending cookie; rejected protected access also clears its browser session cookie.
- **Rules:** [`typescript-conventions-rules.md`](../../../rules/typescript-conventions-rules.md), [`provision-layer-rules.md`](../../../rules/provision-layer-rules.md), [`web-app-routing-rules.md`](../../../rules/web-app-routing-rules.md), [`widget-testing-rules.md`](../../../rules/widget-testing-rules.md). Apply the provider antipattern prohibition against provider-owned tests and the routing rule requiring real registered-handler coverage.
- **Risks/controls:** Token or account identifiers could cross hydration or browser storage; keep the token-bearing object server-only and assert negative privacy cases. Pending cleanup could delete an authenticated session; use the signed pending cookie identifier only and assert no Better Auth session mutation. Concurrent sessions could be over-revoked; use two persisted session rows in handler integration.
- **Exit:** `pnpm --filter web test:unit`; focused registered-handler coverage through `pnpm --filter web test:integration -- tests/identity/sign-in-auth-handler.test.ts tests/identity/register-confirmation-auth-handler.test.ts`; inspect real HTTP status, `Set-Cookie`, PostgreSQL rows, concurrent-session preservation and safe response bodies. `auth.rest` must contain labeled requests for `POST /api/auth/sign-out` and `POST /api/auth/pending-confirmation/sign-out`, current methods/paths/headers/bodies, reusable local variables and no credentials.

#### F1-T2 — Extend the browser-safe authentication context

- **Status/owner:** `in_progress` — `identity-auth-bff-builder`
- **Depends/parallel:** Depends on F1-T1's operation contracts; sequential within F1 and parallel with F2's rendering work after the contract is recorded.
- **Paths:** `apps/web/src/provision/auth/cookie-session-auth-provider.ts`; `apps/web/src/ui/shared/contexts/auth-context/types/auth-context-value.ts`; `apps/web/src/ui/shared/contexts/auth-context/use-auth-context-provider.ts`; `apps/web/src/ui/shared/contexts/auth-context/tests/use-auth-context-provider.test.ts`; `apps/web/tests/fixtures/identity-module-fixture.ts`
- **Traceability:** `RF-04`, `RF-05`, `RF-06`, `RF-07`; `CA-04`, `CA-05`, `CA-06`, `CA-07`; `RP-03`, `RP-10`; `JN-07`
- **Outcome:** The browser receives `signOut` and `exitPendingConfirmation` as typed operations with same-origin requests, safe response validation, generic recoverable `AuthError` mapping and no persisted secret or pending identifier.
- **Rules:** [`typescript-conventions-rules.md`](../../../rules/typescript-conventions-rules.md), [`ui-layer-rules.md`](../../../rules/ui-layer-rules.md), [`provision-layer-rules.md`](../../../rules/provision-layer-rules.md), [`widget-testing-rules.md`](../../../rules/widget-testing-rules.md). Do not create provider-owned tests; test the context boundary and consuming routed behavior.
- **Risks/controls:** Non-success or malformed responses could leave the UI in an unhandled state; normalize them to the existing safe auth error contract and test retry. Fixture changes could accidentally expose server-only access; assert the browser fixture contains only the layout projection.
- **Exit:** `pnpm --filter web test:unit`; the context test verifies the complete value and provider delegation; browser fixtures verify request method, same-origin path, response handling and absence of secrets.

### F2 — Shared shell and pending-confirmation experience

#### F2-T1 — Implement the account menu in the authenticated desktop and mobile shell

- **Status/owner:** `in_progress` — `identity-shell-ui-builder`
- **Depends/parallel:** Depends on the F1 typed `LayoutAccount` and auth operation contract; may proceed in parallel with F1 implementation after the handshake.
- **Paths:** `apps/web/src/ui/shared/widgets/layouts/root-layout/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/root-layout/use-root-layout.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/use-app-layout.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/use-account-menu.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/tests/account-menu.test.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/account-menu/tests/use-account-menu.test.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/tests/app-layout.test.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/tests/use-app-layout.test.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/desktop-header/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/mobile-header/index.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/mobile-header/use-mobile-header.ts`; `apps/web/src/ui/shared/widgets/layouts/app-layout/desktop-header/tests/desktop-header.test.tsx`; `apps/web/src/ui/shared/widgets/layouts/app-layout/mobile-header/tests/mobile-header.test.tsx`; `apps/web/src/ui/shared/widgets/components/icon/index.tsx`; `apps/web/tests/shared/app-layout.test.ts`
- **Traceability:** `RF-01` to `RF-06`; `CA-01` to `CA-05`; `RP-03`, `RP-10`; `JN-07`
- **Outcome:** One shared account-menu behavior is reachable from desktop and mobile headers, renders the current summary, keeps `Sua conta` disabled and unfocusable, exposes only `Sair` as an enabled action, handles Escape/outside dismissal and focus restoration, prevents duplicate logout, and presents safe pending/error/retry states in pt-BR.
- **Rules:** [`typescript-conventions-rules.md`](../../../rules/typescript-conventions-rules.md), [`ui-layer-rules.md`](../../../rules/ui-layer-rules.md), [`widget-testing-rules.md`](../../../rules/widget-testing-rules.md), [`web-app-routing-rules.md`](../../../rules/web-app-routing-rules.md). Apply the UI antipatterns against local nested widgets, raw icon imports, direct navigation and color-only state communication. Apply the widget rule that component tests mock only the owning hook while route tests render actual composition.
- **Design references:** [`design/handoff.md`](./design/handoff.md), `design/references/h7fGzC.png`, `design/references/x9zS2.png`, `design/references/sFInu.png`; use existing `Icon`, Button, focus, typography, spacing and dark-only tokens. Preserve the approved disabled `Sua conta` deviation.
- **Risks/controls:** Desktop and mobile header menus could share outside/Escape listeners; scope refs and cleanup per menu instance and verify both viewports. Visual state could become color-only; use text, icon and announced alert semantics. Menu geometry could clip at narrow widths; validate the exact 390 x 844 viewport.
- **Exit:** `pnpm --filter web test:unit`; `pnpm --filter web test:integration -- tests/shared/app-layout.test.ts`; verify accessible roles/names, `aria-expanded`, keyboard traversal, focus return, outside click, one request during pending, safe error/retry and final `/login` navigation through the actual shared layout.

#### F2-T2 — Add the public pending-confirmation route and standalone exit

- **Status/owner:** `in_progress` — `identity-shell-ui-builder`
- **Depends/parallel:** Depends on F1-T2's `exitPendingConfirmation` operation; sequential with route generation but parallel with F2-T1's account-menu rendering.
- **Paths:** `apps/web/src/routes/pending-confirmation/index.tsx`; `apps/web/src/ui/identity/widgets/pages/pending-confirmation-page/index.tsx`; `apps/web/src/ui/identity/widgets/pages/pending-confirmation-page/use-pending-confirmation-page.ts`; `apps/web/src/ui/identity/widgets/pages/pending-confirmation-page/tests/pending-confirmation-page.test.tsx`; `apps/web/tests/routes/identity/pending-confirmation.index.test.tsx`
- **Traceability:** `RF-05`, `RF-06`, `RF-07`; `CA-05`, `CA-06`, `CA-07`; `RP-03`, `RP-10`; `JN-07`
- **Outcome:** `/pending-confirmation` remains public and renders the restricted confirmation flow with a standalone `Sair`; success clears pending context and navigates to `/login`, while failure keeps the page usable, announces safe recovery text and allows retry without creating or deleting an authenticated session.
- **Rules:** [`typescript-conventions-rules.md`](../../../rules/typescript-conventions-rules.md), [`ui-layer-rules.md`](../../../rules/ui-layer-rules.md), [`web-app-routing-rules.md`](../../../rules/web-app-routing-rules.md), [`widget-testing-rules.md`](../../../rules/widget-testing-rules.md). Apply the route rule requiring a thin route, canonical `ROUTES`, actual route middleware/composition coverage, and no direct backend dependency in mocked route suites.
- **Design references:** [`design/handoff.md`](./design/handoff.md); pending, failure/retry and narrow-viewport states are approved derived states and require fresh runtime screenshots rather than new Pencil frames.
- **Risks/controls:** The pending exit must not be presented as an authenticated account menu; keep the standalone control separate as required by the canonical PRD and Spec revision `3`. Route generation must not be hand-edited; use the declared generator after the source route exists.
- **Exit:** `pnpm --filter web test:unit`; `pnpm --filter web test:integration -- tests/routes/identity/pending-confirmation.index.test.tsx`; assert actual route composition, request method/path/response, pending state, failure/retry, final `/login`, narrow viewport and no authenticated-session effect.

### F3 — Integrated generation and quality gates

#### F3-T1 — Reconcile the integrated candidate and establish the evidence baseline

- **Status/owner:** `pending` — Orchestrator
- **Depends/parallel:** F1-T1/F1-T2 and F2-T1/F2-T2 completed; no parallel implementation work remains.
- **Paths:** `apps/web/src/routeTree.gen.ts` (generated); `documentation/features/identity/account-menu-logout/evaluation.md` (Orchestrator-owned); all integrated changed paths reviewed against [`spec.md`](./spec.md); no Builder-owned source path may be changed independently in this task.
- **Traceability:** All `RF-01` to `RF-07` and `CA-01` to `CA-07`; all `VM-01` to `VM-03`; all cited `RP-*`/`JN-*` inherited from the Spec.
- **Outcome:** Generated route metadata, source diffs, Builder reports, REST-client parity and the initial Evaluation acceptance matrix agree with Spec revision `3`.
- **Rules:** [`web-app-routing-rules.md`](../../../rules/web-app-routing-rules.md), [`widget-testing-rules.md`](../../../rules/widget-testing-rules.md), [`ui-layer-rules.md`](../../../rules/ui-layer-rules.md), [`provision-layer-rules.md`](../../../rules/provision-layer-rules.md), [`sdd.md`](../../../sdd.md), [`tooling.md`](../../../tooling.md).
- **Risks/controls:** Generated output or shared fixture changes may hide cross-Builder incompatibility; review the complete integrated diff and rerun the affected exits instead of accepting Builder reports alone.
- **Exit:** `pnpm --filter web generate-routes`; `pnpm --filter web check:lint`; `pnpm --filter web check:architecture`; `pnpm --filter web check:types`; `pnpm --filter web test:unit`; `pnpm --filter web test:integration`; `pnpm --filter web build`. Confirm no server FastAPI gate is required because the approved slice changes no FastAPI source, persistence or migration.

### F4 — Independent implementation review

#### F4-T1 — Review the integrated candidate once

- **Status/owner:** `pending` — one read-only `Implementation Reviewer`
- **Depends/parallel:** Starts only after F3's automated gates and evidence baseline pass; no parallel reviewer per Builder, package or specialty.
- **Paths:** Read-only review of the complete integrated diff, `spec.md`, `plan.md`, `evaluation.md`, all affected web source/tests, generated route metadata and `apps/server/rest-client/identity/auth.rest`.
- **Traceability:** Every `CA-01` to `CA-07`, every `VM-01` to `VM-03`, the Design Contract, privacy restrictions and REST-client parity.
- **Outcome:** Advisory findings identify behavioral regressions, cross-Builder contract problems, stale evidence, route or generated-artifact gaps, and UI/server validation omissions without changing files or broadening scope.
- **Rules:** [`sdd.md`](../../../sdd.md) and every affected Rule Pack listed in the F3 task.
- **Risks/controls:** Review findings can invalidate evidence; the Orchestrator records each verified finding as `ACH-*`, resumes the responsible Builder, replaces stale evidence and reruns the affected exit before conclusion.
- **Exit:** Reviewer report is complete and the Orchestrator has verified each finding, recorded its disposition in `evaluation.md`, and either accepted it with evidence or routed a correction.

### F5 — Final correction and handoff

#### F5-T1 — Close the integrated delivery ledger

- **Status/owner:** `pending` — Orchestrator
- **Depends/parallel:** F4-T1 complete and all verified findings resolved by the responsible Builder; no parallel work.
- **Paths:** `documentation/features/identity/account-menu-logout/plan.md`; `documentation/features/identity/account-menu-logout/evaluation.md`; any correction remains inside the previously assigned Builder path and is not created as an overlapping independent ownership boundary.
- **Traceability:** All Spec requirements, acceptance criteria, manual scenarios, visual states and route-group parity obligations.
- **Outcome:** Plan phases/tasks are complete, evidence is current and accepted, and the feature is ready for `conclude-spec`; the Plan remains `draft` until implementation starts, then follows the SDD lifecycle to `in_progress` and completion through conclusion.
- **Rules:** [`sdd.md`](../../../sdd.md), [`tooling.md`](../../../tooling.md), all affected Rule Packs and the nearest repository `AGENTS.md`.
- **Risks/controls:** A changed Spec revision or PRD version invalidates assignments and evidence; stop, record the mismatch, reconcile the Plan and restart affected phases before handoff.
- **Exit:** Every task and phase is complete; all applicable pnpm gates pass; generated route metadata and REST-client artifact are reviewed; every `CA-*` and `VM-*` has accepted evidence; the single Implementation Reviewer is complete; the Evaluation is ready for `conclude-spec`.

# 4. Validation and handoff

| Type | Scenario/surface | Criteria | Reference | Evidence target | Status |
| --- | --- | --- | --- | --- | --- |
| Automated | Account-menu component and hook suites | `CA-01`, `CA-02`, `CA-03`, `CA-05` | Spec Validation Contract; F2-T1 | `evaluation.md` `EV-*` for semantic states, keyboard lifecycle, pending, failure and retry | `pending` |
| Automated | Auth context and browser-safe provider boundary | `CA-04`, `CA-05`, `CA-06`, `CA-07` | Technical Contract; F1-T2 | `evaluation.md` `EV-*` for typed operations, safe errors and no browser secret persistence | `pending` |
| Automated | Pending-confirmation page component and route suite | `CA-05`, `CA-06`, `CA-07` | Technical Contract; F2-T2 | `evaluation.md` `EV-*` for request/response, redirect, failure/retry and no authenticated-session effect | `pending` |
| Runtime | Registered Better Auth sign-out handler with PostgreSQL | `CA-04`, `CA-07` | Technical Contract; F1-T1 | `evaluation.md` `EV-*` with current-session row/cookie deletion and concurrent-session preservation | `pending` |
| Runtime | Registered pending-exit BFF handler with PostgreSQL | `CA-06`, `CA-07` | Technical Contract; F1-T1 | `evaluation.md` `EV-*` with verification cleanup, pending-cookie expiry, idempotency and no Better Auth session mutation | `pending` |
| REST client | Affected BFF auth logout route group | `CA-04`, `CA-06`, `CA-07` | `apps/server/rest-client/identity/auth.rest` | `evaluation.md` `EV-*` parity result for `POST /api/auth/sign-out` and `POST /api/auth/pending-confirmation/sign-out`, methods, paths, headers, bodies, reusable variables and no credentials | `pending` |
| Browser integration | Shared protected `AppLayout` at desktop and mobile widths | `CA-01` to `CA-05` | `apps/web/tests/shared/app-layout.test.ts`; `VM-01`, `VM-02` | `evaluation.md` `EV-*` with actual route composition, mocked transport request/response, URL and visible outcomes | `pending` |
| Browser integration | Public `/pending-confirmation` route | `CA-06`, `CA-07` | `apps/web/tests/routes/identity/pending-confirmation.index.test.tsx`; `VM-03` | `evaluation.md` `EV-*` with actual route composition, pending exit and recovery | `pending` |
| Manual | `VM-01` account-menu interaction and accessibility | `CA-01`, `CA-02`, `CA-03`, `CA-05` | Spec `VM-01`; `design/references/h7fGzC.png`, `x9zS2.png`, `sFInu.png` | Fresh Playwright screenshots at `1440 x 900` and `390 x 844`, keyboard/focus/outside-click and console/network inspection | `pending` |
| Manual | `VM-02` current-session logout isolation | `CA-04`, `CA-05`, `CA-07` | Spec `VM-02` | Two browser contexts, cookie/session persistence, protected-history denial, second-session authorization, privacy inspection and fresh post-logout desktop screenshot | `pending` |
| Manual | `VM-03` pending-context exit | `CA-06`, `CA-07` | Spec `VM-03`; `design/handoff.md` derived-state decision | Fresh `390 x 844` pending success and safe failure/retry screenshots, final URL, no-session assertion and console/network inspection | `pending` |
| Visual | Header component state | `CA-01`, `CA-02` | `design/references/h7fGzC.png`, node `h7fGzC` | Fresh comparison at the exact `1440 x 64` reference state | `pending` |
| Visual | Open account-menu component state | `CA-01` to `CA-05` | `design/references/x9zS2.png`, node `x9zS2` | Fresh comparison at the exact `304 x 192` menu surface state, including approved disabled-row deviation | `pending` |
| Visual | Complete desktop protected state with menu open | `CA-01` to `CA-05` | `design/references/sFInu.png`, node `sFInu` | Fresh comparison at `1440 x 900` with runtime identity data | `pending` |

## Handoff condition

The Orchestrator may route directly to `conclude-spec` only when:

- the integrated candidate preserves the canonical PRD and Spec revision `3` standalone pending-confirmation exit;
- every F1-F5 task and phase is completed with non-overlapping ownership;
- the integrated diff still matches the Spec's affected-path map and Design Contract;
- `pnpm --filter web generate-routes`, `check:lint`, `check:architecture`, `check:types`, `test:unit`, `test:integration` and `build` pass without lowering configured floors;
- generated route metadata, handler fixtures, `auth.rest` and all other generated or shared artifacts are reviewed;
- every `CA-*` and `VM-*` has current accepted evidence, including each supplied visual state and supplemental screenshot decision;
- the real registered BFF handlers prove response, cookie, persistence, isolation and privacy behavior rather than relying only on mocked transport;
- the single Implementation Reviewer completed and all verified findings are resolved; and
- `evaluation.md` is ready for `conclude-spec`.
