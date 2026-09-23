---
title: Learning Activity choice questions
status: completed
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-74
scope:
  - apps/server
  - apps/web
  - design/shifu.pen
  - documentation/features/learning/activity-choice-questions
last_updated_at: 2026-09-23
---

# 1. Context and scope

## Objective and source

Deliver [SHIFU-74](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-74):
an authenticated learner can answer a released Learning Activity containing three
to five single-choice or multiple-selection questions, submit one immutable
attempt, and receive a complete official result with safe conceptual feedback
and its effect on Competency progress. Learning owns authorization, attempts,
evaluation, progress and result disclosure. Curriculum owns question content,
correct options, weights and fixed outcome-specific explanations.

This is a **complete** Spec because the slice crosses two business modules,
FastAPI, PostgreSQL, the event outbox and Inngest, TanStack Start/Router/Query,
account-private API contracts and responsive UI states. Product authority is
the complete [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB),
content ID 83066881, version 13, retrieved 2026-09-23 01:20 UTC. The complete
[Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB),
content ID 83034113, version 6, was also checked for RP-03/RP-04 content
authority. Jira was read on the same date. No Jira or Confluence object is
changed by this Spec.

## Current behavior and product gap

The protected Activity route currently raises not-found. Learning exposes Goal
and Competency reads, but no Activity question, submission, result or retry API.
Its attempt/evaluation entities and SQLAlchemy repositories exist without an
application flow. Curriculum already stores question options and weighted
evaluation rules in JSON, but choice questions have no explanation fields and
its shared provider exposes only Activity summaries. The Learning submission
event and transactional outbox exist, but no Learning Inngest job is registered.
The current CompetencyProgress.record_result incrementally applies a new score
to the previous progress and retains the maximum hard score; RP-15/RP-16 instead
require recomputation from the diagnostic baseline using the latest official
result per Activity, including regression.

## Scope and product alignment

| Area | In scope | Out of scope |
| --- | --- | --- |
| Learning execution | Released Learning choice Activities, sequential question UI, complete submission, immutable attempt, account-private result | Diagnosis, code questions, AI assessment, draft answers and a separate practice mode |
| Evaluation | Exact 0/100 question scoring, Curriculum-weighted final score, background processing, failure/manual recovery | Automatic evaluation-job retries, partial credit and bypassing required parts |
| Progress | Official result applied once; RP-15/RP-16 Competency recomputation and safe next-action projection | General Skill/progress pages, global recommendation UI, Gamification reward implementation |
| Content | Fixed correct/incorrect explanations on Curriculum choice questions, safe Learning projection, updated sample seed | Curriculum authoring/editor UI and generated feedback |
| Results | One complete Activity-result page with all question details, selected answers, progress effect and protected answer disclosure | History list/routes and details of older attempts; code/AI result pages |
| Design | Six Jira frames, removal of misleading protected-answer row, three approved supplemental desktop/mobile frames and saved handoff | Frames D5sVc, CqevA, A5ebO0, xCvbp, pxl1h and K3PSz |

| Source requirement | Delivery | Notes |
| --- | --- | --- |
| Learning RP-09 | full for this slice | Three to five complete answers, irreversible sequential advance, no draft, immutable/idempotent submission. |
| Learning RP-10 | full for Learning choice questions | Single choice receives 100 or 0 with safe result feedback. Diagnostic presentation remains excluded. |
| Learning RP-13 | full for Learning choice questions | One official weighted result only after every mandatory part succeeds; effect once. |
| Learning RP-14 | partial | Pending/failed state, same-Skill pause, leave-screen continuation, preserved answer and manual retry are included; non-choice evaluators remain adjacent work. |
| Learning RP-15 | full for choice-result updates | Recompute the affected Competency from the diagnostic baseline and latest official results; general Skill display is adjacent work. |
| Learning RP-16/RP-17 | partial | Recalculate domain/maturity/focus/recommendation inputs and expose the next action; general Skill page is excluded. |
| Learning RP-18 | partial | Complete current choice-Activity result and durable attempt/result; history browsing and final Skill summary page are excluded. |
| Learning RP-25 | full for this surface | pt-BR, desktop/mobile, keyboard, assistive status, non-color-only states. |
| Learning RP-26 | full for Learning choice questions | Exact-set multi-select scoring and protected incorrect feedback. Diagnosis remains excluded. |
| Learning JN-07 | partial | Covers answering a released choice Activity and receiving its result; surrounding Skill/detail journeys are separate. |
| Curriculum RP-03/RP-04 | partial | Supplies the authoritative three-to-five question contract and Learning-facing content/rules; authoring UI is excluded. |

## Product decisions and assumptions

| Concern | Accepted contract |
| --- | --- |
| Feedback | Curriculum stores separate, fixed, question-specific conceptual explanations for correct and incorrect results. A legacy choice Activity without both explanations is unavailable until its content is updated; there is no generated or generic fallback. |
| Submission identity | The browser creates one stable key per intended submission. Repeating that key reuses the same saved attempt; a deliberate later attempt uses a new key even if answers match. |
| Evaluation | The committed attempt and pending evaluation are handed off through the existing outbox to one Learning-owned Inngest job. The job runs after navigation and has zero automatic evaluation retries. Outbox transport redelivery remains a distinct repository guarantee. |
| Recovery | First terminal job failure preserves the attempt and shows Tentar novamente. An evaluation still pending after five minutes becomes manually recoverable; stale deliveries cannot apply a result after a retry changes its run identity. |
| Result refresh | Check every three seconds while the result view is visible, and once immediately on return. Stop polling on terminal status/unmount/hidden view. |
| Disclosure | Incorrect feedback shows submitted selections and the incorrect explanation; no correct option or missing member of the correct set is disclosed until the same question is answered correctly in a later attempt or the Competency is mastered. The misleading protected-answer row was removed from Pencil. |
| Result layout | Final Activity score, progress effect and details for all three to five questions appear on one page, including on mobile through vertical scrolling. |
| Design examples | Pencil's 68 → 68 and 68 → 78 progress figures are illustrative. Runtime values follow RP-15 and may decrease. |

# 2. Implementation Contract

## Functional requirements

| ID | RP/JN/source coverage | Required behavior |
| --- | --- | --- |
| RF-01 | RP-09, RP-25, Curriculum RP-03/RP-04, JN-07 | Only the authenticated owner of a Goal/Skill experience may open its released Learning choice Activity. Present three to five Curriculum-ordered questions without correct-option flags or result-only feedback in the question response. Unreleased, mismatched, non-choice or incomplete content is unavailable without exposing private details. |
| RF-02 | RP-09, RP-10, RP-26, JN-07 | Show one question at a time with position/total. Require exactly one selected option for single choice or at least one for multiple selection before advancing. Allow multi-select add/remove, advance only forward and never edit an answer after advancing. Warn before leaving with unsent answers; do not persist drafts. |
| RF-03 | RP-09, RP-13, RP-14, JN-07 | The last valid answer exposes one submit action. A complete submission creates one immutable Learning attempt and pending evaluation, starts evaluation automatically, and returns an addressable attempt. Network retries with the same submission key reuse that attempt; concurrent submissions cannot create duplicates or bypass a same-Skill pending/failed pause. |
| RF-04 | RP-10, RP-13, RP-26 | Score single choice 100 only for its one correct option; score multiple selection 100 only for an order-independent exact set. Every other valid answer scores 0, with no partial credit. Calculate one final score from all required question results using Curriculum weights totaling 100%. |
| RF-05 | RP-13, RP-14, RP-25 | Distinguish pending, failed and completed evaluations. Never show pending/system failure as zero or a partial official score. A failure preserves answers and offers manual retry on the same attempt; no automatic evaluation-job retry occurs. A pending run older than five minutes is recoverable manually and a late/stale event cannot apply twice. |
| RF-06 | RP-10, RP-18, RP-26 | On completion, display the final Activity score and every question's score, outcome, submitted selection and outcome-specific conceptual explanation on one page, plus the Competency progress/status effect and appropriate next action. The result remains available after leaving and returning. |
| RF-07 | RP-10, RP-18, RP-26 | While disclosure is barred, an incorrect result never reveals correct option identifiers, a missing correct option, the full correct set or answer-bearing explanations through UI, HTTP responses, logs or browser state. Release the relevant answer only after a later correct answer to that question or Competency mastery. |
| RF-08 | RP-13, RP-15, RP-16, RP-17, RP-18 | Apply each completed official result once. Recompute the affected Competency from its diagnostic baseline using only the latest completed result of each distinct Activity in official result order; recompute hard-result evidence, status, focus and continuation without hiding lower scores or regressions. Keep previously released content available. |
| RF-09 | RP-09, RP-14, RP-18 | Preserve every submitted attempt and evaluation as account-private records even without history UI. Pause only new attempts in the same Skill while an evaluation is pending/failed; allow released-content navigation and other Skills. If the Skill experience is removed before a job finishes, the job does not recreate or mutate it. |
| RF-10 | RP-25, SHIFU-74 | All question, result, loading, validation, pending, failure and recovery states are usable at desktop/mobile widths in pt-BR with semantic controls, keyboard/focus support, announcements and non-color-only cues. |
| RF-11 | RP-10, RP-26, Curriculum RP-03/RP-04 | Curriculum supplies fixed correct/incorrect explanations with every eligible choice question. Missing or invalid explanations block that Activity before submission and produce safe unavailability, not fabricated feedback or an invalid official result. |

