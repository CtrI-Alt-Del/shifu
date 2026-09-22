---
title: Learning Competency detail evaluation
status: completed
spec: ./spec.md
spec_revision: 3
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-72
prd_content_id: 83066881
prd_version: 13
last_updated_at: 2026-09-22
---

# Evaluation status

Implementation is complete against Spec revision `3`. The canonical Learning PRD
was reread in full through Atlassian Shifu MCP on 2026-09-22: content `83066881`,
title `Shifu — PRD — Learning`, status `current`, version `13`. Jira `SHIFU-72`
and the local Spec remain aligned; no amendment is opened. The design authority
is the saved handoff and ten PNG references under `design/`. The implementation
did not edit Pencil; the pre-existing `design/shifu.pen` version change from
`2.17` to `2.18` remains in the worktree as unrelated input provenance.

The baseline source gates passed before feature edits. Integrated validation used
disposable, no-volume PostgreSQL and Redis containers only; no shared Compose
volume, database, or Inngest event was reset or mutated. The full web suite is
green for the feature and existing application suites except the three known
identity handler tests that still return `503` in the pre-existing local auth
fixture. The feature controller suite and migration/seed checks pass against
disposable services. The full 16-test server integration collection passes.
The web integration limitation is isolated to the three known identity
handler tests; expected TanStack Router warnings are emitted when
contract-only child routes throw `notFound()` before their generic boundary.

# Scope and authority checkpoint

| Check | Evidence | Status |
| --- | --- | --- |
| Spec contract | `spec.md`, revision `3`, status `completed` | passed |
| Product authority | Confluence `83066881`, current version `13`, full-page read | passed |
| Delivery traceability | Jira `SHIFU-72`, read-only | passed |
| Design authority | `design/handoff.md` plus ten supplied PNGs and accepted non-focus assumption | passed |
| Write boundary | No Jira/Confluence/Pencil mutation; no sibling destination-page implementation; pre-existing Pencil diff preserved | passed |
| Runtime readiness | Disposable PostgreSQL/Redis validation services; API health `{"status":"ok","name":"Shifu API"}` | passed; services stopped after validation |

# Acceptance coverage

| Acceptance | RF coverage | Automated evidence | Runtime/manual evidence | Visual evidence | Status |
| --- | --- | --- | --- | --- | --- |
| CA-01 Private absence and safe failures | RF-01, RF-06, RF-08 | EV-F5-SERVER-CONTROLLER; EV-F5-WEB-PAGE-ROUTES | VM-03 | error desktop/mobile captures | passed |
| CA-02 Available detail and ownership boundary | RF-01, RF-02, RF-06 | EV-F5-SERVER-UNIT; EV-F5-SERVER-CONTROLLER | VM-01 | seeded desktop/mobile pair | passed |
| CA-03 Ordered Curriculum content | RF-02, RF-03 | EV-F5-SERVER-CONTROLLER | VM-01 | seeded pair | passed |
| CA-04 Focus and recommendation rules | RF-04, RF-05 | EV-F5-SERVER-UNIT; EV-F5-SERVER-CONTROLLER | VM-01, VM-05 | focus-returned desktop/mobile captures | passed |
| CA-05 Released non-focus behavior | RF-04, RF-05, RF-07 | EV-F5-WEB-UNIT; EV-F5-WEB-PAGE-ROUTES | VM-06 | non-focus desktop/mobile captures | passed |
| CA-06 Unavailable projection | RF-01, RF-08 | EV-F5-SERVER-CONTROLLER; EV-F5-WEB-PAGE-ROUTES | VM-04 | unavailable desktop/mobile captures | passed |
| CA-07 Protected routing and navigation | RF-06, RF-07, RF-08 | EV-F5-ROUTES; EV-F5-WEB-PAGE-ROUTES | VM-01, VM-04 | seeded/unavailable pairs | passed |
| CA-08 BFF/query/loading/recovery contract | RF-06, RF-08, RF-09 | EV-F5-WEB-UNIT; EV-F5-WEB-INTEGRATION | VM-02, VM-03 | loading/error desktop/mobile captures | passed |
| CA-09 Responsive accessible UI | RF-07, RF-10 | EV-F5-WEB-LINT; EV-F5-WEB-TYPES; EV-F5-WEB-INTEGRATION | VM-01–VM-06 | required desktop/mobile pairs; ACH-018 boundary | passed with ACH-018 |
| CA-10 Persistence and Goal isolation | RF-02, RF-03, RF-04, RF-10 | EV-F5-MIGRATION-UPGRADE; EV-F5-MIGRATION-DOWNGRADE; EV-F5-SERVER-CONTROLLER | VM-07 | not applicable | passed |

