---
title: Learning Activity JavaScript stdin questions
status: completed
revision: 15
source:
  type: direct-request
  ref: "2026-09-26 user requests: Pencil lZDH7, mixed Activities, resizable panels, and immediate JavaScript output before stdin; 2026-09-27 request to remove remaining supplemental manual evidence gates for conclusion"
scope:
  - apps/server/src/shifu/curriculum
  - apps/server/src/shifu/learning
  - apps/server/src/shifu/intelligence
  - apps/server/src/shifu/shared/core
  - apps/server/src/shifu/shared/database/seed_data.py
  - apps/web
  - documentation/features/learning/js-code-question
last_updated_at: 2026-09-27
---

# 1. Context and scope

## Objective and authority

Deliver the Learning Activity **JavaScript program with standard input and
output** question represented by Pencil node `lZDH7`. A learner edits the
Curriculum project's initial files, practices through a real xterm.js terminal
backed by a browser WebContainer, sees provisional rubric feedback and submits
the whole Activity for an immutable official assessment. An Activity can mix
this code kind with existing single-choice and multiple-selection questions.
This is a **complete** Spec: Curriculum owns content/rubrics; Learning owns
attempts, scores, Concept evidence and progress; an Intelligence Jev provider supplies
bounded rubric decisions. It crosses REST, PostgreSQL, Inngest and responsive web UI.

The complete canonical [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB)
(content ID `83034113`, v12, updated 2026-09-26 12:26:31 UTC) and
[Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB)
(content ID `83066881`, v22, updated 2026-09-26 22:41:45 UTC) were retrieved
and reread 2026-09-26 22:43 UTC. The user's narrowed requests are the delivery source.
[SHIFU-75](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-75) is
background context: its Python/public-hidden-test/Execute-button description
predates both PRDs and conflicts with this scope. Learning PRD v22 was updated
with the user's explicit approval; this task does not update Jira.

## Current behavior and product gap

The shipped Activity route and HTTP operations accept only choice questions.
Curriculum's `CodeQuestion` still stores a starter string and deterministic
cases; its qualitative criterion lacks fixed level/comment choices. The
Curriculum provider marks only complete choice Activities executable.
Learning's attempt JSON can hold a legacy single-string `CodeAnswer`, but
the official evaluator, result DTO and web widgets are choice-only. No
WebContainer or xterm.js dependency is installed. JavaScript stdin and mixed
Activities therefore are not available through the current Learning flow.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Content | Released 3–5 question Learning Activities mixing existing choice and JavaScript stdin, fixed project/rubric | Other code types, diagnosis, authoring UI, package installation/config edits |
| Flow | Provisional feedback for every question, final-only official attempt, immutable results | Persisted partial attempt, cross-device resume, frontend-code autosave for stdin, editing prior question |
| Practice | Monaco editor, browser WebContainer, xterm.js, immediate run with empty stdin until input exists, then automatic rerun with last stdin | Execute button, official deterministic tests, server execution, preview/HTTP panel |
| Evaluation | AI picks fixed code-rubric decisions; Learning scores mixed answers and Concept evidence | Generated free-text feedback, provisional progress, Gamification delivery |
| UI | Desktop/mobile code question and result, adjustable desktop panel widths, read-only assessed files | New recommendation logic/presentation, generic IDE features or a new history-list route |

| Source requirement | Delivery | Notes |
| --- | --- | --- |
| Curriculum RP-03/JN-03 | partial | Stdin project/rubric and mixed choice compatibility; other code kinds deferred. |
| Learning RP-09/JN-07 | partial | Sequential provisional feedback and final-only immutable attempt on this Activity slice. |
| Learning RP-11/RP-12 | partial | Browser practice and preliminary/official rubric assessment for stdin code. |
| Learning RP-13/RP-14 | partial | One official score/effect and failure recovery for mixed Activities. |
| Learning RP-18/RP-25/RP-27/JN-08 | partial | Code result details, Concept evidence and accessible recovery on this surface; new recommendation behavior is deferred. |

| Product decision | Contract |
| --- | --- |
| Supported kinds | `javascript_stdin` is the only new code kind; choice kinds may appear in any position. An Activity with another code kind is unavailable in this slice. |
| Attempt timing | Opening, typing, practicing and requesting preliminary feedback create no attempt or progress. Only complete final submission does. |
| Provisional feedback | After requesting it, the assessed answer is frozen in the current UI. Conclusive feedback allows only forward navigation; mandatory inconclusive code feedback blocks advance and offers reevaluation of that same answer. It can differ from later official assessment. |
| Local state | Browser autosave in RP-09 applies to frontend code, not stdin code. Leaving warns that unsent stdin source/answers may be lost. |
| Repetition | A completed Activity may be repeated as a new full attempt; no question is redone in the current pass. |
| Widget ownership | The mixed Activity page is `ActivityPage`; `ChoiceQuestion` and `CodeQuestion` are sibling widgets under `activity-page`. The public Activity URL is unchanged. |
| Workspace resizing | The user's 2026-09-26 screenshot/request adds two desktop splitters for the prompt/files, editor and terminal columns. Widths are local to the open question, preserve editor/terminal state, and do not appear in the single-column mobile layout. |
| Practice before stdin | Learning RP-11/JN-07 v22 and the user's 2026-09-26 request require the current JavaScript entrypoint to run on load and after edits with empty stdin until the learner supplies input. Output independent of stdin appears immediately; the terminal still invites input. Subsequent edits use the last supplied input. No Execute button is added. |
| Recommendation | This delivery does not create or change next-Material/Activity recommendation logic or presentation. Existing result-page recommendation behavior is preserved where currently returned; the new frames focus on the result content and omit that separate block. New RP-17/RP-18 guidance is a later slice. |

# 2. Implementation Contract

## Functional requirements

| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | Curriculum RP-03/JN-03; Learning RP-09 | Present a released 3–5 question Learning Activity in Curriculum order with only supported choice/stdin kinds; show difficulty, position, total and progress without leaking correct choice keys or private rubric data. |
| RF-02 | Curriculum RP-03; Learning RP-11 | Show the stdin question's fixed initial project in an editor/file tree; only Curriculum-designated initial files are editable, and this kind cannot add files or change dependencies/configuration. |
| RF-03 | Learning RP-11/JN-07 v22; user xterm.js and immediate-output decisions | In a supported browser, run the current JavaScript entrypoint on load and after edits with empty stdin until the learner supplies input; display output independent of stdin immediately while still inviting input. After input, rerun with the latest stdin after edits. Show boot/stdout/stderr/errors in a real interactive xterm.js Terminal tab. Only Curriculum-permitted commands run. |
| RF-04 | Learning RP-09/RP-11/RP-12 | Show clearly provisional feedback after each valid choice/code answer. For code show the provisional weighted score, criterion weights/levels/fixed comments and read-only assessed files. No preliminary action creates an attempt. |
| RF-05 | Learning RP-12/JN-07 | A mandatory inconclusive code criterion yields no provisional score, blocks advance and permits reevaluation of the same frozen answer. A Shifu failure is recoverable, never learner score zero. |
| RF-06 | Learning RP-09/JN-07 | Keep a forward-only in-browser sequence, require one valid answer per 3–5 questions and offer final Activity submission after the last preliminary result. Warn before leaving with unsent work. |
| RF-07 | Learning RP-09/RP-13 | Final submission atomically stores one account-owned immutable Activity attempt and pending evaluation, then starts official assessment without a second user action; replay cannot duplicate it. |
| RF-08 | Curriculum RP-03; Learning RP-11–RP-13/RP-27 | Official code assessment uses saved source/rubric, with AI selecting only defined level IDs or inconclusive. Learning validates decisions, maps each level to its saved fixed comment/observation ID, calculates criterion/question/Activity weights and applies Concept evidence separately. Practice output never grades. |
| RF-09 | Learning RP-13/RP-14/JN-08 | After final submission, show pending/failed/complete states for the separate official assessment; preserve the same source/attempt on official failure or mandatory inconclusive, allow reevaluation of that saved answer, and apply one coherent progress effect once. Question-level provisional failures recover before submission. |
| RF-10 | Learning RP-18/RP-25; approved result-page interaction | Lead with the official Activity score and progress effect. Show ordered question summaries with details initially collapsed; the learner can expand any number independently. Expanded code details show rubric and read-only submitted files; choice disclosure remains protected. Use accessible responsive pt-BR behavior. Preserve existing next-step presentation when Learning supplies it; do not add a new recommendation contract. |
| RF-11 | Learning RP-11/JN-07; 2026-09-26 direct user request: resizable panels | On desktop (at least 1024px), let the learner adjust the widths of the prompt/files, editor and terminal panels with pointer or keyboard. Keep all three usable without losing source, terminal output or focus; retain the single-column mobile composition. |

## Acceptance criteria

| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01/02 | Eligible content | Owned, released 3–5 choice/stdin Activity with valid rubric | Learner opens it | Correct order, progress and editable initial-file tree appear; private grading data stays server-side | Controller/widget/VM-01 |
| CA-02 | RF-01/02 | Invalid content | Unsupported kind, invalid rubric/weights, missing entrypoint, duplicate or unsafe paths | Learner opens it | Activity is unavailable, with no partial misleading sequence | Curriculum/HTTP/VM-06 |
| CA-03 | RF-03 | Automatic practice | Compatible isolated browser/project with exact permitted `node` entrypoint command | Learner opens a code question, enters stdin or edits | The allowlisted entrypoint runs on load and each edit with empty stdin before first input, showing input-independent output and an input prompt; after input, edits reuse the latest stdin. If the exact command is absent, practice fails closed without spawning a process. xterm.js shows output/errors; stale run output cannot replace latest; no Execute action | Browser/VM-02 |
| CA-04 | RF-03/06 | Degraded practice | WebContainer boot fails or browser unsupported | Learner edits/submits | Practice-unavailable text appears, but editing and assessment continue; no false zero | Browser/VM-03 |
| CA-05 | RF-04/05 | Provisional result | Valid choice/code answer | Learner requests assessment | No attempt/progress/outbox exists; safe fixed choice explanation or code rubric/read-only source appears | Unit/controller/DB/VM-04 |
| CA-06 | RF-05/06 | Inconclusive/sequence | Mandatory code criterion inconclusive | Learner sees result | No score/Next appears; same frozen source may be reevaluated; conclusive result advances once with no prior edit | Unit/widget/VM-04 |
| CA-07 | RF-06/07 | Complete idempotent submit | All answers valid, one stable key | Learner submits/retries transport | One immutable attempt, pending evaluation/outbox; matching replay returns it, conflicting replay rejects | Unit/controller/DB/VM-05 |
| CA-08 | RF-07 | Access/concurrency | Anonymous/other account, wrong hierarchy, unresolved same-Skill evaluation or concurrent submit | GET/preliminary/POST/retry | Safe 401/404/409/422; no cross-account source leak or duplicate effect | Controller/DB/VM-06 |
| CA-09 | RF-08 | Official grade | Mixed answers and unequal part/criterion weights | Job completes | Choice exact-set 0/100 plus allowed code levels produce weighted Activity score; fixed comments and independent Concept evidence match saved rubric | Unit/job/VM-05 |
| CA-10 | RF-08/09 | No false zero | User syntax/runtime error, mandatory inconclusive, invalid AI output or provider failure | Official run | User error is rubric-assessed; inconclusive/technical failure has no final score/effect and retries same source | Unit/job/VM-07 |
| CA-11 | RF-09 | Once-only result | Duplicate/stale job after retry | Result applies | One official effect; no extra attempt/evidence/progress/mastery/recommendation update | Job/DB/VM-07 |
| CA-12 | RF-09/10 | Durable result | Learner leaves/returns during run or retries failure | Result route loads | Persisted pending/failed/completed state and read-only source return; same-Skill new attempt paused until resolution | Controller/browser/VM-07 |
| CA-13 | RF-10 | Official details | Authorized completed attempt | Learner opens result and expands multiple questions | Official score/progress precede ordered collapsed summaries; each summary shows position/type/title/score, multiple may remain open, code exposes rubric and read-only submitted files, choice disclosure stays protected, and any existing recommendation remains available | Controller/widget/VM-05 |
| CA-14 | RF-01–RF-10 | Inclusive UI | Desktop/mobile, keyboard/AT | Learner completes flow and reviews result | Tabs/editor/terminal/independent question disclosures/actions have labels, focus and announced expanded state; state not color-only; no clipped action/horizontal page overflow | Widget/browser/VM-01–VM-05 |
| CA-15 | RF-11 | Resizable desktop panels | Code question at desktop width (at least 1024px) | Learner drags each divider or uses arrow keys while it has focus | Adjacent panel widths change within usable limits (sidebar 220px, editor 280px, terminal 240px minimum when space allows); separator name/value/focus are accessible; editing and terminal state survive; the mobile stack has no resize controls or horizontal overflow | Widget/browser/VM-02 |

## Design Contract

The [saved handoff](./design/handoff.md) is the feature-local visual authority.
`lZDH7` specifies the contiguous enunciado/arquivos/editor/terminal workspace
at 1440 × 900. `O070h` specifies the stdin preliminary-result hierarchy,
read-only `main.js` and rubric treatment. `oPNtH` specifies the default
completed mixed-result state: official score and progress first, then collapsed
question summaries. `Qxidv` shows all three summaries open in a 1440 × 1400
full-page specimen; the 1440 × 900 runtime viewport scrolls through the details.
The result frames focus on the newly specified result content. They omit the
existing recommendation block without requiring its removal from runtime.
The existing
[choice handoff](../activity-choice-questions/design/handoff.md) governs
expanded choice details and their disclosure. At 390 × 844 use one accessible
column, collapsible enunciado/file tree and a separate Terminal tab; desktop
split must not force horizontal page scrolling. Loading, unavailable,
inconclusive, pending, failed and official states use text/live status. Fresh
desktop/mobile Playwright captures document the retained states; exact
side-by-side comparison remains required for retained visual scenarios, while
the VIS-02/VIS-05 comparisons are supplemental under revision 15.
The supplied 2026-09-26 screenshot adds subtle vertical resize handles between
the three desktop panels. The saved `lZDH7` frame remains the default-width
reference; resizing changes only local workspace geometry, not question state.

# 3. Technical Contract

## Current technical state

