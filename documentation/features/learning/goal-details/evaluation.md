---
title: SHIFU-64 Goal detail evaluation
status: in_progress
spec: ./spec.md
spec_revision: 5
plan: ./plan.md
source: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-64
prd_content_id: 83066881
prd_version: 17
last_updated_at: 2026-09-24
---

# Evaluation status

Revision 5 animates the highlighted path's dashes and keeps them static under
reduced-motion preference. The user explicitly amended the visual treatment
during implementation; the graph topology and hover/focus scope are unchanged.

Revision 4 adds transient prerequisite-path highlighting on graph-card hover and
keyboard focus. Learning PRD `83066881` v17 was reread in full on 2026-09-24;
RP-04/RP-25 allow this presentation without changing official relations.

Revision 3 records the user-requested graph interaction: dragging empty canvas pans
the viewport, and the graph icon restores the initial fitted view with a tooltip.
Learning PRD `83066881` v17 was read in full on 2026-09-24; its new optional
introductory-material rule does not change this Goal detail slice. Existing
Revision 2 graph-interaction evidence is historical; the revision 3 pan/reset
scenario now has fresh browser evidence below.

Implementation started against Spec revision 2 after the complete authority preflight.
Learning PRD `83066881` version 16 and Curriculum PRD `83034113` version 9 were
reread on 2026-09-24. Their progress, concept, coverage and relationship updates were
reconciled without expanding this read-only Goal-details slice.

# Scope and authority checkpoint

| Check | Evidence | Status |
| --- | --- | --- |
| Spec contract | `spec.md`, revision 5, status ready | passed for this amendment |
| Product authority | Learning `83066881` v17 and Curriculum `83034113` v9; RP-04/RP-25 unchanged | passed for this amendment |
| Delivery traceability | Jira `SHIFU-64`, read-only | passed |
| Design authority | `design/manifest.md` and seven saved PNG references | passed |
| Write boundary | No Jira, Confluence or Pencil mutation | passed |
| Baseline | Branch `feat/shifu-64`; pre-existing untracked ticket/feature artifacts preserved | passed |
| Builder assignments | Server F2 and Web F3 activated with non-overlapping source/test paths | passed |

# Acceptance coverage

| Criterion | Spec coverage | Required evidence | Disposition | Status |
| --- | --- | --- | --- | --- |
| CA-01 | RF-01 | use case, controller, VM-01 | pending | pending |
| CA-02 | RF-02 | page, route, VM-02 | pending | pending |
| CA-03 | RF-03 | projection, graph/list, VM-03 | pending | pending |
| CA-04 | RF-04 | projection/status, graph/list, VM-03 | pending | pending |
| CA-05 | RF-05 | page hook and VM-03 | pending | pending |
| CA-06 | RF-06 | graph hook and VM-03 | EV-008 pan/reset/tooltip, EV-011 animated path hover/focus, and EV-012 mouse-wheel zoom passed; remaining VM-03 pending | partial |
| CA-07 | RF-07 | controller/page recovery and VM-02 | pending | pending |
| CA-08 | RF-08 | destinations and VM-04 | pending; SHIFU-65 integration gate | pending |
| CA-09 | RF-09 | widget/route accessibility and VM-03 | pending | pending |
| CA-10 | RF-10 | route migration and VM-01 | pending | pending |

# Automated gates

| CI | Command/sensor | Coverage | Result | Evidence |
| --- | --- | --- | --- | --- |
| CI-F | `cd apps/server && uv run pytest tests/learning/core/use_cases/test_get_goal_detail_use_case.py -q` | CA-01–04/07 | passed: 6 tests | EV-01 |
| CI-S | `cd apps/server && uv run pytest tests/learning/server/controllers/test_get_goal_detail_controller.py -q` | CA-01–04/07 | passed: 5 tests | EV-013 |
| CI-W | `pnpm --filter web check:lint`, `check:types`, focused Vitest and Playwright | CA-02–10 | passed: lint/types; 8 focused widget tests; 5 browser tests | EV-013 |
| CI-D | route generation, architecture, build and integrated application checks | all applicable | architecture/build passed; other integrated checks pending | EV-013 |

# Manual and visual evidence

| Evidence | Scenario/state | Viewport/reference | Observed result | Status |
| --- | --- | --- | --- | --- |
| VM-01 / EV-04 | privacy and legacy routes | runtime | pending | pending |
| VM-02 / EV-05 | loading, empty, error, recovery | runtime | pending | pending |
| VM-03 / EV-06 | graph/list, keyboard and statuses | runtime | pan/reset at desktop/mobile passed in EV-008; wheel zoom passed in EV-012; remaining scenarios pending | partial |
| VM-04 / EV-07 | real destinations | runtime / SHIFU-65 | pending | pending |
| EV-09–EV-31 | all manifest frames and supplemental states | exact manifest viewports | pending | pending |

# Review findings

| Finding | Classification | Source | Affected evidence | Status and resolution |
| --- | --- | --- | --- | --- |
| ACH-001 | authority reconciliation | PRD versions 16/9 | Spec revision 1 evidence | resolved by Spec revision 2 |
| ACH-002 | environment | Docker daemon unavailable | CI-S and full-stack/runtime evidence | resolved: Docker Compose services were running; controller suite passed 4/4 |
| ACH-003 | dependency | SHIFU-65 add-skill route absent locally and on its remote branch | CA-08 / VM-04 | resolved under explicit user authorization: created the protected `/learning/goals/$goalId/skills/add` route boundary in SHIFU-64; it does not implement SHIFU-65's mutation flow |
| ACH-004 | contract amendment | User requested graph pan/reset after revision 2 excluded dragging | CA-06 / VM-03 | resolved in Spec revision 3: canvas pans while skill nodes stay fixed; reset control gets a tooltip |
| ACH-005 | contract amendment | User requested hover path emphasis with screenshot reference | CA-06 / VM-03 | resolved in Spec revision 4: prerequisite chain highlighted temporarily on hover/focus; unrelated relations stay neutral |
| ACH-006 | visual correction | User specified that the highlighted path should move | CA-06 / VM-03 | resolved in Spec revision 5: dashed stroke animates in path direction; reduced-motion keeps it static |

