---
title: Learning Activity fill-in-the-blank questions with a word bank
status: ready
revision: 2
source:
  type: issue
  ref: "https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-123"
scope:
  - apps/server/src/shifu/curriculum
  - apps/server/src/shifu/shared/core
  - apps/server/src/shifu/learning
  - apps/server/src/shifu/shared/database
  - apps/web
  - documentation/features/learning/fill-blanks-question
last_updated_at: 2026-11-17
---

# Objective

Deliver the Learning Activity **fill-in-the-blank with a word bank** question
("lacunas com banco de palavras"). The learner fills every blank of a
Curriculum-defined text by dragging a bank word onto a blank or by selecting a
word and then a blank. Mouse, touch and keyboard all reach the same result. The
learner gets equal credit for each correct blank:
`score = 100 × correct blanks ÷ total blanks`. Grading, provisional feedback and
per-Concept evidence are objective and predefined by Curriculum. This format
never uses AI or the Mentor.

This is a **complete** Spec. It crosses Curriculum (content and invariants),
Shared (the provider-neutral snapshot), Learning (answers, scoring, Concept
evidence, attempts, history and disclosure), persistence of JSON answers and
results, the REST contract, the development seed and the web Activity and
result UI. The official evaluation reuses the existing Inngest evaluation job.

## Current behavior and product gap

On `main` (`9b606f4b`), Curriculum's `ActivityQuestion` union supports single
choice, multiple selection and the code kinds only. Learning's `ActivityAnswer`
and `EvaluationPartResult` unions and the web `ActivityQuestion`/`ActivityAnswer`
types have no fill-blanks shape.

The mixed `CurriculumLearningActivitySnapshot` path is selected only when an
Activity contains a code question. Choice-only Activities use
`CurriculumChoiceActivitySnapshot`.

No drag-and-drop library is installed in `apps/web`. The development seed has
no English Skill.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Content (Curriculum) | Fill-blanks question: text segments, one or more blanks, accepted words per blank, word-bank occurrences (repeated words are distinct, equivalent occurrences; optional distractors), content language, three predefined explanations, objective Concept criteria mapped to blanks; content invariants including a complete solution without reusing occurrences | Diagnostic Activities; authoring through the UI; dynamic question generation; a complete English curriculum |
| Composition | Learning Activities with three to five questions, mixing fill-blanks with every existing Learning question kind | Changes to the composition rule or to diagnostic content |
| Interaction (learner) | Drag-and-drop and select-word-then-blank by mouse, touch and keyboard; remove and replace until the learner advances; a replaced word returns to the bank; no automatic swap between blanks | Word or phrase ordering; per-blank correctness marks in provisional feedback (decision Q3) |
| Provisional feedback | Stateless, per question: the submitted fill, score, correct-blank count and the predefined explanation; no attempt, official grade, progress or reward | Persisting provisional feedback across devices (RP-09 reserves that for step ordering) |
| Official evaluation | Immutable attempt created only on final submission; equal-credit scoring; Activity grade by Curriculum weights; per-Concept evidence as the proportion of the Concept's mapped blanks that are correct (decision Q2); one coherent progress effect; Shifu-failure recovery of the same attempt | New progress, mastery or recommendation rules |
| Result and history | Provisional, official and history views show the submitted fill, score, count and explanation; the expected fill is disclosed only after a later fully correct attempt of that question or Competency mastery | Revealing expected words earlier |
| UI | Desktop and mobile question widget; feedback and result rendering; pt-BR controls with content marked in the studied language | New routes; visual changes to other question kinds |
| Example content | One fictional English Skill in the development seed, with a Learning Activity that holds three fill-blanks questions and one single-choice question, plus the diagnostic content needed to reach learning | Official curriculum content |

Selected outcomes:

- Curriculum RP-03 (fill-blanks rules) and RP-04 (Learning reads the rules and
  evaluation needed): **full** for this format.
- Learning RP-09, RP-13, RP-14, RP-15, RP-18, RP-20, RP-25 and RP-27:
  **partial**. Their general attempt, evaluation, recovery, progress, history
  and review machinery already exists and is extended to the new kind without
  changing its rules.
- Journeys: Learning JN-07, JN-08 and JN-13; Curriculum JN-03 and JN-04.

Penpot boards: see the Design Contract. Their availability is a readiness
blocker until verified (decision Q5).

# Behavior Contract