| Evidence | Current responsibility | Gap |
| --- | --- | --- |
| `apps/server/src/shifu/curriculum/core/domain/structures/code_question.py`, `qualitative_criterion.py`, `database/sqlalchemy/mappers/activity_mapper.py` | Legacy string source/cases and generic qualitative criteria in JSON | No fixed project, stdin discriminator or level/comment catalog |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py`, `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Choice-only full snapshot and release eligibility | Cannot project a mixed Activity |
| `apps/server/src/shifu/learning/core/use_cases/{get,submit,evaluate}_choice_activity_use_case.py` | Choice-only read, final submit and evaluation | No provisional endpoint or code/Concept branch |
| `apps/server/src/shifu/learning/core/domain/entities/activity_attempt.py`, `database/sqlalchemy/mappers/activity_attempt_mapper.py` | Immutable JSON answers/snapshot and scoped submission key | Legacy `CodeAnswer` is one string; mixed snapshot cannot hydrate |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_evaluation_mapper.py`, `messaging/inngest/jobs/evaluate_choice_activity_job.py` | Choice result and durable official job | Old case-based code result; no AI rubric branch |
| `apps/web/src/core/learning/choice-activity.ts`, `rest/services/learning-service.ts`, choice Activity/result widgets | Choice-only transport and routed UI | No project files, xterm.js or mixed/provisional rendering |
| `apps/web/package.json`, `apps/web/vite.config.ts` | No practice packages or isolation headers | WebContainer cannot start |

CodeGraph exploration of `CodeQuestion`/`ActivityMapper`, the Learning submit
and job path, and the web service/page established these call paths. The code
is baseline evidence; the cited PRDs govern new behavior.

## Dependencies

| Boundary | Dependency | Current state | Required role and constraint |
| --- | --- | --- | --- |
| Web editor | `@monaco-editor/react` | Not in `apps/web/package.json`; add through the root pnpm workspace and lockfile | Monaco-backed editable project files and read-only submitted files; the editor does not execute or grade code. |
| Browser practice | `@webcontainer/api` | Not installed; add to web dependencies and root lockfile | Run the fixed Curriculum project in a supported browser; practice is optional for assessment. |
| Terminal | `@xterm/xterm`, `@xterm/addon-fit` | Not installed; add to web dependencies and root lockfile | Render the real terminal and fit it to its tab; input reaches only the active permitted practice process. |
| Official AI assessment | Jev 1.13 through OpenRouter Decisions API | The typed HTTP provider is not yet implemented; `httpx` is present transitively but is not a direct server dependency | An Intelligence-owned Jev provider implements a Shared core port over immutable Curriculum snapshots, wraps OpenRouter `POST /api/alpha/decisions` with Pydantic transport validation and returns bounded decisions; declare `httpx` as a direct dependency. Neither `typesafe-sdk` nor Agno is required for this assessment. Provider failure remains inconclusive or retryable, never a learner score of zero. |
| Durable submission and evaluation | Existing PostgreSQL, outbox and Inngest job infrastructure | Already in the server runtime | Persist the final attempt and run official evaluation once; no new database or queue product is introduced. |
| Browser delivery | WebContainer-compatible isolation headers in local development and a supported browser | Local development configuration must be verified | Allow practice to boot locally; unsupported delivery still permits editing and assessment. Production hosting, HTTPS, and commercial-use licensing are outside this feature Spec. |
| Question project | Curriculum-defined `fixed_dependencies` and permitted commands | New content contract; supplied per published question | Mount only approved project packages and commands inside WebContainer. The learner cannot install packages or alter project configuration. |

Install versions must be selected against the current manifests during
implementation and recorded in the appropriate lockfile; this Spec does not
claim that an uninstalled package or deployed browser capability already works.

## Runtime decisions and crossing contracts

| Decision | Contract and guarantee |
| --- | --- |
| Content | Add discriminated `javascript_stdin` with Curriculum-owned initial files/paths, editable flags, entrypoint, fixed dependencies and permitted practice commands. No additional files for this kind. Rubric criteria have stable keys, weights, required flags, fixed comments for 0/25/50/75/100 and inconclusive; one required correctness/adherence criterion. Separate Concept rubrics have their own levels, examples, interpretation limits and inconclusive outcome. Validate paths, unique keys and 100% criterion/part totals. |
| Snapshot | A versioned mixed Activity snapshot preserves ordered questions, private correct choice keys, full code rubric and Concept criteria. GET projects safe public fields; final attempt stores the private snapshot so later content edits do not change official history. Old choice snapshots remain readable. |
| Preliminary HTTP | Authenticated `POST /learning/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}/questions/{question_key}/preliminary-evaluations` accepts one discriminated answer and the GET revision, returning `status`, optional `score`, safe fixed feedback and code criterion selections. It reads the published Curriculum snapshot, writes no attempt/evaluation/outbox/progress and returns no attempt ID. It is not authorization for official submission. |
| Final HTTP | Existing `POST .../activities/{activity_id}/attempts` accepts one discriminated answer per ordered question, the GET revision and a stable submission key. Learning checks an existing account/Skill-scoped key against its saved answers first; identical replay returns the original attempt even if Curriculum changed. For a new key, Learning checks revision/current publication and the complete 3–5 answer set, then atomically stores immutable answers/snapshot, pending evaluation and one outbox event. Changed content returns safe 409 without a partial attempt. |
| Official job | A short read transaction loads the saved attempt/snapshot and active evaluation `run_id`; the transaction closes before the bounded provider call. Learning scores choice exact sets, calls the shared `CodeRubricAssessorProvider` port for code and validates returned criterion/Concept keys and levels. A new transaction locks/rechecks the same active run, maps fixed comments, computes weighted question/Activity scores and Concept evidence, and commits one final evaluation/effect/outbox update. Stale runs discard results. On failure/inconclusive, the saved attempt stays intact without a final score; retry starts a new run and may reassess all parts because no partial checkpoint is promised. Duplicate runs cannot apply a second effect. |
| AI | Intelligence owns one `JevCodeRubricAssessorProvider` provider using a server-owned `httpx` client, Pydantic transport models, pinned `typesafe/jev-1.13`, and OpenRouter's Decisions API. It implements the shared `CodeRubricAssessorProvider` core port for Learning and future diagnostic consumers. The port takes one immutable, provider-neutral `CodeRubricAssessmentInput` assembled from saved Curriculum snapshots and submitted files, not Curriculum/Learning entities or repositories. All code question kinds use the same decision implementation: prompt, project files and saved rubric/Concept criteria vary; `question_kind` supplies context but does not dispatch to another assessor. Each saved criterion becomes a closed-set `choice` question with only its fixed level IDs and `inconclusive` available. Learning maps chosen IDs to saved comments/observations and computes weights; the provider owns no grading, authorization or progress rule. Neither TypeSafe SDK nor Agno is involved. No free feedback text, arbitrary model ID or browser rubric has authority. No submitted code runs inside FastAPI or the AI provider. Missing/invalid model decisions become inconclusive or typed failure, never zero. |
| Browser | `CodeEditor` uses `@monaco-editor/react` in editable and read-only modes. A client-only `CodePracticeRunner` core contract is implemented in web provision with `@webcontainer/api` and injected at the route composition boundary. One WebContainer instance per browser tab is booted and reused across the question lifecycle, then torn down on exit. It mounts the fixed project and starts only the exact Curriculum-allowlisted `node` entrypoint with zero stdin bytes supplied on load. Every startup, edit and terminal-input run checks that exact command first and fails closed without a process if it is absent. Each edit supersedes the prior run and starts the current source with no supplied input until the first learner input; afterward edits reuse the last supplied stdin. The no-input run shows output independent of stdin and then invites input; if the WebContainer pseudoterminal leaves an input-dependent process waiting at the 10-second bound, stop that process and keep the terminal in its waiting-input state, then start a fresh run when input arrives. A real `@xterm/xterm` Terminal with `@xterm/addon-fit` sends stdin to the allowlisted practice program and renders stdout/stderr/status. There is no Execute button, separate command line or unrestricted shell. Superseded processes/listeners are disposed. Initial practice bounds: 10 seconds per program run, 1 MiB terminal output per run and 256 KiB total editable source; crossing a bound stops only practice and shows a recoverable message, except the expected no-input wait state. CPU and memory remain browser-managed under the approved Architecture rule; no unsupported quota guarantee is claimed. Source is never sent to a Shifu execution endpoint. |
| Unsupported runtime | Probe browser/isolation availability; show a practice-only failure while keeping edit/submit available. Verify WebContainer-compatible COOP/COEP in Vite dev/preview. Production host configuration, HTTPS verification, and commercial-use licensing are deployment concerns outside this feature Spec and are not release acceptance criteria here. |
| Persistence | Existing JSON attempt/evaluation columns and scoped unique index suffice; no Alembic schema change. Mappers need explicit new discriminators and backward-compatible legacy choice/case hydration; historic evaluations are not regraded. |

The [WebContainers API](https://webcontainers.io/api) documents the
single-instance/process lifecycle; the [header guide](https://webcontainers.io/guides/configuring-headers)
defines deployment isolation requirements. The
The [OpenRouter Decisions API reference](https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request)
documents the `POST /api/alpha/decisions` request and typed `choice` response.
The provider sends `typesafe/jev-1.13` with a server-side OpenRouter key,
validates the transport payload with Pydantic and maps selected option IDs to
the Shared core result. This API path does not use chat completions.

| Boundary | Producer → consumer | Canonical payload and ownership | Failure/consistency |
| --- | --- | --- | --- |
| Curriculum provider | Curriculum DB → Learning | Immutable mixed private snapshot; public GET projection excludes choice correctness/hidden rubric details | Missing/unsupported content fails closed |
| Preliminary REST | Browser → Learning → Intelligence Jev provider through Shared port if code | Single answer; fixed provisional criterion/result DTO; no persisted attempt | Shifu failure is retryable on same frozen answer; stale browser response ignored |
| Final REST/outbox | Browser → Learning DB → Inngest | Complete answers, key, saved snapshot, attempt/run IDs | Atomic pending row/event, account scope, idempotent replay |
| Official assessment | Inngest → Learning use case → Shared port → Intelligence Jev provider | Saved source/rubric, typed fixed decisions | Read transaction, remote call outside lock, then guarded `run_id` commit; retry same attempt |
| Practice | Editor → WebContainer → xterm.js | Only Curriculum files/permitted commands, last stdin and transient output | Client disposal, output bound, unsupported-browser fallback; no grade input |

Account identity comes from authentication, never the body. The browser
freezes the exact requested preliminary source and rejects an older response;
the server rechecks all final answers because provisional feedback is not a
durable authorization. Raw source, prompts, terminal content and credentials
must not enter logs/error responses. Authorized account-owned result reads are
the only disclosure path for submitted source.

The mixed GET projects `activity_revision` (a digest of the complete current
snapshot) and ordered `questions` with `kind`, `key`, prompt and public display
fields. A code question exposes its fixed project, editable paths, entrypoint,
fixed dependencies, permitted commands and rubric criterion names/weights; correct choice keys,
rubric examples/level comments and Concept scoring remain private until their
allowed result disclosure. Both preliminary and final requests carry that
revision. Each code answer is `{kind: "javascript_stdin", question_key,
files: [{path, content}]}` with exactly the designated editable paths; the
server uses Curriculum's immutable noneditable files. The preliminary code
response contains each criterion key, weight, selected level or `inconclusive`,
fixed comment and optional provisional score. The official result adds the
saved read-only files, Activity score and Learning progress effect. Server
limits for HTTP payload and AI work are typed configuration values; the
implementation must record their chosen values and rejection tests before
this Contract is marked implemented.

The resulting domain schemas below name the fields introduced or changed by
this slice. Existing choice/legacy fields remain as declared in their current
structures. `ActivityEvaluation` retains its current
`id/attempt_id/status/parts/started_at/score/failure_code/completed_at/
effect_applied_at/run_id/progress_before/progress_after/status_before/
status_after` fields. Decimal percentages are in `[0, 100]`; stored
collections are immutable tuples.

| Structure/entity | Resulting fields and invariants |
| --- | --- |
| `JavascriptStdinQuestion` | `key: str`, `kind: javascript_stdin`, `prompt: str`, `initial_files: tuple[{path: str, content: str, editable: bool}]`, `entrypoint: str`, `fixed_dependencies: tuple[{name: str, version: str}]`, `permitted_commands: tuple[{id: str, executable: str, arguments: tuple[str, ...]}]`, `concept_criteria: tuple[CodeConceptCriterion, ...]`; nonempty unique safe relative paths, entrypoint included, no learner-created paths or package/config edits. |
| `CodeRubricCriterion` | `key: str`, `name: str`, `description: str`, `weight_percentage: int`, `required: bool`, `fixed_comments: tuple[{id: str, level: 0/25/50/75/100, text: str}, ...]`, `inconclusive_comment: {id: str, text: str}`; unique complete level catalog, bounded nonempty comments and one mandatory correctness/adherence criterion per code part. |
| `CodeConceptCriterion` | `concept_id: str`, `description: str`, `level_observations: tuple[{id: str, level: 0/25/50/75/100, evidence: str, interpretation_limit: str}, ...]`, `inconclusive_observation: {id: str, text: str}`; Concept IDs belong to the owning Competency and have a complete fixed catalog. |
| `CodeRubricEvaluationPart` | `question_key: str`, `weight_percentage: int`, `criteria: tuple[CodeRubricCriterion, ...]`; unique criterion keys, criteria total 100%, all Activity part weights total 100%. |
| Shared Curriculum snapshots | `CurriculumLearningActivitySnapshot`: `id: str`, `competency_id: str`, `difficulty: str`, `title: str`, `questions: tuple[choice or stdin snapshot, ...]`, `parts: tuple[choice or code part snapshot, ...]`, `required_concept_ids: tuple[str, ...]`, `activity_type: str`, `schema_version: int`, `revision: str`; `CurriculumJavascriptStdinQuestionSnapshot`: `key/kind/prompt/initial_files/entrypoint/fixed_dependencies/permitted_commands/concept_criteria` with `kind = javascript_stdin`. Criterion/part snapshots carry the same named fields and invariants as their Curriculum originals. Private rubric examples, fixed comments and correct choice keys stay out of public GET. |
| `CodeAnswer` and `ActivityAttempt` | Legacy `CodeAnswer(question_key, source_code)` remains readable; new tagged code answer is `question_key: str`, `files: tuple[{path: str, content: str}, ...]` with exactly the question's editable paths and no `source_code`. `ActivityAttempt` retains `id/skill_experience_id/competency_id/activity_id/kind/answers/submitted_at/submission_key`; `grading_snapshot` expands to the old choice or new mixed snapshot union and is immutable after submit. |
| `CodeRubricResult` | `question_key: str`, `score: Decimal or None`, `criterion_results: tuple[{key: str, level: 0/25/50/75/100/inconclusive, comment_id: str}, ...]`, `concept_observations: tuple[{concept_id: str, level: 0/25/50/75/100/inconclusive, observation_id: str}, ...]`; one entry per saved rubric item, no free model feedback, null score if a required criterion is inconclusive. |
| `CodeRubricAssessmentInput` | Shared immutable value: `question_kind: str`, `prompt: str`, `project_files: tuple[(path: str, content: str), ...]`, `submitted_paths: tuple[str, ...]`, `rubric_criteria: tuple[CurriculumCodeRubricCriterionSnapshot, ...]`, `concept_criteria: tuple[CurriculumCodeConceptCriterionSnapshot, ...]`; the complete effective project is assembled from the saved initial project plus submitted editable files, and `submitted_paths` identifies learner-authored content. `question_kind` describes context and never selects a different assessor. Learning accepts only `javascript_stdin` in this Spec and constructs this input after validating the saved snapshot; later code kinds provide their own validated project mapping and criteria to the same port. No grade, account data, mutable provider payload or free-form metadata. |
| `CodeRubricDecisions` | Shared immutable value: `criterion_levels: tuple[{key: str, level: 0/25/50/75/100/inconclusive}, ...]`, `concept_levels: tuple[{concept_id: str, level: 0/25/50/75/100/inconclusive}, ...]`; no score, comment text, confidence-as-grade, provider payload or learning state. |
| `ChoiceActivityDetail` and `CodeQuestionDetail` | Activity detail retains `activity_id/title/difficulty/can_submit/latest_attempt_id/unresolved_attempt_id/is_diagnostic`, adds `activity_revision: str` and widens `questions` to choice or code details. A code detail has `key/kind/prompt/initial_files/entrypoint/editable_paths/fixed_dependencies/permitted_commands` plus public criterion keys/names/weights; dependency names/versions are the Curriculum-fixed browser practice project, with no learner configuration edit; no private grading examples or choice answer keys. |
| `ChoiceAttemptDetail` and `CodeResultDetail` | Attempt detail retains `attempt_id/activity_id/status/submitted_at/retry_allowed/score/failure_message/progress_before/progress_after/status_before/status_after/next_action` and widens `questions` to choice or code results. A code result has `question_key/prompt/submitted_files/score/criterion_results/concept_observations`; submitted files are read-only and only shown to the owning account. |

The new shared
`CodeRubricAssessorProvider.assess(request: CodeRubricAssessmentInput) -> CodeRubricDecisions`
port accepts one immutable, provider-neutral assessment input assembled by Learning
from the saved question, rubric part and submitted files;
it returns typed fixed rubric keys/levels and Concept observations or the existing
Shared `ServiceUnavailableError`. Intelligence's `JevCodeRubricAssessorProvider` implements that port
under `intelligence/providers` without importing Learning or Curriculum. It
uses OpenRouter's Decisions API and validates every returned question key and
selected option before crossing the port. Learning translates the failure to
its existing `EvaluationUnavailableError` and alone decides scores, comments,
Concept evidence and progress. A separate Shared core structure defines the
decision result. The `PreviewActivityQuestionFeedbackUseCase`'s
`execute(account_id, goal_id, skill_id, competency_id, activity_id,
question_key, activity_revision, answer) -> PreliminaryQuestionResult`
performs scoped reads and no writes. The web `CodePracticeRunner` exposes
`start(project)`, `updateFile(path, content)`, `sendStdin(text)`,
`subscribe(listener)` and `dispose()`;
the provision adapter owns WebContainer processes, output ordering and cleanup.

## Affected layers and paths

Paths are repository-relative. Existing Activity/result URLs stay stable; the
choice-named implementation may be renamed consistently within its existing
boundary, but there must be one Activity endpoint and one official evaluator.
Every new structure is exported through its owning package initializer; the
table names all source boundaries, with tests specified in section 4.

| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| `ActivityPage` | Page | Existing Activity index route | Sibling `ChoiceQuestion` and `CodeQuestion` widgets, `QuestionFeedback` | Ordered safe questions, source state, preliminary and final actions | `use-activity-page.ts` |
| `ChoiceQuestion` | Component | `ActivityPage` | Existing choice controls | Choice options and selection state | Parent page hook |
| `CodeQuestion` | Component | `ActivityPage` | `CodeEditor`, `CodeTerminal`, two `PanelResizeHandle` instances on desktop | Fixed project/editable paths, stdin, practice status, frozen mode and local panel widths | `use-code-question.ts` |
| `PanelResizeHandle` | Pure component | `CodeQuestion` | Accessible vertical separator | Pointer drag, keyboard resize and visible focus; hidden in mobile stack | Parent question hook |
| `CodeEditor` | Shared Learning component | `CodeQuestion` or result detail | Monaco editor, file tree and source tabs | File map, allowed editable paths, selected path, read-only flag | `use-code-editor.ts` |
| `CodeTerminal` | Component | `CodeQuestion` | xterm.js mount and accessible transcript | Practice status/output and permitted input callbacks | `use-code-terminal.ts` |
| `QuestionFeedback` | Pure component | `ActivityPage` | Fixed criterion/choice details and action | Provisional state, score or inconclusive, next/final action | Parent page hook |
| `ChoiceResultPage` | Page | Existing attempt index route | Independent question disclosures, existing result detail and `CodeEditor` | Official score/progress first; all completed-question details initially closed and independently expandable; existing recommendation behavior preserved; retry only for post-submit failure | `use-choice-result-page.ts` |

Expected widget tree after moving the existing choice page and its nested
choice widget into the type-neutral Activity page:

```text
apps/web/src/ui/learning/widgets/
├── components/code-editor/
│   ├── index.tsx
│   ├── use-code-editor.ts
│   └── tests/
│       ├── code-editor.test.tsx
│       └── use-code-editor.test.ts
└── pages/activity-page/
    ├── index.tsx
    ├── use-activity-page.ts
    ├── tests/
    │   ├── activity-page.test.tsx
    │   └── use-activity-page.test.ts
    ├── choice-question/
    │   ├── index.tsx
    │   ├── choice-question.css
    │   └── tests/choice-question.test.tsx
    ├── code-question/
    │   ├── index.tsx
    │   ├── use-code-question.ts
    │   ├── code-question.css
    │   ├── tests/code-question.test.tsx
    │   ├── tests/use-code-question.test.ts
    │   ├── panel-resize-handle/index.tsx
    │   └── code-terminal/
    │       ├── index.tsx
    │       ├── use-code-terminal.ts
    │       └── tests/
    │           ├── code-terminal.test.tsx
    │           └── use-code-terminal.test.ts
    └── question-feedback/index.tsx
