---
title: React code questions in learning activities
status: draft
revision: 2
mode: complete
---

# Objective

Deliver React component questions inside existing Learning activities, using the existing Curriculum question, rubric, preliminary evaluation, official attempt, recovery and history flows. Learners edit curricular files, optionally practice in an isolated WebContainer preview, create only permitted extra files, and resume drafts saved in their own browser. Preserve choice questions, JavaScript stdin questions, diagnostic behavior and existing progress rules.

# Scope

**Included:** React question and immutable attempt snapshot contracts; authoritatively validated initial/additional files; public rubric; React practice runtime; activity/editor/result presentation; browser-local draft lifecycle and cross-tab ordering; preliminary and official assessments; existing evaluation job, idempotency, recovery and historical reads; responsive and keyboard-accessible experience in pt-BR.

**Excluded:** Fastify and React+Fastify questions, standalone HTML/CSS/JS, React in diagnostic activities, arbitrary dependency/configuration editing or installs, draft synchronization to the server, a generic IDE, a second evaluation pipeline, and changes to unrelated progress/gamification business rules. SHIFU-111, SHIFU-23 and SHIFU-98 remain separate delivery scopes; this change may integrate their existing contracts but must not claim to implement them fully.

| Requirement | Product source / journey | Delivery |
| --- | --- | --- |
| RP-03 | Curriculum RP-03, JN-03 | React project and file policy from curricular content |
| RP-09, RP-11, RP-12 | Learning RP-09, RP-11, RP-12; JN-07/JN-08 | Browser draft, practice, preliminary freeze and inconclusive retry |
| RP-13, RP-14, RP-18, RP-27 | Learning; official attempt lifecycle and consumers | Existing immutable attempt, recovery, result and history pipeline |
| RP-25, RP-29 | Learning; accessibility, localization and data lifecycle | Responsive pt-BR UI, identity-scoped drafts and deletion invalidation |

# Behavior Contract