| ID | RP/JN/source coverage | Observable required behavior |
| --- | --- | --- |
| RF-01 | Curriculum RP-03, JN-03 | A fill-blanks question defines a prompt, a content language, ordered text segments that reference each blank exactly once, one or more blanks with one or more accepted words each, and word-bank occurrences with distinct keys. The bank may contain distractors and repeated words. It defines a correct explanation and an incorrect explanation, plus a partial explanation when the question has two or more blanks. Each Concept criterion maps a Concept to one or more blanks with objective criterion text, examples and limits. Content is rejected unless a complete correct fill exists with each occurrence used at most once. |
| RF-02 | Curriculum RP-03; Learning RP-13 | Fill-blanks questions exist only in Learning Activities. Diagnostic Activities that contain them are rejected by Curriculum, never published by the content provider, and never presented. Correction, feedback and evidence never call an AI provider or the Mentor. |
| RF-03 | Curriculum RP-04; Learning RP-09, RP-18 | Opening an Activity exposes the prompt, content language, segments, blank keys and bank occurrences in Curriculum order. Accepted words, Concept criteria and the answer key never leave the server before disclosure. |
| RF-04 | Learning RP-09, RP-25, JN-07 | The learner places an occurrence in a blank by dragging it, or by selecting a word and then a blank, with mouse, touch or keyboard. Each occurrence occupies at most one blank. Placing into an occupied blank returns the previous occurrence to the bank, without moving words between blanks. The learner can remove a placed word. All of this is allowed until the learner advances past the question. |
| RF-05 | Learning RP-25 | Focus, the selected word, filled blanks and feedback outcome are announced to assistive technology and shown with text or icon, not color alone. Controls and guidance are in pt-BR. Segments and bank words carry the Curriculum content language. Desktop and mobile layouts keep every control reachable. |
| RF-06 | Learning RP-09, JN-07 | Checking the question or advancing requires every blank to be filled with distinct, existing occurrences. A complete answer may be wrong. The server rejects incomplete, duplicated, unknown or foreign-kind answers without effects. |
| RF-07 | Curriculum RP-03; Learning RP-13 | Question score = 100 × correct blanks ÷ total blanks (Decimal, quantized to two decimals, `ROUND_HALF_UP`). All blanks weigh the same. A blank is correct when the placed occurrence's word is one of that blank's accepted words, so occurrences of the same word are equivalent. The question score enters the Activity grade through its Curriculum part weight. |
| RF-08 | Learning RP-09, RP-13, RP-18, JN-07 | Provisional feedback for the current fill returns the score, correct-blank count, blank count and the predefined explanation. The explanation is correct at 100, partial between 0 and 100, and incorrect at 0. Feedback creates no attempt, evaluation, progress, evidence or reward. It does not mark which blanks are right or wrong. Editing after feedback clears it. A fresh check is needed before advancing. |
| RF-09 | Learning RP-09, JN-07 | The Activity shows one question at a time with difficulty, position, total and progress bar. Advancing is sequential and the UI cannot return to edit an earlier question. Only the final submission creates the immutable attempt, with the placements the learner had when advancing. A replay with the same submission key and answers returns the same attempt. A replay with different answers is a conflict. |
| RF-10 | Curriculum RP-03; Learning RP-13, RP-15, RP-27 | The official evaluation stores, per fill-blanks question, the score, correct-blank keys, blank count and explanation. Each mapped Concept gets evidence `100 × correct mapped blanks ÷ mapped blanks`, distinct from the question score. Existing aggregation applies: when several questions map the same Concept, their average forms one Activity contribution, and progress, mastery and recommendation update once. |
| RF-11 | Learning RP-14, JN-08 | A Shifu failure during evaluation keeps the submitted placements. Retry re-evaluates the same attempt without a new submission. Reprocessing never duplicates results or pedagogical effects. While an evaluation is pending or failed in the Skill, new submissions in that Skill are blocked. |
| RF-12 | Learning RP-18, RP-20, JN-13 | The official result and attempt history show the submitted fill read-only, the score, the correct-blank count and the explanation. The expected fill (accepted words per blank) is disclosed only after a fully correct evaluation of that question (the same attempt or a later one in the same Activity), or after the Competency is mastered, matching the choice-question precedent. Attempts sent after Skill completion are recorded as review attempts without changing preserved results. |
| RF-13 | Learning RP-09, RP-14; `AGENTS.md` isolation | Every read and write checks that the Goal and Skill experience belong to the authenticated account and that the content revision is current. Another account's experience is reported as not found, with no effects. |
| RF-14 | SHIFU-123 scope ("exemplos em inglês") | The development seed provides a fictional English Skill with an eligible Learning Activity of three fill-blanks questions and one single-choice question. Its fill-blanks content covers multiple blanks, two accepted words for one blank, a distractor and a repeated word. The seed has the diagnostic content needed to start the Skill, and a seeded learner experience already in learning with the Competency released. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Content with several blanks, a blank with two accepted words, a distractor and a repeated word | The question is constructed | It is accepted and its normalized values are preserved | CI-01 |
| CA-02 | RF-01, RF-02 | Invalid content (Curriculum structures and the Shared snapshot): no blanks; a blank without accepted words; duplicate blank or occurrence keys; a segment referencing an unknown blank; a blank absent from segments or referenced twice; an unsatisfiable bank (needs reuse or lacks a word); a Concept criterion without blanks or with an unknown blank; a missing required explanation; a partial explanation on a one-blank question; a diagnostic Activity containing the question | Construction or Activity creation runs | Curriculum raises `InvalidActivityError`; the Shared snapshot raises `ValidationError` | CI-01 |
| CA-03 | RF-02, RF-03, RF-13 | A released Learning Activity mixing fill-blanks and single choice | The owner opens it | 200 with segments, blank keys, bank occurrences in Curriculum order and `contentLanguage`, and no accepted words or Concept criteria in the body; another account gets 404 | CI-03, CI-07 |
| CA-04 | RF-04, RF-05 | The question widget with an empty fill | The learner selects a word then a blank by click, by Enter/Space and by a drag; places a second word into the same blank; removes a placed word | Each placement uses the chosen occurrence once, the replaced occurrence returns to the bank, no other blank changes, removal empties the blank, and each change is announced in the live region with pt-BR text | CI-09 |
| CA-05 | RF-05 | The widget in empty, selected, filled and feedback states | It is rendered | Blanks and words expose pt-BR accessible names and pressed/filled state, content nodes carry `lang`, outcome labels use text and icon | CI-09, VM-03..VM-06 |
| CA-06 | RF-06, RF-08, RF-09 | A fill-blanks question inside the Activity page | Blanks are partly filled; then fully filled and checked; then edited; then checked again and advanced | Check is disabled while incomplete; feedback appears after check; editing clears feedback and requires a new check; advancing locks the question and the previous question cannot be edited | CI-10 |
| CA-07 | RF-07, RF-08 | A three-blank question | Provisional feedback is requested with 0, 1 and 3 correct blanks, and with a repeated-word occurrence in place of its twin | Scores 0, 33.33 and 100 with the incorrect, partial and correct explanations; twin occurrences score the same; no attempt, evaluation or progress repository write | CI-02 |
| CA-08 | RF-06, RF-13 | A provisional-feedback request | The fill is incomplete, repeats an occurrence, names an unknown occurrence or blank, has another kind, has a stale revision or targets another account | 400, 400, 400, 400, 409 and 404 respectively, with no persisted effect | CI-02, CI-04 |
| CA-09 | RF-06, RF-09 | Final submission of a mixed Activity | Answers are complete; then the same key is replayed; then the same key is sent with different placements; then an incomplete fill is sent | 201 with a pending attempt persisted with placements and a pending evaluation and outbox event; replay returns 200 with the same attempt; conflict 409; incomplete 400 with no attempt row | CI-03, CI-05 |
| CA-10 | RF-07, RF-10 | A pending attempt with fill-blanks scores 0, partial and 100 and a Concept mapped to two blanks with one correct | The evaluation runs | Part scores follow RF-07; the Activity grade uses part weights; the Concept observation is 50, independent of the question score; one progress update is applied | CI-02 |
| CA-11 | RF-10, RF-11 | An evaluation that already completed, or a stale run | The evaluation is processed again | No second evaluation, observation or progress change is written | CI-02, CI-08 |
| CA-12 | RF-11 | A failed evaluation of a fill-blanks attempt | Retry is requested | The same attempt is re-queued with its stored placements and no new attempt is created | CI-02 |
| CA-13 | RF-09, RF-10, RF-11 | A seeded fill-blanks attempt and its outbox event | The registered Inngest job processes it, including a duplicate delivery | The evaluation completes once with the expected part results and Concept observation | CI-08 |
| CA-14 | RF-12 | An incorrect or partial fill-blanks result | The owner views the attempt before any later fully correct attempt and without mastery; then after a later fully correct attempt; then for a mastered Competency | The first view shows submitted fill, score, count and explanation without expected words; the later views include the expected accepted words per blank | CI-02, CI-06 |
| CA-15 | RF-12 | A Skill experience in completed status | A fill-blanks Activity is submitted and evaluated | The attempt kind is review and preserved progress, mastery and completion do not change | CI-02 |
| CA-16 | RF-08, RF-12, RF-05 | Feedback and result payloads at 100, partial and 0 | The feedback and result detail render | Labels "Resposta correta", "Parcialmente correta" or "Resposta incorreta" with icon, "N de M lacunas corretas", the explanation and the read-only fill; the expected fill appears only when disclosed | CI-10, CI-11 |
| CA-17 | RF-03..RF-12, RF-14 | The seeded English experience with the real web and API | The learner fills by drag and by selection, checks, edits, advances, submits and opens the result and history on desktop and mobile | The journey completes with the outcomes above, no console errors and a working keyboard path | VM-01, VM-02, CI-12 |
| CA-19 | RF-01, RF-03 | A fill-blanks question whose Concept criterion names a Concept outside the Activity's Competency | The owner opens the Activity | The provider does not publish it, and the response is 404 with no partial projection | CI-07 |
| CA-20 | RF-02 | A diagnostic batch submission | An item answer has `kind: 'fill_blanks'` | 422, no attempt, evaluation or outbox row; a choice answer is not rejected by the validator | CI-17 |
| CA-18 | RF-05 | Required states and viewports | Fresh captures are compared with fresh Penpot exports | Layout, hierarchy, tokens and states match within accepted deviations | VM-03..VM-06 |

## Design Contract

**Readiness blocker:** the Penpot MCP is not connected in this session, so
none of the boards below has been verified. SHIFU-123 names the frames
"Atividade / Lacunas — Inglês" and "Atividade / Lacunas — preenchidas" on the
Desktop page of `shifu.fig`. `AGENTS.md` makes `shifu.fig` a historical record
only. Before `ready`, inspect the Shifu Penpot file and:

- replace each "pending" cell below with the actual page, board and component
  names;
- confirm that mobile boards exist, or record an explicitly accepted visual
  assumption.

| Surface / route | State / viewport | Penpot page / board / components | CA / Visual check | Allowed deviations |
| --- | --- | --- | --- | --- |
| Activity page, fill-blanks question | Empty fill / desktop 1440×900 | Desktop / "Atividade / Lacunas — Inglês" (pending verification) | CA-18 / VM-03 | Real seed copy and word count |
| Activity page, fill-blanks question | Filled with provisional feedback (partial) / desktop 1440×900 | Desktop / "Atividade / Lacunas — preenchidas" (pending verification) | CA-18 / VM-04 | Feedback copy from seed |
| Activity page, fill-blanks question | Empty and filled / mobile 390×844 | Mobile / matching boards (pending; to be confirmed in Penpot) | CA-18 / VM-05 | Same as desktop |
| Result page, fill-blanks result detail | Partial result, expected fill hidden / desktop and mobile | Pending verification in Penpot | CA-18 / VM-06 | None beyond seed copy |

Token and primitive mapping, kept consistent with `documentation/design.md`
and the existing choice question:

- Bank words and blank slots render through the shadcn `Button` primitive. The
  `outline` variant is used for idle words and empty blanks. The selected word
  uses the `--accent` background with a `--selo-text` border and a visible
  "Selecionada" text marker, mirroring `choice-question.css`.
- Filled blanks keep the `--border` and `--muted` surfaces.
- Focus uses the shared visible focus treatment (2px `--foreground` outline).
- Feedback reuses the `QuestionFeedback` surface. Its outcome icon uses the
  shared `Icon` component with the existing `IconName` values `circle-check`
  (correct), `circle-alert` (partial) and `x` (incorrect). `QuestionFeedback` has no
  icon map today, so `useQuestionFeedback` owns the band-to-label-and-icon
  mapping.
- Question header, progress and navigation reuse `ActivityQuestionHeader` and
  the Activity page footer unchanged.

Preserved UI: other question kinds, the Activity header and progress, and the
result page layout outside the new fill-blanks detail.

# Technical Contract

## Architecture Mapping

Owner: Learning for answers, evaluation, evidence and history. Curriculum owns
content. Shared owns only the provider-neutral snapshot.

Rules:

- Server: [Python](../../../rules/python-conventions-rules.md),
  [Provider Layer](../../../rules/provision-layer-rules.md) (the Curriculum
  content provider changes; it gets no test file of its own),
  [Core](../../../rules/core-layer-rules.md),
  [Use Case Testing](../../../rules/use-case-testing-rules.md),
  [REST](../../../rules/rest-layer-rules.md),
  [Controller Testing](../../../rules/controllers-testing-rules.md),
  [Database](../../../rules/database-layer-rules.md) and
  [Job Testing](../../../rules/jobs-testing-rules.md).