## Acceptance criteria

| ID | RF coverage | Requirement | Given | When | Then | Expected evidence |
| --- | --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01, RF-11 | Private Activity read | Anonymous, non-owner, mismatched hierarchy, unreleased Competency, non-choice Activity or incomplete explanation | Activity is opened | Authentication rejects anonymous access; private absence uses safe not-found/unavailable behavior; valid owner receives 3–5 ordered safe questions without answer flags or explanations | Controller/use-case integration; VM-01/VM-05 |
| CA-02 | RF-02, RF-10 | Sequential answers | A valid three-to-five question Activity with both choice types | Learner selects/removes choices and advances | Invalid/empty selection cannot advance; only current question renders; prior answers cannot be revisited or changed; leaving warns of unsent loss | Widget/route tests; VM-01/VM-02 |
| CA-03 | RF-03, RF-09 | Immutable, idempotent submission | All answers valid and Skill accepts a new attempt | Learner submits, retries the same request/key, or submits concurrently | One attempt, one pending evaluation and one authoritative handoff exist for the key; answers remain fixed; different key is a new attempt only after blocking evaluation resolves | Use-case/controller/PostgreSQL tests; VM-01/VM-06 |
| CA-04 | RF-04, RF-11 | Objective scoring | Single and multiple answers include exact, incomplete, extra and order-varied sets with unequal Curriculum weights | Job evaluates | Correct parts are 100, others 0; all required parts recorded; final weighted score appears once only when all valid parts complete | Use-case/job tests; VM-03 |
| CA-05 | RF-05, RF-09 | Pending, failure and manual retry | Evaluation is pending, fails, or remains pending beyond five minutes | Learner views or retries the attempt | Pending has no score; first job failure or stale pending offers Tentar novamente with same answers/attempt; retry creates a new run identity and cannot duplicate official effects; same Skill is paused, other Skills are not | Job/controller/widget tests; VM-03/VM-06 |
| CA-06 | RF-06, RF-10 | Complete result | A three-to-five question attempt completes | Learner views/returns to its result | One final weighted score and every question detail, explanation and progress effect appear on the same page; result view checks every 3 seconds while visible and immediately on return | Controller/widget/route tests; VM-03/VM-04 |
| CA-07 | RF-07 | Protected incorrect answer | The learner answered a single or multiple question incorrectly and has not later answered it correctly or mastered the Competency | Result/API is inspected | Only submitted choices, score and safe incorrect explanation appear; correct identities and missing correct selections are absent from response and DOM | Use-case/controller/security tests; VM-03 |
| CA-08 | RF-07, RF-08 | Disclosure and regression | A later attempt gets the same question right, or Competency mastery changes after a new result | Result and progress are read | Eligible answer is shown; official progress may rise or fall; hard-result evidence, status/focus and next action reflect only current official results | Use-case/controller tests; VM-03/VM-05 |
| CA-09 | RF-08, RF-09 | Exactly-once and deletion | Duplicate/stale event, concurrent job, duplicate completion, or Skill removal occurs | Job processes | At most one official effect/event is committed; stale events are ignored; deleted experience is not recreated and no other account/Goal is affected | Real Inngest/PostgreSQL tests; VM-06 |
| CA-10 | RF-02, RF-05, RF-06, RF-10 | Responsive accessible states | Desktop 1440 × 900 and mobile 390 × 844 | Learner uses keyboard, assistive labels and touch through selection, pending, failure and result | Visible focus, 44 px mobile targets, clear status text, no horizontal overflow or bottom-nav obstruction, announced changes and safe reduced motion | Widget/route tests; VM-01–VM-04 |
| CA-11 | RF-01, RF-11 | Fixed feedback content | An older Curriculum JSON question lacks either explanation | Owner opens Activity | It is unavailable before submission; no generic/generated copy or correct answer leaks; updated authored content restores eligibility | Provider/controller tests; VM-05 |
| CA-12 | RF-03, RF-06, RF-09 | Durable return | Learner leaves while evaluation runs and reopens the Activity/attempt | Result is requested | The same attempt is found; processing/failed/completed status is current; no new attempt is created by navigation or polling | Controller/route/job tests; VM-03/VM-06 |

## Cross-cutting restrictions

| Concern | Contract |
| --- | --- |
| Account privacy | Authorize Goal ownership and Skill/Competency/Activity hierarchy before returning content or attempt state; never expose whether another account has an attempt. |
| Credentials | TanStack server functions obtain Better Auth access server-side; bearer tokens and answer keys never enter browser storage, URLs, logs or client-visible errors. |
| Score semantics | Zero means an evaluated incorrect result only. Failed/pending has no official score. Display rounding cannot affect mastery. |
| Attempts | Answers and evaluation-rule snapshot used for one submission are immutable; manual retry changes evaluation run state only. |
| Delivery | Learning use cases write events to the module transaction's outbox; controllers never publish directly. Inngest function retries are zero, while outbox delivery may redeliver its event. |
| History | Persist records now, but do not create history list or historical-detail routes in this ticket. |

## Design Contract

The file-backed visual authority is [design/handoff.md](./design/handoff.md).
Nine inspected and saved Pencil references cover desktop single/multiple
questions, four individual correctness states, the complete desktop result,
mobile multiple selection and the complete mobile result. The desktop
references have 1440 × 900 source frames; mobile references have 390 × 844
source frames. The saved PNGs are deliberate uniformly scaled previews, with
their exact preview dimensions and source viewports recorded in the handoff.
The UI uses existing Shifu dark tokens and shell, with two new shared
radio/checkbox primitives. Four or
five result details extend the page vertically without clipping. Runtime
focus, polling and announcements may differ from static frames while
preserving the visual hierarchy and protected-answer behavior.

# 3. Technical Contract

## Current technical state and runtime flow

| Evidence | Current responsibility | Gap |
| --- | --- | --- |
| `ActivityAttempt`, `ActivityEvaluation`, their SQLAlchemy models/repositories | Persist submitted answers and one evaluation per attempt | No submission key, frozen grading snapshot or run identity; no use cases consume them. |
| `CompetencyProgress.record_result` | Updates progress after a score | Uses previous progress and maximum hard score, so cannot recompute the latest official set or regress correctly. |
| `CurriculumContentProvider` and `DatabaseCurriculumContentProvider` | Supply Learning's Skill/Activity summary | No private choice-question/rule projection; Curriculum JSON has no explanation fields. |
| `ActivitySubmissionRequestedEvent`, outbox and `InngestMessaging` | Durable event publication; registered Identity job | Submission event lacks run identity; no Learning job is registered. |
| Learning REST router and web Activity route | Expose Goal/detail; authenticate route | No Activity, attempt, result or retry endpoints; Activity route always throws not-found. |

The authenticated Activity GET first verifies Goal ownership, Skill experience,
Competency release and exact Activity hierarchy. Curriculum's provider returns a
private, immutable-at-use choice projection with ordered questions, option IDs,
correct flags, fixed correct/incorrect explanations, difficulty and weighted
parts. Learning validates 3–5 choice questions, unique keys/options, one-to-one
required parts and 100% total weight before making a safe question projection.
For legacy JSON, the mapper accepts absent explanation fields as `None`; the
provider rejects the Activity for execution until every explanation is authored.
This preserves existing rows without guessing their meaning. Curriculum seed
content must supply both explanations before the new path is usable.

