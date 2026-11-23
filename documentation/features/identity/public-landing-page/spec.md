---
title: Public landing page
status: ready
revision: 1
source:
  type: issue
  ref: SHIFU-121; user goal and SHIFU-121-plano-de-implementacao.md
scope:
  - Identity public entry and landing page
last_updated_at: 2026-11-22
---

# Objective

Compact Spec for SHIFU-121. Present Shifu to visitors at `/` and guide them to registration, sign-in, or the public privacy notice. Preserve direct protected entry for active accounts and pending-confirmation handling.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Visitor / Identity | Public landing, responsive editorial composition, accurate MVP explanation, registration/sign-in/privacy links | New auth rules, account collection forms, tracking, analytics, pricing, campaigns, SEO, external content services |
| Active or pending account / Identity | Server-resolved root entry selects protected HomePage or pending confirmation before rendering | New routes, business endpoints, auth policy, migration, Inngest changes |
| Learning content | Explain diagnosis, personalized path, guided practice with correction and return, measurable progress, and consistency; identify Logic Programming as MVP; label Cooking and Languages “Em breve” | New curriculum, enrollment, availability dates, or future feature access |
| Mentor | Explain hint-led guidance, conscious AI use, and usefulness when AI is unavailable | Promises of guaranteed results or AI-dependent landing content |

RP-12 and JN-12 are fully in scope. RP-01, RP-02, RP-03, RP-07, RP-10 and RP-11 provide supporting behavior and destinations; this work does not change their contracts.

Delivery slice: Identity RP-12 and JN-12 are full. Supporting Identity outcomes are referenced only for existing registration, sign-in, pending confirmation, privacy, and accessibility contracts; no supporting outcome is changed or deferred.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | Identity RP-12, JN-12; supported by RP-02/RP-03 | `/` is public without valid access. An active valid session enters the existing protected HomePage without rendering the landing. A validated pending-confirmation context redirects to pending confirmation. Rejected/invalid/expired session context follows existing safe handling. Authentication dependency failure is not treated as anonymous access. |
| RF-02 | Identity RP-12, JN-12; supported by RP-01/RP-03/RP-11 | Landing explains Shifu and the required learning journey and Mentor behavior in direct pt-BR. Registration, sign-in, and privacy actions reach canonical existing routes. No forms collect visitor data and no private or account-dependent data is rendered. |
| RF-03 | Identity RP-12, JN-12; plan scope | Logic Programming is identified as the MVP validation case. Cooking and Languages are marked “Em breve”. Any preview is visibly labeled “Exemplo ilustrativo” and contains no real learner data or implied real results. |
| RF-04 | Identity RP-10/RP-12; design.md | Desktop and mobile layouts are keyboard usable, have visible focus and readable labels, avoid horizontal overflow at 320 px, and keep account creation visible without scrolling at 1440×900 and 390×844. Reduced motion, hidden-page pause, static fallback, and no-blur fallback are supported. |
| RF-05 | Identity RP-12; plan scope | Public rendering does not call private HomePage business queries, depend on AI/external content services, expose session tokens, emit visitor tracking, or allow session-dependent responses to be shared by cache. Authenticated home-entry publication remains limited to the valid authenticated path. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | No valid access | Visitor requests `/` | Landing is server-selected and shown without AppLayout or protected queries | CI-01, VM-01 |
| CA-02 | RF-01/RF-05 | Active valid session | User requests `/` or enters via in-app navigation | Existing HomePage and AppLayout render directly; landing never flashes; entry event is published only for authenticated root entry | CI-01, VM-01 |
| CA-03 | RF-01 | Valid, invalid, expired, or absent pending context; session rejected or auth dependency unavailable | User requests `/` | Valid pending context redirects; invalid/rejected access uses existing safe handling; dependency outage does not grant public access | CI-01, CI-02 |
| CA-04 | RF-02/RF-03 | Visitor at `/` | Reads page and follows actions | Required promise, journey, Mentor/AI explanation, MVP/future labels and illustrative label are clear; actions reach canonical register/login/privacy routes | CI-01, VM-01, VM-02 |
| CA-05 | RF-04 | Desktop, 390 px, and 320 px viewport; reduced motion and hidden document | Visitor navigates and observes the page | First-screen registration, responsive reading order, keyboard focus, no horizontal overflow, reduced motion, pause and fallbacks work | CI-01, VM-01, VM-02 |
| CA-06 | RF-05 | Public response and unavailable optional content services | Visitor requests `/` | No account data, business query, visitor tracking, AI, or external content dependency is used; session-dependent response is not shared across users | CI-01, VM-01 |

