---
title: Questão HTML, CSS e JavaScript em Atividades de aprendizagem
status: ready
revision: 1
source:
  type: direct-request
  ref: SHIFU-86-CONTEXTO.md and SHIFU-86-IMPLEMENTACAO.md
scope:
  - Curriculum
  - Learning
  - Web
last_updated_at: 2026-10-23
---

# Objective

Complete-mode feature. Add curricular HTML/CSS/JavaScript questions to existing
Learning Activities, retaining mixed question ordering and existing evaluation,
attempt and history behavior. The supplied SHIFU-86 documents are the approved
design and bounded contract for this implementation.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Curriculum content | HTML/CSS/JavaScript project, editable files, runtime commands and rubric in snapshots | Curriculum authoring UI; HTML diagnosis |
| Learner Activity | Isolated practice, local drafts, rubric preview, complete submission and history | Extra files, arbitrary shell, package installation, server/device-synced drafts |
| Evaluation | Existing rubric assessor and immutable official attempt path | Deterministic preview-based grading; new score/progress rules |
| Platform | Protected existing routes, account and experience authorization | New route, React/Fastify feature work, SHIFU-110/23 completion |

Selected product outcomes are implemented for the HTML activity slice; adjacent
requirements outside this slice remain deferred as listed in the source documents.
UI reference: Pencil `design/shifu.pen`, nodes Veyl9 and EzCt3, adapted to current
Web tokens and responsive layout.

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | Curriculum RP-03/JN-03; Learning RP-09 | Curriculum owns initial files, editability, fixed runtime, rubric and order. Learning serves HTML only in practice Activities, alongside supported question types. |
| RF-02 | Learning RP-11–14, RP-18, RP-21–22, RP-25, RP-29 | Practice is isolated and optional; local drafts are account/context/revision scoped; preview and terminal never affect grades. |
| RF-03 | Learning RP-12–14, RP-18 | Preliminary feedback and official evaluation use frozen submitted content and the current official rubric. Mandatory inconclusive results block advancement and are recoverable. |
| RF-04 | Learning RP-13, RP-18, RP-29; Identity v2 and Privacy Lifecycle v4 | Complete submission creates one immutable attempt, supports recovery/history, pauses only the affected Habilidade while evaluation is pending/failed, and cannot recreate user data after invalidation. |
| RF-05 | SHIFU-86 and visual references Veyl9/EzCt3 | Responsive pt-BR UI supports keyboard/focus and communicates practice, save and evaluation states in text. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | An authorized mixed Activity contains HTML | It is read or submitted | Curricular order, safe type handling, and no private correction data are preserved | CI-01 |
| CA-02 | RF-01 | A curricular HTML project is loaded | Files are edited/submitted | Only designated editable files are accepted; unsafe paths, extras and read-only edits are rejected | CI-01 |
| CA-03 | RF-02, RF-05 | An HTML question opens | Practice starts or fails | Preview/terminal start automatically when supported; isolated preview is optional; no Run/HTTP controls; failure leaves editing/submission available | CI-02, VM-01 |
| CA-04 | RF-02 | A learner edits a response | They revisit or use another tab | Local draft restores only for the same stable account/context/revision; latest saved generation wins; errors are visible | CI-03, VM-01 |
| CA-05 | RF-02, RF-04 | Context/revision is revoked or another tab edits | A frozen response is restored/re-evaluated | Invalid drafts are blocked/cleared; evaluated bytes remain frozen | CI-03 |
| CA-06 | RF-03 | Official rubric and valid response exist | Preliminary evaluation runs | Official criteria/weights and fixed comments are shown; preview has no official effect; inconclusive mandatory criteria block progress and retry uses identical bytes | CI-04 |
| CA-07 | RF-03, RF-04 | All Activity answers are valid | Activity is submitted or retried | One immutable attempt is created idempotently; official evaluation uses the saved snapshot; technical failure is not converted to zero | CI-05 |
| CA-08 | RF-04 | An HTML attempt is pending, failed or complete | Learner retries, starts another attempt or reopens history | Recovery reuses the attempt; only a new attempt for the affected Habilidade is paused while its evaluation is pending/failed; other Habilidades remain usable; history renders read-only without starting a runtime | CI-06, VM-01 |
| CA-09 | RF-03, RF-04 | Evaluator receives an HTML attempt | Data is invalidated or processing is delayed | Evaluator gets only required prompt/files/rubric and late work cannot recreate deleted learner data | CI-07 |
| CA-10 | RF-05 | Desktop/mobile and keyboard users open the Activity | They edit, practice and evaluate | Layout follows the design reference, has no horizontal page overflow, visible focus and accessible textual states | VM-01, VM-02 |

# Technical Contract

## Architecture Mapping