The browser retains answers and a submission UUID for the active submission,
including transport-error retry. POST receives the complete ordered answer set
and key. The Learning use case receives existing `ClockProvider` and
`IdentifierProvider` ports through composition; it never reads the clock or
generates IDs directly. It checks owner/hierarchy and a current Curriculum
projection, then locks the
Skill experience row. In one Learning transaction it reuses an existing attempt
for that key or creates an immutable attempt, a private grading snapshot, a
pending evaluation with a fresh run ID, and the submission outbox event. A
unique `(skill_experience_id, submission_key)` index resolves concurrent repeats.
An existing key with a different answer payload is `409`; a new key while a
same-Skill evaluation is pending/failed is `409`. No cross-module transaction
is required: the Curriculum read finishes before Learning's write. The
attempt's grading snapshot freezes the accepted content/rules for background
scoring and is never serialized to the browser.

The registered Learning Inngest function strictly validates the complete
submission event payload, then uses only `(attempt_id, run_id)` as its lookup
authority.
Its first durable step resolves the current attempt/evaluation; a missing or
stale run exits without effect. Within a Learning transaction, it locks the
evaluation and Skill experience, scores every frozen required part, stores the
single complete result, recomputes the affected Competency from its diagnostic
baseline and latest completed result per Activity, stores that result's before/
after progress and status, applies the effect once, and writes
`ActivityEvaluatedEvent` to the outbox. A deleted Skill experience exits
without recreation. An error before commit rolls back score, progress and event;
the job's failure handler stores a safe failure code in a separate transaction
only if that run remains pending. Configure the evaluation function with zero
automatic retries. Outbox redelivery is independently idempotent.

Authenticated GET of an attempt uses the injected clock and atomically marks
its pending run failed when
`started_at + 5 minutes` has passed; the late event then fails the run-ID/status
check. POST retry locks and changes only the failed evaluation to pending with
a new run ID/time and writes a new outbox event; answers and grading snapshot
stay fixed. The result GET projects only public fields and enforces
question-level disclosure using later completed correct attempts or current
Competency mastery. It never sends correct flags or protected explanations.
The Activity GET exposes the owner's latest attempt ID and unresolved attempt
ID, when present, so a lost POST response or later return can reach the saved
result without recreating an attempt. The visible result page polls GET every
three seconds, checks immediately on return, and stops on hidden/unmounted or
terminal state. Navigation does not cancel the background job.

| Boundary | Producer | Consumer | Canonical contract | Mapping/guarantees | Failure ownership |
| --- | --- | --- | --- | --- | --- |
| Curriculum → Learning | `CurriculumContentProvider.get_choice_activity` | Learning read/submit use cases | Private `CurriculumChoiceActivitySnapshot` | Ordered questions, all option flags, two explanations, weights/difficulty; no HTTP serialization | Provider yields unavailable on missing/invalid content. |
| Learning → browser | Activity GET controller | Web service/page | Safe question DTO | IDs/text/options without flags, rules or explanations | Controller maps private absence to 404. |
| Browser → Learning | Submit controller | `SubmitChoiceActivityUseCase` | Complete answers + submission key | Authenticated owner, strict ordered keys and option-ID validation | 400 invalid input; 404 private absence; 409 blocked/key conflict. |
| Learning → outbox → Inngest | Submit/retry use cases | `EvaluateChoiceActivityJob` | `ActivitySubmissionRequestedEvent` with attempt/run IDs | Same Learning commit as pending state; at-least-once handoff | Outbox delivery retries; job has zero evaluation retries. |
| Learning → browser | Attempt GET/retry controllers | Web result page | Pending/failed/completed result DTO | No score until completed; safe question projection/disclosure | 404 private absence; 409 invalid retry; 503 provider outage. |
| Learning → outbox | Evaluate use case | Future module subscribers | Existing `ActivityEvaluatedEvent` | Once with official effect commit | Duplicate run exits; no event on failure. |

## Resulting domain and transport schemas

| Contract | Complete resulting fields and invariant |
| --- | --- |
| Curriculum `SingleChoiceQuestion`/`MultipleSelectionQuestion` | Existing `key`, `prompt`, `options`; add `correct_explanation: str | None`, `incorrect_explanation: str | None` for legacy deserialization. Both nonblank to be Learning-eligible. Existing correct-option count invariants remain. |
| Private `CurriculumChoiceActivitySnapshot` | Activity `id`, `competency_id`, `difficulty`, `title`, ordered `CurriculumChoiceQuestionSnapshot` tuple and `CurriculumChoicePartSnapshot` tuple. No framework types. |
| Private `CurriculumChoiceQuestionSnapshot` / `CurriculumChoiceOptionSnapshot` / `CurriculumChoicePartSnapshot` | Question: `key`, `kind`, `prompt`, ordered options, both fixed explanations. Option: `key`, `text`, `is_correct`. Part: `question_key`, Decimal percentage weight. Each is a separate shared structure module. |
| `ActivityAttempt` | Existing `id`, `skill_experience_id`, `competency_id`, `activity_id`, `kind`, immutable `answers`, `submitted_at`; add immutable `submission_key`, private immutable `grading_snapshot`. Historic attempts may have nullable key/snapshot but cannot be retried without a snapshot. |
| `ActivityEvaluation` | Existing `id`, `attempt_id`, `status`, `parts`, `started_at`, nullable `score`, `failure_code`, `completed_at`, `effect_applied_at`; add `run_id`, nullable `progress_before`, `progress_after`, `status_before`, `status_after`. Pending has no score/parts/effect; failed has failure code but no score/effect; completed has every required part, score, completion time and stable progress effect. Retry replaces run ID and clears old failure only. |
| `ChoiceEvaluationResult` | Existing `question_key`, Decimal `score`, `is_correct`, `explanation`; explanation is the frozen fixed text for the actual outcome. No generated feedback. |
| `CompetencyProgress` | Existing identity, release, baseline/current percentages, status, mastery time and hard score; replace incremental `record_result` path with recomputation from baseline plus ordered latest completed results. A lower latest hard score can remove mastery. |
| Learning `ChoiceActivityDetail` / `ChoiceQuestionDetail` / `ChoiceOptionDetail` | Framework-free public Activity projection: activity ID/title/difficulty, ordered safe questions with key/kind/prompt/ordered `ChoiceOptionDetail(key,text)` values, `can_submit`, latest/unresolved attempt IDs. No grading flag. Each structure is one module. |
| Learning `ChoiceAttemptDetail` / `ChoiceResultDetail` | Framework-free result projection: attempt identity/status/time/retry state, optional score and stable progress effect/current next action; each complete detail contains question key/prompt, submitted option keys, score/outcome, fixed explanation and conditionally released correct keys. Each structure is one module. |
| Submission event | Existing `attempt_id`, `skill_experience_id`, `activity_id`, `kind`, `requested_at`; add `run_id`. No answers or grading keys in event. |
| Activity GET DTO | `activity_id`, `title`, `difficulty`, ordered `questions[{key, kind, prompt, options[{key,text}]}]`, where `kind` is `single_choice` or `multiple_selection`; `can_submit`, `latest_attempt_id?`, `unresolved_attempt_id?`; never `is_correct`, weights, answer set or explanations. Unavailable content returns 404 rather than this DTO. |
| Submit DTO | Request `{submission_key, answers:[{question_key, selected_option_keys}]}`; response `{attempt_id, status:"pending", result_url}`. Key is an opaque UUID, scoped to Skill experience. |
| Attempt DTO | `{attempt_id, activity_id, status, submitted_at, retry_allowed, failure_message?, score?, progress_before?, progress_after?, status_before?, status_after?, next_action?, questions?}`; completed questions include key, prompt, submitted option keys, score, outcome, one outcome-specific explanation and only conditionally disclosed correct option keys. The saved before/after effect is stable; next action may reflect current availability. Failed/pending omit all official score/result fields. |

## HTTP operations and error mapping

All operations require Better Auth bearer authentication and route IDs for Goal,
Skill, Competency and Activity. The route nesting is the hierarchy assertion,
not a substitute for repository ownership checks. Use the existing Learning
router prefix `/learning` and existing snake_case API serialization convention.