- Web: [TypeScript](../../../rules/typescript-conventions-rules.md),
  [UI](../../../rules/ui-layer-rules.md) and
  [Widget Testing](../../../rules/widget-testing-rules.md).

Routing and Validation Package Rules are not selected because no route or
reusable Zod schema changes. Messaging Rules are not selected: the job, events,
outbox and brokers are unchanged. The seed adds Curriculum and Learning rows
only and writes no outbox events, so the seed-composition combination adds no
messaging obligation.

**Selected approach.** Fill-blanks is objective and AI-free. It follows the
synchronous choice pattern:

- the preview is computed on request and never persisted;
- grading is deterministic inside `EvaluateChoiceActivityUseCase`;
- answers and part results persist in the existing JSON `answers`,
  `grading_snapshot` and evaluation `parts` columns, so no Alembic migration is
  needed;
- any Activity containing a fill-blanks question uses the mixed
  `CurriculumLearningActivitySnapshot`, the same way code Activities do;
- the existing destination predicate already routes non-code mixed attempts to
  the Inngest job, so the AgentOS registry and workflow stay unchanged.

The delivery starts from `main` (decision Q1). Conflicts with open PR #52
(SHIFU-122) are reconciled when either one merges, keeping both kinds.

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Curriculum core | `FillBlanksQuestion`, `FillBlanksSegment`, `FillBlanksBlank`, `FillBlanksBankWord`, `FillBlanksConceptCriterion` under `curriculum/core/domain/structures/` | Content structures with the RF-01 invariants and the solvability check; exported from the structures barrel |
| Modify | Curriculum core | `ActivityQuestion` in `activity_question.py`; `Activity` in `curriculum/core/domain/entities/activity.py` | Union gains `FillBlanksQuestion`; Activity requires a `CorrectnessEvaluationPart` for it and rejects it in diagnostic Activities |
| Modify | Curriculum database | `ActivityMapper` in `curriculum/database/sqlalchemy/mappers/activity_mapper.py` | Maps `kind: 'fill_blanks'` question JSON both ways, through a `kind` branch placed before the generic `'kind' in data` rejection; no schema change |
| Modify | Curriculum provider | `CurriculumContentProvider._get_activity` / `get_skill_content` in `curriculum/providers/curriculum_content_provider/curriculum_content_provider.py` | Publishes `CurriculumFillBlanksQuestionSnapshot` with a `CurriculumChoicePartSnapshot` weight. Returns `None` when a criterion Concept is outside the Activity's Competency. `get_choice_activity` keeps returning `None` for Activities with fill-blanks. The projection and Concept check live in a new Curriculum-owned `FillBlanksSnapshotProjection` (`fill_blanks_snapshot_projection.py`, same package), called from both methods, so no branching is added under their existing `# noqa: C901` |
| Create | Shared core | `CurriculumFillBlanksQuestionSnapshot`, `CurriculumFillBlanksSegmentSnapshot`, `CurriculumFillBlanksBlankSnapshot`, `CurriculumFillBlanksWordSnapshot`, `CurriculumFillBlanksConceptCriterionSnapshot` under `shared/core/domain/structures/` | Provider-neutral snapshot including the answer key (server-only) |
| Modify | Shared core | `CurriculumLearningActivitySnapshot` | `questions` union gains the fill-blanks snapshot; it pairs with `CurriculumChoicePartSnapshot` and is rejected when `activity_type == 'diagnostic'` |
| Create | Learning core | `FillBlanksAnswer`, `FillBlanksPlacement`, `FillBlanksEvaluationResult`, `FillBlanksQuestionDetail`, `FillBlanksSegmentDetail`, `FillBlanksWordDetail`, `FillBlanksResultDetail`, `FillBlanksExpectedBlank` under `learning/core/domain/structures/` | Answer, persisted result, public question projection and result projection |
| Modify | Learning core | `ChoiceActivityDetail.questions` (`choice_activity_detail.py`), `ChoiceAttemptDetail.questions` (`choice_attempt_detail.py`) | Projection unions gain `FillBlanksQuestionDetail` and `FillBlanksResultDetail` |
| Modify | Learning core | `ActivityAnswer` (`activity_answer.py`), `EvaluationPartResult` (`evaluation_part_result.py`) | Unions gain `FillBlanksAnswer` and `FillBlanksEvaluationResult`; the preview and submit inputs widen from `ChoiceAnswerSubmission \| CodeAnswer` to also accept `FillBlanksAnswer` (`ChoiceAnswerSubmission` itself is unchanged) |
| Create | Learning core | `FillBlanksScoring` in `learning/core/use_cases/fill_blanks_scoring.py` | Static operations shared by preview, submit and evaluation: `normalize(question, answer)`, `score(question, answer)` and `concept_observations(question, result)`; not a use case and has no I/O |
| Modify | Learning core | `GetChoiceActivityUseCase`, `PreviewActivityQuestionFeedbackUseCase`, `SubmitChoiceActivityUseCase`, `EvaluateChoiceActivityUseCase`, `GetChoiceAttemptUseCase` | The mixed-snapshot predicate also matches fill-blanks. Each use case projects, previews, normalizes, scores, observes Concepts and discloses fill-blanks as specified. Disclosure treats a fully correct `FillBlanksEvaluationResult` like a correct choice |
| Modify | Learning database | `ActivityAttemptMapper`, `ActivityEvaluationMapper` | Serialize and deserialize `kind: 'fill_blanks'` answers, grading snapshots and part results in the existing JSON columns. The `kind` branch comes before the legacy `is_correct`/`options` heuristics, and legacy rows stay readable (see Persistence discriminators) |
| Modify | Learning REST | `get_choice_activity_controller.py`, `preview_activity_question_feedback_controller.py`, `submit_choice_activity_controller.py`, `get_choice_attempt_controller.py` | Request and response models gain the fill-blanks variants (below); routes, paths and statuses unchanged |
| Modify | Learning REST (shared request consumer) | `SubmitDiagnosticBatchController` in `submit_diagnostic_batch_controller.py` | It reuses `AnswerRequest`. Diagnostic behavior stays unchanged. The controller-local `ItemRequest` model gains a Pydantic validator that rejects any answer with `kind == 'fill_blanks'`, so the shared request-validation handler returns 422 before the use case runs and placements are never coerced into `ChoiceAnswerSubmission`. The OpenAPI schema still lists the shared kind literal, which is a documented transport-schema difference only. `SubmitDiagnosticBatchUseCase` and its `DiagnosticSubmissionItem.answers` type (`ChoiceAnswerSubmission \| CodeAnswer`) are unchanged. It calls `SubmitChoiceActivityUseCase.normalize_answers`, and diagnostic snapshots can never contain fill-blanks questions (RF-02) |
| Modify | API examples | `apps/server/rest-client/learning/activities.rest` | Non-secret preview and submit examples with `fill_blanks` answers |
| Modify | Development seed | `shared/database/seed_data.py`; new `curriculum/database/english_fill_blanks_seed.py` | RF-14 content and seeded experience; no seed-specific test module |
| Unchanged consumer | Learning messaging and AI | `evaluate_choice_activity_job.py`, `learning_workflows_registry.py`, `retry_choice_evaluation_use_case.py` | Must keep routing non-code mixed attempts to `inngest` and re-queuing the stored attempt; covered by CI-02 and CI-08 |
| Modify | Web core | `apps/web/src/core/learning/choice-activity.ts` | Adds `FillBlanksQuestion`, `FillBlanksAnswer`, `FillBlanksResultQuestion` and extends `PreliminaryQuestionResult` and the unions |
| Modify | Web REST | `apps/web/src/rest/services/learning-service.ts` | Maps the fill-blanks question, answer, preview and result shapes |
| Create | Web UI | `activity-page/fill-blanks-question/**` | Question widget tree (below) |
| Modify | Web UI | `activity-page/index.tsx`, `use-activity-page.ts`, `question-feedback/index.tsx`, `choice-result-page/choice-result-detail/index.tsx` plus a new `fill-blanks-result/` child | Render, answer ownership, check gating, labels and disclosed expected fill |
| Modify | Web manifest | `apps/web/package.json`, `pnpm-lock.yaml` | Adds `@dnd-kit/core` (decision Q4) with the version pinned by the lockfile |

### Expected file tree