```

| Decision | Chosen approach | Alternative considered | Reason | Accepted trade-off |
| --- | --- | --- | --- | --- |
| Preliminary feedback | Authenticated stateless HTTP request | Partial server attempt | RP-09 creates an attempt only at final submit | Unsent sequence is lost when browser state is lost |
| Mixed Activity | Extend existing Activity/result route and evaluator | Parallel code-only route | One Activity has one ordered 3–5 question contract | Choice-facing files need careful compatibility changes |
| Activity page ownership | Move the existing choice page to `activity-page` and render choice/code question widgets as siblings | Keep a mixed Activity under `choice-activity-page` | The page owns the Activity sequence, not a particular question kind | Update route imports and colocated tests without changing the URL |
| Practice | WebContainer behind web provision contract plus xterm.js | Run learner code on FastAPI | Architecture/browser-practice authority and no server execution | Unsupported browsers edit/submit without practice |
| Official retry | Reassess saved answer in a new run | Persist per-part checkpoints | Existing `ActivityEvaluation.retry()` clears parts; correctness and simple recovery first | Repeated AI cost; no duplicate official effect |
| Content drift | Revision check for new submit, but replay key checked first | Silently use edited current rubric | Preserve the exact content shown and idempotent committed replay | User may need to reopen after a Curriculum change |

| Application/layer/path | Change | Declaration/operation and guarantee |
| --- | --- | --- |
| `apps/server/src/shifu/curriculum/core/domain/structures/javascript_stdin_question.py` | Create | `JavascriptStdinQuestion`: prompt, safe initial files/entrypoint, editable paths, practice configuration and Concept criteria. |
| `apps/server/src/shifu/curriculum/core/domain/structures/code_rubric_criterion.py` | Create | `CodeRubricCriterion`: key, required flag, weight, fixed levels/comments and inconclusive. |
| `apps/server/src/shifu/curriculum/core/domain/structures/code_concept_criterion.py` | Create | `CodeConceptCriterion`: Concept ID, observations for five levels, examples/limits and inconclusive semantics independent of question grade. |
| `apps/server/src/shifu/curriculum/core/domain/structures/code_rubric_evaluation_part.py` | Create | `CodeRubricEvaluationPart`: question key/part weight and complete criterion set. |
| `apps/server/src/shifu/curriculum/core/domain/structures/activity_question.py` | Modify | Add new discriminated unions/exports without deleting legacy kinds. |
| `apps/server/src/shifu/curriculum/core/domain/structures/evaluation_part.py` | Modify | Add new discriminated unions/exports without deleting legacy kinds. |
| `apps/server/src/shifu/curriculum/core/domain/structures/__init__.py` | Modify | Add new discriminated unions/exports without deleting legacy kinds. |
| `apps/server/src/shifu/curriculum/core/domain/entities/activity.py` | Modify | Enforce new-kind key/rubric/Concept invariants while allowing legacy rows to hydrate; provider enforces 3–5 released Learning questions. |
| `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py` | Modify | JSON round trip for new kind and legacy deserialization. |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_learning_activity_snapshot.py` | Create | `CurriculumLearningActivitySnapshot`: ordered immutable mixed questions, public/private fields and revision discriminator. |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_javascript_stdin_question_snapshot.py` | Create | `CurriculumJavascriptStdinQuestionSnapshot`: immutable project and rubric input for one question; one core structure per file. |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_code_rubric_criterion_snapshot.py` | Create | `CurriculumCodeRubricCriterionSnapshot`: criterion key, required flag, weight and exact level/comment table. |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_code_concept_criterion_snapshot.py` | Create | `CurriculumCodeConceptCriterionSnapshot`: Concept ID, levels/examples/limits and inconclusive observation. |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_code_rubric_part_snapshot.py` | Create | `CurriculumCodeRubricPartSnapshot`: question key/Activity weight and criterion tuple. |
| `apps/server/src/shifu/shared/core/domain/structures/code_rubric_assessment_input.py` | Create | Immutable normalized question kind, prompt, complete effective project files, submitted paths and saved rubric/Concept criteria; only stdin is produced by this Spec, and kind does not dispatch assessment implementations. |
| `apps/server/src/shifu/shared/core/domain/structures/code_rubric_decisions.py` | Create | Immutable provider-neutral criterion/Concept key and level decisions; no grade, comment text, HTTP or model metadata. |
| `apps/server/src/shifu/shared/database/seed_data.py` | Modify | Add one fixed mixed JavaScript stdin Activity to the existing local development learner's Goal/Skill/Competency sequence for manual persisted-browser evidence; this is development fixture content, not official released Curriculum content. |
| `apps/server/src/shifu/shared/core/domain/structures/__init__.py` | Modify | Export new snapshots, `CodeRubricAssessmentInput` and `CodeRubricDecisions`. |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py` | Modify | `get_learning_activity`; retain `get_choice_activity` for legacy/diagnostic consumers. |
| `apps/server/src/shifu/shared/core/interfaces/code_rubric_assessor_provider.py` | Create | Shared `CodeRubricAssessorProvider.assess(request: CodeRubricAssessmentInput)` protocol returning `CodeRubricDecisions` or existing Shared `ServiceUnavailableError`; no Learning, Intelligence, SDK or HTTP import. |
| `apps/server/src/shifu/shared/core/interfaces/__init__.py` | Modify | Export the shared assessor port. |
| `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Modify | Build complete eligible mixed snapshot and fail closed on unsupported content. |
| `apps/server/src/shifu/learning/core/domain/structures/code_answer.py` | Modify | New answers carry files by path; hydrate historic `source_code` unchanged. |
| `apps/server/src/shifu/learning/core/domain/structures/activity_answer.py` | Modify | New answers carry files by path; hydrate historic `source_code` unchanged. |
| `apps/server/src/shifu/learning/core/domain/structures/code_rubric_result.py` | Create | `CodeRubricResult`: fixed decisions, optional weighted score and distinct Concept observations. |
| `apps/server/src/shifu/learning/core/domain/structures/evaluation_part_result.py` | Modify | Add `CodeRubricResult` to the explicit evaluation-part union without reinterpreting legacy case results. |
| `apps/server/src/shifu/learning/core/domain/structures/__init__.py` | Modify | Export the new result and preliminary/mixed structures used at the Learning boundary. |
| `apps/server/src/shifu/learning/core/domain/structures/choice_activity_detail.py` | Modify | Public discriminated choice/code Activity projection. |
| `apps/server/src/shifu/learning/core/domain/structures/code_question_detail.py` | Create | Public stdin question projection includes fixed dependency names/versions, permitted commands and safe rubric names/weights; excludes private criteria/comment catalogs. |
| `apps/server/src/shifu/learning/core/domain/structures/choice_attempt_detail.py` | Modify | Widen official question details to choice/code while retaining pending/failed fields. |
| `apps/server/src/shifu/learning/core/domain/structures/code_result_detail.py` | Create | Account-owned read-only submitted files, fixed rubric decisions and Concept observations. |
| `apps/server/src/shifu/learning/core/domain/entities/activity_attempt.py` | Modify | Preserve complete mixed immutable answers and private grading snapshot; no partial attempt. |
| `apps/server/src/shifu/learning/core/domain/entities/activity_evaluation.py` | Modify | Preserve one pending/failed/completed official state, run identity and once-only effect; retry may clear prior parts. |
| `apps/server/src/shifu/learning/core/use_cases/preview_activity_question_feedback_use_case.py` | Create | Scoped read plus stateless choice/code feedback; no repository writes. |
| `apps/server/src/shifu/learning/core/use_cases/__init__.py` | Modify | Export the feedback-preview use case for controller registration. |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_activity_use_case.py` | Modify | Mixed read/submit/score/result/retry, saved rubric and existing choice behavior. |
| `apps/server/src/shifu/learning/core/use_cases/submit_choice_activity_use_case.py` | Modify | Mixed read/submit/score/result/retry, saved rubric and existing choice behavior. |
| `apps/server/src/shifu/learning/core/use_cases/evaluate_choice_activity_use_case.py` | Modify | Mixed read/submit/score/result/retry, saved rubric and existing choice behavior. |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_attempt_use_case.py` | Modify | Mixed read/submit/score/result/retry, saved rubric and existing choice behavior. |
| `apps/server/src/shifu/learning/core/use_cases/retry_choice_evaluation_use_case.py` | Modify | Mixed read/submit/score/result/retry, saved rubric and existing choice behavior. |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py` | Modify | Tagged new snapshot/answer/result and legacy compatibility; existing models/indexes stay. |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_evaluation_mapper.py` | Modify | Tagged new snapshot/answer/result and legacy compatibility; existing models/indexes stay. |
| `apps/server/src/shifu/learning/rest/controllers/preview_activity_question_feedback_controller.py` | Create | Authenticated provisional-feedback POST, safe schema/errors and no persistence. |
| `apps/server/src/shifu/learning/rest/controllers/get_choice_activity_controller.py` | Modify | Discriminated transport, private result, idempotent final submit and controller export. |
| `apps/server/src/shifu/learning/rest/controllers/submit_choice_activity_controller.py` | Modify | Discriminated transport, private result, idempotent final submit and controller export. |
| `apps/server/src/shifu/learning/rest/controllers/get_choice_attempt_controller.py` | Modify | Discriminated transport, private result, idempotent final submit and controller export. |
| `apps/server/src/shifu/learning/rest/controllers/retry_choice_evaluation_controller.py` | Modify | Discriminated transport, private result, idempotent final submit and controller export. |
| `apps/server/src/shifu/learning/rest/controllers/__init__.py` | Modify | Discriminated transport, private result, idempotent final submit and controller export. |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | Register the preliminary route without import-time I/O. |
| `apps/server/src/shifu/learning/pipes/learning_pipe.py` | Modify | Expose the shared assessor port to controllers; no rubric business logic in the pipe. |
| `apps/server/src/shifu/app.py` | Modify | Construct the Intelligence Jev provider once, inject it behind the Shared port into Learning HTTP and Inngest paths, and close its HTTP client during application shutdown; no import-time I/O. |
| `apps/server/src/shifu/intelligence/providers/code_rubric_assessor_provider/jev_code_rubric_assessor_provider.py` | Create | `JevCodeRubricAssessorProvider` implements the Shared port using `httpx.Client.post` to OpenRouter `POST /api/alpha/decisions`; Pydantic transport models, fixed `choice` criteria and typed error translation stay here. No Learning/Curriculum imports, grading or progress rules, TypeSafe SDK or Agno. |
| `apps/server/src/shifu/shared/settings.py` | Modify | Typed server-only OpenRouter key, Decisions API URL, pinned Jev model and bounded request settings. |
| `apps/server/pyproject.toml` | Modify | Declare the existing transitive `httpx` as a direct dependency for the Intelligence Jev provider; no TypeSafe SDK or Agno dependency for this assessment. |
| `apps/server/uv.lock` | Modify | Refresh lockfile metadata after adding `httpx` as a direct dependency. |
| `apps/server/src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py` | Modify | Durable mixed evaluation via existing event/run identity, once-only effects. |
| `apps/server/src/shifu/learning/messaging/inngest/learning_inngest_messaging.py` | Modify | Durable mixed evaluation via existing event/run identity, once-only effects. |
| `apps/server/rest-client/learning/activities.rest` | Modify | Preserve labeled diagnostic examples; keep labeled GET Activity, POST attempts, GET attempt and POST retry, and add preliminary and mixed-body examples with non-secret variables/headers. |
| `apps/web/package.json` | Modify | Add `@monaco-editor/react`, `@webcontainer/api`, `@xterm/xterm` and `@xterm/addon-fit`. |
| `pnpm-lock.yaml` | Modify | Lock the four added web dependencies and their transitive packages. |
| `apps/web/vite.config.ts` | Modify | Configure local WebContainer-compatible isolation headers. |
| `apps/web/src/core/learning/choice-activity.ts` | Modify | Discriminated DTO/service, preliminary action and mixed result; preserve choice transport. |
| `apps/web/src/rest/services/learning-service.ts` | Modify | Discriminated DTO/service, preliminary action and mixed result; preserve choice transport. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/index.tsx` | Move + modify | Move from `choice-activity-page/index.tsx`; rename `ChoiceActivityPage` to `ActivityPage`, compose sibling choice/code widgets and preserve the route contract. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/use-activity-page.ts` | Move + modify | Move from `choice-activity-page/use-choice-activity-page.ts`; rename hook/types, own mixed sequence, frozen feedback, stale-response guard, final submit and leave warning. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/choice-question/index.tsx` | Move + modify | Move the existing choice widget under the neutral page; update its parent hook type import without changing choice behavior. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/choice-question/choice-question.css` | Move | Preserve the existing choice widget stylesheet at its new colocated path. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/choice-question/tests/choice-question.test.tsx` | Move + modify | Preserve choice behavior coverage and update moved imports. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/index.tsx` | Create | Enunciado/Arquivos tabs, editor/tree, Terminal tab, accessible desktop splitters and mobile stack; no new-file control. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/use-code-question.ts` | Create | Question state plus local panel sizing, bounded drag/keyboard behavior and unchanged runner lifecycle. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-question.css` | Create | Desktop grid tracks for the two bounded splitters while preserving stacked mobile layout. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/panel-resize-handle/index.tsx` | Create | Reusable pure separator with accessible name/value, pointer and keyboard affordances and visible focus. |
| `apps/web/src/ui/learning/widgets/components/code-editor/index.tsx` | Create | Monaco-backed editable/read-only source tabs and file-tree composition shared by question/result through explicit props. |
| `apps/web/src/ui/learning/widgets/components/code-editor/use-code-editor.ts` | Create | Selected file, tree visibility and keyboard/focus behavior; no mutation outside permitted paths. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/question-feedback/index.tsx` | Create | Shared provisional choice/code result presentation with score/inconclusive status and forward/final action. |
| `apps/web/src/core/learning/code-practice-runner.ts` | Create | `CodePracticeRunner` contract: fixed project input, status/output stream, stdin, edit/restart and dispose; no explicit Execute action. |
| `apps/web/src/provision/learning/webcontainer-code-practice-runner.ts` | Create + modify | Client-only `@webcontainer/api` implementation, allowlisted entrypoint with empty-stdin startup/edit runs, last-input reuse, process/stream lifecycle and practice bounds. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/index.tsx` | Create | xterm.js lifecycle/fit/input/output and accessible fallback transcript. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/use-code-terminal.ts` | Create | xterm.js lifecycle/fit/input/output and accessible fallback transcript. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/code-question.test.tsx` | Create | Stateful question widget public contract and practice fallback. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/use-code-question.test.ts` | Create | Question hook source/practice/freeze transitions. |
| `apps/web/src/ui/learning/widgets/components/code-editor/tests/code-editor.test.tsx` | Create | Editor public file-tree, tabs and read-only contract. |
| `apps/web/src/ui/learning/widgets/components/code-editor/tests/use-code-editor.test.ts` | Create | Editor selection, editable-path and focus state. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/tests/code-terminal.test.tsx` | Create | Terminal public status/input/output controls. |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/tests/use-code-terminal.test.ts` | Create | Terminal hook lifecycle, subscription and cleanup. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/index.tsx` | Modify | Official summary before ordered independent disclosures; code/choice details and only post-submit failure/retry state. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/use-choice-result-page.ts` | Modify | Repoint its `getChoiceActivityAction` import to `activity-page/use-activity-page` (preserving the exported action contract), then add a local expanded-question key set initialized empty per result view and independent toggles without a server write. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx` | Modify | Accessible summary control with `aria-expanded`/`aria-controls`, protected choice detail and code rubric/read-only file tree; no terminal. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx` | Modify | Owning nested-widget boundary for initially closed/open summary control, keyboard/ARIA and read-only code detail. |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx` | Modify | Import `ActivityPage` from the neutral widget path, reuse the protected URL and inject the browser runner factory through explicit Page props; no duplicate code route. |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/index.tsx` | Modify | Reuse the protected official-result URL and pass read-only result data; never boot WebContainer on this route. |