| Method and path below `/learning` | Controller/use case | Success | Rejection |
| --- | --- | --- | --- |
| `GET /goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}` | `GetChoiceActivityController` / `GetChoiceActivityUseCase` | 200 safe question DTO | 401, 404 private/unavailable, 503 provider outage |
| `POST /goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}/attempts` | `SubmitChoiceActivityController` / `SubmitChoiceActivityUseCase` | 201 new or 200 same-key replay | 400 semantically invalid answer, 422 malformed body, 401, 404, 409 blocked/key mismatch, 503 |
| `GET /goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}/attempts/{attempt_id}` | `GetChoiceAttemptController` / `GetChoiceAttemptUseCase` | 200 current status/result | 401, 404 private absence |
| `POST /goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}/activities/{activity_id}/attempts/{attempt_id}/retry` | `RetryChoiceEvaluationController` / `RetryChoiceEvaluationUseCase` | 202 same attempt/new run pending | 401, 404, 409 non-failed/conflict |

Map shared `ValidationError` to HTTP 400 and `ConflictError` to HTTP 409 in
`AppErrorHandler`; FastAPI/Pydantic body-shape rejection remains 422. Use a
generic `NotFoundError` with non-disclosing 404 for wrong account/hierarchy or
ineligible content; do not expose `ActivityNotAvailableError`'s 403 on this
private read. The `activities.rest`
REST-client file covers all four labeled operations with non-secret variables.

## Affected layer contracts and paths

`Create` paths below do not currently exist; `Modify` paths do. Generated
route metadata is produced by the existing web build/router generator and is
never hand-edited. New files are named here to fix ownership and test seams;
implementation may split a file only if the same declarations and rule-compliant
consumer/producer graph are preserved in a Spec amendment.

### Server Domain, Interfaces and Use cases

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/curriculum/core/domain/structures/single_choice_question.py` | Modify | `SingleChoiceQuestion` | Two optional-on-read authored explanations; eligibility requires both | Curriculum mapper/provider | Core tests |
| `apps/server/src/shifu/curriculum/core/domain/structures/multiple_selection_question.py` | Modify | `MultipleSelectionQuestion` | Same explanation contract; preserve correct-set invariant | Curriculum mapper/provider | Core tests |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_choice_activity_snapshot.py` | Create | `CurriculumChoiceActivitySnapshot` | Framework-free ordered questions, correctness, explanations, weights | Curriculum provider → Learning | Use-case tests |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_choice_question_snapshot.py` | Create | `CurriculumChoiceQuestionSnapshot` | One private ordered question and fixed feedback | Activity snapshot | Use-case tests |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_choice_option_snapshot.py` | Create | `CurriculumChoiceOptionSnapshot` | One keyed option and correctness flag | Question snapshot | Use-case tests |
| `apps/server/src/shifu/shared/core/domain/structures/curriculum_choice_part_snapshot.py` | Create | `CurriculumChoicePartSnapshot` | One required weighted question key | Activity snapshot | Use-case tests |
| `apps/server/src/shifu/shared/core/domain/structures/__init__.py` | Modify | Snapshot exports | Export only shared provider contract types | Provider/use cases | Import checks |
| `apps/server/src/shifu/shared/core/interfaces/curriculum_content_provider.py` | Modify | `get_choice_activity` | Private read interface; `None` on missing/ineligible content | Curriculum adapter → Learning | Use-case tests |
| `apps/server/src/shifu/learning/core/domain/entities/activity_attempt.py` | Modify | `ActivityAttempt` | Frozen key and grading snapshot | Submission/job/result | Domain/use-case tests |
| `apps/server/src/shifu/learning/core/domain/entities/activity_evaluation.py` | Modify | `ActivityEvaluation` | Run identity, stable progress effect, legal status transitions, once-only effect | Job/retry/result | Domain/use-case tests |
| `apps/server/src/shifu/learning/core/domain/entities/competency_progress.py` | Modify | `CompetencyProgress` | Full recomputation and mastery regression | Evaluate use case | Core tests |
| `apps/server/src/shifu/learning/core/domain/structures/choice_activity_detail.py` | Create | `ChoiceActivityDetail` | Safe Activity output without grading fields | GET use case/controller | Unit/controller |
| `apps/server/src/shifu/learning/core/domain/structures/choice_question_detail.py` | Create | `ChoiceQuestionDetail` | Safe ordered question/options | Activity detail | Unit/controller |
| `apps/server/src/shifu/learning/core/domain/structures/choice_option_detail.py` | Create | `ChoiceOptionDetail` | Public option key/text without correctness | Question detail | Unit/controller |
| `apps/server/src/shifu/learning/core/domain/structures/choice_attempt_detail.py` | Create | `ChoiceAttemptDetail` | Status/result output and saved progress effect | GET use case/controller | Unit/controller |
| `apps/server/src/shifu/learning/core/domain/structures/choice_result_detail.py` | Create | `ChoiceResultDetail` | Safe per-question result/disclosure | Attempt detail | Unit/controller |
| `apps/server/src/shifu/learning/core/domain/structures/__init__.py` | Modify | Public detail exports | Export new Learning structures | Use cases/controllers | Import checks |
| `apps/server/src/shifu/learning/core/domain/events/activity_submission_requested_event.py` | Modify | Submission payload | Add run ID without answers/key | Outbox/job | Job tests |
| `apps/server/src/shifu/learning/core/interfaces/activity_attempts_repository.py` | Modify | Lookup by submission key | Scope lookup to Skill experience | Submit use case | PostgreSQL integration |
| `apps/server/src/shifu/learning/core/interfaces/activity_evaluations_repository.py` | Modify | Locked current run and latest results | Consistent attempt/evaluation sets; exclude unscorable legacy rows from blocking | Job/result use cases | PostgreSQL integration |
| `apps/server/src/shifu/learning/core/interfaces/skill_experiences_repository.py` | Modify | Row-lock lookup | Serialize new same-Skill submissions | Submit/job use cases | PostgreSQL integration |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_activity_use_case.py` | Create | `GetChoiceActivityUseCase` | Owner/release/hierarchy and safe projection | Provider, Learning DB | Unit/controller |
| `apps/server/src/shifu/learning/core/use_cases/submit_choice_activity_use_case.py` | Create | `SubmitChoiceActivityUseCase` | Strict answers, key replay, atomic attempt/evaluation/outbox | Provider, Learning DB | Unit/controller |
| `apps/server/src/shifu/learning/core/use_cases/evaluate_choice_activity_use_case.py` | Create | `EvaluateChoiceActivityUseCase` | Frozen scoring, locked completion and progress/event effect | Learning DB | Unit/job |
| `apps/server/src/shifu/learning/core/use_cases/get_choice_attempt_use_case.py` | Create | `GetChoiceAttemptUseCase` | Stale timeout, privacy, disclosure and safe DTO | Learning DB | Unit/controller |
| `apps/server/src/shifu/learning/core/use_cases/retry_choice_evaluation_use_case.py` | Create | `RetryChoiceEvaluationUseCase` | Failed-only fresh run/outbox | Learning DB | Unit/controller |
| `apps/server/src/shifu/learning/core/use_cases/__init__.py` | Modify | Public use-case exports | Export new use cases | Controllers/job | Import checks |

### Server Database, Provision, REST, Messaging and Composition

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/src/shifu/curriculum/database/sqlalchemy/mappers/activity_mapper.py` | Modify | Choice JSON mapper | Read old missing explanation as `None`; write authored fields | Curriculum persistence | Controller integration |
| `apps/server/src/shifu/curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Modify | `get_choice_activity` | Load exact Activity, verify question/rule eligibility, create private snapshot | Shared provider port | Use-case/controller |
| `apps/server/src/shifu/fakers/curriculum/entities/activity_faker.py` | Modify | Choice content seed/faker | Supply fixed safe outcome explanations | Seed/test setup | Integration tests |
| `apps/server/src/shifu/learning/database/sqlalchemy/models/activity_attempt_model.py` | Modify | Attempt columns/index | Nullable legacy key/snapshot, unique scoped key | Migration/mapper | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/models/activity_evaluation_model.py` | Modify | Run/effect columns | Nullable legacy run ID and saved before/after progress/status; one evaluation per attempt | Migration/mapper | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_attempt_mapper.py` | Modify | Attempt mapper | Lossless answers/snapshot/key mapping | Repository | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/mappers/activity_evaluation_mapper.py` | Modify | Evaluation mapper | Persist transitions and run ID | Repository | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/activity_attempts_repository.py` | Modify | Key lookup | Scoped unique replay under concurrency | Interface | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/activity_evaluations_repository.py` | Modify | Locked/current/latest queries | Status/run checks, exclude non-runnable legacy rows from same-Skill blocking, and latest completed results | Interface | DB integration |
| `apps/server/src/shifu/learning/database/sqlalchemy/repositories/skill_experiences_repository.py` | Modify | Locking read | `FOR UPDATE` current Skill experience | Interface | DB integration |
| `apps/server/migrations/versions/f64a8c3d7e21_add_choice_attempt_handoff.py` | Create | Alembic migration | Down revision `e1a2b3c4d5e6`; add key/snapshot/run/effect columns and unique partial index; classify pre-feature unresolved rows without snapshots as archival failed, preserving answers | Models | Migration integration |
| `apps/server/src/shifu/learning/rest/controllers/get_choice_activity_controller.py` | Create | GET registration + local `Response` | Authenticated safe question read; Pydantic validates core detail | Use case/router | Mirrored controller test |
| `apps/server/src/shifu/learning/rest/controllers/submit_choice_activity_controller.py` | Create | POST registration + local `Request`/`Response` | Strict body, new/replay status mapping | Use case/router | Mirrored controller test |
| `apps/server/src/shifu/learning/rest/controllers/get_choice_attempt_controller.py` | Create | GET registration + local `Response` | Current status/disclosure; Pydantic validates core detail | Use case/router | Mirrored controller test |
| `apps/server/src/shifu/learning/rest/controllers/retry_choice_evaluation_controller.py` | Create | POST registration + local `Response` | Failed-only response | Use case/router | Mirrored controller test |
| `apps/server/src/shifu/learning/rest/controllers/__init__.py` | Modify | Controller exports | Export new registrations | Learning router | Import checks |
| `apps/server/src/shifu/learning/rest/router.py` | Modify | Four route registrations | Exact route/method parity | FastAPI app | Controller tests |
| `apps/server/src/shifu/learning/pipes/learning_pipe.py` | Modify | Dependency access | Reuse Learning DB/Curriculum provider and expose injected `ClockProvider`/`IdentifierProvider` to controllers | App state | Controller tests |
| `apps/server/src/shifu/rest/handlers/app_error_handler.py` | Modify | Validation/conflict mapping | Typed 400/409; existing safe 404/422/503 | Controllers | Controller tests |
| `apps/server/src/shifu/learning/messaging/inngest/jobs/evaluate_choice_activity_job.py` | Create | `EvaluateChoiceActivityJob` | Strict Pydantic event input, zero retry; current run only; injected DB/clock, worker-thread DB step, failure transaction | Event/use case | Real job test |
| `apps/server/src/shifu/learning/messaging/inngest/jobs/__init__.py` | Create | Job export | Export handler | Registrar | Import checks |
| `apps/server/src/shifu/learning/messaging/inngest/learning_inngest_messaging.py` | Create | `LearningInngestMessaging` | Register one Learning job with bound DB/clock/ID dependencies | App composition | Real job test |
| `apps/server/src/shifu/learning/messaging/inngest/__init__.py` | Create | Registrar export | Export registrar | App composition | Import checks |
| `apps/server/src/shifu/app.py` | Modify | Inngest registrar/dependency composition | Bind shared `SystemClockProvider` and existing ID provider to Learning controllers/job; add Learning group without replacing Identity | App startup | Job integration |
| `apps/server/rest-client/learning/activities.rest` | Create | Four labeled requests | Exact current methods/routes, safe example bodies, non-secret variables | HTTP contract | Manual parity |