# Automated gate evidence

| Evidence | Command | Result |
| --- | --- | --- |
| EV-BASE-WEB-LINT | `pnpm --filter web check:lint` | passed; repository pnpm warning only |
| EV-BASE-WEB-ARCH | `pnpm --filter web check:architecture` | passed; 94 modules / 212 dependencies |
| EV-BASE-WEB-TYPES | `pnpm --filter web check:types` | passed |
| EV-BASE-WEB-UNIT | `pnpm --filter web test:unit` | passed; 10 files / 24 tests |
| EV-BASE-WEB-BUILD | `pnpm --filter web build` | passed; Vite client and SSR builds |
| EV-BASE-WEB-INTEGRATION | `pnpm --filter web test:integration` | 21 passed / 3 pre-existing identity handler failures (`503`; local auth fixture/database baseline) |
| EV-BASE-SERVER-LINT | `cd apps/server && uv run poe check:lint` | passed; Ruff clean |
| EV-BASE-SERVER-ARCH | `cd apps/server && uv run poe check:architecture` | passed |
| EV-BASE-SERVER-TYPES | `cd apps/server && uv run poe check:types` | passed; 0 errors/warnings/notes |
| EV-BASE-SERVER-UNIT | `cd apps/server && uv run poe test:unit` | passed; 8 tests |
| EV-BASE-SERVER-BUILD | `cd apps/server && uv run poe build` | passed; sdist and wheel built (existing README warning) |
| EV-BASE-SERVER-INTEGRATION | `cd apps/server && uv run poe test:integration` | baseline blocked by unavailable Redis/PostgreSQL; integrated rerun passed 13 tests with disposable services |

## Integrated candidate gates