### Design Contract

| Surface / route | State / viewport | Penpot page / board / components | CA / Visual check | Allowed deviations |
| --- | --- | --- | --- | --- |
| Public `/` | Visitor, 1440×900 and 390×844; check minimum 320 px | No landing board was found in the named Shifu Penpot pages. Use existing Design System semantic tokens and local fonts; do not treat the `landing-glass` sample as a complete screen. | CA-04/CA-05 / VM-02 | Browser-reviewed composition because no matching board exists. Translucent preview surface and localized soft shadow are the ticket/plan exception to the general no-shadow hierarchy rule. |

Preserve “Dojo editorial”: dark Shifu tokens, Instrument Serif display, DM Sans body/control, jade only for learning progress, rectangular progress bars, and the existing seal action color. Concentrate glass, reflection and soft shadow in the illustrative learning preview. Do not use brass for learning progress. Keep decoration nonessential and restrained.

# Technical Contract

## Architecture Mapping

Owner: Identity. Rules: [UI Layer](../../../rules/ui-layer-rules.md), [Web App Routing](../../../rules/web-app-routing-rules.md), [Widget Testing](../../../rules/widget-testing-rules.md), [Provider Layer](../../../rules/provision-layer-rules.md), [TypeScript Conventions](../../../rules/typescript-conventions-rules.md).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Identity UI | `[N] apps/web/src/ui/identity/widgets/pages/landing-page/` | Page and feature-owned child widgets with kebab-case directories and `index.tsx`; the page hook owns document-visibility motion state. Static preview data is explicitly illustrative. |
| Create | Landing page composition | `[N] landing-page/index.tsx`, `landing-page/use-landing-page.ts`, `landing-page/hero-section/index.tsx`, `landing-page/hero-section/progress-preview/index.tsx`, `landing-page/learning-journey-section/index.tsx`, `landing-page/learning-topics-section/index.tsx`, `landing-page/mentor-section/index.tsx`, `landing-page/final-call-to-action-section/index.tsx` | Page composes one widget per visual section. Static sections and preview are pure renderers and do not receive fabricated behavior hooks. The preview is illustrative and has no fake controls. |
| Modify | Root route | `[M] apps/web/src/routes/index.tsx` | Keep `/`; consume the typed server result with `Route.useRouteContext()` and select landing or existing HomePage without client-side auth flash. |
| Modify | Root middleware | `[M] apps/web/src/middlewares/enter-main-page-middleware.ts` | Return a discriminated public/authenticated result. Redirect validated pending context; preserve safe error behavior and authenticated entry publication. |
| Modify if needed | Auth provision | `[M, conditional] apps/web/src/provision/auth/better-auth/better-auth-provider.ts` | Expose only a server-side operation that validates pending context through existing signed-cookie and stored-context checks. Never expose cookie contents or token to browser context. |
| Modify | Root layout | `[M] apps/web/src/ui/shared/widgets/layouts/root-layout/index.tsx`, `use-root-layout.ts` | Consume the same root match context as the root route. Compose public root mode without AppLayout and active root mode with AppLayout; do not classify `/` as always public by pathname. Preserve public auth routes and hydration. |
| Reuse | Shared | `apps/web/src/constants/routes.ts`; `apps/web/src/ui/shared/hooks/use-reduced-motion-preference.ts`; `apps/web/src/ui/shared/styles/global.css` | Use canonical register/login/privacy paths, motion preference boundary and existing tokens/fonts. Keep landing-only styling local. |
| Preserve | Shared home | `apps/web/src/ui/shared/widgets/pages/home-page/` | Preserve Goals and planner behavior. |
| Create | Widget tests | `[N] apps/web/src/ui/identity/widgets/pages/landing-page/tests/landing-page.test.tsx`, `tests/use-landing-page.test.ts` | Cover page content, navigation affordances, accessibility-relevant semantics and document-visibility motion behavior at owning widget boundary. |
| Create | Browser integration | `[N] apps/web/tests/identity/landing-page.test.ts` | Cover real routed visitor and controlled-auth root entry/pending states without replacing those checks with provider-owned tests. |
| Update as impacted | Layout consumers | `[M, conditional] apps/web/src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx`, `use-root-layout.test.ts`; `apps/web/tests/shared/root-layout.test.ts`; `apps/web/tests/fixtures/identity-module-fixture.ts` | Update the root mode contract and preserve existing public-route classification. Do not add provision/provider-owned tests. |