| ID | Observable requirement | Acceptance criteria | Authority |
| --- | --- | --- | --- |
| RF-01 | A Learning activity accepts React questions alongside choice and JavaScript stdin questions, preserving sequential navigation and existing consumers. | CA-01: mixed 3–5 question activity renders and advances correctly; choice, stdin and diagnostic flows retain behavior. Unknown discriminators fail closed. | RP-11, RP-25; Jira SHIFU-88 |
| RF-02 | React workspaces are constructed from curricular initial files, fixed dependencies, entrypoint, permitted commands, rubric and optional extra-file policy. | CA-02: only curricular initial files and policy-permitted additions are accepted; server rejects invalid paths, duplicate/colliding names, forbidden config/dependency files, unsupported extensions/directories/counts, payload tampering and oversized content. Canonical paths are relative POSIX paths, at most 240 characters with segments at most 64 characters, ASCII letters/digits/underscore/dot/hyphen, and no hidden segments, empty/dot/traversal segments, backslashes or NUL. Additional policy has allowed directory subtrees, allowed suffixes and `max_files` (1–32); absent policy means no additions. The submitted project source is at most 256 KiB total, matching the existing Web runner bound. Test no policy, 0 additions, exactly max, max+1, malformed paths, collisions/config files, and just-over-256-KiB totals. No rename/delete or package installation is introduced. | RP-03/JN-03; RP-11 |
| RF-03 | Optional browser practice starts with the question, updates on edits, and exposes preview/terminal status without a Run button. | CA-03: a real React project renders and hot-updates; runtime errors/unavailable browser leave editing, preliminary assessment and submission usable; process and stale preview resources are disposed. Preview is hosted on the WebContainer's distinct origin in a sandboxed frame with scripts only and no top-navigation, forms, popups or downloads; no Shifu token is passed to it. If a distinct origin and required frame restrictions cannot be confirmed, disable preview and keep editing/assessment/submission. Verify preview URL origin differs from the app origin, sandbox flags are present, auth headers/cookies are absent from preview requests, and the app remains inaccessible from learner code. | RP-11 |
| RF-04 | Editable files autosave locally, isolated by stable account identity, goal/skill experience, activity, question and curricular revision. | CA-04: same-browser logout/login restores the correct account draft; separate devices do not sync; changing goal, recreated experience, account, activity, question or revision cannot cross-load a draft. Storage failure/corruption/quota is visible and protects against silent loss. | RP-09, RP-29 |
| RF-05 | Draft updates coordinate across tabs and lifecycle changes. | CA-05: latest persisted edit wins; delayed older writes cannot overwrite it; same-origin tabs receive deletion tombstones through the existing browser lifecycle signal and cannot recreate invalidated drafts; on every new/reconnected activity session, an authoritative successful Learning activity read must validate active account/experience/revision before restore or submit. A not-found/closed/unauthorized result removes matching drafts and leaves a local tombstone; unavailable/offline validation fails closed for restore and submission, while an already open editor may retain a clearly unsaved local copy until reconnection. Logout alone preserves the draft. A disconnected browser cannot be remotely erased; on its next online validation it must purge the draft before it can be restored or sent. | RP-09, RP-29 |
| RF-06 | The question shows curricular criterion names/weights and policy-derived additional-file instructions. | CA-06: UI reflects actual criterion names/weights and actual file policy; no illustrative weight, path, extension or limit is baked into product behavior. | RP-03/JN-03, RP-11 |
| RF-07 | Preliminary assessment freezes the exact file set; inconclusive required criteria block progression and can be retried against the same frozen response. | CA-07: preliminary requests create no official attempt/progress/effects; response presents provisional score, each criterion's weight, selected level, its preconfigured comment, inconclusive state where applicable, and exact submitted files in read-only form. Inconclusive required criteria show no provisional official score and block progression; retry uses byte-identical frozen files/answers even after another tab changes its draft. Conclusive assessment may advance. | RP-11, RP-12 |
| RF-08 | Only a complete final activity submission creates the official immutable attempt, evaluated through the existing transaction/outbox/job path. | CA-08: incomplete/tampered submissions are rejected; replay is idempotent; evaluation scores all files from the submitted curricular snapshot; retry reuses the same attempt/files and applies effects once; inconclusive/failure is not converted to a final zero or partial official score. | RP-13, RP-14, RP-18 |
| RF-09 | Official results and submitted files remain viewable as read-only history after navigation and later curriculum changes. | CA-09: reloaded result uses the stored question/project/rubric snapshot and never boots a practice runtime. | RP-18, RP-27 |
| RF-10 | Interface is pt-BR, usable at desktop and mobile widths with keyboard and accessible feedback. | CA-10: desktop matches the two approved Pencil frames; mobile follows current Shifu responsive navigation/panel patterns; focus, tab order, labels and status/error announcements are usable. | RP-25; SHIFU-88 frames ZWAmr/ZQZkP |

# Technical Contract