| Evidence | Command | Result |
| --- | --- | --- |
| EV-F5-WEB-LINT | `pnpm --filter web check:lint` | passed; 125 files |
| EV-F5-WEB-ARCH | `pnpm --filter web check:architecture` | passed; 126 modules / 338 dependencies |
| EV-F5-WEB-TYPES | `pnpm --filter web check:types` | passed after route generation |
| EV-F5-WEB-UNIT | `pnpm --filter web test:unit` | passed; 21 files / 53 tests |
| EV-F5-WEB-BUILD | `pnpm --filter web build` | passed; client and SSR bundles |
| EV-F5-WEB-PAGE-ROUTES | `pnpm --filter web exec playwright test tests/learning --reporter=line` | passed; 8 protected/contract route assertions inside the owning page suites, including anonymous redirect and no-detail-request assertions |
| EV-F5-WEB-INTEGRATION | `pnpm --filter web test:integration` | 25 passed / 3 pre-existing identity handler failures (`503`); no Learning failures |
| EV-F5-ROUTES | `pnpm --filter web generate-routes` | passed; generated route tree reviewed |
| EV-F6-STRUCTURAL | Orchestrator path-map review against `spec.md`, `plan.md`, `git status`, generated route metadata, and the final tree | passed; repository rules explicitly define no executable `check:spec-implementation` command, so none was invented |
| EV-F5-SERVER-LINT | `cd apps/server && uv run poe check:lint` | passed; 480 files formatted |
| EV-F5-SERVER-ARCH | `cd apps/server && uv run poe check:architecture` | passed |
| EV-F5-SERVER-TYPES | `cd apps/server && uv run poe check:types` | passed; 0 errors/warnings/notes |
| EV-F5-SERVER-UNIT | `cd apps/server && uv run pytest tests/learning/core/use_cases/test_get_competency_detail_use_case.py` | passed; 10 tests |
| EV-F5-SERVER-CONTROLLER | `cd apps/server && uv run poe test:integration` | passed; 16 collected / 16 passed, including feature/controller and identity coverage |
| EV-F5-SERVER-BUILD | `cd apps/server && uv run poe build` | passed; sdist and wheel |
| EV-F5-MIGRATION-SYNTAX | `cd apps/server && uv run python -m py_compile migrations/versions/d72c0f4e8a31_add_learning_competency_detail_integrity.py` | passed |
| EV-F5-MIGRATION-UPGRADE | `cd apps/server && uv run poe db:upgrade head` against disposable PostgreSQL | passed through `d72c0f4e8a31`; no shared volume |
| EV-F5-MIGRATION-DOWNGRADE | `cd apps/server && uv run poe db:downgrade c4d82f1e7a30` followed by `uv run --env-file .env.local poe db:upgrade head` | passed on disposable PostgreSQL; loss boundary inspected and head reapplied |
| EV-F5-SEED | `cd apps/server && uv run poe db:seed` against disposable PostgreSQL | passed; deterministic local scenarios loaded |

Known non-blocking baseline warnings: deprecated Starlette/httpx and anyio test
client APIs, pnpm `onlyBuiltDependencies` placement, and the existing Vite chunk
size warning. These are recorded, not silently treated as feature evidence.

# Runtime and visual evidence

| Evidence group | Required artifact | Status |
| --- | --- | --- |
| VM-01 | real available focus/order/recommendation/navigation at desktop and mobile | passed; `/tmp/shifu-vm01-desktop.png` and `/tmp/shifu-vm01-mobile.png`, clean console, live RPC `200` |
| VM-02 | held-request loading at desktop and mobile | asserted transient captures `/tmp/shifu-loading-manual-1440.png` and `/tmp/shifu-loading-manual-390.png`; backend lineage not claimed (ACH-018) |
| VM-03 | private absence, recoverable error, retry and recovery | controller/page/widget suites plus asserted transient captures `/tmp/shifu-error-manual-1440.png` and `/tmp/shifu-error-manual-390.png`; backend lineage not claimed (ACH-018) |
| VM-04 | unavailable projection and safe Skill navigation | controller/page/widget/route suites plus asserted transient captures `/tmp/shifu-unavailable-manual-1440.png` and `/tmp/shifu-unavailable-manual-390.png`; backend lineage not claimed (ACH-018) |
| VM-05 | focus-returned derivation and no-write evidence | use-case no-write matrix, widget suite, controller snapshot test, and asserted transient captures `/tmp/shifu-focus-returned-manual-1440.png` and `/tmp/shifu-focus-returned-manual-390.png`; backend lineage not claimed (ACH-018) |
| VM-06 | released non-focus desktop/mobile supplemental screenshots | asserted transient captures `/tmp/shifu-non-focus-manual-1440.png` and `/tmp/shifu-non-focus-manual-390.png`; no local recommendation verified in the transient harness; backend lineage not claimed (ACH-018) |
| VM-07 | disposable migration, score round-trip, indexes, isolation, no-write evidence | passed fresh migration upgrade/seed/schema inspection plus 15-test server integration and snapshot/isolation coverage |
| Design references | fresh comparisons for `xsNI4`, `R7GgrF`, `DF05W`, `IqpIe`, `m4Swx`, `pYLj5`, `VrlNG`, `B0DSt`, `A61TJ`, `u301ZL`, plus accepted non-focus states | VM-01 plus the asserted manual state captures were inspected at the required desktop/mobile viewports; state-by-state review recorded |

