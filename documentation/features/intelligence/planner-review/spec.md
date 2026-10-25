---
title: Goal Planner proposal review with graph and list views, direct edits and restart
status: draft
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-93
scope:
  - apps/web (intelligence; shared graph zoom controls)
  - documentation/features/intelligence/planner-review
last_updated_at: 2026-10-20
---

# Objective

Replace the provisional review handoff of `SHIFU-92` with the final review step of the
Planner: a validated proposal is shown on its own surface with the title and description
editable in place, the Skills and justifications read-only in a Graph (initial view) or a
List, a `Reiniciar planejamento` modal that starts a new generation through the
`SHIFU-91` restart route, `Cancelar`, and a `Criar objetivo` action that delivers the
current proposal and edits through an explicit integration contract consumed by
`SHIFU-95`. Compact mode: one route already covered by a browser suite; eight frames.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Review surface (learner) | `Revise seu objetivo`, editable title and description, `Habilidades sugeridas` header with Graph/List switcher, relation summary, restart guidance, `Cancelar`, `Reiniciar planejamento`, `Criar objetivo` | Editing Skills or justifications, adding/removing Skills |
| Graph (learner) | Read-only graph with the proposal as root and the Skills as nodes; edges only from the Curriculum relations returned by the backend; zoom controls and fit; keyboard focusable nodes | Invented connections, prerequisites, mandatory order, progress, node menus, links to Learning |
| List (learner) | Same Skills and justifications as the graph, in reading order | Reordering |
| Restart (learner) | Modal with the active intention prefilled, replacement warning, single `Iniciar planejamento` action, close by X or Esc; `POST …/restart` through a new server function; the page then shows the `SHIFU-92` processing/interview/outcome surfaces | In-place edits of the previous answers |
| Goal creation contract (system) | `PlanningGoalCreationRequest` delivered to `PlannerPage.onCreateGoal`; without a consumer the page shows a neutral notice | The confirmation call, its states and the Learning creation (`SHIFU-95`) |
| Shared | `GraphZoomControls` promoted from the Learning Goal page to `ui/shared` | Any other Learning change |

PRD coverage: `RP-09` **implemented** for the review presentation, `RP-10` **partial**
(review, direct edits and restart delivered; confirmation belongs to `SHIFU-95`), `RP-07`
**implemented** for cancel and the restart processing states, `RP-12` **implemented** for
the review surface. Journeys `JN-07`/`JN-08` (arrival), `JN-09` and `JN-12` covered up to
the confirmation.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-09, RP-10; JN-07, JN-08 | When the planning status is `proposal`, the page renders the review surface instead of the interview: title, description, every Skill with its justification, the Graph view first (desktop and mobile), the switcher, `Cancelar`, `Reiniciar planejamento` and `Criar objetivo`. No invalid proposal reaches the surface (`SHIFU-91` validation). |
| RF-02 | RP-09, RP-10 | Switching Graph/List keeps the same Skills and justifications and the current title/description edits; no request is sent. Skills and justifications have no edit, add or remove affordance. |
| RF-03 | RP-09 | The graph edges come only from `proposal.relations` (foundation → Skill) plus a root edge for Skills without a foundation in the proposal; nothing implies order or priority. Each node exposes its name and justification to assistive technology. |
| RF-04 | RP-09, RP-10 | Title and description are edited directly without any AI call; the edited title is reflected in the graph root. Empty required fields block `Criar objetivo` with a pt-BR message beside the field; edits live only in page memory. |
| RF-05 | RP-10; JN-09 | `Reiniciar planejamento` opens a modal with the active intention prefilled in an editable text area, a replacement warning and only `Iniciar planejamento`; no `Cancelar` button. |
| RF-06 | RP-10; JN-09 | Closing the modal by X or Esc keeps the proposal, the edits and the planning, and sends no request. Focus returns to the trigger. |
| RF-07 | RP-07, RP-10; JN-09 | Submitting a valid new intention posts `/intelligence/planning-sessions/{id}/restart`; the response (`202`, processing) replaces the review with the `SHIFU-92` processing surface; later states (interview, proposal, outcomes) follow the `SHIFU-92` contract; late results of the previous generation never restore the discarded proposal (backend fence + query replacement). A failed request keeps the modal open with a message. |
| RF-08 | RP-07; JN-12 | `Cancelar` on the review deletes the planning and returns to the Home; the `SHIFU-92` abandon rules (reload, direct link) apply unchanged. No Goal is created by review, edits, switching or restart. |
| RF-09 | RP-10 | `Criar objetivo` validates and delivers `{ planningId, title, description, proposal }` to the `onCreateGoal` contract; when the page has no consumer yet, a neutral notice says the creation arrives with the next delivery and nothing else happens. |
| RF-10 | RP-12 | Desktop and mobile frames are followed; tabs, fields, graph controls, dialog and actions are keyboard operable with visible focus; the List offers the same information as the Graph. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | A `proposal` planning with three Skills and one relation | The page renders | `Revise seu objetivo`, both fields prefilled, `Grafo` tab selected, graph with the root and three nodes, relation summary, three actions | CI-01 / CI-02 / VM-02 |
| CA-02 | RF-02 | The review with an edited title | The learner switches to `Lista` and back | The list shows the three names and justifications; the title field and the root node keep the edited title; no `_serverFn` call is made | CI-01 / CI-02 |
| CA-03 | RF-03 | Relations `python → automacao` | The graph renders | One edge for the relation plus root edges for the Skills without foundation; no edge for the unrelated pair | CI-01 |
| CA-04 | RF-04 | The title cleared | `Criar objetivo` | `Informe um título para o Objetivo.` appears, the contract is not called | CI-01 / CI-02 |
| CA-05 | RF-09 | Valid fields | `Criar objetivo` | The contract receives the planning id, trimmed title and description and the untouched proposal; without a consumer the notice `A criação do Objetivo chega na próxima etapa do Planejador.` is shown and no Learning request is sent | CI-01 / CI-02 |
| CA-06 | RF-05 | The review | `Reiniciar planejamento` | A dialog titled `Reiniciar planejamento` with the intention prefilled, the warning and a single `Iniciar planejamento`; focus lands in the text area | CI-01 / CI-02 / VM-02 |
| CA-07 | RF-06 | The dialog open after editing the title | Esc, then X | The dialog closes each time, the title edit is kept, no request is sent, focus returns to the trigger | CI-01 / CI-02 |
| CA-08 | RF-07 | The dialog with a new intention | `Iniciar planejamento` | `restartPlanningServer` receives `{ planningId, initialIntent }`; the page shows `Analisando seu objetivo…`; the next poll renders the new batch; the previous proposal is gone | CI-01 / CI-02 |
| CA-09 | RF-07 | The restart request fails with `409` | `Iniciar planejamento` | The dialog stays open with the conflict message; the proposal remains | CI-01 |
| CA-10 | RF-08 | The review | `Cancelar` | `DELETE` is sent and the URL becomes `/` | CI-02 |
| CA-11 | RF-10 | 390 × 844 | The review renders, tabs are operated with arrow keys, the dialog opened with Enter | No horizontal scroll; the list view is reachable by keyboard; Esc closes the dialog and focus returns | CI-02 / VM-02 |