## Architecture Mapping

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Modify/Create | Curriculum core | `apps/server/src/shifu/curriculum/core/domain/structures/{activity_question.py,react_question.py,__init__.py}`; `entities/activity.py` | Add explicit React discriminator, concept criteria, file policy and curricular validation without widening stdin rules; activity kind/rubric invariants prohibit unsupported React diagnostic use. |
| Modify/Create | Shared snapshots | `apps/server/src/shifu/shared/core/domain/structures/{curriculum_learning_activity_snapshot.py,curriculum_react_question_snapshot.py,__init__.py}` | Snapshot full question, policy, dependencies, commands and rubric for stable assessments/history; retain old snapshot decoding. |
| Modify | Curriculum provision/database | `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py`; `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py` | Map seeded/loaded content and calculate revision/concept projections for React. |
| Modify/Create | Learning core | `apps/server/src/shifu/learning/core/domain/structures/{code_answer.py,code_question_detail.py}`; `apps/server/src/shifu/learning/core/use_cases/{code_answer_validation.py,get_choice_activity_use_case.py,preview_activity_question_feedback_use_case.py,submit_choice_activity_use_case.py,evaluate_choice_activity_use_case.py,get_choice_attempt_use_case.py}` | Centralize answer/file validation for preview and final submit; keep transactional attempt/outbox/idempotency and same-attempt recovery. Reuse `CodeAnswer`/`CodeSubmittedFile`; do not execute learner code in API. |
| Modify | Learning REST | `apps/server/src/shifu/learning/rest/controllers/{get_choice_activity_controller.py,preview_activity_question_feedback_controller.py,submit_choice_activity_controller.py}` | Expose explicit React discriminator and preserve validation at HTTP boundary. Official evaluation continues through the existing job. |
| Modify | Learning persistence | `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py` | Decode React snapshots/results while preserving old choice/stdin data. Existing Inngest job and transaction/outbox path are reused unchanged; no migration is expected because snapshots are serialized JSON. |
| Modify | Web contracts/REST | `apps/web/src/core/learning/choice-activity.ts`; `apps/web/src/rest/services/learning-service.ts` | Add React question/answer/result types and explicit wire mappings; unknown kinds fail closed. |
| Modify/Create | Web runtime | `apps/web/src/core/learning/react-practice-runner.ts [new]`; `apps/web/src/provision/learning/react-webcontainer-practice-runner.ts [new]` | Provide a separately managed long-lived React dev server with fixed trusted setup, allowlisted commands, preview URL/status, hot updates, timeout/resource disposal and unavailable fallback. Do not apply stdin's short process lifecycle. |
| Modify/Create | Learning UI | `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx`; `apps/web/src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts,react-question/{index.tsx,use-react-question.ts}}`; `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/` | Compose React workspace, policy-gated add-file action, live preview, save status, preliminary read-only response and historical display. Preserve existing routes and other question types. |
| Create | Browser-local state | `apps/web/src/core/learning/react-question-draft/react-question-draft-store.ts [new]`; React activity widget | Versioned schema keyed by account + experience + activity + question + revision; validate before restore, coordinate tabs and monotonic writes, and invalidate on authoritative deletion/closure lifecycle. Never send drafts to server. |
| Create | Feature artifacts | `documentation/features/learning/react-code-question/{spec.md,evaluation.md,design/handoff.md,design/references/}` | Maintain this contract/evidence and approved visual references; do not alter historical `js-code-question` artifacts. |

### Expected file tree