The root server result is:

```ts
export type MainPageEntry =
  | { mode: 'public' }
  | { mode: 'authenticated'; account: LayoutAccount }
```

`enterMainPageMiddleware` resolves `Promise<MainPageEntry>`. The route component and `RootLayout` read this same root route match context. Only the authenticated variant carries existing display account fields; neither variant contains a token. A validated pending context redirects before returning a result.

Expected scoped file tree:

```text
apps/web/src/ui/identity/widgets/pages/landing-page/ [N]
├── index.tsx
├── use-landing-page.ts
├── landing-page.css
├── hero-section/ [N]
│   ├── index.tsx
│   └── progress-preview/ [N]
│       └── index.tsx
├── learning-journey-section/ [N]
│   └── index.tsx
├── learning-topics-section/ [N]
│   └── index.tsx
├── mentor-section/ [N]
│   └── index.tsx
├── final-call-to-action-section/ [N]
│   └── index.tsx
└── tests/ [N]
    ├── landing-page.test.tsx
    └── use-landing-page.test.ts
apps/web/tests/identity/landing-page.test.ts [N]
apps/web/src/routes/index.tsx [M]
apps/web/src/middlewares/enter-main-page-middleware.ts [M]
apps/web/src/ui/shared/widgets/layouts/root-layout/index.tsx [M]
apps/web/src/ui/shared/widgets/layouts/root-layout/use-root-layout.ts [M]
apps/web/src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx [M, conditional]
apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts [M, conditional]
apps/web/tests/shared/root-layout.test.ts [M, conditional]
apps/web/tests/fixtures/identity-module-fixture.ts [M, conditional]
apps/web/src/provision/auth/better-auth/better-auth-provider.ts [M, conditional]
```

Do not add a public API endpoint, business rule, package, or dependency. Do not manually edit generated route metadata. Prefer CSS for slow decoration and pause it when reduced motion is requested or the page is hidden. Any animation must have a static fallback and preserve contrast. The document response for `/` in every mode must include `Cache-Control: private, no-store` so session-dependent HTML cannot enter a shared cache. Middleware decisions remain server-side; no token is serialized into route context.

## Runtime Flow

`/` invokes server middleware. The server validates current access and the pending-confirmation context using existing auth provision semantics. It checks for the pending-flow cookie by name only to avoid an unnecessary status request; its value never grants access. A valid signed and stored pending context redirects to pending confirmation even if message delivery needs attention. An invalid or expired context yields public route context. An absent or rejected session yields public route context and the landing. Identity or auth persistence failures retain the existing fail-safe error behavior and do not authorize access. The route/layout consume the same server result on initial render and hydration. Landing links use canonical route names and load only static local content.

# Verification Contract

## Shared setup

Use Web tooling from `apps/web` with pnpm. Route integration uses the controlled identity transport from the existing Playwright setup; do not treat mocks as proof of real auth persistence. The manual visitor journey uses the running local Web app at `http://127.0.0.1:7000/` after checking actual service health. Keep browser artifacts under `apps/web/.playwright-cli/{screenshots,snapshots,logs,states}/`. Never print or commit browser state. Do not stop shared Docker services; stop only task-started processes.

## Automated

### CI-01 — Root landing and auth composition

**Criteria:** CA-01 through CA-06

**Expected result:** Visitor, active, pending, rejected/expired and unavailable-auth cases produce their specified route, layout and request behavior. Required text and destinations are present. Viewports, reduced motion and visibility behavior meet RF-04; public view has no private calls or visitor tracking.

**Setup / inputs:** Use the shared Playwright factory in `apps/web/tests/playwright.ts` and Identity module fixture in `apps/web/tests/fixtures/identity-module-fixture.ts`; use the configured controlled identity transport where required. Cover visitor, active account, valid/invalid/expired pending context, rejected session, auth dependency failure, public navigation destinations, desktop/mobile/minimum widths, reduced motion, hidden visibility, content-service unavailability, and assert the root document response has `Cache-Control: private, no-store` in visitor and authenticated modes.

**Proof:** `apps/web/tests/identity/landing-page.test.ts` (planned) plus directly affected existing consumer integration selections identified from the final diff.