```text
apps/server/
├── rest-client/learning/activities.rest                                   [M]
├── src/shifu/
│   ├── curriculum/
│   │   ├── core/domain/
│   │   │   ├── entities/activity.py                                       [M]
│   │   │   └── structures/
│   │   │       ├── __init__.py                                            [M]
│   │   │       ├── activity_question.py                                   [M]
│   │   │       ├── fill_blanks_bank_word.py                               [N]
│   │   │       ├── fill_blanks_blank.py                                   [N]
│   │   │       ├── fill_blanks_concept_criterion.py                       [N]
│   │   │       ├── fill_blanks_question.py                                [N]
│   │   │       └── fill_blanks_segment.py                                 [N]
│   │   ├── database/
│   │   │   ├── english_fill_blanks_seed.py                                [N]
│   │   │   └── sqlalchemy/mappers/activity_mapper.py                      [M]
│   │   └── providers/curriculum_content_provider/
│   │       ├── curriculum_content_provider.py                             [M]
│   │       └── fill_blanks_snapshot_projection.py                         [N]
│   ├── shared/
│   │   ├── core/domain/structures/
│   │   │   ├── __init__.py                                                [M]
│   │   │   ├── curriculum_fill_blanks_blank_snapshot.py                   [N]
│   │   │   ├── curriculum_fill_blanks_concept_criterion_snapshot.py       [N]
│   │   │   ├── curriculum_fill_blanks_question_snapshot.py                [N]
│   │   │   ├── curriculum_fill_blanks_segment_snapshot.py                 [N]
│   │   │   ├── curriculum_fill_blanks_word_snapshot.py                    [N]
│   │   │   └── curriculum_learning_activity_snapshot.py                   [M]
│   │   └── database/seed_data.py                                          [M]
│   └── learning/
│       ├── core/domain/structures/
│       │   ├── __init__.py                                                [M]
│       │   ├── activity_answer.py                                         [M]
│       │   ├── choice_activity_detail.py                                  [M]
│       │   ├── choice_attempt_detail.py                                   [M]
│       │   ├── evaluation_part_result.py                                  [M]
│       │   ├── fill_blanks_answer.py                                      [N]
│       │   ├── fill_blanks_evaluation_result.py                           [N]
│       │   ├── fill_blanks_expected_blank.py                              [N]
│       │   ├── fill_blanks_placement.py                                   [N]
│       │   ├── fill_blanks_question_detail.py                             [N]
│       │   ├── fill_blanks_result_detail.py                               [N]
│       │   ├── fill_blanks_segment_detail.py                              [N]
│       │   └── fill_blanks_word_detail.py                                 [N]
│       ├── core/use_cases/
│       │   ├── evaluate_choice_activity_use_case.py                       [M]
│       │   ├── fill_blanks_scoring.py                                     [N]
│       │   ├── get_choice_activity_use_case.py                            [M]
│       │   ├── get_choice_attempt_use_case.py                             [M]
│       │   ├── preview_activity_question_feedback_use_case.py             [M]
│       │   └── submit_choice_activity_use_case.py                         [M]
│       ├── database/sqlalchemy/mappers/
│       │   ├── activity_attempt_mapper.py                                 [M]
│       │   └── activity_evaluation_mapper.py                              [M]
│       └── rest/controllers/
│           ├── submit_diagnostic_batch_controller.py                      [M]
│           ├── get_choice_activity_controller.py                          [M]
│           ├── get_choice_attempt_controller.py                           [M]
│           ├── preview_activity_question_feedback_controller.py           [M]
│           └── submit_choice_activity_controller.py                       [M]
└── tests/
    ├── curriculum/core/domain/test_fill_blanks_question.py                [N]
    ├── learning/core/use_cases/
    │   ├── test_evaluate_choice_activity_use_case.py                      [M]
    │   ├── test_get_choice_activity_use_case.py                           [M]
    │   ├── test_get_choice_attempt_use_case.py                            [M]
    │   ├── test_preview_activity_question_feedback_use_case.py            [M]
    │   ├── test_retry_choice_evaluation_use_case.py                       [M]
    │   └── test_submit_choice_activity_use_case.py                        [M]
    ├── learning/server/controllers/
    │   ├── test_submit_diagnostic_batch_controller.py                     [N]
    │   ├── test_get_choice_activity_controller.py                         [M]
    │   ├── test_get_choice_attempt_controller.py                          [M]
    │   ├── test_preview_activity_question_feedback_controller.py          [M]
    │   └── test_submit_choice_activity_controller.py                      [M]
    └── messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py  [M]

apps/web/
├── package.json                                                           [M]
├── src/
│   ├── core/learning/
│   │   ├── choice-activity.ts                                             [M]
│   │   └── fakers/
│   │       ├── fill-blanks-question-faker.ts                              [N]
│   │       └── index.ts                                                   [M]
│   ├── rest/services/learning-service.ts                                  [M]
│   └── ui/learning/widgets/pages/
│       ├── activity-page/
│       │   ├── index.tsx                                                  [M]
│       │   ├── use-activity-page.ts                                       [M]
│       │   ├── question-feedback/
│       │   │   ├── index.tsx                                              [M]
│       │   │   └── use-question-feedback.ts                               [M] band → label and icon, "N de M" text
│       │   ├── fill-blanks-question/                                      [N]
│       │   │   ├── index.tsx                  DndContext, live region, composition
│       │   │   ├── use-fill-blanks-question.ts selection, place/remove/replace, drag end, announcements
│       │   │   ├── fill-blanks-question.css
│       │   │   ├── fill-blanks-text/
│       │   │   │   ├── index.tsx              pure renderer of segments
│       │   │   │   └── blank-slot/
│       │   │   │       ├── index.tsx
│       │   │   │       └── use-blank-slot.ts  droppable + draggable placed word
│       │   │   ├── word-bank/
│       │   │   │   ├── index.tsx              pure renderer of available occurrences
│       │   │   │   └── bank-word/
│       │   │   │       ├── index.tsx
│       │   │   │       └── use-bank-word.ts   draggable occurrence
│       │   │   └── tests/
│       │   │       ├── fill-blanks-question.test.tsx
│       │   │       └── use-fill-blanks-question.test.ts
│       │   └── tests/
│       │       ├── activity-page.test.tsx                                 [M]
│       │       └── use-activity-page.test.ts                              [M]
│       └── choice-result-page/choice-result-detail/
│           ├── index.tsx                                                  [M]
│           ├── fill-blanks-result/                                        [N]
│           │   ├── index.tsx
│           │   └── use-fill-blanks-result.ts  placed word per blank, band label, disclosed words
│           └── tests/choice-result-detail.test.tsx                        [M]
└── tests/learning/
    ├── activity-page.test.ts                                              [M]
    └── choice-result-page.test.ts                                         [M]
pnpm-lock.yaml                                                             [M]
```

### Content and snapshot declarations

Curriculum core (one class per module; validation raises `InvalidActivityError`):

```python
@structure
class FillBlanksSegment:
    text: str | None = None       # exactly one of text / blank_key is set
    blank_key: str | None = None

@structure
class FillBlanksBlank:
    key: str
    accepted_words: tuple[str, ...]   # non-empty, distinct, non-blank

@structure
class FillBlanksBankWord:
    key: str                          # unique per question; repeated words get distinct keys
    word: str

@structure
class FillBlanksConceptCriterion:
    concept_id: str
    criterion: str
    examples: str
    limits: str
    blank_keys: tuple[str, ...]       # non-empty, distinct, subset of the question's blanks

@structure
class FillBlanksQuestion:
    key: str
    prompt: str                       # pt-BR instruction
    content_language: str             # BCP 47 tag, e.g. 'en'
    segments: tuple[FillBlanksSegment, ...]
    blanks: tuple[FillBlanksBlank, ...]
    bank: tuple[FillBlanksBankWord, ...]
    correct_explanation: str
    incorrect_explanation: str
    partial_explanation: str | None   # required iff len(blanks) >= 2
    concept_criteria: tuple[FillBlanksConceptCriterion, ...]  # non-empty, distinct concept ids
    kind: Literal['fill_blanks'] = 'fill_blanks'   # stored JSON discriminator
```

**Persistence discriminators.** The JSON mappers select types by `kind`
first. Legacy rows have no `kind`, or a code kind, and keep their current
branches:

- `ActivityMapper._question_from_data` adds a `kind == 'fill_blanks'` branch
  before its `'kind' in data` rejection.
- `ActivityAttemptMapper` deserializes answers with `kind == 'fill_blanks'` as
  `FillBlanksAnswer`. Its grading-snapshot question allowlist accepts the
  fill-blanks snapshot.
- `ActivityEvaluationMapper._deserialize_parts` checks
  `kind == 'fill_blanks'` **before** the `is_correct` choice branch.

Words are compared exactly after trimming surrounding whitespace. The
solvability invariant is a bipartite matching of every blank to a distinct
occurrence whose word is accepted for that blank. The question is valid only
when such a matching covers all blanks.

Example: the blanks `b1 = {'go', 'walk'}` and `b2 = {'go'}` with the bank
`[go#1, go#2, run#3]` are solvable. With the bank `[go#1, run#3]` they are not,
because `b2` would need `go#1` again.

The Shared `CurriculumFillBlanksQuestionSnapshot` mirrors these fields with
`kind: Literal['fill_blanks']`. Its child snapshots use `ValidationError`, and
it re-checks key uniqueness and segment and blank references. Its part is the
existing `CurriculumChoicePartSnapshot(question_key, weight_percentage)`.

### Learning declarations