# Technical Contract

## Architecture Mapping

Owner: `intelligence`. Rules: [UI layer](../../../rules/ui-layer-rules.md),
[widget testing](../../../rules/widget-testing-rules.md),
[web routing](../../../rules/web-app-routing-rules.md), [design](../../../design.md).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Modify | web core | `apps/web/src/core/intelligence/planning-session.ts` | `PlanningGoalCreationRequest = { planningId: string; title: string; description: string; proposal: PlanningProposal }`, `PLANNING_INTENT_MAX_LENGTH = 4000` |
| Modify | web REST | `IntelligenceService.restartPlanning(accessToken, planningId, initialIntent)` | `POST …/restart` with `{ initial_intent }`, mapped like the other planner calls |
| Create | web hooks | `useRestartPlanningAction`, `restartPlanningServer` — `apps/web/src/ui/intelligence/hooks/use-restart-planning-action.ts` | Zod input `{ planningId, initialIntent (1–4000, trimmed) }`, `withPlanningService`, mutation named `restartPlanning` |
| Create | web shared | `GraphZoomControls` — `apps/web/src/ui/shared/widgets/components/graph-zoom-controls/index.tsx` | Promoted from `goal-detail-page/goal-skill-graph/goal-graph-controls`; Learning imports the shared one |
| Delete | web UI | `apps/web/src/ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/goal-graph-controls/index.tsx` | Replaced by the shared widget |
| Create | web UI | `PlanningProposalReview` — `apps/web/src/ui/intelligence/widgets/pages/planner-page/planning-proposal-review/` | `index.tsx`, `use-planning-proposal-review.ts`, nested `proposal-skill-graph/` (`index.tsx`, `use-proposal-skill-graph.ts`, `proposal-graph-node/index.tsx`), `proposal-skill-list/index.tsx`, `restart-planning-dialog/` (`index.tsx`, `use-restart-planning-dialog.ts`) and their `tests/` |
| Delete | web UI | `planner-page/planning-proposal-handoff/` | Replaced by the review |
| Modify | web UI | `usePlannerPage`, `PlannerPage` | `onCreateGoal?` prop, `handleRestart`, `handleCreateGoal`, `isRestarting`, `restartErrorMessage`, `goalCreationNotice`; the `proposal` view renders the review keyed by `generation` inside the 1170 px column of the frames (other states keep 760 px) |
| Modify | web shared | `Icon` allowlist, `Textarea` usage | `git-fork` icon for the graph helper; review and dialog text areas without resize handle, as drawn |
| Modify | web tests | `planner-page/tests/*`, `hooks/tests/planning-server-functions.test.ts`, `tests/intelligence/planner-page.test.ts` | Review coverage, restart server function, browser scenarios CA-01 … CA-11 and the eight frame captures |
| Modify | CI | `.github/workflows/web-app-ci.yaml` | New Vitest files in the scoped coverage run |