# Review findings

| Finding | Source | Classification | Resolution/status |
| --- | --- | --- | --- |
| ACH-001 | Prior Confluence reader timeouts during preflight | environment/authority gate | resolved by complete current read of `83066881` v13; Spec revision remains frozen at `3` |
| ACH-002 | Implementation Reviewer: Pencil provenance was unclear | evidence/provenance | resolved; `design/shifu.pen` was pre-existing `2.17` → `2.18` worktree state, was not edited by implementation, and is now explicitly recorded as unrelated input |
| ACH-003 | Implementation Reviewer: child destination routes rendered a placeholder | conformance | resolved; both child routes now authenticate and throw TanStack Router `notFound()` from their loaders, with no placeholder component |
| ACH-004 | Implementation Reviewer: migration omitted declared uniqueness/index metadata | persistence integrity | resolved; migration now preflights SkillExperience duplicates and creates the declared Learning/Curriculum constraint and indexes, with reverse downgrade operations |
| ACH-005 | Implementation Reviewer: migration did not validate all mastered invariants | persistence integrity | resolved; migration now aborts mastered-row preservation when progress is below `85`, hard score below `80`, or `mastered_at` is absent |
| ACH-006 | Implementation Reviewer: auth middleware returned access data into route context | security boundary | resolved; protected route middleware now redirects unauthenticated requests and returns `undefined` for authenticated requests, keeping tokens out of route context |
| ACH-007 | Implementation Reviewer: mobile content titles were truncated | responsive UI | resolved; content titles now wrap with `break-words` instead of ellipsis truncation |
| ACH-008 | Implementation Reviewer: page hook bypassed the navigation wrapper | repository convention | resolved; the hook now obtains navigation through `useNavigation`, whose generic navigate function is shared by the wrapper |
| ACH-009 | Implementation Reviewer: no `check:spec-implementation` row | repository command availability | resolved as non-applicable; local create-plan/conclude-spec authorities explicitly prohibit inventing this command, and EV-F6-STRUCTURAL records the required Orchestrator path-map review instead |
| ACH-010 | Implementation Reviewer: manual VM-02–VM-06 evidence was incomplete | evidence freshness | superseded by ACH-011; fresh transient Playwright captures now cover VM-01–VM-06 at both required viewports |
| ACH-011 | Resumed Implementation Reviewer: prior VM screenshots were stale or incorrectly sized | evidence freshness | resolved; transient Playwright CLI capture regenerated VM-01–VM-06 desktop/mobile artifacts at exactly `1440×900` and `390×844` after the corrections |
| ACH-012 | Resumed Implementation Reviewer: route assertions lacked anonymous and no-detail-request coverage | route conformance | resolved; page-owned route assertions cover anonymous redirects, authenticated ordering, generic not-found, preserved IDs, and no competency-detail request for contract-only Activity routes |
| ACH-013 | Resumed Implementation Reviewer: Goal/account isolation and no-write persistence evidence was narrow | persistence evidence | resolved; controller integration now includes row-level snapshot/no-write assertions and a valid other-account Goal privacy test; fresh run reports 16 server integration tests passing |
| ACH-014 | Resumed Implementation Reviewer: mobile shell lacked persistent bottom navigation | responsive UI | resolved; AppLayout now renders a four-destination mobile bottom navigation with 44px targets, account access, safe-area padding, and reserved content space |
| ACH-015 | Resumed Implementation Reviewer: feedback surfaces were top-aligned | responsive UI | resolved; loading, private-absence, unavailable, and recoverable-error surfaces now use centered responsive compositions above the persistent mobile navigation |
| ACH-016 | Resumed Implementation Reviewer: Skill/Material route coverage remained authenticated-only | route conformance | resolved; owning page suites include anonymous Skill/Material redirects and no-detail-request assertions for Material |
| ACH-017 | Resumed Implementation Reviewer: isolation evidence lacked two valid Goal contexts and current counts were stale | persistence/evidence ledger | resolved; the other-account test now creates a valid Goal plus SkillExperience sharing the same Skill, and Evaluation/Plan counts are reconciled to 16 collected server tests (10 feature-controller cases) and 8 page-owned route assertions |
| ACH-018 | Resumed Implementation Reviewer: VM-02–VM-06 evidence did not retain a real full-stack lineage | runtime evidence | accepted limitation for this delivery; real seeded VM-01 was rerun with twelve `200` Learning responses, while VM-02–VM-06 remain fresh transient UI-state captures and are not represented as real backend evidence |
| ACH-019 | Resumed Implementation Reviewer: VM-07 evidence lacked downgrade/repeated-read/duplicate coverage | persistence evidence | resolved in source and validation; repeated reads now compare progress plus Learning table counts, duplicate SkillExperience insertion is rejected, and disposable downgrade/re-upgrade passed |
| ACH-020 | Final resumed Implementation Reviewer: no additional implementation defect; conditional GO recommended | final disposition | accepted; ACH-018 is the sole remaining evidence limitation and is explicitly carried into the delivery conformance record |
| ACH-021 | Conclusion visual review found older retained mobile captures for VM-03, VM-05, and VM-06 did not show their declared states | evidence freshness | resolved; a temporary Playwright harness asserted each semantic state before capture, regenerated the ten desktop/mobile state images, and was removed without a tracked artifact |