```python
@structure
class FillBlanksPlacement:
    blank_key: str
    word_key: str

@structure
class FillBlanksAnswer:              # member of ActivityAnswer; accepted by preview and submit inputs
    question_key: str
    placements: tuple[FillBlanksPlacement, ...]   # normalized to segment order of blanks
    kind: Literal['fill_blanks'] = 'fill_blanks'

@structure
class FillBlanksEvaluationResult:    # member of EvaluationPartResult, persisted in evaluation parts
    question_key: str
    score: Decimal                   # Percentage, 2 decimals
    is_correct: bool                 # score == 100; drives disclosure
    correct_blank_keys: tuple[str, ...]
    blank_count: int
    explanation: str
    kind: Literal['fill_blanks'] = 'fill_blanks'   # read before the choice `is_correct` branch

@structure
class FillBlanksWordDetail:
    key: str
    word: str

@structure
class FillBlanksSegmentDetail:
    text: str | None = None
    blank_key: str | None = None

@structure
class FillBlanksQuestionDetail:       # public; no accepted words or criteria
    key: str
    kind: Literal['fill_blanks']
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegmentDetail, ...]
    bank: tuple[FillBlanksWordDetail, ...]

@structure
class FillBlanksExpectedBlank:
    blank_key: str
    accepted_words: tuple[str, ...]

@structure
class FillBlanksResultDetail:
    question_key: str
    prompt: str
    content_language: str
    segments: tuple[FillBlanksSegmentDetail, ...]
    bank: tuple[FillBlanksWordDetail, ...]
    placements: tuple[FillBlanksPlacement, ...]
    score: Decimal
    is_correct: bool
    correct_blank_count: int
    blank_count: int
    explanation: str
    disclosed_expected_blanks: tuple[FillBlanksExpectedBlank, ...] = ()
    kind: Literal['fill_blanks'] = 'fill_blanks'
```

`FillBlanksResultDetail` deliberately exposes only `correct_blank_count`, not
which blanks are correct, before disclosure (decision Q3).
`PreliminaryQuestionResult` (in `preview_activity_question_feedback_use_case.py`)
gains `correct_blank_count: int | None = None` and
`blank_count: int | None = None`. For fill-blanks it returns
`status='conclusive'`, the score, `is_correct` and the explanation.

`FillBlanksScoring` (pure, static):

- `normalize(question, answer) -> FillBlanksAnswer` raises `ValidationError`
  unless every blank appears exactly once, occurrence keys are distinct and
  known, and no unknown blank is present.
- `score(question, answer) -> FillBlanksEvaluationResult` applies RF-07 and
  selects the explanation by band: 100 gives correct, 0 gives incorrect, and
  anything between gives partial.
- `concept_observations(question, result) -> dict[str, Decimal]` returns
  `100 × |mapped ∩ correct| ÷ |mapped|` per criterion, quantized like the
  score.

### REST contracts

The routes are unchanged and live under the existing Learning router. Only the
request and response unions grow.

All paths below are relative to
`/learning/goals/{goal_id}/skills/{skill_id}/competencies/{competency_id}`.

- `GET .../activities/{activity_id}`: the `questions` union adds
  `FillBlanksQuestionResponse { key, kind: 'fill_blanks', prompt,
  content_language, segments: [{ text | null, blank_key | null }],
  bank: [{ key, word }] }`.
- `POST .../activities/{activity_id}/questions/{question_key}/preliminary-evaluations`: the
  `AnswerRequest.kind` literal adds `'fill_blanks'` with a required
  `placements: [{ blank_key, word_key }]`. `selected_option_keys` and `files`
  must be absent for this kind; otherwise 422. The response adds
  `correct_blank_count` and `blank_count` (null for other kinds).
- `POST .../activities/{activity_id}/attempts`: the same `AnswerRequest`
  extension. The response is unchanged: 201 for a new pending attempt and 200
  for a replay.
- `GET .../activities/{activity_id}/attempts/{attempt_id}`: the `questions` union adds
  `FillBlanksQuestionResultResponse { question_key, kind: 'fill_blanks',
  prompt, content_language, segments, bank, placements, score, is_correct,
  correct_blank_count, blank_count, explanation, disclosed_expected_blanks }`.
  Controllers validate structures through controller-local `TypeAdapter`s.
- Errors use the existing `AppErrorHandler` mapping:
  - 404 for a missing Goal or experience, another account's experience, or
    unreleased content;
  - 409 for a stale revision, a submission-key conflict or a pending
    evaluation;
  - 400 for an invalid fill (the domain `ValidationError` mapping) and 422 for a malformed body shape.
  
  Messages are pt-BR.

### Web declarations

```ts
export type FillBlanksSegment = { text: string | null; blankKey: string | null }
export type FillBlanksWord = { key: string; word: string }
export type FillBlanksQuestion = {
  key: string
  kind: 'fill_blanks'
  prompt: string
  contentLanguage: string
  segments: readonly FillBlanksSegment[]
  bank: readonly FillBlanksWord[]
}
export type FillBlanksPlacement = { blankKey: string; wordKey: string }
export type FillBlanksAnswer = {
  kind: 'fill_blanks'
  questionKey: string
  placements: readonly FillBlanksPlacement[]
}
export type FillBlanksResultQuestion = {
  key: string
  kind: 'fill_blanks'
  prompt: string
  contentLanguage: string
  segments: readonly FillBlanksSegment[]
  bank: readonly FillBlanksWord[]
  placements: readonly FillBlanksPlacement[]
  score: number
  isCorrect: boolean
  correctBlankCount: number
  blankCount: number
  explanation: string
  expectedBlanks?: readonly { blankKey: string; acceptedWords: readonly string[] }[]
}
// ActivityQuestion, ActivityAnswer and ActivityResultQuestion unions gain these members;
// PreliminaryQuestionResult gains correctBlankCount?: number and blankCount?: number.
```

### Widget ownership and state

- **`useActivityPage`** stays the single owner of answers. A
  `FillBlanksAnswer` holds partial placements while the learner edits.
  `hasValidSelection` for fill-blanks means that every blank has a placement.
  Any change to the placements clears `feedback` and the feedback error.
  Advancing keeps the answer frozen in `answers` for final submission and is
  blocked until a conclusive feedback exists for the current fill. This is the
  existing check-then-advance flow.
- **`FillBlanksQuestion`** (`index.tsx`) receives:
  - `question`;
  - `placements`;
  - `isLocked`;
  - `onPlacementsChange(placements)`.

  It mounts `DndContext` and a polite live region, and composes
  `FillBlanksText` and `WordBank`. The sensors (pointer, touch and keyboard,
  via `useSensors`) are built in `useFillBlanksQuestion` and passed in, so
  `index.tsx` holds no hook logic.
- **`useFillBlanksQuestion`** owns:
  - the selected occurrence key;
  - the announcement text;
  - the place, remove and replace transitions, as pure derivations from
    `placements`;
  - `handleDragEnd`, which maps the drop target to a placement;
  - `handleWordSelect` and `handleBlankActivate`. Activating an empty blank
    with a selection places the word. Activating a filled blank without a
    selection removes its word. With a selection, it replaces the word and the
    previous occurrence returns to the bank.

  It never moves a word from one blank to another automatically. Dragging a
  placed word onto another blank is treated as remove-then-place: the target's
  previous word returns to the bank.
- **`BlankSlot`, `BankWord` and `WordBank`** own only their `@dnd-kit` droppable and draggable bindings in `use-blank-slot.ts`, `use-bank-word.ts` and `use-word-bank.ts` (the bank is a drop target for returning a placed word). Both render
  shadcn `Button`s with `aria-pressed` or `aria-describedby` and pt-BR names,
  for example "Lacuna 2, vazia" and "Lacuna 2, preenchida com go". Content
  text carries `lang={contentLanguage}`.
- **`FillBlanksText`** is a pure renderer of precomputed props
  (segments with their placed word, available occurrences). They have no
  hooks or tests of their own and are covered through `FillBlanksQuestion`.
- **`useQuestionFeedback`** (existing hook, extended) derives the
  score-band label and icon and the "N de M lacunas corretas" text.
  `QuestionFeedback` only renders them.
- **`FillBlanksResult`**, the new child of `ChoiceResultDetail`, owns
  `useFillBlanksResult`. The hook derives the placed word per blank, the band
  label and icon, and the disclosed "Preenchimento esperado". Its behavior is
  covered through the real composition in `choice-result-detail.test.tsx`
  (CI-11). It gets no dedicated hook test, because the logic is a direct
  derivation that the parent test observes fully.

There are no new contexts, query hooks or action hooks. The existing preview,
submit and attempt operations in `use-activity-page.ts` and
`use-choice-result-page.ts` carry the new shapes with unchanged cache and
refetch behavior.

## Runtime Flow

