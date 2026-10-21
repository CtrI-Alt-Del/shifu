---
title: SHIFU-96 Public privacy policy page
status: implemented
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-96 (issue 12606)
scope:
  - Identity public privacy notice
  - Web routing and entrypoints
last_updated_at: 2026-10-21
---

# Objective

Deliver the public, Portuguese privacy notice required by SHIFU-96. The page will explain Shifu's data practices, legal bases, rights, contact, retention and AI-provider transfers, and be reachable without an account from the existing Identity entrypoints. Compact mode; all public factual choices are owned by this task and approved for the academic product demonstration by the user.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Public learner or former learner | Anonymous `/privacy` page with linked contents, disclosures, rights and contact | An API, account-specific data, request workflow, consent capture or confirmation that a `mailto:` was sent/received |
| Identity navigation | Links from Account, Sign in and Register; public-route classification | Account-deletion flow/modal is absent and remains with its owning implementation; no deletion workflow is created here |
| Data and privacy disclosures | Categories, purposes/legal bases, minors, essential cookies, vendors/transfers, rights, retention and version date | Operational implementation of deletion, vendor contracts, access requests or provider routing changes |

Selected Identity requirements: `RP-06` full for the published notice and Account entrypoint; `RP-09` partial for user-facing retention/deletion disclosures only; `RP-10` full for accessible navigation/reading; `RP-11` partial for the public manual contact channel. `JN-11` supplies post-account-closure context; the protected account deletion journey is outside this change.

## Design handoff

See [`design/handoff.md`](design/handoff.md). It identifies both required Pencil references, viewports, tokens, required states and accepted deviations. The `.pen` design is not modified.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | `RP-06`, `RP-10`, `JN-11`; SHIFU-96 | `/privacy` renders directly without a session or private application shell and remains available to a former learner. |
| RF-02 | `RP-06`, `RP-09`, `RP-11`; SHIFU-96 | The page explains data categories, purpose and legal basis; GSW as controller; children/adolescents; necessary cookies; AI/model providers and possible international transfers; rights; deletion/retention; and notice version/date in clear pt-BR. |
| RF-03 | `RP-06`, `RP-11`; SHIFU-96 | The privacy email is visible and linked with the exact destination, subject and body from the issue. Activating it only opens the mail client; the page does not report successful submission or receipt. |
| RF-04 | `RP-06`; SHIFU-96 | Account, Sign in and Register expose a navigable link to the canonical `/privacy` route. |
| RF-05 | `RP-10`; SHIFU-96 and Pencil references | The index, section hierarchy, contact link and page work with keyboard and assistive names at desktop and mobile widths without horizontal overflow, clipped content or loss of focus indication. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | A browser without an authenticated session | It opens `/privacy` directly | The URL resolves, policy heading/content render, and the private navigation shell is absent | CI-01, VM-01 |
| CA-02 | RF-02 | The public page | A learner scans its contents | All disclosure sections, data-purpose/legal-basis relationships, version and retention distinction are present in pt-BR | CI-01, VM-01 |
| CA-03 | RF-03 | The public page | A learner follows the privacy contact | The visible address is `shifu.ctrlaltdel@gmail.com`; `href` encodes recipient `shifu.ctrlaltdel@gmail.com`, subject `Solicitação sobre meus dados — Shifu`, and body `Olá! Gostaria de solicitar: [descreva seu pedido].`; no delivery claim is shown | CI-01, VM-01 |
| CA-04 | RF-04 | Account, Sign in or Register | A learner activates its privacy link | Navigation reaches `/privacy` and the page renders | CI-02 |
| CA-05 | RF-05 | Desktop 1440 px and mobile 390 px; keyboard only | A learner uses the index, sections and contact | The layout follows the handoff, anchor targets are focusable/readable, contrast/focus remain usable, and document width does not exceed viewport | CI-01, VM-02 |

Public disclosure decisions for this academic demonstration: GSW is the controller; the privacy contact is the named Encarregada Gabriela da Silva, reached at `shifu.ctrlaltdel@gmail.com`. Her identity is fictional by the user's explicit authorization. The public page identifies GSW and the Encarregada, gives the contact, and does not identify the product as an academic demonstration.

The public data-purpose/legal-basis matrix is:

| Data | Purpose | Legal basis disclosed |
| --- | --- | --- |
| Display name, email, password verifier, account/session metadata | Create and protect the account, authenticate access, and provide account functions | Contract performance (LGPD art. 7, V); legitimate interest (art. 7, IX) for session security |
| Learning objectives, responses, attempts, evaluations and progress | Deliver and personalize the learning experience | Contract performance (art. 7, V); always subject to the best interests of a child/adolescent (art. 14) |
| Mentor conversations, memories, attachments and extracted content submitted by the learner | Provide requested AI guidance and preserve the user's conversation context | Contract performance (art. 7, V); the user chooses whether to send content to Mentor |
| XP, level, practice streaks and achievements | Deliver the learner's gamification features | Contract performance (art. 7, V) |
| Email recipient, transactional message content and delivery metadata | Send account and service communications requested by the learner or needed to provide the account | Contract performance (art. 7, V); legal obligation (art. 7, II) when the communication is legally required |
| Application-access records | Protect the service and retain records required by the applicable statute | Legal obligation (art. 7, II; Marco Civil art. 15 for six-month application-access records) |
| Other security/operational logs and request correspondence | Detect incidents, operate the service, and respond to the user or regulator | Legitimate interest (art. 7, IX) and legal obligation (art. 7, II), as applicable to each record |

These bases are not represented as consent to the policy. The service does not treat a privacy-policy click or registration as blanket consent. Processing of children's data prioritizes best interests (art. 14); where consent is the applicable basis for a child, specific and prominent consent from a parent or legal guardian is obtained. For other applicable bases, the page explains the purpose and safeguards without calling consent the sole legal basis. The page does not invite users to enter sensitive personal data into Mentor.

The page states that only necessary session/security cookies are used and no advertising or analytics cookies are used, consistent with the inspected Web source. For transactional email, it names an SMTP delivery provider operating in Brazil, as an explicit academic assumption selected by the user; the current source supports both SMTP and Resend and uses a local SMTP/Mailpit example, so this destination is not verified as an operational deployment fact. It names OpenRouter, OpenAI, Amazon Bedrock and DeepSeek as providers associated with configured models and discloses possible processing in the United States (including OpenRouter) and China (DeepSeek), with other provider operating countries possible if routing changes. The OpenRouter global endpoint is not country-pinned by the current code; the notice does not promise that all requests stay in one country. It discloses the user-approved academic assumption that ANPD standard contractual clauses and supplementary safeguards apply to AI transfers. Provider settings request ZDR and deny data collection; the page distinguishes these provider controls from Shifu's own storage.

Retention in this task follows Q9 = A: application-access records are disclosed as retained for six months under Marco Civil art. 15 for the product scenario; other technical logs are kept only as needed for stated purposes/legal duties; active account records are deleted within 24 hours after confirmed closure; backup copies expire within 30 days after deletion, subject to specific legal preservation. This differs from the internal PRD/policy v4 statement that groups access and technical logs under 30 days. The user's explicit task decision governs this notice; the Confluence source remains unchanged and the conflict is recorded.

# Technical Contract

## Architecture Mapping

Owner: Identity. Rules: [UI Layer](../../../../rules/ui-layer-rules.md), [Web App Routing](../../../../rules/web-app-routing-rules.md), [Widget Testing](../../../../rules/widget-testing-rules.md), [TypeScript Conventions](../../../../rules/typescript-conventions-rules.md).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | TanStack route | `apps/web/src/routes/privacy/index.tsx` | Register `/privacy/` with the static `PrivacyPolicyPage`; no route loader, auth middleware, REST call or account context. |
| Create | Identity page widget | `apps/web/src/ui/identity/widgets/pages/privacy-policy-page/index.tsx` | Render semantic static policy, labeled table of contents, anchored sections, disclosure copy and mailto. Pure renderer; no hook/state. |
| Modify | Canonical Web routes | `apps/web/src/constants/routes.ts` | Add `privacy: '/privacy'` to `ROUTES` so `Anchor` consumers use the canonical route type. |
| Modify | Public route boundary | `apps/web/src/ui/shared/widgets/layouts/root-layout/use-root-layout.ts` | Add `ROUTES.privacy` to `PUBLIC_ROUTE_PATHS`; `useRootLayout` then avoids reading an account from route matches and `RootLayout` omits `AppLayout`. |
| Modify | Account entrypoint | `apps/web/src/ui/identity/widgets/pages/account-page/index.tsx` | Replace the inactive Privacy card status with an `Anchor` to `privacy`. |
| Modify | Sign-in entrypoint | `apps/web/src/ui/identity/widgets/pages/sign-in-page/index.tsx` | Add a visible policy link using `Anchor` without changing form submission/error behavior. |
| Modify | Registration entrypoint | `apps/web/src/ui/identity/widgets/pages/register-page/index.tsx` | Add a visible policy link using `Anchor`; do not imply registration is consent to all processing. |
| Generate | TanStack route tree | `apps/web/src/routeTree.gen.ts` | Regenerate from the route source with `pnpm --filter web generate-routes`; do not hand edit. |
| Modify | Root-layout unit test | `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts` | Assert `/privacy` and trailing-slash variant are public while protected paths remain private. |
| Modify | Existing journey tests | `apps/web/tests/identity/account-page.test.ts`, `sign-in-page.test.ts`, `register-page.test.ts` | Assert each entrypoint's link and destination. |
| Create | Public route integration test | `apps/web/tests/identity/privacy-policy-page.test.ts` | Cover direct anonymous access, required content/anchors, exact mailto, link navigation, keyboard and mobile width. |