```text
[new] apps/server/src/shifu/curriculum/core/domain/structures/react_question.py
[new] apps/server/src/shifu/shared/core/domain/structures/curriculum_react_question_snapshot.py
[modified] apps/server/src/shifu/curriculum/core/domain/{entities/activity.py,structures/activity_question.py,structures/__init__.py}
[modified] apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py
[modified] apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py
[modified] apps/server/src/shifu/shared/core/domain/structures/{curriculum_learning_activity_snapshot.py,__init__.py}
[new] apps/server/src/shifu/learning/core/use_cases/code_answer_validation.py
[modified] apps/server/src/shifu/learning/core/domain/structures/{code_answer.py,code_question_detail.py}
[modified] apps/server/src/shifu/learning/core/use_cases/{get_choice_activity_use_case.py,preview_activity_question_feedback_use_case.py,submit_choice_activity_use_case.py,evaluate_choice_activity_use_case.py,get_choice_attempt_use_case.py}
[modified] apps/server/src/shifu/learning/rest/controllers/{get_choice_activity_controller.py,preview_activity_question_feedback_controller.py,submit_choice_activity_controller.py}
[modified] apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py
[modified] apps/web/src/core/learning/choice-activity.ts
[new] apps/web/src/core/learning/react-practice-runner.ts
[new] apps/web/src/core/learning/react-question-draft/react-question-draft-store.ts
[new] apps/web/src/provision/learning/react-webcontainer-practice-runner.ts
[modified] apps/web/src/rest/services/learning-service.ts
[modified] apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx
[modified] apps/web/src/ui/learning/widgets/components/code-editor/index.tsx
[modified] apps/web/src/ui/learning/widgets/pages/activity-page/{index.tsx,use-activity-page.ts,question-feedback/index.tsx,question-feedback/use-question-feedback.ts}
[new] apps/web/src/ui/learning/widgets/pages/activity-page/react-question/{index.tsx,use-react-question.ts}
[modified] apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx
[new] apps/server/tests/curriculum/core/domain/test_react_question.py
[modified] apps/server/tests/learning/core/use_cases/{test_preview_activity_question_feedback_use_case.py,test_submit_choice_activity_use_case.py}
[modified] apps/server/rest-client/learning/activities.rest
[modified] apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx
[new] apps/web/src/ui/learning/widgets/pages/activity-page/react-question/tests/react-question.test.tsx
[new] apps/web/src/ui/learning/widgets/pages/activity-page/react-question/tests/use-react-question.test.tsx
[modified] documentation/features/learning/react-code-question/spec.md
[new] documentation/features/learning/react-code-question/evaluation.md
[new] documentation/features/learning/react-code-question/design/handoff.md
[new] documentation/features/learning/react-code-question/design/references/ZWAmr.png
[new] documentation/features/learning/react-code-question/design/references/ZQZkP.png
```

File-level details may vary only within the named ownership boundaries; no new REST route, migration, server-side draft table or new assessment pipeline is in scope.

## Runtime Flow

1. Curriculum supplies a discriminated React question and `additional_file_policy` (`allowed_directories`, `allowed_extensions`, `max_files`); there is no global visible file-count/extension example. Learning maps it into a client-safe detail and issues an activity revision. The browser derives a draft key using authenticated stable account identity and concrete goal/skill experience, activity and question IDs; it validates schema, revision, path policy and total 256-KiB project-source bound before restoration.
2. Edits update the local draft with a monotonic generation/write. Same-origin tabs share update and deletion tombstones; every write checks the stored generation before commit. An authoritative activity/session read gates restore, preliminary assessment and final submit. A removed experience, closed account or invalid revision deletes matching browser data and leaves a tombstone. Logout retains drafts. If a browser was disconnected during a deletion, it cannot learn the tombstone offline; it must fail closed and purge on next connection before restoration/submission. No draft is sent to the server, so offline local data cannot repopulate a deleted server record.
3. The WebContainer boots automatically for supported browsers from a constructed project, generated trusted package configuration, fixed dependencies and curricular command allowlist. Learner files execute only in a preview served from a distinct WebContainer origin. The preview iframe is sandboxed to scripts (no top navigation, forms, popups or downloads); Shifu cookies, bearer tokens and parent-window references are not exposed. If those guarantees cannot be met, disable runtime practice while keeping editing, assessment and submission. Edits mount/update files and refresh preview. Disposal terminates process/listeners and revokes stale preview state.
4. Preliminary assessment submits the complete editable initial files plus permitted additional files and revision to Learning; read-only initial files are reconstituted from the curricular snapshot. The server validates exact editable/additional paths, bounds and contents. The response is frozen and displays provisional score, criteria, selected levels/comments and files read-only. Inconclusive required criteria keep progression blocked; retry sends the identical frozen response. This path creates no attempt or effects.
5. Final full-activity submission is validated against the same policy and question revision, snapshots project/rubric and submitted files, then commits the attempt with its evaluation/outbox record using existing idempotency guarantees. The existing Inngest job invokes the existing assessment port, guards obsolete/deleted contexts and applies effects once.
6. Results and retries hydrate from the persisted snapshot. Historical UI is read-only and does not start WebContainers. Compatibility decoders continue reading existing choice/stdin attempts.