```mermaid
sequenceDiagram
    participant W as Web Activity page
    participant API as Learning REST
    participant UC as Learning use cases
    participant CP as CurriculumContentProvider
    participant DB as Learning DB (JSON columns + outbox)
    participant J as Inngest evaluate job
    W->>API: GET activity
    API->>UC: GetChoiceActivityUseCase(account, goal, skill, competency, activity)
    UC->>CP: get_learning_activity (fill-blanks present)
    UC-->>W: public question detail (no accepted words)
    W->>API: POST preliminary-evaluations {fill_blanks placements, revision}
    API->>UC: Preview (ownership, revision, FillBlanksScoring.normalize/score)
    UC-->>W: score, counts, explanation (no writes)
    W->>API: POST attempts {submission_key, answers}
    API->>UC: SubmitChoiceActivityUseCase
    UC->>DB: attempt(answers, grading_snapshot) + pending evaluation + outbox event (one transaction)
    DB-->>J: destination 'inngest' (non-code mixed snapshot)
    J->>UC: EvaluateChoiceActivityUseCase(attempt_id, run_id, code_decisions=())
    UC->>DB: lock experience+evaluation; score parts; Concept observations; progress/mastery/recommendation once
    W->>API: GET attempt
    API->>UC: GetChoiceAttemptUseCase (disclosure rule)
    UC-->>W: result detail (expected fill only when released)
```

The flow keeps these guarantees:

- **Trusted context.** The account id comes from the authenticated session
  pipe. Ownership is checked inside the transaction for writes.
- **Validation.**
  - Transport shape is checked by Pydantic.
  - Fill semantics are checked by `FillBlanksScoring.normalize`, before any
    write, in both preview and submit.
  - A stale revision is a conflict.
  - Diagnostic Activities never contain the kind, so a diagnostic submission
    with it cannot be produced. The provider would also return `None` for such
    content.
- **Transactions.** The attempt, the pending evaluation and the outbox event
  commit together. The evaluation locks the experience and the evaluation row,
  and only completes a `PENDING` evaluation with the matching `run_id`. A
  duplicate or stale delivery therefore writes nothing (CA-11).
- **Failure and recovery.** Unexpected errors in the job mark the evaluation
  `FAILED` (existing `on_failure`). The stored answers are untouched. Retry
  issues a new `run_id` for the same attempt (CA-12). New submissions in the
  Skill stay blocked while the evaluation is unresolved.
- **Review.** For a completed experience the attempt kind is `REVIEW`. The
  existing review branch records the evaluation without progress or mastery
  effects (CA-15).
- **Deletion.** Skill or Goal removal and account closure delete attempts as
  today. A late job finds no attempt or experience and writes nothing.

# Verification Contract

## Shared setup

- **Server use-case tests** (`apps/server`) instantiate use cases with
  `create_autospec` mocks of `LearningDatabase` repositories,
  `CurriculumContentProvider`, `ClockProvider` and `IdentifierProvider`. A
  fill-blanks snapshot is built inline or through an existing Learning faker.
  There is no infrastructure.
- **Server controller tests** use the shared `TestClient` from
  `apps/server/tests/conftest.py`, with a disposable PostgreSQL Testcontainer
  at Alembic head and tables reset per test. Prerequisites are created through
  the existing controller fixture helpers:
  - an account and its authenticated session;
  - a Goal with a Skill experience in learning and a released Competency;
  - a Curriculum Activity with three fill-blanks questions and one single
    choice;
  - a second account for isolation.

  Docker is required. A skip is not a pass.
- **Real job test** runs
  `SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest ...` with
  `apps/server/tests/fixtures/inngest_fixture.py`, which brings disposable
  Inngest and PostgreSQL containers and the configured callback port. It never
  uses the Compose Inngest instance.
- **Web Vitest** runs from the repository root. Component tests mock the
  owning hook (`useFillBlanksQuestionMock`, `useActivityPageMock`) and render
  the real children inside `DndContext`. Hook tests use `renderHook`.
- **Web Playwright suites** are the existing
  `apps/web/tests/learning/*.test.ts` route suites with their current request
  fixtures. They prove browser composition, not real persistence.
- **Manual checks** use the Playwright CLI against the real web
  (`http://127.0.0.1:7000`) and API (`GET /health`) with the seeded local
  account and `.playwright-cli/states/shifu-auth-state.json`.
  - The RF-14 English content and experience exist in a database only after
    the development seed runs.
  - Applying `db:seed` resets shared local data and **requires explicit user
    authorization**. Without it, run the journey on a disposable Compose
    project, or record VM-01/VM-02 as Blocked.
  - The journey creates new attempts on the seeded experience. Rerunning only
    adds history and needs no cleanup beyond closing the task-started session.

## Automated

### CI-01 — Fill-blanks content invariants

**Criteria:** CA-01, CA-02

**Expected result:** Valid content constructs. Each invalid class in CA-02
raises `InvalidActivityError`, including the unsolvable bank and the
diagnostic Activity case. The Shared `CurriculumFillBlanksQuestionSnapshot`
raises `ValidationError` for duplicate keys and for broken segment or blank
references. `CurriculumLearningActivitySnapshot` raises `ValidationError` for
a diagnostic snapshot containing it, and for a fill-blanks question paired
with a non-choice part. This follows the
`test_react_question.py::test_should_reject_invalid_frozen_react_learning_snapshot`
precedent.

**Setup / inputs:** equivalence classes from CA-01 and CA-02. Boundary values:
one blank (where a partial explanation is forbidden), two blanks (where it is
required), a bank equal to the blank count, and a bank with distractors.

**Proof:** planned `apps/server/tests/curriculum/core/domain/test_fill_blanks_question.py`
(`TestFillBlanksQuestion`). This is focused domain conformance, permitted
because no Curriculum use case owns these invariants.

```bash
cd apps/server && uv run pytest tests/curriculum/core/domain/test_fill_blanks_question.py
```

**Passing condition:** every class asserted, with a non-zero collected count
and no skips.

### CI-02 — Learning use cases for preview, scoring, evidence, recovery and disclosure

**Criteria:** CA-07, CA-08 (ownership, revision and validation part), CA-10,
CA-11, CA-12, CA-14, CA-15

**Expected result:**

- Preview returns 0, 33.33 and 100 with the matching explanations. Twin
  occurrences are equivalent. Invalid fills raise `ValidationError`, a stale
  revision raises `ConflictError` and a foreign account raises
  `NotFoundError`, all without repository writes.
- Evaluation persists `FillBlanksEvaluationResult` parts and applies the
  weighted Activity grade. It writes the Concept observation 50 for a Concept
  mapped to two blanks with one correct. It does nothing for a completed or
  stale run, and makes no progress change for `REVIEW`.
- Retry re-queues the same attempt.
- Attempt detail hides the expected blanks until a later fully correct
  attempt or mastery.

**Setup / inputs:** autospecced ports and an inline fill-blanks mixed snapshot.

**Proof** (all exist; fill-blanks scenarios are planned additions):

- `apps/server/tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py`
- `.../test_submit_choice_activity_use_case.py`
- `.../test_evaluate_choice_activity_use_case.py`
- `.../test_get_choice_activity_use_case.py`
- `.../test_get_choice_attempt_use_case.py`
- `.../test_retry_choice_evaluation_use_case.py`

```bash
cd apps/server && uv run pytest \
  tests/learning/core/use_cases/test_preview_activity_question_feedback_use_case.py \
  tests/learning/core/use_cases/test_submit_choice_activity_use_case.py \
  tests/learning/core/use_cases/test_evaluate_choice_activity_use_case.py \
  tests/learning/core/use_cases/test_get_choice_activity_use_case.py \
  tests/learning/core/use_cases/test_get_choice_attempt_use_case.py \
  tests/learning/core/use_cases/test_retry_choice_evaluation_use_case.py
```

**Passing condition:**

- Each listed outcome has an exact assertion.
- Rejection paths assert that downstream ports were not called.
- Existing choice and code scenarios still pass.

### CI-03 — GET Activity and submission use-case projections

**Criteria:** CA-03, CA-09 (normalization part)

**Expected result:**

- `GetChoiceActivityUseCase` returns `FillBlanksQuestionDetail` without
  answer-key fields, through the mixed path.
- `SubmitChoiceActivityUseCase` normalizes placements to blank order, persists
  the attempt, pending evaluation and event in one transaction, replays an
  identical key, raises `ConflictError` for a differing replay, and raises
  `ValidationError` before any write for an incomplete fill.

**Proof:** fill-blanks scenarios in `test_get_choice_activity_use_case.py` and
`test_submit_choice_activity_use_case.py`, run by the CI-02 command.

**Passing condition:** the scenarios execute in the CI-02 run, and their
names are recorded in Evaluation.

### CI-04 — Preview feedback controller

**Criteria:** CA-07 (HTTP), CA-08

**Expected result:**

- 200 with `score`, `correct_blank_count`, `blank_count` and `explanation`,
  and no expected words.
- 400 for an incomplete, duplicated or unknown fill and 422 for a mixed-field body
  shape, both with a pt-BR message.
- 409 for a stale revision.
- 404 for another account.
- No `activity_attempts` or `activity_evaluations` rows in any case.