## Runtime Flow

The file route renders a static Identity widget under the existing root provider composition. Public-route classification prevents `AppLayout` and account extraction; the route does not invoke authentication queries, the server, persistence or provider calls. Table-of-contents links target page section IDs. Privacy email uses a browser `mailto:` URI; the Shifu page has no send/receipt callback. Links from existing surfaces use the shared `Anchor` wrapper and typed `ROUTES` value. The future deletion modal is not present and is not created by this contract.

# Verification Contract

## Shared setup

Work from the repository root unless stated. Web unit tests run with Vitest/jsdom and the existing `apps/web/tests/setup.ts`. Browser route tests use the configured Playwright fixture and mocked transport for unrelated authentication requests; the privacy route itself must be opened through TanStack Router without an authenticated state. For the manual real-service check, use the user-started Web/API services; do not reset shared data or print browser storage. Keep captures/logs under `apps/web/.playwright-cli/{screenshots,logs,snapshots}/`.

## Automated

### CI-01 — Direct public policy route and disclosures

**Criteria:** CA-01, CA-02, CA-03, CA-05

**Expected result:** An anonymous direct visit renders all required section headings, index targets, contact and required retention/content disclosures; the mailto URI is exact; keyboard/mobile checks show no horizontal overflow.

**Setup / inputs:** Use the route integration spec with no authenticated state at 390 px and desktop viewport; test all section links and the email URI.

**Proof:** `apps/web/tests/identity/privacy-policy-page.test.ts` (planned).

```bash
pnpm --filter web exec playwright test tests/identity/privacy-policy-page.test.ts
```

**Passing condition:** The specified browser test executes and asserts URL, visible content, anchor targets, URI, keyboard navigation and document width.

### CI-02 — Existing privacy entrypoints

**Criteria:** CA-04

**Expected result:** Account, Sign in and Register each expose the link to the canonical route.

**Setup / inputs:** Use existing routes and their configured browser fixture.

**Proof:** `apps/web/tests/identity/account-page.test.ts`, `sign-in-page.test.ts`, `register-page.test.ts`.

```bash
pnpm --filter web exec playwright test tests/identity/account-page.test.ts tests/identity/sign-in-page.test.ts tests/identity/register-page.test.ts
```

**Passing condition:** All three named files execute and assert visible link names and `/privacy` destinations; existing form and access assertions remain intact.

### CI-03 — Public-route classification

**Criteria:** CA-01

**Expected result:** `/privacy` is public with or without trailing slash; protected routes remain private.

**Setup / inputs:** Existing Vitest setup.

**Proof:** `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts`.

```bash
pnpm --filter web exec vitest run src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts
```

**Passing condition:** The target test file executes assertions for `/privacy`, `/privacy/` and protected examples.

### CI-04 — Web types, lint/complexity, architecture and build

**Criteria:** CA-01–CA-05

**Scope:** Web app and scoped changed source/test files.

**Checks:** `pnpm --filter web check:types`; scoped non-writing `pnpm exec biome check <changed Web paths>` from root (includes configured complexity lint); `pnpm --filter web check:architecture`; `pnpm --filter web build`. No dedicated quantitative complexity metrics runner is configured; manual logic review is recorded separately and is not a metrics pass.

**Passing condition:** Route generation is current; each applicable command exits successfully; scoped Biome paths equal changed source/test paths; build and architecture validate the generated route and page imports.

### CI-05 — Changed-file coverage

**Criteria:** CA-01–CA-04

**Scope:** Every changed production Web file selected by `apps/web/scripts/check-changed-coverage.ts` and its focused Vitest tests, including the public route, Identity entrypoints, privacy page, and public-route layout.

**Checks:** The `Changed Web file coverage` workflow step runs the route and affected widget/layout test directories before enforcing per-file coverage thresholds of 85% lines/statements/functions and 80% branches.