Widget contracts:

```ts
export type PlanningProposalReviewProps = {
  planningId: string
  intent: string
  proposal: PlanningProposal
  isCancelling: boolean
  isRestarting: boolean
  restartErrorMessage: string | null
  goalCreationNotice: string | null
  onCancel: () => void
  onRestart: (initialIntent: string) => Promise<boolean>
  onCreateGoal: (request: PlanningGoalCreationRequest) => void
}
// usePlanningProposalReview → view: 'graph' | 'list'; title; description; titleError; descriptionError;
//   relationSummary; isRestartDialogOpen; restartTriggerRef; handleViewChange; handleTitleChange;
//   handleDescriptionChange; handleCreateGoal; handleOpenRestart; handleCloseRestart; handleSubmitRestart
export type ProposalSkillGraphProps = { title: string; skills: PlanningProposalSkill[]; relations: PlanningSkillRelation[] }
export type ProposalSkillListProps = { skills: PlanningProposalSkill[] }
export type RestartPlanningDialogProps = {
  isOpen: boolean; initialIntent: string; isSubmitting: boolean; errorMessage: string | null
  restoreFocusRef: RefObject<HTMLButtonElement | null>; onClose: () => void; onSubmit: (intent: string) => void
}
export type GraphZoomControlsProps = { zoom: number; canZoomIn: boolean; canZoomOut: boolean; onZoomIn: () => void; onZoomOut: () => void }
```

Expected file tree:

```text
apps/web/src/
├── core/intelligence/planning-session.ts                                   [M]
├── rest/services/intelligence-service.ts                                   [M]
├── ui/shared/widgets/components/graph-zoom-controls/index.tsx              [N]
├── ui/learning/widgets/pages/goal-detail-page/goal-skill-graph/index.tsx   [M]
├── ui/intelligence/hooks/use-restart-planning-action.ts                    [N]
├── ui/intelligence/hooks/tests/planning-server-functions.test.ts           [M]
└── ui/intelligence/widgets/pages/planner-page/
    ├── index.tsx, use-planner-page.ts                                      [M]
    ├── tests/planner-page.test.tsx, tests/use-planner-page.test.ts         [M]
    └── planning-proposal-review/
        ├── index.tsx, use-planning-proposal-review.ts                      [N]
        ├── proposal-skill-graph/{index.tsx,use-proposal-skill-graph.ts}          [N]
        ├── proposal-skill-graph/proposal-graph-node/index.tsx              [N]
        ├── proposal-skill-list/index.tsx                                   [N]
        ├── restart-planning-dialog/{index.tsx,use-restart-planning-dialog.ts} [N]
        └── tests/{planning-proposal-review.test.tsx,use-planning-proposal-review.test.ts,
                  use-proposal-skill-graph.test.ts,use-restart-planning-dialog.test.ts} [N]
apps/web/tests/intelligence/planner-page.test.ts                            [M]
documentation/features/intelligence/planner-review/{spec.md,evaluation.md,design/handoff.md,design/*.png} [N]
```

Dependency direction: `PlannerPage` → `PlanningProposalReview` (owns edits, view, dialog
state) → `ProposalSkillGraph`/`ProposalSkillList`/`RestartPlanningDialog`. The page hook
owns the restart mutation and the goal-creation contract; the review receives them as
callbacks. The graph layout runs through ELK as in Learning (vertical spacing and order inside each
layer); every layer is then centered on the widest one and the tree hangs from the top of
the box at zoom 1 when it fits. Geometry follows the box width: 360/400 px nodes with 48 px
gaps from 800 px up (desktop frame), rows shared by the Skills of a layer with 16 px gaps
below (mobile frame). Its nodes are read-only.

## Runtime Flow