**Proof:** planned scenarios in `apps/server/tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py`.

```bash
cd apps/server && uv run pytest tests/learning/server/controllers/test_preview_activity_question_feedback_controller.py
```

**Passing condition:** status, body and the absence of rows are asserted
through fresh sessions.

### CI-05 — Submit controller and persistence

**Criteria:** CA-09

**Expected result:**

- 201 pending, with the attempt row storing `fill_blanks` placements and the
  grading snapshot, a pending evaluation and one outbox event.
- An identical replay returns 200 with the same attempt.
- A differing replay returns 409.
- An incomplete fill returns 400 with no rows.
- A submission while an evaluation is unresolved returns 409.

**Proof:** planned scenarios in `apps/server/tests/learning/server/controllers/test_submit_choice_activity_controller.py`.

```bash
cd apps/server && uv run pytest tests/learning/server/controllers/test_submit_choice_activity_controller.py
```

**Passing condition:** persisted JSON is read back through the real mappers,
and legacy choice and code rows still deserialize.

### CI-06 — Attempt result controller and disclosure

**Criteria:** CA-14

**Expected result:** a completed partial attempt returns
`FillBlanksQuestionResultResponse` with an empty `disclosed_expected_blanks`.
After a later fully correct attempt, or with a mastered Competency, the
response includes the accepted words per blank. Another account gets 404.

**Proof:** planned scenarios in `apps/server/tests/learning/server/controllers/test_get_choice_attempt_controller.py`.

```bash
cd apps/server && uv run pytest tests/learning/server/controllers/test_get_choice_attempt_controller.py
```

**Passing condition:** exact body assertions for both disclosure states.

### CI-07 — GET Activity controller

**Criteria:** CA-03, CA-19

**Expected result:** 200 with the public fill-blanks shape in Curriculum
order. The serialized body contains no accepted words or `concept_criteria`.
Another account gets 404. An Activity whose fill-blanks criterion names a
Concept outside its Competency is not published and returns 404. This proves
the provider guarantee through its consumer.

**Proof:** planned scenario in `apps/server/tests/learning/server/controllers/test_get_choice_activity_controller.py`.

```bash
cd apps/server && uv run pytest tests/learning/server/controllers/test_get_choice_activity_controller.py
```

**Passing condition:** a body equality assertion, plus a negative search of
the raw JSON for the hidden field names and explanation texts (every accepted word is also a bank word, so the words themselves cannot be searched).

### CI-17 — Diagnostic batch keeps its contract

**Criteria:** CA-20

**Expected result:** a diagnostic batch item answer with
`kind: 'fill_blanks'` returns 422 with a pt-BR message. No attempt,
evaluation or outbox row is written. A choice answer in the same body is not
rejected by the new validator. The valid-batch success path stays covered by the
existing legacy journey test
`tests/learning/rest/controllers/test_adaptive_journey_controller.py`, run as a
consumer check.

**Proof:** planned
`apps/server/tests/learning/server/controllers/test_submit_diagnostic_batch_controller.py`
(`TestSubmitDiagnosticBatchController`). This is a module-first file; the
legacy `tests/learning/rest/**` tree is not extended.

```bash
cd apps/server && uv run pytest tests/learning/server/controllers/test_submit_diagnostic_batch_controller.py
```

**Passing condition:** status, body and the absence of rows are asserted.

### CI-08 — Registered evaluation job for a fill-blanks attempt

**Criteria:** CA-11, CA-13

**Expected result:** the outbox destination for the saved non-code mixed
attempt is `'inngest'`, asserted the same way `_outbox_destination` does in the
existing mixed scenario. The canonical `ActivitySubmissionRequestedEvent`
reaches the registered job. The evaluation completes once with the expected
parts and Concept observation. A duplicate delivery writes nothing more.

**Proof:** planned
`test_registered_job_evaluates_saved_fill_blanks_attempt_once` in
`TestEvaluateChoiceActivityJob`, in
`apps/server/tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py`.

```bash
cd apps/server && SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest \
  tests/messaging/inngest/jobs/learning/test_evaluate_choice_activity_job.py
```

**Passing condition:** the new scenario runs (it is not skipped) and asserts
the persisted state through a new session. The existing scenarios still pass.

### CI-09 — Fill-blanks question widget and hook

**Criteria:** CA-04, CA-05

**Expected result:**

- The hook covers select-then-place, keyboard activation, drag end, replace
  (the previous word returns to the bank), remove, no cross-blank move, locked
  state ignoring input, and the announcement text for each transition.
- The component renders pt-BR accessible names, the selected and filled
  states, `lang` on content, the bank without placed occurrences, and
  delegation of the hook handlers.

**Proof:**

- planned `apps/web/src/ui/learning/widgets/pages/activity-page/fill-blanks-question/tests/use-fill-blanks-question.test.ts`;
- planned `.../fill-blanks-question/tests/fill-blanks-question.test.tsx`, which
  mocks `useFillBlanksQuestion`.

```bash
pnpm --filter web exec vitest run \
  src/ui/learning/widgets/pages/activity-page/fill-blanks-question/tests/use-fill-blanks-question.test.ts \
  src/ui/learning/widgets/pages/activity-page/fill-blanks-question/tests/fill-blanks-question.test.tsx
```

**Passing condition:** every returned value and handler of the hook is
exercised. Assertions use roles and names.

### CI-10 — Activity page integration of the new kind

**Criteria:** CA-06, CA-16 (feedback)

**Expected result:**

- Check is disabled until all blanks are filled.
- Preview is called with `fill_blanks` placements.
- The feedback label, count and explanation render.
- Editing clears the feedback.
- Advancing locks the question.
- The final submission includes the frozen placements.

**Proof:** fill-blanks scenarios in
`apps/web/src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts`
and `.../activity-page/tests/activity-page.test.tsx`.

```bash
pnpm --filter web exec vitest run \
  src/ui/learning/widgets/pages/activity-page/tests/use-activity-page.test.ts \
  src/ui/learning/widgets/pages/activity-page/tests/activity-page.test.tsx
```

**Passing condition:** the scenarios execute, and the existing choice and code
scenarios still pass.

### CI-11 — Result detail rendering

**Criteria:** CA-16

**Expected result:** a partial result shows the read-only fill, the
"Parcialmente correta" label with icon, "N de M lacunas corretas" and the
explanation, with no "Preenchimento esperado". A disclosed result shows the
expected words.

**Proof:** scenarios in `apps/web/src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx`.

```bash
pnpm --filter web exec vitest run \
  src/ui/learning/widgets/pages/choice-result-page/choice-result-detail/tests/choice-result-detail.test.tsx
```

**Passing condition:** both disclosure states are asserted.

### CI-12 — Browser route suites

**Criteria:** CA-17 (browser composition)

**Expected result:** the Activity route renders a fill-blanks question. A
keyboard-only fill, check, advance and submit works. The result route renders
the fill-blanks detail. Scenarios run at 1440×900 and at 390×844 through
`setViewportSize`, the way the existing suite does.

**Proof:** scenarios added to `apps/web/tests/learning/activity-page.test.ts`
and `apps/web/tests/learning/choice-result-page.test.ts`.

```bash
pnpm --filter web exec playwright test tests/learning/activity-page.test.ts tests/learning/choice-result-page.test.ts
```

**Passing condition:** the new scenarios run. These suites stub server
functions, so they do not exercise `learning-service.ts`. They are reported
as browser composition only.

`learning-service.ts` runs inside server functions, so the browser sees only
`/_serverFn/` payloads, never the REST bodies. The service's fill-blanks
mapping is therefore proven end to end by VM-01:

- the real API accepts the preview and the submission;
- the rendered feedback score and count match the fill;
- the attempt reloaded from history shows the same fill.

The disclosed-expected-words branch of the mapping is a recorded limitation
of the manual journey, because the VM-01 attempt is partial. It is covered on
the server by CI-06 and in rendering by CI-11.

### CI-13 — Types

**Scope:** Server contracts and implementation; Web contracts, service and UI.

```bash
# from the repository root
(cd apps/server && uv run poe check:types)
pnpm --filter web check:types
```

**Passing condition:** zero errors and warnings in both projects.

### CI-14 — Lint and format

**Scope:** exact changed Server and Web paths from the file tree.

```bash
# from the repository root
(cd apps/server && uv run ruff check --no-fix <changed-python-paths...> && uv run ruff format --check <changed-python-paths...>)
pnpm exec biome check <changed-web-paths...>
```

**Passing condition:** zero diagnostics on the recorded path list.

### CI-15 — Complexity

**Scope:** the changed logic. This includes `FillBlanksScoring`, the
matching check in `FillBlanksQuestion`, `FillBlanksSnapshotProjection`,
`SubmitChoiceActivityUseCase.normalize_answers`, the diagnostic
`ItemRequest` validator,
`EvaluateChoiceActivityUseCase._score_mixed_part` and
`_v2_observation_scores`, the provider `_get_activity` and
`get_skill_content`, the three mappers, and `use-activity-page.ts`,
`use-fill-blanks-question.ts`, `use-question-feedback.ts` and
`use-fill-blanks-result.ts`.