**Passing condition:** Each eligible changed production file is present in `coverage/coverage-summary.json` and meets all configured thresholds; tests are selected explicitly in `.github/workflows/web-app-ci.yaml`.

## Manual

### VM-01 — Anonymous public journey and contact

**Type:** Manual

**Criteria:** CA-01, CA-02, CA-03, CA-04

**Tool / setup:** Playwright CLI in `apps/web`, user-started healthy Web/API services, no saved authenticated state required.

**Procedure:** Open `/privacy` directly in a fresh anonymous browser context; inspect page URL, headings, data/legal basis disclosures, provider/transfer note and distinct retention periods; tab through index and contact; inspect the contact link; open sign-in and registration and follow their privacy links. From authenticated account route, follow the privacy link.

**Passing condition:** Direct route works without redirect/private shell; content is readable; links reach `/privacy`; email address, subject and body match the contract; the UI does not claim a message was submitted or received; no console errors or unexpected API requests occur.

## Visual

### VM-02 — Policy layout at desktop and mobile

**Type:** Visual

**Criteria:** CA-05

**Reference / setup:** `design/handoff.md`, Pencil frames `w6IXZ` at 1440 px and `yJrRV` at 390 px; VM-01 page state.

**Capture / comparison:** Capture full-page screenshots with Playwright CLI into `apps/web/.playwright-cli/screenshots/` at 1440 px desktop and 390 px mobile; inspect against the reference layout. Ignore reference copy and date, which are stale; compare geometry, hierarchy, typography, colors, and responsive behavior.

**Passing condition:** Desktop uses the two-column index/reading layout and a max 1150 px container; mobile stacks index and content with 20 px side padding; typography/tokens match the handoff; no clipping/overflow; focus style remains visible.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Identity PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345), content `83001345`, v2, retrieved 2026-10-21 BRT; parent `82804737`; `RP-06/09/10/11`, `JN-11` | Identity notice, deletion disclosure, access and accessibility | Implement only public notice and current links; deletion modal does not exist | Complete read verified in task context. Jira/Confluence unchanged. |
| [Common privacy policy](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/100106241), content `100106241`, v4, retrieved 2026-10-21 BRT; parent `82804737` | Data map, retention and provider privacy decisions | Reconcile content for this task; surface retention conflict | Internal source says logs up to 30d; user chose six months for application-access records. This Spec follows Q9=A; external page remains unchanged. |
| [SHIFU-96](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-96), issue `12606` | Public page scope, mailto and entrypoints | Use exact email, subject/body and `/privacy` path | Read in full earlier in task context; no Jira update requested. |
| [SHIFU-113](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-113) and user decisions Q1–Q9 | Public facts and assumptions | Task 96 owns this notice; use user-authorized academic demonstration facts | No Jira/Confluence writes. Fictional contact identity and transfer safeguard are recorded as demonstration assumptions. |
| [LGPD](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm), [Marco Civil](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm), [ANPD Res. 18/2024](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/encarregado-completo_ocultado.pdf), [ANPD Res. 19/2024](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024), [ANPD Enunciado 1/2023](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-divulga-enunciado-sobre-o-tratamento-de-dados-pessoais-de-criancas-e-adolescentes) | Lawful bases, rights, children, DPO disclosure, application-access records and international-transfer transparency | Public text must use those distinctions and not claim consent as a universal basis or turn log retention into a general personal-data rule | Educational demonstration uses fictional controller contact/person/provider safeguards as authorized; content does not assert those operational facts were independently verified. |
| `documentation/design.md`, `documentation/rules.md`, selected Rule Pack and `documentation/tooling.md` | UI tokens, routes, widget tests, static gates | Follow selected tokens and exact scoped commands | UI, Web Routing, Widget Testing, TypeScript rules selected. |
| `design/handoff.md` and Pencil `design/shifu.pen` | Visual intent | Preserve frame layout; replace stale copy | Existing `.pen` file is read-only for this task. |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-21 | Initial contract for the public privacy notice and current Identity entrypoints | SHIFU-96, user-approved scope and Q9=A |
| 2 | 2026-10-21 | Identify Gabriela da Silva as the fictional Encarregada in the public notice | User-provided change explicitly included in the SHIFU-96 delivery |
| 3 | 2026-10-21 | Make changed-file Web coverage a named verification gate and include SHIFU-96 route/Identity/layout tests in its selection | PR #38 coverage job omitted the changed component tests, resulting in zero coverage for affected files; the gate selection is corrected and verified locally |