# Evidence log

- `EV-001` — 2026-09-24: complete Learning and Curriculum authority reads confirmed
  current versions 16 and 9; Spec revision 2 freezes the compatible SHIFU-64 slice.
- `EV-002` — 2026-09-24: feature tree, route placeholders, services, design manifest,
  manifests and rule packs inspected before Builder activation.
- `EV-003` — 2026-09-24: F2 Server and F3 Web builders activated. Their reports are
  not acceptance evidence until the Orchestrator reviews the integrated diff and reruns
  the listed gates.
- `EV-004` — 2026-09-24: server Ruff and BasedPyright passed after correcting the
  Goal projection type narrowing; focused unit suite passed 6/6. The controller suite
  could not initialize its disposable PostgreSQL container because the local Docker
  named pipe was absent, so its four cases are not accepted as passing evidence.
- `EV-005` — 2026-09-24: web lint and strict typecheck passed; the focused Goal page,
  hook and graph Vitest suites passed 8/8. Playwright launched Vite but did not return
  a result summary, so browser evidence remains pending.
- `EV-006` — 2026-09-24: after Docker Desktop was made available, the Goal-detail
  controller suite passed 4/4 against its disposable PostgreSQL container. Server Ruff
  and BasedPyright, plus web Biome and strict TypeScript, were rerun for final code
  validation.
- `EV-007` — 2026-09-24: `origin/feat/shifu-65` was inspected and contains no
  `/learning/goals/$goalId/skills/add` route. With explicit user authorization, the
  route boundary was created in SHIFU-64 and linked from the Goal detail header and
  empty state. The route deliberately leaves SHIFU-65's selection/mutation behavior
  out of this ticket.
- `EV-008` — 2026-09-24: CodeGraph query `GoalSkillGraph ReactFlow canvas pan zoom
  controls fitView reset icon and goal detail page` located the ReactFlow owner and
  confirmed `panOnDrag` was false. Learning PRD 83066881 v17 was read in full; its
  new optional introductory-material rule is outside this Goal detail slice.
  `pnpm exec playwright test tests/learning/goal-detail-page.test.ts --reporter=line`
  passed 4/4 on the final candidate; the graph scenario verified canvas drag and
  zoom change the transform, icon click restores the desktop fit, tooltip is
  visible on hover, and mobile drag plus keyboard Enter restores the mobile fit.
  Fresh captures:
  `/tmp/shifu-goal-graph-tooltip.png`, `/tmp/shifu-goal-graph-reset.png`,
  `/tmp/shifu-goal-graph-mobile-reset.png`; inspected visually. Focused graph
  Vitest passed 2/2, `pnpm check:types` passed, and scoped Biome passed after
  formatting. No app processes were started for this validation.
- `EV-009` — 2026-09-24: visual correction requested by the user. The graph's
  existing React Flow Background now renders 1.5px dots on a 24px grid using
  the existing decorative border token. The canvas surface and page background
  are unchanged. A fresh Playwright screenshot was captured and inspected at
  `/tmp/shifu-goal-graph-subtle-background.png`; the focused pan/reset browser
  scenario passed 1/1 after the visual change.
- `EV-010` — 2026-09-24: user-requested canvas height increased from 34rem to
  40rem. Fresh Playwright captures at desktop and 390px mobile were inspected:
  `/tmp/shifu-goal-canvas-taller-desktop.png` and
  `/tmp/shifu-goal-canvas-taller-mobile.png`. The focused pan/reset browser
  scenario passed 1/1 with the taller canvas.
- `EV-011` — 2026-09-24: CodeGraph query `GoalSkillGraph ReactFlow edges nodes hover
  path highlight useGoalSkillGraph GoalGraphNode` identified the hook-owned edges,
  ReactFlow renderer, and card boundary. Learning PRD 83066881 v17 was reread in
  full. The focused Playwright case passed 1/1: hovering skill C highlighted
  both root→A→B→C and root→E→C with dashed Selo edges, left the root→D branch
  neutral, cleared on pointer exit, and highlighted again on keyboard focus.
  The animated edge CSS was confirmed in the browser and reduced-motion turned
  animation off while preserving the highlight. Screenshot captured and inspected
  at `/tmp/shifu-goal-graph-highlighted-path-branches.png`. The final Goal detail
  browser suite passed 5/5; focused graph Vitest passed 2/2, strict TypeScript
  and scoped Biome passed. One concurrent suite run timed out while waiting for
  the graph loading state; a longer graph-ready wait and serial rerun passed 5/5.
- `EV-012` — 2026-09-24: enabled React Flow wheel zoom within its existing
  25–200% limits. The focused Playwright graph scenario passed 1/1: a wheel
  movement changed the viewport transform, reverse movement changed it again,
  and the reset control restored the initial fit. The zoomed canvas screenshot
  `/tmp/shifu-goal-wheel-zoom.png` was captured and inspected. Strict TypeScript,
  scoped Biome, and `git diff --check` passed.
- `EV-013` — 2026-09-24: commit preflight on the integrated local candidate.
  Web lint, strict types, architecture and production build passed; Goal detail
  Vitest passed 8/8 and its Playwright route suite passed 5/5. The server Goal
  detail controller suite passed 5/5 against disposable PostgreSQL. Scoped Ruff,
  Ruff format and BasedPyright passed. The shared database was not reseeded.
