---
title: Mentor — conversation summary and continuity
status: implemented
revision: 3
source:
  type: issue
  ref: https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-102
scope:
  - intelligence/mentor
  - web/mentor-page-and-fab
last_updated_at: 2026-10-20
---

# Objective

Long Mentor conversations keep their continuity through a **local, extractive summary
of the conversation's own older messages**. When a learner message is about to be
answered and the conversation has grown past a fixed threshold, the answer run first
summarizes the older part ("Resumindo contexto…"), then answers using that summary plus
the recent messages. A "Contexto resumido" marker in the timeline lets the learner read
the summary the Mentor uses and jump back to the original messages. The full history is
never deleted, reordered or rewritten.

**Mode: complete** — new persistence, a new pre-answer phase inside the registered
AgentOS answer workflow, fences against concurrent cancel/delete/account loss, a privacy
lifecycle and cross-surface UI.

**Baseline (current source):** general Mentor answers are local and deterministic
([mentor-context rev18, Amendment 16](../mentor-context/spec.md)); the local router reads
only the current message plus reference IDs of the last completed attempt;
`PrepareMentorResponseUseCase` loads the **unbounded** history (`find_all`) and passes it
to the attachment answer path, whose reviewer receives all of it. No summarization,
truncation or context window exists on server or web. Session deletion tombstones the
session and hard-deletes messages/attempts/events; on `identity/account.deleted`
Intelligence purges only attachments.

**Summarization uses no AI provider.** It runs Shifu's already-loaded local NLP stack
(spaCy `pt_core_news_sm`, multilingual E5 embeddings) with TextRank/MMR. Nothing leaves
Shifu; no model endpoint, usage receipt or quota debit is involved.

# Scope