**Checks:**

- Server: Ruff `C90` (McCabe) through the CI-14 command.
- Web: Biome complexity rules through the CI-14 command.
- No dedicated metrics tool or baseline is configured. A quantitative metric
  is therefore not required and is recorded as Not applicable.

**Passing condition:** no new complexity diagnostics. Existing suppressions
such as `# noqa: C901` on `_get_activity`, `get_skill_content` and
`normalize_answers` are not broadened, and no branch is hidden under them.
New fill-blanks branching moves into Learning's `FillBlanksScoring` or
Curriculum's `FillBlanksSnapshotProjection`. Each stays on its own side of
the Tach boundary.

### CI-16 — Architecture, build and test integrity

```bash
# from the repository root
(cd apps/server && uv run poe check:architecture && uv run poe build)
pnpm --filter web check:architecture
pnpm --filter web build
pnpm check:test-integrity
```

**Passing condition:**

- Tach and Dependency Cruiser pass. In particular, Curriculum does not import
  Learning and the reverse, and core imports no framework.
- Both builds succeed.
- Every new or changed test file in this Spec is listed as an allowed kind.
- The independent review reported that `pnpm check:test-integrity` may
  already fail on `main` because of
  `apps/server/tests/curriculum/database/test_roadmap_skills_seed.py`. This was
  inferred from the checker's patterns, not observed. Confirm it at
  implementation kickoff.
  - If it is confirmed, record the gate as **Failed (pre-existing)** in
    Evaluation, together with the evidence that every file this delivery adds
    or changes is listed as allowed.
  - The delivery stays incomplete on this gate until a separate maintenance
    fix lands, or the user explicitly accepts the exception. Either way, the
    result is never reported as a pass.
  - The file is not moved, deleted or excluded to evade the check.

Selection rationale per [Tooling](../../../tooling.md#selecting-unit-and-integration-tests):

- The use-case, controller and job files listed above are the direct owners
  and consumers of the changed unions, mappers and routing.
- `SubmitDiagnosticBatchController` consumes the shared `AnswerRequest`,
  and `SubmitDiagnosticBatchUseCase` calls the shared
  `SubmitChoiceActivityUseCase.normalize_answers`. CI-17 covers that boundary
  through HTTP.
- Gamification's `RecognizeActivityEvaluatedUseCase._activity_title` reads
  `get_choice_activity`. That returns `None` for mixed Activities, so XP
  history falls back to its generic label, as it already does for code
  Activities. This is an accepted, unchanged limitation, and no Gamification
  file changes.
- Intelligence's Mentor context reads only aggregate progress.
- Full suites are not required.

## Manual

### VM-01 — Real desktop journey with the seeded English Activity

**Type:** Manual

**Criteria:** CA-17

**Tool / setup:** Playwright CLI session `shifu` from `apps/web`, desktop
1440×900, and the shared setup's seeded English experience.

**Procedure:**

1. Open the English Activity from its Competency.
2. Question 1: fill one blank by drag and the rest by click-select-then-blank.
   Replace one word and remove one word, then refill.
3. Check, and read the provisional feedback.
4. Edit one blank and confirm that the feedback clears. Check again.
5. Advance. Answer the remaining questions, using keyboard only (Tab, Enter,
   Space) for one fill-blanks question.
6. Submit, then wait for the result.
7. Open the attempt from history.

**Passing condition:**

- The final URL is the result route.
- The real API accepted the preview and the submission: the feedback
  renders, and the attempt reaches the result route instead of an error
  state.
- The rendered feedback score and "N de M lacunas corretas" match the fill
  that was entered.
- The result shows the submitted fill, score and explanation without expected
  words for a partial answer. Reopening the attempt from history shows the
  same fill.
- History lists the attempt.
- There are no console errors.
- Focus is always visible.
- Close the task-started session.

### VM-02 — Real mobile journey

**Type:** Manual

**Criteria:** CA-17

**Tool / setup:** as in VM-01, at a 390×844 viewport with touch emulation.

**Procedure:** fill by touch drag and by tap-select-then-tap-blank. Remove a
word, check, advance, submit and open the result.

**Passing condition:** there is no horizontal page scroll. Every control is
reachable without overlap. Outcomes match VM-01.

## Visual

### VM-03 — Empty fill-blanks question, desktop

**Type:** Visual

**Criteria:** CA-18

**Reference / setup:** the Penpot board for the empty state named in the
Design Contract (pending verification), at desktop 1440×900. The capture is
taken during VM-01 step 1.

**Capture / comparison:** a fresh Penpot MCP export of the board compared with
the Playwright CLI capture under `apps/web/.playwright-cli/screenshots/`.

**Passing condition:** header, text with blanks, bank layout, typography,
spacing, tokens and focus treatment match. Deviations are limited to those in
the Design Contract.

### VM-04 — Filled question with partial provisional feedback, desktop

**Type:** Visual

**Criteria:** CA-18

**Reference / setup:** the Penpot board for the filled state (pending
verification). The capture is taken during VM-01 step 3.

**Capture / comparison:** as in VM-03.

**Passing condition:** filled blanks, the feedback label with icon, the count
and the explanation match the board.

### VM-05 — Empty and filled question, mobile

**Type:** Visual

**Criteria:** CA-18

**Reference / setup:** the mobile boards (pending). The capture is taken
during VM-02 at 390×844.

**Capture / comparison:** as in VM-03.

**Passing condition:** the board's layout and reflow match, and touch targets
are at least 44×44 px.

### VM-06 — Partial result detail, desktop and mobile

**Type:** Visual

**Criteria:** CA-18

**Reference / setup:** the result board (pending). The capture is taken during
VM-01 step 6 and VM-02.

**Capture / comparison:** as in VM-03.

**Passing condition:** read-only fill, label, count and explanation match, and
no expected fill is shown.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Learning PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83066881/Shifu+PRD+Learning), "Shifu — PRD — Learning", content ID `83066881`, last modified 2026-11-12, read in full 2026-11-17 | RP-09, RP-13, RP-14, RP-15, RP-18, RP-20, RP-25, RP-27; JN-07, JN-08, JN-13 | Unchanged intent. Q3 follows RP-09 ("editable until advance") literally and shows no per-blank marks, which RP-18 permits | The Confluence API did not return a version number. SHIFU-123 cites version 28. Confirm the version before `ready`. No external write |
| [Curriculum PRD](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83034113/Shifu+PRD+Curriculum), "Shifu — PRD — Curriculum", content ID `83034113`, last modified 2026-11-02, read in full 2026-11-17 | RP-03, RP-04; JN-03, JN-04 | Unchanged intent. The partial explanation is a Spec interpretation of "explicações" for a format with partial credit | SHIFU-123 cites version 15. Confirm before `ready`. No external write |
| [SHIFU-123](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-123), Dev Task under Epic SHIFU-10, Sprint 3 | Delivery scope and validation | Its visual source (`shifu.fig`/OpenPencil) conflicts with `AGENTS.md` (Penpot via MCP). This Spec uses Penpot | Conflict reported. Jira is not edited |
| Shifu Penpot file (Penpot MCP) | Visual intent | Verify the boards in the Design Contract and add the mobile boards | Penpot MCP was unavailable in the authoring session and in the implementation session. On 2026-11-17 the user directed implementation of the written Spec with this outstanding. Code and automated work proceed. VM-03..VM-06 stay **Blocked** until the boards are verified through the MCP, and no visual pass is claimed before then |
| PR #52 / `feat/shifu-122` (open) | Same unions, controllers and Activity page | Reconcile both kinds at the later merge | Implementation dependency, not a readiness blocker |
| Rules listed in Architecture Mapping; [`design.md`](../../../design.md); [`tooling.md`](../../../tooling.md) | Server and Web boundaries, tokens and commands | Confirmed. No rule change | Recheck before conclusion |
| `apps/server/rest-client/learning/activities.rest` | API examples | Add fill-blanks preview and submit examples | Part of the delivery |
| Development seed | Example content | `db:seed` application needs explicit authorization | Manual-check dependency |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 2 | 2026-11-17 | Corrections found while implementing: an invalid fill maps to HTTP 400 (domain `ValidationError`) and a malformed body shape to 422; keyboard and assistive technology use select-then-place and drag is pointer/touch; the word bank owns a drop-target hook; shared outcome hook; partial icon; extra fakers, fixtures and seed files; CI-07 and CI-17 wording | Implementation evidence. No product behavior changed |
| 1 | 2026-11-17 | Initial contract | SHIFU-123. Decisions: Q1 start from `main`; Q2 per-Concept evidence as the proportion of mapped blanks correct; Q3 edits allowed until advance, with feedback showing score, count and explanation only; Q4 `@dnd-kit/core` plus select-then-place; Q5 Penpot verification before `ready` |

Follow [SDD](../../../sdd.md) and [Create Spec](../../../prompts/create-spec-prompt.md).