No Alembic migration is required. New JSON discriminators cannot be mistaken
for old case-based `CodeEvaluationResult`. This feature verifies local browser
isolation only; production delivery configuration and licensing are out of scope.

# 4. Validation Contract

## Revision 15 evidence boundary

Revision 15 keeps all product behavior, functional requirements, acceptance
criteria, and automated CI gates unchanged. At the user's direction, the
remaining live manual replay matrices and exact visual-reference comparisons
are supplemental evidence rather than release gates. Their IDs remain stable
for traceability, but their absence does not block conclusion when the mapped
automated boundary tests pass and the core persisted learner journey is recorded
in Evaluation. This applies to the live same-answer recovery repetition in
VM-04, the second-account live authorization/content/revision/concurrency matrix
in VM-06, the persisted provider-failure/retry/stale-duplicate browser trace in
VM-07, and side-by-side visual comparison for VIS-02/VIS-05. It does not waive
any behavior assertion in the unit, controller, PostgreSQL, job, route, or
responsive-layout tests listed below, nor the successful persisted journey in
EV-077. Production host, HTTPS, and licensing checks remain excluded under
revision 14.

## Executable gates

| CI | Command / directory | Coverage |
| --- | --- | --- |
| CI-01 | `pnpm --filter web check:lint` / root | Web conventions |
| CI-02 | `pnpm --filter web check:architecture` / root | Web dependency direction |
| CI-03 | `pnpm --filter web check:types` / root | Mixed DTO/runtime types |
| CI-04 | `pnpm --filter web test:unit` / root | Activity/code/result widgets and owning hooks |
| CI-05 | `pnpm --filter web test:integration` / root | Protected routes and browser behavior |
| CI-06 | `pnpm --filter web build` / root | Route/build/SSR boundary |
| CI-07 | `uv run poe check:lint` / `apps/server` | Python conventions |
| CI-08 | `uv run poe check:architecture` / `apps/server` | Module dependency direction |
| CI-09 | `uv run poe check:types` / `apps/server` | Python contracts |
| CI-10 | `uv run poe test:unit` / `apps/server` | Content, rubric, replay and progress rules |
| CI-11 | `uv run poe test:integration` / `apps/server` | Real HTTP/PostgreSQL/outbox |
| CI-12 | `uv run poe test:jobs` / `apps/server` | Registered real Inngest evaluation path |
| CI-13 | `uv run poe build` / `apps/server` | Server package build |