Owner: Curriculum owns canonical question and rubric; Learning owns authorization,
draft lifecycle, attempts, evaluation and history; Web owns local drafts and UI.
Rules: Python, Core, REST, Database, Provision, AI, Messaging and relevant Web
TypeScript, UI, Routing, REST and Widget Testing rules selected from `rules.md`.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Modify | Curriculum core/database/provider | `apps/server/src/shifu/curriculum/**` | Add discriminated HTML question, validate project and rubric, and round-trip the immutable curricular snapshot. |
| Modify | Shared and Learning core | `apps/server/src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py`; `apps/server/src/shifu/learning/core/**` | Carry HTML details and normalize exact editable-file responses under configured size limits; preserve rubric preview, attempt and evaluation guarantees. |
| Modify | Learning REST/database/AI | `apps/server/src/shifu/learning/rest/**`, `database/sqlalchemy/mappers/**`, `ai/learning_workflows_registry.py` | Extend existing contracts and persistence/workflow routing without new route or migration unless serialization proof requires one. |
| Modify | Web domain and REST | `apps/web/src/core/learning/choice-activity.ts`, `apps/web/src/rest/services/learning-service.ts` | Add explicit HTML question, response, feedback and result mappings; reject unknown discriminators. |
| Create / Modify | Web practice and draft | `apps/web/src/core/learning/**`; `apps/web/src/provision/learning/**` | Add restricted long-running WebContainer preview/terminal; safely reuse draft generations, tombstones and cross-tab sync while preserving React data. |
| Create / Modify | Learning widgets/routes | `apps/web/src/ui/learning/widgets/pages/activity-page/**`, `choice-result-page/**`, protected Activity route | Add HTML editor/practice/rubric UI and integrate frozen feedback, submission and read-only historical display. |

No database migration is expected; JSON snapshot, attempt and response round-trip
must prove compatibility with choice/stdin/React and existing records. Practice
must not receive authenticated app state. Official input uses configured Server
limits; WebContainer project is bounded to 256 KiB UTF-8. Paths are canonical
relative POSIX paths with existing code-project limits. Only Curriculum-approved
commands/dependencies can run; the learner cannot add files or install packages.

## Runtime Flow

Learning authenticates and authorizes the account, experience and current
curricular revision, then serves the ordered Activity snapshot. Web restores a
matching local draft only after that read succeeds. The isolated WebContainer
receives the curricular project and edits, starts only an authorized command,
and serves the preview from a separate origin in a scripts-only sandboxed
iframe. Preview failure does not block the answer. Preliminary assessment uses
the exact normalized files and freezes the result. Complete submission persists
one immutable snapshot and idempotent event; the existing Learning AgentOS
workflow evaluates it and records recoverable status/progress. History is
read-only and does not start practice. Invalidation prevents late work from
recreating deleted learner records.

# Verification Contract

## Shared setup

Use repository fixtures and declared commands from `documentation/tooling.md`.
Server controller integration uses disposable test databases. Browser checks
use Playwright CLI from `apps/web`, authenticated state kept locally, healthy
Web/API dependencies and only task-started services. Never reset shared data.

## Automated

### CI-01 — Curriculum and mixed Activity contracts

**Criteria:** CA-01–02. Add `apps/server/tests/curriculum/core/domain/test_html_css_js_question.py` (planned), extend `apps/server/tests/curriculum/core/domain/test_react_question.py` for snapshot serialization, and extend `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` plus `apps/server/tests/learning/rest/controllers/test_get_choice_activity_controller.py`. The existing `apps/server/tests/learning/rest/controllers/test_get_choice_attempt_controller.py` owns persisted ActivityMapper and attempt snapshot round-trip coverage. Cover valid/invalid projects, mixed order, unknown types, diagnosis rejection, path/file attacks and legacy choice/stdin/React round-trips.

```bash
uv run pytest -q tests/curriculum/core/domain/test_html_css_js_question.py tests/curriculum/core/domain/test_react_question.py tests/learning/core/use_cases/test_get_choice_activity_use_case.py tests/learning/rest/controllers/test_get_choice_activity_controller.py tests/learning/rest/controllers/test_get_choice_attempt_controller.py
```

Run from `apps/server`. Pass only if the selected tests execute and all contracts
and legacy types pass.

### CI-02 — WebContainer practice

**Criteria:** CA-03. New `apps/web/src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/html-css-js-question.test.tsx` and `use-html-css-js-question.test.ts` are planned. Cover restricted startup, updates, terminal, disposal, failure fallback, sandbox and size bounds at the consuming widget/hook.

```bash
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/html-css-js-question.test.tsx src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/use-html-css-js-question.test.ts
```

### CI-03 — Local drafts and concurrency

**Criteria:** CA-04–05. Extend `apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts` and the new HTML hook tests planned under `html-css-js-question/tests/`. Cover IndexedDB, two tabs, saved generations, account/revision scoping, tombstones, storage failure, React compatibility and frozen responses at consumers.