**Trust and bounds:** Server validation is authoritative. Additional directory prefixes, suffixes and count come from the Curricular policy and are schema-bounded (`max_files` 1–32); absent policy disallows all additional files. The full editable project source (initial and additional) is capped at 256 KiB across Web and Server. Paths use the canonical grammar and limits in CA-02. Reject collisions, config/lock/dependency files, disallowed extensions/directories/count, altered commands and over-limit requests. Policy data is curricular; no client field may broaden it. No arbitrary shell, user-controlled install, API-side code execution or preview from the app origin.

**Consistency:** A draft write is accepted only for its current generation/revision and without a deletion tombstone. Cross-tab messaging is an invalidation/update hint; storage and successful authoritative Learning reads are source of truth. A disconnected browser cannot receive remote deletion; it cannot restore or submit until reconnect validation and then purges a removed/closed context. Preliminary response is immutable for its retry lifecycle. Attempt + snapshot + outbox retain existing transaction boundary, submission idempotency and same-attempt retry semantics.

# Verification Contract

### Automated

#### CI-01 — Curriculum and snapshot contracts

**Type:** Automated
**Criteria:** CA-01, CA-02, CA-08, CA-09
**Command / paths:** in `apps/server`, `uv run pytest -q tests/curriculum/core/domain/test_javascript_stdin_question.py tests/curriculum/core/domain/test_react_question.py`; add exact existing `test_activity.py`/snapshot mapper paths only if those files are changed.
**Passing condition:** valid and invalid policy cases behave as specified; new snapshots round-trip; existing choice/stdin snapshots still decode; revision and rubric/project snapshot remain stable after curriculum edits.

#### CI-02 — Learning assessment and lifecycle

**Type:** Automated
**Criteria:** CA-02, CA-07, CA-08, CA-09
**Command / paths:** execute from `apps/server` after the new tests exist:

```text
uv run pytest -q tests/learning/core/use_cases/test_get_choice_activity_use_case.py tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py tests/learning/core/use_cases/test_submit_choice_activity_use_case.py tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py tests/learning/core/use_cases/test_get_choice_attempt_use_case.py tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py tests/learning/server/controllers/test_get_choice_activity_controller.py tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py tests/learning/server/controllers/test_submit_choice_activity_controller.py tests/learning/server/controllers/test_get_choice_attempt_controller.py tests/learning/server/controllers/test_retry_choice_evaluation_controller.py tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py
```
**Passing condition:** invalid/tampered/additional files fail in preview and submit; inconclusive retry is frozen; preliminary creates no attempt/effects; final submission replay, job retry and obsolete/deleted contexts preserve existing idempotency and apply effects once.

#### CI-03 — Web runtime, draft and widgets

**Type:** Automated
**Criteria:** CA-01, CA-03–CA-07, CA-09, CA-10
**Command / paths:** from repository root, use the existing Vitest selector `pnpm --filter web exec vitest run` with the paths below; add exact newly created widget test paths under the same ownership boundaries:

```text
src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx
src/ui/learning/widgets/pages/activity-page/react-question/tests/react-question.test.tsx
src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts
src/ui/learning/widgets/pages/activity-page/code-question/tests/code-question.test.tsx
src/ui/learning/widgets/pages/activity-page/code-question/tests/use-code-question.test.ts
src/ui/learning/widgets/components/code-editor/tests/code-editor.test.tsx
src/ui/learning/widgets/components/code-editor/tests/use-code-editor.test.ts
src/ui/learning/widgets/components/code-file-tree/tests/code-file-tree.test.tsx
src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx
tests/learning/activity-page.test.ts
tests/learning/choice-result-page.test.ts
```