| Test file | Test type | Target | Coverage goal |
| --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | unit | get choice activity use case (Modify) | Safe mixed content/account/release, malformed Curriculum project/rubric and Concept coverage through the consuming use case; CA-01/02/08 |
| `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py` | unit | preview activity question feedback use case (Create) | Stateless fixed feedback from typed decision keys, no writes, missing/invalid choices, inconclusive and Shifu failure; assert normalized input contains saved noneditable files, submitted editable replacements in stable path order and exact `submitted_paths`; CA-05/06/10 |
| `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | unit | submit choice activity use case (Modify) | Complete source, revision conflict, replay after content change, concurrency; CA-07/08 |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | unit | evaluate choice activity use case (Modify) | Unequal weights, fixed Jev choice IDs/Concept evidence, missing or invalid decisions, outside-transaction call, stale run and no false zero; assert official assessment normalizes the saved complete project with stable path order and exact submitted paths, regardless of later Curriculum edits; CA-09–CA-11 |
| `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` | unit | get choice attempt use case (Modify) | Account-private mixed result and read-only source; CA-12/13 |
| `apps/server/tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py` | unit | retry choice evaluation use case (Modify) | Same saved answer/new run and once-only result; CA-10–CA-12 |
| `apps/server/tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py` | integration | preview activity question feedback controller (Create) | Auth/payload/status and no DB/outbox effects; CA-05/06/08 |
| `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` | integration | get choice activity controller (Modify) | Real Curriculum provider/mapper against database: valid mixed GET returns the exact fixed dependency names/versions while excluding private rubric details, malformed project/rubric and unsupported content fail closed; account scope; CA-01/02/08 |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | integration | submit choice activity controller (Modify) | Real mixed HTTP/PostgreSQL/outbox and replay; CA-07/08 |
| `apps/server/tests/learning/server/controllers/test_get_choice_attempt_controller.py` | integration | get choice attempt controller (Modify) | Private pending/failed/complete source/rubric; CA-12/13 |
| `apps/server/tests/learning/server/controllers/test_retry_choice_evaluation_controller.py` | integration | retry choice evaluation controller (Modify) | Retry same attempt and account scope; CA-08/10/12 |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | integration | evaluate choice activity job (Modify) | Registered event/job, typed provider response mapping and failure through composed boundary, duplicate/stale run and saved effect; CA-09–CA-12 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/code-question.test.tsx` | component | code question (Create) | Editor/terminal statuses, pt-BR/focus, splitters and unsupported practice; CA-03/04/14/15 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/tests/use-code-question.test.ts` | hook unit | use code question (Create) | Last stdin, edit restart, stale output, dispose, frozen source and bounded resizing; CA-03–CA-06/15 |
| `apps/web/src/ui/learning/widgets/components/code-editor/tests/code-editor.test.tsx` | component | code editor (Create) | Initial-file tabs/tree, read-only result and keyboard; CA-02/13/14 |
| `apps/web/src/ui/learning/widgets/components/code-editor/tests/use-code-editor.test.ts` | hook unit | use code editor (Create) | Selection/tree state, editable-path enforcement and focus return; CA-02/13/14 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/tests/code-terminal.test.tsx` | component | code terminal (Create) | Public xterm status, input and output with mocked hook; CA-03/04/14 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/code-question/code-terminal/tests/use-code-terminal.test.ts` | hook unit | use code terminal (Create) | Terminal lifecycle, subscription, input dispatch and cleanup; CA-03/04/14 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx` | component | Activity page (Move + modify) | Moved choice page coverage plus mixed preliminary/final UI and no previous edit; CA-05–CA-07/14 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts` | hook unit | Activity page hook (Move + modify) | Moved hook coverage plus sequence, stale request, revision and leave warning; CA-05–CA-08 |
| `apps/web/src/ui/learning/widgets/pages/activity-page/choice-question/tests/choice-question.test.tsx` | component | Choice question (Move + modify) | Existing choice interactions and updated parent hook imports; CA-01/14 |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/choice-result-page.test.tsx` | component | choice result page (Modify) | Official summary order, initially closed independent disclosures, keyboard/ARIA, code detail without terminal, pending/failed and choice safety; CA-12–CA-14 |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx` | component | choice result detail (Modify) | Closed/open public control, keyboard/ARIA, multiple-independent prop contract, code read-only/no terminal and choice disclosure; CA-13/14 |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/use-choice-result-page.test.ts` | hook unit | use choice result page (Modify) | Empty initial expanded-key set, multiple independent toggles, persisted status/retry/navigation; CA-12/13 |
| `apps/web/tests/routes/learning/activities.$activityId.index.test.tsx` | route/browser | activities.$activityId.index (Modify) | Deterministic protected mixed route, method/body/URL and injected-runner interaction before/after stdin; live WebContainer startup/output is VM-02 evidence; CA-01/03/05–CA-08. |
| `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx` | route | activities.$activityId.attempts.$attemptId.index (Modify) | Mixed result/retry route; CA-12–CA-14 |
| `apps/web/tests/learning/activity-page.test.ts` | browser | Activity page (Move + modify) | Existing browser coverage plus mixed Activity route at desktop/mobile; CA-03–CA-06/14 |
| `apps/web/tests/learning/choice-result-page.test.ts` | browser | choice result page (Modify) | Actual result route/details; CA-12–CA-14 |