```bash
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts src/ui/learning/widgets/pages/activity-page/html-css-js-question/tests/use-html-css-js-question.test.ts
```

### CI-04 — Preliminary rubric feedback

**Criteria:** CA-06. Extend `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py`, `apps/server/tests/learning/rest/controllers/test_preview_activity_question_feedback_controller.py`, `apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx` and `apps/web/tests/learning/activity-page.test.ts`. Cover public rubric, exact frozen files, non-official effects, inconclusive blocking and identical retry.

```bash
uv run pytest -q tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/rest/controllers/test_preview_activity_question_feedback_controller.py
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx tests/learning/activity-page.test.ts
```

### CI-05 — Official submission

**Criteria:** CA-07. Extend `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py`, `test_prepare_code_activity_evaluation_use_case.py`, `test_evaluate_choice_activity_use_case.py`, `apps/server/tests/learning/rest/controllers/test_submit_choice_activity_controller.py` and `apps/server/tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py`. Cover immutable snapshot, idempotent replay, evaluation failure/recovery and exactly-once progress. The workflow test is an in-process workflow boundary; the supplied context says no registered AgentOS test suite exists.

```bash
uv run pytest -q tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_prepare_code_activity_evaluation_use_case.py tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/rest/controllers/test_submit_choice_activity_controller.py tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py
```

### CI-06 — Historical attempts

**Criteria:** CA-08. Extend `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py`, `apps/server/tests/learning/rest/controllers/test_get_choice_attempt_controller.py`, `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx` and `apps/web/tests/learning/choice-result-page.test.ts`. Cover pending/failed/completed HTML attempts, per-Habilidade pause with other Habilidades usable, read-only files/rubric and old result types.

```bash
uv run pytest -q tests/learning/core/use_cases/test_get_choice_attempt_use_case.py tests/learning/rest/controllers/test_get_choice_attempt_controller.py
pnpm --filter web exec vitest run src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx tests/learning/choice-result-page.test.ts
```

### CI-07 — Privacy and invalidation

**Criteria:** CA-09. Extend `apps/server/tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py` and the owning submit/evaluation use-case tests named in CI-05. Prove minimal evaluator input and delayed work after account/context invalidation at these existing consumer boundaries; the context reports no registered AgentOS integration suite.

```bash
uv run pytest -q tests/learning/ai/workflows/test_evaluate_code_activity_workflow.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py
```

### CI-08 — Scoped project gates

Run affected Web type, lint, architecture and build checks and Server type,
lint, architecture and build checks, plus focused tests. Record complexity lint
separately from quantitative metrics; no dedicated metrics tool is configured.
Use `pnpm --filter web check:types`, `check:lint`, `check:architecture`,
`build`; from `apps/server`, `uv run poe check:types`, `check:lint`,
`check:architecture`, `build`.

## Manual

### VM-01 — Authenticated mixed Activity

**Type:** Manual. **Criteria:** CA-03–09. Use Playwright CLI and a real
authenticated Activity. Edit allowed files, inspect preview and terminal, test
draft recovery across logout/login and two tabs, evaluate, submit, revisit result
and inspect requests, URL and console. Verify isolated iframe origin and sandbox.

## Visual

### VM-02 — Desktop and mobile Activity

**Type:** Visual. **Criteria:** CA-10. Capture 1440×900 and 390×844; compare to
Veyl9/EzCt3 and inspect responsive layout, keyboard focus and overflow.

See [`design/handoff.md`](design/handoff.md) for required states, viewports,
references and accepted adaptations.

## Baseline static checks

Type, lint/format and configured complexity lint are required for affected Web
and Server projects. Record separate evidence entries. Quantitative complexity
metrics are unavailable and must be reported as such, not passed implicitly.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| Learning PRD, content 83066881 v26, retrieved 2026-10-23 per supplied context | Learning RP-09, 11–14, 18, 21–22, 25, 29 | Implement scoped HTML journey | No external write; authority research supplied in context document |
| Curriculum PRD, content 83034113 v13, retrieved 2026-10-23 per supplied context | Curriculum RP-03/JN-03 | Implement curricular project/rubric projection | No external write; authority research supplied in context document |
| Identity PRD, content 83001345 v2; Privacy Lifecycle Policy, content 100106241 v4; retrieved 2026-10-23 per supplied context | Active account identity, deletion and no late data recreation | Preserve existing ownership/invalidation boundaries only | No new Identity behavior; source metadata per supplied context |
| SHIFU-86-CONTEXTO.md and SHIFU-86-IMPLEMENTACAO.md | Task scope, CAs, design and checks | This Spec derives its bounded contract from both | User-directed; no Jira/Confluence refresh |
| Repository Architecture, Modules, Rules, Tooling and SDD | Ownership, code boundaries, checkers and delivery | Reconcile implementation and Evaluation | Local authoritative guidance |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-23 | Initial bounded complete contract | User-directed SHIFU-86 implementation documents |