### Web UI and Composition

| Widget | Kind | Parent/entry | Direct children | Public contract | Behavior owner |
| --- | --- | --- | --- | --- | --- |
| `ChoiceActivityPage` | Page | Activity route | `ChoiceQuestion`, actions/status | Route IDs; one current question | `use-choice-activity-page` |
| `ChoiceQuestion` | Component | `ChoiceActivityPage` | Shared radio/checkbox and Button | Prompt/options/selection callbacks | Parent hook |
| `ChoiceResultPage` | Page | Attempt route | Summary, `ChoiceResultDetail`, pending/failure action | Route IDs + attempt ID; complete result | `use-choice-result-page` |
| `ChoiceResultDetail` | Component | `ChoiceResultPage` | Safe choice/outcome/explanation | Public detail DTO only | Parent hook |

Expected new widget tree (each entry is an affected path below):

```text
apps/web/src/ui/learning/widgets/pages/
  choice-activity-page/
    index.tsx
    use-choice-activity-page.ts
    choice-question/index.tsx
    choice-question/tests/choice-question.test.tsx
    tests/choice-activity-page.test.tsx
    tests/use-choice-activity-page.test.ts
  choice-result-page/
    index.tsx
    use-choice-result-page.ts
    choice-result-detail/index.tsx
    choice-result-detail/tests/choice-result-detail.test.tsx
    tests/choice-result-page.test.tsx
    tests/use-choice-result-page.test.ts
```

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/web/src/core/learning/choice-activity.ts` | Create | Safe DTO types | Browser receives no private grading fields | REST service/widgets | Widget/route |
| `apps/web/src/ui/shadcn/radio-group.tsx` | Create | Shared radio-group primitive | Native group/label/value/disabled/focus semantics with existing tokens; one selection; keyboard arrow/Space behavior | `ChoiceQuestion` | Nested widget test |
| `apps/web/src/ui/shadcn/checkbox.tsx` | Create | Shared checkbox primitive | Native checked/indeterminate/disabled/label/focus semantics with existing tokens; independent toggles | `ChoiceQuestion` | Nested widget test |
| `apps/web/src/rest/services/learning-service.ts` | Modify | Four activity methods | Existing server-side auth pattern; strict result states | Web hooks | Route integration |
| `apps/web/src/constants/routes.ts` | Modify | Activity/attempt path helpers | Exact nested URLs, encoded IDs | Widgets/routes | Route integration |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId.tsx` | Remove | Former Activity leaf | Replace with segment parent and index leaf | Router | Route generation |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/route.tsx` | Create | Activity segment parent | Auth guard and `Outlet` for Activity/attempt children | Router | Mocked route suite |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/index.tsx` | Create | Activity index leaf | Render question page under parent | Page | Mocked route suite |
| `apps/web/src/routes/learning/goals/$goalId/skills/$skillId/competencies/$competencyId/activities/$activityId/attempts/$attemptId/index.tsx` | Create | Attempt leaf | Render result page under parent | Page | Mocked route suite |
| `apps/web/src/routeTree.gen.ts` | Generate | TanStack route tree | Generated from route files, never hand-edit | Router | Web build |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/index.tsx` | Create | `ChoiceActivityPage` | Render current question, validation/loading/leave warning | Hook/component | Colocated test |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/use-choice-activity-page.ts` | Create | `useChoiceActivityPage` | Sequential local answers; retain one key for transport retries; route to saved attempt on return | Page/service | Hook test |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/choice-question/index.tsx` | Create | `ChoiceQuestion` | Compose shared radio/checkbox primitives; selected/focus/mobile targets | Page | Nested widget test |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/choice-question/tests/choice-question.test.tsx` | Create | Component test | Single/multiple select, label/focus, disabled controls | ChoiceQuestion | Vitest |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/tests/choice-activity-page.test.tsx` | Create | Widget test | Choice states and controls with owning hook mock | Page | Vitest |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/tests/use-choice-activity-page.test.ts` | Create | Hook test | Forward-only, key reuse, submission/error transitions | Hook | Vitest |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/index.tsx` | Create | `ChoiceResultPage` | Pending/failure/completed and complete vertical result | Hook/detail | Colocated test |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/use-choice-result-page.ts` | Create | `useChoiceResultPage` | Visible-only 3-second polling, immediate return, retry | Page/service | Hook test |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/index.tsx` | Create | `ChoiceResultDetail` | Render only public outcome/selected/correct-if-released | Page | Nested widget test |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx` | Create | Component test | Safe detail, fixed explanation, protected/released answers | ChoiceResultDetail | Vitest |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/choice-result-page.test.tsx` | Create | Widget test | Summary, all details, protected answer and recovery | Page | Vitest |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/use-choice-result-page.test.ts` | Create | Hook test | Poll lifecycle/retry/return | Hook | Vitest |
| `apps/web/tests/routes/learning/activities.$activityId.route.test.tsx` | Create | Activity parent route test | Mocked authentication; parent `Outlet`, child selection and navigation | Parent route | Playwright |
| `apps/web/tests/routes/learning/activities.$activityId.index.test.tsx` | Create | Activity index route test | Mocked Activity transport; URL, submit and narrow viewport | Question leaf route | Playwright |
| `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx` | Create | Attempt index route test | Mocked pending/failure/completed responses and navigation | Result leaf route | Playwright |
| `apps/web/tests/learning/choice-activity-page.test.ts` | Create | Activity page integration test | Exercise the actual nested Activity route and ChoiceActivityPage composition with mocked transport | `ChoiceActivityPage` | Playwright |
| `apps/web/tests/learning/choice-result-page.test.ts` | Create | Result page integration test | Exercise the actual nested attempt route and ChoiceResultPage composition with mocked transport | `ChoiceResultPage` | Playwright |
| `apps/web/tests/learning/competency-detail-page.test.ts` | Modify | Existing route assertion | Replace Activity not-found expectation with guarded navigation | Route/page | Playwright |