Query/action hooks and concrete providers do not get dedicated suites. Mocked
browser transport does not prove persistence, and a mocked WebContainer does
not prove actual browser execution. Existing choice suites stay green.

## Manual scenarios

| VM | CA | Preconditions, viewport and reference | Numbered actions, assertions and evidence |
| --- | --- | --- | --- |
| VM-01 | CA-01/02/14 | Healthy PostgreSQL/API/web; owned published 3-question mixed Activity; 1440 × 900; `lZDH7.png` and existing choice reference. | 1. Open protected Activity URL and inspect safe GET/order/progress. 2. Answer choice, request feedback and advance to stdin. 3. Open Arquivos with keyboard and edit a permitted file. Assert no prior edit, no answer key in GET/DOM, correct URL/focus, no overflow, failed requests or console errors; save desktop screenshot and request trace. |
| VM-02 | CA-03/14/15 | Healthy web and compatible isolated browser; published stdin project; 1440 × 900 plus 390 × 844; `lZDH7.png` at default widths. | 1. Open the code question with blank source, edit it to `console.log('fff')`, and confirm `fff` appears without terminal input; the terminal still invites stdin. 2. Type `Shifu` in xterm.js and inspect output. 3. Edit source and verify automatic rerun with `Shifu`; enter different stdin and edit again. 4. Verify only the Curriculum-allowlisted entrypoint ran and stale output never replaces the current run. 5. Drag each desktop divider, then resize it with keyboard arrows; check minimum widths, focus and unchanged editor/terminal state. 6. Check that mobile remains stacked without dividers. Assert status/output, no Execute button or Shifu execution request, no horizontal page overflow or console errors; save pre-input output and default/resized screenshots/transcript. |
| VM-03 | CA-04/14 | Healthy API/web; force WebContainer boot failure or unsupported browser; 390 × 844; desktop `lZDH7.png` as content reference. | 1. Open Activity, traverse tabs/editor/terminal with keyboard. 2. Edit source, request provisional feedback and continue. Assert practice-unavailable announcement, usable editor/assessment, no page overflow or lost focus, safe preliminary request and no false score; save mobile screenshot and console/network log. |
| VM-04 | CA-05/06 | Automated preview/recovery tests; the real preview no-write capture in EV-077. The separate live same-answer recovery repetition is supplemental under revision 15. | Automated use-case/hook/controller recovery assertions remain required. The EV-077 preview confirms unchanged attempts, evaluations, progress, Concept observations and event counts. |
| VM-05 | CA-07/09/12/13/14 | Healthy PostgreSQL/API/web/Inngest with evaluation function registered, real authenticated account and published mixed Activity; 1440 × 900 plus 390 × 844; default `oPNtH.png`, expanded full-page `Qxidv.png` and code detail `O070h.png`. | 1. Answer all 3–5 questions and submit from last feedback. 2. Inspect POST body/status, pending URL and outbox/job registration. 3. Wait for official result; verify score/progress, all question summaries closed and any existing recommendation still available. 4. Use keyboard to expand two questions concurrently and inspect read-only code files/choice disclosure, then close one and confirm the other stays open. Assert one immutable attempt, saved snapshot/files, weighted score and progress effect, private source, `aria-expanded`/focus, no terminal, console/failed-request errors or overflow; save HTTP/DB/job IDs and default/expanded desktop/mobile screenshots. |
| VM-06 | CA-02/07/08 | Automated controller/PostgreSQL account-scope, content, revision, replay and conflict tests. A live two-account fixture matrix is supplemental under revision 15. | The automated cases listed above remain required and are recorded in CI-10/11 evidence. No second seed account or live browser/API matrix is required for this delivery. |
| VM-07 | CA-10/11/12 | Automated provider failure, inconclusive, retry, stale-run and duplicate-job tests. A persisted browser replay trace is supplemental under revision 15. | The automated use-case/controller/job cases listed above remain required and are recorded in CI-10–12 evidence. The successful persisted result and outbox path is recorded in EV-077. |