# Evidence log

- `EV-001` — Full canonical PRD read completed through Atlassian Shifu MCP for
  content `83066881`, version `13`; current title/status and Learning rules
  reconcile with the Spec.
- `EV-002` — Web baseline lint, architecture, types, unit, and build passed;
  integration is blocked only by unavailable PostgreSQL.
- `EV-003` — Server baseline lint, architecture, types, and unit passed;
  integration is blocked only by unavailable Redis/database services.
- `EV-004` — `docker compose ps` showed no running services; no shared service,
  volume, database, or event was reset.
- `EV-005` — F1–F5 source integration passed the available static, unit, build,
  route-generation, route, and type gates. Disposable PostgreSQL migration/seed,
  13 server integration tests, and real VM-01 desktop/mobile validation passed.
  Three pre-existing web identity handler failures remain isolated from the new
  Learning surface.
- `EV-006` — Disposable PostgreSQL upgraded through `d72c0f4e8a31`, seeded
  successfully, and was used by the integrated server controller suite; the
  disposable Redis container supported the same run. Both containers had no
  shared volume and were stopped after validation.
- `EV-007` — Real VM-01 sign-in and seeded Competency detail at 1440×900 and
  390×844 showed the seeded five-item ordered sequence, progress/focus-returned
  projection, recommendation, persistent mobile navigation, clean console output,
  and twelve successful Learning server-function responses (`200`).
- `EV-008` — `pnpm --filter web exec playwright test
  tests/runtime-evidence.manual.test.ts --workers=1 --reporter=line` ran as a
  transient Playwright CLI runtime harness and passed all 10 state captures.
  Loading, error, unavailable, focus-returned, and released non-focus DOM states
  were asserted before capture at `1440×900` and `390×844`. The harness was
  removed after capture and produced no tracked artifact.
- `EV-009` — Fresh server integration rerun collected 16 tests and passed all
  16, including row-level no-write/hard-score snapshot assertions and a valid
  other-account Goal privacy scenario. Disposable migration upgrade, seed, and
  schema-name inspection also passed.
- `EV-010` — Fresh owning-page integration rerun passed 8 route assertions, covering
  anonymous redirects for Skill, Competency, Activity, and Material; authenticated
  generic not-found ordering; preserved Competency IDs; and no detail request for
  the contract-only Activity/Material routes.
- `EV-011` — The feature controller file contains 10 passing tests, including
  repeated GET no-write/table-count snapshots and duplicate SkillExperience
  rejection. The full server integration collection is 16 tests with all 16
  passed on the current disposable service run.