| Area / actor | Included | Excluded or deferred |
| --- | --- | --- |
| Learner (owner of a conversation) | Automatic summarization of long conversations; "Resumindo contexto…" while it runs; "Contexto resumido" marker; reading dialog; "Ver mensagens originais"; "Fechar resumo"; failure notice; page and FAB; desktop and 390 px mobile; keyboard; pt-BR | Manual "resumir agora" or manual retry; browsing previous summary versions; editing/deleting a summary; sharing/exporting |
| Intelligence — summary engine | Extractive summary (spans of verbatim message text), Assuntos/Dúvidas/Orientações, deterministic template text, one current version, `algorithm_version` | Abstractive/LLM summaries; remote inference of any kind for summarization; embeddings index of summaries |
| Intelligence — answer pipeline | Pre-answer `summarize-conversation-context` step; prepare reads summary + messages after the boundary; the reviewer request receives bounded `history` + `summary` (the attachment answer agent's input is unchanged); router uses Assuntos only for a guarded retry | Enabling general answer generation (writer); changing FAQ thresholds, intents, pedagogy or abstention; memories (RP-14) |
| Lifecycle | Conversation deletion removes summaries in the same transaction; account deletion purges summaries immediately; fences block recreation | Purging sessions/messages/attempts/events on account deletion (pre-existing gap, see Documentation Alignment); Privacy Policy deadlines for individual deletion |
| Quota (RP-02) | Summarization records no usage and debits nothing | Quota implementation, percentages, renewal, UI |

Selected canonical outcomes (PRD Intelligence, content 83099649 **v9**):

- **RP-15 — full.** Automatic summarization of long conversations; own-conversation
  sources only; summary + recent messages for continuity; full history preserved; no
  mastery claims, no substitute for fresh Learning reads, no memory recreation; failure
  never deletes messages nor presents incomplete results; states/controls accessible.
- **JN-19 — full.**
- **RP-03 — partial:** history preservation, independence between conversations and the
  summary part of conversation deletion; conversation management itself is SHIFU-99.
- **RP-06 — partial:** summarization inside the answer run preserves RP-06's single
  in-progress response, cancel and retry without duplicating the learner message.
- **RP-02 — partial:** the auxiliary summarization never reduces visible quota (it uses
  no inference); quota itself stays deferred.
- **RP-11 / RP-13 / JN-14 / JN-16 — partial:** summaries and derived versions only
  (owner-only access, immediate removal on conversation deletion, immediate purge on
  account deletion, no recreation by pending processing, minimization by storing spans
  instead of copied text). ZDR/aggregator conditions are **not applicable** to
  summarization because no inference endpoint is used.
- **RP-12 — partial:** the summary surfaces (marker, dialog, notice, disabled composer).
- **RP-14 — partial:** a summary never creates or recreates a memory and never feeds
  memory creation; memories themselves are not implemented here.
- **RP-04 — partial:** the router's guarded use of Assuntos; mutable Learning state is
  still read fresh; the summary is never authority for product state.
- **RP-01 — not applicable** for summarization ("no eligible AI option" cannot occur:
  no AI provider is used).

Design: [design/handoff.md](design/handoff.md) (KVnFQ, RDiWy, T4Edi, ov9QQ, ySE0r).

# Behavior Contract

Definitions used below:

- **Boundary** — the last message included in the current ready summary, identified by
  `(created_at, id)`; messages "after the boundary" are strictly greater in that order.
- **Recent window** — the 10 newest messages of the conversation at evaluation time,
  including the pending learner message being answered. Never summarized.
- **Unsummarized volume** — messages after the current boundary and outside the recent
  window: their count and their total `content` length in Unicode code points.

| ID | RP / JN / source | Observable required behavior |
| --- | --- | --- |
| RF-01 | RP-15, JN-19, RP-02 | When the answer run starts for a learner message, Intelligence evaluates the unsummarized volume. If **count ≥ 20 or characters ≥ 16,000**, it summarizes before answering: the response publishes progress `summarize-context` (UI "Resumindo contexto…"), then continues to the normal answer. Below the threshold no summary row, event or progress is produced. The new boundary is the newest message outside the recent window at evaluation time; messages after it are never absorbed. No usage receipt, model call or quota effect is produced. |
| RF-02 | RP-15, RP-03, RP-13 | A summary is built **only** from the same conversation: the previous ready summary's excerpts plus the messages after the previous boundary up to the new boundary. It contains ≤ 8 **Assuntos** (key phrases), ≤ 5 **Dúvidas** (learner excerpts) and ≤ 5 **Orientações** (Mentor excerpts). Every excerpt is a verbatim span of one source message of that conversation, ≤ 280 code points (a cut keeps the verbatim prefix; the rendered text appends "…"), never inside fenced code. Output is deterministic for the same input and `algorithm_version`. The summary invents no facts and asserts no mastery. |
| RF-03 | RP-15, RP-13 | Each conversation has at most one **ready** summary and at most one **processing** summary. A newly completed version replaces the previous ready version and any failed rows in the same transaction; superseded versions are not kept. |
| RF-04 | RP-15, RP-04, RP-03, RP-14 | Answer preparation uses the ready summary (if any) **plus every message strictly after its boundary**, which always includes the pending learner message. The reviewer request of the attachment path receives that bounded history plus the summary instead of the full history; the attachment answer agent's own input (question, allowed sources, chunks) is unchanged. The local router may use the summary's Assuntos **only** to retry FAQ retrieval once for an elliptical part (≤ 6 content tokens after preprocessing, or an unresolved reference) whose own retrieval returned nothing, with unchanged thresholds; the summary never selects an Objective, Habilidade, Activity, Curriculum proposal or clarification target. Learning/Curriculum/Gamification context is still read fresh. Summaries never create or update memories. |
| RF-05 | RP-03, RP-15 | Summarization never deletes, edits, hides or reorders messages. The full history stays readable through the existing paginated detail in `(created_at, id)` order. |
| RF-06 | RP-06, RP-15, RP-12 | Summarization failure is never fatal: any error in the step marks the row `failed` with a closed code (`nlp_unavailable`, `invalid_output`, `exhausted`) and the answer continues with the previous summary (or none) plus all messages after that boundary. While the latest attempt failed, the UI shows "Não foi possível resumir o contexto. O histórico completo continua disponível." after that learner message. The next learner message re-evaluates and retries. Cancel during summarization discards an uncommitted summary; a summary committed before cancel stays. Retry reuses the same learner message (existing SHIFU-100 behavior) and never duplicates it. No partial summary is ever visible. |
| RF-07 | RP-03, RP-11, RP-13 | Only the owner can read a conversation's summary state or content. A foreign session, a tombstoned session and a session without a ready summary are indistinguishable (404). The step re-checks account access before reading messages and again at commit; inactive account or changed access revision discards the result without a notice. |
| RF-08 | RP-03, RP-11, RP-13, JN-14, JN-16 | Deleting a conversation removes all its summary rows in the deletion transaction; an in-flight step cannot commit afterwards. `identity/account.deleted` purges every summary row of the account immediately (idempotent). Pending or late processing never recreates a summary for a deleted conversation or closed account. |
| RF-09 | RP-15, JN-19 | Session detail exposes `summary.current` (marker data or null) and `summary.failure_after_message_id` (notice anchor or null). `GET …/summary` returns the rendered summary `text` (deterministic pt-BR template over the verbatim excerpts), `version`, `covered_message_count` and `first_message_id`; it never returns offsets. Responses are private and `no-store`. Response progress is **the progress of the latest status event** (null clears it): the step emits `summarize-context` when it starts summarizing and a closing `status/processing` event with null progress when it ends (ready, failed or discarded), so "Resumindo contexto…" ends live and after reconnect/replay. `write-answer`/`review-answer` keep their meaning. |
| RF-10 | RP-12, RP-15, JN-19 | Page and FAB: while `progress = summarize-context` the live area shows the processing marker ("Resumindo contexto…", not color-only, reduced-motion safe) after the pending message instead of `ResponseStatus`, with "Cancelar" reachable, and the composer is disabled with placeholder "Aguarde enquanto o contexto é resumido". After completion the ready marker marks where the summarization happened: it sits right after the learner message whose answer run produced the summary (`summary.current.after_message_id`, the same spot where "Resumindo contexto…" was shown) and before that message's answer, and it stays there as the conversation continues until a newer summary replaces it. When that message is unknown (its attempt no longer exists) the marker falls back to right after the boundary message, or to the top of the loaded list when the boundary is in an unloaded older page. The position is presentation only: the summary still covers exactly the messages up to the boundary. "Ver resumo" opens a modal dialog titled "Resumo desta conversa" with the summary text as plain text, "Suas mensagens originais continuam disponíveis.", "Ver mensagens originais" and "Fechar resumo"; focus moves into the dialog and is trapped there. "Ver mensagens originais" closes the dialog, loads older pages until the first summarized message is present, scrolls to it and moves focus to it. "Fechar resumo", the close button and Escape close the dialog and return focus to "Ver resumo". The dialog is centered (`max-w-lg`) on desktop and near full-screen with 16 px margins at 390 px; in the FAB it renders above the panel. Keyboard operable, pt-BR, no horizontal overflow at 390 px. |
| RF-11 | RP-13 | Summarization sends no data outside Shifu. Telemetry, when enabled, receives one operational span per summarization with only an opaque correlation UUID, duration, outcome (`ready`, `failed`, `discarded`), closed failure code and counts; the router span adds an `expanded` count. No account/session/message IDs or text. Telemetry failure never changes the result. |
| RF-12 | RP-15; SHIFU-102 validation | A versioned synthetic pt-BR evaluation of long conversations gates quality: per case Dúvida/Orientação recall ≥ 0.80, Assunto recall ≥ 0.70, 100% span fidelity, zero cross-case leakage and zero fenced-code excerpts. |

| ID | RF coverage | Given | When | Then | Checks |
| --- | --- | --- | --- | --- | --- |
| CA-01 | RF-01 | Conversations whose unsummarized volume is 19 / 20 messages and 15,999 / 16,000 code points, with and without a previous boundary | The answer run starts | Exactly the ≥ 20 / ≥ 16,000 cases summarize; boundary = newest message outside the 10-message window; below threshold no row/event/progress | CI-01, CI-05 |
| CA-02 | RF-01, RF-11 | Any summarization | It runs, succeeds or fails | No usage receipt, model call, quota effect or outbound text; telemetry span allowlisted | CI-01, CI-05 |
| CA-03 | RF-02, RF-12 | Conversations with code fences, greetings, topic change, previous summary | Summarize | Excerpts are verbatim spans of this conversation, within limits, not in fences; same input ⇒ same output; previous excerpts fold in | CI-01, CI-05, CI-08 |
| CA-04 | RF-03 | A ready v1 and a failed row exist | v2 completes | v2 ready; v1 and failed rows gone in the same transaction; one ready / one processing max enforced by the database | CI-01, CI-05, CI-17 |
| CA-05 | RF-04, RF-05 | Ready summary with boundary B; messages after B including the pending one | Prepare runs | History = all messages after B (none lost); summary and bounded history reach the reviewer request; attachment answer input unchanged; Learning context read fresh; no summary ⇒ today's behavior; messages unchanged and ordered | CI-02, CI-05 |
| CA-06 | RF-04 | Elliptical part without FAQ match; non-elliptical part; explicit reference present | Route with topics | Single guarded retry only for the elliptical unmatched part, same gates; never alters references/proposals/clarifications; existing router regressions stay green | CI-05, CI-09 |
| CA-07 | RF-06 | Summarizer raises (NLP unavailable / invalid output / other) | Answer run | Row `failed` with the right code; answer completes normally; notice anchored after that learner message; next message retries and, on success, notice disappears | CI-01, CI-05, CI-10, CI-11 |
| CA-08 | RF-06 | Summarization in progress | Learner cancels, then retries | Uncommitted summary discarded; committed summary kept; retry uses the same learner message; no duplicate message | CI-01, CI-05 |
| CA-09 | RF-07 | Accounts A and B; sessions S1/S2 of A | B reads A's summary; S2 answer runs | 404 for B (same as absent/tombstoned); S2 never sees S1 content; access revision change or inactive account discards the step | CI-01, CI-04, CI-05, CI-06 |
| CA-10 | RF-08 | Ready and processing summaries | Learner deletes the conversation during/after summarization | Summary rows gone in the deletion transaction; late commit discarded; nothing readable or recreated | CI-03, CI-05, CI-06 |
| CA-11 | RF-08 | Account with summaries | `identity/account.deleted` delivered (twice) | All its summary rows deleted immediately; second delivery is a no-op success; invalid payload is non-retriable | CI-03, CI-07 |
| CA-12 | RF-09 | Session with/without ready or failed summary; response in progress | GET detail, GET summary, SSE live and replay | Contract fields/404/no-store as specified; `summarize-context` shown while summarizing and cleared by the closing null-progress event, live and after reconnect; `write-answer`/`review-answer` unchanged; no offsets exposed | CI-01, CI-04, CI-05, CI-06, CI-10 |
| CA-13 | RF-10 | Page and FAB at 1440/390 | Summarizing → summarized → open dialog → originals → close; failure | States, placement, dialog focus trap and return, keyboard/Escape, plain text, no overflow, not color-only | CI-10, CI-11, VM-01, VM-02, VM-03, VM-04, VM-05, VM-06 |
| CA-14 | RF-12 | Versioned synthetic dataset | Run the eval | Thresholds met; failure exits non-zero | CI-08 |

# Technical Contract

## Architecture Mapping

**Owner:** Intelligence. Identity contributes only the existing `MentorAccessProvider`
(`assert_current` with the attempt's grant) and the `identity/account.deleted` event name
(injected by composition). Learning, Curriculum and Gamification are unchanged. Shared
gains nothing; it keeps owning the outbox, AgentOS transport and telemetry transport.

**Rules** ([router](../../../rules.md)): Python Conventions, Core Layer, Use Case Testing,
Database Layer, Provision Layer, AI Layer, Messaging Layer, Job Testing, REST Layer,
Controller Testing, Server App Layer, TypeScript Conventions, UI Layer, Widget Testing.
Web App Routing is not selected (no route/search change). Re-run discovery if scope expands.

**Selected approach and rationale:** summarization is a **pre-answer step of the existing
answer workflow** (matches KVnFQ/RDiWy and JN-19; reuses the attempt claim, SSE progress
and RP-06's in-progress lock; no concurrent summary runs, no polling). The algorithm is a
technology-named provider behind a Core port (AI Rules: NLP adapters in providers, policy
in Core). Storage keeps **spans, not copied text** (RP-13 minimization; excerpts cannot
drift). Rejected: separate AgentOS workflow after completion (did not match the approved
design; needed polling and its own lease/retry queue); Inngest job (would load a second
copy of the NLP models; AI Rules route asynchronous NLP through AgentOS); LLM/abstractive
summary (user decision: local NLP; avoids RP-13 inference and quota).

| Action | Boundary | Element / Path | Required change |
| --- | --- | --- | --- |
| Create | Core entity | `MentorSessionSummary` — `apps/server/src/shifu/intelligence/core/domain/entities/mentor_session_summary.py` | Versioned summary row (declaration below); exported from `entities/__init__.py`. |
| Create | Core enums | `MentorSummaryStatus`, `MentorSummaryFailureCode`, `MentorSummaryExcerptKind` — `core/domain/enums/mentor_summary_status.py`, `mentor_summary_failure_code.py`, `mentor_summary_excerpt_kind.py` | `StrEnum`s; exported. |
| Modify | Core enum | `MentorWorkflowStep` — `core/domain/enums/mentor_workflow_step.py` | Adds `SUMMARIZE_CONTEXT = 'summarize-context'`. |
| Create | Core structures | `MentorSummaryBoundary`, `MentorSummaryExcerptSpan`, `MentorTextSpan`, `MentorMessageVolume`, `MentorConversationSummaryDraft`, `MentorSummaryExcerpt`, `MentorConversationSummaryContext`, `MentorSummaryMarker`, `MentorSessionSummaryState`, `MentorSessionSummaryContent` — one module each under `core/domain/structures/` | Immutable `@structure`s (declarations below); exported. `MentorConversationSummaryContext.from_summary(...)` is the single pure Core renderer (templates as Core constants). |
| Modify | Core structures | `MentorGenerationRequest` — `core/domain/structures/mentor_generation_request.py`; `MentorSessionDetail` — `core/domain/structures/mentor_session_detail.py` | Request: `history` now holds only messages after the boundary; adds `summary` (read by the reviewer). Detail: adds `summary: MentorSessionSummaryState`. |
| Create | Core error | `MentorSessionSummaryNotFoundError` — `core/domain/errors/mentor_session_summary_not_found_error.py` | Typed 404 for absent/foreign/tombstoned. |
| Create | Core ports | `MentorSessionSummariesRepository` — `core/interfaces/mentor_session_summaries_repository.py`; `MentorConversationSummarizerProvider` — `core/interfaces/mentor_conversation_summarizer_provider.py` | Declarations below; exported. |
| Modify | Core ports | `MentorMessagesRepository` (`measure_unsummarized`, `find_range`, `find_by_ids`), `MentorRouteProvider.route(..., topics=())`, `MentorTelemetryProvider.emit` (`outcome` adds `ready`/`discarded`, optional `failure_code`), `IntelligenceDatabaseRepositories.mentor_session_summaries` | Existing members unchanged; `find_all` stays for its existing consumers. |
| Create | Core use cases | `SummarizeMentorSessionContextUseCase`, `GetMentorSessionSummaryUseCase`, `PurgeMentorSummariesForAccountUseCase` — `core/use_cases/*.py` | Policy, fences, purge; exported from `use_cases/__init__.py`. |
| Modify | Core use cases | `PrepareMentorResponseUseCase` (`prepare_mentor_response_use_case.py`), `RemoveMentorSessionUseCase` (`remove_mentor_session_use_case.py`), detail loader `load_mentor_detail` (`mentor_detail.py`) | Prepare reads ready summary + `find_range` + `find_by_ids`; passes `topics` and the request `summary`. Remove calls `mentor_session_summaries.remove_by_session_id` **immediately after `lock_session`**, before events/attempts/messages removal. Detail loader adds `summary` state. |
| Create | Provider | `TextrankMentorConversationSummarizerProvider` — `providers/summarization/textrank/textrank_mentor_conversation_summarizer_provider.py` (+ `__init__.py` files) | TextRank/MMR/key phrases with fixed constants; receives the shared `SpacyMentorTextPreprocessorProvider` (concrete, for `segment()`, following the router's existing concrete use) and `MentorEmbeddingsProvider`; loads cue data. |
| Modify | Providers | `SpacyMentorTextPreprocessorProvider` (`segment`); `LocalMentorRouteProvider` (`topics` guarded retry, `expanded` count); `LazyMentorRouteProvider` (accepts injected preprocessor/embeddings instances instead of constructing them); `LangfuseMentorTelemetryProvider` — `providers/telemetry/langfuse/langfuse_mentor_telemetry_provider.py` (allowlist for new outcomes and `failure_code`) | Existing methods/thresholds unchanged. |
| Create | AI data | `ai/data/mentor-summary-cues.json`; `ai/data/mentor-summary-evaluation.json` | Versioned cue lists (validated at provider construction); versioned synthetic eval dataset. |
| Modify | AI workflow | `ProcessMentorResponseWorkflow` — `ai/agno/workflows/process_mentor_response_workflow.py`; `MentorReviewerAgent` — `ai/agno/agents/mentor_reviewer_agent.py`; `IntelligenceWorkflowsRegistry` — `ai/intelligence_workflows_registry.py` | New first step `summarize-conversation-context` (`max_retries=0`, executor never raises); reviewer instructions read `summary` + recent `history`; registry owns **one** lazy spaCy preprocessor and **one** E5 embeddings instance shared by `LazyMentorRouteProvider` and the summarizer, accepts `summarizer: MentorConversationSummarizerProvider \| None = None` (test seam) and exposes `purge_mentor_summaries_use_case`. No new workflow ID, event or outbox route. |
| Create | SQLAlchemy | `MentorSessionSummaryModel` (`database/sqlalchemy/models/mentor_session_summary_model.py`), mapper (`mappers/mentor_session_summary_mapper.py`), repository (`repositories/mentor_session_summaries_repository.py`) | Table/constraints below; registered in `models/__init__.py` and `intelligence_database.py`. |
| Modify | SQLAlchemy | `MentorMessagesRepository` adapter (`repositories/mentor_messages_repository.py`); `MentorResponseEventsRepository.snapshot` (`repositories/mentor_response_events_repository.py`); `MentorResponseEventModel` (`models/mentor_response_event_model.py`) | Aggregate/range/by-ids queries over existing indexes; snapshot `progress` = progress of the latest `status` event (null allowed); `ck_mentor_event_progress` accepts `summarize-context`. |
| Create | Migration | `apps/server/migrations/versions/<generated>_add_mentor_session_summaries.py` | Generated with `uv run poe db:migrate "add mentor session summaries"` from `apps/server` (against the local development database, generation only), then reviewed: create table, indexes, constraints; replace `ck_mentor_event_progress`; downgrade reverses both (downgrade fails safely if any `summarize-context` progress rows exist — documented in the revision). No backfill. |
| Create | Messaging | `PurgeMentorSummariesOnAccountDeletedJob` — `messaging/inngest/jobs/purge_mentor_summaries_on_account_deleted_job.py` | `FUNCTION_ID = 'intelligence-purge-mentor-summaries-on-account-deleted'`; `_EVENT_NAME` injected; step `purge_mentor_summaries`; `retries=3`. |
| Modify | Messaging / composition | `IntelligenceInngestMessaging.register_jobs` (`messaging/inngest/intelligence_inngest_messaging.py`); `apps/server/src/shifu/app.py` | Registers the job beside the attachment purge job with the `identity/account.deleted` name from `AccountDeletedEvent.EVENT_NAME`, using the registry's `purge_mentor_summaries_use_case`. |
| Create | REST | `GetMentorSessionSummaryController` — `rest/controllers/get_mentor_session_summary_controller.py` (module-local `Response`) | `GET /intelligence/mentor-sessions/{session_id}/summary`; constructs `GetMentorSessionSummaryUseCase(database, access_provider)` from the existing `IntelligencePipe` database/access dependencies, like `GetMentorSessionController` (no new pipe getter). |
| Modify | REST | `get_mentor_session_controller.py` (`Response` gains `summary`); `MentorSessionSchemas` (`rest/schemas/mentor_session_schemas.py`: `Detail` gains `summary`, inherited by `submit_mentor_message_controller.Response`); `rest/router.py`; `apps/server/rest-client/intelligence/intelligence.rest` | Progress stays typed by `MentorWorkflowStep` on `MentorResponseSnapshot` (no separate REST literal). Examples added. |
| Create / Modify | Eval | Create `apps/server/evals/summarize_mentor_session_eval.py`; modify `evals/run.py` and `apps/server/tests/evals/test_run.py` | Selector `summarize-mentor-session` in `EVAL_CLASSES`; the eval test proves a failing case exits non-zero. |
| Modify | CI | `.github/workflows/server-app-ci.yaml` | Add new/modified test files to `changed-file-coverage`'s explicit list; add the existing "Prepare pinned local Mentor model" step to the `evals` job. |
| Modify | Web dependency | `apps/web/package.json`, `pnpm-lock.yaml` | Add `@radix-ui/react-dialog` (same family/major line as the installed `@radix-ui/react-alert-dialog`) via `pnpm --filter web add @radix-ui/react-dialog`. |
| Create | Web primitive | `apps/web/src/ui/shadcn/dialog.tsx` | shadcn-style Dialog primitive reusing `.dialog-overlay`/`.dialog-content` and their reduced-motion rules; non-alert `role="dialog"`. |
| Modify | Web core | `apps/web/src/core/intelligence/mentor-response.ts`; Create `apps/web/src/core/intelligence/mentor-session-summary.ts` | `MentorWorkflowStep` union adds `'summarize-context'`; summary types (declarations below). |
| Modify | Web REST | `apps/web/src/rest/services/intelligence-service.ts` | Map `detail.summary`; add `getMentorSessionSummary(sessionId)`. |
| Modify | Web hooks | `ui/intelligence/hooks/use-mentor-response-stream.ts` | Zod progress enum accepts `summarize-context` and null on status events (no test file change: realtime hooks are proven at their consumers). |
| Modify | Web context | `ui/intelligence/contexts/mentor-context/use-mentor-context-provider.ts`, `types/mentor-context-value.ts` | Summary state from detail; on `status` events apply `event.progress` (null clears); `revealMessage(messageId)`. |
| Create / Modify | Web widgets | `summary-marker/` (new, with colocated `use-mentor-session-summary-query.ts`), `conversation/`, `message-list/`, `message-item/`, `composer/`, `response-status/` under `ui/intelligence/widgets/components/mentor-chat/conversation/`; shared `Icon` map | Composition below. |

### Expected file tree

```text
.github/workflows/server-app-ci.yaml                                         [M]
pnpm-lock.yaml                                                               [M]
apps/server/
├── migrations/versions/<generated>_add_mentor_session_summaries.py          [N] (name produced by alembic)
├── rest-client/intelligence/intelligence.rest                               [M]
├── evals/
│   ├── run.py                                                               [M]
│   └── summarize_mentor_session_eval.py                                     [N]
├── src/shifu/
│   ├── app.py                                                               [M]
│   └── intelligence/
│       ├── ai/
│       │   ├── data/{mentor-summary-cues.json, mentor-summary-evaluation.json}  [N]
│       │   ├── intelligence_workflows_registry.py                           [M]
│       │   └── agno/
│       │       ├── agents/mentor_reviewer_agent.py                          [M]
│       │       └── workflows/process_mentor_response_workflow.py            [M]
│       ├── core/
│       │   ├── domain/
│       │   │   ├── entities/{__init__.py [M], mentor_session_summary.py [N]}
│       │   │   ├── enums/{__init__.py [M], mentor_workflow_step.py [M],
│       │   │   │          mentor_summary_status.py [N], mentor_summary_failure_code.py [N],
│       │   │   │          mentor_summary_excerpt_kind.py [N]}
│       │   │   ├── errors/{__init__.py [M], mentor_session_summary_not_found_error.py [N]}
│       │   │   └── structures/
│       │   │       ├── __init__.py                                          [M]
│       │   │       ├── mentor_summary_boundary.py                           [N]
│       │   │       ├── mentor_summary_excerpt_span.py                       [N]
│       │   │       ├── mentor_summary_excerpt.py                            [N]
│       │   │       ├── mentor_text_span.py                                  [N]
│       │   │       ├── mentor_message_volume.py                             [N]
│       │   │       ├── mentor_conversation_summary_draft.py                 [N]
│       │   │       ├── mentor_conversation_summary_context.py               [N] (from_summary renderer)
│       │   │       ├── mentor_summary_marker.py                             [N]
│       │   │       ├── mentor_session_summary_state.py                      [N]
│       │   │       ├── mentor_session_summary_content.py                    [N]
│       │   │       ├── mentor_generation_request.py                         [M]
│       │   │       └── mentor_session_detail.py                             [M]
│       │   ├── interfaces/
│       │   │   ├── __init__.py                                              [M]
│       │   │   ├── mentor_session_summaries_repository.py                   [N]
│       │   │   ├── mentor_conversation_summarizer_provider.py               [N]
│       │   │   ├── mentor_messages_repository.py                            [M]
│       │   │   ├── mentor_route_provider.py                                 [M]
│       │   │   ├── mentor_telemetry_provider.py                             [M]
│       │   │   └── intelligence_database.py                                 [M]
│       │   └── use_cases/
│       │       ├── __init__.py                                              [M]
│       │       ├── summarize_mentor_session_context_use_case.py             [N]
│       │       ├── get_mentor_session_summary_use_case.py                   [N]
│       │       ├── purge_mentor_summaries_for_account_use_case.py           [N]
│       │       ├── prepare_mentor_response_use_case.py                      [M]
│       │       ├── remove_mentor_session_use_case.py                        [M]
│       │       └── mentor_detail.py                                         [M]
│       ├── database/sqlalchemy/
│       │   ├── intelligence_database.py                                     [M]
│       │   ├── models/{__init__.py [M], mentor_session_summary_model.py [N],
│       │   │           mentor_response_event_model.py [M]}
│       │   ├── mappers/{__init__.py [M], mentor_session_summary_mapper.py [N]}
│       │   └── repositories/{__init__.py [M], mentor_session_summaries_repository.py [N],
│       │                     mentor_messages_repository.py [M], mentor_response_events_repository.py [M]}
│       ├── providers/
│       │   ├── summarization/__init__.py                                    [N]
│       │   ├── summarization/textrank/__init__.py                           [N]
│       │   ├── summarization/textrank/textrank_mentor_conversation_summarizer_provider.py [N]
│       │   ├── text_preprocessing/spacy/spacy_mentor_text_preprocessor_provider.py      [M]
│       │   ├── routing/{local_mentor_route_provider.py, lazy_mentor_route_provider.py}  [M]
│       │   └── telemetry/langfuse/langfuse_mentor_telemetry_provider.py     [M]
│       ├── messaging/inngest/
│       │   ├── intelligence_inngest_messaging.py                            [M]
│       │   └── jobs/{__init__.py [M], purge_mentor_summaries_on_account_deleted_job.py [N]}
│       └── rest/
│           ├── controllers/{__init__.py [M], get_mentor_session_summary_controller.py [N],
│           │                get_mentor_session_controller.py [M]}
│           ├── schemas/mentor_session_schemas.py                            [M]
│           └── router.py                                                    [M]
└── tests/
    ├── evals/test_run.py                                                    [M]
    ├── fixtures/mentor_job_fixture.py                                       [M] (long-conversation seeding helper and summarizer seam wiring, if not expressible through existing helpers)
    ├── intelligence/core/use_cases/
    │   ├── test_summarize_mentor_session_context_use_case.py                [N]
    │   ├── test_get_mentor_session_summary_use_case.py                      [N]
    │   ├── test_purge_mentor_summaries_for_account_use_case.py              [N]
    │   ├── test_prepare_mentor_response_use_case.py                         [M]
    │   ├── test_remove_mentor_session_use_case.py                           [M]
    │   └── test_get_mentor_session_use_case.py                              [M]
    ├── intelligence/server/controllers/
    │   ├── test_get_mentor_session_summary_controller.py                    [N]
    │   ├── test_get_mentor_session_controller.py                            [M]
    │   ├── test_remove_mentor_session_controller.py                         [M]
    │   └── test_stream_mentor_response_controller.py                        [M]
    ├── intelligence/server/agentos/
    │   ├── test_process_mentor_response_summary.py                          [N]
    │   └── test_process_mentor_response_workflow.py                         [M] (composition/constructor only)
    └── messaging/inngest/jobs/intelligence/
        └── test_purge_mentor_summaries_on_account_deleted_job.py            [N]
apps/web/
├── package.json                                                             [M] @radix-ui/react-dialog
├── src/
│   ├── core/intelligence/{mentor-response.ts [M], mentor-session-summary.ts [N]}
│   ├── rest/services/intelligence-service.ts                                [M]
│   └── ui/
│       ├── shadcn/dialog.tsx                                                [N]
│       ├── shared/widgets/components/icon/index.tsx                         [M] scroll-text
│       └── intelligence/
│           ├── hooks/use-mentor-response-stream.ts                          [M]
│           ├── contexts/mentor-context/
│           │   ├── use-mentor-context-provider.ts                           [M]
│           │   ├── types/mentor-context-value.ts                            [M]
│           │   └── tests/{use-mentor-context-provider.test.ts,
│           │            mentor-transport-consumer.test.tsx}                 [M]
│           └── widgets/components/mentor-chat/conversation/
│               ├── index.tsx                                                [M] live area: processing marker / failure notice
│               ├── use-conversation.ts                                      [M] ConversationItem; reveal target scroll/focus
│               ├── tests/{conversation.test.tsx, use-conversation.test.ts}  [M]
│               ├── message-list/index.tsx                                   [M] renders summary-marker items
│               ├── message-list/message-item/index.tsx                      [M] id / data-message-id / tabIndex -1
│               ├── message-list/message-item/tests/message-item.test.tsx    [M]
│               ├── summary-marker/                                          [N] Mentor/CompactionMarker (ready | processing | failed)
│               │   ├── index.tsx
│               │   ├── use-summary-marker.ts
│               │   ├── use-mentor-session-summary-query.ts                  colocated query hook (no dedicated test)
│               │   ├── summary-dialog/index.tsx                             pure renderer inside ui/shadcn/dialog (no hook, no test file)
│               │   └── tests/{summary-marker.test.tsx, use-summary-marker.test.ts}
│               ├── composer/{index.tsx, use-composer.ts}                    [M]
│               ├── composer/tests/{composer.test.tsx, use-composer.test.ts} [M]
│               └── response-status/index.tsx                                [M] (no test file; covered by conversation tests)
└── tests/
    ├── intelligence/intelligence-page.test.ts                               [M]
    └── shared/app-layout.test.ts                                            [M] (FAB)
documentation/features/intelligence/mentor-conversation-summary/
├── spec.md                                                                  [N]
└── design/{handoff.md, references/{KVnFQ,RDiWy,T4Edi,ov9QQ,ySE0r}.png}      [N]
```

No Intelligence faker module exists today; tests construct `MentorSessionSummary` through
its `start`/`complete`/`fail` methods, following the existing Intelligence tests.

### New concepts

**Summary row (`MentorSessionSummary`).** Intelligence-owned derived personal data, one
row per version in `intelligence_mentor_session_summaries`. Source of truth for "what
the Mentor uses as context of older messages". Lifecycle: created `processing` by the
summarize step of one answer attempt → `ready` (replacing older rows) or `failed`.
Example: a conversation with 31 messages gets v1 covering messages 1–21 (boundary =
message 21); messages 22–31 stay recent. Authorization comes from the owning attempt's
access grant; lifetime is bounded by its conversation (explicit removal + FK cascade).

**Span (`MentorSummaryExcerptSpan`).** A pointer into one message
(`message_id`, `start`, `end`, `kind`) instead of a copy of text. Rendering slices the
current message content loaded with `find_by_ids`; validation guarantees it stays inside
the message, outside fenced code and ≤ 280 code points. Spans are never sent to the browser.

**Summarizer provider (`MentorConversationSummarizerProvider`).** A pure function
`summarize(messages, previous) -> draft`. Input: the range messages and the previous
rendered context; output: topics, spans, `algorithm_version`. It owns no state and
performs no I/O except reading the shared, already-loaded models and its cue data. The
registry owns the single spaCy preprocessor and E5 embeddings instances and injects them
into both this provider and `LazyMentorRouteProvider`. Algorithm (fixed `ClassVar`
constants, part of `algorithm_version`): spaCy sentence spans via `segment()` (fenced
code removed from candidates) → drop candidates with < 4 content tokens → E5 passage
embeddings → similarity graph with edges at cosine ≥ 0.30 → PageRank (damping 0.85,
≤ 100 iterations, tolerance 1e-6) → cue-based kind (learner question cues ⇒ doubt,
Mentor guidance cues ⇒ guidance, from `mentor-summary-cues.json`) → MMR (λ = 0.70, skip
similarity ≥ 0.92) up to 5 per kind; key phrases from noun chunks + inline-code
identifiers deduplicated by lemma, scored by centroid cosine × frequency weight, MMR up to 8.

**Rendered context (`MentorConversationSummaryContext`).** The summary as consumers see
it: topics, excerpt texts with their `message_id`, and the template `text`. Built only by
the pure Core factory `MentorConversationSummaryContext.from_summary(summary, messages)`
from a ready row and its source messages; the pt-BR templates are Core constants. Example
text: *"Nesta conversa, os assuntos foram range, lista e índices. Você perguntou: “Meu
laço não mostra o último item da lista. O que esqueci?” O Mentor orientou: “Veja quais
índices range produz e compare com o tamanho da lista.”"* Consumed by the reading
endpoint, the reviewer request and the router (`topics`). The REST read path therefore
needs no NLP provider.

**Summary state on detail (`MentorSessionSummaryState`).** What the timeline needs
without loading content: `current` (version, boundary message, covered count,
completed_at, after_message_id) and `failure_after_message_id`. "In progress" is **not** part of it; it
comes from the response snapshot's latest status-event progress, so there is one source
of truth for in-flight state.

**Progress semantics.** A response's progress is the progress of its latest `status`
event; a status event with null progress clears it. The summarize step brackets its work
with `summarize-context` and a closing null-progress status event, so the indicator ends
both live and on reconnect. Existing `write-answer`/`review-answer` events already are
status events and keep their behavior.

### Declarations (Python, Core)

```python
# core/domain/enums/mentor_summary_status.py
class MentorSummaryStatus(StrEnum):
    PROCESSING = 'processing'
    READY = 'ready'
    FAILED = 'failed'

# core/domain/enums/mentor_summary_failure_code.py
class MentorSummaryFailureCode(StrEnum):
    NLP_UNAVAILABLE = 'nlp_unavailable'
    INVALID_OUTPUT = 'invalid_output'
    EXHAUSTED = 'exhausted'

# core/domain/enums/mentor_summary_excerpt_kind.py
class MentorSummaryExcerptKind(StrEnum):
    DOUBT = 'doubt'
    GUIDANCE = 'guidance'

# core/domain/enums/mentor_workflow_step.py (result)
class MentorWorkflowStep(StrEnum):
    SUMMARIZE_CONTEXT = 'summarize-context'
    WRITE_ANSWER = 'write-answer'
    REVIEW_ANSWER = 'review-answer'

# core/domain/structures/mentor_summary_boundary.py
@structure
class MentorSummaryBoundary:
    message_id: str
    created_at: datetime  # UTC; ordering is (created_at, message_id)

# core/domain/structures/mentor_text_span.py — returned by SpacyMentorTextPreprocessorProvider.segment()
@structure
class MentorTextSpan:
    start: int  # code-point offset, inclusive
    end: int    # code-point offset, exclusive

# core/domain/structures/mentor_summary_excerpt_span.py
@structure
class MentorSummaryExcerptSpan:
    message_id: str
    start: int
    end: int
    kind: MentorSummaryExcerptKind

# core/domain/structures/mentor_message_volume.py
@structure
class MentorMessageVolume:
    count: int
    characters: int
    last_message: MentorSummaryBoundary | None  # newest message outside the recent window

# core/domain/structures/mentor_conversation_summary_draft.py
@structure
class MentorConversationSummaryDraft:
    topics: tuple[str, ...]                         # ≤ 8, each non-empty, ≤ 80 code points
    excerpts: tuple[MentorSummaryExcerptSpan, ...]  # ≤ 5 doubt + ≤ 5 guidance
    algorithm_version: str

# core/domain/structures/mentor_summary_excerpt.py
@structure
class MentorSummaryExcerpt:
    message_id: str
    kind: MentorSummaryExcerptKind
    text: str

# core/domain/structures/mentor_conversation_summary_context.py
@structure
class MentorConversationSummaryContext:
    version: int
    boundary: MentorSummaryBoundary
    covered_message_count: int
    first_message_id: str
    topics: tuple[str, ...]
    excerpts: tuple[MentorSummaryExcerpt, ...]
    text: str  # deterministic pt-BR template over topics/excerpts

    @classmethod
    def from_summary(
        cls, summary: 'MentorSessionSummary', messages: tuple[MentorMessage, ...]
    ) -> 'MentorConversationSummaryContext': ...  # pure; raises ValueError if a span's message is missing

# core/domain/entities/mentor_session_summary.py
@frozen_entity
class MentorSessionSummary:
    id: str
    account_id: str
    session_id: str
    attempt_id: str | None          # required while PROCESSING
    version: int                     # ≥ 1, unique per session
    status: MentorSummaryStatus
    boundary: MentorSummaryBoundary
    covered_message_count: int       # > 0
    first_message_id: str
    topics: tuple[str, ...]          # non-empty only when READY
    excerpts: tuple[MentorSummaryExcerptSpan, ...]  # only when READY
    algorithm_version: str | None    # only when READY
    failure_code: MentorSummaryFailureCode | None   # only when FAILED
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None    # only when READY

    @classmethod
    def start(cls, *, id: str, account_id: str, session_id: str, attempt_id: str,
              version: int, boundary: MentorSummaryBoundary, covered_message_count: int,
              first_message_id: str, now: datetime) -> 'MentorSessionSummary': ...
    def complete(self, draft: MentorConversationSummaryDraft, now: datetime) -> 'MentorSessionSummary': ...
    def fail(self, code: MentorSummaryFailureCode, now: datetime) -> 'MentorSessionSummary': ...

# core/domain/structures/mentor_summary_marker.py
@structure
class MentorSummaryMarker:
    version: int
    boundary_message_id: str
    covered_message_count: int
    completed_at: datetime
    after_message_id: str | None = None  # learner message that triggered the summary

# core/domain/structures/mentor_session_summary_state.py
@structure
class MentorSessionSummaryState:
    current: MentorSummaryMarker | None = None
    failure_after_message_id: str | None = None

# core/domain/structures/mentor_session_summary_content.py
@structure
class MentorSessionSummaryContent:
    version: int
    text: str
    covered_message_count: int
    first_message_id: str

# core/domain/structures/mentor_session_detail.py (result)
@structure
class MentorSessionDetail:
    session: MentorSession
    messages: MentorMessagesPage
    pending_learner_message_id: str | None
    response: MentorResponseSnapshot | None = None
    summary: MentorSessionSummaryState = MentorSessionSummaryState()

# core/domain/structures/mentor_generation_request.py (scoped excerpt; other fields unchanged)
@structure
class MentorGenerationRequest:
    ...
    history: tuple[MentorMessage, ...]  # now: only messages after the summary boundary
    ...
    attachment_context: MentorAttachmentContext | None = None
    summary: MentorConversationSummaryContext | None = None  # read by the reviewer only

# core/domain/errors/mentor_session_summary_not_found_error.py
class MentorSessionSummaryNotFoundError(NotFoundError):
    message: str = 'Resumo da conversa não encontrado.'
```

```python
class MentorSessionSummariesRepository(Protocol):
    def find_ready(self, account_id: str, session_id: str) -> MentorSessionSummary | None: ...
    def find_processing_for_update(self, account_id: str, session_id: str) -> MentorSessionSummary | None: ...
    def find_failed(self, account_id: str, session_id: str) -> MentorSessionSummary | None: ...
    def next_version(self, session_id: str) -> int: ...
    def add(self, summary: MentorSessionSummary) -> None: ...  # conflict on active index ⇒ typed error
    def update(self, summary: MentorSessionSummary) -> None: ...
    def remove_superseded(self, session_id: str, keep_id: str) -> None: ...  # ready + failed except keep_id
    def remove(self, summary_id: str) -> None: ...
    def remove_by_session_id(self, session_id: str) -> None: ...
    def remove_by_account_id(self, account_id: str) -> int: ...
    def remove_all(self) -> None: ...

class MentorConversationSummarizerProvider(Protocol):
    def summarize(
        self,
        messages: tuple[MentorMessage, ...],
        previous: MentorConversationSummaryContext | None,
    ) -> MentorConversationSummaryDraft: ...

class MentorMessagesRepository(Protocol):  # scoped excerpt; existing members unchanged
    def measure_unsummarized(
        self, account_id: str, session_id: str,
        after: MentorSummaryBoundary | None, keep_recent: int,
    ) -> MentorMessageVolume: ...
    def find_range(
        self, account_id: str, session_id: str,
        after: MentorSummaryBoundary | None, until: MentorSummaryBoundary | None = None,
    ) -> tuple[MentorMessage, ...]: ...
    def find_by_ids(
        self, account_id: str, session_id: str, message_ids: tuple[str, ...]
    ) -> tuple[MentorMessage, ...]: ...  # only messages of that session; order by (created_at, id)

class MentorRouteProvider(Protocol):
    def route(
        self, content: str, context: MentorContextSnapshot, topics: tuple[str, ...] = ()
    ) -> MentorRouteResult: ...

class MentorTelemetryProvider(Protocol):  # scoped excerpt of emit; scope() unchanged
    def emit(
        self, stage: str, *, correlation_id: str, profile: str, duration_ms: float,
        counts: Mapping[str, int],
        outcome: Literal['passed', 'failed', 'abstained', 'cancelled', 'ready', 'discarded'],
        failure_code: MentorSummaryFailureCode | None = None,
    ) -> None: ...

class SummarizeMentorSessionContextUseCase:
    SUMMARY_MESSAGE_THRESHOLD: ClassVar[int] = 20
    SUMMARY_CHARACTER_THRESHOLD: ClassVar[int] = 16_000
    RECENT_WINDOW: ClassVar[int] = 10
    def __init__(self, database: IntelligenceDatabase, summarizer: MentorConversationSummarizerProvider,
                 access_provider: MentorAccessProvider, clock_provider: ClockProvider,
                 identifier_provider: IdentifierProvider,
                 progress: RecordMentorResponseProgressUseCase,
                 renew_claim: RenewMentorResponseClaimUseCase,
                 telemetry: MentorTelemetryProvider) -> None: ...
    def execute(self, attempt_id: str, execution_owner: str) -> None: ...  # never raises

class GetMentorSessionSummaryUseCase:
    def __init__(self, database: IntelligenceDatabase, access_provider: MentorAccessProvider) -> None: ...
    def execute(self, account_id: str, session_id: str) -> MentorSessionSummaryContent: ...

class PurgeMentorSummariesForAccountUseCase:
    def __init__(self, database: IntelligenceDatabase) -> None: ...
    def execute(self, account_id: str) -> int: ...  # rows removed; idempotent
```

`SummarizeMentorSessionContextUseCase` records the opening `summarize-context` progress
through `RecordMentorResponseProgressUseCase` and appends the closing null-progress
status event itself through `MentorResponseEventsRepository` (that use case only accepts
a `MentorWorkflowStep`). `execute` **never raises**: claim loss, a missing
attempt, a deadlock or `OperationalError` in the claim phase, and any summary error all
end the step normally; prepare's existing `_start` then decides cancel or release exactly
as today. Exact dependency names follow existing source types; ordinary private helpers
remain implementation choices.

### Persistence

Table `intelligence_mentor_session_summaries` (SQLAlchemy model + reviewed Alembic revision):

- `id` String(26) PK (ULID); `account_id` String(26) not null, index `ix_mentor_summary_account`.
- `session_id` String(26) FK → `intelligence_mentor_sessions.id` **ON DELETE CASCADE**.
- `attempt_id` String(26) nullable FK → `intelligence_mentor_response_attempts.id` **ON DELETE SET NULL**.
- `version` Integer not null, `ck_mentor_summary_version` (`version >= 1`), unique `uq_mentor_summary_version (session_id, version)`.
- `status` String(16) not null, `ck_mentor_summary_status` in (`processing`, `ready`, `failed`).
- `boundary_message_id` String(26) not null FK → `intelligence_mentor_messages.id` **ON DELETE CASCADE**; `boundary_created_at` timestamptz not null.
- `first_message_id` String(26) not null; `covered_message_count` Integer `> 0`.
- `topics` JSONB null; `excerpts` JSONB null; `algorithm_version` String(64) null; `completed_at` timestamptz null.
- `failure_code` String(32) null, in (`nlp_unavailable`, `invalid_output`, `exhausted`).
- `created_at`, `updated_at` timestamptz not null.
- `ck_mentor_summary_ready_content`: `(status = 'ready') = (topics IS NOT NULL AND excerpts IS NOT NULL AND algorithm_version IS NOT NULL AND completed_at IS NOT NULL)`.
- `ck_mentor_summary_failure`: `(status = 'failed') = (failure_code IS NOT NULL)`.
- `ck_mentor_summary_processing_attempt`: `status <> 'processing' OR attempt_id IS NOT NULL`.
- Partial unique `uq_mentor_summary_ready (session_id) WHERE status = 'ready'`.
- Partial unique `uq_mentor_summary_active (session_id) WHERE status = 'processing'`.

Because a `processing` row requires its attempt, `RemoveMentorSessionUseCase` must remove
summary rows **before** attempts (immediately after `lock_session`); otherwise `SET NULL`
would violate `ck_mentor_summary_processing_attempt`.

`ck_mentor_event_progress` is replaced to accept
`progress IN ('summarize-context','write-answer','review-answer')` with the existing
`kind = 'status' AND status = 'processing'` condition (null progress stays valid).
`MentorResponseEventsRepository.snapshot` derives `progress` from the latest `status`
event of the processing attempt (null if that event has none). JSONB values are written
only from validated Core structures (`excerpts`: list of `{message_id, start, end, kind}`).
The repository adapter's range/aggregate queries use `ix_mentor_message_history
(session_id, created_at, id)`; `measure_unsummarized` excludes the newest `keep_recent`
rows by that order and sums `char_length(content)`; `find_by_ids` filters by session and
id list (≤ 10 ids).

### REST contract

`GET /intelligence/mentor-sessions/{session_id}` — the controller's `Response` (and
`MentorSessionSchemas.Detail`, inherited by `submit_mentor_message_controller.Response`)
gains:

```json
"summary": {
  "current": {"version": 2, "boundary_message_id": "01J…", "covered_message_count": 21,
              "completed_at": "2026-10-18T14:00:00Z", "after_message_id": "01J…"},
  "failure_after_message_id": null
}
```

`current` and `failure_after_message_id` are independently nullable. The snapshot's
`progress` (typed `MentorWorkflowStep | None`) may be `summarize-context`.

`GET /intelligence/mentor-sessions/{session_id}/summary` — authenticated, owner-only,
`Cache-Control: no-store`; module-local `Response` in its controller.

- 200 `{"version": 2, "text": "Nesta conversa, os assuntos foram …", "covered_message_count": 21, "first_message_id": "01J…"}`
- 404 `MentorSessionSummaryNotFoundError` (sanitized, same body for absent, foreign or tombstoned).
- 401/403/503 follow the existing Mentor read errors (access provider unavailable ⇒ existing sanitized mapping).

`apps/server/rest-client/intelligence/intelligence.rest` gains non-secret examples for
both requests using the file's existing variables.

### Web contracts

```ts
// core/intelligence/mentor-response.ts (scoped)
export type MentorWorkflowStep = 'summarize-context' | 'write-answer' | 'review-answer'

// core/intelligence/mentor-session-summary.ts
export type MentorSummaryMarker = {
  version: number
  boundaryMessageId: string
  coveredMessageCount: number
  completedAt: string
  afterMessageId: string | null  // learner message that triggered the summary
}
export type MentorSessionSummaryState = {
  current: MentorSummaryMarker | null
  failureAfterMessageId: string | null
}
export type MentorSessionSummaryContent = {
  version: number
  text: string
  coveredMessageCount: number
  firstMessageId: string
}

// MentorSessionDetail (rest/services/intelligence-service.ts) gains: summary: MentorSessionSummaryState
// IntelligenceService gains: getMentorSessionSummary(sessionId: string): Promise<MentorSessionSummaryContent>

// MentorContextValue (scoped additions)
summary: MentorSessionSummaryState
isSummarizingContext: boolean            // derived: response active && progress === 'summarize-context'
revealMessage(messageId: string): Promise<boolean>  // pages older messages until present; false if not found

// ui/shadcn/dialog.tsx — exports mirror ui/shadcn/alert-dialog.tsx, each
// ({ className = '', ...props }: React.ComponentPropsWithoutRef<typeof RadixDialog.X>)
export { Dialog, DialogTrigger, DialogPortal, DialogOverlay, DialogContent,
  DialogHeader, DialogFooter, DialogTitle, DialogDescription, DialogClose }

// ConversationItem (use-conversation.ts)
type ConversationItem =
  | { kind: 'message'; message: MentorMessage }
  | { kind: 'summary-marker'; marker: MentorSummaryMarker }
```

**Widget composition and state ownership.**

- `MentorContext` (provider shared by page and FAB, mounted in `app-layout`) owns
  `sessionDetail.summary`, derives `isSummarizingContext` from the response snapshot and
  SSE (on `status` events it applies `event.progress`, so null clears it), and exposes
  `revealMessage`, which reuses `readDetail`'s older-page loading and `mergeSessionDetail`.
  No polling or new transport.
- `Conversation` (`use-conversation.ts`) derives `ConversationItem[]`: the marker goes
  right after `afterMessageId` (the learner message that triggered the summary) when that
  message is loaded; otherwise right after `boundaryMessageId`; otherwise at the top of the
  loaded list (the boundary message is then not loaded, and all loaded messages are after it). When
  `isSummarizingContext`, the live area renders `SummaryMarker variant="processing"` in
  place of `ResponseStatus`, keeping the existing cancel action. When
  `failureAfterMessageId` is set and no summarization is in progress, a
  `SummaryMarker variant="failed"` is placed right after that message.
- `SummaryMarker` (`summary-marker/index.tsx` + `use-summary-marker.ts`) owns the dialog:
  `isOpen`, the content query (colocated `use-mentor-session-summary-query.ts`, fetched on
  first open, read-only; refetched when `marker.version` changes), "Ver mensagens
  originais" (close, then `revealMessage(firstMessageId)` and focus that message) and
  focus return to "Ver resumo" on close. The trigger has `aria-haspopup="dialog"`. The
  processing variant is an `<output>` with text; the failed variant has text plus
  `circle-alert`.
- `SummaryDialog` (`summary-dialog/index.tsx`) is a pure renderer inside the new
  `ui/shadcn/dialog.tsx` primitive and follows the UI Layer "Dialog header structure":
  a `scroll-text` semantic icon tile left of the title "Resumo desta conversa" and the
  `DialogDescription` "Suas mensagens originais continuam disponíveis."; the `x` close
  action isolated at the top-right; a soft separator between header and body; the body
  holds the plain-text `text` and its loading and error states; the footer holds "Ver
  mensagens originais" and "Fechar resumo". The primitive provides the focus trap,
  Escape and portal (above the FAB panel, as the existing AlertDialogs already do). The
  390 px near-full-screen layout is applied by `SummaryDialog` through the `className`
  override (`w-[calc(100%-2rem)]`, a viewport-bounded max height and internal scrolling);
  the primitive's base `max-w-lg` stays unchanged. No hook, no test file.
- `MessageItem` gets `id`/`data-message-id` and `tabIndex={-1}` on its focusable root so
  reveal can focus it. `Composer` is disabled with placeholder "Aguarde enquanto o
  contexto é resumido" while `isSummarizingContext`.
- The colocated query hook has no dedicated test; its behavior is proven through the
  `summary-marker` widget tests and the browser suites (Widget Testing Rules).

## Runtime Flow

```mermaid
sequenceDiagram
  participant B as AgentOS broker
  participant W as ProcessMentorResponseWorkflow
  participant S as SummarizeMentorSessionContextUseCase
  participant N as Textrank summarizer
  participant P as PrepareMentorResponseUseCase
  participant DB as PostgreSQL
  B->>W: ticket {attempt_id, event_id}
  W->>S: step summarize-conversation-context (never raises)
  S->>DB: claim attempt (owner=event_id), QUEUED→PROCESSING
  S->>DB: lock_session · delete stale processing row · measure_unsummarized
  alt below threshold or claim/phase error
    S-->>W: return
  else threshold met
    S->>DB: under session lock + fences: insert/resume processing row · progress summarize-context
    S->>S: assert_response_access
    S->>DB: find_range(prev boundary, new boundary) · find_by_ids(previous excerpts)
    S->>N: summarize(messages, previous) (no transaction, lease renewed)
    S->>DB: lock_session → find_by_id_for_update · not tombstoned · attempt current & claimed · row processing · assert_current · validate spans
    alt checks pass
      S->>DB: row ready; remove_superseded
    else summary error
      S->>DB: row failed(code)
    else fence failure
      S->>DB: discard (no write)
    end
    S->>DB: closing status event (progress = null)
    S-->>W: return
  end
  W->>P: step prepare-and-publish-local-response
  P->>DB: _start (same-owner re-claim) · ready summary · find_range(after=boundary) · find_by_ids
  P->>P: route(content, context, topics) · reviewer request(history, summary)
  W->>W: write/review loop (unchanged) → finalize (unchanged)
```

1. **Entry and trust.** The existing outbox → AgentOS ticket runs
   `intelligence-process-mentor-response` with `{attempt_id, event_id}`. The trusted
   account comes from the attempt row, never from browser input. The step validates the
   input like `_prepare_and_publish` and never raises.
2. **Claim.** The step claims the attempt with the same repository `claim` as prepare
   (QUEUED → PROCESSING, owner = event id, 5-minute lease) and appends the existing
   PROCESSING status event when transitioning. Prepare later re-claims with the same
   owner, which `claim()` already permits, and skips the transition because the attempt
   is already PROCESSING. If the claim fails or the claim phase hits a deadlock or
   `OperationalError`, the step returns and prepare's `_start` decides cancel or release.
3. **Stale rows.** Under `lock_session`, a `processing` row whose attempt is not the
   current claimed attempt is deleted; a `processing` row of this attempt (redelivery) is
   resumed with its frozen boundary.
4. **Measure.** `measure_unsummarized(after=ready.boundary or None, keep_recent=10)`;
   below both thresholds the step ends without writes.
5. **Start.** In the same session-locked transaction, after `assert_response_current`-
   equivalent fences (session not tombstoned, attempt current and claimed by this
   owner): insert `processing` (version = `next_version`, boundary =
   `volume.last_message`, first message = the conversation's first message, covered
   count = previous covered + range count) and record progress `summarize-context`
   through `RecordMentorResponseProgressUseCase` (SSE).
6. **Access and load.** `assert_response_access(attempt)`; inactive account / changed
   revision ⇒ delete the row (outcome `discarded`, no notice). Load the range
   `find_range(after=previous boundary, until=new boundary)` and the previous ready row's
   excerpt messages with `find_by_ids`, then build the previous context with
   `MentorConversationSummaryContext.from_summary`.
7. **Summarize.** Outside any transaction; the attempt lease is renewed through the
   existing renew use case. Provider errors map to `nlp_unavailable` (models/resources
   unavailable: `OSError`, `ServiceUnavailableError`) or `exhausted` (other transient
   errors such as database operational errors).
8. **Commit (fenced).** In one transaction: `lock_session`, then `find_by_id_for_update`
   (the same order as `RemoveMentorSessionUseCase`), session not tombstoned, attempt
   current and claimed by this owner, row still `processing`, `assert_response_access`;
   validate every span (message in this session's covered range, `0 ≤ start < end ≤ len`,
   ≤ 280 code points, outside fenced code) and limits; then `complete` +
   `remove_superseded`. Validation failure ⇒ `failed/invalid_output`. Fence failure ⇒
   discard without writes (a deletion transaction already removed the row).
9. **Failure write and close.** Errors from 7 are written as `failed` in their own
   transaction, guarded by the same fences; if the fences fail, nothing is written. In
   every outcome where the attempt is still current, `SummarizeMentorSessionContextUseCase`
   itself appends a closing `status/processing` event with null progress (next session
   sequence, inside its own fenced transaction: attempt current and claimed); the
   existing `RecordMentorResponseProgressUseCase` is used only for `summarize-context` and
   stays unchanged. The step then returns normally.
10. **Prepare.** Reads the ready row (if any), `find_range(after=boundary)` and the
    excerpt messages via `find_by_ids` in its read transaction, renders the context with
    `from_summary`, passes `topics` to the router and `history`/`summary` to the reviewer
    request. The attachment answer agent's input is unchanged. Learning/Curriculum/
    Gamification context is read through the existing context provider exactly as today.
11. **Router.** For each part, the existing retrieval runs first. Only if it returns no
    FAQ reference and the part is elliptical does it retry once with
    `part + top-3 topics by similarity to the part`, accepting only results that pass
    the unchanged gates; curriculum proposals and clarifications never use topics.
12. **Cancel / retry / delete / account.** Cancel (existing) makes the attempt non-current
    ⇒ step 8 discards an uncommitted summary; a committed one stays. Retry creates a new
    attempt for the same learner message ⇒ step 3 removes the stale row and step 4
    re-measures. Conversation deletion removes summary rows in
    `RemoveMentorSessionUseCase` immediately after `lock_session`, before events,
    attempts, messages and the tombstone. Account deletion:
    `PurgeMentorSummariesOnAccountDeletedJob` step `purge_mentor_summaries` →
    `PurgeMentorSummariesForAccountUseCase`; later steps fail `assert_response_access`.
13. **Reads.** Detail adds `summary` from the ready row and the newest failed row (its
    attempt's learner message, when no ready row is newer). `GET …/summary` authorizes
    with the existing read grant, loads the ready row and its excerpt messages with
    `find_by_ids`, renders with `from_summary`; absent/foreign/tombstoned ⇒ 404.
14. **Web.** SSE `progress = summarize-context` ⇒ processing marker + disabled composer;
    the closing null-progress status event ends it; `completed` ⇒ existing detail re-read
    ⇒ marker placement; reconnect replays progress via the snapshot. Telemetry emits one
    `summarize` span per step that summarized.

# Verification Contract

## Shared setup

All test files marked `[N]` are **planned**; at implementation kickoff reconcile names
with the actual diff and runner discovery. Invoke only existing files and verified test
names. An empty selection, skip or unavailable dependency is not a pass.

**Server automated.** Existing prerequisites: `apps/server/tests/conftest.py`,
`tests/fixtures/postgres_fixture.py` (disposable PostgreSQL 17 + pgvector, Alembic head,
per-test cleanup), `tests/fixtures/redis_fixture.py`, `tests/fixtures/agentos_fixture.py`
and `tests/fixtures/mentor_job_fixture.py` (registered AgentOS runtime with real local
NLP and `controlled_mentor_endpoint` for the attachment/reviewer endpoint double). Use
`AccountFaker` (`src/shifu/fakers/identity/entities/account_faker.py`) for two active
accounts. Use-case tests mock Core ports with autospec; no Docker. AgentOS tests require
`SHIFU_RUN_REAL_AGENTOS_TESTS=1` and the pinned local Mentor model prepared as in CI
("Prepare pinned local Mentor model"); a skip is Blocked, not passed. Real Inngest job
tests require `SHIFU_RUN_REAL_INNGEST_TESTS=1`. Long conversations are created through
repository fixtures inside the disposable database (messages with controlled
`created_at`), never in shared data.

**Web automated.** Vitest under `apps/web` with `tests/setup.ts`; widget tests mock only
the owning behavior hook and render real internal children. Playwright browser suites
use `tests/playwright.ts`, the BFF fixture and `tests/fixtures/mentor-stream-fixture.ts`
(mocked transport; proves rendered contracts, not real auth or persistence).

**Manual/visual.** Real local services: verify `docker compose ps`, API `GET /health`
and web login; defaults Web 7000, API 7777, Intelligence AgentOS runtime started by the
API lifespan with the pinned local model available. Actor: the existing local account
documented in Tooling's local seed section; resolve its password privately; load
`apps/web/.playwright-cli/states/shifu-auth-state.json` without printing it, or sign in
through the form if expired. Create **one fresh conversation** with a unique marker
(e.g. `[SHIFU-102 VM <timestamp>]` in the first message) and send learner messages
through the UI/API one at a time, waiting for each local answer. The 16th learner
message is the first that triggers (31 messages − 10 recent = 21 ≥ 20). Never reset or
reseed shared data. Cleanup: delete only the conversation created by the journey; close
only task-started browser sessions/processes; leave shared Docker services running.
Artifacts under `apps/web/.playwright-cli/{screenshots,snapshots,logs}/`.

## Automated

### CI-01 — Summarize step policy, fences and failures

**Criteria:** CA-01, CA-02, CA-03, CA-04, CA-07, CA-08, CA-09, CA-12

**Expected result:** exact threshold boundaries (19/20 messages; 15,999/16,000 code
points, including multi-byte characters), recent window of 10 including the pending
message, with and without previous boundary; below threshold no row/progress; stale-row
deletion and same-attempt resume; boundary frozen at evaluation; version increment;
`complete` + `remove_superseded`; span/limit validation ⇒ `invalid_output`;
`OSError`/`ServiceUnavailableError` ⇒ `nlp_unavailable`; other transient ⇒
`exhausted`; fences (tombstone, attempt not current/cancelled, owner lost, row gone,
access revision changed, inactive account) ⇒ no write; no usage receipt recorded;
telemetry outcome values and `failure_code`; the closing null-progress status event in every outcome where the attempt is still current; the processing-row insert happens only under `lock_session` with the session/attempt fences; claim loss, missing attempt, deadlock or `OperationalError` in the claim phase return without raising; the use case never raises.

**Proof:** `apps/server/tests/intelligence/core/use_cases/test_summarize_mentor_session_context_use_case.py` [N] (mocked ports).

```bash
cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_summarize_mentor_session_context_use_case.py
```

**Passing condition:** every listed case asserted, including absent effects; selection non-empty.

### CI-02 — Prepare consumes summary and bounded history

**Criteria:** CA-05

**Expected result:** with a ready summary, `find_range(after=boundary)` replaces
`find_all` and `find_by_ids` loads the excerpt messages; the pending learner message is always included; `summary` and bounded
`history` reach the reviewer request while the attachment answer agent's input is unchanged; `topics` reach `route`; the context provider is
still called with the same hints/references; without a summary, behavior and inputs
equal today's.

**Proof:** `apps/server/tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py` [M].

```bash
cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_prepare_mentor_response_use_case.py
```

**Passing condition:** new and existing cases pass.

### CI-03 — Conversation deletion and account purge use cases

**Criteria:** CA-10, CA-11

**Expected result:** `RemoveMentorSessionUseCase` calls `mentor_session_summaries.remove_by_session_id` inside its
transaction immediately after `lock_session` and before the events, attempts and messages removal and the tombstone (order asserted); `PurgeMentorSummariesForAccountUseCase` removes all
account rows and returns 0 on repeat.

**Proof:** `tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py` [M], `tests/intelligence/core/use_cases/test_purge_mentor_summaries_for_account_use_case.py` [N].

```bash
cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_remove_mentor_session_use_case.py tests/intelligence/core/use_cases/test_purge_mentor_summaries_for_account_use_case.py
```

**Passing condition:** ordering and idempotency asserted.

### CI-04 — Summary reads and detail state

**Criteria:** CA-09, CA-12

**Expected result:** `GetMentorSessionSummaryUseCase` authorizes, renders the ready row
via `MentorConversationSummaryContext.from_summary`, and raises `MentorSessionSummaryNotFoundError` for absent,
foreign and tombstoned sessions alike; `GetMentorSessionUseCase`/`load_mentor_detail`
return `summary.current` (including `after_message_id`, the learner message of the summary's attempt, null when the attempt is gone or belongs to another session) and
`failure_after_message_id` correctly (failed newer than ready only).

**Proof:** `tests/intelligence/core/use_cases/test_get_mentor_session_summary_use_case.py` [N], `tests/intelligence/core/use_cases/test_get_mentor_session_use_case.py` [M].

```bash
cd apps/server && uv run pytest tests/intelligence/core/use_cases/test_get_mentor_session_summary_use_case.py tests/intelligence/core/use_cases/test_get_mentor_session_use_case.py
```

**Passing condition:** all branches asserted.

### CI-05 — Registered answer workflow with summarization

**Criteria:** CA-01, CA-02, CA-03, CA-04, CA-05, CA-06, CA-07, CA-08, CA-09, CA-10, CA-12

**Expected result:** through the registered Intelligence AgentOS runtime with real
spaCy/E5 and PostgreSQL: a conversation crossing the threshold emits a
`summarize-context` progress event before the answer and a closing null-progress status event after it, persists one `ready` row whose
spans are verbatim and within limits, and the answer completes; a second crossing folds
the previous summary into v2 and removes v1; messages stay unchanged and ordered; two
conversations of one account and two accounts never share excerpts; for an attachment
answer through `controlled_mentor_endpoint`, the captured **reviewer** request contains `history` = post-boundary messages
and `summary` and no pre-boundary message text, while the attachment answer request keeps its existing shape; the
router retry fires only for an elliptical unmatched part; a summarizer forced to fail
(fault injected through the registry's `summarizer` seam only in that scenario) yields
`failed/nlp_unavailable`, the answer still completes and a later crossing succeeds;
cancel during summarization discards the uncommitted row; deleting the conversation while a row is `processing` succeeds (no check violation) and leaves no row; a forced claim-phase `OperationalError` lets prepare's existing path decide and the run does not fail in the summary step; the router and summarizer receive the same spaCy/E5 instances from the registry; access revision change discards; the database constraints reject a second
ready/processing row; zero usage receipts and zero model calls for summarization;
captured telemetry spans contain only allowlisted attributes.

**Proof:** `apps/server/tests/intelligence/server/agentos/test_process_mentor_response_summary.py` [N]; composition-only updates in `tests/intelligence/server/agentos/test_process_mentor_response_workflow.py` [M].

```bash
cd apps/server && SHIFU_RUN_REAL_AGENTOS_TESTS=1 uv run pytest tests/intelligence/server/agentos/test_process_mentor_response_summary.py tests/intelligence/server/agentos/test_process_mentor_response_workflow.py
```

**Passing condition:** all scenarios pass with real models (not skipped); fault
injection limited to the failure scenario; persisted rows/events observed through the
database, not internals.

### CI-06 — Controllers and SSE contract

**Criteria:** CA-09, CA-10, CA-12

**Expected result:** detail includes `summary` with null/ready/failed combinations (the ready marker carries `after_message_id`);
`GET …/summary` 200 body shape, `no-store`, 404 for absent/foreign/tombstoned with the
same body, no offsets in any response; deletion removes summary rows; SSE replays the
`summarize-context` progress event and the closing null-progress event after reconnect (`after_sequence`), and the snapshot's `progress` is null after the closing event while `write-answer`/`review-answer` snapshots are unchanged.

**Proof:** `tests/intelligence/server/controllers/test_get_mentor_session_summary_controller.py` [N]; `test_get_mentor_session_controller.py`, `test_remove_mentor_session_controller.py`, `test_stream_mentor_response_controller.py` [M].

```bash
cd apps/server && uv run pytest tests/intelligence/server/controllers/test_get_mentor_session_summary_controller.py tests/intelligence/server/controllers/test_get_mentor_session_controller.py tests/intelligence/server/controllers/test_remove_mentor_session_controller.py tests/intelligence/server/controllers/test_stream_mentor_response_controller.py
```

**Passing condition:** HTTP status, headers, bodies and persisted effects asserted.

### CI-07 — Account-deleted summary purge job

**Criteria:** CA-11

**Expected result:** registered Inngest function
`intelligence-purge-mentor-summaries-on-account-deleted` triggered by
`identity/account.deleted` deletes all summary rows of that account and none of another;
duplicate delivery succeeds without effect; invalid payload is non-retriable; the
attachment purge job still runs for the same event.

**Proof:** `apps/server/tests/messaging/inngest/jobs/intelligence/test_purge_mentor_summaries_on_account_deleted_job.py` [N].

```bash
cd apps/server && SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/intelligence/test_purge_mentor_summaries_on_account_deleted_job.py
```

**Passing condition:** real Inngest execution (not skipped) with persisted effects asserted.

### CI-08 — Summary quality eval

**Criteria:** CA-03, CA-14

**Expected result:** about 12 versioned synthetic pt-BR long conversations (programming
help, topic change, code-heavy, greetings/filler, two near-topic conversations) with
annotated must-keep Dúvidas, Orientações and Assuntos. Per case: Dúvida/Orientação
recall ≥ 0.80, Assunto recall ≥ 0.70, 100% span fidelity (each excerpt is a substring
of its source message), zero leakage across cases, zero fenced-code excerpts. Same
result in `double` and `real` modes (no model calls). A deliberately failing case in
`tests/evals/test_run.py` proves non-zero exit.

**Proof:** `apps/server/evals/summarize_mentor_session_eval.py` [N] with dataset `src/shifu/intelligence/ai/data/mentor-summary-evaluation.json` [N]; registered in `evals/run.py`; `apps/server/tests/evals/test_run.py` [M].

```bash
cd apps/server && uv run python evals/run.py --workflow summarize-mentor-session --output-dir test-results/evals
cd apps/server && uv run pytest tests/evals/test_run.py
```

**Passing condition:** exit code 0, report lists every case with metrics; CI `evals` job runs it with the pinned local model prepared.

### CI-09 — Mentor-context router regression

**Criteria:** CA-06

**Expected result:** existing local FAQ/abstention and NLP integrity behavior unchanged
when `topics` is empty or not applicable.

**Proof:** existing `tests/intelligence/server/agentos/test_process_mentor_response_workflow.py::test_registered_runtime_keeps_indexed_faq_and_abstention_local` and `tests/messaging/inngest/jobs/intelligence/test_mentor_nlp_integrity_job.py`.

```bash
cd apps/server && SHIFU_RUN_REAL_AGENTOS_TESTS=1 uv run pytest "tests/intelligence/server/agentos/test_process_mentor_response_workflow.py::test_registered_runtime_keeps_indexed_faq_and_abstention_local"
cd apps/server && SHIFU_RUN_REAL_INNGEST_TESTS=1 uv run pytest tests/messaging/inngest/jobs/intelligence/test_mentor_nlp_integrity_job.py
```

**Passing condition:** pass unchanged (not skipped). Affected because `LocalMentorRouteProvider.route` changes signature and behavior.

### CI-10 — Web widgets and context

**Criteria:** CA-07, CA-13

**Expected result:** `SummaryMarker` ready/processing/failed variants; "Ver resumo"
(`aria-haspopup="dialog"`) opens the dialog by keyboard, focus moves into it and is trapped; Escape, the close button and "Fechar resumo" close it and return focus to "Ver resumo";
"Ver mensagens originais" closes the dialog and calls `revealMessage(firstMessageId)`; loading and
error states; plain-text rendering of hostile text (`<script>`, Markdown); `MessageItem` exposes `id`/`data-message-id` and is focusable; `Conversation`
item positions (marker after the triggering message when loaded, else after the boundary, else at the top), processing marker replaces
`ResponseStatus` and keeps cancel, failure notice after its message and hidden while
summarizing; composer disabled with the placeholder; provider maps `summary`, derives
`isSummarizingContext` from SSE progress and snapshot replay, clears it on the closing null-progress status event, and `revealMessage` pages
until found (and returns false when absent); the stream consumer accepts `summarize-context` (proven in `mentor-transport-consumer.test.tsx`, not in a dedicated realtime-hook test).

**Proof:** `apps/web/src/ui/intelligence/widgets/components/mentor-chat/conversation/summary-marker/tests/{summary-marker.test.tsx,use-summary-marker.test.ts}` [N]; `conversation/tests/{conversation.test.tsx,use-conversation.test.ts}`, `message-list/message-item/tests/message-item.test.tsx`, `composer/tests/{composer.test.tsx,use-composer.test.ts}`, `contexts/mentor-context/tests/{use-mentor-context-provider.test.ts,mentor-transport-consumer.test.tsx}` [M]. The legacy `hooks/tests/use-mentor-response-stream.test.ts` is not extended (UI Layer: realtime hooks are verified at their consumers).

```bash
pnpm --filter web exec vitest run src/ui/intelligence/widgets/components/mentor-chat/conversation/summary-marker/tests/summary-marker.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/summary-marker/tests/use-summary-marker.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/conversation.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/tests/use-conversation.test.ts src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/composer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/composer/tests/use-composer.test.ts src/ui/intelligence/contexts/mentor-context/tests/use-mentor-context-provider.test.ts src/ui/intelligence/contexts/mentor-context/tests/mentor-transport-consumer.test.tsx src/ui/intelligence/widgets/components/mentor-chat/conversation/message-list/message-item/tests/message-item.test.tsx
```

**Passing condition:** all listed files execute and pass.

### CI-11 — Web browser integration (page and FAB)

**Criteria:** CA-07, CA-13

**Expected result:** with mocked transport/stream fixture: page at 1440 and 390 shows
the processing marker and disabled composer during `summarize-context`, then the ready
marker; "Ver resumo" opens the dialog (role `dialog`, accessible name "Resumo desta conversa"), outgoing request is `GET` to the summary server
function/path; "Ver mensagens originais" closes it, loads older pages (asserted requests with
cursor) and focuses the first message; Escape and "Fechar resumo" return focus to "Ver resumo"; failure notice
renders; no horizontal overflow at 390 (dialog near full-screen with 16 px margins); FAB shows the same states and the dialog above its panel.

**Proof:** `apps/web/tests/intelligence/intelligence-page.test.ts` [M]; `apps/web/tests/shared/app-layout.test.ts` [M].

```bash
pnpm --filter web exec playwright test tests/intelligence/intelligence-page.test.ts tests/shared/app-layout.test.ts
```

**Passing condition:** new scenarios and existing ones in both files pass.

### CI-12 — Server types

**Scope:** `apps/server` (basedpyright project). **Command:** `cd apps/server && uv run poe check:types`. **Passing condition:** zero errors.

### CI-13 — Web types

**Scope:** `apps/web` project and consumers. **Command:** `pnpm --filter web check:types`. **Passing condition:** zero errors.

### CI-14 — Server lint, format and complexity lint

**Scope:** every changed/created Python path above. **Commands:**

```bash
cd apps/server && uv run ruff check --no-fix <changed-paths...>
cd apps/server && uv run ruff format --check <changed-paths...>
```

**Passing condition:** zero diagnostics, including configured `C90` complexity. A
quantitative complexity metric is **not required** by this Spec (no configured runner);
record that disposition, not a pass.

### CI-15 — Web lint and complexity lint

**Scope:** every changed/created web path above. **Command:** `pnpm exec biome check <changed-paths...>` from the repository root. **Passing condition:** zero errors; configured complexity rules reported with their severity; no quantitative metric required.

### CI-16 — Architecture and project gates

**Commands:** `cd apps/server && uv run poe check:architecture` (Tach), `pnpm --filter web check:architecture` (depcruise), `pnpm --filter web build`. **Passing condition:** all pass; no new cross-module import.

### CI-17 — Migration upgrade, downgrade and drift

**Criteria:** CA-04

**Expected result:** in a disposable PostgreSQL 17 + pgvector container started for this check (never the developer or shared database), run Alembic **without** `.env.local` (the `poe db:*` tasks load it when present):

```bash
cd apps/server && DATABASE_URL=postgresql+psycopg://shifu:<disposable-password>@127.0.0.1:<disposable-port>/shifu uv run alembic upgrade head
cd apps/server && DATABASE_URL=postgresql+psycopg://shifu:<disposable-password>@127.0.0.1:<disposable-port>/shifu uv run alembic downgrade -1
cd apps/server && DATABASE_URL=postgresql+psycopg://shifu:<disposable-password>@127.0.0.1:<disposable-port>/shifu uv run alembic upgrade head
```

The database URL variable name and roles are confirmed against `DatabaseSettings` and the CI integration job before running; upgrade, downgrade and re-upgrade succeed; constraints/indexes exist as
declared; CI "Check Alembic migration drift" passes. Recorded as delivery evidence (no
dedicated migration test module, per Database Rules).

**Passing condition:** commands succeed against a disposable database; never against shared data.

### CI-18 — CI coverage and evals wiring

**Scope:** `.github/workflows/server-app-ci.yaml`. **Expected result:** new and modified
server test files appear in the `changed-file-coverage` explicit list;
`check_changed_coverage.py` passes for every changed production file on the PR head;
the `evals` job prepares the pinned local model and runs the new selector. **Passing
condition:** current-head CI green for those jobs (publication only; local-only
completion records CI as not applicable).

## Manual

### VM-01 — Desktop page: summarizing, reading and originals

**Type:** Manual

**Criteria:** CA-13

**Tool / setup:** Playwright CLI from `apps/web` (`playwright-cli -s=shifu open http://127.0.0.1:7000/intelligence`), shared setup, viewport 1440×900.

**Procedure:** create the marked conversation; send 15 learner messages waiting for each
answer; send the 16th and observe "Resumindo contexto…" after it with the composer
disabled; wait for the answer; locate "Contexto resumido"; activate "Ver resumo" by
keyboard; confirm the dialog opens with focus inside; read the summary; activate "Ver mensagens originais"; confirm the dialog closed and the first message is
focused and visible; return to the marker, reopen, press Escape and confirm
focus on "Ver resumo"; reopen and activate "Fechar resumo" with the same result; delete the conversation.

**Passing condition:** URL stays `/intelligence?session=<id>`; requests include the
summary GET (200) and older-page reads; the summary text quotes only this conversation;
no console errors (warnings classified); keyboard-only path works; captures saved for
VM-03..VM-05; conversation deleted at the end.

### VM-02 — FAB and mobile reading journey

**Type:** Manual

**Criteria:** CA-13

**Tool / setup:** same session/conversation setup (a second marked conversation, or
VM-01's before deletion); FAB at 1440×900 on a non-Mentor route; page at 390×844.

**Procedure:** in the FAB open the conversation, "Ver resumo" (dialog above the panel), "Ver mensagens originais",
"Fechar resumo"; at 390 repeat on the page (dialog near full-screen).

**Passing condition:** same outcomes as VM-01 inside the FAB panel; at 390 no horizontal
overflow and buttons ≥ 44 px; captures saved for VM-06; cleanup as in shared setup.

## Visual

### VM-03 — Summarizing state (KVnFQ)

**Type:** Visual

**Criteria:** CA-13

**Reference / setup:** [KVnFQ.png](design/references/KVnFQ.png); VM-01 capture at 1440×900 during `summarize-context`.

**Passing condition:** processing marker after the pending message with `loader-circle`
and "Resumindo contexto…" in jade text; composer disabled with the placeholder; accepted
adaptations from the handoff (cancel kept; composer controls kept disabled).

### VM-04 — Summarized marker (RDiWy)

**Type:** Visual

**Criteria:** CA-13

**Reference / setup:** [RDiWy.png](design/references/RDiWy.png); VM-01 capture after completion.

**Passing condition:** marker anatomy (icon, muted 13 px label, ghost "Ver resumo")
matches ySE0r; position is the learner message that triggered the summary (accepted adaptation).

### VM-05 — Reading dialog desktop (T4Edi content)

**Type:** Visual

**Criteria:** CA-13

**Reference / setup:** [T4Edi.png](design/references/T4Edi.png); VM-01 capture with the dialog open.

**Passing condition:** dialog header follows the shared hierarchy (scroll-text icon tile, title, description = preservation line, top-right close, separator); body/footer match T4Edi's card content (paragraph, two bordered ghost buttons, surface/border/spacing per handoff mapping); container is the centered `max-w-lg` dialog with overlay (approved adaptation); paragraph text is the runtime template (approved adaptation).

### VM-06 — Reading dialog mobile (ov9QQ content)

**Type:** Visual

**Criteria:** CA-13

**Reference / setup:** [ov9QQ.png](design/references/ov9QQ.png); VM-02 capture at 390×844.

**Passing condition:** same header hierarchy as VM-05; near full-screen dialog with 16 px margins, stacked full-width actions as in ov9QQ, scrollable content, no overflow, readable contrast, focus visible.

Integration runs after all scopes are integrated, using the files above; tests are
selected only for the scoped changes and their direct consumers
([Tooling selection policy](../../../tooling.md#selecting-unit-and-integration-tests)).
Broaden only for demonstrated dependency impact (for example a shared fixture change),
recording why. Fix failures and rerun affected checks; review and conclusion reuse
unaffected current proof.

# Documentation Alignment

| Document / authority | Governs | Required update or confirmation | Disposition / dependency |
| --- | --- | --- | --- |
| [Shifu — PRD — Intelligence](https://joaogoliveiragarcia.atlassian.net/wiki/spaces/Shifu/pages/83099649/Shifu+PRD+Intelligence), content 83099649, **version 9** (2026-10-13T16:12:19Z, "Remover elegibilidade ZDR do escopo do ditado browser-managed"), retrieved complete 2026-10-18T11:32-03:00 | RP-15, JN-19 (full); RP-02/03/04/06/11/12/13/14, JN-14/16 (partial); RP-01 not applicable to summarization | No PRD change. SHIFU-102 cites version 7; RP-15/JN-19 text is unchanged in v9. Recheck version at conclusion. | External write not authorized; none required |
| [SHIFU-102](https://joaogoliveiragarcia.atlassian.net/browse/SHIFU-102) (Dev Task, parent SHIFU-29, blocks SHIFU-45) | Delivery scope and acceptance | Trigger criterion, technique and storage defined here as the ticket delegates. Its "execução por IA … ZDR … sem opção elegível" criterion is satisfied by using no AI provider (not applicable), not by a ZDR proof. | No Jira change |
| [mentor-context spec rev18](../mentor-context/spec.md) (SHIFU-100) | Local answer routing | **Supersedes RF-07's "não depende de contexto conversacional gerado / sem sumarização" only for** RF-04's guarded topic retry and the visible summary; everything else unchanged. | Record in its future revision if that Spec is reopened; no edit now |
| [mentor-context design handoff](../mentor-context/design/handoff.md) | Summaries frames exclusion | Superseded for KVnFQ/RDiWy/T4Edi/ov9QQ by [this handoff](design/handoff.md) | — |
| [mentor-sessions-management spec](../mentor-sessions-management/spec.md) (SHIFU-99) | Deletion, detail | Deletion transaction gains summary removal; detail gains `summary`; contracts otherwise unchanged | — |
| [mentor-attachments spec](../mentor-attachments/spec.md) (SHIFU-103) | Attachment answer, reviewer, AgentOS workflow | Reviewer receives bounded history + summary; the attachment answer agent's input is unchanged; workflow gains a first step; no new workflow | — |
| Web dependencies (`apps/web/package.json`) | UI primitives | Adds `@radix-ui/react-dialog` (approved Q30/Q74) and `ui/shadcn/dialog.tsx` | Install with `pnpm --filter web add @radix-ui/react-dialog` at implementation |
| Pre-existing RP-11 gap | Account deletion of sessions/messages/attempts/events | **Not fixed here.** Intelligence still does not purge conversation messages on account deletion; this Spec purges summaries only and does not claim RP-11 compliance for other data. Recommend a separate ticket. | Out of scope; reported |
| [Architecture](../../../architecture.md) "Agentic workflow composition" | Mentor contextual-response description | Add one sentence that the answer workflow summarizes long conversations locally (extractive, no inference) before preparation | Update at implementation |
| [Modules](../../../modules.md) Intelligence | Conversation summaries | Already describes summaries; confirm unchanged | Confirm at conclusion |
| Rules (selected above) and [Tooling](../../../tooling.md) | Boundaries and commands | Confirmed; no rule change | Recheck if scope expands |

# Revision History

| Revision | Date | Contract change | Reason / source |
| --- | --- | --- | --- |
| 1 | 2026-10-18 | Initial contract | SHIFU-102 against PRD v9; user decisions Q1–Q66: local extractive NLP; pre-answer step in the answer workflow (design KVnFQ/RDiWy); thresholds 20 messages / 16,000 code points with 10 recent; single current version; spans; reading dialog (Q74, approved adaptation of T4Edi/ov9QQ); summaries-only account purge. Spec Reviewer findings B1–B2, H1–H8, M1–M4, L1–L4 and recheck R1–R4 resolved before first presentation (Q67–Q78) |
| 2 | 2026-10-20 | RF-10 marker placement: below the boundary's Mentor answer when the boundary is a learner question (presentation only; coverage unchanged); Web contracts and VM-04 wording aligned | User feedback on the seeded conversation: the marker appeared between a question and its answer instead of below the old chat. Handoff updated; CI-10, CI-11, VM-01..VM-04 and VM-02 placement reopened |
| 3 | 2026-10-20 | RF-09/RF-10: `summary.current` gains `after_message_id` (the learner message whose answer run produced the summary, from the summary's attempt; null when the attempt is gone) and the marker is placed right after it; replaces the revision-2 placement rule | User decision (option A) on the seeded conversation: the marker must sit where the summarization happened, after the user's triggering message. Handoff, REST contract, Web contracts, CI-04/CI-06/CI-10/CI-11 and VM-04 placement reopened |