```powershell
pnpm exec playwright test tests/identity/landing-page.test.ts tests/shared/root-layout.test.ts
```

Working directory: `apps/web`.

**Passing condition:** Intended test cases execute and assert route URL, rendered shell, no landing flash for active accounts, requests, console, and relevant viewport/motion outcomes. Mocked cases prove only their controlled boundary.

### CI-02 — Landing and root-layout widget behavior

**Criteria:** CA-04/CA-05; root-layout regressions affecting CA-01/CA-02

**Expected result:** The landing page renders required copy, canonical action links, illustrative labeling, and responsive/motion behavior. Root-layout tests prove server-selected public/authenticated mode composes the correct shell without changing existing public-route classification or theme behavior.

**Setup / inputs:** Vitest and Testing Library in the configured jsdom environment.

**Proof:** `apps/web/src/ui/identity/widgets/pages/landing-page/tests/landing-page.test.tsx` and `use-landing-page.test.ts` (planned), `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx`, and `apps/web/src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts`.

```powershell
pnpm exec vitest run src/ui/identity/widgets/pages/landing-page/tests/landing-page.test.tsx src/ui/identity/widgets/pages/landing-page/tests/use-landing-page.test.ts src/ui/shared/widgets/layouts/root-layout/tests/root-layout.test.tsx src/ui/shared/widgets/layouts/root-layout/tests/use-root-layout.test.ts
```

Working directory: `apps/web`.

**Passing condition:** Tests execute the page composition and root-layout consumers and assert accessible user-visible outcomes and route mode; they do not mock internal static landing child widgets.

### CI-03 — Web static and production gates

**Scope:** Changed Web source, routes, layouts, auth provision and direct consumers.

**Checks:** `pnpm --filter web check:types`; `pnpm --filter web check:lint`; `pnpm --filter web check:architecture`; `pnpm --filter web build`. Lint includes configured complexity rules; report lint and complexity disposition separately. No quantitative complexity runner is declared.

**Passing condition:** All four declared gates pass with no errors or warnings. Any focused Biome command names only real changed paths.

## Manual

### VM-01 — Visitor and account entry

**Type:** Manual

**Criteria:** CA-01 through CA-04, CA-06

**Tool / setup:** Playwright CLI from `apps/web`; verify Web/API health and session state privately.

**Procedure:** Open `/` as visitor; inspect first screen and full page at 1440×900 and 390×844, then 320 px width; use keyboard through registration, sign-in and privacy; inspect requests, console and rendered state. In authenticated session, open `/` and verify direct protected HomePage with no landing flash. Inspect pending confirmation redirect where a valid local state exists.

**Passing condition:** Final URLs, visible text/shell, keyboard order/focus, no horizontal overflow, no private public requests, and no console errors match the contract. Record unavailable real-session state explicitly.

## Visual

### VM-02 — Public landing composition

**Type:** Visual

**Criteria:** CA-04/CA-05

**Reference / setup:** Shifu Design System tokens and fonts; no matching Penpot landing board exists. Browser composition reviewed at 1440×900 and 390×844, with width checked at 320 px.

**Capture / comparison:** Fresh Playwright screenshots under `.playwright-cli/screenshots/`; inspect first screen, full page, preview, focus and reduced-motion fallback. There is no matching Penpot export, so do not claim a Penpot-to-browser comparison. Measure contrast on the rendered composition, including translucency.

**Passing condition:** Required hierarchy, copy, labels, token use, contrast, responsive order, touch targets, focus and illustrative labeling are visually verified. Record the no-board limitation and any accepted deviations.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Identity PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83001345), “Shifu — PRD — Identity”, content `83001345`, version 6, parent `82804737`, updated 2026-11-20T20:00:16.502Z; retrieved 2026-11-22 21:23 BRT | RP-12/JN-12 and supporting Identity requirements | Confirmed complete page; no product amendment | No Atlassian write. |
| `SHIFU-121-plano-de-implementacao.md` | Scope, source facts, design proposal and check plan | Reconcile with actual code and current PRD during implementation | Planning input only; not a second product authority. |
| `documentation/architecture.md`, `modules.md`, `design.md`, `tooling.md`, selected Rules | Boundaries and implementation | Confirmed existing root route, Identity-owned auth provision, existing HomePage, tokens, scripts and test outputs | Recheck any scope expansion. |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-11-22 | Initial compact contract for public landing and server-resolved root entry | SHIFU-121, user goal, current Identity PRD v6, repository plan |