- `EV-012` — Disposable PostgreSQL successfully downgraded from `d72c0f4e8a31`
  to `c4d82f1e7a30` and upgraded back to head, with seed reapplied afterward.
- `EV-013` — Current integrated candidate gates passed: web lint, architecture
  (`126` modules / `338` dependencies), types, unit (`21` files / `53` tests),
  build, route generation, server lint (`480` files), architecture, types,
  focused Learning unit tests, full server integration (`16/16`), and build.
  Web integration passed `25/28`; the three failures are the pre-existing
  identity handler `503` tests and no Learning test failed.
- `EV-014` — The final visual inspection reviewed all VM-01–VM-06 desktop/mobile
  captures after explicit state assertions. The conclusion pass corrected the
  previously stale mobile state evidence and removed the temporary harness.

# Final conformance record

- **Contract:** `documentation/features/learning/competency-detail/spec.md`,
  revision `3`, status `completed`; canonical PRD content `83066881`, version
  `13`; Jira `SHIFU-72`; no external authority was mutated.
- **Plan scope:** F1–F7 completed. Builder Core, Builder Web, and Builder Server
  owned their non-overlapping paths; the Orchestrator owned package/lockfile,
  application composition, migration, generated route metadata, integration,
  and all SDD artifacts. The complete diff was reviewed with unrelated existing
  worktree changes preserved, including the pre-existing Pencil version change.
- **Contracted implementation:** Learning owns private authorization, progress,
  focus/recommendation, isolation, and the competency-detail projection;
  Curriculum remains authoritative for hierarchy/content; the BFF, FastAPI
  route, REST artifact, migration, generated route tree, widgets, loading/error/
  unavailable states, protected child routes, and mobile navigation are present.
  No sibling destination page, automatic activity start, private-data leak, or
  read-side write was introduced.
- **Current evidence:** CA-01–CA-10 and VM-01–VM-07 are mapped above; web lint,
  types, architecture, unit, build, route, and integration gates passed; server
  lint, types, architecture, focused feature tests, migration upgrade/downgrade,
  seed, schema, duplicate-rejection, isolation, and no-write checks passed. The
  full server collection is 16/16; web integration remains 25/28 because of
  the three pre-existing identity handler `503` tests.
- **Evidence boundary:** VM-01 has retained real seeded BFF/FastAPI/PostgreSQL
  lineage and twelve successful Learning responses. VM-02–VM-06 have fresh
  asserted Playwright UI-state captures at `1440×900` and `390×844`, but no
  retained full-stack backend lineage; ACH-018 is accepted as the sole delivery
  limitation. The final Implementation Reviewer issued a conditional GO with
  no additional implementation defect.

# Builder assignments

| Builder | Owned paths | Prohibited paths | Exit |
| --- | --- | --- | --- |
| Builder Core | F2 paths in `plan.md`: Shared snapshots/interfaces and Learning Core structures/errors/use case plus focused unit test | Web, database, REST, app composition, generated artifacts, Spec/Plan/Evaluation | focused use-case test, server types, architecture |
| Builder Web | F3 paths in `plan.md`: web contracts/context, widgets/primitives, route sources and web tests | Server, migration, `routeTree.gen.ts`, app/root shared composition, Spec/Plan/Evaluation | focused web tests, types, architecture |
| Builder Server | F4 paths after Core acceptance | Core contracts, web, app composition, migration unless explicitly handed off | controller integration through `FastAPIApp.register()`, route-complete REST artifact |
| Orchestrator | package/lockfile, app/root composition, generated route metadata, migration, SDD artifacts, integration/final validation | unassigned Builder-owned paths while active | integrated gates and Evaluation |

The Plan is the sequencing ledger; this Evaluation is the evidence ledger.
Builder reports are advisory until their diffs and command results are inspected
and reproduced by the Orchestrator.