Add widget coverage for draft restore/storage/ordering/deletion inside the existing activity widget test boundaries; do not add provider/REST adapter or query-hook-only suites.
**Passing condition:** real React preview updates automatically; unsupported/failed runtime preserves edit/assess/submit; file action obeys policy; tab storage, account/experience isolation, logout restore, ordered writes, invalidation and storage errors meet criteria; prelim/history are frozen/read-only; existing choice/stdin/diagnostic tests pass. The widget test asserts exactly `sandbox="allow-scripts"`, HTTPS and a distinct origin on the SDK's `*.webcontainer.io` or `*.webcontainer-api.io` host. Only a real browser can prove denied parent-document access or absence of credentials on preview requests; retain those observations under VM-01.

#### CI-04 — Applicable quality gates

**Type:** Automated
**Criteria:** CA-01–CA-10
**Commands:** from repository root: `pnpm --filter web check:types`, `pnpm --filter web check:lint`, `pnpm --filter web check:architecture`, `pnpm --filter web test:coverage`, `pnpm --filter web build`; from `apps/server`: `uv run poe check:types`, `uv run poe check:lint`, `uv run poe check:architecture`, `uv run poe test`, `uv run poe build`; root email checks: `pnpm --dir packages/email check:code`, `check:types`, `build`. Run only after command/runtime configuration is confirmed in Tooling.
**Passing condition:** checks complete without failure; test counts prove relevant selections executed; build artifacts match CI expectations. Server `poe test` must include real Inngest jobs with `SHIFU_RUN_REAL_INNGEST_TESTS=1`, or a separately proven full jobs run. No skip is counted as pass.

#### CI-05 — Database compatibility

**Type:** Automated
**Criteria:** CA-08, CA-09
**Setup / checks:** disposable database only; migrate to head and run `uv run alembic check` as CI does. Never reset shared Docker data.
**Passing condition:** migration/model state agrees and old JSON snapshots remain readable; if no migration is needed, record source-backed JSON compatibility evidence.

#### CI-06 — Risk-based mutation assessment

**Type:** Automated
**Criteria:** CA-02, CA-07, CA-08
**Scope / rationale:** server path admission and idempotent official effects are correctness-critical. Inspect the exact use-case diff and tests. If affected rejection/idempotency assertions do not distinguish the relevant failure cases, run configured targeted core mutation only for those production files and matching tests. If existing assertions directly distinguish them, record mutation as not required with assertion evidence. If no eligible use case changes, record not applicable.
**Passing condition:** when required, important mutants are killed or individually justified as equivalent; when not required, recorded assessment names assertions covering path rejection and effect idempotency. Report duration/survivors when run. Never run whole-package/`--all` mutation.

#### CI-07 — Complexity, types and lint dispositions

**Type:** Automated
**Criteria:** CA-01–CA-10
**Passing condition:** CI-04 provides actual changed-project type/lint checks; configured Biome/Ruff C90 complexity lint is separately recorded. Do not claim a numeric complexity metric without an installed checker.

#### CI-08 — Scoped regression and coverage reconciliation

**Type:** Automated
**Criteria:** CA-01–CA-10
**Checks:** feature tests extend existing Learning controllers/use-cases/job and Web widgets/routes; then execute the complete regressions explicitly authorized by the task plan: Web `test:coverage` (no duplicate `test:unit`), Server `poe test` including real jobs, and applicable Email gates.
**Passing condition:** full declared selections finish and report actual test counts; failures are fixed and rerun; no unrelated full suite is inferred from a partial command.

### Manual

#### VM-01 — Authenticated React activity lifecycle