Common setup: verify `docker compose ps`, API/web health and Inngest
registration before the scenarios that need them. Use disposable accounts and
content; do not reset shared data or stop shared Docker services. Inspect DOM,
focus, final URL, requests, console and failed responses for each browser
scenario. Stop only application processes started for validation; record actual
captures, row counts and outcomes in Evaluation.

Configure and exercise browser resource/output bounds with a controlled fixture;
do not log raw provider payloads or terminal contents.

| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01/02 | Curriculum-backed GET controller and routed page tests | VM-01; VM-06 live matrix supplemental | Evaluation content and route evidence |
| CA-03/04 | Runner/terminal widgets and browser tests | VM-02/03 | Evaluation terminal transcript and desktop/mobile captures |
| CA-05/06 | Preliminary use case/controller and Activity hook tests | VM-04 live recovery repetition supplemental | Evaluation no-write query and provisional-result capture |
| CA-07/08 | Submit use case/controller/DB tests | VM-05; VM-06 live matrix supplemental | Evaluation HTTP, row and outbox identity |
| CA-09–CA-12 | Official use case/job/controller/result route tests | VM-05; VM-07 persisted browser trace supplemental | Evaluation job trace, run identity and once-only effect |
| CA-13/14 | Result/Activity widget and route tests | VM-01/03/05; VIS-02/05 exact comparisons supplemental | Evaluation keyboard/DOM, accessibility and viewport captures |
| CA-15 | Code question widget/hook and browser route | VM-02 | Desktop drag/keyboard dimensions, mobile stack, focus/state and fresh screenshots |

# 5. Documentation alignment and revision history

| Document | Authority for | State | Alignment |
| --- | --- | --- | --- |
| [Curriculum PRD v12](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB), ID `83034113` | RP-03/JN-03 content/rubric | confirmed | Complete page read 2026-09-26; only stdin code plus choice delivered here. |
| [Learning PRD v22](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB), ID `83066881` | RP-09/11–14/18/25/27, JN-07/08 | changed | Complete page reread 2026-09-26 22:43 UTC after user-approved RP-11/JN-07 amendment: JavaScript practice runs with empty stdin before first input, still without an Execute button; provisional feedback remains separate from official persistence. |
| [SHIFU-75](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-75) | Historical delivery context | conflicting | Python/tests/Execute and old PRD v13 are stale; a separate explicit external edit is needed to update Jira. |
| [SDD](../../../sdd.md), [Modules](../../../modules.md), [Architecture](../../../architecture.md) | Lifecycle/ownership/runtime | changed/confirmed | Architecture's pre-input waiting sentence is aligned to Learning PRD v22: run the allowlisted JavaScript entrypoint with empty stdin before first input. Existing browser bounds, isolation and module authority remain. |
| [Design system](../../../design.md), [handoff](./design/handoff.md) | UI tokens, saved frames and responsive mapping | changed with documented gap | Design/handoff terminal guidance is aligned to the pre-input output state; saved `lZDH7` stays the default visual frame. No dedicated mobile Pencil code frame exists; a fresh mobile runtime capture is required. |
| [Tooling](../../../tooling.md), current manifests | Real commands/installed state | confirmed | Monaco, xterm.js and WebContainers are absent; `httpx` is transitive and must become a direct server dependency at implementation. TypeSafe SDK and Agno are not required for this assessment. |

| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| [TypeScript](../../../rules/typescript-conventions-rules.md), [UI](../../../rules/ui-layer-rules.md), [routing](../../../rules/web-app-routing-rules.md), [widgets](../../../rules/widget-testing-rules.md) | Web UI, routes and browser tests | 2026-09-26 worktree |
| [Python](../../../rules/python-conventions-rules.md), [core](../../../rules/core-layer-rules.md), [use-case testing](../../../rules/use-case-testing-rules.md) | Curriculum/Learning domain and use cases | 2026-09-26 worktree |
| [REST](../../../rules/rest-layer-rules.md), [controllers](../../../rules/controllers-testing-rules.md), [server app](../../../rules/server-app-layer-rules.md) | HTTP and composition | 2026-09-26 worktree |
| [database](../../../rules/database-layer-rules.md), [provision](../../../rules/provision-layer-rules.md) | JSON mapping, provider lifecycle and module-owned implementation of Shared port | 2026-09-26 worktree |
| [messaging](../../../rules/messaging-layer-rules.md), [jobs](../../../rules/jobs-testing-rules.md), [AI](../../../rules/ai-layer-rules.md) | Official job, Shared port and Intelligence provider | 2026-09-26 worktree |

| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | 2026-09-26 | Initial stdin-code/mixed-Activity contract, saved Pencil references and approved browser-resource Architecture alignment. | User request, Curriculum v12, Learning v21 and `lZDH7`. |
| 2 | 2026-09-26 | Result page leads with official summary and uses independent question disclosures initially collapsed; added saved mixed-result frame. | User-approved result-page interaction and Pencil `oPNtH`. |
| 3 | 2026-09-26 | Deferred new recommendation behavior while retaining the official result page, independent question details and existing guidance; aligned both Pencil result frames. | User request to address recommendation separately. |
| 4 | 2026-09-26 | Renamed the planned mixed Activity widget boundary to `activity-page` and placed existing choice and new code question widgets as siblings; route URL stays fixed. | User-approved widget ownership correction. |
| 5 | 2026-09-26 | Named Monaco and the exact xterm fit-addon package in the expected web dependencies and editor contract. | Reconciled Spec with Architecture code-editor authority. |
| 6 | 2026-09-26 | Replaced the planned Agno code-assessment workflow with an Intelligence-owned Jev provider; then switched its transport from TypeSafe SDK to OpenRouter's Decisions API using typed Pydantic validation. Added scoped Tach dependencies for cross-module composition and aligned Architecture/AI rules. | User-directed provider architecture and OpenRouter Decisions API reference. |
| 7 | 2026-09-26 | Moved the Jev provider back to Intelligence behind a Shared core assessor port over immutable Curriculum snapshots. Removed the cross-module composition adapter and its Tach dependency change. | User clarified module ownership and domain-object boundary. |
| 8 | 2026-09-26 | Changed the assessor port to accept a normalized immutable `CodeRubricAssessmentInput`; all code question kinds use the same Jev decision implementation while prompt, project files and saved criteria vary. This delivery still enables only JavaScript stdin. | User clarified future code questions reuse one evaluation implementation. |
| 9 | 2026-09-26 | Renamed the planned per-question provisional-feedback use case, controller and tests to `preview_activity_question_feedback` to distinguish them from the official Activity evaluation. | User challenged the `preliminarily_evaluate` naming. |
| 10 | 2026-09-26 | Renamed the planned Intelligence provider folder from `openrouter` to `code_rubric_assessor_provider`; the Jev implementation file and OpenRouter transport remain the same. | User requested capability-named provider placement. |
| 11 | 2026-09-26 | Made `fixed_dependencies` explicit in the public `CodeQuestionDetail` and mixed GET projection; the fixed project already required them for browser practice. No new editable configuration, command or product outcome. | Resolved ACH-005 transport field omission before F2 server and Web DTO implementation. |
| 12 | 2026-09-26 | Added accessible, bounded desktop resizing for the three code-question panels while preserving the mobile stack and practice state; added RF-11/CA-15 and VM-02 visual/interaction evidence. | Direct user request based on the current three-panel browser screenshot. |
| 13 | 2026-09-26 | JavaScript stdin practice runs on load and edit with empty stdin before first user input, showing input-independent output while still inviting stdin; after input it reuses the latest value. Updated RF-03/CA-03/VM-02 and aligned runner/terminal contract to the no-button implementation. | User reported that `console.log` produced no output before input; user-approved Learning RP-11/JN-07 v22 amendment. |
| 14 | 2026-09-27 | Removed production host, HTTPS, and commercial-use licensing verification from this feature's release acceptance scope; retained local Vite isolation-header validation. Added the local seed fixture path and kept the persisted real-backend journey in manual Playwright evidence rather than the mocked Web route-test suite. | User directed that the production-host release check be removed from scope; Spec review clarified the seed/test path ledger and test-integrity boundary. |
| 15 | 2026-09-27 | Kept all product and automated test requirements, while making the live VM-04 recovery repetition, VM-06 two-account matrix, VM-07 persisted retry/stale-duplicate trace, and VIS-02/VIS-05 exact visual comparisons supplemental rather than release gates. | User directed that the remaining evidence pendencies be removed so the Spec could be concluded; no product behavior or canonical PRD requirement changed. |