Proposal arrives (`GET` or `202` body) → review mounts keyed by `generation` with the
proposal title/description as initial edits → Graph first → edits stay local → `Reiniciar
planejamento` → dialog (prefilled intent) → `Iniciar planejamento` →
`restartPlanningServer` → `POST …/restart` (`202`, `processing`, generation + 1) → page
sets the query data → `SHIFU-92` processing/interview/outcome surfaces → a new `proposal`
mounts a fresh review. `Criar objetivo` → validation → `onCreateGoal(request)` (SHIFU-95)
or the neutral notice. `Cancelar` → `DELETE` → Home.

# Verification Contract

## Shared setup

Same as `../planner-interview/spec.md`: Vitest (jsdom, `@xyflow/react` stubbed as in the
Learning Goal page test), Playwright with mocked `_serverFn` transport through the Home
composer entry, `PlanningSessionFaker.fakeProposal`.

## Automated

### CI-01 — Review widgets and page hook under Vitest

**Criteria:** CA-01 … CA-09

**Proof:** `planning-proposal-review/tests/*.test.ts(x)`, `planner-page/tests/*.test.ts(x)`,
`hooks/tests/planning-server-functions.test.ts`.

```bash
cd apps/web && pnpm exec vitest run src/ui/intelligence src/routes/intelligence
```

**Passing condition:** every case passes; changed files meet the coverage thresholds
through the scoped CI command and `check-changed-coverage.ts`.

### CI-02 — Route integration with mocked transport

**Criteria:** CA-01, CA-02, CA-04 … CA-08, CA-10, CA-11

**Proof:** `apps/web/tests/intelligence/planner-page.test.ts` (review scenarios appended).

```bash
cd apps/web && pnpm test:integration tests/intelligence/planner-page.test.ts
```

### CI-03 — Applicable baseline checks

`pnpm --dir apps/web check:lint`, `check:architecture`, `check:types`, `generate-routes`
(no diff), scoped coverage run.

## Manual

### VM-01 — Review against the real backend

Needs `OPENROUTER_API_KEY` to obtain a real proposal; without it the review is exercised
with mocked transport only (limitation).

## Visual

### VM-02 — Frames versus implementation

Eight frames (`bzItW`, `gXrEP`, `zX9Ow`, `zCbC0`, `eSaNL`, `NxoN7`, `SU4H8`, `lPCGg`)
exported at scale 1 and compared with captures from CI-02 at 1440 × 900 and 390 × 844;
deviations listed in `design/handoff.md`.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| Shifu PRD Intelligence (Confluence 83099649, v4) | RP-07, RP-09, RP-10, RP-12; JN-09, JN-12 | Restart modal without `Cancelar`, direct edits, graph/list equivalence | Unchanged intent |
| `documentation/design.md` T16, §4.3 (graph needs a list), §8 | Review screen | Confirmed | None |
| `documentation/rules/ui-layer-rules.md` (dialog header structure) | Dialog composition | The approved frame `eSaNL` has no icon tile or separator; the frame is followed and the deviation recorded | Reviewer confirmation |
| `../planner-interview/spec.md` | Review handoff boundary | `PlanningProposalHandoff` replaced by `PlanningProposalReview` as planned | Noted in its evaluation |

Decisions: `D1` the review is rendered inside the planner route (same page, separate
surface) keyed by generation; `D2` graph nodes carry no progress bar or actions menu (the
frames reuse Learning's node, a proposal has neither); `D3` one icon (`graduation-cap`) for
every Skill node because the payload has no icon; `D4` the restart dialog uses the shared
AlertDialog primitives with the frame's header (title + close) instead of the icon-tile
header; `D5` `Criar objetivo` without a consumer shows a neutral notice; `D6` the
Learning zoom controls become a shared widget drawn at 136 × 40 (32 px buttons) with an
invisible 44 px hit area to keep the mobile touch rule; `D7` the review uses the 1170 px
column of its frames while the interview and processing states keep the 760 px column of
SHIFU-92; `D8` the graph geometry depends on the box width (wide nodes from 800 px, shared
rows below) with every layer centered and the tree top-aligned, so both frames are matched
without a second layout engine; `D9` the `git-fork` helper icon drawn in the frames is the
restore control (44 px ghost button with tooltip).

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-20 | Initial contract | SHIFU-93 ticket, PRD v4, eight approved frames |
| 2 | 2026-10-20 | Decisions D6 … D9 (zoom control size, review column, graph geometry, restore control); no CSS file for the graph; `git-fork` icon added to the allowlist | Frame measurements taken during implementation (VM-02) |
| 3 | 2026-10-20 | RF-09 / CA-05 and D5 superseded: `Criar objetivo` now confirms the proposal through `../planner-confirmation/spec.md` (`PlannerPage` owns the creation; the `onCreateGoal` prop and the neutral notice are gone; the request carries a `confirmationKey`) | SHIFU-95 delivery |