**Type:** Manual
**Criteria:** CA-01–CA-09
**Tool / setup:** Playwright CLI from `apps/web`, authenticated local state or visible sign-in; local seeded account from `documentation/tooling.md`; web/API health and actual function registration verified. The complete repository seed currently contains no React question. Use only a dedicated disposable PostgreSQL database/container and a test-only fixture that constructs a 3–5 question mixed activity; record the fixture path, command, database endpoint and teardown of task-started resources before running. Never run `db:seed`, migration reset, or fixture writes against the shared Compose database. If no disposable fixture and isolated DB are available, record VM-01 Blocked and request the user to provide/approve the isolated setup rather than mutate shared data.
**Procedure:** open activity; edit JSX; add a permitted file; observe live preview and terminal; navigate away/logout and return; confirm local draft; perform preliminary assessment and inspect rubric/frozen files; finish all questions and submit; reopen result and verify stored files. Exercise keyboard/focus. Capture the preview iframe element and assert its origin differs from the app origin, scheme is HTTPS, host is the SDK's `*.webcontainer.io` or `*.webcontainer-api.io`, and `sandbox` is exactly `allow-scripts`. Observe actual preview navigation and subresource requests; retain URL and request metadata proving no `Authorization` or `Cookie` header is sent. Attempt parent-document access from the preview and record the expected cross-origin denial. Record URL, relevant requests, keyboard path and console.
**Passing condition:** observed runtime and persisted result match CA-01–CA-09; draft is local only; assessment/history use real authenticated boundaries; browser evidence records all four preview guarantees (distinct HTTPS origin, sandbox flags, no auth headers/cookies, denied parent access); no unexpected console errors or accessibility-blocking keyboard traps.

### Visual

#### VM-02 — React workspace desktop and mobile

**Type:** Visual
**Criteria:** CA-03, CA-06, CA-10
**Reference / setup:** feature-local `design/handoff.md`, `design/references/ZWAmr.png`, `ZQZkP.png`; desktop viewport 1440×900 and mobile viewport 390×844.
**Capture / comparison:** capture activity states for enunciado/preview and authorized files; inspect actual images against frames and existing mobile patterns. Compare panel hierarchy, design tokens, draft status, rubrica, permission information, focus and overflow.
**Passing condition:** desktop composition matches references within runtime data differences; mobile preserves task/editor actions with responsive panels and no horizontal page overflow. Mobile is an adaptation, not a referenced Pencil frame. Also inspect preliminary/result as functional output in VM-01 against established Learning patterns.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning) — `Shifu — PRD — Learning`, content `83066881`, v26, parent `82804737`, version updated `2026-10-05T02:11:45.152Z`; complete read `2026-10-15T00:16:41Z` | RP-09/11/12/13/14/18/25/27/29; JN-07/08 | Reconcile existing draft, attempt, assessment, result and deletion flows; do not copy PRD or update Confluence. | No external write requested; recheck version before conclusion. |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum) — `Shifu — PRD — Curriculum`, content `83034113`, v13, parent `82804737`, version updated `2026-10-04T23:01:19.677Z`; complete read `2026-10-15T00:16:41Z` | RP-03; JN-03 | Preserve curricular file/dependency/command policy and rubric as source of truth. | No external write requested; recheck version before conclusion. |
| Jira SHIFU-88, issue `12598`, parent SHIFU-10 | Bounded delivery and Pencil frames | Implement this delivery slice only; branch publication is already automated to “Fazendo”. | `https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-88`; do not mutate Jira manually. |
| `documentation/{rules,architecture,modules,tooling,design,sdd}.md`, selected Rule Packs and manifests | Boundaries, style, tool gates and workflow | Reconfirm paths/commands during implementation; update only feature artifacts unless required by findings. | Local authority; selected packs include TypeScript, Python, Core, use-case, REST/controllers, database, Provision, UI and widget testing; messaging/jobs only if changed. |
| Approved Pencil frames `ZWAmr` and `ZQZkP` | Desktop UI intent | Bundle exports and maintain token mapping; mobile is an adaptation from existing patterns. | References saved in `design/references/`; `.pen` remains unmodified. |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-14 | Initial complete contract for React activity questions, authorized by the user in chat. | SHIFU-88, current Learning/Curriculum PRDs, repo rules, and approved design discussion. |
| 2 | 2026-10-15 | Made the expected file tree exact and separated iframe DOM assertions from browser-only credential and origin-isolation evidence. | Integrated candidate paths and executable boundaries of jsdom versus real-browser security checks. |