The three new route files have a one-to-one test contract:

| Route file | Dedicated mocked Playwright suite | Primary boundary |
| --- | --- | --- |
| `activities/$activityId/route.tsx` | `activities.$activityId.route.test.tsx` | Authentication, parent `Outlet`, child routing. |
| `activities/$activityId/index.tsx` | `activities.$activityId.index.test.tsx` | Question page loading, input, submission and error states. |
| `activities/$activityId/attempts/$attemptId/index.tsx` | `activities.$activityId.attempts.$attemptId.index.test.tsx` | Pending, failure/retry, complete result and return. |

The two routed Page widgets also have module-owned Playwright integration suites,
as required by the Widget Testing Rule. These suites exercise actual route and page
composition; they supplement and do not replace the route-file suites above.

| Routed Page widget | Module-owned Playwright suite | Primary boundary |
| --- | --- | --- |
| `ChoiceActivityPage` | `apps/web/tests/learning/choice-activity-page.test.ts` | Sequential interaction, request/response behavior and recovery through the actual route. |
| `ChoiceResultPage` | `apps/web/tests/learning/choice-result-page.test.ts` | Pending, retry, completed detail and return behavior through the actual attempt route. |

### Server test boundaries

| Path | Change | Declaration/operation | Contract and guarantees | Dependencies/consumers | Generation/tests |
| --- | --- | --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | Create | Mirrored use-case test | Owner/hierarchy, safe content, legacy ineligibility | Core | Unit |
| `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | Create | Mirrored use-case test | Answers, key replay, same-Skill lock and outbox | Core | Unit |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | Create | Mirrored use-case test | Exact scoring, recomputation, once-only effect | Core | Unit |
| `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` | Create | Mirrored use-case test | Timeout, disclosure, saved result and privacy | Core | Unit |
| `apps/server/tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py` | Create | Mirrored use-case test | Failed-only new run and event | Core | Unit |
| `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` | Create | Mirrored HTTP test | Auth, safe ordered content and 404 | REST/DB | Integration |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | Create | Mirrored HTTP test | Body/status, persistence, key replay, conflict and legacy non-blocking | REST/DB | Integration |
| `apps/server/tests/learning/server/controllers/test_get_choice_attempt_controller.py` | Create | Mirrored HTTP test | Status/result/disclosure and stale expiry | REST/DB | Integration |
| `apps/server/tests/learning/server/controllers/test_retry_choice_evaluation_controller.py` | Create | Mirrored HTTP test | Same attempt/new run, 409 and outbox | REST/DB | Integration |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | Create | Inngest job test | Registered event, durable commit, stale/duplicate/failure | Real Testcontainers | `test:jobs` |

No dedicated tests target repositories, mappers, REST service or query/action
hooks; their behavior is proven at permitted use-case, controller, job, widget
and browser boundaries. Do not create `apps/server/tests/database/**`, route
tests outside `apps/web/tests/routes/learning`, a new event publisher, a Curriculum-authored score,
or a second browser persistence store.

## Migration, rollout and technical decisions

The migration adds nullable columns so existing records remain readable, plus
a partial unique index for non-null submission keys scoped to the Skill
experience. New submissions always populate all new fields. Preflight counts
legacy pending/failed rows and their Skill IDs. Existing pending rows without
a frozen snapshot become terminal `FAILED` with an archival failure code in the
migration; existing failed rows keep their answers/failure state. The unresolved
same-Skill blocker ignores all rows without a grading snapshot/run ID, and the
new result route does not advertise them as retryable. This prevents an old
unscorable attempt from blocking new choice Activities forever. Completed legacy
records remain unchanged and readable as historical metadata. Curriculum's
JSON column needs no schema change;
legacy rows with missing explanations remain unavailable until editorial
backfill. Release requires seeded/published target Activities to pass that
eligibility check before exposing their entry route. No seed reset or existing
data deletion is part of this Contract.

| Decision | Chosen approach | Alternative considered | Reason | Accepted trade-off |
| --- | --- | --- | --- | --- |
| Evaluation handoff | Learning outbox → Inngest job | Request-time scoring | User requires background evaluation after navigation and durable work. | Visible pending and async operational dependency. |
| Submission deduplication | Client key + scoped unique index | Answer/time-window deduplication | Intentional later identical answers remain distinct. | Client must retain key until first result is known. |
| Scoring source | Private snapshot on attempt | Re-read live Curriculum in job | Content edits cannot change a submitted attempt. | Sensitive JSON needs strict private access. |
| Timeout | Resolve pending older than 5 minutes on authenticated read | Indefinite pending or separate scheduler | Supports manual recovery without a new timer service. | Failure becomes visible on next read. |
| Result refresh | 3-second visible polling | Push or manual-only refresh | Meets approved immediate result updates with existing HTTP path. | Short periodic reads while visible. |

The user explicitly chose zero automatic evaluation-job retries. This overrides
the Messaging Rule's general finite-retry guidance for transient job failures;
the required durable outbox delivery retry remains in place. The first failed
job run becomes manually recoverable, and the five-minute stale handoff check
covers an undelivered event.

# 4. Validation Contract

The following are required implementation checks, not evidence of execution in
this Spec task. Server unit tests prove domain/use-case decisions; real HTTP
integration proves authentication, serialization and PostgreSQL effects; the
registered Inngest job is exercised through disposable Inngest/PostgreSQL
Testcontainers; widget tests prove interaction and accessibility state; routed
Playwright route tests prove UI-to-REST behavior with deterministic mocked
transport. Manual CLI scenarios plus server integration prove the persisted
browser/job flow; mocked route coverage is never counted as backend evidence.

| Test file | Test type | Target | Coverage goal |
| --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_get_choice_activity_use_case.py` | unit | Activity read | CA-01/11: owner/release/hierarchy, safe content, legacy ineligibility. |
| `apps/server/tests/learning/core/use_cases/test_submit_choice_activity_use_case.py` | unit | Submission | CA-03: strict answers, scoped replay, lock and one outbox event. |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | unit | Evaluation | CA-04/08/09: exact scores, latest-result recomputation and once-only effect. |
| `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` | unit | Result read | CA-05–CA-08/12: timeout, safe disclosure and durable state. |
| `apps/server/tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py` | unit | Retry | CA-05/09: same attempt, new run/outbox, stale rejection. |
| `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py` | integration | Real Activity GET | CA-01/11: auth, safe response, 404 and legacy content. |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | integration | Real submit POST | CA-03: 400/409/422, safe JSON and PostgreSQL/outbox effects. |
| `apps/server/tests/learning/server/controllers/test_get_choice_attempt_controller.py` | integration | Real attempt GET | CA-05–CA-08/12: status, disclosure, persisted effect and expiry. |
| `apps/server/tests/learning/server/controllers/test_retry_choice_evaluation_controller.py` | integration | Real retry POST | CA-05/09: same attempt, new run and one outbox event. |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | job integration | Registered Learning function/outbox | CA-04/05/09/12: committed event, one effect, duplicate/stale events, failure and deleted Skill. |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/tests/choice-activity-page.test.tsx` | component | Activity page | CA-02/10: selected/disabled/focus/validation states and semantic options. |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/tests/use-choice-activity-page.test.ts` | hook unit | Activity behavior | CA-02/03: forward-only answers, stable key, submit and error recovery. |
| `apps/web/src/ui/learning/widgets/pages/choice-activity-page/choice-question/tests/choice-question.test.tsx` | component | `ChoiceQuestion` | CA-02/10: radio/checkbox labels, selected/disabled, focus and keyboard. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/choice-result-page.test.tsx` | component | Result page | CA-05–CA-08/10: status, safe content, all details and retry action. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/use-choice-result-page.test.ts` | hook unit | Result behavior | CA-05/06/12: visible polling interval, immediate return check, cleanup and retry. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx` | component | `ChoiceResultDetail` | CA-07/08: selected options, safe fixed feedback and released answer. |
| `apps/web/tests/routes/learning/activities.$activityId.route.test.tsx` | browser route | Mocked Activity parent route | CA-01/12: authentication guard, parent `Outlet`, child navigation and URL. |
| `apps/web/tests/routes/learning/activities.$activityId.index.test.tsx` | browser route | Mocked Activity index route | CA-01–CA-03/10/11: question transport states, URL and responsive controls. |
| `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx` | browser route | Mocked attempt index route | CA-05–CA-08/10/12: pending/failure/completed responses and navigation return. |
| `apps/web/tests/learning/choice-activity-page.test.ts` | browser integration | `ChoiceActivityPage` through actual Activity route | CA-01–CA-03/10/11: page composition, selection, submission contract, URL and narrow viewport. |
| `apps/web/tests/learning/choice-result-page.test.ts` | browser integration | `ChoiceResultPage` through actual attempt route | CA-05–CA-08/10/12: status/recovery, disclosure, complete details, request and return behavior. |
| `apps/web/tests/learning/competency-detail-page.test.ts` | browser integration | Parent route | CA-01/12: released Activity entry and correct nested navigation. |

| Test file | Test case | Description | Assertions |
| --- | --- | --- | --- |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | Exact sets and weights | Mix single, multiple, extra/missing, order-varied and unequal weights | Only exact selections score 100; every part exists; final weighted score; no partial credit. |
| `apps/server/tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py` | Recompute after lower repeat | Later lower result replaces same Activity's older result | Baseline fold, progress regression, hard evidence and mastery/focus reflect latest official set. |
| `apps/server/tests/learning/core/use_cases/test_get_choice_attempt_use_case.py` | Protected answer | Wrong answer before/after later correct or mastery | Correct option identities absent until eligible; fixed wrong explanation always safe. |
| `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py` | Private routes and replay | Anonymous, wrong account, malformed, invalid answer, blocked and repeated key | 401/404/422/400/409 as contracted; one attempt/evaluation/outbox; no key leakage. |
| `apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py` | Durable and stale run | Deliver accepted, duplicate and pre-retry run after timeout | Exactly one completed effect/event; stale run exits; failed run remains retryable. |
| `apps/web/src/ui/learning/widgets/pages/choice-result-page/tests/use-choice-result-page.test.ts` | Poll lifecycle | Visible pending, hidden, return, terminal and unmount | Three-second checks only while visible/pending; immediate return check; no orphan timer. |
| `apps/web/tests/routes/learning/activities.$activityId.attempts.$attemptId.index.test.tsx` | Mocked routed result | Model pending, mixed completed, failed/retry and return responses | Final URL, all rendered details and expected requests; no claim about persistence. |
| `apps/web/tests/learning/choice-activity-page.test.ts` | Activity page route flow | Exercise page through actual middleware, route and composition | Final URL, selection/submit UI, mocked method/path/body and visible outcome. |
| `apps/web/tests/learning/choice-result-page.test.ts` | Result page route flow | Exercise page through actual middleware, route and composition | Pending/failure/retry/completed states, visible disclosure, request and return behavior. |

| Acceptance | Automated boundary | Manual scenario | Evidence target |
| --- | --- | --- | --- |
| CA-01 | Server unit/controller; Activity parent and index route suites | VM-01, VM-05 | Evaluation: HTTP/auth and Activity screenshots |
| CA-02 | Activity widget/hook/browser suites | VM-01, VM-02 | Evaluation: interaction/keyboard and screenshots |
| CA-03 | Server unit/controller; Activity hook/browser | VM-01, VM-06, VM-07 | Evaluation: database/outbox and replay |
| CA-04 | Server unit and real job suite | VM-03 | Evaluation: question/final score and job trace |
| CA-05 | Server controller/job; Result widget/hook/browser | VM-03, VM-06, VM-07 | Evaluation: status/retry and persisted run IDs |
| CA-06 | Server controller; Result widget/hook/browser | VM-03, VM-04 | Evaluation: desktop/mobile complete result screenshots |
| CA-07 | Server unit/controller; Result widget/browser | VM-03 | Evaluation: response/DOM disclosure inspection |
| CA-08 | Server unit/controller; Result browser | VM-03, VM-05 | Evaluation: latest-result progress and disclosure |
| CA-09 | Server unit/controller and real job suite | VM-06, VM-07 | Evaluation: one effect/event and deletion check |
| CA-10 | Both widget and browser suites | VM-01–VM-04 | Evaluation: focus, accessibility and viewport screenshots |
| CA-11 | Provider via server unit/controller; Activity browser | VM-05 | Evaluation: unavailable/re-enabled content |
| CA-12 | Server controller/job; Activity parent and attempt index route suites | VM-03, VM-06 | Evaluation: durable return state |

## Manual scenarios

Use a disposable local test account and a published fixture Skill with one
released three-question Activity containing both choice types, fixed
explanations and unequal weights. For four/five-question coverage, publish a
separate fixture Activity. Start only PostgreSQL, Redis, Inngest, FastAPI and web
services required by the scenario; verify `docker compose ps`, API health,
web reachability and Learning job registration before testing. Use Playwright
CLI with an authenticated real browser and actual server persistence. Keep all
credentials out of screenshots and Evaluation. Reset only disposable fixture
records through an authorized fixture path; do not seed/reset shared data.

| VM | CA mapping | Start / viewport / saved reference | Actions and assertions | Evidence / cleanup |
| --- | --- | --- | --- | --- |
| VM-01 | CA-01–CA-03, CA-10 | Released Activity route, 1440 × 900; `o2q7H.png`, `Cj8R7.png` | 1. Open as owner; inspect safe GET and 3–5 question order. 2. Tab/radio/checkbox through both types; reject empty advance, add/remove multi choice, advance and verify no back edit. 3. Submit complete attempt; inspect POST, attempt URL, one DB attempt/evaluation/outbox. 4. Reuse same key through a transport retry; verify same attempt. Check focus, labels, live status, console and failed requests. | Evaluation: fresh desktop question screenshots, URL/HTTP/DB observations; remove disposable fixture only. |
| VM-02 | CA-02, CA-10 | Released Activity route, 390 × 844; `rf857.png` | 1. Select/unselect with touch and keyboard. 2. Check 44 px targets, scroll, focus, no horizontal overflow or bottom-nav obstruction. 3. Trigger leave warning with unsent answers and return; confirm no draft persisted. Inspect console/network. | Evaluation: fresh mobile question/leave-state screenshots and DOM measurements; no shared-data reset. |
| VM-03 | CA-04–CA-08, CA-10/12 | Attempt result route, 1440 × 900; `PCnZO.png`, `YDgNz.png`, `gftrs.png`, `ad7p6.png`, `ntBNV.png` | 1. Observe pending with no score; check GET every 3 seconds while visible. 2. Leave and return; confirm same attempt and immediate GET. 3. On completion inspect final weighted score, all details, fixed feedback, safe response/DOM, progress and action; compare four correctness frames. 4. On later correct attempt or mastery inspect permitted disclosure and possible regression. Check URL, focus/announcements, console, failed requests, persisted official results and outbox effect. | Evaluation: fresh pending, complete and protected/correct desktop screenshots, HTTP/DB/job evidence; disposable fixtures only. |
| VM-04 | CA-06, CA-10 | Attempt result route, 390 × 844; `k3bUS8.png` | 1. Open completed three- and five-question attempts. 2. Scroll through all details; verify no clipping, horizontal overflow or bottom-nav obstruction. 3. Use keyboard through retry/next action where applicable; inspect text/status, focus and reduced-motion behavior, console and failed requests. | Evaluation: fresh mobile complete/long-result screenshots and viewport/DOM checks; no shared-data reset. |
| VM-05 | CA-01, CA-08, CA-11 | Activity route, 1440 × 900; question references | 1. As anonymous/other account/wrong hierarchy inspect 401 or safe 404. 2. Use disposable legacy content missing each explanation, then authored content; verify unavailable before update and eligible after. 3. Inspect no answer flags/explanations in GET or browser state. Check URL, focus, console and failed requests. | Evaluation: HTTP response and access matrix, content fixture states; clean only disposable records. |
| VM-06 | CA-03, CA-05, CA-09/12 | Result route, 1440 × 900; adjacent pending/failure states described in the design handoff | 1. Make a disposable evaluation fail, verify no official score and same-Skill pause; other Skill remains usable. 2. Trigger Tentar novamente, inspect 202/new run and same answer/attempt. 3. Exercise >5-minute pending, late delivery and duplicate event in disposable Inngest setup; verify one effect/event and no Skill recreation after removal. 4. Inspect pending/failure/recovered focus, live status, URL, network and console. | Evaluation: job trace, DB/outbox identities and fresh pending/failure/recovery screenshots; no shared-service teardown. |
| VM-07 | CA-03, CA-05, CA-09 | Disposable PostgreSQL Testcontainer; no browser/design reference | 1. Count legacy unresolved rows and Skill IDs before migration. 2. Upgrade from `e1a2b3c4d5e6` to `f64a8c3d7e21`; verify columns, partial unique index, preserved answers and archival failure classification. 3. Verify duplicate non-null scoped submission key is rejected but null legacy keys remain accepted; a legacy unresolved row does not block a new attempt. 4. Downgrade to `e1a2b3c4d5e6` and re-upgrade on disposable data; verify no lost preexisting attempt/evaluation data and current head. No URL/network/focus assertions apply to this database-only scenario. | Evaluation: preflight counts, Alembic command output, SQL constraint/index checks and row comparison; destroy only the disposable container. |

## Executable commands and REST parity

| CI | Command / working directory | Gate |
| --- | --- | --- |
| CI-01 | `pnpm --filter web check:lint` / root | Web lint |
| CI-02 | `pnpm --filter web check:architecture` / root | Web import boundaries |
| CI-03 | `pnpm --filter web check:types` / root | Web type contracts |
| CI-04 | `pnpm --filter web test:unit` / root | Widget/hook behavior |
| CI-05 | `pnpm --filter web test:integration` / root | Routed browser integration |
| CI-06 | `pnpm --filter web build` / root | Route generation/build |
| CI-07 | `uv run poe check:lint` / `apps/server` | Python lint |
| CI-08 | `uv run poe check:architecture` / `apps/server` | Python boundaries |
| CI-09 | `uv run poe check:types` / `apps/server` | Python typing |
| CI-10 | `uv run poe test:unit` / `apps/server` | Domain/use cases |
| CI-11 | `uv run poe test:integration` / `apps/server` | Real HTTP/PostgreSQL |
| CI-12 | `uv run poe test:jobs` / `apps/server` | Real disposable Inngest job |
| CI-13 | `uv run poe build` / `apps/server` | Server build |
| CI-14 | `uv run poe db:upgrade f64a8c3d7e21` / `apps/server`, disposable DB only | Migration upgrade/preflight |
| CI-15 | `uv run poe db:downgrade e1a2b3c4d5e6` then `uv run poe db:upgrade f64a8c3d7e21` / `apps/server`, disposable DB only | Applicable downgrade/re-upgrade; VM-07 checks index/data |

`apps/server/rest-client/learning/activities.rest` must have one labeled
request for each of the four controller routes, with exact method/path, path
parameters, `Content-Type` where relevant, bearer placeholder variable,
representative complete answer and retry bodies, and no actual credentials.
The REST file is parity evidence; CI-11 and VM-01/03/06 prove actual behavior.

# 5. Documentation alignment and revision history

| Document | Authority for | State | Required change/confirmation |
| --- | --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AYDzB), ID 83066881 v13 | RP-09/10/13–18/25/26, JN-07 | confirmed | Complete page read 2026-09-23 01:20 UTC; partial adjacent outcomes remain separate. No external edit. |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/x/AQDzB), ID 83034113 v6 | RP-03/RP-04, authored content | confirmed | Complete page read; fixed outcome explanations extend the local content contract, with legacy fail-closed rollout. No external edit. |
| [SHIFU-74](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-74) | Delivery source, design links | confirmed | Ticket read; SHIFU-19/20 are dependent capability context, not build order. No external edit. |
| [SDD](../../../sdd.md) | Artifact lifecycle/identifiers | confirmed | Spec, Plan and Evaluation are completed locally; saved design references remain linked. |
| [Architecture](../../../architecture.md) and [Modules](../../../modules.md) | Runtime and business ownership | confirmed | Learning owns official result; Curriculum owns content; shared provider is neutral; Inngest composition follows existing app. |
| [Design system](../../../design.md) and [handoff](./design/handoff.md) | UI tokens and nine visual states | changed | Approved Pencil frames saved; runtime uses existing tokens and fresh comparison screenshots. |
| [Tooling](../../../tooling.md) | Real commands/services | confirmed | CI-01–CI-15 correspond to current manifests/tooling. |

| Rule | Applies to | Evaluated revision |
| --- | --- | --- |
| `documentation/rules/python-conventions-rules.md` | Server code/tests | 2026-09-23 worktree |
| `documentation/rules/typescript-conventions-rules.md` | Web code/tests | 2026-09-23 worktree |
| `documentation/rules/core-layer-rules.md` | Domain/interfaces/use cases | 2026-09-23 worktree |
| `documentation/rules/use-case-testing-rules.md` | Server unit boundary | 2026-09-23 worktree |
| `documentation/rules/database-layer-rules.md` | Mapper/model/repository/migration | 2026-09-23 worktree |
| `documentation/rules/provision-layer-rules.md` | Curriculum provider/clock/IDs | 2026-09-23 worktree |
| `documentation/rules/rest-layer-rules.md` | Controllers/schemas/web REST | 2026-09-23 worktree |
| `documentation/rules/controllers-testing-rules.md` | Real HTTP integration | 2026-09-23 worktree |
| `documentation/rules/server-app-layer-rules.md` | Pipe/app registration | 2026-09-23 worktree |
| `documentation/rules/messaging-layer-rules.md` | Event/outbox/Inngest | 2026-09-23 worktree |
| `documentation/rules/jobs-testing-rules.md` | Real job tests | 2026-09-23 worktree |
| `documentation/rules/ui-layer-rules.md` | Activity/result widgets | 2026-09-23 worktree |
| `documentation/rules/web-app-routing-rules.md` | TanStack routes/generated tree | 2026-09-23 worktree |
| `documentation/rules/widget-testing-rules.md` | Widget and Playwright boundaries | 2026-09-23 worktree |

| Revision | Date | Material change | Reason |
| --- | --- | --- | --- |
| 1 | 2026-09-23 | Created choice-Activity Contract, private snapshot/job/recovery boundaries, fixed explanations and nine-frame design handoff. | SHIFU-74, canonical PRDs and confirmed grilling decisions. |
| 2 | 2026-09-23 | Added a dedicated mocked Playwright suite for the Activity parent route and aligned all three suite names with their route files. | Web Routing Rule requires one integration suite per new route file before planning. |
| 3 | 2026-09-23 | Added module-owned Playwright suites for both routed Page widgets in addition to the three route-file suites, and named the Activity DTO `kind` wire values. | Reconciliation of both Web test Rules and a fixed cross-Builder wire contract. |

## 6. Implementation outcome

Spec revision 3 is implemented and independently reviewed. The Learning Activity
question flow now covers Curriculum snapshots, immutable attempts, official async
evaluation, safe result disclosure, responsive question/result Pages, nested routes,
and the matching four-operation REST client. Current acceptance and runtime evidence,
findings, selected PRD dispositions and validation results are recorded in
[evaluation.md](./evaluation.md). No Confluence PRD checkbox or Jira status was changed.
